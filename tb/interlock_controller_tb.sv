`timescale 1ns/1ps
`default_nettype none

module interlock_controller_tb;
    logic clk = 0;
    logic reset = 0;
    logic [7:0] vibration_level = 0;
    logic transient_event = 0;
    logic [1:0] state;
    logic warning, interlock, motor_enable, event_latched;

    always #5 clk = ~clk;

    interlock_controller dut (.*);

    task automatic check(input logic [1:0] expected_state,
                         input logic expected_motor,
                         input string label);
        @(negedge clk);
        if (state !== expected_state || motor_enable !== expected_motor) begin
            $error("%s: state=%0d motor=%0b", label, state, motor_enable);
            $fatal(1);
        end
    endtask

    initial begin
        $dumpfile("build/interlock_controller.vcd");
        $dumpvars(0, interlock_controller_tb);

        reset = 1; repeat (2) @(posedge clk); @(negedge clk); reset = 0;
        vibration_level = 8'd5;  check(2'd0, 1'b1, "NORMAL");
        vibration_level = 8'd30; check(2'd1, 1'b1, "WARNING");
        vibration_level = 8'd70; check(2'd2, 1'b0, "VIBRATION TRIP");

        vibration_level = 8'd5;  check(2'd2, 1'b0, "TRIP LATCHED");
        reset = 1; @(posedge clk); @(negedge clk); reset = 0;
        check(2'd0, 1'b1, "RESET");

        transient_event = 1; @(posedge clk); @(negedge clk); transient_event = 0;
        check(2'd2, 1'b0, "ESD_SIM TRIP");
        if (!event_latched) $fatal(1, "event_latched was not set");

        $display("PASS: interlock_controller_tb");
        $finish;
    end
endmodule

`default_nettype wire


