"""Single owner for admission, legacy maintenance and Limitless reconciliation."""
from concurrent.futures import ThreadPoolExecutor, wait
import json
from pathlib import Path
import signal
import sys
import threading
import time

from bridge import BridgeRefusal, SharedDemoRuntime
from collectors import run_limitless, run_limitless_finalizer, run_polymarket
from maker_collector import run_makers
import storage

LOCK = threading.Lock()


def report(value):
    with LOCK:
        print(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')),flush=True)


def run(database, feed, owner, epoch, edge_end):
    pause = threading.Event()
    shutdown = threading.Event()
    collector_stop = threading.Event()
    finalizer_stop = threading.Event()
    signal.signal(signal.SIGUSR1, lambda *_: pause.set())
    signal.signal(signal.SIGTERM, lambda *_: shutdown.set())
    admission_end = time.monotonic() + (edge_end - time.time())
    if time.monotonic() >= admission_end:
        raise RuntimeError('authorized application window has expired')
    runtime = SharedDemoRuntime(database, feed, storage, owner, epoch, report=report,
                                enable_second_limitless=True)
    runtime.start()
    try:
        follow=runtime.following()
        jobs=[]
        for entry in follow:
            venue,wallet=entry['venue'],entry['wallet']
            if venue=='polymarket':
                jobs.extend((('polymarket-taker',venue,wallet,run_polymarket),
                             ('polymarket-maker',venue,wallet,run_makers)))
            elif venue=='limitless':
                jobs.append(('limitless-'+str(len(jobs)),venue,wallet,run_limitless))
            else:
                raise RuntimeError('unrecognized configured demo venue')
        if len(jobs)!=4:
            raise RuntimeError('following configuration does not match the approved scope')
    except BaseException:
        runtime.close()
        raise
    report({'stage':'app-writer-ready','epoch':epoch+1,'collectorCount':len(jobs)})
    with ThreadPoolExecutor(max_workers=len(jobs)+1) as pool:
        finalizer = pool.submit(run_limitless_finalizer,runtime.adapter('limitless'),finalizer_stop,report)
        tasks = {label:pool.submit(collector,runtime.adapter(venue),wallet,collector_stop,admission_end,
                                  lambda value,label=label:report({**value,'collector':label}))
                 for label,venue,wallet,collector in jobs}
        admissions_stopped = False
        try:
            while not shutdown.is_set() and time.time() < edge_end:
                for venue in list(tasks):
                    future = tasks[venue]
                    if future.done():
                        try:
                            future.result()
                        except BridgeRefusal as error:
                            if not collector_stop.is_set() or str(error) != 'ADMISSIONS_STOPPED':
                                raise
                        del tasks[venue]
                        report({'stage':'app-collector-ended','venue':venue})
                if not admissions_stopped and (pause.is_set() or not tasks or time.monotonic() >= admission_end):
                    collector_stop.set()
                    runtime.stop_admissions()
                    admissions_stopped = True
                    report({'stage':'app-admissions-stopped','pendingLimitless':len(runtime.pending_limitless())})
                if finalizer.done():
                    finalizer.result()
                    raise RuntimeError('Limitless reconciliation stopped unexpectedly')
                if runtime.closed.is_set():
                    raise RuntimeError('demo writer stopped unexpectedly')
                shutdown.wait(.25)
        finally:
            collector_stop.set()
            if not runtime.closed.is_set():
                try:
                    if not admissions_stopped:
                        runtime.stop_admissions()
                    _,unfinished = wait(tasks.values(),timeout=35)
                    if unfinished:
                        raise RuntimeError('venue collector did not stop within its deadline')
                finally:
                    finalizer_stop.set()
                    try:
                        finalizer.result(timeout=18)
                    finally:
                        snapshot = runtime.snapshot()
                        count = len(runtime.pending_limitless())
                        runtime.close()
                        report({'stage':'app-writer-drained','pendingLimitless':count,'reserved':snapshot['reserved']})
            else:
                finalizer_stop.set()


if __name__ == '__main__':
    db, publication, owner, epoch, cutoff = sys.argv[1:]
    run(Path(db),Path(publication),owner,int(epoch),int(cutoff))
