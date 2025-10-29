#ifndef SRC_FEDIUX_TASK_LANGUAGE_PARSER_H_
#define SRC_FEDIUX_TASK_LANGUAGE_PARSER_H_

#include <string>
#include <map>
#include <vector>

#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/service/dataset/service.h"

using fediux::service::DatasetWithParamTag;

namespace fediux::task {
// Fediux language layer
class LanguageParser {
 public:
    explicit LanguageParser(const rpc::PushTaskRequest& task_request);
    ~LanguageParser() = default;
    virtual retcode parseTask() = 0;
    virtual retcode parseDatasets() = 0;
    virtual retcode parseNodes()  = 0;
    retcode MergePartyAccessInfo(
        const std::map<std::string, Node>& party_access_info);

    rpc::PushTaskRequest& getPushTaskRequest() {
      return task_request_;
    }
    std::vector<DatasetWithParamTag>& getDatasets() {
      return input_datasets_with_tag_;
    }

 protected:
    rpc::PushTaskRequest task_request_;
    std::vector<DatasetWithParamTag> input_datasets_with_tag_;
};
}  // namespace fediux::task
#endif  // SRC_FEDIUX_TASK_LANGUAGE_PARSER_H_
