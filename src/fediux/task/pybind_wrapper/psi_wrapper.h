#ifndef SRC_FEDIUX_TASK_PYBIND_WRAPPER_PSI_WRAPPER_H_
#define SRC_FEDIUX_TASK_PYBIND_WRAPPER_PSI_WRAPPER_H_
#include <string>
#include <vector>
#include <memory>

#include "src/fediux/task/semantic/psi_task.h"
#include "src/fediux/protos/common.pb.h"
#include "src/fediux/protos/worker.pb.h"

namespace fediux::task {
class PsiExecutor {
 public:
  explicit PsiExecutor(const std::string& task_req,
                       const std::string& root_ca_path,
                       const std::string& key_path,
                       const std::string& cert_path);
  std::vector<std::string> RunPsi(const std::vector<std::string>& input,
                                  const std::vector<std::string>& parties,
                                  const std::string& receiver,
                                  bool broadcast_result,
                                  const std::string& protocol);
 protected:
  enum class Role : uint8_t {
    kClient,
    kServer,
  };
  retcode NegotiateSubTaskId(std::string* sub_task_id, Role role);
  auto BuildPsiTaskRequest(const std::vector<std::string>& parties,
                           const std::string& receiver,
                           bool broadcast_result,
                           const std::string& protocol,
                           const fediux::rpc::PushTaskRequest& request) ->
      std::unique_ptr<fediux::rpc::PushTaskRequest>;
 private:
  std::unique_ptr<PsiTask> task_ptr_{nullptr};
  std::unique_ptr<fediux::rpc::PushTaskRequest> task_req_ptr_{nullptr};
  std::string root_ca_path_;
  std::string key_path_;
  std::string cert_path_;
};
}  // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_PYBIND_WRAPPER_PSI_WRAPPER_H_
