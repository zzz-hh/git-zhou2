package(default_visibility = ["//visibility:public"])
config_setting(
  name = "enable_sgx",
  values = {"define" : "enable_sgx=true"},
)
cc_library(
  name = "factory",
  hdrs = ["factory.h"],
  deps = [
    ":common_def",
    ":base_psi_operator",
    ":kkrt_psi_operator",
    ":ecdh_psi_operator",
  ] + select({
    "enable_sgx": [
      ":tee_psi_operator",
    ],
	  "//conditions:default": [],
  }),
)

cc_library(
  name = "common_def",
  hdrs = ["common.h"],
)

cc_library(
  name = "base_psi_operator",
  hdrs = ["base_psi.h"],
  srcs = ["base_psi.cc"],
  deps = [
    ":common_def",
    "//src/fediux/util:endian_util",
    "//src/fediux/util:util_lib",
    "//src/fediux/common:common_defination",
    "//src/fediux/util/network:communication_lib",
  ],
)

cc_library(
  name = "kkrt_psi_operator",
  hdrs = ["kkrt_psi.h"],
  srcs = ["kkrt_psi.cc"],
  deps = [
    ":base_psi_operator",
    "//src/fediux/util:endian_util",
    "//src/fediux/util:util_lib",
    "//src/fediux/protos:worker_proto",
    "@osu_libpsi//:libpsi",
    "//src/fediux/util/network:message_exchange_interface",
  ]
)

OPENMINED_PSI = "@org_openmined_psi//private_set_intersection/cpp"
cc_library(
  name = "ecdh_psi_operator",
  hdrs = ["ecdh_psi.h"],
  srcs = ["ecdh_psi.cc"],
  deps = [
    ":base_psi_operator",
    "//src/fediux/util:endian_util",
    "//src/fediux/util:util_lib",
    "%s:psi_client" % OPENMINED_PSI,
    "%s:psi_server" % OPENMINED_PSI,
    "@fmt//:fmt",
  ]
)
cc_library(
  name = "tee_psi_operator",
  hdrs = ["tee_psi.h"],
  srcs = ["tee_psi.cc"],
  deps = [
    ":base_psi_operator",
    "//src/fediux/util:endian_util",
    "//src/fediux/util:util_lib",
    "//src/fediux/util:hash_lib",
    "//src/fediux/util:file_util",
    "@tee_engine//sgx/engine:engine_lib",
    "@tee_engine//sgx/ra:ra_service",
  ]
)