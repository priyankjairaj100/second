/* Unregistered software prototype. No floating-point arithmetic, no model work.
 * Decodes the existing V26 payload; all framing/hash checks stay in its parser.
 * This is not an admitted replacement for any registered implementation. */
#include <stdint.h>
#include <stddef.h>

#define SIGN (UINT64_C(1) << 63)
#define ABS_MASK (SIGN - 1)
#define GUARD UINT64_C(0x7FEFFFC000000000)

static uint64_t little(const unsigned char *p, unsigned n) {
    uint64_t x = 0;
    for (unsigned j = 0; j < n; ++j) x |= (uint64_t)p[j] << (8*j);
    return x;
}

/* Input magnitude is at most 2^48+1, including midpoint construction. */
static int dyadic(int64_t integer, int power, uint64_t *out) {
    if (!integer) { *out = 0; return 0; }
    uint64_t sign = integer < 0 ? SIGN : 0;
    uint64_t m = (uint64_t)(integer < 0 ? -integer : integer);
    while (!(m & 1)) { m >>= 1; ++power; }
    unsigned length = 0;
    for (uint64_t t = m; t; t >>= 1) ++length;
    int top = power + (int)length - 1;
    if (power < -1074 || top > 1023 || length > 53) return 7;
    if (top < -1022) *out = sign | (m << (power+1074));
    else *out = sign | ((uint64_t)(top+1023) << 52)
                     | ((m << (53-length)) - (UINT64_C(1) << 52));
    return 0;
}

int decode(const unsigned char *payload, size_t size, size_t total,
           unsigned bits, size_t block_size, uint64_t *lower, uint64_t *upper,
           uint64_t *center, uint64_t *radius, size_t *escapes) {
    if (!payload || !lower || !upper || !escapes || !total || total > 16000000
        || size > 128u*1024u*1024u || bits < 16 || bits > 48 || bits % 8
        || !block_size || block_size > 4096 || (!!center != !!radius)) return 10;
    size_t cursor = 0;
    unsigned byte_width = bits/8;
    *escapes = 0;
    for (size_t start = 0; start < total; start += block_size) {
        size_t count = total-start < block_size ? total-start : block_size;
        size_t flag_bytes = (count+3)/4;
        size_t fixed = 2+flag_bytes+count*byte_width;
        if (cursor > size || fixed > size-cursor) return 1;
        unsigned top_raw = (unsigned)little(payload+cursor, 2);
        int top = top_raw >= 32768 ? (int)top_raw-65536 : (int)top_raw;
        if (top < -1074 || top > 1023) return 2;
        int step = top-((int)bits-2);
        if (step < -1074) step = -1074;
        const unsigned char *flags = payload+cursor+2;
        const unsigned char *integers = flags+flag_bytes;
        cursor += fixed;
        if (count%4 && (flags[flag_bytes-1] >> (2*(count%4)))) return 3;
        for (size_t j = 0; j < count; ++j) {
            unsigned flag = (flags[j/4] >> (2*(j%4))) & 3;
            uint64_t raw = little(integers+j*byte_width, byte_width);
            int64_t integer = (raw & (UINT64_C(1) << (bits-1)))
                ? (int64_t)raw-(INT64_C(1) << bits) : (int64_t)raw;
            uint64_t lo, hi;
            if (flag == 3) return 4;
            if (flag == 2) {
                if (integer || cursor > size || size-cursor < 8) return 5;
                lo = hi = little(payload+cursor, 8);
                cursor += 8;
                if (((lo & ABS_MASK) >> 52) == 2047) return 6;
                if ((lo & ABS_MASK) <= GUARD) return 8;
                ++*escapes;
            } else {
                int error = dyadic(integer, step, &lo);
                if (error) return error;
                hi = lo;
                if (!flag && (error = dyadic(integer+1, step, &hi))) return error;
            }
            lower[start+j] = lo;
            upper[start+j] = hi;
            if (center) {
                center[start+j] = lo;
                radius[start+j] = 0;
                if (!flag) {
                    int error = dyadic(1, step > -1074 ? step-1 : step, radius+start+j);
                    if (error) return error;
                    if (step > -1074 && (error = dyadic(2*integer+1, step-1, center+start+j))) return error;
                }
            }
        }
    }
    return cursor == size ? 0 : 9;
}
