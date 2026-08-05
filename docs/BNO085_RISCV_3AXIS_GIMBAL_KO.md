# BNO085 + RV32I 3축 짐벌 MVP 구현 가이드

## 1. 이 저장소의 현재 목표

BNO085가 내보내는 UART-RVC 자세/가속도 프레임을 iCE40HX8K가 수신한다. FPGA 내부의 직접 구현한 RV32I CPU가 MMIO 레지스터에서 Roll/Pitch/Yaw를 읽고, 정수 기반 제어값을 계산해 서보 PWM 레지스터에 기록한다.

```text
BNO085 → UART-RVC → FPGA RTL parser → MMIO → RV32I C firmware
                                              ↓
                                       3 × 50 Hz PWM
                                              ↓
                                    R0/R1/R2 servo signals
```

PC 대시보드는 FPGA가 그대로 forward한 RVC 프레임을 읽는다. 그래서 PC 화면의 각도는 센서 raw 값이고, **A 영점은 현재 서보 제어 기준에만 적용**된다.

## 2. 정확한 범위

현재 구현은 다음을 포함한다.

- BNO085 UART-RVC 115200 bps 수신
- 19-byte `AA AA ... checksum` 프레임 검증
- RV32I MMIO 레지스터를 통한 Roll/Pitch/Yaw 읽기
- 12 MHz 기준 20 ms frame, 1.1~1.9 ms 범위의 3채널 서보 PWM
- 센서 프레임 timeout 또는 CPU PWM write 전에는 1.5 ms 중립값 강제
- A 키패드로 현재 자세를 R0/R1/R2 공통 영점으로 캡처
- BNO 원시 프레임의 PC UART forward
- Pygame 그래프 및 간단한 3축 stage 시각화

아직 포함하지 않는 것:

- 실제 PID의 I/D 항과 자동 gain tuning
- BNO085 I2C/SHTP 직접 제어
- 3D 프린트 기구 조립 후의 실제 수평 유지 성능
- Isolation Forest/SPC/FDC 최종 분석
- 실제 ESD 방전 생성 또는 검출

따라서 발표에서 “3축 짐벌 **제어 MVP**와 FDC 확장 기반”이라고 설명한다. “이미 고정밀 능동 레벨링을 달성했다”고 단정하면 안 된다.

## 3. 핀맵

| 기능 | 보드 위치/패키지 핀 | 연결 대상 |
|---|---|---|
| 12 MHz clock | J3 | 보드 내장 클록 |
| BNO RVC RX | J6 I0 / C3 | BNO085 SDA (UART-RVC TX), 표준 UART 정상 극성 |
| A 영점 버튼 | keypad A / C6 | 보드 내장 버튼 |
| PC UART TX | B12 | FTDI/PC |
| R0 PWM | B2 | Roll servo signal (yellow/orange) |
| R1 PWM | D1 | Pitch servo signal |
| R2 PWM | H1 | Yaw servo signal |
| Green status | T9 | 보드 RGB green |
| Red status | P8 | 센서 프레임 timeout |

실제 배선 전원은 모두 끈 상태에서 한다. `constraints/bno085_3axis_cpu.pcf`가 이 표의 단일 기준이다.

## 4. BNO085 UART-RVC 배선

Adafruit BNO085 breakout 기준:

| BNO085 | 연결 |
|---|---|
| VIN | 검증된 3.3 V |
| GND | FPGA GND |
| P0 | 3.3 V (UART-RVC mode 선택) |
| P1 | GND 또는 breakout 기본 low 상태 |
| SDA | J6 I0 / C3 |
| SCL, INT | 이 MVP에서는 연결하지 않음 |
| RST | 일반적으로 연결하지 않음 |

P0/P1 설정은 **전원을 넣기 전**에 고정한다. 이 구현은 I2C 모드가 아니며, BNO085의 UART-RVC 출력이 SDA 핀에 나온다는 전제를 사용한다.

C3 수신은 표준 UART처럼 Idle High, Start Low이며 RTL에서 `.Rx(bno_rxc)`로 직접 받는다. 다른 GPIO로 옮기면 PCF와 실제 핀의 Idle/Start 극성을 오실로스코프로 검증한다.

## 5. 서보와 외부 전원

SG90/MS18급 3선 서보:

| 서보 선 | 연결 |
|---|---|
| red | 외부 안정화된 5 V |
| black/brown | 외부 5 V GND |
| yellow/orange/white | FPGA PWM R0, R1, R2 |

**필수:** 외부 5 V GND와 FPGA GND를 공통으로 연결한다.

- FPGA USB/3.3 V에서 서보 전원을 공급하지 않는다.
- 3개 서보는 5 V 3 A 이상 권장 전원을 사용한다.
- 470~1000 uF 전해 커패시터를 서보 전원 가까이에 둔다.
- 전원 인가 전 red-GND가 5 V인지 멀티미터로 확인한다.
- 회전 부품을 손으로 잡고 처음에는 1개 축만 저속으로 확인한다.

## 6. CPU / MMIO

| 주소 | 방향 | 의미 |
|---:|---|---|
| `0x80000060` | R | Roll, centidegree |
| `0x80000064` | R | timeout/sample/checksum 상태 |
| `0x80000068` | R/W | R0 PWM tick |
| `0x8000006C` | R | A button |
| `0x80000070` | R | Pitch, centidegree |
| `0x80000074` | R | Yaw, centidegree |
| `0x80000078` | R/W | R1 PWM tick |
| `0x8000007C` | R/W | R2 PWM tick |

펌웨어 제어식:

```text
servo_ticks = clamp(18000 - ((angle_cd - zero_cd) * 17 / 32), 13200, 22800)
```

12 MHz에서 `18000 tick = 1.50 ms`이다. 기본 P 스케일은 1 centidegree당 `17/32 tick`(1도당 약 53.125 tick)이며, 펌웨어의 `KP_NUMERATOR`와 `KP_DENOMINATOR`로 튜닝한다. 기구 조립 뒤 한 축이 반대로 움직이면 해당 축의 부호만 바꾼다.

## 7. 빌드와 업로드

WSL에서 다음을 실행한다.

```bash
cd /mnt/c/kiat_project
make -f Makefile.gimbal gimbal-firmware
make -f Makefile.gimbal gimbal-lint
make -f Makefile.gimbal gimbal-bitstream
make -f Makefile.gimbal gimbal-cram
```

`gimbal-cram`은 `iceprog -S`를 사용한다. 즉 전원 제거 후에는 사라진다. `gimbal-flash`은 보드 점퍼가 Flash configuration에 맞을 때만 사용하고, 먼저 CRAM에서 동작을 확인한다.

## 8. Pygame 대시보드

```bash
sudo apt install python3-pygame python3-serial
python3 pc/bno085_rvc_dashboard.py --simulate
python3 pc/bno085_rvc_dashboard.py --port /dev/ttyUSB1 --baud 115200
```

화면 해석:

- Roll/Pitch/Yaw: 센서의 raw 각도
- ACC: raw acceleration, mg
- vibration: `sqrt(ax² + ay² + (az-1000)²)`, 현재는 시각화 지표
- `RVC VALID`: 최근 0.5초 안에 checksum이 맞는 RVC 프레임을 수신
- `WAITING`: 배선, RVC mode, UART port, FPGA CRAM bitstream을 차례로 점검

## 9. 하드웨어 검증 순서

1. **센서 전원만:** VIN=3.3 V, GND continuity, P0/P1 mode 확인.
2. **BNO + FPGA:** 대시보드가 `RVC VALID`가 되는지 확인한다.
3. **서보 1개:** R0 signal + 5 V external + common GND로 중립 PWM을 확인한다.
4. **A button:** 현재 자세에서 A를 눌러 그 자세가 서보 중심이 되는지 본다.
5. **R1/R2 추가:** 기구를 결합하기 전 세 채널을 각각 검증한다.
6. **3D gimbal:** 기계적 간섭 없이 작은 ±5°부터 시험한다.
7. **PID/FDC 확장:** 충분한 로그 후에만 gain, SPC, AI를 추가한다.

## 10. 다음 단계

- 서보 혼을 SG90 spline에 정확히 결합하고 3D 프린트 gimbal을 조립한다.
- 축별 부호/gain을 보정한다.
- P 제어가 안정된 뒤 D 항과 deadband를 추가한다.
- BNO 가속도 데이터를 CSV로 저장하고, 정상 상태를 기준으로 SPC와 Isolation Forest를 학습한다.
- AI는 경고만 출력하고, timeout/angle safety는 FPGA/RV32I 경로에 남긴다.
