package(default_visibility = ["//visibility:public",],)
cc_library(
    name = "sqlite_driver",
    hdrs = ["sqlite_driver.h"],
    srcs = ["sqlite_driver.cc"],
    deps = [
        "//src/fediux/data_store:base_driver",
        "//src/fediux/util:arrow_wrapper_util",
        "//src/fediux/util:util_lib",
        "//src/fediux/util:thread_local_data",
        "@arrow",
        "@com_github_sqlite_wrapper//:sqlite_wrapper",
        "@nlohmann_json",
    ],
)