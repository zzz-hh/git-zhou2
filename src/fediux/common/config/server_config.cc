#include "src/fediux/common/config/server_config.h"
#include <unistd.h>
#include <yaml-cpp/yaml.h>
#include <fstream>

namespace fediux {
retcode ServerConfig::initServerConfig(const std::string& config_file) {
  if (is_init_flag.load(std::memory_order::memory_order_relaxed)) {
    return retcode::SUCCESS;
  }
  config_file_ = config_file;
  try {
    YAML::Node root_config = YAML::LoadFile(config_file);
    config_ = root_config.as<fediux::common::NodeConfig>();
    is_init_flag.store(true);
  } catch (std::exception& e) {
    LOG(ERROR) << "load config file: " << config_file << " failed. "
               << e.what();
    return retcode::FAIL;
  }
  return retcode::SUCCESS;
}
Node& ServerConfig::PublicServiceConfig() {
  if (PublicIpProxyEnabled()) {
    return PublicIpProxyConfig();
  } else {
    return getServiceConfig();
  }
}
}  // namespace fediux
