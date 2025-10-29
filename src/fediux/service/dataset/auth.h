#ifndef SRC_FEDIUX_SERVICE_DATASET_AUTH_H__
#define SRC_FEDIUX_SERVICE_DATASET_AUTH_H__

namespace fediux::service {
class DatasetAuthFilterInterface {
    // TODO
    virtual bool isWriteAuth(const std::string& datasetId, const std::string& owner) = 0;
    virtual bool isReadAuth(const std::string &datasetId, const std::string& owner) = 0;
};

} // namespace fediux::service

#endif // SRC_FEDIUX_SERVICE_DATASET_AUTH_H__
