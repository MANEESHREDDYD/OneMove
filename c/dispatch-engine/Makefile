CC = gcc
CFLAGS = -Wall -O3 -Iinclude

all: dispatch_engine

dispatch_engine: src/main.c src/haversine.c src/dispatch.c
	$(CC) $(CFLAGS) -o dispatch_engine src/main.c src/haversine.c src/dispatch.c -lm

test: tests/test_dispatch.c src/haversine.c src/dispatch.c
	$(CC) $(CFLAGS) -o test_dispatch tests/test_dispatch.c src/haversine.c src/dispatch.c -lm
	./test_dispatch

benchmark: dispatch_engine
	@echo "Running Benchmark..."
	./dispatch_engine data/sample_orders.csv data/sample_partners.csv

clean:
	rm -f dispatch_engine test_dispatch
