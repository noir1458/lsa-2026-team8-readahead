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

LABEL=$1
DEV=/dev/sdb
MNT=/mnt/ext4-lab
FILE=$MNT/assignment8/fio-test.0.0

case "$LABEL:$(uname -r)" in
B0:*-b0 | P1:*-p1) ;;
*)
	echo "이름 $LABEL 과 부팅된 커널 $(uname -r) 이 맞지 않는다"
	exit 1
	;;
esac

# 부팅 직후에 도는 백그라운드 작업이 시간 측정에 섞이지 않게 기다린다.
# 부팅 후 4분이 지나고 1분 평균 부하가 0.6 아래일 때 시작한다 (최대 10분 대기).
waited=0
while [ "$waited" -lt 600 ]; do
	up=$(cut -d. -f1 /proc/uptime)
	load=$(cut -d' ' -f1 /proc/loadavg)
	if [ "$up" -ge 240 ] && awk -v l="$load" 'BEGIN { exit !(l < 0.6) }'; then
		break
	fi
	sleep 10
	waited=$((waited + 10))
done
echo "측정 시작: 부팅 후 ${up}초, 1분 평균 부하 $load"

mountpoint -q "$MNT" || sudo mount -o ro "$DEV" "$MNT"
mkdir -p results

# 파일 전체를 읽어 내용이 커널에 따라 달라지지 않는지 확인하는 용도
sha256sum "$FILE" | cut -d' ' -f1 > "results/sha256_${LABEL}.txt"

scripts/run_compare.sh "$LABEL" "$FILE"
if [ "$LABEL" = B0 ]; then
	scripts/run_compare.sh Btuned32 "$FILE" 32
	scripts/run_compare.sh Btuned16 "$FILE" 16
fi
