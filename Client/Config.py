from aioquic.quic.connection import QuicConfiguration


class ClientConfig(QuicConfiguration):
    def __init__(self):
        super(ClientConfig, self).__init__(is_client=True, max_datagram_frame_size=165536)

