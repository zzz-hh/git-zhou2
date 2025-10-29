#ifndef SRC_FEDIUX_KERNEL_PSI_UTIL_H_
#define SRC_FEDIUX_KERNEL_PSI_UTIL_H_
#include <memory>
#include <string>
#include <vector>

#include "src/fediux/common/common.h"
#include "arrow/api.h"
#include "src/fediux/data_store/factory.h"

namespace fediux::psi {
class PsiCommonUtil {
 public:
  bool IsValidDataType(const arrow::Type::type& type_id);
  bool isNumeric(const arrow::Type::type& type_id);
  bool isNumeric64Type(const arrow::Type::type& type_id);
  bool isNumeric32Type(const arrow::Type::type& type_id);
  bool isString(const arrow::Type::type& type_id);
  bool validationDataColum(const std::vector<int>& data_cols,
                           int table_max_colums);
  retcode LoadDatasetFromTable(std::shared_ptr<arrow::Table> table,
                               const std::vector<int>& col_index,
                               std::vector<std::string>& col_array);
  retcode LoadDatasetFromTable(std::shared_ptr<arrow::Table> table,
                               const std::vector<int>& col_index,
                               std::vector<std::string>* col_data,
                               std::vector<std::string>* col_name);
  retcode LoadDatasetInternal(std::shared_ptr<DataDriver>& driver,
                              const std::vector<int>& data_col,
                              std::vector<std::string>& col_array);
  retcode LoadDatasetInternal(std::shared_ptr<DataDriver>& driver,
                              const std::vector<int>& data_col,
                              std::vector<std::string>* col_data,
                              std::vector<std::string>* col_names);
  retcode LoadDatasetInternal(const std::string& driver_name,
                              const std::string& conn_str,
                              const std::vector<int>& data_cols,
                              std::vector <std::string>& col_array);
  retcode saveDataToCSVFile(const std::vector<std::string>& data,
                            const std::string& file_path,
                            const std::string& col_title);
  retcode SaveDataToCSVFile(const std::vector<std::string>& data,
                            const std::string& file_path,
                            const std::vector<std::string>& col_title);

 protected:
  /**
   * table with multi trunk
   * using multi-thread to process data for multi-trunk
  */
  retcode ExtractDataFromTrunkArray(std::shared_ptr<arrow::Table>& table_data,
                                    std::vector<std::string>* col_data,
                                    std::vector<std::string>* col_name);
  /**
   * table with only trunk
   * using multi-thread to process data for data array
  */
  retcode ExtractDataFromArray(std::shared_ptr<arrow::Table>& table_data,
                               std::vector<std::string>* col_data,
                               std::vector<std::string>* col_name);
};
}  // namespace fediux::psi
#endif  // SRC_FEDIUX_KERNEL_PSI_UTIL_H_
