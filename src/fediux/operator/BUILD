package(default_visibility = ["//visibility:public"])
cc_library(
  name = "aby3_operator",
  hdrs = [
    "aby3_operator.h"
  ],
  srcs = [
    "aby3_operator.cc"
  ],
  deps = [
    "//src/fediux/common:common_lib",
    "//src/fediux/util:eigen_util",
    "//src/fediux/util/network:mpc_channel",
    "//src/fediux/util/network:mpc_commpkg",
    "@com_github_ladnir_aby3//aby3:aby3_lib",
    "@ladnir_cryptoTools//:libcryptoTools",
    "@com_github_glog_glog//:glog",
    "@eigen//:eigen",
  ],
)