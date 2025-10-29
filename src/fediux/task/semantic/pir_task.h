#ifndef SRC_FEDIUX_TASK_SEMANTIC_PIR_TASK_H_
#define SRC_FEDIUX_TASK_SEMANTIC_PIR_TASK_H_
#include <string>
#include "src/fediux/task/semantic/task.h"
#include "src/fediux/common/common.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/kernel/pir/common.h"
#include "src/fediux/kernel/pir/operator/base_pir.h"
#include "src/fediux/util/util.h"
#include "src/fediux/util/file_util.h"
namespace fediux::task {
using BasePirOperator = fediux::pir::BasePirOperator;

class PirTask : public TaskBase {
 public:
  PirTask(const TaskParam *task_param,
          std::shared_ptr<DatasetService> dataset_service);
  ~PirTask() = default;
  int execute() override;

 protected:
  retcode LoadParams(const rpc::Task& task);
  retcode GetServerDataSetSchema(const rpc::Task& task);
  retcode LoadDataset();
  retcode ClientLoadDataset();
  retcode ServerLoadDataset();
  std::shared_ptr<Dataset> LoadDataSetInternal(const std::string& dataset_id);
  bool DbCacheAvailable(const std::string& db_file_cache) {
    return FileExists(db_file_cache);
  }
  std::vector<std::string> GetSelectedContent(
      std::shared_ptr<arrow::Table>& data_tbl,
      const std::vector<int>& selected_col);
  retcode SaveResult();
  retcode InitOperator();
  retcode ExecuteOperator();
  retcode BuildOptions(const rpc::Task& task,
                       fediux::pir::Options* option);
  bool NeedSaveResult();
  retcode ParseQueryConfig(const rpc::Task& task_config);
  retcode ParseDataset(const rpc::Task& task_config);
  retcode ParsePirType(const rpc::Task& task_config);
  retcode ParseResultPathConfig(const rpc::Task& task_config);
  retcode ParsePirRole(const rpc::Task& task_config, Role* role);

 private:
  int pir_type_{rpc::PirType::KEY_PIR};
  std::string dataset_path_;
  std::string dataset_id_;
  std::string result_file_path_;
  fediux::pir::PirDataType elements_;
  fediux::pir::PirDataType result_;
  fediux::pir::Options options_;
  std::string db_cache_dir_{"data/cache"};
  std::unique_ptr<BasePirOperator> operator_{nullptr};
  std::vector<std::string> server_dataset_schema_;
  std::vector<int> server_key_columns_;
  std::vector<int> server_label_columns_;
  std::vector<int> client_key_columns_;

  // std::string dataset_path_;
  // std::string dataset_id_;

  // std::string db_file_cache_;
  // fediux::Node client_node_;
  // std::string key{"key_pir"};
  // std::string psi_params_str_;
  // std::unique_ptr<apsi::oprf::OPRFKey> oprf_key_{nullptr};
  // bool generate_db_offline_{false};
};
}  // namespace fediux::task
#endif  // SRC_FEDIUX_TASK_SEMANTIC_PIR_TASK_H_
