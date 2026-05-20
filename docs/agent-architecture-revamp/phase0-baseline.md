# Phase 0 Baseline — Bank of Ed

*Generated from two pre-improvement scan artifacts. All metrics reflect AESPA behaviour
before any Specialist Agent, Adversarial Validator, or Recon output-contract changes.*

---

## Runs Included

| Run | Label | Exported | Findings |
|---|---|---|---|
| `aespa-boe-2026-05-16.md` | new wstg skill prompts | 2026-05-16 | 60 |
| `aespa-boe-2026-05-18.md` | new xss checks | 2026-05-18 | 35 |

Target: **Bank of Ed** — `http://192.168.3.101` (local CTF-style banking app)

---

## Per-Run Metrics

### new wstg skill prompts (2026-05-16)

**Severity breakdown:**

| Severity | Count |
|---|---|
| Critical | 7 |
| High | 24 |
| Medium | 26 |
| Low | 3 |

**Validation status breakdown:**

| Status | Count |
|---|---|
| validating | 32 |
| unvalidated | 18 |
| confirmed | 9 |
| low_confidence | 1 |

**Finding source breakdown:**

| Source | Count |
|---|---|
| unknown | 60 |

**Computed rates:**

| Metric | Value | Notes |
|---|---|---|
| Findings/run | 60 | |
| Confirmed rate | 15.0% | 9/60 have `confirmed` status |
| False-positive rate | 0.0% | 0/60 have `false_positive` status |
| Low-confidence rate | 1.7% | 1/60 have `low_confidence` status |
| Still-validating / unvalidated | 83.3% | 50/60 — validator did not reach a verdict |
| Within-run duplicate titles | 37 | findings sharing a title with another in this run |

### new xss checks (2026-05-18)

**Severity breakdown:**

| Severity | Count |
|---|---|
| Critical | 3 |
| High | 10 |
| Medium | 9 |
| Info | 13 |

**Validation status breakdown:**

| Status | Count |
|---|---|
| unvalidated | 16 |
| confirmed | 10 |
| low_confidence | 9 |

**Finding source breakdown:**

| Source | Count |
|---|---|
| deterministic_probe | 23 |
| dynamic_scan | 12 |

**Computed rates:**

| Metric | Value | Notes |
|---|---|---|
| Findings/run | 35 | |
| Confirmed rate | 28.6% | 10/35 have `confirmed` status |
| False-positive rate | 0.0% | 0/35 have `false_positive` status |
| Low-confidence rate | 25.7% | 9/35 have `low_confidence` status |
| Still-validating / unvalidated | 45.7% | 16/35 — validator did not reach a verdict |
| Within-run duplicate titles | 15 | findings sharing a title with another in this run |

---

## Cross-Run Overlap

| Metric | Value |
|---|---|
| Unique finding titles (combined) | 40 |
| Titles appearing in both runs | 3 |
| Titles unique to run 1 (2026-05-16) | 20 |
| Titles unique to run 2 (2026-05-18) | 17 |
| Cross-run repeat rate | 7.5% |

**Titles present in both runs:**

- SQL Injection in Admin Customer Search Endpoint
- SQL injection error disclosure
- Unauthenticated access to protected endpoint

**Titles unique to run 1 only:**

- Admin Can Directly Manipulate Customer Account Balances
- Admin Can Reset Any Customer Password - Enables Account Takeover
- Admin Database Reset Endpoint - Destructive Operation Without Adequate Protectio
- Admin JavaScript Source Files Publicly Accessible Without Authentication
- CORS Misconfiguration: Arbitrary Origin Reflected with Credentials Allowed
- Database Credentials Exposed via /api/health Endpoint
- Default/Weak Admin Credentials - admin/password123
- IDOR on Profile Update Endpoint - Cross-User Profile Modification
- IDOR on Transaction Detail Endpoint - Cross-User Transaction Access
- JWT Forgery Enables Full Account Takeover of Any User
- JWT Signing Secret Exposed via /api/health Endpoint
- Manipulated AUD Exchange Rate Enables Fraudulent FX Conversions
- Missing Security Headers on Banking Application HTML Pages
- Sensitive Fields (password_hash, totp_secret) Exposed in Registration/Profile AP
- Server Version Disclosure in HTTP Response Headers
- Stored XSS in Transfer Description, Profile Name, and Address Book Fields
- TOTP Bypass on External Transfers - MFA Not Enforced Server-Side
- User Enumeration via Login Error Messages and Response Timing
- Verbose Error Messages Expose Internal File Paths and Stack Traces
- Weak MD5 Password Hashing for New User Registrations

**Titles unique to run 2 only:**

- Admin Database Reset Endpoint Allows Complete Data Destruction — The admin API e
- Admin JWT Token Accepted by User Banking API Endpoints (Privilege Boundary Bypas
- CORS Misconfiguration: Arbitrary Origin Reflection with Credentials Allowed
- Default Admin Credentials Allow Full Administrative Access
- IDOR in External Transfer Endpoint Allows Unauthorized Fund Transfers from Any A
- Missing Content-Security-Policy Header — The banking application does not set a 
- Potential stored XSS sink identified in JS source: .innerHTML
- Potential stored XSS sink identified in JS source: amount
- Potential stored XSS sink identified in JS source: converted_amount
- Potential stored XSS sink identified in JS source: pagination
- Potential stored XSS sink identified in JS source: payee_name
- Potential stored XSS sink identified in JS source: perspective
- Potential stored XSS sink identified in JS source: rate
- Sensitive Configuration Exposed via /api/health Endpoint
- Sensitive data exposed in API response
- TOTP 2FA Bypass: Transfer Check Endpoint Not Enforced by Transfer Execution Endp
- User Enumeration via Login Error Messages — The login endpoint returns different

---

## Consolidated Vulnerability Inventory

*Best-quality finding record per unique vulnerability (preferred: highest CVSS, fullest evidence).*

### Critical

**JWT Forgery Enables Full Account Takeover of Any User**  
OWASP: `A01` | CVSS: `9.8` | Status: `validating` | URL: `http://192.168.3.101/api/health`  
> Using the JWT secret obtained from /api/health, an attacker can forge a signed JWT for any user ID. The /api/profile and /api/accounts endpoints accept these forged tokens and return the targeted user's full profile and financial account data. Forged tokens for user IDs 1 and 2 both succeeded, retur

**Admin Database Reset Endpoint - Destructive Operation Without Adequate Protection**  
OWASP: `A01` | CVSS: `9.1` | Status: `unvalidated` | URL: `http://192.168.3.101/api/admin/system/reset`  
> The admin system reset endpoint accepts a POST request and resets the entire database to its initial state. The endpoint requires only a valid admin JWT token and a JSON body with {"confirm": "RESET"}. Combined with the weak admin credentials (admin/password123), any attacker who gains admin access 

**IDOR in External Transfer Endpoint Allows Unauthorized Fund Transfers from Any Account**  
OWASP: `A01` | CVSS: `9.1` | Status: `unvalidated` | URL: `http://192.168.3.101/api/transfers/external`  
> The /api/transfers/external endpoint does not verify that the from_account_id belongs to the authenticated user. Any authenticated user can specify any account ID as the source of a transfer, allowing them to drain funds from other users' accounts. The /api/transfers/own endpoint correctly enforces 

**JWT Signing Secret Exposed via /api/health Endpoint**  
OWASP: `A02` | CVSS: `9.8` | Status: `unvalidated` | URL: `http://192.168.3.101/api/health`  
> The /api/health endpoint is publicly accessible without authentication and returns the application's JWT signing secret (u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw) along with database credentials (host, name, user). An attacker can use this secret to forge arbitrary JWT tokens for an

**Sensitive Configuration Exposed via /api/health Endpoint**  
OWASP: `A02` | CVSS: `10` | Status: `unvalidated` | URL: `http://192.168.3.101/api/health`  
> The unauthenticated /api/health endpoint exposes the application's JWT signing secret, database hostname, database name, and database username. Any unauthenticated attacker can retrieve the JWT secret and use it to forge valid JWT tokens for any user ID, enabling complete account takeover for all us

**SQL Injection in Admin Customer Search Endpoint**  
OWASP: `A03` | CVSS: `9.1` | Status: `unvalidated` | URL: `http://192.168.3.101/api/admin/customers`  
> The admin customers search endpoint is vulnerable to SQL injection. The `search` query parameter is directly concatenated into a SQL query without parameterization. An attacker with admin access can extract the entire database, modify data, or potentially execute OS commands depending on MySQL confi

**Default Admin Credentials Allow Full Administrative Access**  
OWASP: `A07` | CVSS: `9.8` | Status: `unvalidated` | URL: `http://192.168.3.101/api/admin/auth/login`  
> The admin panel at /admin/ and its API at /api/admin/ are accessible using default credentials admin/admin123. Once authenticated, the admin can view all customer PII, all account balances, reset customer passwords, modify account balances, and delete customers.

**Default/Weak Admin Credentials - admin/password123**  
OWASP: `A07` | CVSS: `9.8` | Status: `unvalidated` | URL: `http://192.168.3.101/api/admin/auth/login`  
> The admin panel uses weak, easily guessable credentials (username: admin, password: password123). An unauthenticated attacker can gain full administrative access to the banking application by guessing these credentials. The admin panel provides access to all customer data, account balances, transact

### High

**IDOR on Profile Update Endpoint - Cross-User Profile Modification**  
OWASP: `A01` | CVSS: `8.1` | Status: `validating` | URL: `http://192.168.3.101/api/health`  
> The PUT /api/profile endpoint allows the authenticated session (user id=2, wei.zhang@example.com) to successfully update profile fields and receive a full profile response. The probe was labelled as user 2 attempting to update user 1's profile; the response confirms the update succeeded and returned

**Admin Can Reset Any Customer Password - Enables Account Takeover**  
OWASP: `A01` | CVSS: `8.1` | Status: `unvalidated` | URL: `http://192.168.3.101/api/admin/customers/22/reset-password`  
> The admin API provides an endpoint to reset any customer's password to an arbitrary value. An attacker with admin credentials can reset any customer's password and immediately log in as that customer, gaining full access to their banking accounts, transaction history, and funds. This endpoint requir

**Admin Database Reset Endpoint Allows Complete Data Destruction — The admin API exposes a database re**  
OWASP: `A01` | CVSS: `8.1` | Status: `unvalidated` | URL: `http://192.168.3.101/api/admin/system/reset`  
> The admin API exposes a database reset endpoint at /api/admin/system/reset that completely wipes and restores the database to its initial state. Combined with the default admin credentials (admin/admin123), any unauthenticated attacker can gain admin access and then destroy all customer data.

**Admin JWT Token Accepted by User Banking API Endpoints (Privilege Boundary Bypass)**  
OWASP: `A01` | CVSS: `8.8` | Status: `unvalidated` | URL: `http://192.168.3.101/api/transfers/own`  
> The admin JWT token (issued with iss: "BankOfEdAdmin") is accepted by the user-facing banking API endpoints including /api/profile, /api/accounts, /api/transfers/own, and /api/transfers/external. This means an admin can perform banking operations as any user, including initiating transfers from user

**Sensitive Fields (password_hash, totp_secret) Exposed in Registration/Profile API Response**  
OWASP: `A02` | CVSS: `7.5` | Status: `unvalidated` | URL: `http://192.168.3.101/api/auth/register`  
> The registration API response (and likely the profile API) returns sensitive fields including password_hash and totp_secret directly to the client. The password_hash appears to be an MD5 hash (32 hex characters), which is a weak hashing algorithm. Exposing these fields allows attackers to attempt of

**Weak MD5 Password Hashing for New User Registrations**  
OWASP: `A02` | CVSS: `7.5` | Status: `unvalidated` | URL: `http://192.168.3.101/api/auth/register`  
> Newly registered users have their passwords hashed with MD5 (a cryptographically broken algorithm), while existing users appear to use bcrypt. MD5 hashes can be cracked extremely rapidly using rainbow tables or GPU-accelerated brute force. The password_hash field is also exposed in API responses, ma

**SQL injection error disclosure**  
OWASP: `A03` | CVSS: `7.1` | Status: `confirmed` | URL: `http://192.168.3.101/api/admin/customers?search=test' UNION SELECT 1,2,3,4,5,6,7,8-- -`  
> An SQL injection probe produced a database error or server error indicative of unsafely handled input.

**Admin Can Directly Manipulate Customer Account Balances**  
OWASP: `A04` | CVSS: `8.7` | Status: `unvalidated` | URL: `http://192.168.3.101/api/admin/accounts/6/balance`  
> The admin API provides an endpoint to directly update any customer's account balance to an arbitrary value. An attacker with admin credentials can set any account balance to any amount, enabling financial fraud. The endpoint accepts a PUT request with a JSON body containing the new balance value.

**Manipulated AUD Exchange Rate Enables Fraudulent FX Conversions**  
OWASP: `A04` | CVSS: `7.5` | Status: `unvalidated` | URL: `http://192.168.3.101/api/fx/rates`  
> The AUD exchange rate has been manipulated to an extremely low value (0.00000001 instead of the expected ~1.0), causing the FX conversion to return astronomically incorrect values. Converting 1000 AUD to EUR returns 92,500,000,000 EUR instead of approximately 925 EUR. This manipulation could be expl

**TOTP 2FA Bypass: Transfer Check Endpoint Not Enforced by Transfer Execution Endpoint**  
OWASP: `A04` | CVSS: `7.5` | Status: `unvalidated` | URL: `http://192.168.3.101/api/transfers/external`  
> The /api/transfers/check endpoint indicates that TOTP (2FA) verification is required for manual external transfers. However, the /api/transfers/external endpoint does not enforce this requirement - transfers complete successfully without providing a TOTP code. The check endpoint is advisory only and

**TOTP Bypass on External Transfers - MFA Not Enforced Server-Side**  
OWASP: `A04` | CVSS: `8.1` | Status: `unvalidated` | URL: `http://192.168.3.101/api/transfers/external`  
> The /api/transfers/check endpoint correctly identifies that manual/external transfers require TOTP verification (returns requires_totp: true). However, the actual /api/transfers/external endpoint does not enforce this requirement - it processes the transfer even when no TOTP code is provided. The re

**CORS Misconfiguration: Arbitrary Origin Reflected with Credentials Allowed**  
OWASP: `A05` | CVSS: `8.1` | Status: `unvalidated` | URL: `http://192.168.3.101/api/profile`  
> The API reflects arbitrary Origin headers in the Access-Control-Allow-Origin response header while simultaneously setting Access-Control-Allow-Credentials: true. This allows any malicious website to make cross-origin authenticated requests to the API and read the responses, effectively bypassing the

**CORS Misconfiguration: Arbitrary Origin Reflection with Credentials Allowed**  
OWASP: `A05` | CVSS: `7.5` | Status: `unvalidated` | URL: `http://192.168.3.101/api/`  
> All API endpoints reflect any Origin header in the Access-Control-Allow-Origin response header while also setting Access-Control-Allow-Credentials: true. This allows any website to make credentialed cross-origin requests to the API and read the responses, enabling cross-origin data theft of authenti

**Database Credentials Exposed via /api/health Endpoint**  
OWASP: `A05` | CVSS: `7.5` | Status: `low_confidence` | URL: `http://192.168.3.101/api/health`  
> The /api/health endpoint exposes database connection credentials including the database host, database name, and database username. While the password is not exposed, this information significantly reduces the effort required for an attacker to target the database directly.

### Medium

**Unauthenticated access to protected endpoint**  
OWASP: `A01` | CVSS: `6.5` | Status: `confirmed` | URL: `http://192.168.3.101/banking/js/pages/accounts.js?v=20260213-2`  
> The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

**IDOR on Transaction Detail Endpoint - Cross-User Transaction Access**  
OWASP: `A01` | CVSS: `6.5` | Status: `unvalidated` | URL: `http://192.168.3.101/api/transactions/1`  
> The /api/transactions/{id} endpoint does not verify that the requested transaction belongs to the authenticated user. Any authenticated user can access any transaction by ID, exposing transaction details including amounts, account numbers, BSB codes, and transfer descriptions belonging to other user

**Sensitive data exposed in API response**  
OWASP: `A02` | CVSS: `6.5` | Status: `confirmed` | URL: `http://192.168.3.101/api/health`  
> The response contains field names commonly associated with secrets, hashes, tokens, debug state, or privileged metadata.

**Stored XSS in Transfer Description, Profile Name, and Address Book Fields**  
OWASP: `A03` | CVSS: `5.4` | Status: `unvalidated` | URL: `http://192.168.3.101/api/transfers/own`  
> The transfer description field accepts and stores arbitrary HTML/JavaScript without sanitization. The stored payload is returned in API responses and may be rendered in the banking application's transaction history view and potentially in the admin panel, leading to stored XSS.

**Admin JavaScript Source Files Publicly Accessible Without Authentication**  
OWASP: `A05` | CVSS: `5.3` | Status: `validating` | URL: `http://192.168.3.101/api/health`  
> The admin panel JavaScript files at /admin/js/pages/system.js, /admin/js/pages/fx-rates.js, and /admin/js/pages/customers.js are served with HTTP 200 to unauthenticated requests. These files reveal admin API endpoint paths, parameter names, operation logic, and UI structure.

**Server Version Disclosure in HTTP Response Headers**  
OWASP: `A05` | CVSS: `5.3` | Status: `validating` | URL: `http://192.168.3.101/api/health`  
> Every HTTP response from the server includes the header 'server: Apache/2.4.58 (Ubuntu)', disclosing the exact web server software name, version, and underlying operating system to unauthenticated requesters.

**Missing Content-Security-Policy Header — The banking application does not set a Content-Security-Pol**  
OWASP: `A05` | CVSS: `4.3` | Status: `unvalidated` | URL: `http://192.168.3.101/banking/`  
> The banking application does not set a Content-Security-Policy (CSP) header on any of its pages. Without CSP, the browser has no restrictions on which scripts can execute, making XSS attacks more impactful. The application also loads external scripts from cdn.tailwindcss.com without subresource inte

**Missing Security Headers on Banking Application HTML Pages**  
OWASP: `A05` | CVSS: `4.3` | Status: `unvalidated` | URL: `http://192.168.3.101/banking/`  
> The banking application HTML pages are missing several important security headers. The server version is exposed in the Server header. No Content-Security-Policy is present, which would help mitigate XSS attacks. The application runs over HTTP (not HTTPS), so HSTS is not applicable but the lack of H

**Verbose Error Messages Expose Internal File Paths and Stack Traces**  
OWASP: `A05` | CVSS: `5.3` | Status: `unvalidated` | URL: `http://192.168.3.101/api/transfers/check`  
> API error responses expose internal server details including full file paths, class names, method signatures, and stack traces. This information helps attackers understand the application's internal structure and identify potential attack vectors.

**User Enumeration via Login Error Messages and Response Timing**  
OWASP: `A07` | CVSS: `5.3` | Status: `unvalidated` | URL: `http://192.168.3.101/api/auth/login`  
> The login endpoint returns different error codes and messages depending on whether the email address exists in the system. This allows attackers to enumerate valid user accounts. Additionally, the response time differs significantly (122ms for valid email vs 12ms for non-existent), providing a timin

**User Enumeration via Login Error Messages — The login endpoint returns different error codes and mes**  
OWASP: `A07` | CVSS: `5.3` | Status: `unvalidated` | URL: `http://192.168.3.101/api/auth/login`  
> The login endpoint returns different error codes and messages depending on whether the email address exists in the system. This allows an attacker to enumerate valid email addresses by observing the error response.

### Info

**Potential stored XSS sink identified in JS source: .innerHTML**  
OWASP: `A03` | CVSS: `0` | Status: `unvalidated` | URL: `http://192.168.3.101/banking/js/utils.js?v=20260213-2`  
> Static analysis of http://192.168.3.101/banking/js/utils.js?v=20260213-2 found an unsanitized innerHTML assignment using the field '.innerHTML'. No escapeHtml(), DOMPurify, or equivalent sanitizer call was found in the surrounding context.  Code context: }, 3500);   }    /* ---- Modal ---- */   func

**Potential stored XSS sink identified in JS source: amount**  
OWASP: `A03` | CVSS: `0` | Status: `low_confidence` | URL: `http://192.168.3.101/banking/js/pages/dashboard.js?v=20260213-2`  
> Static analysis of http://192.168.3.101/banking/js/pages/dashboard.js?v=20260213-2 found an unsanitized innerHTML assignment using the field 'amount'. No escapeHtml(), DOMPurify, or equivalent sanitizer call was found in the surrounding context.  Code context: at) + '</p>' +           '</div>' +    

**Potential stored XSS sink identified in JS source: converted_amount**  
OWASP: `A03` | CVSS: `0` | Status: `low_confidence` | URL: `http://192.168.3.101/banking/js/pages/transfers.js?v=20260213-2`  
> Static analysis of http://192.168.3.101/banking/js/pages/transfers.js?v=20260213-2 found an unsanitized innerHTML assignment using the field 'converted_amount'. No escapeHtml(), DOMPurify, or equivalent sanitizer call was found in the surrounding context.  Code context: e;     var otherCurrency = (s

**Potential stored XSS sink identified in JS source: pagination**  
OWASP: `A03` | CVSS: `0` | Status: `low_confidence` | URL: `http://192.168.3.101/banking/js/pages/accounts.js?v=20260213-2`  
> Static analysis of http://192.168.3.101/banking/js/pages/accounts.js?v=20260213-2 found an unsanitized innerHTML assignment using the field 'pagination'. No escapeHtml(), DOMPurify, or equivalent sanitizer call was found in the surrounding context.  Code context: var pagination = res.data.pagination

**Potential stored XSS sink identified in JS source: payee_name**  
OWASP: `A03` | CVSS: `0` | Status: `low_confidence` | URL: `http://192.168.3.101/banking/js/pages/transfers.js?v=20260213-2`  
> Static analysis of http://192.168.3.101/banking/js/pages/transfers.js?v=20260213-2 found an unsanitized innerHTML assignment using the field 'payee_name'. No escapeHtml(), DOMPurify, or equivalent sanitizer call was found in the surrounding context.  Code context: try.nickname || entry.payee_name) +

**Potential stored XSS sink identified in JS source: perspective**  
OWASP: `A03` | CVSS: `0` | Status: `low_confidence` | URL: `http://192.168.3.101/banking/js/pages/dashboard.js?v=20260213-2`  
> Static analysis of http://192.168.3.101/banking/js/pages/dashboard.js?v=20260213-2 found an unsanitized innerHTML assignment using the field 'perspective'. No escapeHtml(), DOMPurify, or equivalent sanitizer call was found in the surrounding context.  Code context: U.formatCurrency(total);   }    fu

**Potential stored XSS sink identified in JS source: rate**  
OWASP: `A03` | CVSS: `0` | Status: `low_confidence` | URL: `http://192.168.3.101/banking/js/pages/transfers.js?v=20260213-2`  
> Static analysis of http://192.168.3.101/banking/js/pages/transfers.js?v=20260213-2 found an unsanitized innerHTML assignment using the field 'rate'. No escapeHtml(), DOMPurify, or equivalent sanitizer call was found in the surrounding context.  Code context: rrency) +             '<span class="text-

---

## Aggregate Baseline Metrics

*Values to beat after Phases 1–3 are implemented.*

| Metric | Baseline |
|---|---|
| Average findings/run | 48 (95 across 2 runs) |
| Confirmed rate | 20.0% |
| False-positive rate | 0.0% (0 explicit FP verdicts in these runs) |
| Low-confidence rate | 10.5% |
| Still-unresolved rate | 69.5% (validating + unvalidated) |
| Cross-run repeat rate | 7.5% |
| Unique vulnerabilities (combined) | 40 |

> **Time-to-confirmation**: Not measurable from export artifacts — no per-finding timestamp is stored.
> This metric needs a DB migration (add `confirmed_at` column to `scan_findings`) to be tracked in future runs.

---

## Notes

- Run 1 has `finding_source = unknown` throughout — the source tracking column was added after that run.
- Run 2 distinguishes `dynamic_scan` (LLM-driven) vs `deterministic_probe` (rule-based).
- The majority of unresolved findings are from the `validating` state in Run 1, meaning the validator
  was running (or was pending) when the export was taken. No explicit `false_positive` verdicts were
  recorded in either run — this limits the false-positive-rate baseline to 0%, which is likely an
  artefact of incomplete validation rather than genuine 0% FPs.
- Run 2's 12 info-level `Potential stored XSS sink` findings from the deterministic module received
  `low_confidence` or `unvalidated` status; these inflate totals significantly.

*Update this document with a third run after Phase 1 (Recon output contract) is complete.*
