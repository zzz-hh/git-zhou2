import sys
from os import path
from typing_extensions import Self

here = path.abspath(path.join(path.dirname(__file__), "."))
sys.path.append(here)


class GRPCConnect(object):
    """fediux gRPC connect

    :param str node: Address of the node.
    :param str cert: Path of the local cert file path.

    :return: A fediux gRPC connect.
    """
    __instance_node = {}
    __first_init = False

    # def __new__(cls: type(Self), node, cert) -> Self:
    #     if node not in cls.__instance_node:
    #         cls.__instance_node[node] = super().__new__(cls)
    #     return cls.__instance_node[node]

    def __init__(self, node: str, cert: str) -> None:
        """Constructor
        """
        self.task_map = {}
        if node is not None:
            self.node = node
            # self.channel = grpc.insecure_channel(node)
            # self.aio_channel = grpc.aio.insecure_channel(node)
        else:
            raise

        if cert is not None:
            self.cert = cert
            # TODO
            pass
