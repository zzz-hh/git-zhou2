#include "src/fediux/task/semantic/scheduler/pir_scheduler.h"
#include <utility>

#include "absl/memory/memory.h"
#include "absl/strings/str_cat.h"
#include "src/fediux/common/config/server_config.h"
#include "src/fediux/util/log.h"
#include "src/fediux/util/proto_log_helper.h"
#include "src/fediux/common/value_check_util.h"

using fediux::rpc::ParamValue;
using fediux::rpc::TaskType;
using fediux::rpc::VirtualMachine;
using fediux::rpc::VarType;
using fediux::rpc::PirType;
namespace pb_util = fediux::proto::util;

namespace fediux::task {
retcode PIRScheduler::ScheduleTask(const std::string& party_name,
                                  const Node dest_node,
                                  const PushTaskRequest& request) {
  SET_THREAD_NAME("PIRScheduler");
  PushTaskReply reply;
  PushTaskRequest send_request;
  send_request.CopyFrom(request);
  const auto& task_info = send_request.task().task_info();
  std::string TASK_INFO_STR = pb_util::TaskInfoToString(task_info);
  auto task_ptr = send_request.mutable_task();
  task_ptr->set_party_name(party_name);
  if (party_name == PARTY_SERVER) {
    // remove client data when send data to server
    auto param_map_ptr = task_ptr->mutable_params()->mutable_param_map();
    auto it = param_map_ptr->find("clientData");
    if (it != param_map_ptr->end()) {
      it->second.Clear();
    }
  }
  // fill scheduler info
  AddSchedulerNode(task_ptr);
  // send request
  std::string dest_node_address = dest_node.to_string();
  LOG(INFO) << TASK_INFO_STR << "dest node " << dest_node_address;
  auto channel = this->getLinkContext()->getChannel(dest_node);
  auto ret = channel->executeTask(send_request, &reply);
  if (ret == retcode::SUCCESS) {
    VLOG(5) << TASK_INFO_STR
        <<  "submit task to : " << dest_node_address << " reply success";
  } else {
    set_error();
    LOG(ERROR) << TASK_INFO_STR
        << "submit task to : " << dest_node_address << " reply failed";
    return retcode::FAIL;
  }
  parseNotifyServer(reply);
  return retcode::SUCCESS;
}

retcode PIRScheduler::dispatch(const PushTaskRequest *pushTaskRequest) {
  PushTaskRequest push_request;
  push_request.CopyFrom(*pushTaskRequest);
  const auto& params = push_request.task().params().param_map();
  const auto& task_info = push_request.task().task_info();
  std::string TASK_INFO_STR = pb_util::TaskInfoToString(task_info);
  // if query request using query keyword instead of dataset,
  // add client access info as dispatch server info
  auto it = params.find("clientData");
  if (it != params.end()) {
    auto& pv_client_data = it->second;
    if (pv_client_data.is_array()) {
      auto party_access_info =
          push_request.mutable_task()->mutable_party_access_info();
      auto& party_info = (*party_access_info)[PARTY_CLIENT];
      auto& local_node = getLocalNodeCfg();
      node2PbNode(local_node, &party_info);
    }
  }
  int pirType = PirType::ID_PIR;
  auto param_it = params.find("pirType");
  if (param_it != params.end()) {
    pirType = param_it->second.value_int32();
  }
  const auto& participate_node = push_request.task().party_access_info();
  do {
    auto it = params.find("DbInfo");
    if (it != params.end()) {  // task for offline generate query db
      break;
    }
    // check the party number for this task
    std::set<std::string> dup_filter;
    for (const auto& [party_name, node] : participate_node) {
      Node node_info;
      pbNode2Node(node, &node_info);
      dup_filter.insert(node_info.to_string());
      this->error_msg_.insert({party_name, ""});
    }
    if (dup_filter.size() < 2) {
      std::string error_msg = "PIR task need 2 party "
                            "to participate for this task.";
      error_msg.append("but get ").append(std::to_string(dup_filter.size()));
      RaiseException(error_msg);
    }
  } while (0);

  LOG(INFO) << TASK_INFO_STR
      << "begin to Dispatch SubmitTask to PIR task party node ...";
  std::vector<std::thread> thrds;
  for (const auto& [party_name, node] : participate_node) {
    Node dest_node;
    pbNode2Node(node, &dest_node);
    LOG(INFO) << TASK_INFO_STR
        << "Dispatch SubmitTask to PIR party node: "
        << dest_node.to_string() << " "
        << "party_name: " << party_name;
    thrds.emplace_back(
      std::thread(
        &PIRScheduler::ScheduleTask,
        this,
        party_name,
        dest_node,
        std::ref(push_request)));
  }
  for (auto &t : thrds) {
    t.join();
  }
  if (has_error()) {
    return retcode::FAIL;
  }
  return retcode::SUCCESS;
}

}  // namespace fediux::task
