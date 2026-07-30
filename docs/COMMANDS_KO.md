# 테스트벤치 및 FPGA 명령어 모음집

이 프로젝트의 Makefile은 Purdue ECE270 수업 템플릿의 도구 경로와 명령 형식을 따른다.

## 현재 위치 확인

터미널 경로가 이미 `~/Desktop/kiat_project`라면 리포 안에 들어와 있는 것이다.

```bash
pwd
```

이때는 `cd kiat_project`를 다시 실행하지 않는다. 바로 `git pull`과 `make`를 실행한다.

## 파형 시뮬레이터까지 자동 실행

가장 간단한 명령:

```bash
make sim
```

수업 템플릿의 원래 명명 방식:

```bash
make sim_interlock_controller_src
```

두 명령은 동일하게 다음 작업을 수행한다.

1. `rtl/interlock_controller.sv` 컴파일
2. `tb/interlock_controller_tb.sv` 실행
3. `build/interlock_controller.vcd` 생성
4. GTKWave로 파형 자동 열기

GTKWave 창을 닫으면 `make` 명령도 종료된다. 터미널에서 PASS 여부만 빠르게 확인하려면 다음을 사용한다.

```bash
make test
```

## 최신 코드로 실행

현재 리포 안에서:

```bash
git pull origin main
make clean
make sim
```

성공하면 터미널에 다음 문구가 표시되고 GTKWave가 열린다.

```text
PASS: interlock_controller_tb
```

## 수업식 lint

```bash
make vlint_interlock_controller
```

전체 보드 top까지 lint하려면:

```bash
make lint
```

## Purdue 도구 환경 확인

Makefile이 수업 템플릿과 같은 실습실 도구 경로를 자동으로 추가한다. 필요한 도구를 한 번에 확인한다.

```bash
make check_env
```

각 도구 옆에 실제 경로가 출력되어야 한다. `nextpnr-ice40`도 이 명령 안에서 수업용 경로에서 검색된다.

## 비트스트림 생성 및 FPGA 업로드

부품이 없어도 온보드 버튼과 7-segment만 사용하는 현재 데모는 업로드할 수 있다.

```bash
make clean
make bitstream
```

FPGA 연결 확인:

```bash
iceprog -t
```

휘발성 CRAM 업로드:

```bash
make cram
```

전원을 꺼도 유지되는 Flash 업로드:

```bash
make flash
```

처음에는 안전한 `make cram`을 권장한다.

## 직접 실행하는 방법

Makefile 문제를 분리해서 테스트할 때만 사용한다.

```bash
mkdir -p build
iverilog -g2012 \
  -o build/interlock_controller_tb \
  rtl/interlock_controller.sv \
  tb/interlock_controller_tb.sv
vvp build/interlock_controller_tb
gtkwave build/interlock_controller.vcd
```

## GTKWave에서 확인할 신호

- `vibration_level`: 가상 진동값
- `transient_event`: ESD_SIM 이벤트 입력
- `state`: `0=NORMAL`, `1=WARNING`, `2=INTERLOCK`
- `warning`: 경고 출력
- `interlock`: 차단 출력
- `motor_enable`: 모터 구동 허가
- `event_latched`: ESD_SIM 이벤트 래치

## 테스트 시나리오

1. Reset
2. 진동값 5: NORMAL, motor_enable=1
3. 진동값 30: WARNING, motor_enable=1
4. 진동값 70: INTERLOCK, motor_enable=0
5. 진동값을 5로 내려도 INTERLOCK 유지
6. Reset 후 NORMAL 복귀
7. ESD_SIM 이벤트 후 INTERLOCK 및 event_latched=1

## 자주 발생하는 오류

### `cd: kiat_project: No such file or directory`

이미 리포 안에 있으므로 `cd`를 다시 실행하지 않는다. `pwd`로 확인한다.

### `nextpnr-ice40: No such file or directory`

먼저 최신 Makefile을 받고 수업용 경로가 잡히는지 확인한다.

```bash
git pull origin main
make check_env
make clean
make bitstream
```

### GTKWave가 열리지 않음

```bash
make test
ls -lh build/interlock_controller.vcd
gtkwave build/interlock_controller.vcd
```

SSH 접속 환경이라면 그래픽 전달(X11)이 없어서 창이 표시되지 않을 수 있다. Purdue 랩 PC의 그래픽 데스크톱 터미널에서 실행한다.

### 이전 빌드가 남아 이상하게 동작함

```bash
make clean
make test
```
