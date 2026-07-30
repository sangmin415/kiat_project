`default_nettype none

module seven_segment_status (
    input  logic [1:0] state,
    input  logic       event_latched,
    output logic [7:0] segments
);
    always_comb begin
        segments = 8'b0011_1111;       // 0 = NORMAL
        if (state == 2'd1)
            segments = 8'b0000_0110;   // 1 = WARNING
        if (state == 2'd2)
            segments = event_latched
                     ? 8'b0111_1001    // E = ESD_SIM trip
                     : 8'b0011_1000;   // L = vibration limit trip
    end
endmodule

`default_nettype wire

