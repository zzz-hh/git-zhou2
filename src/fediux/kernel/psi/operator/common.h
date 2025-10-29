#ifndef SRC_FEDIUX_KERNEL_PSI_OPERATOR_COMMON_H_
#define SRC_FEDIUX_KERNEL_PSI_OPERATOR_COMMON_H_
namespace fediux::psi {

enum class PsiType {
  ECDH = 0,
  KKRT,
  TEE,
};

enum class PsiResultType {
  INTERSECTION = 0,
  DIFFERENCE = 1,
};
}  // namespace fediux::psi

#endif  // SRC_FEDIUX_KERNEL_PSI_OPERATOR_COMMON_H_
