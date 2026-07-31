# BNO085 기반 모터 진동 모니터링 및 FPGA 인터록 구현 계획

## 1. 프로젝트 정의

### 프로젝트명

**BNO085 기반 모터 설비 진동 모니터링 및 FPGA 실시간 인터록 시스템**

### 한 줄 설명

3D 프린터로 제작한 구형 하우징 내부에 BNO085와 편심 모터를 고정하고, FPGA PWM으로 여러 진동 조건을 재현한다. FPGA는 위험 진동이나 ESD_SIM 이벤트가 발생하면 CPU·PC·AI 상태와 관계없이 모터를 즉시 차단하고, PC는 FDC/SPC 시각화와 AI 이상탐지를 담당한다.

### 프로젝트 범위

이 프로젝트는 실제 반도체 설비의 고주파 베어링 진단기나 실제 ESD 측정기가 아니다. 저속 소형 모터에서 발생하는 진동 변화와 안전한 버튼 기반 ESD_SIM 이벤트를 이용하여 설비 상태 감시, 이상 경고, 하드웨어 인터록 구조를 검증하는 교육용 데모다.

## 2. 전체 시스템 구조

```text
                         +-- 버튼 3: ESD_SIM
                         |
BNO085 --I2C-- MCU --UART-- FPGA --PWM-- DRV8833 -- 편심 모터
                         |
                         +-- 하드웨어 인터록
                         +-- LED / 7-segment
                         +-- UART -- PC FDC·SPC·AI 대시보드
```

### 역할 분담

- **BNO085:** 선형가속도 X/Y/Z 측정
- **센서 브리지 MCU:** BNO085 라이브러리와 I2C/SHTP 처리를 담당하고 측정값을 FPGA용 고정 길이 UART 패킷으로 변환
- **FPGA:** 센서 패킷 수신, PWM 생성, 진동 지표 계산, 상태 FSM, 하드웨어 인터록 및 보드 표시
- **DRV8833:** FPGA의 3.3V PWM 신호로 편심 모터 구동
- **PC:** 실시간 그래프, CSV 로그, SPC 관리도 및 AI 이상탐지
- **RISC-V CPU:** FPGA 단독 MVP가 완성된 뒤 이동평균, MMIO 및 UART 텔레메트리 기능으로 확장

BNO085의 통신 프로토콜은 ADXL345보다 복잡하므로 5일 프로젝트에서는 MCU를 센서 통신 브리지로 사용하는 구성을 기본안으로 한다. FPGA가 BNO085의 SHTP 프로토콜을 직접 처리하는 방식은 확장 목표로 둔다.

## 3. 기구 및 전기 구성

### 3D 프린터 구조

- 구체 자체는 회전시키지 않고 내부 편심 모터만 회전시킨다.
- BNO085를 구체 내부 프레임 또는 외벽에 단단히 고정한다.
- 편심 모터는 별도 브래킷으로 고정한다.
- 센서가 내부에서 움직이면 설비 진동이 아니라 충돌을 측정하므로 느슨하게 넣지 않는다.
- 구체는 테이블 또는 시험 지그에 고정한다.
- 정상·이상 조건은 PWM, 편심추 질량, 체결 상태를 변경하여 재현한다.

### 전원 및 연결 원칙

- FPGA GPIO에 모터를 직접 연결하지 않는다.
- FPGA는 DRV8833의 제어 입력에만 3.3V PWM을 출력한다.
- 모터는 별도 전원을 사용하고 FPGA, MCU, DRV8833의 GND를 공통 연결한다.
- 모터 전원에는 충분한 디커플링 커패시터를 배치한다.
- 센서 전원 배선은 모터 전원 배선과 분리하거나 필터링한다.
- DRV8833의 Fault 출력을 사용할 수 있으면 FPGA의 추가 인터록 입력으로 연결한다.

## 4. PWM 기반 진동 조건

| 모드 | PWM 듀티비 | 의미 |
|---|---:|---|
| `STOP` | 0% | 설비 정지 |
| `NORMAL` | 35% | 정상 운전 |
| `LOAD` | 50% | 부하 증가 |
| `WARNING` | 65% | 진동 증가 |
| `FAULT` | 80% | 비정상 진동 |
| `TRIP` | 0% | 인터록에 의한 강제 차단 |

PWM 주파수는 초기값 20kHz로 설정한다. 낮은 듀티비에서 모터가 기동하지 않으면 시작할 때 약 0.2초 동안 100%를 출력한 후 목표 듀티비로 낮춘다.

PWM은 모터 회전속도를 바꾸므로 진동의 세기와 주요 주파수가 함께 변한다. AI 학습 시 PWM 값만으로 정상·불량을 구분하지 않도록 동일한 PWM에서도 편심추, 체결 상태 또는 외부 충격 조건을 변경하여 데이터를 수집한다.

## 5. 센서 데이터 경로

### BNO085 설정

- 선형가속도 X/Y/Z를 사용한다.
- 초기 샘플링 속도는 100Hz로 설정한다.
- 센서 융합 자세각보다 중력 성분이 제거된 선형가속도를 우선 사용한다.
- MCU에서 부동소수점 가속도를 mg 단위의 signed 16-bit 정수로 변환한다.

### MCU에서 FPGA로 보내는 패킷

```text
Header | Sequence | AX_L | AX_H | AY_L | AY_H | AZ_L | AZ_H | Checksum
```

- Header: 패킷 시작 바이트
- Sequence: 패킷 누락 확인
- AX/AY/AZ: mg 단위 signed 16-bit 값
- Checksum: XOR 또는 8-bit 합으로 패킷 오류 확인
- UART 초기 속도: 115200bps

100Hz에서 9바이트 패킷을 전송하면 UART 대역폭 안에서 충분히 처리할 수 있다.

## 6. FPGA RTL 구성

```text
rtl/
  top_bno085_interlock.sv
  sensor_uart_rx.sv
  sensor_packet_parser.sv
  vibration_monitor.sv
  motor_pwm.sv
  interlock_controller.sv
  seven_segment_status.sv
  uart_tx.sv
  mmio_interlock.sv          # RISC-V 확장
```

### 모듈별 기능

- `sensor_uart_rx.sv`: MCU UART 바이트 수신
- `sensor_packet_parser.sv`: Header, X/Y/Z 및 Checksum 복원
- `vibration_monitor.sv`: 절댓값, 이동평균, Peak 및 통신 타임아웃 계산
- `motor_pwm.sv`: 약 20kHz PWM 및 기동 부스트 생성
- `interlock_controller.sv`: NORMAL/WARNING/INTERLOCK/ESD_SIM 상태 제어
- `seven_segment_status.sv`: `0`, `1`, `L`, `E` 상태 표시
- `uart_tx.sv`: FPGA 상태와 측정값을 PC로 전송
- `mmio_interlock.sv`: RISC-V CPU가 센서값과 상태 레지스터를 읽는 확장 인터페이스

### FPGA 진동 지표

FPGA에서는 실시간 인터록을 위해 복잡한 제곱근 대신 다음 값을 사용한다.

```text
vibration_level = abs(AX) + abs(AY) + abs(AZ)
moving_average  = 최근 16개 vibration_level의 평균
```

PC에서는 원본 X/Y/Z 데이터로 RMS와 FFT를 추가 계산한다.

## 7. 인터록 정책

| 조건 | FPGA 동작 |
|---|---|
| 진동 이동평균이 경고값 초과 | WARNING 상태 및 경고 LED |
| 순간 Peak가 절대 위험값 초과 | 즉시 INTERLOCK |
| 진동 이동평균이 위험값을 일정 시간 초과 | INTERLOCK |
| BNO085 데이터가 일정 시간 들어오지 않음 | 통신 이상 INTERLOCK |
| DRV8833 Fault 입력 발생 | 모터 차단 |
| 버튼 3 입력 | ESD_SIM 이벤트 래치 및 모터 차단 |
| 버튼 0 입력 | 안전 조건 확인 후 Reset |

인터록이 발생하면 `motor_enable`을 0으로 만들고 PWM 출력을 강제로 0%로 고정한다. 이 경로는 RISC-V CPU, PC 대시보드 및 AI와 독립적으로 작동해야 한다.

## 8. PC FDC·SPC 대시보드

### 실시간 표시

- BNO085 X/Y/Z 선형가속도
- FPGA 진동 지표와 이동평균
- PWM 듀티비
- NORMAL/WARNING/INTERLOCK 상태
- 모터 Enable 상태
- ESD_SIM 이벤트 래치
- 센서 통신 상태
- AI NORMAL/ANOMALY 결과

### 데이터 저장

```text
timestamp,ax_mg,ay_mg,az_mg,vibration,moving_average,pwm,state,event,motor_enable
```

### SPC 관리도

정상 데이터 구간에서 중심선과 관리한계선을 계산한다.

```text
CL  = mean
UCL = mean + 3 * standard_deviation
LCL = max(0, mean - 3 * standard_deviation)
```

SPC 이탈은 조기 경고에만 사용하며 안전 차단은 FPGA가 담당한다.

## 9. AI 이상탐지

초기 모델은 적은 자체 수집 데이터에 적합한 Isolation Forest를 사용한다.

### 1초 윈도우 특징

- X/Y/Z RMS
- Peak와 Peak-to-Peak
- 표준편차
- Crest factor
- 주요 FFT 주파수
- 이동평균
- PWM 듀티비와 모터 운전 상태

### 데이터 수집

1. 정상 조립 상태에서 여러 PWM 조건의 데이터를 수집한다.
2. 동일한 PWM에서 편심추 변경, 체결 불량 모사, 외부 충격 데이터를 추가한다.
3. 시간 순서를 유지하여 학습·검증 데이터를 분리한다.
4. 정상 데이터 중심으로 Isolation Forest를 학습한다.
5. AI 결과는 조기 경고로만 사용하고 직접 모터를 차단하지 않는다.

소규모 자체 데이터에는 H100 GPU가 필요하지 않다. 데이터가 충분히 쌓인 뒤 1D CNN과 비교하는 것은 확장 목표다.

## 10. 5일 구현 일정

### 1일차: 부품 없이 RTL 검증

- `motor_pwm.sv`와 테스트벤치 작성
- 가상 BNO085 UART 패킷 생성기 작성
- UART 수신·패킷 파서·진동 계산기 검증
- 기존 인터록 FSM과 7-segment 연결
- 전체 RTL 시뮬레이션

### 2일차: 센서와 모터 연결

- BNO085와 MCU I2C 연결
- 100Hz 선형가속도 출력 확인
- DRV8833과 편심 모터 연결
- FPGA PWM 듀티비별 모터 동작 확인

### 3일차: FPGA 통합

- 센서 UART 패킷 실시간 수신
- Warning과 Interlock 임계값 조정
- 센서 통신 타임아웃 Fail-safe 검증
- LED, RGB LED 및 7-segment 검증

### 4일차: PC 및 AI

- 실시간 그래프와 CSV 기록
- SPC 관리선 계산
- 정상·이상 진동 데이터 수집
- Isolation Forest 학습과 결과 표시

### 5일차: 통합 시연 및 문서화

- 정상, 경고, 진동 인터록 시나리오 검증
- ESD_SIM 인터록 검증
- 센서 통신 단절 Fail-safe 검증
- 시연 영상과 결과 그래프 저장
- 블록도, 회로도, 검증 결과와 한계 정리

## 11. 최종 시연 순서

1. FPGA를 CRAM에 업로드하고 시스템을 Reset한다.
2. PWM 35%에서 모터를 구동하고 NORMAL 상태를 확인한다.
3. BNO085 X/Y/Z와 진동 지표가 PC에 표시되는지 확인한다.
4. PWM을 65%로 올려 WARNING 상태를 확인한다.
5. 동일 PWM에서 편심 조건을 변경하여 AI ANOMALY를 확인한다.
6. 위험 임계값을 넘겨 FPGA가 PWM을 0%로 만들고 모터를 차단하는지 확인한다.
7. 7-segment의 `L`과 PC의 VIBRATION INTERLOCK 로그를 확인한다.
8. Reset 후 정상 상태로 복귀한다.
9. 버튼 3을 눌러 ESD_SIM 이벤트, `E` 표시 및 즉시 모터 차단을 확인한다.
10. 센서 UART 선을 제거해 통신 단절 Fail-safe를 확인한다.

## 12. 완료 기준과 우선순위

### 필수 MVP

- BNO085 실시간 선형가속도 측정
- MCU에서 FPGA로 센서 UART 패킷 전송
- FPGA PWM 기반 모터 제어
- FPGA 하드웨어 진동 인터록
- 7-segment 및 LED 상태 표시
- PC 실시간 그래프와 CSV 저장

### 시간 여유 시 추가

- SPC 관리도
- Isolation Forest 이상탐지
- DRV8833 Fault 입력
- RISC-V MMIO와 이동평균 펌웨어
- FPGA의 BNO085 직접 통신
- 1D CNN 모델 비교

## 13. 포트폴리오 표현

> BNO085 선형가속도 데이터를 이용해 모터 설비의 진동 상태를 수집하고, iCE40 FPGA에서 PWM 구동과 실시간 임계값 인터록을 구현했다. 정상 데이터 기반 SPC 및 Isolation Forest 조기 경고를 PC 대시보드에 통합했으며, CPU·AI 오류와 관계없이 FPGA가 모터 출력을 직접 차단하는 Fail-safe 구조를 검증했다.
