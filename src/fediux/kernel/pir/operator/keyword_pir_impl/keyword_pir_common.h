#ifndef SRC_FEDIUX_KERNEL_PIR_OPERATOR_KEYWORD_PIR_IMPL_KEYWORD_PIR_COMMON_H_
#define SRC_FEDIUX_KERNEL_PIR_OPERATOR_KEYWORD_PIR_IMPL_KEYWORD_PIR_COMMON_H_
#include <cstdint>
namespace fediux::pir {
enum class RequestType : uint8_t {
  PsiParam = 0,
  Oprf,
  Query,
};
struct PirConstant {
  inline static double table_size_factor{0.9};
};
}
#endif  // SRC_FEDIUX_KERNEL_PIR_OPERATOR_KEYWORD_PIR_IMPL_KEYWORD_PIR_COMMON_H_
