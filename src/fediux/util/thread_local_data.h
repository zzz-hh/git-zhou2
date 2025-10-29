#ifndef SRC_FEDIUX_UTIL_THREAD_LOCAL_DATA_H_
#define SRC_FEDIUX_UTIL_THREAD_LOCAL_DATA_H_
#include <string>
#include <thread>
namespace fediux {
std::string& ThreadLocalErrorMsg();
void SetThreadLocalErrorMsg(const std::string& msg_info);
void ResetThreadLocalErrorMsg();
}  // namespace fediux
#endif  // SRC_FEDIUX_UTIL_THREAD_LOCAL_DATA_H_
