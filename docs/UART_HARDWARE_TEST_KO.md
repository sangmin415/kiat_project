# FPGA UART 실물 통신 시험 가이드

## 시험 목적

센서가 없는 상태에서 PC와 iCE40HX8K FPGA 사이의 UART 양방향 통신을 검증한다.

```text
PC COM 포트 -> FPGA Rx -> UART 수신기
                          |
                          +-> 마지막 바이트 LED/7-segment 표시
                          +-> FPGA Tx -> PC Echo
```

통신 설정은 `115200bps, 8 data bits, no parity, 1 stop bit`이다.

## RTL 시뮬레이션

```bash
make clean
make test_uart
```

성공 결과:

```text
PASS: uart_echo_tb
```

## FPGA 업로드

먼저 보드 연결 상태를 확인하고 CRAM에 업로드한다.

```bash
iceprog -t
make clean
make cram
```

`iceprog -t`는 반드시 업로드 전에 실행한다. 장치 확인 과정에서 기존 CRAM 구성이 초기화될 수 있다.

성공 결과:

```text
programming..
cdone: high
Bye.
```

## Windows 시험

필요 패키지:

```powershell
python -m pip install pyserial
```

장치 관리자에서 FTDI COM 포트를 확인한 후 실행한다.

```powershell
python pc/uart_echo_test.py --port COM12
```

## WSL 시험

FTDI가 WSL에 attach된 상태에서 UART 채널을 확인한다.

```bash
ls -l /dev/ttyUSB*
python3 pc/uart_echo_test.py --port /dev/ttyUSB1
```

권한 오류가 발생하면 사용자를 `dialout` 그룹에 추가하거나 해당 장치 권한을 확인한다.

## 성공 기준

```text
55 -> 55
A3 -> A3
00 -> 00
FF -> FF
UART_HARDWARE_PASS
```

- 7-segment 두 자리는 마지막 수신 바이트를 16진수로 표시한다.
- 왼쪽 LED 8개는 마지막 수신 바이트의 비트 패턴을 표시한다.
- UART Echo는 내부 power-on reset을 사용한다.
- 기존 버튼 기반 인터록은 버튼 0 Reset, 버튼 1 Warning, 버튼 2 진동 Trip, 버튼 3 ESD_SIM을 유지한다.

## 이번 실물 검증 결과

- UART RX/TX 테스트벤치: PASS
- HX8K 합성 및 배치·배선: PASS
- 12MHz 타이밍: PASS
- WSL `iceprog -S` CRAM 업로드: PASS
- WSL `/dev/ttyUSB1` Echo: PASS
- Windows `COM12` Echo: PASS

이 검증은 UART 물리 통신에 대한 결과다. BNO085 센서 패킷, PWM 모터 구동 및 Pygame 실데이터 수신은 이후 단계에서 별도로 검증해야 한다.
