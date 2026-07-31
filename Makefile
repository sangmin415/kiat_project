###########################################################################################
# Purdue KIAT/STARS - Makefile for the photo-process interlock demo
# Simulation target naming and lab tool paths follow the ECE270 course template.
###########################################################################################

export PATH := /home/shay/a/ece270/bin:$(PATH)
export LD_LIBRARY_PATH := /home/shay/a/ece270/lib:$(LD_LIBRARY_PATH)

SHELL := bash
BUILD := build
RTL := rtl/interlock_controller.sv rtl/seven_segment_status.sv rtl/seven_segment_hex.sv rtl/uart_echo.sv rtl/top_board_demo.sv
PCF := constraints/ece270_rev2.pcf
TOP := top_board_demo
JSON := $(BUILD)/interlock_demo.json
ASC := $(BUILD)/interlock_demo.asc
BIN := $(BUILD)/interlock_demo.bin

.PHONY: test test_uart test_command sim lint check_env synth bitstream cram flash clean

test:
	mkdir -p $(BUILD)
	iverilog -g2012 -o $(BUILD)/interlock_tb rtl/interlock_controller.sv tb/interlock_controller_tb.sv
	vvp $(BUILD)/interlock_tb
	iverilog -g2012 -o $(BUILD)/uart_echo_tb rtl/uart_echo.sv tb/uart_echo_tb.sv
	vvp $(BUILD)/uart_echo_tb
	iverilog -g2012 -s top_board_uart_demo_tb_v2 -o $(BUILD)/uart_command_tb $(RTL) tb/top_board_uart_command_tb.sv
	vvp $(BUILD)/uart_command_tb

test_uart:
	mkdir -p $(BUILD)
	iverilog -g2012 -o $(BUILD)/uart_echo_tb rtl/uart_echo.sv tb/uart_echo_tb.sv
	vvp $(BUILD)/uart_echo_tb

test_command:
	mkdir -p $(BUILD)
	iverilog -g2012 -s top_board_uart_demo_tb_v2 -o $(BUILD)/uart_command_tb $(RTL) tb/top_board_uart_command_tb.sv
	vvp $(BUILD)/uart_command_tb

# Convenient short alias. It executes the course-template target below.
sim: sim_interlock_controller_src

lint:
	verilator --lint-only -Wall --top-module $(TOP) $(RTL)

check_env:
	@echo "Purdue FPGA toolchain paths:"
	@for tool in iverilog vvp gtkwave verilator yosys nextpnr-ice40 icepack iceprog; do \
		printf "%-16s" "$$tool"; \
		command -v "$$tool" || { echo "NOT FOUND"; exit 1; }; \
	done

# *******************************************************************************
# COMPILATION & SIMULATION TARGETS - Purdue course-template naming
# *******************************************************************************

.PHONY: sim_%_src vlint_%
sim_%_src:
	@echo -e "Creating executable for source simulation...\n"
	@mkdir -p $(BUILD) && rm -rf $(BUILD)/*
	@iverilog -g2012 -o $(BUILD)/$*_tb rtl/$*.sv tb/$*_tb.sv
	@echo -e "\nSource compilation complete!\n"
	@echo -e "Simulating source...\n"
	@vvp -l vvp_sim.log $(BUILD)/$*_tb
	@echo -e "\nSimulation complete!\n"
	@echo -e "Opening waveforms...\n"
	@if [ -f waves/$*.gtkw ]; then \
		gtkwave waves/$*.gtkw; \
	else \
		gtkwave $(BUILD)/$*.vcd; \
	fi

vlint_%:
	@verilator --lint-only -Wall --top-module $* rtl/$*.sv
	@echo -e "\nNo linting errors found for $*.\n"

# *******************************************************************************
# FPGA TARGETS
# *******************************************************************************

$(JSON): $(RTL)
	mkdir -p $(BUILD)
	# Remove debug-only scope metadata for compatibility with older nextpnr.
	# This command works with both the older WSL Yosys and newer Purdue Yosys.
	yosys -q -p 'read_verilog -sv $(RTL); synth_ice40 -top $(TOP); delete t:$$scopeinfo; write_json $(JSON)'

$(ASC): $(JSON) $(PCF)
	nextpnr-ice40 --hx8k --package ct256 --pcf $(PCF) --json $(JSON) --asc $(ASC)

$(BIN): $(ASC)
	icepack $(ASC) $(BIN)

synth: $(JSON)

bitstream: $(BIN)

cram: $(BIN)
	iceprog -S $(BIN)

flash: $(BIN)
	iceprog $(BIN)

clean:
	rm -rf $(BUILD) vvp_sim.log
