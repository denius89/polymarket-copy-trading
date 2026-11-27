"""Bounded, run-local writer turns for a disposable single-host Polygon demo."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
from threading import local
from time import monotonic, sleep

from resolver import Skip


_thread = local()


@contextmanager
def shared_write_turn(*, wait_seconds=0.6):
    filename = os.environ.get('CCT_CLOSED_POLYGON_WRITE_TURN')
    if not filename:
        yield
        return
    if getattr(_thread, 'filename', None) == filename:
        yield
        return
    path = Path(filename)
    if not path.is_absolute() or path.parent.stat().st_mode & 0o077:
        raise ValueError('Invalid path for closed Polygon writer turns')
    fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Invalid file for closed Polygon writer turns')
        deadline = monotonic() + wait_seconds
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise Skip('POLYGON_WRITER_TURN_BUSY')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                sleep(min(remaining, .01))
        _thread.filename = filename
        try:
            yield
        finally:
            del _thread.filename
    finally:
        os.close(fd)
