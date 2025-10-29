#ifndef SRC_FEDIUX_DATA_STORE_FACTORY_H_
#define SRC_FEDIUX_DATA_STORE_FACTORY_H_

#include <memory>
#include <boost/algorithm/string.hpp>
#include <nlohmann/json.hpp>
#include "src/fediux/data_store/driver.h"
#include "src/fediux/data_store/csv/csv_driver.h"
#include "src/fediux/data_store/sqlite/sqlite_driver.h"
#include "src/fediux/data_store/image/image_driver.h"
#include "src/fediux/util/util.h"
#ifdef ENABLE_MYSQL_DRIVER
#include "src/fediux/data_store/mysql/mysql_driver.h"
#endif
#include "src/fediux/common/value_check_util.h"

namespace fediux {
class DataDirverFactory {
 public:
  using DataSetAccessInfoPtr = std::unique_ptr<DataSetAccessInfo>;
  using DataDriverPtr = std::shared_ptr<DataDriver>;
  static DataDriverPtr getDriver(const std::string &dirverName,
      const std::string& nodeletAddr,
      DataSetAccessInfoPtr access_info = nullptr) {
    DataDriverPtr driver_ptr{nullptr};
    std::string driver_name = strToUpper(dirverName);
    if (driver_name == kDriveType[DriverType::CSV]) {
      driver_ptr = std::make_shared<CSVDriver>(nodeletAddr,
                                               std::move(access_info));
    } else if (driver_name == kDriveType[DriverType::SQLITE]) {
      driver_ptr = std::make_shared<SQLiteDriver>(nodeletAddr,
                                                  std::move(access_info));
    } else if (driver_name == kDriveType[DriverType::MYSQL]) {
#ifdef ENABLE_MYSQL_DRIVER
      driver_ptr = std::make_shared<MySQLDriver>(nodeletAddr,
                                                 std::move(access_info));
#else
      std::string err_msg = "MySQL is not enabled";
      RaiseException(err_msg);
#endif
    } else if (driver_name == kDriveType[DriverType::IMAGE]) {
      driver_ptr = std::make_shared<ImageDriver>(nodeletAddr,
                                                 std::move(access_info));
    } else {
      std::string err_msg =
          "[DataDriverFactory] Invalid driver name [" + dirverName + "]";
      RaiseException(err_msg);
    }
    return driver_ptr;
  }

  // internal
  static DataSetAccessInfoPtr createAccessInfoInternal(
      const std::string& driver_type) {
    std::string drive_type_ = strToUpper(driver_type);
    DataSetAccessInfoPtr access_info_ptr{nullptr};
    if (drive_type_ == kDriveType[DriverType::CSV]) {
      access_info_ptr = std::make_unique<CSVAccessInfo>();
    } else if (drive_type_ == kDriveType[DriverType::SQLITE]) {
      access_info_ptr = std::make_unique<SQLiteAccessInfo>();
    } else if (drive_type_ == kDriveType[DriverType::MYSQL]) {
#ifdef ENABLE_MYSQL_DRIVER
      access_info_ptr = std::make_unique<MySQLAccessInfo>();
#else
      std::string err_msg = "MySQL is not enabled";
      RaiseException(err_msg);
#endif
    } else if (drive_type_ == kDriveType[DriverType::IMAGE]) {
      access_info_ptr = std::make_unique<ImageAccessInfo>();
    } else {
      std::string err_msg = "unsupported driver type: " + drive_type_;
      RaiseException(err_msg);
    }
    return access_info_ptr;
  }

  static DataSetAccessInfoPtr createAccessInfo(
      const std::string& driver_type,
      const std::string& meta_info) {
    auto access_info_ptr = createAccessInfoInternal(driver_type);
    if (access_info_ptr == nullptr) {
      return nullptr;
    }
    auto ret = access_info_ptr->fromJsonString(meta_info);
    if (ret == retcode::FAIL) {
      std::string err_msg = "create dataset access info failed";
      RaiseException(err_msg);
    }
    return access_info_ptr;
  }

  static DataSetAccessInfoPtr createAccessInfo(
      const std::string& driver_type, const YAML::Node& meta_info) {
    auto access_info_ptr = createAccessInfoInternal(driver_type);
    if (access_info_ptr == nullptr) {
      return nullptr;
    }
    // init
    auto ret = access_info_ptr->fromYamlConfig(meta_info);
    if (ret == retcode::FAIL) {
      std::string err_msg = "create dataset access info failed";
      RaiseException(err_msg);
    }
    return access_info_ptr;
  }

  static DataSetAccessInfoPtr createAccessInfo(
      const std::string& driver_type, const DatasetMetaInfo& meta_info) {
    auto access_info_ptr = createAccessInfoInternal(driver_type);
    if (access_info_ptr == nullptr) {
      return nullptr;
    }
    // init
    auto ret = access_info_ptr->FromMetaInfo(meta_info);
    if (ret == retcode::FAIL) {
      std::string err_msg = "create dataset access info failed";
      RaiseException(err_msg);
    }
    return access_info_ptr;
  }
};

} // namespace fediux

#endif // SRC_FEDIUX_DATA_STORE_FACTORY_H_
