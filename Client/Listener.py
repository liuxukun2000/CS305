import pickle
import struct
from multiprocessing import Process
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


class MouseListener:
    def __init__(self, client: Client, interval: float = 0.05) -> None:
        """
        鼠标移动的监听类

        :param client:
        :param interval:
        """
        assert 0.001 <= interval <= 1, "0.001 <= interval <= 1"
        self._status: Dict[str, str] = dict(
            left="down",
            right="down",
            middle="down"
        )
        self.size = pyautogui.size()  # 获取屏幕大小，便于映射
        self.interval: float = interval  # 采样间隔
        self._last_record: float = time.time()
        self.client = client

    def on_click(self, e: ButtonEvent) -> None:
        """
        点击触发函数
        :param e:
        :return:
        """
        if self._status[e.button] == e.event_type:  # 数据缓冲
            return
        self._status[e.button] = e.event_type
        self.client.send(str(("MOUSE", "BUTTON", e.button, e.event_type)))

    def on_wheel(self, e: WheelEvent) -> None:
        """
        滚动触发函数
        :param e:
        :return:
        """
        self.client.send(str(("MOUSE", "WHEEL", e.delta)))

    def on_move(self, e: MoveEvent) -> None:
        """
        移动触发函数
        :param e:
        :return:
        """
        self.client.send(str(("MOUSE", "MOVE", *tuple(map(lambda x, y: (x / y), (e.x, e.y), self.size)))))

    def global_hook(self, e) -> None:
        """
        全局钩子函数
        :param e:
        :return:
        """
        if isinstance(e, MoveEvent):
            if time.time() - self._last_record >= self.interval:  # 保证采样率
                self._last_record = time.time()
                self.on_move(e)
        elif isinstance(e, WheelEvent):  # 根据事件选择函数
            self.on_wheel(e)
        else:
            self.on_click(e)

    @property
    def position(self) -> Tuple[int, int]:
        """
        获取鼠标位置
        :return:
        """
        return mouse.get_position()

    def start(self):
        """
        设置鼠标的全局钩子
        :return:
        """
        mouse.hook(self.global_hook)

    @staticmethod
    def stop():
        """
        停止监听
        :return:
        """
        mouse.unhook_all()


class KeyboardListener:
    def __init__(self, client: Client) -> None:
        """
        键盘监听器类
        :param client:
        """
        self.client = client
        self.statues: List[bool] = [False for i in range(300)]

    def global_hook(self, key: KeyboardEvent) -> None:
        """
        全局钩子
        :param key:
        :return:
        """
        return self.on_press(key) if key.event_type == 'down' else self.on_release(key)

    def on_press(self, key: KeyboardEvent) -> None:
        """
        按压触发器
        :param key:
        :return:
        """
        if self.statues[key.scan_code]:  # 缓存，防止持续按压
            return
        self.statues[key.scan_code] = True
        self.client.send(str(("KEYBOARD", key.scan_code, True)))

    def on_release(self, key: KeyboardEvent) -> None:
        """
        释放触发器
        :param key:
        :return:
        """
        if not self.statues[key.scan_code]:  # 缓存，防止持续按压
            return
        self.statues[key.scan_code] = False
        self.client.send(str(("KEYBOARD", key.scan_code, False)))

    def start(self):
        """
        设置全局钩子
        :return:
        """
        keyboard.unhook_all()
        keyboard.block_key(272)  # 不监听鼠标左键点击
        keyboard.block_key(273)  # 右键
        keyboard.block_key(274)  # 中键
        keyboard.hook(self.global_hook)

    @staticmethod
    def stop():
        keyboard.unhook_all()


class ScreenListener(threading.Thread):
    def __init__(self, client: Client) -> None:
        self.client = client
        self.__stop = False
        super().__init__()

    def run(self):
        print(self.client)
        start = time.time()
        num = 0
        while not self.__stop:
            # time.sleep(0.05)
            #
            num += 1
            image = cv2.cvtColor(numpy.asarray(ImageGrab.grab()), cv2.COLOR_RGB2BGR)
            image = cv2.resize(image, (640, 360))
            image = zlib.compress(pickle.dumps(image), zlib.Z_BEST_COMPRESSION)
            self.client.send(image)
            if num == 100:
                break
            print('send', time.time() - start)
            # return
        print('<-----', time.time() - start)

    def stop(self):
        self.__stop = True
        time.sleep(0.3)
        self.close()


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
    start = time.time()
    for i in range(30):
        image = cv2.cvtColor(numpy.asarray(ImageGrab.grab()), cv2.COLOR_RGB2BGR)
        image = cv2.resize(image, (1280, 720))
        image = zlib.compress(pickle.dumps(image), zlib.Z_BEST_COMPRESSION)
    print(time.time() - start)


    # print(len(image), struct.pack("L", len(image)))

    # self.client.send(struct.pack("L", len(image)) + image)
    # print(struct.calcsize("L"))
    # ans = struct.pack("L", 130010)
    # print(ans, len(ans))
    # ans = ans + ans
    # ans = ans + ans
    # ans = ans + ans
    #
    # y = struct.unpack("L", ans[:8])
    # print(y, ans[:8])

    # image = cv2.cvtColor(numpy.asarray(ImageGrab.grab()), cv2.COLOR_RGB2BGR)
    # image = cv2.resize(image, (1280, 720))
    # image = zlib.compress(pickle.dumps(image), zlib.Z_BEST_COMPRESSION)
    # print(len(image))
    # with open('test', 'wb') as f:
    #     f.write(b'SCREEN ' + image)
    # x = b''
    # with open('test', 'rb') as f:
    #     x = f.read(len(image) + 7)
    # print(x[-10:])
    #
    # x = b''
    # with open('test', 'rb') as f:
    #     x = f.read()
    # print(x[-10:])
   # time.sleep(3)
   # print('clic')
   # pyautogui.mouseDown(button='left')
   # print('clic')
   # pyautogui.mouseUp(button='left')
   # time.sleep(3)
   # mouse.wheel(-10)
