# FPGA-RISC-V Photo Process Interlock

FPGA와 RISC-V CPU, PC 기반 이상 탐지를 결합해 포토 공정 마스크 스테이지의 **위치 오차·진동 이상·비정상 이벤트**를 모사하고 감시하는 프로젝트입니다.

> 이 프로젝트는 실제 ESD 계측기나 마스크 결함 검사 장비가 아닙니다. 로터리 엔코더와 버튼, 가속도 센서를 이용해 공정 설비에서 발생할 수 있는 위치 오차·진동·비정상 이벤트를 모사하는 교육용 데모입니다.

## 1. 프로젝트 목표

- 로터리 엔코더로 마스크 스테이지의 상대 위치 오차 모사
- ADXL345 가속도 센서로 장비 진동 데이터 수집
- 이벤트 버튼으로 ESD와 같은 비정상 이벤트 상황 모사
- FPGA 하드웨어가 임계치 초과를 즉시 감지해 인터록 수행
- RISC-V CPU가 MMIO로 설비 상태를 읽고 UART로 PC에 전송
- PC 대시보드가 FDC 형태의 실시간 그래프와 이벤트 로그 표시
- Isolation Forest가 정상 패턴에서 벗어난 이상 징후를 조기 경고

## 2. 시스템 구조

```text
로터리 엔코더 ── 위치 변화 ──┐
ADXL345 ─────── X/Y/Z 진동 ──┼──> FPGA RTL
이벤트 버튼 ── 비정상 이벤트 ┘      ├─ 입력 동기화 및 디바운스
                                   ├─ 엔코더 디코딩
                                   ├─ 센서 샘플 수집
                                   ├─ 이벤트 래치
                                   ├─ 임계치 비교
                                   └─ 즉시 인터록
                                            │ MMIO
                                            v
                                      RISC-V CPU
                                   상태 읽기 및 UART 전송
                                            │
                                            v
                                         PC 대시보드
                                   실시간 그래프 및 AI 경고

FPGA 인터록 출력 ──> LED / 부저 / 모터 드라이버 Enable OFF
```

## 3. 역할 분담

| 구성 | 역할 |
|---|---|
| FPGA RTL | 빠른 입력 감시, 이벤트 래치, 임계치 비교, 즉시 인터록 |
| RISC-V CPU | MMIO 상태 읽기, 상태 패킷 구성, UART 전송 |
| PC AI | 정상 패턴 학습, 위치·진동 이상 징후 판정 |
| PC 대시보드 | 실시간 그래프, 상태 표시, 이벤트 로그 저장 |

AI 또는 CPU가 응답하지 않아도 하드웨어 임계치를 넘으면 FPGA가 독립적으로 인터록을 수행하도록 설계합니다.

## 4. 대상 하드웨어

- Lattice iCE40HX-8K Breakout Board
- iCE40HX8K-CT256 FPGA
- 12 MHz 온보드 클록
- 3.3 V GPIO
- J2 2x20 사용자 헤더
- 온보드 LED 8개

### 추가 부품

- 로터리 엔코더 1개
- 이벤트 버튼 및 리셋 버튼
- ADXL345 3축 가속도 센서 모듈
- 패시브 부저
- 브레드보드 및 점퍼선
- 선택: 소형 DC 모터와 3.3 V 로직 호환 모터 드라이버

모터는 FPGA GPIO에 직접 연결하지 않고 별도 모터 드라이버의 Enable 입력만 제어합니다.

## 5. 상태 및 인터록

| 상태 | 조건 | 동작 |
|---|---|---|
| `NORMAL` | 위치·진동이 정상 범위 | 정상 LED, 모터 Enable 유지 |
| `WARNING` | 경고 기준 이상, 인터록 기준 미만 | 경고 LED 및 느린 부저 |
| `AI WARNING` | PC 모델이 정상 패턴 이탈 감지 | 대시보드 경고 및 로그 저장 |
| `INTERLOCK` | 위치 임계치 초과, 강한 충격 또는 이벤트 발생 | 빨간 LED, 빠른 부저, 모터 Enable 차단 |

AI 판정만으로 안전 출력을 차단하지 않습니다. 즉시 차단 조건은 FPGA RTL에 구현합니다.

## 6. FPGA 구현 계획

```text
rtl/
  top_interlock.sv
  encoder_decoder.sv
  button_sync_debounce.sv
  event_latch.sv
  vibration_monitor.sv
  interlock_controller.sv
  warning_buzzer.sv
  uart_tx.sv
  mmio_interlock.sv

tb/
  encoder_decoder_tb.sv
  event_latch_tb.sv
  interlock_controller_tb.sv
  uart_tx_tb.sv
  top_interlock_tb.sv
```

부품이 도착하기 전에는 테스트벤치가 엔코더 A/B상, 버튼 바운스, 위치 오차, 진동 샘플을 가상 입력으로 생성합니다.

### 우선 검증 항목

- 엔코더 정방향·역방향 카운트
- 버튼 바운스가 이벤트 한 번으로 처리되는지 확인
- 이벤트 상태가 리셋 전까지 유지되는지 확인
- 위치 또는 진동 임계치 초과 시 인터록 발생
- 인터록 시 부저·LED·모터 Enable 출력 확인
- 리셋 후 정상 상태 복귀
- UART 패킷과 전송 타이밍 검증
- iCE40HX-8K 합성 및 자원 사용량 확인

## 7. RISC-V 및 MMIO 계획

초기 구현은 인터럽트와 C 런타임 없이 RV32I 어셈블리 polling 방식으로 진행합니다.

```text
0x8000_0000 : POSITION_ERROR  (read)
0x8000_0004 : EVENT_STATUS    (read)
0x8000_0008 : VIBRATION_LEVEL (read)
0x8000_000C : INTERLOCK       (read)
0x8000_0010 : THRESHOLD       (read/write)
0x8000_0014 : CONTROL         (write)
0x8000_0018 : UART_TX         (write)
```

CPU 통합 전에도 FPGA 단독 인터록과 UART 송신이 동작하는 MVP를 먼저 완성합니다. RISC-V 통합은 CPU 검증이 완료된 뒤 추가합니다.

## 8. PC 대시보드와 AI

UART는 초기 안정성을 위해 9,600 bps로 시작하고 약 100 ms마다 상태를 전송합니다.

```text
time_ms,position_error,vibration_level,event_latched,interlock
1200,2,7,0,0
1300,5,10,0,0
1400,11,28,0,1
```

대시보드는 다음을 표시합니다.

- 위치 오차 실시간 그래프
- X/Y/Z 진동 및 진동 수준 그래프
- 경고·인터록 기준선
- `NORMAL`, `WARNING`, `AI WARNING`, `INTERLOCK` 상태
- 이벤트 발생 시간과 원인
- CSV 로그 저장

AI는 노트북 CPU에서 동작하는 Isolation Forest를 사용합니다. 1초 구간마다 다음 특징을 계산합니다.

- 평균 및 최대 위치 오차
- 위치 변화량과 방향 전환 횟수
- 진동 RMS, 표준편차, 최댓값
- 이벤트 발생 여부

AI는 조기 경고를 담당하고 FPGA 하드웨어 인터록은 독립적으로 유지합니다.

## 9. 구현 우선순위

### MVP

1. 엔코더와 이벤트 버튼의 가상 입력 테스트벤치
2. FPGA 위치 카운터·이벤트 래치·인터록
3. LED·부저·모터 Enable 출력
4. UART 송신
5. PC 실시간 그래프

### 확장

6. ADXL345 실제 센서 연결
7. Isolation Forest 이상 징후 경고
8. RISC-V MMIO 및 UART 연동
9. 실제 모터 드라이버 Enable 제어

## 10. 5일 구현 일정

| 일차 | 목표 | 완료 기준 |
|---|---|---|
| 1일차 | 엔코더·버튼·인터록 RTL 및 테스트벤치 | 모든 기본 테스트 통과 |
| 2일차 | UART 송신과 PC 가상 FDC 대시보드 | 가상 데이터 실시간 표시 |
| 3일차 | FPGA 보드 합성·LED·부저 검증 | 보드 출력 정상 동작 |
| 4일차 | ADXL345·AI 또는 RISC-V 연동 | 핵심 확장 기능 하나 이상 완료 |
| 5일차 | 통합 시연, 로그, 문서 및 영상 | 정상·경고·인터록 시나리오 재현 |

## 11. 시연 시나리오

1. 정상 위치·진동에서 `NORMAL` 상태를 확인합니다.
2. 엔코더를 천천히 이동해 `WARNING` 상태를 발생시킵니다.
3. 엔코더를 빠르게 앞뒤로 움직이거나 진동을 가해 `AI WARNING`을 확인합니다.
4. 임계치를 넘기거나 이벤트 버튼을 누르면 FPGA가 즉시 `INTERLOCK`을 수행합니다.
5. LED와 부저, 모터 Enable 차단을 확인합니다.
6. PC 그래프와 CSV 로그에서 발생 시점과 원인을 확인합니다.

## 12. 현재 상태

- 프로젝트 범위 및 시스템 구조 확정
- iCE40HX-8K 보드 문서와 3.3 V GPIO 조건 확인
- FPGA 시뮬레이션·합성 도구 확인
- 하드웨어 부품 주문 전
- RTL, 테스트벤치, PC 프로그램은 이후 단계에서 구현 예정
