# Linux PC 기반 FPGA 빌드·업로드·시험 가이드

## 1. 적용 범위

현재 단계는 ADXL345가 도착하기 전에 내장 버튼을 가상 센서로 사용하는 `top_board_demo`를 iCE40HX8K에 올리는 절차다. 외부 센서 핀은 물리 헤더를 확정한 뒤 추가한다.

## 2. Ubuntu 도구 설치

```bash
sudo apt update
sudo apt install -y git make iverilog verilator yosys nextpnr-ice40 fpga-icestorm
```

설치 확인:

```bash
iverilog -V
verilator --version
yosys -V
nextpnr-ice40 --version
iceprog --version
```

## 3. 리포 준비

```bash
git clone https://github.com/sangmin415/kiat_project.git
cd kiat_project
```

## 4. 시뮬레이션과 lint

```bash
make clean
make test
make lint
```

`make test`는 정상·경고·고진동 인터록·Reset·ESD_SIM 이벤트를 자동 검증하고 `build/interlock_controller.vcd`를 생성한다.

## 5. 비트스트림 생성

```bash
make bitstream
```

Yosys 합성, nextpnr-ice40 배치·배선, IcePack 변환을 거쳐 `build/interlock_demo.bin`이 생성된다. 대상은 `iCE40HX8K`, 패키지는 `CT256`, 입력 클록은 12 MHz다.

## 6. FPGA 업로드

USB 케이블을 연결하고 장치를 확인한다.

```bash
lsusb
iceprog -t
```

먼저 전원을 끄면 사라지는 CRAM으로 시험한다.

```bash
make cram
```

동작 확인 후에만 SPI Flash에 기록한다.

```bash
make flash
```

`flash`는 전원을 다시 켜도 설계가 유지된다. 초기 시험은 반드시 `cram`을 사용한다.

## 7. 보드 시험 순서

| 조작 | 기대 결과 |
|---|---|
| 전원/Reset | RGB 녹색, 7세그먼트 `0`, motor-enable LED ON |
| PB1 | RGB 파란색, 7세그먼트 `1`, WARNING |
| PB2 | RGB 빨간색, 7세그먼트 `L`, motor-enable OFF |
| PB2 해제 | INTERLOCK 유지 |
| PB0 | NORMAL 복귀 |
| PB3 | 7세그먼트 `E`, ESD_SIM 래치, motor-enable OFF |

현재 `left[0]` LED가 향후 MOSFET 드라이버의 motor-enable 신호를 대신한다.

## 8. Windows 가상 시각화

```powershell
py -3 pc\windows_demo.py
```

NORMAL, WARNING, VIBRATION TRIP, ESD_SIM, RESET을 화면에서 재현하며 `logs/windows_demo.csv`에 저장한다.

## 9. 문제 해결

- `no iCE40 device found`: USB 케이블, 보드 점퍼, Linux USB 권한 확인
- PCF 오류: `--hx8k --package ct256` 확인
- Flash 기록 전 오류: `make cram`으로 먼저 검증
- 외부 센서: 확인되지 않은 확장 헤더 핀을 임의로 연결하지 말 것
- 실제 스파크·고전압 ESD는 사용하지 말 것
