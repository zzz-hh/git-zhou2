#ifndef SRC_FEDIUX_TASK_SEMANTIC_PSI_TASK_H_
#define SRC_FEDIUX_TASK_SEMANTIC_PSI_TASK_H_

#include <vector>
#include <map>
#include <memory>
#include <string>
#include <set>

#include "src/fediux/protos/common.pb.h"
#include "src/fediux/protos/worker.pb.h"
#include "src/fediux/task/semantic/task.h"
#include "src/fediux/common/common.h"
#include "src/fediux/kernel/psi/operator/base_psi.h"
#include "src/fediux/kernel/psi/util.h"

namespace rpc = fediux::rpc;

namespace fediux::task {
using BasePsiOperator = fediux::psi::BasePsiOperator;

class PsiTask : public TaskBase, public fediux::psi::PsiCommonUtil {
 public:
  PsiTask(const TaskParam *task_param);
  PsiTask(const TaskParam *task_param,
          std::shared_ptr<DatasetService> dataset_service);
  PsiTask(const TaskParam *task_param,
          std::shared_ptr<DatasetService> dataset_service,
          void* ra_server, void* tee_engine);
  ~PsiTask() = default;
  int execute() override;
  retcode ExecuteTask(const std::vector<std::string>& input,
                      std::vector<std::string>* result);
  fediux::psi::Options& PsiOptions() {return options_;}
 protected:
  retcode LoadParams(const rpc::Task& task);
  retcode LoadDataset();
  retcode SaveResult();
  retcode InitOperator();
  retcode ExecuteOperator();
  retcode BuildOptions(const rpc::Task& task,
                       fediux::psi::Options* option);
  bool NeedSaveResult();
  bool IsClient();
  bool IsServer();
  bool IsTeeCompute();

 private:
  std::vector<int> data_index_;
  std::vector<std::string> data_colums_name_;
  int psi_type_{rpc::PsiTag::KKRT};
  std::string dataset_path_;
  std::string dataset_id_;
  std::string result_file_path_;
  std::vector<std::string> elements_;
  std::vector<std::string> result_;
  bool broadcast_result_{false};
  std::unique_ptr<BasePsiOperator> psi_operator_{nullptr};
  fediux::psi::Options options_;
  bool unique_values_{true};
  bool load_dataset_{true};
  // for TEE
  void* ra_server_{nullptr};
  void* tee_executor_{nullptr};
};
}  // namespace fediux::task
#endif  // SRC_FEDIUX_TASK_SEMANTIC_PSI_TASK_H_
