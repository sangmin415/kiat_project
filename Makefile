BUILD := build
RTL := rtl/interlock_controller.sv rtl/seven_segment_status.sv rtl/top_board_demo.sv
PCF := constraints/ece270_rev2.pcf
TOP := top_board_demo
JSON := $(BUILD)/interlock_demo.json
ASC := $(BUILD)/interlock_demo.asc
BIN := $(BUILD)/interlock_demo.bin

.PHONY: test lint synth bitstream cram flash clean

test:
	mkdir -p $(BUILD)
	iverilog -g2012 -o $(BUILD)/interlock_tb rtl/interlock_controller.sv tb/interlock_controller_tb.sv
	vvp $(BUILD)/interlock_tb

lint:
	verilator --lint-only -Wall -Wno-UNUSEDSIGNAL --top-module $(TOP) $(RTL)

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

vlint_%:
	@verilator --lint-only -Wall --top-module $* rtl/$*.sv
	@echo "No linting errors found for $*."

clean:
	rm -rf $(BUILD)
