#include "src/fediux/task/semantic/scheduler/fl_scheduler.h"

#include <memory>

#include "absl/strings/str_cat.h"
#include "src/fediux/task/language/py_parser.h"
#include "src/fediux/protos/common.pb.h"
#include "src/fediux/service/dataset/util.hpp"
#include "src/fediux/util/log.h"
#include "src/fediux/util/proto_log_helper.h"

using fediux::rpc::Task;
using fediux::rpc::Params;
using fediux::rpc::ParamValue;
using fediux::rpc::VarType;
using fediux::rpc::TaskType;
using fediux::rpc::VirtualMachine;
using fediux::rpc::EndPoint;
using fediux::rpc::LinkType;

using fediux::service::DataURLToDetail;
namespace pb_util = fediux::proto::util;

namespace fediux::task {

retcode FLScheduler::ScheduleTask(const std::string& party_name,
                                  const Node dest_node,
                                  const PushTaskRequest& request) {
  SET_THREAD_NAME("FLScheduler");
  PushTaskReply reply;
  PushTaskRequest send_request;
  send_request.CopyFrom(request);
  auto task_ptr = send_request.mutable_task();
  task_ptr->set_party_name(party_name);
  const auto& task_info = send_request.task().task_info();
  std::string TASK_INFO_STR = pb_util::TaskInfoToString(task_info);
  // fill scheduler info
  AddSchedulerNode(task_ptr);
  // send request
  std::string dest_node_address = dest_node.to_string();
  LOG(INFO) << TASK_INFO_STR << "dest node " << dest_node_address;
  auto channel = this->getLinkContext()->getChannel(dest_node);
  auto ret = channel->executeTask(send_request, &reply);
  if (ret == retcode::SUCCESS) {
    VLOG(5) << TASK_INFO_STR
            << "submit task to : " << dest_node_address << " reply success";
  } else {
    LOG(ERROR) << TASK_INFO_STR
               << "submit task to : " << dest_node_address << " reply failed";
    return retcode::FAIL;
  }
  parseNotifyServer(reply);
  return retcode::SUCCESS;
}

/**
 * @brief Dispatch FL task to different role. eg: xgboost host & guest.
 *
 */
retcode FLScheduler::dispatch(const PushTaskRequest *pushTaskRequest) {
  PushTaskRequest send_request;
  send_request.CopyFrom(*pushTaskRequest);
  std::string request_str;
  request_str = pb_util::TaskRequestToString(send_request);
  LOG(INFO) << "FLScheduler::dispatch: " << request_str;
  const auto& task_info = send_request.task().task_info();
  std::string TASK_INFO_STR = pb_util::TaskInfoToString(task_info);
  // schedule
  std::vector<std::thread> thrds;
  const auto& party_access_info = send_request.task().party_access_info();
  for (const auto& [party_name, node] : party_access_info) {
    this->error_msg_.insert({party_name, ""});
  }
  for (const auto& [party_name, node] : party_access_info) {
    Node dest_node;
    pbNode2Node(node, &dest_node);
    LOG(INFO) << TASK_INFO_STR
        << "Dispatch SubmitTask to: " << dest_node.to_string() << " "
        << "party_name: " << party_name;
    thrds.emplace_back(
      std::thread(
        &FLScheduler::ScheduleTask,
        this,
        party_name,
        dest_node,
        std::ref(send_request)));
  }
  for (auto&& t : thrds) {
    t.join();
  }
  if (has_error()) {
    return retcode::FAIL;
  }
  return retcode::SUCCESS;
}

void FLScheduler::getDataMetaListByRole(const std::string &role,
    std::vector<std::shared_ptr<DatasetMeta>> *data_meta_list) {
  for (size_t i = 0; i < this->metas_with_role_tag_.size(); i++) {
    if (this->metas_with_role_tag_[i].second == role) {
      data_meta_list->push_back(this->metas_with_role_tag_[i].first);
    }
  }
}
} // namespace fediux::task
