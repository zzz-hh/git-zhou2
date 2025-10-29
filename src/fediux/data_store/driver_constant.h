#ifndef SRC_FEDIUX_DATA_STORE_DRIVER_CONSTANT_H_
#define SRC_FEDIUX_DATA_STORE_DRIVER_CONSTANT_H_
#include <map>
#include <string>

namespace fediux {
enum class DriverType {
  CSV = 0,
  SQLITE,
  HDFS,
  MYSQL,
  IMAGE,
};

static std::map<DriverType, std::string> kDriveType = {
  {DriverType::CSV, "CSV"},
  {DriverType::SQLITE, "SQLITE"},
  {DriverType::HDFS, "HDFS"},
  {DriverType::MYSQL, "MYSQL"},
  {DriverType::IMAGE, "IMAGE"},
};
}  // namespace fediux
#endif  // SRC_FEDIUX_DATA_STORE_DRIVER_CONSTANT_H_
