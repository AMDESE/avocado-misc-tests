/*
 * test_avx512cd.c - AVX-512 Conflict Detection (CD) instruction tests
 *
 * Tests: vplzcntd, vplzcntq, vpconflictd, vpconflictq
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vplzcntd(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 1u << (i % 32);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vplzcntd %%zmm0, %%zmm1\n\t"
		"vmovdqu32 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected = 31 - (i % 32);

		if (c[i] != expected) {
			printf("FAIL avx512cd/vplzcntd: lzcnt(1<<%d)=%u, expected %u\n",
			       i % 32, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512cd/vplzcntd: packed 32-bit leading zero count correct\n");
	return 0;
}

static int test_vplzcntq(void)
{
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 1ULL << (i * 8);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vplzcntq %%zmm0, %%zmm1\n\t"
		"vmovdqu64 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		uint64_t expected = 63 - (i * 8);

		if (c[i] != expected) {
			printf("FAIL avx512cd/vplzcntq: lzcnt(1<<%d)=%lu, expected %lu\n",
			       i * 8, (unsigned long)c[i], (unsigned long)expected);
			return 1;
		}
	}
	printf("PASS avx512cd/vplzcntq: packed 64-bit leading zero count correct\n");
	return 0;
}

static int test_vpconflictd(void)
{
	/*
	 * vpconflictd: for each element, produce a bitmask of prior elements
	 * with the same value.
	 *
	 * Input:  {10, 20, 10, 30, 20, 10, 40, 50, 10, 20, 30, 40, 50, 60, 70, 80}
	 * Expected conflict masks:
	 *   [0]=10: no prior match         -> 0x0000
	 *   [1]=20: no prior match         -> 0x0000
	 *   [2]=10: matches [0]            -> 0x0001
	 *   [3]=30: no prior match         -> 0x0000
	 *   [4]=20: matches [1]            -> 0x0002
	 *   [5]=10: matches [0],[2]        -> 0x0005
	 *   [6]=40: no prior match         -> 0x0000
	 *   [7]=50: no prior match         -> 0x0000
	 *   [8]=10: matches [0],[2],[5]    -> 0x0025
	 *   [9]=20: matches [1],[4]        -> 0x0012
	 *   [10]=30: matches [3]           -> 0x0008
	 *   [11]=40: matches [6]           -> 0x0040
	 *   [12]=50: matches [7]           -> 0x0080
	 *   [13]=60: no prior match        -> 0x0000
	 *   [14]=70: no prior match        -> 0x0000
	 *   [15]=80: no prior match        -> 0x0000
	 */
	uint32_t a[16] __attribute__((aligned(64))) = {
		10, 20, 10, 30, 20, 10, 40, 50,
		10, 20, 30, 40, 50, 60, 70, 80
	};
	uint32_t c[16] __attribute__((aligned(64)));
	uint32_t expected[16] = {
		0x0000, 0x0000, 0x0001, 0x0000,
		0x0002, 0x0005, 0x0000, 0x0000,
		0x0025, 0x0012, 0x0008, 0x0040,
		0x0080, 0x0000, 0x0000, 0x0000
	};
	int i;

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vpconflictd %%zmm0, %%zmm1\n\t"
		"vmovdqu32 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != expected[i]) {
			printf("FAIL avx512cd/vpconflictd: c[%d]=0x%04x, expected 0x%04x\n",
			       i, c[i], expected[i]);
			return 1;
		}
	}
	printf("PASS avx512cd/vpconflictd: packed 32-bit conflict detection correct\n");
	return 0;
}

static int test_vpconflictq(void)
{
	/*
	 * vpconflictq: same as vpconflictd but for 64-bit elements (8 lanes).
	 * Input:  {100, 200, 100, 300, 200, 100, 400, 500}
	 * Expected:
	 *   [0]=100: no match       -> 0x00
	 *   [1]=200: no match       -> 0x00
	 *   [2]=100: matches [0]    -> 0x01
	 *   [3]=300: no match       -> 0x00
	 *   [4]=200: matches [1]    -> 0x02
	 *   [5]=100: matches [0],[2]-> 0x05
	 *   [6]=400: no match       -> 0x00
	 *   [7]=500: no match       -> 0x00
	 */
	uint64_t a[8] __attribute__((aligned(64))) = {
		100, 200, 100, 300, 200, 100, 400, 500
	};
	uint64_t c[8] __attribute__((aligned(64)));
	uint64_t expected[8] = {
		0x00, 0x00, 0x01, 0x00, 0x02, 0x05, 0x00, 0x00
	};
	int i;

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vpconflictq %%zmm0, %%zmm1\n\t"
		"vmovdqu64 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (c[i] != expected[i]) {
			printf("FAIL avx512cd/vpconflictq: c[%d]=0x%02lx, expected 0x%02lx\n",
			       i, (unsigned long)c[i], (unsigned long)expected[i]);
			return 1;
		}
	}
	printf("PASS avx512cd/vpconflictq: packed 64-bit conflict detection correct\n");
	return 0;
}

int test_avx512cd_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vplzcntd() == 0) passed++; else failed++;
	total++; if (test_vplzcntq() == 0) passed++; else failed++;
	total++; if (test_vpconflictd() == 0) passed++; else failed++;
	total++; if (test_vpconflictq() == 0) passed++; else failed++;

	printf("\n=== avx512cd: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
