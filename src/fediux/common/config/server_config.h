#ifndef SRC_FEDIUX_COMMON_CONFIG_SERVER_CONFIG_H_
#define SRC_FEDIUX_COMMON_CONFIG_SERVER_CONFIG_H_
#include <glog/logging.h>
#include <string>
#include <atomic>
#include "src/fediux/common/common.h"
#include "src/fediux/common/config/config.h"

namespace fediux {
using fediux::common::CertificateConfig;
using fediux::common::RedisConfig;
using fediux::common::NodeConfig;
class ServerConfig {
 public:
  ServerConfig() = default;
  static ServerConfig& getInstance() {
    static ServerConfig ins;
    return ins;
  }
  retcode initServerConfig(const std::string& config_file);
  Node& getServiceConfig() { return config_.server_config;}
  bool PublicIpProxyEnabled() {return config_.public_ip_proxy_enable;}
  Node& PublicIpProxyConfig() {return config_.public_ip_proxy_config.host_info;}
  CertificateConfig& getCertificateConfig() {return config_.cert_config;}
  NodeConfig& getNodeConfig() {return config_;}
  std::string getConfigFile() {return config_file_;}
  Node& ProxyServerCfg() {return config_.proxy_server_cfg.host_info;}
  std::string& StoragePath() {return config_.storage_info.path;}
  Node& PublicServiceConfig();
  bool IsInitFlag() {return is_init_flag.load(std::memory_order::memory_order_relaxed);}

 protected:
  ServerConfig(const ServerConfig&) = default;
  ServerConfig(ServerConfig&&) = default;
  ServerConfig& operator=(const ServerConfig&) = default;
  ServerConfig& operator=(ServerConfig&&) = default;

 private:
  std::atomic<bool> is_init_flag{false};
  NodeConfig config_;
  std::string config_file_;
};
}  // namespace fediux

#endif  // SRC_FEDIUX_COMMON_CONFIG_SERVER_CONFIG_H_
