"""Polymarket marketable-order delay using the published Gamma and CLOB fields."""

GAMMA_EVIDENCE = 'https://docs.polymarket.com/market-data/market-details'
CLOB_EVIDENCE = 'https://docs.polymarket.com/api-reference/markets/get-clob-market-info'


class MarketParameterError(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def delay_for_market(gamma, clob):
    seconds = gamma.get('secondsDelay')
    taker_delay = clob.get('itode', False)
    if type(taker_delay) is not bool or (seconds is not None and (type(seconds) is not int or not 0 <= seconds <= 30)):
        raise MarketParameterError('MARKET_EXECUTION_DELAY_UNPROVEN')
    if seconds and taker_delay:
        raise MarketParameterError('MARKET_EXECUTION_DELAY_COMPOSITION_UNPROVEN')
    if seconds:
        return seconds * 1000, GAMMA_EVIDENCE
    return (250 if taker_delay else 0), CLOB_EVIDENCE
