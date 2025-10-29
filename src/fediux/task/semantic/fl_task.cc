#include "src/fediux/task/semantic/fl_task.h"
#include <glog/logging.h>
#include <iostream>
#include <chrono>
#include <thread>
#include <memory>
#include "src/fediux/util/util.h"
#include "base64.h"
#include <google/protobuf/text_format.h>
#include "pybind11/embed.h"

namespace fediux::task {
using Process = Poco::Process;
using ProcessHandle = Poco::ProcessHandle;
namespace py = pybind11;
FLTask::FLTask(const std::string& node_id,
               const TaskParam* task_param,
               const PushTaskRequest& task_request,
               std::shared_ptr<DatasetService> dataset_service) :
               TaskBase(task_param, dataset_service),
               task_request_(&task_request) {}

int FLTask::execute() {
  std::string pb_task_request_;
  bool succ_flag = task_request_->SerializeToString(&pb_task_request_);
  if (!succ_flag) {
    LOG(ERROR) << "ill formatted task request";
    return -1;
  }

  py::scoped_interpreter python;
  VLOG(1) << "<<<<<<<<< Import PrmimiHub Python Executor <<<<<<<<<";
  py::object ph_exec_m_ =
      py::module::import("fediux.executor").attr("Executor");
  py::object ph_context_m_ = py::module::import("fediux.context");
  py::object set_message;
  set_message = ph_context_m_.attr("set_message");
  set_message(py::bytes(pb_task_request_));
  set_message.release();
  auto& server_config = fediux::ServerConfig::getInstance();
  auto& host_cfg = server_config.getServiceConfig();
  if (host_cfg.use_tls()) {
    auto& cert_config = server_config.getCertificateConfig();
    auto root_ca_path = cert_config.rootCAPath();
    auto key_path = cert_config.keyPath();
    auto cert_path = cert_config.certPath();
    VLOG(1) << "Set cert config info, root_ca_path: " << root_ca_path << " "
        << "key_path: " << key_path << " "
        << "cert_path: " << cert_path;
    py::object set_cert_config;
    set_cert_config = ph_context_m_.attr("set_cert_config");
    set_cert_config(root_ca_path, key_path, cert_path);
    set_cert_config.release();
  }
  VLOG(1) << "<<<<<<<<< Start executing Python code <<<<<<<<<" << std::endl;
  // Execute python code.
  ph_exec_m_.attr("execute_py")();
  VLOG(1) << "<<<<<<<<< Execute Python Code End <<<<<<<<<" << std::endl;
  py::object mpc_util = py::module::import("fediux.MPC.util");
  py::object stop_aux_task = mpc_util.attr("stop_auxiliary_party");
  stop_aux_task();
  stop_aux_task.release();
  VLOG(1) << "<<<<<<<<< Clean Task Env End <<<<<<<<<" << std::endl;
  return 0;
}

}  // namespace fediux::task
