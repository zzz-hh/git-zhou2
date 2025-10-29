package(default_visibility = ["//visibility:public"])

config_setting(
    name = "aarch64",
    values = {"define": "cpu_arch=aarch64"},
)

config_setting(
    name = "x86_64",
    values = {"define": "cpu_arch=x86_64"},
)
config_setting(
    name = "darwin_x86_64",
    values = {"define": "cpu_arch=darwin_x86_64"},
)

config_setting(
   name = "microsoft-apsi",
   values = {"define": "microsoft-apsi=true"},
)

#factory for create task
cc_library(
    name = "task_factory",
    hdrs = ["factory.h"],
    deps = [
        ":fl_task",
        ":mpc_task",
        ":pir_task",
        ":psi_task",
    ],
)

cc_library(
    name = "task_context",
    hdrs = ["task_context.h"],
    srcs = ["task_context.cc"],
    deps = [
        "//src/fediux/util/network:communication_lib",
        "//src/fediux/common/config:server_config",
        "//src/fediux/util:threadsafe_queue",
    ],
)

cc_library(
    name = "task_interface",
    hdrs = ["task.h"],
    srcs = ["task.cc"],
    deps = [
        ":task_context",
        "//src/fediux/protos:worker_proto",
        "//src/fediux/service:dataset_service",
    ],
)

#fl task
cc_library(
  name = "fl_task",
  hdrs = ["fl_task.h"],
  srcs = ["fl_task.cc"],
  copts = [
    "-fvisibility=hidden"
  ],
  deps = [
    ":task_interface",
    "//src/fediux/util:util_lib",
    "@com_github_base64_cpp//:base64_lib",
    "@poco//:poco",
    "@pybind11",
  ],
)

#mpc task
cc_library(
    name = "mpc_task",
    hdrs = ["mpc_task.h"],
    srcs = ["mpc_task.cc"],

    copts = select({
        ":x86_64": ["-maes"],
        ":aarch64": [],
        "//conditions:default": [],
    }),

    deps = [
        ":task_interface",
        "//src/fediux/algorithm:algorithm_lib",

    ] + select({
        ":x86_64": [
            #"//src/fediux/algorithm:cryptflow2_algorithm_lib",
        ],
        ":aarch64": [],
        "//conditions:default": [],
    }),

)

# psi task
cc_library(
  name = "psi_task",
  hdrs = ["psi_task.h"],
  srcs = ["psi_task.cc"],
  deps = [
    ":task_interface",
    "//src/fediux/kernel/psi:psi_util",
    "//src/fediux/kernel/psi/operator:factory",
  ],
)

cc_library(
    name = "tee_task",
    hdrs = ["tee_task.h"],
    srcs = ["tee_task.cc"],
    deps = [
        ":task_interface",
        "@pybind11",
    ],
)

# pir task
cc_library(
  name = "pir_task",
  hdrs = ["pir_task.h"],
  srcs = ["pir_task.cc"],
  deps = [
    ":task_interface",
    "//src/fediux/kernel/pir:common_def",
    "//src/fediux/kernel/pir/operator:factory",
  ],
)

# task semantic parser
cc_library(
    name = "task_semantic_parser",
    hdrs = ["parser.h"],
    srcs = ["parser.cc"],
    deps = [
        ":task_factory",
        "//src/fediux/task/language:language_parser_factory",
        "//src/fediux/task/semantic/scheduler:scheduler_factory",
        "//src/fediux/task:task_common",
        "//src/fediux/service:dataset_service",
    ]
)
