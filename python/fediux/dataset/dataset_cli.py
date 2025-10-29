from typing import List
import pyarrow as pa
import pandas as pd
import pyarrow.flight
import threading
import json
from time import sleep


class DatasetClient:
    def do_put(self, df_data, data_url: str):
        raise NotImplementedError()

    def do_get(self, ticket):
        raise NotImplementedError()


class FlightClient(DatasetClient):
    def __init__(self, flight_server_addr: str) -> None:
        super().__init__()
        self.client = pa.flight.connect(f"grpc://{flight_server_addr}")

    def do_put(self, df_data, data_url: str) -> List:
        upload_descriptor = pa.flight.FlightDescriptor.for_path(data_url)
        # df_data to arrow table
        table = pyarrow.Table.from_pandas(df_data)
        writer, meta_reader = self.client.do_put(upload_descriptor, table.schema)
        # TODO test print
        meta = []

        def _reader_thread(meta):
            r = meta_reader.read()
            while r is not None:
                meta.append(json.loads(r.to_pybytes().decode('utf8')))
                r = meta_reader.read()

        thread = threading.Thread(target=_reader_thread, args=(meta,))
        thread.start()
        with writer:
            writer.write_table(table)
            writer.done_writing()
            thread.join()
        while not meta:
            print("waiting for reader get metadata...", )
            sleep(1)
        return meta

    def do_get(self, ticket: str) -> pd.DataFrame:
        reader = self.client.do_get(pyarrow.flight.Ticket(ticket))
        data = reader.read_all()
        df_data = data.to_pandas()
        return df_data


class DatasetClientFactory:
    """Dataset client factory
    """

    @staticmethod
    def create(type: str, node: str, cert: str) -> DatasetClient:
        """Create a dataset client
        """
        if type == "flight":
            return FlightClient(node)
        else:
            raise NotImplementedError()
