#ifndef SRC_FEDIUX_NODE_NODELET_H_
#define SRC_FEDIUX_NODE_NODELET_H_

#include <string>
#include <future>
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/common/common.h"
#include "src/fediux/common/config/server_config.h"
#ifdef SGX
#include "sgx/ra/service.h"
#include "sgx/engine/sgx_engine.h"
#endif

namespace fediux {
/**
 * @brief The Nodelet class
 * Provide protocols, services
 *
 */
class Nodelet {
 public:
  explicit Nodelet(const std::string &config_file_path,
                  std::shared_ptr<service::DatasetService> service);
  ~Nodelet() = default;
  std::string getNodeletAddr() const {
    return nodelet_addr_;
  }
  std::shared_ptr<service::DatasetService>& getDataService() {
    return dataset_service_;
  }

#ifdef SGX
  std::shared_ptr<sgx::RaTlsService>& GetRaService() {return ra_service_;}
  std::shared_ptr<sgx::TeeEngine>& GetTeeExecutor() {return tee_executor_;}
#endif

 protected:
  void loadConifg(const std::string &config_file_path, unsigned int timeout);

 private:
  std::string nodelet_addr_;
  std::string config_file_path_;
  std::shared_ptr<service::DatasetService> dataset_service_{nullptr};
#ifdef SGX
  std::shared_ptr<sgx::RaTlsService> ra_service_{nullptr};
  std::shared_ptr<sgx::TeeEngine> tee_executor_{nullptr};
  std::unique_ptr<sgx::CertAuth> auth_{nullptr};
  std::unique_ptr<sgx::RaTlsHandlerImpl> ra_handler_{nullptr};
#endif
};

} // namespace fediux

#endif // SRC_FEDIUX_NODE_NODELET_H_
