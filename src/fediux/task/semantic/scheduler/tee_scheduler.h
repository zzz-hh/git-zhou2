#ifndef SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_TEE_SCHEDULER_H_
#define SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_TEE_SCHEDULER_H_

#include <string>
#include <vector>
#include "src/fediux/task/semantic/scheduler/scheduler.h"
#include "src/fediux/protos/common.pb.h"
#include "src/fediux/util/util.h"
#include "src/fediux/common/common.h"


using fediux::service::DatasetMeta;
using fediux::service::DatasetMetaWithParamTag;
using fediux::rpc::Params;

namespace fediux::task {
/**
 * @brief The TeeScheduler class
 *     TEE scheduler is a SGX2.0 scheduler. Support role:
 *        1. Executor: node that can execute a task in SGX2.0 enclave.
 *        2. DataProvider:  node that can provide data to a task.
 * @todo
 */
class TEEScheduler : public VMScheduler {
  public:
    TEEScheduler() = default;
    TEEScheduler(const std::string &node_id,
                 std::vector<rpc::Node> &peer_list,
                 const PeerDatasetMap &peer_dataset_map,
                 const Params params,
                 bool singleton)
        : VMScheduler(node_id, singleton), peer_list_(peer_list),
          peer_dataset_map_(peer_dataset_map) {

        rpc::Node node;
        node.set_node_id("TEE_Executor");
        auto param_map = params.param_map();
        try {
            std::string server_addr = param_map["server"].value_string();
            // split ip:port
            std::vector<std::string> v;
            str_split(server_addr, &v);
            node.set_ip(v[0]);
            node.set_port(std::stoi(v[1]));
            // Add server node to peer_list_ head.
            peer_list_.insert(peer_list_.begin(), node);
        } catch (std::exception &e) {
            LOG(ERROR) << "get TEE server addr error: " << e.what();
        }

    }

    ~TEEScheduler() {}

    retcode dispatch(const PushTaskRequest *pushTaskRequest) override;

  private:
    void add_vm(rpc::Node *executor, rpc::Node *dpv, int party_id,
                const PushTaskRequest *pushTaskRequest);
    void push_task_to_node(const std::string &node_id,
                           const PeerDatasetMap &peer_dataset_map,
                           const PushTaskRequest &request,
                           const Node& dest_node_address);

    std::vector<rpc::Node> peer_list_;
    const PeerDatasetMap peer_dataset_map_;

}; // class TEEScheduler

} // namespace fediux::task

#endif // SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_TEE_SCHEDULER_H_
