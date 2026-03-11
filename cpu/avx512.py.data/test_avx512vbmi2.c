/*
 * test_avx512vbmi2.c - AVX-512 Vector Byte Manipulation Instructions 2 (VBMI2) tests
 *
 * Tests: vpcompressb, vpcompressw, vpexpandb, vpexpandw,
 *        vpshldd, vpshldq, vpshrdd, vpshrdq
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpcompressb(void)
{
	/*
	 * vpcompressb: compress bytes selected by mask into contiguous output.
	 * Use all-ones mask (identity: output equals input).
	 */
	uint8_t a[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		a[i] = (uint8_t)(i + 10);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"kxnorq %%k1, %%k1, %%k1\n\t"
		"vpcompressb %%zmm0, %%zmm1 %{%%k1%}\n\t"
		"vmovdqu8 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t expected = (uint8_t)(i + 10);

		if (c[i] != expected) {
			printf("FAIL avx512_vbmi2/vpcompressb: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512_vbmi2/vpcompressb: byte compress with all-ones mask correct\n");
	return 0;
}

static int test_vpcompressw(void)
{
	/*
	 * vpcompressw: compress words by mask.
	 * Mask selects even-indexed words; they get packed contiguously.
	 */
	uint16_t a[32] __attribute__((aligned(64)));
	uint16_t c[32] __attribute__((aligned(64)));
	unsigned int mask = 0x55555555;
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = (uint16_t)(i * 100);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"kmovd %2, %%k1\n\t"
		"vpxord %%zmm1, %%zmm1, %%zmm1\n\t"
		"vpcompressw %%zmm0, %%zmm1 %{%%k1%}\n\t"
		"vmovdqu16 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c), "r"(mask)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		uint16_t expected = (uint16_t)(i * 2 * 100);

		if (c[i] != expected) {
			printf("FAIL avx512_vbmi2/vpcompressw: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512_vbmi2/vpcompressw: word compress with even-mask correct\n");
	return 0;
}

static int test_vpexpandb(void)
{
	/*
	 * vpexpandb: expand contiguous bytes to positions indicated by mask.
	 * All-ones mask = identity (output equals input).
	 */
	uint8_t a[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		a[i] = (uint8_t)(i + 20);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"kxnorq %%k1, %%k1, %%k1\n\t"
		"vpxord %%zmm1, %%zmm1, %%zmm1\n\t"
		"vpexpandb %%zmm0, %%zmm1 %{%%k1%}\n\t"
		"vmovdqu8 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t expected = (uint8_t)(i + 20);

		if (c[i] != expected) {
			printf("FAIL avx512_vbmi2/vpexpandb: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512_vbmi2/vpexpandb: byte expand with all-ones mask correct\n");
	return 0;
}

static int test_vpexpandw(void)
{
	/*
	 * vpexpandw: expand contiguous words to mask positions.
	 * All-ones mask = identity.
	 */
	uint16_t a[32] __attribute__((aligned(64)));
	uint16_t c[32] __attribute__((aligned(64)));
	unsigned int mask = 0xFFFFFFFF;
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = (uint16_t)(i * 10);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"kmovd %2, %%k1\n\t"
		"vpxord %%zmm1, %%zmm1, %%zmm1\n\t"
		"vpexpandw %%zmm0, %%zmm1 %{%%k1%}\n\t"
		"vmovdqu16 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c), "r"(mask)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		uint16_t expected = (uint16_t)(i * 10);

		if (c[i] != expected) {
			printf("FAIL avx512_vbmi2/vpexpandw: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512_vbmi2/vpexpandw: word expand with all-ones mask correct\n");
	return 0;
}

static int test_vpshldd(void)
{
	/*
	 * vpshldd: double-precision shift left on 32-bit elements (funnel shift).
	 * For each lane: result = (src1 << count) | (src2 >> (32 - count))
	 *
	 * src1 = 0x12345678, src2 = 0xAABBCCDD, count = 4
	 * result = (0x12345678 << 4) | (0xAABBCCDD >> 28)
	 *        = 0x23456780 | 0x0000000A = 0x2345678A
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0x12345678;
		b[i] = 0xAABBCCDD;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpshldd $4, %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != 0x2345678A) {
			printf("FAIL avx512_vbmi2/vpshldd: c[%d]=0x%08x, expected 0x2345678A\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512_vbmi2/vpshldd: 32-bit funnel shift left correct\n");
	return 0;
}

static int test_vpshldq(void)
{
	/*
	 * vpshldq: 64-bit funnel shift left.
	 * src1 = 0x123456789ABCDEF0, src2 = 0xFEDCBA9876543210, count = 8
	 * result = (src1 << 8) | (src2 >> 56)
	 *        = 0x3456789ABCDEF000 | 0x00000000000000FE
	 *        = 0x3456789ABCDEF0FE
	 */
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t b[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 0x123456789ABCDEF0ULL;
		b[i] = 0xFEDCBA9876543210ULL;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vpshldq $8, %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (c[i] != 0x3456789ABCDEF0FEULL) {
			printf("FAIL avx512_vbmi2/vpshldq: c[%d]=0x%016lx, expected 0x3456789ABCDEF0FE\n",
			       i, (unsigned long)c[i]);
			return 1;
		}
	}
	printf("PASS avx512_vbmi2/vpshldq: 64-bit funnel shift left correct\n");
	return 0;
}

static int test_vpshrdd(void)
{
	/*
	 * vpshrdd: 32-bit funnel shift right.
	 * result = (src1 >> count) | (src2 << (32 - count))
	 *
	 * src1 = 0x12345678, src2 = 0xAABBCCDD, count = 4
	 * result = (0x12345678 >> 4) | (0xAABBCCDD << 28)
	 *        = 0x01234567 | 0xD0000000 = 0xD1234567
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0x12345678;
		b[i] = 0xAABBCCDD;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpshrdd $4, %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != 0xD1234567) {
			printf("FAIL avx512_vbmi2/vpshrdd: c[%d]=0x%08x, expected 0xD1234567\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512_vbmi2/vpshrdd: 32-bit funnel shift right correct\n");
	return 0;
}

static int test_vpshrdq(void)
{
	/*
	 * vpshrdq: 64-bit funnel shift right.
	 * src1 = 0x123456789ABCDEF0, src2 = 0xFEDCBA9876543210, count = 8
	 * result = (src1 >> 8) | (src2 << 56)
	 *        = 0x00123456789ABCDE | 0x1000000000000000
	 *        = 0x10123456789ABCDE
	 */
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t b[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 0x123456789ABCDEF0ULL;
		b[i] = 0xFEDCBA9876543210ULL;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vpshrdq $8, %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (c[i] != 0x10123456789ABCDEULL) {
			printf("FAIL avx512_vbmi2/vpshrdq: c[%d]=0x%016lx, expected 0x10123456789ABCDE\n",
			       i, (unsigned long)c[i]);
			return 1;
		}
	}
	printf("PASS avx512_vbmi2/vpshrdq: 64-bit funnel shift right correct\n");
	return 0;
}

int test_avx512vbmi2_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpcompressb() == 0) passed++; else failed++;
	total++; if (test_vpcompressw() == 0) passed++; else failed++;
	total++; if (test_vpexpandb() == 0) passed++; else failed++;
	total++; if (test_vpexpandw() == 0) passed++; else failed++;
	total++; if (test_vpshldd() == 0) passed++; else failed++;
	total++; if (test_vpshldq() == 0) passed++; else failed++;
	total++; if (test_vpshrdd() == 0) passed++; else failed++;
	total++; if (test_vpshrdq() == 0) passed++; else failed++;

	printf("\n=== avx512_vbmi2: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
