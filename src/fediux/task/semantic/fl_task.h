#ifndef SRC_FEDIUX_TASK_SEMANTIC_FL_TASK_H_
#define SRC_FEDIUX_TASK_SEMANTIC_FL_TASK_H_

#include <string>
#include <vector>

#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/task/semantic/task.h"
#include "Poco/Process.h"

using fediux::rpc::PushTaskRequest;

namespace fediux::task {
/* *
 * @brief Federated Learning task, only support python code.
 *  TODO Run python use pybind11.
 */
class FLTask : public TaskBase {
 public:
    FLTask(const std::string &node_id, const TaskParam *task_param,
           const PushTaskRequest &task_request,
           std::shared_ptr<DatasetService> dataset_service);

    ~FLTask() = default;
    int execute() override;
    void kill_task() {
      LOG(WARNING) << "task receives kill task request and stop stauts";
      stop_.store(true);
      task_context_.clean();
    };

 private:
  const PushTaskRequest* task_request_{nullptr};
  std::unique_ptr<Poco::ProcessHandle> process_handler_{nullptr};
};
} // namespace fediux::task

#endif // SRC_FEDIUX_TASK_SEMANTIC_FL_TASK_H_
