#!/bin/sh
# 지금 부팅된 커널에서 측정 한 벌을 돌린다.
#
# 사용법 (저장소 최상위에서): scripts/measure_kernel.sh <B0|P1>
#   B0  원본 커널. 기본 설정으로 잰 뒤, 같은 커널에서 read_ahead_kb만 줄인
#       B-tuned(32, 16)도 이어서 잰다.
#   P1  패치 커널. 기본 설정으로만 잰다.
#
# 테스트 디스크를 읽기 전용으로 마운트하고, 파일 전체의 sha256도 남긴다.
set -eu
. scripts/lib.sh

LABEL=$1
DEV=/dev/sdb
MNT=/mnt/ext4-lab
FILE=$MNT/assignment8/fio-test.0.0

check_kernel "$LABEL"
settle

mountpoint -q "$MNT" || sudo mount -o ro "$DEV" "$MNT"
mkdir -p results

# 파일 전체를 읽어 내용이 커널에 따라 달라지지 않는지 확인하는 용도
sha256sum "$FILE" | cut -d' ' -f1 > "results/sha256_${LABEL}.txt"

scripts/run_compare.sh "$LABEL" "$FILE"
if [ "$LABEL" = B0 ]; then
	scripts/run_compare.sh Btuned32 "$FILE" 32
	scripts/run_compare.sh Btuned16 "$FILE" 16
fi
