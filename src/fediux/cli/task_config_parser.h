#ifndef SRC_FEDIUX_CLI_TASK_CONFIG_PARSER_H_
#define SRC_FEDIUX_CLI_TASK_CONFIG_PARSER_H_
#include <string>
#include <nlohmann/json.hpp>
#include "src/fediux/common/common.h"
#include "src/fediux/protos/common.pb.h"
#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/cli/cli.h"

namespace fediux {
struct DownloadFileInfo {
  std::string remote_file_path;
  std::string save_as;
};
using DownloadFileListType = std::vector<DownloadFileInfo>;
using TaskFlow = rpc::PushTaskRequest;
retcode BuildRequestWithTaskConfig(const nlohmann::json& js,
                                   TaskFlow* request);
retcode BuildFederatedRequest(const nlohmann::json& js_task_config,
                              rpc::Task* task_ptr);
void fillParamByScalar(const std::string& value_type,
                       const nlohmann::json& obj, rpc::ParamValue* pv);
void fillParamByArray(const std::string& value_type,
                      const nlohmann::json& obj, rpc::ParamValue* pv);
retcode ParseTaskConfigFile(const std::string& file_path,
                            TaskFlow* task_flow,
                            DownloadFileListType* download_file_cfg);
retcode ParseDownFileConfig(const nlohmann::json& js_cfg,
                            DownloadFileListType* download_file_cfg);

retcode DownloadData(fediux::SDKClient& client,
                     const rpc::TaskContext& task_info,
                     const DownloadFileListType& download_files_cfg);
void RunTask(const std::string& task_config_file, SDKClient& client);
}  // namespace fediux
#endif  // SRC_FEDIUX_CLI_TASK_CONFIG_PARSER_H_
