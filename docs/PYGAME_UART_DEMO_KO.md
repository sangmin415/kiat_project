# Pygame UART FPGA 데모 사용 가이드

이 문서는 센서와 모터가 아직 없는 상태에서 **Windows PC + Purdue ECE270 iCE40HX8K FPGA 보드**만으로 실행하는 하드웨어 인 더 루프(HIL) 데모의 사용법을 설명합니다.

## 1. 현재 데모에서 실제인 것과 가상인 것

### 실제 동작

- Windows PC와 FPGA 사이의 COM12 UART 송수신
- Pygame 버튼에서 FPGA로 보내는 제어 명령
- FPGA 내부의 NORMAL, WARNING, INTERLOCK 상태 결정
- 진동 이상 및 ESD_SIM 이벤트 래치
- FPGA의 motor enable 논리 출력
- 보드 RGB LED, 일반 LED, 7-segment 상태 표시
- Pygame의 200 ms 주기 FPGA 상태 조회

### 현재 시뮬레이션인 것

- BNO085의 X/Y/Z 가속도 데이터
- 진동 수치와 이동 평균 그래프
- 화면 속 편심 모터 회전과 구형 테스트 리그의 흔들림
- PWM 요청값에 따른 진동 크기

따라서 현재 데모는 **센서 측정 데모가 아니라 PC 명령 → UART → FPGA 안전 FSM → UART 상태 응답 → PC 시각화의 전체 제어 흐름을 검증하는 데모**입니다.

## 2. 실행 전 확인

- FPGA 보드를 USB로 Windows PC에 연결합니다.
- 장치 관리자에서 UART 포트를 확인합니다. 현재 기본값은 COM12입니다.
- COM12를 사용하는 다른 Python 프로그램, 시리얼 터미널, PuTTY 등을 모두 닫습니다.
- FPGA 전원을 뺐다가 다시 연결했다면 CRAM 설정이 사라질 수 있으므로 4장의 업로드 과정을 다시 수행합니다.

## 3. Python 패키지 설치

PowerShell에서 저장소로 이동합니다.

```powershell
cd C:\kiat_project
```

현재 PC에서는 `python` 명령이 PATH에 없으므로 다음과 같이 Python 실행 파일의 전체 경로를 사용합니다.

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" -m pip install pygame pyserial
```

설치 확인:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" -c "import pygame, serial; print('PYTHON_DEPENDENCIES_PASS')"
```

## 4. FPGA RTL 검증 및 업로드

### 4.1 테스트벤치

Purdue Linux PC 또는 WSL에서 실행합니다.

```bash
cd /mnt/c/kiat_project
make clean
make test_command
```

정상 결과:

```text
PASS: top_board_uart_demo_tb
```

전체 테스트는 다음 명령으로 실행합니다.

```bash
make test
```

### 4.2 비트스트림 생성

```bash
make bitstream
```

정상적으로 완료되면 `build/interlock_demo.bin`이 생성됩니다.

### 4.3 CRAM 업로드

보드 USB가 WSL에 연결된 상태에서 실행합니다.

```bash
iceprog -t
iceprog -S build/interlock_demo.bin
```

성공 기준:

```text
programming..
cdone: high
Bye.
```

CRAM 업로드는 휘발성입니다. 보드 전원을 끄거나 USB를 뽑으면 다시 업로드해야 합니다.

Windows에서 WSL로 USB를 넘겼다면 업로드 후 다시 Windows로 반환해야 COM12가 나타납니다.

```powershell
& "C:\Program Files\usbipd-win\usbipd.exe" detach --busid 1-2
```

BUSID는 PC 환경에 따라 달라질 수 있으므로 먼저 확인할 수 있습니다.

```powershell
& "C:\Program Files\usbipd-win\usbipd.exe" list
```

## 5. UART 명령 기능 실물 검사

Pygame을 실행하기 전에 다음 검사를 권장합니다.

```powershell
cd C:\kiat_project
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" .\pc\uart_command_test.py --port COM12
```

정상 결과 예시:

```text
RESET/STOPPED          status=0x81
NORMAL/RUNNING         status=0xA0
WARNING/RUNNING        status=0xA4
VIBRATION/INTERLOCK    status=0x88
RESET/STOPPED          status=0x81
ESD/INTERLOCK          status=0xC8
FINAL RESET/STOPPED    status=0x81
UART_COMMAND_HARDWARE_PASS
```

이 테스트 프로그램과 Pygame은 COM12를 동시에 사용할 수 없습니다. 테스트가 끝난 뒤 Pygame을 실행합니다.

## 6. Pygame 실행

### FPGA 실물 연동 모드

```powershell
cd C:\kiat_project
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" .\pc\pygame_demo.py --port COM12
```

오른쪽 위에 `FPGA ONLINE`이 표시되고 상태 창의 UART LINK가 `COM12 / 115200`이면 실물 연동 상태입니다.

### FPGA 없는 화면 전용 모드

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" .\pc\pygame_demo.py --demo
```

이 모드는 UART를 열지 않으며 화면에 `DEMO MODE`가 표시됩니다.

### 자동 종료 스모크 테스트

예를 들어 30프레임만 실행하고 종료하려면:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" .\pc\pygame_demo.py --demo --smoke-test 30
```

## 7. 버튼과 키보드 사용법

| 화면 버튼 | 키 | UART | 동작 |
|---|---:|---:|---|
| RUN NORMAL | N | `0x10` | 정상 운전 상태, 요청 PWM 40% |
| WARNING | W | `0x11` | 경고 수준 모사, 요청 PWM 65% |
| STRONG VIB | V | `0x12` | 강진동을 모사하고 FPGA 인터록 발생 |
| ESD_SIM | E | `0x13` | 안전한 가상 ESD 이벤트를 발생시키고 래치 |
| RANDOM | A | - | NORMAL 시작 후 3~7초 사이에 진동 또는 ESD_SIM을 무작위로 1회 발생 |
| RESET | R | `0x14` | 인터록과 ESD 래치를 해제한 뒤 STOPPED 유지 |
| STOP | S | `0x15` | 운전자 정지, motor enable 비활성화 |

인터록은 래치되므로 STRONG VIB 또는 ESD_SIM 이후에는 RESET을 먼저 누른 뒤 RUN NORMAL을 눌러야 합니다.

## 8. 권장 시연 순서

1. 프로그램 실행 후 `FPGA ONLINE`과 `STOPPED`를 확인합니다.
2. **RUN NORMAL**을 누릅니다.
   - 화면 상태: NORMAL
   - MOTOR ENABLE: ON
   - 보드 정상 LED 활성화
   - 화면 속 회전체가 정상 속도로 동작
3. **WARNING**을 누릅니다.
   - 화면 상태: WARNING
   - MOTOR ENABLE: ON
   - 경고 LED 활성화
   - 진동 그래프 크기 증가
4. **RESET**을 누른 다음 **RUN NORMAL**을 다시 누릅니다.
5. **STRONG VIB**을 누릅니다.
   - 화면 상태: INTERLOCK
   - MOTOR ENABLE: OFF
   - TRIP REASON: VIBRATION_SIM
   - FPGA 빨간 LED와 7-segment 인터록 표시
6. **RESET** 후 **RUN NORMAL**을 누릅니다.
7. **ESD_SIM**을 누릅니다.
   - 화면 상태: INTERLOCK
   - ESD EVENT: LATCHED
   - MOTOR ENABLE: OFF
   - 7-segment에 E 표시
8. **RESET**으로 안전 상태에 복귀합니다.
9. 마지막으로 **RANDOM**을 눌러 3~7초 사이의 예측 불가능한 고장 주입을 시연합니다.

## 9. 화면 구성

### ROTATING VIBRATION TEST RIG

- 파란 점: 편심 모터
- 초록 점: 향후 장착할 BNO085
- 회전 속도와 흔들림: 현재 PWM 및 가상 진동에 따른 시각 효과
- INTERLOCK 이후 motor enable이 꺼지면 관성처럼 서서히 감속

### REAL-TIME VIBRATION

- 금색 선: 가상 진동 수치
- 파란 선: 최근 12개 샘플의 이동 평균
- 샘플 주기: 100 ms
- BNO085 도착 전까지 이 그래프는 실제 센서 데이터가 아닙니다.

### FPGA LIVE STATUS

- SYSTEM STATE: FPGA에서 회신한 상태
- UART LINK: 실물 연결 여부
- MOTOR ENABLE: FPGA 안전 출력 상태
- ESD EVENT: 이벤트 래치 여부
- TRIP REASON: 진동 또는 ESD_SIM
- ACCEL XYZ, VIB / AVG: 현재는 가상 센서 데이터
- PWM REQ / APPLIED: 요청값과 FPGA motor enable을 반영한 적용값
- RECENT UART / CONTROL EVENTS: 송신 명령과 ACK 기록

## 10. UART 프로토콜

### PC → FPGA

| 바이트 | 명령 |
|---:|---|
| `0x10` | NORMAL |
| `0x11` | WARNING |
| `0x12` | VIBRATION TRIP |
| `0x13` | ESD_SIM TRIP |
| `0x14` | RESET 후 STOPPED |
| `0x15` | STOP |
| `0xF0` | 상태 조회 |

Pygame은 약 200 ms마다 `0xF0`을 전송합니다. 일반 명령은 FPGA가 같은 바이트를 ACK로 에코합니다.

### FPGA → PC 상태 바이트

| 비트 | 의미 |
|---:|---|
| 7 | 상태 응답 표시, 항상 1 |
| 6 | ESD 이벤트 래치 |
| 5 | motor enable |
| 4 | 예약 |
| 3:2 | FPGA 상태: 0 NORMAL, 1 WARNING, 2 INTERLOCK |
| 1 | 예약 |
| 0 | operator stop |

현재 대표 상태:

| 상태 | 바이트 |
|---|---:|
| STOPPED | `0x81` |
| NORMAL / RUNNING | `0xA0` |
| WARNING / RUNNING | `0xA4` |
| VIBRATION INTERLOCK | `0x88` |
| ESD INTERLOCK | `0xC8` |

## 11. 보드 표시

- 정상 운전: 초록 RGB LED
- WARNING: 파란 RGB LED
- INTERLOCK: 빨간 RGB LED
- STOPPED: 파란 RGB LED
- 진동 인터록: 7-segment 상태 문자 `L`
- ESD_SIM 인터록: 7-segment 상태 문자 `E`
- 비인터록 상태: 최근 UART 바이트를 하위 두 7-segment에 16진수로 표시
- 왼쪽 일반 LED: 최근 UART 수신 바이트
- 오른쪽 일반 LED: operator stop, UART TX busy, interlock, warning 상태

내장 버튼 기능:

| 버튼 | 기능 |
|---:|---|
| 0 | 인터록 리셋 |
| 1 | WARNING 입력 |
| 2 | 강진동 TRIP 입력 |
| 3 | ESD_SIM 입력 |

## 12. CSV 로그

실행 중 다음 파일에 로그가 저장됩니다.

```text
C:\kiat_project\logs\pygame_uart_demo.csv
```

기록 항목:

- time
- mode
- state
- motor_enable
- event_latched
- ax, ay, az
- vibration
- average
- pwm

프로그램을 실행할 때마다 파일을 새로 작성하므로 기존 로그가 필요하면 실행 전에 다른 이름으로 복사합니다.

## 13. 자주 발생하는 문제

### `python` 명령을 찾을 수 없음

전체 경로 명령을 사용합니다.

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" .\pc\pygame_demo.py --port COM12
```

### COM12 Access denied 또는 device busy

다른 프로그램이 COM12를 사용 중입니다.

```powershell
Get-Process python,pythonw -ErrorAction SilentlyContinue
```

기존 Pygame, UART 테스트 프로그램, 시리얼 터미널을 종료한 뒤 다시 실행합니다. 한 번에 하나의 프로그램만 COM12를 열 수 있습니다.

### FPGA ONLINE이 아니라 DEMO MODE로 표시됨

- FPGA USB 연결 상태를 확인합니다.
- 장치 관리자에서 실제 COM 번호를 확인합니다.
- COM 번호가 다르면 `--port COM번호`로 실행합니다.
- WSL에 USB가 연결된 상태라면 `usbipd detach`로 Windows에 반환합니다.
- Pygame 실행 중에는 자동 재연결하지 않으므로 창을 닫고 다시 실행합니다.

### UART는 연결되지만 상태가 이상함

GitHub 코드, FPGA 비트스트림, Pygame이 서로 다른 버전일 수 있습니다.

```powershell
cd C:\kiat_project
git pull origin main
```

그다음 `make clean`, `make test_command`, `make bitstream`을 실행하고 FPGA를 다시 프로그래밍합니다.

## 14. 종료

창의 닫기 버튼을 누르면 UART와 CSV 파일을 정상적으로 닫습니다. PowerShell에서 강제 종료해야 한다면 실행 중인 Python 프로세스를 확인한 뒤 해당 Pygame 프로세스만 종료합니다.
