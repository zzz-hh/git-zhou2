package(default_visibility = ["//visibility:public",],)
cc_library(
    name = "mysql_driver",
    hdrs = ["mysql_driver.h"],
    srcs = ["mysql_driver.cc"],
    linkopts = [
        "-L/usr/lib64/mysql",
        "-lmysqlclient",
    ],
    deps = [
        "//src/fediux/data_store:base_driver",
        "//src/fediux/util:arrow_wrapper_util",
        "//src/fediux/util:util_lib",
        "//src/fediux/util:thread_local_data",
        "@arrow",
        "@nlohmann_json",
    ],
)
