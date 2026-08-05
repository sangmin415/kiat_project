module top_riscv_bno_3axis_cpu (
    input logic hwclk, input logic bno_rxc, input logic zero_button,
    output logic Tx, output wire servo_r0, servo_r1, servo_r2, output wire green
);
    localparam integer FRAME_TICKS = 240000;
    localparam integer PWM_MIN_TICKS = 13200, PWM_CENTER_TICKS = 18000, PWM_MAX_TICKS = 22800;
    logic [1:0] phase = 0;
    wire memclk = hwclk, cpu_clk = ~phase[1];
    always_ff @(posedge memclk) phase <= phase + 1'b1;

    logic [7:0] startup = 8'hff;
    wire reset = |startup;
    always_ff @(posedge hwclk) if (startup != 0) startup <= startup - 1'b1;

    logic [7:0] rx_data;
    logic rx_valid;
    logic signed [15:0] yaw_cd, pitch_cd, roll_cd, accel_x, accel_y, accel_z;
    logic [7:0] sample_seq;
    logic sample_valid, checksum_error, sensor_timeout, forward_overflow;
    uart_rx #(.CLK_HZ(12_000_000), .BAUD(115_200)) bno_receiver (
        .clk(hwclk), .reset(reset), .Rx(bno_rxc), .data(rx_data), .valid(rx_valid)
    );
    bno085_rvc_parser_cpu parser (
        .clk(hwclk), .reset(reset), .byte_data(rx_data), .byte_valid(rx_valid),
        .yaw_cd(yaw_cd), .pitch_cd(pitch_cd), .roll_cd(roll_cd),
        .accel_x_mg(accel_x), .accel_y_mg(accel_y), .accel_z_mg(accel_z),
        .sample_seq(sample_seq), .sample_valid(sample_valid),
        .checksum_error(checksum_error), .sensor_timeout(sensor_timeout)
    );
    rvc_uart_forwarder gui_forwarder (
        .clk(hwclk), .reset(reset), .rx_data(rx_data), .rx_valid(rx_valid),
        .Tx(Tx), .overflow(forward_overflow)
    );

    logic [31:0] monitor_pc, monitor_wb_data, mmio_addr, mmio_dout, mmio_din;
    logic [4:0] monitor_wb_reg;
    logic monitor_wb_we, monitor_halt;
    logic [3:0] mmio_be;
    logic mmio_we, mmio_re;
    logic [17:0] pwm_r0_reg, pwm_r1_reg, pwm_r2_reg;
    logic cpu_seen_pwm_write;

    riscvmove #(
        .INIT_FILE("build/gimbal/cpu_3axis_program.hex"),
        .DATA_INIT_FILE("build/gimbal/cpu_3axis_data.hex")
    ) cpu (
        .clk(cpu_clk), .memclk(memclk), .phase(phase), .reset(reset),
        .monitor_pc(monitor_pc), .monitor_wb_data(monitor_wb_data),
        .monitor_wb_reg(monitor_wb_reg), .monitor_wb_we(monitor_wb_we), .monitor_halt(monitor_halt),
        .mmio_addr(mmio_addr), .mmio_dout(mmio_dout), .mmio_be(mmio_be),
        .mmio_we(mmio_we), .mmio_re(mmio_re), .mmio_din(mmio_din)
    );

    always_comb begin
        mmio_din = 0;
        case (mmio_addr)
            32'h8000_0060: mmio_din = {{16{roll_cd[15]}}, roll_cd};
            32'h8000_0064: mmio_din = {16'b0, sample_seq, 4'b0, forward_overflow, checksum_error, sample_valid, sensor_timeout};
            32'h8000_0068: mmio_din = {{14{1'b0}}, pwm_r0_reg};
            32'h8000_006c: mmio_din = {31'b0, zero_button};
            32'h8000_0070: mmio_din = {{16{pitch_cd[15]}}, pitch_cd};
            32'h8000_0074: mmio_din = {{16{yaw_cd[15]}}, yaw_cd};
            32'h8000_0078: mmio_din = {{14{1'b0}}, pwm_r1_reg};
            32'h8000_007c: mmio_din = {{14{1'b0}}, pwm_r2_reg};
            default: ;
        endcase
    end

    always_ff @(posedge memclk) begin
        if (reset) begin
            pwm_r0_reg <= PWM_CENTER_TICKS; pwm_r1_reg <= PWM_CENTER_TICKS; pwm_r2_reg <= PWM_CENTER_TICKS;
            cpu_seen_pwm_write <= 0;
        end else if (mmio_we) begin
            if (mmio_addr == 32'h8000_0068 || mmio_addr == 32'h8000_0078 || mmio_addr == 32'h8000_007c)
                cpu_seen_pwm_write <= 1;
            if (mmio_addr == 32'h8000_0068)
                if (mmio_dout < PWM_MIN_TICKS) pwm_r0_reg <= PWM_MIN_TICKS;
                else if (mmio_dout > PWM_MAX_TICKS) pwm_r0_reg <= PWM_MAX_TICKS;
                else pwm_r0_reg <= mmio_dout[17:0];
            if (mmio_addr == 32'h8000_0078)
                if (mmio_dout < PWM_MIN_TICKS) pwm_r1_reg <= PWM_MIN_TICKS;
                else if (mmio_dout > PWM_MAX_TICKS) pwm_r1_reg <= PWM_MAX_TICKS;
                else pwm_r1_reg <= mmio_dout[17:0];
            if (mmio_addr == 32'h8000_007c)
                if (mmio_dout < PWM_MIN_TICKS) pwm_r2_reg <= PWM_MIN_TICKS;
                else if (mmio_dout > PWM_MAX_TICKS) pwm_r2_reg <= PWM_MAX_TICKS;
                else pwm_r2_reg <= mmio_dout[17:0];
        end
    end

    logic [17:0] pwm_count;
    wire [17:0] safe_r0 = (sensor_timeout || !cpu_seen_pwm_write) ? PWM_CENTER_TICKS : pwm_r0_reg;
    wire [17:0] safe_r1 = (sensor_timeout || !cpu_seen_pwm_write) ? PWM_CENTER_TICKS : pwm_r1_reg;
    wire [17:0] safe_r2 = (sensor_timeout || !cpu_seen_pwm_write) ? PWM_CENTER_TICKS : pwm_r2_reg;
    always_ff @(posedge hwclk) begin
        if (reset || pwm_count == FRAME_TICKS - 1) pwm_count <= 0;
        else pwm_count <= pwm_count + 1'b1;
    end
    assign servo_r0 = (pwm_count < safe_r0);
    assign servo_r1 = (pwm_count < safe_r1);
    assign servo_r2 = (pwm_count < safe_r2);
    assign green = cpu_seen_pwm_write;
endmodule
