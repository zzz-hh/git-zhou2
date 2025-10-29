#include "src/fediux/task/semantic/tee_task.h"

#include <glog/logging.h>
#include <pybind11/embed.h>

namespace fediux::task {
TEEDataProviderTask::TEEDataProviderTask(
    const std::string& node_id,
    const TaskParam *task_param,
    std::shared_ptr<DatasetService> dataset_service)
    : TaskBase(task_param, dataset_service) {
    auto param_map = task_param->params().param_map();
    try {
        this->server_addr_ = param_map["server"].value_string();
        this->dataset_ = param_map["dataset"].value_string();
    } catch (std::exception& e) {
        LOG(ERROR) << "Failed to load params: " << e.what();
        return;
    }

}

TEEDataProviderTask::~TEEDataProviderTask() {
    flight_client_.release();
}

int TEEDataProviderTask::execute() {
    // TODO start apache arrow flight python client to upload dataset.
    py::gil_scoped_acquire acquire;
    flight_client_ = py::module::import("fediux.TEE").attr("flight_client");
    flight_client_.attr("upload_dataset")(this->dataset_, this->server_addr_);

    return 0;
}

} // namespace fediux::task
