# 부품 없이 진행하는 FPGA 인터록 데모

## 목적

ADXL345, 진동 모터, MOSFET 드라이버가 도착하기 전에 내장 버튼을 가상 센서로 사용해 테스트벤치와 실제 FPGA 인터록 동작을 검증한다.

현재 `top_board_demo.sv`가 이 용도로 작성돼 있으므로 외부 부품 없이 실행할 수 있다.

## 1. 최신 코드 받기

```bash
cd ~/kiat_project
git pull origin main
```

처음 받는 경우:

```bash
git clone https://github.com/sangmin415/kiat_project.git
cd kiat_project
```

## 2. 테스트벤치 실행

Purdue 수업 템플릿 방식:

```bash
make clean
make sim_interlock_controller_src
```

짧은 별칭:

```bash
make test
```

파형 확인:

```bash
gtkwave build/interlock_controller.vcd
```

## 3. RTL lint

```bash
make vlint_interlock_controller
```

또는 전체 보드 최상위 모듈까지 검사:

```bash
make lint
```

## 4. FPGA 비트스트림 생성

```bash
make bitstream
```

성공하면 다음 파일이 생성된다.

```text
build/interlock_demo.bin
```

## 5. 보드 연결 확인

```bash
lsusb
iceprog -t
```

`iceprog`가 없으면:

```bash
sudo apt update
sudo apt install -y fpga-icestorm
```

## 6. 휘발성 CRAM 업로드

```bash
make cram
```

전원을 끄면 설계가 사라지므로 초기 시험에 적합하다. 현재 단계에서는 `make flash`를 사용하지 않는다.

## 7. 버튼 시험

| 보드 입력 | 가상 의미 | 기대 출력 |
|---|---|---|
| 아무 입력 없음 | 정상 진동값 5 | 녹색 RGB, 7세그먼트 `0`, motor-enable LED ON |
| 숫자 1 버튼 | 경고 진동값 30 | 파란색 RGB, `1`, motor-enable 유지 |
| 숫자 2 버튼 | 위험 진동값 70 | 빨간색 RGB, `L`, motor-enable OFF |
| 숫자 0 버튼 | Reset | NORMAL 복귀 |
| 숫자 3 버튼 | ESD_SIM 이벤트 | 빨간색 RGB, `E`, 이벤트 래치, motor-enable OFF |

숫자 2 또는 3 버튼을 놓아도 INTERLOCK은 유지돼야 한다. 숫자 0 Reset 버튼으로만 정상 복귀한다.

## 8. 현재 코드 수정 필요 여부

부품 없는 시험에는 수정할 필요가 없다.

- `top_board_demo.sv`: 버튼을 가상 센서로 변환
- `interlock_controller.sv`: 경고·인터록 판단 및 래치
- `seven_segment_status.sv`: `0`, `1`, `L`, `E` 표시
- `ece270_rev2.pcf`: 내장 버튼·LED·7세그먼트 핀 연결

부품 도착 후에는 다음 모듈을 추가한다.

1. ADXL345 I2C 수신기
2. 실제 진동값 계산기
3. ESD_SIM 외부 입력 동기화
4. MOSFET motor-enable 외부 GPIO
5. UART 상태 패킷 송신기

## 9. 안전 주의

- 모터를 FPGA GPIO에 직접 연결하지 않는다.
- 외부 부품 연결 전 GPIO 핀과 3.3V 호환성을 확인한다.
- 실제 스파크나 고전압 ESD를 만들지 않는다.
- Flash 기록 전에는 반드시 CRAM으로 동작을 검증한다.
