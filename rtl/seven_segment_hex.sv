`default_nettype none

module seven_segment_hex (
    input  logic [3:0] value,
    output logic [7:0] segments
);
    always_comb begin
        case (value)
            4'h0: segments = 8'b0011_1111;
            4'h1: segments = 8'b0000_0110;
            4'h2: segments = 8'b0101_1011;
            4'h3: segments = 8'b0100_1111;
            4'h4: segments = 8'b0110_0110;
            4'h5: segments = 8'b0110_1101;
            4'h6: segments = 8'b0111_1101;
            4'h7: segments = 8'b0000_0111;
            4'h8: segments = 8'b0111_1111;
            4'h9: segments = 8'b0110_1111;
            4'hA: segments = 8'b0111_0111;
            4'hB: segments = 8'b0111_1100;
            4'hC: segments = 8'b0011_1001;
            4'hD: segments = 8'b0101_1110;
            4'hE: segments = 8'b0111_1001;
            default: segments = 8'b0111_0001;
        endcase
    end
endmodule

`default_nettype wire

