# SAST Report: SAST – BankOfEd-main.zip

- Exported: 27/09/2026, 12:33:41
- Total issues: 28

## Issue Summary

| # | Severity | Candidate | Confidence | Validation | Reportable | Location |
|---:|---|---|---:|---|---|---|
| 1 | HIGH | Unauthenticated health endpoint exposes JWT signing secret and database configuration | 99% | confirmed | Yes | BankOfEd-main/src/Router.php:27 |
| 2 | HIGH | Public health endpoint exposes the JWT signing secret | 99% | inconclusive | No | BankOfEd-main/src/Router.php:32 |
| 3 | HIGH | Customer authentication accepts unsigned forged JWTs | 99% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:58 |
| 4 | HIGH | Hard-coded default admin JWT secret enables admin token forgery | 94% | inconclusive | No | BankOfEd-main/config/admin.php:21 |
| 5 | HIGH | Public health endpoint exposes the customer JWT signing secret | 99% | confirmed | Yes | BankOfEd-main/src/Router.php:32 |
| 6 | HIGH | Published default machine token authorizes money transfers | 99% | confirmed | Yes | BankOfEd-main/config/app.php:35 |
| 7 | HIGH | Hard-coded SSO signing secret permits forged insurance identities | 90% | confirmed | Yes | BankOfEd-main/config/app.php:33 |
| 8 | HIGH | SQL injection in admin customer search | 99% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:21 |
| 9 | HIGH | Stored XSS in admin accounts table through account name | 99% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/accounts.js:54 |
| 10 | HIGH | Stored XSS in admin customer detail through customer name | 99% | confirmed | Yes | BankOfEd-main/public/admin/js/pages/customers.js:161 |
| 11 | HIGH | Stored XSS in account transaction history | 99% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/accounts.js:171 |
| 12 | LOW | Insurance SSO tab can navigate the banking tab | 86% | confirmed | Yes | BankOfEd-main/public/banking/js/app.js:105 |
| 13 | HIGH | Stored XSS in dashboard transaction descriptions | 99% | confirmed | Yes | BankOfEd-main/public/banking/js/pages/dashboard.js:98 |
| 14 | HIGH | SQL injection in admin customer search count query | 99% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:28 |
| 15 | HIGH | SQL injection in admin customer search result query | 99% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:33 |
| 16 | HIGH | External transfer debits an account without checking ownership | 99% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:95 |
| 17 | HIGH | Credit-card CVVs are stored and returned in plaintext | 99% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:75 |
| 18 | HIGH | Unauthenticated admin export exposes all banking records | 99% | confirmed | Yes | BankOfEd-main/src/Controllers/AdminUserController.php:174 |
| 19 | HIGH | Hardcoded fallback machine token permits unauthorized payment requests | 99% | confirmed | Yes | BankOfEd-main/src/Middleware/MachineAuthMiddleware.php:19 |
| 20 | HIGH | Avatar proxy allows SSRF and local file disclosure | 99% | confirmed | Yes | BankOfEd-main/src/Controllers/ProfileController.php:80 |
| 21 | MEDIUM | Passwords are stored with unsalted MD5 | 99% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:24 |
| 22 | HIGH | Hardcoded admin JWT secret enables token forgery | 0% | pending | No | BankOfEd-main/src/Middleware/AdminAuthMiddleware.php:27 |
| 23 | MEDIUM | Login accepts weak MD5 password hashes | 98% | confirmed | Yes | BankOfEd-main/src/Services/AuthService.php:31 |
| 24 | HIGH | External transfer debits arbitrary customer accounts | 99% | confirmed | Yes | BankOfEd-main/src/Models/Account.php:13 |
| 25 | HIGH | External transfer can debit another user's account | 99% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:174 |
| 26 | HIGH | Hard-coded fallback machine token authorizes payment transfers | 99% | confirmed | Yes | BankOfEd-main/src/Models/MachineToken.php:23 |
| 27 | HIGH | SQL injection through transaction sort parameter | 99% | confirmed | Yes | BankOfEd-main/src/Models/Transaction.php:40 |
| 28 | HIGH | Required TOTP can be omitted from external transfers | 99% | confirmed | Yes | BankOfEd-main/src/Services/TransferService.php:231 |

## 1. Unauthenticated health endpoint exposes JWT signing secret and database configuration

- Lead reference: NIWE-001
- Category: A02
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:27
- Fingerprint: 4e4d19aa796831120134a9d770ba6777d290b4ea106afda813734df9fd5ace05

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 83,
  "symbol": "Router::dispatch",
  "input": "Unauthenticated GET /api/health"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 27,
  "symbol": "Router::health",
  "operation": "Returns runtime secrets and database configuration in JSON"
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
    "External unauthenticated caller sends GET /api/health.",
    "Router registers the health route with auth=false, so no customer or admin authentication control is applied.",
    "Router::health loads runtime database settings and the JWT signing secret.",
    "Response::success directly JSON-encodes db_host, db_name, db_user, and jwt_secret into the HTTP response.",
    "The caller learns database configuration and the HS256 secret, which can be used to create apparently valid customer JWTs where signature validation is used."
  ],
  "impact": "Unauthenticated disclosure of sensitive runtime configuration and the customer JWT signing credential, enabling customer impersonation and access to protected banking functions.",
  "severity_reasoning": "High because the endpoint is remotely reachable without authentication and exposes a signing secret that protects customer identities, along with database connection details.",
  "dynamic_test": "From a logged-out client, request GET /api/health and verify whether the JSON response contains db_host, db_name, db_user, and jwt_secret. If returned, use only a test account and isolated environment to mint an HS256 token with that secret and check whether a protected customer endpoint accepts it."
}
```

#### Validator reasoning

Confirmed. public/.htaccess rewrites an otherwise-unhandled /api/health request to public/index.php. That entry point sends non-admin API requests to Router::dispatch. The GET /api/health route is registered with auth=false, and dispatch invokes AuthMiddleware or MachineAuthMiddleware only for routes marked true or machine. Router::health then requires config/app.php and passes db_host, db_name, db_user, and jwt_secret directly to Response::success. Response::success places the data in the response array and echoes json_encode without redaction, so the values reach an unauthenticated HTTP response. app.php reads JWT_SECRET from the environment or falls back to the known development secret, and sets HS256. No environment check, authorization gate, or output filtering blocks this path. Adjacent AuthService code also uses the same app config for token creation; its decodeToken currently does not verify the JWT signature, which does not weaken the confirmed secret-disclosure finding.

#### Code evidence

```
Router::health() requires config/app.php and passes 'db_host', 'db_name', 'db_user', and 'jwt_secret' into Response::success (Router.php:24-34). dispatch() registers GET /api/health with 'auth' => false (Router.php:83). Response::success echoes json_encode(['success' => true, 'data' => $data, ...]) (src/Helpers/Response.php:9-15). config/app.php sources jwt_secret from JWT_SECRET and otherwise uses a known default.
```

## 2. Public health endpoint exposes the JWT signing secret

- Lead reference: NIWE-002
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: inconclusive
- Reportable: No
- Location: BankOfEd-main/src/Router.php:32
- Fingerprint: f8536a99d705ab3e2c4606bb8f6634306a54425ba881390999b2a3ec942d29cc

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 25,
  "symbol": "configuration return array",
  "input": "JWT_SECRET environment variable or hard-coded fallback"
}
```

#### Controls encountered

```
[
  "No authentication is applied to /api/health",
  "The admin surface uses a separate ADMIN_JWT_SECRET, so this leak is scoped to application JWTs"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 32,
  "symbol": "Router::health",
  "operation": "unauthenticated JSON response exposes jwt_secret"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Independent validator failed before closing this candidate."
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

Validator failed: {"error": {"message": "Reconnecting... 2/5", "codexErrorInfo": {"responseStreamDisconnected": {"httpStatusCode": null}}, "additionalDetails": "stream disconnected before completion: failed to lookup address information: nodename nor servname provided, or not known"}, "willRetry": true, "threadId": "01a054fe-56c9-7381-82f2-a59390e01d2b", "turnId": "01a054fe-56e2-7f71-8c19-dffbb893d09b"}

#### Code evidence

```
Router::health loads config/app.php and includes 'jwt_secret' => $config['jwt_secret'] in Response::success. Router::dispatch registers GET /api/health with 'auth' => false at line 87. config/app.php sources jwt_secret from JWT_SECRET and falls back to a hard-coded value; AuthService::createToken uses that secret with HS256.
```

## 3. Customer authentication accepts unsigned forged JWTs

- Lead reference: NIWE-003
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:58
- Fingerprint: a41d295cd31a529d4e57851fade4f40e320c2bc2bff0c427d254966d96594bf9

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AuthMiddleware.php",
  "line": 20,
  "symbol": "AuthMiddleware::handle",
  "input": "attacker-controlled Authorization bearer token"
}
```

#### Controls encountered

```
[
  "Router applies AuthMiddleware to GET /api/profile and other routes with auth=true.",
  "AuthService::decodeToken only requires three dot-separated segments and a payload exp at or after the current time.",
  "AuthMiddleware checks only revocation status for attacker-supplied jti and existence of the attacker-supplied sub user ID.",
  "ProfileController::show uses the user returned by User::findById without any independent authentication or authorization check."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 58,
  "symbol": "AuthService::decodeToken",
  "operation": "decodes and trusts JWT payload without signature verification"
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
    "External unauthenticated caller sends a request to any route marked auth=true with an attacker-created three-part Bearer token.",
    "AuthMiddleware extracts the token and passes it to AuthService::decodeToken.",
    "decodeToken base64-decodes the payload but does not verify the JWT signature.",
    "Attacker-controlled sub, jti, and exp claims cross the authentication boundary when sub names an existing user, jti is not revoked, and exp is in the future.",
    "AuthMiddleware loads the selected user and grants that user's privileges to the protected route."
  ],
  "impact": "Unauthenticated customer impersonation and access to protected banking operations under any known or guessed existing user ID.",
  "severity_reasoning": "High because the core customer authentication boundary accepts attacker-controlled identity claims without cryptographic verification.",
  "dynamic_test": "Create an unsigned or incorrectly signed three-part JWT whose payload contains the ID of a dedicated test user, a fresh jti, and a future exp. Send it to a harmless auth=true endpoint and verify whether the response is treated as that test user despite the invalid signature."
}
```

#### Validator reasoning

Confirmed concrete path: an attacker controls the Authorization Bearer value in AuthMiddleware::handle. AuthService::decodeToken splits it into three parts, base64-decodes and JSON-parses parts[1], checks only exp, and returns that payload; it never verifies parts[2] or calls Firebase JWT decoding. The attacker can therefore provide a syntactically valid forged payload with a future exp, an unrevoked arbitrary jti, and an existing user's numeric sub. AuthMiddleware then calls User::findById($payload->sub) and returns authenticated context. Router dispatches GET /api/profile through this middleware, and ProfileController::show returns User::toPublic($auth['user']). No effective signature, issuer, audience, or independent authorization check blocks the forged token.

#### Code evidence

```
AuthService::decodeToken uses explode('.', $token), then json_decode(base64_decode(...$parts[1]...)); it checks only exp and never calls JWT::decode or verifies parts[2]. AuthMiddleware.php:22 trusts this payload, checks only jti revocation, loads User::findById($payload->sub), and returns authenticated user context. Router.php marks profile, account, transfer, transaction, and other customer routes auth=true and invokes AuthMiddleware::handle.
```

## 4. Hard-coded default admin JWT secret enables admin token forgery

- Lead reference: NIWE-004
- Category: A07
- Severity: HIGH
- Confidence: 94%
- Validation: inconclusive
- Reportable: No
- Location: BankOfEd-main/config/admin.php:21
- Fingerprint: d6683bd991471eeb9452a88917263c2d62ca62021d29af0724b67dfab2f944a2

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/admin.php",
  "line": 21,
  "symbol": "configuration return",
  "input": "default ADMIN_JWT_SECRET"
}
```

#### Controls encountered

```
[
  "HS256 signature verification",
  "issuer check",
  "jti revocation lookup",
  "admin row existence check"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Middleware/AdminAuthMiddleware.php",
  "line": 27,
  "symbol": "AdminAuthMiddleware::handle",
  "operation": "JWT::decode then authorize admin identity"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "Deployment may override ADMIN_JWT_SECRET; the bundled/default deployment path does not require it.",
  "Independent validator failed before closing this candidate."
]
```

#### Attack path

Not available for this candidate

#### Validator reasoning

Validator failed: {"error": {"message": "Reconnecting... 2/5", "codexErrorInfo": {"responseStreamDisconnected": {"httpStatusCode": null}}, "additionalDetails": "stream disconnected before completion: failed to lookup address information: nodename nor servname provided, or not known"}, "willRetry": true, "threadId": "01a054fe-eb1f-7180-a58c-cb77bfcc8391", "turnId": "01a054fe-ec3a-7840-9715-79c8c1413872"}

#### Code evidence

```
config/admin.php:21 defaults jwt_secret to 'bankofed-admin-secret-change-in-production'. src/Middleware/AdminAuthMiddleware.php:24-53 decodes HS256 with that secret, accepts iss BankOfEdAdmin, checks a caller-chosen jti against revocation, and loads admin_users by sub. install/admin_schema.sql:20-22 seeds the default admin, whose first auto-increment id is 1. src/AdminRouter.php maps authenticated admin tokens to PUT /api/admin/accounts/{id}/balance and POST /api/admin/system/reset.
```

## 5. Public health endpoint exposes the customer JWT signing secret

- Lead reference: NIWE-005
- Category: A02
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Router.php:32
- Fingerprint: 991ab38ad6ef70932cd289af79bdfaf818ab810c4a92c2b5786ca762d0ca5683

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 23,
  "symbol": "configuration return",
  "input": "JWT_SECRET or hard-coded fallback"
}
```

#### Controls encountered

```
[
  "None on the health route: Router::dispatch only invokes AuthMiddleware for routes whose auth value is true, while /api/health is registered with auth=false.",
  "CorsMiddleware only sets response headers and handles OPTIONS; it does not authenticate or restrict direct HTTP requests.",
  "AuthMiddleware's expiry, revocation, and user-existence checks apply only to other protected routes and cannot prevent reading /api/health."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Router.php",
  "line": 32,
  "symbol": "Router::health",
  "operation": "unauthenticated response discloses jwt_secret"
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
    "External unauthenticated caller requests GET /api/health.",
    "The route has auth=false and returns the configured jwt_secret.",
    "The caller can build a customer JWT containing attacker-chosen identity claims using the exposed HS256 credential.",
    "Customer AuthMiddleware uses token claims to select a user and authorize auth=true routes; the current decoder also fails to verify signatures.",
    "Protected customer data and banking actions become reachable as the selected user."
  ],
  "impact": "Disclosure of the customer authentication secret and potential arbitrary customer impersonation across protected banking routes.",
  "severity_reasoning": "High because a public endpoint exposes a credential intended to establish customer identity. The separate missing-signature check makes exploitation possible even without the disclosed value.",
  "dynamic_test": "While logged out, retrieve GET /api/health and confirm whether jwt_secret is present. In an isolated test account, mint an HS256 token with the disclosed secret and request a harmless protected endpoint, recording whether the server assigns the chosen test identity."
}
```

#### Validator reasoning

Confirmed. public/index.php routes /api/health to Router::dispatch, and Router.php registers GET /api/health with auth=false. The FOUND branch therefore calls Router::health without either auth middleware. Router::health requires config/app.php and passes config['jwt_secret'] directly to Response::success, whose json_encode output is sent to the caller and then exits. config/app.php obtains JWT_SECRET or falls back to a fixed development secret. AuthService::createToken uses the same value for HS256 tokens, so the exposed value is the signing credential. The downstream authorization path is also concretely weak: AuthMiddleware calls AuthService::decodeToken, which only splits and base64-decodes the payload and checks exp, with no signature verification, then loads the user by the attacker-controlled sub. Thus there is a direct unauthenticated source-to-sink disclosure and no effective blocking control.

#### Code evidence

```
config/app.php:23 supplies jwt_secret. src/Router.php:21-35 loads the config and includes jwt_secret in Response::success; src/Router.php:80 exposes GET /api/health with auth=false. src/Middleware/AuthMiddleware.php:24-45 accepts the decoded sub and loads that user. src/Services/AuthService.php:51-66 explicitly parses the JWT payload without signature verification and checks only exp. Seed data creates predictable user IDs, including user 1.
```

## 6. Published default machine token authorizes money transfers

- Lead reference: NIWE-006
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:35
- Fingerprint: 26e9acca3f5dcdecb03664e3ee7170aecd61205aef51f5109c1d5a7eea23fa23

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 35,
  "symbol": "configuration return",
  "input": "hard-coded MACHINE_TOKEN fallback"
}
```

#### Controls encountered

```
[
  "MachineAuthMiddleware requires a Bearer token and MachineToken hashes it with SHA-256 before lookup.",
  "PaymentController restricts the face_insurance/configured_machine_token identity to the FACE Insurance account or user 16 accounts.",
  "The transfer enforces positive amount, active source account, and sufficient balance checks.",
  "Internal destinations must be active accounts; external destinations only need the syntactic BSB format."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 235,
  "symbol": "PaymentController::transfer",
  "operation": "debit authorized source account and transfer funds"
}
```

#### Counterevidence

```
[
  "The bearer token is published in config/app.php and the matching active hash is installed by install/seed.sql, so the authentication control does not keep an attacker out.",
  "The source-account restriction intentionally grants the published identity access to seeded account 100, which has a seeded balance.",
  "The external-destination branch permits attacker-supplied BSB and account number and still debits the source account even when no local target account exists."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External unauthenticated caller obtains the published default machine bearer token from source or bundled configuration.",
    "The caller submits it to the machine-authenticated payment transfer endpoint.",
    "MachineAuthMiddleware and MachineToken::validateToken accept it as face_insurance or configured_machine_token.",
    "Payment transfer authorization permits that machine identity to select the FACE Insurance settlement account or an account owned by seeded user 16.",
    "The transfer service debits the authorized source and sends funds to an attacker-selected internal or external destination."
  ],
  "impact": "Unauthorized debit of merchant or seeded-user accounts and transfer of funds to attacker-controlled destinations.",
  "severity_reasoning": "High because a remotely usable, repository-known credential crosses the machine authentication boundary and reaches a money-transfer operation.",
  "dynamic_test": "In a disposable deployment using default configuration and seeded data, call the payment transfer endpoint with the published token and a minimal transfer from a designated test merchant account to a test destination. Verify whether the request authenticates as the configured machine and creates the transfer."
}
```

#### Validator reasoning

Confirmed concrete path: config/app.php:35 supplies the fixed token mch_face_insurance_secret_key_2026 when MACHINE_TOKEN is unset. install/seed.sql:243-255 creates active user 16, account 100 (BSB 062-001, account 88880001, balance 100000000.00), merchant faceinsurance mapped to account 100, and an active machine_tokens row named face_insurance containing SHA2 of that token. POST /api/payments/transfer is registered as machine-authenticated in src/Router.php:70-72; Router invokes MachineAuthMiddleware, which accepts the published token through MachineToken::validateToken and passes the database row name face_insurance to the controller. In PaymentController::transfer, the caller can select 062-001/88880001 as from_bsb/from_account_number. The face_insurance authorization check accepts account 100 (or any account with user_id 16). After the positive amount and balance checks, the controller debits the source with Account::updateBalance at line 229, optionally credits a local destination, and creates a completed transaction at lines 231-250. For a non-bank BSB, the code does not require a local destination account, so an attacker can choose an arbitrary external BSB/account number while the source debit still commits. No effective control prevents use of the source-published token or prevents the authorized machine identity from initiating these transfers.

#### Code evidence

```
config/app.php:35 defaults machine_token to 'mch_face_insurance_secret_key_2026'. install/seed.sql:253-255 stores SHA256 of the same token as active face_insurance. src/Models/MachineToken.php:10-31 accepts either the seeded hash or configuration fallback. src/Router.php:62-64 exposes POST /api/payments/transfer under machine auth. src/Controllers/PaymentController.php:180-196 authorizes this machine name for account id 100 or user id 16, and lines 229-250 debit that account and credit an attacker-selected target. install/seed.sql:243-247 seeds account 100 with balance 100000000.00.
```

## 7. Hard-coded SSO signing secret permits forged insurance identities

- Lead reference: NIWE-007
- Category: A07
- Severity: HIGH
- Confidence: 90%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/config/app.php:33
- Fingerprint: 3ae27f4f88570260d3b625aaed87fbd9b91ce3c82e3f59fd0d0fadb54dcce96f

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/config/app.php",
  "line": 33,
  "symbol": "configuration return",
  "input": "hard-coded INSURANCE_SSO_SECRET fallback"
}
```

#### Controls encountered

```
[
  "INSURANCE_SSO_SECRET can override the default when explicitly set",
  "The issuance endpoints require BankOfEd authentication",
  "JWT exp is five minutes and jti is random"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/InsuranceService.php",
  "line": 40,
  "symbol": "InsuranceService::generateSsoToken",
  "operation": "JWT::encode identity assertion with shared HS256 secret"
}
```

#### Counterevidence

```
[
  "The FACE Insurance consumer is not included, so its exact account-linking behavior cannot be demonstrated",
  "A deployment that explicitly sets a different INSURANCE_SSO_SECRET would not use the exposed default"
]
```

#### Proof gaps

```
[
  "No in-repository consumer code proves whether FACE Insurance accepts the issuer, subject, and name claims exactly as supplied",
  "No live or deployment configuration outside this archive proves the consumer is currently using the bundled default"
]
```

#### Attack path

```
{
  "nodes": [
    "An actor with access to the repository learns the bundled SSO HS256 shared secret.",
    "The actor creates an assertion with attacker-chosen email and name, issuer BankOfEd, and acceptable timestamps.",
    "The forged assertion is sent to a FACE Insurance deployment configured with the matching default secret.",
    "The insurance SSO verifier treats the valid HS256 signature and claims as a BankOfEd-issued identity.",
    "The attacker receives the insurance privileges of the forged BankOfEd user."
  ],
  "impact": "Cross-application identity forgery and impersonation in FACE Insurance deployments that retain the bundled shared secret.",
  "severity_reasoning": "High because knowledge of source supplies an identity-provider signing key, although exploitation depends on the paired insurance deployment retaining the same default.",
  "dynamic_test": "In an isolated BankOfEd and FACE Insurance pair configured with the bundled default secret, generate an HS256 assertion for a dedicated test email with issuer BankOfEd and valid timestamps. Submit it to the insurance SSO callback and verify whether a session is created for that identity."
}
```

#### Validator reasoning

Confirmed as a hard-coded shared-key SSO defect. config/app.php:33 falls back to the repository-visible constant, while .env.example omits INSURANCE_SSO_SECRET and deploy.sh writes no value for it, so the documented deployment uses the fixed secret unless an operator adds an override. InsuranceService::generateSsoToken reads that value and passes it directly to Firebase JWT::encode with HS256 at line 40. The payload contains the identity claims and ordinary JWT time claims; anyone who obtains the source can independently choose those claims and compute valid signatures without calling the authenticated BankOfEd route. The five-minute exp and random jti limit token lifetime and collisions but do not prevent minting fresh tokens. getSsoUrl then places the signed token in the external application's /sso URL. The consumer is outside the archive, so account-linking cannot be independently verified, but that is a limitation on the downstream impact proof rather than a control on the exposed signing key; a consumer that accepts the integration's legitimate tokens must have the corresponding shared secret.

#### Code evidence

```
config/app.php:33 defaults insurance_sso_secret to 'bankofed-goosecable-sso-shared-secret-key-32b'. src/Services/InsuranceService.php:24-40 creates identity assertions containing attacker-reproducible iss/sub/name/time claims and signs with that secret using HS256. src/Services/InsuranceService.php:47-57 sends the token to the insurance application's /sso endpoint.
```

## 8. SQL injection in admin customer search

- Lead reference: NIWE-008
- Category: A03
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:21
- Fingerprint: 0a71248c0de0a0c52bd357271183c506637ca7737b92ecd95b3c6f94a95cf2ca

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/public/admin/js/pages/customers.js",
  "line": 25,
  "symbol": "handleSearch",
  "input": "customer-search input e.target.value"
}
```

#### Controls encountered

```
[
  "AdminRouter marks GET /api/admin/customers as auth=true and AdminAuthMiddleware requires a valid, non-expired, non-revoked JWT for an existing admin.",
  "That authentication check limits the attacker to an admin session but does not constrain the search value.",
  "page, per_page, and offset are integer-cast, but search is copied from $_GET without validation, escaping, or a prepared placeholder.",
  "PDO native prepares are enabled, but the vulnerable count and customer queries use query() with an interpolated SQL string."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 25,
  "symbol": "AdminUserController::index",
  "operation": "PDO query of SQL string containing interpolated $_GET['search']"
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
    "An authenticated administrator supplies a crafted search query parameter to GET /api/admin/customers.",
    "Admin route authentication crosses the admin boundary but no SQL-safe allowlist or parameter binding is applied to search.",
    "AdminUserController::index interpolates search into the WHERE clause for both COUNT and customer SELECT statements.",
    "PDO::query executes the attacker-altered SQL.",
    "The administrator may change query behavior and potentially read or modify database data as allowed by the driver and connection."
  ],
  "impact": "Database query manipulation with possible disclosure or modification of banking records under the application's database privileges.",
  "severity_reasoning": "High because attacker-controlled SQL reaches two queries, though access requires an authenticated admin and exact impact depends on PDO and database configuration.",
  "dynamic_test": "Using a dedicated low-impact admin test account and disposable database, compare a normal search with a boolean-changing search payload and observe result count and rows. If needed, use a harmless timing expression supported by the configured database to confirm evaluation without modifying data."
}
```

#### Validator reasoning

Confirmed. The route in BankOfEd/src/AdminRouter.php dispatches GET /api/admin/customers to AdminUserController::index and performs authentication before invoking it. In index(), $_GET['search'] is inserted directly into the WHERE clause used in both countSql and the customer SELECT, and both strings are executed through PDO::query(). A request with search=%27%20OR%201%3D1--%20 is decoded by PHP to ' OR 1=1-- . The resulting MySQL predicate begins `first_name LIKE '%' OR 1=1-- `, with the remaining predicate commented out, so the count and customer queries return all rows. The configured AdminDatabase DSN is MySQL, and neither URL encoding nor admin authentication blocks SQL metacharacters. This is a concrete reachable source-to-sink SQL injection path for an authenticated admin.

#### Code evidence

```
public/admin/js/pages/customers.js:25-34 copies e.target.value into searchTerm and calls Api.getCustomers(... search: searchTerm). public/admin/js/api.js:46-50 URL-encodes that value into the search query parameter. src/Controllers/AdminUserController.php:15 reads $_GET['search']; lines 20-21 construct `WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'`; lines 25 and 30 execute SQL containing that interpolation with `$db->query(...)` rather than a prepared placeholder.
```

## 9. Stored XSS in admin accounts table through account name

- Lead reference: NIWE-009
- Category: A03
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/accounts.js:54
- Fingerprint: 92348937bf0d6b35fb9cecff886bff5d838b2cb8e963015f449c748020223ef2

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 28,
  "symbol": "AccountController::store",
  "input": "authenticated user's JSON account_name"
}
```

#### Controls encountered

```
[
  "The customer account-creation route requires a valid customer token, but the authenticated customer may choose account_name freely; validation only enforces required|string|max:100.",
  "The admin accounts route requires a valid admin JWT, which limits the victim page to administrators but does not sanitize the stored value.",
  "The visible account-name cell uses escapeHtml, but the separate onclick interpolation uses the same HTML escape for a JavaScript string and then attempts to escape literal apostrophes too late.",
  "No Content-Security-Policy header is configured in the deployment headers; the configured X-XSS-Protection header is a legacy browser hint and does not reliably block this DOM/inline-handler path."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/accounts.js",
  "line": 54,
  "symbol": "renderTable",
  "operation": "innerHTML creates an inline onclick handler containing account_name in JavaScript string context"
}
```

#### Counterevidence

```
[
  "An administrator must be authenticated, visit the accounts page, and click Edit Balance, so exploitation is interaction-dependent.",
  "The account name is capped at 100 characters and the visible table text is escaped, but neither prevents the short breakout payload in the onclick value."
]
```

#### Proof gaps

```
[
  "The finding relies on standard browser behavior that decodes &#39; in an HTML event-handler attribute before compiling the handler.",
  "A live browser reproduction was not run in this validation session."
]
```

#### Attack path

```
{
  "nodes": [
    "An authenticated banking user creates an account with attacker-controlled JavaScript syntax in account_name.",
    "The server stores the account name and later returns it through the admin accounts API.",
    "The admin accounts table renderer applies HTML escaping, then embeds the value inside a single-quoted JavaScript argument in an inline onclick attribute.",
    "The HTML parser decodes &#39; before the inline handler is compiled, allowing the stored apostrophe to terminate the JavaScript string.",
    "An administrator clicks Edit Balance and the payload executes with the admin origin and session privileges."
  ],
  "impact": "Stored script execution in an administrator's browser, enabling admin-session actions and access to data available to the admin origin.",
  "severity_reasoning": "High because a normal customer can persist input that crosses into an admin-origin script sink, although execution requires the administrator to click the affected control.",
  "dynamic_test": "Create a test account whose name contains a benign payload that sets a unique DOM marker through the inline-handler breakout. Log in as a test administrator, open the accounts table, click Edit Balance for that row, and verify whether the marker is created."
}
```

#### Validator reasoning

The source-to-sink path is concrete. POST /api/accounts reaches AccountController::store after customer authentication. Validator::make permits arbitrary string content up to 100 characters, and the value is inserted into accounts without transformation. GET /api/admin/accounts returns account_name directly to the authenticated admin SPA. In renderTable, innerHTML receives a button attribute built as a single-quoted JavaScript argument around U.escapeHtml(a.account_name). escapeHtml converts an apostrophe to the character reference &#39;, so replace(/'/g, "\\'") does not alter it. HTML parsing decodes that reference before the inline onclick handler is compiled. For account_name = "');alert(document.domain);//", the handler contains showEditBalanceModal(id, '');alert(document.domain);//', 'balance'), making the stored payload execute when the admin clicks Edit Balance. The 100-character limit, visible-cell escaping, and admin authentication do not block this path.

#### Code evidence

```
src/Controllers/AccountController.php:24-29 accepts account_name with only required|string|max:100 and src/Controllers/AccountController.php:109-115 stores it. src/Controllers/AdminAccountController.php:19-35 returns a.account_name to the admin UI. public/admin/js/pages/accounts.js:50 constructs `onclick="...showEditBalanceModal(..., '" + U.escapeHtml(a.account_name).replace(/'/g, "\\'") + "', ...)"`; utils.js:15-18 maps apostrophe to `&#39;`, so the following replace sees no literal apostrophe. The browser decodes `&#39;` in the attribute before treating it as handler source. The completed row string is assigned to container.innerHTML at accounts.js:54.
```

## 10. Stored XSS in admin customer detail through customer name

- Lead reference: NIWE-010
- Category: A03
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/admin/js/pages/customers.js:161
- Fingerprint: e69e93701c4af5febfa0e97ce0721279fc9b4c7c352e640b17a90a70c6ef31fd

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 75,
  "symbol": "AdminUserController::show",
  "input": "stored customer first_name and last_name"
}
```

#### Controls encountered

```
[
  "The customer detail endpoint requires an authenticated admin, so the sink is limited to the admin panel.",
  "The payload executes only when the administrator clicks the rendered Delete button."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/admin/js/pages/customers.js",
  "line": 161,
  "symbol": "renderDetail",
  "operation": "innerHTML creates an inline onclick handler containing the stored name in JavaScript string context"
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
    "A customer stores attacker-controlled syntax in their first or last name.",
    "The admin customer detail API returns the stored name.",
    "customers.js HTML-escapes the name and then unsuccessfully tries to backslash apostrophes after they have become entities.",
    "The value is inserted into a single-quoted JavaScript argument in the Delete button's inline onclick handler; the browser decodes the entity before compiling it.",
    "A test administrator views the customer and clicks Delete, executing the stored payload in the admin origin."
  ],
  "impact": "Stored JavaScript execution with administrator-origin access, allowing privileged API calls or theft of data exposed to the admin session.",
  "severity_reasoning": "High because customer-controlled persistent data reaches an admin script context. Exploitation requires an administrator to click the affected Delete button.",
  "dynamic_test": "Set a dedicated customer's name to a benign inline-handler breakout payload that writes a unique DOM marker. As a test administrator, open that customer's detail view and click Delete, then check whether the marker appears without performing destructive follow-on actions."
}
```

#### Validator reasoning

Confirmed. A customer-controlled name has viable write paths: registration validates only required/string/max length, profile update allows first_name and last_name with only string/max length, and AdminUserController::update applies those fields without any character restriction. AdminUserController::show returns the stored values from the users table through the authenticated GET /api/admin/customers/{id} route. The admin route is reachable from the frontend router, and showDetail passes the response to renderDetail. At customers.js:106, the name is placed inside a single-quoted JavaScript argument in a double-quoted inline onclick attribute. escapeHtml converts apostrophes to &#39;, then replace(/'/g, "\\'") sees no apostrophes and adds no JavaScript escaping. HTML parsing decodes &#39; back to a quote before compiling the event handler. For a stored name beginning with ');alert(document.domain);//, the handler becomes effectively confirmDelete(id, '');alert(document.domain);//... and the alert runs on a Delete click. There is no CSP or other source-level control shown that disables inline handlers, and the modal later escapes the name but that occurs after the event handler has already been compiled. This is a concrete stored source-to-sink path with no effective blocking control.

#### Code evidence

```
public/admin/js/pages/customers.js:103-108 builds `onclick="...confirmDelete(c.id, '" + U.escapeHtml(c.first_name + ' ' + c.last_name).replace(/'/g, "\\'") + "')"`; utils.js:15-18 maps apostrophe to `&#39;`, meaning replace(/'/g) cannot add JavaScript escaping. The completed string is parsed through innerHTML at customers.js:161. AdminUserController.php:72-78 returns stored first_name and last_name. Those profile fields are customer data and are also accepted for updates.
```

## 11. Stored XSS in account transaction history

- Lead reference: NIWE-011
- Category: A03
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/accounts.js:171
- Fingerprint: fed2c9c6be90a0ba9b8cb4540beeadfa6eb0518c127e3a27b2360ff6a233270c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 82,
  "symbol": "transferExternal",
  "input": "JSON body field description"
}
```

#### Controls encountered

```
[
  "The transfer route and transaction-history route both require authentication, but this does not restrict a malicious authenticated account holder.",
  "description is validated only as a string with a 255-character maximum; HTML event-handler payloads fit within that limit.",
  "AccountController::show and TransactionController::index verify the requested account belongs to the viewing user, which protects access to the history but does not encode its contents.",
  "Response::success uses plain json_encode and Transaction::format returns the stored description unchanged.",
  "No CSP or other response-level control was found that would block the inline event-handler payload; the recipient UI assigns the description-containing string to innerHTML."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/accounts.js",
  "line": 171,
  "symbol": "renderDetailTransactions",
  "operation": "container.innerHTML = html with raw tx.description"
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
    "An authenticated attacker submits POST /api/transfers/external with HTML or JavaScript in description and a recipient whose history the attacker wants to affect.",
    "TransactionController accepts description as a string and TransferService stores it unchanged in the transaction record.",
    "The recipient later requests the affected account's transaction history.",
    "renderDetailTransactions concatenates tx.description without U.escapeHtml and assigns the constructed markup to innerHTML.",
    "The browser executes the stored payload in the recipient's authenticated banking origin."
  ],
  "impact": "Stored script execution in another customer's banking session, with access to same-origin data and actions available to that victim.",
  "severity_reasoning": "High because an authenticated customer can persist active content that executes automatically when another customer views transaction history.",
  "dynamic_test": "From an attacker test account, make a small transfer to a victim test account with a benign description payload such as an image error handler that sets a DOM marker. Open the recipient account history as the victim and verify whether the marker is set."
}
```

#### Validator reasoning

Confirmed source-to-sink path: POST /api/transfers/external is authenticated and TransactionController::transferExternal accepts JSON description after only string|max:255 validation. TransferService::transferExternal passes the nullable string directly to Transaction::create as description. When the supplied BSB and account number identify an internal account, Account::findByBsbAndNumber sets to_account_id and the transaction is inserted while the destination balance is credited. The recipient can request that account's history because AccountController::show/TransactionController::index authorize ownership of the requested account; Transaction::findByAccount/findByUser select rows involving that account, Transaction::format returns description unchanged, and Response::success serializes it without HTML escaping. In accounts.js renderDetailTransactions concatenates tx.description directly into a table cell and sets container.innerHTML. A payload such as <img src=x onerror=alert(document.domain)> is under 255 characters and executes when the recipient opens the account detail. The authorization check is for viewing the recipient's own account and is not a sanitization control.

#### Code evidence

```
Source: TransactionController.php transferExternal reads JSON description and validates only string|max:255, then passes it to TransferService::transferExternal. Storage: TransferService.php creates the transaction with 'description' => $description and credits an internal destination. Retrieval: TransactionController::index verifies the requested account belongs to the viewer, then Transaction::findByUser returns transactions where that account is from_account_id or to_account_id. Sink: accounts.js lines 151-171 builds '<td ...>' + (tx.description || '—') + '</td>' and assigns container.innerHTML = html.
```

## 12. Insurance SSO tab can navigate the banking tab

- Lead reference: NIWE-012
- Category: A05
- Severity: LOW
- Confidence: 86%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/app.js:105
- Fingerprint: 1e18c8da197e46da457469e4493f61250016e9df10b959a036e574291c0c1a79

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Services/InsuranceService.php",
  "line": 50,
  "symbol": "InsuranceService::getSsoUrl",
  "input": "Setting::get('insurance_app_url') or config insurance_app_url"
}
```

#### Controls encountered

```
[
  "GET /api/insurance/sso is protected by AuthMiddleware, so an unauthenticated caller cannot obtain an SSO URL.",
  "The administrator settings endpoint requires AdminAuthMiddleware and applies FILTER_VALIDATE_URL to updates.",
  "Neither control prevents a valid but malicious or compromised external insurance origin, and no allowlist, CSP/COOP header, or noopener feature is present."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/app.js",
  "line": 105,
  "symbol": "launchInsurance",
  "operation": "window.open(res.data.sso_url, '_blank')"
}
```

#### Counterevidence

```
[
  "The URL is administrator-configured rather than directly supplied by an ordinary banking user.",
  "The default destination is http://localhost:8001, so exploitation requires a changed configuration or a compromised/deceptive configured destination."
]
```

#### Proof gaps

```
[
  "Exploitability depends on the browser retaining window.opener for window.open(..., '_blank') and on the opened origin being malicious or compromised; the source does not establish behavior across all browsers."
]
```

#### Attack path

```
{
  "nodes": [
    "An authenticated banking user requests the insurance SSO launch action.",
    "The server builds data.sso_url from Setting::get('insurance_app_url') or application configuration and returns it from GET /api/insurance/sso.",
    "Banking app.js passes the external URL to window.open(url, '_blank') without noopener.",
    "The opened insurance page retains a window.opener reference across the external trust boundary.",
    "A malicious or compromised insurance destination can navigate the original BankOfEd tab to a phishing page."
  ],
  "impact": "Reverse-tabnabbing of the banking tab, which can present a phishing page to an authenticated user.",
  "severity_reasoning": "Low because exploitation requires control or compromise of the externally configured insurance destination and primarily enables navigation rather than direct same-origin access.",
  "dynamic_test": "In a test deployment, configure insurance_app_url to a controlled page that calls window.opener.location.assign() with a harmless local marker URL. Launch insurance from the banking UI and verify whether the original banking tab is navigated."
}
```

#### Validator reasoning

The path is concrete: a banking click or the /insurance route calls launchInsurance, Api.getInsuranceSsoUrl() requests GET /api/insurance/sso, Router dispatches it through AuthMiddleware, InsuranceController::ssoUrl returns InsuranceService::getSsoUrl(), and that concatenates the configured base URL with the SSO token. The promise handler passes that value directly to window.open(res.data.sso_url, '_blank') with no feature string. JSON encoding does not constrain the URL's destination, and the admin-side FILTER_VALIDATE_URL check is only syntactic validation with no host allowlist. The authenticated-user and administrator-configured controls reduce who can trigger or set the value but do not block tabnabbing when the configured external origin is malicious or compromised. Apache headers shown include X-Frame-Options and Referrer-Policy, but no Cross-Origin-Opener-Policy; those headers do not supply the missing opener isolation.

#### Code evidence

```
InsuranceService.php:50-55 selects insurance_app_url from the settings database or config and builds the external SSO URL. InsuranceController.php:14-23 returns it as sso_url. api.js:124 requests /insurance/sso. app.js:102-105 opens res.data.sso_url in _blank with no 'noopener' feature.
```

## 13. Stored XSS in dashboard transaction descriptions

- Lead reference: NIWE-013
- Category: A03
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/public/banking/js/pages/dashboard.js:98
- Fingerprint: 3167de21e8815c8ccf3736d64299840416f6590aa799b7920d972f3c2566b12a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 80,
  "symbol": "transferExternal",
  "input": "JSON body description and from_account_id"
}
```

#### Controls encountered

```
[
  "POST /api/transfers/external requires a valid bearer token",
  "description is type-checked as a string and limited to 255 characters",
  "manual transfer destinations require a syntactically valid BSB and eight-digit account number",
  "the application sets X-XSS-Protection in Apache, but this is not an effective modern browser mitigation and no CSP or output encoding is present"
]
```

#### Sink

```
{
  "file": "BankOfEd-main/public/banking/js/pages/dashboard.js",
  "line": 98,
  "symbol": "renderTransactions",
  "operation": "container.innerHTML = html"
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
    "An authenticated attacker sends POST /api/transfers/external with another user's from_account_id and an HTML payload in description.",
    "TransferService loads the source through Account::findById without checking that it belongs to the authenticated caller.",
    "The service stores the description in a transaction associated with the victim account while also processing the unauthorized debit.",
    "The victim's dashboard retrieves the transaction through GET /api/transactions.",
    "dashboard.js concatenates the unescaped description into markup and assigns it to container.innerHTML, executing the payload in the victim session."
  ],
  "impact": "Stored script execution in a chosen customer's banking session, combined with unauthorized use of that customer's account as the transfer source.",
  "severity_reasoning": "High because a customer can target another customer's account and place active content into a page that executes automatically in the victim's authenticated origin.",
  "dynamic_test": "With two disposable users, submit an external transfer as the attacker using the victim's account ID and a benign description payload that sets a DOM marker. Open the victim dashboard and verify both that the transaction appears and that the marker executes."
}
```

#### Validator reasoning

Confirmed. The authenticated route passes the attacker-controlled JSON description and from_account_id to TransferService::transferExternal. That service loads the source with Account::findById($fromAccountId), unlike transferOwn which uses findByIdAndUser, and then updates the account balance and creates a transaction with the unmodified description. TransactionController::index calls Transaction::findByUser for the logged-in user; with no account_id it joins transactions through t.from_account_id to accounts.user_id, so a transaction created from another user's account is returned in that user's transaction feed. Response::success/json_encode preserves the string for the JSON client. The dashboard fetches that feed on every dashboard load and renderTransactions concatenates tx.description directly into a <p> string before assigning container.innerHTML. There is no escaping, sanitization, CSP, or other effective execution barrier. A payload such as </p><img src=x onerror=...> can therefore execute in the victim's authenticated banking page. The length limit and bearer authentication do not block the path.

#### Code evidence

```
TransactionController.php:80-117 accepts description (only string|max:255) and calls transferExternal. TransferService.php:175-180 uses Account::findById($fromAccountId) with no user ownership check; lines 275-283 stores $description. Transaction.php:39-67 returns transactions joined through the source account owner and lines 119-122 exposes description. dashboard.js:29-32 passes API transactions to renderTransactions; lines 79-98 concatenate (tx.description || tx.type) directly into html and assign container.innerHTML.
```

## 14. SQL injection in admin customer search count query

- Lead reference: NIWE-014
- Category: A03
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:28
- Fingerprint: 0462ef92d2298f0e89008d4f019fa98894def2cb2ebfbb3cef1b80d3f53103f6

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 16,
  "symbol": "AdminUserController::index",
  "input": "$_GET['search']"
}
```

#### Controls encountered

```
[
  "AdminRouter maps GET /api/admin/customers to AdminUserController::index and invokes AdminAuthMiddleware::handle(), so authentication gates reachability only.",
  "AdminDatabase uses MySQL PDO with ATTR_EMULATE_PREPARES=false, but the affected statements are still built as raw SQL and executed with PDO::query; no binding or escaping is applied to search.",
  "The same interpolated where clause is used in both the COUNT query and the customer SELECT query, so the input can change predicate semantics and the returned customer set."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 28,
  "symbol": "AdminUserController::index",
  "operation": "PDO::query($countSql)"
}
```

#### Counterevidence

```
[
  "The admin authentication requirement limits exploitation to an authenticated admin account.",
  "Native PDO prepares and the default MySQL single-statement behavior may prevent stacked-statement modification through this call."
]
```

#### Proof gaps

```
[
  "The source does not establish whether the deployed MySQL connection enables multi-statements, so arbitrary write or stacked-query impact is unproven.",
  "The concrete database contents and production error/display settings are not available."
]
```

#### Attack path

```
{
  "nodes": [
    "An authenticated administrator controls search on GET /api/admin/customers.",
    "AdminUserController::index concatenates search into a LIKE predicate without parameter binding.",
    "The constructed COUNT SQL string is passed to PDO::query.",
    "The database evaluates attacker-supplied SQL structure with application database privileges.",
    "Changed counts, errors, or timing can disclose data and driver-permitted statements may cause broader database impact."
  ],
  "impact": "SQL injection in the count query, enabling database inference and potentially broader read or write effects depending on the driver.",
  "severity_reasoning": "High because raw user input reaches PDO::query in SQL syntax, though admin authentication is required and modification capability is configuration-dependent.",
  "dynamic_test": "On a disposable database with a test admin, send normal and boolean-altering search values and compare the returned total count. Use a harmless supported timing expression only if necessary to confirm SQL evaluation."
}
```

#### Validator reasoning

Confirmed SQL injection. public/index.php routes /api/admin/* to AdminRouter; the GET /api/admin/customers route requires AdminAuthMiddleware and then calls AdminUserController::index. In index(), $_GET['search'] is copied directly into a quoted LIKE expression, assigned to $where, interpolated into $countSql, and executed by $db->query($countSql). No validation, escaping, or parameter binding occurs. A quote and SQL syntax supplied in search can terminate the intended string and alter the WHERE expression. The identical $where is then interpolated into the fetch query, giving a second source-to-sink path that can alter which user rows are returned. Authentication is an access control boundary, not an injection control. The unproven stacked-query/write behavior affects impact breadth, not the existence of the SQL injection.

#### Code evidence

```
$search = $_GET['search'] ?? '';
if ($search !== '') {
    $where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
}
$countSql = "SELECT COUNT(*) FROM users {$where}";
$stmt = $db->query($countSql);
```

## 15. SQL injection in admin customer search result query

- Lead reference: NIWE-015
- Category: A03
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:33
- Fingerprint: 493ea56e088d1a443288ccdbcf012cee9dfd4094bb5f04016ac187e0c7ef6601

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 16,
  "symbol": "AdminUserController::index",
  "input": "$_GET['search']"
}
```

#### Controls encountered

```
[
  "AdminRouter maps GET /api/admin/customers to AdminUserController::index and invokes AdminAuthMiddleware::handle() before the handler.",
  "AdminAuthMiddleware validates the Bearer JWT, issuer, revocation status, and admin user; this limits access to authenticated admins but does not sanitize the search value.",
  "Pagination values are integer-cast and bounded, but those controls do not affect the interpolated search fragment.",
  "AdminDatabase uses PDO with native prepares, but the vulnerable calls are direct PDO::query calls and no prepared statement or escaping is used for $search."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 33,
  "symbol": "AdminUserController::index",
  "operation": "PDO::query($sql)"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "The exact MySQL account privileges are not shown, so impact beyond reading rows in users and related query results cannot be determined."
]
```

#### Attack path

```
{
  "nodes": [
    "An authenticated administrator supplies crafted search input to GET /api/admin/customers.",
    "The controller directly interpolates search into the result query's WHERE clause.",
    "PDO::query executes the altered customer SELECT statement.",
    "The injected expression changes filtering, ordering, unions, or other supported query behavior.",
    "Rows or derived database values outside the intended customer search can be returned to the caller."
  ],
  "impact": "Unauthorized database disclosure through manipulation of the admin customer result query, with possible broader effects if the database driver permits them.",
  "severity_reasoning": "High because attacker-controlled SQL is executed directly and returned results can expose database contents, despite the requirement for admin access.",
  "dynamic_test": "Using a test admin and disposable data, compare a normal search response with a benign boolean or UNION-style payload compatible with the configured database. Verify whether rows outside the intended filter are returned without changing data."
}
```

#### Validator reasoning

The route is reachable and the authentication middleware runs before AdminUserController::index, so the attacker must be an authenticated admin. Within index, $_GET['search'] is assigned directly to $search. When non-empty, it is interpolated into the quoted LIKE expressions in $where, which is then interpolated into both countSql and the result $sql. Each statement is executed with PDO::query($sql), with no binding, escaping, or validation of search. A scalar input such as x' OR 1=1 # can terminate the first LIKE string and comment the remainder of the WHERE line in MySQL, changing the query predicate. This is a concrete source-to-sink SQL injection path; the auth and pagination controls do not block it.

#### Code evidence

```
$search = $_GET['search'] ?? '';
$where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
$sql = "SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}";
$stmt = $db->query($sql);
```

## 16. External transfer debits an account without checking ownership

- Lead reference: NIWE-016
- Category: API1
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:95
- Fingerprint: e4de672edfe96f9a4343dbe48ce3d2ffbab2b64bb6bb5e35b4e5a262827cb2b9

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 83,
  "symbol": "transferExternal",
  "input": "JSON from_account_id"
}
```

#### Controls encountered

```
[
  "POST /api/transfers/external is authentication-protected, so an attacker needs a valid user token.",
  "from_account_id is only checked as required/numeric and then cast to int; no user ownership check is applied.",
  "The positive amount check does not constrain the selected account.",
  "Manual destinations accept attacker-supplied BSB and eight-digit account number.",
  "TOTP is not an effective blocker because transfers proceed when TOTP is disabled and also proceed when an enabled user's code is omitted."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 95,
  "symbol": "updateBalance",
  "operation": "UPDATE accounts balance by attacker-selected id"
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
    "An authenticated customer submits POST /api/transfers/external with a guessed or known victim from_account_id and an attacker-controlled destination.",
    "TransactionController checks only that from_account_id is numeric.",
    "TransferService::transferExternal calls Account::findById, crossing the object authorization boundary without binding the account to the authenticated user.",
    "Account::updateBalance debits the attacker-selected account ID.",
    "The transfer credits or sends funds to the destination chosen by the attacker."
  ],
  "impact": "Direct theft or unauthorized movement of funds from any customer account whose identifier can be obtained or guessed.",
  "severity_reasoning": "High because any authenticated customer can cross an object-level authorization boundary and reach the balance-debit sink.",
  "dynamic_test": "Create attacker and victim test users with funded accounts. Authenticate as the attacker and submit a minimal external transfer using the victim account ID and a controlled test destination. Verify whether the victim balance decreases and a transfer record is created."
}
```

#### Validator reasoning

Confirmed. Router.php maps the endpoint to TransactionController::transferExternal with auth=true, and AuthMiddleware supplies the authenticated user. The controller reads JSON from php://input, validates from_account_id only as required|numeric, casts it to int, and passes it to TransferService::transferExternal. In that service, $userId is used to scope address-book lookup, but the source is loaded with Account::findById($fromAccountId), whose query filters only WHERE id = ?. There is no comparison between the loaded account's user_id and the authenticated user. For a valid victim account ID, the manual branch permits attacker-controlled destination details, and the transaction executes Account::updateBalance($fromAccountId, '-' . $debitAmount). Account::updateBalance issues UPDATE accounts SET balance = balance + ? WHERE id = ?, so the attacker-selected account is debited. The transaction records and returns the selected source ID. Account IDs are exposed to authenticated users through AccountController::index and are integer route identifiers, making known or guessed IDs practical. No framework or database control shown binds the update to the authenticated user.

#### Code evidence

```
src/Controllers/TransactionController.php:83-112 reads JSON from php://input and passes (int)$data['from_account_id']; src/Services/TransferService.php:175-180 calls Account::findById($fromAccountId) without binding it to $userId; src/Services/TransferService.php:266-272 calls Account::updateBalance($fromAccountId, '-' . $debitAmount); src/Models/Account.php:93-95 executes UPDATE accounts SET balance = balance + ? WHERE id = ?.
```

## 17. Credit-card CVVs are stored and returned in plaintext

- Lead reference: NIWE-017
- Category: A02
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:75
- Fingerprint: 050a392ebc4a91fc9ee396c8d6b6189b7943f2c5fcf5d98e3b2456b3403cffe4

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AccountController.php",
  "line": 23,
  "symbol": "store",
  "input": "Authenticated account-creation request triggers generated CVV"
}
```

#### Controls encountered

```
[
  "Account routes require a valid bearer token.",
  "GET /api/accounts/{id} scopes the lookup to the authenticated user's ID.",
  "Database writes use prepared statements with bound parameters."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 75,
  "symbol": "create",
  "operation": "INSERT plaintext card_cvv into accounts"
}
```

#### Counterevidence

```
[
  "Authentication and owner scoping limit who can retrieve the record, but do not encrypt or redact the CVV.",
  "The CVV is server-generated and random, but it remains reusable payment authentication data once stored and returned."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "A customer creates a credit-card account through the account creation flow.",
    "The application generates a CVV and passes it with card number and expiry into Account::create.",
    "Account::create inserts card_cvv directly into a plain VARCHAR database column with no encryption or one-way protection.",
    "Account::toPublic includes card_cvv in API output for credit-card accounts.",
    "Anyone who gains database read access or authorized/compromised access to the account response obtains reusable card verification data."
  ],
  "impact": "Disclosure of reusable CVVs together with card number and expiry data, increasing payment-card fraud risk after an API or database compromise.",
  "severity_reasoning": "High because highly sensitive authentication data is stored reversibly and returned by the API, making any account or database disclosure substantially more damaging.",
  "dynamic_test": "In a disposable account, create a credit-card product, inspect the returned account API response for card_cvv, then inspect the corresponding test database row through an authorized test fixture to verify whether the same plaintext CVV is stored."
}
```

#### Validator reasoning

Confirmed. For a credit_card request, AccountController::store generates $cardCvv with AccountService::generateCreditCardCvv(), includes it as card_cvv in the array passed to Account::create(), and Account::create() binds that value directly in the INSERT into accounts.card_cvv. The schema declares card_cvv as VARCHAR(4), with no encryption or hash representation. Account::findByUser(), Account::findById(), and Account::findByIdAndUser() select the full row, and Account::toPublic() copies card_number, card_expiry, and card_cvv into the response for credit-card accounts. The authenticated GET /api/accounts, GET /api/accounts/{id}, and POST /api/accounts response paths call toPublic(), so an authenticated owner receives the plaintext CVV and PAN. No masking, encryption, tokenization, or redaction blocks either the persistence or response sink.

#### Code evidence

```
src/Controllers/AccountController.php:50-52 generates $cardCvv; lines 108-119 pass it as card_cvv to Account::create; src/Models/Account.php:73-87 inserts card_cvv as a bound plaintext value; install/schema.sql:34 defines card_cvv VARCHAR(4); src/Models/Account.php:108-115 includes card_number, card_expiry, and card_cvv in toPublic; src/Controllers/AccountController.php:17-19 and 149 return toPublic results.
```

## 18. Unauthenticated admin export exposes all banking records

- Lead reference: NIWE-018
- Category: A01
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/AdminUserController.php:174
- Fingerprint: 6143e0a56f010eb74904b449e475c0bd512731859fec35522e3b76c530285874

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/AdminRouter.php",
  "line": 48,
  "symbol": "AdminRouter::dispatch",
  "input": "Unauthenticated GET /api/admin/export/users"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/AdminUserController.php",
  "line": 174,
  "symbol": "AdminUserController::exportAll",
  "operation": "Bulk database read and JSON response"
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
    "External unauthenticated caller sends GET to the admin export route.",
    "Router registers the export handler with auth=false, so the request crosses the admin boundary without credentials.",
    "AdminUserController::exportAll runs SELECT * across users, accounts, and transactions.",
    "The handler serializes complete database rows into the response.",
    "The caller receives password hashes, stored card fields, customer records, account data, and transaction history."
  ],
  "impact": "Bulk unauthenticated disclosure of the banking database, including credentials, payment-card data, balances, identities, and transaction records.",
  "severity_reasoning": "High because a public request directly reaches a full-record export sink with no authorization check.",
  "dynamic_test": "From a logged-out client against a disposable seeded deployment, request the admin export endpoint and verify whether it returns user, account, and transaction rows, including representative sensitive fields, without an Authorization header."
}
```

#### Validator reasoning

Confirmed. public/index.php routes every /api/admin/ request to AdminRouter::dispatch, and public/.htaccess rewrites API paths to that front controller. AdminRouter registers GET /api/admin/export/users with auth=false and only calls AdminAuthMiddleware::handle() when the route's auth flag is truthy. It then invokes AdminUserController::exportAll() without arguments. exportAll() runs SELECT * FROM users, SELECT * FROM accounts, and SELECT * FROM transactions ORDER BY created_at DESC, fetches all rows, and passes them directly to Response::success(). Response::success() JSON-encodes the data and exits. The schema confirms users contains password_hash and totp_secret, while accounts contains card_number, card_expiry, and card_cvv. No validation, authorization, redaction, or encoding control blocks the route-to-response path.

#### Code evidence

```
AdminRouter.php:48 registers GET /api/admin/export/users with 'auth' => false. AdminRouter.php:80-83 invokes AdminAuthMiddleware only when requiresAuth is truthy. AdminUserController.php:171-186 executes SELECT * FROM users, SELECT * FROM accounts, and SELECT * FROM transactions, then passes all rows to Response::success.
```

## 19. Hardcoded fallback machine token permits unauthorized payment requests

- Lead reference: NIWE-019
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Middleware/MachineAuthMiddleware.php:19
- Fingerprint: d7c3ff978bc685140a181589a2216c7d953c5b4d3a8ea587eaee3f91002255e1

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/MachineAuthMiddleware.php",
  "line": 12,
  "symbol": "MachineAuthMiddleware::handle",
  "input": "HTTP Authorization bearer token"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/PaymentController.php",
  "line": 35,
  "symbol": "PaymentController::process",
  "operation": "Authorize and execute payment"
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
    "External caller learns the repository-known fallback machine token.",
    "The caller submits it as a Bearer token to a machine-authenticated payment route.",
    "MachineAuthMiddleware forwards the raw value to MachineToken::validateToken.",
    "When no active database token matches, validateToken compares it to the configured fallback and returns an authenticated configured_machine_token identity.",
    "The caller reaches payment processing and, on the transfer route, authorization for FACE Insurance or seeded user 16 accounts."
  ],
  "impact": "Unauthorized payment requests and potential transfer of funds from FACE Insurance or seeded-user accounts.",
  "severity_reasoning": "High because a source-known default credential can remotely cross machine authentication and access financial operations whenever the override is absent.",
  "dynamic_test": "In a disposable deployment with MACHINE_TOKEN unset, submit the documented fallback token to a harmless machine-auth status or minimal payment request. Verify the authenticated machine identity, then use a small test-only transfer to confirm whether the privileged transfer path is reachable."
}
```

#### Validator reasoning

Concrete path: HTTP Authorization Bearer mch_face_insurance_secret_key_2026 reaches MachineAuthMiddleware::handle, which calls MachineToken::validateToken. config/app.php uses that same hardcoded value when MACHINE_TOKEN is unset, and validateToken returns configured_machine_token on an exact match even if the database lookup misses. Router dispatches the authenticated request to POST /api/payments/process. PaymentController::process accepts the supplied merchant and card data, then atomically debits the matched active credit-card account and credits the merchant account. No authorization check ties process to a particular machine identity, merchant, or card owner. The standard .env.example and deployment flow do not set MACHINE_TOKEN, so the fallback is active by default.

#### Code evidence

```
Router.php:71-72 marks POST /api/payments/process and /api/payments/transfer as machine-authenticated. MachineAuthMiddleware.php:19-25 validates the supplied bearer token using MachineToken::validateToken. config/app.php defines machine_token as getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026'. MachineToken.php:25-34 accepts that fallback and returns name configured_machine_token. PaymentController.php:35 onward processes a merchant/card payment for the authenticated machine.
```

## 20. Avatar proxy allows SSRF and local file disclosure

- Lead reference: NIWE-020
- Category: A10
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Controllers/ProfileController.php:80
- Fingerprint: 2f1644138fb2681ddaa11fc64777831ba2aa5db53934057986d5d561fd10402a

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 65,
  "symbol": "ProfileController::avatarProxy",
  "input": "JSON body field url"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a valid, non-revoked bearer token and an existing user, but the avatar endpoint is intended for any authenticated user and has no privilege or destination restriction.",
  "The stream context only sets a five-second HTTP timeout and follow_location; it performs no scheme, host, IP, redirect, content-type, or size validation.",
  "The application and Docker configuration contain no wrapper or allow_url_fopen restriction that would block the demonstrated fetch paths."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Controllers/ProfileController.php",
  "line": 80,
  "symbol": "file_get_contents",
  "operation": "Server-side fetch of attacker-selected URL"
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
    "An authenticated customer supplies an attacker-controlled url to the avatar proxy endpoint.",
    "ProfileController passes the value directly to file_get_contents without scheme, host, address, redirect, or size controls.",
    "PHP stream wrappers fetch the selected resource with the server's network and filesystem privileges.",
    "The controller base64-encodes the returned bytes and includes them in its response.",
    "The caller reads internal HTTP responses or local files accessible to the application process."
  ],
  "impact": "Server-side request forgery into internal services and direct local file disclosure with response exfiltration.",
  "severity_reasoning": "High because an ordinary authenticated user controls a server-side fetch and receives the response, with no network or scheme restrictions.",
  "dynamic_test": "Authenticate as a test user and request the avatar proxy with a controlled loopback HTTP endpoint that returns a unique marker, then with a harmless test file URL if file wrappers are enabled. Verify whether each marker is returned base64-encoded. Do not target production metadata services or sensitive files."
}
```

#### Validator reasoning

Router.php registers POST /api/profile/avatar with auth=true, so an authenticated user reaches ProfileController::avatarProxy. The method decodes the request body, rejects only an empty url, and passes the attacker-controlled value unchanged to file_get_contents($data['url'], false, $context). A user can supply an HTTP URL targeting an internal service; follow_location also permits unvalidated redirects. A local filesystem path such as /etc/passwd is also accepted by file_get_contents, independently of HTTP wrapper settings. On success the bytes are base64-encoded and included in avatar_data in Response::success, with no response-size cap. Authentication is not an effective control against an authenticated-user SSRF or file-read claim.

#### Code evidence

```
Router.php:51 exposes authenticated POST /api/profile/avatar. ProfileController.php:65-68 reads attacker JSON data['url']; lines 71-80 create only an HTTP timeout/follow-redirect context and call file_get_contents($data['url'], false, $context). Lines 90-105 base64-encode the fetched content and return it in avatar_data.
```

## 21. Passwords are stored with unsalted MD5

- Lead reference: NIWE-021
- Category: A02
- Severity: MEDIUM
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:24
- Fingerprint: 5c32d13f4353ae5ba7e8202f223e13e9d210850093610b59b7f854afa7ec7e5d

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 13,
  "symbol": "AuthController::register",
  "input": "JSON body password"
}
```

#### Controls encountered

```
[
  "Registration input is length-limited to 128 characters, but no control changes the storage algorithm or adds a salt/slow KDF."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 24,
  "symbol": "AuthService::hashPassword",
  "operation": "md5 password hashing"
}
```

#### Counterevidence

```
[
  "The database write uses a prepared statement, which prevents SQL injection but does not mitigate weak password hashing."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "A user submits a password to POST /api/auth/register.",
    "The registration controller passes it to AuthService::hashPassword.",
    "hashPassword computes an unsalted MD5 digest.",
    "User::create stores the deterministic fast digest in users.password_hash.",
    "An actor who later obtains the user table can cheaply test large password dictionaries and correlate users with equal passwords."
  ],
  "impact": "Rapid offline recovery of common customer passwords after a database disclosure, with reuse risk against this and other services.",
  "severity_reasoning": "Medium because exploitation requires access to stored hashes, but MD5 provides inadequate resistance to password cracking and lacks per-user salts.",
  "dynamic_test": "Register two disposable users with the same test password, inspect their password_hash values through an authorized test fixture, and verify that both equal the expected MD5 digest. Run only a small controlled dictionary check against those test hashes."
}
```

#### Validator reasoning

The inspected registration path is concrete: AuthController::register reads the request JSON password, calls AuthService::hashPassword, and the service returns md5($password). User::create persists the returned value as users.password_hash via a prepared INSERT. The input length check only bounds the password and permits weak passwords; it does not make MD5 suitable for password storage. The prepared statement protects the SQL operation, not the confidentiality or cracking resistance of the stored digest. The candidate is therefore a reportable unsalted fast-hash password-storage issue.

#### Code evidence

```
Router.php registers POST /api/auth/register -> AuthController::register. AuthController.php reads password from php://input and sets 'password_hash' => AuthService::hashPassword($data['password']). AuthService.php:22-25 returns md5($password). User.php:29-38 inserts password_hash into users through a prepared statement.
```

## 22. Hardcoded admin JWT secret enables token forgery

- Lead reference: NIWE-022
- Category: A07
- Severity: HIGH
- Confidence: 0%
- Validation: pending
- Reportable: No
- Location: BankOfEd-main/src/Middleware/AdminAuthMiddleware.php:27
- Fingerprint: 3c7f639a0e421cf815c4eeb50aeb3175a985fb0540da44b38be42c5b66afdd9e

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/AdminAuthMiddleware.php",
  "line": 14,
  "symbol": "AdminAuthMiddleware::handle",
  "input": "HTTP Authorization bearer JWT"
}
```

#### Controls encountered

```
[
  "Issuer, expiry, revocation, and admin-record existence are checked, but all can be satisfied by a forged token except the need to guess/enumerate a valid admin ID."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Middleware/AdminAuthMiddleware.php",
  "line": 27,
  "symbol": "JWT::decode",
  "operation": "Admin authentication decision using default shared secret"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

Not available for this candidate

#### Code evidence

```
config/admin.php defines jwt_secret as getenv('ADMIN_JWT_SECRET') ?: 'bankofed-admin-secret-change-in-production'. AdminAuthMiddleware.php:27 decodes attacker-supplied bearer JWTs with that HS256 key, checks only issuer and revocation, then loads admin_users by payload->sub at lines 46-53. AdminRouter.php marks customer, account, FX, and system administration endpoints auth=true.
```

## 23. Login accepts weak MD5 password hashes

- Lead reference: NIWE-023
- Category: A02
- Severity: MEDIUM
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/AuthService.php:31
- Fingerprint: cf283b564212c6a65e32d76c80ec765f872988fcb404757e2fe132a1c38d8da6

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/AuthController.php",
  "line": 49,
  "symbol": "AuthController::login",
  "input": "JSON body password"
}
```

#### Controls encountered

```
[
  "Registration validates password length only and then unconditionally stores AuthService::hashPassword(), which returns md5($password).",
  "The public POST /api/auth/login route is registered with auth=false and directly calls AuthService::verifyPassword().",
  "The only branch condition is strlen($hash) === 32; application-generated MD5 hashes are 32 characters, so they reach the MD5 comparison.",
  "The login input is passed to md5($password) and compared with the stored value using ordinary equality."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/AuthService.php",
  "line": 31,
  "symbol": "AuthService::verifyPassword",
  "operation": "MD5 password verification"
}
```

#### Counterevidence

```
[
  "Non-32-character hashes are checked with password_verify(), so manually migrated bcrypt accounts would not use the MD5 branch."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External caller submits credentials to POST /api/auth/login.",
    "The login flow retrieves the user's stored password_hash and passes it with the supplied password to verifyPassword.",
    "For any 32-character stored hash, verifyPassword selects the legacy MD5 branch.",
    "The service computes md5 of the supplied password and compares it with ordinary equality.",
    "Accounts retaining MD5 hashes authenticate based on a fast, unsalted, non-constant-time verifier."
  ],
  "impact": "Continued exposure of legacy accounts to efficient offline password cracking, with a weaker comparison primitive in the authentication path.",
  "severity_reasoning": "Medium because the login endpoint preserves weak MD5-protected credentials; practical account takeover generally depends on obtaining or cracking a stored hash.",
  "dynamic_test": "Seed a disposable account with a known 32-character MD5 password hash. Attempt login with the matching and non-matching passwords and verify that the MD5 branch remains accepted. Separately measure only coarse repeated timings in a local test environment if assessing the comparison behavior."
}
```

#### Validator reasoning

Confirmed. There is a complete source-to-sink path: POST /api/auth/register accepts the password, AuthController calls AuthService::hashPassword(), and that method unconditionally returns md5($password), which User::create() stores as password_hash. On the public POST /api/auth/login route, the submitted password reaches AuthService::verifyPassword() after User::findByEmail(). Because the stored application-generated digest is exactly 32 characters, the method executes md5($password) === $hash. No authorization, rehash, algorithm allowlist, or stronger-password-storage control blocks this path. The password validator only enforces required/min/max constraints and does not mitigate MD5 storage. This is a concrete weak-password-hashing finding; the ordinary equality is a secondary comparison issue.

#### Code evidence

```
AuthController.php:49-68 reads JSON email/password, loads User::findByEmail(), and invokes AuthService::verifyPassword($data['password'], $user['password_hash']). AuthService.php:29-31 selects the MD5 branch solely when strlen($hash) === 32 and returns md5($password) === $hash.
```

## 24. External transfer debits arbitrary customer accounts

- Lead reference: NIWE-024
- Category: A01
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Account.php:13
- Fingerprint: 852585f39be2999ffc37bb126823f09146363d3ce78f3f778764f8db1643361c

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 88,
  "symbol": "TransactionController::transferExternal",
  "input": "JSON body field from_account_id"
}
```

#### Controls encountered

```
[
  "AuthMiddleware requires a valid non-revoked bearer token and supplies the authenticated user.",
  "The request validates from_account_id as numeric and casts it to int.",
  "Address-book destinations are checked with findByIdAndUser, but that check does not cover the source account; manual destinations have no ownership relationship to the source."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Account.php",
  "line": 13,
  "symbol": "Account::findById",
  "operation": "Account lookup without user ownership predicate before debit"
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
    "An authenticated customer sends POST /api/transfers/external with another customer's account ID as from_account_id.",
    "The endpoint accepts the object identifier from the request.",
    "TransferService resolves it using Account::findById, which filters by ID only and does not enforce ownership.",
    "The service debits that account and processes the attacker-chosen destination.",
    "Funds leave the victim account under the attacker's authenticated session."
  ],
  "impact": "Unauthorized transfer of funds from arbitrary customer accounts through broken object-level authorization.",
  "severity_reasoning": "High because authentication does not constrain the source account object, allowing direct financial loss for other customers.",
  "dynamic_test": "With attacker and victim test users, authenticate as the attacker and submit a minimal external transfer using the victim's account ID and a controlled destination. Verify whether the request succeeds and the victim's test balance is reduced."
}
```

#### Validator reasoning

Confirmed. Router.php exposes POST /api/transfers/external with auth=true, and AuthMiddleware supplies auth['user']; this establishes authentication only. TransactionController::transferExternal accepts the numeric JSON field from_account_id and passes it with the user to TransferService::transferExternal. In that service, userId is derived but the source is loaded with Account::findById($fromAccountId). Account::findById executes SELECT * FROM accounts WHERE id = ? with no user_id predicate. After only a null check, the same unowned ID reaches Account::updateBalance($fromAccountId, '-' . $debitAmount) inside the transaction, and the destination can be resolved and credited via Account::findByBsbAndNumber. No ownership, authorization, or balance control blocks the debit. The separate address-book ownership check validates only the destination entry.

#### Code evidence

```
TransactionController.php:79-105 accepts JSON from_account_id and passes it with auth['user'] to TransferService::transferExternal. TransferService.php:168-178 derives userId but calls Account::findById($fromAccountId) without an owner predicate. Account.php:10-15 executes SELECT * FROM accounts WHERE id = ?. TransferService.php:268-291 then calls Account::updateBalance($fromAccountId, '-' . $debitAmount) and credits the resolved destination inside a transaction.
```

## 25. External transfer can debit another user's account

- Lead reference: NIWE-025
- Category: API1
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:174
- Fingerprint: f54c5c9738d093bf7544e5b9a8f95f62134e99d427555b0c230c792b5817a2b4

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 93,
  "symbol": "TransactionController::transferExternal",
  "input": "JSON body from_account_id, destination and amount"
}
```

#### Controls encountered

```
[
  "POST /api/transfers/external requires a valid bearer token via AuthMiddleware.",
  "TransactionController validates from_account_id as numeric, amount format/positivity, and manual destination format.",
  "Address-book destinations are user-scoped and TOTP may be checked, but neither control binds from_account_id to the authenticated user."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 268,
  "symbol": "TransferService::transferExternal",
  "operation": "debit source account selected without ownership check"
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
    "Authenticated caller controls from_account_id, BSB, and account number in POST /api/transfers/external.",
    "TransactionController forwards the numeric source ID to TransferService::transferExternal.",
    "transferExternal uses Account::findById instead of Account::findByIdAndUser and performs no caller-ownership check.",
    "The service updates the selected account balance and records the transfer.",
    "The attacker's chosen external destination receives funds debited from another user."
  ],
  "impact": "Cross-customer account debit and theft of funds to an attacker-selected external destination.",
  "severity_reasoning": "High because an ordinary customer can bypass source-account ownership checks and invoke a direct debit operation.",
  "dynamic_test": "Set up two test customers, authenticate as one, and submit a small external transfer with the other customer's account ID and a controlled test BSB/account number. Confirm whether the victim account is debited and the transfer record names the supplied destination."
}
```

#### Validator reasoning

Confirmed. Router dispatches the authenticated POST /api/transfers/external request to TransactionController::transferExternal. The controller takes from_account_id directly from JSON, casts it to int, and passes it with the authenticated user to TransferService. transferExternal derives $userId but loads the source with Account::findById($fromAccountId), whose query filters only by account id; the available findByIdAndUser() query is not used. For any existing account belonging to another user, execution continues through destination and TOTP handling, then within the transaction calls Account::updateBalance($fromAccountId, '-' . $debitAmount). That update also filters only by id, and Transaction::create records the same foreign source account. Manual BSB/account-number input is format-validated but not ownership-restricted, so an authenticated attacker can debit a selected victim account and send the funds externally. Authentication, numeric validation, address-book scoping, and optional TOTP do not provide source-account authorization.

#### Code evidence

```
Router.php maps authenticated POST /api/transfers/external to TransactionController::transferExternal. TransactionController.php reads from_account_id, destination details, and amount from php://input and passes them to TransferService. TransferService.php:170-176 derives the authenticated user ID but calls Account::findById($fromAccountId) without user_id. Lines 267-270 call Account::updateBalance($fromAccountId, '-' . $debitAmount) and optionally credit the chosen internal destination. Account.php provides findByIdAndUser() but it is not used here.
```

## 26. Hard-coded fallback machine token authorizes payment transfers

- Lead reference: NIWE-026
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/MachineToken.php:23
- Fingerprint: c560e60f975ada60f63689c2b0c4e4f6320c2d697fd395ec120fb9e64afa3ee3

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Middleware/MachineAuthMiddleware.php",
  "line": 13,
  "symbol": "MachineAuthMiddleware::handle",
  "input": "HTTP Authorization bearer token"
}
```

#### Controls encountered

```
[
  "The active-token database lookup does not block the known token: install/seed.sql inserts SHA256('mch_face_insurance_secret_key_2026') as the active face_insurance token.",
  "PaymentController checks that the source account is active, the amount is positive, and the balance is sufficient.",
  "Transfers require the source account to be the FACE Insurance merchant account (id 100) or an account owned by user 16."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/MachineToken.php",
  "line": 25,
  "symbol": "MachineToken::validateToken",
  "operation": "Comparison against hard-coded fallback authentication secret"
}
```

#### Counterevidence

```
[
  "An operator who sets MACHINE_TOKEN to a non-default value would prevent the fallback comparison, so exploitability depends on deployment configuration.",
  "The source-account restriction limits the debit to the seeded FACE Insurance/user-16 funds."
]
```

#### Proof gaps

```
[
  "The running deployment's environment cannot be verified from source alone."
]
```

#### Attack path

```
{
  "nodes": [
    "Unauthenticated remote caller supplies the hard-coded fallback value in the Authorization Bearer header.",
    "MachineAuthMiddleware sends the raw token to MachineToken::validateToken.",
    "After no active database match, validateToken compares it to the configured value that defaults to the repository secret.",
    "A match creates the privileged configured_machine_token identity and Router permits POST /api/payments/transfer.",
    "PaymentController allows that identity to debit the FACE Insurance merchant account or an account owned by user 16 and transfer funds."
  ],
  "impact": "Unauthorized privileged payment transfers from the merchant or seeded-user accounts.",
  "severity_reasoning": "High because a repository-known fallback credential crosses an unauthenticated machine boundary and reaches a money-transfer sink when defaults are retained.",
  "dynamic_test": "In an isolated default-config deployment with no matching database token and MACHINE_TOKEN unset, call POST /api/payments/transfer with the fallback token and a minimal test transfer. Verify whether authentication resolves to configured_machine_token and whether the designated test source is debited."
}
```

#### Validator reasoning

A concrete unauthenticated request path exists: public/index.php routes /api requests to Router::dispatch; Router maps POST /api/payments/transfer to PaymentController::transfer with auth='machine'; MachineAuthMiddleware reads HTTP_AUTHORIZATION, extracts the bearer value, and calls MachineToken::validateToken. With no matching active DB row, config/app.php uses getenv('MACHINE_TOKEN') ?: 'mch_face_insurance_secret_key_2026', and MachineToken accepts that raw value and returns the configured_machine_token identity. PaymentController::transfer explicitly treats that identity as authorized for the seeded FACE Insurance account (account 100, user 16) and then calls Account::updateBalance on the source account before creating a completed transaction. The destination can be any external BSB/account or an existing BankOfEd account. The DB lookup is not an effective mitigation because seed.sql stores the same hard-coded token as an active face_insurance token, which also passes authentication and the same privileged source-account check.

#### Code evidence

```
MachineAuthMiddleware.php:13-24 reads HTTP_AUTHORIZATION and passes its bearer value to MachineToken::validateToken. MachineToken.php:10 hashes the input for DB lookup, but lines 23-31 load config and accept rawToken === fallbackToken, returning configured_machine_token. config/app.php:35 defaults MACHINE_TOKEN to mch_face_insurance_secret_key_2026. Router.php exposes POST /api/payments/transfer with machine auth. PaymentController.php:183-193 authorizes configured_machine_token for the FACE Insurance account or user 16, and lines 227-249 debit the source and create the transfer.
```

## 27. SQL injection through transaction sort parameter

- Lead reference: NIWE-027
- Category: A03
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Models/Transaction.php:40
- Fingerprint: e69692d636a297316f8cd314eadfcfd4ddf0f1324a14823f9e36dcf9cb433f26

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 17,
  "symbol": "TransactionController::index",
  "input": "GET sort"
}
```

#### Controls encountered

```
[
  "Router dispatches GET /api/transactions to TransactionController::index with AuthMiddleware::handle(), so authentication is required but does not constrain the sort string.",
  "TransactionController::index assigns $_GET['sort'] directly, with only a default when absent; there is no allowlist, validation, escaping, or normalization.",
  "Transaction::findByUser interpolates the string into ORDER BY t.{$sort} DESC in both the account_id and no-account branches.",
  "Database uses PDO native prepares, but only the separately supplied values are bound; the interpolated ORDER BY text is parsed as SQL before prepare."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Models/Transaction.php",
  "line": 40,
  "symbol": "Transaction::findByUser",
  "operation": "Untrusted string interpolation into SQL ORDER BY"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

```
[
  "No runtime probe was performed, so database-specific execution of a timing payload was not independently observed."
]
```

#### Attack path

```
{
  "nodes": [
    "An authenticated customer supplies a crafted sort query parameter to GET /api/transactions.",
    "The controller passes sort unchanged to Transaction::findByUser.",
    "The model interpolates it into ORDER BY t.{$sort} DESC; value placeholders do not protect this SQL expression slot.",
    "PDO executes the injected ORDER BY expression with application database privileges.",
    "Conditional ordering, errors, or timing behavior can be used to infer database values."
  ],
  "impact": "Authenticated SQL injection that can alter transaction queries and infer sensitive database data, with scope determined by the database driver.",
  "severity_reasoning": "High because arbitrary SQL expressions reach an ORDER BY sink for any authenticated user, enabling blind data extraction even if stacked statements are disabled.",
  "dynamic_test": "As a test customer on a disposable MySQL database, compare a normal sort with a harmless constant expression and then a conditional timing expression. Confirm injection through changed ordering or controlled latency without modifying data."
}
```

#### Validator reasoning

The source-to-sink path is concrete and reachable: an authenticated request to GET /api/transactions reaches TransactionController::index, reads the attacker-controlled GET parameter sort, and passes it unchanged to Transaction::findByUser. The model builds SQL strings containing ORDER BY t.{$sort} DESC at lines 40 and 55 before calling PDO::prepare. A value such as created_at,IF(1=1,SLEEP(5),0) becomes an additional MySQL ORDER BY expression; the trailing DESC does not prevent expression injection. The account ownership check only protects the optional account_id and does not affect sort. Native PDO prepares cannot parameterize SQL identifiers or expressions and therefore provide no blocking control here.

#### Code evidence

```
TransactionController.php:17 reads $_GET['sort'] without an allowlist and line 28 passes it to Transaction::findByUser. Transaction.php:40-46 constructs SELECT ... ORDER BY t.{$sort} DESC and executes it. Database.php sets native prepares, but sort is interpolated before prepare rather than bound.
```

## 28. Required TOTP can be omitted from external transfers

- Lead reference: NIWE-028
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: BankOfEd-main/src/Services/TransferService.php:231
- Fingerprint: 8226a359d4a85266b20c4a53d30b86db01808bdc92a99ccf6eb89048c6af7a42

### Evidence Chain

#### Source

```
{
  "file": "BankOfEd-main/src/Controllers/TransactionController.php",
  "line": 93,
  "symbol": "TransactionController::transferExternal",
  "input": "JSON body with omitted totp_code"
}
```

#### Controls encountered

```
[
  "The route requires a valid bearer token through AuthMiddleware, but that only authenticates the user and does not enforce TOTP.",
  "The frontend asks for TOTP or disables its button, but this is client-side behavior and does not protect the POST endpoint.",
  "A non-empty supplied code is verified with TotpService::verify(), but there is no rejection path when the code is absent."
]
```

#### Sink

```
{
  "file": "BankOfEd-main/src/Services/TransferService.php",
  "line": 268,
  "symbol": "TransferService::transferExternal",
  "operation": "funds transfer after skipped TOTP verification"
}
```

#### Counterevidence

```
[
  "TransactionController::transferExternal passes $data['totp_code'] ?? null and does not validate totp_code.",
  "The required-TOTP branch in TransferService::transferExternal has no else that rejects a missing code for enabled users.",
  "When totp_enabled is false, the code explicitly sets totpVerified false and continues.",
  "The subsequent debit, transaction creation, and Database::commit() execute regardless of totpVerified.",
  "checkTransfer and the UI are advisory and can be skipped by directly calling POST /api/transfers/external."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "An authenticated customer submits POST /api/transfers/external for a manual or unverified payee where checkTotpRequired returns required=true.",
    "The request omits totp_code, or the account has TOTP disabled.",
    "transferExternal checks the code only when totp_enabled is true and totp_code is non-empty.",
    "The required-TOTP decision is not enforced, so execution crosses the step-up authentication control without verification.",
    "The service updates balances and completes the external transfer."
  ],
  "impact": "Bypass of required step-up authentication for external transfers, allowing a session thief or authenticated attacker to complete transfers without the intended second factor.",
  "severity_reasoning": "High because a financial transaction explicitly marked as requiring TOTP can reach the balance-update sink without satisfying that control.",
  "dynamic_test": "With a disposable user for whom the chosen manual or unverified-payee transfer reports TOTP required, submit a small transfer without totp_code. Repeat with TOTP enabled and the code omitted. Verify whether either transfer completes and changes the test balance."
}
```

#### Validator reasoning

Confirmed. An authenticated caller can submit a valid manual external transfer with no totp_code. The controller accepts the omitted field as null and passes it to TransferService. For manual transfers, checkTotpRequired() returns required=true. If TOTP is enabled, !empty($totpCode) is false for null, so neither verification nor rejection occurs. If TOTP is disabled, the service explicitly continues. In either case, totpVerified remains false, but there is no later guard on that flag; the service debits the source account, creates a completed transaction, and commits it. The same path applies to an owned unverified address-book payee. The only relevant control is client-side UI logic, which is bypassed by a direct request.

#### Code evidence

```
TransactionController.php:93-132 accepts optional totp_code from the JSON body and passes null when omitted. TransferService.php:225-242 enters the required branch, but disabled TOTP explicitly proceeds and enabled TOTP is verified only inside elseif (!empty($totpCode)); there is no rejecting else. Lines 266-300 then debit the source, create the transaction, and commit. TotpService::verify() itself uses the OTPHP verifier, but it is skipped when the code is absent.
```
