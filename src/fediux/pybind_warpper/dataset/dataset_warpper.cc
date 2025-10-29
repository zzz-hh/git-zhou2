#include <pybind11/pybind11.h>

#include "dataset_warpper.hpp"

PYBIND11_MODULE(fediux_dataset_warpper, m) {

    m.doc() = "primhub dataset API wrapper"; // Optional module docstring
    m.def("test_unwrap_arrow_pyobject", &test_unwrap_arrow_pyobject, pybind11::call_guard<pybind11::gil_scoped_release>());
    m.def("reg_arrow_table_as_ph_dataset", &reg_arrow_table_as_ph_dataset, pybind11::call_guard<pybind11::gil_scoped_release>());
}
