from os import write as send
from os import read as receive
from enum import Enum, unique
from random import random
from time import sleep


IPC_RECEVER = 0
IPC_SENDR = 1
IPC_ERROR = 2
IPC_EVENT_LENGTH = 4096
IPC_ENCODE = 'utf8'


@unique
class REvent(Enum):
    DisplayReady = 'display-ready'
    UserLogin = 'user-login'
    ChangeName = 'change-name'
    NetworkSpeed = 'network-speed'
    DisplayName = 'display-name'
    UserLogout = 'user-logout'
    ChangePassword = 'change-password'


@unique
class SEvent(Enum):
    ClientReady = 'client-ready'
    ClientMessage = 'client-message'
    NetworkSpeed = 'network-speed'
    DisplayName = 'display-name'
    Okay = 'okay'
    Failed = 'failed'


def event_reply(event: SEvent, *body) -> None:
    send(IPC_SENDR, bytes('||||'.join((event.value,) + body).encode(IPC_ENCODE)))


def event_listen(max_len: int = IPC_EVENT_LENGTH) -> tuple[REvent, list[str]]:
    datagram = receive(IPC_RECEVER, max_len)
    msgs = datagram.decode(IPC_ENCODE).strip().split('||||')
    return (REvent(msgs[0]), msgs[1:])


@unique
class State(Enum):
    ConnectScene = 0
    MainScene = 1


def connect_scene(event: REvent, body: list[str]) -> State:
    match event:
        case REvent.DisplayReady:
            event_reply(SEvent.ClientReady)
            return State.ConnectScene
        case REvent.UserLogin:
            send(2, bytes(str(body).encode(IPC_ENCODE)))
            if body[0] == 'admin' and body[1] == 'kjkttt':
                sleep(1)
                event_reply(SEvent.Okay)
                return State.MainScene
            else:
                event_reply(SEvent.Failed, '用户名或密码错误')
                return State.ConnectScene
        case _:
            event_reply(SEvent.Failed, 'Unknown Message')
            return State.ConnectScene


def main_scene(event: REvent, body: list[str]) -> State:
    match event:
        case REvent.NetworkSpeed:
            event_reply(SEvent.NetworkSpeed, f'{round(random() * 1000)}')
            return State.MainScene
        case REvent.DisplayName:
            sleep(1)
            event_reply(SEvent.DisplayName, '锟斤拷')
            return State.MainScene
        case REvent.UserLogout:
            event_reply(SEvent.Okay)
            return State.ConnectScene
        case REvent.ChangeName:
            event_reply(SEvent.Okay)
            return State.MainScene
        case REvent.ChangePassword:
            event_reply(SEvent.Okay)
            return State.MainScene
        case _:
            event_reply(SEvent.Failed, 'Unknown Message')
            return State.MainScene


if __name__ == '__main__':
    scene = State.ConnectScene
    while True:
        (event, body) = event_listen()
        match scene:
            case State.ConnectScene:
                scene = connect_scene(event, body)
            case State.MainScene:
                scene = main_scene(event, body)
            case _:
                continue
