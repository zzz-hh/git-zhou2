#ifndef SRC_FEDIUX_TASK_LANGUAGE_FACTORY_H_
#define SRC_FEDIUX_TASK_LANGUAGE_FACTORY_H_

#include <glog/logging.h>
#include <memory>

#include "src/fediux/task/language/parser.h"
#include "src/fediux/task/language/proto_parser.h"
#include "src/fediux/task/language/py_parser.h"
#include "src/fediux/util/log.h"
#include "src/fediux/util/proto_log_helper.h"

using fediux::rpc::Language;
using fediux::rpc::PushTaskRequest;
using fediux::rpc::TaskType;
using fediux::service::DatasetService;

namespace pb_util = fediux::proto::util;
namespace fediux::task {
using fediux::rpc::Language;
class LanguageParserFactory {
 public:
  static std::shared_ptr<LanguageParser> Create(
      const PushTaskRequest &task_request) {
    auto language = task_request.task().language();
    std::shared_ptr<LanguageParser> parser_ptr{nullptr};
    switch (language) {
    case Language::PROTO:
      parser_ptr = std::make_shared<ProtoParser>(task_request);
      break;
    case Language::PYTHON:
      parser_ptr = std::make_shared<PyParser>(task_request);
      break;
    default:
      const auto& task_info = task_request.task().task_info();
      std::string task_inof_str = pb_util::TaskInfoToString(task_info);
      LOG(WARNING) << task_inof_str << "Unsupported language: " << language;
      break;
    }
    return parser_ptr;
  }
};  // class LanguageParserFactory
}   // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_LANGUAGE_FACTORY_H_
