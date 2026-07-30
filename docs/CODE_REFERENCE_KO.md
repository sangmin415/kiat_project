# 코드 구성 및 기능 설명서

## `rtl/interlock_controller.sv`

진동값을 경고·위험 임계값과 비교해 `NORMAL`, `WARNING`, `INTERLOCK` 상태를 만든다. 위험 진동 또는 ESD_SIM 이벤트가 발생하면 모터 Enable을 즉시 끄고 상태를 래치한다. Reset만 인터록을 해제한다.

## `rtl/seven_segment_status.sv`

상태를 7세그먼트 패턴으로 변환한다.

- `0`: 정상
- `1`: 경고
- `L`: 진동 임계치 인터록
- `E`: ESD_SIM 이벤트 인터록

## `rtl/top_board_demo.sv`

부품 도착 전에 사용하는 최상위 모듈이다. PB1을 경고 진동, PB2를 위험 진동, PB3을 ESD_SIM 이벤트, PB0을 Reset으로 사용한다. RGB LED, 7세그먼트, 좌우 LED에 상태를 연결한다.

## `tb/interlock_controller_tb.sv`

정상, 경고, 고진동 인터록, 인터록 유지, Reset, ESD_SIM 인터록을 순서대로 자동 검증한다. 실패 시 `$fatal`로 종료하며 VCD 파형을 저장한다.

## `constraints/ece270_rev2.pcf`

ECE270 rev.2 보드의 버튼, LED, RGB LED, 7세그먼트, UART와 iCE40 CT256 볼 좌표를 연결한다. 현재 최상위 모듈에서 사용하지 않는 UART 제약은 배치·배선 중 경고로 표시될 수 있으나 오류는 아니다.

## `pc/windows_demo.py`

FPGA 없이 실행하는 Purdue Old Gold 스타일 FDC 화면이다. 가상 진동 그래프, 시스템 상태, motor-enable, 이벤트 래치를 표시하고 CSV로 기록한다.

## `Makefile`

- `make test`: Icarus Verilog 시뮬레이션
- `make lint`: Verilator 정적 검사
- `make synth`: Yosys 합성
- `make bitstream`: nextpnr와 IcePack으로 `.bin` 생성
- `make cram`: 휘발성 CRAM에 업로드
- `make flash`: 비휘발성 SPI Flash에 기록
- `make clean`: 생성 파일 제거

## 현재 구조의 안전 원칙

PC와 CPU는 표시·진단 계층이다. 위험 진동과 ESD_SIM 이벤트에 대한 motor-enable 차단은 FPGA RTL이 독립적으로 수행한다.

## 다음 구현 단계

1. ADXL345 I2C 수신기
2. 외부 ESD_SIM 입력 동기화
3. FPGA UART CSV 송신기
4. Linux 실시간 UART 대시보드
5. RISC-V MMIO와 8-sample 이동평균
