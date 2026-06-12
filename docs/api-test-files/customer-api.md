# GooseCable Insurance — Customer REST API

Developer reference for the customer-facing REST API exposed by the GooseCable backend.

---

## Base URL

All endpoints live under:

```
/api/customer
```

e.g. `https://api.goosecable.example.com/api/customer/profile`

---

## Authentication

The API supports two authentication modes. Every protected endpoint accepts either.

---

### Mode 1 — Customer JWT

A short-lived token tied to a specific customer account. Intended for direct use by customers in client applications.

The customer context is implicit — all data is automatically scoped to the authenticated customer. The `X-Customer-Id` header is **not** needed and is ignored.

#### Obtain a token

```
POST /api/customer/auth
Content-Type: application/json
```

**Request body**

```json
{
  "email": "jane.smith@example.com",
  "password": "hunter2"
}
```

**Response `200 OK`**

```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9...",
  "email": "jane.smith@example.com",
  "customerId": 42
}
```

**Error responses**

| Status | Meaning |
|--------|---------|
| `401 Unauthorized` | Email not found, or password does not match |
| `400 Bad Request` | Validation failure (missing/malformed fields) |

#### Using a customer JWT

```
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```

Tokens are valid for **24 hours** by default. Any protected endpoint returns `401` if the token is absent, expired, or invalid.

---

### Mode 2 — Machine Bearer Token

A long-lived static secret for server-to-server integrations (e.g. a backend calling GooseCable on behalf of a customer). Machine tokens never expire; they are revoked explicitly by an admin.

Because a machine token is not tied to any customer, **every request must also include the `X-Customer-Id` header** to specify which customer to act on behalf of. Omitting it returns `400 Bad Request`.

#### Provisioning a machine token

An admin generates machine tokens in the GooseCable admin panel: **Admin → Machine Tokens → Generate Token**. The raw token value is shown **once only** at creation — copy and store it securely immediately. Tokens are prefixed `mch_` for easy identification.

#### Using a machine token

```
Authorization: Bearer mch_<token>
X-Customer-Id: 42
```

**Example**

```bash
curl https://api.goosecable.example.com/api/customer/policies \
  -H "Authorization: Bearer mch_abc123..." \
  -H "X-Customer-Id: 42"
```

---

---

## Endpoints

> **Machine token users:** every endpoint below requires the `X-Customer-Id: <id>` request header when authenticating with a machine bearer token. When using a customer JWT this header is not needed.

### Profile

#### GET /api/customer/profile

Returns the authenticated customer's own account details.

**Response `200 OK`**

```json
{
  "id": 42,
  "firstName": "Jane",
  "lastName": "Smith",
  "email": "jane.smith@example.com",
  "phone": "07700900123",
  "dateOfBirth": "1985-03-12",
  "addressLine1": "14 High Street",
  "addressLine2": null,
  "city": "Manchester",
  "postcode": "M1 1AB"
}
```

---

### Policies

#### GET /api/customer/policies

Returns all policies belonging to the authenticated customer (any status — QUOTED, ACTIVE, LAPSED, CANCELLED).

**Response `200 OK`** — array of policy objects (see [Policy object](#policy-object))

#### GET /api/customer/policies/{id}

Returns a single policy. Returns `403 Forbidden` if the policy belongs to a different customer.

**Response `200 OK`** — single policy object

---

### Claims

#### GET /api/customer/claims

Returns all claims across all of the customer's policies.

**Response `200 OK`**

```json
[
  {
    "id": 7,
    "claimNumber": "CLM-2026-000007",
    "policyId": 3,
    "policyNumber": "MOT-2026-000003",
    "status": "OPEN",
    "incidentDate": "2026-05-28",
    "description": "Vehicle damaged in car park.",
    "estimatedAmount": 1200.00,
    "settledAmount": null,
    "createdAt": "2026-05-29T10:14:33"
  }
]
```

#### POST /api/customer/claims

Submit a new claim against one of the customer's **ACTIVE** policies.

```
POST /api/customer/claims
Content-Type: application/json
Authorization: Bearer <token>
```

**Request body**

```json
{
  "policyId": 3,
  "incidentDate": "2026-05-28",
  "description": "Vehicle damaged in car park.",
  "estimatedAmount": 1200.00
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `policyId` | number | Yes | Must be an ACTIVE policy owned by this customer |
| `incidentDate` | date (ISO 8601) | Yes | |
| `description` | string | Yes | Max 5,000 characters |
| `estimatedAmount` | decimal | No | |

**Response `201 Created`** — the newly created claim object

**Error responses**

| Status | Meaning |
|--------|---------|
| `400 Bad Request` | Validation failure |
| `403 Forbidden` | `policyId` belongs to a different customer |
| `422 Unprocessable Entity` | Policy is not ACTIVE |

---

### Quotes

Quotes are created with status `QUOTED`. Once issued by the backend they can be reviewed internally and bound to an ACTIVE policy by GooseCable staff. The `quoteId` in the response can be used to track status via `GET /api/customer/policies/{quoteId}`.

> **Tip — Spendix vehicle lookup:** Use the [Vehicle lookup](#vehicle-lookup--premium-estimation) endpoints to browse supported makes/models/years and obtain a Spendix-sourced premium estimate before submitting a motor quote. Pass the `id` of the chosen year entry as `spendixYearId` in the motor quote request to have the premium calculated from the catalogued car value automatically.

#### POST /api/customer/quotes/motor

```
POST /api/customer/quotes/motor
Content-Type: application/json
Authorization: Bearer <token>
```

**Request body**

```json
{
  "vehicleReg": "AB12 CDE",
  "make": "Ford",
  "model": "Focus",
  "year": 2021,
  "estimatedValue": 12000.00,
  "spendixYearId": 7,
  "coverType": "COMPREHENSIVE",
  "mainDriverName": "Jane Smith",
  "mainDriverDob": "1985-03-12",
  "namedDrivers": "John Smith",
  "startDate": "2026-07-01",
  "endDate": "2027-06-30"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `vehicleReg` | string | Yes | Max 20 chars |
| `make` | string | Yes | Max 100 chars |
| `model` | string | Yes | Max 100 chars |
| `year` | integer | Yes | 1900–2100 |
| `estimatedValue` | decimal | Yes | Used as the insured value on the policy; also used for premium if `spendixYearId` is not supplied |
| `spendixYearId` | integer | No | ID from `GET /api/customer/vehicles/models/{modelId}/years`. When provided the premium is calculated from the Spendix catalogued car value rather than `estimatedValue` |
| `coverType` | enum | Yes | `COMPREHENSIVE`, `THIRD_PARTY_FIRE_AND_THEFT`, `THIRD_PARTY_ONLY` |
| `mainDriverName` | string | Yes | Max 150 chars |
| `mainDriverDob` | date | Yes | ISO 8601 |
| `namedDrivers` | string | No | Free text, max 500 chars |
| `startDate` | date | Yes | ISO 8601 |
| `endDate` | date | Yes | ISO 8601 |

**Response `201 Created`**

```json
{
  "quoteId": 12,
  "policyType": "MOTOR",
  "annualPremium": 336.00,
  "startDate": "2026-07-01",
  "endDate": "2027-06-30"
}
```

---

#### POST /api/customer/quotes/home

**Request body**

```json
{
  "propertyAddress": "14 High Street, Manchester, M1 1AB",
  "propertyType": "DETACHED",
  "rebuildValue": 250000.00,
  "yearBuilt": 1975,
  "bedroomCount": 3,
  "hasAlarm": true,
  "hasDeadbolts": true,
  "startDate": "2026-07-01",
  "endDate": "2027-06-30"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `propertyAddress` | string | Yes | Max 400 chars |
| `propertyType` | enum | Yes | `DETACHED`, `SEMI_DETACHED`, `TERRACED`, `FLAT` |
| `rebuildValue` | decimal | Yes | |
| `yearBuilt` | integer | Yes | 1600–2100 |
| `bedroomCount` | integer | Yes | 1–20 |
| `hasAlarm` | boolean | No | Default false; 5% premium discount |
| `hasDeadbolts` | boolean | No | Default false; 3% premium discount |
| `startDate` | date | Yes | |
| `endDate` | date | Yes | |

**Response `201 Created`** — quote response object (same shape as motor)

---

#### POST /api/customer/quotes/contents

**Request body**

```json
{
  "contentsValue": 15000.00,
  "highValueItemsValue": 3000.00,
  "accidentalDamageCover": true,
  "startDate": "2026-07-01",
  "endDate": "2027-06-30"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `contentsValue` | decimal | Yes | |
| `highValueItemsValue` | decimal | No | Items individually valued above £1,500 |
| `accidentalDamageCover` | boolean | No | Default false; adds 15% load |
| `startDate` | date | Yes | |
| `endDate` | date | Yes | |

**Response `201 Created`** — quote response object

---

### Vehicle lookup & premium estimation

Browse the Spendix vehicle catalogue to find supported makes, models, and year-based market values, and get a premium estimate before committing to a quote.

> These endpoints require a valid customer JWT or machine bearer token.

#### GET /api/customer/vehicles/makes

Returns all supported vehicle makes in alphabetical order.

**Response `200 OK`**

```json
[
  { "id": 1, "name": "Ford" },
  { "id": 2, "name": "Toyota" }
]
```

---

#### GET /api/customer/vehicles/makes/{makeId}/models

Returns all models for the given make.

**Response `200 OK`**

```json
[
  { "id": 5, "name": "Focus" },
  { "id": 6, "name": "Fiesta" }
]
```

**Error responses**

| Status | Meaning |
|--------|---------|
| `400 Bad Request` | `makeId` not found |

---

#### GET /api/customer/vehicles/models/{modelId}/years

Returns all year entries for the given model, newest first. Each entry includes the Spendix catalogued market value for that year.

**Response `200 OK`**

```json
[
  { "id": 7, "year": 2023, "value": 18500.00 },
  { "id": 8, "year": 2022, "value": 16200.00 },
  { "id": 9, "year": 2021, "value": 14000.00 }
]
```

**Error responses**

| Status | Meaning |
|--------|---------|
| `400 Bad Request` | `modelId` not found |

---

#### GET /api/customer/vehicles/years/{yearId}/premium

Calculates the annual motor insurance premium for the given Spendix year entry and cover type.

**Query parameters**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `coverType` | enum | Yes | `COMPREHENSIVE`, `THIRD_PARTY_FIRE_AND_THEFT`, `THIRD_PARTY_ONLY` |

**Response `200 OK`**

```json
{
  "yearId": 7,
  "coverType": "COMPREHENSIVE",
  "annualPremium": 129.50
}
```

**Premium formula**

`annualPremium = carValue × 0.5% × coverMultiplier`

| Cover type | Multiplier |
|------------|------------|
| `THIRD_PARTY_ONLY` | 1.0× |
| `THIRD_PARTY_FIRE_AND_THEFT` | 1.1× |
| `COMPREHENSIVE` | 1.4× |

**Error responses**

| Status | Meaning |
|--------|---------|
| `400 Bad Request` | `yearId` not found or `coverType` missing/invalid |

---

## Reference

### Policy object

Common fields are always present. Type-specific fields are populated for the relevant `policyType` and `null` otherwise.

```json
{
  "id": 3,
  "policyNumber": "MOT-2026-000003",
  "policyType": "MOTOR",
  "status": "ACTIVE",
  "annualPremium": 336.00,
  "startDate": "2026-07-01",
  "endDate": "2027-06-30",

  // Motor only
  "vehicleReg": "AB12 CDE",
  "make": "Ford",
  "model": "Focus",
  "year": 2021,
  "estimatedValue": 12000.00,
  "coverType": "COMPREHENSIVE",
  "mainDriverName": "Jane Smith",
  "mainDriverDob": "1985-03-12",
  "namedDrivers": "John Smith",

  // Home only
  "propertyAddress": null,
  "propertyType": null,
  "rebuildValue": null,
  "yearBuilt": null,
  "bedroomCount": null,
  "hasAlarm": null,
  "hasDeadbolts": null,

  // Contents only
  "contentsValue": null,
  "highValueItemsValue": null,
  "accidentalDamageCover": null
}
```

### Enumerations

**`policyType`** — `MOTOR`, `HOME`, `CONTENTS`

**`policyStatus`** — `QUOTED`, `ACTIVE`, `LAPSED`, `CANCELLED`

**`coverType`** (motor) — `COMPREHENSIVE`, `THIRD_PARTY_FIRE_AND_THEFT`, `THIRD_PARTY_ONLY`

**`propertyType`** (home) — `DETACHED`, `SEMI_DETACHED`, `TERRACED`, `FLAT`

**`claimStatus`** — `OPEN`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `SETTLED`

---

## Error response format

Spring Boot's default `ProblemDetail` / RFC 9457 format is used for errors.

```json
{
  "type": "about:blank",
  "title": "Bad Request",
  "status": 400,
  "detail": "Validation failed",
  "instance": "/api/customer/claims"
}
```

---

## Quick-start example (curl)

```bash
# 1. Authenticate
TOKEN=$(curl -s -X POST https://api.goosecable.example.com/api/customer/auth \
  -H "Content-Type: application/json" \
  -d '{"email":"jane.smith@example.com","password":"hunter2"}' \
  | jq -r '.token')

# 2. Fetch profile
curl -s https://api.goosecable.example.com/api/customer/profile \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. List policies
curl -s https://api.goosecable.example.com/api/customer/policies \
  -H "Authorization: Bearer $TOKEN" | jq

# 4a. Browse vehicle catalogue and get a Spendix-sourced premium estimate
curl -s https://api.goosecable.example.com/api/customer/vehicles/makes \
  -H "Authorization: Bearer $TOKEN" | jq

curl -s https://api.goosecable.example.com/api/customer/vehicles/makes/1/models \
  -H "Authorization: Bearer $TOKEN" | jq

curl -s https://api.goosecable.example.com/api/customer/vehicles/models/5/years \
  -H "Authorization: Bearer $TOKEN" | jq

curl -s "https://api.goosecable.example.com/api/customer/vehicles/years/7/premium?coverType=COMPREHENSIVE" \
  -H "Authorization: Bearer $TOKEN" | jq

# 4b. Get a motor quote (using Spendix year id for accurate premium)
curl -s -X POST https://api.goosecable.example.com/api/customer/quotes/motor \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicleReg": "AB12 CDE",
    "make": "Ford",
    "model": "Focus",
    "year": 2021,
    "estimatedValue": 14000.00,
    "spendixYearId": 7,
    "coverType": "COMPREHENSIVE",
    "mainDriverName": "Jane Smith",
    "mainDriverDob": "1985-03-12",
    "startDate": "2026-07-01",
    "endDate": "2027-06-30"
  }' | jq

# 5. Submit a claim
curl -s -X POST https://api.goosecable.example.com/api/customer/claims \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "policyId": 3,
    "incidentDate": "2026-05-28",
    "description": "Vehicle damaged in car park.",
    "estimatedAmount": 1200.00
  }' | jq
```

---

## Security notes

- **Never log or persist the JWT** on the client beyond what's needed for the session.
- The JWT secret in `application.properties` (`app.jwt.secret`) **must be replaced** with a cryptographically random Base64-encoded value of at least 256 bits before deployment. Generate one with: `openssl rand -base64 32`
- Token expiry defaults to 24 hours (`app.jwt.expiry-ms=86400000`). Tune for your use case.
- Machine tokens are stored as SHA-256 hashes. The raw value is shown only once at generation time.
- Machine tokens do not expire — revoke them promptly via the admin panel if compromised.
- Customer passwords are stored as BCrypt hashes. Passwords are set/reset by GooseCable staff via the internal admin UI.
- All API endpoints enforce ownership — a customer can only read/write their own data, regardless of auth mode.
