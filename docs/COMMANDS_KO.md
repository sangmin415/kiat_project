# 테스트벤치 명령어 모음집

부품 없이 `interlock_controller` 테스트벤치만 실행할 때 사용하는 명령어다.

## 가장 빠른 실행

Linux 터미널에서:

```bash
git clone https://github.com/sangmin415/kiat_project.git
cd kiat_project
make test
```

이미 리포를 받은 경우:

```bash
cd kiat_project
git pull
make clean
make test
```

명령이 오류 없이 종료되면 테스트벤치가 통과한 것이다. 실패하면 `$fatal`과 실패한 상태 이름이 출력된다.

## 필요한 도구 설치 - Ubuntu

```bash
sudo apt update
sudo apt install -y git make iverilog gtkwave
```

설치 확인:

```bash
iverilog -V
vvp -V
gtkwave --version
```

## Makefile 없이 직접 실행

```bash
mkdir -p build
iverilog -g2012 \
  -o build/interlock_tb \
  rtl/interlock_controller.sv \
  tb/interlock_controller_tb.sv
vvp build/interlock_tb
```

## 파형 열기

테스트 실행 후 다음 파일이 생성된다.

```text
build/interlock_controller.vcd
```

GTKWave 실행:

```bash
gtkwave build/interlock_controller.vcd
```

확인할 신호:

- `vibration_level`: 가상 진동값
- `transient_event`: ESD_SIM 이벤트 입력
- `state`: `0=NORMAL`, `1=WARNING`, `2=INTERLOCK`
- `warning`: 경고 출력
- `interlock`: 차단 출력
- `motor_enable`: 모터 구동 허가
- `event_latched`: ESD_SIM 이벤트 래치

## 테스트 시나리오 순서

1. Reset
2. 진동값 5 - NORMAL, motor_enable=1
3. 진동값 30 - WARNING, motor_enable=1
4. 진동값 70 - INTERLOCK, motor_enable=0
5. 진동값을 5로 내려도 INTERLOCK 유지
6. Reset 후 NORMAL 복귀
7. ESD_SIM 이벤트 입력 후 INTERLOCK 및 event_latched=1

## Windows에서 WSL로 실행

PowerShell에서:

```powershell
wsl -d Ubuntu-24.04
cd /mnt/c/Users/<Windows사용자명>/kiat_project
make clean
make test
```

리포를 WSL 홈에 복제했다면:

```bash
cd ~/kiat_project
make clean
make test
```

Windows 경로에 한글이나 공백이 있어 문제가 발생하면 WSL 홈 경로에서 실행하는 방법을 권장한다.

## 자주 발생하는 오류

### `iverilog: command not found`

```bash
sudo apt install -y iverilog
```

### VCD 파일이 없음

먼저 `make test`가 성공했는지 확인한다.

```bash
ls -lh build/interlock_controller.vcd
```

### 이전 빌드가 남아 이상하게 동작함

```bash
make clean
make test
```

### 테스트 실패 위치 확인

```bash
vvp build/interlock_tb | tee testbench.log
```

그다음 `testbench.log`에서 `$error`, `FATAL`, 상태 이름을 확인한다.
