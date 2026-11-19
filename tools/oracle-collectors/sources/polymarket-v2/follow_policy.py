"""Explicit approved follow scopes; caller input cannot add arbitrary wallets."""
POLY='0xed3bed3eafd729a26cdb20e927b8ed8ca8d251f2'
OLD_LIMITLESS='0x0d6a4c42efe6af0a81632dcfe0e8d1e76d1d4ada'
NEW_LIMITLESS='0x8e86c88ffbacdc802c1fb3f67e4ee8e05ed4dce3'
LABELS={('polymarket',POLY):'0xed3bed…51f2',
        ('limitless',OLD_LIMITLESS):'SharpDownyLarch',
        ('limitless',NEW_LIMITLESS):'0x8e86…dce3'}


def approved_follows(enable_second_limitless=False):
    if type(enable_second_limitless) is not bool:raise ValueError('FOLLOW_FLAG_MUST_BE_BOOLEAN')
    keys=[('polymarket',POLY),('limitless',OLD_LIMITLESS)]
    if enable_second_limitless:keys.append(('limitless',NEW_LIMITLESS))
    return tuple(dict(venue=venue,wallet=wallet,label=LABELS[venue,wallet]) for venue,wallet in keys)


def label(venue,wallet):return LABELS[venue,wallet.lower()]
