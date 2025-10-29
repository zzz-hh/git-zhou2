#include <unistd.h>
#include <cstdio>
#include <thread>
#include <string>

#include "src/fediux/service/notify/service.h"
#include "src/fediux/service/notify/model.h"
#include <signal.h>

using fediux::service::NotifyService;
using fediux::service::NotifyServer;
using fediux::service::GRPCNotifyServer;
using fediux::service::EventBusNotifyDelegate;

NotifyService *notify_service_ptr;

void handler(int sig) {
    std::cout << "get signal: " << sig << std::endl;
    GRPCNotifyServer::getInstance().stop();
    delete notify_service_ptr;
}

// TODO read to simulate task stauts and result.

void stdin_func() {
    std::string line;
    std::cout << "waiting input: ";
    while (std::getline(std::cin, line)) {
        if (line == "quit") {
            std::cout << "quit" << std::endl;
            break;
        } else if (line == "s") {
            // simulate send task status
            std::cout << "simulate send task status" << std::endl;
             // FIXME test code
            GRPCNotifyServer::getInstance().addSession();

            EventBusNotifyDelegate::getInstance().notifyStatus(
                  "1", "1","client_id", "SUCCESS", "task test status");

        } else if (line == "r") {
            // simulate send task status
            std::cout << "simulate send task result" << std::endl;
            EventBusNotifyDelegate::getInstance().notifyResult(
                "1", "1","client_id", "task test result");
        } else {
            std::cout << "input: " << line << std::endl;
        }
    }
}

void server_func() {
    notify_service_ptr = new NotifyService("127.0.0.1:7667");
    notify_service_ptr->run();
}

int main(int argc, const char **argv) {
    signal(SIGTERM, handler);
    signal(SIGINT, handler);
    // run stdin in thread
    std::thread stdin_thread(stdin_func);
    // run server in thread
    std::thread server_thread(server_func);
    stdin_thread.join();
    server_thread.join();

    return 0;
}


