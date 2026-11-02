/* Seeded malformed-input stress harness for address/undefined sanitizers. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include "decode.c"
static uint64_t state = UINT64_C(20261022);
static unsigned random_byte(void) {
    state ^= state << 13; state ^= state >> 7; state ^= state << 17;
    return (unsigned)(state & 255);
}
int main(void) {
    unsigned char data[1024];
    uint64_t lower[64], upper[64], center[64], radius[64];
    size_t escapes;
    for (size_t k=0; k<100000; ++k) {
        size_t n = 1+(k%64), bytes = (k%1025), block = 1+(k%64);
        unsigned bits = 16+8*(k%5);
        for (size_t j=0; j<bytes; ++j) data[j] = (unsigned char)random_byte();
        /* Force some valid exponent prefixes to reach integer decoding. */
        if (bytes>=2 && k%2) { data[0]=0; data[1]=0; }
        int result = decode(data, bytes, n, bits, block, lower, upper,
            k%2 ? center : NULL, k%2 ? radius : NULL, &escapes);
        if (result < 0 || result > 10) return 1;
    }
    puts("100000 seeded malformed cases completed under ASan and UBSan");
    return 0;
}
