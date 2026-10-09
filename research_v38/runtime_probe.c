#define _GNU_SOURCE
#include <cpuid.h>
#include <errno.h>
#include <fenv.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>

/* Return live facts. Never fill missing facts from a saved manifest. */
int v38_cpuid_enabled(void) {
#if defined(__x86_64__) && defined(SYS_arch_prctl)
    errno = 0;
    long value = syscall(SYS_arch_prctl, 0x1011 /* ARCH_GET_CPUID */, 0);
    return value == 1 ? 1 : (value == 0 ? 0 : -errno);
#else
    return -38;
#endif
}

int v38_cpuid(uint32_t leaf, uint32_t subleaf, uint32_t result[4]) {
    if (v38_cpuid_enabled() != 1) return -1;
    __cpuid_count(leaf, subleaf, result[0], result[1], result[2], result[3]);
    return 0;
}

int v38_xcr0(uint64_t *result) {
    uint32_t a, b, c, d;
    if (v38_cpuid_enabled() != 1) return -1;
    __cpuid_count(1, 0, a, b, c, d);
    if ((c & (3u << 26)) != (3u << 26)) return -2;
    __asm__ volatile("xgetbv" : "=a" (a), "=d" (d) : "c" (0));
    *result = ((uint64_t)d << 32) | a;
    return 0;
}

int v38_fenv(uint32_t *mxcsr, uint16_t *x87cw) {
    __asm__ volatile("stmxcsr %0" : "=m" (*mxcsr));
    __asm__ volatile("fnstcw %0" : "=m" (*x87cw));
    return fegetround();
}

#ifdef V38_PROBE_MAIN
int main(void) {
    uint32_t values[4];
    uint64_t xcr0 = 0;
    if (v38_cpuid(0, 0, values)) return 10;
    if (v38_cpuid(1, 0, values)) return 11;
    if ((values[2] & (3u << 26)) == (3u << 26) && v38_xcr0(&xcr0)) return 12;
    puts("live-cpuid-probe-v38-ok");
    return 0;
}
#endif
