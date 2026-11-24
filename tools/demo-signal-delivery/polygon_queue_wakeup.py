"""Wake the isolated financial worker when the durable queue changes."""
from contextlib import contextmanager
from threading import Condition, Event, Thread

from psycopg import OperationalError

SOURCE_READY = "demo_delivery_polygon_source_ready"


class QueueWake:
    def __init__(self):
        self.changed = Condition()
        self.generation = 0
        self.source_generation = 0

    def wait(self, after, timeout):
        with self.changed:
            self.changed.wait_for(lambda: self.generation != after, timeout)

    def wait_for_source(self, after, timeout):
        with self.changed:
            return self.changed.wait_for(lambda: self.source_generation != after, timeout)

    def listen(self, connect, stop):
        while not stop.is_set():
            try:
                with connect() as db:
                    db.commit()
                    db.autocommit = True
                    db.execute('LISTEN demo_delivery_ready')
                    db.execute('LISTEN ' + SOURCE_READY)
                    while not stop.is_set():
                        for notice in db.notifies(timeout=0.25, stop_after=1):
                            with self.changed:
                                if notice.channel == SOURCE_READY:
                                    self.source_generation += 1
                                elif notice.channel == 'demo_delivery_ready':
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
