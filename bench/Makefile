CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra

all: ra_bench smallfile_bench

ra_bench: ra_bench.c
	$(CC) $(CFLAGS) -o $@ $<

smallfile_bench: smallfile_bench.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f ra_bench smallfile_bench

.PHONY: all clean
