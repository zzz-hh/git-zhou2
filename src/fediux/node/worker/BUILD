package(default_visibility = ["//visibility:public"])
cc_library(
  name = "worker_lib_impl",
  hdrs = ["worker.h"],
  srcs = ["worker.cc"],
  deps = [
    "//src/fediux/node:nodelet_lib",
    "//src/fediux/protos:worker_proto",
    "//src/fediux/common:common_defination",
    "//src/fediux/task:task_factory",
    "//src/fediux/util:log_util",
    "//src/fediux/util:pb_log_helper",
    "@poco//:poco",
    "@com_github_base64_cpp//:base64_lib",
  ],
)