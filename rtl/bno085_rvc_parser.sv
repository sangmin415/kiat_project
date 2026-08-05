module bno085_rvc_parser #(
    parameter integer CLK_HZ = 12_000_000,
    parameter integer TIMEOUT_MS = 50
) (
    input logic clk, input logic reset,
    input logic [7:0] byte_data, input logic byte_valid,
    output logic signed [15:0] yaw_cd, pitch_cd, roll_cd,
    output logic signed [15:0] accel_x_mg, accel_y_mg, accel_z_mg,
    output logic [7:0] sample_seq, output logic sample_valid,
    output logic checksum_error, output logic sensor_timeout
);
    localparam integer TIMEOUT_CLKS = (CLK_HZ / 1000) * TIMEOUT_MS;
    localparam integer TIMEOUT_W = $clog2(TIMEOUT_CLKS + 1);
    localparam [1:0] WAIT_AA0 = 0, WAIT_AA1 = 1, PAYLOAD = 2, CHECKSUM = 3;
    logic [1:0] state;
    logic [4:0] byte_index;
    logic [7:0] checksum_sum, rx_seq;
    logic [7:0] yaw_l, pitch_l, roll_l, ax_l, ay_l, az_l;
    logic signed [15:0] rx_yaw, rx_pitch, rx_roll, rx_ax, rx_ay, rx_az;
    logic [TIMEOUT_W-1:0] timeout_count;

    always_ff @(posedge clk) begin
        sample_valid <= 1'b0;
        if (reset) begin
            state <= WAIT_AA0; byte_index <= 0; checksum_sum <= 0; checksum_error <= 0;
            sensor_timeout <= 1; timeout_count <= 0; yaw_cd <= 0; pitch_cd <= 0;
            roll_cd <= 0; accel_x_mg <= 0; accel_y_mg <= 0; accel_z_mg <= 0; sample_seq <= 0;
        end else begin
            if (timeout_count < TIMEOUT_CLKS) timeout_count <= timeout_count + 1'b1;
            if (timeout_count >= TIMEOUT_CLKS - 1) sensor_timeout <= 1'b1;
            if (byte_valid) case (state)
                WAIT_AA0: if (byte_data == 8'haa) state <= WAIT_AA1;
                WAIT_AA1: if (byte_data == 8'haa) begin
                    state <= PAYLOAD; byte_index <= 5'd2; checksum_sum <= 0;
                end else state <= WAIT_AA0;
                PAYLOAD: begin
                    checksum_sum <= checksum_sum + byte_data;
                    case (byte_index)
                        5'd2: rx_seq <= byte_data;
                        5'd3: yaw_l <= byte_data;    5'd4: rx_yaw[15:8] <= byte_data;
                        5'd5: pitch_l <= byte_data;  5'd6: rx_pitch[15:8] <= byte_data;
                        5'd7: roll_l <= byte_data;   5'd8: rx_roll[15:8] <= byte_data;
                        5'd9: ax_l <= byte_data;     5'd10: rx_ax[15:8] <= byte_data;
                        5'd11: ay_l <= byte_data;    5'd12: rx_ay[15:8] <= byte_data;
                        5'd13: az_l <= byte_data;    5'd14: rx_az[15:8] <= byte_data;
                        default: ;
                    endcase
                    if (byte_index == 5'd17) state <= CHECKSUM;
                    else byte_index <= byte_index + 1'b1;
                end
                CHECKSUM: begin
                    state <= WAIT_AA0;
                    if (byte_data == checksum_sum) begin
                        yaw_cd <= {rx_yaw[15:8], yaw_l};
                        pitch_cd <= {rx_pitch[15:8], pitch_l};
                        roll_cd <= {rx_roll[15:8], roll_l};
                        accel_x_mg <= {rx_ax[15:8], ax_l};
                        accel_y_mg <= {rx_ay[15:8], ay_l};
                        accel_z_mg <= {rx_az[15:8], az_l};
                        sample_seq <= rx_seq; sample_valid <= 1; checksum_error <= 0;
                        sensor_timeout <= 0; timeout_count <= 0;
                    end else checksum_error <= 1;
                end
                default: state <= WAIT_AA0;
            endcase
        end
    end
endmodule
