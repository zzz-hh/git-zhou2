#ifndef SRC_FEDIUX_SERVICE_DATASET_LOCALKV_STORAGE_LEVELDB_H_
#define SRC_FEDIUX_SERVICE_DATASET_LOCALKV_STORAGE_LEVELDB_H_

#include <string>
#include <leveldb/db.h>
#include "src/fediux/service/dataset/meta_service/localkv/storage_backend.h"

namespace fediux::service {
class StorageBackendLevelDB : public StorageBackend {
 public:
  StorageBackendLevelDB(const std::string& path);
  ~StorageBackendLevelDB();

  retcode PutValue(const Key& key, const Value& value) override;
  retcode GetValue(const Key& key, Value* result) override;
  retcode GetValue(const std::vector<Key>& keys,
                    std::map<Key, Value>* result) override;
  retcode Erase(const Key& key) override;
  retcode GetAll(std::map<Key, Value>* results) override;

 private:
    std::string path_;
    leveldb::DB* db_{nullptr};

}; // class StorageBackendLevelDB
}  // namespace fediux::service

#endif  // SRC_FEDIUX_SERVICE_DATASET_LOCALKV_STORAGE_LEVELDB_H_
