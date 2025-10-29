#ifndef SRC_FEDIUX_KERNEL_PIR_COMMON_H_
#define SRC_FEDIUX_KERNEL_PIR_COMMON_H_
#include <unordered_map>
#include <vector>
#include <string>

namespace fediux::pir {
using PirDataType = std::unordered_map<std::string, std::vector<std::string>>;
enum class PirType {
  ID_PIR = 0,
  KEY_PIR,
};
}  // namespace fediux::pir
#endif  // SRC_FEDIUX_KERNEL_PIR_COMMON_H_
