import ast
import pickle
import time
import zlib
from multiprocessing import Process
from threading import Event
from threading import Thread
from typing import Union, Sequence
from PIL import ImageEnhance, Image
import keyboard
import pyautogui
import mouse

import cv2
import numpy
from PIL import ImageGrab

from Listener import MouseListener, KeyboardListener
from Protocol import Client


def LISTEN(ID: str) -> str:
    return str(("LISTEN", ID))


def CONTROL(ID: str) -> str:
    return str(("CONTROL", ID))


class Base:
    def __init__(self, ID: str, event: Event) -> None:
        self.__id = ID
        self.event: Event = event
        self.client = None
        self.init_msg = ''

    @property
    def id(self) -> str:
        return self.__id

    def stop(self) -> None:
        self.event.set()

    def init(self) -> None:
        self.client = Client()
        self.client.send(self.init_msg)
        self.client.run()

    def start(self) -> None:
        NotImplementedError("start method must be implemented!!!")


class SimpleManager(Base):
    def __init__(self, ID: str, event: Event) -> None:
        super(SimpleManager, self).__init__(ID, event)
        self.mouse = None
        self.keyboard = None

    def init(self) -> None:
        self.client = Client()
        self.client.send(self.init_msg)
        self.client.run()
        self.mouse = MouseListener(self.client)
        self.keyboard = KeyboardListener(self.client)

    def start(self) -> None:
        self.init()
        self.mouse.start()
        self.keyboard.start()
        self.event.wait()


class ScreenManager(Base):
    def __init__(self, ID: str, event: Event, _x: int = 1280, _y: int = 720) -> None:
        super(ScreenManager, self).__init__(ID, event)
        self.__x = _x
        self.__y = _y
        self._num = 0
        self._start = time.time()

    def start(self) -> None:
        self.init()
        while not self.event.is_set():
            image = cv2.resize(cv2.cvtColor(numpy.asarray(ImageGrab.grab()), cv2.COLOR_RGB2BGR), (self.__x, self.__y))
            self._num += 1
            self.client.send(zlib.compress(pickle.dumps(image), zlib.Z_BEST_COMPRESSION))
            # self.client.send(pickle.dumps(image))
            print(f"Send {self._num} images in {time.time() - self._start} s")



class ScreenReceiver(Base):
    def __init__(self, ID: str, event: Event, _x: int = 1920, _y: int = 1080) -> None:
        super(ScreenReceiver, self).__init__(ID, event)
        self.__queue = None
        self._num = 0
        self.__x = _x
        self.__y = _y
        self._start = time.time()

    def start(self) -> None:
        self.init()
        print('receive in')
        self.__queue = self.client.queue
        while not self.event.is_set():
            image = zlib.decompress(self.__queue.get())
            # image = self.__queue.get()
            # print('receive image')
            self._num += 1
            image = cv2.resize(pickle.loads(image), (self.__x, self.__y))
            if self._num % 50 == 0:
                cv2.imwrite(f"{self._num}.jpg", image)
            print(f"Receive {self._num} images in {time.time() - self._start} s")


class SimpleReceiver(Base):
    def __init__(self, ID: str, event: Event) -> None:
        super(SimpleReceiver, self).__init__(ID, event)
        self.__queue = None
        self._size = pyautogui.size()

    @staticmethod
    def process_keyboard(key: int, down: bool) -> None:
        keyboard.press(key) if down else keyboard.release(key)

    def process_mouse(self, op: Sequence[Union[str, int]]) -> None:
        if op[0] == "BUTTON":
            pyautogui.mouseDown(button=op[1]) if op[2] == "down" else pyautogui.mouseUp(button=op[1])
        elif op[0] == "WHEEL":
            pyautogui.scroll(op[1])
        else:
            mouse.move(*list(map(lambda x, y: int(x * y), op[1:], self._size)), duration=0.05)

    def start(self) -> None:
        self.init()
        self.__queue = self.client.queue
        while not self.event.is_set():
            data = ast.literal_eval(self.__queue.get())
            if data[0] == 'MOUSE':
                self.process_mouse(data[1:])
            elif data[0] == 'KEYBOARD':
                self.process_keyboard(*data[1:])


def get_process(manager: Base) -> Process:
    return Process(target=manager.start)