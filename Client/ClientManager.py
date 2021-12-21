import ast
import os
import pickle
import struct
import sys
import threading
import time
import zlib
from multiprocessing import Process, Queue
# from asyncio import Queue
from enum import Enum, unique
from typing import Union, ByteString, Text, Tuple, Dict, Callable, Any
import requests
from utils import *

URL = "http://oj.sustech.xyz:8000"


@unique
class ReceiveEvent(Enum):
    DisplayReady = 'display-ready'
    UserLogin = 'user-login'
    ChangeName = 'change-name'
    NetworkDelay = 'network-delay'
    DisplayName = 'display-name'
    UserLogout = 'user-logout'
    ChangePassword = 'change-password'


@unique
class SendEvent(Enum):
    ClientReady = 'client-ready'
    ClientMessage = 'client-message'
    NetworkDelay = 'network-delay'
    DisplayName = 'display-name'
    Okay = 'okay'
    Failed = 'failed'


def printf(data: Text) -> None:
    os.write(1, bytes(data.encode('utf-8')))
    # os.write(2, bytes(data.encode('utf-8')))


def scanf() -> Tuple[ReceiveEvent, Any]:
    data = os.read(0, 4096).decode('utf-8').strip().split('||||')
    os.write(2, bytes(str(data).encode('utf-8')))
    return ReceiveEvent(data[0]), data[1:]


@unique
class ClientMode(Enum):
    INIT = 0
    LOGIN = 1
    LISTENER = 2
    CONTROLLER = 3
    LEADER = 4
    MEETING = 5


def get_message(event: SendEvent, msg: Any) -> str:
    return '||||'.join((event.value, *msg))


class ClientManager:
    def __init__(self) -> None:
        self.__event = Event()
        self.__simple_manager: Union[SimpleManager, None] = None
        self.__screen_manager: Union[ScreenManager, None] = None
        self.__simple_receiver: Union[SimpleReceiver, None] = None
        self.__screen_receiver: Union[ScreenReceiver, None] = None

        self._mode: ClientMode = ClientMode.INIT
        self._session = requests.Session()

        self._control_connection: Client = Client()
        self._control_queue: Queue = self._control_connection.queue
        self._control_connection.run()

        self.__simple_process: Union[Process, None] = None
        self.__screen_process: Union[Process, None] = None

        self.__username: str = ""
        self.__token: str = ""

    def delay(self) -> int:
        printf(get_message(SendEvent.NetworkDelay, (str(self._control_connection.delay),)))
        return self._control_connection.delay

    def display_name(self):
        printf(get_message(SendEvent.DisplayName, (self.__username)))
        return self.__username

    def logout(self):
        printf(get_message(SendEvent.Okay, ()))
        self._mode = ClientMode.INIT

    def connected(self) -> None:
        printf(get_message(SendEvent.ClientReady, ()))

    @staticmethod
    def _url(_url: str) -> str:
        return f"{URL}/{_url}" if _url[0] != '/' else f"{URL}{_url}"

    @property
    def mode(self) -> ClientMode:
        return self._mode

    @staticmethod
    def create_connection() -> Client:
        return Client()

    def change_name(self, username) -> None:
        data = dict(
            newname=username
        )
        try:
            response = self._session.post(url=self._url('/changename/'), data=data)
            data = response.json()
            if data.get('status', 500) != 200:
                printf(get_message(SendEvent.Failed, ()))
            self.__username = username

            printf(get_message(SendEvent.Okay, ()))
        except Exception:
            printf(get_message(SendEvent.Failed, ()))

    def change_password(self, password: str) -> None:
        data = dict(
            password=password
        )
        try:
            response = self._session.post(url=self._url('/changepwd/'), data=data)
            data = response.json()
            if data.get('status', 500) != 200:
                printf(get_message(SendEvent.Failed, ()))
            printf(get_message(SendEvent.Okay, ()))
        except Exception:
            printf(get_message(SendEvent.Failed, ()))

    def login(self, username: str, password: str) -> None:
        data = dict(
            username=username,
            password=password
        )
        try:
            response = self._session.post(url=self._url('/login/'), data=data)
            data = response.json()
            if data.get('status', 500) != 200:
                printf(get_message(SendEvent.Failed, ()))
            self._mode = ClientMode.LOGIN
            self.__username = username
            self.__token = data['token']
            printf(get_message(SendEvent.Okay, ()))
        except Exception:
            printf(get_message(SendEvent.Failed, ()))

    def listen(self) -> str:
        try:
            response = self._session.post(url=self._url('/listen/'))
            data = response.json()
            if data.get('status', 500) != 200:
                return ""
            ID = data['id']
            ID = '1'
            # listener 需要发送screen,接收simple
            self.__screen_manager = ScreenManager(ID, self.__event)
            self.__screen_manager.init_msg = LISTEN(f"{ID}_screen")
            self.__screen_process = get_process(self.__screen_manager)
            self.__screen_process.start()

            # self.__simple_receiver = SimpleReceiver(ID, self.__event)
            # self.__simple_receiver.init(LISTEN(f"{ID}_simple"))
            # self.__simple_process = get_process(self.__simple_receiver)
            # self.__simple_process.start()
            return ID
        except Exception:
            return ""

    def control(self, ID: str) -> bool:
        self.__screen_receiver = ScreenReceiver(ID, self.__event)
        self.__screen_receiver.init_msg = CONTROL(f"{ID}_screen")
        self.__screen_process = get_process(self.__screen_receiver)
        self.__screen_process.start()

        # self.__simple_manager = SimpleManager(ID, self.__event)
        # self.__simple_manager.init(CONTROL(f"{ID}_simple"))
        # self.__simple_process = get_process(self.__simple_manager)
        # self.__simple_process.start()
        return True

    def stop(self):
        self.__event.set()


if __name__ == '__main__':
    manager = ClientManager()
    FUNCTIONHASH: Dict[ReceiveEvent, Callable] = {
        ReceiveEvent.DisplayReady: manager.connected,
        ReceiveEvent.DisplayName: manager.display_name,
        ReceiveEvent.NetworkDelay: manager.delay,
        ReceiveEvent.UserLogout: manager.logout,
        ReceiveEvent.UserLogin: manager.login,
        ReceiveEvent.ChangeName: manager.change_name,
        ReceiveEvent.ChangePassword: manager.change_password
    }
    while True:
        event, data = scanf()
        # os.write(2, b'rec')
        FUNCTIONHASH[event](*data)
        # os.write(2, b'done')

    #
    #
    #
    # # op = input()
    # # printf('client-ready')
    # # op = input()
    # y = ClientManager()
    # x = ClientManager()
    # # getattr(y, '_simple_connection')
    #
    # y.login('1', '1')
    # x.login('1', '1')
    # y.control('1')
    #
    # x.listen()
    #
    # print('inp')
    # c = input()
    # print('stop')
    # x.stop()
    # y.stop()
    # sys.exit(0)
    #
    # # x.stop()
    # # print('1111111111111111111111')
