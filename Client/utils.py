import ast
import asyncio
import pickle
import signal
import sys
import time
import zlib
from multiprocessing import Process, Event, Queue
from threading import Thread
import base64
from typing import Union, Sequence
from io import BytesIO
import sounddevice as sd
from PIL import ImageEnhance, Image
import keyboard
import pyautogui
import mouse
from events import *
import cv2
import numpy
from PIL import ImageGrab

from Listener import MouseListener, KeyboardListener
from Protocol import Client

CHUNK = 1024
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 0.5


def start_loop(loop: asyncio.BaseEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


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
        keyboard.unhook_all()
        mouse.unhook_all()


class ScreenManager(Base):
    def __init__(self, ID: str, event: Event, _x: int = 1280, _y: int = 720) -> None:
        super(ScreenManager, self).__init__(ID, event)
        self.__x = _x
        self.__y = _y
        self._num = 0
        self._start = time.time()

    def start(self, screen: bool = True) -> None:
        self.init()
        op = True
        cap = None
        if not screen:
            cap = cv2.VideoCapture(0)
            op = cap.isOpened()
        if screen or not op:
            while not self.event.is_set():
                start = time.time()

                image = ImageGrab.grab()
                image = cv2.cvtColor(numpy.asarray(image.resize((1920, 1080), Image.ANTIALIAS)), cv2.COLOR_RGB2BGR)
                # image = cv2.resize(cv2.cvtColor(numpy.asarray(ImageGrab.grab()), cv2.COLOR_RGB2BGR), (self.__x, self.__y))
                self._num += 1
                # self.client.send(zlib.compress(cv2.imencode('.jpeg', image)[1], zlib.Z_BEST_COMPRESSION))
                self.client.send(zlib.compress(pickle.dumps(image), zlib.Z_BEST_COMPRESSION))
                # self.client.send(pickle.dumps(image))
                debug(f"Send {self._num} images in {time.time() - self._start} s")
                _ = round(0.25 - time.time() + start, 2)
                if _ > 0:
                    time.sleep(_)
                # time.sleep(3)
        else:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 360)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
            while not self.event.is_set():
                start = time.time()
                _, image = cap.read()
                if not _:
                    break
                self._num += 1
                self.client.send(zlib.compress(pickle.dumps(image), zlib.Z_BEST_COMPRESSION))
                # self.client.send(pickle.dumps(image))
                debug(f"Send {self._num} images in {time.time() - self._start} s")
                _ = round(0.2 - time.time() + start, 2)
                if _ > 0:
                    time.sleep(_)


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
        self._start = time.time()
        self.__queue = self.client.queue
        while not self.event.is_set():
            image = zlib.decompress(self.__queue.get())
            # image = self.__queue.get()
            if self.__queue.qsize() >= 12:
                _ = self.__queue.get()
                continue
            # print('receive image')
            self._num += 1
            image = cv2.resize(pickle.loads(image), (self.__x, self.__y))
            if self._num % 50 == 0:
                cv2.imwrite(f"{self._num}.jpg", image)
            image = cv2.imencode('.jpg', image)[1].tostring()
            debug('recive')
            # image = cv2.resize(cv2.imdecode(image, 1), (self.__x, self.__y))
            # printf(get_message(SendEvent.ScreenImage, (str(base64.b64encode(image)), str(self.client.delay))))
            os.write(1, b'screen-image||||' + base64.b64encode(image) + b'||||' +
                     bytes(str(self.client.delay).encode('utf-8')) + b'@@@@')
            # sys.stdout.flush()

            # with open(f"{self._num}.txt", 'w') as f:
            #     f.write(get_message(SendEvent.ScreenImage, (str(base64.b64encode(image)),)))

            debug(f"Receive {self._num} images in {time.time() - self._start} s")
        printf(get_message(SendEvent.EndControl, ()))
        debug('image--------------shut------------------down')


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
        keyboard.unhook_all()
        mouse.unhook_all()
        self.__queue = self.client.queue
        while not self.event.is_set():
            data = ast.literal_eval(self.__queue.get().decode('utf-8'))
            if data[0] == 'MOUSE':
                self.process_mouse(data[1:])
            elif data[0] == 'KEYBOARD':
                self.process_keyboard(*data[1:])


def get_process(manager: Base) -> Process:
    return Process(target=manager.start)

HANDLED_SIGNALS = (
    signal.SIGINT,  # Unix signal 2. Sent by Ctrl+C.
    signal.SIGTERM,  # Unix signal 15. Sent by `kill <pid>`.
)


def signal_handler(a, b):
    try:
        sd.stop()
        debug('audio stop')
    except Exception:
        pass

class AudioManager(Base):
    def __init__(self, ID: str, event: Event, token: str) -> None:
        super(AudioManager, self).__init__(ID, event)
        self.__queue = None
        self.__token = token

    def start(self) -> None:
        self.init()
        while not self.event.is_set():
            myrecording = sd.rec(int(RECORD_SECONDS * RATE), samplerate=RATE, channels=1)
            sd.wait()
            self.client.send(zlib.compress(pickle.dumps((self.__token, myrecording)), zlib.Z_BEST_SPEED))


class AudioReceiver(Base):
    def __init__(self, ID: str, event: Event, token: str) -> None:
        super(AudioReceiver, self).__init__(ID, event)
        self.__queue = None
        self.__threads = 4
        self.__token = token

    @staticmethod
    def play(queue: Queue):
        while True:
            data = queue.get()
            sd.play(data)

    def start(self) -> None:
        for sig in HANDLED_SIGNALS:
            signal.signal(sig, signal_handler)
        self.init()
        queues: List[Queue] = [Queue() for i in range(self.__threads)]
        pool: List[Thread] = [Thread(target=self.play, args=(queues[i],)) for i in range(self.__threads)]
        for i in pool:
            i.setDaemon(True)
            i.start()
        print('receive in')
        self.__queue = self.client.queue
        tmp = 0
        while not self.event.is_set():
            token, data = pickle.loads(zlib.decompress(self.__queue.get()))
            if token != self.__token:
                queues[tmp % self.__threads].put(data)
                tmp += 1
        sd.stop(ignore_errors=True)
        for i in pool:
            try:
                i._stop()
            except Exception:
                pass
        debug('audio--------------shut------------------down')



