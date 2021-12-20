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
        super(ServerConfig, self).__init__(is_client=False, max_datagram_frame_size=165536, quic_logger=QuicLogger())
        self.load_cert_chain("/home/satan/桌面/计网/Project/Server/fullchain.pem",
                             "/home/satan/桌面/计网/Project/Server/privkey.pem")
