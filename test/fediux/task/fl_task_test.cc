#include "gtest/gtest.h"

#include "src/fediux/task/language/py_parser.h"


namespace fediux::task {
TEST(PyParserTest, PyParserTest_parserDatasets) {
    const char* py_code_c =
        "from fediux import dataset \n"
        "dataset.get('test_data') \n"
        "dataset.get('test_label')";

    // std::string py_code(py_code_c);
    // auto ds = PyParser(py_code).parseDatasets();
    // ASSERT_EQ(ds.size(), 2);
}

}  // namespace fediux::task
