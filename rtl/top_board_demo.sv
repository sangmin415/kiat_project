`default_nettype none

module top_board_demo (
    input  logic       hwclk,
    input  logic [3:0] pb,
    input  logic       Rx,
    output logic       Tx,
    output logic       CTSn,
    output logic       DCDn,
    output logic [7:0] ss7, ss6, ss5, ss4, ss3, ss2, ss1, ss0,
    output logic [7:0] left, right,
    output logic       red, green, blue
);
    logic [7:0] vibration_level;
    logic [1:0] state;
    logic warning, interlock, motor_enable, event_latched;
    logic [7:0] status_segments, hex_low, hex_high;
    logic [7:0] last_uart_byte;
    logic uart_rx_seen, uart_tx_busy;
    logic [3:0] uart_startup = 4'hF;
    logic uart_reset;

    always_ff @(posedge hwclk) begin
        if (uart_startup != 0) uart_startup <= uart_startup - 1'b1;
    end
    assign uart_reset = |uart_startup;

    always_comb begin
        vibration_level = 8'd5;
        if (pb[1]) vibration_level = 8'd30;
        if (pb[2]) vibration_level = 8'd70;
    end

    interlock_controller controller (
        .clk(hwclk), .reset(pb[0]), .vibration_level(vibration_level),
        .transient_event(pb[3]), .state(state), .warning(warning),
        .interlock(interlock), .motor_enable(motor_enable),
        .event_latched(event_latched)
    );

    uart_echo serial_echo (
        .clk(hwclk), .reset(uart_reset), .Rx(Rx), .Tx(Tx),
        .last_byte(last_uart_byte), .rx_seen(uart_rx_seen),
        .tx_busy(uart_tx_busy)
    );

    seven_segment_status status_display (
        .state(state), .event_latched(event_latched), .segments(status_segments)
    );
    seven_segment_hex low_digit (.value(last_uart_byte[3:0]), .segments(hex_low));
    seven_segment_hex high_digit (.value(last_uart_byte[7:4]), .segments(hex_high));

    always_comb begin
        ss0 = status_segments;
        ss1 = 8'b0;
        if (!interlock && uart_rx_seen) begin
            ss0 = hex_low;
            ss1 = hex_high;
        end
    end

    assign ss2 = 0;
    assign ss3 = 0;
    assign ss4 = 0;
    assign ss5 = 0;
    assign ss6 = 0;
    assign ss7 = 0;
    assign left = uart_rx_seen ? last_uart_byte : {7'b0, motor_enable};
    assign right = {5'b0, uart_tx_busy, interlock, warning};
    assign red = interlock;
    assign green = (state == 2'd0);
    assign blue = warning;
    assign CTSn = 1'b0;
    assign DCDn = 1'b0;
endmodule

`default_nettype wire

