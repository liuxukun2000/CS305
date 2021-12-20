import ast
import os
import pickle
import sys
import time
import zlib
from asyncio import Queue
from enum import Enum, unique
from typing import Union, ByteString, Text
from threading import Thread
from Protocol import ClientProtocol
from Protocol import Client
from Controller import Controller
import requests
from Listener import MouseListener, KeyboardListener, ScreenListener, AudioListener

URL = "http://oj.sustech.xyz:8000"


def printf(data: Text) -> None:
    os.write(1, bytes(data.encode('utf-8')))


@unique
class ClientMode(Enum):
    INIT = 0
    LOGIN = 1
    LISTENER = 2
    CONTROLLER = 3
    LEADER = 4
    MEETING = 5


class ClientManager:
    def __init__(self) -> None:
        self._mouse_listener: Union[MouseListener, None] = None
        self._keyboard_listener: Union[KeyboardListener, None] = None
        self._screen_listener: Union[ScreenListener, None] = None
        self._audio_listener: Union[AudioListener, None] = None
        self._mode: ClientMode = ClientMode.INIT
        self._session = requests.Session()

        self._simple_connection: Union[Client, None] = None
        self._screen_connection: Union[Client, None] = None
        self._voice_connection: Union[Client, None] = None
        self._control_connection: Client = Client()

        self._simple_queue: [Queue, None] = None
        self._screen_queue: [Queue, None] = None
        self._voice_queue: [Queue, None] = None
        self._control_queue: Queue = self._control_connection.queue

        self._control_connection.run()

        self._exit = False
        self._simple_receive_thread = None
        self._screen_receive_thread = None
        self._voice_receive_thread = None
        self._control_receive_thread = None
        self._controller = Controller()

    @staticmethod
    def LISTEN(ID: str) -> str:
        return str(("LISTEN", ID))

    @staticmethod
    def CONTROL(ID: str) -> str:
        return str(("CONTROL", ID))

    @staticmethod
    def _url(_url: str) -> str:
        return f"{URL}/{_url}" if _url[0] != '/' else f"{URL}{_url}"

    @property
    def mode(self) -> ClientMode:
        return self._mode

    def receive_simple(self):
        _op = bytes("('".encode('utf-8'))
        op = b''
        while True:
            if not self._simple_queue.empty() and not self._exit:
                data = self._simple_queue.get_nowait()
                op += data
                if not data.startswith(_op):
                    continue
                _data = ast.literal_eval(op.decode('utf-8'))
                op = b''
                if _data[0] == 'MOUSE':
                    self._controller.process_mouse(_data[1:])
                elif _data[0] == 'KEYBOARD':
                    self._controller.process_keyboard(*_data[1:])
            else:
                if self._exit:
                    break

    def receive_image(self):
        _image = bytes("('SCREEN'".encode('utf-8'))
        image = b''
        while True:
            if not self._screen_queue.empty() and not self._exit:
                data = self._screen_queue.get_nowait()
                image += data
                if not data.startswith(_image):
                    continue
                if image.endswith(b')'):
                    _data = ast.literal_eval(image.decode('utf-8'))
                    self._controller.process_screen(_data[1])
                    image = b''
                    print('recieve')
                else:
                    print('hhh')
            else:
                if self._exit:
                    break
                # else:
                #     print('emp', self.queue.empty())
                #     time.sleep(0.5)

    @staticmethod
    def create_connection() -> Client:
        return Client()

    def set_simple_connection(self, connection: Client) -> None:
        self._simple_connection = connection
        self._simple_queue = connection.queue

    def set_screen_connection(self, connection: Client) -> None:
        self._screen_connection = connection
        self._screen_queue = connection.queue

    def login(self, username: str, password: str) -> bool:
        data = dict(
            username=username,
            password=password
        )
        try:
            response = self._session.post(url=self._url('/login/'), data=data)
            data = response.json()
            if data.get('status', 500) != 200:
                return False
            self._mode = ClientMode.LOGIN
            return True
        except Exception:
            return False

    def send(self, data: Union[str, ByteString], _name: str) -> None:
        connection = None
        if _name == "control":
            connection = self._control_connection
        elif _name == "screen":
            connection = self._screen_connection
        elif _name == "simple":
            connection = self._simple_connection
        if connection:
            connection.send(data)

    def start_receive_simple(self) -> None:
        self._simple_receive_thread = Thread(target=self.receive_simple)
        self._simple_receive_thread.setDaemon(True)
        self._simple_receive_thread.start()

    def start_receive_screen(self) -> None:
        self._screen_receive_thread = Thread(target=self.receive_image)
        self._screen_receive_thread.setDaemon(True)
        self._screen_receive_thread.start()

    def listen(self) -> str:
        try:
            response = self._session.post(url=self._url('/listen/'))
            data = response.json()
            if data.get('status', 500) != 200:
                return ""
            ID = data['id']
            self.set_simple_connection(self.create_connection())
            self.set_screen_connection(self.create_connection())
            self.send(self.LISTEN('1simple'), 'simple')
            self.send(self.LISTEN('1screen'), 'screen')
            self.set_screen_listener()
            self._screen_connection.run()
            self._simple_connection.run()
            self._mode = ClientMode.LISTENER
            self.start_receive_simple()
            return ID
        except Exception:
            return ""

    def control(self, ID: str) -> bool:
        self.set_simple_connection(self.create_connection())
        self.set_screen_connection(self.create_connection())
        self.send(self.CONTROL('1simple'), 'simple')
        self.send(self.CONTROL('1screen'), 'screen')
        self._mode = ClientMode.CONTROLLER
        self.set_keyboard_listener()
        self.set_mouse_listener()
        self._simple_connection.run()
        self._screen_connection.run()
        self.start_receive_screen()
        return True

    def set_keyboard_listener(self) -> None:
        self._keyboard_listener = KeyboardListener(self._simple_connection)
        self._keyboard_listener.setDaemon(True)
        self._keyboard_listener.start()

    def set_mouse_listener(self) -> None:
        self._mouse_listener = MouseListener(self._simple_connection)
        self._mouse_listener.setDaemon(True)
        self._mouse_listener.start()

    def set_screen_listener(self) -> None:
        self._screen_listener = ScreenListener(self._screen_connection)
        self._screen_listener.setDaemon(True)
        self._screen_listener.start()

    def stop(self):
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._screen_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        # if self._recive_thread:
        #     self._recive_thread._stop()
        # self._screen_listener.stop()


if __name__ == '__main__':
    # op = input()
    # printf('client-ready')
    # op = input()
    y = ClientManager()
    # getattr(y, '_simple_connection')

    y.login('1', '1')
    # y.listen()
    y.control('1')
    c = input()
    y.stop()
    sys.exit(0)

    # x.stop()
    # print('1111111111111111111111')
