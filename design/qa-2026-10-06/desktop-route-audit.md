# Desktop route audit · 6 October 2026

File: `lxPP2um7FvIbt02K8eeH4T`. Pages EN `186:2`, RU `205:2`.

## Official entries

| Version | Launcher (two explicit routes) | First overview | Isolated first catalogue | Isolated first trader profile | Active home |
|---|---|---|---|---|---|
| Desktop RU | 584:265 | 955:3790 | 1839:52340 | 1839:52618 | 905:9074 |
| Desktop EN | 584:225 | 955:18385 | 1839:53961 | 1839:54460 | 905:9713 |

Present links:

- [Desktop RU](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=584-265&starting-point-node-id=584%3A265)
- [Desktop EN](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=584-225&starting-point-node-id=584%3A225)

Each launcher contains **First launch / Первый запуск** and **Active demo / Активное демо**. The first action explicitly sets session stage to `before`; the active action sets `active`. Direct legacy active-home entries also initialize `active` and the active balance strings, eliminating reliance on an unset variable.

## Main first-run route

| Step | RU | EN |
|---|---|---|
| Overview | 955:3790 | 955:18385 |
| Select prepared trader | 1839:52340 | 1839:53961 |
| Trader profile | 1839:52618 | 1839:54460 |
| Fixed setup | 949:13057 | 949:16861 |
| Fixed review | 949:13097 | 1616:6998 |
| Percentage setup | 1707:34154 | 1709:6862 |
| Percentage review | 1707:34245 | 1709:6972 |
| Percentage edit | 1726:34196 | 1726:6956 |
| Email entry before launch | 1854:8894 | 1853:7369 |
| Email sample verification | 1854:9409 | 1853:7868 |
| Starting | 949:13137 | 1753:7613 |
| Fresh home | 949:13177 | 949:16981 |
| Fresh funds | 955:3652 | 955:18247 |
| Fresh positions | 955:3698 | 955:18293 |
| Fresh events | 955:3744 | 955:18339 |
| Fresh orders | 1396:31127 | 1396:20057 |

The cloned catalogue/profile preserve editable design-system instances, Inter fonts, variables, and vector layers. No flattened screenshot content was imported. The first-run catalogue intentionally shows **one prepared trader (Momentum Fox)**, and the first-run profile shows **30 days**; the prepared active catalogue and profile retain their existing full content.

First-run headers now display **200.00**. The inherited prototype balance binding overrode the initial text-property update; it was removed on these specific text instances before applying the fresh balance. Historical “My copies” blocks are hidden on the first-run profiles. First-run header help/notifications/profile icons are hidden to prevent entry into prepared historical account screens. Sidebar routes point to first-run/fresh states, not the active dataset. The percent-mode switch links were restored after route isolation.

The fresh-session explicit prepared-example action is the only deliberate route from a fresh session to active history.

## Confirmed active-route repairs

Root's manual Present check found EN sidebar Events and header balance leading to fresh states. These were repaired on the active main screens and detail views:

- Events: EN `905:9845`, RU `905:9206`.
- Header balance/funds: EN `905:9867`, RU `905:9228`.
- Active Home/Traders/Positions sidebar destinations are now explicit active targets.
- EN My profile `905:9977` now exposes component buttons to Report `1753:7561`, Copying history `1753:7649`, Markets `1753:7689`. New button IDs: `1839:57491`, `1839:57494`, `1839:57497`.
- Launcher preview matches the active fixture: total 209.77, available 180.38, positions 23.60, reserve 5.79.

Root reported manual EN Present passes for Events, Funds, Profile → Report → Back, Copying history, and Markets after these fixes. Earlier RU active navigation was manually passed by root.

## Orders example separated from current ledger

The $20 order with $8 filled/$12 reserved is a teaching example, not part of the fixture's 41 current orders.

- RU row `1746:12784` moved outside Data list `1037:23151`, labelled “Учебный пример частичного исполнения”; count `908:3215` restored to 41.
- EN row `1746:23777` moved outside Data list `1037:31315`, renamed as a separate learning example; count `1037:31313` restored to 41.
- Existing active balance/reserve totals were retained.

## Evidence and remaining checks

Composition screenshots inspected after repairs: both launchers, both first catalogues/profiles, both fresh homes, EN My profile. Editable-layer readback: RU catalogue 52 TEXT/180 INSTANCE; RU profile 62 TEXT/33 INSTANCE; EN catalogue 80 TEXT/283 INSTANCE; EN profile 108 TEXT/63 INSTANCE; all reported Inter and no IMAGE-filled nodes. Counts include hidden inherited legacy layers.

A complete all-descendant reaction dump was abandoned after timeout; this is not evidence that every edge in the entire file was checked. Focused routes were extracted and repaired; final Present walkthrough is performed by root.

Root reported manual percentage launch for EN to empty `949:16981` with 200, and RU percentage review with 200. The absent EN fresh sidebar labels were repaired by replacing affected instances with existing master instances. Final screenshot of `949:16981` shows four readable labels (Home/Traders/Positions/Events) and $200.00; its master header is `1850:11805`. RU fresh/profile and EN first profile headers/sidebars were also replaced with clean component instances. RU absolute layout placement was explicitly corrected. Root manually passed the RU fixed email branch: review → email entry → verification → same review → launching.

First-run catalogue is intentionally a prepared selection, not a fully functioning search/filter implementation. Unsupported filter/sort controls are hidden in this first-run slice. Full catalogue controls remain in the active route. The first-run search field is a visual sample; selection uses the prepared trader.


## Email gate and preservation of settings

Guest launcher sets `Review/Authenticated` (`VariableID:830:3`) false. Active launcher and legacy active home set it true. Fixed/percentage review Start sends an unauthenticated user to the sample email flow. Verification sets authentication true and returns to the same fixed or percentage review using session stage `auth-fixed`/`auth-percent`. Starting still requires a separate review action. Back to review does not authenticate.

RU fixed actor `949:13345`, percentage actor `1707:34258`; EN fixed `1616:7028`, percentage `1709:7002`. RU existing setup eligibility is retained after the authentication check. A Figma conditional fallback initially swallowed the appended email block; it was fixed by placing unauthenticated first. The retained variable `Explore/RU/Fix/setup/can-launch` (`VariableID:954:6211`) is launch eligibility, not an explicit risk-consent checkbox.

Both email frames state explicitly that no email is sent; `you@example.com` and verification are static prototype samples. Confirm label is “Подтвердить и продолжить” / “Confirm and continue”. No working authentication service or input validation is claimed.

## Final fresh-navigation parity

Final composition screenshots pass both fresh homes: four readable nav labels at top, consistent 200 balance. Fresh home has an AFTER_TIMEOUT 0.01 initialization of `Review/SessionStage=empty`. Empty-screen Home routes preserve the fresh home after launch, while pre-launch empty previews return to first overview. EN affected visible navigation used `Recovery/Nav/home`, so both Recovery and legacy Home actors were repaired. RU equivalents were repaired on funds/positions/events/orders. This closes the percentage path losing fresh-session state. EN auth master headers are `1867:16404` / `1867:16432`; RU email label was widened to one line.
