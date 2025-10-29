#ifndef SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_ABY3_SCHEDULER_H_
#define SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_ABY3_SCHEDULER_H_
#include <glog/logging.h>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <memory>
#include <numeric>
#include <string>
#include <thread>
#include <vector>
#include <map>

#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/task/semantic/scheduler/scheduler.h"
#include "src/fediux/common/common.h"

using PushTaskReply = fediux::rpc::PushTaskReply;
using PushTaskRequest = fediux::rpc::PushTaskRequest;
using VMNode = fediux::rpc::VMNode;
using DatasetWithParamTag = fediux::service::DatasetWithParamTag;
using PeerDatasetMap = fediux::task::PeerDatasetMap;

namespace fediux::task {
class ABY3Scheduler : public VMScheduler {
 public:
  ABY3Scheduler() = default;
  ABY3Scheduler(const std::string &node_id,
                const std::vector<rpc::Node> &peer_list,
                const PeerDatasetMap &peer_dataset_map, bool singleton)
      : VMScheduler(node_id, singleton),
        peer_list_(peer_list),
        peer_dataset_map_(peer_dataset_map) {}

  retcode dispatch(const PushTaskRequest *pushTaskRequest) override;
  void add_vm(int party_id,
              const PushTaskRequest& pushTaskRequest,
              const std::vector<rpc::Node>& party_nodes,
              rpc::Node *single_node);

 protected:
  retcode ScheduleTask(const std::string& party_name,
                      const Node dest_node,
                      const PushTaskRequest& request);

 private:
  const std::vector<rpc::Node> peer_list_;
  const PeerDatasetMap peer_dataset_map_;
  std::map<std::string, std::string> dataset_owner_;
};

}  // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_ABY3_SCHEDULER_H_
