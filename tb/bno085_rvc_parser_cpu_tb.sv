module bno085_rvc_parser_cpu_tb;
    logic clk=0, reset=1, byte_valid=0;
    logic [7:0] byte_data=0;
    logic signed [15:0] yaw_cd,pitch_cd,roll_cd,ax,ay,az;
    logic [7:0] seq;
    logic valid, checksum_error, sensor_timeout;
    bno085_rvc_parser_cpu #(.CLK_HZ(1000), .TIMEOUT_MS(100)) dut (
        .clk, .reset, .byte_data, .byte_valid, .yaw_cd, .pitch_cd, .roll_cd,
        .accel_x_mg(ax), .accel_y_mg(ay), .accel_z_mg(az), .sample_seq(seq),
        .sample_valid(valid), .checksum_error, .sensor_timeout
    );
    always #5 clk=~clk;
    task send(input [7:0] value);
        begin @(negedge clk); byte_data=value; byte_valid=1; @(negedge clk); byte_valid=0; end
    endtask
    initial begin
        #25; reset=0;
        send(8'haa); send(8'haa);
        // sequence, yaw, pitch, roll, ax, ay, az, and 3 reserved bytes
        send(8'h07); send(8'h34); send(8'h12); send(8'hfe); send(8'hff);
        send(8'h9c); send(8'hff); send(8'h0a); send(8'h00); send(8'hf6);
        send(8'hff); send(8'he8); send(8'h03); send(8'h00); send(8'h00); send(8'h00);
        send(8'hcf); // sum of bytes index 2 through 17
        @(posedge clk); #1;
        $display("valid=%0d seq=%h yaw=%0d pitch=%0d roll=%0d ax=%0d ay=%0d az=%0d timeout=%0d", valid, seq, yaw_cd, pitch_cd, roll_cd, ax, ay, az, sensor_timeout);
        if (!valid || seq!=8'h07 || yaw_cd!=16'sh1234 || pitch_cd!=-2 || roll_cd!=-100 ||
            ax!=10 || ay!=-10 || az!=1000 || sensor_timeout)
            $fatal(1, "RVC parser did not decode expected values");
        $display("PASS: bno085_rvc_parser_cpu_tb");
        $finish;
    end
endmodule
