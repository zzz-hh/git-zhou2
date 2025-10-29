#include "src/fediux/kernel/pir/operator/base_pir.h"
namespace fediux::pir {
retcode BasePirOperator::Execute(const PirDataType& input,
                                 PirDataType* result) {
  return OnExecute(input, result);
}
}  // namespace fediux::pir
