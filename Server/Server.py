import ast
import asyncio
import threading
import time
from typing import Union, ByteString, Sequence, Dict, List
from aioquic.asyncio import *
from aioquic.quic.events import QuicEvent, StreamDataReceived, ConnectionTerminated
import redis
from ServerConfig import ServerConfig
from multiprocessing import Event, Process


def start_loop(loop: asyncio.BaseEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


class ServerProtocol(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):
        """
        服务器协议
        以下所有变量均以下划线开头表示私有变量
        :param args:
        :param kwargs:
        """
        self.__loop = asyncio.new_event_loop()
        self.__thread = threading.Thread(target=start_loop, args=(self.__loop,))  # 维持事件循环的运行
        self.__thread.setDaemon(True)  # 设置守护线程
        self.__thread.start()
        self.__transport = threading.Thread(target=self.transport)  # 开始转发
        self.__transport.setDaemon(True)
        self.__connection = None
        self.__publish: str = None
        self.__subscribe: str = None
        self.ready = False
        self._cache: List[bytes] = [b'' for i in range(256)]  # 服务器缓存，用于手动拼接数据报
        super().__init__(*args, **kwargs)

    def transport(self) -> None:
        """
        用于广播收到的信息
        :return:
        """
        _ = self.__connection.pubsub()
        _.subscribe(self.__subscribe)
        for msg in _.listen():
            if isinstance(msg['data'], bytes):
                self.sync_send(msg['data'])

    def connect_redis(self) -> None:
        self.__connection = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)

    def set_publish(self, publish: str) -> None:
        self.__publish = publish

    def set_subscribe(self, subscribe) -> None:
        self.__subscribe = subscribe

    def init(self, data: bytes):
        """
        数据初始化，服务器收到的第一条消息将被用于初始化状态
        :param data:
        :return:
        """
        args = ast.literal_eval(data.decode('utf-8'))
        if args[0] == "LISTEN":
            self.set_subscribe(f"{args[1]}_c")
            self.set_publish(f"{args[1]}_l")
        elif args[0] == "CONTROL":
            self.set_subscribe(f"{args[1]}_l")
            self.set_publish(f"{args[1]}_c")
        elif args[0] == "control":
            self.set_subscribe(f"{args[1]}")
            self.set_publish(f"{args[1]}")
        else:
            return
        self.connect_redis()
        self.ready = True
        self.__transport.start()

    def close_connection(self):
        """
        关不连接
        :return:
        """
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
        """
        数据接收触发器
        :param event:
        :return:
        """
        if isinstance(event, StreamDataReceived):  # 如果收到了数据
            if not self.ready:
                self.init(event.data)  # 第一条消息
            else:
                _id = event.stream_id % 256  # 循环队列
                if not event.end_stream:  # 拼接缓存
                    self._cache[_id] += event.data
                else:  # 拼接完成， 发送
                    self.__connection.publish(self.__publish, self._cache[_id] + event.data)
                    self._cache[_id] = b''
        if isinstance(event, ConnectionTerminated):  # 断开连接
            self.close_connection()
            print(event)

    def sync_send(self, data: Union[str, ByteString]) -> None:
        """
        异步发送的非阻塞同步实现
        :param data:
        :return:
        """
        asyncio.run_coroutine_threadsafe(self.send(data), self._loop)

    async def send(self, data: Union[str, ByteString]) -> None:
        """
        数据发送
        :param data:
        :return:
        """
        stream_id = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(stream_id,
                                    bytes(data.encode('utf-8') if isinstance(data, str) else data),
                                    True)
        self.transmit()  # 清空缓冲
        await asyncio.sleep(0.0001)


def run(_event: Event):
    print('start')
    loop = asyncio.get_event_loop()
    t = threading.Thread(target=start_loop, args=(loop,))
    t.setDaemon(True)
    t.start()
    configuration = ServerConfig()
    asyncio.run_coroutine_threadsafe(serve(
        host="0.0.0.0",
        port=8080,
        configuration=configuration,
        create_protocol=ServerProtocol,
    ), loop)
    _event.wait()
    print('end')


if __name__ == '__main__':
    event = Event()
    pro = []
    num = 8
    for i in range(num):
        pro.append(Process(target=run, args=(event,)))
        print(i)
        pro[i].daemon = True
        pro[i].start()
        # time.sleep(0.5)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        event.set()
    time.sleep(1)
    print('killing')
    for i in range(num):
        pro[i].terminate()
        pro[i].kill()
