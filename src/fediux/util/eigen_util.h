#ifndef SRC_FEDIUX_UTIL_EIGEN_UTIL_H_
#define SRC_FEDIUX_UTIL_EIGEN_UTIL_H_
#include <iostream>
#include <fstream>
#include <vector>
#include <string>

#include "Eigen/Dense"

namespace fediux {

static Eigen::IOFormat HeavyFmt(Eigen::FullPrecision, 0, ",", ",", "[", "]");

static Eigen::IOFormat CSVFormat(Eigen::StreamPrecision, Eigen::DontAlignCols, ", ", ",");

template <typename Derived>
void writeToCSVfile(std::string name, const Eigen::MatrixBase<Derived>& matrix);

Eigen::MatrixXd openData(std::string fileToOpen);

}  // namespace fediux

#endif  // SRC_FEDIUX_UTIL_EIGEN_UTIL_H_
