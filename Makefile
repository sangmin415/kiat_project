BUILD := build
RTL := rtl/interlock_controller.sv rtl/seven_segment_status.sv rtl/top_board_demo.sv

.PHONY: test lint clean

test:
	mkdir -p $(BUILD)
	iverilog -g2012 -o $(BUILD)/interlock_tb rtl/interlock_controller.sv tb/interlock_controller_tb.sv
	vvp $(BUILD)/interlock_tb

lint:
	verilator --lint-only -Wall --top-module top_board_demo $(RTL)

clean:
	rm -rf $(BUILD)

