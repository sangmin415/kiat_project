module servo_command_parser #(
    parameter integer CLK_HZ = 12_000_000, parameter integer TIMEOUT_MS = 100
) (
    input logic clk, input logic reset, input logic [7:0] byte_data, input logic byte_valid,
    output logic [15:0] r0_ticks, r1_ticks, r2_ticks,
    output logic command_valid, checksum_error, command_timeout
);
    localparam integer TIMEOUT_CLKS = (CLK_HZ / 1000) * TIMEOUT_MS;
    localparam integer TW = $clog2(TIMEOUT_CLKS + 1);
    localparam [1:0] HDR0=0, HDR1=1, DATA=2, SUM=3;
    logic [1:0] state; logic [2:0] index; logic [7:0] sum;
    logic [7:0] r0_hi,r0_lo,r1_hi,r1_lo,r2_hi,r2_lo;
    logic [TW-1:0] timeout_count;
    always_ff @(posedge clk) begin
        command_valid <= 0;
        if (reset) begin
            state<=HDR0; index<=0; sum<=0; checksum_error<=0; command_timeout<=1; timeout_count<=0;
            r0_ticks<=16'd18000; r1_ticks<=16'd18000; r2_ticks<=16'd18000;
        end else begin
            if (timeout_count < TIMEOUT_CLKS) timeout_count <= timeout_count + 1'b1;
            if (timeout_count >= TIMEOUT_CLKS-1) command_timeout <= 1;
            if (byte_valid) case (state)
                HDR0: if (byte_data==8'h55) state<=HDR1;
                HDR1: if (byte_data==8'ha5) begin state<=DATA; index<=0; sum<=0; end else state<=HDR0;
                DATA: begin
                    sum <= sum + byte_data;
                    case (index)
                        0:r0_hi<=byte_data; 1:r0_lo<=byte_data;
                        2:r1_hi<=byte_data; 3:r1_lo<=byte_data;
                        4:r2_hi<=byte_data; 5:r2_lo<=byte_data;
                    endcase
                    if (index==5) state<=SUM; else index<=index+1'b1;
                end
                SUM: begin
                    state<=HDR0;
                    if (byte_data==sum) begin
                        r0_ticks<={r0_hi,r0_lo}; r1_ticks<={r1_hi,r1_lo}; r2_ticks<={r2_hi,r2_lo};
                        command_valid<=1; checksum_error<=0; command_timeout<=0; timeout_count<=0;
                    end else checksum_error<=1;
                end
                default: state<=HDR0;
            endcase
        end
    end
endmodule
