/*
 * test_avx512vbmi.c - AVX-512 Vector Byte Manipulation Instructions (VBMI) tests
 *
 * Tests: vpermb, vpermi2b, vpermt2b
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpermb(void)
{
	/*
	 * vpermb: byte-granular permutation across 64 bytes.
	 * Index array reverses the source bytes.
	 */
	uint8_t src[64] __attribute__((aligned(64)));
	uint8_t idx[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		src[i] = (uint8_t)i;
		idx[i] = (uint8_t)(63 - i);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpermb %%zmm0, %%zmm1, %%zmm2\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		:
		: "r"(src), "r"(idx), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t expected = (uint8_t)(63 - i);

		if (c[i] != expected) {
			printf("FAIL avx512vbmi/vpermb: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512vbmi/vpermb: byte permutation correct\n");
	return 0;
}

static int test_vpermi2b(void)
{
	/*
	 * vpermi2b: full byte permutation using two source tables.
	 * zmm1 (indices) selects bytes from zmm2 (table0, indices 0-63)
	 * or zmm3 (table1, indices 64-127) based on index bit 6.
	 *
	 * table0 = {10, 11, 12, ..., 73}
	 * table1 = {80, 81, 82, ..., 143}
	 * indices: even positions select from table0 (idx=0,1,2,...),
	 *          odd positions select from table1 (idx=64,65,66,...)
	 */
	uint8_t table0[64] __attribute__((aligned(64)));
	uint8_t table1[64] __attribute__((aligned(64)));
	uint8_t indices[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		table0[i] = (uint8_t)(i + 10);
		table1[i] = (uint8_t)(i + 80);
	}

	for (i = 0; i < 64; i++) {
		if (i % 2 == 0)
			indices[i] = (uint8_t)(i / 2);
		else
			indices[i] = (uint8_t)(64 + i / 2);
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vmovdqu8 (%2), %%zmm2\n\t"
		"vpermi2b %%zmm2, %%zmm1, %%zmm0\n\t"
		"vmovdqu8 %%zmm0, (%3)\n\t"
		:
		: "r"(indices), "r"(table0), "r"(table1), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t expected;

		if (i % 2 == 0)
			expected = (uint8_t)(i / 2 + 10);
		else
			expected = (uint8_t)(i / 2 + 80);

		if (c[i] != expected) {
			printf("FAIL avx512vbmi/vpermi2b: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512vbmi/vpermi2b: two-source byte permutation correct\n");
	return 0;
}

static int test_vpermt2b(void)
{
	/*
	 * vpermt2b: full byte permutation using two source tables.
	 * zmm2 has indices, zmm1 and zmm3 are the two tables.
	 * Result replaces zmm1 (first table).
	 *
	 * table0 (zmm1) = {0, 1, 2, ..., 63}
	 * table1 (zmm3) = {64, 65, 66, ..., 127}
	 * indices (zmm2) = {127, 126, 125, ..., 64, 63, 62, ..., 0}
	 *   i.e., reversed concatenation of both tables
	 */
	uint8_t table0[64] __attribute__((aligned(64)));
	uint8_t table1[64] __attribute__((aligned(64)));
	uint8_t indices[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		table0[i] = (uint8_t)i;
		table1[i] = (uint8_t)(i + 64);
		indices[i] = (uint8_t)(127 - i);
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vmovdqu8 (%2), %%zmm2\n\t"
		"vpermt2b %%zmm2, %%zmm1, %%zmm0\n\t"
		"vmovdqu8 %%zmm0, (%3)\n\t"
		:
		: "r"(table0), "r"(indices), "r"(table1), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t expected = (uint8_t)(127 - i);

		if (c[i] != expected) {
			printf("FAIL avx512vbmi/vpermt2b: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512vbmi/vpermt2b: two-table byte permutation correct\n");
	return 0;
}

int test_avx512vbmi_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpermb() == 0) passed++; else failed++;
	total++; if (test_vpermi2b() == 0) passed++; else failed++;
	total++; if (test_vpermt2b() == 0) passed++; else failed++;

	printf("\n=== avx512vbmi: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
