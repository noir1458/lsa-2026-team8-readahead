# 실행 환경

측정에 쓴 VM, 커널, 설정을 적는다. 결과 CSV는 이 폴더에 있다.

## VM

| 항목 | 값 |
|---|---|
| 가상화 | VirtualBox 게스트 (게스트 확장 7.2.16), 호스트는 Windows |
| OS | Ubuntu 20.04.6 LTS, x86_64 |
| CPU, 메모리 | vCPU 2개, 3.8 GiB |
| 컴파일러 | gcc 9.4.0 |

## 커널

| 이름 | `uname -r` | 내용 |
|---|---|---|
| B0 | `5.4.214-b0` | kernel.org의 `linux-5.4.214.tar.xz` 그대로 |
| P1 | `5.4.214-p1` | B0 소스에 `patches/p1-readahead-marker.patch` 적용 |

- 소스 압축 파일의 SHA-256: `9abc79b4808c827eb82f8a44313ce6d3ade255949989bb98c11acda7ca3bc5db` (kernel.org 공식 값과 일치)
- 두 커널은 같은 소스 폴더에서 같은 설정으로 빌드했다. 설정 파일의 차이는 `CONFIG_LOCALVERSION` 한 줄이다.
- 설정은 수업 과제 때 쓰던 5.4.214 설정에서 출발해, `make localmodconfig`로 로드된 모듈만 남기고(82개) `CONFIG_DEBUG_INFO`를 껐다. B0의 설정 파일은 `config-5.4.214-b0`이다.
- B-tuned는 별도 커널이 아니다. B0 커널에서 테스트 디스크의 `read_ahead_kb`만 32 또는 16으로 줄인 조건이다.

## 테스트 디스크와 파일

| 항목 | 값 |
|---|---|
| 디스크 | `/dev/sdb`, 2 GiB 가상 디스크, ext4 |
| 마운트 | `/mnt/ext4-lab`, 읽기 전용 |
| read_ahead_kb | 128 (기본값, 32페이지) |
| I/O 스케줄러 | mq-deadline |
| 파일 | `assignment8/fio-test.0.0`, 939,524,096바이트(896 MiB), extent 5개 |
| 파일 SHA-256 | `528ca462137c7541d34ba4c875895fb9fb23665a7e4607232f999c312da05836` |

파일은 수업 과제 8에서 fio가 만든 것을 읽기만 한다.

## 측정 방법

- 매 실행 전에 `sync; echo 3 > /proc/sys/vm/drop_caches`
- 4 KiB 단위 `pread`, 단일 프로세스
- 읽은 양은 `/proc/self/io`의 `read_bytes`, 시간은 `CLOCK_MONOTONIC`
- burst 패턴은 N페이지를 읽고 1 MiB를 건너뛰기를 500회 반복한다. 순차 패턴은 파일 전체를 읽는다.
- 커널마다 한 번 부팅해서 잰다. 부팅 후 4분이 지나고 1분 평균 부하가 0.6 아래일 때 시작한다.

## 측정 기록 (2026-11-15)

| 파일 | 커널 | 조건 | 반복 |
|---|---|---|---|
| `step2_5.4.214-SEOJUNGMIN+.csv` | 5.4.214-SEOJUNGMIN+ | 2단계 확인. burst를 기본 설정과 `POSIX_FADV_RANDOM`으로 | 3 |
| `compare_B0_5.4.214-b0.csv` | 5.4.214-b0 | B0, read_ahead_kb 128 | 5 |
| `compare_Btuned32_5.4.214-b0.csv` | 5.4.214-b0 | B-tuned, read_ahead_kb 32 | 5 |
| `compare_Btuned16_5.4.214-b0.csv` | 5.4.214-b0 | B-tuned, read_ahead_kb 16 | 5 |
| `compare_P1_5.4.214-p1.csv` | 5.4.214-p1 | P1, read_ahead_kb 128 | 5 |
| `sha256_B0.txt`, `sha256_P1.txt` | 각 커널 | 테스트 파일 전체의 SHA-256 | 1 |
| `smallfile_B0_5.4.214-b0.csv` | 5.4.214-b0 | 작은 파일 순차 읽기, B0 (2026-11-16) | 5 |
| `smallfile_P1_5.4.214-p1.csv` | 5.4.214-p1 | 작은 파일 순차 읽기, P1 (2026-11-16) | 5 |
| `sweep_5.4.214-b0.csv` | 5.4.214-b0 | burst 길이 1~32페이지, B0와 B-tuned 32, 16 (2026-11-16) | 3 |
| `sweep_5.4.214-p1.csv` | 5.4.214-p1 | burst 길이 1~32페이지, P1 (2026-11-16) | 3 |

- 작은 파일 순차 읽기는 루트 디스크(`/dev/sda5`, ext4, read_ahead_kb 128)에 만든 파일 1,200개로 쟀다. 64 KiB 500개, 256 KiB 500개, 1024 KiB 200개이고 `scripts/make_small_files.sh`로 만든다. 파일을 하나씩 열어 4 KiB씩 끝까지 읽고, 페이지마다 0, 50, 200마이크로초 동안 CPU를 쓰며 머문다. `pread_ms`는 `pread` 안에서 보낸 시간의 합이다. B0는 부팅 후 249초(부하 0.20), P1은 246초(부하 0.24)에 시작했다.
- burst 길이 1~32페이지 측정(`sweep_*.csv`)은 `scripts/measure_sweep.sh`로 했다. 읽은 양만 보는 측정이라 길이마다 3회 잰다. B0는 부팅 후 245초(부하 0.27), P1은 244초(부하 0.14)에 시작했다.
- `5.4.214-SEOJUNGMIN+`는 kernel.org의 5.4.214에 수업 과제용 시스템 콜 하나를 더한 커널이다. `mm/`, `fs/`, `block/`은 원본과 같다.
- B0는 부팅 후 약 4분, 부하 약 0.5일 때 측정을 시작했다. 대기 규칙을 스크립트에 넣기 전이다.
- P1은 두 번 쟀다. 첫 번째는 부팅 30초 뒤에 시작해 부팅 직후 작업과 겹쳤기 때문에(부하 3.3) 버렸다. 남긴 것은 부팅 후 248초, 부하 0.54에서 시작한 두 번째 측정이다. 두 측정의 `read_bytes`는 같았다.
