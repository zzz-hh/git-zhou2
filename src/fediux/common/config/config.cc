#include "src/fediux/common/config/config.h"

#if defined(__GNUC__) && (__GNUC__ < 8) && !defined(__clang__)
#include <experimental/filesystem>
#else
#include <filesystem>
#endif
#include <fstream>


#if defined(__GNUC__) && (__GNUC__ < 8) && !defined(__clang__)
namespace fs = std::experimental::filesystem;
#else
namespace fs = std::filesystem;
#endif

namespace fediux::file_utility {
retcode checkFileValidation(const std::string& config_file) {
  fs::path file(config_file);
  if (!fs::exists(file)) {
    LOG(ERROR) << "File " << file.string() << " does not exist";
    return retcode::FAIL;
  }
  return retcode::SUCCESS;
}

retcode getFileContents(const std::string& fpath, std::string* contents) {
  // auto ret = checkFileValidation(fpath);
  // if (ret != retcode::SUCCESS) {
  //     return retcode::FAIL;
  // }
  std::ifstream f_in_stream(fpath);
  std::string contents_((std::istreambuf_iterator<char>(f_in_stream)),
                      std::istreambuf_iterator<char>());
  *contents = std::move(contents_);
  return retcode::SUCCESS;
}
}  // namespace fediux::file_utility

namespace fediux::common {
retcode CertificateConfig::initCertificateConfig() {
  auto ret = fediux::file_utility::getFileContents(this->root_ca_path_,
                                                     &this->root_ca_content_);
  if (ret != retcode::SUCCESS) {
    return retcode::FAIL;
  }
  ret = fediux::file_utility::getFileContents(this->key_path_,
                                                &this->key_content_);
  if (ret != retcode::SUCCESS) {
    return retcode::FAIL;
  }
  ret = fediux::file_utility::getFileContents(this->cert_path_,
                                                &this->cert_content_);
  if (ret != retcode::SUCCESS) {
    return retcode::FAIL;
  }
  return retcode::SUCCESS;
}
}  // namespace fediux::common
