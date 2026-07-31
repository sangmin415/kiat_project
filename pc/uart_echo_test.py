import argparse
import serial
import time


parser = argparse.ArgumentParser(description="Test the FPGA UART echo design.")
parser.add_argument("--port", default="COM12", help="Serial port, e.g. COM12 or /dev/ttyUSB1")
parser.add_argument("--baud", type=int, default=115200)
args = parser.parse_args()

values = [0x55, 0xA3, 0x00, 0xFF]
with serial.Serial(args.port, args.baud, timeout=1) as uart:
    uart.reset_input_buffer()
    results = []
    for value in values:
        uart.write(bytes([value]))
        uart.flush()
        echo = uart.read(1)
        results.append((value, echo))
        time.sleep(0.05)

for value, echo in results:
    received = echo.hex().upper() if echo else "TIMEOUT"
    print(f"{value:02X} -> {received}")

if not all(echo == bytes([value]) for value, echo in results):
    raise SystemExit("UART_HARDWARE_FAIL")

print("UART_HARDWARE_PASS")
