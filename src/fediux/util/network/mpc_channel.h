#ifndef SRC_FEDIUX_UTIL_NETWORK_MPC_CHANNEL_H_
#define SRC_FEDIUX_UTIL_NETWORK_MPC_CHANNEL_H_
#include <string>
#include <queue>
#include <memory>
#include <atomic>
#include <utility>

#include "cryptoTools/Common/Defines.h"
#include "cryptoTools/Network/SocketAdapter.h"
#include "src/fediux/util/network/grpc_link_context.h"
#include "src/fediux/util/network/link_context.h"
#include "src/fediux/util/threadsafe_queue.h"
#include "network/base_channel.h"

using fediux::ThreadSafeQueue;
namespace ph_link = primihub::link;
namespace fediux::network {
class MPCTaskChannel : public ph_link::ChannelBase {
 public:
  MPCTaskChannel(const std::string &job_id,
                  const std::string &task_id,
                  const std::string &request_id,
                  const std::string &local_node_id,
                  const std::string &peer_node_id,
                  LinkContext *link_context,
                  std::shared_ptr<network::IChannel> channel) {
    job_id_ = job_id;
    task_id_ = task_id;
    request_id_ = request_id;
    local_node_id_ = local_node_id;
    peer_node_id_ = peer_node_id;
    link_context_ = link_context;
    send_channel_ = channel;
    recv_channel_ = channel;
    cancel_ = false;

    // send_count_.store(0);
    // recv_count_.store(0);
    std::stringstream ss_send;
    ss_send << request_id_ << "_" << sub_task_id_<< "_"
            << local_node_id_ << "_" << peer_node_id_;
    send_key_ = ss_send.str();
    std::stringstream ss_recv;
    ss_recv << request_id_ << "_" << sub_task_id_<< "_"
            << peer_node_id_ << "_" << local_node_id_;
    recv_key_ = ss_recv.str();
    VLOG(3) << "job_id " << job_id_ << ", task_id " << task_id_
            << ", request_id " << request_id_
            << ", local_node " << local_node_id_ << ", peer node "
            << peer_node_id_;
  }

  MPCTaskChannel(const std::string &local_node_id,
                  const std::string &peer_node_id,
                  LinkContext *link_context,
                  std::shared_ptr<network::IChannel> channel) {
    job_id_ = link_context->job_id();
    task_id_ = link_context->task_id();
    sub_task_id_ = link_context->sub_task_id();
    request_id_ = link_context->request_id();
    local_node_id_ = local_node_id;
    peer_node_id_ = peer_node_id;
    link_context_ = link_context;
    send_channel_ = channel;
    recv_channel_ = channel;
    cancel_ = false;

    // send_count_.store(0);
    // recv_count_.store(0);
    std::stringstream ss_send;
    ss_send << request_id_ << "_" << sub_task_id_<< "_"
            << local_node_id_ << "_" << peer_node_id_;
    send_key_ = ss_send.str();
    std::stringstream ss_recv;
    ss_recv << request_id_ << "_" << sub_task_id_<< "_"
            << peer_node_id_ << "_" << local_node_id_;
    recv_key_ = ss_recv.str();
    VLOG(3) << "job_id " << job_id_ << ", task_id " << task_id_
            << ", request_id " << request_id_
            << ", local_node " << local_node_id_ << ", peer node "
            << peer_node_id_;
  }

  MPCTaskChannel(const std::string &local_node_id,
                  const std::string &peer_node_id,
                  LinkContext *link_context,
                  std::shared_ptr<network::IChannel> send_channel,
                  std::shared_ptr<network::IChannel> recv_channel) {
    job_id_ = link_context->job_id();
    task_id_ = link_context->task_id();
    sub_task_id_ = link_context->sub_task_id();
    request_id_ = link_context->request_id();
    local_node_id_ = local_node_id;
    peer_node_id_ = peer_node_id;
    link_context_ = link_context;
    send_channel_ = std::move(send_channel);
    recv_channel_ = std::move(recv_channel);
    cancel_ = false;
    std::stringstream ss_send;
    ss_send << request_id_ << "_" << sub_task_id_<< "_"
            << local_node_id_ << "_" << peer_node_id_;
    send_key_ = ss_send.str();
    std::stringstream ss_recv;
    ss_recv << request_id_ << "_" << sub_task_id_<< "_"
            << peer_node_id_ << "_" << local_node_id_;
    recv_key_ = ss_recv.str();

    VLOG(3) << "job_id " << job_id_ << ", task_id " << task_id_ << ", "
            << "request_id " << request_id_ << ", "
            << "local_node " << local_node_id_ << ", peer node "
            << peer_node_id_;
  }

  ~MPCTaskChannel() {}
  ph_link::retcode SendImpl(const std::string& send_buf) override;
  ph_link::retcode SendImpl(std::string_view send_buff_sv) override;
  ph_link::retcode SendImpl(const char* buff, size_t size) override;
  ph_link::retcode RecvImpl(std::string* recv_buf) override;
  ph_link::retcode RecvImpl(char* recv_buf, size_t recv_size) override;
  void close() override;
  void cancel() override;

 private:
  std::atomic<bool> cancel_{false};
  std::string job_id_;
  std::string task_id_;
  std::string sub_task_id_;
  std::string request_id_;
  std::string local_node_id_;
  std::string peer_node_id_;
  std::shared_ptr<network::IChannel> send_channel_;
  std::shared_ptr<network::IChannel> recv_channel_;
  network::LinkContext* link_context_{nullptr};
  std::string send_key_;
  std::string recv_key_;
};
}  // namespace fediux::network
#endif  // SRC_FEDIUX_UTIL_NETWORK_MPC_CHANNEL_H_

