"""Persist a processed closed Limitless range within witnessed Base finality."""
from collections import deque
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_NB, flock
import json
import os
from pathlib import Path
import re
import stat
from tempfile import NamedTemporaryFile
from threading import Lock
from time import monotonic


def header(value):
    if not isinstance(value, dict):
        raise ValueError("Base witness did not return a block")
    number, digest = value.get("number"), value.get("hash")
    if not isinstance(number, str) or not re.fullmatch(r"0x[0-9a-f]{1,14}", number):
        raise ValueError("Invalid witnessed Base height")
    if not isinstance(digest, str) or not re.fullmatch(r"0x[0-9a-f]{64}", digest):
        raise ValueError("Invalid witnessed Base block hash")
    return int(number,16),digest


class Checkpoint:
    def __init__(self,path,scope,seed,witness,report):
        self.path=path
        self.scope=scope
        self.seed=seed
        self.witness=witness
        self.report=report
        self.height=None
        self.processed=None
        self.digest=None
        self.anchors=deque()
        self.mutex=Lock()
        self.next_attempt=0

    @contextmanager
    def lock(self):
        if not self.path.is_absolute() or self.path.parent.resolve(strict=True)!=self.path.parent:
            raise ValueError("Expected a local immutable state path for Limitless")
        info=self.path.parent.stat()
        if info.st_uid!=os.getuid() or info.st_mode&0o077:
            raise ValueError("Expected a private Limitless state directory")
        fd=os.open(str(self.path)+".lock",os.O_CREAT|os.O_NOFOLLOW|os.O_RDWR,0o600)
        try:
            flock(fd,LOCK_EX|LOCK_NB)
            yield
        finally:
            os.close(fd)

    def agreed_hash(self,height):
        blocks=[header(block) for block in self.witness("eth_getBlockByNumber",hex(height),False)]
        if len(blocks)!=2 or blocks[0]!=blocks[1] or blocks[0][0]!=height:
            raise ValueError("Base witnesses disagree on the cursor")
        return blocks[0][1]

    def finalized(self):
        blocks=[header(block) for block in self.witness("eth_getBlockByNumber","finalized",False)]
        if len(blocks)!=2:
            raise ValueError("Expected two Base finality witnesses")
        return min(number for number,_ in blocks)

    def resume(self,persist_seed=True):
        try:
            descriptor=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        except FileNotFoundError:
            height=self.seed
            digest=None
        else:
            with os.fdopen(descriptor,"rb") as stream:
                info=os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
                    raise ValueError("Expected private Limitless checkpoint data")
                payload=json.loads(stream.read(2049))
            if set(payload)!={"scope","height","hash"} or payload["scope"]!=self.scope:
                raise ValueError("Limitless checkpoint belongs to another session")
            height,digest=payload["height"],payload["hash"]
            if (type(height) is not int or height<self.seed or not isinstance(digest,str)
                    or not re.fullmatch(r"0x[0-9a-f]{64}",digest)):
                raise ValueError("Invalid saved Limitless checkpoint height")
        if self.finalized()<height:
            raise ValueError("Limitless checkpoint is above common Base finality")
        verified=self.agreed_hash(height)
        if digest is not None and verified!=digest:
            raise ValueError("Saved Base checkpoint hash changed")
        if digest is None and persist_seed:
            self.save(height,verified)
        self.height=self.processed=height
        self.digest=verified
        self.report({"stage":"limitless-checkpoint-resumed","scannedThrough":height})
        return height

    def complete(self,low,high,digest):
        with self.mutex:
            if (type(low) is not int or type(high) is not int or low>high or low>self.processed+1
                    or not isinstance(digest,str) or not re.fullmatch(r"0x[0-9a-f]{64}",digest)):
                raise ValueError("The processed Limitless range does not continue the saved source")
            if high>self.processed:
                if len(self.anchors)>=4096:
                    raise ValueError("Limitless checkpoints are not keeping up with Base")
                self.anchors.append((high,digest))
                self.processed=high

    def maintain(self,stop):
        while not stop.wait(4):
            self.flush()
        self.flush(force=True)

    def flush(self,force=False):
        if self.processed is None or self.processed<=self.height or (not force and monotonic()<self.next_attempt):
            return
        self.next_attempt=monotonic()+20
        try:
            final=self.finalized()
            with self.mutex:
                candidate=next((anchor for anchor in reversed(self.anchors) if anchor[0]<=final),None)
            if candidate is None:
                return
            height,seen_hash=candidate
            digest=self.agreed_hash(height)
        except (OSError,ValueError,TypeError,KeyError):
            self.report({"stage":"limitless-checkpoint-witness","status":"waiting"})
            return
        if digest!=seen_hash:
            raise ValueError("The processed Base range changed before finality")
        self.save(height,digest)
        with self.mutex:
            self.height=height
            while self.anchors and self.anchors[0][0]<=height:
                self.anchors.popleft()
        self.report({"stage":"limitless-checkpoint-saved","scannedThrough":height})

    def save(self,height,digest):
        payload=json.dumps({"scope":self.scope,"height":height,"hash":digest})+"\n"
        temporary=None
        try:
            with NamedTemporaryFile(mode="w",dir=self.path.parent,delete=False) as output:
                temporary=Path(output.name)
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary,self.path)
            directory=os.open(self.path.parent,os.O_RDONLY|os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
