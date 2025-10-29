#ifndef SRC_FEDIUX_CLI_CLI_H_
#define SRC_FEDIUX_CLI_CLI_H_

#include <glog/logging.h>
#include <grpc/grpc.h>
#include <grpcpp/channel.h>
#include <grpcpp/client_context.h>
#include <grpcpp/create_channel.h>
#include <grpcpp/security/credentials.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
#include <map>

#include "src/fediux/protos/worker.grpc.pb.h"
#include "src/fediux/protos/common.pb.h"
#include "src/fediux/common/config/config.h"
#include "src/fediux/util/util.h"
#include "src/fediux/protos/service.grpc.pb.h"
#include "src/fediux/util/network/link_context.h"
#include "src/fediux/common/common.h"

using fediux::rpc::VMNode;
using fediux::rpc::PushTaskRequest;
using fediux::rpc::PushTaskReply;
using fediux::rpc::Task;
using fediux::rpc::TaskType;
using fediux::rpc::Language;
using fediux::rpc::Params;
using fediux::rpc::VarType;

namespace fediux {
class SDKClient {
 public:
  explicit SDKClient(std::shared_ptr<fediux::network::IChannel> channel,
        fediux::network::LinkContext* link_ctx)
      : channel_(channel), link_ctx_ref_(link_ctx) {
  }

  retcode SubmitTask(const rpc::PushTaskRequest& task_request,
                     rpc::PushTaskReply* task_info);
  retcode DownloadData(const rpc::TaskContext& request_id,
                       const std::vector<std::string>& file_list,
                       std::vector<std::string>* recv_data);
  retcode SaveData(const std::string& file_name,
                   const std::vector<std::string>& recv_data);
  retcode CheckTaskStauts(const rpc::PushTaskReply& task_reply_info);
  retcode RegisterDataset(const rpc::NewDatasetRequest& req,
                          rpc::NewDatasetResponse* reply);
 private:
  std::shared_ptr<fediux::network::IChannel> channel_{nullptr};
  fediux::network::LinkContext* link_ctx_ref_{nullptr};
};

}  // namespace fediux

#endif  // SRC_FEDIUX_CLI_CLI_H_
