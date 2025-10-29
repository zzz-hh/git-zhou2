#ifndef SRC_FEDIUX_ALGORITHM_CRYPTFLOW2_MAXPOOL_H_
#define SRC_FEDIUX_ALGORITHM_CRYPTFLOW2_MAXPOOL_H_

#include "Eigen/Dense"

#include "src/fediux/algorithm/base.h"
#include "src/fediux/common/clp.h"
#include "src/fediux/common/common.h"
#include "src/fediux/common/type/type.h"
#include "src/fediux/protocol/cryptflow2/NonLinear/maxpool.h"
#include "src/fediux/protocol/cryptflow2/globals.h"
#include "src/fediux/util/network/socket/session.h"
#include "src/fediux/common/clp.h"
#include "src/fediux/common/type/type.h"
#include "src/fediux/data_store/driver.h"
#include "src/fediux/data_store/factory.h"

#include <fstream>
#include <thread>

using namespace std;
using namespace fediux::sci;

#define MAX_THREADS 4

namespace fediux::cryptflow2
{
  class MaxPoolExecutor : public AlgorithmBase
  {
  public:
    explicit MaxPoolExecutor(PartyConfig &config,
                             std::shared_ptr<DatasetService> dataset_service);
    int loadParams(fediux::rpc::Task &task) override;
    int loadDataset(void) override;
    int initPartyComm(void) override;
    int execute() override;
    int finishPartyComm(void) override;
    int saveModel(void);

  private:
    int num_rows = 35;     // Row num of maxpool
    int num_cols = 1 << 6; // Col num of maxpool
    int b = 4;             // Radix Base
    int batch_size = 0;    // Batch size

    string node_id;         // node id
    string input_filepath_; // input data file directory(path)
    uint64_t mask_l;        // mask
    uint64_t *x;            // input
    uint64_t *z;            // output

    IOPack *iopackArr[MAX_THREADS];
    OTPack *otpackArr[MAX_THREADS];
    void ring_maxpool_thread(int, uint64_t *, uint64_t *, int, int);

    int __party = 0;                // __party ID
    int __bitlength = 32;           // __bitlength of input
    int __num_threads = 1;          // thread_number
    string __address = "127.0.0.1"; // network __address
    int __port = 32000;             // network ports
  };
} // namespace fediux

#endif
