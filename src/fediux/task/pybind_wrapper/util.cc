#include "src/fediux/task/pybind_wrapper/util.h"
#include <glog/logging.h>
#include <random>
#include <utility>
#include "uuid.h"                                                     // NOLINT
namespace fediux::task::wrapper {
retcode GenerateSubtaskId(std::string* sub_task_id) {
  std::random_device rd;
  auto seed_data = std::array<int, std::mt19937::state_size> {};
  std::generate(std::begin(seed_data), std::end(seed_data), std::ref(rd));
  std::seed_seq seq(std::begin(seed_data), std::end(seed_data));
  std::mt19937 generator(seq);
  uuids::uuid_random_generator gen{generator};
  const uuids::uuid id = gen();
  *subtask_id = uuids::to_string(id);
  return retcode::SUCCESS;
}
}