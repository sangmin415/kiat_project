`default_nettype none

module top_board_demo (
    input  logic       hwclk,
    input  logic [3:0] pb,
    output logic [7:0] ss7, ss6, ss5, ss4, ss3, ss2, ss1, ss0,
    output logic [7:0] left, right,
    output logic       red, green, blue
);
    logic [7:0] vibration_level;
    logic [1:0] state;
    logic warning, interlock, motor_enable, event_latched;

    // Pre-hardware demo controls:
    // PB0 reset, PB1 warning vibration, PB2 dangerous vibration, PB3 ESD_SIM.
    always_comb begin
        vibration_level = 8'd5;
        if (pb[1]) vibration_level = 8'd30;
        if (pb[2]) vibration_level = 8'd70;
    end

    interlock_controller controller (
        .clk(hwclk),
        .reset(pb[0]),
        .vibration_level(vibration_level),
        .transient_event(pb[3]),
        .state(state),
        .warning(warning),
        .interlock(interlock),
        .motor_enable(motor_enable),
        .event_latched(event_latched)
    );

    seven_segment_status display (
        .state(state),
        .event_latched(event_latched),
        .segments(ss0)
    );

    assign ss1 = 8'b0; assign ss2 = 8'b0; assign ss3 = 8'b0;
    assign ss4 = 8'b0; assign ss5 = 8'b0; assign ss6 = 8'b0;
    assign ss7 = 8'b0;

    assign left  = {7'b0, motor_enable};
    assign right = {6'b0, interlock, warning};
    assign red   = interlock;
    assign green = (state == 2'd0);
    assign blue  = warning;
endmodule

`default_nettype wire

