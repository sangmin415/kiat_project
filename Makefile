# Purdue ECE270/STARS lab toolchain.
export PATH := /home/shay/a/ece270/bin:$(PATH)
export LD_LIBRARY_PATH := /home/shay/a/ece270/lib:$(LD_LIBRARY_PATH)

SHELL := bash
BUILD := build
RTL := rtl/interlock_controller.sv rtl/seven_segment_status.sv rtl/top_board_demo.sv
PCF := constraints/ece270_rev2.pcf
TOP := top_board_demo
JSON := $(BUILD)/interlock_demo.json
ASC := $(BUILD)/interlock_demo.asc
BIN := $(BUILD)/interlock_demo.bin

.PHONY: test sim lint check_env synth bitstream cram flash clean

test:
	mkdir -p $(BUILD)
	iverilog -g2012 -o $(BUILD)/interlock_tb rtl/interlock_controller.sv tb/interlock_controller_tb.sv
	vvp $(BUILD)/interlock_tb

# Short course-style GUI alias: run the testbench and open its VCD in GTKWave.
sim: sim_interlock_controller_src

lint:
	verilator --lint-only -Wall --top-module $(TOP) $(RTL)

check_env:
	@echo "Purdue FPGA toolchain paths:"
	@for tool in iverilog vvp gtkwave verilator yosys nextpnr-ice40 icepack iceprog; do \
		printf "%-16s" "$$tool"; \
		command -v "$$tool" || { echo "NOT FOUND"; exit 1; }; \
	done

$(JSON): $(RTL)
	mkdir -p $(BUILD)
	yosys -q -p "read_verilog -sv $(RTL); synth_ice40 -top $(TOP); write_json $(JSON)"

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

# Purdue ECE270 template-compatible commands.
.PHONY: sim_%_src vlint_%
sim_%_src:
	@echo "Compiling $* source simulation..."
	@mkdir -p $(BUILD)
	@iverilog -g2012 -o $(BUILD)/$*_tb rtl/$*.sv tb/$*_tb.sv
	@echo "Running $* testbench..."
	@vvp $(BUILD)/$*_tb
	@echo "Simulation complete. VCD: $(BUILD)/$*.vcd"
	@echo "Opening waveform viewer..."
	@if command -v gtkwave >/dev/null 2>&1; then \
		gtkwave $(BUILD)/$*.vcd >/dev/null 2>&1 & \
	else \
		echo "GTKWave not found. Open $(BUILD)/$*.vcd after installing it."; \
	fi

vlint_%:
	@verilator --lint-only -Wall --top-module $* rtl/$*.sv
	@echo "No linting errors found for $*."

clean:
	rm -rf $(BUILD)
