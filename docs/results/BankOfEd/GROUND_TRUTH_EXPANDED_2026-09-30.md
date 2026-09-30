# BankOfEd - Expanded ground truth (2026-09-30)

38 findings: the original 23 IDs plus 15 additions supported by recorded scan evidence and inspection of the scanned source. The original IDs and descriptions are retained. The additions describe the demonstrated behavior and required conditions.

This is a snapshot of saved results reviewed on 30 September 2026. No live target requests, new scans, transfers or password resets were performed. Bank of Ed run 268 was still running at inventory capture; only its finding available then was included.

Use the companion JSON for Benchmark Lab imports. It preserves the saved baseline entries exactly, including their existing severity and classification values. The Markdown importer defaults every severity to medium; this readable file is not a substitute for the JSON when severity matters. Evidence and limitations are in [GROUND_TRUTH_REVIEW_2026-09-30.md](GROUND_TRUTH_REVIEW_2026-09-30.md).

## A01: Broken Access Control

### 1. IDOR in Transaction Detail

- **File:** `src/Controllers/TransactionController.php`
- **Description:** Removed user ownership verification. Any authenticated user can view any transaction by its ID.
- **Exploit:** `GET /api/transactions/1`. `GET /api/transactions/1` returns transaction details regardless of who owns it.

### 2. IDOR via Mass Assignment in Profile Update

- **File:** `src/Controllers/ProfileController.php`
- **Description:** Accepts a `user_id` field in the request body, allowing any authenticated user to modify another user's profile.
- **Exploit:** `PUT /api/profile`. `PUT /api/profile` with body `{"user_id": 2, "email": "attacker@evil.com"}` overwrites user 2's email.

### 23. IDOR on Source Account in Pay Anyone (External Transfer)

- **File:** `src/Services/TransferService.php`
- **Description:** The `from_account_id` parameter is resolved with `Account::findById()` instead of `Account::findByIdAndUser()`. There is no ownership check, so any authenticated user can reference any account in the bank as the source of an external transfer, draining funds from accounts they do not own.
- **Exploit:** `POST /api/transfers/external`. `POST /api/transfers/external` with body `{"from_account_id": 5, "to_bsb": "110-001", "to_account_number": "99999999", "amount": "500.00"}` - debits account 5 regardless of who owns it.

## A02: Cryptographic Failures

### 3. MD5 Password Hashing

- **File:** `src/Services/AuthService.php`
- **Description:** Replaced bcrypt with MD5. MD5 is fast and trivially reversible via rainbow tables.
- **Exploit:** Obtain a password hash from the API (see #4), then crack it instantly with any MD5 lookup table.

### 4. Sensitive Data Exposure in API Responses

- **File:** `src/Models/User.php`
- **Description:** `password_hash` and `totp_secret` are included in every API response that returns user data (login, register, profile).
- **Exploit:** `GET /api/profile`. `GET /api/profile` returns the user's password hash and TOTP secret in plaintext.

### 26. Known default signing key permits administrator token forgery

- **File:** `config/admin.php` line 21, `src/Middleware/AdminAuthMiddleware.php` line 27, `src/Controllers/AdminAuthController.php` line 38
- **Description:** When ADMIN_JWT_SECRET is unset or unchanged, administrator JWTs are signed and verified with a key published in the source. An attacker can sign a token for an existing administrator without knowing the administrator password.
- **Exploit:** `GET /api/admin/customers; GET /api/admin/system/settings`. A token independently signed with the published default key and a valid administrator subject and issuer is accepted by protected admin APIs. An unsigned or incorrectly signed admin token is rejected, showing that the defect is the known key rather than missing signature verification. The supplied deployment has not replaced ADMIN_JWT_SECRET.
- **Evidence:** Recorded dynamic verification plus complete signing/verification source path. WFPS-002 records a forged default-key token reading customers and settings. The inspected middleware uses Firebase JWT verification and checks issuer, revocation and administrator existence.
- **Conditions:** Requires the default key to remain active. This is distinct from GT-18, which concerns customer JWTs and missing signature checks. No fresh token was sent during this review.

### 28. Active insurance SSO signing key is published in source

- **File:** `config/app.php` line 33, `src/Services/InsuranceService.php` line 23, `src/Services/InsuranceService.php` line 39
- **Description:** Insurance SSO assertions are signed with a fixed key published in the application when INSURANCE_SSO_SECRET is not replaced. The recorded scan verified a real issued assertion using that key, so anyone who knows it can create cryptographically valid assertions with chosen identity claims.
- **Exploit:** `GET /api/insurance/sso; GET /api/insurance/sso-redirect`. A real SSO assertion issued by BankOfEd verifies with the published default HMAC key. The source signs user identity claims with that key when INSURANCE_SSO_SECRET is unset. For a claim of downstream account takeover, additionally show that the receiving insurance application accepts a forged identity assertion.
- **Evidence:** WFPS-008 records signature_valid=true when verifying a live SSO redirect assertion with the known fallback. The signing path was independently inspected.
- **Conditions:** The established finding is compromised assertion authenticity while the default key is active. Acceptance of a forged assertion and account takeover in FACE Insurance were not demonstrated in the reviewed evidence. Do not score that additional consequence as proven.

### 29. Persistent storage and routine disclosure of card CVV and full card details

- **File:** `install/schema.sql` line 32, `src/Models/Account.php` line 111, `src/Controllers/AccountController.php` line 18
- **Description:** Credit-card records retain the CVV in a normal database column. The account serializer returns the stored CVV, full card number and expiry in routine customer account responses and account-creation responses.
- **Exploit:** `GET /api/accounts; GET /api/accounts/{id}; POST /api/accounts`. An ordinary authenticated account response contains the full card number, expiry and stored CVV. Source inspection shows the CVV is persistently stored and returned by Account::toPublic. Separate customers or newly created cards return their own values, ruling out a single placeholder.
- **Evidence:** KOWT-009 records full card fields on an ordinary accounts request. WFPS-102 records them on new-card creation. KAZU-023 validator reasoning independently checked two customers. Source confirms storage and serialization.
- **Conditions:** Do not claim this endpoint is unauthenticated or that ownership checks are missing. The new entry concerns retained CVV and its routine serialization; displaying a virtual card number to its owner alone is not enough. KAZU-023 contains an unrelated pasted 422 request, so that request is not used as proof.

## A03: Injection

### 5. SQL Injection in Admin Customer Search

- **File:** `src/Controllers/AdminUserController.php`
- **Description:** The `$_GET['search']` parameter is directly concatenated into SQL without parameterization.
- **Exploit:** `GET /api/admin/customers?search=`. `GET /api/admin/customers?search=' UNION SELECT 1,password_hash,3,4,5,6,7 FROM admin_users--`

### 6. Stored XSS in Dashboard Transaction List

- **File:** `public/banking/js/pages/dashboard.js`
- **Description:** Transaction description rendered as raw HTML via `innerHTML` without `escapeHtml()`.
- **Exploit:** Send a transfer with `description: "<img src=x onerror=alert(document.cookie)>"` - executes when victim views dashboard.

### 7. Stored XSS in Account Detail Transaction Table

- **File:** `public/banking/js/pages/accounts.js`
- **Description:** Same as #6 but in the account detail view's transaction table.
- **Exploit:** 

### 22. SQL Injection in Transaction Listing (Customer-Facing)

- **File:** `src/Models/Transaction.php`, `src/Controllers/TransactionController.php`
- **Description:** The `sort` query parameter from `GET /api/transactions` is concatenated directly into the `ORDER BY` clause without sanitization or whitelist validation.
- **Exploit:** `GET /api/transactions?sort=created_at`. `GET /api/transactions?sort=created_at DESC; SELECT SLEEP(5)--` for time-based blind SQLi, or `GET /api/transactions?sort=(SELECT password_hash FROM users LIMIT 1)` for data extraction via error messages.

### 33. Stored XSS through customer names in administrator Delete controls

- **File:** `src/Controllers/AuthController.php` line 19, `public/admin/js/pages/customers.js` line 106, `public/admin/js/pages/customers.js` line 161
- **Description:** A customer can store a crafted first or last name that becomes executable JavaScript in the administrator customer-detail Delete button. Execution occurs when an administrator clicks that button.
- **Exploit:** `POST /api/auth/register; PUT /api/profile; admin customer detail Delete button`. An unprivileged customer stores a short crafted name through registration or profile update. The admin detail renderer produces an onclick string that contains the decoded JavaScript breakout. Clicking Delete in an authenticated admin browser executes a harmless DOM marker in the admin origin.
- **Evidence:** WFPS-025 records admin Delete execution and a DOM marker. SCOE-043 traces the complete customer-to-admin storage/render path. Independent source inspection confirms the escaping order and innerHTML assignment.
- **Conditions:** Requires an administrator to view the affected customer and click Delete. Ordinary escaped name text in the table is not the vulnerable sink. Do not count registration and profile update as separate bugs.

### 34. Stored XSS through account names in administrator Edit Balance controls

- **File:** `src/Controllers/AccountController.php` line 26, `public/admin/js/pages/accounts.js` line 50, `public/admin/js/pages/accounts.js` line 54
- **Description:** A customer can store a crafted account name that executes JavaScript in the administrator origin when an administrator clicks Edit Balance for that account.
- **Exploit:** `POST /api/accounts; admin accounts Edit Balance button`. A regular customer creates an account with a crafted name accepted by the length validation. The admin accounts page loads that persisted name and constructs the vulnerable inline handler. Clicking Edit Balance executes a harmless DOM marker in the admin browser.
- **Evidence:** WFPS-112 records account 110, the decoded live onclick value, and a successful admin DOM marker. SCOE-065 independently traces public registration, customer account creation and admin rendering.
- **Conditions:** Requires an administrator click. This is distinct from customer-name XSS because a different stored field and renderer need repair. It does not establish unauthenticated balance editing.

### 35. Stored XSS through address-book nicknames in Delete controls

- **File:** `src/Controllers/AddressBookController.php` line 26, `public/banking/js/pages/addressbook.js` line 64, `public/banking/js/pages/addressbook.js` line 70
- **Description:** A crafted nickname stored in an account's address book executes JavaScript when that account's user clicks Delete. A victim must be induced to enter/store the nickname; an attacker cannot directly write another user's address book through this finding.
- **Exploit:** `POST /api/address-book; PUT /api/address-book/{id}; address-book Delete button`. The nickname is stored in the acting user's address book and retrieved unchanged. HTML parsing turns the encoded quote into a JavaScript-string breakout in the Delete handler. Clicking Delete in that user's browser executes a harmless DOM marker.
- **Evidence:** WFPS-110 records persisted entry 23 and a successful DOM marker after clicking Delete. SCOE-064 confirms ownership scoping and the executable sink.
- **Conditions:** User-assisted/self-XSS with a real execution result, not a proven cross-customer write. Severity is limited accordingly. Do not conflate it with historical unproven address-book IDOR claims or escaped payee text.

### 36. Avatar import parses untrusted URL and Content-Type as page HTML

- **File:** `src/Controllers/ProfileController.php` line 86, `src/Controllers/ProfileController.php` line 95, `src/Controllers/ProfileController.php` line 102, `public/banking/js/pages/profile.js` line 138, `public/banking/js/pages/profile.js` line 142, `public/banking/js/app.js` line 72
- **Description:** The avatar UI inserts the returned source URL and avatar data URL into HTML strings. A URL fragment containing markup can execute in the importing user's profile. A malicious avatar server can also put quote/handler characters in its Content-Type, which is copied into avatar_data and parsed in the profile/sidebar image HTML.
- **Exploit:** `POST /api/profile/avatar; banking profile/avatar rendering`. A successful import preserves a raw HTML payload in source_url and persists it in avatar_url. Reloading the profile parses the payload and executes a harmless DOM marker. For the Content-Type variant, trace the unfiltered response header into avatar_data and into the image HTML sink; base64 encoding of the body does not encode the MIME prefix.
- **Evidence:** KOWT-026 records successful URL-fragment import, persistence and browser DOM execution. SGBH-056/SCOE-057 trace the remote-header variant; independent source inspection confirms both unsafe HTML sinks.
- **Conditions:** The recorded browser execution covers source_url. The Content-Type variant has complete static evidence but no independent recorded runtime execution used here. Both require the victim to import the attacker-controlled URL/content. This is distinct from SSRF/local-file reading in GT-21 and from merely detecting jQuery's version in GT-14.

## A04: Insecure Design

### 8. TOTP Bypass on External Transfers

- **File:** `src/Services/TransferService.php`
- **Description:** If TOTP is required but the user hasn't configured it, the transfer proceeds anyway. Additionally, if TOTP is configured but the code is simply omitted from the request, the transfer still goes through.
- **Exploit:** `POST /api/transfers/external`. Send `POST /api/transfers/external` without a `totp_code` field - transfer completes without 2FA.

### 9. No Balance Check on External Transfers

- **File:** `src/Services/TransferService.php`
- **Description:** The insufficient funds check was removed for external transfers, allowing unlimited overdraft.
- **Exploit:** Transfer $1,000,000 from an account with $0 balance - it succeeds.

### 30. Customers can originate uncapped loans with immediate cash disbursement

- **File:** `src/Controllers/AccountController.php` line 88, `src/Controllers/AccountController.php` line 143
- **Description:** An ordinary customer can choose a positive loan amount and immediately receive the proceeds in an owned transaction account. There is no server-side borrowing cap or approval stage before the cash is posted.
- **Exploit:** `POST /api/accounts`. A regular customer requests a loan amount well beyond normal product limits and receives an active loan. A follow-up read shows the completed disbursement transaction and the corresponding increase in the destination account balance. The request requires no prior approval and source inspection shows no borrowing cap.
- **Evidence:** WFPS-095 records a 1,000,000 loan and validator verification of a further 999,999,999,999.99 disbursement. QZDR-016 checked both Zoe's loan and the credited transaction account. KAZU-013 corroborates another persisted disbursement.
- **Conditions:** The destination ownership/type checks work. Creating a loan account alone would be weaker evidence; the posted cash is decisive. The maximum is still bounded by storage/numeric limits, so do not describe literally infinite borrowing.

### 31. Customers can choose an uncapped spendable credit-card limit

- **File:** `src/Controllers/AccountController.php` line 40, `src/Controllers/AccountController.php` line 61, `src/Controllers/AccountController.php` line 127
- **Description:** Customers can supply their own positive credit_limit when opening a credit card. The application uses that value as both the product limit and available balance without a server-side cap or approval stage.
- **Exploit:** `POST /api/accounts`. A regular or newly registered customer creates a card with an unusually large chosen limit. The server persists the requested credit_limit and an equal available balance. Source inspection shows the chosen value directly funds the card and no product cap/approval step intervenes.
- **Evidence:** WFPS-102 records a 999,999,999 limit and a follow-up account read. RIAG-016 records a newly registered customer creating a 1,000,000 limit after supplying the required account name.
- **Conditions:** Count unlimited self-issued credit once, rather than separate findings for default-limit issuance, no underwriting and caller-chosen limits. Full card details are covered separately by GT-29.

### 32. Own-account transfers ignore credit-card available funds and limits

- **File:** `src/Services/TransferService.php` line 104, `src/Services/TransferService.php` line 111
- **Description:** A customer can transfer from an owned credit card to another owned account even when the transfer exceeds available credit. A completed transfer can leave the card well beyond its stated limit while crediting spendable funds elsewhere.
- **Exploit:** `POST /api/transfers/own`. A customer uses a credit-card source and another account belonging to the same customer. The requested amount exceeds available credit and the endpoint still completes the debit/credit. A follow-up transfer succeeds even after the card balance is already beyond its credit_limit.
- **Evidence:** WFPS-022 records a 100,000 transfer from a card with about 24,990 available credit, producing -75,011; the validator repeated a further debit at -75,012 against a 25,000 limit. Source confirms cards are excluded from the funds check.
- **Conditions:** Ownership checks are present. This is a separate operation from the external-transfer overdraft in GT-9 and does not require concurrent requests.

### 37. Concurrent payments and own-account transfers can spend the same balance twice

- **File:** `src/Controllers/PaymentController.php` line 91, `src/Controllers/PaymentController.php` line 197, `src/Services/TransferService.php` line 104, `src/Models/Account.php` line 94, `install/schema.sql` line 31
- **Description:** These handlers check a fetched balance before starting the debit transaction. Concurrent requests can both pass that check and later commit unconditional debits, overdrawing a card, settlement account, or owned transaction/FX account.
- **Exploit:** `POST /api/payments/process; POST /api/payments/transfer; POST /api/transfers/own`. Trace each reachable handler from account lookup and funds comparison to a later transaction and unconditional balance update. Confirm that schema/transaction helpers provide no balance floor, row lock or conditional debit. For dynamic confirmation, arrange overlapping requests with starting balance B and two debits A where A <= B < 2A; show both committed transactions and the negative final balance.
- **Evidence:** Complete static evidence. The source places reads/checks before beginTransaction, uses balance = balance + ? WHERE id = ?, and declares a signed DECIMAL balance without a nonnegative constraint. Row serialization applies both deltas; it does not repeat the earlier check. SGBH-046 also includes the own-transfer trace.
- **Conditions:** No concurrent exploit was executed in this review and no dynamic double-spend result is claimed. Requires overlapping requests and appropriate customer/machine credentials. Group the three instances because they share the same unchecked-debit invariant. External-transfer missing checks remain GT-9; credit-card own transfers that skip checks entirely remain GT-32.

## A05: Security Misconfiguration

### 10. Stack Trace Leakage in Error Responses

- **File:** `public/index.php`
- **Description:** Full file paths, line numbers, and stack traces are exposed in 500 error responses.
- **Exploit:** Trigger any server error to see internal file structure and code paths.

### 11. Overly Permissive CORS

- **File:** `src/Middleware/CorsMiddleware.php`
- **Description:** Reflects any `Origin` header, allows credentials, and permits all headers. Enables cross-origin attacks from any domain.
- **Exploit:** A malicious site can make authenticated API requests on behalf of a logged-in user.

### 12. Unauthenticated Config/Secret Leakage

- **File:** `src/Router.php`
- **Description:** `GET /api/health` is unauthenticated and exposes database credentials, JWT secret, PHP version, and server software.
- **Exploit:** `GET /api/health`. `GET /api/health` returns `jwt_secret`, `db_host`, `db_user`, `db_name` in plaintext.

## A06: Vulnerable and Outdated Components

### 13. Outdated moment.js

- **File:** `public/banking/index.html`, `public/banking/js/utils.js`
- **Description:** Loads `moment@2.29.1`, which has known vulnerabilities: CVE-2022-24785 (path traversal via crafted locale) and CVE-2022-31129 (ReDoS via long date strings). Fixed in 2.29.4.
- **Exploit:** View source / network tab shows `moment@2.29.1/moment.min.js`. Retire.js flags it immediately. The library is exercised whenever any date is rendered (dashboard, transactions, accounts).

### 14. Outdated jQuery

- **File:** `public/banking/index.html`, `public/banking/js/pages/profile.js`
- **Description:** Loads `jquery@3.3.1`, which has known vulnerabilities: CVE-2019-11358 (prototype pollution via `$.extend`) and CVE-2020-11022 / CVE-2020-11023 (XSS via `jQuery.htmlPrefilter` when passing untrusted HTML to DOM-manipulation methods like `.html()`). Fixed in 3.5.0.
- **Exploit:** View source / network tab shows `jquery@3.3.1/jquery.min.js`. Retire.js flags it immediately. It is exercised by the "Import profile photo from URL" feature on the Profile page, where the server-controlled response is passed into jQuery `.html()`.

## A07: Identification and Authentication Failures

### 15. User Enumeration on Login

- **File:** `src/Controllers/AuthController.php`
- **Description:** Returns different error codes for "email not found" (`USER_NOT_FOUND`) vs "wrong password" (`WRONG_PASSWORD`), allowing attackers to enumerate valid accounts.
- **Exploit:** `POST /api/auth/login`. `POST /api/auth/login` with various emails - a `USER_NOT_FOUND` response confirms the email doesn't exist; `WRONG_PASSWORD` confirms it does.

### 16. Weak Password Policy

- **File:** `src/Controllers/AuthController.php`
- **Description:** Minimum password length reduced from 8 to 1 character.
- **Exploit:** Register with password `a` - it succeeds.

### 17. No Brute-Force Protection

- **File:** 
- **Description:** No rate limiting on login, registration, or TOTP verification endpoints.
- **Exploit:** Automated credential stuffing or TOTP brute-forcing with no throttling.

### 24. Active default administrator credentials

- **File:** `install/admin_schema.sql` line 24, `install/seed.sql` line 233, `src/Controllers/AdminAuthController.php` line 15
- **Description:** The shipped admin account accepts admin / admin123 and issues a working administrator token. Anyone who can reach the deployed admin login can gain administrator access while these credentials remain active.
- **Exploit:** `POST /api/admin/auth/login`. An anonymous, cookie-free login using admin / admin123 returns an administrator token. The same username with an incorrect password is rejected. The issued token can read a protected administrator endpoint that rejects anonymous requests.
- **Evidence:** Recorded dynamic verification and source inspection. KOWT-031 used anonymous login and an incorrect-password control; KAZU-022 also used the issued token against protected customer/account lists.
- **Conditions:** Applies when seeded credentials have not been changed. Count the password once, rather than counting every admin action it unlocks.

### 25. Active shared default customer password

- **File:** `install/seed.sql` line 16, `src/Controllers/AuthController.php` line 47
- **Description:** Multiple seeded customer accounts accept the publicly documented password password. An attacker who knows a seeded email can obtain that customer's banking session.
- **Exploit:** `POST /api/auth/login`. Anonymous login with password password succeeds for at least two distinct seeded customers. An incorrect password is rejected for each customer. The responses identify different customers and issue usable session credentials.
- **Evidence:** Recorded dynamic verification and source inspection. KOWT-032 tested Amelia and Zoe separately; wrong-password controls returned 401 and the correct default returned distinct IDs 1 and 3.
- **Conditions:** This is separate from the registration password-length policy. Limited to seeded accounts whose passwords are unchanged.

### 27. Public default machine token grants access to payment APIs

- **File:** `config/app.php` line 35, `src/Models/MachineToken.php` line 23, `public/admin/index.html` line 219, `src/Middleware/MachineAuthMiddleware.php` line 21, `src/Controllers/PaymentController.php` line 139
- **Description:** A fixed machine credential is published in configuration, seed data and the shipped admin HTML. The credential is accepted by the machine-authenticated payment APIs, including transfers from the FACE Insurance settlement account.
- **Exploit:** `POST /api/payments/transfer; POST /api/payments/process`. An anonymous response for the shipped admin HTML contains the actual machine token, or the default configuration and seed credential are shown to be active. Missing or incorrect machine credentials are rejected. Using the published token, with no customer or admin session, completes a payment or a transfer from an authorized settlement account.
- **Evidence:** ULJJ-006 records a cookie-free ranged HTML response containing the token; source line 219 contains that literal value. QZDR-013 records a completed settlement-account transfer and a 401 without the token. WFPS-004 records an accepted card payment.
- **Conditions:** The payment APIs intentionally use machine authentication. The defect is public exposure of a working credential. Do not claim unrestricted access to every source account: the default token is scoped in PaymentController::transfer. Some later validators deny the static disclosure; that conflicts with the supplied source and the earlier anonymous response. Admin-only settings display alone is not a separate finding.

### 38. Administrator password resets leave existing customer sessions valid

- **File:** `src/Controllers/AdminUserController.php` line 145, `src/Controllers/AdminUserController.php` line 165, `src/Middleware/AuthMiddleware.php` line 23, `src/Services/AuthService.php` line 35, `config/app.php` line 25
- **Description:** Resetting a customer password changes only password_hash. Previously issued, unexpired, non-revoked customer JWTs continue to authorize that customer's requests, including a stolen session the reset was intended to recover from.
- **Exploit:** `POST /api/admin/customers/{id}/reset-password; subsequent protected customer request`. Trace resetPassword to its password_hash-only UPDATE and verify there is no user session invalidation. Trace customer authentication and confirm it checks expiration, token-specific revocation and user existence, with no password-change cutoff. For dynamic confirmation, log in before an admin reset; after the reset verify the old password fails but the original unexpired token still accesses a protected endpoint.
- **Evidence:** Complete static evidence. ILTJ-025 and NMMU-028 independently trace reset and authentication. Source confirms only logout revokes a presented jti and reset has no user-wide session cutoff.
- **Conditions:** No fresh password reset was performed. The static path establishes continued acceptance of an existing valid token for up to the configured 24-hour expiry. This finding does not rely on GT-18 or on forging a replacement jti.

## A08: Software and Data Integrity Failures

### 18. JWT Signature Bypass

- **File:** `src/Services/AuthService.php`
- **Description:** Replaced proper JWT verification with manual base64 decode. Only checks token expiration - completely ignores the cryptographic signature.
- **Exploit:** Forge a token: base64-encode `{"sub": 1, "exp": 9999999999}` as the payload, use any signature - it will be accepted as valid.

## A09: Security Logging and Monitoring Failures

### 19. Unauthenticated Full Data Export

- **File:** `src/Controllers/AdminUserController.php`, `src/AdminRouter.php`
- **Description:** `GET /api/admin/export/users` dumps ALL users (including password hashes and TOTP secrets), all accounts, and all transactions - without requiring any authentication.
- **Exploit:** `GET /api/admin/export/users`. `GET /api/admin/export/users` - returns the entire database contents.

### 20. No Audit Logging

- **File:** 
- **Description:** The application has zero logging for security-relevant events: failed logins, transfers, admin actions, password resets, TOTP changes, etc. There is no way to detect or investigate a breach.
- **Exploit:** 

## A10: Server-Side Request Forgery (SSRF)

### 21. Avatar Proxy Fetches Arbitrary URLs

- **File:** `src/Controllers/ProfileController.php`, `src/Router.php`
- **Description:** `POST /api/profile/avatar` accepts an arbitrary `url` parameter and fetches it server-side with `file_get_contents()`. No URL validation, no scheme restriction, no SSRF protections. The submitted URL is persisted to `users.avatar_url` and re-fetched server-side every time the Profile page loads, so the SSRF fires repeatedly, not just on the initial import.
- **Exploit:** `POST /api/profile/avatar`. `POST /api/profile/avatar` with body `{"url": "file:///etc/passwd"}` reads local files. `{"url": "http://169.254.169.254/latest/meta-data/"}` reads cloud instance metadata. The feature is reachable from the normal UI, so the `POST /api/profile/avatar {"url": ...}` request appears in any intercepting proxy (Burp/ZAP) during normal use - a tester sees the server fetching a user-supplied URL and tries SSRF payloads. Profile page → "Profile Photo" card → "Import from URL" (`public/banking/index.html`, wired in `public/banking/js/pages/profile.js` - `importAvatar()`, calls `Api.importAvatar()` in `public/banking/js/api.js`).

