# BNO085 기반 단일 모터 진동 모니터링 및 FPGA 인터록 상세 계획

## 1. 최종 프로젝트 정의

### 프로젝트명

**BNO085 기반 모터 설비 진동 모니터링 및 FPGA 실시간 인터록 시스템**

### 한 줄 설명

고정된 3D 프린터 구형 하우징 내부에 BNO085와 편심 모터 1개를 장착하고, Python이 FPGA에 정상 PWM과 무작위 고강도 PWM을 명령하여 이상 진동 조건을 주입한다. FPGA는 BNO085 측정 데이터만으로 위험 진동을 판단하고, ESD_SIM 이벤트 또는 센서 장애가 발생해도 CPU·PC·AI와 독립적으로 모터를 즉시 차단한다.

### 프로젝트 범위와 정확한 표현

- 실제 반도체 설비의 고주파 베어링 진단기가 아니다.
- 실제 ESD 방전이나 스파크를 생성·측정하지 않는다.
- 소형 모터 하우징의 진동 수준 변화와 안전한 저전압 과도 이벤트를 이용한 교육용 설비 인터록 데모다.
- Python이 PWM을 높이는 동작은 **비정상 진동 조건을 재현하는 Fault Injection**이다.
- 안전 차단은 AI가 아니라 FPGA 하드웨어 임계값과 이벤트 래치가 담당한다.

## 2. 최종 시스템 구조

```text
                                 ┌─ 온보드 버튼 3
[ESD_SIM] 외부 버튼 → RC → 슈미트 ─┤
                                 └─ FPGA event input

[PC Python]
  랜덤 PWM 명령 ── UART ────────────────┐
  FDC/SPC/AI 대시보드 ← UART ──────────┤
                                         ▼
[BNO085] ─ I2C ─ [센서 브리지 MCU] ─ UART ─ [iCE40HX8K FPGA]
                                                  │
                                                  ├─ PWM / motor_enable
                                                  ▼
                                              [DRV8833]
                                                  │
                                                  ▼
                                       [편심 진동 모터 1개]
                                                  │
                                                  ▼
                             [고정된 3D 프린터 구형 하우징]
                                                  │
                                                  └─ 실제 진동 → BNO085
```

### 역할 분담

- **BNO085:** 구체 하우징의 선형가속도 X/Y/Z 측정
- **센서 브리지 MCU:** BNO085의 I2C/SHTP 통신 처리와 고정 길이 UART 패킷 생성
- **FPGA:** PC 명령 수신, PWM 생성, 센서 패킷 수신, 진동 계산, 인터록, 표시 및 PC 텔레메트리
- **DRV8833:** FPGA의 3.3V PWM을 받아 편심 모터 구동
- **Python:** 정상 운전과 랜덤 Fault Injection 시나리오 실행, CSV 저장, 그래프, SPC 및 AI
- **RISC-V CPU:** FPGA 단독 MVP 완성 후 MMIO, 이동평균 및 텔레메트리 전처리 기능으로 확장

## 3. 물리적 배치

### 구체 내부

- BNO085 1개
- 편심 진동 모터 1개
- 센서와 모터를 고정하는 내부 플레이트
- 나사 체결용 스탠드오프
- 센서선과 모터선이 빠져나오는 케이블 홀

### 구체 외부

- iCE40HX8K FPGA 보드
- 센서 브리지 MCU
- DRV8833 모터 드라이버
- 모터용 외부 전원
- ESD_SIM RC·슈미트 트리거 회로
- PC와 FPGA를 연결하는 USB/UART

FPGA, DRV8833, RC 회로를 구체 안에 넣지 않는다. 구체는 굴리거나 회전시키지 않고 테이블 또는 지그에 고정하며 내부 편심 모터만 회전시킨다.

## 4. 3D 프린터 구체 설계

### 권장 형상

- 지름 약 100~150mm
- 위·아래 두 개의 반구로 분리
- 아래쪽에 굴러가지 않는 평평한 받침 추가
- 중앙 내부 플레이트에 모터와 센서 장착
- 반구 결합용 나사 구멍과 인서트 구성
- 센서선과 모터선을 분리해 배출할 수 있는 케이블 홀 2개
- 반복 분해가 가능하도록 접착제만으로 밀봉하지 않음

### 센서 장착

- BNO085를 나사 또는 단단한 접착 패드로 내부 플레이트에 고정한다.
- 센서가 움직이거나 공 내부에 부딪히면 설비 진동이 아닌 충돌 신호가 측정되므로 느슨하게 두지 않는다.
- 센서 축 방향을 표시해 재조립 후에도 동일한 방향을 유지한다.
- 모터와 너무 가깝게 배치해 센서가 포화되지 않도록 약간 떨어뜨린다.

### 모터 장착

- 반드시 편심추가 있는 ERM 진동 모터 또는 편심추를 장착한 DC 모터를 사용한다.
- 모터 브래킷을 내부 플레이트에 단단히 고정한다.
- 회전 부품이 전선이나 구체 외벽에 닿지 않도록 간격을 확보한다.
- 초기 시험은 구체를 닫지 않은 상태에서 낮은 PWM으로 수행한다.

## 5. 실제 배선

### BNO085와 MCU

```text
BNO085 VIN/3V3 ─ MCU 센서 전원
BNO085 GND     ─ MCU GND
BNO085 SDA     ─ MCU SDA
BNO085 SCL     ─ MCU SCL
```

사용하는 BNO085 Breakout의 전원 및 I/O 전압 사양을 확인한 뒤 연결한다.

### MCU와 FPGA

```text
MCU UART TX ─ FPGA 외부 GPIO sensor_rx
MCU GND     ─ FPGA GND
```

초기 구현에서는 센서 데이터가 MCU에서 FPGA로 단방향 전송되므로 MCU TX 한 선만 필수다. 설정 명령이 필요하면 FPGA TX를 MCU RX에 추가한다.

### FPGA와 DRV8833

```text
FPGA motor_pwm    ─ DRV8833 AIN1
FPGA direction/0  ─ DRV8833 AIN2
FPGA GND          ─ DRV8833 GND
외부 모터 전원 +  ─ DRV8833 VMOTOR
편심 모터 두 선   ─ DRV8833 AOUT1/AOUT2
DRV8833 FLT       ─ FPGA fault input  # 선택
```

모터는 한 방향으로만 회전하면 되므로 AIN2는 고정 LOW로 두고 AIN1에 PWM을 인가한다. 최종 연결은 실제 DRV8833 Breakout의 핀 이름을 다시 확인한 후 진행한다.

### 공통 전원 원칙

- FPGA GPIO로 모터에 전원을 공급하지 않는다.
- 모터는 별도 전원을 사용한다.
- FPGA, MCU, BNO085, DRV8833의 기준 GND는 공통 연결한다.
- 모터 전원과 센서 전원 배선을 서로 떨어뜨린다.
- 모터 전원 입력과 센서 전원 근처에 디커플링 커패시터를 배치한다.
- 전원 극성과 전압을 멀티미터로 확인한 뒤 FPGA를 연결한다.

## 6. ESD_SIM 회로

실제 스파크 대신 3.3V 버튼 입력과 RC 미분기를 이용해 짧은 저전압 과도 이벤트를 만든다.

```text
3.3V → Push Button → 10nF 직렬 C → event_node
                                      │
                                      └─ 100kΩ → GND

event_node → 3.3V 슈미트 트리거 → FPGA esd_sim_in
```

초기 시정수:

```text
τ = R × C = 100kΩ × 10nF = 1ms
```

### 안전 검증

1. FPGA에서 분리한 상태로 RC 회로를 구성한다.
2. MSO-X 3014A CH1로 RC 노드의 과도 펄스를 확인한다.
3. CH2로 슈미트 트리거 출력을 확인한다.
4. FPGA에 연결되는 출력이 0~3.3V인지 확인한다.
5. RC 노드를 FPGA에 직접 연결하지 않고 슈미트 트리거 출력만 연결한다.
6. 외부 회로가 준비되기 전에는 현재 검증된 온보드 버튼 3을 ESD_SIM으로 사용한다.

## 7. PWM 제어 구조

Python은 PWM 파형을 직접 만들지 않는다. Python은 UART로 목표 듀티비를 보내고 FPGA가 12MHz 클록으로 실제 PWM을 생성한다.

```text
Python requested_duty → FPGA PWM register → 20kHz PWM → DRV8833
```

12MHz 클록에서 20kHz PWM의 한 주기는 600클록이다.

```text
PWM_PERIOD_COUNT = 12,000,000 / 20,000 = 600
PWM_HIGH_COUNT   = 600 × duty / 100
```

### PWM 우선순위

```text
if reset:
    applied_pwm = 0
elif interlock or esd_event or sensor_timeout or driver_fault:
    applied_pwm = 0
elif pc_command_timeout:
    applied_pwm = 0
else:
    applied_pwm = requested_pwm
```

Python 명령이나 RISC-V 소프트웨어가 어떤 값을 보내더라도 인터록 신호가 활성화되면 FPGA가 PWM을 0%로 강제한다.

### 모터 기동 보정

낮은 듀티비에서 모터가 출발하지 않으면 다음과 같이 기동 부스트를 적용한다.

```text
정지 → 약 0.2초 동안 100% → 목표 듀티비 적용
```

기동 부스트 중에도 ESD_SIM과 하드 인터록은 즉시 PWM을 0%로 만들 수 있어야 한다.

## 8. 정상 및 랜덤 이상 진동 시나리오

모터는 한 개만 사용한다.

| 구간 | PWM | 지속시간 | 의미 |
|---|---:|---:|---|
| 시작 | 0% | 1초 | Reset 및 센서 안정화 |
| 정상 | 35~40% | 무작위 5~15초 | 일정한 정상 진동 |
| Fault Injection | 75~100% | 무작위 0.3~2초 | 강한 비정상 진동 모사 |
| Interlock | 0% | Reset 전까지 | FPGA 강제 차단 |

Python은 다음 순서로 동작한다.

```python
while test_is_running:
    send_requested_pwm(40)
    wait(random.uniform(5.0, 15.0))

    injected_pwm = random.randint(75, 100)
    mark_fault_start(injected_pwm)
    send_requested_pwm(injected_pwm)
    wait(random.uniform(0.3, 2.0))

    # 위험 진동이 검출되면 FPGA가 자체적으로 PWM을 0%로 강제한다.
```

### 실험 해석

PWM 증가는 의도적으로 발생시킨 Fault Injection이다. 검출 알고리즘은 PWM 명령값을 보고 판정하지 않고 BNO085 측정 데이터만 사용해야 한다. Python은 PWM 주입 시각을 정답 라벨로 기록해 감지 성공 여부와 감지 지연시간을 계산한다.

## 9. 센서 데이터 경로

### BNO085 설정

- 선형가속도 X/Y/Z 사용
- 초기 샘플링 속도 100Hz
- 자세각보다 중력 성분이 제거된 선형가속도 우선 사용
- MCU에서 가속도를 mg 단위 signed 16-bit 정수로 변환
- 이 프로젝트는 진동 크기 변화 감지가 목적이며 정밀 고주파 스펙트럼 진단을 주장하지 않음

### MCU에서 FPGA로 보내는 패킷

```text
Header | Sequence | AX_L | AX_H | AY_L | AY_H | AZ_L | AZ_H | Checksum
```

- Header: 패킷 시작 바이트
- Sequence: 누락 패킷 확인
- AX/AY/AZ: mg 단위 signed 16-bit
- Checksum: XOR 또는 8-bit 합
- UART: 115200bps
- 전송 주기: 10ms, 약 100Hz

## 10. FPGA 진동 처리

FPGA 하드 인터록에서는 제곱근이 필요한 정확한 벡터 크기보다 연산이 간단한 절댓값 합을 사용한다.

```text
vibration_level = abs(AX) + abs(AY) + abs(AZ)
moving_average  = 최근 16개 vibration_level 평균
peak            = 최근 윈도우의 최대 vibration_level
```

### 초기 상태 판정

```text
moving_average < warning_threshold
→ NORMAL

moving_average >= warning_threshold
→ WARNING

peak >= hard_trip_threshold
→ 즉시 INTERLOCK

moving_average >= trip_threshold가 N회 연속
→ INTERLOCK

sensor_packet_timeout
→ INTERLOCK
```

임계값은 먼저 정상 PWM 40%와 Fault PWM 75~100% 데이터를 수집한 뒤 결정한다. 임의의 숫자를 최종 임계값으로 고정하지 않는다.

## 11. FPGA RTL 계획

```text
rtl/
  top_bno085_interlock.sv
  uart_rx.sv
  pc_command_parser.sv
  sensor_packet_parser.sv
  vibration_monitor.sv
  motor_pwm.sv
  interlock_controller.sv
  seven_segment_status.sv
  uart_tx.sv
  telemetry_packet.sv
  mmio_interlock.sv          # RISC-V 확장

tb/
  motor_pwm_tb.sv
  sensor_packet_parser_tb.sv
  vibration_monitor_tb.sv
  interlock_controller_tb.sv
  top_bno085_interlock_tb.sv
```

### 모듈별 역할

- `uart_rx.sv`: MCU 또는 PC에서 UART 바이트 수신
- `pc_command_parser.sv`: PWM 설정, Reset 및 시험 명령 복원
- `sensor_packet_parser.sv`: X/Y/Z 패킷과 Checksum 검증
- `vibration_monitor.sv`: 절댓값 합, 이동평균, Peak 및 센서 타임아웃
- `motor_pwm.sv`: 20kHz PWM, 기동 부스트 및 강제 차단
- `interlock_controller.sv`: NORMAL/WARNING/INTERLOCK/ESD_SIM 상태 FSM
- `seven_segment_status.sv`: `0`, `1`, `L`, `E` 상태 출력
- `telemetry_packet.sv`: PC로 보낼 측정값과 상태 프레임 생성
- `mmio_interlock.sv`: RISC-V CPU용 상태 및 제어 레지스터

## 12. FPGA 입력 우선순위와 표시

| 이벤트 | motor PWM | 7-segment | RGB LED | 래치 |
|---|---:|---|---|---|
| NORMAL | Python 요청값 | `0` | Green | 없음 |
| WARNING | Python 요청값 | `1` | Blue | 선택 |
| 진동 Trip | 0% | `L` | Red | 유지 |
| ESD_SIM | 0% | `E` | Red | 유지 |
| 센서 Timeout | 0% | `E` 또는 별도 코드 | Red | 유지 |
| DRV8833 Fault | 0% | 별도 코드 | Red | 유지 |

ESD_SIM이 진동 Trip보다 나중에 들어오더라도 이벤트 원인을 별도 레지스터에 기록한다. Reset은 모터가 정지하고 위험 입력이 해제된 상태에서만 허용한다.

## 13. PC 대시보드 및 로그

### 조작 화면

- PWM 수동 슬라이더 0~100%
- NORMAL RUN 버튼
- RANDOM FAULT TEST 시작·정지 버튼
- RESET 요청 버튼
- 현재 requested PWM과 FPGA applied PWM 동시 표시
- 인터록 상태와 원인 표시

### 실시간 표시

- BNO085 X/Y/Z
- vibration_level, moving_average, peak
- NORMAL/WARNING/INTERLOCK
- 센서 패킷 수신 상태
- ESD_SIM 래치
- 감지 지연시간
- SPC 및 AI 상태

### CSV 형식

```text
timestamp_ms,ax_mg,ay_mg,az_mg,vibration,moving_average,requested_pwm,applied_pwm,fault_injected,state,trip_reason
```

`fault_injected`는 모델 입력이 아니라 성능 평가용 정답 라벨로만 사용한다.

## 14. SPC 및 AI

### SPC

정상 PWM 구간의 진동 특징으로 관리한계선을 계산한다.

```text
CL  = mean
UCL = mean + 3 × standard_deviation
LCL = max(0, mean - 3 × standard_deviation)
```

### Isolation Forest

1초 윈도우에서 다음 특징을 계산한다.

- X/Y/Z RMS
- Peak와 Peak-to-Peak
- 표준편차
- Crest factor
- 이동평균
- 가능하면 주요 FFT 주파수

AI 입력에서 `fault_injected`, trip 결과 및 PWM 주입 정답은 제외한다. AI는 조기 경고만 제공하고 FPGA 인터록을 직접 제어하지 않는다.

소규모 자체 데이터에는 H100 GPU가 필요하지 않으며 CPU 기반 Isolation Forest가 적합하다. 충분한 데이터가 확보된 뒤 1D CNN과 비교하는 것은 확장 목표다.

## 15. 부품 도착 전 구현

- 기존 버튼 기반 인터록 FPGA 실물 검증 유지
- `motor_pwm.sv`와 테스트벤치 작성
- 가상 BNO085 UART 패킷 생성기 작성
- `sensor_packet_parser.sv` 구현
- `vibration_monitor.sv` 구현
- Python 랜덤 PWM 시험 로직 구현
- 대시보드에 requested/applied PWM 및 Fault Injection 표시 추가
- 센서 Timeout 및 ESD_SIM 통합 테스트벤치 작성

## 16. 부품 도착 후 5일 일정

### 1일차: 개별 부품 확인

- BNO085를 MCU에 연결해 X/Y/Z 확인
- DRV8833과 모터를 FPGA 없이 낮은 전압으로 확인
- FPGA PWM 출력 주파수와 듀티비를 오실로스코프로 확인
- RC와 슈미트 트리거 출력 파형 확인

### 2일차: 모터와 구체 조립

- 내부 플레이트에 센서와 모터 고정
- 구체를 열어둔 상태에서 PWM 20~40% 시험
- 전선 간섭, 모터 발열, 센서 포화 여부 확인
- 정상 PWM별 BNO085 기준 데이터 수집

### 3일차: FPGA 통합

- MCU 센서 패킷을 FPGA에서 수신
- Python PWM 명령을 FPGA에서 수신
- Warning과 Trip 임계값 임시 설정
- 인터록 시 PWM 0% 강제 동작 확인
- 센서 통신선 제거 Fail-safe 확인

### 4일차: PC 및 데이터 분석

- 랜덤 PWM Fault Injection 자동화
- CSV 로그와 감지 지연시간 계산
- SPC 관리선 생성
- Isolation Forest 학습과 혼동행렬 확인

### 5일차: 최종 시연 및 문서화

- 정상 → 랜덤 Fault → 진동 인터록
- Reset → 정상 복귀
- ESD_SIM → 즉시 인터록
- 센서 Timeout → Fail-safe
- 영상, 회로 사진, 오실로스코프 파형 및 PC 그래프 저장
- 실제 구현 범위와 미구현 확장 범위를 구분해 기록

## 17. 단계별 통합 시험

### 시험 A: FPGA 단독

- 버튼 1: WARNING
- 버튼 2: 진동 Trip 모사
- 버튼 3: ESD_SIM
- 버튼 0: Reset
- 현재 완료: 테스트벤치, 합성, 배치·배선 및 CRAM 업로드, 7-segment `E` 실물 확인

### 시험 B: PWM만 연결

- 오실로스코프로 20kHz와 듀티비 확인
- DRV8833을 연결하고 20%, 40%, 60%, 80% 속도 비교
- 인터록 입력 시 PWM이 즉시 LOW가 되는지 확인

### 시험 C: 센서만 연결

- 모터 OFF에서 노이즈 기준값 수집
- 모터 40%에서 정상 진동값 수집
- 모터 75~100%에서 비정상 진동값 수집
- 센서 패킷 누락과 Checksum 오류 처리 확인

### 시험 D: 전체 시스템

- Python이 PWM 40%로 정상 운전
- 5~15초 후 랜덤 고강도 PWM 주입
- BNO085 측정값 급증
- FPGA 인터록과 모터 차단
- PC 로그의 주입 시각과 검출 시각 비교
- Reset 후 ESD_SIM 독립 시험

## 18. 최종 시연 순서

1. FPGA를 CRAM에 업로드한다.
2. 시스템 Reset 후 센서 통신 정상 상태를 확인한다.
3. Python 대시보드에서 RANDOM FAULT TEST를 시작한다.
4. FPGA가 모터를 PWM 40%로 구동한다.
5. 5~15초 동안 안정적인 정상 진동 그래프를 보여준다.
6. Python이 예고 없이 75~100% PWM을 0.3~2초간 요청한다.
7. BNO085 측정값만 이용해 FPGA가 위험 진동을 감지한다.
8. FPGA가 applied PWM을 0%로 강제하고 모터를 차단한다.
9. 7-segment `L`, RGB Red 및 PC VIBRATION INTERLOCK을 확인한다.
10. 주입 시각부터 차단 시각까지 감지 지연시간을 표시한다.
11. Reset 후 다시 PWM 40% 정상 운전을 확인한다.
12. ESD_SIM 버튼을 눌러 진동과 관계없이 즉시 차단되는지 확인한다.
13. 7-segment `E`와 이벤트 로그를 확인한다.

## 19. 완료 기준

### 필수 MVP

- BNO085 실시간 선형가속도 측정
- MCU에서 FPGA로 센서 UART 패킷 전송
- Python에서 FPGA로 PWM 명령 전송
- FPGA 20kHz PWM과 DRV8833 모터 구동
- 단일 모터 정상·랜덤 고강도 진동 재현
- FPGA 진동 임계값 인터록
- FPGA ESD_SIM 이벤트 인터록
- 센서 통신 Timeout Fail-safe
- 7-segment와 LED 상태 표시
- PC 실시간 그래프 및 CSV 로그

### 시간 여유 시 추가

- SPC 관리도
- Isolation Forest 이상탐지
- DRV8833 Fault 입력
- RISC-V MMIO와 이동평균 펌웨어
- BNO085 직접 FPGA 통신
- 1D CNN 비교

## 20. 주요 리스크와 대응

| 리스크 | 대응 |
|---|---|
| BNO085 프로토콜 구현 지연 | MCU 라이브러리를 이용한 UART 브리지 사용 |
| 낮은 PWM에서 모터 정지 | 0.2초 기동 부스트 적용 |
| 모터 노이즈로 센서/UART 오류 | 전원 분리, 공통 GND, 디커플링 및 배선 분리 |
| 센서가 흔들려 충돌 신호 발생 | 내부 플레이트에 단단히 고정 |
| BNO085 샘플링보다 높은 진동 주파수 | 정밀 FFT가 아닌 진동 크기 변화 감지로 범위 제한 |
| Python 또는 UART 중단 | 명령 Timeout 시 FPGA가 PWM 0%로 차단 |
| AI 오탐 | AI는 경고만 수행하고 차단은 FPGA가 담당 |
| 실제 ESD로 오해 | 문서와 발표에서 ESD_SIM 저전압 모사임을 명시 |

## 21. 포트폴리오 표현

> 고정형 3D 프린터 모터 하우징 내부에 BNO085와 편심 모터를 장착하고, Python 기반 랜덤 PWM Fault Injection으로 정상 및 비정상 진동 조건을 재현했다. iCE40 FPGA가 센서 측정값만으로 진동 Peak와 이동평균을 실시간 감시하고, 위험 진동·센서 통신 단절·저전압 ESD_SIM 이벤트 발생 시 CPU와 AI 상태에 관계없이 DRV8833의 모터 출력을 즉시 차단하는 Fail-safe 인터록을 구현했다.
