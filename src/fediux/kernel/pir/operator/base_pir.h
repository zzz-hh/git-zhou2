#ifndef SRC_FEDIUX_KERNEL_PIR_OPERATOR_BASE_PIR_H_
#define SRC_FEDIUX_KERNEL_PIR_OPERATOR_BASE_PIR_H_
#include <map>
#include <string>
#include "src/fediux/common/common.h"
#include "src/fediux/kernel/pir/common.h"
#include "src/fediux/util/network/link_context.h"
namespace fediux::pir {
using LinkContext = network::LinkContext;
struct Options {
  LinkContext* link_ctx_ref;
  std::map<std::string, Node> party_info;
  std::string self_party;
  std::string code;
  Role role;
  // online
  bool use_cache{false};
  // offline task
  bool generate_db{false};
  std::string db_path;
  Node peer_node;
  Node proxy_node;
};

class BasePirOperator {
 public:
  explicit BasePirOperator(const Options& options) : options_(options) {}
  virtual ~BasePirOperator() = default;
  /**
   * PSI protocol
  */
  retcode Execute(const PirDataType& input, PirDataType* result);
  virtual retcode OnExecute(const PirDataType& input, PirDataType* result) = 0;
  void set_stop() {stop_.store(true);}

 protected:
  bool has_stopped() {
    return stop_.load(std::memory_order::memory_order_relaxed);
  }
  std::string PartyName() {return options_.self_party;}
  Role role() {return options_.role;}
  LinkContext* GetLinkContext() {return options_.link_ctx_ref;}
  Node& PeerNode() {return options_.peer_node;}
  Node& ProxyNode() {return options_.proxy_node;}
  std::string PackageCountKey(const std::string& request_id) {
    return "pack_count";
  }

 protected:
  std::atomic<bool> stop_{false};
  Options options_;
  std::string key_{"pir_key"};
  std::string response_key_{"response_pir_key"};
  std::string key_task_end_{"pir_task_end"};
};
}  // namespace fediux::pir
#endif  // SRC_FEDIUX_KERNEL_PIR_OPERATOR_BASE_PIR_H_
