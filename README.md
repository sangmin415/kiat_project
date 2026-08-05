# BNO085 + PC 제어 3축 짐벌 MVP

BNO085 UART-RVC 자세 데이터를 iCE40HX8K FPGA가 PC로 전달하고, **PC Pygame 대시보드가 영점과 각도→PWM 계산**을 수행하는 3축 서보 짐벌 프로젝트입니다.

이 버전은 RV32I CPU를 사용하지 않습니다. FPGA는 UART 수신, packet checksum, 50Hz PWM, timeout fail-safe를 담당합니다.

```text
BNO085 → FPGA UART/RVC parser → PC dashboard
                                   │
                         PC calculates R0/R1/R2 PWM
                                   │
                                UART B10
                                   ▼
                           FPGA PWM generator
                                   ▼
                           SG90/MS18 x 3
```

## 현재 구현

- BNO085 UART-RVC 115200bps 수신, checksum, 50ms sensor timeout
- 원시 RVC 프레임을 PC로 forward
- PC가 Roll/Pitch/Yaw와 영점으로 3채널 PWM tick 계산
- PC 키보드 Z 또는 FPGA 키패드 B로 영점 캡처
- PC→FPGA PWM command checksum 검증
- PC command timeout 또는 sensor timeout 시 세 서보 1.5ms 중립 복귀
- 12MHz FPGA에서 20ms/50Hz PWM 생성
- Pygame 대시보드와 각도/진동 시각화

7-segment와 부저는 현재 top에 연결하지 않았습니다. 세그먼트에 문자가 보이면 이전 비트스트림이 보드에 남아 있는 상태입니다.

## 핀맵

| 기능 | FPGA 핀 |
|---|---|
| BNO085 UART-RVC | C3 / J6 I0 |
| PC UART RX | B10 |
| PC UART TX | B12 |
| 키패드 B 영점 | A6 |
| R0 PWM | B2 |
| R1 PWM | D1 |
| R2 PWM | H1 |
| Green status LED | T9 |

서보 red는 외부 5V, black/brown은 외부 GND, signal은 R0/R1/R2에 연결합니다. 외부 GND와 FPGA GND는 공통이어야 합니다.

## 실행

```bash
cd /mnt/c/kiat_project
make -f Makefile.pcservo pcservo-test
make -f Makefile.pcservo pcservo-bitstream
make -f Makefile.pcservo pcservo-cram
python3 pc/bno085_rvc_dashboard.py --port /dev/ttyUSB1 --baud 115200
```

대시보드를 연 뒤 보드의 B 키를 누르면 현재 자세를 영점으로 잡습니다. PC 키보드 Z도 같은 기능입니다.

자세한 내용: [PC 제어 짐벌 가이드](docs/BNO085_PC_SERVO_GIMBAL_KO.md)
