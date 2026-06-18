# Scan Comparison: Sonnet 4.6 Specialist vs Ground Truth

- **Site:** Bank of Ed
- **Scan date:** 2026-05-24
- **Ground truth vulnerabilities:** 23
- **Scan findings (unique):** 26
- **Coverage:** 13 found (57%), 10 missed (43%)

---

## Table 1: Ground Truth vs Scan Coverage

| GT ID | Vulnerability | OWASP Category | Found? | Validation Status | Matched Scan Finding |
|---|---|---|---|---|---|
| #1 | IDOR in Transaction Detail | A01 | ✅ Yes | Validating | IDOR: Unauthorized Access to Other Users' Transaction Data via `/api/transactions/{id}` |
| #2 | IDOR via Mass Assignment in Profile Update | A01 | ❌ No | — | — |
| #3 | MD5 Password Hashing | A02 | ✅ Yes | Confirmed | Weak MD5 Password Hashing for New User Registrations |
| #4 | Sensitive Data Exposure in API Responses (pw hash + TOTP secret) | A02 | ✅ Yes | Confirmed | Password Hash and TOTP Secret Exposed in Login/Profile API Response |
| #5 | SQL Injection in Admin Customer Search | A03 | ✅ Yes | Confirmed | SQL Injection in Admin Customer Search Endpoint |
| #6 | Stored XSS in Dashboard Transaction List | A03 | ✅ Yes | Confirmed | Stored XSS via Transaction Description in Banking Dashboard |
| #7 | Stored XSS in Account Detail Transaction Table | A03 | ❌ No | — | XSS found in dashboard (#6) but account detail view not tested |
| #8 | TOTP Bypass on External Transfers | A04 | ✅ Yes | Confirmed | Business Logic Bypass: TOTP Requirement Not Enforced on External Transfer Endpoint |
| #9 | No Balance Check on External Transfers | A04 | ✅ Yes | Confirmed | Business Logic: External Transfer Allows Unlimited Overdraft |
| #10 | Stack Trace Leakage in Error Responses | A05 | ✅ Yes | Confirmed | Verbose Stack Traces Exposed in API Error Responses |
| #11 | Overly Permissive CORS | A05 | ✅ Yes | Confirmed | CORS Misconfiguration: Arbitrary Origin Reflection with Credentials Allowed |
| #12 | Unauthenticated Config/Secret Leakage (`/api/health`) | A05 | ✅ Yes* | Confirmed | JWT Secret Exposed in `/api/health` Endpoint *(miscategorised as A02 by scanner)* |
| #13 | Downgraded JWT Library (`firebase/php-jwt ^5.0`) | A06 | ❌ No | — | — |
| #14 | Known Vulnerable PHPMailer (`^5.2`) | A06 | ❌ No | — | — |
| #15 | User Enumeration on Login | A07 | ✅ Yes | Confirmed | User Enumeration via Login Error Messages |
| #16 | Weak Password Policy (min length = 1) | A07 | ❌ No | — | — |
| #17 | No Brute-Force Protection on Login/TOTP | A07 | ❌ No | — | — |
| #18 | JWT Signature Bypass (base64 decode only) | A08 | ❌ No | — | — |
| #19 | Unauthenticated Full Data Export (`/api/admin/export/users`) | A09 | ❌ No | — | — |
| #20 | No Audit Logging | A09 | ❌ No | — | — |
| #21 | SSRF via Avatar Proxy (`file://`, metadata URLs) | A10 | ❌ No | — | — |
| #22 | SQL Injection in Transaction Listing (`sort` param) | A03 | ✅ Yes | Validating | SQL Injection via `sort` Parameter in `/api/transactions` |
| #23 | IDOR on Source Account in External Transfer | A01 | ✅ Yes | Unconfirmed | IDOR: Unauthorized Fund Transfer from Other Users' Accounts via `/api/transfers/external` |

\* Finding #12 was correctly identified but miscategorised as A02 instead of A05.

---

## Table 2: Scan Findings NOT in Ground Truth

| Finding | OWASP (scanner) | Severity | Status | Notes |
|---|---|---|---|---|
| Admin Panel Accessible with Default Credentials (`admin`/`admin123`) | A07 | Critical | Confirmed | Genuine finding — likely a real undocumented vulnerability |
| IDOR: Admin API Allows Direct Account Balance Manipulation | A01 | Critical | Validating | Not documented; plausibly real |
| Admin JWT Token Expiry Not Validated | A07 | High | Confirmed | Adjacent to #18 (JWT Signature Bypass) but a distinct claim |
| IDOR: Admin Accounts Endpoint Accessible with Regular User JWT | A01 | High | Validating | Possible real finding — admin endpoints not properly gated |
| IDOR: Admin API Exposes Full Customer PII Without Scoping | A01 | High | Validating | Related to #19 (unauthenticated export) but requires auth — different vulnerability |
| IDOR: Unauthorized Access to Other Users' Profile Data via `/api/profile` | A01 | High | Validating | Adjacent to #2 (mass assignment write) but this is read access — different exploit path |
| Stored XSS via Address Book Nickname Field | A03 | High | Validating | Same XSS class as #6/#7 but different injection point — possibly real |
| TOTP Setup Endpoint Accessible Without Authentication | A07 | High | Validating | Not documented; plausibly real |
| Admin Panel Accessible Without Network Restriction | A05 | Medium | Validating | Config/design observation; not a coded vulnerability |
| Deleted/Invalidated User Tokens Accepted by Some Endpoints | A07 | Medium | Validating | Could be a consequence of #18 JWT Signature Bypass, or a real session issue |
| Missing Content-Security-Policy Header | A05 | Medium | Confirmed | Real but minor hardening gap; not in scope of ground truth |
| Server Version Disclosed in HTTP Response Headers | A05 | Info | Validating | Real but informational; not in scope of ground truth |

---

## Key Takeaways

- **Biggest blind spots:** A06 (vulnerable components — both library issues missed entirely), A08 (JWT signature bypass), A09 (no audit logging, unauthenticated data export), A10 (SSRF), and the account-detail XSS (#7).
- **Miscategorisation:** Finding #12 (health endpoint leaking secrets) is a real hit but was tagged A02 instead of A05.
- **Notable extras:** Default admin credentials and the admin endpoint IDOR findings are plausibly real vulnerabilities not captured in the ground truth, rather than false positives.
