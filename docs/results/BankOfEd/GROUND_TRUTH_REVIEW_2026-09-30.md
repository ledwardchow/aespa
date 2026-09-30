# BankOfEd ground-truth review - 30 September 2026

The expanded dataset contains **38 findings: 23 retained and 15 added**. The original saved dataset and VULNERABILITIES.md are unchanged. New IDs are GT-24 through GT-38. Use [GROUND_TRUTH_EXPANDED_2026-09-30.json](GROUND_TRUTH_EXPANDED_2026-09-30.json) for Benchmark Lab; the [Markdown copy](GROUND_TRUTH_EXPANDED_2026-09-30.md) is for reading.

## Scope and evidence standard

Reviewed the retained Bank of Ed results in the current database, historical database backups, exported reports and comparison documents under docs/results. This inventory contains **3,795 records**, including duplicates across scans, exports and backups. These are not 3,795 distinct vulnerabilities. There are no Bank of Ed API collections in the current database. The current revision archive was inspected as text; the other scan archives were inventoried and hashed. No uploaded application code was executed.

| Source | Records | Scope |
|---|---:|---|
| live_dast | 738 | 31 web runs for site 1, including failed/stopped runs and the one available finding in running run 268. |
| live_sast | 1006 | 16 SAST runs whose archive filename or source locator identifies BankOfEd. |
| export_dast | 413 | 8 structured finding exports, including the older June report. |
| backup_dast | 1392 | 2 retained historical database backups, with Bank of Ed site associations. |
| export_sast | 246 | 4 full BankOfEd SAST report exports. |

The [scan inventory CSV](GROUND_TRUTH_SCAN_INVENTORY_2026-09-30.csv) identifies every included record. It records scanner status for traceability, not as an endorsement. The inventory also retains misplaced historical records so their exclusion is visible. Comparison documents are supporting context, not independent evidence; one comparison explicitly counts unconfirmed results as confirmed, which was not accepted here. The Goosecable report in the BankOfEd directory was excluded as a different target.

Additions require either a recorded successful exploit with useful controls and inspected source, or a complete source path that establishes the failure without an unresolved runtime dependency. Scanner confidence, repeated titles, a 200 app shell, raw text returned in JSON, and a validator exhausting its budget are insufficient by themselves. A dismissed SAST record can mean it was merged before validation; those notes were read rather than treating every dismissal as a disproof.

No live HTTP requests or new exploitation were performed during this review. Dynamic evidence below was recorded by earlier scans. **GT-37 and GT-38 have source confirmation, not new runtime confirmation.** The Content-Type variant in GT-36 also has static evidence only. GT-28 confirms the active public SSO signing key, without claiming a demonstrated downstream insurance account takeover.

The snapshot is limited to records available when read on 30 September 2026. Run 268 was still running and had one finding at inventory capture. Files or results outside this workspace were not searched. Historical builds and deployed services can differ from the source archive, so historical behavior is not assumed to exist in every current build.

## Added findings and supporting records

### GT-24 - Active default administrator credentials

Recorded dynamic verification and source inspection. KOWT-031 used anonymous login and an incorrect-password control; KAZU-022 also used the issued token against protected customer/account lists.

Applies when seeded credentials have not been changed. Count the password once, rather than counting every admin action it unlocks.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 1982 | 235 | KOWT-031 | confirmed |
| scan_finding 2489 | 266 | KAZU-022 | confirmed |

### GT-25 - Active shared default customer password

Recorded dynamic verification and source inspection. KOWT-032 tested Amelia and Zoe separately; wrong-password controls returned 401 and the correct default returned distinct IDs 1 and 3.

This is separate from the registration password-length policy. Limited to seeded accounts whose passwords are unchanged.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 1983 | 235 | KOWT-032 | confirmed |
| scan_finding 2381 | 250 | WFPS-115 | confirmed |

### GT-26 - Known default signing key permits administrator token forgery

Recorded dynamic verification plus complete signing/verification source path. WFPS-002 records a forged default-key token reading customers and settings. The inspected middleware uses Firebase JWT verification and checks issuer, revocation and administrator existence.

Requires the default key to remain active. This is distinct from GT-18, which concerns customer JWTs and missing signature checks. No fresh token was sent during this review.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2302 | 250 | WFPS-002 | confirmed |
| scan_lead 2782 | 265 | NMMU-060 | dismissed |
| scan_lead 2862 | 267 | SCOE-044 | dismissed |

### GT-27 - Public default machine token grants access to payment APIs

ULJJ-006 records a cookie-free ranged HTML response containing the token; source line 219 contains that literal value. QZDR-013 records a completed settlement-account transfer and a 401 without the token. WFPS-004 records an accepted card payment.

The payment APIs intentionally use machine authentication. The defect is public exposure of a working credential. Do not claim unrestricted access to every source account: the default token is scoped in PaymentController::transfer. Some later validators deny the static disclosure; that conflicts with the supplied source and the earlier anonymous response. Admin-only settings display alone is not a separate finding.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2057 | 241 | ULJJ-006 | confirmed |
| scan_finding 2301 | 250 | WFPS-004 | confirmed |
| scan_finding 2416 | 251 | QZDR-013 | confirmed |
| scan_finding 2479 | 266 | KAZU-012 | false_positive |

### GT-28 - Active insurance SSO signing key is published in source

WFPS-008 records signature_valid=true when verifying a live SSO redirect assertion with the known fallback. The signing path was independently inspected.

The established finding is compromised assertion authenticity while the default key is active. Acceptance of a forged assertion and account takeover in FACE Insurance were not demonstrated in the reviewed evidence. Do not score that additional consequence as proven.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2332 | 250 | WFPS-008 | confirmed |
| scan_lead 2742 | 265 | NMMU-020 | confirmed |

### GT-29 - Persistent storage and routine disclosure of card CVV and full card details

KOWT-009 records full card fields on an ordinary accounts request. WFPS-102 records them on new-card creation. KAZU-023 validator reasoning independently checked two customers. Source confirms storage and serialization.

Do not claim this endpoint is unauthenticated or that ownership checks are missing. The new entry concerns retained CVV and its routine serialization; displaying a virtual card number to its owner alone is not enough. KAZU-023 contains an unrelated pasted 422 request, so that request is not used as proof.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 1936 | 235 | KOWT-009 | confirmed |
| scan_finding 2317 | 250 | WFPS-102 | confirmed |
| scan_finding 2490 | 266 | KAZU-023 | confirmed |

### GT-30 - Customers can originate uncapped loans with immediate cash disbursement

WFPS-095 records a 1,000,000 loan and validator verification of a further 999,999,999,999.99 disbursement. QZDR-016 checked both Zoe's loan and the credited transaction account. KAZU-013 corroborates another persisted disbursement.

The destination ownership/type checks work. Creating a loan account alone would be weaker evidence; the posted cash is decisive. The maximum is still bounded by storage/numeric limits, so do not describe literally infinite borrowing.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2306 | 250 | WFPS-095 | confirmed |
| scan_finding 2419 | 251 | QZDR-016 | confirmed |
| scan_finding 2480 | 266 | KAZU-013 | confirmed |

### GT-31 - Customers can choose an uncapped spendable credit-card limit

WFPS-102 records a 999,999,999 limit and a follow-up account read. RIAG-016 records a newly registered customer creating a 1,000,000 limit after supplying the required account name.

Count unlimited self-issued credit once, rather than separate findings for default-limit issuance, no underwriting and caller-chosen limits. Full card details are covered separately by GT-29.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2317 | 250 | WFPS-102 | confirmed |
| scan_finding 2459 | 253 | RIAG-016 | confirmed |

### GT-32 - Own-account transfers ignore credit-card available funds and limits

WFPS-022 records a 100,000 transfer from a card with about 24,990 available credit, producing -75,011; the validator repeated a further debit at -75,012 against a 25,000 limit. Source confirms cards are excluded from the funds check.

Ownership checks are present. This is a separate operation from the external-transfer overdraft in GT-9 and does not require concurrent requests.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2307 | 250 | WFPS-022 | confirmed |
| scan_lead 2728 | 265 | NMMU-006 | confirmed |

### GT-33 - Stored XSS through customer names in administrator Delete controls

WFPS-025 records admin Delete execution and a DOM marker. SCOE-043 traces the complete customer-to-admin storage/render path. Independent source inspection confirms the escaping order and innerHTML assignment.

Requires an administrator to view the affected customer and click Delete. Ordinary escaped name text in the table is not the vulnerable sink. Do not count registration and profile update as separate bugs.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2325 | 250 | WFPS-025 | confirmed |
| scan_lead 2861 | 267 | SCOE-043 | confirmed |

### GT-34 - Stored XSS through account names in administrator Edit Balance controls

WFPS-112 records account 110, the decoded live onclick value, and a successful admin DOM marker. SCOE-065 independently traces public registration, customer account creation and admin rendering.

Requires an administrator click. This is distinct from customer-name XSS because a different stored field and renderer need repair. It does not establish unauthenticated balance editing.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2337 | 250 | WFPS-112 | confirmed |
| scan_lead 2892 | 267 | SCOE-065 | confirmed |

### GT-35 - Stored XSS through address-book nicknames in Delete controls

WFPS-110 records persisted entry 23 and a successful DOM marker after clicking Delete. SCOE-064 confirms ownership scoping and the executable sink.

User-assisted/self-XSS with a real execution result, not a proven cross-customer write. Severity is limited accordingly. Do not conflate it with historical unproven address-book IDOR claims or escaped payee text.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 2330 | 250 | WFPS-110 | confirmed |
| scan_lead 2891 | 267 | SCOE-064 | confirmed |

### GT-36 - Avatar import parses untrusted URL and Content-Type as page HTML

KOWT-026 records successful URL-fragment import, persistence and browser DOM execution. SGBH-056/SCOE-057 trace the remote-header variant; independent source inspection confirms both unsafe HTML sinks.

The recorded browser execution covers source_url. The Content-Type variant has complete static evidence but no independent recorded runtime execution used here. Both require the victim to import the attacker-controlled URL/content. This is distinct from SSRF/local-file reading in GT-21 and from merely detecting jQuery's version in GT-14.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_finding 1977 | 235 | KOWT-026 | confirmed |
| scan_lead 2501 | 259 | SGBH-056 | confirmed |
| scan_lead 2880 | 267 | SCOE-057 | confirmed |

### GT-37 - Concurrent payments and own-account transfers can spend the same balance twice

Complete static evidence. The source places reads/checks before beginTransaction, uses balance = balance + ? WHERE id = ?, and declares a signed DECIMAL balance without a nonnegative constraint. Row serialization applies both deltas; it does not repeat the earlier check. SGBH-046 also includes the own-transfer trace.

No concurrent exploit was executed in this review and no dynamic double-spend result is claimed. Requires overlapping requests and appropriate customer/machine credentials. Group the three instances because they share the same unchecked-debit invariant. External-transfer missing checks remain GT-9; credit-card own transfers that skip checks entirely remain GT-32.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_lead 2491 | 259 | SGBH-046 | confirmed |
| scan_lead 2755 | 265 | NMMU-033 | confirmed |
| scan_lead 2756 | 265 | NMMU-034 | confirmed |
| scan_lead 2856 | 267 | SCOE-040 | confirmed |
| scan_lead 2860 | 267 | SCOE-042 | confirmed |

### GT-38 - Administrator password resets leave existing customer sessions valid

Complete static evidence. ILTJ-025 and NMMU-028 independently trace reset and authentication. Source confirms only logout revokes a presented jti and reset has no user-wide session cutoff.

No fresh password reset was performed. The static path establishes continued acceptance of an existing valid token for up to the configured 24-hour expiry. This finding does not rely on GT-18 or on forging a replacement jti.

| Record | Scan | Finding or lead reference | Scanner status |
|---|---:|---|---|
| scan_lead 2610 | 261 | ILTJ-025 | confirmed |
| scan_lead 2750 | 265 | NMMU-028 | confirmed |

## Claims held back or covered by existing IDs

| Claim | Decision |
|---|---|
| Login ignores enabled TOTP | Held back. Password-only login is present, but public/index.html describes TOTP as protecting high-value transfers. The explicit transfer step-up policy does not establish a required login challenge. SAST lead 2807 explains this contrary policy evidence. The missing transfer check remains GT-8. |
| Charges succeed when CVV is omitted | Held back as a separate vulnerability. Source proves CVV is optional and recorded charges omit it, but a machine-authenticated merchant payment API can intentionally support card-on-file charges. No product rule requiring CVV for every charge was established. The publicly known machine credential is GT-27 and stored/disclosed CVV is GT-29. |
| Every active machine-token name can debit any account | Held back. The fail-open branch exists, but the shipped seed and fallback produce only face_insurance and configured_machine_token, both of which enter the account restriction. Another active machine identity must be created out of band. Lead 2754 provides this counterevidence. |
| Admin settings API returns the machine token | Covered by GT-27 only where it supports identification of the exposed token. The settings endpoint itself is admin-authenticated; admin display of a configured integration credential does not independently establish unauthorized disclosure. |
| Admin-only FX rate name XSS | Held back under the strict boundary requirement. The unsafe inline handler exists, but writing currency_name already requires the same unrestricted administrator role. No lower-privileged author or less-trusted import path was shown. Separate customer-to-admin XSS is included as GT-33/34. |
| Admin can set balances, reset passwords, delete users or reset the database | Those are existing administrator capabilities. Default credentials/key are GT-24/26, missing audit records remain GT-20, and surviving sessions are GT-38. No extra finding is added just because an authorized admin action succeeds. |
| Arbitrary SSO destination configured by an admin | Held back. insurance_app_url is writable only by an administrator. No supported lower-privileged writer or enforced partner allowlist was established. A token in the SSO URL also does not by itself prove leakage to an attacker. |
| SSO token in a query string or localStorage bearer-token storage | Held back as separate findings. These are observable storage/transport choices, with no independent attacker read demonstrated. Existing XSS has concrete token-access consequences. |
| HTTP, absent security headers, CDN scripts without SRI, server banners | Held back from the strict additions. These are deployment/hardening observations, often localhost-specific; no separate exploit or violated deployment requirement was demonstrated. Absence of CSP can support an XSS finding but is not counted again. |
| Anonymous or cross-user access to SPA routes and JavaScript | A public HTML app shell or static JS response is not access to protected bank data. Many older rows use fragment URLs or share ambient sessions; require a cookie-free/token-free API response or a verified non-owner session before adding an access-control finding. |
| Address-book IDOR and transfer-payee dropdown XSS | Historical claims are held back for this dataset. Current inspected AddressBookController scopes show/update/delete to the current user; transfers.js escapes the payee label. Older mismatched request evidence and absent alternate-user controls do not override those guards. The proven nickname Delete-handler XSS remains GT-35. |
| Negative JSON transfer amount bypasses validation | Rejected. Lead 842 was disproved: validateDecimal casts values to strings and checks them; the controller separately rejects nonpositive amounts. The quoted is_string guard was not in the source. |
| SQL injection in stored descriptions/FX labels | Returning or storing a SQL-looking string does not show SQL execution. Transaction creation uses bound parameters. The established interpolation defects remain GT-5 and GT-22. |
| Profile-name HTML returned in JSON | Raw JSON text does not prove browser execution. The supported customer-name execution is the administrator inline Delete handler in GT-33; ordinary name rendering uses escapeHtml. |
| Transfer FX multiplier and missing settlement checks | Held back. Administrator-controlled rate changes and deliberately supported external-bank transfers do not establish an unprivileged money-creation bug. One recent FX claim used two AUD accounts and was disproved by the actual currencies. |
| Duplicate submissions / stale If-Match / missing KYC | No unique authorization, idempotency, concurrency-control or onboarding requirement was established from these observations alone. The complete stale-balance debit paths are included as GT-37. |
| Vampi SQL injection, plaintext passwords and Werkzeug console under a Bank of Ed scan | Wrong target. Historical records 501-503 in the July backup describe /users/v1, SQLite and a Python/Werkzeug service. BankOfEd is PHP/MariaDB. They remain in the inventory as misplaced records and are excluded. |
| Customer-token forgery through leaked JWT key or admin/customer token overlap | Covered by existing GT-12 and GT-18 where supported. Do not add another finding for each downstream endpoint reached. Some current validator notes claim signatures are checked while the inspected customer decoder ignores them; that deployment/source disagreement is documented rather than assumed resolved. |

## Baseline cautions

The original 23 entries are retained exactly in JSON, including their original severities. They are an inherited benchmark, not 23 new confirmations made in this review. In particular:

- GT-11 establishes arbitrary CORS origin reflection. The browser does not automatically attach the banking bearer token from another origin's localStorage, so reflected CORS alone does not prove theft of an authenticated account response.
- GT-13/14 retain the original vulnerable-component inventory. A version observation does not prove every listed CVE can be exploited in this browser application. No external CVE lookup was performed here.
- GT-3 should not be interpreted as all hashes being instantly crackable. The demonstrated new-registration defect is fast unsalted MD5; seeded users also include bcrypt hashes.
- GT-5/22 identify SQL interpolation. The original example payloads should not be assumed to work with every database configuration.
- GT-12's recorded health payload exposes the JWT key and database connection metadata; current observations do not show a database password in that response.
- GT-19 is an access-control/data-disclosure issue even though the inherited category is A09. Category changes were not made because the request was to expand the existing ground truth.

## Source archive and scan traceability

Source line numbers on the new entries refer to the archive for SAST run 256, commit **7cc913742c5824c109243aa00146f9e1af1f44bd**. It is also the recorded revision for later SAST runs 258, 259, 261, 262, 265 and 267. The archive contains the shipped HTML token literal, card serializer, credit issuance paths, unsafe inline handlers, stale-balance checks and password-reset/authentication code inspected above. Archive identity does not assert that every deployed server used the same revision.

| SAST run | Source archive | SHA-256 | Recorded revision |
|---:|---|---|---|
| 90 | 72918b14c98941c28d84a2bd86db052d.zip | 30942ba924135a75992b2302d1d3236413b92515a1eee254516a2c93bb2a91de | not recorded |
| 110 | 02b888c105cb49128f937bd702fca509.zip | 30942ba924135a75992b2302d1d3236413b92515a1eee254516a2c93bb2a91de | not recorded |
| 152 | e56cf76796ba43c5863a98bc393964c0.zip | 092a0397b3ccc01b60f2b01354d0ced7033ad9fc86f8bd8cc5513968d014b5a1 | not recorded |
| 175 | 7d82395391554996aea88c544c1f4f92.zip | 092a0397b3ccc01b60f2b01354d0ced7033ad9fc86f8bd8cc5513968d014b5a1 | not recorded |
| 179 | c70ddb2f4d214d569f9e2713580ab6f7.zip | 092a0397b3ccc01b60f2b01354d0ced7033ad9fc86f8bd8cc5513968d014b5a1 | not recorded |
| 196 | d6363d82b5a642debccbe04aa6b98ccc.zip | 6c92a7335df4cb3136d8d92acc0682f33a6ccdbf705cd73034334ee476916b42 | not recorded |
| 230 | 0aaf0ea2671e4090856833a892199230.zip | 6c92a7335df4cb3136d8d92acc0682f33a6ccdbf705cd73034334ee476916b42 | not recorded |
| 231 | dab3ec61368c428aa74989bb71a4fc66.zip | 6c92a7335df4cb3136d8d92acc0682f33a6ccdbf705cd73034334ee476916b42 | not recorded |
| 249 | 1695a863ea994a358291ce6353562641.zip | 6c92a7335df4cb3136d8d92acc0682f33a6ccdbf705cd73034334ee476916b42 | not recorded |
| 256 | b247dd74deb74270bbe909762f13cc18.zip | daa8c74deb0aba7c3eb526cf5cff347a3eef9790fb617f974aa4baabaa2ed837 | 7cc913742c5824c109243aa00146f9e1af1f44bd |
| 258 | a4f12472a8ff4ba9a814a73b0cf101aa.zip | daa8c74deb0aba7c3eb526cf5cff347a3eef9790fb617f974aa4baabaa2ed837 | 7cc913742c5824c109243aa00146f9e1af1f44bd |
| 259 | ff6d803f89024fa9881af19de35ae33f.zip | daa8c74deb0aba7c3eb526cf5cff347a3eef9790fb617f974aa4baabaa2ed837 | 7cc913742c5824c109243aa00146f9e1af1f44bd |
| 261 | 9957c51b32d54e5f95a1300b04bb8897.zip | daa8c74deb0aba7c3eb526cf5cff347a3eef9790fb617f974aa4baabaa2ed837 | 7cc913742c5824c109243aa00146f9e1af1f44bd |
| 262 | e58b7ea3c47b495796e227b2dc8e2a74.zip | daa8c74deb0aba7c3eb526cf5cff347a3eef9790fb617f974aa4baabaa2ed837 | 7cc913742c5824c109243aa00146f9e1af1f44bd |
| 265 | 939649c97cfd49c090e79824c99fcddd.zip | daa8c74deb0aba7c3eb526cf5cff347a3eef9790fb617f974aa4baabaa2ed837 | 7cc913742c5824c109243aa00146f9e1af1f44bd |
| 267 | 83df01bffc9744bd98ab21b31260df2e.zip | daa8c74deb0aba7c3eb526cf5cff347a3eef9790fb617f974aa4baabaa2ed837 | 7cc913742c5824c109243aa00146f9e1af1f44bd |

| Web scan ID | Name | Status at capture | Findings |
|---:|---|---|---:|
| 1 | Sonnet 4.6 - 12:30pm Monday AEST | complete | 0 |
| 4 | Kimi K2.7 | complete | 0 |
| 5 | Minimax M3 | complete | 0 |
| 6 | new workprogram smoketest | complete | 0 |
| 7 | workprogram fill bugfix testing #190 | complete | 0 |
| 10 | GLM 5.2 | complete | 0 |
| 35 | Gemini 3.5 flash | complete | 19 |
| 36 | small model test | complete | 32 |
| 98 | Run #11 | complete | 0 |
| 141 | Run #14 | failed | 19 |
| 142 | daybreak 2 | failed | 10 |
| 143 | Run #16 | complete | 30 |
| 153 | qwen 3.8 27b local | failed | 26 |
| 172 | Run #25 | complete | 0 |
| 178 | Run #27 | complete | 21 |
| 197 | Run #28 | complete | 0 |
| 198 | Run #29 | complete | 22 |
| 202 | Run #30 | complete | 13 |
| 216 | Run #43 | complete | 0 |
| 221 | Run #45 | complete | 15 |
| 222 | Run #46 | complete | 33 |
| 223 | Run #47 | failed | 4 |
| 224 | TAC1 | complete | 59 |
| 235 | Run #34 | complete | 95 |
| 241 | new deep scan | stopped | 9 |
| 242 | Run #36 | complete | 24 |
| 243 | Run #37 | complete | 88 |
| 250 | grok sast-dast | complete | 116 |
| 251 | Run #42 | complete | 40 |
| 253 | 6 luna | complete | 24 |
| 266 | Grok 4.7 BOE | complete | 38 |
| 268 | TAC1 6 Luna | running | 1 |

| Export file | Records |
|---|---:|
| docs/results/BankOfEd/boe-luna-6-dast-quick-2026-09-27.md | 24 |
| docs/results/BankOfEd/boe-luna-dast-deep-2026-09-27.md | 24 |
| docs/results/BankOfEd/boe-minimax-m3-dast-2026-07-14.md | 34 |
| docs/results/BankOfEd/boe-opus-4-8-dast-quick-2026-07-14.md | 19 |
| docs/results/BankOfEd/boe-sol-5-6-tac-dast-quick-2026-09-27.md | 95 |
| docs/results/BankOfEd/boe-sol-5-6-tac-sast-dast-2026-09-27.md | 59 |
| docs/results/BankOfEd/boe-sonnet-5-dast-quick-2026-07-14.md | 29 |
| docs/results/aespa-boe-2026-06-01.md | 129 |
| docs/results/BankOfEd/boe-grok-4-6-sast-deep-2026-09-27.md | 83 |
| docs/results/BankOfEd/boe-sol-5-6-tac-sast-light-2026-09-27.md | 28 |
| docs/results/BankOfEd/boe-sonnet-5-sast-deep-2026-09-27.md | 96 |
| docs/results/BankOfEd/boe-sonnet-5-sast-light-2026-09-27.md | 39 |

Historical backups: aespa_data/db-backups/aespa-2026-06-16.db (994 associated findings) and aespa_data/db-backups/aespa-2026-07-15-edmanda.db (398 associated findings). The saved starting dataset was benchmarking_dataset id 2 in aespa_data/extensions/aespa.benchmarking.db.

Other comparison/context files read: MODEL_COMPARISON.md and evaluations/*.md in this directory, docs/results/bankofed-deepseek-vs-sonnet-comparison-2026-05-27.md, scan-results-2026-05-24.md, results-comparison.md and vuln-scanner-comparison.md. Those files summarize earlier results and do not increase the record counts.
