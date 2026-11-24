"""Wake the isolated financial worker when the durable queue changes."""
from contextlib import contextmanager
from threading import Condition, Event, Thread

from psycopg import OperationalError


class QueueWake:
    def __init__(self):
        self.changed = Condition()
        self.generation = 0

    def wait(self, after, timeout):
        with self.changed:
            self.changed.wait_for(lambda: self.generation != after, timeout)

    def listen(self, connect, stop):
        while not stop.is_set():
            try:
                with connect() as db:
                    db.commit()
                    db.autocommit = True
                    db.execute('LISTEN demo_delivery_ready')
                    while not stop.is_set():
                        for _ in db.notifies(timeout=0.25, stop_after=1):
                            with self.changed:
                                self.generation += 1
                                self.changed.notify_all()
            except (OSError, OperationalError, ValueError):
                # The caller continues bounded polling during a disconnect.
                stop.wait(1)


@contextmanager
def watch_queue(connect):
    wake = QueueWake()
    stop = Event()
    thread = Thread(target=wake.listen, args=(connect, stop), daemon=True)
    thread.start()
    try:
        yield wake
    finally:
        stop.set()
        thread.join(timeout=5)
