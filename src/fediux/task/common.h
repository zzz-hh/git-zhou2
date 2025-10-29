//
#ifndef SRC_FEDIUX_TASK_SEMANTIC_COMMON_H_
#define SRC_FEDIUX_TASK_SEMANTIC_COMMON_H_
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/protos/common.pb.h"
using fediux::rpc::Task;
using fediux::rpc::Language;
using fediux::service::DatasetService;
using fediux::service::DatasetWithParamTag;
using fediux::service::DatasetMetaWithParamTag;

namespace fediux::task {
struct NodeContext {
    std::string role;
    std::string protocol;
    std::string next_peer;
    std::string task_type;
    std::vector<std::string> datasets;
    std::string dumps_func;
    std::map<std::string, std::string> dataset_port_map;
};
using PeerDatasetMap = std::map<std::string, std::vector<DatasetWithParamTag>>;
using NodeWithRoleTag = std::pair<rpc::Node, std::string>;
using PeerContextMap = std::map<std::string, NodeContext>; // key: role name
}  // namespace fediux::task
#endif  // SRC_FEDIUX_TASK_SEMANTIC_COMMON_H_
