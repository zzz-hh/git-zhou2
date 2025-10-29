#include "gtest/gtest.h"
#include "src/fediux/util/crypto/prng.h"

using namespace fediux;

TEST(prng_test, prng_et) {
  PRNG prng(toBlock(1));
  for (u64 i = 0; i < 100; ++i) {
    std::cout << "prng.get<int>(): " << prng.get<int>() << std::endl;
  }
}