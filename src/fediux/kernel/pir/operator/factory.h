#ifndef SRC_FEDIUX_KERNEL_PIR_OPERATOR_FACTORY_H_
#define SRC_FEDIUX_KERNEL_PIR_OPERATOR_FACTORY_H_
#include <glog/logging.h>
#include <memory>
#include "src/fediux/kernel/pir/common.h"
#include "src/fediux/kernel/pir/operator/keyword_pir_impl/keyword_pir_client.h"
#include "src/fediux/kernel/pir/operator/keyword_pir_impl/keyword_pir_server.h"
namespace fediux::pir {
class Factory {
 public:
  static std::unique_ptr<BasePirOperator> Create(PirType pir_type,
      const Options& options) {
    std::unique_ptr<BasePirOperator> operator_ptr{nullptr};
    switch (pir_type) {
    case PirType::ID_PIR:
      LOG(ERROR) << "Unimplement";
      break;
    case PirType::KEY_PIR: {
      if (RoleValidation::IsClient(options.role)) {
        operator_ptr = std::make_unique<KeywordPirOperatorClient>(options);
      } else if (RoleValidation::IsServer(options.role)) {
        operator_ptr = std::make_unique<KeywordPirOperatorServer>(options);
      } else {
        LOG(ERROR) << "unknown role: " << static_cast<int>(options.role);
      }
      break;
    }
    default:
      LOG(ERROR) << "unknown pir operator: " << static_cast<int>(pir_type);
      break;
    }
    return operator_ptr;
  }
};
}  // namespace fediux::pir
#endif  // SRC_FEDIUX_KERNEL_PIR_OPERATOR_FACTORY_H_
