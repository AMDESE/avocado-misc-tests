/*
 * test_avx512bitalg.c - AVX-512 Bit Algorithms (BITALG) instruction tests
 *
 * Tests: vpopcntb, vpopcntw, vpshufbitqmb
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpopcntb(void)
{
	uint8_t a[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		a[i] = (uint8_t)i;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vpopcntb %%zmm0, %%zmm1\n\t"
		"vmovdqu8 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t expected = 0;
		uint8_t v = (uint8_t)i;

		while (v) {
			expected += v & 1;
			v >>= 1;
		}
		if (c[i] != expected) {
			printf("FAIL avx512_bitalg/vpopcntb: popcnt(%d)=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512_bitalg/vpopcntb: packed byte popcount correct\n");
	return 0;
}

static int test_vpopcntw(void)
{
	uint16_t a[32] __attribute__((aligned(64)));
	uint16_t c[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = (uint16_t)((1u << ((i % 16) + 1)) - 1);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vpopcntw %%zmm0, %%zmm1\n\t"
		"vmovdqu16 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		uint16_t expected = (uint16_t)((i % 16) + 1);

		if (c[i] != expected) {
			printf("FAIL avx512_bitalg/vpopcntw: popcnt(0x%04x)=%u, expected %u\n",
			       a[i], c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512_bitalg/vpopcntw: packed word popcount correct\n");
	return 0;
}

static int test_vpshufbitqmb(void)
{
	/*
	 * vpshufbitqmb: for each byte j in each qword i of src2,
	 * use bits [5:0] as a bit index into qword i of src1,
	 * and set the corresponding mask bit.
	 *
	 * src1: all qwords = 0x5555555555555555 (alternating bits: ...0101)
	 * src2: bytes alternating {0, 1, 0, 1, ...} per qword
	 *   byte selecting bit 0: bit 0 of 0x55..55 = 1 -> mask bit = 1
	 *   byte selecting bit 1: bit 1 of 0x55..55 = 0 -> mask bit = 0
	 *
	 * Expected mask: 0x5555555555555555 (alternating 1,0 across 64 bytes)
	 */
	uint64_t src1[8] __attribute__((aligned(64)));
	uint8_t src2[64] __attribute__((aligned(64)));
	uint64_t result_mask;
	int i;

	for (i = 0; i < 8; i++)
		src1[i] = 0x5555555555555555ULL;

	for (i = 0; i < 64; i++)
		src2[i] = (uint8_t)(i & 1);

	asm volatile(
		"vmovdqu64 (%1), %%zmm0\n\t"
		"vmovdqu8 (%2), %%zmm1\n\t"
		"vpshufbitqmb %%zmm1, %%zmm0, %%k1\n\t"
		"kmovq %%k1, %0\n\t"
		: "=r"(result_mask)
		: "r"(src1), "r"(src2)
		: "memory"
	);

	if (result_mask != 0x5555555555555555ULL) {
		printf("FAIL avx512_bitalg/vpshufbitqmb: mask=0x%016lx, expected 0x5555555555555555\n",
		       (unsigned long)result_mask);
		return 1;
	}
	printf("PASS avx512_bitalg/vpshufbitqmb: bit shuffle to mask correct\n");
	return 0;
}

int test_avx512bitalg_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpopcntb() == 0) passed++; else failed++;
	total++; if (test_vpopcntw() == 0) passed++; else failed++;
	total++; if (test_vpshufbitqmb() == 0) passed++; else failed++;

	printf("\n=== avx512_bitalg: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
