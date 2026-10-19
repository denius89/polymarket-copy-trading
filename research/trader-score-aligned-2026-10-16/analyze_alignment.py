"""Frozen three-day diagnostic: no wallet returns, fills or scores inferred.

Dependencies: duckdb==1.4.1. Run after fetch_quotes.py and extract_trades.py.
Final outcome columns in the source are deliberately excluded from analysis.
"""
import hashlib
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent
START, END = 1772323200000, 1772582400000

def rows(c, sql, params=None):
    cur = c.execute(sql, params or [])
    names = [x[0] for x in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]

def main():
    manifest = json.loads((ROOT/'trades-manifest.json').read_text())
    assert len(manifest) == 4, 'All four UTC+8 partitions must finish first'
    quote_manifest=json.loads((ROOT/'quotes-manifest.json').read_text())
    inputs = manifest + quote_manifest
    for entry in inputs:
        p = ROOT / entry['file']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == entry['sha256'], p
    c = duckdb.connect()
    c.execute("SET TimeZone='UTC'")
    c.execute("SET memory_limit='1GB'")
    c.execute('SET threads=4')
    c.read_parquet([str(ROOT/m['file']) for m in quote_manifest
                   if Path(m['file']).name.startswith('date=')], filename=True).create_view('raw_q')
    c.read_parquet([str(ROOT/m['file']) for m in manifest]).create_view('raw_t')
    # Preserve all archive rows; no event IDs exist, so identical rows are not
    # silently treated as duplicate chain events.
    c.execute(f'''CREATE TABLE t AS SELECT row_number() over () AS row_id,
        asset_id,block_timestamp*1000 AS trade_ms,price,taker_direction,maker,taker,
        usdc_amount,fee_usdc,condition_id,
        taker_direction IN ('BUY','SELL') AND isfinite(price) AND price>0 AND price<=1
          AND isfinite(usdc_amount) AND usdc_amount>=0 AS semantics_ok
        FROM raw_t WHERE block_timestamp*1000>={START} AND block_timestamp*1000<{END}''')
    # Coalesce identical BBO values at a timestamp, but preserve conflicts. Do
    # not discard bad quotes before ASOF, which would fall back to an older one.
    c.execute(f'''CREATE TABLE q AS SELECT asset_id,source_ts_ms AS quote_ms,
        min(best_bid) AS bid,min(best_ask) AS ask,
        count(DISTINCT struct_pack(bid:=best_bid,ask:=best_ask)) AS versions,
        min(ingest_ts_ms) AS earliest_ingest_ms,max(ingest_ts_ms) AS latest_ingest_ms,
        count(*) AS source_rows
        FROM raw_q WHERE source_ts_ms>={START-1000} AND source_ts_ms<{END+6000}
        GROUP BY asset_id,source_ts_ms''')
    c.execute('''CREATE TABLE arrivals AS SELECT t.*,lag_ms,trade_ms+lag_ms AS arrival_ms
        FROM t CROSS JOIN (VALUES (500),(2000),(5000)) AS lag(lag_ms)''')
    c.execute('''CREATE TABLE joined AS SELECT a.*,q.quote_ms,q.bid,q.ask,q.versions,
        q.earliest_ingest_ms,q.latest_ingest_ms,
        arrival_ms-quote_ms AS age_ms,
        q.quote_ms IS NOT NULL AND arrival_ms-quote_ms BETWEEN 0 AND 1000 AS fresh,
        isfinite(q.bid) AND isfinite(q.ask) AND q.bid>=0 AND q.ask>=q.bid AND q.ask<=1 AS valid_bbo,
        q.versions=1 AND q.quote_ms<>arrival_ms AS unambiguous_quote,
        CASE WHEN taker_direction='BUY' THEN q.ask-price ELSE price-q.bid END AS adverse
        FROM arrivals a ASOF LEFT JOIN q ON a.asset_id=q.asset_id AND a.arrival_ms>=q.quote_ms''')
    c.execute('''CREATE VIEW eligible AS SELECT *,
        coalesce(semantics_ok AND fresh AND valid_bbo AND unambiguous_quote,false) AS eligible
        FROM joined''')
    c.execute('''CREATE TABLE common AS SELECT row_id FROM eligible GROUP BY row_id
        HAVING count(*)=3 AND bool_and(eligible)''')
    report = dict(
        result_kind='descriptive_provider_quote_diagnostic',
        diagnostic_kind='provider_side_aligned_conditional_quote_displacement_not_execution_or_pnl',
        interval_utc=['2026-03-01T00:00:00Z','2026-03-04T00:00:00Z'],
        model_verdict='comparison_blocked_by_horizon_and_data',
        complete_30_day_outcomes=0,
        selected_token_count=len(manifest[0]['predicate']['asset_ids']),
        scope='StandardBinary archive rows for tokens selected by quote availability, not all Polymarket fills; no maker-wallet reconstruction.',
        quote_partition_ranges=rows(c,'''SELECT filename,count(*) AS rows,
            min(source_ts_ms) AS first_ms,max(source_ts_ms) AS last_ms
            FROM raw_q GROUP BY filename ORDER BY filename'''),
        trades=rows(c,'''SELECT count(*) AS rows,count(DISTINCT asset_id) AS assets,
            count(DISTINCT condition_id) AS conditions,count(DISTINCT taker) AS takers,
            count(DISTINCT maker) AS makers,min(trade_ms) AS first_ms,max(trade_ms) AS last_ms,
            count(*) FILTER (WHERE NOT coalesce(semantics_ok,false)) AS invalid_semantics FROM t''')[0],
        quotes=rows(c,f'''SELECT count(*) AS rows,count(DISTINCT asset_id) AS assets,
            count(*) FILTER (WHERE ingest_ts_ms<source_ts_ms) AS negative_ingest_lag_rows,
            count(*) FILTER (WHERE best_bid IS NULL OR best_ask IS NULL) AS missing_bbo_rows,
            count(*) FILTER (WHERE NOT coalesce(isfinite(best_bid) AND isfinite(best_ask)
              AND best_bid>=0 AND best_ask>=best_bid AND best_ask<=1,false)) AS invalid_bbo_rows
            FROM raw_q WHERE source_ts_ms>={START} AND source_ts_ms<{END}''')[0],
        funnels=rows(c,'''SELECT lag_ms,count(*) AS all_subset_rows,
            count(*) FILTER (WHERE semantics_ok) AS supported_semantics,
            count(*) FILTER (WHERE semantics_ok AND quote_ms IS NOT NULL) AS asof_present,
            count(*) FILTER (WHERE semantics_ok AND fresh) AS fresh,
            count(*) FILTER (WHERE semantics_ok AND fresh AND valid_bbo) AS fresh_valid,
            count(*) FILTER (WHERE eligible) AS eligible,
            count(*) FILTER (WHERE semantics_ok AND fresh AND valid_bbo AND versions>1) AS conflicting_bbo,
            count(*) FILTER (WHERE semantics_ok AND fresh AND valid_bbo AND quote_ms=arrival_ms) AS exact_timestamp_ties,
            count(*) FILTER (WHERE eligible AND earliest_ingest_ms>arrival_ms) AS eligible_ingested_after_arrival,
            count(*) FILTER (WHERE eligible AND latest_ingest_ms>arrival_ms) AS eligible_any_ingested_after_arrival
            FROM eligible GROUP BY lag_ms ORDER BY lag_ms'''),
        caveats=[
            'Block timestamps are settlement time with second precision, not offchain match time; all comparisons are conditional, not measured product arrivals.',
            'Source clock and recorder route are not independently verified. Earliest quote ingestion may be after simulated arrival.',
            'Price-change BBO can include provider fallback; validity tests alone do not prove historical executable quotes.',
            'Conflicting BBO at identical timestamps and exact arrival ties excluded; no event-ID deduplication is possible.',
            'Price change size is not available top depth. No $5 fills, fees, cash balance, PnL or score inferred.',
            'Final market labels and resolution metadata never read into analytical tables.',
        ],
    )
    report['quote_event_types']=rows(c,f'''SELECT event_type,count(*) AS rows
        FROM raw_q WHERE source_ts_ms>={START} AND source_ts_ms<{END} GROUP BY event_type ORDER BY rows DESC''')
    report['bbo_evidence_class']='provider_only_fallback_and_clock_provenance_unverified'
    report['comparisons'] = []
    for cohort, where in [('per_lag','eligible'),('common_all_lags','eligible AND row_id IN (SELECT row_id FROM common)')]:
        data = rows(c,f'''SELECT lag_ms,taker_direction,count(*) AS rows,
            count(DISTINCT asset_id) AS assets,count(DISTINCT condition_id) AS conditions,
            quantile_cont(100*adverse,0.1) AS adverse_cents_p10,
            quantile_cont(100*adverse,0.5) AS adverse_cents_median,
            quantile_cont(100*adverse,0.9) AS adverse_cents_p90,
            quantile_cont(10000*adverse/price,0.5) AS adverse_bps_median,
            quantile_cont(100*(ask-bid),0.5) AS spread_cents_median,
            quantile_cont(age_ms,0.5) AS age_ms_median
            FROM eligible WHERE {where} GROUP BY lag_ms,taker_direction ORDER BY lag_ms,taker_direction''')
        report['comparisons'].append(dict(cohort=cohort,groups=data))
    report['common_complete_case_rows'] = c.execute('SELECT count(*) FROM common').fetchone()[0]
    # Added after observing ingestion gaps: a labelled secondary audit only.
    # This rejects a source-time-selected quote not yet recorded. It does not
    # reconstruct a full recorder-time feed or change the frozen primary test.
    report['secondary_recorded_by_arrival_audit'] = dict(
        preregistered=False,
        method='Subset of primary diagnostic; require all identical BBO records at selected source timestamp ingested by arrival. No fallback to an older recorded quote.',
        groups=rows(c,'''SELECT lag_ms,count(*) FILTER (WHERE eligible) AS primary_diagnostic_rows,
          count(*) FILTER (WHERE eligible AND latest_ingest_ms<=arrival_ms) AS recorded_by_arrival_rows
          FROM eligible GROUP BY lag_ms ORDER BY lag_ms'''),
        common_all_lags_rows=c.execute('''SELECT count(*) FROM (SELECT row_id FROM eligible GROUP BY row_id
          HAVING count(*)=3 AND bool_and(eligible AND latest_ingest_ms<=arrival_ms))''').fetchone()[0])
    # Descriptive signed gross trade legs as supplied by the archive: these
    # are NOT independently verified cash movements or a portfolio ledger.
    c.execute(f'''COPY (SELECT taker,asset_id,condition_id,taker_direction,
        count(*) AS source_rows,sum(usdc_amount) AS archive_gross_notional_usd,
        sum(CASE WHEN taker_direction='BUY' THEN -usdc_amount ELSE usdc_amount END) AS provider_normalized_signed_notional_proxy_usd,
        sum(fee_usdc) FILTER (WHERE isfinite(fee_usdc) AND fee_usdc>=0) AS archive_fee_field_usd,
        count(*) FILTER (WHERE NOT coalesce(isfinite(fee_usdc) AND fee_usdc>=0,false)) AS unknown_or_invalid_fee_rows,
        'provider_normalized_trade_legs_unreconciled' AS evidence_class,
        'archive_taker_only_subset' AS row_kind
        FROM t WHERE semantics_ok GROUP BY ALL)
        TO '{ROOT/'partial-trade-legs.csv'}' (HEADER,DELIMITER ',')''')
    report['partial_trade_legs'] = rows(c,'''SELECT taker_direction,count(*) AS source_rows,
        sum(usdc_amount) AS archive_gross_notional_usd,
        sum(fee_usdc) FILTER (WHERE isfinite(fee_usdc) AND fee_usdc>=0) AS archive_fee_field_usd,
        count(*) FILTER (WHERE NOT coalesce(isfinite(fee_usdc) AND fee_usdc>=0,false)) AS unknown_or_invalid_fee_rows
        FROM t WHERE semantics_ok GROUP BY taker_direction ORDER BY taker_direction''')
    c.execute(f'''COPY (SELECT lag_ms,asset_id,condition_id,taker_direction,
        count(*) AS source_rows,count(*) FILTER (WHERE eligible) AS eligible_rows,
        quantile_cont(100*adverse,0.5) FILTER (WHERE eligible) AS adverse_cents_median
        FROM eligible GROUP BY ALL) TO '{ROOT/'coverage-by-token.csv'}' (HEADER,DELIMITER ',')''')
    c.execute(f'''COPY (SELECT lag_ms,asset_id,condition_id,taker_direction,trade_ms,
        price AS provider_trade_price,arrival_ms,quote_ms,age_ms,bid,ask,versions,
        earliest_ingest_ms,eligible,100*adverse AS adverse_cents
        FROM eligible QUALIFY row_number() OVER (PARTITION BY lag_ms,taker_direction,eligible
          ORDER BY trade_ms,asset_id,price,maker,taker,row_id)=1
        ORDER BY lag_ms,taker_direction,eligible)
        TO '{ROOT/'diagnostic-examples.csv'}' (HEADER,DELIMITER ',')''')
    # Clock uncertainty sensitivity is declared in protocol, not a tuned lag.
    report['clock_sensitivity'] = []
    for shift in [-1000,1000]:
        report['clock_sensitivity'].append(dict(source_clock_shift_ms=shift,groups=rows(c,f'''
            WITH shifted AS (SELECT *,quote_ms+{shift} AS shifted_ms FROM q),
            j AS (SELECT a.*,s.bid,s.ask,s.versions,s.shifted_ms,
               arrival_ms-shifted_ms AS age FROM arrivals a ASOF LEFT JOIN shifted s
               ON a.asset_id=s.asset_id AND a.arrival_ms>=s.shifted_ms)
            , e AS (SELECT *,coalesce(semantics_ok AND age BETWEEN 0 AND 1000
              AND versions=1 AND shifted_ms<>arrival_ms AND isfinite(bid) AND isfinite(ask)
              AND bid>=0 AND ask>=bid AND ask<=1,false) AS ok,
              CASE WHEN taker_direction='BUY' THEN ask-price ELSE price-bid END AS adverse
              FROM j)
            SELECT lag_ms,taker_direction,count(*) AS denominator_rows,
              count(*) FILTER (WHERE ok) AS eligible_rows,
              quantile_cont(100*adverse,0.5) FILTER (WHERE ok) AS adverse_cents_median,
              quantile_cont(100*adverse,0.1) FILTER (WHERE ok) AS adverse_cents_p10,
              quantile_cont(100*adverse,0.9) FILTER (WHERE ok) AS adverse_cents_p90
            FROM e GROUP BY lag_ms,taker_direction ORDER BY lag_ms,taker_direction''')))
    report['input_manifest_files']=['quotes-manifest.json','trades-manifest.json']
    report['partial_trade_legs_warning']='Signed notional proxy, not wallet money movements. Fee source field is not verified taker cash expense; BUY fees can be tokens.'
    assert report['trades']['rows']==sum(m['rows'] for m in manifest)
    assert len(report['funnels'])==3
    for funnel in report['funnels']:
        counts=[funnel[k] for k in ['all_subset_rows','supported_semantics','asof_present','fresh','fresh_valid','eligible']]
        assert counts==sorted(counts,reverse=True), counts
        assert report['common_complete_case_rows']<=funnel['eligible']
    common_groups=report['comparisons'][1]['groups']
    for lag in [500,2000,5000]:
        assert sum(x['rows'] for x in common_groups if x['lag_ms']==lag)==report['common_complete_case_rows']
    (ROOT/'alignment-results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ['trades','quotes','funnels','common_complete_case_rows','comparisons','partial_trade_legs']},indent=2))

if __name__ == '__main__':
    main()
