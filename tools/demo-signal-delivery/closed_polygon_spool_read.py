"""Read verified, immutable blocks from the closed collector's private spool."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from resolver import Skip


def read_spool_range(filename, cursor, limit):
    path = Path(filename)
    if not path.is_absolute() or path.parent.stat().st_mode & 0o077 or path.is_symlink():
        raise ValueError('Invalid closed Polygon read spool')
    if not path.is_file():
        raise Skip('POLYGON_SPOOL_STARTING')
    start = int(cursor['checkpoint']['number'])
    expected_hash = cursor['checkpoint']['hash']
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0.1)) as db:
            state = db.execute('SELECT wallet,height,anchor_height,anchor_hash FROM ingress_cursor').fetchone()
            if state is None:
                raise Skip('POLYGON_SPOOL_STARTING')
            wallet, head, anchor, anchor_hash = state
            if start < anchor or start > head or cursor['wallet'] != wallet:
                raise ValueError('Polygon spool checkpoint outside the collector scope')
            if start == anchor:
                if expected_hash != anchor_hash:
                    raise ValueError('Polygon spool anchor changed')
            else:
                row = db.execute('SELECT header FROM ingress_blocks WHERE height=?', (start,)).fetchone()
                if row is None or json.loads(row[0])['hash'] != expected_hash:
                    raise ValueError('Polygon spool checkpoint hash changed')
            rows = db.execute('SELECT height,header,logs FROM ingress_blocks '
                              'WHERE height>? AND height<=? ORDER BY height LIMIT ?', (start, head, limit)).fetchall()
    except sqlite3.OperationalError:
        raise Skip('POLYGON_SPOOL_NOT_READY') from None
    headers, logs = {}, []
    for number, serialized_header, serialized_logs in rows:
        header = json.loads(serialized_header)
        if number != start + len(headers) + 1 or header['parentHash'] != expected_hash:
            raise ValueError('Polygon spool range is not continuous')
        for log in json.loads(serialized_logs):
            if (log['owner'], log['blockNumber'], log['blockHash']) != (wallet, header['number'], header['hash']):
                raise ValueError('Polygon spool contains an event outside the verified block')
            logs.append(log)
        headers[number] = header
        expected_hash = header['hash']
    return ((headers, logs) if headers else None), head
