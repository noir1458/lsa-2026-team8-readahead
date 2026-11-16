# 측정 스크립트들이 같이 쓰는 함수. `. scripts/lib.sh` 로 불러 쓴다.

# 조건 이름(B0, P1)과 지금 부팅된 커널이 맞는지 확인한다.
check_kernel() {
	case "$1:$(uname -r)" in
	B0:*-b0 | P1:*-p1) ;;
	*)
		echo "이름 $1 과 부팅된 커널 $(uname -r) 이 맞지 않는다"
		exit 1
		;;
	esac
}

# 부팅 직후에 도는 백그라운드 작업이 시간 측정에 섞이지 않게 기다린다.
# 부팅 후 4분이 지나고 1분 평균 부하가 0.6 아래일 때 돌아온다 (최대 10분 대기).
settle() {
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
}

# 페이지 캐시와 inode·dentry 캐시를 비운다.
drop_caches() {
	sync
	echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
}
