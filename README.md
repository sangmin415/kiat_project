# BNO085 + RV32I 3축 능동 레벨링 / FDC 준비 프로젝트

iCE40HX8K FPGA 보드에서 **직접 구현한 RV32I RISC-V CPU**가 BNO085의 자세 데이터를 MMIO로 읽고, 3채널 서보 PWM 명령을 계산하는 3축 짐벌 MVP입니다.

현재 단계의 목표는 “카메라 짐벌”이 아니라, 반도체 웨이퍼 이송 스테이지의 기울어짐을 모사하는 **3축 능동 레벨링 플랫폼**을 만드는 것입니다. 이후에는 BNO085 가속도 로그를 PC에서 분석해 SPC·Isolation Forest 기반 FDC로 확장합니다.

> 안전한 표현: 실제 반도체 장비를 제어하거나 실제 ESD를 측정하는 시스템이 아닙니다. BNO085, SG90/MS18급 서보, 3D 프린트 짐벌을 사용한 교육·포트폴리오용 모사 시스템입니다.

## 현재 아키텍처

```text
BNO085 UART-RVC 115200 bps
       │  (SDA pin used as RVC TX)
       ▼
iCE40HX8K FPGA
 ├─ UART RX + RVC packet parser (RTL)
 ├─ RV32I custom CPU
 │   └─ MMIO read → fixed-point P control / A-button zero capture
 ├─ 50 Hz PWM generator (R0/R1/R2)
 └─ RVC UART forwarder → PC
                         │
                         ▼
                 Pygame monitor / future FDC
```

- RTL은 수신·패킷 파싱·PWM 타이밍·timeout 안전 동작을 담당합니다.
- RV32I 펌웨어는 각도(centidegree)를 정수로 읽어 세 축의 PWM 명령을 갱신합니다.
- PC는 원시 UART-RVC 프레임을 시각화합니다. PC AI는 추후 경고용이며, 안전 차단 역할을 맡지 않습니다.

## 구현 상태

| 항목 | 상태 |
|---|---|
| BNO085 UART-RVC 파서, UART forwarder | 구현 |
| RV32I MMIO + 정수 제어 펌웨어 | 구현 |
| R0/R1/R2 50 Hz PWM | 구현 |
| A 키패드 영점 캡처 (서보 기준값) | 구현 |
| sensor timeout 시 1.5 ms 중립 PWM | 구현 |
| Pygame UART-RVC 대시보드 | 구현 |
| iCE40 합성·배치·배선·12 MHz 타이밍 | 통과한 기준 소스 반영 |
| 실물 3축 기구 조립·튜닝 | 진행 전 |
| PID(I/D 포함), AI FDC | 다음 단계 |

현재 펌웨어는 완전한 PID가 아니라 안전하게 범위를 제한한 **고정소수점 비례(P) 제어 MVP**입니다. 3D 프린트 짐벌과 서보 혼 결합 후 기구 방향에 맞춰 각 축 부호와 gain을 튜닝해야 합니다.

## 빠른 시작: WSL 빌드·업로드

수업용 RV32I 코어가 `/mnt/c/2132132/riscvmove`에 있을 때:

```bash
cd /mnt/c/kiat_project
make -f Makefile.gimbal gimbal-bitstream RISCVMOVE_ROOT=/mnt/c/2132132/riscvmove
make -f Makefile.gimbal gimbal-cram      RISCVMOVE_ROOT=/mnt/c/2132132/riscvmove
```

`gimbal-cram`은 **일시적 SRAM(CRAM) 업로드**입니다. USB/보드 전원이 끊기면 사라집니다. Flash 업로드는 보드 점퍼를 올바르게 설정한 뒤에만 다음을 사용합니다.

```bash
make -f Makefile.gimbal gimbal-flash RISCVMOVE_ROOT=/mnt/c/2132132/riscvmove
```

## Pygame 대시보드

의존성:

```bash
sudo apt install python3-pygame python3-serial
```

시뮬레이션:

```bash
python3 pc/bno085_rvc_dashboard.py --simulate
```

실물 FPGA UART:

```bash
python3 pc/bno085_rvc_dashboard.py --port /dev/ttyUSB1 --baud 115200
```

Windows 직접 연결 환경이라면 `--port COM11`처럼 바꿉니다. FPGA의 실제 포트는 `ls /dev/ttyUSB*` 또는 Windows Device Manager로 확인해야 합니다.

## 문서와 소스

- [3축 BNO085/RV32I 짐벌 구현·배선·검증 가이드](docs/BNO085_RISCV_3AXIS_GIMBAL_KO.md)
- [기존 단일 모터 인터록 계획의 전환 안내](docs/BNO085_MOTOR_INTERLOCK_PLAN_KO.md)
- `rtl/top_riscv_bno_3axis_cpu.sv`: 전체 FPGA/RV32I top
- `firmware/bno085_3axis_cpu.c`: CPU에서 실행되는 정수 제어 펌웨어
- `constraints/bno085_3axis_cpu.pcf`: 현재 보드 핀맵
- `Makefile.gimbal`: WSL/Purdue toolchain 빌드·CRAM·Flash 명령
- `pc/bno085_rvc_dashboard.py`: 실시간 Pygame 대시보드

기존 `rtl/interlock_*.sv`, 기존 `Makefile`, ADXL345/ESD 데모 코드는 과거 인터록 실습 자산으로 남겨 두었습니다. 현재 3축 짐벌 빌드는 `Makefile.gimbal`을 사용합니다.
