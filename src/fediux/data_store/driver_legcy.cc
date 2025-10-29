#include "src/fediux/data_store/driver_legcy.h"

using namespace Eigen;

namespace fediux {

eMatrix<double> load_data_local(const std::string& fullpath) {
  std::cout << "go into function: load_data_local" << std::endl;
  std::string line, num;
  std::fstream fs;

  fs.open(fullpath.c_str(), std::fstream::in);
  if (!fs) {
    std::cout << "File not exists: " << fullpath << std::endl;
    return eMatrix<double>(0, 0);
  } else {
    std::cout << "Start to load data from a fixed full path: "
      << fullpath << std::endl;
  }

  unsigned int rowInd = 0;
  unsigned int colInd;
  std::vector<std::vector<double>> tmpVec;
  std::vector<double> tmpRow;
  while (getline(fs, line)) {
    rowInd += 1;
    colInd = 0;
    std::istringstream readstr(line);
    tmpRow.clear();
    // while (readstr >> num) {
    while (getline(readstr, num, ',')) {
      colInd += 1;
      tmpRow.push_back(std::stold(num.c_str()));
    }
    tmpVec.push_back(tmpRow);
  }
  fs.close();

  eMatrix<double> res(rowInd, colInd);
  for (unsigned int i = 0; i < rowInd; ++i) {
    for (unsigned int j = 0; j < colInd; ++j) {
      res(i, j) = tmpVec[i][j];
    }
  }

  return res;
}


eMatrix<double> load_data_local_logistic(const std::string& fullpath) {
  std::cout << "go into function: load_data_local" << fullpath << std::endl;
  std::string line, num;
  std::fstream fs;

  fs.open(fullpath.c_str(), std::fstream::in);
  if (!fs) {
    std::cout << "File not exists: " << fullpath << std::endl;
    return eMatrix<double>(0, 0);
  } else {
    std::cout << "Start to load data from a fixed full path: "
      << fullpath << std::endl;
  }

  unsigned int rowInd = 0;
  unsigned int colInd;
  std::vector<std::vector<double>> tmpVec;
  std::vector<double> tmpRow;
  while (getline(fs, line)) {
    rowInd += 1;
    colInd = 0;
    std::istringstream readstr(line);
    tmpRow.clear();
    // while (readstr >> num) {
    while (getline(readstr, num, ',')) {
      colInd += 1;
      tmpRow.push_back(std::stold(num.c_str()));
    }
    tmpVec.push_back(tmpRow);
  }
  fs.close();

  eMatrix<double> res(rowInd, colInd);
  for (unsigned int i = 0; i < rowInd; ++i) {
    for (unsigned int j = 0; j < colInd; ++j) {
      res(i, j) = tmpVec[i][j];
    }
  }

  return res;
}

} // namespace fediux
