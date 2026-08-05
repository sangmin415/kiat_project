module uart_rx #(
    parameter integer CLK_HZ = 12_000_000, parameter integer BAUD = 115_200
) (
    input logic clk, input logic reset, input logic Rx,
    output logic [7:0] data, output logic valid
);
    localparam integer CLKS_PER_BIT = CLK_HZ / BAUD;
    localparam integer HALF_BIT = CLKS_PER_BIT / 2;
    localparam [1:0] IDLE=0, START=1, DATA=2, STOP=3;
    logic rx_meta, rx_sync; logic [1:0] state; logic [15:0] count;
    logic [2:0] bit_index; logic [7:0] shift;
    always_ff @(posedge clk or posedge reset)
        if (reset) begin rx_meta<=1; rx_sync<=1; end
        else begin rx_meta<=Rx; rx_sync<=rx_meta; end
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin state<=IDLE; count<=0; bit_index<=0; shift<=0; data<=0; valid<=0; end
        else begin
            valid<=0;
            case (state)
                IDLE: if (!rx_sync) begin count<=HALF_BIT-1; state<=START; end
                START: if (count==0) begin
                    if (!rx_sync) begin count<=CLKS_PER_BIT-1; bit_index<=0; state<=DATA; end
                    else state<=IDLE;
                end else count<=count-1'b1;
                DATA: if (count==0) begin
                    shift[bit_index]<=rx_sync; count<=CLKS_PER_BIT-1;
                    if (bit_index==7) state<=STOP; else bit_index<=bit_index+1'b1;
                end else count<=count-1'b1;
                STOP: if (count==0) begin
                    if (rx_sync) begin data<=shift; valid<=1; end
                    state<=IDLE;
                end else count<=count-1'b1;
                default: state<=IDLE;
            endcase
        end
    end
endmodule

module uart_tx #(
    parameter integer CLK_HZ = 12_000_000, parameter integer BAUD = 115_200
) (
    input logic clk, input logic reset, input logic [7:0] data, input logic start,
    output logic Tx, output logic busy
);
    localparam integer CLKS_PER_BIT = CLK_HZ / BAUD;
    logic [9:0] frame; logic [3:0] bit_index; logic [15:0] count;
    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin Tx<=1; busy<=0; frame<=10'h3ff; bit_index<=0; count<=0; end
        else if (!busy) begin
            Tx<=1;
            if (start) begin frame<={1'b1,data,1'b0}; bit_index<=0; count<=CLKS_PER_BIT-1; Tx<=0; busy<=1; end
        end else if (count==0) begin
            if (bit_index==9) begin Tx<=1; busy<=0; end
            else begin bit_index<=bit_index+1'b1; Tx<=frame[bit_index+1'b1]; count<=CLKS_PER_BIT-1; end
        end else count<=count-1'b1;
    end
endmodule
