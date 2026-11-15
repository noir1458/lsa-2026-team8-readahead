/*
 * ra_bench - readahead 실험용 읽기 벤치마크
 *
 * 파일을 4 KiB 단위 pread로 읽고, 그동안 디스크에서 실제로 읽힌 양
 * (/proc/self/io 의 read_bytes)과 걸린 시간을 CSV 한 줄로 출력한다.
 *
 * 패턴
 *   burst : N페이지를 이어서 읽고 jump만큼 건너뛰기를 반복한다
 *   seq   : 처음부터 끝까지 순서대로 읽는다
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

/* 이 프로세스가 디스크에서 읽어 오게 만든 바이트 수 (readahead 포함) */
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

/* off부터 pages페이지를 4 KiB씩 읽는다. 읽은 내용은 sum에 섞어 넣는다. */
static void read_pages(int fd, off_t off, long pages, uint64_t *sum)
{
	static uint64_t buf[PAGE / 8];
	long i, k;

	for (i = 0; i < pages; i++) {
		ssize_t n = pread(fd, buf, PAGE, off + (off_t)i * PAGE);

		if (n < 0)
			die("pread");
		if (n != PAGE) {
			fprintf(stderr, "짧게 읽힘: offset %lld\n",
				(long long)(off + (off_t)i * PAGE));
			exit(1);
		}
		for (k = 0; k < PAGE / 8; k++)
			*sum = (*sum ^ buf[k]) * 1099511628211ull;
	}
}

static void usage(const char *prog)
{
	fprintf(stderr,
		"사용법: %s -f 파일 -p burst|seq [옵션]\n"
		"  -b N   burst 한 번에 읽는 페이지 수 (기본 4)\n"
		"  -j K   burst 사이에 건너뛰는 거리, KiB (기본 1024)\n"
		"  -n C   burst 반복 횟수 (기본 200)\n"
		"  -a A   normal 또는 random (POSIX_FADV_RANDOM), 기본 normal\n"
		"  -l L   CSV 첫 칸에 넣을 이름 (기본 none)\n"
		"  -H     CSV 머리글만 출력하고 끝낸다\n",
		prog);
	exit(2);
}

int main(int argc, char **argv)
{
	const char *file = NULL, *pattern = NULL;
	const char *advice = "normal", *label = "none";
	long burst = 4, jump_kib = 1024, count = 200;
	uint64_t requested, rb0, rb1, t0, t1, sum = 14695981039346656037ull;
	struct utsname un;
	struct stat st;
	int fd, opt;
	long i;

	while ((opt = getopt(argc, argv, "f:p:b:j:n:a:l:H")) != -1) {
		switch (opt) {
		case 'f': file = optarg; break;
		case 'p': pattern = optarg; break;
		case 'b': burst = atol(optarg); break;
		case 'j': jump_kib = atol(optarg); break;
		case 'n': count = atol(optarg); break;
		case 'a': advice = optarg; break;
		case 'l': label = optarg; break;
		case 'H':
			puts("label,kernel,pattern,burst_pages,jump_kib,bursts,"
			     "advice,requested_bytes,read_bytes,elapsed_ms,checksum");
			return 0;
		default: usage(argv[0]);
		}
	}
	if (!file || !pattern)
		usage(argv[0]);
	if (strcmp(pattern, "burst") && strcmp(pattern, "seq"))
		usage(argv[0]);
	if (strcmp(advice, "normal") && strcmp(advice, "random"))
		usage(argv[0]);
	if (burst < 1 || jump_kib < 0 || count < 1)
		usage(argv[0]);

	fd = open(file, O_RDONLY);
	if (fd < 0)
		die(file);
	if (fstat(fd, &st) < 0)
		die("fstat");
	if (!strcmp(advice, "random") &&
	    posix_fadvise(fd, 0, 0, POSIX_FADV_RANDOM) != 0) {
		fprintf(stderr, "posix_fadvise 실패\n");
		return 1;
	}

	if (!strcmp(pattern, "seq")) {
		burst = st.st_size / PAGE;	/* 파일 전체를 한 번에 */
		jump_kib = 0;
		count = 1;
	}
	{
		off_t stride = (off_t)burst * PAGE + (off_t)jump_kib * 1024;
		off_t need = (off_t)(count - 1) * stride + (off_t)burst * PAGE;

		if (burst < 1 || need > st.st_size) {
			fprintf(stderr, "파일이 작다: %lld바이트 필요, 파일은 %lld바이트\n",
				(long long)need, (long long)st.st_size);
			return 1;
		}

		/*
		 * 측정에 쓰는 코드를 미리 한 번씩 실행해 메모리에 올린다.
		 * 0바이트 pread는 파일 내용을 건드리지 않는다. 캐시를 비운
		 * 직후에는 libc 코드도 디스크에서 읽히는데, 그 양이 측정값에
		 * 섞이지 않게 하려는 것이다.
		 */
		if (pread(fd, &sum, 0, 0) < 0)
			die("pread");
		(void)read_bytes_now();
		(void)now_ns();

		rb0 = read_bytes_now();
		t0 = now_ns();
		for (i = 0; i < count; i++)
			read_pages(fd, (off_t)i * stride, burst, &sum);
		t1 = now_ns();
		rb1 = read_bytes_now();
	}
	close(fd);

	requested = (uint64_t)count * (uint64_t)burst * PAGE;
	if (uname(&un) < 0)
		die("uname");
	printf("%s,%s,%s,%ld,%ld,%ld,%s,%" PRIu64 ",%" PRIu64 ",%.3f,%016" PRIx64 "\n",
	       label, un.release, pattern,
	       strcmp(pattern, "seq") ? burst : 0, jump_kib, count, advice,
	       requested, rb1 - rb0, (double)(t1 - t0) / 1e6, sum);
	return 0;
}
