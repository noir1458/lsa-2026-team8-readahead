#!/bin/sh
# 작은 파일 순차 읽기 측정에 쓸 파일 묶음을 만든다.
# 64 KiB 500개, 256 KiB 500개, 1024 KiB 200개 (모두 약 360 MiB).
# 이미 있는 파일은 다시 만들지 않는다.
#
# 사용법: scripts/make_small_files.sh <디렉터리>
set -eu

DIR=$1
mkdir -p "$DIR"

for spec in 64:500 256:500 1024:200; do
	kib=${spec%%:*}
	n=${spec##*:}
	i=0
	while [ "$i" -lt "$n" ]; do
		f=$DIR/f_${kib}_$i
		[ -f "$f" ] || dd if=/dev/urandom of="$f" bs="${kib}k" count=1 iflag=fullblock status=none
		i=$((i + 1))
	done
done
sync
echo "파일 $(ls "$DIR" | wc -l)개, $(du -sh "$DIR" | cut -f1)"
