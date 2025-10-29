#ifndef SRC_FEDIUX_UTIL_HASH_H_
#define SRC_FEDIUX_UTIL_HASH_H_
#include <openssl/evp.h>
#include <string>
namespace fediux {
class Hash {
 public:
  explicit Hash(const std::string& alg = "sha256");
  bool Init() { return md_ != nullptr;}
  std::string HashToString(const std::string &msg);

 private:
  int alg_{NID_sha256};
  const EVP_MD* md_{nullptr};
};
}  // namespace fediux
#endif  // SRC_FEDIUX_UTIL_HASH_H_
