import pickle
import struct
import time
from typing import List, Tuple, Dict
import struct
import pyaudio
from PIL import ImageGrab
from cv2 import cv2
import numpy
from pynput import mouse, keyboard
import threading
import keyboard, mouse
from keyboard import KeyboardEvent
from mouse import MoveEvent, ButtonEvent, WheelEvent
from Protocol import Client
import pyautogui, asyncio, sys
import zlib

__all__ = ['MouseListener', 'KeyboardListener', 'AudioListener']

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 0.5


class MouseListener(threading.Thread):
    def __init__(self, client: Client, interval: float = 0.05) -> None:
        assert 0.001 <= interval <= 1, "0.001 <= interval <= 1"
        self._status: Dict[str, str] = dict(
            left="down",
            right="down",
            middle="down"
        )
        self.size = pyautogui.size()
        self.interval: float = interval
        self._last_record: float = time.time()
        self.client = client
        super().__init__()

    def on_click(self, e: ButtonEvent) -> None:
        if self._status[e.button] == e.event_type:
            return
        self._status[e.button] = e.event_type
        self.client.send(str(("MOUSE", "BUTTON", e.button, e.event_type)))

    def on_wheel(self, e: WheelEvent) -> None:
        self.client.send(str(("MOUSE", "WHEEL", e.delta)))

    def on_move(self, e: MoveEvent) -> None:
        # print(map(lambda x, y: int(x * y), (e.x, e.y), self._rate))
        self.client.send(str(("MOUSE", "MOVE", *tuple(map(lambda x, y: (x / y), (e.x, e.y), self.size)))))

    def global_hook(self, e) -> None:
        if isinstance(e, MoveEvent):
            if time.time() - self._last_record >= self.interval:
                self._last_record = time.time()
                self.on_move(e)
        elif isinstance(e, WheelEvent):
            self.on_wheel(e)
        else:
            self.on_click(e)

    @property
    def position(self) -> Tuple[int, int]:
        return mouse.get_position()

    def start(self):
        mouse.hook(self.global_hook)

    def stop(self):
        mouse.unhook_all()
        self._stop()


class KeyboardListener(threading.Thread):
    def __init__(self, client: Client) -> None:
        self.client = client
        self.statues: List[bool] = [False for i in range(300)]
        super().__init__()

    def global_hook(self, key: KeyboardEvent) -> None:
        return self.on_press(key) if key.event_type == 'down' else self.on_release(key)

    def on_press(self, key: KeyboardEvent) -> None:
        # print('press', key.scan_code, self.statues[key.scan_code])
        if self.statues[key.scan_code]:
            return
        self.statues[key.scan_code] = True
        self.client.send(str(("KEYBOARD", key.scan_code, True)))

    def on_release(self, key: KeyboardEvent) -> None:
        # print('release', key.scan_code, self.statues[key.scan_code])
        if not self.statues[key.scan_code]:
            print('not', key.scan_code)
            return
        self.statues[key.scan_code] = False
        self.client.send(str(("KEYBOARD", key.scan_code, False)))

    def run(self):
        keyboard.unhook_all()
        keyboard.block_key(272)
        keyboard.block_key(273)
        keyboard.block_key(274)
        keyboard.hook(self.global_hook)
        keyboard.wait(hotkey='ctrl+q')
        print('key')

    def stop(self):
        keyboard.unhook_all()
        self._stop()


class ScreenListener(threading.Thread):
    def __init__(self, client: Client) -> None:
        self.client = client
        self.__stop = False
        super().__init__()

    def run(self):
        while not self.__stop:
            time.sleep(3)
            # self.client.send(str(("SCREEN", '1')))
            image = cv2.cvtColor(numpy.asarray(ImageGrab.grab()), cv2.COLOR_RGB2BGR)
            image = cv2.resize(image, (1280, 720))
            image = zlib.compress(pickle.dumps(image), zlib.Z_BEST_COMPRESSION)
            print(len(image))
            self.client.send(struct.pack("L", len(image)) + image)

    def stop(self):
        self.__stop = True
        time.sleep(0.3)
        self._stop()


class AudioListener(threading.Thread):
    def __init__(self, client: Client) -> None:
        self._client = client
        self.__audio = pyaudio.PyAudio()
        self.__stream = None
        self.__stop = False
        super().__init__()

    def run(self):
        self.__stream = self.__audio.open(format=FORMAT,
                                          channels=CHANNELS,
                                          rate=RATE,
                                          input=True,
                                          frames_per_buffer=CHUNK)
        while not self.__stop and self.__stream.is_active():
            frames = []
            for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = self.__stream.read(CHUNK)
                frames.append(data)
            self._client.send(str(("AUDIO", pickle.dumps(frames))))

    def stop(self):
        self.__stop = True
        time.sleep(0.3)
        self.__stream.stop_stream()
        self.__stream.close()
        self._stop()


if __name__ == '__main__':
    print(struct.calcsize("L"))
    image = cv2.cvtColor(numpy.asarray(ImageGrab.grab()), cv2.COLOR_RGB2BGR)
    image = cv2.resize(image, (1280, 720))
    image = zlib.compress(pickle.dumps(image), zlib.Z_BEST_COMPRESSION)
    print(len(image))
    with open('test', 'wb') as f:
        f.write(b'SCREEN ' + image)
    x = b''
    with open('test', 'rb') as f:
        x = f.read(len(image) + 7)
    print(x[-10:])

    x = b''
    with open('test', 'rb') as f:
        x = f.read()
    print(x[-10:])
   # time.sleep(3)
   # print('clic')
   # pyautogui.mouseDown(button='left')
   # print('clic')
   # pyautogui.mouseUp(button='left')
   # time.sleep(3)
   # mouse.wheel(-10)
