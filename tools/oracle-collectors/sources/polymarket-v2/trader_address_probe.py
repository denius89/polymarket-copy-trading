from urllib.parse import quote, urlencode
import source

def base_logs(low, high, wallets):
    return source.rpc('eth_getLogs', {'address': sorted(source.FEE_MODULES),
                      'topics': [source.MATCH, None, sorted(source.address_topic(w) for w in wallets)],
                      'fromBlock': hex(max(0, low)), 'toBlock': hex(high)})

def resolve_limitless(log, wallet, token, side, historical):
    history_url = f'{source.LIMITLESS_API}/portfolio/{wallet}/history?' + urlencode({'limit': 30})
    rows = source.json_read(history_url)['data']
    hints = {}
    for row in rows:
        market = row.get('market') or {}
        strategy = row.get('strategy') or ''
        if (row.get('transactionHash', '').lower() == log['transactionHash'].lower()
                and strategy.lower().endswith(side.lower()) and row.get('outcomeIndex') in (0, 1)
                and market.get('slug') and market.get('conditionId')):
            hints[market['slug']] = market
    if not hints:
        # Catalogue lookup happens only after the address-filtered log is captured.
        for page in (1, 2):
            data = source.json_read(f'{source.LIMITLESS_API}/markets/active?' + urlencode({
                'limit': 25, 'page': page, 'tradeType': 'clob'}))
            for market in data['data']:
                tokens = market.get('tokens') or {}
                if token in map(str, tokens.values()) and market.get('slug'):
                    hints[market['slug']] = market
            if hints or page * 25 >= data['totalMarketsCount']:
                break
    if not hints and historical and historical['transaction'].lower() == log['transactionHash'].lower():
        hints[historical['market']] = {'conditionId': historical['condition']}
    matches = []
    for slug, hint in hints.items():
        detail = source.json_read(f'{source.LIMITLESS_API}/markets/{quote(slug, safe="")}')
        venue = detail.get('venue') or {}
        tokens = detail.get('tokens') or {}
        outcome = [name for name in ('yes', 'no') if str(tokens.get(name)) == token]
        if (detail.get('conditionId') == hint.get('conditionId') and len(outcome) == 1
                and str(venue.get('feeModule', '')).lower() == log['address'].lower()
                and venue.get('feeModuleType') == 'COLLATERAL'):
            matches.append((detail, outcome[0]))
    if len(matches) != 1:
        return None, 'MARKET_TOKEN_MAPPING_UNPROVEN'
    return matches[0], None
