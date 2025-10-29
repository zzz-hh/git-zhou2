#include <glog/logging.h>
#include <unistd.h>
#include <iostream>
#include <sstream>
#include <fstream>

#include "src/fediux/protos/common.pb.h"
#include "src/fediux/task/language/proto_parser.h"
#include "src/fediux/util/util.h"
#include "src/fediux/util/log.h"
#include "src/fediux/util/proto_log_helper.h"

using fediux::rpc::Params;
using fediux::rpc::ParamValue;
namespace pb_util = fediux::proto::util;
namespace fediux::task {
ProtoParser::ProtoParser(const rpc::PushTaskRequest& task_request)
    : LanguageParser(task_request) {}

retcode ProtoParser::parseDatasets() {
  const auto& task_config = this->getPushTaskRequest().task();
  const auto& party_datasets = task_config.party_datasets();
  const auto& task_info = task_config.task_info();
  std::string task_inof_str = pb_util::TaskInfoToString(task_info);
  VLOG(0) << task_inof_str << "party_datasets: " << party_datasets.size();
  for (const auto& [party_name,  dataset_map] : party_datasets) {
    for (const auto& [dataset_index, datasetid] : dataset_map.data()) {
      if (datasetid.empty()) {
        LOG(WARNING) << task_inof_str
                     << "dataset for party: " << party_name << " is empty";
        continue;
      }
      this->input_datasets_with_tag_.emplace_back(
          std::make_pair(datasetid, party_name));
    }
  }
  return retcode::SUCCESS;
}

} // namespace fediux::task
