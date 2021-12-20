import asyncio
from asyncio.queues import Queue
import socket
import sys
from typing import cast, Optional, Callable, Union
from aioquic.asyncio import connect, QuicConnectionProtocol
from aioquic.asyncio.protocol import QuicStreamHandler
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import QuicEvent, StreamDataReceived, ConnectionTerminated
from aioquic.tls import SessionTicketHandler
# import nest_asyncio
# nest_asyncio.apply()
from Config import ClientConfig
import threading
import ipaddress


def start_loop(loop: asyncio.BaseEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


class ClientProtocol(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):
        self._connect = False
        self.__queue = None
        super(ClientProtocol, self).__init__(*args, **kwargs)

    @property
    def connected(self) -> bool:
        return self._connect

    def set_queue(self, queue: Queue) -> None:
        self.__queue = queue

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = cast(asyncio.DatagramTransport, transport)
        self._connect = True

    async def send(self, data: str) -> None:
        stream_id = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(stream_id, bytes(data.encode('utf-8')) if isinstance(data, str) else data, False)
        self.transmit()
        await asyncio.sleep(0.0001)

    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, StreamDataReceived):
            # print(event.data)
            if self.__queue and not self.__queue.full():
                self.__queue.put_nowait(event.data)
                # print('queue-> ', event.data)
            else:
                pass
                # print('<------', print(event.data))
        if isinstance(event, ConnectionTerminated):
            # print('closed')
            print(event)


class Client:
    def __init__(self, host: str = "oj.sustech.xyz", port: int = 8080) -> None:
        self.loop = asyncio.new_event_loop()
        self._connect: ClientProtocol = cast(ClientProtocol, self.loop.run_until_complete(
            self.connect(
                host=host,
                port=port,
                configuration=ClientConfig(),
                create_protocol=ClientProtocol
            )
        ))
        self._signal = None
        self.size = 0
        self.t = threading.Thread(target=start_loop, args=(self.loop,))
        self.t.setDaemon(True)
        self.t.start()
        self.queue = Queue(maxsize=128)
        self._connect.set_queue(self.queue)

    @staticmethod
    async def connect(host: str,
                      port: int,
                      *,
                      configuration: Optional[QuicConfiguration] = None,
                      create_protocol: Optional[Callable] = QuicConnectionProtocol,
                      session_ticket_handler: Optional[SessionTicketHandler] = None,
                      stream_handler: Optional[QuicStreamHandler] = None,
                      wait_connected: bool = True,
                      local_port: int = 0, ):
        loop = asyncio.get_event_loop()
        local_host = "::"
        try:
            ipaddress.ip_address(host)
            server_name = None
        except ValueError:
            server_name = host

        # lookup remote address
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
        addr = infos[0][4]
        if len(addr) == 2:
            # determine behaviour for IPv4
            if sys.platform == "win32":
                # on Windows, we must use an IPv4 socket to reach an IPv4 host
                local_host = "0.0.0.0"
            else:
                # other platforms support dual-stack sockets
                addr = ("::ffff:" + addr[0], addr[1], 0, 0)

        # prepare QUIC connection
        if configuration is None:
            configuration = QuicConfiguration(is_client=True)
        if configuration.server_name is None:
            configuration.server_name = server_name
        connection = QuicConnection(
            configuration=configuration, session_ticket_handler=session_ticket_handler
        )

        # connect
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: create_protocol(connection, stream_handler=stream_handler),
            local_addr=(local_host, local_port),
        )
        protocol = cast(QuicConnectionProtocol, protocol)
        # try:
        protocol.connect(addr)
        if wait_connected:
            await protocol.wait_connected()
        return protocol

    def send(self, data: Union[str, bytes]):
        try:
            asyncio.run_coroutine_threadsafe(self._connect.send(data), self.loop)
        except Exception as e:
            print(e)

    async def ping(self):
        while True:
            await self._connect.ping()
            await asyncio.sleep(1)

    def run(self):
        asyncio.run_coroutine_threadsafe(self.ping(), self.loop)

        # self.t.join()


if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(run())
    x = Client()
    print('start')
    x.start()
    x.send('123')
    x.join()
