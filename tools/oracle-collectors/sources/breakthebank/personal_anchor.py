"""Capture the public finalized-block proof needed for a personal enrollment."""
import argparse
import base64
import os
from pathlib import Path
from time import monotonic

from personal_range import checkpoint, header, utc_ms, wire_time
from resolver import canonical, sha, uint
from rtds_operator import BoundedRPC, RPC


def capture():
    rpc = BoundedRPC()
    deadline = monotonic() + 6

    def read(method, params):
        return rpc(method, params, deadline - monotonic())

    chain_raw = read('eth_chainId', [])
    if uint(chain_raw) != 137:
        raise ValueError('Unexpected chain')
    finalized_raw = read('eth_getBlockByNumber', ['finalized', False])
    observed = wire_time(utc_ms())
    finalized = header(finalized_raw)
    canonical_raw = read('eth_getBlockByNumber', [hex(int(finalized['number'])), False])
    if header(canonical_raw) != finalized:
        raise ValueError('Finalized block does not match canonical inclusion')
    evidence = dict(endpoint=RPC, observedAt=observed, chainIdResult=chain_raw,
                    finalizedResult=finalized_raw, canonicalResult=canonical_raw)
    proof = dict(chainId=137, method='eth_getBlockByNumber', tag='finalized',
                 observedAt=observed, finalized=checkpoint(finalized), canonicalHash=finalized['hash'],
                 evidenceRef='polygon-finalized:sha256:' + sha(evidence))
    return proof, evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('evidence_path', type=Path)
    args = parser.parse_args()
    proof, evidence = capture()
    fd = os.open(args.evidence_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as output:
        output.write(canonical(dict(proof=proof, evidence=evidence)) + '\n')
    print(base64.b64encode(canonical(proof).encode()).decode())


if __name__ == '__main__':
    main()
