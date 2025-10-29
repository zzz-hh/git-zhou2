#ifndef SRC_FEDIUX_TASK_SEMANTIC_TEE_TASK_H_
#define SRC_FEDIUX_TASK_SEMANTIC_TEE_TASK_H_

// #include <pybind11/embed.h>
#include "src/fediux/task/semantic/task.h"

// namespace py = pybind11;
namespace fediux::task {
// /**
//  * @brief TEE Executor role task
//  *  1. compile AI server SGX enclave application
//  *  2. run SGX enclave application
//  *  3. Notice all DataProvider  start to provide data
//  */
// class TEEExecutorTask : public TaskBase {
//     public:
//         TEEExecutorTask(const TaskParam *task_param,
//                         std::shared_ptr<DatasetService> dataset_service);
//         ~TEEExecutorTask() {}

//         int compile();
//         int execute();
// };

/**
 * @brief TEE DataProvider role task
 *
 */
class TEEDataProviderTask: public TaskBase {
    public:
        TEEDataProviderTask(
            const std::string& node_id,
            const TaskParam *task_param,
            std::shared_ptr<DatasetService> dataset_service);
        ~TEEDataProviderTask();
        int execute();
    private:
        py::object flight_client_;
        std::string dataset_, server_addr_;
};

} // namespace fediux::task

#endif  // SRC_FEDIUX_TASK_SEMANTIC_TEE_TASK_H_
