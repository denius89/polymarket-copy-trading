from handover_maker import PACKAGE,handover,under_release_lock
from handover_follow import display_ready
if __name__=='__main__':
    under_release_lock(lambda:handover('shadow-paper-e99162d8-app-buy-v3.service','shadow-paper-e99162d8-app-buy-v4.service','b9ffa3c7f514ece5','shared-demo-follow-b9ffa3c7f514ece5',7,'shared-demo-reconnect-'+PACKAGE.name,ready=display_ready))
