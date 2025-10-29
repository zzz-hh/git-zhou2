#ifndef SRC_FEDIUX_TASK_PYBIND_WRAPPER_UTIL_H_
#define SRC_FEDIUX_TASK_PYBIND_WRAPPER_UTIL_H_
#include <string>
#include "src/fediux/common/common.h"
namespace fediux::task::wrapper {
retcode GenerateSubtaskId(std::string* sub_task_id);
}
#endif  // SRC_FEDIUX_TASK_PYBIND_WRAPPER_UTIL_H_
