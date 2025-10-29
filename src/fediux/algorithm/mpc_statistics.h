#ifndef SRC_FEDIUX_ALGORITHM_MPC_STATISTICS_H_
#define SRC_FEDIUX_ALGORITHM_MPC_STATISTICS_H_
#include <string>
#include <vector>
#include <map>
#include <memory>

#include "src/fediux/algorithm/base.h"
#include "src/fediux/common/type.h"
#include "src/fediux/operator/aby3_operator.h"
#include "src/fediux/executor/statistics.h"

using fediux::ColumnDtype;
using MPCStatisticsType = fediux::MPCStatisticsOperator::MPCStatisticsType;

namespace fediux {
class MPCStatisticsExecutor : public AlgorithmBase {
 public:
  explicit MPCStatisticsExecutor(
      PartyConfig &config, std::shared_ptr<DatasetService> dataset_service);

  ~MPCStatisticsExecutor() {}

  int loadParams(fediux::rpc::Task &task) override;
  int loadDataset() override;
  int execute() override;
  retcode execute(const eMatrix<double>& input_data_info,
                  const std::vector<std::string>& col_names,
                  std::vector<double>* result) override;
  retcode InitEngine() override;
  int saveModel() override;

 private:
  retcode _parseColumnName(const std::string &json_str);
  retcode _parseColumnDtype(const std::string &json_str);

  bool do_nothing_ = false;

  eMatrix<double> result_;
  std::vector<std::string> target_columns_;

  std::shared_ptr<fediux::Dataset> input_value_;


  std::string new_ds_id_;
  std::string output_path_;
  std::string ds_name_;
  std::string dataset_id_;
  bool is_dataset_detail_{false};
  std::string job_id_;
  std::string task_id_;
  std::string statistics_type_;
  std::map<std::string, ColumnDtype> col_type_;

  MPCStatisticsType type_{MPCStatisticsType::UNKNOWN};
  std::unique_ptr<MPCStatisticsOperator> executor_;
};
}  // namespace fediux
#endif  // SRC_FEDIUX_ALGORITHM_MPC_STATISTICS_H_
