# Audit 81 · User UI changes · 6 October 2026

Scope: section 4.2 of document 81. Only user pages EN mobile29:2, RU mobile33:2, EN desktop186:2, RU desktop205:2 were edited. No admin, fixture, application/API implementation, persistence, STATE or ROADMAP changes by this agent.

IDs BL-* below belong to audit81, not the differently numbered open-question registry in MVP_BUSINESS_LOGIC.

## Changes

- BL01: active demo report and copying history explicitly say **Historical limit compliance is unverified / Соблюдение исторических лимитов не подтверждено**. Missing effective policy history means current30 does not prove historical compliance. No invented limit was introduced.
- BL02: all12 messages of ticket01 were rewritten from audit81-ticket01-messages.json, including UTC times. They now describe order-closed-04-buy: purchase2.40 plus0.01 test expense, fully filled10shares; sale2.20 minus0.01 expense; net2.19, result−0.22, no remaining reserve. Ticket remains separate from operation status.
- BL03: catalogue card drawdown values and sorted-catalogue values now show —. Hidden inherited profile summary text was aligned to unverified drawdown, matching visible profile metrics. Catalogue explanation says period evidence is missing. Existing copy-quality text already states insufficient data / no calculated rating.
- BL06: unknown order retains $1.01 reserve; new risk-increasing buys are explicitly blocked pending reconciliation, change/cancel unavailable, no blind resubmission. Visible home warning distinguishes an active session from blocked new buys; available balance remains $180.38.
- BL07: change-order explanation distinguishes cancellation of remaining quantity from a separate new order after reconciliation. Pending copy no longer promises positions/funds cannot change: confirmed fills may arrive while cancellation is pending.
- BL08: manual action concerns shares of the selected Momentum Fox copy, with no automatic sale. Pending orders/reserves need reconciliation; ownership accounting and re-entry remain decisions, rather than a claimed implemented isolation mechanism.
- BL10: global rules are a template for new setups. Local settings show Before20perposition/30daily → selected values below for new signals; existing reserve persists. Mandatory ceilings/global-local combination are explicitly unresolved, not inferred new limits.
- BL13: existing Oct6 email gate preserves fixed/percentage review intent; confirmation returns to review, launch requires another explicit click. No automatic trade after login or real email delivery is claimed.
- BL14: ticket labels aligned with Sent/Waiting for support/Waiting for your reply/Resolved/Closed; ticket status does not indicate order completion.
- BL15: referral note says service program is separate from venue programs, no demo accrual, audience eligibility needs a decision. Existing25% of actually received service fees,24months,7days,$25monthly terms retained.

## Main screen IDs

| Version | Catalogue | Thread | Unknown order | Change order | Manual | Limits | Report | Copying history |
|---|---|---|---|---|---|---|---|---|
| EN mobile |905:1788|905:9039|905:8733|951:9710|951:9792|965:18165|905:8529|949:9348|
| RU mobile |888:1734|888:2625|888:2328|951:4607|951:4689|965:4984|888:2130|949:4439|
| EN desktop |905:9735|905:10329|905:10131|951:17686|951:17766|965:18478|1753:7561|1753:7649|
| RU desktop |905:9096|905:9690|905:9492|951:13702|951:13782|965:18321|905:9360|949:13217|

Global limits965:18122/4941/18433/18276. Referral393:58/502 and396:3/529.
Canonical launcher, review, email and fresh/active routes from Oct6 were retained.

## Mutation evidence

Editable text/component instances were retained. Text fonts loaded from each existing node before edit; no screenshot fills/new raster content imported.

| Page | Recorded text mutations (before referral notes) |
|---|---|
| 29:2 | 69 |
| 33:2 | 69 |
| 186:2 | 125 |
| 205:2 | 121 |

## Boundaries

The demo has one active session. Blocking scope across live accounts and authority for resuming after reconciliation are not specified by this UI pass. Mandatory ceilings, manual-lot accounting, durable operations, two-tab behavior, idempotency, send_unknown recovery, actual auth/input validation and real account readiness remain implementation/product dependencies. Static prototype variables do not prove persistence across reload/login.

BL03 fixture confirmedness metadata is maintained by business agent. Synthetic historical numbers retained in source data must not be treated as verified comparison inputs. This UI pass does not alter runtime filtering functions.

## Visual QA

Completed visual inspection of 14 representative screens: four catalogues, four ticket threads, EN mobile/RU desktop limits, EN mobile/RU desktop reports, EN mobile/RU desktop unknown orders. After the final BL06 wording, all four home screens and RU desktop unknown-order detail were rendered again: no new clipping or overlap. Thread lower messages were checked structurally against the 12-message source; screenshot viewports show only the first part of the scroll. Existing editable layouts and fonts were retained.

Local evidence, also inspected by root:

- [RU catalogue](audit81-ru-catalog.png)
- [RU ticket thread](audit81-ru-thread.png)

This is a visual/text/prototype-state pass, not proof of real execution, persistence, backend readiness or delivery.


## Drawdown filter and binding verification

The hidden desktop metric group still contained a drawdown ≤5% choice. All 15 EN and 9 RU desktop copies were made unavailable: descendant reactions removed, label replaced with Drawdown unavailable / Просадка недоступна, opacity 0.55; draft and applied drawdown variables set false in every mode. Disabled groups: EN1072:36810,1072:36916,1078:5995,1072:37233,1072:37339,1078:6209,1839:54207,1839:54313,1839:54422,1853:7615,1853:7721,1853:7830,1853:8114,1853:8220,1853:8329; RU1072:36381,1579:8294,1839:52580,1854:9140,1854:9246,1854:9355,1854:9655,1854:9761,1854:9870. Existing sort options are PnL/activity/original order; no verified drawdown ranking is offered.

152 changed card metric text nodes were checked across four pages: no characters-variable binding can restore a percentage. Fixture confirmedness metadata remains the business agent’s responsibility.

Final BL06 visible home warning text IDs: EN mobile1036:23874, RU mobile1036:21869, EN desktop1036:22904, RU desktop1035:19785. Available-balance captions EN desktopI1036:22826;1012:51 / RU desktopI1035:19727;1012:51 now show the same block. The four order detail IDs remain in the table above.
