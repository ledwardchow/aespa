# BankOfEd - Intentional Vulnerabilities (OWASP Top 10)

This document maps all intentionally introduced vulnerabilities for security training purposes.

---

## A01: Broken Access Control

### 1. IDOR in Transaction Detail
- **File:** `src/Controllers/TransactionController.php` — `show()`
- **Description:** Removed user ownership verification. Any authenticated user can view any transaction by its ID.
- **Exploit:** `GET /api/transactions/1` returns transaction details regardless of who owns it.

### 2. IDOR via Mass Assignment in Profile Update
- **File:** `src/Controllers/ProfileController.php` — `update()`
- **Description:** Accepts a `user_id` field in the request body, allowing any authenticated user to modify another user's profile.
- **Exploit:** `PUT /api/profile` with body `{"user_id": 2, "email": "attacker@evil.com"}` overwrites user 2's email.

### 23. IDOR on Source Account in Pay Anyone (External Transfer)
- **File:** `src/Services/TransferService.php` — `transferExternal()`
- **Description:** The `from_account_id` parameter is resolved with `Account::findById()` instead of `Account::findByIdAndUser()`. There is no ownership check, so any authenticated user can reference any account in the bank as the source of an external transfer, draining funds from accounts they do not own.
- **Exploit:** `POST /api/transfers/external` with body `{"from_account_id": 5, "to_bsb": "110-001", "to_account_number": "99999999", "amount": "500.00"}` — debits account 5 regardless of who owns it.

---

## A02: Cryptographic Failures

### 3. MD5 Password Hashing
- **File:** `src/Services/AuthService.php` — `hashPassword()`
- **Description:** Replaced bcrypt with MD5. MD5 is fast and trivially reversible via rainbow tables.
- **Exploit:** Obtain a password hash from the API (see #4), then crack it instantly with any MD5 lookup table.

### 4. Sensitive Data Exposure in API Responses
- **File:** `src/Models/User.php` — `toPublic()`
- **Description:** `password_hash` and `totp_secret` are included in every API response that returns user data (login, register, profile).
- **Exploit:** `GET /api/profile` returns the user's password hash and TOTP secret in plaintext.

---

## A03: Injection

### 5. SQL Injection in Admin Customer Search
- **File:** `src/Controllers/AdminUserController.php` — `index()`
- **Description:** The `$_GET['search']` parameter is directly concatenated into SQL without parameterization.
- **Exploit:** `GET /api/admin/customers?search=' UNION SELECT 1,password_hash,3,4,5,6,7 FROM admin_users--`

### 6. Stored XSS in Dashboard Transaction List
- **File:** `public/banking/js/pages/dashboard.js` — `renderTransactions()`
- **Description:** Transaction description rendered as raw HTML via `innerHTML` without `escapeHtml()`.
- **Exploit:** Send a transfer with `description: "<img src=x onerror=alert(document.cookie)>"` — executes when victim views dashboard.

### 7. Stored XSS in Account Detail Transaction Table
- **File:** `public/banking/js/pages/accounts.js` — `renderDetailTransactions()`
- **Description:** Same as #6 but in the account detail view's transaction table.

### 22. SQL Injection in Transaction Listing (Customer-Facing)
- **File:** `src/Models/Transaction.php` — `findByUser()`, called from `src/Controllers/TransactionController.php` — `index()`
- **Description:** The `sort` query parameter from `GET /api/transactions` is concatenated directly into the `ORDER BY` clause without sanitization or whitelist validation.
- **Exploit:** `GET /api/transactions?sort=created_at DESC; SELECT SLEEP(5)--` for time-based blind SQLi, or `GET /api/transactions?sort=(SELECT password_hash FROM users LIMIT 1)` for data extraction via error messages.

---

## A04: Insecure Design

### 8. TOTP Bypass on External Transfers
- **File:** `src/Services/TransferService.php` — `transferExternal()`
- **Description:** If TOTP is required but the user hasn't configured it, the transfer proceeds anyway. Additionally, if TOTP is configured but the code is simply omitted from the request, the transfer still goes through.
- **Exploit:** Send `POST /api/transfers/external` without a `totp_code` field — transfer completes without 2FA.

### 9. No Balance Check on External Transfers
- **File:** `src/Services/TransferService.php` — `transferExternal()`
- **Description:** The insufficient funds check was removed for external transfers, allowing unlimited overdraft.
- **Exploit:** Transfer $1,000,000 from an account with $0 balance — it succeeds.

---

## A05: Security Misconfiguration

### 10. Stack Trace Leakage in Error Responses
- **File:** `public/index.php` — exception handler
- **Description:** Full file paths, line numbers, and stack traces are exposed in 500 error responses.
- **Exploit:** Trigger any server error to see internal file structure and code paths.

### 11. Overly Permissive CORS
- **File:** `src/Middleware/CorsMiddleware.php` — `handle()`
- **Description:** Reflects any `Origin` header, allows credentials, and permits all headers. Enables cross-origin attacks from any domain.
- **Exploit:** A malicious site can make authenticated API requests on behalf of a logged-in user.

### 12. Unauthenticated Config/Secret Leakage
- **File:** `src/Router.php` — `health()`
- **Description:** `GET /api/health` is unauthenticated and exposes database credentials, JWT secret, PHP version, and server software.
- **Exploit:** `GET /api/health` returns `jwt_secret`, `db_host`, `db_user`, `db_name` in plaintext.

---

## A06: Vulnerable and Outdated Components

> These are intentionally **client-side** libraries so they are discoverable through
> dynamic/black-box testing: the exact version is shipped in the `<script src=...>` URL
> in `public/banking/index.html` and is flagged instantly by Retire.js, Burp, or the
> browser dev tools. Both libraries are genuinely used by the app, so they show up at
> runtime rather than being dead dependencies.

### 13. Outdated moment.js
- **File:** `public/banking/index.html` (loaded from CDN), used in `public/banking/js/utils.js` — `formatDate()` / `formatDateTime()`.
- **Description:** Loads `moment@2.29.1`, which has known vulnerabilities: CVE-2022-24785 (path traversal via crafted locale) and CVE-2022-31129 (ReDoS via long date strings). Fixed in 2.29.4.
- **Discovery:** View source / network tab shows `moment@2.29.1/moment.min.js`. Retire.js flags it immediately. The library is exercised whenever any date is rendered (dashboard, transactions, accounts).

### 14. Outdated jQuery
- **File:** `public/banking/index.html` (loaded from CDN), used in `public/banking/js/pages/profile.js` — `importAvatar()`.
- **Description:** Loads `jquery@3.3.1`, which has known vulnerabilities: CVE-2019-11358 (prototype pollution via `$.extend`) and CVE-2020-11022 / CVE-2020-11023 (XSS via `jQuery.htmlPrefilter` when passing untrusted HTML to DOM-manipulation methods like `.html()`). Fixed in 3.5.0.
- **Discovery:** View source / network tab shows `jquery@3.3.1/jquery.min.js`. Retire.js flags it immediately. It is exercised by the "Import profile photo from URL" feature on the Profile page, where the server-controlled response is passed into jQuery `.html()`.

---

## A07: Identification and Authentication Failures

### 15. User Enumeration on Login
- **File:** `src/Controllers/AuthController.php` — `login()`
- **Description:** Returns different error codes for "email not found" (`USER_NOT_FOUND`) vs "wrong password" (`WRONG_PASSWORD`), allowing attackers to enumerate valid accounts.
- **Exploit:** `POST /api/auth/login` with various emails — a `USER_NOT_FOUND` response confirms the email doesn't exist; `WRONG_PASSWORD` confirms it does.

### 16. Weak Password Policy
- **File:** `src/Controllers/AuthController.php` — `register()`
- **Description:** Minimum password length reduced from 8 to 1 character.
- **Exploit:** Register with password `a` — it succeeds.

### 17. No Brute-Force Protection
- **Description:** No rate limiting on login, registration, or TOTP verification endpoints.
- **Exploit:** Automated credential stuffing or TOTP brute-forcing with no throttling.

---

## A08: Software and Data Integrity Failures

### 18. JWT Signature Bypass
- **File:** `src/Services/AuthService.php` — `decodeToken()`
- **Description:** Replaced proper JWT verification with manual base64 decode. Only checks token expiration — completely ignores the cryptographic signature.
- **Exploit:** Forge a token: base64-encode `{"sub": 1, "exp": 9999999999}` as the payload, use any signature — it will be accepted as valid.

---

## A09: Security Logging and Monitoring Failures

### 19. Unauthenticated Full Data Export
- **File:** `src/Controllers/AdminUserController.php` — `exportAll()`, registered in `src/AdminRouter.php`
- **Description:** `GET /api/admin/export/users` dumps ALL users (including password hashes and TOTP secrets), all accounts, and all transactions — without requiring any authentication.
- **Exploit:** `GET /api/admin/export/users` — returns the entire database contents.

### 20. No Audit Logging
- **Description:** The application has zero logging for security-relevant events: failed logins, transfers, admin actions, password resets, TOTP changes, etc. There is no way to detect or investigate a breach.

---

## A10: Server-Side Request Forgery (SSRF)

### 21. Avatar Proxy Fetches Arbitrary URLs
- **File:** `src/Controllers/ProfileController.php` — `avatarProxy()`, registered in `src/Router.php`
- **UI entry point:** Profile page → "Profile Photo" card → "Import from URL" (`public/banking/index.html`, wired in `public/banking/js/pages/profile.js` — `importAvatar()`, calls `Api.importAvatar()` in `public/banking/js/api.js`).
- **Description:** `POST /api/profile/avatar` accepts an arbitrary `url` parameter and fetches it server-side with `file_get_contents()`. No URL validation, no scheme restriction, no SSRF protections. The submitted URL is persisted to `users.avatar_url` and **re-fetched server-side every time the Profile page loads**, so the SSRF fires repeatedly, not just on the initial import.
- **Discovery:** The feature is reachable from the normal UI, so the `POST /api/profile/avatar {"url": ...}` request appears in any intercepting proxy (Burp/ZAP) during normal use — a tester sees the server fetching a user-supplied URL and tries SSRF payloads.
- **Exploit:** `POST /api/profile/avatar` with body `{"url": "file:///etc/passwd"}` reads local files. `{"url": "http://169.254.169.254/latest/meta-data/"}` reads cloud instance metadata.

---

## Summary

| OWASP Category | Count | Vulnerability IDs |
|---|---|---|
| A01: Broken Access Control | 3 | #1, #2, #23 |
| A02: Cryptographic Failures | 2 | #3, #4 |
| A03: Injection | 4 | #5, #6, #7, #22 |
| A04: Insecure Design | 2 | #8, #9 |
| A05: Security Misconfiguration | 3 | #10, #11, #12 |
| A06: Vulnerable Components | 2 | #13, #14 |
| A07: Auth Failures | 3 | #15, #16, #17 |
| A08: Integrity Failures | 1 | #18 |
| A09: Logging Failures | 2 | #19, #20 |
| A10: SSRF | 1 | #21 |
| **Total** | **23** | |
