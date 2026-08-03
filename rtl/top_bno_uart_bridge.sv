`default_nettype none

// Stage-1 BNO085 test: raw UART-RVC is forwarded to the on-board FTDI UART.
// R1 is an input in this design; B12 is the FPGA-to-PC serial transmit pin.
module top_bno_uart_bridge (
    input  wire hwclk,
    input  wire bno_rxc,
    output wire Tx
);
    wire unused_clock = hwclk;
    assign Tx = bno_rxc;
endmodule

`default_nettype wire
