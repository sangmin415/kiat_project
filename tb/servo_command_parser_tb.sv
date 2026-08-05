module servo_command_parser_tb;
 logic clk=0,reset=1,valid=0; logic [7:0] data=0;
 logic [15:0] r0,r1,r2; logic cmd,err,timeout,saw=0;
 servo_command_parser #(.CLK_HZ(1000),.TIMEOUT_MS(100)) dut(
  .clk,.reset,.byte_data(data),.byte_valid(valid),.r0_ticks(r0),.r1_ticks(r1),.r2_ticks(r2),
  .command_valid(cmd),.checksum_error(err),.command_timeout(timeout));
 always #5 clk=~clk;
 always @(posedge clk) if(cmd) saw<=1;
 task send(input [7:0] b); begin @(negedge clk);data=b;valid=1;@(negedge clk);valid=0;end endtask
 initial begin
  #25;reset=0;
  send(8'h55);send(8'ha5);send(8'h46);send(8'h50);send(8'h4b);send(8'h00);send(8'h57);send(8'h30);send(8'h6f);
  @(posedge clk);#1;
  if(!saw||r0!=16'd18000||r1!=16'd19200||r2!=16'd22320||timeout) $fatal(1,"PC servo packet parser failed");
  $display("PASS: servo_command_parser_tb");$finish;
 end
endmodule
