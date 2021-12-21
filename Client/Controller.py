import pickle
import os

import zlib
from typing import Sequence, Union, Text
import mouse
import keyboard
import pyautogui
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 0.5


def printf(data: Text) -> None:
    os.write(1, bytes(data.encode('utf-8')))


class Controller:
    def __init__(self) -> None:
        self._size = pyautogui.size()
        self.__audio = pyaudio.PyAudio()
        self.__audio_stream = self.__audio.open(format=FORMAT,
                                                channels=CHANNELS,
                                                rate=RATE,
                                                output=True,
                                                frames_per_buffer=CHUNK
                                                )
        self.f = open('test', 'rb+')

    @staticmethod
    def process_keyboard(key: int, down: bool) -> None:
        keyboard.press(key) if down else keyboard.release(key)

    def process_mouse(self, op: Sequence[Union[str, int]]) -> None:
        if op[0] == "BUTTON":
            pyautogui.mouseDown(button=op[1]) if op[2] == "down" else pyautogui.mouseUp(button=op[1])
        elif op[0] == "WHEEL":
            pyautogui.scroll(op[1])
        else:
            mouse.move(*list(map(lambda x, y: int(x * y), op[1:], self._size)), duration=0.035)

    def process_screen(self, data: bytes):
        print(len(data))
        image = zlib.decompress(data)
        image = pickle.loads(image)
        self.f.write(image)
        # print('screen-image', image)
        # printf(f'screen-image||||{image.toBytes()}')

    def process_audio(self, data: bytes):
        data = pickle.loads(data)
        for i in data:
            self.__audio_stream.write(i, CHUNK)
