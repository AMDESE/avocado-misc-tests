/*
 * test_avx512vpopcntdq.c - AVX-512 Vector Population Count DQ instruction tests
 *
 * Tests: vpopcntd, vpopcntq
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpopcntd(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (1u << ((i % 16) + 1)) - 1;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vpopcntd %%zmm0, %%zmm1\n\t"
		"vmovdqu32 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected = (i % 16) + 1;

		if (c[i] != expected) {
			printf("FAIL avx512_vpopcntdq/vpopcntd: popcnt(0x%x)=%u, expected %u\n",
			       a[i], c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512_vpopcntdq/vpopcntd: packed 32-bit popcount correct\n");
	return 0;
}

static int test_vpopcntq(void)
{
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (1ULL << (i + 1)) - 1;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vpopcntq %%zmm0, %%zmm1\n\t"
		"vmovdqu64 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		uint64_t expected = i + 1;

		if (c[i] != expected) {
			printf("FAIL avx512_vpopcntdq/vpopcntq: popcnt(0x%lx)=%lu, expected %lu\n",
			       (unsigned long)a[i], (unsigned long)c[i],
			       (unsigned long)expected);
			return 1;
		}
	}
	printf("PASS avx512_vpopcntdq/vpopcntq: packed 64-bit popcount correct\n");
	return 0;
}

int test_avx512vpopcntdq_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpopcntd() == 0) passed++; else failed++;
	total++; if (test_vpopcntq() == 0) passed++; else failed++;

	printf("\n=== avx512_vpopcntdq: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
