#ifndef SRC_FEDIUX_SERVICE_DATASET_META_SERVICE_MEMORY_IMPL_H_
#define SRC_FEDIUX_SERVICE_DATASET_META_SERVICE_MEMORY_IMPL_H_
#include <vector>
#include <memory>

#include "src/fediux/common/common.h"
#include "src/fediux/service/dataset/meta_service/interface.h"
#include "src/fediux/service/dataset/meta_service/localkv/storage_backend.h"

namespace fediux::service {
class MemoryDatasetMetaService : public DatasetMetaService {
 public:
  MemoryDatasetMetaService();
  retcode PutMeta(const DatasetMeta& meta) override;
  retcode GetMeta(const DatasetId &id, FoundMetaHandler handler) override;
  retcode FindPeerListFromDatasets(
      const std::vector<DatasetWithParamTag>& datasets_with_tag,
      FoundMetaListHandler handler) override;
  retcode GetAllMetas(std::vector<DatasetMeta>* metas) override;

 private:
  std::unique_ptr<StorageBackend> storage_{nullptr};
};
}  // namespace fediux::service

#endif  // SRC_FEDIUX_SERVICE_DATASET_META_SERVICE_MEMORY_IMPL_H_
