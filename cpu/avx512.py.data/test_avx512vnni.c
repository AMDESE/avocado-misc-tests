/*
 * test_avx512vnni.c - AVX-512 Vector Neural Network Instructions (VNNI) tests
 *
 * Tests: vpdpbusd, vpdpbusds, vpdpwssd, vpdpwssds
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpdpbusd(void)
{
	/*
	 * vpdpbusd: for each 32-bit lane, multiply 4 pairs of (uint8 * int8)
	 * and accumulate into a 32-bit accumulator.
	 *   a bytes: [1, 1, 1, 1] per lane  (uint8)
	 *   b bytes: [2, 2, 2, 2] per lane  (int8)
	 *   src accumulator = 0
	 *   result per lane = 0 + 1*2 + 1*2 + 1*2 + 1*2 = 8
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t src[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0x01010101;
		b[i] = 0x02020202;
		src[i] = 0;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vmovdqu32 (%2), %%zmm2\n\t"
		"vpdpbusd %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(src), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != 8) {
			printf("FAIL avx512_vnni/vpdpbusd: c[%d]=%u, expected 8\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512_vnni/vpdpbusd: uint8*int8 dot product correct\n");
	return 0;
}

static int test_vpdpbusds(void)
{
	/*
	 * vpdpbusds: same as vpdpbusd but with saturation.
	 * Use values that would overflow int32 without saturation.
	 *   a bytes: [255, 255, 255, 255] per lane (uint8 = 0xFF)
	 *   b bytes: [127, 127, 127, 127] per lane (int8 = 0x7F)
	 *   src accumulator = 0x7FFFFFF0 (near INT32_MAX)
	 *   dot product per lane = 255*127*4 = 129540
	 *   Without saturation: 0x7FFFFFF0 + 129540 = overflow
	 *   With saturation: clamped to 0x7FFFFFFF (INT32_MAX)
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t src[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0xFFFFFFFF;
		b[i] = 0x7F7F7F7F;
		src[i] = 0x7FFFFFF0;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vmovdqu32 (%2), %%zmm2\n\t"
		"vpdpbusds %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(src), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if ((int32_t)c[i] != 0x7FFFFFFF) {
			printf("FAIL avx512_vnni/vpdpbusds: c[%d]=0x%08x, expected 0x7FFFFFFF\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512_vnni/vpdpbusds: uint8*int8 dot product with saturation correct\n");
	return 0;
}

static int test_vpdpwssd(void)
{
	/*
	 * vpdpwssd: for each 32-bit lane, multiply 2 pairs of (int16 * int16)
	 * and accumulate into a 32-bit accumulator.
	 *   a words: [3, 4] per lane
	 *   b words: [5, 6] per lane
	 *   src accumulator = 100
	 *   result per lane = 100 + 3*5 + 4*6 = 100 + 15 + 24 = 139
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t src[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (4u << 16) | 3u;
		b[i] = (6u << 16) | 5u;
		src[i] = 100;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vmovdqu32 (%2), %%zmm2\n\t"
		"vpdpwssd %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(src), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != 139) {
			printf("FAIL avx512_vnni/vpdpwssd: c[%d]=%u, expected 139\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512_vnni/vpdpwssd: int16*int16 dot product correct\n");
	return 0;
}

static int test_vpdpwssds(void)
{
	/*
	 * vpdpwssds: same as vpdpwssd but with saturation.
	 *   a words: [32767, 32767] per lane (INT16_MAX)
	 *   b words: [32767, 32767] per lane (INT16_MAX)
	 *   src accumulator = 0x7FFFFFF0 (near INT32_MAX)
	 *   dot product = 32767*32767 + 32767*32767 = 2147352578
	 *   Without saturation: 0x7FFFFFF0 + 2147352578 = overflow
	 *   With saturation: 0x7FFFFFFF
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	uint32_t src[16] __attribute__((aligned(64)));
	uint32_t c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0x7FFF7FFF;
		b[i] = 0x7FFF7FFF;
		src[i] = 0x7FFFFFF0;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu32 (%0), %%zmm0\n\t"
		"vmovdqu32 (%1), %%zmm1\n\t"
		"vmovdqu32 (%2), %%zmm2\n\t"
		"vpdpwssds %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu32 %%zmm2, (%3)\n\t"
		:
		: "r"(a), "r"(b), "r"(src), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if ((int32_t)c[i] != 0x7FFFFFFF) {
			printf("FAIL avx512_vnni/vpdpwssds: c[%d]=0x%08x, expected 0x7FFFFFFF\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512_vnni/vpdpwssds: int16*int16 dot product with saturation correct\n");
	return 0;
}

int test_avx512vnni_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpdpbusd() == 0) passed++; else failed++;
	total++; if (test_vpdpbusds() == 0) passed++; else failed++;
	total++; if (test_vpdpwssd() == 0) passed++; else failed++;
	total++; if (test_vpdpwssds() == 0) passed++; else failed++;

	printf("\n=== avx512_vnni: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
