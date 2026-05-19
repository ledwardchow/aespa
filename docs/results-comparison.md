# Bank of Ed AI Pentest Scanner Comparison

This comparison evaluates five AI-assisted pentest runs against the 23-item ground-truth vulnerability list defined in `VULNERABILITIES.md`. A scanner receives:

- **✓** when it identified the same underlying vulnerability or exploit path.
- **◐** when it identified a related weakness but not the exact vulnerable endpoint or exploitation condition.
- **✗** when it did not identify the issue.

The ground truth includes IDORs, SQL injection, TOTP bypass, sensitive-data exposure, JWT weaknesses, CORS issues, brute-force weaknesses, dependency vulnerabilities, XSS sinks, SSRF, logging failures, and authentication flaws.

## Main comparison table

| # | Ground-truth vulnerability | Aespa Sonnet 4.6 | Claude Code Sonnet 4.6 | Claude Code Qwen 3.6 | Codex GPT-5.5 | Strix Sonnet 4.6 |
|---:|---|---|---|---|---|---|
| 1 | IDOR in transaction detail, `GET /api/transactions/{id}` | ✓ | ✓ | ✗ | ✓ | ✓ |
| 2 | Profile-update mass assignment IDOR, `PUT /api/profile` with `user_id` | ✗ | ✗ | ✗ | ✗ | ✗ |
| 3 | MD5 password hashing | ✗ | ✓ | ✗ | ✓ | ✓ |
| 4 | `password_hash` and `totp_secret` exposed in API responses | ✓ | ✓ | ✗ | ✓ | ✓ |
| 5 | SQLi in admin customer search | ✓ | ✓ | ✗ | ✗ | ✗ |
| 6 | Stored XSS in dashboard transaction list | ◐ Found stored XSS in adjacent admin/account sinks, not the transaction-list sink | ◐ Found stored XSS in account names, wrong sink | ◐ Generic possible XSS only | ✗ | ✓ |
| 7 | Stored XSS in account-detail transaction table | ◐ Adjacent stored XSS finding, wrong sink | ◐ Adjacent stored XSS finding, wrong sink | ◐ Generic possible XSS only | ✗ | ✓ |
| 8 | TOTP bypass on external transfers | ✓ | ✓ | ✗ | ✓ | ◐ Exposed TOTP secret enables valid-code generation but transfer-endpoint bypass not independently confirmed |
| 9 | No balance check on external transfers | ◐ Demonstrated negative-balance transfer behaviour but not isolated as a standalone logic flaw | ✗ | ✗ | ◐ Mentioned balance validation concerns but not as a confirmed exploit | ◐ Demonstrated overdraft via concurrent race condition, not identified as standalone balance-validation absence |
| 10 | Stack trace leakage | ✓ | ✓ | ✗ | ✗ | ✗ |
| 11 | Overly permissive CORS | ✓ | ✗ | ✗ | ✓ | ✗ |
| 12 | Unauthenticated config/JWT-secret leakage via `/api/health` | ✓ | ✗ | ✗ | ✓ | ✓ |
| 13 | Downgraded vulnerable JWT library | ✗ | ✗ | ✗ | ✗ | ✗ |
| 14 | Vulnerable PHPMailer dependency | ✗ | ✗ | ✗ | ✗ | ✗ |
| 15 | User enumeration on login | ✓ | ✓ | ✗ | ✓ | ✗ |
| 16 | Weak password policy | ✗ | ✗ | ◐ Reported weak/undefined password requirements without proving the vulnerable acceptance condition | ✗ | ✗ |
| 17 | No brute-force protection | ✓ | ✓ | ◐ Mentioned missing lockout and TOTP throttling behaviour | ✓ | ✗ |
| 18 | JWT signature bypass | ◐ Demonstrated arbitrary JWT forgery through exposed signing secret rather than the specific signature-validation flaw | ✗ | ✗ | ◐ Found JWT forgery via leaked secret rather than the signature-ignore flaw | ✓ |
| 19 | Unauthenticated full data export | ✗ | ✗ | ✗ | ✗ | ✗ |
| 20 | No audit logging | ◐ Mentioned missing admin action auditing and weak operational controls | ✗ | ✗ | ✗ | ✗ |
| 21 | SSRF avatar proxy | ✗ | ✗ | ✗ | ✗ | ✗ |
| 22 | SQLi in transaction listing `sort` parameter | ✗ | ✗ | ✗ | ✗ | ✗ |
| 23 | IDOR on source account in external transfer | ✓ | ✗ | ✗ | ✓ | ✗ |

## Scorecard

| Scanner | Full matches | Partial matches | Misses | Adjusted rating |
|---|---:|---:|---:|---:|
| Aespa Sonnet 4.6 | 9 | 6 | 8 | 7.3 / 10 |
| Codex GPT-5.5 | 8 | 2 | 13 | 7.0 / 10 |
| Claude Code Sonnet 4.6 | 8 | 2 | 13 | 6.8 / 10 |
| Strix Sonnet 4.6 | 7 | 2 | 14 | 6.5 / 10 |
| Claude Code Qwen 3.6 | 0 | 4 | 19 | 1.5 / 10 |

## Scanner assessment

### Aespa Sonnet 4.6

Aespa produced the broadest set of confirmed high-impact findings in this run. It identified the transaction-detail IDOR, password and TOTP-secret exposure, admin-search SQL injection, transfer TOTP bypass, permissive CORS, `/api/health` JWT-secret disclosure, login enumeration, missing brute-force protection, stack-trace leakage, and the external-transfer source-account IDOR.

The strongest aspect of the report was its endpoint-level validation. The findings included concrete exploit evidence, HTTP requests, response bodies, authentication context, and impact descriptions. It successfully chained `/api/health` disclosure into arbitrary JWT forgery and broader account compromise scenarios. The scanner also surfaced operationally useful findings around verbose errors, missing security headers, weak admin credentials, and admin-side exposure risks.

Its main weakness was precision around exploit classification. Several findings mapped to adjacent vulnerabilities rather than the exact ground-truth sink. The stored XSS findings targeted different rendering locations, and the JWT issue relied on secret disclosure rather than independently identifying the intended signature-validation flaw. It also generated a large number of extra findings outside the curated ground-truth list, some of which were lower-confidence or operational observations rather than core application vulnerabilities.

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
| Aespa Sonnet 4.6 | Weak admin credentials; arbitrary admin balance manipulation; admin account inventory exposure; public admin panel exposure; missing security headers; server-version disclosure; verbose framework errors; admin JWT storage in `localStorage`; weak seeded customer credentials; additional stored XSS sinks. |
| Claude Code Sonnet 4.6 | Weak admin credentials; stored XSS in account names; missing CSP/HSTS; publicly linked admin panel. |
| Strix Sonnet 4.6 | Database credentials and server metadata (PHP/Apache version) disclosed via `/api/health` beyond the JWT-secret scope. |
| Claude Code Qwen 3.6 | robots.txt disclosure; exposed contact email; malformed state dropdown; missing visible session timeout; CSRF-token absence; SPA/hash-routing observations; role-model concerns. |
| Codex GPT-5.5 | Weak seeded customer credentials; weak admin credentials; unlimited loan creation/redraw logic flaws; missing security headers; JWT forgery via leaked signing secret. |

## Final ranking

1. **Aespa Sonnet 4.6** — best overall balance of exploit validation, endpoint coverage, and confirmed high-impact findings.
2. **Codex GPT-5.5** — strongest exploit-chain reasoning and hidden API attack-path discovery.
3. **Claude Code Sonnet 4.6** — clean reporting and good validation quality, but weaker hidden-surface coverage.
4. **Strix Sonnet 4.6** — highest finding precision and the only scanner to correctly identify both XSS sinks, but limited to the highest-severity subset of the attack surface.
5. **Claude Code Qwen 3.6** — mostly a UI/configuration audit with limited exploit validation.

Aespa performed best on overall coverage and confirmed exploit evidence. Codex remained the strongest at identifying chained account-compromise paths and high-severity API abuse. Claude Code Sonnet was the cleanest low-noise scanner for breadth. Strix matched fewer total vulnerabilities but achieved the highest precision on the findings it did report — uniquely correct on both XSS sinks and the `alg: none` JWT bypass — making it strong for critical-path triage at the cost of coverage depth. Qwen primarily identified surface-level weaknesses rather than validated exploitation paths.
