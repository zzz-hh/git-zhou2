#ifndef TEST_FEDIUX_ALGORITHM_STATISTICS_UTIL_H_
#define TEST_FEDIUX_ALGORITHM_STATISTICS_UTIL_H_
#include <map>
#include <string>
#include <vector>

#include "src/fediux/common/common.h"
#include "src/fediux/data_store/factory.h"
#include "src/fediux/service/dataset/meta_service/factory.h"
#include "src/fediux/service/dataset/service.h"

namespace fediux::test {
using namespace fediux;
void registerDataSet(const std::vector<DatasetMetaInfo>& meta_infos,
    std::shared_ptr<fediux::service::DatasetService> service);

void BuildTaskConfig(const std::string& role,
    const std::vector<rpc::Node>& node_list,
    std::map<std::string, std::string>& dataset_list,
    std::map<std::string, std::string>& param_info,
    rpc::Task* task_config);

std::string BuildColumnInfo(std::map<std::string,
                                std::map<std::string, std::string>>& datasets_info,
                            std::map<std::string, int>& column_convert_option);
std::string BuildTaskDetail(const std::string& function_type,
                            const std::vector<std::string>& party_datasets,
                            const std::vector<std::string>& checked_columns);
void BuildPartyNodeInfo(std::vector<rpc::Node>* node_list);
}   // namespace fediux::test
#endif  // TEST_FEDIUX_ALGORITHM_STATISTICS_UTIL_H_
