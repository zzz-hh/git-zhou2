#ifndef SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_H_
#define SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_H_

#include <algorithm>
#include <cmath>
#include <iostream>
#include <memory>
#include <numeric>
#include <string>
#include <thread>
#include <vector>
#include <future>

#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/util/network/link_context.h"
#include "src/fediux/util/network/link_factory.h"
#include "src/fediux/common/config/server_config.h"

using fediux::rpc::PushTaskReply;
using fediux::rpc::PushTaskRequest;
using fediux::rpc::VMNode;
using fediux::service::DatasetWithParamTag;

namespace fediux::task {
using PeerDatasetMap = std::map<std::string, std::vector<DatasetWithParamTag>>;

class VMScheduler {
 public:
  VMScheduler();
  VMScheduler(const std::string &node_id, bool singleton);
  virtual ~VMScheduler() = default;
  virtual retcode dispatch(const PushTaskRequest *pushTaskRequest);
  virtual void set_dataset_owner(
      std::map<std::string, std::string> &dataset_owner) {}

  inline std::string get_node_id() const {return node_id_;}
  void parseNotifyServer(const PushTaskReply& reply);

  void addTaskServer(Node&& node_info);
  void addTaskServer(const Node& node_info);

  auto getLinkContext() -> std::unique_ptr<fediux::network::LinkContext>& {
    return link_ctx_;
  }
  std::vector<Node>& taskServer() {
    return task_server_info;
  }

 protected:
  retcode AddSchedulerNode(rpc::Task* task);
  void initCertificate();
  Node& getLocalNodeCfg() const;
  void InitLinkContext();
  retcode ScheduleTask(const std::string& party_name,
                    const Node dest_node,
                    const PushTaskRequest& request);
  void set_error() {error_.store(true);}
  bool has_error() {return error_.load(std::memory_order::memory_order_relaxed);}
 protected:
  const std::string node_id_;
  bool singleton_;
  std::unique_ptr<fediux::network::LinkContext> link_ctx_{nullptr};
  std::mutex task_server_mtx;
  std::vector<Node> task_server_info;
  std::atomic<bool> error_{false};        //
  std::map<std::string, std::string> error_msg_;
};
} // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_H_
