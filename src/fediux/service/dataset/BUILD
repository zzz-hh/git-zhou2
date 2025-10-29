package(default_visibility = ["//visibility:public",],)

cc_library(
  name = "dataset_service_impl",
  hdrs = [
    "service.h",
  ],
  srcs = [
    "service.cc",
  ],
  deps = [
    ":dataset_util",
    ":model_lib",
    "//src/fediux/service/dataset/meta_service:meta_service_interface",
    "//src/fediux/service/dataset/meta_service:meta_service_grpc_impl",
    "//src/fediux/data_store:data_store_lib",
    "//src/fediux/util:redis_helper",
    "//src/fediux/common/config:server_config",
    "//src/fediux/util:arrow_wrapper_util",
    "@arrow",
    "@nlohmann_json",
  ],
)

cc_library(
  name = "model_lib",
  hdrs = ["model.h"],
  srcs = ["model.cc"],
  deps = [
    "//src/fediux/util:arrow_wrapper_util",
    "//src/fediux/data_store:base_driver",
  ],
)

cc_library(
  name = "dataset_util",
  hdrs = [
    "util.hpp"
  ],
  deps = [
    "//src/fediux/common:common_defination",
    "//src/fediux/util:util_lib",
  ],
)