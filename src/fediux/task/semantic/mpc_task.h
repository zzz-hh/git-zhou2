#ifndef SRC_FEDIUX_TASK_SEMANTIC_MPC_TASK_H_
#define SRC_FEDIUX_TASK_SEMANTIC_MPC_TASK_H_

#include <map>
#include <memory>
#include <string>

#include "src/fediux/algorithm/base.h"
#include "src/fediux/task/semantic/task.h"

using fediux::AlgorithmBase;

namespace fediux::task {

class MPCTask : public TaskBase {
 public:
  MPCTask(const std::string &node_id,
          const std::string &function_name,
          const TaskParam *task_param,
          std::shared_ptr<DatasetService> dataset_service);
  MPCTask(const std::string& funcaton_name, const TaskParam *task_param);
  ~MPCTask() = default;
  int execute() override;
  retcode ExecuteTask(const std::vector<double>& input_data,
                      const std::vector<int64_t>& col_rows,
                      std::vector<double>* result);
  retcode ExecuteImpl();

 protected:
  std::shared_ptr<Dataset> MakeDataset(const std::vector<double>& input_data,
                                       int64_t colum_num);
  std::shared_ptr<Dataset> MakeDataset();
  retcode MakeAuxiliaryComputeData(const std::vector<int64_t>& shape,
                                   std::vector<double>* input,
                                   std::vector<int64_t>* col_rows);
  retcode RecvShapeFromLauncher(std::vector<int64_t>* shape);

 private:
    std::shared_ptr<AlgorithmBase> algorithm_{nullptr};
};

} // namespace fediux::task

#endif // SRC_FEDIUX_TASK_SEMANTIC_MPC_TASK_H_
