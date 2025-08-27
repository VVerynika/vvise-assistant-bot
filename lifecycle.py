import threading


_stop_event = threading.Event()


def stop() -> None:
    _stop_event.set()


def is_stopping() -> bool:
    return _stop_event.is_set()


def wait(seconds: float) -> bool:
    return _stop_event.wait(timeout=seconds)

