#ifndef SRC_FEDIUX_UTIL_FILE_UTIL_H_
#define SRC_FEDIUX_UTIL_FILE_UTIL_H_

#include <dirent.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <string>
#include <sstream>
#include <vector>
#include <map>
#include <utility>
#include "src/fediux/common/common.h"

namespace fediux {
retcode ReadFileContents(const std::string& fpath, std::string* contents);
std::vector<std::string> GetFiles(const std::string& path);
int ValidateDir(const std::string &file_path);
bool FileExists(const std::string& file_path);
bool RemoveFile(const std::string& file_path);
int64_t FileSize(const std::string& file_path);
/**
 * complete path using provided path
 * if file_path is relative path, concat default_storage_path to file path
 * or using file_path
*/
std::string CompletePath(const std::string& default_storage_path,
                         const std::string& file_path);
/**
 * complete path using storage path configured in config file
 * if file_path is relative path, concat default_storage_path to file path
 * or using file_path
*/
std::string CompletePath(const std::string& file_path);
}

#endif  // SRC_FEDIUX_UTIL_FILE_UTIL_H_
