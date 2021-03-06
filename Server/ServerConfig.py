from typing import Dict, Optional
from aioquic.quic.connection import QuicConfiguration
from aioquic.quic.logger import QuicLogger
from aioquic.tls import SessionTicket


class SessionTicketStore:
    """
    Simple in-memory store for session tickets.
    """

    def __init__(self) -> None:
        self.tickets: Dict[bytes, SessionTicket] = {}

    def add(self, ticket: SessionTicket) -> None:
        self.tickets[ticket.ticket] = ticket

    def pop(self, label: bytes) -> Optional[SessionTicket]:
        return self.tickets.pop(label, None)


class ServerConfig(QuicConfiguration):
    def __init__(self):
        """
        设置服务器信息
        """
        super(ServerConfig, self).__init__(is_client=False, max_datagram_frame_size=165536, quic_logger=QuicLogger())
        self.load_cert_chain("/run/media/satan/DATA/projectdjango/Server/fullchain.pem",
                             "/run/media/satan/DATA/projectdjango/Server/privkey.pem")
        # 选择用于TLS1.3协议的证书
