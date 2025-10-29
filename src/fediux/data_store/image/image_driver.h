#ifndef SRC_FEDIUX_DATA_STORE_IMAGE_IMAGE_DRIVER_H_
#define SRC_FEDIUX_DATA_STORE_IMAGE_IMAGE_DRIVER_H_

#include <memory>
#include <vector>
#include <string>

#include "src/fediux/data_store/dataset.h"
#include "src/fediux/data_store/driver.h"

namespace fediux {
class ImageDriver;
struct ImageAccessInfo : public DataSetAccessInfo {
  ImageAccessInfo() = default;
  ImageAccessInfo(const std::string& image_dir, const std::string& annotations_file)
      : image_dir_(image_dir), annotations_file_(annotations_file) {}
  std::string toString() override;
  retcode ParseFromJsonImpl(const nlohmann::json& access_info) override;
  retcode ParseFromYamlConfigImpl(const YAML::Node& meta_info) override;
  retcode ParseFromMetaInfoImpl(const DatasetMetaInfo& meta_info) override;

 public:
  std::string image_dir_;
  std::string annotations_file_;
};

class ImageCursor : public Cursor {
 public:
  explicit ImageCursor(std::shared_ptr<ImageDriver> driver);
  ~ImageCursor();
  std::shared_ptr<Dataset> readMeta() override;
  std::shared_ptr<Dataset> read() override;
  std::shared_ptr<Dataset> read(const std::shared_ptr<arrow::Schema>& data_schema) override;
  std::shared_ptr<Dataset> read(int64_t offset, int64_t limit) override;
  int write(std::shared_ptr<Dataset> dataset) override;
  void close() override;

 private:
  unsigned long long offset_{0};    // NOLINT
  std::shared_ptr<ImageDriver> driver_;
};

class ImageDriver : public DataDriver, public std::enable_shared_from_this<ImageDriver> {
 public:
  explicit ImageDriver(const std::string &nodelet_addr);
  ImageDriver(const std::string &nodelet_addr, std::unique_ptr<DataSetAccessInfo> access_info);
  ~ImageDriver() {}
  std::unique_ptr<Cursor> read() override;
  std::unique_ptr<Cursor> read(const std::string& access_info) override;
  std::unique_ptr<Cursor> initCursor(const std::string& access_ifno) override;
  std::unique_ptr<Cursor> initCursor();
  std::unique_ptr<Cursor> GetCursor() override;
  std::unique_ptr<Cursor> GetCursor(const std::vector<int>& col_index) override;
  std::string getDataURL() const override;

 protected:
  void setDriverType();
};

}  // namespace fediux

#endif  // SRC_FEDIUX_DATA_STORE_IMAGE_IMAGE_DRIVER_H_
