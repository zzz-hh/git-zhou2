#ifndef SRC_FEDIUX_TASK_SEMANTIC_FACTORY_H_
#define SRC_FEDIUX_TASK_SEMANTIC_FACTORY_H_

#include <glog/logging.h>
#include <memory>

#include "src/fediux/task/semantic/task.h"
#include "src/fediux/task/semantic/mpc_task.h"
#include "src/fediux/task/semantic/fl_task.h"
#include "src/fediux/task/semantic/psi_task.h"
#include "src/fediux/task/semantic/pir_task.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/util/log.h"
#include "src/fediux/util/proto_log_helper.h"

using fediux::rpc::PushTaskRequest;
using fediux::rpc::Language;
using fediux::rpc::TaskType;
using fediux::service::DatasetService;
namespace pb_util = fediux::proto::util;
namespace fediux::task {

class TaskFactory {
 public:
  static std::shared_ptr<TaskBase> Create(const std::string& node_id,
      const PushTaskRequest& request,
      std::shared_ptr<DatasetService> dataset_service,
      void* ra_service = nullptr,
      void* executor = nullptr) {
    auto task_language = request.task().language();
    const auto& task_info = request.task().task_info();
    std::string task_inof_str = pb_util::TaskInfoToString(task_info);
    auto task_type = request.task().type();
    std::shared_ptr<TaskBase> task_ptr{nullptr};
    switch (task_language) {
    case Language::PYTHON:
      task_ptr = TaskFactory::CreateFLTask(node_id, request, dataset_service);
      break;
    case Language::PROTO: {
      switch (task_type) {
      case rpc::TaskType::ACTOR_TASK:
        task_ptr = TaskFactory::CreateMPCTask(node_id, request, dataset_service);
        break;
      case rpc::TaskType::PSI_TASK:
        task_ptr =
            TaskFactory::CreatePSITask(node_id, request, dataset_service,
                                       ra_service, executor);
        break;
      case rpc::TaskType::PIR_TASK:
        task_ptr = TaskFactory::CreatePIRTask(node_id, request, dataset_service);
        break;
      default:
        LOG(ERROR) << task_inof_str << "unsupported task type: " << task_type;
        break;
      }
      break;
    }
    default:
      LOG(ERROR) << task_inof_str << "unsupported language: " << task_language;
      break;
    }
    return task_ptr;
  }

  static std::shared_ptr<TaskBase> CreateFLTask(const std::string& node_id,
      const PushTaskRequest& request,
      std::shared_ptr<DatasetService> dataset_service) {
    const auto& task_param = request.task();
    return std::make_shared<FLTask>(node_id, &task_param,
                                    request, dataset_service);
  }

  static std::shared_ptr<TaskBase> CreateMPCTask(const std::string& node_id,
      const PushTaskRequest& request,
      std::shared_ptr<DatasetService> dataset_service) {
    const auto& _function_name = request.task().code();
    const auto& task_param = request.task();
    return std::make_shared<MPCTask>(node_id, _function_name,
                                    &task_param, dataset_service);
  }

  static std::shared_ptr<TaskBase> CreatePSITask(const std::string& node_id,
      const PushTaskRequest& request,
      std::shared_ptr<DatasetService> dataset_service,
      void* ra_server,
      void* tee_engine) {
    const auto& task_config = request.task();
    std::shared_ptr<TaskBase> task_ptr{nullptr};
    task_ptr = std::make_shared<PsiTask>(&task_config, dataset_service,
                                         ra_server, tee_engine);
    return task_ptr;
  }

  static std::shared_ptr<TaskBase> CreatePIRTask(const std::string& node_id,
      const PushTaskRequest& request,
      std::shared_ptr<DatasetService> dataset_service) {
    const auto& task_config = request.task();
    return std::make_shared<PirTask>(&task_config, dataset_service);
  }

};
}  // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_SEMANTIC_FACTORY_H_
