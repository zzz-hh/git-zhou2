#ifndef SRC_FEDIUX_UTIL_PROTO_LOG_HELPER_H_
#define SRC_FEDIUX_UTIL_PROTO_LOG_HELPER_H_

#include <string>
#include "src/fediux/protos/worker.pb.h"
#include <google/protobuf/text_format.h>
#include <google/protobuf/util/json_util.h>

namespace rpc = fediux::rpc;

namespace fediux::proto::util {
std::string TaskInfoToString(const rpc::TaskContext& task_info,
                              bool json_format = false);
std::string TaskInfoToString(const std::string& task_info);
std::string TaskInfoToString(const std::string& request_id, const std::string& task_id);
std::string TaskConfigToString(const rpc::Task& task_config);
std::string TaskRequestToString(const rpc::PushTaskRequest& task_req);
std::string TaskStatusToString(const rpc::TaskStatus& status);
template <typename T>
std::string TypeToString(const T& pb_item) {
  std::string info;
  auto pb_printer = google::protobuf::TextFormat::Printer();
  pb_printer.SetSingleLineMode(true);
  pb_printer.PrintToString(pb_item, &info);
  return info;
}

}  // namespace fediux::proto::util
#endif  // SRC_FEDIUX_UTIL_PROTO_LOG_HELPER_H_
