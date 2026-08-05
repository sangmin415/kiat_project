module rvc_uart_forwarder #(
    parameter integer CLK_HZ = 12_000_000, parameter integer BAUD = 115_200
) (
    input logic clk, input logic reset, input logic [7:0] rx_data, input logic rx_valid,
    output logic Tx, output logic overflow
);
    logic [7:0] fifo [0:7], tx_data;
    logic [2:0] write_ptr, read_ptr;
    logic [3:0] count;
    logic tx_start, tx_busy;
    wire push = rx_valid && (count != 4'd8);
    // tx_start is registered, so uart_tx does not raise busy until the
    // following clock. Blocking another pop while start is pending prevents
    // the next FIFO byte from being discarded during that one-cycle window.
    wire pop = !tx_busy && !tx_start && (count != 0);

    uart_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) tx_engine (
        .clk(clk), .reset(reset), .data(tx_data), .start(tx_start), .Tx(Tx), .busy(tx_busy)
    );
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            write_ptr <= 0; read_ptr <= 0; count <= 0; tx_data <= 0; tx_start <= 0; overflow <= 0;
        end else begin
            tx_start <= 0;
            if (rx_valid && count == 4'd8) overflow <= 1;
            if (push) begin fifo[write_ptr] <= rx_data; write_ptr <= write_ptr + 1'b1; end
            if (pop) begin tx_data <= fifo[read_ptr]; read_ptr <= read_ptr + 1'b1; tx_start <= 1; end
            case ({push, pop})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: count <= count;
            endcase
        end
    end
endmodule
