#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "src/fediux/common/type/type.h"

namespace fediux {

TEST(TypeTest, si64_add) {
  si64 a_share({1, 2});
  si64 b_share({10, 20});
  si64 c_share;
  c_share = a_share + b_share;
  EXPECT_EQ(c_share[0], 11);
  EXPECT_EQ(c_share[1], 22);
}

}  // namespace fediux
