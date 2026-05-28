# Bank of Ed Scanner Comparison: Deepseek v4 Flash vs Sonnet 4.6 (new cache strategy)

**Date:** 2026-05-27  
**Target:** Bank of Ed (bankofed.leddytech.com) — 23-item ground-truth vulnerability list  
**Scans:**
- **Deepseek v4 Flash** — Aespa run using DeepSeek v4 Flash via Foundry API. 135 raw issues.
- **Sonnet 4.6 (new cache)** — Aespa run using Claude Sonnet 4.6, testing the new caching strategy. 59 raw issues.

**Notation:** ✓ confirmed match · ◐ partial/adjacent match · ✗ not found

---

## Ground-truth coverage table

| # | OWASP | Ground-truth vulnerability | Deepseek v4 Flash | Sonnet 4.6 (new cache) |
|---:|---|---|---|---|
| 1 | A01 | IDOR in transaction detail, `GET /api/transactions/{id}` | ✓ Issue #98 — accessed another user's transaction; ownership check absence confirmed | ✓ Issue #45 — accessed transactions from accounts belonging to other users; HTTP 200 confirmed |
| 2 | A01 | Profile-update mass assignment IDOR, `PUT /api/profile` with `user_id` | ✗ | ✓ Captured in "Sensitive data exposed" issues — `PUT /api/profile?user_id=3` returned HTTP 200, modifying another user's profile |
| 3 | A02 | MD5 password hashing | ✓ Issues #54, #65 — registration response returned 32-char hex hash confirmed as MD5 | ✓ Issue #6 — MD5 hash of `password123` verified against known digest |
| 4 | A02 | `password_hash` and `totp_secret` exposed in API responses | ✓ Issues #15, #55, #66–69 — both fields returned in login and profile responses | ✓ Issue #9 — both fields returned on login; `totp_secret` exposure noted separately |
| 5 | A03 | SQLi in admin customer search | ✓ Issues #2, #7, #56, #57 — `'` broke SQL, full SQLSTATE error and stack trace returned | ✓ Issues #3, #4, #16 — error-based and time-based injection confirmed with file-path disclosure |
| 6 | A03 | Stored XSS in dashboard transaction list (`dashboard.js`) | ◐ Static `.innerHTML` sinks flagged by deterministic module; profile first-name XSS confirmed in admin panel but transaction-description sink in `dashboard.js` not specifically proven | ✓ Issue #18 — `POST /api/transfers/own` with `<img src=x onerror=…>` in description; `dashboard.js` renders `tx.description` via `innerHTML` without sanitisation, confirmed dynamically |
| 7 | A03 | Stored XSS in account-detail transaction table (`accounts.js`) | ◐ Static `.innerHTML` sinks flagged; `accounts.js` not specifically confirmed | ◐ Issues #46–59 — `.innerHTML` sinks identified across banking JS files via static analysis; `accounts.js` not independently confirmed as exploited |
| 8 | A04 | TOTP bypass on external transfers | ◐ Within the balance-check evidence (Issue #13) the response showed `totp_verified: false` with transfer succeeding, but no standalone TOTP-bypass finding was raised | ✓ Issue #19 — `POST /api/transfers/external` without `totp_code` returned HTTP 201 with `totp_verified: false`; transfer completed |
| 9 | A04 | No balance check on external transfers | ✓ Issues #13, #14 — $50,000 transfer from account with $3,300 balance succeeded; new balance −$46,699 | ✓ Issue #8 — overdraft confirmed; transfer of amount exceeding balance returned HTTP 201 |
| 10 | A05 | Stack trace leakage in error responses | ✓ Issues #94–96 ("Verbose SQL Error Disclosure") — full file path `/var/www/bankofed/…`, line number, and PHP stack trace returned in 500 responses | ✓ Embedded in SQLi issues #3, #4 — `SQLSTATE`, file path, and stack trace returned in every SQL error response |
| 11 | A05 | Overly permissive CORS | ✓ Issues #80–87, #97, #99–100 — arbitrary `Origin` reflected; `Access-Control-Allow-Credentials: true` confirmed | ✓ Issues #1, #20–26 — arbitrary origin reflected with credentials; confirmed across all API routes |
| 12 | A05 | Unauthenticated config/JWT-secret leakage via `/api/health` | ✓ Issue #1 — `jwt_secret`, `db_host`, `db_user`, `db_name`, PHP version returned without authentication | ✓ Issue #2 — JWT signing secret returned in plaintext; database credentials and server metadata also exposed |
| 13 | A06 | Downgraded vulnerable JWT library (`firebase/php-jwt ^5.0`) | ✗ | ✗ |
| 14 | A06 | Vulnerable PHPMailer dependency (`^5.2`, CVE-2016-10033) | ✗ | ✗ |
| 15 | A07 | User enumeration on login | ✓ Issue #93 — `USER_NOT_FOUND` vs `WRONG_PASSWORD` error codes distinguish valid/invalid accounts | ✓ Issue #44 — distinct `USER_NOT_FOUND`/`WRONG_PASSWORD` codes confirmed |
| 16 | A07 | Weak password policy (1-character minimum) | ✗ | ✗ |
| 17 | A07 | No brute-force protection | ✗ | ✗ |
| 18 | A08 | JWT signature bypass (signatures not verified at all) | ✓ Issues #5, #6 — forged token with arbitrary payload base64-encoded accepted; authentication achieved without valid signing secret | ◐ Issue #2 noted that leaked JWT secret enables token forgery, but the underlying signature-ignore flaw was not independently tested or confirmed |
| 19 | A09 | Unauthenticated full data export (`GET /api/admin/export/users`) | ✗ | ✗ |
| 20 | A09 | No audit logging | ✗ | ✗ |
| 21 | A10 | SSRF via avatar proxy (`POST /api/profile/avatar`) | ✗ | ✗ |
| 22 | A03 | SQLi in transaction listing `sort` parameter | ✗ | ✓ Issues #10–15 — `GET /api/transactions?sort=created_at'` returned SQLSTATE error with stack trace from `Transaction.php:55` |
| 23 | A01 | IDOR on source account in external transfer (`from_account_id`) | ✗ | ✓ Issues #7, #45 — `POST /api/transfers/external` with `from_account_id` belonging to another user succeeded; funds debited from victim account |

---

## Scorecard

| Scanner | Full ✓ | Partial ◐ | Misses ✗ | Score (/ 23) | Adjusted rating |
|---|---:|---:|---:|---|---|
| Sonnet 4.6 (new cache) | 14 | 2 | 7 | 15 / 23 (65 %) | **9.0 / 10** |
| Deepseek v4 Flash | 10 | 3 | 10 | 11.5 / 23 (50 %) | **6.5 / 10** |

*Adjusted rating factors in finding quality, noise ratio, and false-positive load in addition to raw detection rate.*

### Context: relative to prior Aespa Sonnet 4.6 run

The prior Sonnet 4.6 run (without the new caching strategy) scored 13 full + 1 partial = 8.5 / 10. The new-cache run improves to **14 full + 2 partial**, adding the profile-update mass assignment IDOR (#2) — a finding no previous scanner in this benchmark had confirmed.

---

## Additional findings (not in ground truth)

These are issues raised by each scanner that do not correspond to any of the 23 defined ground-truth vulnerabilities. They may be valid real findings, variant findings, or false positives.

| Scanner | Extra finding | Assessment |
|---|---|---|
| Deepseek v4 Flash | Default admin credentials (Issues #3, #4) | Validation inconclusive — scanner could not reproduce; likely false positive |
| Deepseek v4 Flash | Admin unrestricted account balance manipulation (Issue #10) | Plausible real finding — admin endpoint allows arbitrary balance changes; not in ground-truth scope |
| Deepseek v4 Flash | Unauthorized role access to admin endpoints (Issues #11, #30–53, #62–64, and ~20 more) | Mostly generic endpoint probe noise; significant duplication reduces signal value |
| Deepseek v4 Flash | Admin database reset endpoint — unrestricted access (Issue #12) | Likely real finding — admin can wipe the entire database; not in ground-truth scope |
| Deepseek v4 Flash | Stored XSS in profile first-name field (admin panel) (Issues #29, #58, #89) | Real finding — name field renders unescaped in admin panel; adjacent to but distinct from ground-truth dashboard/accounts XSS |
| Deepseek v4 Flash | Potential stored XSS sinks in JS source (Issues #108–135) | Static analysis output, low-confidence; most lack dynamic confirmation |
| Deepseek v4 Flash | Missing HTTP Strict-Transport-Security header (Issues #101–103, #106–107) | Valid low-severity finding |
| Sonnet 4.6 (new cache) | Unrestricted loan creation — users can create loans with arbitrary amounts (Issue #5) | Potentially real business-logic flaw; dynamically confirmed HTTP 201 response |
| Sonnet 4.6 (new cache) | Unauthorized role access to admin endpoints (Issues #20–26) | Generic admin probe findings; some duplication |
| Sonnet 4.6 (new cache) | Missing Content-Security-Policy header (Issue #27) | Valid finding; amplifies confirmed XSS impact |
| Sonnet 4.6 (new cache) | Unauthenticated access to protected endpoints (Issues #34–43) | Various admin endpoints probed without auth; some may overlap with ground-truth #19 scope but export endpoint not specifically identified |
| Sonnet 4.6 (new cache) | Potential stored XSS sinks in JS source (Issues #46–59) | Static analysis output; some confirmed dynamically via related findings |

---

## Noise analysis

| Scanner | Raw issues | Unique finding types (estimated) | Duplication rate |
|---|---:|---:|---|
| Deepseek v4 Flash | 135 | ~18 | ~87 % |
| Sonnet 4.6 (new cache) | 59 | ~19 | ~68 % |

Deepseek generated 2.3× more raw issues than Sonnet for fewer confirmed ground-truth hits. The bulk of the Deepseek volume came from repeated "Unauthorized role access to admin endpoint" (≥30 instances), "Unauthenticated access to protected endpoint" (≥18 instances), and CORS duplicates (≥12 instances). This substantially increases analyst triage time.

---

## Unique findings by scanner

**Deepseek ✓ vs Sonnet ◐:**
- #18 JWT signature bypass — Deepseek independently forged a token and confirmed acceptance; Sonnet only noted the leaked JWT secret enables forgery without testing the signature-ignore flaw directly.

**Sonnet ✓ vs Deepseek ✗:**
- #2 Profile-update mass assignment IDOR
- #8 TOTP bypass on external transfers (standalone confirmed finding)
- #22 SQLi in transaction listing `sort` parameter
- #23 IDOR on source account in external transfer

**Both partial ◐ (neither confirmed):**
- #7 Stored XSS in account-detail transaction table — both flagged static `.innerHTML` sinks; neither confirmed the `accounts.js` `renderDetailTransactions()` exploit path.

**Both missed ✗:** #13, #14, #16, #17, #19, #20, #21.

---

## Cost analysis

| Scanner | API / provider | Cost | Findings (GT) | Cost per GT finding |
|---|---|---|---:|---|
| Deepseek v4 Flash | DeepSeek API | $1.37 | 10 | $0.14 / finding |
| Deepseek v4 Flash | Foundry API | $3.30 | 10 | $0.33 / finding |
| Sonnet 4.6 (new cache) | Anthropic API | $7.80 | 14 | $0.56 / finding |

---

## Value judgement

**Sonnet 4.6 (new cache) is the clear winner for security testing quality.** It finds 40 % more ground-truth vulnerabilities than Deepseek v4 Flash (14 vs 10 confirmed), with substantially less noise. Critically, the four vulnerabilities Sonnet found that Deepseek missed — TOTP bypass, external-transfer source-account IDOR, transaction `sort` SQLi, and mass assignment IDOR — are all high-severity findings with direct financial fraud or account-takeover impact in a banking application. Missing any of them in a real engagement would be a material gap.

At $7.80, Sonnet costs $0.56 per ground-truth finding. At Foundry pricing, Deepseek costs $0.33 per finding; at DeepSeek API pricing, just $0.14. However, raw cost-per-finding comparisons are misleading when the cheaper scanner misses critical vulnerabilities. The four high-severity issues Deepseek missed represent far more remediation and business risk than the $4.50–$6.43 cost saving.

**Deepseek v4 Flash's sole meaningful advantage** is finding #18 (JWT signature bypass) independently — a finding Sonnet only approached indirectly. At DeepSeek API pricing ($1.37), it also offers an extremely cheap first-pass triage scan. Used together — Deepseek for initial broad sweep, Sonnet for depth — the combined cost would be $9.17 (Foundry) or $7.17 (DeepSeek API + Anthropic), picking up 14 confirmed ground-truth findings plus a full ✓ on the JWT bypass (#18, which Sonnet only partially covers) vs Sonnet's 14 full + 2 partial alone.

**Recommendation by use case:**

| Use case | Recommendation |
|---|---|
| Full security audit / penetration test | Sonnet 4.6 ($7.80) — substantially better coverage and signal quality |
| Quick budget triage scan | Deepseek v4 Flash via DeepSeek API ($1.37) — reasonable baseline at minimal cost |
| Maximum coverage | Run both (DeepSeek API + Sonnet): ~$9.17 combined, 15 confirmed GT findings |
| Cost-sensitivity with quality floor | Deepseek via Foundry ($3.30) misses too many critical findings to recommend for a banking app |

**Neither scanner is sufficient as a sole testing mechanism.** Both miss the A06 dependency vulnerabilities (PHPMailer, JWT library downgrade), SSRF, the unauthenticated export endpoint, audit-logging absence, brute-force protection, and weak password policy — consistent with the limitations of a black-box dynamic scanner that does not inspect `composer.json` or probe low-traffic endpoints.

The new caching strategy in the Sonnet run also delivered the first confirmed detection of the mass assignment IDOR (#2) across all scanners in this benchmark, suggesting the implementation improvement has measurable security-testing impact.
