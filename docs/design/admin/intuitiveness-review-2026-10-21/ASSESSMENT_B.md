# Assessment B · SHADOW admin intuition · 2026-10-21

Independent read-only review. Repo HEAD e2dcea910b92d49bbf783374e33ba4f5e288c17e; git status clean at end. Figma file lxPP2um7FvIbt02K8eeH4T, Admin RU+EN page 1981:29. Read current project context, operating rules, financial UX skill, critique B instructions, applicable AGENTS, current ROADMAP/PROJECT_STATE/README. No A or parent detector findings consulted. No source/Figma/settings edits.

## Evidence and coverage

Own temporary IAB tab created from requested RU entry 2960:55007. Initial loading completed; browser inspection was available. Prototype controls were used through observed accessibility labels; screenshots visually confirmed start state. Screenreader settings were not changed. AX output initially said support disabled; later Figma exposed prototype labels. This does not prove implemented accessibility.

Eight card-index frames visually inspected with Figma get_screenshot: 1982:37788 users, 1982:37844 user card, 2185:22038 support ticket, 2187:23231 status change, 2414:117985 unknown-result incident, 3485:73706 closure blocked, 3326:72674 Nora operations personal profile, 3069:63938 support-role permissions. Screenshots of profiles are default/direct-entry fixtures, while browser profile had dynamic return context; do not confuse these states.

Observed browser routes:
- 2960:55007 feedback -> My profile -> 3326:72674 -> Back to work -> exact 2960:55007.
- New direct prototype entry to 1982:37788 users -> Demo Atlas -> 1982:37844 -> To list -> exact 1982:37788.
- Users sidebar Support -> 2185:21070 support queue -> TKT-1042 -> 2185:22038 -> Change status -> 2187:23231 -> Waiting for customer -> 2187:23342.
- Incidents sidebar -> 2414:117179 -> INC-DEMO-03 -> 2414:117985 -> Take in work -> 2414:118177 -> My profile -> 3182:78753 -> Back to work -> exact 2414:118177.

## Findings

### P1 · Changing status fabricates a sent reply in the observed prototype route
Source ticket 2185:22038 showed two messages (user MSG-1042-A, Nora MSG-1042-B). I did not type or send any reply. Selecting Change status (2187:23231), then Waiting for customer, opened 2187:23342 with a new Oleg reply MSG-1042-C marked Sent at 10:20, explaining a purchase limit. This directly contradicts the status form's instruction that sending state is separate from ticket status. A trainee can infer that changing status sends a reply or that work was completed without their action. Preserve conversation snapshot across status-only changes; show status feedback independently. This is a design/prototype state defect, not evidence of real message transmission.

### P1 · A normal section navigation silently replaces the acting employee
At 1982:37788/1982:37844, header was Working space / owner. Clicking the existing Support sidebar action opened 2185:21070 with Oleg Smirnov STAFF-206 and a completely different role menu. No explicit role-demo choice or handoff explains why the actor changed. A colleague walking this as one workflow may misread access loss as their own restrictions or believe ordinary menu navigation changes their account/role. Use an explicit demo persona/context switch, or keep the acting persona constant for navigation. Does not show actual authorization weakness.

### P2 · Empty-result fixture looks like an operational command
1982:37788 has a button/link literally No results immediately below two visible users, above Search and selection. The main copy says there are two users without filtering. A new employee may read No results as current search feedback or as an action to clear results. In support, equivalent fixture labels explicitly say Example empty queue. Mark user-list fixture Example: no matches and group it with demo scenarios; keep Search and selection with the list context.

### P2 · Personal role description does not answer what the employee may do
3326:72674 and browser 3182:78753 contain Rights = Operational work and support, with Viewing own powers, without changing assignment. This appears as static table text with no detail link in the observed AX state. Unlike owner editor 3069:63938, the personal profile does not enumerate venue/environment/actions/scope/expiry. Employee can understand they cannot edit access, but cannot check whether e.g. changing status or viewing a client is included. Provide a read-only My access detail reachable from the rights row, showing granted actions and scope. No actual rights tested.

## Strengths and secondary observations
- Nora profile and Oleg profile both display an explicit return destination and return to the exact originating working screen; incident's In work state survived this excursion.
- Incident 2414:117985 prominently says that incident status cannot mark an operation successful or release a reserve. Browser Take in work changes case status, adds an assignment history row, and leaves this warning visible. Blocked-closure screenshot 3485:73706 retains known execution $12, evidence ID, unresolved discrepancy and reserve restriction, with recovery links.
- Ticket separates public reply from internal note, identifies customer and session, labels message receipt/sending, offers history and queue return. Status form is concise (three choices plus return), but currently omits ticket ID/current status from its local content; P2 improvement to reduce memory across the dedicated screen.
- The role editor 3069:63938 distinguishes a role draft from granted access, gives per-section outcomes, venue and expiry, and offers final review. Its 18-row permission table is long but structured; its actual edit/approval chain was not browser-tested.
- User card makes demo context, venue, budget and session visible. VIP is its purple primary action even for a general lookup; consider weighting actions by the employee task after observing actual use, rather than treating this as a proven failure.

## Readiness against five employee questions

- Where am I? Mostly clear through heading, active menu and working-context header. Owner -> Oleg navigation prevents a reliable single-person mental model across sections.
- What am I working on? Clear for user card, support ticket and incident IDs; weaker on the dedicated status-change screen, which omits ticket ID/current status.
- What may I do? Visible actions and financial incident restrictions are helpful; personal profile gives only a broad rights summary, not exact scope/actions/expiry.
- What will happen? Incident action meanings are explicitly constrained, but status-only action unexpectedly adds a sent message in the prototype. This is the main readiness blocker for an independent employee walkthrough.
- What next? Specific return destinations, incident reconciliation link, and blocked-closure recovery links are good. Mixed demo-state shortcuts and ordinary commands still require explanation.

Verdict: suitable for a guided design review; not ready to call the selected employee flows independently intuitive until the two P1 prototype/context issues are resolved. This is UX readiness of the inspected subset, not release readiness.

## Limits and cleanup

DOM detector and injected overlay not applicable to these Figma canvas designs under project AGENTS. No markup application/runtime exists for this task. No detector/server/injection launched; no overlay claimed. This is not a missing/crashed detector claim. Prototype reading cannot establish semantic runtime accessibility, actual authorization, backend persistence, performance or financial correctness. RU desktop subset only; EN/mobile, all 878 pairs, full permission matrix and all combinations not checked.

Figma asset URL download was attempted once but shell DNS/network resolution failed; used allowed inline screenshot response fallback (enableBase64Response) afterward. No downloaded screenshot artifacts retained. Report only is saved under /private/tmp/shadow-intuition-B/. All eight screenshots were visually read from tool output. Temporary browser tab close() succeeded after final exact-return verification; no servers/processes started, user tabs/settings untouched.

Questions skipped: isolated assessment B; parent owns user-facing synthesis and closing question.
