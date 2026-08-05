module top_bno085_pc_servo (
    input logic hwclk, input logic bno_rxc, input logic pc_rxc, input logic zero_button_b,
    output logic Tx, output wire servo_r0, servo_r1, servo_r2, output wire green
);
    localparam integer FRAME_TICKS=240000;
    localparam integer PWM_MIN=13200, PWM_CENTER=18000, PWM_MAX=22800;
    logic [7:0] startup=8'hff; wire reset=|startup;
    always_ff @(posedge hwclk) if(startup!=0) startup<=startup-1'b1;
    logic b_meta,b_sync,b_prev;
    wire b_zero_event=b_sync&&!b_prev;
    always_ff @(posedge hwclk) begin b_meta<=zero_button_b; b_sync<=b_meta; b_prev<=b_sync; end

    logic [7:0] bno_byte,pc_byte; logic bno_valid,pc_valid;
    logic signed [15:0] yaw_cd,pitch_cd,roll_cd,ax,ay,az;
    logic [7:0] sample_seq; logic sample_valid,checksum_error,sensor_timeout,forward_overflow;
    uart_rx #(.CLK_HZ(12_000_000),.BAUD(115_200)) bno_rx(
        .clk(hwclk),.reset(reset),.Rx(~bno_rxc),.data(bno_byte),.valid(bno_valid));
    uart_rx #(.CLK_HZ(12_000_000),.BAUD(115_200)) pc_rx(
        .clk(hwclk),.reset(reset),.Rx(pc_rxc),.data(pc_byte),.valid(pc_valid));
    bno085_rvc_parser sensor(
        .clk(hwclk),.reset(reset),.byte_data(bno_byte),.byte_valid(bno_valid),
        .yaw_cd(yaw_cd),.pitch_cd(pitch_cd),.roll_cd(roll_cd),.accel_x_mg(ax),.accel_y_mg(ay),.accel_z_mg(az),
        .sample_seq(sample_seq),.sample_valid(sample_valid),.checksum_error(checksum_error),.sensor_timeout(sensor_timeout));
    rvc_uart_forwarder forwarder(
        .clk(hwclk),.reset(reset),.rx_data(bno_byte),.rx_valid(bno_valid),.zero_event(b_zero_event),.Tx(Tx),.overflow(forward_overflow));

    logic [15:0] pc_r0,pc_r1,pc_r2; logic command_valid,command_checksum_error,command_timeout;
    servo_command_parser commands(
        .clk(hwclk),.reset(reset),.byte_data(pc_byte),.byte_valid(pc_valid),
        .r0_ticks(pc_r0),.r1_ticks(pc_r1),.r2_ticks(pc_r2),
        .command_valid(command_valid),.checksum_error(command_checksum_error),.command_timeout(command_timeout));
    function automatic [17:0] clamp_pwm(input [15:0] ticks);
        if(ticks<PWM_MIN) clamp_pwm=PWM_MIN; else if(ticks>PWM_MAX) clamp_pwm=PWM_MAX; else clamp_pwm=ticks;
    endfunction
    wire [17:0] safe_r0=(sensor_timeout||command_timeout)?PWM_CENTER:clamp_pwm(pc_r0);
    wire [17:0] safe_r1=(sensor_timeout||command_timeout)?PWM_CENTER:clamp_pwm(pc_r1);
    wire [17:0] safe_r2=(sensor_timeout||command_timeout)?PWM_CENTER:clamp_pwm(pc_r2);
    logic [17:0] frame_count;
    always_ff @(posedge hwclk) if(reset||frame_count==FRAME_TICKS-1) frame_count<=0; else frame_count<=frame_count+1'b1;
    assign servo_r0=frame_count<safe_r0; assign servo_r1=frame_count<safe_r1; assign servo_r2=frame_count<safe_r2;
    assign green=!(sensor_timeout||command_timeout);
endmodule
