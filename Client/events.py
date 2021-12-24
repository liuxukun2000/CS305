import os
from enum import Enum, unique
from typing import Any, Text, Union, Any, Tuple

def debug(x: str):
    os.write(2, bytes(x.encode('utf-8')))


@unique
class ReceiveEvent(Enum):
    DisplayReady = 'display-ready'
    UserLogin = 'user-login'
    UserRegister = 'user-register'

    GetCode = 'get-code'
    ChangeName = 'change-name'
    NetworkDelay = 'network-delay'
    DisplayName = 'display-name'
    UserLogout = 'user-logout'
    ChangePassword = 'change-password'
    RefreshCode = 'refresh-code'

    EnableSlave = 'enable-slave'
    DisableSlave = 'disable-slave'
    RemoteControl = 'remote-control'
    CreateMeeting = 'create-meeting'
    JoinMeeting = 'join-meeting'

    TerminateControl = 'terminate-control'
    ConfirmExit = 'confirm-exit'


@unique
class SendEvent(Enum):
    ClientReady = 'client-ready'
    ClientMessage = 'client-message'
    NetworkDelay = 'network-delay'
    DisplayName = 'display-name'
    Okay = 'okay'
    Failed = 'failed'
    ScreenImage = 'screen-image'
    EndControl = 'end-control'


def printf(data: Text) -> None:
    os.write(1, bytes(data.encode('utf-8')))
    # os.write(2, bytes(data.encode('utf-8')))


def scanf() -> Tuple[Union[ReceiveEvent, None], Any]:
    data = os.read(0, 4096).decode('utf-8').strip().split('||||')
    try:
        return ReceiveEvent(data[0]), data[1:]
    except Exception:
        return None, None


@unique
class ClientMode(Enum):
    INIT = 0
    LOGIN = 1
    LISTENER = 2
    CONTROLLER = 3
    LEADER = 4
    MEETING = 5


def get_message(event: SendEvent, msg: Any) -> str:
    return '||||'.join((event.value, *msg)) + '@@@@'
