package(default_visibility = ["//visibility:public"])

cc_library(
  name = "task_engine_impl",
  srcs = ["main.cc"],
  copts = [
    "-fvisibility=hidden"
  ],
  deps = [
    ":task_engine",
    "@com_google_absl//absl/base",
    "@com_google_absl//absl/flags:flag",
    "@com_google_absl//absl/flags:parse",
    "@com_google_absl//absl/memory",
    "@com_github_glog_glog//:glog",
    "@pybind11",
  ],
)

cc_library(
  name = "task_engine",
  hdrs = ["task_executor.h"],
  srcs = ["task_executor.cc"],
  deps = [
    "//src/fediux/common:common_defination",
    "//src/fediux/protos:worker_proto",
    "//src/fediux/util/network:communication_lib",
    "//src/fediux/util:util_lib",
    "//src/fediux/common/config:server_config",
    "//src/fediux/task/semantic:task_factory",
    "//src/fediux/service/dataset/meta_service:meta_service_factory",
    "//src/fediux/service:dataset_service",
    "//src/fediux/util:log_util",
    "//src/fediux/util:pb_log_helper",
    "@com_github_base64_cpp//:base64_lib",
  ],
)

