`timescale 1ns/1ps

module top_bno_uart_bridge_tb;
    reg hwclk = 1'b0;
    reg bno_rxc;
    wire Tx;
    top_bno_uart_bridge dut (.hwclk(hwclk), .bno_rxc(bno_rxc), .Tx(Tx));
    always #5 hwclk = ~hwclk;
    task check;
        input expected;
        begin
            #1;
            if (Tx !== expected) begin
                $display("ERROR: expected Tx=%b, observed Tx=%b", expected, Tx);
                $fatal;
            end
        end
    endtask
    initial begin
        bno_rxc = 1'b1; check(1'b1);
        bno_rxc = 1'b0; check(1'b0);
        bno_rxc = 1'b1; check(1'b1);
        bno_rxc = 1'b0; check(1'b0);
        $display("PASS: top_bno_uart_bridge_tb");
        $finish;
    end
endmodule
