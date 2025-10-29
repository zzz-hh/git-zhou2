#ifndef SRC_FEDIUX_ALGORITHM_LOGISTIC_PLAIN_H_
#define SRC_FEDIUX_ALGORITHM_LOGISTIC_PLAIN_H_
#include <time.h>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>
#include <exception>

namespace fediux {
  int logistic_plain_main();
  int logistic_2plain_main(std::string &filename);
}

#endif  // SRC_FEDIUX_ALGORITHM_LOGISTIC_PLAIN_H_
