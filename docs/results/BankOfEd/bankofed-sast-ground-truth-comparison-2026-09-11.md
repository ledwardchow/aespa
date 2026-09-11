# BankOfEd SAST comparison - Sonnet 5 Deep and Light modes

## Results

| Scan mode | Total scan issues | Ground-truth vulnerabilities found | Recall | Missed | Estimated token cost | Cost per vulnerability found |
|---|---:|---:|---:|---:|---:|---:|
| Deep - Sonnet 5 | 96 | 19 of 23 | 82.6% | 4 | $27.82 | $1.46 |
| Light - Sonnet 5 | 39 | 15 of 23 | 65.2% | 8 | $13.70 | $0.91 |

Deep mode found four vulnerabilities that Light mode missed:

- **#10 - Stack Trace Leakage in Error Responses**
- **#11 - Overly Permissive CORS**
- **#16 - Weak Password Policy**
- **#17 - No Brute-Force Protection**

Both modes missed:

- **#13 - Outdated moment.js**
- **#14 - Outdated jQuery**
- **#15 - User Enumeration on Login**
- **#20 - No Audit Logging**

## Cost comparison

| Measure | Deep - Sonnet 5 | Light - Sonnet 5 |
|---|---:|---:|
| Estimated token cost | $27.82 | $13.70 |
| Ground-truth vulnerabilities found | 19 | 15 |
| Cost per vulnerability found | $1.46 | $0.91 |

## Ground-truth comparison

| # | Ground-truth vulnerability | Deep - Sonnet 5 | Deep issue(s) | Light - Sonnet 5 | Light issue(s) | Notes |
|---:|---|:---:|---|:---:|---|---|
| 1 | IDOR in Transaction Detail | Yes | 19, 31, 45, 69 | Yes | 39 | Both modes identify the missing transaction ownership check. |
| 2 | IDOR via Mass Assignment in Profile Update | Yes | 18, 26, 39, 58, 71, 80 | Yes | 38 | Both modes identify the attacker-controlled `user_id`. |
| 3 | MD5 Password Hashing | Yes | 73, 76 | Yes | 34 | Both modes identify active unsalted MD5 password storage. |
| 4 | Sensitive Data Exposure in API Responses | Yes | 29, 40, 72 | Yes | 38 | Light mode covers this inside its profile IDOR finding. Its evidence explicitly identifies `User::toPublic()` returning `password_hash` and `totp_secret`. |
| 5 | SQL Injection in Admin Customer Search | Yes | 10, 24, 42, 60, 65 | Yes | 24, 25, 30 | Both modes identify direct interpolation of the `search` parameter into SQL. |
| 6 | Stored XSS in Dashboard Transaction List | Yes | 38, 54, 94 | Yes | 21, 22 | Both modes identify unescaped transaction descriptions on the dashboard. |
| 7 | Stored XSS in Account Detail Transaction Table | Yes | 33, 52, 53, 91, 92, 93 | Yes | 19, 20 | Both modes identify unescaped transaction descriptions in the account view. |
| 8 | TOTP Bypass on External Transfers | Yes | 78, 96 | Yes | 37 | Both modes cover users without TOTP and omission of `totp_code` when TOTP is enabled. |
| 9 | No Balance Check on External Transfers | Yes | 32, 77 | Yes | 36 | In both reports this is explicit in validator reasoning for the external-transfer IDOR rather than a standalone issue. |
| 10 | Stack Trace Leakage in Error Responses | Yes | 75 | No | - | Deep mode identifies exception messages, file paths, line numbers, and stack traces returned to API clients. |
| 11 | Overly Permissive CORS | Yes | 9, 20 | No | 6 dismissed | Light mode identifies the configuration but dismisses it. Deep mode has confirmed issues 9 and 20, so only Deep counts as finding it. |
| 12 | Unauthenticated Config/Secret Leakage | Yes | 1, 5, 13, 15, 28, 30, 44, 51, 57, 74, 81, 86, 95 | Yes | 1, 7, 8, 10, 26 | Both modes identify the unauthenticated health endpoint and its JWT/database disclosures. |
| 13 | Outdated moment.js | No | - | No | - | Neither mode identifies moment.js 2.29.1 or its known vulnerabilities. |
| 14 | Outdated jQuery | No | - | No | - | Both reports discuss jQuery rendering behavior, but neither identifies jQuery 3.3.1 as an outdated vulnerable component. |
| 15 | User Enumeration on Login | No | - | No | - | Neither mode identifies the different `USER_NOT_FOUND` and `WRONG_PASSWORD` responses. |
| 16 | Weak Password Policy | Yes | 76 | No | - | Deep issue 76 explicitly records registration validation as `min:1|max:128`. Light mode's MD5 issue does not identify the one-character policy. |
| 17 | No Brute-Force Protection | Yes | 41 | No | - | Deep mode confirms no rate limiting or lockout on TOTP verification. Light mode has no equivalent issue. |
| 18 | JWT Signature Bypass | Yes | 12, 25, 50, 70, 79 | Yes | 27, 35 | Both modes identify customer JWT payloads being trusted without signature verification. |
| 19 | Unauthenticated Full Data Export | Yes | 16, 17, 43, 62, 67 | Yes | 31 | Both modes identify the unauthenticated users/accounts/transactions export. |
| 20 | No Audit Logging | No | - | No | - | Neither mode identifies the lack of security-event or audit logging. |
| 21 | Avatar Proxy Fetches Arbitrary URLs | Yes | 27, 36, 48, 55, 59, 68, 82 | Yes | 33 | Both modes identify unrestricted server-side URL fetching. |
| 22 | SQL Injection in Transaction Listing | Yes | 11, 63, 64, 66, 83 | Yes | 28, 29 | Both modes identify the `sort` parameter being inserted into the `ORDER BY` clause. |
| 23 | IDOR on Source Account in External Transfer | Yes | 32, 35, 77 | Yes | 36 | Both modes identify an arbitrary `from_account_id` being used without an ownership check. |

## Coverage details

Deep mode has 17 standalone matches and two matches found explicitly inside other findings:

- **#9 - No Balance Check on External Transfers** appears in the validator reasoning for issues 32 and 77.
- **#16 - Weak Password Policy** appears in the evidence for issue 76.

Light mode has 13 standalone matches and two matches found explicitly inside other findings:

- **#4 - Sensitive Data Exposure in API Responses** appears in the evidence for issue 38.
- **#9 - No Balance Check on External Transfers** appears in the validator reasoning for issue 36.

