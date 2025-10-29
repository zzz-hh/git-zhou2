#ifndef SRC_FEDIUX_TASK_ENGINE_TASK_EXECUTOR_H_
#define SRC_FEDIUX_TASK_ENGINE_TASK_EXECUTOR_H_
#include <memory>

#include "src/fediux/common/common.h"
#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/util/network/link_context.h"
#include "src/fediux/util/network/link_factory.h"
#include "src/fediux/task/semantic/task.h"

namespace fediux::task_engine {
using TaskRequest = rpc::PushTaskRequest;
using TaskRequestPtr = std::unique_ptr<TaskRequest>;
using LinkMode = network::LinkMode;
using LinkContext = network::LinkContext;
using LinkContextPtr = std::unique_ptr<LinkContext>;
using TaskPtr = std::shared_ptr<fediux::task::TaskBase>;
using DatasetService = fediux::service::DatasetService;
using DatasetServicePtr = std::shared_ptr<DatasetService>;
class TaskEngine {
 public:
  TaskEngine() = default;
  ~TaskEngine() = default;
  retcode Init(const std::string& server_id,
               const std::string& server_config_file,
               const std::string& request);
  retcode Execute();

  retcode GetScheduleNode();
  retcode UpdateStatus(rpc::TaskStatus::StatusCode code_status,
                       const std::string& msg_info);

 protected:
  retcode ParseTaskRequest(const std::string& request_str);
  retcode InitCommunication();
  retcode InitDatasetSerivce();
  retcode CreateTask();
 private:
  TaskRequestPtr task_request_{nullptr};
  std::string node_id_;
  std::string config_file_;
  Node schedule_node_;
  bool schedule_node_available_{false};
  LinkMode link_mode_{LinkMode::GRPC};
  LinkContextPtr link_ctx_{nullptr};
  TaskPtr task_{nullptr};
  DatasetServicePtr dataset_service_{nullptr};
};
}  // namespace fediux::task_engine
#endif  // SRC_FEDIUX_TASK_ENGINE_TASK_EXECUTOR_H_
