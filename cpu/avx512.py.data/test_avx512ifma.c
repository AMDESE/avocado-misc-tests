/*
 * test_avx512ifma.c - AVX-512 Integer Fused Multiply-Add (IFMA) instruction tests
 *
 * Tests: vpmadd52luq, vpmadd52huq
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpmadd52luq(void)
{
	/*
	 * vpmadd52luq: dst = src + low52(a[51:0] * b[51:0])
	 * a=3, b=7: product=21, low 52 bits=21
	 * src=10: result = 10 + 21 = 31
	 */
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t b[8] __attribute__((aligned(64)));
	uint64_t src[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 3;
		b[i] = 7;
		src[i] = 10;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vmovdqu64 (%2), %%zmm2\n\t"
		"vpmadd52luq %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(src), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (c[i] != 31) {
			printf("FAIL avx512ifma/vpmadd52luq: c[%d]=%lu, expected 31\n",
			       i, (unsigned long)c[i]);
			return 1;
		}
	}
	printf("PASS avx512ifma/vpmadd52luq: 52-bit multiply-add low correct\n");
	return 0;
}

static int test_vpmadd52huq(void)
{
	/*
	 * vpmadd52huq: dst = src + high52(a[51:0] * b[51:0])
	 * a = 2^26, b = 2^27: product = 2^53
	 *   In 104-bit result: bits [103:52] = 2, bits [51:0] = 0
	 * src = 10: result = 10 + 2 = 12
	 */
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t b[8] __attribute__((aligned(64)));
	uint64_t src[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 1ULL << 26;
		b[i] = 1ULL << 27;
		src[i] = 10;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vmovdqu64 (%2), %%zmm2\n\t"
		"vpmadd52huq %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(src), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (c[i] != 12) {
			printf("FAIL avx512ifma/vpmadd52huq: c[%d]=%lu, expected 12\n",
			       i, (unsigned long)c[i]);
			return 1;
		}
	}
	printf("PASS avx512ifma/vpmadd52huq: 52-bit multiply-add high correct\n");
	return 0;
}

int test_avx512ifma_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpmadd52luq() == 0) passed++; else failed++;
	total++; if (test_vpmadd52huq() == 0) passed++; else failed++;

	printf("\n=== avx512ifma: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
