import ph_secure_lib as ph_slib
from fediux.context import Context
from enum import Enum
import numpy as np
from fediux.utils.logger_util import logger

class PsiType(Enum):
    KKRT = "KKRT"
    ECDH = "ECDH"

class DataType(Enum):
    Interger = 0
    String = 1

class TwoPartyPsi:
    def __init__(self):
        cert_config = Context.cert_config
        root_ca_path = cert_config.get("root_ca_path", "")
        key_path = cert_config.get("key_path", "")
        cert_path = cert_config.get("cert_path", "")
        self.psi_executor = ph_slib.PSIExecutor(Context.message,
                                root_ca_path, key_path, cert_path)

    def run(self,
            input: np.ndarray,
            parties: list,
            receiver: str,
            broadcast: bool,
            protocol: PsiType = PsiType.KKRT,
            data_type: DataType = DataType.String):
        if len(input) == 0:
            return list()
        if data_type == DataType.Interger:
            logger.info(f"dtype is int")
            return self.psi_executor.run_as_integer(
                input, parties, receiver, broadcast, protocol.value)
        elif data_type == DataType.String:
            logger.info(f"dtype is str")
            return self.psi_executor.run_as_string(
                input, parties, receiver, broadcast, protocol.value)