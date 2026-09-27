# Scan result compared with ground truth

The scan fully found 17 of the 23 ground-truth vulnerabilities. It partially found 2 more and missed 4.

| ID | Ground-truth vulnerability | Scan result | Matching scan finding |
|---:|---|---|---|
| 1 | IDOR in transaction detail | Yes | #16, ZTRL-009 - Other customers' transactions readable by ID |
| 2 | IDOR through `user_id` mass assignment in profile update | No | No corresponding finding |
| 3 | MD5 password hashing | Yes | #10, ZTRL-006 - Registration stores unsalted MD5 hashes |
| 4 | Password hash and TOTP secret exposed in user responses | Yes | #9, ZTRL-003 - Login returns password hashes and TOTP secrets. Registration exposure was also covered by #10 |
| 5 | SQL injection in admin customer search | Yes | #4, ZTRL-010 - Confirmed SQL injection with boolean and error-based extraction |
| 6 | Stored XSS in dashboard transactions | Yes | #12, ZTRL-013 |
| 7 | Stored XSS in account-detail transactions | Yes | #11, ZTRL-019 |
| 8 | TOTP bypass on external transfers | Yes | #7, ZTRL-012 - Transfer completed without `totp_code` |
| 9 | No balance check on external transfers | Yes | #7, ZTRL-012 - Transfer produced a negative balance |
| 10 | Stack traces exposed in error responses | Yes | #22, ZTRL-020 - SQL errors, paths and stack traces exposed |
| 11 | Overly permissive reflected CORS | Yes | #25, ZTRL-002 - Arbitrary origins reflected with credentials |
| 12 | Unauthenticated config and secret leakage from `/api/health` | Yes | #2, ZTRL-001 |
| 13 | Outdated Moment.js 2.29.1 | Yes | #15, ZTRL-023 |
| 14 | Outdated jQuery 3.3.1 | Yes | #15, ZTRL-023 |
| 15 | User enumeration during login | Yes | #17, ZTRL-011 |
| 16 | One-character passwords accepted | Yes | #18, ZTRL-005 |
| 17 | No rate limiting on login, registration or TOTP verification | Partial | #21/ZTRL-022 and #23/ZTRL-014 found missing controls on admin and customer login. Registration and TOTP endpoints were not tested |
| 18 | JWT signature verification bypass | No | The scan found the leaked JWT signing secret, but did not identify that arbitrary or invalid signatures are accepted |
| 19 | Unauthenticated full database export | No | No corresponding finding for `/api/admin/export/users` |
| 20 | No security audit logging | No | No corresponding finding |
| 21 | SSRF through avatar URL fetching | Yes | #5, ZTRL-008 - Confirmed HTTP, loopback and `file://` access |
| 22 | SQL injection in transaction-list `sort` parameter | Partial | #22, ZTRL-020 triggered SQL errors and confirmed unsanitized query construction, but reported it as error disclosure rather than demonstrating SQL injection |
| 23 | IDOR on external-transfer source account | Yes | #1, ZTRL-025 - Confirmed debit from another customer's account |

## Coverage

- Fully found: **17/23 - 73.9%**
- Fully or partially found: **19/23 - 82.6%**
- Missed: **4/23 - 17.4%**
- Missed IDs: **#2, #18, #19 and #20**

The scan also reported several issues outside the ground truth, including unbounded credit-card and loan amounts, stored avatar XSS, secrets in `localStorage`, and missing security headers. Three of its 25 exported findings were marked `false_positive`, so they are not counted as ground-truth matches.
