from Server import Server as server


class Remote:
    def __init__(self, remote_id: str) -> None:
        self.listener: server = None
        self.controller: server = None
        self._id = remote_id

    def set_listener(self, listener: server) -> None:
        self.listener = listener
        self.listener.set_publish(f"{self._id}_l")
        self.listener.set_subscribe(f"{self._id}_c")

    def set_controller(self, controller) -> None:
        self.controller = controller
        self.controller.set_publish(f"{self._id}_c")
        self.controller.set_subscribe(f"{self._id}_l")

    def start(self) -> None:
        self.controller.connect_redis()
        self.listener.connect_redis()

    def stop(self) -> None:
        pass

    @property
    def id(self) -> str:
        return self._id

    @property
    def status(self) -> int:
        return 1
