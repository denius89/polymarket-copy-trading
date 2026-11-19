"""Activate the second Limitless follower while keeping the same shared ledger."""
import json

import backup
import edge
from handover_maker import PACKAGE,handover,under_release_lock

OLD_RUN='903088f3806aeb04'


def render(rollback):
    package=PACKAGE/'ui'
    assets={path.name.encode():path.read_bytes() for path in (package/'assets').iterdir() if path.is_file()}
    return edge.install((package/'index.html').read_bytes(),assets,rollback,
        index_sha='0b67f0dbf9e3371c81586c89b051a43a19f1f7fa1cd74b442a8d399814427625',
        config_sha='71fc37c86be6dc75c7ff8b6ecebb91f13b0439f6c74e7e69de67b7da0e7fbbc1',
        anchor=b'index-BmCGHMCy.js')


def display_ready():
    following=json.loads(backup.FEED.read_text()).get('following')
    return isinstance(following,list) and sorted(row['venue'] for row in following)==['limitless','limitless','polymarket']


if __name__=='__main__':
    under_release_lock(lambda:handover('shadow-paper-e99162d8-app-buy-v2.service','shadow-paper-e99162d8-app-buy-v3.service',
        OLD_RUN,'shared-demo-maker-'+OLD_RUN,5,'shared-demo-follow-'+PACKAGE.name,publish_ui=render,ready=display_ready))
