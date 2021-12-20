import ast
import asyncio
import threading
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
        self.__loop = asyncio.new_event_loop()
        self.__thread = threading.Thread(target=start_loop, args=(self.__loop,))
        self.__thread.setDaemon(True)
        self.__thread.start()
        self.__transport = threading.Thread(target=self.transport)
        self.__transport.setDaemon(True)
        self.__connection = None
        self.__publish: str = None
        self.__subscribe: str = None
        self.ready = False
        super().__init__(*args, **kwargs)

    def transport(self) -> None:
        _ = self.__connection.pubsub()
        _.subscribe(self.__subscribe)
        for msg in _.listen():
            print(msg)
            if isinstance(msg['data'], bytes):
                print('sent')
                self.sync_send(msg['data'])

    def connect_redis(self) -> None:
        self.__connection = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)

    def set_publish(self, publish: str) -> None:
        self.__publish = publish

    def set_subscribe(self, subscribe) -> None:
        self.__subscribe = subscribe

    def init(self, data: bytes):
        args = ast.literal_eval(data.decode('utf-8'))
        if args[0] == "LISTEN":
            self.set_subscribe(f"{args[1]}_c")
            self.set_publish(f"{args[1]}_l")
        elif args[0] == "CONTROL":
            self.set_subscribe(f"{args[1]}_l")
            self.set_publish(f"{args[1]}_c")
        else:
            return
        self.connect_redis()
        self.ready = True
        self.__transport.start()

    def close_connection(self):
        try:
            if self.__connection:
                self.__connection.close()
            if not self.ready:
                return
            self.__transport._stop()
            self.ready = False
        except Exception:
            pass

    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, StreamDataReceived):
            print(event)
            if not self.ready:
                self.init(event.data)
            else:
                self.__connection.publish(self.__publish, event.data)
                print('pub', event.data)
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