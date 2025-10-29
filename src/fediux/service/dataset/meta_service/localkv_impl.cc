
#include "src/fediux/service/dataset/meta_service/localkv_impl.h"

namespace fediux::service {
retcode LocalDatasetMetaService::PutMeta(const DatasetMeta& meta) {
  return retcode::SUCCESS;
}

retcode LocalDatasetMetaService::GetMeta(const DatasetId &id, FoundMetaHandler handler) {
  return retcode::SUCCESS;
}

retcode LocalDatasetMetaService::FindPeerListFromDatasets(
    const std::vector<DatasetWithParamTag>& datasets_with_tag,
    FoundMetaListHandler handler) {
//
  return retcode::SUCCESS;
}

retcode LocalDatasetMetaService::GetAllMetas(std::vector<DatasetMeta>* metas) {
  return retcode::SUCCESS;
}

}  // namespace fediux::service