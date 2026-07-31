"""Hardware smoke test for the single-byte FPGA interlock protocol."""
import argparse
import time
import serial

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="COM12")
parser.add_argument("--baud", type=int, default=115200)
args = parser.parse_args()

def transact(uart, command, expected=None):
    uart.write(bytes([command]))
    uart.flush()
    value = uart.read(1)
    if not value:
        raise SystemExit(f"TIMEOUT after 0x{command:02X}")
    actual = value[0]
    if expected is not None and actual != expected:
        raise SystemExit(f"FAIL 0x{command:02X}: expected 0x{expected:02X}, got 0x{actual:02X}")
    return actual

with serial.Serial(args.port, args.baud, timeout=1) as uart:
    uart.reset_input_buffer()
    for command, status, label in [
        (0x14, 0x81, "RESET/STOPPED"),
        (0x10, 0xA0, "NORMAL/RUNNING"),
        (0x11, 0xA4, "WARNING/RUNNING"),
        (0x12, 0x88, "VIBRATION/INTERLOCK"),
        (0x14, 0x81, "RESET/STOPPED"),
        (0x13, 0xC8, "ESD/INTERLOCK"),
        (0x14, 0x81, "FINAL RESET/STOPPED"),
    ]:
        transact(uart, command, command)
        time.sleep(0.03)
        actual_status = transact(uart, 0xF0, status)
        print(f"{label:<22} status=0x{actual_status:02X}")

print("UART_COMMAND_HARDWARE_PASS")

