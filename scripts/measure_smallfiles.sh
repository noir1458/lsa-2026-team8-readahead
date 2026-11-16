#!/bin/sh
# 작은 파일 순차 읽기 측정: 지금 부팅된 커널에서 작은 파일들을 처음부터 끝까지
# 4 KiB씩 읽는다. 패치가 순차 읽기 초반에 손해를 주는지 보기 위한 것이다.
#
# 사용법 (저장소 최상위에서): scripts/measure_smallfiles.sh <B0|P1> [파일 디렉터리]
#
# 파일 크기(64, 256, 1024 KiB)와 페이지당 머무는 시간(0, 50, 200 마이크로초)을
# 바꿔 가며 조건마다 5회 잰다. 파일은 scripts/make_small_files.sh 로 미리 만든다.
set -eu
. scripts/lib.sh

LABEL=$1
DIR=${2:-$HOME/lsa-readahead/smallfiles}
BENCH=bench/smallfile_bench
REPEAT=5
OUT=results/smallfile_${LABEL}_$(uname -r).csv

check_kernel "$LABEL"
settle

DISK=$(basename "$(df --output=source "$DIR" | tail -1)" | sed 's/[0-9]*$//')
echo "커널 $(uname -r), 디스크 $DISK, read_ahead_kb $(cat "/sys/block/$DISK/queue/read_ahead_kb")"

mkdir -p results
"$BENCH" -H > "$OUT"
for spec in 64:500 256:500 1024:200; do
	kib=${spec%%:*}
	n=${spec##*:}
	for think in 0 50 200; do
		i=1
		while [ "$i" -le "$REPEAT" ]; do
			drop_caches
			"$BENCH" -d "$DIR" -s "$kib" -n "$n" -t "$think" -l "$LABEL" >> "$OUT"
			i=$((i + 1))
		done
	done
done

echo "저장: $OUT"
