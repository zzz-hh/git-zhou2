#ifndef SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_FL_SCHEDULER_H_
#define SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_FL_SCHEDULER_H_

#include "src/fediux/task/semantic/scheduler/scheduler.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/service/dataset/model.h"
#include "src/fediux/common/common.h"
#include "src/fediux/task/common.h"

using fediux::service::DatasetMetaWithParamTag;
using fediux::service::DatasetMeta;

namespace fediux::task {
class FLScheduler : public VMScheduler {
 public:
  FLScheduler() = default;
  FLScheduler(const std::string &node_id,
              bool singleton,
              const std::vector<NodeWithRoleTag> &peers_with_tag,
              const PeerContextMap &peer_context_map,
              const std::vector<DatasetMetaWithParamTag> &metas_with_role_tag)
            : VMScheduler(node_id, singleton),
            peers_with_tag_(peers_with_tag),
            peer_context_map_(peer_context_map),
            metas_with_role_tag_(metas_with_role_tag) {}
  ~FLScheduler() {}

  retcode dispatch(const PushTaskRequest *pushTaskRequest) override;

 protected:
  retcode ScheduleTask(const std::string& party_name,
                    const Node dest_node,
                    const PushTaskRequest& request);

 private:
  void getDataMetaListByRole(const std::string &role,
      std::vector<std::shared_ptr<DatasetMeta>> *data_meta_list);

  std::vector<NodeWithRoleTag> peers_with_tag_;
  PeerContextMap peer_context_map_;
  std::vector<DatasetMetaWithParamTag> metas_with_role_tag_;

};

}  // namespace fediux::task


#endif  // SRC_FEDIUX_TASK_SEMANTIC_SCHEDULER_FL_SCHEDULER_H_

