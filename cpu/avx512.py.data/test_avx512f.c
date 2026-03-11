/*
 * test_avx512f.c - AVX-512 Foundation (F) instruction tests
 *
 * Tests cover the core AVX-512F instruction set:
 *   Integer arithmetic: vpaddd, vpaddq, vpsubd, vpsubq, vpmulld, vpmuldq
 *   Logical: vpandd, vpord, vpxord, vpandnd, vpternlogd
 *   Shifts: vpslld/vpsrld/vpsrad (imm), vpsllq/vpsrlq/vpsraq (imm),
 *           vpsllvd/vpsrlvd (variable)
 *   Min/Max: vpminsd/vpmaxsd, vpminud/vpmaxud, vpminsq/vpmaxsq
 *   Abs: vpabsd, vpabsq
 *   Broadcast: vpbroadcastd, vpbroadcastq
 *   Permute: vpermd, vpermq
 *   Blend: vpblendmd (masked)
 *   Compress/Expand: vpcompressd, vpexpandd
 *   FP: vaddps/vaddpd, vmulps/vmulpd, vfmadd231ps/vfmadd231pd
 *   Convert: vcvtdq2ps, vcvtps2dq
 *   Unpack: vpunpckldq, vpunpckhdq
 *   Align: valignd
 *   Gather/Scatter: vpgatherdd, vpscatterdd
 *   Mask: kmovw, kandw, korw, knotw, kxorw
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

/* ---- Integer arithmetic ---- */

static int test_vpaddd(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (uint32_t)(i + 1);
		b[i] = (uint32_t)((i + 1) * 10);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpaddd %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		: : "r"(a), "r"(b), "r"(c) : "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected = (i + 1) + (i + 1) * 10;

		if (c[i] != expected) {
			printf("FAIL avx512f/vpaddd: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpaddd: packed 32-bit add correct\n");
	return 0;
}

static int test_vpaddq(void)
{
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t b[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (uint64_t)(i + 1) * 1000000000ULL;
		b[i] = (uint64_t)(i + 1) * 2000000000ULL;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vpaddq %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		: : "r"(a), "r"(b), "r"(c) : "memory"
	);

	for (i = 0; i < 8; i++) {
		uint64_t expected = (uint64_t)(i + 1) * 3000000000ULL;

		if (c[i] != expected) {
			printf("FAIL avx512f/vpaddq: c[%d]=%lu, expected %lu\n",
			       i, (unsigned long)c[i], (unsigned long)expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpaddq: packed 64-bit add correct\n");
	return 0;
}

static int test_vpsubd(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 1000;
		b[i] = (uint32_t)(i * 10);
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpsubd %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		: : "r"(a), "r"(b), "r"(c) : "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected = 1000 - i * 10;

		if (c[i] != expected) {
			printf("FAIL avx512f/vpsubd: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpsubd: packed 32-bit subtract correct\n");
	return 0;
}

static int test_vpsubq(void)
{
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t b[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 10000000000ULL;
		b[i] = (uint64_t)(i + 1) * 1000000000ULL;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vpsubq %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		: : "r"(a), "r"(b), "r"(c) : "memory"
	);

	for (i = 0; i < 8; i++) {
		uint64_t expected = 10000000000ULL - (uint64_t)(i + 1) * 1000000000ULL;

		if (c[i] != expected) {
			printf("FAIL avx512f/vpsubq: c[%d]=%lu, expected %lu\n",
			       i, (unsigned long)c[i], (unsigned long)expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpsubq: packed 64-bit subtract correct\n");
	return 0;
}

static int test_vpmulld(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (uint32_t)(i + 1);
		b[i] = 7;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpmulld %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		: : "r"(a), "r"(b), "r"(c) : "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected = (uint32_t)(i + 1) * 7;

		if (c[i] != expected) {
			printf("FAIL avx512f/vpmulld: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpmulld: packed 32-bit multiply low correct\n");
	return 0;
}

static int test_vpmuldq(void)
{
	/*
	 * vpmuldq: signed 32x32->64 multiply using even-indexed dwords.
	 * For each pair of even dwords: result[i] = (int64_t)a[2i] * (int64_t)b[2i]
	 */
	int32_t a[16] __attribute__((aligned(64)));
	int32_t b[16] __attribute__((aligned(64)));
	int64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (i % 2 == 0) ? (int32_t)(100000 + i) : 0;
		b[i] = (i % 2 == 0) ? (int32_t)(200000 + i) : 0;
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpmuldq %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		: : "r"(a), "r"(b), "r"(c) : "memory"
	);

	for (i = 0; i < 8; i++) {
		int64_t expected = (int64_t)(100000 + i * 2) * (int64_t)(200000 + i * 2);

		if (c[i] != expected) {
			printf("FAIL avx512f/vpmuldq: c[%d]=%ld, expected %ld\n",
			       i, (long)c[i], (long)expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpmuldq: signed 32x32->64 multiply correct\n");
	return 0;
}

/* ---- Logical operations ---- */

static int test_logical_d(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c_and[16] __attribute__((aligned(64)));
	uint32_t c_or[16] __attribute__((aligned(64)));
	uint32_t c_xor[16] __attribute__((aligned(64)));
	uint32_t c_andn[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0xFF00FF00;
		b[i] = 0x0FF00FF0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpandd %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpord %%zmm1, %%zmm0, %%zmm3\n\t"
		"vpxord %%zmm1, %%zmm0, %%zmm4\n\t"
		"vpandnd %%zmm1, %%zmm0, %%zmm5\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		"vmovdqu32 %%zmm3, (%3)\n\t"
		"vmovdqu32 %%zmm4, (%4)\n\t"
		"vmovdqu32 %%zmm5, (%5)\n\t"
		:
		: "r"(a), "r"(b), "r"(c_and), "r"(c_or), "r"(c_xor), "r"(c_andn)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c_and[i] != (0xFF00FF00 & 0x0FF00FF0)) {
			printf("FAIL avx512f/vpandd: c[%d]=0x%08x\n", i, c_and[i]);
			return 1;
		}
		if (c_or[i] != (0xFF00FF00 | 0x0FF00FF0)) {
			printf("FAIL avx512f/vpord: c[%d]=0x%08x\n", i, c_or[i]);
			return 1;
		}
		if (c_xor[i] != (0xFF00FF00 ^ 0x0FF00FF0)) {
			printf("FAIL avx512f/vpxord: c[%d]=0x%08x\n", i, c_xor[i]);
			return 1;
		}
		/* vpandnd: NOT(a) AND b */
		if (c_andn[i] != (~0xFF00FF00 & 0x0FF00FF0)) {
			printf("FAIL avx512f/vpandnd: c[%d]=0x%08x\n", i, c_andn[i]);
			return 1;
		}
	}
	printf("PASS avx512f/logical_d: AND/OR/XOR/ANDNOT correct\n");
	return 0;
}

static int test_vpternlogd(void)
{
	/*
	 * vpternlogd with imm=0x96 implements XOR of three inputs.
	 * a=0xFF00FF00, b=0x0FF00FF0, c=0x00FF00FF
	 * a XOR b XOR c = 0xF00FF00F
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t cv[16] __attribute__((aligned(64)));
	uint32_t r[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0xFF00FF00;
		b[i] = 0x0FF00FF0;
		cv[i] = 0x00FF00FF;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vmovdqu32 (%2), %%zmm2\n\t"
		"vpternlogd $0x96, %%zmm2, %%zmm1, %%zmm0\n\t"
		"vmovdqu32 %%zmm0, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(cv), "r"(r)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected = 0xFF00FF00 ^ 0x0FF00FF0 ^ 0x00FF00FF;

		if (r[i] != expected) {
			printf("FAIL avx512f/vpternlogd: r[%d]=0x%08x, expected 0x%08x\n",
			       i, r[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpternlogd: ternary logic (3-way XOR) correct\n");
	return 0;
}

/* ---- Shift operations ---- */

static int test_shift_d_imm(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t csll[16] __attribute__((aligned(64)));
	uint32_t csrl[16] __attribute__((aligned(64)));
	int32_t sa[16] __attribute__((aligned(64)));
	int32_t csra[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0x12345678;
		sa[i] = -1024;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vpslld $4, %%zmm0, %%zmm1\n\t"
		"vpsrld $4, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm1, (%1)\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		"vmovdqu32 (%3), %%zmm3\n\t"
		"vpsrad $2, %%zmm3, %%zmm4\n\t"
		"vmovdqu32 %%zmm4, (%4)\n\t"
		:
		: "r"(a), "r"(csll), "r"(csrl), "r"(sa), "r"(csra)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (csll[i] != (0x12345678u << 4)) {
			printf("FAIL avx512f/vpslld: c[%d]=0x%08x\n", i, csll[i]);
			return 1;
		}
		if (csrl[i] != (0x12345678u >> 4)) {
			printf("FAIL avx512f/vpsrld: c[%d]=0x%08x\n", i, csrl[i]);
			return 1;
		}
		if (csra[i] != (-1024 >> 2)) {
			printf("FAIL avx512f/vpsrad: c[%d]=%d, expected %d\n",
			       i, csra[i], -1024 >> 2);
			return 1;
		}
	}
	printf("PASS avx512f/shift_d_imm: 32-bit shifts (imm) correct\n");
	return 0;
}

static int test_shift_q_imm(void)
{
	uint64_t a[8] __attribute__((aligned(64)));
	uint64_t csll[8] __attribute__((aligned(64)));
	uint64_t csrl[8] __attribute__((aligned(64)));
	int64_t sa[8] __attribute__((aligned(64)));
	int64_t csra[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = 0x123456789ABCDEF0ULL;
		sa[i] = -4096;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vpsllq $8, %%zmm0, %%zmm1\n\t"
		"vpsrlq $8, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm1, (%1)\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		"vmovdqu64 (%3), %%zmm3\n\t"
		"vpsraq $4, %%zmm3, %%zmm4\n\t"
		"vmovdqu64 %%zmm4, (%4)\n\t"
		:
		: "r"(a), "r"(csll), "r"(csrl), "r"(sa), "r"(csra)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (csll[i] != (0x123456789ABCDEF0ULL << 8)) {
			printf("FAIL avx512f/vpsllq: c[%d]=0x%016lx\n",
			       i, (unsigned long)csll[i]);
			return 1;
		}
		if (csrl[i] != (0x123456789ABCDEF0ULL >> 8)) {
			printf("FAIL avx512f/vpsrlq: c[%d]=0x%016lx\n",
			       i, (unsigned long)csrl[i]);
			return 1;
		}
		/* vpsraq: arithmetic right shift of 64-bit (new in AVX-512F) */
		if (csra[i] != ((int64_t)-4096 >> 4)) {
			printf("FAIL avx512f/vpsraq: c[%d]=%ld, expected %ld\n",
			       i, (long)csra[i], (long)((int64_t)-4096 >> 4));
			return 1;
		}
	}
	printf("PASS avx512f/shift_q_imm: 64-bit shifts (imm) correct\n");
	return 0;
}

static int test_shift_d_var(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t counts[16] __attribute__((aligned(64)));
	uint32_t csll[16] __attribute__((aligned(64)));
	uint32_t csrl[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0xFF000000;
		counts[i] = (uint32_t)(i % 8);
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpsllvd %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpsrlvd %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		"vmovdqu32 %%zmm3, (%3)\n\t"
		:
		: "r"(a), "r"(counts), "r"(csll), "r"(csrl)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t shift = (uint32_t)(i % 8);
		uint32_t esll = 0xFF000000u << shift;
		uint32_t esrl = 0xFF000000u >> shift;

		if (csll[i] != esll) {
			printf("FAIL avx512f/vpsllvd: c[%d]=0x%08x, expected 0x%08x\n",
			       i, csll[i], esll);
			return 1;
		}
		if (csrl[i] != esrl) {
			printf("FAIL avx512f/vpsrlvd: c[%d]=0x%08x, expected 0x%08x\n",
			       i, csrl[i], esrl);
			return 1;
		}
	}
	printf("PASS avx512f/shift_d_var: 32-bit variable shifts correct\n");
	return 0;
}

/* ---- Min/Max ---- */

static int test_minmax_sd(void)
{
	int32_t a[16] __attribute__((aligned(64)));
	int32_t b[16] __attribute__((aligned(64)));
	int32_t cmin[16] __attribute__((aligned(64)));
	int32_t cmax[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (int32_t)(i * 10 - 80);
		b[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpminsd %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpmaxsd %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		"vmovdqu32 %%zmm3, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(cmin), "r"(cmax)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		int32_t v = (int32_t)(i * 10 - 80);
		int32_t emin = (v < 0) ? v : 0;
		int32_t emax = (v > 0) ? v : 0;

		if (cmin[i] != emin || cmax[i] != emax) {
			printf("FAIL avx512f/minmax_sd: i=%d, min=%d/%d, max=%d/%d\n",
			       i, cmin[i], emin, cmax[i], emax);
			return 1;
		}
	}
	printf("PASS avx512f/minmax_sd: signed 32-bit min/max correct\n");
	return 0;
}

static int test_minmax_ud(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t cmin[16] __attribute__((aligned(64)));
	uint32_t cmax[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (uint32_t)(i * 20);
		b[i] = 150;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpminud %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpmaxud %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		"vmovdqu32 %%zmm3, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(cmin), "r"(cmax)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t v = (uint32_t)(i * 20);
		uint32_t emin = (v < 150) ? v : 150;
		uint32_t emax = (v > 150) ? v : 150;

		if (cmin[i] != emin || cmax[i] != emax) {
			printf("FAIL avx512f/minmax_ud: i=%d\n", i);
			return 1;
		}
	}
	printf("PASS avx512f/minmax_ud: unsigned 32-bit min/max correct\n");
	return 0;
}

static int test_minmax_sq(void)
{
	int64_t a[8] __attribute__((aligned(64)));
	int64_t b[8] __attribute__((aligned(64)));
	int64_t cmin[8] __attribute__((aligned(64)));
	int64_t cmax[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (int64_t)(i * 100 - 350);
		b[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vpminsq %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpmaxsq %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		"vmovdqu64 %%zmm3, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(cmin), "r"(cmax)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		int64_t v = (int64_t)(i * 100 - 350);
		int64_t emin = (v < 0) ? v : 0;
		int64_t emax = (v > 0) ? v : 0;

		if (cmin[i] != emin || cmax[i] != emax) {
			printf("FAIL avx512f/minmax_sq: i=%d\n", i);
			return 1;
		}
	}
	printf("PASS avx512f/minmax_sq: signed 64-bit min/max correct\n");
	return 0;
}

/* ---- Absolute value ---- */

static int test_vpabsd(void)
{
	int32_t a[16] __attribute__((aligned(64)));
	int32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = -(i + 1) * 100;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vpabsd %%zmm0, %%zmm1\n\t"
		"vmovdqu32 %%zmm1, (%1)\n\t"
		: : "r"(a), "r"(c) : "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != (i + 1) * 100) {
			printf("FAIL avx512f/vpabsd: c[%d]=%d, expected %d\n",
			       i, c[i], (i + 1) * 100);
			return 1;
		}
	}
	printf("PASS avx512f/vpabsd: packed 32-bit absolute value correct\n");
	return 0;
}

static int test_vpabsq(void)
{
	int64_t a[8] __attribute__((aligned(64)));
	int64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = -(int64_t)(i + 1) * 1000000;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vpabsq %%zmm0, %%zmm1\n\t"
		"vmovdqu64 %%zmm1, (%1)\n\t"
		: : "r"(a), "r"(c) : "memory"
	);

	for (i = 0; i < 8; i++) {
		int64_t expected = (int64_t)(i + 1) * 1000000;

		if (c[i] != expected) {
			printf("FAIL avx512f/vpabsq: c[%d]=%ld, expected %ld\n",
			       i, (long)c[i], (long)expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpabsq: packed 64-bit absolute value correct\n");
	return 0;
}

/* ---- Broadcast ---- */

static int test_broadcast(void)
{
	uint32_t dval = 12345;
	uint64_t qval = 9876543210ULL;
	uint32_t cd[16] __attribute__((aligned(64)));
	uint64_t cq[8] __attribute__((aligned(64)));
	int i;

	memset(cd, 0, sizeof(cd));
	memset(cq, 0, sizeof(cq));

	asm volatile(
		"vpbroadcastd %2, %%zmm0\n\t"
		"vmovdqu32 %%zmm0, (%0)\n\t"
		"vpbroadcastq %3, %%zmm1\n\t"
		"vmovdqu64 %%zmm1, (%1)\n\t"
		:
		: "r"(cd), "r"(cq), "m"(dval), "m"(qval)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (cd[i] != 12345) {
			printf("FAIL avx512f/vpbroadcastd: c[%d]=%u\n", i, cd[i]);
			return 1;
		}
	}
	for (i = 0; i < 8; i++) {
		if (cq[i] != 9876543210ULL) {
			printf("FAIL avx512f/vpbroadcastq: c[%d]=%lu\n",
			       i, (unsigned long)cq[i]);
			return 1;
		}
	}
	printf("PASS avx512f/broadcast: 32-bit and 64-bit broadcast correct\n");
	return 0;
}

/* ---- Permute ---- */

static int test_vpermd(void)
{
	uint32_t src[16] __attribute__((aligned(64)));
	uint32_t idx[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		src[i] = (uint32_t)(i * 100);
		idx[i] = (uint32_t)(15 - i);
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpermd %%zmm0, %%zmm1, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		: : "r"(src), "r"(idx), "r"(c) : "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected = (uint32_t)((15 - i) * 100);

		if (c[i] != expected) {
			printf("FAIL avx512f/vpermd: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpermd: packed 32-bit permute correct\n");
	return 0;
}

static int test_vpermq(void)
{
	uint64_t src[8] __attribute__((aligned(64)));
	uint64_t idx[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		src[i] = (uint64_t)(i * 1000);
		idx[i] = (uint64_t)(7 - i);
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vpermq %%zmm0, %%zmm1, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		: : "r"(src), "r"(idx), "r"(c) : "memory"
	);

	for (i = 0; i < 8; i++) {
		uint64_t expected = (uint64_t)((7 - i) * 1000);

		if (c[i] != expected) {
			printf("FAIL avx512f/vpermq: c[%d]=%lu, expected %lu\n",
			       i, (unsigned long)c[i], (unsigned long)expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpermq: packed 64-bit permute correct\n");
	return 0;
}

/* ---- Blend with mask ---- */

static int test_vpblendmd(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	unsigned int mask = 0xAAAA; /* odd lanes from b, even from a */
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 1;
		b[i] = 2;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"kmovw %3, %%k1\n\t"
		"vpblendmd %%zmm1, %%zmm0, %%zmm2 %{%%k1%}\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c), "r"(mask)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected = (i % 2 == 0) ? 1 : 2;

		if (c[i] != expected) {
			printf("FAIL avx512f/vpblendmd: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpblendmd: masked 32-bit blend correct\n");
	return 0;
}

/* ---- Compress / Expand ---- */

static int test_compress_expand_d(void)
{
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t compressed[16] __attribute__((aligned(64)));
	uint32_t expanded[16] __attribute__((aligned(64)));
	unsigned int mask = 0x5555; /* even elements */
	int i;

	for (i = 0; i < 16; i++)
		a[i] = (uint32_t)(i * 10);

	memset(compressed, 0, sizeof(compressed));
	memset(expanded, 0, sizeof(expanded));

	/* Compress: select even-indexed elements -> contiguous output */
	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"kmovw %2, %%k1\n\t"
		"vpxord %%zmm1, %%zmm1, %%zmm1\n\t"
		"vpcompressd %%zmm0, %%zmm1 %{%%k1%}\n\t"
		"vmovdqu32 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(compressed), "r"(mask)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		uint32_t expected = (uint32_t)(i * 2 * 10);

		if (compressed[i] != expected) {
			printf("FAIL avx512f/vpcompressd: c[%d]=%u, expected %u\n",
			       i, compressed[i], expected);
			return 1;
		}
	}

	/* Expand: spread 8 contiguous values to even positions */
	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"kmovw %2, %%k1\n\t"
		"vpxord %%zmm1, %%zmm1, %%zmm1\n\t"
		"vpexpandd %%zmm0, %%zmm1 %{%%k1%}\n\t"
		"vmovdqu32 %%zmm1, (%1)\n\t"
		:
		: "r"(compressed), "r"(expanded), "r"(mask)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (expanded[i * 2] != compressed[i]) {
			printf("FAIL avx512f/vpexpandd: c[%d]=%u, expected %u\n",
			       i * 2, expanded[i * 2], compressed[i]);
			return 1;
		}
	}
	printf("PASS avx512f/compress_expand_d: 32-bit compress/expand correct\n");
	return 0;
}

/* ---- Floating point ---- */

static int test_fp_add(void)
{
	float ps_a[16] __attribute__((aligned(64)));
	float ps_b[16] __attribute__((aligned(64)));
	float ps_c[16] __attribute__((aligned(64)));
	double pd_a[8] __attribute__((aligned(64)));
	double pd_b[8] __attribute__((aligned(64)));
	double pd_c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		ps_a[i] = (float)(i + 1);
		ps_b[i] = 0.5f;
	}
	for (i = 0; i < 8; i++) {
		pd_a[i] = (double)(i + 1);
		pd_b[i] = 0.25;
	}

	memset(ps_c, 0, sizeof(ps_c));
	memset(pd_c, 0, sizeof(pd_c));

	asm volatile(
		"vmovups (%0), %%zmm0\n\t"
		"vmovups (%1), %%zmm1\n\t"
		"vaddps %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovups %%zmm2, (%2)\n\t"
		"vmovupd (%3), %%zmm3\n\t"
		"vmovupd (%4), %%zmm4\n\t"
		"vaddpd %%zmm4, %%zmm3, %%zmm5\n\t"
		"vmovupd %%zmm5, (%5)\n\t"
		:
		: "r"(ps_a), "r"(ps_b), "r"(ps_c),
		  "r"(pd_a), "r"(pd_b), "r"(pd_c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		float expected = (float)(i + 1) + 0.5f;

		if (ps_c[i] != expected) {
			printf("FAIL avx512f/vaddps: c[%d]=%f, expected %f\n",
			       i, ps_c[i], expected);
			return 1;
		}
	}
	for (i = 0; i < 8; i++) {
		double expected = (double)(i + 1) + 0.25;

		if (pd_c[i] != expected) {
			printf("FAIL avx512f/vaddpd: c[%d]=%f, expected %f\n",
			       i, pd_c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/fp_add: vaddps and vaddpd correct\n");
	return 0;
}

static int test_fp_mul(void)
{
	float ps_a[16] __attribute__((aligned(64)));
	float ps_b[16] __attribute__((aligned(64)));
	float ps_c[16] __attribute__((aligned(64)));
	double pd_a[8] __attribute__((aligned(64)));
	double pd_b[8] __attribute__((aligned(64)));
	double pd_c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		ps_a[i] = (float)(i + 1);
		ps_b[i] = 2.0f;
	}
	for (i = 0; i < 8; i++) {
		pd_a[i] = (double)(i + 1);
		pd_b[i] = 3.0;
	}

	memset(ps_c, 0, sizeof(ps_c));
	memset(pd_c, 0, sizeof(pd_c));

	asm volatile(
		"vmovups (%0), %%zmm0\n\t"
		"vmovups (%1), %%zmm1\n\t"
		"vmulps %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovups %%zmm2, (%2)\n\t"
		"vmovupd (%3), %%zmm3\n\t"
		"vmovupd (%4), %%zmm4\n\t"
		"vmulpd %%zmm4, %%zmm3, %%zmm5\n\t"
		"vmovupd %%zmm5, (%5)\n\t"
		:
		: "r"(ps_a), "r"(ps_b), "r"(ps_c),
		  "r"(pd_a), "r"(pd_b), "r"(pd_c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		float expected = (float)(i + 1) * 2.0f;

		if (ps_c[i] != expected) {
			printf("FAIL avx512f/vmulps: c[%d]=%f, expected %f\n",
			       i, ps_c[i], expected);
			return 1;
		}
	}
	for (i = 0; i < 8; i++) {
		double expected = (double)(i + 1) * 3.0;

		if (pd_c[i] != expected) {
			printf("FAIL avx512f/vmulpd: c[%d]=%f, expected %f\n",
			       i, pd_c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/fp_mul: vmulps and vmulpd correct\n");
	return 0;
}

static int test_fma(void)
{
	/*
	 * vfmadd231ps: dst = dst + a * b  (single-precision)
	 * vfmadd231pd: dst = dst + a * b  (double-precision)
	 *
	 * a=2.0, b=3.0, dst(accum)=10.0 -> result = 10 + 2*3 = 16
	 */
	float ps_a[16] __attribute__((aligned(64)));
	float ps_b[16] __attribute__((aligned(64)));
	float ps_c[16] __attribute__((aligned(64)));
	double pd_a[8] __attribute__((aligned(64)));
	double pd_b[8] __attribute__((aligned(64)));
	double pd_c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		ps_a[i] = 2.0f;
		ps_b[i] = 3.0f;
		ps_c[i] = 10.0f;
	}
	for (i = 0; i < 8; i++) {
		pd_a[i] = 2.0;
		pd_b[i] = 3.0;
		pd_c[i] = 10.0;
	}

	asm volatile(
		"vmovups (%0), %%zmm0\n\t"
		"vmovups (%1), %%zmm1\n\t"
		"vmovups (%2), %%zmm2\n\t"
		"vfmadd231ps %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovups %%zmm2, (%2)\n\t"
		"vmovupd (%3), %%zmm3\n\t"
		"vmovupd (%4), %%zmm4\n\t"
		"vmovupd (%5), %%zmm5\n\t"
		"vfmadd231pd %%zmm4, %%zmm3, %%zmm5\n\t"
		"vmovupd %%zmm5, (%5)\n\t"
		:
		: "r"(ps_a), "r"(ps_b), "r"(ps_c),
		  "r"(pd_a), "r"(pd_b), "r"(pd_c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (ps_c[i] != 16.0f) {
			printf("FAIL avx512f/vfmadd231ps: c[%d]=%f, expected 16.0\n",
			       i, ps_c[i]);
			return 1;
		}
	}
	for (i = 0; i < 8; i++) {
		if (pd_c[i] != 16.0) {
			printf("FAIL avx512f/vfmadd231pd: c[%d]=%f, expected 16.0\n",
			       i, pd_c[i]);
			return 1;
		}
	}
	printf("PASS avx512f/fma: vfmadd231ps and vfmadd231pd correct\n");
	return 0;
}

/* ---- Convert ---- */

static int test_convert(void)
{
	int32_t ia[16] __attribute__((aligned(64)));
	float fc[16] __attribute__((aligned(64)));
	float fa[16] __attribute__((aligned(64)));
	int32_t ic[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		ia[i] = (i + 1) * 100;
		fa[i] = (float)((i + 1) * 100);
	}

	memset(fc, 0, sizeof(fc));
	memset(ic, 0, sizeof(ic));

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vcvtdq2ps %%zmm0, %%zmm1\n\t"
		"vmovups %%zmm1, (%1)\n\t"
		"vmovups (%2), %%zmm2\n\t"
		"vcvtps2dq %%zmm2, %%zmm3\n\t"
		"vmovdqu32 %%zmm3, (%3)\n\t"
		:
		: "r"(ia), "r"(fc), "r"(fa), "r"(ic)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		float ef = (float)((i + 1) * 100);

		if (fc[i] != ef) {
			printf("FAIL avx512f/vcvtdq2ps: c[%d]=%f, expected %f\n",
			       i, fc[i], ef);
			return 1;
		}
		if (ic[i] != (i + 1) * 100) {
			printf("FAIL avx512f/vcvtps2dq: c[%d]=%d, expected %d\n",
			       i, ic[i], (i + 1) * 100);
			return 1;
		}
	}
	printf("PASS avx512f/convert: vcvtdq2ps and vcvtps2dq correct\n");
	return 0;
}

/* ---- Unpack ---- */

static int test_unpack_d(void)
{
	/*
	 * vpunpckldq: interleave low dwords from each 128-bit lane.
	 * vpunpckhdq: interleave high dwords from each 128-bit lane.
	 *
	 * Within each 128-bit lane (4 dwords each):
	 *   a = {A0, A1, A2, A3}, b = {B0, B1, B2, B3}
	 *   unpack_lo = {A0, B0, A1, B1}
	 *   unpack_hi = {A2, B2, A3, B3}
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c_lo[16] __attribute__((aligned(64)));
	uint32_t c_hi[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (uint32_t)(i + 100);
		b[i] = (uint32_t)(i + 200);
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vpunpckldq %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpunpckhdq %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		"vmovdqu32 %%zmm3, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(c_lo), "r"(c_hi)
		: "memory"
	);

	for (i = 0; i < 16; i += 4) {
		if (c_lo[i] != a[i] || c_lo[i+1] != b[i] ||
		    c_lo[i+2] != a[i+1] || c_lo[i+3] != b[i+1]) {
			printf("FAIL avx512f/vpunpckldq at lane %d\n", i / 4);
			return 1;
		}
		if (c_hi[i] != a[i+2] || c_hi[i+1] != b[i+2] ||
		    c_hi[i+2] != a[i+3] || c_hi[i+3] != b[i+3]) {
			printf("FAIL avx512f/vpunpckhdq at lane %d\n", i / 4);
			return 1;
		}
	}
	printf("PASS avx512f/unpack_d: 32-bit unpack low/high correct\n");
	return 0;
}

/* ---- Align ---- */

static int test_valignd(void)
{
	/*
	 * valignd: concatenate two vectors and extract 16 contiguous dwords
	 * starting at byte offset imm*4.
	 *
	 * a = {0,1,...,15}, b = {16,17,...,31}
	 * valignd $4, zmm_b, zmm_a: conceptually concat(b,a) then take elements [4..19]
	 * Result = {4,5,6,...,15,16,17,18,19}
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (uint32_t)i;
		b[i] = (uint32_t)(i + 16);
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"valignd $4, %%zmm0, %%zmm1, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		: : "r"(a), "r"(b), "r"(c) : "memory"
	);

	for (i = 0; i < 16; i++) {
		uint32_t expected;

		if (i + 4 < 16)
			expected = a[i + 4];
		else
			expected = b[i + 4 - 16];

		if (c[i] != expected) {
			printf("FAIL avx512f/valignd: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/valignd: 32-bit vector align correct\n");
	return 0;
}

/* ---- Gather ---- */

static int test_vpgatherdd(void)
{
	/*
	 * vpgatherdd: gather 32-bit elements from memory using 32-bit indices.
	 * table[i] = i*100, indices = {0,2,4,...,30}
	 * Expected: {0, 200, 400, ..., 3000}
	 */
	int32_t table[32] __attribute__((aligned(64)));
	int32_t indices[16] __attribute__((aligned(64)));
	int32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++)
		table[i] = i * 100;

	for (i = 0; i < 16; i++)
		indices[i] = i * 2;

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu32 (%0), %%zmm1\n\t"
		"vpxord %%zmm0, %%zmm0, %%zmm0\n\t"
		"kxnorw %%k1, %%k1, %%k1\n\t"
		"vpgatherdd (%1,%%zmm1,4), %%zmm0 %{%%k1%}\n\t"
		"vmovdqu32 %%zmm0, (%2)\n\t"
		:
		: "r"(indices), "r"(table), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		int32_t expected = (i * 2) * 100;

		if (c[i] != expected) {
			printf("FAIL avx512f/vpgatherdd: c[%d]=%d, expected %d\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpgatherdd: 32-bit gather correct\n");
	return 0;
}

/* ---- Scatter ---- */

static int test_vpscatterdd(void)
{
	/*
	 * vpscatterdd: scatter 32-bit elements to memory using 32-bit indices.
	 * Scatter values {10, 20, ..., 160} to even positions.
	 */
	int32_t values[16] __attribute__((aligned(64)));
	int32_t indices[16] __attribute__((aligned(64)));
	int32_t table[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		values[i] = (i + 1) * 10;
		indices[i] = i * 2;
	}

	memset(table, 0, sizeof(table));

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"kxnorw %%k1, %%k1, %%k1\n\t"
		"vpscatterdd %%zmm0, (%2,%%zmm1,4) %{%%k1%}\n\t"
		:
		: "r"(values), "r"(indices), "r"(table)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		int32_t expected = (i + 1) * 10;

		if (table[i * 2] != expected) {
			printf("FAIL avx512f/vpscatterdd: table[%d]=%d, expected %d\n",
			       i * 2, table[i * 2], expected);
			return 1;
		}
	}
	printf("PASS avx512f/vpscatterdd: 32-bit scatter correct\n");
	return 0;
}

/* ---- Mask operations ---- */

static int test_mask_ops(void)
{
	unsigned int m1 = 0xAAAA, m2 = 0x5555;
	unsigned int r_and, r_or, r_xor, r_not;

	asm volatile(
		"kmovw %[m1], %%k1\n\t"
		"kmovw %[m2], %%k2\n\t"
		"kandw %%k2, %%k1, %%k3\n\t"
		"kmovw %%k3, %[ra]\n\t"
		"korw %%k2, %%k1, %%k3\n\t"
		"kmovw %%k3, %[ro]\n\t"
		"kxorw %%k2, %%k1, %%k3\n\t"
		"kmovw %%k3, %[rx]\n\t"
		"knotw %%k1, %%k3\n\t"
		"kmovw %%k3, %[rn]\n\t"
		: [ra] "=r"(r_and), [ro] "=r"(r_or),
		  [rx] "=r"(r_xor), [rn] "=r"(r_not)
		: [m1] "r"(m1), [m2] "r"(m2)
	);

	r_and &= 0xFFFF;
	r_or &= 0xFFFF;
	r_xor &= 0xFFFF;
	r_not &= 0xFFFF;

	if (r_and != (0xAAAA & 0x5555)) {
		printf("FAIL avx512f/kandw: got 0x%04x, expected 0x%04x\n",
		       r_and, 0xAAAA & 0x5555);
		return 1;
	}
	if (r_or != (0xAAAA | 0x5555)) {
		printf("FAIL avx512f/korw: got 0x%04x, expected 0x%04x\n",
		       r_or, 0xAAAA | 0x5555);
		return 1;
	}
	if (r_xor != (0xAAAA ^ 0x5555)) {
		printf("FAIL avx512f/kxorw: got 0x%04x, expected 0x%04x\n",
		       r_xor, 0xAAAA ^ 0x5555);
		return 1;
	}
	if (r_not != (uint16_t)(~0xAAAA)) {
		printf("FAIL avx512f/knotw: got 0x%04x, expected 0x%04x\n",
		       r_not, (uint16_t)(~0xAAAA));
		return 1;
	}
	printf("PASS avx512f/mask_ops: kmovw/kandw/korw/kxorw/knotw correct\n");
	return 0;
}

/* ---- Test suite entry point ---- */

int test_avx512f_all(void)
{
	int total = 0, passed = 0, failed = 0;

	/* Integer arithmetic */
	total++; if (test_vpaddd() == 0) passed++; else failed++;
	total++; if (test_vpaddq() == 0) passed++; else failed++;
	total++; if (test_vpsubd() == 0) passed++; else failed++;
	total++; if (test_vpsubq() == 0) passed++; else failed++;
	total++; if (test_vpmulld() == 0) passed++; else failed++;
	total++; if (test_vpmuldq() == 0) passed++; else failed++;

	/* Logical */
	total++; if (test_logical_d() == 0) passed++; else failed++;
	total++; if (test_vpternlogd() == 0) passed++; else failed++;

	/* Shifts */
	total++; if (test_shift_d_imm() == 0) passed++; else failed++;
	total++; if (test_shift_q_imm() == 0) passed++; else failed++;
	total++; if (test_shift_d_var() == 0) passed++; else failed++;

	/* Min/Max */
	total++; if (test_minmax_sd() == 0) passed++; else failed++;
	total++; if (test_minmax_ud() == 0) passed++; else failed++;
	total++; if (test_minmax_sq() == 0) passed++; else failed++;

	/* Absolute value */
	total++; if (test_vpabsd() == 0) passed++; else failed++;
	total++; if (test_vpabsq() == 0) passed++; else failed++;

	/* Broadcast */
	total++; if (test_broadcast() == 0) passed++; else failed++;

	/* Permute */
	total++; if (test_vpermd() == 0) passed++; else failed++;
	total++; if (test_vpermq() == 0) passed++; else failed++;

	/* Blend */
	total++; if (test_vpblendmd() == 0) passed++; else failed++;

	/* Compress/Expand */
	total++; if (test_compress_expand_d() == 0) passed++; else failed++;

	/* Floating point */
	total++; if (test_fp_add() == 0) passed++; else failed++;
	total++; if (test_fp_mul() == 0) passed++; else failed++;
	total++; if (test_fma() == 0) passed++; else failed++;

	/* Convert */
	total++; if (test_convert() == 0) passed++; else failed++;

	/* Unpack */
	total++; if (test_unpack_d() == 0) passed++; else failed++;

	/* Align */
	total++; if (test_valignd() == 0) passed++; else failed++;

	/* Gather/Scatter */
	total++; if (test_vpgatherdd() == 0) passed++; else failed++;
	total++; if (test_vpscatterdd() == 0) passed++; else failed++;

	/* Mask operations */
	total++; if (test_mask_ops() == 0) passed++; else failed++;

	printf("\n=== avx512f: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
