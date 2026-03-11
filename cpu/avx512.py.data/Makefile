BIN = avx512_check

SRCS = avx512_check.c \
       test_avx512f.c \
       test_avx512bw.c \
       test_avx512dq.c \
       test_avx512cd.c \
       test_avx512vl.c \
       test_avx512ifma.c \
       test_avx512vbmi.c \
       test_avx512vbmi2.c \
       test_avx512vnni.c \
       test_avx512bitalg.c \
       test_avx512vpopcntdq.c

OBJS = $(SRCS:.c=.o)

CFLAGS = -mavx512f -mavx512bw -mavx512dq -mavx512cd -mavx512vl \
         -mavx512ifma -mavx512vbmi -mavx512vnni -mavx512vpopcntdq \
         -mavx512bitalg -mavx512vbmi2

all: $(BIN)

$(BIN): $(OBJS)
	cc $(CFLAGS) -o $@ $^ -lm

%.o: %.c
	cc $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(BIN) $(OBJS)
