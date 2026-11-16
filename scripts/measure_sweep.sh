#!/bin/sh
# burst 길이를 1~32페이지로 바꿔 가며 디스크에서 읽은 양을 잰다.
# 읽은 양은 반복해도 같으므로 조건마다 3회만 잰다.
#
# 사용법 (저장소 최상위에서): scripts/measure_sweep.sh <B0|P1>
#   B0  원본 커널. 기본 설정과 read_ahead_kb 32, 16을 잰다.
#   P1  패치 커널. 기본 설정으로만 잰다.
#
# 결과: results/sweep_<커널 이름>.csv
set -eu
. scripts/lib.sh

LABEL=$1
DEV=/dev/sdb
MNT=/mnt/ext4-lab
FILE=$MNT/assignment8/fio-test.0.0
BENCH=bench/ra_bench
REPEAT=3
COUNT=500
OUT=results/sweep_$(uname -r).csv

check_kernel "$LABEL"
settle

mountpoint -q "$MNT" || sudo mount -o ro "$DEV" "$MNT"
DISK=$(basename "$(df --output=source "$FILE" | tail -1)")
RA_PATH=/sys/block/$DISK/queue/read_ahead_kb
RA_OLD=$(cat "$RA_PATH")
trap 'echo "$RA_OLD" | sudo tee "$RA_PATH" > /dev/null' EXIT

# sweep <조건 이름> <read_ahead_kb>
sweep() {
	echo "$2" | sudo tee "$RA_PATH" > /dev/null
	echo "$1: 커널 $(uname -r), 디스크 $DISK, read_ahead_kb $(cat "$RA_PATH")"
	burst=1
	while [ "$burst" -le 32 ]; do
		i=1
		while [ "$i" -le "$REPEAT" ]; do
			drop_caches
			"$BENCH" -f "$FILE" -l "$1" -p burst -b "$burst" -n "$COUNT" >> "$OUT"
			i=$((i + 1))
		done
		burst=$((burst + 1))
	done
}

mkdir -p results
"$BENCH" -H > "$OUT"
sweep "$LABEL" 128
if [ "$LABEL" = B0 ]; then
	sweep Btuned32 32
	sweep Btuned16 16
fi
echo "저장: $OUT"
