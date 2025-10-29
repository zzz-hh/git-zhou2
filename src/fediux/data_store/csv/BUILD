package(default_visibility = ["//visibility:public",],)
cc_library(
    name = "csv_driver",
    hdrs = ["csv_driver.h"],
    srcs = ["csv_driver.cc"],
    deps = [
        "//src/fediux/data_store:base_driver",
        "//src/fediux/util:util_lib",
        "//src/fediux/util:thread_local_data",
        "@arrow",
        "@nlohmann_json",
    ],
)