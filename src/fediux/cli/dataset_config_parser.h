#ifndef SRC_FEDIUX_CLI_DATASET_CONFIG_PARSER_H_
#define SRC_FEDIUX_CLI_DATASET_CONFIG_PARSER_H_
#include <vector>
#include <string>
#include "src/fediux/common/common.h"
#include "src/fediux/protos/service.pb.h"
#include "src/fediux/cli/cli.h"

namespace fediux {
retcode ParseDatasetMetaInfo(const std::string& config_file,
                             std::vector<rpc::NewDatasetRequest>* requests);
retcode ParseTaskConfigFile(const std::string& file_path,
                            std::vector<rpc::NewDatasetRequest>* requests);
void RegisterDataset(const std::string& task_config_file, SDKClient& client);
}  // namespace fediux
#endif  // SRC_FEDIUX_CLI_DATASET_CONFIG_PARSER_H_
