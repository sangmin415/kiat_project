`default_nettype none

module uart_rx #(
    parameter integer CLK_HZ = 12_000_000,
    parameter integer BAUD   = 115_200
) (
    input  logic       clk,
    input  logic       reset,
    input  logic       Rx,
    output logic [7:0] data,
    output logic       valid
);
    localparam integer CLKS_PER_BIT = CLK_HZ / BAUD;
    localparam integer HALF_BIT = CLKS_PER_BIT / 2;
    localparam [1:0] IDLE = 2'd0, START = 2'd1, DATA = 2'd2, STOP = 2'd3;
    logic rx_meta, rx_sync;
    logic [1:0] state;
    logic [15:0] count;
    logic [2:0] bit_index;
    logic [7:0] shift;

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            rx_meta <= 1'b1;
            rx_sync <= 1'b1;
        end else begin
            rx_meta <= Rx;
            rx_sync <= rx_meta;
        end
    end

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= IDLE;
            count <= 0;
            bit_index <= 0;
            shift <= 0;
            data <= 0;
            valid <= 1'b0;
        end else begin
            valid <= 1'b0;
            case (state)
                IDLE: if (!rx_sync) begin
                    count <= HALF_BIT - 1;
                    state <= START;
                end
                START: if (count == 0) begin
                    if (!rx_sync) begin
                        count <= CLKS_PER_BIT - 1;
                        bit_index <= 0;
                        state <= DATA;
                    end else state <= IDLE;
                end else count <= count - 1'b1;
                DATA: if (count == 0) begin
                    shift[bit_index] <= rx_sync;
                    count <= CLKS_PER_BIT - 1;
                    if (bit_index == 7) state <= STOP;
                    else bit_index <= bit_index + 1'b1;
                end else count <= count - 1'b1;
                STOP: if (count == 0) begin
                    if (rx_sync) begin
                        data <= shift;
                        valid <= 1'b1;
                    end
                    state <= IDLE;
                end else count <= count - 1'b1;
                default: state <= IDLE;
            endcase
        end
    end
endmodule


module uart_tx #(
    parameter integer CLK_HZ = 12_000_000,
    parameter integer BAUD   = 115_200
) (
    input  logic       clk,
    input  logic       reset,
    input  logic [7:0] data,
    input  logic       start,
    output logic       Tx,
    output logic       busy
);
    localparam integer CLKS_PER_BIT = CLK_HZ / BAUD;
    logic [9:0] frame;
    logic [3:0] bit_index;
    logic [15:0] count;

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            Tx <= 1'b1;
            busy <= 1'b0;
            frame <= 10'h3ff;
            bit_index <= 0;
            count <= 0;
        end else if (!busy) begin
            Tx <= 1'b1;
            if (start) begin
                frame <= {1'b1, data, 1'b0};
                bit_index <= 0;
                count <= CLKS_PER_BIT - 1;
                Tx <= 1'b0;
                busy <= 1'b1;
            end
        end else if (count == 0) begin
            if (bit_index == 9) begin
                Tx <= 1'b1;
                busy <= 1'b0;
            end else begin
                bit_index <= bit_index + 1'b1;
                Tx <= frame[bit_index + 1'b1];
                count <= CLKS_PER_BIT - 1;
            end
        end else count <= count - 1'b1;
    end
endmodule


module uart_echo #(
    parameter integer CLK_HZ = 12_000_000,
    parameter integer BAUD   = 115_200
) (
    input  logic       clk,
    input  logic       reset,
    input  logic       Rx,
    output logic       Tx,
    output logic [7:0] last_byte,
    output logic       rx_seen,
    output logic       tx_busy
);
    logic [7:0] rx_data;
    logic rx_valid, tx_start;

    uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) receiver (
        .clk(clk), .reset(reset), .Rx(Rx), .data(rx_data), .valid(rx_valid)
    );
    uart_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) transmitter (
        .clk(clk), .reset(reset), .data(last_byte), .start(tx_start),
        .Tx(Tx), .busy(tx_busy)
    );

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            last_byte <= 0;
            rx_seen <= 1'b0;
            tx_start <= 1'b0;
        end else begin
            tx_start <= 1'b0;
            if (rx_valid) begin
                last_byte <= rx_data;
                rx_seen <= 1'b1;
                if (!tx_busy) tx_start <= 1'b1;
            end
        end
    end
endmodule

`default_nettype wire

