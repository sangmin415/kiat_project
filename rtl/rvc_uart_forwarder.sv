module rvc_uart_forwarder #(
    parameter integer CLK_HZ = 12_000_000, parameter integer BAUD = 115_200
) (
    input logic clk, input logic reset, input logic [7:0] rx_data, input logic rx_valid,
    input logic zero_event, output logic Tx, output logic overflow
);
    logic [7:0] fifo [0:7], tx_data;
    logic [2:0] write_ptr, read_ptr; logic [3:0] count;
    logic tx_start, tx_busy, event_pending; logic [1:0] event_index;
    wire event_launch = !tx_busy && event_pending && count==0;
    wire pop = !tx_busy && !event_launch && count!=0;
    wire push = rx_valid && count!=8;
    function automatic [7:0] event_byte(input [1:0] index);
        case(index)
            0:event_byte=8'h55; 1:event_byte=8'h5a; 2:event_byte=8'h42; default:event_byte=8'hf1;
        endcase
    endfunction
    uart_tx #(.CLK_HZ(CLK_HZ),.BAUD(BAUD)) tx_engine(
        .clk(clk),.reset(reset),.data(tx_data),.start(tx_start),.Tx(Tx),.busy(tx_busy));
    always_ff @(posedge clk or posedge reset) begin
        if(reset) begin
            write_ptr<=0;read_ptr<=0;count<=0;tx_data<=0;tx_start<=0;overflow<=0;
            event_pending<=0;event_index<=0;
        end else begin
            tx_start<=0;
            if(zero_event) event_pending<=1;
            if(rx_valid&&count==8) overflow<=1;
            if(push) begin fifo[write_ptr]<=rx_data;write_ptr<=write_ptr+1'b1;end
            if(event_launch) begin
                tx_data<=event_byte(event_index);tx_start<=1;
                if(event_index==3) begin event_index<=0;event_pending<=0;end
                else event_index<=event_index+1'b1;
            end else if(pop) begin
                tx_data<=fifo[read_ptr];read_ptr<=read_ptr+1'b1;tx_start<=1;
            end
            case({push,pop})
                2'b10:count<=count+1'b1;
                2'b01:count<=count-1'b1;
                default:count<=count;
            endcase
        end
    end
endmodule
