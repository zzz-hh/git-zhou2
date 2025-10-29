package(default_visibility = ["//visibility:public"])
config_setting(
  name = "enable_sgx",
  values = {"define" : "enable_sgx=true"},
)
cc_library(
  name = "node_impl",
  hdrs = [
    "node_interface.h",
    "node_impl.h"
  ],
  srcs = [
    "main.cc",
    "node_interface.cc",
    "node_impl.cc",
  ],
  deps = [
    ":data_register_service",
    ":nodelet_lib",
    "//src/fediux/common:common_defination",
    "//src/fediux/node/worker:worker_lib_impl",
    "//src/fediux/protos:worker_proto",
    "//src/fediux/common/config:config_lib",
    "//src/fediux/util:util_lib",
    "//src/fediux/util:log_util",
    "//src/fediux/util:pb_log_helper",
    "//src/fediux/util:hash_lib",
    "//src/fediux/task/language:language_parser_factory",
    "//src/fediux/task/semantic:task_semantic_parser",
    "//src/fediux/service/dataset/meta_service:meta_service_factory",
    "@com_github_glog_glog//:glog",
    "@com_github_grpc_grpc//:grpc++",
    "@com_google_absl//absl/flags:flag",
    "@com_google_absl//absl/flags:parse",
    "@arrow",
    "@curl//:curl",
    "@com_github_stduuid//:stduuid_lib",
  ],
)

cc_library(
  name = "data_register_service",
  hdrs = ["ds.h"],
  srcs = ["ds.cc"],
  deps = [
    "//src/fediux/protos:service_proto",
    "//src/fediux/data_store:data_store_lib",
    "//src/fediux/service:dataset_service",
    "//src/fediux/util:thread_local_data",
    "//src/fediux/common/config:server_config",
    "//src/fediux/util:pb_log_helper",
    "//src/fediux/util:file_util",
  ],
)

cc_library(
  name = "nodelet_lib",
  hdrs = ["nodelet.h"],
  srcs = ["nodelet.cc"],
  deps = [
    "//src/fediux/common:common_defination",
    "//src/fediux/service:dataset_service",
  ] + select({
    "enable_sgx": [
      "@tee_engine//sgx/engine:engine_lib",
      "@tee_engine//sgx/ra:ra_service"
    ],
	  "//conditions:default": [],
  }),
)
