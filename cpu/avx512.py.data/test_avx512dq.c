/*
 * test_avx512dq.c - AVX-512 Doubleword and Quadword (DQ) instruction tests
 *
 * Tests: vpmullq, vcvtqq2pd, vcvtpd2qq, vcvtuqq2pd, vcvtpd2uqq,
 *        vandps (512-bit), vorps (512-bit), vxorps (512-bit),
 *        vextractf64x2, vinsertf64x2
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int test_vpmullq(void)
{
	int64_t a[8] __attribute__((aligned(64)));
	int64_t b[8] __attribute__((aligned(64)));
	int64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = i + 1;
		b[i] = 10;
		c[i] = 0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vmovdqu64 (%1), %%zmm1\n\t"
		"vpmullq %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovdqu64 %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		int64_t expected = (int64_t)(i + 1) * 10;

		if (c[i] != expected) {
			printf("FAIL avx512dq/vpmullq: c[%d]=%ld, expected %ld\n",
			       i, (long)c[i], (long)expected);
			return 1;
		}
	}
	printf("PASS avx512dq/vpmullq: packed 64-bit multiply correct\n");
	return 0;
}

static int test_vcvtqq2pd(void)
{
	int64_t a[8] __attribute__((aligned(64)));
	double c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (i + 1) * 100;
		c[i] = 0.0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vcvtqq2pd %%zmm0, %%zmm1\n\t"
		"vmovupd %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		double expected = (double)((i + 1) * 100);

		if (c[i] != expected) {
			printf("FAIL avx512dq/vcvtqq2pd: c[%d]=%f, expected %f\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512dq/vcvtqq2pd: int64 to double conversion correct\n");
	return 0;
}

static int test_vcvtpd2qq(void)
{
	double a[8] __attribute__((aligned(64)));
	int64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (double)((i + 1) * 100);
		c[i] = 0;
	}

	asm volatile(
		"vmovupd (%0), %%zmm0\n\t"
		"vcvtpd2qq %%zmm0, %%zmm1\n\t"
		"vmovdqu64 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		int64_t expected = (int64_t)((i + 1) * 100);

		if (c[i] != expected) {
			printf("FAIL avx512dq/vcvtpd2qq: c[%d]=%ld, expected %ld\n",
			       i, (long)c[i], (long)expected);
			return 1;
		}
	}
	printf("PASS avx512dq/vcvtpd2qq: double to int64 conversion correct\n");
	return 0;
}

static int test_vcvtuqq2pd(void)
{
	uint64_t a[8] __attribute__((aligned(64)));
	double c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (uint64_t)(i + 1) * 1000;
		c[i] = 0.0;
	}

	asm volatile(
		"vmovdqu64 (%0), %%zmm0\n\t"
		"vcvtuqq2pd %%zmm0, %%zmm1\n\t"
		"vmovupd %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		double expected = (double)((uint64_t)(i + 1) * 1000);

		if (c[i] != expected) {
			printf("FAIL avx512dq/vcvtuqq2pd: c[%d]=%f, expected %f\n",
			       i, c[i], expected);
			return 1;
		}
	}
	printf("PASS avx512dq/vcvtuqq2pd: uint64 to double conversion correct\n");
	return 0;
}

static int test_vcvtpd2uqq(void)
{
	double a[8] __attribute__((aligned(64)));
	uint64_t c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (double)((i + 1) * 1000);
		c[i] = 0;
	}

	asm volatile(
		"vmovupd (%0), %%zmm0\n\t"
		"vcvtpd2uqq %%zmm0, %%zmm1\n\t"
		"vmovdqu64 %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 8; i++) {
		uint64_t expected = (uint64_t)((i + 1) * 1000);

		if (c[i] != expected) {
			printf("FAIL avx512dq/vcvtpd2uqq: c[%d]=%lu, expected %lu\n",
			       i, (unsigned long)c[i], (unsigned long)expected);
			return 1;
		}
	}
	printf("PASS avx512dq/vcvtpd2uqq: double to uint64 conversion correct\n");
	return 0;
}

static int test_vandps_512(void)
{
	/*
	 * vandps on ZMM (512-bit FP logical AND) requires AVX-512DQ.
	 * Treat float bits as integers: 0xFFFFFFFF AND 0x3F800000 = 0x3F800000 (1.0f)
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	float c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0xFFFFFFFF;
		b[i] = 0x3F800000;
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovups (%0), %%zmm0\n\t"
		"vmovups (%1), %%zmm1\n\t"
		"vandps %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovups %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != 1.0f) {
			printf("FAIL avx512dq/vandps: c[%d]=%f, expected 1.0\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512dq/vandps: 512-bit FP AND correct\n");
	return 0;
}

static int test_vorps_512(void)
{
	/*
	 * vorps on ZMM: 0x00000000 OR 0x40000000 = 0x40000000 (2.0f)
	 */
	uint32_t a[16] __attribute__((aligned(64)));
	uint32_t b[16] __attribute__((aligned(64)));
	float c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = 0x00000000;
		b[i] = 0x40000000;
	}

	memset(c, 0, sizeof(c));

	asm volatile(
		"vmovups (%0), %%zmm0\n\t"
		"vmovups (%1), %%zmm1\n\t"
		"vorps %%zmm1, %%zmm0, %%zmm2\n\t"
		"vmovups %%zmm2, (%2)\n\t"
		:
		: "r"(a), "r"(b), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != 2.0f) {
			printf("FAIL avx512dq/vorps: c[%d]=%f, expected 2.0\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512dq/vorps: 512-bit FP OR correct\n");
	return 0;
}

static int test_vxorps_512(void)
{
	/*
	 * vxorps on ZMM: XOR a float with itself -> 0.0
	 */
	float a[16] __attribute__((aligned(64)));
	float c[16] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 16; i++) {
		a[i] = (float)(i + 1);
		c[i] = 99.0f;
	}

	asm volatile(
		"vmovups (%0), %%zmm0\n\t"
		"vxorps %%zmm0, %%zmm0, %%zmm1\n\t"
		"vmovups %%zmm1, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	for (i = 0; i < 16; i++) {
		if (c[i] != 0.0f) {
			printf("FAIL avx512dq/vxorps: c[%d]=%f, expected 0.0\n",
			       i, c[i]);
			return 1;
		}
	}
	printf("PASS avx512dq/vxorps: 512-bit FP XOR correct\n");
	return 0;
}

static int test_vextractf64x2(void)
{
	/*
	 * vextractf64x2: extract 128-bit (2 doubles) from ZMM at specified lane.
	 * zmm = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0}
	 * Extract lane 2 (elements 4-5) -> {5.0, 6.0}
	 */
	double a[8] __attribute__((aligned(64)));
	double c[2] __attribute__((aligned(16)));
	int i;

	for (i = 0; i < 8; i++)
		a[i] = (double)(i + 1);

	c[0] = c[1] = 0.0;

	asm volatile(
		"vmovapd (%0), %%zmm0\n\t"
		"vextractf64x2 $2, %%zmm0, (%1)\n\t"
		:
		: "r"(a), "r"(c)
		: "memory"
	);

	if (c[0] != 5.0 || c[1] != 6.0) {
		printf("FAIL avx512dq/vextractf64x2: got {%f,%f}, expected {5.0,6.0}\n",
		       c[0], c[1]);
		return 1;
	}
	printf("PASS avx512dq/vextractf64x2: 128-bit extract from 512-bit correct\n");
	return 0;
}

static int test_vinsertf64x2(void)
{
	/*
	 * vinsertf64x2: insert 128-bit (2 doubles) into ZMM at specified lane.
	 * Start with zmm = {1,2,3,4,5,6,7,8}
	 * Insert {99.0, 100.0} at lane 1 (elements 2-3)
	 * Result: {1,2,99,100,5,6,7,8}
	 */
	double a[8] __attribute__((aligned(64)));
	double ins[2] __attribute__((aligned(16)));
	double c[8] __attribute__((aligned(64)));
	int i;

	for (i = 0; i < 8; i++) {
		a[i] = (double)(i + 1);
		c[i] = 0.0;
	}
	ins[0] = 99.0;
	ins[1] = 100.0;

	asm volatile(
		"vmovapd (%0), %%zmm0\n\t"
		"vinsertf64x2 $1, (%1), %%zmm0, %%zmm1\n\t"
		"vmovapd %%zmm1, (%2)\n\t"
		:
		: "r"(a), "r"(ins), "r"(c)
		: "memory"
	);

	double expected[8] = {1.0, 2.0, 99.0, 100.0, 5.0, 6.0, 7.0, 8.0};

	for (i = 0; i < 8; i++) {
		if (c[i] != expected[i]) {
			printf("FAIL avx512dq/vinsertf64x2: c[%d]=%f, expected %f\n",
			       i, c[i], expected[i]);
			return 1;
		}
	}
	printf("PASS avx512dq/vinsertf64x2: 128-bit insert into 512-bit correct\n");
	return 0;
}

int test_avx512dq_all(void)
{
	int total = 0, passed = 0, failed = 0;

	total++; if (test_vpmullq() == 0) passed++; else failed++;
	total++; if (test_vcvtqq2pd() == 0) passed++; else failed++;
	total++; if (test_vcvtpd2qq() == 0) passed++; else failed++;
	total++; if (test_vcvtuqq2pd() == 0) passed++; else failed++;
	total++; if (test_vcvtpd2uqq() == 0) passed++; else failed++;
	total++; if (test_vandps_512() == 0) passed++; else failed++;
	total++; if (test_vorps_512() == 0) passed++; else failed++;
	total++; if (test_vxorps_512() == 0) passed++; else failed++;
	total++; if (test_vextractf64x2() == 0) passed++; else failed++;
	total++; if (test_vinsertf64x2() == 0) passed++; else failed++;

	printf("\n=== avx512dq: %d tests, %d passed, %d failed ===\n",
	       total, passed, failed);
	return failed > 0 ? 1 : 0;
}
