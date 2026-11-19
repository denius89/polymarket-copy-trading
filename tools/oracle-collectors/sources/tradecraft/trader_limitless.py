from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlencode
from book_engine import GateSkip
from pooled import market_key
from trader_address_probe import resolve_limitless
import source

REFRESH_S = 90

POLL_S = 2

WARM_SLOTS = 2

def history(wallet):
    url = f'{source.LIMITLESS_API}/portfolio/{wallet}/history?' + urlencode({'limit': 20})
    return source.json_read(url)['data']

def warm_hints(wallets):
    """History discovers subscriptions. It is never admitted as a live signal."""
    choices = {}
    with ThreadPoolExecutor(max_workers=min(4, len(wallets))) as pool:
        jobs = {wallet: pool.submit(history, wallet) for wallet in wallets}
        for wallet, job in jobs.items():
            for row in job.result():
                item = row.get('market') or {}
                when = row.get('blockTimestamp')
                if (not item.get('slug') or not item.get('conditionId')
                        or row.get('outcomeIndex') != 0 or type(when) is not int):
                    continue
                key = item['slug'], item['conditionId']
                best = choices.get(key)
                if best is None or when > best[0]:
                    choices[key] = when, wallet
    return sorted(((when, slug, condition, wallet) for (slug, condition), (when, wallet) in choices.items()),
                  reverse=True)[:8]

class Subscriptions:
    def __init__(self, books):
        self.books = books
        self.warm = {}
        self.hot = None

    def prune(self, now):
        self.warm = {key: entry for key, entry in self.warm.items() if entry[1] > now}
        if self.hot and self.hot[1] <= now:
            self.hot = None

    def sync(self, now):
        self.prune(now)
        active = [entry[0] for entry in self.warm.values()]
        if self.hot:
            active.append(self.hot[0])
        self.books.sync(active)

    def prewarm(self, hints, now):
        self.prune(now)
        if len(self.warm) == WARM_SLOTS:
            return
        for _, slug, condition, wallet in hints:
            if any(m.slug == slug for m, _ in self.warm.values()):
                continue
            detail = source.json_read(f'{source.LIMITLESS_API}/markets/{quote(slug, safe="")}')
            venue = detail.get('venue') or {}
            token = (detail.get('tokens') or {}).get('yes')
            expiry = detail.get('expirationTimestamp')
            module = str(venue.get('feeModule', '')).lower()
            if (detail.get('conditionId') != condition or detail.get('tradeType') != 'clob'
                    or detail.get('expired') is not False or detail.get('status') not in {'CREATED', 'FUNDED'}
                    or not token or type(expiry) is not int or expiry <= now
                    or venue.get('feeModuleType') != 'COLLATERAL' or module not in source.FEE_MODULES):
                continue
            market = source.Market('limitless', condition, str(token), wallet, slug, module)
            self.warm[market_key(market)] = market, expiry
            if len(self.warm) == WARM_SLOTS:
                return

    def known(self, token):
        matches = [m for m, _ in self.warm.values() if m.token == token]
        if self.hot and self.hot[0].token == token:
            matches.append(self.hot[0])
        ids = {(m.market, m.slug) for m in matches}
        return matches[0] if len(ids) == 1 else None

    def follow(self, market, expiry, now):
        if market_key(market) not in self.warm:
            self.hot = market, expiry
        self.sync(now)

def market_for(log, subscriptions, wallet, token):
    known = subscriptions.known(token)
    if known and known.fee_module == log['address'].lower():
        return source.Market('limitless', known.market, token, wallet, known.slug, known.fee_module)
    mapped, reason = resolve_limitless(log, wallet, token, 'BUY', None)
    if mapped is None:
        raise GateSkip(reason)
    detail, outcome = mapped
    if outcome != 'yes':
        raise GateSkip('BOOK_OUTCOME_UNSUPPORTED')
    return source.Market('limitless', detail['conditionId'], token, wallet, detail['slug'],
                         log['address'].lower())

def collect(logs, wallet_set, observed, first_seen, counts):
    grouped = {}
    for log in logs:
        topics = log['topics']
        if (log.get('removed') or len(topics) != 4 or topics[0] != source.MATCH
                or log['address'].lower() not in source.FEE_MODULES):
            continue
        wallet = '0x' + topics[2][-40:].lower()
        if wallet not in wallet_set:
            continue
        key = log['transactionHash'].lower(), topics[1].lower()
        grouped.setdefault(key, []).append((log, wallet))
    for key, items in grouped.items():
        if key in first_seen:
            continue
        first_seen[key] = observed
        if len(items) != 1:
            counts['AMBIGUOUS_MATCH'] += 1
            continue
        log, wallet = items[0]
        values = source.words(log['data'])
        if len(values) != 8 or values[0] != 0 or min(values[2:4]) <= 0:
            counts['OUTSIDE_BUY_SCOPE'] += 1
            continue
        yield log, wallet, str(int(log['topics'][3], 16)), observed
