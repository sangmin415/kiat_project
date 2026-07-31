`timescale 1ns/1ps
`default_nettype none
module top_board_uart_demo_tb_v2;
    localparam integer CLK_HZ = 1_000_000, BAUD = 100_000;
    localparam integer CLKS_PER_BIT = CLK_HZ / BAUD;
    logic hwclk = 0, Rx = 1; logic [3:0] pb = 0;
    logic Tx, CTSn, DCDn, red, green, blue;
    logic [7:0] ss7, ss6, ss5, ss4, ss3, ss2, ss1, ss0, left, right;
    logic [7:0] monitor_data; logic monitor_valid;
    always #5 hwclk = ~hwclk;
    top_board_demo #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) dut (.*);
    uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) monitor (
        .clk(hwclk), .reset(1'b0), .Rx(Tx), .data(monitor_data), .valid(monitor_valid));
    task automatic drive_bit(input logic value);
        integer i; begin Rx = value; for (i=0; i<CLKS_PER_BIT; i=i+1) @(posedge hwclk); end
    endtask
    task automatic send_byte(input logic [7:0] value);
        integer i; begin drive_bit(0); for (i=0; i<8; i=i+1) drive_bit(value[i]); drive_bit(1); drive_bit(1); end
    endtask
    task automatic expect_byte(input logic [7:0] expected, input string label);
        begin
            if (monitor_valid) wait (!monitor_valid);
            wait (monitor_valid);
            if (monitor_data !== expected) begin
                $error("%s expected=%02x actual=%02x", label, expected, monitor_data); $fatal(1);
            end
            wait (!monitor_valid);
        end
    endtask
    task automatic command(input logic [7:0] value);
        begin fork send_byte(value); expect_byte(value, "command echo"); join end
    endtask
    task automatic query(input logic [7:0] expected);
        begin fork send_byte(8'hF0); expect_byte(expected, "status"); join end
    endtask
    initial begin
        $dumpfile("build/top_board_uart_demo.vcd"); $dumpvars(0, top_board_uart_demo_tb_v2);
        repeat (25) @(posedge hwclk);
        command(8'h10); repeat (4) @(posedge hwclk); query(8'hA0);
        command(8'h11); repeat (4) @(posedge hwclk); query(8'hA4);
        command(8'h14); repeat (4) @(posedge hwclk); query(8'h81);
        command(8'h12); repeat (4) @(posedge hwclk); query(8'h88);
        command(8'h14); repeat (4) @(posedge hwclk);
        command(8'h13); repeat (4) @(posedge hwclk); query(8'hC8);
        $display("PASS: top_board_uart_demo_tb"); $finish;
    end
endmodule
`default_nettype wire

