#ifndef SRC_FEDIUX_UTIL_ENDIAN_UTIL_H_
#define SRC_FEDIUX_UTIL_ENDIAN_UTIL_H_
#ifdef __linux__
#include <endian.h>
#endif
namespace fediux {
#ifdef __linux__
#define ntohll(x)     be64toh(x)
#define htonll(x)     htobe64(x)
#endif
}
#endif  // SRC_FEDIUX_UTIL_ENDIAN_UTIL_H_
