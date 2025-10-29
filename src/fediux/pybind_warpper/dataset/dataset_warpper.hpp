#include <iostream>
#include <memory>

#include <pybind11/pybind11.h>
#include <arrow/array.h>
#include <arrow/python/pyarrow.h>
#include <arrow/table.h>

#include "src/fediux/data_store/dataset.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/service/dataset/model.h"
#include "src/fediux/data_store/factory.h"


using namespace arrow;

using fediux::Dataset;
using fediux::DataDriver;
using fediux::DataDirverFactory;
using fediux::service::DatasetService;
using fediux::service::DatasetMeta;
using fediux::service::DatasetVisbility;


namespace pybind11
{
    namespace detail
    {
        template <typename TableType>
        struct gen_type_caster
        {
        public:
            PYBIND11_TYPE_CASTER(std::shared_ptr<TableType>, _("pyarrow::Table"));
            // Python -> C++
            bool load(handle src, bool)
            {
                PyObject *source = src.ptr();
                if (!arrow::py::is_table(source))
                    return false;
                arrow::Result<std::shared_ptr<arrow::Table>> result = arrow::py::unwrap_table(source);
                if (!result.ok())
                    return false;
                value = std::static_pointer_cast<TableType>(result.ValueOrDie());
                return true;
            }
            // C++ -> Python
            static handle cast(std::shared_ptr<TableType> src, return_value_policy /* policy */, handle /* parent */)
            {
                return arrow::py::wrap_table(src);
            }
        };
        template <>
        struct type_caster<std::shared_ptr<arrow::Table>> : public gen_type_caster<arrow::Table>
        {
        };
    }
}  // namespace pybind11::detail


// NOTE !!! only for test !!!
void test_unwrap_arrow_pyobject(std::shared_ptr<arrow::Table> &table) {
    std::cout << "------- unwrap_arrow_pyobject-----" << std::endl;
    std::cout << "Table schema: " << std::endl;
    std::cout << table->schema()->ToString() << std::endl;
}

// Register apache arrow table object as fediux dataset and publish on DHT.
// NOTE default using csv driver
void reg_arrow_table_as_ph_dataset(std::shared_ptr<DatasetService> &dataset_service,
                                   std::string &dataset_name,
                                   std::shared_ptr<arrow::Table> &table) {
    // Construct fediux::dataset object from arrow table.
    std::shared_ptr<fediux::DataDriver> driver =
        fediux::DataDirverFactory::getDriver("CSV", dataset_service->getNodeletAddr());
    std::string filepath = "data/" + dataset_name + ".csv";
    auto cursor = driver->initCursor(filepath);
    auto dataset = std::make_shared<fediux::Dataset>(table, driver);

    // Get dataset meta form dataset object.
    DatasetMeta meta(dataset, dataset_name, DatasetVisbility::PUBLIC);

    // Register meta on DHT.
    dataset_service->regDataset(meta);
}
