`timescale 1ns/1ps
`default_nettype none

module uart_echo_tb;
    localparam integer CLK_HZ = 1_000_000;
    localparam integer BAUD = 100_000;
    localparam integer CLKS_PER_BIT = CLK_HZ / BAUD;
    logic clk = 0, reset = 1, Rx = 1, Tx;
    logic [7:0] last_byte, monitor_data;
    logic rx_seen, tx_busy, monitor_valid;
    always #5 clk = ~clk;

    uart_echo #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) dut (
        .clk(clk), .reset(reset), .Rx(Rx), .Tx(Tx),
        .last_byte(last_byte), .rx_seen(rx_seen), .tx_busy(tx_busy)
    );
    uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) monitor (
        .clk(clk), .reset(reset), .Rx(Tx), .data(monitor_data), .valid(monitor_valid)
    );

    task automatic drive_bit(input logic value);
        integer i;
        begin
            Rx = value;
            for (i = 0; i < CLKS_PER_BIT; i = i + 1) @(posedge clk);
        end
    endtask

    task automatic send_byte(input logic [7:0] value);
        integer i;
        begin
            drive_bit(0);
            for (i = 0; i < 8; i = i + 1) drive_bit(value[i]);
            drive_bit(1);
            drive_bit(1);
        end
    endtask

    task automatic expect_echo(input logic [7:0] expected);
        begin
            wait (monitor_valid);
            if (monitor_data !== expected) begin
                $error("expected=%02x actual=%02x", expected, monitor_data);
                $fatal(1);
            end
            @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("build/uart_echo.vcd");
        $dumpvars(0, uart_echo_tb);
        repeat (4) @(posedge clk);
        @(negedge clk); reset = 0;
        fork send_byte(8'h55); expect_echo(8'h55); join
        if (!rx_seen || last_byte !== 8'h55) $fatal(1, "0x55 not latched");
        repeat (5) @(posedge clk);
        fork send_byte(8'hA3); expect_echo(8'hA3); join
        if (last_byte !== 8'hA3) $fatal(1, "0xA3 not latched");
        $display("PASS: uart_echo_tb");
        $finish;
    end
endmodule

`default_nettype wire

