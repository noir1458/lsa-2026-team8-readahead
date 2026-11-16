/*
 * smallfile_bench - 작은 파일 여러 개를 처음부터 끝까지 순서대로 읽는 벤치마크
 *
 * 디렉터리 안의 f_<크기>_<번호> 파일을 차례로 열어 4 KiB씩 pread로 끝까지
 * 읽는다. 한 페이지를 읽을 때마다 think 마이크로초 동안 CPU를 쓰며 머문다.
 * 읽은 내용을 처리하느라 시간이 걸리는 프로그램을 흉내 낸 것이다.
 *
 * pread 안에서 보낸 시간의 합(pread_ms)을 따로 잰다. 미리 읽기가 제때 끝나
 * 있으면 이 값이 작고, 프로그램이 디스크를 기다리면 커진다.
 *
 * 캐시는 여기서 비우지 않는다. 실행 전에 밖에서 drop_caches를 해 둔다.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>

#define PAGE 4096

static void die(const char *msg)
{
	perror(msg);
	exit(1);
}

static uint64_t read_bytes_now(void)
{
	FILE *f = fopen("/proc/self/io", "r");
	char line[128];
	uint64_t v = 0;
	int found = 0;

	if (!f)
		die("/proc/self/io");
	while (fgets(line, sizeof line, f)) {
		if (sscanf(line, "read_bytes: %" SCNu64, &v) == 1) {
			found = 1;
			break;
		}
	}
	fclose(f);
	if (!found) {
		fprintf(stderr, "/proc/self/io 에 read_bytes 항목이 없다\n");
		exit(1);
	}
	return v;
}

static uint64_t now_ns(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

/* ns 동안 CPU를 쓰며 머문다. 잠들지 않는다. */
static void think(uint64_t ns)
{
	uint64_t end = now_ns() + ns;

	while (now_ns() < end)
		;
}

static void usage(const char *prog)
{
	fprintf(stderr,
		"사용법: %s -d 디렉터리 -s 파일크기KiB -n 파일수 [옵션]\n"
		"  -t U   페이지 하나를 읽은 뒤 머무는 시간, 마이크로초 (기본 0)\n"
		"  -l L   CSV 첫 칸에 넣을 이름 (기본 none)\n"
		"  -H     CSV 머리글만 출력하고 끝낸다\n",
		prog);
	exit(2);
}

int main(int argc, char **argv)
{
	static uint64_t buf[PAGE / 8];
	const char *dir = NULL, *label = "none";
	long kib = 0, files = 0, think_us = 0;
	uint64_t rb0, rb1, t0, t1, pread_ns = 0, sum = 14695981039346656037ull;
	struct utsname un;
	char path[4096];
	long i, p, k;
	int opt;

	while ((opt = getopt(argc, argv, "d:s:n:t:l:H")) != -1) {
		switch (opt) {
		case 'd': dir = optarg; break;
		case 's': kib = atol(optarg); break;
		case 'n': files = atol(optarg); break;
		case 't': think_us = atol(optarg); break;
		case 'l': label = optarg; break;
		case 'H':
			puts("label,kernel,file_kib,files,think_us,read_bytes,"
			     "elapsed_ms,pread_ms,checksum");
			return 0;
		default: usage(argv[0]);
		}
	}
	if (!dir || kib < 4 || files < 1 || think_us < 0)
		usage(argv[0]);

	/* 측정에 쓰는 코드를 미리 한 번씩 실행해 메모리에 올린다 */
	(void)read_bytes_now();
	think(1000);

	rb0 = read_bytes_now();
	t0 = now_ns();
	for (i = 0; i < files; i++) {
		struct stat st;
		long pages;
		int fd;

		snprintf(path, sizeof path, "%s/f_%ld_%ld", dir, kib, i);
		fd = open(path, O_RDONLY);
		if (fd < 0)
			die(path);
		if (fstat(fd, &st) < 0)
			die("fstat");
		pages = st.st_size / PAGE;
		if (pages != kib / 4) {
			fprintf(stderr, "%s: 크기가 %ld KiB가 아니다\n", path, kib);
			return 1;
		}
		for (p = 0; p < pages; p++) {
			uint64_t a = now_ns();
			ssize_t n = pread(fd, buf, PAGE, (off_t)p * PAGE);

			pread_ns += now_ns() - a;
			if (n != PAGE) {
				fprintf(stderr, "%s: 짧게 읽힘\n", path);
				return 1;
			}
			for (k = 0; k < PAGE / 8; k++)
				sum = (sum ^ buf[k]) * 1099511628211ull;
			if (think_us)
				think((uint64_t)think_us * 1000);
		}
		close(fd);
	}
	t1 = now_ns();
	rb1 = read_bytes_now();

	if (uname(&un) < 0)
		die("uname");
	printf("%s,%s,%ld,%ld,%ld,%" PRIu64 ",%.3f,%.3f,%016" PRIx64 "\n",
	       label, un.release, kib, files, think_us, rb1 - rb0,
	       (double)(t1 - t0) / 1e6, (double)pread_ns / 1e6, sum);
	return 0;
}
