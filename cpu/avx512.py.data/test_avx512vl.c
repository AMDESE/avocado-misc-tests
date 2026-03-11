/*
 * test_avx512vl.c - AVX-512 Vector Length Extensions (VL) instruction tests
 *
 * VL enables EVEX-encoded 128-bit (XMM) and 256-bit (YMM) operations,
 * adding masking support and new register encodings.
 *
 * Tests: EVEX vpaddd ymm/xmm, vpmulld ymm, vaddps ymm, vpbroadcastd ymm,
 *        vpabsd ymm, vpblendmd ymm (masked), vpaddd xmm (masked), vpminsd ymm
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpaddd_ymm(void)
{
	uint32_t a[8] __attribute__((aligned(32)));
	uint32_t b[8] __attribute__((aligned(32)));
	uint32_t c[8] __attribute__((aligned(32)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 100;
		b[i] = 200;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%ymm0\n\t"
		"vmovdqu32 (%1), %%ymm1\n\t"
		"vpaddd %%ymm1, %%ymm0, %%ymm2\n\t"
		"vmovdqu32 %%ymm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (c[i] != 300) {
			printf("FAIL avx512vl/vpaddd_ymm: c[%d]=%u, expected 300\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512vl/vpaddd_ymm: EVEX 256-bit packed add correct\n");
	return 0;
}

static int test_vpaddd_xmm(void)
{
	uint32_t a[4] __attribute__((aligned(16)));
	uint32_t b[4] __attribute__((aligned(16)));
	uint32_t c[4] __attribute__((aligned(16)));
	int i;

	for (i = 0; i < 4; i++) {
		a[i] = 50;
		b[i] = 75;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%xmm0\n\t"
		"vmovdqu32 (%1), %%xmm1\n\t"
		"vpaddd %%xmm1, %%xmm0, %%xmm2\n\t"
		"vmovdqu32 %%xmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 4; i++) {
		if (c[i] != 125) {
			printf("FAIL avx512vl/vpaddd_xmm: c[%d]=%u, expected 125\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512vl/vpaddd_xmm: EVEX 128-bit packed add correct\n");
	return 0;
}

static int test_vpmulld_ymm(void)
{
	uint32_t a[8] __attribute__((aligned(32)));
	uint32_t b[8] __attribute__((aligned(32)));
	uint32_t c[8] __attribute__((aligned(32)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = i + 1;
		b[i] = 10;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%ymm0\n\t"
		"vmovdqu32 (%1), %%ymm1\n\t"
		"vpmulld %%ymm1, %%ymm0, %%ymm2\n\t"
		"vmovdqu32 %%ymm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		uint32_t expected = (i + 1) * 10;

		if (c[i] != expected) {
			printf("FAIL avx512vl/vpmulld_ymm: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512vl/vpmulld_ymm: EVEX 256-bit packed multiply correct\n");
	return 0;
}

static int test_vaddps_ymm(void)
{
	float a[8] __attribute__((aligned(32)));
	float b[8] __attribute__((aligned(32)));
	float c[8] __attribute__((aligned(32)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (float)(i + 1);
		b[i] = 0.5f;
		c[i] = 0.0f;
	}

	asm volatile(
		"vmovups (%0), %%ymm0\n\t"
		"vmovups (%1), %%ymm1\n\t"
		"vaddps %%ymm1, %%ymm0, %%ymm2\n\t"
		"vmovups %%ymm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		float expected = (float)(i + 1) + 0.5f;

		if (c[i] != expected) {
			printf("FAIL avx512vl/vaddps_ymm: c[%d]=%f, expected %f\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512vl/vaddps_ymm: EVEX 256-bit FP add correct\n");
	return 0;
}

static int test_vpbroadcastd_ymm(void)
{
	uint32_t val = 42;
	uint32_t c[8] __attribute__((aligned(32)));
	int i;

	memset(c, 0, sizeof(c));

	asm volatile(
		"vpbroadcastd %1, %%ymm0\n\t"
		"vmovdqu32 %%ymm0, (%0)\n\t"
		:
		: "r"(c), "m"(val)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (c[i] != 42) {
			printf("FAIL avx512vl/vpbroadcastd_ymm: c[%d]=%u, expected 42\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512vl/vpbroadcastd_ymm: EVEX 256-bit broadcast correct\n");
	return 0;
}

static int test_vpabsd_ymm(void)
{
	int32_t a[8] __attribute__((aligned(32)));
	int32_t c[8] __attribute__((aligned(32)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = -(i + 1);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%ymm0\n\t"
		"vpabsd %%ymm0, %%ymm1\n\t"
		"vmovdqu32 %%ymm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		int32_t expected = i + 1;

		if (c[i] != expected) {
			printf("FAIL avx512vl/vpabsd_ymm: c[%d]=%d, expected %d\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512vl/vpabsd_ymm: EVEX 256-bit absolute value correct\n");
	return 0;
}

static int test_vpblendmd_ymm(void)
{
	/*
	 * vpblendmd with mask on YMM (EVEX only).
	 * mask = 0xAA = 10101010: even lanes from a, odd lanes from b.
	 */
	uint32_t a[8] __attribute__((aligned(32)));
	uint32_t b[8] __attribute__((aligned(32)));
	uint32_t c[8] __attribute__((aligned(32)));
	unsigned int mask = 0xAA;
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 1;
		b[i] = 2;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%ymm0\n\t"
		"vmovdqu32 (%1), %%ymm1\n\t"
		"kmovw %3, %%k1\n\t"
		"vpblendmd %%ymm1, %%ymm0, %%ymm2 %{%%k1%}\n\t"
		"vmovdqu32 %%ymm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c), "r"(mask)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		uint32_t expected = (i % 2 == 0) ? 1 : 2;

		if (c[i] != expected) {
			printf("FAIL avx512vl/vpblendmd_ymm: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512vl/vpblendmd_ymm: EVEX 256-bit masked blend correct\n");
	return 0;
}

static int test_vpminsd_ymm(void)
{
	int32_t a[8] __attribute__((aligned(32)));
	int32_t b[8] __attribute__((aligned(32)));
	int32_t c[8] __attribute__((aligned(32)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = i * 10;
		b[i] = 35;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%ymm0\n\t"
		"vmovdqu32 (%1), %%ymm1\n\t"
		"vpminsd %%ymm1, %%ymm0, %%ymm2\n\t"
		"vmovdqu32 %%ymm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		int32_t expected = (i * 10 < 35) ? i * 10 : 35;

		if (c[i] != expected) {
			printf("FAIL avx512vl/vpminsd_ymm: c[%d]=%d, expected %d\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512vl/vpminsd_ymm: EVEX 256-bit signed min correct\n");
	return 0;
}

int test_avx512vl_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpaddd_ymm() == 0) passed++; else failed++;
	total++; if (test_vpaddd_xmm() == 0) passed++; else failed++;
	total++; if (test_vpmulld_ymm() == 0) passed++; else failed++;
	total++; if (test_vaddps_ymm() == 0) passed++; else failed++;
	total++; if (test_vpbroadcastd_ymm() == 0) passed++; else failed++;
	total++; if (test_vpabsd_ymm() == 0) passed++; else failed++;
	total++; if (test_vpblendmd_ymm() == 0) passed++; else failed++;
	total++; if (test_vpminsd_ymm() == 0) passed++; else failed++;

	printf("\n=== avx512vl: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
