#include "src/fediux/task/language/parser.h"

namespace fediux::task {
LanguageParser::LanguageParser(const rpc::PushTaskRequest& task_request) {
  task_request_.CopyFrom(task_request);
}

retcode LanguageParser::MergePartyAccessInfo(
    const std::map<std::string, Node>& party_access_info) {
  std::map<std::string, Node> filtered_party;
  auto party_access_info_ptr =
      this->task_request_.mutable_task()->mutable_party_access_info();
  // fetch all party from mutable_party_access_info
  for (const auto& [party_name, pb_node] : *party_access_info_ptr) {
    Node node;
    pbNode2Node(pb_node, &node);
    auto iter = filtered_party.find(party_name);
    if (iter == filtered_party.end()) {
      filtered_party[party_name] = std::move(node);
    }
  }
  // need_merged
  for (const auto& [party_name, node] : party_access_info) {
    auto iter = filtered_party.find(party_name);
    if (iter == filtered_party.end()) {
      filtered_party[party_name] = node;
    }
  }
  // refill all
  party_access_info_ptr->clear();
  int32_t party_id{0};
  for (auto& [party_name, node] : filtered_party) {
    auto& party_node = (*party_access_info_ptr)[party_name];
    node2PbNode(node, &party_node);
    party_node.set_party_id(party_id);
    party_id++;
  }
  return retcode::SUCCESS;
}
}  // namespace fediux::task {