#include "src/fediux/util/proto_log_helper.h"

namespace fediux::proto::util {
std::string TaskInfoToString(const std::string& request_id) {
  std::string info = "RequestId: ";
  info.append(request_id).append(" ");
  return info;
}
std::string TaskInfoToString(const std::string& request_id,
                             const std::string& task_id) {
//
std::string info;
info.append("TaskId: ").append(task_id).append(", ")
    .append("RequestId: ").append(request_id).append(" ");
return info;
}
std::string TaskInfoToString(const rpc::TaskContext& task_info,
                             bool json_format) {
  return TaskInfoToString(task_info.request_id(), task_info.task_id());
  // std::string info;
  // if (json_format) {
  //   google::protobuf::util::MessageToJsonString(task_info, &info);
  // } else {
  //   auto pb_printer = google::protobuf::TextFormat::Printer();
  //   pb_printer.SetSingleLineMode(true);
  //   pb_printer.PrintToString(task_info, &info);
  // }
  // return info;
}

std::string TaskConfigToString(const rpc::Task& task_config) {
  std::string info;
  auto pb_printer = google::protobuf::TextFormat::Printer();
  pb_printer.SetSingleLineMode(true);
  pb_printer.PrintToString(task_config, &info);
  return info;
}

std::string TaskRequestToString(const rpc::PushTaskRequest& task_req) {
  std::string info;
  auto pb_printer = google::protobuf::TextFormat::Printer();
  pb_printer.SetSingleLineMode(true);
  pb_printer.PrintToString(task_req, &info);
  return info;
}

std::string TaskStatusToString(const rpc::TaskStatus& status) {
  const auto& code_name = rpc::TaskStatus::StatusCode_Name(status.status());
  std::string info;
  info.append("party: ")
      .append("\"").append(status.party()).append("\" ")
      .append("status: ").append(code_name).append(" ")
      .append("message: ")
      .append("\"").append(status.message()).append("\"");
  return info;
}
}  // namespace fediux::proto::util
