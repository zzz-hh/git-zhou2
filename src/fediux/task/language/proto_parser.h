#ifndef SRC_FEDIUX_TASK_LANGUAGE_PROTO_PARSER_H_
#define SRC_FEDIUX_TASK_LANGUAGE_PROTO_PARSER_H_

#include <vector>

#include "src/fediux/task/language/parser.h"
#include "src/fediux/common/common.h"

using fediux::service::DatasetWithParamTag;

namespace fediux::task {
class ProtoParser : public LanguageParser {
 public:
  ProtoParser(const rpc::PushTaskRequest &pushTaskRequest);
  ~ProtoParser() = default;
  retcode parseTask() override {return retcode::SUCCESS;}
  retcode parseDatasets() override;
  retcode parseNodes() override {return retcode::SUCCESS;}
};

}  // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_LANGUAGE_PROTO_PARSER_H_
