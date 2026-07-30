`default_nettype none

module interlock_controller #(
    parameter [7:0] WARNING_THRESHOLD = 8'd20,
    parameter [7:0] DANGER_THRESHOLD  = 8'd50
) (
    input  logic       clk,
    input  logic       reset,
    input  logic [7:0] vibration_level,
    input  logic       transient_event,
    output logic [1:0] state,
    output logic       warning,
    output logic       interlock,
    output logic       motor_enable,
    output logic       event_latched
);
    localparam logic [1:0] NORMAL = 2'd0;
    localparam logic [1:0] WARN   = 2'd1;
    localparam logic [1:0] TRIP   = 2'd2;

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            state         <= NORMAL;
            event_latched <= 1'b0;
        end else begin
            if (transient_event)
                event_latched <= 1'b1;

            if (state == TRIP || transient_event ||
                vibration_level >= DANGER_THRESHOLD)
                state <= TRIP;
            else if (vibration_level >= WARNING_THRESHOLD)
                state <= WARN;
            else
                state <= NORMAL;
        end
    end

    always_comb begin
        warning      = (state == WARN);
        interlock    = (state == TRIP);
        motor_enable = (state != TRIP);
    end
endmodule

`default_nettype wire

