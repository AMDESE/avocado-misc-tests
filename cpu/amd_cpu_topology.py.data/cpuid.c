#include <stdio.h>
#include <stdlib.h>

#undef DEBUG
#ifdef DEBUG
#define dprintf(...)   printf( __VA_ARGS__)
#else
#define dprintf(...)
#endif

struct cpuid_regs {
	unsigned int eax;
	unsigned int ebx;
	unsigned int ecx;
	unsigned int edx;
};

static inline void native_cpuid(unsigned int *eax, unsigned int *ebx,
				unsigned int *ecx, unsigned int *edx)
{
	/* ecx is often an input as well as an output. */
	asm volatile("cpuid"
	    : "=a" (*eax),
	      "=b" (*ebx),
	      "=c" (*ecx),
	      "=d" (*edx)
	    : "0" (*eax), "2" (*ecx)
	    : "memory");
}

static inline struct cpuid_regs cpuid_read(unsigned int leaf, unsigned int subleaf)
{
	struct cpuid_regs regs;

	regs.eax = leaf;
	regs.ecx = subleaf;
	native_cpuid(&regs.eax, &regs.ebx, &regs.ecx, &regs.edx);

	return regs;
}

void print_usage(char *progname)
{
	printf("Usage: %s <cpuid-leaf-in-hex> [cpuid-subleaf-in-hex]\n", progname);
}

int main(int argc, char *argv[])
{
	unsigned int leaf;
	unsigned int subleaf = 0;
        struct cpuid_regs regs;

	if (argc < 2) {
		print_usage(argv[0]);
		return -1;
	}

	if (argc >= 3)
		subleaf = (unsigned int) strtoul(argv[2], NULL, 16);

	leaf = (unsigned int)strtoul(argv[1], NULL, 16);

	dprintf("leaf = 0x%08x, subleaf = 0x%02x\n", leaf, subleaf);
	regs = cpuid_read(leaf, subleaf);

	printf("0x%08x 0x%02x: eax=0x%08x  ebx=0x%08x ecx=0x%08x edx=0x%08x\n",
	       leaf, subleaf, regs.eax, regs.ebx, regs.ecx, regs.edx);

	return 0;
}
