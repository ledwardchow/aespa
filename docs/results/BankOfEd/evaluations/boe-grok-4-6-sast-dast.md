# Finished scan comparison with ground truth

## Sources

- Ground truth: `VULNERABILITIES.md`
- Finished scan: `grok-sast-dast-issues-2026-09-19 (1).md`
- Finished scan findings: 116
- Ground-truth findings: 23

## Method

Findings were matched by vulnerable behavior, affected endpoint, and code location. Duplicate scan reports count once. Findings marked `unconfirmed` or `validating` are treated as confirmed for this comparison.

| GT ID | Ground-truth finding | Result | Best matching scan finding(s) | Notes |
|---:|---|:---:|---|---|
| 1 | Transaction-detail IDOR | Yes | WFPS-007, WFPS-013 | Cross-user transaction access was confirmed. |
| 2 | Profile-update IDOR through `user_id` | Yes | WFPS-006, WFPS-012 | Cross-user reading and modification were confirmed. |
| 3 | MD5 password hashing | Yes | WFPS-054 | Registration was shown to store unsalted MD5 hashes. |
| 4 | Password hash and TOTP secret exposed in API responses | Yes | WFPS-009, WFPS-016, WFPS-116 | Found in profile, login, and related API responses. WFPS-116 is still validating but is counted as confirmed. |
| 5 | SQL injection in admin customer search | Yes | WFPS-035, WFPS-040, WFPS-118 | Found through code review and dynamic testing. |
| 6 | Stored XSS in dashboard transaction list | Yes | WFPS-029, WFPS-030, WFPS-073 | The unconfirmed WFPS-029 is counted as confirmed. Confirmed duplicates also exist. |
| 7 | Stored XSS in account-detail transaction table | Yes | WFPS-072 | The account-detail renderer inserts transaction descriptions into `innerHTML`. |
| 8 | TOTP bypass on external transfers | Yes | WFPS-023, WFPS-044, WFPS-057, WFPS-067 | Covers an omitted code and users without TOTP configured. |
| 9 | No balance check on external transfers | Yes | WFPS-058, WFPS-060 | Missing service and balance-floor checks were found. |
| 10 | Stack traces exposed in error responses | Yes | WFPS-127 | Reported directly as "Verbose SQL exceptions disclose stack traces and DB version." It is validating and counted as confirmed. |
| 11 | Overly permissive CORS | Yes | WFPS-101, WFPS-117 | Arbitrary Origin reflection and credential-enabled CORS were found. |
| 12 | Unauthenticated health endpoint leaks configuration and secrets | Yes | WFPS-003, WFPS-019 | Confirmed without authentication. |
| 13 | Outdated moment.js 2.29.1 | **No** | None | The version appears in captured HTML evidence, but no finding identifies its known vulnerabilities or required upgrade. |
| 14 | Outdated jQuery 3.3.1 | **No** | None | The script URL appears in evidence, but the scan does not report the vulnerable version or related CVEs. |
| 15 | User enumeration on login | Yes | WFPS-098 | Different responses disclose whether an email exists. |
| 16 | Weak one-character password policy | Yes | WFPS-054, WFPS-115 | A one-character password was accepted. The finished scan also found accounts using the default password `password`. |
| 17 | No brute-force protection | **Partial** | WFPS-100, WFPS-108 | Customer and admin login were covered. Registration and TOTP verification were not separately tested or reported for missing throttling. |
| 18 | JWT signature bypass | Yes | WFPS-011, WFPS-020 | Invalidly signed customer JWTs were accepted. |
| 19 | Unauthenticated full data export | Yes | WFPS-005, WFPS-015 | The complete users, accounts, and transactions export was confirmed without authentication. |
| 20 | No security audit logging | **No** | None | No finding covers missing logging of authentication, transfers, admin actions, or TOTP changes. |
| 21 | Avatar proxy SSRF | Yes | WFPS-037, WFPS-086 | HTTP, loopback, and `file://` access were confirmed. |
| 22 | SQL injection in transaction-list `sort` parameter | Yes | WFPS-113, WFPS-125 | The injection was identified dynamically and in the model code. |
| 23 | External-transfer source-account IDOR | Yes | WFPS-014, WFPS-056 | Arbitrary `from_account_id` values can debit other customers' accounts. |

## Coverage

- Fully found: **19 of 23**
- Partially found: **1 of 23**
- Missed: **3 of 23**
- Coverage counting the partial match: **20 of 23, or 87%**
- Strict full-match coverage: **19 of 23, or 83%**

The missed findings are:

1. Outdated moment.js
2. Outdated jQuery
3. Missing security audit logging

The partial finding is incomplete endpoint coverage for brute-force protection. Customer and admin login were covered, but registration and TOTP verification were not.
