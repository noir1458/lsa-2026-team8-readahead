#!/bin/sh
# 비교 측정: 지금 부팅된 커널에서 짧은 burst와 긴 순차 읽기를 반복해 CSV로 저장한다.
# 매 실행 전에 페이지 캐시를 비운다.
#
# 사용법 (저장소 최상위에서):
#   scripts/run_compare.sh <이름> <테스트 파일> [read_ahead_kb]
#
#   이름           CSV 첫 칸에 들어갈 조건 이름 (예: B0, P1, Btuned32)
#   read_ahead_kb  주면 테스트 파일이 있는 디스크의 read_ahead_kb를 그 값으로
#                  바꿔서 측정하고, 끝나면 원래 값으로 되돌린다
#
# drop_caches와 read_ahead_kb 변경 때문에 sudo가 필요하다.
set -eu

LABEL=$1
FILE=$2
RA_KB=${3:-}
BENCH=bench/ra_bench
REPEAT=5
COUNT=500
OUT=results/compare_${LABEL}_$(uname -r).csv

DISK=$(basename "$(df --output=source "$FILE" | tail -1)")
RA_PATH=/sys/block/$DISK/queue/read_ahead_kb
RA_OLD=$(cat "$RA_PATH")

if [ -n "$RA_KB" ]; then
	echo "$RA_KB" | sudo tee "$RA_PATH" > /dev/null
	trap 'echo "$RA_OLD" | sudo tee "$RA_PATH" > /dev/null' EXIT
fi
echo "커널 $(uname -r), 디스크 $DISK, read_ahead_kb $(cat "$RA_PATH")"

run() {
	i=1
	while [ "$i" -le "$REPEAT" ]; do
		sync
		echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
		"$BENCH" -f "$FILE" -l "$LABEL" "$@" >> "$OUT"
		i=$((i + 1))
	done
}

mkdir -p results
"$BENCH" -H > "$OUT"
for burst in 2 3 4 8 16; do
	run -p burst -b "$burst" -n "$COUNT"
done
run -p seq

echo "저장: $OUT"
