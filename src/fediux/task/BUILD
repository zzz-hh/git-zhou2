package(default_visibility = ["//visibility:public"])
cc_library(
    name = "task_common",
    hdrs = ["common.h"],
    deps = [
        "//src/fediux/service:dataset_service",
        "//src/fediux/protos:common_proto",
    ],
)
cc_library(
    name = "task_factory",
    deps = [
        "//src/fediux/task/semantic:task_factory"
    ],
)

cc_library(
    name = "task_scheduler",
    deps = [
        "//src/fediux/task/semantic/scheduler:scheduler_lib",
    ],
)

