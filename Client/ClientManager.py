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
        self.__mouse_listener: Union[MouseListener, None] = None
        self.__keyboard_listener: Union[KeyboardListener, None] = None
        self.__screen_listener: Union[ScreenListener, None] = None
        self.__audio_listener: Union[AudioListener, None] = None
        self.__mode: ClientMode = ClientMode.INIT
        self.__session = requests.Session()

        self.__simple_connection: Union[Client, None] = None
        self.__screen_connection: Union[Client, None] = None
        self.__voice_connection: Union[Client, None] = None
        self.__control_connection: Client = Client()

        self.__simple_queue: [Queue, None] = None
        self.__screen_queue: [Queue, None] = None
        self.__voice_queue: [Queue, None] = None
        self.__control_queue: Queue = self.__control_connection.queue

        self.__control_connection.run()

        self.__exit = False
        self.__simple_receive_thread = None
        self.__screen_receive_thread = None
        self.__voice_receive_thread = None
        self.__control_receive_thread = None
        self.__controller = Controller()

    @staticmethod
    def LISTEN(ID: str) -> str:
        return str(("LISTEN", ID))

    @staticmethod
    def CONTROL(ID: str) -> str:
        return str(("CONTROL", ID))

    @staticmethod
    def __url(_url: str) -> str:
        return f"{URL}/{_url}" if _url[0] != '/' else f"{URL}{_url}"

    @property
    def mode(self) -> ClientMode:
        return self.__mode

    def receive_simple(self):
        _op = bytes("('".encode('utf-8'))
        op = b''
        while True:
            if not self.__simple_queue.empty() and not self.__exit:
                data = self.__simple_queue.get_nowait()
                if not data.startswith(_op):
                    op += data
                    continue
                data = ast.literal_eval(op.decode('utf-8'))
                op = b''
                if data[0] == 'MOUSE':
                    self.__controller.process_mouse(data[1:])
                elif data[0] == 'KEYBOARD':
                    self.__controller.process_keyboard(*data[1:])
            else:
                if self.__exit:
                    break

    def receive_image(self):
        _image = bytes("('SCREEN'".encode('utf-8'))
        image = b''
        while True:
            if not self.__screen_queue.empty() and not self.__exit:
                data = self.__screen_queue.get_nowait()
                if not data.startswith(_image):
                    image += data
                    continue
                data = ast.literal_eval(image.decode('utf-8'))
                self.__controller.process_screen(data[1])
                image = b''
                print('recieve')
            else:
                if self.__exit:
                    break
                # else:
                #     print('emp', self.queue.empty())
                #     time.sleep(0.5)

    @staticmethod
    def create_connection() -> Client:
        return Client()

    def set_connection(self, connection: Client, _name: str) -> None:
        _tmp = getattr(self, f"__{_name}_connection")
        _tmp = connection
        _tmp = getattr(self, f"__{_name}_queue")
        _tmp = connection.queue

    def login(self, username: str, password: str) -> bool:
        data = dict(
            username=username,
            password=password
        )
        try:
            response = self.__session.post(url=self.__url('/login/'), data=data)
            data = response.json()
            if data.get('status', 500) != 200:
                return False
            self.__mode = ClientMode.LOGIN
            return True
        except Exception:
            return False

    def send(self, data: Union[str, ByteString], _name: str) -> None:
        connection = getattr(self, f"__{_name}_connection")
        if connection:
            connection.send(data)

    def start_receive_simple(self) -> None:
        self.__simple_receive_thread = Thread(target=self.receive_simple)
        self.__simple_receive_thread.setDaemon(True)
        self.__simple_receive_thread.start()

    def start_receive_screen(self) -> None:
        self.__screen_receive_thread = Thread(target=self.receive_image)
        self.__screen_receive_thread.setDaemon(True)
        self.__screen_receive_thread.start()

    def listen(self) -> str:
        try:
            response = self.__session.post(url=self.__url('/listen/'))
            data = response.json()
            if data.get('status', 500) != 200:
                return ""
            ID = data['id']
            self.set_connection(self.create_connection(), "screen")
            self.send(self.LISTEN('1'), 'control')
            self.set_screen_listener()
            self.__screen_connection.run()
            self.__mode = ClientMode.LISTENER
            self.start_receive_simple()
            return ID
        except Exception:
            return ""

    def control(self, ID: str) -> bool:
        self.set_connection(self.create_connection(), "simple")
        self.send(self.CONTROL(ID), 'control')
        self.__mode = ClientMode.CONTROLLER
        self.set_keyboard_listener()
        self.set_mouse_listener()
        self.__simple_connection.run()
        self.start_receive_screen()
        return True

    def set_keyboard_listener(self) -> None:
        self.__keyboard_listener = KeyboardListener(self.__simple_connection)
        self.__keyboard_listener.setDaemon(True)
        self.__keyboard_listener.start()

    def set_mouse_listener(self) -> None:
        self.__mouse_listener = MouseListener(self.__simple_connection)
        self.__mouse_listener.setDaemon(True)
        self.__mouse_listener.start()

    def set_screen_listener(self) -> None:
        self.__screen_listener = ScreenListener(self.__screen_connection)
        self.__screen_listener.setDaemon(True)
        self.__screen_listener.start()

    def stop(self):
        if self.__mouse_listener:
            self.__mouse_listener.stop()
        if self.__screen_listener:
            self.__mouse_listener.stop()
        if self.__keyboard_listener:
            self.__keyboard_listener.stop()
        # if self.__recive_thread:
        #     self.__recive_thread._stop()
        # self.__screen_listener.stop()


if __name__ == '__main__':
    # op = input()
    # printf('client-ready')
    # op = input()
    y = ClientManager()
    y.login('1', '1')
    y.control('1')
    c = input()
    y.stop()
    sys.exit(0)
    # x.stop()
    # print('1111111111111111111111')
