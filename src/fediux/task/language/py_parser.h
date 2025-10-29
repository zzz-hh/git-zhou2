#ifndef SRC_FEDIUX_TASK_LANGUAGE_PY_PARSER_H_
#define SRC_FEDIUX_TASK_LANGUAGE_PY_PARSER_H_

#include <string>
#include <vector>

#include "src/fediux/task/language/parser.h"
#include "src/fediux/task/common.h"

namespace fediux::task {

class PyParser : public LanguageParser {
 public:
    PyParser(const rpc::PushTaskRequest &pushTaskRequest)
        : LanguageParser(pushTaskRequest) {
    }
    ~PyParser();
    retcode parseTask() override;
    retcode parseDatasets();
    retcode parseNodes() override;

    std::map<std::string, NodeContext> getNodeContextMap() const {
        return nodes_context_map_;
    }

 private:
    std::string py_code_;
    std::string procotol_;
    std::vector<std::string> roles_;
    std::vector<std::string> func_params_;
    std::map<std::string, NodeContext> nodes_context_map_;
};

}  // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_LANGUAGE_PY_PARSER_H_
