#ifndef SRC_FEDIUX_TASK_SEMANTIC_TASK_H_
#define SRC_FEDIUX_TASK_SEMANTIC_TASK_H_
#include <glog/logging.h>
#include "src/fediux/protos/common.pb.h"
#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/task/semantic/task_context.h"
#include "src/fediux/common/value_check_util.h"

using fediux::rpc::Task;
using fediux::service::DatasetService;

namespace fediux::task {
using TaskParam = fediux::rpc::Task;

/**
 * @brief Basic task class
 *
 */
class TaskBase {
 public:
  using task_context_t = TaskContext;
  TaskBase() = default;
  TaskBase(const TaskParam* task_param,
          std::shared_ptr<DatasetService> dataset_service);

  virtual ~TaskBase() = default;
  virtual int execute() {return 0;};
  virtual void kill_task() {
    LOG(WARNING) << "task receives kill task request and stop stauts";
    stop_.store(true);
    task_context_.clean();
  };

  bool has_stopped() {
    return stop_.load(std::memory_order_relaxed);
  }

  void setTaskInfo(const std::string& node_id, const std::string& job_id ,
                   const std::string& task_id, const std::string& request_id,
                   const std::string& sub_task_id) {
    job_id_ = job_id;
    task_id_ = task_id;
    request_id_ = request_id;
    node_id_ = node_id;
    sub_task_id_ = sub_task_id;
    task_context_.setTaskInfo(job_id, task_id, request_id, sub_task_id);
  }

  inline std::string job_id() {
    return job_id_;
  }
  inline std::string task_id() {
    return task_id_;
  }
  inline std::string node_id() {
    return node_id_;
  }
  inline std::string request_id() {
    return request_id_;
  }
  inline std::string sub_task_id() {
    return sub_task_id_;
  }
  inline std::string party_name() {
    return party_name_;
  }
  inline task_context_t& getTaskContext() {
    return task_context_;
  }
  inline task_context_t* getMutableTaskContext() {
    return &task_context_;
  }
  void setTaskParam(const TaskParam& task_param);
  TaskParam* getTaskParam();
  std::shared_ptr<DatasetService>& getDatasetService() {
    return dataset_service_;
  }
  retcode ExtractProxyNode(const rpc::Task& task_config, Node* proxy_node);

  retcode send(const std::string& key,
               const Node& dest_node,
               const std::string& send_buff);
  retcode send(const std::string& key,
               const Node& dest_node,
               std::string_view send_buff);
  retcode recv(const std::string& key, std::string* recv_buff);
  retcode recv(const std::string& key, char* recv_buff, size_t length);
  retcode sendRecv(const std::string& key, const Node& dest_node,
      const std::string& send_buff, std::string* recv_buff);
  retcode sendRecv(const std::string& key, const Node& dest_node,
      std::string_view send_buff, std::string* recv_buff);
  /**
   * prepare data for sendRecv interface called by peer,
   * the server just prepare data and push into send queue
  */
  retcode pushDataToSendQueue(const std::string& key, std::string&& send_data);

 protected:
   std::atomic<bool> stop_{false};
   TaskParam task_param_;
   std::shared_ptr<DatasetService> dataset_service_;
   task_context_t task_context_;
   std::string job_id_;
   std::string task_id_;
   std::string node_id_;
   std::string sub_task_id_;
   std::string request_id_;
   std::string party_name_;
   bool is_dataset_detail_{false};
};

} // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_SEMANTIC_TASK_H_
