import ast
import asyncio
import threading
import time
from typing import Union, ByteString, Sequence
from aioquic.asyncio import *
from aioquic.quic.events import QuicEvent, StreamDataReceived, ConnectionTerminated
import redis
from ServerConfig import ServerConfig


def start_loop(loop: asyncio.BaseEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


class ServerProtocol(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)



    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, StreamDataReceived):
            # print(event)
            if not self.ready:
                self.init(event.data)
            else:
                # start = time.time()
                self.__connection.publish(self.__publish, event.data)
                # print(time.time() - start)
                # print('pub', event.data)
        if isinstance(event, ConnectionTerminated):
            self.close_connection()
            print(event)

    def sync_send(self, data: Union[str, ByteString]) -> None:
        asyncio.run_coroutine_threadsafe(self.send(data), self._loop)

    async def send(self, data: Union[str, ByteString]) -> None:
        stream_id = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(stream_id,
                                    bytes(data.encode('utf-8') if isinstance(data, str) else data),
                                    False)
        self.transmit()
        await asyncio.sleep(0.0001)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    configuration = ServerConfig()


    x = loop.run_until_complete(serve(
        host="0.0.0.0",
        port=8080,
        configuration=configuration,
        create_protocol=ServerProtocol,
    ))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass