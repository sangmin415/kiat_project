# FPGA pre-hardware test guide

This guide verifies the interlock before the ADXL345, motor driver, and
ESD_SIM circuit arrive.

## 1. Simulation

Required tools: Icarus Verilog and Verilator.

```bash
make test
make lint
```

Expected simulation result:

```text
PASS: interlock_controller_tb
```

The test covers:

1. low vibration -> `NORMAL`, motor enabled;
2. medium vibration -> `WARNING`, motor still enabled;
3. high vibration -> latched `INTERLOCK`, motor disabled;
4. reset -> `NORMAL`;
5. transient event -> latched `ESD_SIM INTERLOCK`.

## 2. Board control mapping

The temporary board demo uses the ECE270 pushbuttons as sensor substitutes.

| Input | Function |
|---|---|
| `PB0` | reset |
| `PB1` | warning vibration value (`30`) |
| `PB2` | dangerous vibration value (`70`) |
| `PB3` | ESD_SIM transient event |

Outputs:

| Output | Meaning |
|---|---|
| seven-segment `0` | normal |
| seven-segment `1` | warning |
| seven-segment `L` | vibration-limit interlock |
| seven-segment `E` | ESD_SIM interlock |
| green RGB | normal |
| blue RGB | warning |
| red RGB | interlock |
| left LED 0 | future motor-enable signal |

## 3. Manual board test

1. Program the board with `top_board_demo`.
2. After reset, confirm green RGB, digit `0`, and left LED 0 are on.
3. Hold PB1: blue RGB and digit `1` must appear.
4. Release PB1: the system returns to normal.
5. Press PB2: red RGB appears, digit `L` appears, and left LED 0 turns off.
6. Release PB2: the interlock must remain latched.
7. Press PB0: the system returns to normal.
8. Press PB3: digit `E` appears and the motor-enable LED turns off.
9. Press PB0 again to clear the event latch.

## 4. Oscilloscope checks

Before parts arrive, probe only existing low-voltage board signals:

- 12 MHz `hwclk`;
- the future motor-enable test output;
- UART Tx after UART is added.

After parts arrive, use the MSO-X 3014A to verify:

- ADXL345 SDA/SCL stay in the 0-3.3 V range;
- the RC node is never connected directly to the FPGA;
- the 74HC14 output is a clean 0/3.3 V pulse;
- no overshoot exceeds the FPGA input rating.

Do not create a real spark or apply high voltage near the FPGA or USB cable.

## 5. Current limitation

The external GPIO header pin assignment is intentionally not included yet.
Add it only after the exact ECE270 header schematic or verified header pin map
is available. The current demo uses only known onboard I/O.

