`timescale 1ns/1ps
module rvc_uart_forwarder_tb;
    logic clk = 0, reset = 1;
    logic [7:0] rx_data = 0;
    logic rx_valid = 0, zero_event = 0;
    logic tx, overflow;
    logic [7:0] decoded;
    logic decoded_valid;
    logic [7:0] received [0:2];
    integer received_count = 0;

    always #5 clk = ~clk;

    rvc_uart_forwarder #(.CLK_HZ(1_000_000), .BAUD(100_000)) dut (
        .clk(clk), .reset(reset), .rx_data(rx_data), .rx_valid(rx_valid), .zero_event(zero_event),
        .Tx(tx), .overflow(overflow)
    );

    uart_rx #(.CLK_HZ(1_000_000), .BAUD(100_000)) monitor (
        .clk(clk), .reset(reset), .Rx(tx), .data(decoded), .valid(decoded_valid)
    );

    always_ff @(posedge clk) begin
        if (decoded_valid && received_count < 3) begin
            received[received_count] <= decoded;
            received_count <= received_count + 1;
        end
    end

    initial begin
        repeat (4) @(posedge clk);
        reset = 0;

        @(negedge clk); rx_data = 8'h12; rx_valid = 1;
        @(negedge clk); rx_data = 8'h34;
        @(negedge clk); rx_data = 8'h56;
        @(negedge clk); rx_valid = 0;

        repeat (500) @(posedge clk);
        if (overflow) $fatal(1, "unexpected FIFO overflow");
        if (received_count != 3)
            $fatal(1, "expected 3 bytes, received %0d", received_count);
        if (received[0] !== 8'h12 || received[1] !== 8'h34 || received[2] !== 8'h56)
            $fatal(1, "byte mismatch: %02x %02x %02x",
                   received[0], received[1], received[2]);
        $display("PASS: rvc_uart_forwarder_tb");
        $finish;
    end
endmodule
