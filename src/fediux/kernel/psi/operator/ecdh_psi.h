#ifndef SRC_FEDIUX_KERNEL_PSI_OPERATOR_ECDH_PSI_H_
#define SRC_FEDIUX_KERNEL_PSI_OPERATOR_ECDH_PSI_H_
#include <unordered_map>
#include <memory>
#include <string>
#include <set>
#include <vector>

#include "src/fediux/kernel/psi/operator/base_psi.h"
#include "private_set_intersection/cpp/psi_client.h"
#include "src/fediux/protos/common.pb.h"
#include "src/fediux/protos/psi.pb.h"
#include "src/fediux/protos/worker.pb.h"

namespace fediux::psi {
namespace openminded_psi = private_set_intersection;
class EcdhPsiOperator : public BasePsiOperator {
 public:
  explicit EcdhPsiOperator(const Options& options) : BasePsiOperator(options) {}
  retcode OnExecute(const std::vector<std::string>& input,
                    std::vector<std::string>* result) override;

 protected:
  retcode ExecuteAsClient(const std::vector<std::string>& input,
                          std::vector<std::string>* result);
  retcode SendRequetToServer(psi_proto::Request&& psi_request);
  retcode BuildInitParam(int64_t element_size, std::string* init_param);
  retcode SendInitParam(const std::string& init_param);
  retcode SendPSIRequestAndWaitResponse(const psi_proto::Request& request,
                                        rpc::PsiResponse* response);
  retcode SendPSIRequestAndWaitResponse(psi_proto::Request&& request,
                                        rpc::PsiResponse* response);
  retcode ParsePsiResponseFromeString(const std::string& res_str,
                                      rpc::PsiResponse* response);
  retcode GetIntersection(const std::vector<std::string> origin_data,
    const std::unique_ptr<openminded_psi::PsiClient>& client,
    rpc::PsiResponse& response,
    std::vector<std::string>* result);
  // server method
  retcode ExecuteAsServer(const std::vector<std::string>& input);
  retcode InitRequest(psi_proto::Request* psi_request);
  retcode PreparePSIResponse(psi_proto::Response&& psi_response,
                             psi_proto::ServerSetup&& setup);
  retcode RecvInitParam(size_t* client_dataset_size, bool* reveal_intersection);
  void SetFpr(double fpr) {fpr_ = fpr;}

 private:
  bool reveal_intersection_{true};
  double fpr_{0.0001};
};
}  // namespace fediux::psi

#endif  // SRC_FEDIUX_KERNEL_PSI_OPERATOR_ECDH_PSI_H_
