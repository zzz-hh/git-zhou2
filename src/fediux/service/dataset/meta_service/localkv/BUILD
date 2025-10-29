package(default_visibility = ["//visibility:public",],)

cc_library(
  name = "kv_interface",
  hdrs = [
    "storage_backend.h",
  ],
  deps = [
    "//src/fediux/service:service_common",
    "//src/fediux/service/dataset:dataset_util",
  ],
)

cc_library(
  name = "leveldb_kv_impl",
  hdrs = [
    "storage_leveldb.h",
  ],
  srcs = [
    "storage_leveldb.cc",
  ],
  deps = [
    ":kv_interface",
    "@com_github_google_leveldb//:leveldb",
  ],
)

cc_library(
  name = "default_kv_impl",
  hdrs = [
    "storage_default.h",
  ],
  srcs = [
    "storage_default.cc",
  ],
  deps = [
    ":kv_interface",
  ],
)

