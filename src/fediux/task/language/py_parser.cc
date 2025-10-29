#include "src/fediux/task/language/py_parser.h"
#include <glog/logging.h>
#include <iostream>
#include "src/fediux/util/log.h"
#include "src/fediux/util/proto_log_helper.h"

namespace pb_util = fediux::proto::util;
namespace fediux::task {
/**
 * @brief Parse datasets from python code.
 * @return Dataset names.
 */
retcode PyParser::parseDatasets() {
  auto& push_task = getPushTaskRequest();
  const auto& task_config = push_task.task();
  const auto& party_datasets = task_config.party_datasets();
  const auto& task_info = task_config.task_info();
  std::string task_inof_str = pb_util::TaskInfoToString(task_info);
  VLOG(0) << task_inof_str << "party_datasets: " << party_datasets.size();
  std::set<std::string> dup_filter;
  for (const auto& [party_name,  dataset_map] : party_datasets) {
    for (const auto& [dataset_index, dataset_id] : dataset_map.data()) {
      if (dataset_id.empty()) {
        LOG(WARNING) << task_inof_str
                     << "dataset id for party: " << party_name << " is empty";
        continue;
      }
      std::string uniq_id = party_name + dataset_id;
      if (dup_filter.find(uniq_id) != dup_filter.end()) {
        continue;
      } else {
        dup_filter.insert(uniq_id);
      }
      VLOG(0) << task_inof_str
              << "party_name: " << party_name << " dataset_id: " << dataset_id;
      auto dataset_with_tag = std::make_pair(dataset_id, party_name);
      this->input_datasets_with_tag_.push_back(std::move(dataset_with_tag));
    }
  }
  return retcode::SUCCESS;
}

PyParser::~PyParser() {}

/**
 * @brief Get
 *            1. What datasets to use.
 *            2. What protocol to use.
 *            3. What roles join nodes should have.
 *            4. What python code and params to execute in each role.
 *         from python code.
 */
retcode PyParser::parseTask() {
  return retcode::SUCCESS;
}

retcode PyParser::parseNodes() {
  // TODO
  return retcode::SUCCESS;
}

} // namespace fediux::task
