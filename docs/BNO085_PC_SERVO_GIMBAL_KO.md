# BNO085 PC 제어 3축 짐벌 가이드

## 데이터 흐름

1. BNO085가 UART-RVC Roll/Pitch/Yaw를 FPGA C3으로 보낸다.
2. FPGA가 checksum을 확인하고 원시 RVC 프레임을 B12 UART로 PC에 전달한다.
3. PC가 영점 기준을 빼고 PWM tick을 계산한다.
4. PC가 B10 UART를 통해 PWM command를 FPGA에 보낸다.
5. FPGA가 checksum과 timeout을 확인한 뒤 R0/B2, R1/D1, R2/H1에 50Hz PWM을 출력한다.

## 영점

- PC 창에서 Z 키를 누르면 영점이 잡힌다.
- 보드의 키패드 B를 누르면 FPGA가 55 5A 42 F1 control event를 PC에 보낸다.
- PC가 그 event를 받았을 때의 Roll/Pitch/Yaw를 영점으로 저장한다.
- B 버튼 핀은 A6이며 A 키는 사용하지 않는다.

## PC to FPGA command

```text
55 A5 R0_H R0_L R1_H R1_L R2_H R2_L CHECKSUM
```

Checksum은 R0_H부터 R2_L까지 6바이트의 8-bit sum이다. 18000 tick은 12MHz 기준 1.5ms이고, FPGA는 13200~22800 tick만 허용한다. PC command가 100ms 이상 없거나 센서가 timeout되면 FPGA가 세 축을 중립으로 복귀시킨다.

## 실행

```bash
make -f Makefile.pcservo pcservo-test
make -f Makefile.pcservo pcservo-lint
make -f Makefile.pcservo pcservo-bitstream
make -f Makefile.pcservo pcservo-cram
python3 pc/bno085_rvc_dashboard.py --simulate
python3 pc/bno085_rvc_dashboard.py --port /dev/ttyUSB1 --baud 115200
```

서보는 외부 5V로만 공급하고, 외부 GND와 FPGA GND는 반드시 공통 연결한다.
