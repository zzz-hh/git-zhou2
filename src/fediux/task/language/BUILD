package(default_visibility = ["//visibility:public"])

cc_library(
    name = "language_parser_factory",
    hdrs = [
        "factory.h",
    ],
    deps = [
        ":proto_parser",
        ":python_parser",
    ],
)

cc_library(
    name = "parser_interface",
    hdrs = [
      "parser.h",
    ],
    srcs = [
      "parser.cc",
    ],
    deps = [
      "//src/fediux/protos:worker_proto",
      "//src/fediux/service:dataset_service",
       "//src/fediux/util:log_util",
      "//src/fediux/util:pb_log_helper",
    ],
)

cc_library(
    name = "proto_parser",
    hdrs = ["proto_parser.h"],
    srcs = ["proto_parser.cc"],
    deps = [
        ":parser_interface",
        "//src/fediux/util:util_lib",
        "//src/fediux/common:common_defination",
        "//src/fediux/util:log_util",
        "//src/fediux/util:pb_log_helper",
    ],
)

cc_library(
    name = "python_parser",
    hdrs = ["py_parser.h"],
    srcs = ["py_parser.cc"],
    copts = [
        "-fvisibility=hidden"
    ],
    deps = [
        ":parser_interface",
        "//src/fediux/task:task_common",
        "@pybind11",
        "@com_github_glog_glog//:glog",
        "//src/fediux/util:log_util",
        "//src/fediux/util:pb_log_helper",
    ],
)
