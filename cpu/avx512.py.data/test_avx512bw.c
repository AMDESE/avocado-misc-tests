/*
 * test_avx512bw.c - AVX-512 Byte and Word (BW) instruction tests
 *
 * Tests: vpaddb, vpsubb, vpaddw, vpsubw, vpaddsb, vpaddusb, vpaddsw, vpaddusw,
 *        vpmullw, vpmulhw, vpmulhuw, vpavgb, vpavgw, vpmaddwd, vpmaddubsw,
 *        vpminub/vpmaxub/vpminsb/vpmaxsb, vpminuw/vpmaxuw/vpminsw/vpmaxsw,
 *        vpabsb, vpabsw, vpshufb, vpsllw/vpsrlw/vpsraw, vpsllvw/vpsrlvw,
 *        vpacksswb, vpackuswb, vpunpcklbw, vpunpckhbw, vpmovwb,
 *        vpsadbw, vpermw, vpblendmb, vpbroadcastb/vpbroadcastw
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpaddb_vpsubb(void)
{
	uint8_t a[64] __attribute__((aligned(64)));
	uint8_t b[64] __attribute__((aligned(64)));
	uint8_t c_add[64] __attribute__((aligned(64)));
	uint8_t c_sub[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		a[i] = (uint8_t)(i + 10);
		b[i] = (uint8_t)(i & 0x0F);
	}

	memset(c_add, 0, 64);
	memset(c_sub, 0, 64);

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpaddb %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpsubb %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		"vmovdqu8 %%zmm3, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(c_add), "r"(c_sub)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t ea = (uint8_t)((i + 10) + (i & 0x0F));
		uint8_t es = (uint8_t)((i + 10) - (i & 0x0F));

		if (c_add[i] != ea) {
			printf("FAIL avx512bw/vpaddb: c[%d]=%u, expected %u\n",
			       i, c_add[i], ea);
			return 1;
		}
		if (c_sub[i] != es) {
			printf("FAIL avx512bw/vpsubb: c[%d]=%u, expected %u\n",
			       i, c_sub[i], es);
			return 1;
		}
	}
	printf("PASS avx512bw/vpaddb_vpsubb: packed byte add/subtract correct\n");
	return 0;
}

static int test_vpaddw_vpsubw(void)
{
	uint16_t a[32] __attribute__((aligned(64)));
	uint16_t b[32] __attribute__((aligned(64)));
	uint16_t c_add[32] __attribute__((aligned(64)));
	uint16_t c_sub[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = (uint16_t)(i * 100);
		b[i] = (uint16_t)(i * 10);
	}

	memset(c_add, 0, sizeof(c_add));
	memset(c_sub, 0, sizeof(c_sub));

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpaddw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpsubw %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		"vmovdqu16 %%zmm3, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(c_add), "r"(c_sub)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		uint16_t ea = (uint16_t)(i * 100 + i * 10);
		uint16_t es = (uint16_t)(i * 100 - i * 10);

		if (c_add[i] != ea) {
			printf("FAIL avx512bw/vpaddw: c[%d]=%u, expected %u\n",
			       i, c_add[i], ea);
			return 1;
		}
		if (c_sub[i] != es) {
			printf("FAIL avx512bw/vpsubw: c[%d]=%u, expected %u\n",
			       i, c_sub[i], es);
			return 1;
		}
	}
	printf("PASS avx512bw/vpaddw_vpsubw: packed word add/subtract correct\n");
	return 0;
}

static int test_saturated_byte(void)
{
	/*
	 * vpaddsb: signed saturated add -> clamp to [-128, 127]
	 * vpaddusb: unsigned saturated add -> clamp to [0, 255]
	 */
	int8_t sa[64] __attribute__((aligned(64)));
	int8_t sb[64] __attribute__((aligned(64)));
	int8_t sc[64] __attribute__((aligned(64)));
	uint8_t ua[64] __attribute__((aligned(64)));
	uint8_t ub[64] __attribute__((aligned(64)));
	uint8_t uc[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		sa[i] = 100;
		sb[i] = 100;
		ua[i] = 200;
		ub[i] = 200;
	}

	memset(sc, 0, 64);
	memset(uc, 0, 64);

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpaddsb %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		"vmovdqu8 (%3), %%zmm3\n\t"
		"vmovdqu8 (%4), %%zmm4\n\t"
		"vpaddusb %%zmm4, %%zmm3, %%zmm5\n\t"
		"vmovdqu8 %%zmm5, (%5)\n\t"
		:
		: "r"(sa), "r"(sb), "r"(sc), "r"(ua), "r"(ub), "r"(uc)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		if (sc[i] != 127) {
			printf("FAIL avx512bw/vpaddsb: c[%d]=%d, expected 127 (saturated)\n",
			       i, sc[i]);
			return 1;
		}
		if (uc[i] != 255) {
			printf("FAIL avx512bw/vpaddusb: c[%d]=%u, expected 255 (saturated)\n",
			       i, uc[i]);
			return 1;
		}
	}
	printf("PASS avx512bw/saturated_byte: signed and unsigned byte saturated add correct\n");
	return 0;
}

static int test_saturated_word(void)
{
	int16_t sa[32] __attribute__((aligned(64)));
	int16_t sb[32] __attribute__((aligned(64)));
	int16_t sc[32] __attribute__((aligned(64)));
	uint16_t ua[32] __attribute__((aligned(64)));
	uint16_t ub[32] __attribute__((aligned(64)));
	uint16_t uc[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		sa[i] = 30000;
		sb[i] = 30000;
		ua[i] = 60000;
		ub[i] = 60000;
	}

	memset(sc, 0, sizeof(sc));
	memset(uc, 0, sizeof(uc));

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpaddsw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		"vmovdqu16 (%3), %%zmm3\n\t"
		"vmovdqu16 (%4), %%zmm4\n\t"
		"vpaddusw %%zmm4, %%zmm3, %%zmm5\n\t"
		"vmovdqu16 %%zmm5, (%5)\n\t"
		:
		: "r"(sa), "r"(sb), "r"(sc), "r"(ua), "r"(ub), "r"(uc)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		if (sc[i] != 32767) {
			printf("FAIL avx512bw/vpaddsw: c[%d]=%d, expected 32767\n",
			       i, sc[i]);
			return 1;
		}
		if (uc[i] != 65535) {
			printf("FAIL avx512bw/vpaddusw: c[%d]=%u, expected 65535\n",
			       i, uc[i]);
			return 1;
		}
	}
	printf("PASS avx512bw/saturated_word: signed and unsigned word saturated add correct\n");
	return 0;
}

static int test_vpmullw(void)
{
	int16_t a[32] __attribute__((aligned(64)));
	int16_t b[32] __attribute__((aligned(64)));
	int16_t c[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = (int16_t)(i + 1);
		b[i] = 3;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpmullw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		int16_t expected = (int16_t)((i + 1) * 3);

		if (c[i] != expected) {
			printf("FAIL avx512bw/vpmullw: c[%d]=%d, expected %d\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512bw/vpmullw: packed word multiply low correct\n");
	return 0;
}

static int test_vpmulhw_vpmulhuw(void)
{
	/*
	 * vpmulhw:  signed high half of 16x16->32 multiply
	 * vpmulhuw: unsigned high half
	 *
	 * a = 1000, b = 1000: product = 1000000
	 *   low 16 = 1000000 & 0xFFFF = 16960 (0x4240)
	 *   high 16 = 1000000 >> 16 = 15 (0x000F)
	 */
	int16_t sa[32] __attribute__((aligned(64)));
	int16_t sb[32] __attribute__((aligned(64)));
	int16_t sc[32] __attribute__((aligned(64)));
	uint16_t ua[32] __attribute__((aligned(64)));
	uint16_t ub[32] __attribute__((aligned(64)));
	uint16_t uc[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		sa[i] = 1000;
		sb[i] = 1000;
		ua[i] = 1000;
		ub[i] = 1000;
	}

	memset(sc, 0, sizeof(sc));
	memset(uc, 0, sizeof(uc));

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpmulhw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		"vmovdqu16 (%3), %%zmm3\n\t"
		"vmovdqu16 (%4), %%zmm4\n\t"
		"vpmulhuw %%zmm4, %%zmm3, %%zmm5\n\t"
		"vmovdqu16 %%zmm5, (%5)\n\t"
		:
		: "r"(sa), "r"(sb), "r"(sc), "r"(ua), "r"(ub), "r"(uc)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		if (sc[i] != 15) {
			printf("FAIL avx512bw/vpmulhw: c[%d]=%d, expected 15\n",
			       i, sc[i]);
			return 1;
		}
		if (uc[i] != 15) {
			printf("FAIL avx512bw/vpmulhuw: c[%d]=%u, expected 15\n",
			       i, uc[i]);
			return 1;
		}
	}
	printf("PASS avx512bw/vpmulhw_vpmulhuw: packed word multiply high correct\n");
	return 0;
}

static int test_vpavgb_vpavgw(void)
{
	uint8_t ba[64] __attribute__((aligned(64)));
	uint8_t bb[64] __attribute__((aligned(64)));
	uint8_t bc[64] __attribute__((aligned(64)));
	uint16_t wa[32] __attribute__((aligned(64)));
	uint16_t wb[32] __attribute__((aligned(64)));
	uint16_t wc[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		ba[i] = 10;
		bb[i] = 20;
	}

	for (i = 0; i < 32; i++) {
		wa[i] = 100;
		wb[i] = 200;
	}

	memset(bc, 0, 64);
	memset(wc, 0, sizeof(wc));

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpavgb %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		"vmovdqu16 (%3), %%zmm3\n\t"
		"vmovdqu16 (%4), %%zmm4\n\t"
		"vpavgw %%zmm4, %%zmm3, %%zmm5\n\t"
		"vmovdqu16 %%zmm5, (%5)\n\t"
		:
		: "r"(ba), "r"(bb), "r"(bc), "r"(wa), "r"(wb), "r"(wc)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		if (bc[i] != 15) {
			printf("FAIL avx512bw/vpavgb: c[%d]=%u, expected 15\n",
			       i, bc[i]);
			return 1;
		}
	}
	for (i = 0; i < 32; i++) {
		if (wc[i] != 150) {
			printf("FAIL avx512bw/vpavgw: c[%d]=%u, expected 150\n",
			       i, wc[i]);
			return 1;
		}
	}
	printf("PASS avx512bw/vpavgb_vpavgw: packed byte/word average correct\n");
	return 0;
}

static int test_vpmaddwd(void)
{
	/*
	 * vpmaddwd: multiply pairs of int16, add adjacent results to int32.
	 * For each 32-bit output: result[j] = a[2j]*b[2j] + a[2j+1]*b[2j+1]
	 *   a words: [3, 4] per pair
	 *   b words: [5, 6] per pair
	 *   result: 3*5 + 4*6 = 15 + 24 = 39
	 */
	int16_t a[32] __attribute__((aligned(64)));
	int16_t b[32] __attribute__((aligned(64)));
	int32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i += 2) {
		a[i] = 3;
		a[i + 1] = 4;
		b[i] = 5;
		b[i + 1] = 6;
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpmaddwd %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != 39) {
			printf("FAIL avx512bw/vpmaddwd: c[%d]=%d, expected 39\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512bw/vpmaddwd: packed multiply-add word to dword correct\n");
	return 0;
}

static int test_vpmaddubsw(void)
{
	/*
	 * vpmaddubsw: multiply uint8 * int8, add adjacent pairs -> int16 (sat).
	 * a bytes (uint8): [2, 3] per pair
	 * b bytes (int8):  [4, 5] per pair
	 * result per word: 2*4 + 3*5 = 8 + 15 = 23
	 */
	uint8_t a[64] __attribute__((aligned(64)));
	int8_t b[64] __attribute__((aligned(64)));
	int16_t c[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i += 2) {
		a[i] = 2;
		a[i + 1] = 3;
		b[i] = 4;
		b[i + 1] = 5;
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpmaddubsw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		if (c[i] != 23) {
			printf("FAIL avx512bw/vpmaddubsw: c[%d]=%d, expected 23\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512bw/vpmaddubsw: uint8*int8 multiply-add to word correct\n");
	return 0;
}

static int test_minmax_byte(void)
{
	uint8_t ua[64] __attribute__((aligned(64)));
	uint8_t ub[64] __attribute__((aligned(64)));
	uint8_t uminc[64] __attribute__((aligned(64)));
	uint8_t umaxc[64] __attribute__((aligned(64)));
	int8_t sa[64] __attribute__((aligned(64)));
	int8_t sb[64] __attribute__((aligned(64)));
	int8_t sminc[64] __attribute__((aligned(64)));
	int8_t smaxc[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		ua[i] = (uint8_t)(i * 4);
		ub[i] = 128;
		sa[i] = (int8_t)(i - 32);
		sb[i] = 0;
	}

	memset(uminc, 0, 64);
	memset(umaxc, 0, 64);
	memset(sminc, 0, 64);
	memset(smaxc, 0, 64);

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpminub %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpmaxub %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		"vmovdqu8 %%zmm3, (%3)\n\t"
		"vmovdqu8 (%4), %%zmm4\n\t"
		"vmovdqu8 (%5), %%zmm5\n\t"
		"vpminsb %%zmm5, %%zmm4, %%zmm6\n\t"
		"vpmaxsb %%zmm5, %%zmm4, %%zmm7\n\t"
		"vmovdqu8 %%zmm6, (%6)\n\t"
		"vmovdqu8 %%zmm7, (%7)\n\t"
		:
		: "r"(ua), "r"(ub), "r"(uminc), "r"(umaxc),
		  "r"(sa), "r"(sb), "r"(sminc), "r"(smaxc)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t umin_exp = (ua[i] < 128) ? ua[i] : 128;
		uint8_t umax_exp = (ua[i] > 128) ? ua[i] : 128;
		int8_t smin_exp = ((int8_t)(i - 32) < 0) ? (int8_t)(i - 32) : 0;
		int8_t smax_exp = ((int8_t)(i - 32) > 0) ? (int8_t)(i - 32) : 0;

		if (uminc[i] != umin_exp || umaxc[i] != umax_exp) {
			printf("FAIL avx512bw/minmax_ubyte: i=%d\n", i);
			return 1;
		}
		if (sminc[i] != smin_exp || smaxc[i] != smax_exp) {
			printf("FAIL avx512bw/minmax_sbyte: i=%d got min=%d max=%d, expected min=%d max=%d\n",
			       i, sminc[i], smaxc[i], smin_exp, smax_exp);
			return 1;
		}
	}
	printf("PASS avx512bw/minmax_byte: packed byte min/max (signed+unsigned) correct\n");
	return 0;
}

static int test_minmax_word(void)
{
	int16_t sa[32] __attribute__((aligned(64)));
	int16_t sb[32] __attribute__((aligned(64)));
	int16_t sminc[32] __attribute__((aligned(64)));
	int16_t smaxc[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		sa[i] = (int16_t)(i * 100 - 1500);
		sb[i] = 0;
	}

	memset(sminc, 0, sizeof(sminc));
	memset(smaxc, 0, sizeof(smaxc));

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpminsw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpmaxsw %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		"vmovdqu16 %%zmm3, (%3)\n\t"
		:
		: "r"(sa), "r"(sb), "r"(sminc), "r"(smaxc)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		int16_t v = (int16_t)(i * 100 - 1500);
		int16_t emin = (v < 0) ? v : 0;
		int16_t emax = (v > 0) ? v : 0;

		if (sminc[i] != emin || smaxc[i] != emax) {
			printf("FAIL avx512bw/minmax_word: i=%d\n", i);
			return 1;
		}
	}
	printf("PASS avx512bw/minmax_word: packed word min/max correct\n");
	return 0;
}

static int test_vpabsb_vpabsw(void)
{
	int8_t ba[64] __attribute__((aligned(64)));
	int8_t bc[64] __attribute__((aligned(64)));
	int16_t wa[32] __attribute__((aligned(64)));
	int16_t wc[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++)
		ba[i] = (int8_t)(-(i % 127) - 1);

	for (i = 0; i < 32; i++)
		wa[i] = (int16_t)(-(i + 1) * 100);

	memset(bc, 0, 64);
	memset(wc, 0, sizeof(wc));

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vpabsb %%zmm0, %%zmm1\n\t"
		"vmovdqu8 %%zmm1, (%1)\n\t"
		"vmovdqu16 (%2), %%zmm2\n\t"
		"vpabsw %%zmm2, %%zmm3\n\t"
		"vmovdqu16 %%zmm3, (%3)\n\t"
		:
		: "r"(ba), "r"(bc), "r"(wa), "r"(wc)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		int8_t expected = (int8_t)((i % 127) + 1);

		if (bc[i] != expected) {
			printf("FAIL avx512bw/vpabsb: c[%d]=%d, expected %d\n",
			       i, bc[i], expected);
			return 1;
		}
	}
	for (i = 0; i < 32; i++) {
		int16_t expected = (int16_t)((i + 1) * 100);

		if (wc[i] != expected) {
			printf("FAIL avx512bw/vpabsw: c[%d]=%d, expected %d\n",
			       i, wc[i], expected);
			return 1;
		}
	}
	printf("PASS avx512bw/vpabsb_vpabsw: packed byte/word absolute value correct\n");
	return 0;
}

static int test_vpshufb(void)
{
	/*
	 * vpshufb: byte shuffle within 128-bit lanes.
	 * For each byte in control: if bit 7 = 1 -> zero; else use bits [3:0]
	 * as index within the 16-byte lane.
	 *
	 * Test: reverse bytes within each 16-byte lane.
	 */
	uint8_t src[64] __attribute__((aligned(64)));
	uint8_t ctrl[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		src[i] = (uint8_t)i;
		ctrl[i] = (uint8_t)(15 - (i % 16));
	}

	memset(c, 0, 64);

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpshufb %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		:
		: "r"(src), "r"(ctrl), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		int lane_base = (i / 16) * 16;
		uint8_t expected = (uint8_t)(lane_base + 15 - (i % 16));

		if (c[i] != expected) {
			printf("FAIL avx512bw/vpshufb: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512bw/vpshufb: packed byte shuffle correct\n");
	return 0;
}

static int test_shift_w_imm(void)
{
	uint16_t a[32] __attribute__((aligned(64)));
	uint16_t csll[32] __attribute__((aligned(64)));
	uint16_t csrl[32] __attribute__((aligned(64)));
	int16_t sa[32] __attribute__((aligned(64)));
	int16_t csra[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = 0x8421;
		sa[i] = -128;
	}

	memset(csll, 0, sizeof(csll));
	memset(csrl, 0, sizeof(csrl));
	memset(csra, 0, sizeof(csra));

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vpsllw $4, %%zmm0, %%zmm1\n\t"
		"vpsrlw $4, %%zmm0, %%zmm2\n\t"
		"vmovdqu16 %%zmm1, (%1)\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		"vmovdqu16 (%3), %%zmm3\n\t"
		"vpsraw $2, %%zmm3, %%zmm4\n\t"
		"vmovdqu16 %%zmm4, (%4)\n\t"
		:
		: "r"(a), "r"(csll), "r"(csrl), "r"(sa), "r"(csra)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		if (csll[i] != (uint16_t)(0x8421 << 4)) {
			printf("FAIL avx512bw/vpsllw: c[%d]=0x%04x, expected 0x%04x\n",
			       i, csll[i], (uint16_t)(0x8421 << 4));
			return 1;
		}
		if (csrl[i] != (uint16_t)(0x8421 >> 4)) {
			printf("FAIL avx512bw/vpsrlw: c[%d]=0x%04x, expected 0x%04x\n",
			       i, csrl[i], (uint16_t)(0x8421 >> 4));
			return 1;
		}
		if (csra[i] != (int16_t)(-128 >> 2)) {
			printf("FAIL avx512bw/vpsraw: c[%d]=%d, expected %d\n",
			       i, csra[i], (int16_t)(-128 >> 2));
			return 1;
		}
	}
	printf("PASS avx512bw/shift_w_imm: packed word shifts (imm) correct\n");
	return 0;
}

static int test_shift_w_var(void)
{
	uint16_t a[32] __attribute__((aligned(64)));
	uint16_t counts[32] __attribute__((aligned(64)));
	uint16_t csll[32] __attribute__((aligned(64)));
	uint16_t csrl[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = 0xFF00;
		counts[i] = (uint16_t)(i % 16);
	}

	memset(csll, 0, sizeof(csll));
	memset(csrl, 0, sizeof(csrl));

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpsllvw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vpsrlvw %%zmm1, %%zmm0, %%zmm3\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		"vmovdqu16 %%zmm3, (%3)\n\t"
		:
		: "r"(a), "r"(counts), "r"(csll), "r"(csrl)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		uint16_t shift = (uint16_t)(i % 16);
		uint16_t esll = (uint16_t)(0xFF00 << shift);
		uint16_t esrl = (uint16_t)(0xFF00 >> shift);

		if (csll[i] != esll) {
			printf("FAIL avx512bw/vpsllvw: c[%d]=0x%04x, expected 0x%04x\n",
			       i, csll[i], esll);
			return 1;
		}
		if (csrl[i] != esrl) {
			printf("FAIL avx512bw/vpsrlvw: c[%d]=0x%04x, expected 0x%04x\n",
			       i, csrl[i], esrl);
			return 1;
		}
	}
	printf("PASS avx512bw/shift_w_var: packed word variable shifts correct\n");
	return 0;
}

static int test_pack_bw(void)
{
	/*
	 * vpacksswb: pack signed words to signed bytes with saturation.
	 * a = {200, 200, ...}, b = {-200, -200, ...}
	 * Expected packed bytes: 127 (saturated from 200), -128 (saturated from -200)
	 * Within each 128-bit lane: first 8 bytes from a, next 8 bytes from b.
	 */
	int16_t a[32] __attribute__((aligned(64)));
	int16_t b[32] __attribute__((aligned(64)));
	int8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = 200;
		b[i] = -200;
	}

	memset(c, 0, 64);

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpacksswb %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		int lane_pos = i % 16;
		int8_t expected = (lane_pos < 8) ? 127 : -128;

		if (c[i] != expected) {
			printf("FAIL avx512bw/vpacksswb: c[%d]=%d, expected %d\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512bw/vpacksswb: pack signed words to signed bytes correct\n");
	return 0;
}

static int test_unpack_bw(void)
{
	/*
	 * vpunpcklbw: interleave low bytes from two sources within each lane.
	 * Within each 128-bit lane, take bytes 0-7 from each source and interleave.
	 */
	uint8_t a[64] __attribute__((aligned(64)));
	uint8_t b[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		a[i] = 0xAA;
		b[i] = 0x55;
	}

	memset(c, 0, 64);

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpunpcklbw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t expected = (i % 2 == 0) ? 0xAA : 0x55;

		if (c[i] != expected) {
			printf("FAIL avx512bw/vpunpcklbw: c[%d]=0x%02x, expected 0x%02x\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512bw/vpunpcklbw: byte unpack low correct\n");
	return 0;
}

static int test_vpmovwb(void)
{
	/*
	 * vpmovwb: truncate packed words to bytes (take low 8 bits of each word).
	 * Input: 32 words in ZMM -> output: 32 bytes in YMM
	 */
	uint16_t a[32] __attribute__((aligned(64)));
	uint8_t c[32] __attribute__((aligned(32)));
	int i;

	for (i = 0; i < 32; i++) {
		a[i] = (uint16_t)(0xFF00 | (i + 10));
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vpmovwb %%zmm0, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		uint8_t expected = (uint8_t)(i + 10);

		if (c[i] != expected) {
			printf("FAIL avx512bw/vpmovwb: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512bw/vpmovwb: truncate words to bytes correct\n");
	return 0;
}

static int test_vpsadbw(void)
{
	/*
	 * vpsadbw: compute sum of absolute differences of uint8 pairs,
	 * accumulating groups of 8 bytes into a 64-bit result.
	 *
	 * a = {10,10,...}, b = {20,20,...}
	 * |10-20| = 10 for each pair, 8 pairs per qword -> sum = 80
	 */
	uint8_t a[64] __attribute__((aligned(64)));
	uint8_t b[64] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 64; i++) {
		a[i] = 10;
		b[i] = 20;
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"vpsadbw %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		if (c[i] != 80) {
			printf("FAIL avx512bw/vpsadbw: c[%d]=%lu, expected 80\n",
			       i, (unsigned long)c[i]);
			return 1;
		}
	}
	printf("PASS avx512bw/vpsadbw: packed absolute difference sum correct\n");
	return 0;
}

static int test_vpermw(void)
{
	/*
	 * vpermw: permute 16-bit words across the full 512-bit register.
	 * Reverse all 32 words.
	 */
	uint16_t src[32] __attribute__((aligned(64)));
	uint16_t idx[32] __attribute__((aligned(64)));
	uint16_t c[32] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 32; i++) {
		src[i] = (uint16_t)(i * 10);
		idx[i] = (uint16_t)(31 - i);
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovdqu16 (%0), %%zmm0\n\t"
		"vmovdqu16 (%1), %%zmm1\n\t"
		"vpermw %%zmm0, %%zmm1, %%zmm2\n\t"
		"vmovdqu16 %%zmm2, (%2)\n\t"
		:
		: "r"(src), "r"(idx), "r"(c)
		: "memory"
	);

	for (i = 0; i < 32; i++) {
		uint16_t expected = (uint16_t)((31 - i) * 10);

		if (c[i] != expected) {
			printf("FAIL avx512bw/vpermw: c[%d]=%u, expected %u\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512bw/vpermw: packed word permutation correct\n");
	return 0;
}

static int test_vpblendmb(void)
{
	/*
	 * vpblendmb: blend bytes using mask.
	 * mask = alternating 0xAA per byte of k register -> odd bytes from b, even from a.
	 */
	uint8_t a[64] __attribute__((aligned(64)));
	uint8_t b[64] __attribute__((aligned(64)));
	uint8_t c[64] __attribute__((aligned(64)));
	uint64_t mask = 0xAAAAAAAAAAAAAAAAULL;
	int i;

	for (i = 0; i < 64; i++) {
		a[i] = 0x11;
		b[i] = 0x22;
	}

	memset(c, 0, 64);

	asm volatile(
		"vmovdqu8 (%0), %%zmm0\n\t"
		"vmovdqu8 (%1), %%zmm1\n\t"
		"kmovq %3, %%k1\n\t"
		"vpblendmb %%zmm1, %%zmm0, %%zmm2 %{%%k1%}\n\t"
		"vmovdqu8 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c), "r"(mask)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		uint8_t expected = (i % 2 == 0) ? 0x11 : 0x22;

		if (c[i] != expected) {
			printf("FAIL avx512bw/vpblendmb: c[%d]=0x%02x, expected 0x%02x\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512bw/vpblendmb: masked byte blend correct\n");
	return 0;
}

static int test_broadcast_bw(void)
{
	uint8_t bval = 42;
	uint8_t bc[64] __attribute__((aligned(64)));
	uint16_t wval = 1234;
	uint16_t wc[32] __attribute__((aligned(64)));
	int i;

	memset(bc, 0, 64);
	memset(wc, 0, sizeof(wc));

	asm volatile(
		"vpbroadcastb %2, %%zmm0\n\t"
		"vmovdqu8 %%zmm0, (%0)\n\t"
		"vpbroadcastw %3, %%zmm1\n\t"
		"vmovdqu16 %%zmm1, (%1)\n\t"
		:
		: "r"(bc), "r"(wc), "m"(bval), "m"(wval)
		: "memory"
	);

	for (i = 0; i < 64; i++) {
		if (bc[i] != 42) {
			printf("FAIL avx512bw/vpbroadcastb: c[%d]=%u, expected 42\n",
			       i, bc[i]);
			return 1;
		}
	}
	for (i = 0; i < 32; i++) {
		if (wc[i] != 1234) {
			printf("FAIL avx512bw/vpbroadcastw: c[%d]=%u, expected 1234\n",
			       i, wc[i]);
			return 1;
		}
	}
	printf("PASS avx512bw/broadcast_bw: byte and word broadcast correct\n");
	return 0;
}

int test_avx512bw_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpaddb_vpsubb() == 0) passed++; else failed++;
	total++; if (test_vpaddw_vpsubw() == 0) passed++; else failed++;
	total++; if (test_saturated_byte() == 0) passed++; else failed++;
	total++; if (test_saturated_word() == 0) passed++; else failed++;
	total++; if (test_vpmullw() == 0) passed++; else failed++;
	total++; if (test_vpmulhw_vpmulhuw() == 0) passed++; else failed++;
	total++; if (test_vpavgb_vpavgw() == 0) passed++; else failed++;
	total++; if (test_vpmaddwd() == 0) passed++; else failed++;
	total++; if (test_vpmaddubsw() == 0) passed++; else failed++;
	total++; if (test_minmax_byte() == 0) passed++; else failed++;
	total++; if (test_minmax_word() == 0) passed++; else failed++;
	total++; if (test_vpabsb_vpabsw() == 0) passed++; else failed++;
	total++; if (test_vpshufb() == 0) passed++; else failed++;
	total++; if (test_shift_w_imm() == 0) passed++; else failed++;
	total++; if (test_shift_w_var() == 0) passed++; else failed++;
	total++; if (test_pack_bw() == 0) passed++; else failed++;
	total++; if (test_unpack_bw() == 0) passed++; else failed++;
	total++; if (test_vpmovwb() == 0) passed++; else failed++;
	total++; if (test_vpsadbw() == 0) passed++; else failed++;
	total++; if (test_vpermw() == 0) passed++; else failed++;
	total++; if (test_vpblendmb() == 0) passed++; else failed++;
	total++; if (test_broadcast_bw() == 0) passed++; else failed++;

	printf("\n=== avx512bw: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
