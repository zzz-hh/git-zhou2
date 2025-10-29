#ifndef SRC_FEDIUX_UTIL_LOG_H_
#define SRC_FEDIUX_UTIL_LOG_H_
#include "glog/logging.h"
#include <string>

namespace fediux {
enum class LogType {
  kScheduler,
  kTask,
  kDataService
};

static std::string LogTypeToString(LogType type) {
  switch (type) {
    case LogType::kScheduler:
      return "SCHEDULER";
    case LogType::kTask:
      return "TASK";
    case LogType::kDataService:
      return "DATA_SERVICE";
    default:
      return "";
  }
}

#define PH_LOG(log_level, log_type) \
    LOG(log_level)
    // LOG(log_level) << LogTypeToString(log_type) << " "

#define PH_VLOG(log_level, log_type) \
    VLOG(log_level)

    // VLOG(log_level) << LogTypeToString(log_type) << " "

#define PH_LOG_EVERY_N(log_level, n, log_type) \
    LOG_EVERY_N(log_level, n) << LogTypeToString(log_type) << " "

}  // namespace fediux

#endif  // SRC_FEDIUX_UTIL_LOG_H_
