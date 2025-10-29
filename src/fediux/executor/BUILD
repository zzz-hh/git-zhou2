package(default_visibility = ["//visibility:public"])

cc_library(
  name = "mpc_express_executor",
  hdrs = [
    "express.h",
    "statistics.h",
  ],
  srcs = [
    "express.cc",
    "statistics.cc",
  ],
  deps = [
    "//src/fediux/common:type",
    "//src/fediux/operator:aby3_operator",
    "//src/fediux/service:dataset_service",
    "@com_github_glog_glog//:glog"
  ],
)
