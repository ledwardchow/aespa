# SAST Report: Goosecable — TAC1

- Exported: 27/09/2026, 12:34:26
- Total issues: 46

## Issue Summary

| # | Severity | Candidate | Confidence | Validation | Reportable | Location |
|---:|---|---|---:|---|---|---|
| 1 | HIGH | Fixed seeded administrator credentials allow full application takeover | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:92 |
| 2 | HIGH | Repository-wide default JWT key allows customer token forgery | 97% | confirmed | Yes | GooseCable-main/src/main/resources/application.properties:22 |
| 3 | MEDIUM | Claim submission accepts incidents outside the insured period | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:62 |
| 4 | HIGH | Legacy motor quote can be bound without required disclosures or complete risk data | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:111 |
| 5 | MEDIUM | Contact-centre users can add privileged claim notes | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java:103 |
| 6 | HIGH | Legacy home quote can be bound without underwriting or disclosure checks | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:233 |
| 7 | HIGH | Claim lifecycle transitions are not enforced server-side | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java:196 |
| 8 | MEDIUM | Contact-centre users can add notes to any claim | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java:103 |
| 9 | HIGH | Unapproved claims can be disbursed | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:140 |
| 10 | HIGH | Legacy contents quote can be bound without underwriting or disclosure checks | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:287 |
| 11 | HIGH | Managers can disburse unapproved claims by calling the endpoint directly | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:139 |
| 12 | HIGH | Claim funds can be disbursed before approval | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:134 |
| 13 | MEDIUM | Claim status endpoints do not enforce valid workflow transitions | 98% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:117 |
| 14 | HIGH | Concurrent disbursement requests can pay the same claim more than once | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:134 |
| 15 | HIGH | Default SSO signing secret enables customer account takeover | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/security/SsoTokenValidator.java:20 |
| 16 | HIGH | Any staff account can reset any customer's portal password | 0% | pending | No | GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerController.java:74 |
| 17 | HIGH | Concurrent disbursement requests can pay the same claim twice | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:134 |
| 18 | HIGH | Hard-coded JWT signing key allows customer account impersonation | 96% | confirmed | Yes | GooseCable-main/src/main/resources/application.properties:20 |
| 19 | HIGH | Claims can be disbursed before approval | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:134 |
| 20 | HIGH | Default SSO signing secret allows forged SSO login | 99% | confirmed | Yes | GooseCable-main/src/main/resources/application.properties:24 |
| 21 | HIGH | Payment gateway uses a published default bearer token | 96% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/BankOfEdPaymentClient.java:32 |
| 22 | HIGH | Default SSO signing secret allows forged customer tokens | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/security/SsoTokenValidator.java:20 |
| 23 | HIGH | Payment requests and bearer credentials are sent over cleartext HTTP | 95% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/BankOfEdPaymentClient.java:75 |
| 24 | HIGH | Hard-coded default SSO signing secret allows customer impersonation | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/security/SsoTokenValidator.java:21 |
| 25 | MEDIUM | Customer password authentication has no brute-force protection | 96% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java:46 |
| 26 | MEDIUM | Claim submission accepts incidents outside the policy coverage period | 98% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:66 |
| 27 | HIGH | Legacy motor quote fields bypass binding and premium controls | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:113 |
| 28 | HIGH | Policy binding skips motor eligibility checks when quoteVersion is null | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:549 |
| 29 | HIGH | Legacy home quote request creates bindable zero-premium policies | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:235 |
| 30 | HIGH | Legacy contents quote request creates bindable zero-premium policies | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:285 |
| 31 | MEDIUM | Concurrent policy binds can generate duplicate policy numbers | 97% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:653 |
| 32 | HIGH | Seeded default staff credentials expose customer password reset | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:112 |
| 33 | HIGH | Seeded administrator credentials are written to application logs | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:567 |
| 34 | MEDIUM | Claim uploads trust attacker-supplied MIME type and can distribute malicious files | 96% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:219 |
| 35 | MEDIUM | Policy bind and cancel operations allow lost-update state races | 98% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:610 |
| 36 | HIGH | Hard-coded JWT signing key allows customer account impersonation | 96% | confirmed | Yes | GooseCable-main/src/main/resources/application.properties:24 |
| 37 | HIGH | Default SSO shared secret permits unauthenticated account takeover | 99% | confirmed | Yes | GooseCable-main/src/main/resources/application.properties:29 |
| 38 | MEDIUM | Claim number generation races under concurrent submissions | 98% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:236 |
| 39 | HIGH | Default administrator credentials are seeded and exposed on the login page | 99% | inconclusive | No | GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:94 |
| 40 | HIGH | Concurrent disbursement requests can pay the same claim more than once | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:151 |
| 41 | HIGH | Legacy motor quote fields bypass binding and premium controls — bindPolicy uses nullable quoteVersion as a security-relevant signal and skips co | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:113 |
| 42 | HIGH | Seeded default staff credentials expose customer password reset — Customer credential reset is available to every authenticated internal role with | 98% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:112 |
| 43 | HIGH | Seeded administrator credentials are written to application logs — Privileged demo accounts use fixed, publicly knowable passwords | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:567 |
| 44 | MEDIUM | Claim number generation races under concurrent submissions — The synchronization scope does not include the database insert and cannot coordi | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:236 |
| 45 | HIGH | Default administrator credentials are seeded and exposed on the login page — The unauthenticated login page discloses the privileged default credentials base | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:94 |
| 46 | HIGH | Concurrent disbursement requests can pay the same claim more than once — The external transfer request does not carry a stable idempotency key for the cl | 99% | confirmed | Yes | GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:151 |

## 1. Fixed seeded administrator credentials allow full application takeover

- Lead reference: FHZM-001
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:92
- Fingerprint: 4eaeb2db65e1339872b4aa1967418bc5b08d42fe9b5fec77624f885dad5b1b51

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/resources/templates/login.html",
  "line": 35,
  "symbol": "POST /login",
  "input": "attacker-supplied username and password"
}
```

#### Controls encountered

No controls recorded

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java",
  "line": 92,
  "symbol": "seed",
  "operation": "creates active fixed-password ADMIN account"
}
```

#### Counterevidence

```
[
  "The main form-login chain keeps CSRF enabled, but /login is public and the login form can be fetched first to obtain any required token; this does not block credential use.",
  "The README describes localhost as the default deployment, but the repository also documents server and Docker deployments, so reachability is an environmental assumption rather than a source-level mitigation."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated actor reaches the staff login page and learns or derives the seeded admin/admin123 credentials.",
    "DataInitializer creates the active ADMIN account when the user table is empty; the reset query parameter also discloses the credentials.",
    "Spring Security authenticates the fixed credentials and grants ROLE_ADMIN.",
    "The actor crosses the authentication and admin-role checks and reaches privileged customer, policy, claim, user, and reset operations."
  ],
  "impact": "Full administrative takeover, including sensitive-record access and privileged mutations.",
  "severity_reasoning": "High because an unauthenticated remote actor can obtain a fixed privileged credential and gain full application control.",
  "dynamic_test": "On a fresh test database, request the login page with the reset parameter, authenticate as admin/admin123, then verify access to one harmless admin-only read and a reversible privileged mutation."
}
```

#### Validator reasoning

DataInitializer is a Spring CommandLineRunner. Its run() method calls seed() whenever userRepository.count() is zero, and resetAndSeed() also calls the same seed() routine after deleting users. seed() creates an active user with username admin, passwordEncoder.encode("admin123"), and role UserRole.ADMIN. UserService.loadUserByUsername() rejects only inactive users and maps the stored role to ROLE_ADMIN. SecurityConfig permits the public /login page and form processing, while /admin/** requires ADMIN; AdminController also applies @PreAuthorize("hasRole('ADMIN')") and exposes user creation, activation/deactivation, password reset, database reset, and machine-token operations. login.html displays the same credentials for any request containing ?reset. No profile guard, generated/externally supplied password, forced password change, or other source-level control prevents an unauthenticated reachable user from logging in with these fixed credentials and obtaining the privileged role.

#### Code evidence

```
DataInitializer.run() calls seed() whenever userRepository.count() is zero. seed() saves username("admin"), password(passwordEncoder.encode("admin123")), role(UserRole.ADMIN), active(true). UserService.loadUserByUsername() maps this role to ROLE_ADMIN. login.html:32 renders 'Credentials: admin / admin123' when ?reset is supplied.
```

## 2. Repository-wide default JWT key allows customer token forgery

- Lead reference: FHZM-002
- Category: A02
- Severity: HIGH
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/resources/application.properties:22
- Fingerprint: 5bda8ee4e90d0ef2deab271f0d3903271447c2061c5cd1bd8e8720e9d5ac7e58

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/resources/application.properties",
  "line": 22,
  "symbol": "app.jwt.secret",
  "input": "known committed HMAC secret"
}
```

#### Controls encountered

```
[
  "Docker entrypoint generates a random APP_JWT_SECRET when the container environment does not provide one, and persists it in /app/secrets.",
  "Deployment documentation instructs operators to replace app.jwt.secret with a random Base64 key.",
  "The issue is conditional on deployments that run the packaged JAR or otherwise omit an override."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/security/JwtAuthenticationFilter.java",
  "line": 31,
  "symbol": "doFilterInternal",
  "operation": "grants ROLE_CUSTOMER based on attacker-forged JWT subject"
}
```

#### Counterevidence

```
[
  "The Docker deployment path has a compensating secret-generation control.",
  "Documentation warns operators to replace the committed value."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Remote actor obtains the repository default app.jwt.secret and identifies a customer email.",
    "The actor creates a correctly signed customer JWT with that email as the subject.",
    "JwtTokenProvider and JwtAuthenticationFilter accept the HMAC signature and install ROLE_CUSTOMER.",
    "CustomerApiController resolves the forged subject directly to the victim customer.",
    "The actor reaches victim profile, policy, claim, upload, quote, and bind operations."
  ],
  "impact": "Customer impersonation and unauthorized read or modification of customer insurance data.",
  "severity_reasoning": "High because a repository-known signing key removes the customer authentication boundary in default deployments.",
  "dynamic_test": "Run the application without APP_JWT_SECRET, mint a short-lived test token for a seeded customer using the committed key, and verify that a profile request returns that customer's identity."
}
```

#### Validator reasoning

Confirmed. application.properties contains a committed Base64 HMAC secret, and JwtTokenProvider decodes it and uses it for both signing and verification. JwtAuthenticationFilter accepts any token that verifies with that key, extracts its subject, and creates ROLE_CUSTOMER without checking that the subject authenticated through the customer login flow. CustomerApiController.resolveCustomer() then uses auth.getName() as the email passed to CustomerService.findByEmail(), which directly loads the customer. Thus an attacker who knows the committed key can forge a non-expired JWT with the subject set to any known customer email and reach GET /api/customer/profile and the other customer API endpoints. SecurityConfig requires authentication for those endpoints but provides no stronger authorization check. The Docker entrypoint mitigates its own container path, and deployment docs recommend an override, but direct JAR execution and deployments that omit the override still load the committed application.properties value, so those controls do not defeat the conditional claim.

#### Code evidence

```
application.properties defines app.jwt.secret=bXktdW5pcXVlLWFuZC12ZXJ5LXNlY3JldC1rZXktZm9yLWp3dC10b2tlbnM=. JwtTokenProvider signs and verifies tokens with this key and uses the subject as email. JwtAuthenticationFilter accepts any valid token as ROLE_CUSTOMER, and CustomerApiController.resolveCustomer() loads the customer by auth.getName().
```

## 3. Claim submission accepts incidents outside the insured period

- Lead reference: FHZM-003
- Category: A04
- Severity: MEDIUM
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:62
- Fingerprint: 7f97ce5ace4eac36eff815d02ad3ce36d0f496d4740d4a2a93df25e36be0ff18

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 138,
  "symbol": "submitClaim",
  "input": "JSON incidentDate and policyId"
}
```

#### Controls encountered

```
[
  "CustomerApiController.submitClaim requires authentication and checks that the requested policy belongs to the acting customer.",
  "The controller requires incidentDate to be non-null and validates additional motor-claim fields when applicable.",
  "ClaimService.createClaim requires the policy's current status to be ACTIVE."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 68,
  "symbol": "createClaim",
  "operation": "persists OPEN claim"
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
    "Authenticated customer selects a policy they own and submits a claim through the customer claim API.",
    "The request supplies an attacker-chosen incidentDate.",
    "Ownership and current ACTIVE status checks pass.",
    "ClaimService omits coverage-period and future-date validation and persists an OPEN claim.",
    "The invalid claim enters staff review and payment workflows."
  ],
  "impact": "Invalid or fraudulent claims can enter the normal adjudication and payment process.",
  "severity_reasoning": "Medium because customer authentication and policy ownership are required, but core coverage-date rules are bypassed.",
  "dynamic_test": "Using an owned active policy, submit separate test claims dated before startDate, after endDate, and in the future; confirm whether each is stored as OPEN."
}
```

#### Validator reasoning

Confirmed. POST /api/customer/claims accepts the JSON incidentDate in SubmitClaimRequest; its only constraint is @NotNull. CustomerApiController.submitClaim copies that value directly into ClaimForm after ownership checking and calls ClaimService.createClaim. ClaimService.createClaim reloads the policy, checks only PolicyStatus.ACTIVE, then assigns form.getIncidentDate() to Claim.incidentDate and saves a ClaimStatus.OPEN record. Claim and Policy entities have no temporal constraint or lifecycle callback, and the repository contains no automatic expiry check or other incident-date comparison. Policy has explicit startDate and endDate fields, including seeded ACTIVE policies with bounded periods, so dates before startDate, after endDate, and future dates can reach persistence. Authentication, ownership, and ACTIVE status do not block those dates; the claim is accepted for subsequent review.

#### Code evidence

```
CustomerApiController.submitClaim maps request.incidentDate into ClaimForm after ownership validation. SubmitClaimRequest.incidentDate has only @NotNull. ClaimService.createClaim checks only policy.getStatus() == ACTIVE and then persists form.getIncidentDate(), without comparison to policy dates or LocalDate.now().
```

## 4. Legacy motor quote can be bound without required disclosures or complete risk data

- Lead reference: FHZM-004
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:111
- Fingerprint: b80c10ee1ba9a85a341ea26be86556f3b44b78c56d22afe065139e1fc4c2f85a

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 218,
  "symbol": "requestMotorQuote",
  "input": "legacy flat MotorQuoteRequest JSON"
}
```

#### Controls encountered

```
[
  "CustomerApiController requires authentication and checks policy ownership before calling bindPolicy.",
  "The legacy branch requires vehicleReg, make, model, year, positive estimatedValue, coverType, main driver name/date of birth, and startDate.",
  "The request DTO applies @Valid to the nested structured objects, but those objects are null on the legacy path; the flat legacy fields are not constrained by nested structured validation."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 544,
  "symbol": "bindPolicy",
  "operation": "sets incomplete quote status ACTIVE"
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
    "Authenticated customer calls the motor quote API with the legacy flat JSON shape and omits the structured vehicle object.",
    "PolicyService selects the legacy branch and creates a QUOTED policy without required disclosure and risk metadata or quoteVersion.",
    "The customer invokes the bind endpoint for the owned quote.",
    "bindPolicy conditions strict validation on non-null quoteVersion, so the legacy quote crosses the underwriting controls.",
    "The service activates incomplete motor coverage."
  ],
  "impact": "A customer can activate motor coverage that was never eligible or properly underwritten.",
  "severity_reasoning": "High because an authenticated customer can deliberately bypass mandatory underwriting and disclosure controls.",
  "dynamic_test": "Create a legacy motor quote missing disclosures and structured risk data, then bind it and confirm the resulting policy becomes ACTIVE."
}
```

#### Validator reasoning

A customer can POST /api/customer/quotes/motor with vehicle omitted and the required legacy flat fields. PolicyService.createMotorQuote(MotorQuoteRequest) then constructs MotorPolicyForm using only those flat fields and calls createMotorQuote(MotorPolicyForm, User). That method stores a QUOTED MotorPolicy with no garaging, usage, payment frequency/basic excess, structured drivers, or disclosure timestamps. isStructuredMotorComplete(policy) is false, so quoteVersion and quoteExpiresAt remain null, while the legacy fallback still sets annualPremium and saves the policy. The customer receives the persisted policy id as quoteId. On POST /api/customer/policies/{id}/bind, the controller verifies only authentication and ownership, then PolicyService.bindPolicy checks status and enters the motor expiry/disclosure/completeness checks only when quoteVersion is non-null. Because the legacy policy has quoteVersion null, those checks are skipped and status is set to ACTIVE with a policy number. The controls limit access to the owning authenticated customer but do not block activation of the incomplete quote.

#### Code evidence

```
createMotorQuote(MotorQuoteRequest) branches on request.getVehicle()==null, copies only legacy fields, and calls createMotorQuote(MotorPolicyForm). That method leaves quoteVersion null unless isStructuredMotorComplete(policy) is true. bindPolicy checks expiry, acknowledgements, and isStructuredMotorComplete only inside `if (policy instanceof MotorPolicy motor && motor.getQuoteVersion() != null)`, then sets ACTIVE.
```

## 5. Contact-centre users can add privileged claim notes

- Lead reference: FHZM-005
- Category: A01
- Severity: MEDIUM
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java:103
- Fingerprint: fc6494d0ca1316fbf7a59d71bdee694367cf2d395a19013efa218c876f2308fa

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 104,
  "symbol": "addNote",
  "input": "Authenticated POST path id and noteForm"
}
```

#### Controls encountered

```
[
  "The main Spring Security chain requires an authenticated principal and leaves POST /claims/{id}/note under anyRequest().authenticated().",
  "CSRF protection and @Valid input validation apply, but neither checks the user's role or claim ownership.",
  "The note form is rendered without a MANAGER/ADMIN authorization condition."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 218,
  "symbol": "addNote",
  "operation": "claimNoteRepository.save(note)"
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
    "Actor authenticates as a CONTACT_CENTRE staff user.",
    "The actor chooses any claim id and posts attacker-controlled text to /claims/{id}/note.",
    "SecurityConfig requires authentication but applies no manager/admin role check.",
    "ClaimController and ClaimService perform no further authorization.",
    "The note is saved as an authoritative staff entry on the selected claim."
  ],
  "impact": "Unauthorized staff can alter claim records and influence later claim handling.",
  "severity_reasoning": "Medium because staff authentication is required, but a lower-privileged role can modify any claim.",
  "dynamic_test": "Authenticate as a CONTACT_CENTRE test user, post a unique benign marker to a claim outside that user's expected duties, and verify the marker appears in the claim notes."
}
```

#### Validator reasoning

Confirmed. ClaimController.addNote maps POST /claims/{id}/note and has no @PreAuthorize or other role check. SecurityConfig restricts only the listed claim transition paths to MANAGER/ADMIN; this note path falls through to anyRequest().authenticated(). UserService assigns ROLE_CONTACT_CENTRE to active contact-centre users, including the seeded staff account, so that role can authenticate on the web chain. The controller loads the authenticated User and passes the attacker-controlled path id and validated note form to ClaimService.addNote. ClaimService.findById(id) loads any claim by id, then ClaimNote.builder().claim(claim).author(author).content(form.getContent()) is persisted by claimNoteRepository.save(note). The documented MANAGER/ADMIN permission is not enforced in executable code. CSRF only requires a token for the authenticated web request and does not prevent a contact-centre user from submitting a same-origin request with a token obtained from the application.

#### Code evidence

```
ClaimController.java:103-113 maps POST /claims/{id}/note and calls claimService.addNote(id, form, user) without @PreAuthorize. SecurityConfig.java:76-80 protects specific claim transitions with MANAGER/ADMIN but falls through to anyRequest().authenticated() for /claims/*/note. ClaimService.java:211-219 persists the note against findById(claimId). docs/plan.md:84-86 says MANAGER has CONTACT_CENTRE permissions plus add claim notes.
```

## 6. Legacy home quote can be bound without underwriting or disclosure checks

- Lead reference: FHZM-006
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:233
- Fingerprint: 45f9b879fa0dfca7aa77adbfc086f18dc238dd755a4ef8d37edc11e2a1890347

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 234,
  "symbol": "requestHomeQuote",
  "input": "legacy flat HomeQuoteRequest JSON"
}
```

#### Controls encountered

```
[
  "Spring Security requires an authenticated customer or machine token for /api/customer/**.",
  "The bind controller checks that the policy belongs to the resolved customer.",
  "@Valid and createLegacyHomeQuote require the legacy flat fields, with size, range, and non-null checks for the fields used to construct the policy."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 544,
  "symbol": "bindPolicy",
  "operation": "sets unchecked home quote ACTIVE"
}
```

#### Counterevidence

```
[
  "The legacy branch is intentionally reachable when address is null, so the presence of the structured contract does not block it.",
  "The ownership check limits which policy can be bound but does not validate the quote's underwriting or disclosure data."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated customer calls the home quote API without a structured address.",
    "PolicyService enters createLegacyHomeQuote and creates a QUOTED HomePolicy with null quoteDetails.",
    "The customer binds the owned quote.",
    "bindPolicy skips residential expiry, disclosure, completeness, and eligibility checks when quoteDetails is null.",
    "The incomplete home policy becomes ACTIVE."
  ],
  "impact": "Home coverage can be activated without required underwriting and disclosures.",
  "severity_reasoning": "High because a customer can intentionally select a legacy shape that bypasses all residential bind controls.",
  "dynamic_test": "Submit a legacy home quote without address, disclosures, or eligibility fields, bind it, and confirm ACTIVE status."
}
```

#### Validator reasoning

The source-to-sink path is concrete. CustomerApiController.requestHomeQuote accepts HomeQuoteRequest and calls PolicyService.createHomeQuote. When request.getAddress() is null, createHomeQuote immediately calls createLegacyHomeQuote instead of validateHomeQuote. That method only checks propertyAddress, propertyType, rebuildValue, yearBuilt, bedroomCount, and startDate, copies those fields into HomePolicyForm, and calls the form overload. The form overload creates a HomePolicy with status QUOTED and never sets its embedded ResidentialQuoteDetails, leaving quoteDetails null. On POST /api/customer/policies/{id}/bind, the controller resolves the customer, verifies ownership, and calls bindPolicy. bindPolicy checks only that status is QUOTED; its home-specific validation is guarded by home.getQuoteDetails() != null, so the legacy policy skips expiry, disclosure, completeness, occupancy/history, eligibility, and cover checks. It then sets status ACTIVE, generates a policy number, and saves the policy. The basic legacy field validation and authentication/ownership controls do not block the claimed activation path.

#### Code evidence

```
createHomeQuote returns createLegacyHomeQuote when request.getAddress()==null. The legacy method accepts only propertyAddress, propertyType, rebuildValue, yearBuilt, bedroomCount, and startDate, then calls the form overload, which does not create ResidentialQuoteDetails. bindPolicy calls validateResidentialBinding(home.getQuoteDetails(), true) only when home.getQuoteDetails()!=null, then sets ACTIVE.
```

## 7. Claim lifecycle transitions are not enforced server-side

- Lead reference: FHZM-007
- Category: A01
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java:196
- Fingerprint: 5578305f25d9264fe361baf11c5cd5bed163ab0b90f3da9b9b867dc0f655422a

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 196,
  "symbol": "markPaid",
  "input": "Authenticated manager-controlled claim id"
}
```

#### Controls encountered

```
[
  "ClaimController routes /claims/{id}/review, /approve, /reject, and /paid through Spring Security role checks for MANAGER or ADMIN.",
  "The web filter chain retains Spring Security's default CSRF protection for these POST routes.",
  "The service loads the claim in a transaction before saving it, so the status change is persisted."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 116,
  "symbol": "updateStatus",
  "operation": "claim.setStatus(newStatus) and repository save"
}
```

#### Counterevidence

```
[
  "The UI restricts which forms are rendered by current status, but those Thymeleaf conditions are not applied by the controller or service.",
  "ClaimService.disburseClaim has checks for PAID and REJECTED, but /claims/{id}/paid does not call disburseClaim and instead calls updateStatus directly."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Actor authenticates with MANAGER or ADMIN privileges.",
    "The actor directly calls a review, approve, reject, or paid endpoint for a claim in an incompatible state.",
    "The role check passes, while UI button visibility is bypassed.",
    "ClaimService.updateStatus overwrites the status without checking the current state.",
    "The claim and payment lifecycle is placed into an invalid state."
  ],
  "impact": "Privileged users can corrupt claim and payment state or bypass required workflow steps.",
  "severity_reasoning": "High because direct requests can mark unapproved claims paid and undermine financial workflow integrity.",
  "dynamic_test": "As a manager, call the paid endpoint for an OPEN test claim and the reject endpoint for a PAID test claim; verify whether both invalid transitions persist."
}
```

#### Validator reasoning

The source-to-sink path is concrete: an authenticated MANAGER or ADMIN can POST /claims/{id}/paid, ClaimController.markPaid passes ClaimStatus.PAID to ClaimService.updateStatus, and updateStatus loads the claim, unconditionally calls claim.setStatus(newStatus), and saves it. The same unchecked helper is used by review, approve, and reject. There is no current-status check in updateStatus, no database transition constraint found in the inspected resources, and no other caller-side state check. Therefore a manager can set an OPEN, UNDER_REVIEW, REJECTED, or already-PAID claim to PAID, or perform the other out-of-sequence transitions, by calling the endpoint directly. Role and CSRF controls limit who can submit the request but do not enforce the lifecycle.

#### Code evidence

```
ClaimController.java:145-203 exposes role-protected transition endpoints that call claimService.updateStatus without checking current status. ClaimService.java:113-122 loads the claim and directly sets any requested status. templates/claims/view.html:31-53 shows intended transitions: review only OPEN, approve/reject only OPEN or UNDER_REVIEW, and paid/disburse only APPROVED or PAYMENT_FAILED.
```

## 8. Contact-centre users can add notes to any claim

- Lead reference: FHZM-008
- Category: A01
- Severity: MEDIUM
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java:103
- Fingerprint: e67ffab3ce47c646299f0eed88d24d37e5e601cddfbfda04ec312b1a718cddeb

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 104,
  "symbol": "addNote",
  "input": "PathVariable id and validated note form from any authenticated web user"
}
```

#### Controls encountered

```
[
  "The main web SecurityFilterChain requires authentication for unmatched routes.",
  "CSRF protection requires a valid token for browser POSTs.",
  "ClaimNoteForm enforces nonblank content and a 5000-character maximum."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 217,
  "symbol": "addNote",
  "operation": "claimNoteRepository.save(note)"
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
    "Actor authenticates as CONTACT_CENTRE.",
    "The actor selects any claim id and calls POST /claims/{id}/note.",
    "The main security chain checks only that the actor is authenticated.",
    "No controller or service role or claim-scope check blocks the request.",
    "The supplied note is persisted on the target claim."
  ],
  "impact": "A lower-privileged staff user can modify any claim's authoritative notes.",
  "severity_reasoning": "Medium because the flaw crosses the documented manager-only authorization boundary but still requires staff access.",
  "dynamic_test": "Log in as CONTACT_CENTRE, add a harmless unique note to an arbitrary claim, and confirm persistence."
}
```

#### Validator reasoning

ClaimController.addNote maps POST /claims/{id}/note and has no @PreAuthorize or other role check. SecurityConfig restricts only selected claim state routes to MANAGER/ADMIN, then applies anyRequest().authenticated(), so an authenticated CONTACT_CENTRE principal reaches this handler. The handler resolves the principal only to record the author and passes the attacker-selected path id to ClaimService.addNote. That service calls findById(id), builds a ClaimNote with the supplied content, and saves it without checking the user's role or claim scope. The seeded CONTACT_CENTRE user and the documented role model show this is a reachable role boundary. CSRF and form validation do not prevent an intentional authenticated user from submitting the request.

#### Code evidence

```
ClaimController.java:103-113 defines addNote without @PreAuthorize and calls claimService.addNote(id,...). SecurityConfig.java:78-80 role-restricts selected claim state endpoints, then uses anyRequest().authenticated(), leaving /claims/*/note open to every logged-in role. ClaimService.java:209-218 loads the attacker-selected claim and saves the note. docs/plan.md:88-91 says MANAGER has the added permission to add claim notes, while CONTACT_CENTRE can create claims.
```

## 9. Unapproved claims can be disbursed

- Lead reference: FHZM-009
- Category: A01
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:140
- Fingerprint: 7190668d89043cb1c30c730af3b6da8753d5c7ec688ded145ef27ef1f31f1b20

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 207,
  "symbol": "disburse",
  "input": "Manager-controlled claim id, payout account, payee, amount, and reference"
}
```

#### Controls encountered

```
[
  "POST endpoint requires an authenticated user with MANAGER or ADMIN through @PreAuthorize and the web SecurityFilterChain.",
  "ClaimDisbursementForm bean validation restricts amount and basic payout-field formats.",
  "CSRF protection applies to the web form request.",
  "The service rejects claims already in PAID or REJECTED state."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 151,
  "symbol": "disburseClaim",
  "operation": "bankOfEdPaymentClient.transfer"
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
    "Actor authenticates as MANAGER or ADMIN and selects an OPEN or UNDER_REVIEW claim.",
    "The actor directly posts destination account and amount to /claims/{id}/disburse.",
    "Endpoint role authorization passes, but the UI-only approval sequence is bypassed.",
    "ClaimService rejects only PAID and REJECTED states and calls BankOfEdPaymentClient.",
    "The external transfer occurs before the claim is marked PAID."
  ],
  "impact": "Funds can be sent to an actor-chosen account without claim approval.",
  "severity_reasoning": "High because an authorized manager can trigger a real financial transfer while bypassing the approval control.",
  "dynamic_test": "Against a stub payment gateway, disburse an OPEN test claim as manager and verify one outbound transfer request is received before any approval action."
}
```

#### Validator reasoning

The request path is reachable: ClaimController.disburse handles POST /claims/{id}/disburse for users with MANAGER or ADMIN and passes the validated ClaimDisbursementForm directly to ClaimService.disburseClaim. The service rejects only PAID and REJECTED. OPEN and UNDER_REVIEW therefore proceed to normalize the submitted BSB/account/payee and take the submitted settledAmount, then call bankOfEdPaymentClient.transfer. A successful result sets the claim to PAID and saves it; a failed result still records PAYMENT_FAILED. The template condition only hides the form for unapproved states and does not protect the endpoint. Bean validation, role checks, and CSRF do not enforce approval state.

#### Code evidence

```
ClaimController.java:206-226 accepts a manager-controlled ClaimDisbursementForm and calls disburseClaim. ClaimService.java:128-143 rejects only PAID and REJECTED, copies form payout details and amount, then calls bankOfEdPaymentClient.transfer. templates/claims/view.html:44-53 only presents disbursement for APPROVED or PAYMENT_FAILED claims, confirming the intended prerequisite is UI-only.
```

## 10. Legacy contents quote can be bound without underwriting or disclosure checks

- Lead reference: FHZM-010
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:287
- Fingerprint: 8cd4a0a9f04de47d1e400e16a5260266d11aa3213064d5c13e0bbffbe2ad543a

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 249,
  "symbol": "requestContentsQuote",
  "input": "legacy flat ContentsQuoteRequest JSON"
}
```

#### Controls encountered

```
[
  "Customer API requires authentication and the bind controller checks that the policy belongs to the acting customer.",
  "The flat DTO enforces only a positive contentsValue; service logic requires a non-null startDate."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 544,
  "symbol": "bindPolicy",
  "operation": "sets unchecked contents quote ACTIVE"
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
    "Authenticated customer calls the contents quote API without a structured address.",
    "PolicyService enters createLegacyContentsQuote and creates a QUOTED ContentsPolicy with null quoteDetails.",
    "The customer calls bind for the owned quote.",
    "bindPolicy skips residential expiry, disclosure, completeness, and eligibility checks because quoteDetails is null.",
    "The incomplete contents policy becomes ACTIVE."
  ],
  "impact": "Contents coverage can be activated without required underwriting controls.",
  "severity_reasoning": "High because the legacy request shape lets customers bypass the full residential eligibility and disclosure process.",
  "dynamic_test": "Create a legacy contents quote missing structured address, disclosures, and eligibility data, then bind it and confirm ACTIVE status."
}
```

#### Validator reasoning

The API accepts a ContentsQuoteRequest with address omitted. createContentsQuote routes that request to createLegacyContentsQuote, which checks only contentsValue and startDate, copies the flat fields into ContentsPolicyForm, and calls the form overload. The form overload creates a QUOTED ContentsPolicy without setting ResidentialQuoteDetails, so quoteDetails remains null. On POST /api/customer/policies/{id}/bind, after ownership and QUOTED status checks, bindPolicy invokes validateResidentialBinding only when contents.getQuoteDetails() is non-null. The legacy policy therefore skips expiry, disclosure, address, occupancy, completeness, and eligibility checks, then is assigned ACTIVE status and a policy number. An authenticated customer can reach this path with only a positive contentsValue and a non-null startDate, so the candidate is exploitable.

#### Code evidence

```
createContentsQuote returns createLegacyContentsQuote when request.getAddress()==null. The legacy method requires only contentsValue and startDate, then calls the form overload, which leaves quoteDetails null. bindPolicy invokes validateResidentialBinding only when contents.getQuoteDetails()!=null and then sets status ACTIVE.
```

## 11. Managers can disburse unapproved claims by calling the endpoint directly

- Lead reference: FHZM-011
- Category: A01
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:139
- Fingerprint: e2cd461749cccd49eae6ac70d8e854ad5af9774d9de77f8ab381ab29dd541391

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 207,
  "symbol": "disburse",
  "input": "Manager-controlled claim id and validated payment form"
}
```

#### Controls encountered

```
[
  "MANAGER or ADMIN role required by controller method security and the web request matcher",
  "Bean validation requires a positive amount and syntactically valid payout fields",
  "PAID and REJECTED claims are rejected before transfer"
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 158,
  "symbol": "disburseClaim",
  "operation": "bankOfEdPaymentClient.transfer(...) sends an external funds-transfer request"
}
```

#### Counterevidence

```
[
  "The UI displays the disbursement control only for APPROVED or PAYMENT_FAILED, but this condition is not enforced in the controller or service."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "MANAGER or ADMIN selects an OPEN or UNDER_REVIEW claim and calls its disburse endpoint directly.",
    "Method-level role authorization succeeds.",
    "ClaimService does not require APPROVED or PAYMENT_FAILED and rejects only PAID and REJECTED.",
    "The service sends attacker-supplied payment details to the gateway.",
    "The claim is marked PAID after the transfer."
  ],
  "impact": "Unapproved claims can cause real payouts to a chosen destination.",
  "severity_reasoning": "High because direct endpoint use bypasses a required financial approval step.",
  "dynamic_test": "Use a stub gateway and submit a manager disbursement for an OPEN claim; confirm the transfer request and resulting PAID state without approval."
}
```

#### Validator reasoning

The endpoint is reachable by an authenticated MANAGER or ADMIN: ClaimController.disburse at /claims/{id}/disburse has @PreAuthorize("hasAnyRole('MANAGER', 'ADMIN')"), and SecurityConfig enables method security and applies the same request-role rule. After @Valid form checks, it loads the claim and calls ClaimService.disburseClaim. That method rejects only PAID and REJECTED, so OPEN and UNDER_REVIEW claims continue through normalization and invoke bankOfEdPaymentClient.transfer(...). A successful result sets the claim to PAID, records the receipt, and saves it. The Thymeleaf condition exposing the form only for APPROVED or PAYMENT_FAILED is presentation logic and does not guard the POST. No server-side allowlist or equivalent status check blocks the source-to-transfer path.

#### Code evidence

```
ClaimController.java:205-226 accepts a manager/admin POST and calls disburseClaim. ClaimService.java:139-145 rejects only PAID and REJECTED, then lines 158-160 call bankOfEdPaymentClient.transfer for every other state. claims/view.html shows the disburse control only for APPROVED or PAYMENT_FAILED claims, so that UI condition is not enforced server-side. docs/plan.md:99 describes approval before an approved status.
```

## 12. Claim funds can be disbursed before approval

- Lead reference: FHZM-012
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:134
- Fingerprint: 673e0c190b41981703d415c351ca8d146a75cfeb357ef035264619898e3c61e6

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 209,
  "symbol": "disburse",
  "input": "claim id and disbursement form"
}
```

#### Controls encountered

```
[
  "Spring method and URL security restrict disbursement to MANAGER or ADMIN.",
  "Bean validation checks amount, BSB, account number, payee name, and reference format/length.",
  "The service blocks already PAID and REJECTED claims."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 154,
  "symbol": "disburseClaim",
  "operation": "external bank transfer"
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
    "A manager, admin, or actor controlling such an account chooses a non-approved claim.",
    "The actor submits a disbursement request containing destination and amount.",
    "ClaimService permits all states except PAID and REJECTED.",
    "The service invokes the external payment sink and then writes PAID.",
    "Approval is skipped entirely."
  ],
  "impact": "The insurer can transfer funds for a claim that has not been approved.",
  "severity_reasoning": "High because a workflow authorization failure reaches an external financial transfer.",
  "dynamic_test": "With the payment client replaced by a recorder, disburse an UNDER_REVIEW claim and verify the gateway invocation occurs without an APPROVED transition."
}
```

#### Validator reasoning

The concrete path is POST /claims/{id}/disburse in ClaimController.disburse, which is reachable by MANAGER or ADMIN and passes the validated form to ClaimService.disburseClaim. The service only rejects PAID and REJECTED. It has no check for APPROVED, so an OPEN or UNDER_REVIEW claim reaches bankOfEdPaymentClient.transfer with the submitted amount and account details; on a successful response it sets the claim status to PAID and saves it. The view hides the disbursement form for non-approved states, but that is only UI behavior and does not protect the endpoint. Security configuration and method security enforce the role, not the claim state.

#### Code evidence

```
ClaimController.disburse accepts POST /claims/{id}/disburse for MANAGER or ADMIN and calls claimService.disburseClaim. disburseClaim checks only status==PAID and status==REJECTED before invoking bankOfEdPaymentClient.transfer(...). It never requires ClaimStatus.APPROVED.
```

## 13. Claim status endpoints do not enforce valid workflow transitions

- Lead reference: FHZM-013
- Category: A01
- Severity: MEDIUM
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:117
- Fingerprint: 9adfa69253294017ecb963e1bf10a59563ba93ac31fbe3147c08a433dabe358d

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 196,
  "symbol": "markPaid",
  "input": "Manager-controlled claim id"
}
```

#### Controls encountered

```
[
  "ClaimController methods require hasAnyRole('MANAGER', 'ADMIN') via @PreAuthorize.",
  "The web security filter chain also restricts the claim status POST paths to MANAGER or ADMIN.",
  "CSRF remains enabled for the web UI security chain."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 119,
  "symbol": "updateStatus",
  "operation": "claim.setStatus(newStatus) followed by claimRepository.save(claim)"
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
    "MANAGER or ADMIN sends a direct POST to a fixed status endpoint.",
    "The endpoint role check passes regardless of the claim's source state.",
    "UI visibility conditions are not evaluated for the direct request.",
    "ClaimService.updateStatus blindly saves the requested fixed status.",
    "Invalid claim and payment lifecycle state is persisted."
  ],
  "impact": "Claim records can falsely indicate payment or be moved backward after payment.",
  "severity_reasoning": "Medium because privileged access is required, but server-side lifecycle integrity is absent.",
  "dynamic_test": "As manager, mark an OPEN claim PAID and then move a PAID claim to APPROVED or REJECTED; verify the stored transitions."
}
```

#### Validator reasoning

The source-to-sink path is concrete: an authenticated MANAGER or ADMIN can POST /claims/{id}/paid, and ClaimController.markPaid at ClaimController.java:196-201 calls ClaimService.updateStatus(id, ClaimStatus.PAID, null, user). ClaimService.updateStatus at ClaimService.java:117-125 loads the claim, assigns the requested status, and saves it without inspecting the prior status or enforcing a transition table. The same unguarded service is used by review, approve, and reject. Therefore a manager can set an OPEN claim to PAID, or move a PAID claim back to APPROVED or REJECTED, by sending direct POST requests. The template conditions only control whether buttons are rendered and do not protect the routes. Role authorization and CSRF prevent unauthenticated or cross-site requests, but neither blocks a legitimate privileged request with an invalid current-state transition.

#### Code evidence

```
ClaimController.java:144-203 exposes the review, approve, reject, and paid POST routes and each calls updateStatus. ClaimService.java:117-125 loads the claim and unconditionally sets newStatus; it never checks claim.getStatus(). claims/view.html conditionally displays controls based on current status, showing that transition restrictions exist only in presentation logic.
```

## 14. Concurrent disbursement requests can pay the same claim more than once

- Lead reference: FHZM-014
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:134
- Fingerprint: b62c5747ffe1196af30fc152d5103ffa8afd36d7320e68501a9aa69eb3db3cdb

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 209,
  "symbol": "disburse",
  "input": "two concurrent POST requests for the same claim id"
}
```

#### Controls encountered

```
[
  "ClaimController restricts the endpoint to MANAGER or ADMIN, but this does not serialize two authorized requests.",
  "Bean validation constrains payment fields, but does not prevent duplicate submission.",
  "@Transactional provides a transaction boundary only; the default repository findById path has no row lock or compare-and-set, and the external HTTP transfer cannot be rolled back."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 154,
  "symbol": "disburseClaim",
  "operation": "duplicate external bank transfers before status update"
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
    "Two authorized manager/admin clients target the same non-PAID claim.",
    "They submit disbursement requests concurrently.",
    "Separate transactions both read the same eligible status because no lock, version check, or atomic reservation exists.",
    "Both calls reach the external payment gateway before either stores PAID.",
    "Both transactions issue a payout for one claim."
  ],
  "impact": "Duplicate real-world payouts can debit the insurer twice for one claim.",
  "severity_reasoning": "High because a practical concurrency race reaches an irreversible external payment sink without idempotency.",
  "dynamic_test": "Use a barrier-enabled stub gateway to hold two concurrent disbursements for one APPROVED test claim; release both and verify whether two transfer calls were recorded."
}
```

#### Validator reasoning

Confirmed. ClaimController.disburse exposes POST /claims/{id}/disburse to authorized staff and directly calls ClaimService.disburseClaim. The service uses claimRepository.findById, checks only the in-memory status, performs bankOfEdPaymentClient.transfer over HTTP, and saves PAID only after a successful response. Claim has no @Version field, ClaimRepository has no locking query, and no idempotency key or in-progress status is used. With two concurrent transactions starting while the claim is non-PAID, both reads can pass the check and both external transfers can complete before either PAID update commits. The transaction cannot undo either already completed bank transfer.

#### Code evidence

```
The @Transactional method loads the claim with repository.findById, checks PAID/REJECTED, calls bankOfEdPaymentClient.transfer, and only on success sets PAID and saves. Claim has no observed @Version field and the repository lookup is not a pessimistic-lock query. The external transfer occurs before the persisted terminal state.
```

## 15. Default SSO signing secret enables customer account takeover

- Lead reference: FHZM-015
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/security/SsoTokenValidator.java:20
- Fingerprint: ee0b9c3a46121860e7a765ae0af50af86ad7fffc2c0f804080d14509f63856af

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 64,
  "symbol": "authenticateSso",
  "input": "Unauthenticated attacker-supplied SSO JWT"
}
```

#### Controls encountered

```
[
  "Spring Security permits unauthenticated POST /api/customer/auth/sso",
  "JJWT verifies the HMAC signature and automatically checks registered time claims such as exp",
  "Issuer must equal the configured BankOfEd value",
  "The subject must be nonblank and must match an existing customer email"
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 79,
  "symbol": "authenticateSso",
  "operation": "jwtTokenProvider.generateToken(customer.getEmail())"
}
```

#### Counterevidence

```
[
  "The validator does enforce signature, issuer, nonblank subject, and parsed JWT time claims, so malformed, expired, wrong-issuer, or wrongly signed tokens are rejected.",
  "A non-existent customer email is rejected before an application JWT is issued."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated actor obtains the default SSO HMAC secret and a customer email.",
    "The actor signs an SSO JWT with issuer BankOfEd and the victim email as subject.",
    "The public /api/customer/auth/sso endpoint passes the token to SsoTokenValidator.",
    "Default-secret signature, issuer, and subject checks pass.",
    "The controller exchanges it for a normal customer JWT used to access victim data and actions."
  ],
  "impact": "Unauthenticated customer account takeover.",
  "severity_reasoning": "High because the public default secret enables remote token forgery and full customer impersonation.",
  "dynamic_test": "Start the supported deployment without APP_SSO_JWT_SECRET, forge a short-lived SSO token for a seeded customer, exchange it, and verify the returned JWT accesses that customer's profile."
}
```

#### Validator reasoning

Confirmed. In the supplied deployment, application.properties resolves app.sso.jwt-secret from APP_SSO_JWT_SECRET with the repository-known fallback bankofed-goosecable-sso-shared-secret-key-32b. docker-compose.yml passes APP_JWT_SECRET but does not pass APP_SSO_JWT_SECRET, and docker-entrypoint.sh generates only APP_JWT_SECRET. Therefore the fallback SSO key is active unless an operator adds an external override outside the supplied deployment. SecurityConfig permits POST /api/customer/auth/sso without authentication. authenticateSso passes the attacker-controlled token to SsoTokenValidator, which verifies it with that known key, checks issuer and nonblank subject, then CustomerService.findByEmail(subject) and jwtTokenProvider.generateToken(customer.getEmail()) issue a normal customer JWT. The existing-email check is lookup, not authorization, and does not prevent impersonation of a known customer email. The source-to-sink path is concrete and has no effective blocking control.

#### Code evidence

```
SecurityConfig.java:47-52 permits POST /api/customer/auth/sso. SsoTokenValidator.java:20-23 defaults to bankofed-goosecable-sso-shared-secret-key-32b and validates only signature, issuer, and nonblank subject. CustomerApiController.java:63-80 resolves the subject email and issues an application JWT. application.properties:25 retains the same default. docker-compose.yml does not set APP_SSO_JWT_SECRET, and docker-entrypoint.sh only generates APP_JWT_SECRET.
```

## 16. Any staff account can reset any customer's portal password

- Lead reference: FHZM-016
- Category: A01
- Severity: HIGH
- Confidence: 0%
- Validation: pending
- Reportable: No
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerController.java:74
- Fingerprint: 55746fc5bebf37cc890015facdd7e1252396b88a2d8f805e5a5e683801160fbe

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerController.java",
  "line": 74,
  "symbol": "setPassword",
  "input": "path customer id and attacker-selected newPassword"
}
```

#### Controls encountered

```
[
  "Authentication and CSRF protection apply, but any authenticated low-privilege staff account is authorized and no current-password or customer confirmation is required."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/CustomerService.java",
  "line": 0,
  "symbol": "setPassword",
  "operation": "overwrites customer password hash"
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
SecurityConfig protects /admin/** and claim state routes by role but leaves /customers/** under anyRequest().authenticated(). CustomerController.setPassword POST /customers/{id}/set-password has no @PreAuthorize and directly calls customerService.setPassword(id,newPassword). UserRole includes CONTACT_CENTRE, and CustomerApiController.authenticate accepts the replaced password.
```

## 17. Concurrent disbursement requests can pay the same claim twice

- Lead reference: FHZM-017
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:134
- Fingerprint: 26f3985a3725c49a1d45d2134a4a7d7b5a2e280be099cf89f468ac087b184263

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 205,
  "symbol": "disburse",
  "input": "concurrent authenticated POST requests for the same claim id"
}
```

#### Controls encountered

```
[
  "ClaimController.disburse is protected by @PreAuthorize for MANAGER or ADMIN, but two authorized requests can run concurrently.",
  "ClaimDisbursementForm validates amount, BSB, account number, payee name, and reference format/length, but does not serialize or deduplicate requests.",
  "The service rejects PAID and REJECTED claims only from each transaction's initial in-memory snapshot."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 155,
  "symbol": "disburseClaim",
  "operation": "external funds transfer before a concurrency-safe state transition"
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
    "Two manager/admin sessions submit disbursements for the same claim at nearly the same time.",
    "Both transactions read a non-PAID status with no row lock or optimistic version.",
    "Each request independently calls the external payment gateway.",
    "Only after the external calls do the transactions save PAID.",
    "The same claim is paid twice."
  ],
  "impact": "Duplicate payouts and direct financial loss.",
  "severity_reasoning": "High because the check-then-transfer race crosses the database transaction boundary and reaches an external payment system.",
  "dynamic_test": "Coordinate two concurrent requests against one APPROVED claim with a delayed stub gateway and assert whether two outbound transfers occur."
}
```

#### Validator reasoning

The source-to-sink path is concrete: POST /claims/{id}/disburse passes the controller role check, invokes ClaimService.disburseClaim, loads the claim through ClaimRepository.findById, checks PAID/REJECTED, and calls BankOfEdPaymentClient.transfer before any PAID state is saved. Claim has no @Version field, ClaimRepository has no locking query, and the payment client sends only ordinary transfer fields with no idempotency key. The external transfer therefore occurs while the transaction still holds the old claim state. Two concurrent authorized transactions can both read APPROVED or another non-terminal status, both call the gateway, and only afterward save PAID. The later database saves do not undo either transfer.

#### Code evidence

```
ClaimController.java:205-224 allows MANAGER/ADMIN to call disburseClaim. ClaimService.java:134-174 checks status in memory, calls bankOfEdPaymentClient.transfer(...) at lines 155-157, then sets PAID and saves. Claim.java has no optimistic-lock @Version field.
```

## 18. Hard-coded JWT signing key allows customer account impersonation

- Lead reference: FHZM-018
- Category: A07
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/resources/application.properties:20
- Fingerprint: 164305366082e3e46c5d311b07634636b8ce2184002aafdc77a6c53e02a25fdf

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/resources/application.properties",
  "line": 20,
  "symbol": "app.jwt.secret",
  "input": "public fixed signing secret"
}
```

#### Controls encountered

```
[
  "JwtTokenProvider verifies the HMAC signature and expiration before authentication.",
  "SecurityConfig requires authentication for every /api/customer/** endpoint.",
  "The Docker entrypoint generates and persists a random APP_JWT_SECRET when Docker deployment does not supply one.",
  "Deployment documentation instructs non-Docker operators to override app.jwt.secret."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/security/JwtAuthenticationFilter.java",
  "line": 37,
  "symbol": "doFilterInternal",
  "operation": "accept forged JWT as ROLE_CUSTOMER"
}
```

#### Counterevidence

```
[
  "The default application.properties value is still loaded when the JAR is run without an external override; there is no fail-fast check or profile restriction.",
  "The Docker and deployment safeguards do not protect direct JAR execution or misconfigured deployments."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Remote actor learns the hard-coded customer JWT signing key and a target email.",
    "The actor creates an HMAC JWT whose subject is the target customer.",
    "JwtAuthenticationFilter accepts it and installs ROLE_CUSTOMER.",
    "CustomerApiController resolves the principal subject to the victim record.",
    "Victim profile, policies, claims, uploads, quotes, and binds become accessible."
  ],
  "impact": "Customer account impersonation and unauthorized data access or state changes.",
  "severity_reasoning": "High because possession of public source material is enough to bypass customer authentication.",
  "dynamic_test": "Forge a test JWT with the committed key for a seeded customer's email and confirm a protected customer endpoint returns that customer's record."
}
```

#### Validator reasoning

Confirmed. application.properties:25 commits a valid, fixed Base64 HMAC key. JwtTokenProvider constructs the signing key directly from app.jwt.secret and accepts any non-expired token whose signature verifies with that key. JwtAuthenticationFilter:31-42 then creates an authenticated principal with ROLE_CUSTOMER and the token subject as its email. SecurityConfig:46-61 applies this filter to /api/customer/** and only requires authenticated(), so a forged token reaches the controller. CustomerApiController:314-324 resolves non-machine callers with customerService.findByEmail(auth.getName()), and /api/customer/profile:85-90 returns that customer's profile. DataInitializer seeds concrete customer emails, so an attacker who knows the committed key can forge a token with a seeded subject and access an existing account. Docker's generated-secret path is a deployment-specific mitigation, but the insecure committed value remains an accepted runtime default for direct JAR execution and is not rejected.

#### Code evidence

```
application.properties sets app.jwt.secret=bXktdW5pcXVlLWFuZC12ZXJ5LXNlY3JldC1rZXktZm9yLWp3dC10b2tlbnM=. JwtTokenProvider.java constructs an HMAC key from that value and validates signed claims. JwtAuthenticationFilter.java assigns ROLE_CUSTOMER and the token subject as principal after signature validation. CustomerApiController.java:318-329 resolves non-machine callers with customerService.findByEmail(auth.getName()).
```

## 19. Claims can be disbursed before approval

- Lead reference: FHZM-019
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:134
- Fingerprint: 34db422fc35dbd5de44852f633e9962b536ea0bd3d211317aec43509024179b7

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 205,
  "symbol": "disburse",
  "input": "settledAmount and payout bank details"
}
```

#### Controls encountered

```
[
  "ClaimController.disburse is protected by @PreAuthorize for MANAGER or ADMIN, but that is privilege authorization rather than an approval-state check.",
  "ClaimDisbursementForm bean validation requires a positive amount and valid nonblank payout fields.",
  "ClaimService.disburseClaim rejects only PAID and REJECTED before calling BankOfEdPaymentClient.transfer."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 155,
  "symbol": "disburseClaim",
  "operation": "external bank transfer"
}
```

#### Counterevidence

```
[
  "claims/view.html only renders the disbursement button for APPROVED or PAYMENT_FAILED, but this is a UI condition and the POST endpoint accepts direct requests.",
  "PAYMENT_FAILED retry behavior may be intentional, but the same service logic also permits OPEN and UNDER_REVIEW claims."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "MANAGER or ADMIN targets a claim in OPEN, UNDER_REVIEW, or PAYMENT_FAILED state.",
    "The actor submits destination bank details and amount to the disbursement endpoint.",
    "Role authorization passes, while ClaimService omits an APPROVED-state requirement.",
    "BankOfEdPaymentClient sends the transfer.",
    "ClaimService records PAID after the unapproved payout."
  ],
  "impact": "Funds can be diverted or paid without an approved settlement.",
  "severity_reasoning": "High because a privileged but non-approval-compliant request reaches a financial transfer sink.",
  "dynamic_test": "With a stub gateway, disburse an OPEN claim using test bank details and confirm an outbound transfer is generated before approval."
}
```

#### Validator reasoning

Confirmed. A manager or admin can POST a valid ClaimDisbursementForm directly to ClaimController.disburse for a claim whose persisted status is OPEN or UNDER_REVIEW. The controller performs validation and calls ClaimService.disburseClaim. That method checks only PAID and REJECTED, copies the request-controlled amount and payout details, and unconditionally invokes bankOfEdPaymentClient.transfer. On a successful bank response it marks the claim PAID and saves it. No service, controller, security, entity, or framework control requires ClaimStatus.APPROVED. The template restriction is bypassable and does not block the source-to-sink path.

#### Code evidence

```
ClaimController.java:205-224 accepts a validated ClaimDisbursementForm from MANAGER/ADMIN and passes it to disburseClaim. ClaimService.java:136-143 rejects only PAID and REJECTED, then lines 145-157 take the request amount/account and invoke bankOfEdPaymentClient.transfer. ClaimStatus includes APPROVED, but the service never requires it.
```

## 20. Default SSO signing secret allows forged SSO login

- Lead reference: FHZM-020
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/resources/application.properties:24
- Fingerprint: 9f92e348e0c90b03d783294de0794b9a517b7efd0e6f891ebba1d5aa66c001fb

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/api/SsoAuthRequest.java",
  "line": 14,
  "symbol": "token",
  "input": "attacker-supplied SSO JWT"
}
```

#### Controls encountered

```
[
  "SsoAuthRequest applies @NotBlank to the token field.",
  "SsoTokenValidator verifies the JWT signature with the configured HMAC key, checks the configured issuer, and rejects expired tokens through JJWT parsing.",
  "CustomerApiController requires the subject email to resolve to an existing Customer before issuing a local JWT.",
  "POST /api/customer/auth/sso is explicitly permitted without prior authentication."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 78,
  "symbol": "authenticateSso",
  "operation": "issue local customer JWT"
}
```

#### Counterevidence

```
[
  "An operator can override APP_SSO_JWT_SECRET, but no source or deployment configuration requires that override.",
  "The Docker Compose environment and deployment documentation do not set or require APP_SSO_JWT_SECRET, so the committed fallback is reachable in documented deployments."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated actor uses the committed SSO secret and a known customer email.",
    "The actor signs a BankOfEd issuer token for that subject.",
    "The public SSO endpoint validates it under the unchanged default.",
    "The endpoint issues a normal customer bearer token.",
    "The bearer token authorizes victim account reads and actions."
  ],
  "impact": "Remote customer account takeover.",
  "severity_reasoning": "High because a public shared secret defeats the SSO trust boundary in the default configuration.",
  "dynamic_test": "Leave APP_SSO_JWT_SECRET unset, exchange a forged test SSO token for a seeded customer, and verify the issued bearer token resolves to that account."
}
```

#### Validator reasoning

Confirmed. When APP_SSO_JWT_SECRET is absent, application.properties resolves app.sso.jwt-secret to the committed 45-byte ASCII value bankofed-goosecable-sso-shared-secret-key-32b. SsoTokenValidator constructs its HMAC SecretKey directly from that value and accepts any attacker-created JWT with a valid signature under that key, issuer BankOfEd, a nonblank subject, and a future expiration. SecurityConfig permits unauthenticated POST /api/customer/auth/sso. CustomerApiController passes the extracted subject to CustomerService.findByEmail and then calls JwtTokenProvider.generateToken(customer.getEmail()), producing the normal customer bearer token. JwtAuthenticationFilter accepts that token and assigns ROLE_CUSTOMER, and DataInitializer seeds real customer accounts such as amelia.chen@example.com. The existing-customer check limits targets to known customers but does not prevent account takeover because those email addresses are obtainable or guessable and the signing key is public in the source.

#### Code evidence

```
application.properties defines app.sso.jwt-secret=${APP_SSO_JWT_SECRET:bankofed-goosecable-sso-shared-secret-key-32b}. SsoTokenValidator.java uses that string directly as an HMAC key, checks only signature, issuer, and nonblank subject, and returns the subject email. CustomerApiController.java:64-80 looks up the customer and issues a local JWT. SecurityConfig.java permits unauthenticated POST requests to /api/customer/auth/sso.
```

## 21. Payment gateway uses a published default bearer token

- Lead reference: FHZM-021
- Category: A02
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/BankOfEdPaymentClient.java:32
- Fingerprint: 4291ac35c3bf8b6a121929142033e87114e73d9b12497e1be324412803ded6b8

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/resources/application.properties",
  "line": 31,
  "symbol": "app.bankofed.machine-token",
  "input": "repository-known default credential"
}
```

#### Controls encountered

```
[
  "The web disbursement route requires MANAGER or ADMIN authentication via Spring Security and @PreAuthorize.",
  "BANKOFED_MACHINE_TOKEN can override the fallback, but docker-compose.yml does not set it and the committed application.properties fallback remains active.",
  "The application sends the token only on its outbound gateway request; the web-route authorization does not protect direct use of the gateway credential."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/BankOfEdPaymentClient.java",
  "line": 80,
  "symbol": "transfer",
  "operation": "Authorization bearer credential sent to payment gateway"
}
```

#### Counterevidence

```
[
  "The repository does not include the Bank of Ed gateway implementation, so its network exposure and server-side token validation are external to this review."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "External actor learns the published default payment bearer token from source or artifact.",
    "The supported deployment leaves BANKOFED_MACHINE_TOKEN unset and the client uses the fallback token.",
    "The actor reaches the payment gateway network endpoint directly.",
    "The gateway accepts the known bearer credential.",
    "Unauthorized transfer attempts reach the payment operation."
  ],
  "impact": "Unauthorized access to the payment API can enable fraudulent transfers.",
  "severity_reasoning": "High because a repository-known machine credential protects a financial service and is active in the documented deployment.",
  "dynamic_test": "In an isolated gateway test environment using the documented default, send a harmless validation or zero-effect test request with the published bearer token and verify whether authentication succeeds."
}
```

#### Validator reasoning

Confirmed. BankOfEdPaymentClient injects the repository-known literal when app.bankofed.machine-token is unset, and the documented compose deployment does not provide BANKOFED_MACHINE_TOKEN. transfer() then constructs an outbound POST to /api/payments/transfer with Authorization: Bearer <machineToken>. The only visible access control protects GooseCable's /claims/{id}/disburse route for managers/admins; it does not rotate, reject, or otherwise constrain the credential at the gateway. The missing gateway implementation limits verification of its deployment, but does not break the concrete source-to-sink path or show an effective blocking control.

#### Code evidence

```
BankOfEdPaymentClient.java:32 injects ${app.bankofed.machine-token:mch_face_insurance_secret_key_2026} and line 80 sends it as a Bearer token. application.properties sets BANKOFED_MACHINE_TOKEN to the same fallback. docker-compose.yml configures database and JWT environment values but no BANKOFED_MACHINE_TOKEN.
```

## 22. Default SSO signing secret allows forged customer tokens

- Lead reference: FHZM-022
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/security/SsoTokenValidator.java:20
- Fingerprint: 1a27fdc677f8f8433907c32aca6c6adfacc6c62884673c18289bc5e0a936ada8

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 64,
  "symbol": "authenticateSso",
  "input": "request.token"
}
```

#### Controls encountered

```
[
  "The endpoint is explicitly permitted without authentication in SecurityConfig.",
  "SsoAuthRequest requires a nonblank token.",
  "The validator checks HMAC signature, issuer, and nonblank subject, but those checks are satisfiable with the fallback secret."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/security/SsoTokenValidator.java",
  "line": 34,
  "symbol": "validateAndExtractEmail",
  "operation": "parseSignedClaims using default HMAC key"
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
    "Unauthenticated actor obtains the default SSO secret and chooses an existing customer email.",
    "The actor creates a signed JWT with issuer BankOfEd and the victim email as subject.",
    "SsoTokenValidator accepts the attacker-supplied token when the environment override is absent.",
    "The controller returns a regular customer JWT.",
    "The actor uses it as the victim."
  ],
  "impact": "Unauthenticated account takeover and customer data access.",
  "severity_reasoning": "High because a public default signing secret provides a direct remote authentication bypass.",
  "dynamic_test": "Run without the SSO secret override, forge and exchange a token for a test customer, then call the profile endpoint with the returned JWT."
}
```

#### Validator reasoning

Confirmed. When APP_SSO_JWT_SECRET is unset, application.properties resolves app.sso.jwt-secret to the literal repository-known value bankofed-goosecable-sso-shared-secret-key-32b, matching the fallback in SsoTokenValidator's @Value. POST /api/customer/auth/sso is permitAll and passes the attacker-controlled request token to validateAndExtractEmail(). A token signed with that secret, carrying issuer BankOfEd and a future or omitted expiration plus an existing customer email as subject, passes validation. CustomerApiController then calls customerService.findByEmail(email) and issues jwtTokenProvider.generateToken(customer.getEmail()), producing a normal customer bearer token for the selected account. No SSO-provider binding, customer password check, or startup failure blocks this path.

#### Code evidence

```
CustomerApiController.java:64-78 passes request.getToken() to validateAndExtractEmail(), looks up the returned subject as a customer email, and generates an application token. SsoTokenValidator.java:20-38 constructs the verification key from @Value("${app.sso.jwt-secret:bankofed-goosecable-sso-shared-secret-key-32b}") and checks only signature, issuer, and nonblank subject. application.properties:29 repeats the same known fallback.
```

## 23. Payment requests and bearer credentials are sent over cleartext HTTP

- Lead reference: FHZM-023
- Category: A02
- Severity: HIGH
- Confidence: 95%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/BankOfEdPaymentClient.java:75
- Fingerprint: bd3c84dbb3132ccf8297421cb54334b0d9f8326075871a52d44f4a99e5b190fc

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 205,
  "symbol": "disburse",
  "input": "bank account, payee, amount, and reference"
}
```

#### Controls encountered

```
[
  "The disbursement route requires an authenticated MANAGER or ADMIN through Spring Security.",
  "ClaimDisbursementForm validates the amount, BSB, account number, payee name, and reference length.",
  "The base URL is configurable and could be set to an HTTPS endpoint in a deployment."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/BankOfEdPaymentClient.java",
  "line": 75,
  "symbol": "transfer",
  "operation": "cleartext HTTP request with bearer token and payment data"
}
```

#### Counterevidence

```
[
  "The default local and container fallback destinations are loopback or host.docker.internal, which can reduce exposure in an isolated deployment.",
  "The repository does not show the runtime payment-gateway deployment or its network controls."
]
```

#### Proof gaps

```
[
  "Whether a deployed environment permits a network attacker to observe or alter the app-to-gateway path is deployment-specific.",
  "The repository does not establish that production overrides BANKOFED_API_BASE to HTTPS."
]
```

#### Attack path

```
{
  "nodes": [
    "A network-positioned actor gains visibility or modification capability on the application-to-payment-gateway path.",
    "BankOfEdPaymentClient sends requests to an HTTP URL.",
    "The request carries the bearer token and full transfer details without transport encryption.",
    "The actor observes or alters the credential, destination, amount, payee, or reference before the gateway receives it.",
    "The exposed token can also be replayed against the gateway."
  ],
  "impact": "Credential theft, sensitive payment-data disclosure, and possible transfer tampering.",
  "severity_reasoning": "High because cleartext transport exposes a reusable payment credential and financial transaction data to a network attacker.",
  "dynamic_test": "Route the application through a controlled HTTP capture proxy in a test environment, perform a stub disbursement, and confirm the Authorization header and payment fields are visible in plaintext."
}
```

#### Validator reasoning

The source-to-sink path is concrete. ClaimController.disburse accepts the validated payment fields and calls ClaimService.disburseClaim; ClaimService passes the BSB, account number, payee, amount, and reference to BankOfEdPaymentClient.transfer. That client constructs the default endpoint as http://localhost:8081/api/payments/transfer and also adds HTTP fallbacks for host.docker.internal, 127.0.0.1, and localhost. It then builds an HttpRequest with the JSON payment payload and an Authorization header containing the bearer machine token and sends it with HttpClient. There is no TLS requirement, HTTPS upgrade, scheme allowlist, certificate configuration, or rejection of HTTP. Authorization and input validation protect who can initiate a transfer and what values are submitted, but do not protect the outbound transport. The configurable base URL is a deployment option, not an effective blocking control because the shipped defaults and fallback paths remain cleartext HTTP.

#### Code evidence

```
BankOfEdPaymentClient.java:28 defaults baseUrl to http://localhost:8081; lines 75-83 send JSON and Authorization over that URI; lines 125-135 add only http:// host.docker.internal, 127.0.0.1, and localhost fallbacks. application.properties also defaults BANKOFED_API_BASE to http://localhost:8081.
```

## 24. Hard-coded default SSO signing secret allows customer impersonation

- Lead reference: FHZM-024
- Category: A02
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/security/SsoTokenValidator.java:21
- Fingerprint: a62e42cff1fc1399efa406d41e3870d50eb26a095f6cf395e9bb7ec1927fb7c9

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 64,
  "symbol": "authenticateSso",
  "input": "request.token containing attacker-signed JWT"
}
```

#### Controls encountered

```
[
  "SsoAuthRequest requires a nonblank token, but does not authenticate its signer",
  "SsoTokenValidator verifies the JWT HMAC with the configured secret and checks issuer BankOfEd plus a nonblank subject",
  "CustomerApiController catches unknown subjects and only exchanges subjects matching an existing customer",
  "SecurityConfig permits POST /api/customer/auth/sso, disables CSRF for the customer API, and does not require prior authentication"
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 77,
  "symbol": "authenticateSso",
  "operation": "issues customer JWT for forged SSO subject"
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
    "Unauthenticated actor knows the default SSO secret and guesses or learns a customer email.",
    "The actor signs an HS256 token with BankOfEd issuer and that email subject.",
    "The public SSO endpoint accepts the signature and claims under the default configuration.",
    "CustomerApiController exchanges it for an application customer JWT.",
    "The actor accesses or changes the victim's policies and claims."
  ],
  "impact": "Customer impersonation and unauthorized insurance data access or changes.",
  "severity_reasoning": "High because no prior account access is needed and the public default secret defeats SSO authentication.",
  "dynamic_test": "Forge a short-lived SSO token for a seeded test customer under the default secret, exchange it, and verify victim-scoped access with the returned JWT."
}
```

#### Validator reasoning

The path is directly reachable. SecurityConfig permits unauthenticated POST /api/customer/auth/sso. application.properties defines app.sso.jwt-secret with APP_SSO_JWT_SECRET falling back to the public literal bankofed-goosecable-sso-shared-secret-key-32b, and docker-compose does not set APP_SSO_JWT_SECRET. SsoTokenValidator constructs the HMAC key from that value and accepts any successfully signed JWT whose issuer equals BankOfEd and whose subject is nonblank; it does not require an external issuer, audience, nonce, or other trusted assertion. CustomerApiController passes the request token to the validator, looks up the returned subject as an email, and calls jwtTokenProvider.generateToken(customer.getEmail()) before returning the application JWT. An attacker can therefore sign an HS256 token with the fallback secret, use an existing customer's email as subject, and obtain that customer's normal JWT. The customer JWT filter then authenticates that token as ROLE_CUSTOMER for subsequent customer API access. No effective blocking control was found.

#### Code evidence

```
CustomerApiController.java:64-79 passes request.token to validateAndExtractEmail(), looks up the returned subject as a customer email, and calls jwtTokenProvider.generateToken(). SsoTokenValidator.java:21 uses @Value("${app.sso.jwt-secret:bankofed-goosecable-sso-shared-secret-key-32b}") and lines 38-58 accept a signed token with issuer BankOfEd and a nonblank subject. application.properties:29 repeats APP_SSO_JWT_SECRET with the same default.
```

## 25. Customer password authentication has no brute-force protection

- Lead reference: FHZM-025
- Category: A07
- Severity: MEDIUM
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java:46
- Fingerprint: 450956829abfb0f969a4a6be53943de568c9340eccf7b632931416902860fa5f

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 46,
  "symbol": "authenticate",
  "input": "attacker-controlled email and password"
}
```

#### Controls encountered

```
[
  "AuthRequest @Valid checks only email/password presence and email syntax",
  "BCrypt-style PasswordEncoder comparison raises per-request cost but does not cap attempts",
  "Generic 401 Invalid credentials response does not throttle or lock out",
  "No application rate-limit, attempt-counter, delay, lockout, or 429 control is present",
  "The API SecurityFilterChain explicitly permits POST /api/customer/auth"
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 59,
  "symbol": "authenticate",
  "operation": "issues bearer JWT after unlimited password checks"
}
```

#### Counterevidence

```
[
  "No source-level reverse proxy or gateway configuration was found that would impose a rate limit",
  "The endpoint is directly exposed by the provided Docker configuration on port 8080"
]
```

#### Proof gaps

```
[
  "An external deployment could add an unreviewed upstream rate limiter, so source-only review cannot exclude infrastructure controls",
  "Account takeover still depends on a customer using a guessable or reused password"
]
```

#### Attack path

```
{
  "nodes": [
    "Unauthenticated remote actor repeatedly calls POST /api/customer/auth with chosen email/password pairs.",
    "The public endpoint performs a password check for every request.",
    "No source/IP/account rate limit, delay, lockout, or attempt counter intervenes.",
    "A correct guess returns a bearer JWT.",
    "The actor uses the JWT to access the customer account."
  ],
  "impact": "Password guessing and credential stuffing can lead to customer account compromise.",
  "severity_reasoning": "Medium because exploitation depends on obtaining or guessing a password, but the endpoint provides no automated-attack resistance.",
  "dynamic_test": "Against a disposable test account, send a controlled burst of failed logins followed by the correct password and measure whether all attempts are processed immediately and the final login still succeeds."
}
```

#### Validator reasoning

The path is concrete: an unauthenticated POST /api/customer/auth reaches CustomerApiController.authenticate; attacker-controlled email is used in customerService.findByEmail and the supplied password is checked with passwordEncoder.matches. A wrong password returns 401, while a correct one immediately calls jwtTokenProvider.generateToken and returns the bearer token. SecurityConfig permits this route and the JWT filter only parses an existing Authorization header; it does not limit authentication attempts. @Valid provides input-shape validation only. The reviewed service, repository, dependencies, filters, and deployment files contain no per-account or per-source counters, delays, lockouts, throttling, or rate limiting. The candidate is therefore confirmed as an application-level brute-force and credential-stuffing control weakness, subject only to possible controls outside the source archive.

#### Code evidence

```
SecurityConfig.java:50 permits POST /api/customer/auth. CustomerApiController.java:46-60 immediately calls findByEmail and passwordEncoder.matches and issues jwtTokenProvider.generateToken on success. A repository search under src/main for rate-limit, throttling, attempt tracking, lockout, or HTTP 429 controls returned no matches.
```

## 26. Claim submission accepts incidents outside the policy coverage period

- Lead reference: FHZM-026
- Category: A04
- Severity: MEDIUM
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:66
- Fingerprint: 86b21ed90b20b27087b1357f7e9edac01aa0b704e1a6888202a5b55c162bb03b

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 139,
  "symbol": "submitClaim",
  "input": "request.incidentDate and request.policyId"
}
```

#### Controls encountered

```
[
  "Customer API requests require authentication",
  "CustomerApiController resolves the authenticated customer and enforces policy ownership",
  "ClaimService requires the selected policy status to be ACTIVE",
  "Motor claims receive required-field validation",
  "Manager/admin review and disbursement endpoints provide a manual approval step"
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 76,
  "symbol": "createClaim",
  "operation": "persists an OPEN claim with unchecked incident date"
}
```

#### Counterevidence

```
[
  "Authentication and ownership checks only constrain which policy can be used; they do not validate incidentDate",
  "SubmitClaimRequest has only @NotNull on incidentDate, with no past, policy-start, or policy-end constraint",
  "ClaimService.createClaim checks only PolicyStatus.ACTIVE and copies the supplied date into a persisted OPEN Claim",
  "The approval and disbursement paths do not recheck incidentDate against policy dates, so manual review is not an effective technical blocking control",
  "Policy bindPolicy sets a quote to ACTIVE without making ACTIVE depend on the policy date range; seeded active policies also carry ordinary start and end dates"
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated customer submits a claim for a policy they own.",
    "The actor supplies an incidentDate before coverage, after coverage, or in the future.",
    "Ownership and ACTIVE-status checks pass.",
    "No coverage-window validation rejects the date.",
    "The OPEN claim is stored and enters review and payment processing."
  ],
  "impact": "Out-of-cover or future losses can be presented as valid claims.",
  "severity_reasoning": "Medium because authentication and policy ownership are enforced, but the central claim eligibility rule is missing.",
  "dynamic_test": "For one owned active policy, submit test claims with dates just before startDate, just after endDate, and tomorrow; verify which are persisted."
}
```

#### Validator reasoning

Confirmed. An authenticated customer can POST /api/customer/claims with an owned ACTIVE policy and a non-null incidentDate outside that policy's coverage period or in the future. CustomerApiController.submitClaim loads the policy, checks ownership, and copies request.incidentDate into ClaimForm before calling ClaimService.createClaim. ClaimService only rejects non-ACTIVE policies, then assigns form.getIncidentDate() directly to a new Claim whose status is OPEN and saves it. SubmitClaimRequest provides no date-range or current-date validation, and ClaimService has no such check. The later manager/admin review and disbursement methods can process the claim without a date recheck, so they reduce payment risk but do not prevent creation of the invalid OPEN claim or guarantee rejection.

#### Code evidence

```
SubmitClaimRequest.java:20 marks incidentDate only @NotNull. CustomerApiController.java:139-148 resolves the customer, loads the policy, and checks ownership, but does not compare incidentDate with the current date or policy dates. ClaimService.java:66-79 checks policy.status == ACTIVE and copies form.incidentDate directly into a new OPEN claim.
```

## 27. Legacy motor quote fields bypass binding and premium controls

- Lead reference: FHZM-027
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:113
- Fingerprint: d0908c555b900409bc732313b736aaf2d6bf77d501ed508c83f0117243dc15c0

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 220,
  "symbol": "requestMotorQuote",
  "input": "legacy flat quote fields with vehicle omitted and estimatedValue=0.01"
}
```

#### Controls encountered

```
[
  "Customer API security chain requires authentication for /api/customer/**.",
  "resolveCustomer binds normal customer JWTs to the authenticated email; machine tokens require X-Customer-Id.",
  "bindPolicy checks QUOTED status.",
  "CustomerApiController.assertOwns prevents binding another customer's policy."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 566,
  "symbol": "bindPolicy",
  "operation": "sets bypass-created quote ACTIVE without structured checks"
}
```

#### Counterevidence

```
[
  "Authentication and ownership checks limit the exploit to an authenticated customer abusing a quote they own; they do not constrain that customer's legacy quote fields or binding."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated customer omits request.vehicle and submits legacy motor fields with a very small positive estimatedValue.",
    "PolicyService selects the legacy quote branch and calculates premium from attacker-controlled value.",
    "The result is QUOTED with incomplete data and null quoteVersion, potentially rounding premium to 0.00.",
    "The customer calls bindPolicy.",
    "Expiry, disclosure, completeness, and eligibility checks are skipped and the policy becomes ACTIVE."
  ],
  "impact": "A customer can obtain active motor coverage at an arbitrarily low or zero rounded premium without underwriting.",
  "severity_reasoning": "High because direct customer input controls price and selects a path that bypasses all binding safeguards.",
  "dynamic_test": "Create a legacy motor quote with estimatedValue 0.01 and missing structured risk/disclosure fields, then bind it and record the premium and ACTIVE state."
}
```

#### Validator reasoning

Confirmed source-to-sink path: CustomerApiController.requestMotorQuote accepts a @Valid MotorQuoteRequest and calls PolicyService.createMotorQuote(request, customer, null). MotorQuoteRequest only requires startDate at the top level; the legacy flat fields have no Bean Validation annotations. When vehicle is null, PolicyService checks only presence of selected legacy fields and estimatedValue.signum() > 0, copies them into MotorPolicyForm, and calls the legacy createMotorQuote overload. That overload sets status QUOTED, leaves quoteVersion and quoteExpiresAt unset, and computes annualPremium with estimatedValue * 0.005 * the cover multiplier, rounded to two decimals. estimatedValue=0.01 therefore produces 0.00 for every supported cover multiplier. CustomerApiController.bindPolicy verifies ownership and calls PolicyService.bindPolicy. The service requires QUOTED, then guards all motor expiry, disclosure, and completeness checks behind motor.getQuoteVersion() != null. The legacy quote has null quoteVersion, so it reaches ACTIVE and receives a policy number despite missing structured fields and acknowledgements. No effective control blocks this authenticated owner-controlled path.

#### Code evidence

```
MotorQuoteRequest.java exposes legacy vehicleReg, make, model, year, estimatedValue, coverType, mainDriverName, mainDriverDob, and startDate fields without structured nested objects. PolicyService.java:113-137 enters the legacy branch when vehicle is null, checks estimatedValue only for >0, then creates a MotorPolicyForm. PolicyService.java:616-628 multiplies attacker-provided estimatedValue by 0.005 and a cover multiplier and rounds to two decimals. PolicyService.java:549 applies motor expiry/disclosure/completeness controls only when motor.quoteVersion != null; legacy createMotorQuote(MotorPolicyForm) does not set quoteVersion. CustomerApiController.java:115-124 exposes direct owner-authorized binding.
```

## 28. Policy binding skips motor eligibility checks when quoteVersion is null

- Lead reference: FHZM-028
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:549
- Fingerprint: 8413978d707b6c99bdc9e342c95e214cabe2ae67499ebfa864b1574c22003a9f

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 116,
  "symbol": "bindPolicy",
  "input": "ID of an owned legacy quote with null quoteVersion"
}
```

#### Controls encountered

```
[
  "Customer authentication is required by resolveCustomer",
  "CustomerApiController checks policy ownership before binding",
  "bindPolicy requires the policy status to be QUOTED"
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 566,
  "symbol": "bindPolicy",
  "operation": "sets policy ACTIVE after validation block is skipped"
}
```

#### Counterevidence

```
[
  "Structured motor requests are validated and receive quoteVersion=1, but that path is bypassed when vehicle is null",
  "Authentication and ownership limit the action to the quote owner; they do not enforce motor eligibility or disclosure requirements"
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated customer creates or owns a legacy motor quote with null quoteVersion.",
    "The customer calls POST /policies/{id}/bind.",
    "Ownership and QUOTED-state checks pass.",
    "bindPolicy treats null quoteVersion as a reason to skip motor expiry, disclosure, completeness, and eligibility validation.",
    "The incomplete, underpriced quote is activated."
  ],
  "impact": "Ineligible or underpriced motor policies can be activated.",
  "severity_reasoning": "High because optional metadata controls whether security-relevant underwriting checks run.",
  "dynamic_test": "Bind an owned legacy motor quote whose quoteVersion is null and required risk fields are absent; confirm the policy becomes ACTIVE."
}
```

#### Validator reasoning

The customer API accepts a request with vehicle == null and only requires the legacy flat fields vehicleReg, make, model, year, estimatedValue > 0, coverType, mainDriverName, mainDriverDob, and startDate. It converts that request to MotorPolicyForm and calls the legacy createMotorQuote overload. That overload populates only legacy motor fields; because the structured fields remain incomplete, isStructuredMotorComplete is false, so quoteVersion and quoteExpiresAt are never set and the legacy premium is stored. The owned quote is then reachable through POST /api/customer/policies/{id}/bind: the controller calls resolveCustomer, findById, assertOwns, and bindPolicy. bindPolicy confirms QUOTED, then its entire motor expiry, disclosure, and completeness block is guarded by motor.getQuoteVersion() != null. The legacy quote has null quoteVersion, so the block is skipped and the method sets status ACTIVE and saves it. No effective control prevents an authenticated owner from activating the incomplete quote.

#### Code evidence

```
PolicyService.java:549 wraps every motor-specific binding validation in `if (policy instanceof MotorPolicy motor && motor.getQuoteVersion() != null)`. PolicyService.java:56-101 creates legacy MotorPolicy records without quoteVersion, disclosure timestamps, expiry, or structured completeness. CustomerApiController.java:115-124 verifies ownership but then calls bindPolicy, which sets status ACTIVE at line 566.
```

## 29. Legacy home quote request creates bindable zero-premium policies

- Lead reference: FHZM-029
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:235
- Fingerprint: 1e90f058b52d143224434d7df5dad4e7013d84d7359ac52086c00c6c3d97a347

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 236,
  "symbol": "requestHomeQuote",
  "input": "legacy flat home quote with address omitted and rebuildValue=0.01"
}
```

#### Controls encountered

```
[
  "Spring Security requires authentication for /api/customer/**.",
  "CustomerApiController resolves the acting customer from the authenticated principal (or requires X-Customer-Id for ROLE_MACHINE).",
  "The bind endpoint checks that the policy belongs to that customer.",
  "bindPolicy requires status QUOTED."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 566,
  "symbol": "bindPolicy",
  "operation": "sets legacy zero-premium policy ACTIVE"
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
    "Authenticated customer omits structured address in a home quote and sets rebuildValue to a tiny positive amount.",
    "The legacy branch omits occupancy, history, disclosures, eligibility, and expiry and calculates a premium that can round to 0.00.",
    "The resulting HomePolicy has null quoteDetails.",
    "bindPolicy skips residential validation.",
    "The zero-premium incomplete policy becomes ACTIVE."
  ],
  "impact": "A customer can activate home insurance without underwriting at effectively no premium.",
  "severity_reasoning": "High because an authenticated actor can directly bypass eligibility and pricing controls.",
  "dynamic_test": "Submit a legacy home quote with rebuildValue 0.01 and no structured underwriting fields, bind it, and confirm a 0.00 premium and ACTIVE status."
}
```

#### Validator reasoning

Confirmed. CustomerApiController.requestHomeQuote accepts an authenticated HomeQuoteRequest and passes it to PolicyService.createHomeQuote. When address is null, createHomeQuote immediately calls createLegacyHomeQuote without validateHomeQuote. The request-level constraints allow rebuildValue=0.01, yearBuilt=1600, and bedroomCount=1; createLegacyHomeQuote additionally requires only propertyAddress, propertyType, rebuildValue, yearBuilt, bedroomCount, and startDate, then builds a HomePolicyForm and calls the form overload. That overload sets status QUOTED, copies the flat fields, leaves quoteDetails null, and stores calculateHomePremium(rebuildValue*0.003 with cent rounding). For rebuildValue=0.01 this is 0.00003, which rounds to 0.00. CustomerApiController.bindPolicy performs the ownership check and then PolicyService.bindPolicy only applies residential validation when a HomePolicy has non-null quoteDetails. The legacy policy therefore reaches policy.setStatus(ACTIVE) and receives a policy number. Authentication and ownership constrain the action to the customer’s own policy but do not block creation or binding of the zero-premium policy.

#### Code evidence

```
HomeQuoteRequest.java:27-35 retains flat property fields and allows rebuildValue >=0.01. PolicyService.java:235-238 selects createLegacyHomeQuote when address is null. Lines 314-331 validate only a small flat subset and create HomePolicy without ResidentialQuoteDetails. Lines 631-637 calculate premium from rebuildValue and round to cents. Lines 558-560 validate a HomePolicy only if quoteDetails != null, after which line 566 activates it.
```

## 30. Legacy contents quote request creates bindable zero-premium policies

- Lead reference: FHZM-030
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:285
- Fingerprint: e709a1c373698a64cc39a25617c6384811cbe91eb96f5168a9f31bc0ac8228a5

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 251,
  "symbol": "requestContentsQuote",
  "input": "legacy flat contents quote with address omitted and contentsValue=0.01"
}
```

#### Controls encountered

```
[
  "The API security chain requires authentication for /api/customer/**.",
  "CustomerApiController.assertOwns restricts binding to the policy owner's customer account.",
  "ContentsQuoteRequest @DecimalMin(\"0.01\") permits contentsValue=0.01.",
  "bindPolicy requires the policy to be in QUOTED state."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 566,
  "symbol": "bindPolicy",
  "operation": "sets legacy zero-premium contents policy ACTIVE"
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
    "Authenticated customer omits structured address in a contents quote and supplies contentsValue 0.01.",
    "The legacy branch creates a quote without address, occupancy, history, disclosure, eligibility, or expiry data and may round premium to 0.00.",
    "The policy has null quoteDetails.",
    "bindPolicy skips residential completeness checks.",
    "The contents policy becomes ACTIVE."
  ],
  "impact": "A customer can obtain active contents coverage at a zero rounded premium without underwriting.",
  "severity_reasoning": "High because attacker-controlled request shape and value bypass both eligibility and pricing safeguards.",
  "dynamic_test": "Create and bind a legacy contents quote with contentsValue 0.01 and omitted structured fields; verify the premium and ACTIVE state."
}
```

#### Validator reasoning

The claimed path is directly reachable. An authenticated customer can POST /api/customer/quotes/contents with startDate set and contentsValue=0.01 while omitting address. @Valid does not reject a null nested address, and createContentsQuote routes address==null to createLegacyContentsQuote. That branch checks only contentsValue and startDate, then calls the ContentsPolicyForm overload, which creates a QUOTED ContentsPolicy without setting quoteDetails and computes annualPremium with contentsValue * 0.004. For 0.01 this is 0.00004, which setScale(2, HALF_UP) stores as 0.00. The quote response exposes the policy id. The owner can POST /api/customer/policies/{id}/bind; after the QUOTED check, bindPolicy invokes residential binding validation only when contents.getQuoteDetails()!=null. The legacy policy has no details, so the validation is skipped and the method sets status ACTIVE and generates a policy number. Authentication and ownership prevent cross-account binding, but do not prevent the owning authenticated customer from activating the incomplete zero-premium policy.

#### Code evidence

```
ContentsQuoteRequest.java:24-28 retains flat fields and permits contentsValue >=0.01. PolicyService.java:285-288 selects createLegacyContentsQuote when address is null. Lines 333-344 construct a ContentsPolicy through the legacy form without ResidentialQuoteDetails. Lines 640-649 calculate premium from the tiny attacker-provided value and round to cents. Lines 561-563 validate contents binding only when quoteDetails != null; line 566 then sets ACTIVE.
```

## 31. Concurrent policy binds can generate duplicate policy numbers

- Lead reference: FHZM-031
- Category: A04
- Severity: MEDIUM
- Confidence: 97%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:653
- Fingerprint: 5d2fb234c29a1359220d5d06f0ed8340a7f40d26d600bf83441edd17c1d6d095

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/PolicyController.java",
  "line": 153,
  "symbol": "bind",
  "input": "concurrent policy ids"
}
```

#### Controls encountered

```
[
  "The bind method rejects policies whose status is not QUOTED.",
  "Spring Security requires authentication for the route.",
  "The unique database constraint prevents two duplicate policy numbers from persisting.",
  "Motor and residential quote completeness and expiry checks may reject invalid quotes before allocation."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 563,
  "symbol": "bindPolicy",
  "operation": "assigns generated unique policy number and saves"
}
```

#### Counterevidence

```
[
  "The unique constraint blocks durable duplicate numbers, but it does not serialize allocation or make both valid bind requests succeed.",
  "The synchronized generator serializes only the count-and-format operation; the surrounding @Transactional method commits after that lock is released.",
  "Different policy types receive different prefixes, so the collision requires concurrent quotes of the same type; the endpoint permits that case."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated customer prepares two distinct owned policies in QUOTED state.",
    "Two bind requests are sent concurrently.",
    "Both transactions count committed policies and derive the same next policy number; the synchronized method returns before either transaction commits.",
    "Each assigns the duplicate number and attempts to save.",
    "The unique constraint rejects one otherwise valid bind, leaving outcome timing-dependent."
  ],
  "impact": "Valid policy binding can fail intermittently, harming lifecycle integrity and availability.",
  "severity_reasoning": "Medium because exploitation requires authenticated concurrent operations and primarily causes transaction failure rather than direct data theft.",
  "dynamic_test": "Use a barrier to submit binds for two different quoted test policies concurrently and observe whether both calculate the same policy number and one fails on the unique constraint."
}
```

#### Validator reasoning

Confirmed. PolicyController.bind exposes POST /policies/{id}/bind and the main security chain requires authentication, with no role or object-level restriction on this action. PolicyService.bindPolicy is a public @Transactional method that accepts any QUOTED policy, sets it ACTIVE, calls the private synchronized generatePolicyNumber, and saves the entity. The generator counts ACTIVE, LAPSED, and CANCELLED rows and returns count+1 with a type/year prefix. Because the synchronized method returns before the outer transaction commits, two concurrent binds of different quoted policies of the same type can each count the same committed rows (plus their own pending update if Hibernate flushes before the count) and receive the same number. Policy.policyNumber is a unique column, so the collision is rejected at the database write/commit; the unique index prevents duplicate persistence but does not prevent one otherwise valid bind transaction from failing and rolling back. No repository lock, serializable transaction setting, retry, or database sequence was found.

#### Code evidence

```
PolicyController.bind(id) calls policyService.bindPolicy(id). bindPolicy is @Transactional, checks QUOTED, changes status, calls generatePolicyNumber(), and saves. generatePolicyNumber is synchronized but computes countByStatus(ACTIVE)+countByStatus(LAPSED)+countByStatus(CANCELLED)+1. The synchronized method returns before the @Transactional bindPolicy commit. Policy.policyNumber is @Column(unique = true). Concurrent transactions can both count the same committed rows and generate the same value.
```

## 32. Seeded default staff credentials expose customer password reset

- Lead reference: FHZM-032
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:112
- Fingerprint: 4efe74c9b2ba38398b4a2132c395e7d6f442b67d6c96ace533d9c881684d5369

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerController.java",
  "line": 86,
  "symbol": "setPassword",
  "input": "attacker-chosen newPassword after login with shipped staff credentials"
}
```

#### Controls encountered

```
[
  "Spring Security requires an authenticated web session.",
  "CSRF protection is enabled for the web chain, but an attacker with the shipped credentials can obtain a valid session and CSRF token through the normal login flow.",
  "newPassword is limited to nonblank values of 8-100 characters.",
  "CustomerService stores the replacement password using BCrypt."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/CustomerService.java",
  "line": 44,
  "symbol": "setPassword",
  "operation": "replaces target customer's password hash"
}
```

#### Counterevidence

```
[
  "The seeded account exists only when the users table is empty, so exploitation depends on a fresh or reset deployment retaining the documented defaults.",
  "The repository does not prove that a particular production instance is internet-exposed."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated actor signs in using seeded staff/staff123 credentials.",
    "The actor enumerates customers and chooses a customer id.",
    "The general authenticated security rule permits POST /customers/{id}/set-password for CONTACT_CENTRE.",
    "The actor sets a new portal password.",
    "The actor authenticates through the customer API and reaches the victim's data and state-changing actions."
  ],
  "impact": "Customer account takeover, sensitive data exposure, and unauthorized customer actions.",
  "severity_reasoning": "High because fixed public staff credentials combine with an over-broad password-reset permission to give remote takeover.",
  "dynamic_test": "On a fresh test database, log in as staff/staff123, reset a seeded test customer's password, then authenticate through /api/customer/auth with the new password."
}
```

#### Validator reasoning

The source supports a complete path. DataInitializer.run() invokes seed() when userRepository.count() is zero, and seed() creates active staff/staff123 with CONTACT_CENTRE. README publishes the same credentials. SecurityConfig's second chain protects /customers/** only with anyRequest().authenticated(); it has no role restriction for CustomerController. CustomerController exposes POST /customers/{id}/set-password, and CustomerService.setPassword finds the attacker-selected customer, BCrypt-encodes the supplied value, and saves it. The authenticated staff user can enumerate IDs through GET /customers and view customer records through GET /customers/{id}. CSRF does not block a logged-in attacker who retrieves the token and submits a same-origin request. The reset credentials then work at the permitAll POST /api/customer/auth endpoint, which issues a JWT for the target customer's email. CustomerApiController resolves JWT users from that email and exposes authenticated profile, policy, claim, quote, bind, and document operations, with no staff-role or customer-ownership check needed after the attacker has obtained the target customer's JWT.

#### Code evidence

```
DataInitializer.run() calls seed() whenever userRepository.count()==0. seed() creates username "staff" with passwordEncoder.encode("staff123") and role CONTACT_CENTRE. README documents these defaults. SecurityConfig applies role checks only to /admin/** and selected claim transitions, then permits any authenticated account for all other requests. CustomerController.setPassword accepts newPassword and calls CustomerService.setPassword(id, raw), which BCrypt-hashes and saves it.
```

## 33. Seeded administrator credentials are written to application logs

- Lead reference: FHZM-033
- Category: A02
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:567
- Fingerprint: 54b9f4e16d3db1335a8b920463cbf745e2c0ec2bc769bbf1f2fc9ec297305023

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java",
  "line": 98,
  "symbol": "seed",
  "input": "hardcoded admin/admin123 credential"
}
```

#### Controls encountered

```
[
  "The database stores a BCrypt hash, but the raw values are passed to the INFO log unchanged.",
  "ROLE_ADMIN protects /admin/** after authentication; it does not mitigate disclosure of the valid admin password.",
  "The reset endpoint is admin-only, but initial seeding runs automatically from CommandLineRunner when the user table is empty."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java",
  "line": 567,
  "symbol": "seed",
  "operation": "SLF4J INFO log of plaintext credentials"
}
```

#### Counterevidence

```
[
  "The application describes these as demo credentials and also exposes admin/admin123 in the README and reset-login page; this reduces secrecy but does not defeat the claimed plaintext log disclosure."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "An actor gains access to routine application INFO logs.",
    "DataInitializer runs on an empty user table or after database reset.",
    "It writes plaintext ADMIN, MANAGER, and staff username/password pairs.",
    "The actor reads the administrator credential from the log.",
    "The actor authenticates and reaches protected /admin/** operations."
  ],
  "impact": "Log readers can recover live administrator credentials and take over the application.",
  "severity_reasoning": "High because routine logs disclose reusable privileged passwords that grant full administrative access.",
  "dynamic_test": "Start with an empty test database, capture INFO logs, verify whether plaintext seeded credentials appear, then use only the test admin credential to confirm an admin-only read."
}
```

#### Validator reasoning

DataInitializer is a Spring component implementing CommandLineRunner. On an empty users table, run() calls seed(), which creates an active user named admin with role ADMIN and passwordEncoder.encode("admin123"). seed() then executes log.info("Login credentials: admin/admin123 | manager/manager123 | staff/staff123"), so the plaintext admin credential reaches the application log. SecurityConfig wires formLogin to the DaoAuthenticationProvider backed by UserService and requires ROLE_ADMIN for /admin/**. There is no forced password change or other check that invalidates the seeded credential. resetAndSeed() deletes users and calls seed() again, providing a second reachable path, although the automatic first-run path alone is sufficient. This is a concrete source-to-log-to-authentication path with no effective blocking control.

#### Code evidence

```
run() calls seed() when userRepository.count() == 0 (lines 39-48). seed() saves admin with passwordEncoder.encode("admin123") and role ADMIN (lines 96-103), manager/manager123 and staff/staff123 (lines 105-121), then executes log.info("Login credentials: admin/admin123  |  manager/manager123  |  staff/staff123") at line 567. SecurityConfig.java:85 restricts /admin/** to ROLE_ADMIN, so the logged admin credential grants access to privileged operations.
```

## 34. Claim uploads trust attacker-supplied MIME type and can distribute malicious files

- Lead reference: FHZM-034
- Category: A04
- Severity: MEDIUM
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:219
- Fingerprint: e51c4057984af1887b07c1dabfb53b8fc62e8323885049fa3e11b8c395a88de8

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 189,
  "symbol": "attachClaimDocument",
  "input": "multipart file bytes, original filename, and Content-Type from authenticated customer"
}
```

#### Controls encountered

```
[
  "The customer API requires authentication and checks that the claim belongs to the resolved customer.",
  "The multipart request and file are limited to 10 MB.",
  "The staff download response uses Content-Disposition attachment.",
  "Thymeleaf escapes the displayed filename."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 222,
  "symbol": "attachDocument",
  "operation": "persist attacker-controlled file metadata and bytes for later staff download"
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
    "Authenticated customer selects a claim they can upload to.",
    "The actor uploads arbitrary bytes while declaring image/* or application/pdf and supplies a misleading filename.",
    "CustomerApiController trusts MultipartFile.getContentType without validating content.",
    "ClaimService stores the bytes and original filename.",
    "Staff encounter the filename and download the attacker-controlled file from /claims/documents/{docId}."
  ],
  "impact": "Stored malicious content can be distributed to staff endpoints, enabling malware delivery or unsafe file handling.",
  "severity_reasoning": "Medium because customer authentication is required and final harm depends on staff opening the downloaded file.",
  "dynamic_test": "Upload a harmless EICAR-style test marker or plain text file declared as image/png to a test claim, then verify staff can download the unchanged non-image bytes and filename."
}
```

#### Validator reasoning

CustomerApiController.attachClaimDocument accepts a non-empty multipart file after checking only file.getContentType(). A caller can declare image/* or application/pdf for arbitrary bytes. It then calls ClaimService.attachDocument, which persists file.getOriginalFilename(), file.getContentType(), and file.getBytes() without signature, content, or malware validation. The same service is also called by the staff upload route without any type validation. ClaimController.downloadDocument later returns the stored bytes with the stored type and filename, and claims/view.html exposes the document link to authenticated staff. Attachment disposition and filename escaping reduce browser rendering and XSS risk, but they do not prevent a customer from storing arbitrary executable or weaponized document bytes for a staff member to download and open. The source-to-sink path is reachable for a normal safe filename and declared MIME type.

#### Code evidence

```
CustomerApiController.java:186-206 accepts POST /api/customer/claims/{id}/documents, checks file.getContentType() only, and calls claimService.attachDocument(id, file, null). ClaimService.java:216-224 stores file.getOriginalFilename(), file.getContentType(), and file.getBytes() without signature/content validation. ClaimController.java:131-138 returns those bytes as an attachment using the stored filename and type; templates/claims/view.html:139-143 presents the uploaded filename as a download link to staff.
```

## 35. Policy bind and cancel operations allow lost-update state races

- Lead reference: FHZM-035
- Category: A04
- Severity: MEDIUM
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:610
- Fingerprint: a6f5b8cbc2bddc8187aabfc42ff6a5d1881ecd3b73d0a435780eb9feacb58dcd

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/PolicyController.java",
  "line": 160,
  "symbol": "cancel",
  "input": "cancel request concurrent with bind"
}
```

#### Controls encountered

```
[
  "The MVC endpoints are behind the authenticated Spring Security filter chain, and CSRF protects form POSTs.",
  "bindPolicy checks QUOTED and quote completeness, while cancelPolicy rejects only an already CANCELLED policy."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 617,
  "symbol": "cancelPolicy",
  "operation": "writes CANCELLED without concurrency guard"
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
    "Authenticated actors issue bind and cancel requests that overlap for the same QUOTED policy.",
    "Each transaction loads an unversioned Policy row without a database lock.",
    "Both validate the stale QUOTED state and write different lifecycle states.",
    "The later commit overwrites the earlier result.",
    "The final status can contradict a successful bind or cancellation response."
  ],
  "impact": "Policy lifecycle state can lose a valid update, producing active coverage after cancellation or cancellation after successful binding.",
  "severity_reasoning": "Medium because authenticated concurrency is required, but the race breaks contract-state integrity.",
  "dynamic_test": "Add a transaction barrier after both operations load the same quoted test policy, release bind and cancel together, and compare both responses with the final database status."
}
```

#### Validator reasoning

Confirmed. PolicyController exposes authenticated POST /policies/{id}/bind and /cancel, and the customer API also calls bindPolicy after an ownership check. Each PolicyService operation is a separate @Transactional request. Both call findById through PolicyRepository.findById, which is an ordinary JpaRepository lookup with no lock. Policy has no @Version field, PolicyRepository has no @Lock query, and application.properties does not configure a serializable isolation level. For a QUOTED row, bindPolicy validates the observed QUOTED state, sets ACTIVE and a policy number, then saves; cancelPolicy validates only that the observed state is not CANCELLED, sets CANCELLED, then saves. Two overlapping transactions can therefore both read QUOTED. The database row lock taken by each UPDATE only serializes the writes; the UPDATE has no version or expected-status predicate, so the later write can overwrite the earlier status. This gives a concrete bind/cancel lost-update path and can leave ACTIVE after a cancellation or CANCELLED after a successful bind response. Authentication and CSRF do not prevent two legitimate authenticated requests from overlapping.

#### Code evidence

```
PolicyController exposes POST /policies/{id}/bind and /cancel to authenticated users. PolicyService.bindPolicy is @Transactional, reads findById, requires QUOTED, and writes ACTIVE. cancelPolicy is separately @Transactional, reads findById, rejects only CANCELLED, and writes CANCELLED. Policy has no @Version field, and repository access uses ordinary findById without pessimistic locking. Thus two transactions can both read QUOTED and commit conflicting status updates.
```

## 36. Hard-coded JWT signing key allows customer account impersonation

- Lead reference: FHZM-036
- Category: A02
- Severity: HIGH
- Confidence: 96%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/resources/application.properties:24
- Fingerprint: 5423cc0f873c2e278b56610440dcedf9434da2c4b627bd5a883e9121d889bd58

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/resources/application.properties",
  "line": 24,
  "symbol": "app.jwt.secret",
  "input": "publicly recoverable fixed HMAC signing secret"
}
```

#### Controls encountered

```
[
  "Spring Security requires authentication for /api/customer/** other than the login endpoints, but a JWT accepted by the filter satisfies that requirement.",
  "JJWT validates the signature and expiration, yet both are attacker-controlled when the committed HMAC key is known.",
  "Policy and claim ownership checks use the customer selected from the authenticated subject, so they do not prevent impersonation of that subject.",
  "Docker Compose and the entrypoint can override or generate APP_JWT_SECRET, and the deployment guide instructs operators to replace the default for a JAR deployment; these controls do not remove the committed fallback or prevent a direct/default deployment from using it."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/security/JwtAuthenticationFilter.java",
  "line": 38,
  "symbol": "doFilterInternal",
  "operation": "accept forged JWT subject as ROLE_CUSTOMER"
}
```

#### Counterevidence

```
[
  "The recommended Docker path generates a random persisted JWT secret when JWT_SECRET is unset.",
  "The documented JAR deployment supplies app.jwt.secret through an external configuration file.",
  "The properties file contains a warning to replace the key in production."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Actor obtains the fixed Base64 customer JWT key and a seeded or known customer email.",
    "The actor signs a bearer token with that email as subject.",
    "JwtAuthenticationFilter validates the token and grants ROLE_CUSTOMER without a token registry lookup.",
    "CustomerApiController resolves the victim from the subject.",
    "The actor reads profile, policies, and claims or uploads documents as the victim."
  ],
  "impact": "Customer account impersonation with sensitive data access and state-changing capability.",
  "severity_reasoning": "High because public source knowledge alone enables remote authentication bypass.",
  "dynamic_test": "Mint a short-lived token under the committed key for a seeded customer, call protected profile and claims reads, and verify the returned identity."
}
```

#### Validator reasoning

Confirmed. application.properties supplies a fixed Base64 value for app.jwt.secret. JwtTokenProvider decodes that value into the HMAC SecretKey and uses it for both signing and verification; expiry only limits token lifetime. JwtAuthenticationFilter accepts any token that verifies with this key, extracts its subject as an email, and installs ROLE_CUSTOMER without checking that the subject authenticated through /auth or that a token was issued by the server. SecurityConfig applies only an authenticated check to the customer API. CustomerApiController.resolveCustomer uses auth.getName() for non-machine callers, and /profile, /policies, /claims, and /claims/{id}/documents then operate on the customer returned by that email; seeded customer emails provide concrete valid subjects. Thus a token minted with the committed key reaches customer data and customer-owned mutation endpoints. Deployment-time overrides reduce exposure for correctly configured Docker/JAR deployments but are not an effective application control because the committed value remains a valid default and is not required.

#### Code evidence

```
application.properties:21-25 defines app.jwt.secret as a fixed committed value. JwtTokenProvider.java:20-27 decodes it into the HMAC key, and lines 29-46 use the same key to sign and verify subject-bearing JWTs. JwtAuthenticationFilter.java:35-42 converts any valid token subject into an authenticated ROLE_CUSTOMER principal. CustomerApiController.java:314-323 resolves non-machine callers by auth.getName(); its /profile, /policies, /claims, and /claims/{id}/documents routes then act as that customer. DataInitializer.java:117-150 commits several valid customer email subjects.
```

## 37. Default SSO shared secret permits unauthenticated account takeover

- Lead reference: FHZM-037
- Category: A02
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/resources/application.properties:29
- Fingerprint: 6bcba2c6c6e8e8917718295f8436eb0602591f9e3d7883c99e3280fb5ae2a679

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/resources/application.properties",
  "line": 29,
  "symbol": "app.sso.jwt-secret",
  "input": "known default SSO signing secret"
}
```

#### Controls encountered

```
[
  "POST /api/customer/auth/sso is explicitly permitAll in SecurityConfig",
  "SsoTokenValidator verifies the HMAC signature and issuer and rejects blank subjects, but uses the committed fallback key when APP_SSO_JWT_SECRET is absent",
  "CustomerService.findByEmail only requires that the attacker choose an email present in the customer database",
  "JwtAuthenticationFilter accepts the controller-issued app JWT as ROLE_CUSTOMER for subsequent /api/customer/** requests"
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 71,
  "symbol": "authenticateSso",
  "operation": "issue application bearer token for attacker-selected customer subject"
}
```

#### Counterevidence

```
[
  "APP_SSO_JWT_SECRET can override the fallback in a correctly configured deployment, but docker-compose.yml and .env.example do not set or require it"
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated actor obtains the default SSO shared secret and identifies a customer email.",
    "The actor signs a BankOfEd JWT for that customer.",
    "The public SSO endpoint validates it with the fallback secret.",
    "The application returns its own customer bearer token.",
    "The actor reaches profile, policy, claim, and upload APIs as the victim."
  ],
  "impact": "Unauthenticated customer account takeover.",
  "severity_reasoning": "High because a public default trust secret enables direct forgery at an unauthenticated endpoint.",
  "dynamic_test": "With APP_SSO_JWT_SECRET unset, forge a test BankOfEd token, exchange it, and verify the issued token accesses the selected test customer's profile."
}
```

#### Validator reasoning

Confirmed concrete path: application.properties resolves app.sso.jwt-secret to the public literal bankofed-goosecable-sso-shared-secret-key-32b when APP_SSO_JWT_SECRET is absent. SecurityConfig permits unauthenticated POST /api/customer/auth/sso. SsoTokenValidator constructs an HMAC key from that literal and accepts a correctly signed JWT with issuer BankOfEd and a nonblank subject; it does not require an expiration claim. CustomerApiController.authenticateSso passes the subject to CustomerService.findByEmail and, for a seeded or otherwise existing customer email, immediately calls JwtTokenProvider.generateToken and returns the customer bearer token. The JWT filter then authenticates that token as ROLE_CUSTOMER, and resolveCustomer uses its email principal for profile, policy, claim, and document operations. The issuer check and customer lookup do not prevent an attacker who knows the committed key and a customer email. No effective blocking control exists on the default configuration path.

#### Code evidence

```
application.properties:27-30 sets app.sso.jwt-secret=${APP_SSO_JWT_SECRET:bankofed-goosecable-sso-shared-secret-key-32b}. SecurityConfig.java:42-48 permits POST /api/customer/auth/sso without authentication. SsoTokenValidator.java:17-49 builds an HMAC key from the configured string and accepts a valid signature, expected issuer, and nonblank subject. CustomerApiController.java:56-73 maps that subject to a customer and returns a locally signed customer JWT. DataInitializer.java:117-150 supplies known valid customer email subjects.
```

## 38. Claim number generation races under concurrent submissions

- Lead reference: FHZM-038
- Category: A04
- Severity: MEDIUM
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:236
- Fingerprint: d16e9ea78176f62830bace8a7aff1b5a94fbd629cb03a7c88a878ad7de384e58

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 90,
  "symbol": "create",
  "input": "concurrent authenticated POST /claims/new requests"
}
```

#### Controls encountered

```
[
  "ClaimService.generateClaimNumber() is synchronized, but it protects only claimRepository.count() and formatting.",
  "Claim.claimNumber has a database-backed unique column constraint, so the race causes a failed insert rather than duplicate committed values.",
  "The web and customer API submission paths require authentication."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 106,
  "symbol": "createClaim",
  "operation": "insert Claim with race-prone unique claimNumber"
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
    "An authenticated customer prepares two valid claim submissions for owned active policies.",
    "The submissions execute concurrently.",
    "Both synchronized number-generation calls can observe the same committed repository count because saving occurs outside the synchronization scope.",
    "Both claims receive the same public number and attempt insertion.",
    "The unique constraint rejects one request; deletion can also cause count-based number reuse."
  ],
  "impact": "Legitimate claim submissions can fail predictably under concurrency or table-history conditions.",
  "severity_reasoning": "Medium because the flaw affects availability and workflow reliability, requiring authenticated submissions or prior deletion state.",
  "dynamic_test": "Synchronize two claim submissions so both generate numbers before either insert commits, then verify whether one fails with a duplicate-number constraint error."
}
```

#### Validator reasoning

ClaimController.create and CustomerApiController.submitClaim both call ClaimService.createClaim. That method is transactional, calls the private synchronized generateClaimNumber() at line 109, and calls claimRepository.save(claim) only after the helper returns. Two concurrent transactions can therefore run the helper serially while the first claim has not yet been persisted: both observe the same committed count and construct the same CLM-year-(count+1) value. The monitor is released before save, and no retry or duplicate-key handling exists. Claim.claimNumber is unique, so one concurrent submission is rejected at insert/flush, producing a concrete availability failure. The same count-based scheme can also select a still-existing number after deletion of a lower-numbered claim.

#### Code evidence

```
ClaimService.java:63-106 builds a Claim, calls generateClaimNumber(), then saves it after the helper returns. Lines 235-239 synchronize only the count/read and format operation. Claim.java:23-24 enforces a unique claimNumber. Because the insert occurs outside the synchronized section, request A can obtain CLM-year-(N+1), release the lock, request B can read the same count before A inserts, and both attempt the same unique value.
```

## 39. Default administrator credentials are seeded and exposed on the login page

- Lead reference: FHZM-039
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: inconclusive
- Reportable: No
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:94
- Fingerprint: 175dc821da4a631163c394588e7ddb2da7d864ce4a1de349ceeec8b3202b8bb6

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/resources/templates/login.html",
  "line": 29,
  "symbol": "reset parameter banner",
  "input": "Unauthenticated reset query parameter"
}
```

#### Controls encountered

```
[
  "Spring Security form login authenticates against UserService and accepts the seeded username/password.",
  "The password is BCrypt-encoded, but the plaintext admin123 is fixed in source and documented.",
  "The /admin/** ADMIN-role check does not block an attacker who logs in as the seeded ADMIN account.",
  "The login route is permitted by formLogin().permitAll(), and the reset query parameter is rendered without authorization or server-side validation."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java",
  "line": 94,
  "symbol": "seed",
  "operation": "Creates active ADMIN with fixed password"
}
```

#### Counterevidence

No counterevidence recorded

#### Proof gaps

No unresolved static proof gaps

#### Attack path

Not available for this candidate

#### Validator reasoning

Confirmed. InsuranceApplication starts the Spring context, and DataInitializer is a component implementing CommandLineRunner. On an empty users table, run() calls seed(), which persists username admin with passwordEncoder.encode("admin123"), role ADMIN, and active true. README.md and deployment documentation also publish the same credentials. LoginController maps unauthenticated GET /login to the login template, while SecurityConfig permits the form-login page. login.html renders the literal admin / admin123 credentials whenever the attacker supplies any reset parameter, with no authorization or provenance check. After submitting those credentials, UserService loads the active user with ROLE_ADMIN, and SecurityConfig plus AdminController authorize /admin/** for that role. The BCrypt encoding and ADMIN authorization are therefore not effective barriers because the plaintext is disclosed and the attacker obtains the required role.

#### Code evidence

```
DataInitializer.run() calls seed() whenever userRepository.count() == 0. seed() saves username "admin", passwordEncoder.encode("admin123"), role ADMIN, active true. login.html:29-32 renders "Credentials: admin / admin123" under th:if="${param.reset}", so GET /login?reset=1 discloses them. SecurityConfig grants /admin/** to role ADMIN.
```

## 40. Concurrent disbursement requests can pay the same claim more than once

- Lead reference: FHZM-040
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:151
- Fingerprint: fe13d5110dba0182f173fd661bc772e048a49728fcc784219f4144989ab06623

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 203,
  "symbol": "disburse",
  "input": "two concurrent authenticated POST requests for the same claim id"
}
```

#### Controls encountered

```
[
  "ClaimController.disburse is restricted to authenticated users with MANAGER or ADMIN roles.",
  "ClaimDisbursementForm validates amount, BSB, account number, payee name, and reference format/length.",
  "The service rejects PAID and REJECTED statuses when those values are observed."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/BankOfEdPaymentClient.java",
  "line": 79,
  "symbol": "transfer",
  "operation": "send duplicate monetary transfer requests"
}
```

#### Counterevidence

```
[
  "Authorization limits who can invoke the endpoint but does not serialize two authorized requests.",
  "The PAID check is performed on each transaction's independently loaded entity and can pass in both transactions.",
  "The @Transactional boundary does not acquire a row lock and the claim is saved only after the external transfer returns."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Two manager/admin clients target the same APPROVED claim.",
    "Concurrent requests both load a non-PAID status without a lock or atomic reservation.",
    "Both invoke the external payment gateway before either commit records PAID.",
    "No stable claim idempotency key lets the gateway collapse duplicates.",
    "Two transfers debit the insurer for one claim."
  ],
  "impact": "Duplicate payout and direct financial loss.",
  "severity_reasoning": "High because a concurrency race reaches a non-idempotent external financial sink.",
  "dynamic_test": "Hold two concurrent approved-claim disbursements at a barrier in a recording stub gateway, release both, and count distinct transfer calls."
}
```

#### Validator reasoning

Confirmed concrete path: ClaimController.disburse accepts POST /claims/{id}/disburse for MANAGER or ADMIN, then calls ClaimService.disburseClaim. The service uses the plain ClaimRepository.findById lookup, checks only the in-memory status, and invokes BankOfEdPaymentClient.transfer while the claim is still not PAID. It assigns PAID and calls claimRepository.save only after a successful gateway response. ClaimRepository has no locking query, Claim has no @Version field or in-progress reservation, and the payment client sends a JSON POST containing the transfer details and bearer token without an idempotency key. With two concurrent transactions, both can read the same APPROVED claim before either commit, both can reach the gateway, and both successful transfers can occur. The database transaction protects each request's eventual update but does not make the external call and status transition atomic.

#### Code evidence

```
ClaimController.java:203-225 exposes POST /claims/{id}/disburse to MANAGER and ADMIN. ClaimService.java:130-151 loads the claim, checks only its current status, then calls bankOfEdPaymentClient.transfer. PAID is assigned only after transfer success at lines 160-165. No pessimistic/optimistic lock or in-progress state is set before the external call. BankOfEdPaymentClient.java:47-79 builds and sends a transfer request without any idempotency key. Claim has no @Version field in the reviewed entity definition.
```

## 41. Legacy motor quote fields bypass binding and premium controls — bindPolicy uses nullable quoteVersion as a security-relevant signal and skips co

- Lead reference: FHZM-041
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java:113
- Fingerprint: 1c37beb81f037f45cf5fd9129c7e67a94803609b7c25c518eadba00291249650

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerApiController.java",
  "line": 220,
  "symbol": "requestMotorQuote",
  "input": "legacy flat quote fields with vehicle omitted and estimatedValue=0.01"
}
```

#### Controls encountered

```
[
  "SecurityConfig requires authentication for /api/customer/**.",
  "CustomerApiController.bindPolicy checks that the policy belongs to the authenticated customer before calling the service.",
  "bindPolicy requires PolicyStatus.QUOTED."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/PolicyService.java",
  "line": 566,
  "symbol": "bindPolicy",
  "operation": "sets bypass-created quote ACTIVE without structured checks"
}
```

#### Counterevidence

```
[
  "These controls only limit access to the customer's own quote and do not constrain the legacy quote values or completeness.",
  "MotorQuoteRequest has no bean-validation constraints on legacy flat fields beyond @NotNull startDate."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated customer omits the structured vehicle object and submits small legacy motor values.",
    "The legacy branch creates a sparse QUOTED policy with attacker-influenced premium and null quoteVersion.",
    "The customer invokes bindPolicy.",
    "The nullable quoteVersion is used as the security-relevant branch condition, so expiry, disclosure, and completeness checks do not run.",
    "The incomplete and potentially zero-premium policy is activated."
  ],
  "impact": "Active underwritten coverage can be obtained with incomplete risk data and negligible premium.",
  "severity_reasoning": "High because a nullable metadata field disables required binding controls for attacker-created quotes.",
  "dynamic_test": "Create a legacy motor quote with null quoteVersion, omitted disclosures, and estimatedValue 0.01; bind it and verify premium plus ACTIVE state."
}
```

#### Validator reasoning

Confirmed concrete path: POST /api/customer/quotes/motor with vehicle omitted enters PolicyService.createMotorQuote(MotorQuoteRequest)'s legacy branch. Its only value check is estimatedValue.signum() > 0; it copies the sparse legacy fields into MotorPolicyForm and calls createMotorQuote(MotorPolicyForm). That method leaves quoteVersion and quoteExpiresAt unset, does not run structured quote validation, and uses calculateMotorPremium: estimatedValue * 0.005 * the cover multiplier, rounded to scale 2. estimatedValue=0.01 therefore produces 0.00 for all supported cover types. The saved policy is QUOTED. POST /api/customer/policies/{id}/bind verifies ownership and QUOTED state, then PolicyService.bindPolicy only applies expiry, disclosure, and isStructuredMotorComplete checks when motor.quoteVersion != null. With the legacy quote's null quoteVersion, it sets status ACTIVE and generates a policy number. No payment or other premium floor check blocks this path.

#### Code evidence

```
MotorQuoteRequest.java exposes legacy vehicleReg, make, model, year, estimatedValue, coverType, mainDriverName, mainDriverDob, and startDate fields without structured nested objects. PolicyService.java:113-137 enters the legacy branch when vehicle is null, checks estimatedValue only for >0, then creates a MotorPolicyForm. PolicyService.java:616-628 multiplies attacker-provided estimatedValue by 0.005 and a cover multiplier and rounds to two decimals. PolicyService.java:549 applies motor expiry/disclosure/completeness controls only when motor.quoteVersion != null; legacy createMotorQuote(MotorPolicyForm) does not set quoteVersion. CustomerApiController.java:115-124 exposes direct owner-authorized binding.
```

## 42. Seeded default staff credentials expose customer password reset — Customer credential reset is available to every authenticated internal role with

- Lead reference: FHZM-042
- Category: A07
- Severity: HIGH
- Confidence: 98%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:112
- Fingerprint: b83228b3382f606e0b894a43562019a251e1e256f4c4e58f4f3868feeb2e2bb9

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/CustomerController.java",
  "line": 86,
  "symbol": "setPassword",
  "input": "attacker-chosen newPassword after login with shipped staff credentials"
}
```

#### Controls encountered

```
[
  "The web chain requires an authenticated session for /customers/**.",
  "CSRF remains enabled for the web chain, so a request needs a valid session CSRF token.",
  "The newPassword request parameter declares nonblank and 8-100 character constraints.",
  "CustomerService stores the replacement using the configured PasswordEncoder."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/CustomerService.java",
  "line": 44,
  "symbol": "setPassword",
  "operation": "replaces target customer's password hash"
}
```

#### Counterevidence

```
[
  "DataInitializer seeds the staff account only when the user table is empty, so the path is deployment-state dependent.",
  "An operator who has changed or removed the documented staff password would no longer be exposed through that credential."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Unauthenticated actor uses fixed staff/staff123 credentials created on an empty database.",
    "The actor crosses the login boundary as CONTACT_CENTRE and enumerates a target customer.",
    "The password-reset route is available to every authenticated internal role and requires no forced credential change.",
    "The actor sets the customer's portal password.",
    "The new password yields a customer JWT and victim-scoped access."
  ],
  "impact": "Remote customer takeover through a low-privileged seeded account.",
  "severity_reasoning": "High because fixed credentials and overly broad reset authorization combine into a direct account-takeover chain.",
  "dynamic_test": "On a fresh test instance, authenticate with the seeded staff credential, reset a test customer's password, and log in through the customer API."
}
```

#### Validator reasoning

Confirmed. DataInitializer.run() calls seed() when userRepository.count() is zero, and seed() creates an active CONTACT_CENTRE user with username staff and the fixed password staff123. README.md and deployment.md publish the same credentials. After form login, SecurityConfig's second chain restricts only /admin/** and selected claim transitions; its anyRequest().authenticated() rule gives CONTACT_CENTRE access to CustomerController. CustomerController has no class or method role check on POST /customers/{id}/set-password, and it passes the attacker-controlled newPassword to CustomerService.setPassword(), which finds the chosen customer, BCrypt-hashes the value, and saves it. The same controller exposes authenticated customer enumeration and views. The changed password is accepted by CustomerApiController.authenticate(), which looks up the customer by email and checks the stored hash, then issues a customer JWT. Customer API profile, policy, claim, quote, and bind routes resolve the JWT principal to that customer, so the takeover path reaches customer data and customer actions. CSRF and password validation do not block an attacker who can log in with the shipped credentials and obtain/use the normal browser form token. The empty-database and credential-change conditions limit when the issue is exploitable but do not defeat the concrete reachable source-to-sink path.

#### Code evidence

```
DataInitializer.run() calls seed() whenever userRepository.count()==0. seed() creates username "staff" with passwordEncoder.encode("staff123") and role CONTACT_CENTRE. README documents these defaults. SecurityConfig applies role checks only to /admin/** and selected claim transitions, then permits any authenticated account for all other requests. CustomerController.setPassword accepts newPassword and calls CustomerService.setPassword(id, raw), which BCrypt-hashes and saves it.
```

## 43. Seeded administrator credentials are written to application logs — Privileged demo accounts use fixed, publicly knowable passwords

- Lead reference: FHZM-043
- Category: A02
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:567
- Fingerprint: 7022865aebfdaa18c737038aee0085cc48f82b8137ac548366c468a130bd7778

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java",
  "line": 98,
  "symbol": "seed",
  "input": "hardcoded admin/admin123 credential"
}
```

#### Controls encountered

```
[
  "The database stores a BCrypt/password-encoded value, but the plaintext admin123 value is passed to the encoder and separately emitted by the INFO log.",
  "The /admin/** matcher and AdminController @PreAuthorize require ADMIN, and the seeded admin user is active with UserRole.ADMIN, so those controls do not block the credential's privileged use.",
  "The initializer seeds on an empty user table and resetAndSeed invokes the same seed method after deleting users."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java",
  "line": 567,
  "symbol": "seed",
  "operation": "SLF4J INFO log of plaintext credentials"
}
```

#### Counterevidence

```
[
  "No forced password change, environment-specific guard, or configuration that suppresses this credential log was found.",
  "The same fixed credentials are also exposed in the login page after reset and in repository documentation, which corroborates that they remain usable defaults."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "DataInitializer creates privileged demo accounts with fixed public passwords.",
    "It also writes the plaintext credentials to INFO logs on empty-database initialization or reset.",
    "An actor learns the values from source, artifacts, the login disclosure, or routine logs.",
    "Spring Security accepts the unchanged admin credential.",
    "The actor reaches all /admin/** functionality."
  ],
  "impact": "Full administrative takeover.",
  "severity_reasoning": "High because fixed privileged credentials remain reusable and are exposed through multiple ordinary channels.",
  "dynamic_test": "Initialize an empty test database, confirm the fixed admin account and plaintext log entry, then verify the unchanged credential authenticates to an admin-only read."
}
```

#### Validator reasoning

DataInitializer.run() calls seed() when userRepository.count() is zero, and resetAndSeed() deletes users then calls seed() again. seed() creates an active admin user with username admin, role ADMIN, and passwordEncoder.encode("admin123"), then logs "Login credentials: admin/admin123 | manager/manager123 | staff/staff123" at INFO. UserService.loadUserByUsername() authenticates the stored user through the configured password encoder and grants ROLE_ADMIN. SecurityConfig permits form login at /login and restricts /admin/** to ROLE_ADMIN; AdminController also has @PreAuthorize("hasRole('ADMIN')"). Therefore a person who can read routine application logs can recover a currently valid admin password and use the normal login flow to reach admin operations. The fixed credential is also directly disclosed by the reset login message and README, and no effective control prevents reuse until an administrator changes it.

#### Code evidence

```
run() calls seed() when userRepository.count() == 0 (lines 39-48). seed() saves admin with passwordEncoder.encode("admin123") and role ADMIN (lines 96-103), manager/manager123 and staff/staff123 (lines 105-121), then executes log.info("Login credentials: admin/admin123  |  manager/manager123  |  staff/staff123") at line 567. SecurityConfig.java:85 restricts /admin/** to ROLE_ADMIN, so the logged admin credential grants access to privileged operations.
```

## 44. Claim number generation races under concurrent submissions — The synchronization scope does not include the database insert and cannot coordi

- Lead reference: FHZM-044
- Category: A04
- Severity: MEDIUM
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:236
- Fingerprint: 6f0aa32371de5b1f0c0e42f3f6d4d886028133d0abf4b2e166dfa560e6936940

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 90,
  "symbol": "create",
  "input": "concurrent authenticated POST /claims/new requests"
}
```

#### Controls encountered

```
[
  "Claim.claimNumber has a database unique constraint, so the race causes one insert to fail rather than create duplicate committed claim numbers.",
  "The POST /claims/new flow requires an authenticated user and validates the form before calling ClaimService.createClaim."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java",
  "line": 106,
  "symbol": "createClaim",
  "operation": "insert Claim with race-prone unique claimNumber"
}
```

#### Counterevidence

```
[
  "The synchronized helper protects only claimRepository.count() and string formatting; it returns before claimRepository.save(claim).",
  "The @Transactional boundary does not extend the Java synchronized lock, so another request can run generateClaimNumber before the first transaction inserts or flushes its Claim.",
  "The lock is local to one ClaimService instance and cannot coordinate multiple application instances."
]
```

#### Proof gaps

No unresolved static proof gaps

#### Attack path

```
{
  "nodes": [
    "Authenticated customer sends two claim submissions concurrently, potentially across application instances.",
    "Each process reads claimRepository.count()+1 while prior inserts are uncommitted.",
    "The JVM synchronized block covers only calculation and cannot coordinate database inserts or other instances.",
    "Both inserts use the same public claim number.",
    "The unique constraint rejects one legitimate claim."
  ],
  "impact": "Claim submission availability becomes timing-dependent and fails under concurrent load.",
  "severity_reasoning": "Medium because the impact is denial of a legitimate workflow rather than unauthorized access, but synchronization does not protect the database invariant.",
  "dynamic_test": "Run two application instances or two barrier-controlled transactions against one database, submit claims concurrently, and check for duplicate generated numbers and a rejected insert."
}
```

#### Validator reasoning

Confirmed source-to-sink path: an authenticated POST /claims/new reaches ClaimController.create, which calls the @Transactional ClaimService.createClaim. That method calls the private synchronized generateClaimNumber(), which reads claimRepository.count() and returns CLM-year-(count+1). The synchronized method ends before ClaimService.createClaim calls claimRepository.save(claim). Two concurrent transactions can therefore both read the same committed count and receive the same claim number before either insert is visible. When both save, the unique claimNumber constraint makes one transaction fail with a database uniqueness error, denying that submission. The same number can also be regenerated after deleting a non-highest claim because generation uses total row count rather than a monotonic database sequence or max-per-year value. The constraint mitigates duplication but does not prevent the timing-dependent availability failure.

#### Code evidence

```
ClaimService.java:63-106 builds a Claim, calls generateClaimNumber(), then saves it after the helper returns. Lines 235-239 synchronize only the count/read and format operation. Claim.java:23-24 enforces a unique claimNumber. Because the insert occurs outside the synchronized section, request A can obtain CLM-year-(N+1), release the lock, request B can read the same count before A inserts, and both attempt the same unique value.
```

## 45. Default administrator credentials are seeded and exposed on the login page — The unauthenticated login page discloses the privileged default credentials base

- Lead reference: FHZM-045
- Category: A07
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java:94
- Fingerprint: 4f27160977ded017bcccde606988e27aad5f195c15542be09d5d346caa47c6ed

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/resources/templates/login.html",
  "line": 29,
  "symbol": "reset parameter banner",
  "input": "Unauthenticated reset query parameter"
}
```

#### Controls encountered

```
[
  "The password is BCrypt-encoded at rest, but this does not protect the disclosed plaintext credential.",
  "The /admin/** authorization requirement is satisfied by the seeded ADMIN account and therefore does not block the attack.",
  "Spring Security formLogin().permitAll() exposes the /login page without authentication."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/config/DataInitializer.java",
  "line": 94,
  "symbol": "seed",
  "operation": "Creates active ADMIN with fixed password"
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
    "Unauthenticated actor requests the login page with the reset query parameter.",
    "The page discloses admin/admin123 without verifying that a reset occurred or that the requester is trusted.",
    "On an empty or reset database, DataInitializer has created that active ADMIN account.",
    "The actor authenticates with the disclosed values and receives ROLE_ADMIN.",
    "The actor reaches protected /admin/** operations."
  ],
  "impact": "Unauthenticated full administrative takeover.",
  "severity_reasoning": "High because a public query parameter reveals a live fixed administrator credential.",
  "dynamic_test": "On a fresh test instance, request /login?reset, confirm credential disclosure, authenticate with the displayed account, and access one admin-only read."
}
```

#### Validator reasoning

Confirmed. DataInitializer.run() invokes seed() when userRepository.count() == 0. seed() creates username admin with passwordEncoder.encode("admin123"), role ADMIN, and active true, with no first-login password change or profile/environment guard. LoginController maps GET /login to the login template, and SecurityConfig's formLogin(...).permitAll() makes it unauthenticated. In login.html, th:if="${param.reset}" displays the literal admin / admin123 credentials for any supplied reset parameter, so GET /login?reset=1 is a concrete disclosure path independent of the admin reset workflow. The same seeded active user is loaded by UserService with ROLE_ADMIN, while SecurityConfig grants /admin/** to ADMIN and AdminController also requires that role. An attacker can submit the disclosed credentials to the form login and obtain access to the admin routes. The BCrypt and role checks are not effective blocking controls.

#### Code evidence

```
DataInitializer.run() calls seed() whenever userRepository.count() == 0. seed() saves username "admin", passwordEncoder.encode("admin123"), role ADMIN, active true. login.html:29-32 renders "Credentials: admin / admin123" under th:if="${param.reset}", so GET /login?reset=1 discloses them. SecurityConfig grants /admin/** to role ADMIN.
```

## 46. Concurrent disbursement requests can pay the same claim more than once — The external transfer request does not carry a stable idempotency key for the cl

- Lead reference: FHZM-046
- Category: A04
- Severity: HIGH
- Confidence: 99%
- Validation: confirmed
- Reportable: Yes
- Location: GooseCable-main/src/main/java/com/goosecable/insurance/service/ClaimService.java:151
- Fingerprint: 3deab17aecfba94790260a0cc3a4c86b22c56ec424343354e44cc2d6ff133095

### Evidence Chain

#### Source

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/controller/ClaimController.java",
  "line": 203,
  "symbol": "disburse",
  "input": "two concurrent authenticated POST requests for the same claim id"
}
```

#### Controls encountered

```
[
  "POST /claims/{id}/disburse is restricted to MANAGER or ADMIN via @PreAuthorize and URL authorization.",
  "The service rejects PAID and REJECTED only based on the status read in each transaction.",
  "@Transactional surrounds each call but does not add a row lock, serializable isolation, version check, or in-progress reservation."
]
```

#### Sink

```
{
  "file": "GooseCable-main/src/main/java/com/goosecable/insurance/service/BankOfEdPaymentClient.java",
  "line": 79,
  "symbol": "transfer",
  "operation": "send duplicate monetary transfer requests"
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
    "Two manager/admin requests disburse the same approved claim concurrently.",
    "Both pass the stale status check and send an external transfer before PAID is committed.",
    "The transfer request lacks a stable idempotency key derived from the claim.",
    "The payment gateway cannot recognize the calls as the same business operation.",
    "Both transfers may settle."
  ],
  "impact": "The insurer can be debited more than once for a single claim.",
  "severity_reasoning": "High because the external financial sink has no final duplicate-suppression control even when concurrent calls occur.",
  "dynamic_test": "Use a recording gateway that supports idempotency inspection, race two disbursements for one claim, and verify that two calls arrive without a shared stable idempotency key."
}
```

#### Validator reasoning

Confirmed. ClaimController.disburse receives two authorized requests and calls ClaimService.disburseClaim. Each transaction executes claimRepository.findById(id), checks PAID/REJECTED, then invokes BankOfEdPaymentClient.transfer before any PAID update is persisted. ClaimRepository.findById has no @Lock query, Claim has no @Version field, and no transaction isolation or application reservation is configured in the reviewed code. Thus concurrent calls can both observe APPROVED (or another non-terminal status) and reach the external transfer. BankOfEdPaymentClient serializes only from/to accounts, amount, and reference into JSON and sends POST /api/payments/transfer; it does not send a stable claim-derived idempotency key or otherwise deduplicate. The later status update to PAID occurs only after transfer success, so it cannot prevent the duplicate external requests. The MANAGER/ADMIN control limits who can trigger the path but does not address the race.

#### Code evidence

```
ClaimController.java:203-225 exposes POST /claims/{id}/disburse to MANAGER and ADMIN. ClaimService.java:130-151 loads the claim, checks only its current status, then calls bankOfEdPaymentClient.transfer. PAID is assigned only after transfer success at lines 160-165. No pessimistic/optimistic lock or in-progress state is set before the external call. BankOfEdPaymentClient.java:47-79 builds and sends a transfer request without any idempotency key. Claim has no @Version field in the reviewed entity definition.
```
