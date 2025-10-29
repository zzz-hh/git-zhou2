#ifndef SRC_FEDIUX_TASK_SEMANTIC_TASK_CONTEXT_H_
#define SRC_FEDIUX_TASK_SEMANTIC_TASK_CONTEXT_H_
#include <unordered_map>
#include <queue>
#include <mutex>
#include <string>
#include <memory>

#include "src/fediux/util/network/link_factory.h"
#include "src/fediux/util/network/link_context.h"
#include "src/fediux/util/threadsafe_queue.h"
#include "src/fediux/common/config/server_config.h"

namespace fediux::task {
// temp data storage
/**
 * TaskContext
 * contains temporary storage, communication link info
*/
class TaskContext {
 public:
  TaskContext() {
    auto link_mode = fediux::network::LinkMode::GRPC;
    link_ctx_ = fediux::network::LinkFactory::createLinkContext(link_mode);
    auto& server_config = fediux::ServerConfig::getInstance();
    if (!server_config.IsInitFlag()) {
      LOG(WARNING) << "instance is not init";
    }

    auto& host_cfg = server_config.getServiceConfig();
    if (host_cfg.use_tls()) {
      LOG(INFO) << "link_ctx_->initCertificate";
      link_ctx_->initCertificate(server_config.getCertificateConfig());
    }
  }

  explicit TaskContext(fediux::network::LinkMode mode) {
    link_ctx_ = fediux::network::LinkFactory::createLinkContext(mode);
    auto& server_config = fediux::ServerConfig::getInstance();
    auto& host_cfg = server_config.getServiceConfig();
    if (host_cfg.use_tls()) {
      LOG(ERROR) << "link_ctx_->initCertificate";
      link_ctx_->initCertificate(server_config.getCertificateConfig());
    }
  }

  void setTaskInfo(const std::string& job_id,
                  const std::string& task_id,
                  const std::string& request_id,
                  const std::string& sub_task_id) {
    link_ctx_->setTaskInfo(job_id, task_id, request_id, sub_task_id);
  }

  std::unique_ptr<fediux::network::LinkContext>& getLinkContext() {
    return link_ctx_;
  }

  void clean() {
    stop_.store(true);
    if (link_ctx_) {
      link_ctx_->Clean();
    }
  }

 private:
  std::unique_ptr<fediux::network::LinkContext> link_ctx_{nullptr};
  std::atomic<bool> stop_{false};
};

}  // namespace fediux::task
#endif  // SRC_FEDIUX_TASK_SEMANTIC_TASK_CONTEXT_H_
