#include <pybind11/pybind11.h>
#include <string>

#include "src/fediux/util/network/socket/ioservice.h"
#include "src/fediux/util/network/socket/session.h"
#include "src/fediux/util/network/socket/channel.h"
#include "src/fediux/util/util.h"


using fediux::SessionMode;
using fediux::IOService;
using fediux::Session;
using fediux::Channel;

namespace py = pybind11;


PYBIND11_MODULE(fediux_channel, m) {
  py::class_<IOService>(m, "IOService")
        .def(py::init<uint64_t>());

  py::enum_<SessionMode>(m, "SessionMode")
        .value("Client", SessionMode::Client)
        .value("Server", SessionMode::Server)
        .export_values();

  py::class_<Session>(m, "Session")
        .def(py::init<IOService &, std::string, SessionMode, std::string>())
        .def("addChannel", &Session::addChannel);

  py::class_<Channel>(m, "Channel")
        .def(py::init<>())
        .def("send", &Channel::send<std::string>)
        .def("asyncSendCopy", &Channel::asyncSendCopy<std::string>)
        .def("recv", [](Channel &self) {
              std::string recv_str;
              self.recv(recv_str);
              return recv_str;
        })
        .def("close", &Channel::close);

}
