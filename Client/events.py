import os
from enum import Enum, unique
from typing import Any, Text, Union, Any, Tuple, List

buf: str = ""


def debug(x: str):
    os.write(2, bytes(x.encode('utf-8')))


@unique
class ReceiveEvent(Enum):
    """
    GUI发送的指令
    """
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

    ExitMeeting = 'exit-meeting'  # username
    StartShare = 'start-share'  #
    EndShare = 'end-share'  #
    EnableAudio = 'enable-audio'  # username
    DisableAudio = 'disable-audio'  # username
    SendMessage = 'send-message'  # msg
    SetAdmin = 'set-admin'  # username
    GiveHost = 'give-host'  # username

    SwitchVideo = 'switch-video'


@unique
class SendEvent(Enum):
    """
    Client发送给GUI的指令
    """
    ClientReady = 'client-ready'
    ClientMessage = 'client-message'
    NetworkDelay = 'network-delay'
    DisplayName = 'display-name'
    Okay = 'okay'
    Failed = 'failed'
    ScreenImage = 'screen-image'

    EndControl = 'end-control'

    StartControl = 'start-control'



    UpdateLevel = 'update-level'  # 0/1/2
    UpdateShare = 'update-share'  # username/''
    UpdateAudio = 'update-audio'  # true/false
    UpdateInfo = 'update-info'  # __token, username
    UpdateMessage = 'update-message'  # from, msg
    UpdateMembers = 'update-members'  # username, level, audio
    ForceExit = 'force-exit'  #


def printf(data: Text) -> None:
    """
    向GUI发消息
    :param data:
    :return:
    """
    os.write(1, bytes(data.encode('utf-8')))


def scanf() -> List[Tuple[Union[ReceiveEvent, None], Any]]:
    """
    接收GUI的消息并进行拆分
    :return:
    """
    ans: List[Tuple[Union[ReceiveEvent, None], Any]] = []
    try:
        global buf
        data = os.read(0, 4096).decode('utf-8').strip()
        buf += data
        while True:
            pos = buf.find('@@@@')  # @@@@ 用于分隔指令
            if pos == -1:
                return ans
            else:
                tmp = buf[: pos].split('||||')  # ||||用于分隔参数
                buf = buf[pos + 4:]
                try:
                    ans.append((ReceiveEvent(tmp[0]), tmp[1:]))
                except Exception:
                    ans.append((None, None))
    except Exception:
        return ans


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
