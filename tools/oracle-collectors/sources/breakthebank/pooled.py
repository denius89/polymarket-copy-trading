from collections import Counter
import threading
from book_engine import GateSkip
import source

def market_key(market):
    return market.venue, market.market, market.token

class Books:
    def __init__(self, gate, deadline):
        self.gate, self.deadline = gate, deadline
        self.workers = {}
        self.frames = Counter()
        self.errors = Counter()

    def sync(self, markets):
        targets = {market_key(m): m for m in markets}
        for key, (thread, stop) in list(self.workers.items()):
            if key not in targets or not thread.is_alive():
                stop.set()
                thread.join(timeout=4)
                if thread.is_alive():
                    raise RuntimeError('book collector did not stop')
                del self.workers[key]
        for key, target in targets.items():
            if key in self.workers:
                continue
            stop = threading.Event()
            thread = threading.Thread(target=self.collect, args=(target, stop), daemon=True)
            self.workers[key] = thread, stop
            thread.start()

    def collect(self, market, stop):
        def feed(frame):
            self.gate.feed_book(frame)
            self.frames[market_key(market)] += 1
        try:
            source.stream_books(market, stop, self.deadline, feed, self.gate.invalidate)
        except (OSError, EOFError, ValueError, KeyError, GateSkip) as error:
            self.errors[type(error).__name__] += 1

    def close(self):
        self.sync([])
