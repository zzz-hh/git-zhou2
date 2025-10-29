#ifndef SRC_FEDIUX_UTIL_UTIL_H_
#define SRC_FEDIUX_UTIL_UTIL_H_

#include <glog/logging.h>
#include <unistd.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <errno.h>
#include <string.h>
#include <fcntl.h>
#include <utility>
#include <cmath>
#include <sstream>
#include <algorithm>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
#include <mutex>
#include <list>
#include <unordered_map>

#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/common/common.h"
namespace fediux {

void str_split(const std::string& str, std::vector<std::string>* v,
               char delimiter = ':');
void str_split(const std::string& str, std::vector<std::string>* v,
                const std::string& delimiter);
void peer_to_list(const std::vector<std::string>& peer,
                  std::vector<fediux::rpc::Node>* list);
void sort_peers(std::vector<std::string>* peers);
retcode pbNode2Node(const fediux::rpc::Node& pb_node, Node* node);
retcode node2PbNode(const Node& node, rpc::Node* pb_node);
retcode parseToNode(const std::string& node_info, Node* node);
retcode parseTopbNode(const std::string& node_info, rpc::Node* node);

class SCopedTimer {
 public:
  SCopedTimer() {
    start_ = std::chrono::high_resolution_clock::now();
  }
  template<typename T = std::chrono::milliseconds>
  double timeElapse() {
    auto now_ = std::chrono::high_resolution_clock::now();
    auto time_diff = std::chrono::duration_cast<T>(now_ - start_).count();
    return time_diff;
  }
 private:
  std::chrono::high_resolution_clock::time_point start_;
};

int getAvailablePort(uint32_t* port);
std::string strToUpper(const std::string& str);
std::string strToLower(const std::string& str);
std::string getCurrentProcessPath();
std::string getCurrentProcessDir();
std::string buf_to_hex_string(const uint8_t* pdata, size_t size);

}  // namespace fediux

#endif  // SRC_FEDIUX_UTIL_UTIL_H_
