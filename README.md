# BNO085 + PC 제어 3축 짐벌 MVP

BNO085 자세 센서와 iCE40HX8K FPGA, PC Pygame 대시보드로 구성한 3축 짐벌 데모입니다.

```text
BNO085 UART-RVC -> FPGA UART/RVC parser -> PC Pygame dashboard
                                                |
                                 PC calculates R0/R1/R2 PWM
                                                |
                                      UART -> FPGA PWM
                                                |
                                          SG90/MS18 x3
```

현재 버전은 RV32I CPU를 사용하지 않습니다. FPGA는 UART 수신/전달, 50 Hz PWM 생성, checksum, sensor/command timeout fail-safe를 맡고, PC는 영점·각도→PWM 계산과 시각화를 맡습니다.

## 기능

- BNO085 UART-RVC 115200 bps 수신 및 checksum 확인
- PC Pygame 실시간 Roll/Pitch/Yaw·진동 그래프
- 중앙 3축 자세 뷰: R0 Roll, R1 Pitch, R2 Yaw와 현재 기울기만 표시
- PC 키보드 **Z** 또는 FPGA 키패드 **B** 영점 설정
- PC -> FPGA 3채널 PWM 명령 checksum 검증
- 50 Hz 서보 PWM, 센서/명령 timeout 시 1.5 ms 중립 복귀
- 다른 PC에서 포트만 지정해 실행 가능

## 저장소 구성

| 경로 | 내용 |
|---|---|
| `rtl/` | iCE40 UART, RVC parser, PWM, FPGA top |
| `pc/bno085_rvc_dashboard.py` | PC 대시보드와 각도→PWM 제어 |
| `constraints/` | iCE40HX8K 핀 제약 |
| `requirements.txt` | PC 실행 의존성 |
| `scripts/` | Windows/Linux 실행 스크립트 |
| `docs/OTHER_PC_SETUP_KO.md` | 다른 PC 배포·실행 가이드 |

## 빠른 시작

### Windows

``powershell
git clone https://github.com/sangmin415/kiat_project.git
cd kiat_project
py -3 -m pip install -r requirements.txt
py -3 -m serial.tools.list_ports
scripts\run_dashboard_windows.bat COM11
```

### Linux / Purdue lab PC

```bash
git clone https://github.com/sangmin415/kiat_project.git
cd kiat_project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m serial.tools.list_ports
bash scripts/run_dashboard_linux.sh /dev/ttyUSB1
```

`COM11`, `/dev/ttyUSB1`은 예시입니다. 실제 포트는 `python -m serial.tools.list_ports` 출력으로 확인합니다.

> FPGA 비트스트림 업로드는 별도입니다. FPGA가 이미 `pcservo` 비트스트림으로 프로그램된 상태에서 위 GUI를 실행합니다.

## FPGA 빌드 및 CRAM 업로드

iCE40 도구가 설치된 Linux/WSL에서:

```bash
make -f Makefile.pcservo pcservo-test
make -f Makefile.pcservo pcservo-bitstream
make -f Makefile.pcservo pcservo-cram
```

`pcservo-cram`은 전원을 끄면 사라지는 임시 업로드입니다.

## 핀 및 전원

| 기능 | 핀 |
|---|---|
| BNO085 UART-RVC | C3 / J6 I0 |
| PC UART RX/TX | B10 / B12 |
| 키패드 B 영점 | A6 |
| R0/R1/R2 PWM | B2 / D1 / H1 |
| Green status LED | T9 |

서보는 **외부 5V**를 사용합니다. red는 +5V, black/brown은 외부 GND, yellow/orange는 R0/R1/R2입니다. 외부 GND와 FPGA GND는 반드시 공통 연결합니다.

## 문서

- [다른 PC에서 실행하기](docs/OTHER_PC_SETUP_KO.md)
- [PC 제어 짐벌 상세 가이드](docs/BNO085_PC_SERVO_GIMBAL_KO.md)
