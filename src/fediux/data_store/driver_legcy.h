#ifndef SRC_FEDIUX_DATASTORE_DRIVER_LEGCY_H_
#define SRC_FEDIUX_DATASTORE_DRIVER_LEGCY_H_


#include <math.h>
#include <stdlib.h>
#include <time.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>
#include <exception>
#include <memory>

namespace fediux {
 eMatrix<double> load_data_local_logistic(const std::string &fullpath);

}  // namespace fediux

#endif // SRC_FEDIUX_DATASTORE_DRIVER_LEGCY_H_
