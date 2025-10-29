#ifndef SRC_FEDIUX_P2P_NODE_STUB_H_
#define SRC_FEDIUX_P2P_NODE_STUB_H_

#include <iostream>
#include <memory>
#include <set>
#include <vector>
#include <string>

#include <boost/beast.hpp>
#include <boost/di.hpp>
#include <boost/thread/thread.hpp>

#include <libp2p/common/hexutil.hpp>
#include <libp2p/injector/kademlia_injector.hpp>
#include <libp2p/log/configurator.hpp>
#include <libp2p/log/sublogger.hpp>
#include <libp2p/multi/content_identifier_codec.hpp>
#include <libp2p/protocol/identify/identify.hpp>
#include <libp2p/protocol/identify/identify_msg_processor.hpp>
#include <libp2p/outcome/outcome.hpp>


namespace fediux::p2p {

/**
 * @brief Nodestub class
 * Provides basic functionality to interact with other nodes. eg: Kademlia, Identify, etc.
 */
class NodeStub {
    public:
        NodeStub(const std::vector<std::string>& bootstrap_nodes_addr);
        ~NodeStub();
        void start(std::string_view ma_str);

        // Kademlia DHT
        void putDHTValue(libp2p::protocol::kademlia::ContentId key, std::string value);
        void putDHTValue(std::string key, std::string value);
        void getDHTValue(std::string key, libp2p::protocol::kademlia::FoundValueHandler handler);
        void getDHTValue(libp2p::protocol::kademlia::ContentId key,
                                libp2p::protocol::kademlia::FoundValueHandler handler);
    private:
        void onInit();
        std::vector<std::string> bootstrap_nodes_addr_;
        std::shared_ptr<boost::asio::io_context> io_context_;
        libp2p::crypto::KeyPair node_kp_;
        std::vector<libp2p::peer::PeerInfo> bootstrap_nodes_;
        std::shared_ptr<libp2p::Host> host_;
        std::shared_ptr<libp2p::protocol::Identify> identify_;
        std::shared_ptr<libp2p::protocol::kademlia::Kademlia> kademlia_;
        libp2p::protocol::kademlia::Config kademlia_config_;
        boost::thread_group threadpool_;

};  // class NodeStub


}  // namespace fediux::p2p

#endif  // SRC_FEDIUX_P2P_P2PNODE_STUB_H_
