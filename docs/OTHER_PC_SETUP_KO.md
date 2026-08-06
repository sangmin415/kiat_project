# 다른 PC에서 실행하기

이 문서는 FPGA에 이미 `pcservo` 비트스트림을 올린 뒤, 다른 Windows 또는 Linux PC에서 Pygame 대시보드를 실행하는 방법이다.

## 1. 공통 준비

```bash
git clone https://github.com/sangmin415/kiat_project.git
cd kiat_project
```

대시보드는 Python 3.10 이상, `pygame`, `pyserial`이 필요하다.

## 2. Windows

PowerShell에서:

``powershell
py -3 -m pip install -r requirements.txt
py -3 -m serial.tools.list_ports
scripts\run_dashboard_windows.bat COM11
```

마지막 줄의 `COM11`은 두 번째 명령에서 보인 FPGA USB Serial 포트로 바꾼다.

## 3. Linux / Purdue lab PC

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m serial.tools.list_ports
bash scripts/run_dashboard_linux.sh /dev/ttyUSB1
```

`/dev/ttyUSB1`은 예시다. USB를 다시 연결하면 `ttyUSB0`, `ttyUSB1`, `ttyUSB2`처럼 번호가 바뀔 수 있으므로 `python -m serial.tools.list_ports` 결과를 우선한다.

## 4. WSL을 쓰는 Windows PC

GUI를 보려면 WSLg 또는 X 서버가 필요하다. FPGA FTDI를 WSL에 연결한 뒤:

``powershell
usbipd list
usbipd attach --wsl --busid <FPGA BUSID>
```

그 다음 Ubuntu에서 Linux 절차와 동일하게 실행한다. 프로그래밍에는 `iceprog -S`가 FTDI를 사용하므로, 업로드 중에는 GUI를 종료한다.

## 5. 실행 확인

- 화면 상단에 `PC CONTROL: <port>`가 표시된다.
- BNO085을 움직이면 Roll/Pitch/Yaw 수치와 중심 평면이 변한다.
- 보드 키패드 **B** 또는 PC 키보드 **Z**를 누르면 영점이 설정된다.
- GUI의 `R0/R1/R2` PWM 값이 변하면 PC -> FPGA 명령 송신은 동작 중이다.

## 6. 하드웨어 연결 요약

- BNO085 UART-RVC: FPGA C3 / J6 I0
- PC UART: FPGA B10(RX), B12(TX)
- R0/R1/R2 PWM: B2/D1/H1
- 서보 red: 별도 5V, black/brown: 별도 GND, yellow/orange: R0/R1/R2
- **외부 5V GND와 FPGA GND는 반드시 공통 연결**

서보 전원을 FPGA 3.3V에서 공급하면 안 된다.
