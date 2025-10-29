package(default_visibility = ["//visibility:public",],)
cc_library(
    name = "image_driver",
    hdrs = ["image_driver.h"],
    srcs = ["image_driver.cc"],
    deps = [
        "//src/fediux/data_store:base_driver",
        "//src/fediux/util:util_lib",
        "@arrow",
        "@nlohmann_json",
    ],
)