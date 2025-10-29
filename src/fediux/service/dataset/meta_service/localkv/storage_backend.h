#ifndef SRC_FEDIUX_SERVICE_DATASET_LOCALKV_STORAGE_BACKEND_H_
#define SRC_FEDIUX_SERVICE_DATASET_LOCALKV_STORAGE_BACKEND_H_

#include <string>
#include <vector>
#include <utility>
#include <map>
#include "src/fediux/common/common.h"
#include "src/fediux/service/dataset/util.hpp"

namespace fediux::service {

/**
 * Backend of key-value storage
 */
class StorageBackend {
 public:
  virtual ~StorageBackend() = default;

  /**
   * Adds @param value corresponding to given @param key.
  */
  virtual retcode PutValue(const Key& key, const Value& value) = 0;

  /**
   * Search for the @return value corresponding to given @param key.
  */
  virtual retcode GetValue(const Key& key, Value* result) = 0;

  /**
   * Search for the @return value corresponding to given @param keys.
  */
  virtual retcode GetValue(const std::vector<Key>& keys,
                            std::map<Key, Value>* result) = 0;

  /**
   * Removes value corresponded to given @param key.
  */
  virtual retcode Erase(const Key& key) = 0;

  /**
   * Get all key and value pairs from the storage.
  */
  virtual retcode GetAll(std::map<Key, Value>* results) = 0;
};  // class StorageBackend

}  // namespace fediux::service

#endif  // SRC_FEDIUX_SERVICE_DATASET_LOCALKV_STORAGE_BACKEND_H_
