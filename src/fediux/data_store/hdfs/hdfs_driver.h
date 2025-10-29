#ifndef SRC_FEDIUX_DATA_STORE_HDFS_HDFS_DRIVER_H_
#define SRC_FEDIUX_DATA_STORE_HDFS_HDFS_DRIVER_H_

namespace fediux {

  #include "src/fediux/data_store/driver.h"
  class HDFSDriver : public DataDriver
  {
  public:
    explicit HDFSDriver(const std::string &filePath) : filePath(filePath) {}

    // eMatrix<double> load_data();

  private:
    const std::string filePath;
  };

} // namespace fediux

#endif  // SRC_FEDIUX_DATA_STORE_HDFS_HDFS_DRIVER_H_
