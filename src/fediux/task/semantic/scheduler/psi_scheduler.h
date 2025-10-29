#ifndef SRC_FEDIUX_TASK_SEMANTIC_PSI_SCHEDULER_H_
#define SRC_FEDIUX_TASK_SEMANTIC_PSI_SCHEDULER_H_

#include <glog/logging.h>
#include <cmath>
#include <iostream>
#include <memory>
#include <numeric>
#include <string>
#include <thread>
#include <vector>
#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/task/semantic/scheduler/scheduler.h"
#include "src/fediux/common/common.h"

using fediux::rpc::PushTaskReply;
using fediux::rpc::PushTaskRequest;
using fediux::rpc::VMNode;
using fediux::service::DatasetWithParamTag;
using fediux::task::PeerDatasetMap;

namespace fediux::task {

class PSIScheduler : public VMScheduler {
 public:
  PSIScheduler(const std::string &node_id,
                const std::vector<rpc::Node> &peer_list,
                const PeerDatasetMap &peer_dataset_map, bool singleton)
    : VMScheduler(node_id, singleton), peer_list_(peer_list),
      peer_dataset_map_(peer_dataset_map) {}

  retcode dispatch(const PushTaskRequest *pushTaskRequest) override;
  void add_vm(rpc::Node *single_node, int i, const PushTaskRequest *pushTaskRequest);
 protected:
  retcode ScheduleTask(const std::string& party_name,
                      const Node dest_node,
                      const PushTaskRequest& request);
private:
    const std::vector<rpc::Node> peer_list_;
    const PeerDatasetMap peer_dataset_map_;
};

} // namespace fediux::task
#endif // SRC_FEDIUX_TASK_SEMANTIC_PSI_SCHEDULER_H_
