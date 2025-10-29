#ifndef SRC_FEDIUX_TASK_SEMANTIC_MPC_SCHEDULER_H_
#define SRC_FEDIUX_TASK_SEMANTIC_MPC_SCHEDULER_H_
#include <string>
#include <vector>

#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/task/semantic/scheduler/scheduler.h"
#include "src/fediux/common/common.h"

using fediux::rpc::PushTaskRequest;

namespace fediux::task {
class MPCScheduler : public VMScheduler {
public:
  MPCScheduler() = default;
  MPCScheduler(const std::string &node_id, const std::vector<rpc::Node> &peer_list,
               const PeerDatasetMap &peer_dataset_map, uint8_t party_num,
               bool singleton)
      : VMScheduler(node_id, singleton) {
    party_num_ = party_num;
    peer_list_ = peer_list;
    peer_dataset_map_ = peer_dataset_map;
  }

  retcode dispatch(const PushTaskRequest *pus_request) override;
 protected:
  void push_task(const std::string &node_id,
                  const PeerDatasetMap &peer_dataset_map,
                  const PushTaskRequest &request,
                  const Node& dest_node);

 protected:
  std::vector<rpc::Node> peer_list_;
  PeerDatasetMap peer_dataset_map_;

 private:
  virtual void add_vm(rpc::Node *node, int i,
                      const PushTaskRequest *push_request) = 0;
  uint8_t party_num_;
};

class CRYPTFLOW2Scheduler : public MPCScheduler {
public:
  CRYPTFLOW2Scheduler() = default;
  CRYPTFLOW2Scheduler(const std::string &node_id,
                      const std::vector<rpc::Node> &peer_list,
                      const PeerDatasetMap &peer_dataset_map, bool singleton)
      : MPCScheduler(node_id, peer_list, peer_dataset_map, 2, singleton) {}

private:
  void add_vm(rpc::Node *node, int i, const PushTaskRequest *push_request) override;
};

class FalconScheduler : public MPCScheduler {
public:
  FalconScheduler() = default;
  FalconScheduler(const std::string &node_id,
                  const std::vector<rpc::Node> &peer_list,
                  const PeerDatasetMap &peer_dataset_map, bool singleton)
      : MPCScheduler(node_id, peer_list, peer_dataset_map, 3, singleton) {}

private:
  void add_vm(rpc::Node *node, int i, const PushTaskRequest *push_request) override;
};
} // namespace fediux::task

#endif
