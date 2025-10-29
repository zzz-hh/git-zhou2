package(default_visibility = ["//visibility:public"])
cc_library(
  name = "factory",
  hdrs = ["factory.h"],
  deps = [
    "//src/fediux/kernel/pir:common_def",
    ":base_pir_operator",
    ":keyword_pir_operator",
  ]
)

cc_library(
  name = "base_pir_operator",
  hdrs = ["base_pir.h"],
  srcs = ["base_pir.cc"],
  deps = [
    "//src/fediux/kernel/pir:common_def",
    "//src/fediux/util:endian_util",
    "//src/fediux/util:util_lib",
    "//src/fediux/common:common_defination",
    "//src/fediux/util/network:communication_lib",
  ],
)

cc_library(
  name = "keyword_pir_operator",
  deps = [
    "//src/fediux/kernel/pir/operator/keyword_pir_impl:keyword_pir_server_impl",
    "//src/fediux/kernel/pir/operator/keyword_pir_impl:keyword_pir_client_impl",
  ]
)
