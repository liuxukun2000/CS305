import asyncio
import ipaddress
import socket
import sys
import threading
import time
from multiprocessing import Queue
from typing import cast, Optional, Callable, Union, List

from aioquic.asyncio import QuicConnectionProtocol
from aioquic.asyncio.protocol import QuicStreamHandler
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import QuicEvent, StreamDataReceived, ConnectionTerminated
from aioquic.tls import SessionTicketHandler

from Config import ClientConfig


def start_loop(loop: asyncio.BaseEventLoop):
    """
    保持事件循环一直运行
    :param loop:
    :return:
    """
    asyncio.set_event_loop(loop)
    loop.run_forever()


class ClientProtocol(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):
        """
        Client端的协议类
        :param args:
        :param kwargs:
        """
        self._connect = False
        self.__queue = None
        self._cache: List[bytes] = [b'' for i in range(256)]
        super(ClientProtocol, self).__init__(*args, **kwargs)

    def set_queue(self, queue: Queue) -> None:
        self.__queue = queue

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = cast(asyncio.DatagramTransport, transport)
        self._connect = True

    async def send(self, data: str) -> None:
        """
        发送数据
        :param data:
        :return:
        """
        stream_id = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(stream_id, bytes(data.encode('utf-8')) if isinstance(data, str) else data, True)
        self.transmit()
        await asyncio.sleep(0.0001)

    @property
    def connected(self) -> bool:
        return self._connect

    def quic_event_received(self, event: QuicEvent):
        """
        详情请见服务器协议实现
        :param event:
        :return:
        """
        if isinstance(event, StreamDataReceived):
            _id = event.stream_id % 256
            if not event.end_stream:
                self._cache[_id] += event.data
            else:
                if self.__queue:
                    self.__queue.put_nowait(self._cache[_id] + event.data)
                self._cache[_id] = b''
        if isinstance(event, ConnectionTerminated):
            self._connect = False


class Client:
    def __init__(self, host: str = "oj.sustech.xyz", port: int = 8080) -> None:
        """
        对于客户端协议的二次封装
        :param host:
        :param port:
        """
        self.loop = asyncio.new_event_loop()
        self._connect: ClientProtocol = cast(ClientProtocol, self.loop.run_until_complete(
            self.connect(
                host=host,
                port=port,
                configuration=ClientConfig(),
                create_protocol=ClientProtocol
            )
        ))  # 强制类型转换
        self.__host = host
        self.__port = port
        self._signal = None
        self.size = 0
        self.t = threading.Thread(target=start_loop, args=(self.loop,))
        self.t.setDaemon(True)  # 设置事件循环线程的守护标志
        self.t.start()
        self.queue = Queue(maxsize=128)  # 设置接收队列
        self._connect.set_queue(self.queue)
        self.__ping = True
        self.__delay = 0

    @property
    def delay(self) -> int:
        return self.__delay

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

        """
        连接服务器
        :param host:
        :param port:
        :param configuration:
        :param create_protocol:
        :param session_ticket_handler:
        :param stream_handler:
        :param wait_connected:
        :param local_port:
        :return:
        """
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
        """
        获取与服务器连接的延时
        :return:
        """
        while self.__ping:
            start = time.time_ns()
            await self._connect.ping()
            self.__delay = round((time.time_ns() - start) / 1000000, 2)
            await asyncio.sleep(1)

    def run(self):
        self.__ping = True
        asyncio.run_coroutine_threadsafe(self.ping(), self.loop)

    @property
    def connected(self) -> bool:
        return self._connect.connected

    def reconnect(self) -> None:
        """
        断线重连的应用层实现
        :return:
        """
        self.__ping = False
        time.sleep(2)
        self._connect = cast(ClientProtocol, self.loop.run_until_complete(
            self.connect(
                host=self.__host,
                port=self.__port,
                configuration=ClientConfig(),
                create_protocol=ClientProtocol
            )
        ))

    def close(self) -> None:
        self._connect.close()

if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(run())
    x = Client()
    print('start')
    x.start()
    x.send('123')
    x.join()
