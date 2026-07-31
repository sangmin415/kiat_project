`default_nettype none

module top_board_demo #(
    parameter integer CLK_HZ = 12_000_000,
    parameter integer BAUD   = 115_200
) (
    input  logic hwclk,
    input  logic [3:0] pb,
    input  logic Rx,
    output logic Tx, CTSn, DCDn,
    output logic [7:0] ss7, ss6, ss5, ss4, ss3, ss2, ss1, ss0,
    output logic [7:0] left, right,
    output logic red, green, blue
);
    localparam [7:0] CMD_RUN_NORMAL = 8'h10, CMD_WARNING = 8'h11;
    localparam [7:0] CMD_VIB_TRIP = 8'h12, CMD_ESD_TRIP = 8'h13;
    localparam [7:0] CMD_RESET = 8'h14, CMD_STOP = 8'h15, CMD_GET_STATUS = 8'hF0;

    logic [7:0] vibration_level, software_vibration;
    logic [1:0] state;
    logic warning, interlock, controller_motor_enable, motor_enable;
    logic event_latched, operator_stop;
    logic [7:0] status_segments, hex_low, hex_high;
    logic [7:0] last_uart_byte, uart_rx_data;
    logic uart_rx_seen, uart_rx_valid, uart_tx_busy;
    logic [3:0] uart_startup = 4'hF;
    logic uart_reset, controller_reset, software_reset, software_event;
    logic [7:0] reply_data;
    logic reply_start;

    always_ff @(posedge hwclk) begin
        if (uart_startup != 0) uart_startup <= uart_startup - 1'b1;
    end
    assign uart_reset = |uart_startup;
    assign controller_reset = pb[0] | software_reset | uart_reset;

    always_comb begin
        vibration_level = software_vibration;
        if (pb[1] && vibration_level < 8'd30) vibration_level = 8'd30;
        if (pb[2]) vibration_level = 8'd70;
    end

    always_ff @(posedge hwclk) begin
        software_reset <= 1'b0;
        software_event <= 1'b0;
        reply_start <= 1'b0;
        if (uart_reset) begin
            software_vibration <= 8'd5;
            operator_stop <= 1'b1;
            reply_data <= 8'h80;
        end else if (uart_rx_valid) begin
            case (uart_rx_data)
                CMD_RUN_NORMAL: begin software_vibration <= 8'd5; operator_stop <= 1'b0; end
                CMD_WARNING: begin software_vibration <= 8'd30; operator_stop <= 1'b0; end
                CMD_VIB_TRIP: begin software_vibration <= 8'd70; operator_stop <= 1'b0; end
                CMD_ESD_TRIP: begin software_event <= 1'b1; operator_stop <= 1'b0; end
                CMD_RESET: begin
                    software_reset <= 1'b1; software_vibration <= 8'd5; operator_stop <= 1'b1;
                end
                CMD_STOP: begin software_vibration <= 8'd5; operator_stop <= 1'b1; end
                CMD_GET_STATUS: begin
                    reply_data <= {1'b1, event_latched, motor_enable, 1'b0,
                                   state, 1'b0, operator_stop};
                    reply_start <= 1'b1;
                end
                default: begin end
            endcase
        end
    end

    interlock_controller controller (
        .clk(hwclk), .reset(controller_reset), .vibration_level(vibration_level),
        .transient_event(pb[3] | software_event), .state(state), .warning(warning),
        .interlock(interlock), .motor_enable(controller_motor_enable),
        .event_latched(event_latched));
    assign motor_enable = controller_motor_enable & ~operator_stop;

    uart_command_link #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) serial_link (
        .clk(hwclk), .reset(uart_reset), .Rx(Rx), .Tx(Tx),
        .rx_data(uart_rx_data), .rx_valid(uart_rx_valid),
        .reply_data(reply_data), .reply_start(reply_start),
        .last_byte(last_uart_byte), .rx_seen(uart_rx_seen), .tx_busy(uart_tx_busy));

    seven_segment_status status_display (
        .state(state), .event_latched(event_latched), .segments(status_segments));
    seven_segment_hex low_digit (.value(last_uart_byte[3:0]), .segments(hex_low));
    seven_segment_hex high_digit (.value(last_uart_byte[7:4]), .segments(hex_high));

    always_comb begin
        ss0 = status_segments; ss1 = 8'b0;
        if (!interlock && uart_rx_seen) begin ss0 = hex_low; ss1 = hex_high; end
    end

    assign ss2 = 0; assign ss3 = 0; assign ss4 = 0;
    assign ss5 = 0; assign ss6 = 0; assign ss7 = 0;
    assign left = uart_rx_seen ? last_uart_byte : {7'b0, motor_enable};
    assign right = {4'b0, operator_stop, uart_tx_busy, interlock, warning};
    assign red = interlock;
    assign green = (state == 2'd0) && !operator_stop;
    assign blue = warning | operator_stop;
    assign CTSn = 1'b0;
    assign DCDn = 1'b0;
endmodule

`default_nettype wire

