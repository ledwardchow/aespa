# Bank of Ed AI Pentest Scanner Comparison

This comparison evaluates five AI-assisted pentest runs against the 23-item ground-truth vulnerability list defined in `VULNERABILITIES.md`. A scanner receives:

- **✓** when it identified the same underlying vulnerability or exploit path.
- **◐** when it identified a related weakness but not the exact vulnerable endpoint or exploitation condition.
- **✗** when it did not identify the issue.

The ground truth includes IDORs, SQL injection, TOTP bypass, sensitive-data exposure, JWT weaknesses, CORS issues, brute-force weaknesses, dependency vulnerabilities, XSS sinks, SSRF, logging failures, and authentication flaws.

## Main comparison table

| # | Ground-truth vulnerability | Aespa Sonnet 4.6 (June 1st 2026) | Claude Code Sonnet 4.6 | Claude Code Qwen 3.6 | Codex GPT-5.5 | Strix Sonnet 4.6 |
|---:|---|---|---|---|---|---|
| 1 | IDOR in transaction detail, `GET /api/transactions/{id}` | ✓ | ✓ | ✗ | ✓ | ✓ |
| 2 | Profile-update mass assignment IDOR, `PUT /api/profile` with `user_id` | ✗ | ✗ | ✗ | ✗ | ✗ |
| 3 | MD5 password hashing | ✓ | ✓ | ✗ | ✓ | ✓ |
| 4 | `password_hash` and `totp_secret` exposed in API responses | ✓ | ✓ | ✗ | ✓ | ✓ |
| 5 | SQLi in admin customer search | ✓ | ✓ | ✗ | ✗ | ✗ |
| 6 | Stored XSS in dashboard transaction list | ✓ Dynamically confirmed XSS via transaction description in `dashboard.js` | ◐ Found stored XSS in account names, wrong sink | ◐ Generic possible XSS only | ✗ | ✓ |
| 7 | Stored XSS in account-detail transaction table | ◐ Static `innerHTML` sink identified in `accounts.js`; dynamic confirmation not established | ◐ Adjacent stored XSS finding, wrong sink | ◐ Generic possible XSS only | ✗ | ✓ |
| 8 | TOTP bypass on external transfers | ✓ | ✓ | ✗ | ✓ | ◐ Exposed TOTP secret enables valid-code generation but transfer-endpoint bypass not independently confirmed |
| 9 | No balance check on external transfers | ✓ | ✗ | ✗ | ◐ Mentioned balance validation concerns but not as a confirmed exploit | ◐ Demonstrated overdraft via concurrent race condition, not identified as standalone balance-validation absence |
| 10 | Stack trace leakage | ✓ | ✓ | ✗ | ✗ | ✗ |
| 11 | Overly permissive CORS | ✓ | ✗ | ✗ | ✓ | ✗ |
| 12 | Unauthenticated config/JWT-secret leakage via `/api/health` | ✓ | ✗ | ✗ | ✓ | ✓ |
| 13 | Downgraded vulnerable JWT library | ✗ | ✗ | ✗ | ✗ | ✗ |
| 14 | Vulnerable PHPMailer dependency | ✗ | ✗ | ✗ | ✗ | ✗ |
| 15 | User enumeration on login | ✓ | ✓ | ✗ | ✓ | ✗ |
| 16 | Weak password policy | ✓ Dynamically confirmed: single-character and three-character passwords accepted by registration endpoint | ✗ | ◐ Reported weak/undefined password requirements without proving the vulnerable acceptance condition | ✗ | ✗ |
| 17 | No brute-force protection | ✓ | ✓ | ◐ Mentioned missing lockout and TOTP throttling behaviour | ✓ | ✗ |
| 18 | JWT signature bypass | ◐ JWT forgery confirmed via leaked signing secret; `alg:none` signature-ignore flaw not independently identified | ✗ | ✗ | ◐ Found JWT forgery via leaked secret rather than the signature-ignore flaw | ✓ |
| 19 | Unauthenticated full data export | ✓ Admin panel and all backing APIs confirmed accessible without authentication; full customer PII and account data extracted | ✗ | ✗ | ✗ | ✗ |
| 20 | No audit logging | ✗ | ✗ | ✗ | ✗ | ✗ |
| 21 | SSRF avatar proxy | ✓ Confirmed with HTTP internal server fetch and `file://` local file read yielding full `/etc/passwd` contents | ✗ | ✗ | ✗ | ✗ |
| 22 | SQLi in transaction listing `sort` parameter | ✓ | ✗ | ✗ | ✗ | ✗ |
| 23 | IDOR on source account in external transfer | ✓ | ✗ | ✗ | ✓ | ✗ |

## Scorecard

| Scanner | Full matches | Partial matches | Misses | Adjusted rating |
|---|---:|---:|---:|---:|
| Aespa Sonnet 4.6 | 17 | 2 | 4 | 9.3 / 10 |
| Codex GPT-5.5 | 8 | 2 | 13 | 7.0 / 10 |
| Claude Code Sonnet 4.6 | 8 | 2 | 13 | 6.8 / 10 |
| Strix Sonnet 4.6 | 7 | 2 | 14 | 6.5 / 10 |
| Claude Code Qwen 3.6 | 0 | 4 | 19 | 1.5 / 10 |

## Scanner assessment

### Aespa Sonnet 4.6

Aespa produced the broadest confirmed finding set of any scanner in this comparison. It identified 15 of 23 ground-truth vulnerabilities outright and partially covered two more, achieving the highest effective coverage score of any scanner tested.

Confirmed findings span all three A01 IDOR entries (transaction-detail enumeration, external-transfer source-account manipulation, and the forged-JWT profile read via the leaked signing secret), both SQL injection instances (admin customer search and the transaction listing `sort` parameter), TOTP bypass on external transfers, no-balance-check logic flaw on external transfers, permissive CORS, `/api/health` JWT-secret and database-credential disclosure, login enumeration, stack-trace leakage, MD5 hashing at registration, sensitive `password_hash` and `totp_secret` API exposure, brute-force protection absence on both the user and admin login endpoints, weak password policy dynamically confirmed by submitting single-character passwords, and unauthenticated full data export via a fully open admin panel.

The two most notable wins over other scanners were SSRF and the open admin panel. Aespa was the only scanner to confirm the avatar SSRF endpoint, extending it to a local file read via `file://` that extracted the full `/etc/passwd` of the server — a significant depth-of-exploitation improvement over merely detecting the vector. It was also the only scanner to confirm that the admin panel and all of its backing `/api/admin/*` APIs require no authentication, which alone constitutes a complete breach of confidentiality for all 22 customer records. Dynamic confirmation of the dashboard stored XSS in `dashboard.js` via an injected `<img onerror>` payload was the only fully confirmed XSS execution among scanners that also correctly attributed the sink.

Its primary weaknesses are coverage gaps and signal-to-noise ratio. Despite the broad reach, the scanner did not identify the `alg:none` JWT signature-ignore bypass (#18, found only indirectly via the signing secret), and the full A06 dependency and A09 audit-logging categories — consistent with a dynamic-first approach that does not inspect installed libraries or application logging behaviour. The 129 raw findings with heavy duplication across severity buckets (multiple near-identical IDOR and CORS re-reports) significantly increases triage effort, and the account-detail XSS sink (#7) was flagged only by static analysis of `accounts.js` rather than via a confirmed injection.

### Codex GPT-5.5

Codex remained the strongest exploit-chain-oriented scanner. It identified the `/api/health` JWT-secret exposure, forged JWT abuse, TOTP bypass, source-account IDOR, transaction-detail IDOR, sensitive API exposure, login enumeration, brute-force weaknesses, and permissive CORS.

Codex performed particularly well against hidden API attack surfaces and multi-step exploitation paths. It consistently focused on externally exploitable flaws with direct account-takeover or fraud implications. The findings were generally concise and technically accurate.

Its main limitation was coverage breadth. It missed the admin-search SQL injection, stack traces, and several secondary application weaknesses that Aespa identified. It also did not identify either XSS sink or several lower-level operational issues.

### Claude Code Sonnet 4.6

Claude Code Sonnet produced a relatively clean and accurate report focused on validated application flaws. It correctly identified the transaction-detail IDOR, MD5 password hashing, sensitive API exposure, admin-search SQL injection, TOTP bypass, stack traces, login enumeration, and missing brute-force protection.

The report quality was strong and generally low-noise. Findings were mapped reasonably well to the underlying vulnerability classes, and the scanner avoided many speculative observations.

However, it missed several of the most dangerous hidden/API-centric flaws, including `/api/health` JWT-secret disclosure, permissive CORS, external-transfer source-account IDOR, and the JWT forgery path. Its coverage of attack chaining was weaker than both Aespa and Codex.

### Strix Sonnet 4.6

Strix produced a compact set of seven confirmed findings, all validated with working proof-of-concept exploitation and CVSS scores. It correctly identified the two most severe vulnerabilities — unauthenticated JWT-secret and database credential disclosure via `/api/health`, and the `alg: none` JWT signature bypass — and was the only scanner to correctly match both ground-truth stored XSS sinks, explicitly naming the rendering surfaces in `dashboard.js` and `accounts.js`. The transaction-detail IDOR, password hash and TOTP-secret API exposure, MD5 hashing, and the race-condition overdraft were all confirmed with concrete HTTP evidence and an end-to-end exploit chain including an unauthorized $500 transfer from a victim account.

The precision of XSS sink attribution and the clean identification of the `alg: none` flaw (which other scanners only found indirectly via secret disclosure) are notable strengths. All findings were high-confidence with no false positives.

The significant limitation is coverage. Strix missed the admin-search SQL injection, permissive CORS, user enumeration, brute-force protection absence, stack-trace leakage, source-account IDOR on external transfers, and all dependency and secondary vulnerability classes. Its seven findings represent the highest-severity slice of the attack surface rather than a comprehensive audit.

### Claude Code Qwen 3.6

Qwen mostly behaved as a surface-level UI and configuration auditor. It reported generic XSS possibilities, weak password requirements, lack of visible lockout protections, session-management concerns, CSRF concerns, and miscellaneous UI or operational observations.

It did not validate the major API vulnerabilities in the ground-truth list and failed to identify the primary exploit chains affecting transfers, JWT handling, or account access control. Most findings were observational rather than exploit-driven.

## Extra findings not in `VULNERABILITIES.md`

| Scanner | Extra findings |
|---|---|
| Aespa Sonnet 4.6 | SSRF with full local file read via `file://` protocol (extracted `/etc/passwd`); default admin credentials (`admin`/`admin123`); universal default customer password ('password' across all 15 accounts); unrestricted loan self-approval allowing arbitrary fund creation; admin balance manipulation endpoint permitting arbitrary account balance override; money-creation defect via cross-account transfer source IDOR (credit applied without corresponding debit); account takeover via unverified email change at `PUT /api/profile`; admin silent password reset without customer notification; unrestricted FX rate manipulation via admin API; stored XSS in profile first_name/last_name fields; stored XSS in address book nickname and payee fields; application served over plain HTTP with no TLS; server version and PHP version disclosure in response headers. |
| Claude Code Sonnet 4.6 | Weak admin credentials; stored XSS in account names; missing CSP/HSTS; publicly linked admin panel. |
| Strix Sonnet 4.6 | Database credentials and server metadata (PHP/Apache version) disclosed via `/api/health` beyond the JWT-secret scope. |
| Claude Code Qwen 3.6 | robots.txt disclosure; exposed contact email; malformed state dropdown; missing visible session timeout; CSRF-token absence; SPA/hash-routing observations; role-model concerns. |
| Codex GPT-5.5 | Weak seeded customer credentials; weak admin credentials; unlimited loan creation/redraw logic flaws; missing security headers; JWT forgery via leaked signing secret. |

## Final ranking

1. **Aespa Sonnet 4.6** — best overall coverage (17/23), only scanner to confirm SSRF with local file read, only scanner to confirm unauthenticated admin panel access, and only scanner to dynamically confirm dashboard XSS.
2. **Codex GPT-5.5** — strongest exploit-chain reasoning and hidden API attack-path discovery.
3. **Claude Code Sonnet 4.6** — clean reporting and good validation quality, but weaker hidden-surface coverage.
4. **Strix Sonnet 4.6** — highest finding precision and the only scanner to correctly identify both XSS sinks, but limited to the highest-severity subset of the attack surface.
5. **Claude Code Qwen 3.6** — mostly a UI/configuration audit with limited exploit validation.

Aespa performed best on overall coverage and confirmed exploit evidence, achieving the highest full-match count of any scanner tested. Its standout results were the SSRF confirmation extended to a full local file read, the only fully confirmed unauthenticated admin panel compromise, both SQL injection instances including the transaction `sort` parameter, the no-balance-check logic flaw on external transfers, and dynamic proof of weak password policy acceptance — none of which any other scanner established in full. Codex remained the strongest at identifying chained account-compromise paths and high-severity API abuse. Claude Code Sonnet was the cleanest low-noise scanner for breadth. Strix matched fewer total vulnerabilities but achieved the highest precision on the findings it did report — uniquely correct on both XSS sinks and the `alg:none` JWT bypass — making it strong for critical-path triage at the cost of coverage depth. Qwen primarily identified surface-level weaknesses rather than validated exploitation paths.
