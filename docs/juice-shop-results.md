# Juice Shop Pentest Scanner Comparison

This comparison consolidates equivalent findings across three penetration testing reports for the same OWASP Juice Shop target.

The Aespa column has been updated from the re-exported Aespa/Sonnet 4.6 findings dated 2026-05-10 19:09:19, which reported 18 raw findings. Duplicate or overlapping findings are consolidated below into one row per underlying vulnerability.

## Consolidated Findings Matrix

| Consolidated vulnerability | Aespa / Sonnet 4.6 | Claude Code / Sonnet 4.6 | Codex / GPT-5.5 | Notes |
|---|---:|---:|---:|---|
| SQL injection — login authentication bypass | Not found | Found | Found | Claude Code and Codex both found classic login SQLi returning an admin JWT. Aespa found product-search SQLi but did not report login authentication bypass. |
| Default / weak admin credentials `admin@juice-sh.op:admin123` | Found | Found | Not found | Aespa and Claude Code both confirmed weak/default admin credentials. Codex did not separately report this. |
| SQL injection in `/rest/products/search` exposing user password hashes | Found | Partial | Partial | Aespa fully exploited UNION SQLi to dump user hashes. Claude Code found verbose SQL errors around product search but did not report the user-hash dump. Codex reported SQL error disclosure and recommended fixing search SQLi, but did not show hash extraction. |
| Unsalted MD5 password hashes | Found | Found | Not found | Aespa reported extracted password hashes as unsalted MD5. Claude Code tied the MD5 admin hash to the weak password. Codex did not report this separately. |
| Full user list / user metadata exposure via `/api/Users` | Found | Found | Found | Aespa reported unauthenticated full user-list exposure. Claude Code reported exposure to any valid JWT. Codex reported exposure after obtaining an admin JWT through SQLi. |
| Individual user record IDOR via `/api/Users/{id}` | Found | Not found | Not found | Aespa reported unauthenticated access to individual user records and authenticated cross-user access to admin user records. |
| Mass assignment allows self-registration as admin via `POST /api/Users` | Found | Not found | Not found | Unique to Aespa. |
| Basket IDOR / cross-user basket access via `/rest/basket/{id}` | Found | Found | Not found | Aespa and Claude Code both found cross-user basket access. Codex did not report this. |
| Feedback API data exposure / sensitive feedback disclosure | Partial | Not found | Not found | Aespa reported a sensitive crypto wallet seed phrase exposed via `/api/Feedbacks`. The re-export no longer includes the broader unauthenticated “all feedback records” finding from the earlier export as a standalone item. |
| Sensitive crypto wallet seed phrase exposed in feedback | Found | Not found | Not found | Unique to Aespa. |
| Feedback CAPTCHA bypass / unauthenticated feedback POST | Found | Not found | Not found | Unique to Aespa. |
| Stored HTML / XSS surface in feedback comments | Found | Not found | Not found | Aespa reported partial stored XSS/HTML sanitisation weakness in feedback comments. |
| HTML injection / XSS surface in search route | Not found | Not found | Found | Unique to Codex. This is separate from Aespa’s feedback XSS finding. |
| Public `/ftp/` directory listing and sensitive files | Not found | Found | Found | Claude Code gave the most detail, including KeePass DB, package backups and coupons. Codex confirmed `acquisitions.md`. Aespa did not report this in the re-export. |
| Null byte extension filter bypass for blocked FTP files | Not found | Found | Not found | Unique to Claude Code. |
| Verbose SQL/database error disclosure | Found | Found | Found | All three found some form of verbose DB/framework error disclosure. |
| Verbose Express/framework stack traces | Partial | Found | Partial | Aespa reported SQL error disclosure with framework version/context. Claude Code reported full stack traces. Codex reported SQL error disclosure with Express version, but not full stack traces as a separate issue. |
| Unauthenticated Prometheus `/metrics` endpoint | Not found | Found | Not found | Unique to Claude Code. |
| Security question enumeration without auth | Not found | Found | Not found | Unique to Claude Code. |
| Application/admin configuration disclosure | Found | Found | Found | Aespa and Codex reported unauthenticated access. Claude Code described admin-token access and noted it compounds SQLi/weak-password findings. |
| Missing security headers — CSP/HSTS/etc. | Found | Found | Found | All found missing CSP/HSTS. Claude Code additionally called out Referrer-Policy and Permissions-Policy. |
| Permissive CORS wildcard | Not found | Found | Found | Aespa did not report CORS in the re-export. |

## Scanner Summary

| Scanner | Raw findings | Consolidated findings found | Notable strengths | Notable misses |
|---|---:|---:|---|---|
| Aespa / Sonnet 4.6 | 18 | 14 | Strong API-focused coverage. Found product-search SQLi with credential/hash extraction, default admin credentials, mass assignment to admin, `/api/Users` exposure, `/api/Users/{id}` IDOR, basket IDOR, feedback seed phrase exposure, feedback CAPTCHA bypass, feedback HTML/XSS surface, config disclosure, security headers and verbose SQL errors. | Missed login SQLi auth bypass, FTP exposure, null-byte FTP bypass, Prometheus metrics, security-question enumeration, CORS wildcard, and search-route XSS. |
| Claude Code / Sonnet 4.6 | 12 | 12 | Best breadth across classic Juice Shop issues. Found login SQLi, weak admin password, authenticated user dump, basket IDOR, FTP exposure, null-byte bypass, verbose stack traces, metrics, security questions, config disclosure, missing headers and CORS. | Missed Aespa’s deeper API findings: mass assignment, `/api/Users/{id}` IDOR, feedback seed phrase exposure, feedback CAPTCHA bypass, feedback XSS surface, and product-search user-hash dump. |
| Codex / GPT-5.5 | 8 | 8 | Shorter report, but found several high-value issues: login SQLi, user metadata exposure, search-route HTML injection/XSS, FTP exposure, CORS, config disclosure, SQL error disclosure and missing headers. | Missed weak/default admin password, basket IDOR, null-byte FTP bypass, metrics, security questions, feedback issues, mass assignment, `/api/Users/{id}` IDOR, and MD5 hash storage as a separate finding. |

## Aespa Re-export Deduplication Notes

The new Aespa export contains 18 raw findings. Several are duplicate or overlapping entries:

| Raw Aespa findings | Consolidated row |
|---|---|
| Findings 1 and 2: Default Administrative Credentials Active | Default / weak admin credentials |
| Findings 3 and 5: SQL Injection in `/rest/products/search` Exposes User Password Hashes | Product-search SQLi exposing password hashes |
| Findings 6 and 8: `/api/Users/{id}` access control / IDOR | Individual user record IDOR |
| Findings 12 and 18: basket access control / IDOR | Basket IDOR |
| Findings 15 and 16: application configuration disclosure | Application/admin configuration disclosure |

## Overall Assessment

Claude Code had the most balanced coverage across the classic Juice Shop attack surface, especially FTP exposure, null-byte bypass, metrics, security-question enumeration and CORS.

Aespa had the strongest API-data-exposure coverage and found several issues missed by the others, including mass assignment to admin, individual user record IDOR, feedback seed phrase exposure, feedback CAPTCHA bypass and product-search SQLi with hash extraction. Its main gaps were the login SQLi authentication bypass and several common Juice Shop reconnaissance/file-exposure findings.

Codex produced the shortest report. It found important issues including login SQLi, search-route HTML injection/XSS and FTP exposure, but missed many secondary and API-specific findings.
