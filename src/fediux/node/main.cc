#include <signal.h>
#include <arrow/util/logging.h>
#include <arrow/api.h>
#include <arrow/flight/internal.h>
#include <arrow/flight/server.h>
#include "absl/flags/flag.h"
#include "absl/flags/parse.h"
#include "absl/memory/memory.h"
#include "absl/strings/str_cat.h"

#include "src/fediux/node/node_interface.h"
#include "src/fediux/node/node_impl.h"

#include "src/fediux/node/ds.h"
#include "src/fediux/common/common.h"
#include "src/fediux/common/config/server_config.h"
#include "src/fediux/service/dataset/service.h"
#include "src/fediux/service/dataset/meta_service/factory.h"
#ifdef SGX
#include "sgx/ra/service.h"
#endif

ABSL_FLAG(std::string, node_id, "node0", "unique node_id");  // deprecated,
                                                             // remove in future
ABSL_FLAG(std::string, config, "./config/node.yaml", "config file");
ABSL_FLAG(bool, singleton, false, "singleton mode");
ABSL_FLAG(int, service_port, 50050, "node service port");  // deprecated,
                                                           // remove in future
/**
 * @brief
 *  Start Apache arrow flight server with NodeService and DatasetService.
 */
#ifdef SGX
void RunServer(fediux::VMNodeInterface* node_service,
               fediux::DataServiceImpl* dataset_service,
               sgx::RaTlsService* ratls_service,
               int service_port) {
#else
void RunServer(fediux::VMNodeInterface* node_service,
               fediux::DataServiceImpl* dataset_service,
               int service_port) {
#endif
    // Initialize server
    arrow::flight::Location location;
    auto& server_config = fediux::ServerConfig::getInstance();
    auto& host_config = server_config.getServiceConfig();
    std::string ip = host_config.ip();
    uint32_t port = host_config.port();
    if (host_config.use_tls()) {
        LOG(INFO) << "server running using tls";
        // Listen to all interfaces
        ARROW_CHECK_OK(arrow::flight::Location::ForGrpcTls(
            "0.0.0.0", port, &location));
    } else {
        LOG(INFO) << "server running in no tls mode";
        ARROW_CHECK_OK(arrow::flight::Location::ForGrpcTcp(
            "0.0.0.0", port, &location));
    }
    arrow::flight::FlightServerOptions options(location);

    auto server = std::make_unique<arrow::flight::FlightServerBase>();
    // Use builder_hook to register grpc service
    options.builder_hook = [&](void *raw_builder) {
      auto builder = reinterpret_cast<grpc::ServerBuilder *>(raw_builder);
      builder->RegisterService(node_service);
      builder->RegisterService(dataset_service);
#ifdef SGX
      if (ratls_service) {
        builder->RegisterService(ratls_service);
      }
#endif
        // set the max message size to 128M
        builder->SetMaxReceiveMessageSize(128 * 1024 * 1024);
    };

    if (host_config.use_tls()) {
        // init certificate
        auto& cert_config = server_config.getCertificateConfig();
        options.verify_client = true;
        options.root_certificates = cert_config.rootCAContent();
        auto& tls_certificates = options.tls_certificates;
        tls_certificates.clear();
        tls_certificates.push_back(
            {cert_config.certContent(), cert_config.keyContent()});
    }
    // Start the server
    ARROW_CHECK_OK(server->Init(options));
    // Exit with a clean error code (0) on SIGTERM
    ARROW_CHECK_OK(server->SetShutdownOnSignals({SIGTERM}));

    LOG(INFO) << " 💻 Node listening on port: " << service_port;

    ARROW_CHECK_OK(server->Serve());
}

int main(int argc, char **argv) {
    // Register SIGINT signal and signal handler
    signal(SIGINT, [](int sig) {
        LOG(INFO) << "Node received SIGINT signal, shutting down...";
        exit(0);
    });

    google::InitGoogleLogging(argv[0]);
    FLAGS_colorlogtostderr = true;
    FLAGS_alsologtostderr = true;
    FLAGS_log_dir = "./log";
    FLAGS_max_log_size = 10;
    FLAGS_stop_logging_if_full_disk = true;

    absl::ParseCommandLine(argc, argv);
    // int service_port = absl::GetFlag(FLAGS_service_port);
    std::string config_file = absl::GetFlag(FLAGS_config);
    auto& server_config = fediux::ServerConfig::getInstance();
    auto ret = server_config.initServerConfig(config_file);
    if (ret != fediux::retcode::SUCCESS) {
        LOG(ERROR) << "init server config failed";
        return -1;
    }
    auto& host_config = server_config.getServiceConfig();
    int32_t service_port = host_config.port();
    std::string node_id = host_config.id();
    auto& cert_config = server_config.getCertificateConfig();
    std::string node_ip = "0.0.0.0";
    // service for dataset meta control
    auto& node_cfg = server_config.getNodeConfig();
    auto& meta_service_cfg = node_cfg.meta_service_config;
    auto meta_service =
        fediux::service::MetaServiceFactory::Create(
            meta_service_cfg.mode, meta_service_cfg.host_info);
    // service for dataset manager
    using DatasetService = fediux::service::DatasetService;
    auto dataset_manager = std::make_shared<DatasetService>(
        std::move(meta_service));
    // service for task process
    auto node_service_impl = std::make_unique<fediux::VMNodeImpl>(
        config_file, dataset_manager);

    // service for dataset register
    auto data_service = std::make_unique<fediux::DataServiceImpl>(
        dataset_manager.get());
#ifdef SGX
    auto ra_service = node_service_impl->GetNodelet()->GetRaService().get();
    if (ra_service == nullptr) {
      LOG(ERROR) << "Ra service is invliad";
      return EXIT_FAILURE;
    }
    auto node_service = std::make_unique<fediux::VMNodeInterface>(
        std::move(node_service_impl));
    RunServer(node_service.get(), data_service.get(), ra_service, service_port);
#else
    auto node_service = std::make_unique<fediux::VMNodeInterface>(
        std::move(node_service_impl));
    RunServer(node_service.get(), data_service.get(), service_port);
#endif
    return EXIT_SUCCESS;
}
