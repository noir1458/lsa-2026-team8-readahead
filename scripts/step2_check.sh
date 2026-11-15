#!/bin/sh
# 2단계 확인: 원본 커널에서 짧은 burst를 기본 설정과 POSIX_FADV_RANDOM으로
# 각각 읽어 read_bytes를 비교한다. 매 실행 전에 페이지 캐시를 비운다.
#
# 사용법 (저장소 최상위에서): scripts/step2_check.sh <테스트 파일> [결과 CSV]
# drop_caches 때문에 sudo가 필요하다.
set -eu

FILE=$1
OUT=${2:-results/step2_$(uname -r).csv}
BENCH=bench/ra_bench
REPEAT=3
COUNT=500

mkdir -p "$(dirname "$OUT")"
"$BENCH" -H > "$OUT"

for burst in 2 3 4 8 16; do
	for advice in normal random; do
		i=1
		while [ "$i" -le "$REPEAT" ]; do
			sync
			echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
			"$BENCH" -f "$FILE" -p burst -b "$burst" -n "$COUNT" \
				-a "$advice" -l step2 >> "$OUT"
			i=$((i + 1))
		done
	done
done

echo "저장: $OUT"
