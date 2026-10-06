# Mobile route audit · 2026-10-06

Scope: Figma file `lxPP2um7FvIbt02K8eeH4T`, mobile RU page `33:2` and EN page `29:2`. Independent structural audit and repairs; **manual Present acceptance is performed by the root agent and is not claimed here**.

## Canonical launchers

| Version | Launcher | First route | Prepared active route |
|---|---|---|---|
| Mobile RU | 1839:57824 | stories 333:533 → isolated catalog 1839:31252 | 888:1701 |
| Mobile EN | 1839:57862 | stories 333:65 → isolated catalog 1839:45683 | 905:1754 |

Both launchers are the first flow starting point on their page. The first button initializes `SessionStage=before`, available funds $200 and false copying-history flags. The second initializes `SessionStage=active`, available funds $180.38 and prepared-copy flags. They are explicitly independent scenarios.

## First route repairs

The former stories CTA opened an active catalog containing $180.38 and six notifications. Created isolated catalog and five existing trader-period screen clones per language, preserving component instances, editable text, variables and Inter fonts.

| Screen | RU | EN |
|---|---|---|
| Catalog | 1839:31252 | 1839:45683 |
| Trader 24h | 1839:32075 | 1839:46507 |
| Trader 7d | 1839:32271 | 1839:46703 |
| Trader 30d | 1839:32467 | 1839:46899 |
| Trader 90d | 1839:32656 | 1839:47088 |
| Trader all time | 1839:32838 | 1839:47270 |
| Fixed setup | 949:4275 | 949:9184 |
| Fixed review | 949:4316 | 949:9225 |
| Manual settings | 1839:55976 | 1839:56727 |
| Percent setup | 1839:56094 | 1839:56848 |
| Percent review | 1839:56218 | 1839:56972 |
| Launch timer | 949:4357 | 949:9266 |
| Newly launched empty session | 949:4398 | 949:9307 |
| Empty funds | 954:4815 | 954:18960 |
| Empty positions | 954:4862 | 954:19007 |
| Empty events | 954:4909 | 954:19054 |
| Empty orders | 1396:20216 | 1396:19969 |

- Stories CTA, first entry and before-session actions now lead to isolated catalog and profiles.
- Nav stays on the same language/device. Home from first-route screens chooses the empty session when `SessionStage=empty`; otherwise it returns to the before-session home.
- Existing launch timer already sets `SessionStage=empty`, available funds $200, and opens the new empty session; retained this behavior.
- First and empty screens show $200, hide six-unread badges, and display no copying history rather than 14 historical copied positions.
- Empty orders had direct routes into active positions and catalog; repaired to isolated catalog and empty positions/events/funds.
- Clarified settings label “Демо-бюджет” / “Demo budget”.
- Collapsed the now-empty catalogue toolbar and profile Options rows. Catalog title → scenario caption and profile Configure → Back now use the existing 16px spacing in both languages. Final catalog screenshots: `mobile-first-catalog-ru.png`, `mobile-first-catalog-en.png`.

## Active demo repairs

- RU orders `888:1866` and EN orders `905:1924` contained an added $20/$8 partial-fill illustration counted as a real ledger item, contradicting reserve totals in the prepared demo.
- Converted illustration rows `1746:3879` / `1746:16671` into explicit scenario links (“Пример: частичное исполнение →” / “Example: partial fill →”), with no ledger amount/status and a compact 56px height. The illustration remains accessible.
- Result labels `891:2761` / `906:10206` now show 41 ledger orders.
- EN Help “About demo” action `906:11359` now has 150×48 bounds and a one-line label, fixing its clipped second line.

## Evidence and limits

Structural audit of the 18 main first-route frames per language found only intentional outside routes: education stories, explicit prepared-example CTA and the fresh-orders screen. The latter was inspected and repaired separately. Catalog and trader profile screenshots in both languages and both launcher screenshots passed visual review; font family is Inter.

First-route header help/profile/notification controls and unsupported profile label-edit / historical-simulation actions are hidden in the dedicated first slice to prevent entering prepared account data. They remain available in the active demo. The first catalog explicitly identifies Momentum Fox as the supported first-entry scenario; other trader cards, search, filter and sort controls are hidden there. The full active catalog remains unchanged. The prototype does not simulate arbitrary text entry or execute real trades. The explicit prepared-example CTA in the empty session is the only deliberate handoff to historical demo data.

No claim of manual Present success is made by this audit. Root acceptance must cover both routes, fixed/percent settings, return from empty funds/positions/events/orders and direct launcher links.

## Email gate required by ADR-0010 / ADR-0012

Guest launcher now initializes `Review/Authenticated` (`VariableID:830:3`) to false; active demo initializes it to true. Guest setup Save and review Start enter an illustrated email branch. The branch explicitly says no email is sent and uses `you@example.com` / `123456`. Confirmation sets authenticated=true and returns to the matching review; existing risk-acceptance guards and new-empty launch remain intact.

| Route | Email entry | Confirmation | Review return |
|---|---|---|---|
| RU fixed | 1853:38155 | 1853:38176 | 949:4316 |
| RU percent | 1853:38217 | 1853:38238 | 1839:56218 |
| EN fixed | 1853:38027 | 1853:38048 | 949:9225 |
| EN percent | 1853:38089 | 1853:38110 | 1839:56972 |

Confirmation action labels now read “Подтвердить и продолжить” / “Confirm and continue”; entry actions read “Показать пример кода” / “Show sample code”. Redundant resend/error demonstration blocks are hidden in this minimal branch. Back returns to the appropriate review or email entry. Screenshot review confirmed readable sample-email explanation, and fresh-session canvas screenshots retain shadow and $200 headers in both languages. Manual Present verification remains with root.
