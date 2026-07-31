# FPGA-RISC-V Photo Process Interlock

> **최신 구현 기준:** 센서는 BNO085, 구동부는 편심 모터 1개와 DRV8833을 사용하며 Python 랜덤 PWM Fault Injection으로 시험합니다. 상세 내용은 [BNO085 단일 모터 인터록 계획](docs/BNO085_MOTOR_INTERLOCK_PLAN_KO.md)을 기준으로 합니다.

ADXL345로 실제 진동을 측정하고, RC 미분기 기반의 저전압 과도 이벤트를 모사해 FPGA-RISC-V 시스템의 인터록 동작을 검증하는 프로젝트입니다.

> 실제 ESD 방전이나 마스크 결함을 검출하는 장비가 아닙니다. 실제 진동 데이터와 ESD 유사 과도 이벤트의 **안전한 저전압 모사**를 이용해 포토 공정 정밀 장비의 상태 감시·인터록 개념을 구현합니다.

## 목표

- 진동 모터가 발생시키는 실제 진동을 ADXL345 3축 가속도 센서로 수집
- FPGA에서 진동 임계치와 과도 이벤트를 감시하고 즉시 인터록 수행
- RISC-V CPU가 MMIO로 상태를 읽고 8개 이동 평균 전처리 후 UART 전송
- PC가 FDC 형태의 실시간 그래프, CSV 로그, SPC 관리도와 AI 조기 경고를 제공
- FPGA가 CPU·PC와 독립적으로 모터 드라이버 Enable을 차단

## 시스템 구조

```text
진동 모터 ── 실제 진동 ──> ADXL345
                              │ I2C
                              v
                        FPGA RTL
                  ┌─────┼───────────────┐
                  │     │               │
              즉시 인터록  MMIO       LED / 7-segment
                  │     │
                  │     v
                  │  RISC-V CPU
                  │  8-sample moving average
                  │     │ UART
                  │     v
                  └──> PC FDC / SPC / AI dashboard

외부 ESD_SIM 버튼 → RC 미분기 → 슈미트 트리거 → FPGA 이벤트 래치
```

## 동작 시나리오

| 상태 | 입력 조건 | FPGA 출력 | PC 표시 |
|---|---|---|---|
| `NORMAL` | 일정한 정상 진동 | 모터 Enable 유지, 정상 LED | 정상 그래프 |
| `WARNING` | 진동 수준 증가 | 경고 LED | SPC Warning |
| `AI WARNING` | 정상 진동 패턴 이탈 | 출력 유지 | AI Warning |
| `INTERLOCK` | 절대 진동 임계치 초과 | LED/7-segment 경고, 모터 OFF | Vibration Interlock |
| `ESD_SIM` | RC 과도 이벤트 입력 | 이벤트 래치, 모터 OFF | ESD_SIM_EVENT 로그 |

SPC와 AI는 조기 경고 역할만 맡습니다. 실제 모터 차단은 FPGA 하드웨어 임계치와 이벤트 래치가 수행합니다.

## 하드웨어

### Purdue ECE270 FPGA Breakout Board

- iCE40HX-8K FPGA와 12 MHz 클록
- 8자리 7-segment
- 20개 내장 푸시버튼
- 내장 LED와 RGB LED
- UART
- 외부 GPIO 헤더

### 외부 부품

- ADXL345 3축 가속도 센서
- ERM 진동 모터
- MOSFET 모터 드라이버
- 2xAA 배터리 홀더와 AA 배터리 2개
- 브레드보드 및 female-to-male 점퍼선
- 피에조 부저
- ESD_SIM 회로: 택트 스위치, 저항·커패시터, 74LVC1G14 또는 74HC14 슈미트 트리거, 0.1uF 디커플링 커패시터

모터는 FPGA GPIO에 직접 연결하지 않습니다. 외부 배터리 전원과 MOSFET 드라이버를 사용하고, FPGA는 드라이버의 Enable/PWM 신호만 제어합니다.

## ESD_SIM 입력

실제 스파크를 만들지 않습니다.

```text
3.3V 버튼 입력
→ RC 미분기: 짧은 저전압 과도 펄스 생성
→ 슈미트 트리거: 안전한 0/3.3V 디지털 이벤트로 정형
→ FPGA GPIO
→ 이벤트 래치 및 즉시 인터록
```

RC 출력은 FPGA GPIO에 직접 연결하지 않습니다. 슈미트 트리거의 3.3V 출력만 FPGA 입력으로 사용합니다.

## FPGA RTL

```text
rtl/
  top_interlock.sv
  adxl345_i2c_master.sv
  vibration_monitor.sv
  button_sync_debounce.sv
  transient_event_latch.sv
  interlock_controller.sv
  motor_pwm.sv
  seven_segment_status.sv
  uart_tx.sv
  mmio_interlock.sv

tb/
  vibration_monitor_tb.sv
  transient_event_latch_tb.sv
  interlock_controller_tb.sv
  uart_tx_tb.sv
  top_interlock_tb.sv
```

### FPGA 역할

- ADXL345 I2C 수신과 진동 수준 레지스터화
- 짧은 과도 이벤트의 입력 동기화·이벤트 래치
- 강한 진동 또는 ESD_SIM 이벤트 시 즉시 인터록
- 내장 LED·7-segment·RGB LED 상태 출력
- 모터 드라이버 Enable/PWM 제어
- CPU 또는 PC로 보낼 상태 데이터 제공

## RISC-V CPU와 MMIO

초기 구현은 RV32I 어셈블리 polling 방식으로 진행합니다.

```text
0x8000_0000 : VIBRATION_SAMPLE  (read)
0x8000_0004 : VIBRATION_LEVEL   (read)
0x8000_0008 : EVENT_STATUS      (read)
0x8000_000C : INTERLOCK         (read)
0x8000_0010 : THRESHOLD         (read/write)
0x8000_0014 : CONTROL           (write)
0x8000_0018 : UART_TX           (write)
```

CPU는 최근 8개 진동값을 합산하고 3비트 시프트해 이동 평균을 계산합니다.

```text
moving_average = (sample[0] + ... + sample[7]) >> 3
```

C 런타임과 인터럽트는 CPU 기본 검증이 끝난 뒤 확장합니다. CPU 통합 전에도 FPGA 단독 인터록과 UART 송신이 동작하는 MVP를 먼저 완성합니다.

## PC FDC / SPC / AI

UART는 초기에는 9,600 bps, 약 100ms 주기로 상태를 전송합니다.

```text
time_ms,vibration_level,event_latched,interlock
1200,7,0,0
1300,10,0,0
1400,28,0,1
1500,8,1,1
```

PC 대시보드 기능:

- X/Y/Z 진동 및 전처리 진동 수준 그래프
- CSV 자동 저장과 이벤트 로그
- 정상 데이터 기반 SPC 관리도
- CL, UCL = mu + 3sigma, LCL = max(0, mu - 3sigma)
- Isolation Forest 기반 AI 조기 경고
- `NORMAL`, `WARNING`, `AI WARNING`, `INTERLOCK`, `ESD_SIM` 표시

## 구현 순서

1. 가상 진동·과도 이벤트 테스트벤치 작성
2. FPGA 인터록, LED, 7-segment, 모터 Enable RTL 검증
3. UART와 Python 가상 FDC 대시보드 구현
4. ADXL345 I2C 실제 연결
5. 진동 모터와 MOSFET 드라이버 실제 연결
6. RC 미분기와 슈미트 트리거 ESD_SIM 입력 연결
7. RISC-V MMIO와 8-sample 이동 평균 연동
8. SPC·AI 대시보드 통합

## 시연

1. 일정한 진동 모터 동작에서 `NORMAL` 상태와 기준 데이터를 확인합니다.
2. 모터 진동을 크게 또는 불규칙하게 만들어 SPC/AI 경고를 확인합니다.
3. 절대 진동 임계치를 넘겨 FPGA 하드웨어 인터록과 모터 OFF를 확인합니다.
4. ESD_SIM 버튼을 눌러 과도 이벤트 래치, 7-segment `E`, 모터 차단과 PC 로그를 확인합니다.
5. 내장 리셋 버튼으로 안전 상태에서만 정상 복귀합니다.

## 포트폴리오 표현

> ADXL345 기반 실제 진동 데이터를 FPGA로 수집하고, RISC-V CPU에서 8-sample 이동 평균 전처리를 수행했다. RC 미분기와 슈미트 트리거를 활용해 ESD 유사 과도 이벤트를 안전한 저전압 신호로 모사하고, FPGA 하드웨어 인터록 및 PC 기반 SPC·AI 대시보드와 연동했다.


## 문서

- [FPGA UART 실물 통신 시험 가이드](docs/UART_HARDWARE_TEST_KO.md)
- [Pygame UART FPGA 데모 사용 가이드](docs/PYGAME_UART_DEMO_KO.md)
- [BNO085 기반 모터 진동 모니터링 및 FPGA 인터록 구현 계획](docs/BNO085_MOTOR_INTERLOCK_PLAN_KO.md)
- [부품 없이 진행하는 FPGA 인터록 데모](docs/NO_PARTS_FPGA_DEMO_KO.md)
- [테스트벤치 명령어 모음집](docs/COMMANDS_KO.md)
- [Linux PC 기반 FPGA 빌드·업로드·시험 가이드](docs/FPGA_TEST_GUIDE_KO.md)
- [코드 구성 및 기능 설명서](docs/CODE_REFERENCE_KO.md)
- [영문 FPGA 사전 테스트 가이드](docs/FPGA_TEST_GUIDE.md)

## 현재 보드만으로 실행하는 UART/Pygame 데모

센서와 모터가 없어도 PC와 FPGA만으로 전체 제어 흐름을 확인할 수 있습니다.

```powershell
git pull origin main
& "$env:LOCALAPPDATA\\Programs\\Python\\Python311\\python.exe" .\\pc\\pygame_demo.py --port COM12
```

Pygame의 `RUN NORMAL`, `WARNING`, `STRONG VIB`, `ESD_SIM`, `RESET`, `STOP` 버튼은 COM12로 FPGA에 명령을 전송합니다. FPGA는 인터록 상태를 직접 결정하고, Pygame은 200 ms마다 상태를 조회해 화면을 갱신합니다. 좌측 테스트 리그는 PWM/진동 상태에 따라 회전·진동하고 인터록 발생 후 감속 정지합니다. BNO085가 없는 현재의 X/Y/Z 및 진동 그래프는 명확히 표시된 시뮬레이션 값입니다.

| 바이트 | 기능 |
|---|---|
| `0x10` | 정상 운전 |
| `0x11` | 경고 진동 모사 |
| `0x12` | 강진동 인터록 모사 |
| `0x13` | ESD_SIM 인터록 |
| `0x14` | 인터록 리셋 후 정지 |
| `0x15` | 운전자 정지 |
| `0xF0` | FPGA 상태 조회 |

RTL 검증은 `make test_command`, 전체 테스트는 `make test`로 실행합니다.

## 현재 상태

- 인터록 FSM, 상태 표시 RTL 구현
- NORMAL/WARNING/INTERLOCK/ESD_SIM 테스트벤치 구현
- Icarus Verilog 시뮬레이션 통과
- Verilator lint 통과 (미사용 보드 버튼 경고 제외)
- Windows Purdue 스타일 가상 FDC 데모 구현
- FPGA 보드 사전 테스트 가이드 작성
- Yosys 합성, nextpnr 배치·배선, IcePack 비트스트림 생성 검증 완료
- Linux CRAM/Flash 업로드용 Makefile과 ECE270 rev.2 PCF 추가
- ADXL345 I2C, 실제 UART 패킷 송신, Linux 실물 대시보드는 다음 단계
