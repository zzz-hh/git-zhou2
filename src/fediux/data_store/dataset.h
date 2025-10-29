#ifndef SRC_FEDIUX_DATA_STORE_DATASET_H_
#define  SRC_FEDIUX_DATA_STORE_DATASET_H_

#include <memory>
#include <variant>
#include <vector>

#include <arrow/table.h>
#include <arrow/tensor.h>
#include <arrow/array.h>

#include "src/fediux/data_store/driver.h"


namespace fediux {

class DataDriver;

enum DatasetLocation {
    LOCAL,
    REMOTE,
};

using DatasetContainerType =
    std::variant<std::shared_ptr<arrow::Table>,
                std::shared_ptr<arrow::Tensor>,
                std::shared_ptr<arrow::Array>>;

class Dataset {
 public:
    // Local dataset
    Dataset(std::shared_ptr<arrow::Table> table,
        std::shared_ptr<fediux::DataDriver> driver)
        : data(table), driver_(std::move(driver)) {
      location_ = DatasetLocation::LOCAL;
    }

    Dataset(const std::vector<std::shared_ptr<arrow::RecordBatch>> &batches,
            std::shared_ptr<fediux::DataDriver> driver)
        : driver_(std::move(driver)) {
      location_ = DatasetLocation::LOCAL;
      // Convert RecordBatch to Table
      auto result = arrow::Table::FromRecordBatches(batches);

      if (result.ok()) {
        data = result.ValueOrDie();
      } else {
        throw std::runtime_error("Error converting RecordBatch to Table");
      }
    }

    // TODO: Only support table now. May support Tensor later.
    DatasetContainerType data;

    // TODO (chenhongbo): Local dataset or remote dataset. Local dataset depends on data driver.
    // Remote dataset needs data url and schema.
    std::shared_ptr<fediux::DataDriver>  getDataDriver() const {
        return driver_;
    }

    // //TODO  Dump dataset using DataDriver.
    // bool write() {
    //     return driver_->getCursor()->write(data);
    // }

  private:
    DatasetLocation location_;
    std::shared_ptr<DataDriver> driver_; // Only valid when location is LOCAL.
};

} // namespace fediux


#endif  // SRC_FEDIUX_DATA_STORE_DATASET_H_
