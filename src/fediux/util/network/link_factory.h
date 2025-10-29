#ifndef SRC_FEDIUX_UTIL_NETWORK_LINK_FACTORY_H_
#define SRC_FEDIUX_UTIL_NETWORK_LINK_FACTORY_H_
#include <glog/logging.h>
#include <memory>
#include "src/fediux/util/network/link_context.h"
#include "src/fediux/util/network/grpc_link_context.h"

namespace fediux::network {
enum class LinkMode {
    GRPC = 0,
    RAW_SOCKET,
};

class LinkFactory {
 public:
  static std::unique_ptr<LinkContext> createLinkContext(
      LinkMode mode = LinkMode::GRPC) {
    if (mode == LinkMode::GRPC) {
      return std::make_unique<GrpcLinkContext>();
    } else {
      LOG(ERROR) << "Unimplement Mode: " << static_cast<int>(mode);
    }
    return nullptr;
  }
};
}  // namespace fediux::network
#endif  // SRC_FEDIUX_UTIL_NETWORK_LINK_FACTORY_H_
