# BankOfEd Scan Results Comparison & Model Benchmark

This document evaluates the security scanning performance and API cost efficiency of **GPT-5.6 Suite**, **MiniMax M3**, **Claude Sonnet 5**, and **Claude Opus 4.8** on the BankOfEd benchmark application, comparing their findings against the ground truth reference in [VULNERABILITIES.md](file:///Users/ledwardchow/GitHub/aespa/docs/results/BankOfEd/VULNERABILITIES.md).

---

## 1. Ground Truth Vulnerability Benchmark (23 Items)

| ID | Ground Truth Vulnerability | OWASP | Target Location | GPT-5.6 Suite | MiniMax M3 | Sonnet 5 | Opus 4.8 |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **1** | IDOR in Transaction Detail | A01 | `TransactionController::show` | Found (#17) | Found (#18) | Found (#19, #39) | Found (#16) |
| **2** | IDOR via Mass Assignment in Profile Update | A01 | `ProfileController::update` | Missed | Found (#9) | Found (#20, #37) | Found (#11) |
| **3** | MD5 Password Hashing | A02 | `AuthService::hashPassword` | Missed | Found (#15, #16) | Found (#28, #52) | Found (#12) |
| **4** | Sensitive Data Exposure (`password_hash`, `totp_secret`) | A02 | `User::toPublic` | Found (#19, #21-23) | Found (#11, #20-25) | Found (#22-27, #43) | Found (#12, #13) |
| **5** | SQL Injection in Admin Customer Search | A03 | `AdminUserController::index` | Found (#18) | Found (#6) | Found (#15, #44) | Found (#9) |
| **6** | Stored XSS in Dashboard Transaction List | A03 | `dashboard.js` | Missed | Found (#13) | Found (#16-18, #47) | Found (#14) |
| **7** | Stored XSS in Account Detail Transaction Table | A03 | `accounts.js` | Missed | Missed | Found (#47) | Missed |
| **8** | TOTP Bypass on External Transfers | A04 | `TransferService::transferExternal` | Found (#2) | Found (#14) | Found (#7, #48) | Found (#8) |
| **9** | No Balance Check on External Transfers | A04 | `TransferService::transferExternal` | Found (#2) | Found (#2) | Found (#9, #10, #42) | Found (#7) |
| **10** | Stack Trace Leakage in Error Responses | A05 | `public/index.php` | Missed | Found (#32) | Found (#33, #36) | Found (#19) |
| **11** | Overly Permissive CORS | A05 | `CorsMiddleware::handle` | Found (#25) | Found (#29, #30) | Found (#31, #32) | Found (#18) |
| **12** | Unauthenticated Config/Secret Leakage | A05 | `Router::health` | Found (#5) | Found (#7) | Found (#5, #50) | Found (#4) |
| **13** | Outdated moment.js (CVE-2022-24785, CVE-2022-31129) | A06 | `public/banking/index.html` | Missed | Found (#26, #27) | Found (#21, #51) | Missed |
| **14** | Outdated jQuery (CVE-2019-11358, CVE-2020-11022) | A06 | `public/banking/index.html` | Missed | Found (#26, #27) | Found (#21, #51) | Missed |
| **15** | User Enumeration on Login | A07 | `AuthController::login` | Found (#28) | Found (#31) | Found (#34, #35) | Missed |
| **16** | Weak Password Policy (1-Character Password) | A07 | `AuthController::register` | Found (#20) | Found (#16) | Found (#28, #53) | Found (#15) |
| **17** | No Brute-Force Protection / Rate Limiting | A07 | Auth Endpoints | Found (#26, #27) | Found (#28) | Found (#29) | Found (#17) |
| **18** | Complete JWT Signature Verification Bypass | A08 | `AuthService::decodeToken` | Missed* | Found (#1) | Found (#1, #41) | Found (#3) |
| **19** | Unauthenticated Full Database Export | A09 | `AdminUserController::exportAll` | Missed | Found (#10) | Found (#8, #49) | Found (#5) |
| **20** | No Audit Logging for Security Events | A09 | Global System | Missed | Missed | Missed | Missed |
| **21** | SSRF via Avatar Proxy | A10 | `ProfileController::avatarProxy` | Found (#7) | Found (#5) | Found (#2, #3, #46) | Found (#2) |
| **22** | SQL Injection in Customer Transaction Listing | A03 | `Transaction::findByUser` | Found (#24) | Found (#12) | Found (#14, #45) | Found (#10) |
| **23** | IDOR on Source Account in Pay Anyone | A01 | `TransferService::transferExternal` | Found (#14) | Found (#8) | Found (#6, #38) | Found (#6) |
| **Total GT** | **Recall Score out of 23** | | | **13 / 23 (56.5%)** | **21 / 23 (91.3%)** | **22 / 23 (95.7%)** | **18 / 23 (78.3%)** |

*\*Note on #18: GPT-5.6 Suite reported JWT forgery (#3), but attributed it to guessing a hardcoded dev secret rather than identifying the total omission of signature verification in `AuthService::decodeToken`.*

---

## 2. Additional Findings Beyond Ground Truth

| Scanner Model | Finding ID & Title | Category / Description | Security Value & Validity |
|---|---|---|---|
| **GPT-5.6 Suite** | **#1**: Administrative Default Credentials | `admin`/`admin123` accepted on `/api/admin/auth/login`. | **High**: Valid configuration flaw in seed database data. |
| | **#3**: Hardcoded JWT Signing Secret Fallback | Claims `bankofed-dev-secret-change-in-production` validates tokens. | **Medium**: Practical exploit path, but misdiagnoses root cause (#18). |
| | **#4**: Unrestricted Self-Issued Loans | Borrowing endpoint permits setting arbitrary loan amounts ($999B+). | **High**: Genuine business logic flaw allowing unlimited credit. |
| | **#6**: Cleartext Transmission of Admin Auth | Plaintext HTTP used for credentials and JWT bearer tokens. | **Low**: Valid transport security finding for unencrypted setups. |
| | **#8**: Race Condition / Duplicate Transfer Submissions | Endpoint lacks idempotency enforcement for concurrent transfers. | **High**: Valid business logic flaw affecting transaction processing. |
| | **#9**: Stored DOM XSS in Payee Dropdown | Unescaped string concatenation of `payee_name` in dropdown options. | **High**: Additional valid stored XSS vector separate from GT #6/7. |
| | **#10-13**: Generic Admin Endpoint Role Bypasses | Four duplicate generic findings on admin endpoint responses. | **Low / Noise**: Duplicate unconfirmed dynamic scanner noise. |
| | **#15**: Own-Account Transfer Loan Balance Bypass | Debit from negative loan balances without authorization/limits. | **Medium**: Valid secondary logical flaw in transfer validation. |
| | **#16**: Admin Direct Balance Overwrite | `/api/admin/accounts/{id}/balance` allows setting arbitrary balance. | **Medium**: Administrative control oversight without audit bounds. |
| | **#29**: Missing Security Response Headers | Missing CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. | **Low**: Standard web application security hygiene issue. |
| **MiniMax M3** | **#3 & #4**: Admin JWT Forgery via SSRF `.env` Leak | SSRF `file:///var/www/bankofed/.env` reads secret to forge admin JWTs. | **High**: Valid exploit chain demonstration combining GT #12 and #21. |
| | **#17**: IDOR on `GET /api/accounts/{id}` | Any authenticated user can read full details of any bank account. | **High**: Valid additional IDOR flaw present in source code. |
| | **#19**: BOLA on Account Index (`GET /api/accounts`) | Returns all bank accounts across all users without user scoping. | **High**: Valid additional BOLA flaw exposing global accounts. |
| | **#33 & #34**: Server Version Header Disclosure | Discloses exact Apache and Ubuntu version strings (`Apache/2.4.58`). | **Low**: Informational banner disclosure (duplicate entry). |
| **Sonnet 5** | **#4**: Administrative Default Credentials | `admin`/`admin123` accepted on admin login endpoint. | **High**: Valid default account issue present in database seeds. |
| | **#11-13**: SQL Injection Error Disclosures | Intermediate error reflection findings during SQLi testing. | **Low / Noise**: Sub-findings of SQLi vulnerabilities #14 and #15. |
| | **#30**: Missing Security Response Headers | Missing X-Frame-Options, CSP, and X-Content-Type-Options on SPA. | **Low**: Valid security header hardening issue. |
| | **#40**: Account Takeover via Profile Mass Assignment | Chaining mass-assignment IDOR (#20) with email change for takeover. | **High**: Excellent threat modeling and attack path synthesis. |
| **Opus 4.8** | **#1**: Default Admin Credentials Accepted | `admin`/`admin123` accepted on admin authentication endpoint. | **High**: Valid configuration issue in seed database data. |

---

## 3. Cost & Token Usage Breakdown

| Scanner Model / Sub-Agent | Uncached Input (↑) | Cached Read (⚡) | Cache Write (✎) | Output (↓) | Exact Cost (USD) |
|---|---|---|---|---|---|
| **MiniMax M3** (`minimax-m3`) | 700,000 | 12,400,000 | — | 564,800 | **$1.2598** |
| **Claude Sonnet 5** (`sonnet-5`) | 298,600 | 15,500,000 | 576,800 | 263,700 | **$11.6643** |
| **Claude Opus 4.8 Run** | | | | | |
| ↳ `claude-opus-4-8` Main Agent | 112,500 | 4,000,000 | 169,700 | 91,000 | $5.8981 |
| ↳ `claude-sonnet-5` Specialist | 12 | 17,200 | 10,100 | 3,600 | $0.0971 |
| **Opus 4.8 Combined Total** | **112,512** | **4,017,200** | **179,800** | **94,600** | **$5.9952** |
| **GPT-5.6 Sol** (Test Lead) | 600,000 | 2,800,000 | — | 81,000 | $6.8300 |
| **GPT-5.6 Terra** (Specialist) | 264,800 | 935,200 | — | 30,000 | $1.3458 |
| **GPT-5.6 Luna** (Crawl, Validator) | 65,100 | 43,400 | — | 11,600 | $0.1390 |
| **GPT-5.6 Suite Combined Total** | **929,900** | **3,778,600** | — | **122,600** | **$8.3148** |

### Itemized Cost Calculation Formulae
* **MiniMax M3 ($1.2598):**
  * Uncached Input: $700,000 \times \frac{\$0.30}{1,000,000} = \$0.2100$
  * Cached Read: $12,400,000 \times \frac{\$0.03}{1,000,000} = \$0.3720$
  * Output: $564,800 \times \frac{\$1.20}{1,000,000} = \$0.6778$
* **Claude Sonnet 5 ($11.6643):**
  * Uncached Input: $298,600 \times \frac{\$3.00}{1,000,000} = \$0.8958$
  * Cache Write: $576,800 \times \frac{\$3.75}{1,000,000} = \$2.1630$
  * Cache Read: $15,500,000 \times \frac{\$0.30}{1,000,000} = \$4.6500$
  * Output: $263,700 \times \frac{\$15.00}{1,000,000} = \$3.9555$
* **Claude Opus 4.8 Run Combined ($5.9952):**
  * `claude-opus-4-8`: $(112,500 \times \frac{\$5.00}{1\text{M}}) + (169,700 \times \frac{\$6.25}{1\text{M}}) + (4,000,000 \times \frac{\$0.50}{1\text{M}}) + (91,000 \times \frac{\$25.00}{1\text{M}}) = \$0.5625 + \$1.0606 + \$2.0000 + \$2.2750 = \$5.8981$
  * `claude-sonnet-5`: $(12 \times \frac{\$3.00}{1\text{M}}) + (10,100 \times \frac{\$3.75}{1\text{M}}) + (17,200 \times \frac{\$0.30}{1\text{M}}) + (3,600 \times \frac{\$15.00}{1\text{M}}) = \$0.0000 + \$0.0379 + \$0.0052 + \$0.0540 = \$0.0971$
* **GPT-5.6 Suite ($8.3148):**
  * `gpt-5.6-sol`: $(600,000 \times \frac{\$5.00}{1\text{M}}) + (2,800,000 \times \frac{\$0.50}{1\text{M}}) + (81,000 \times \frac{\$30.00}{1\text{M}}) = \$3.0000 + \$1.4000 + \$2.4300 = \$6.8300$
  * `gpt-5.6-terra`: $(264,800 \times \frac{\$2.50}{1\text{M}}) + (935,200 \times \frac{\$0.25}{1\text{M}}) + (30,000 \times \frac{\$15.00}{1\text{M}}) = \$0.6620 + \$0.2338 + \$0.4500 = \$1.3458$
  * `gpt-5.6-luna`: $(65,100 \times \frac{\$1.00}{1\text{M}}) + (43,400 \times \frac{\$0.10}{1\text{M}}) + (11,600 \times \frac{\$6.00}{1\text{M}}) = \$0.0651 + \$0.0043 + \$0.0696 = \$0.1390$

---

## 4. Root Cause Analysis: Token Usage vs. Recall Efficiency

GPT-5.6 used **4.71M total input tokens** (inclusive of cache), compared to **4.13M for Opus 4.8**, **13.1M for MiniMax M3**, and **15.8M for Claude Sonnet 5**. Token usage and structural agent configuration directly drove recall performance:

1. **SAST Lead Generation and Code Inspection Coverage:**
   * **Claude Sonnet 5** processed **20 SAST leads** generated by inspecting source code ZIP files (`services/sast_scanner.py`), re-reading PHP source paths, routes, and model definitions.
   * **MiniMax M3** spent tokens reading backend PHP files (`AuthService.php`, `AdminUserController.php`, `User.php`, `Router.php`), accumulating 12.4M cached read tokens.
   * **Claude Opus 4.8** performed precise targeted code inspection, identifying structural flaws (JWT signature bypass GT #18, unauthenticated export GT #19, mass assignment GT #2, SSRF GT #21, MD5 hashing GT #3) while emitting **zero false positives** and only 19 total finding items.
   * **GPT-5.6** generated **0 SAST leads** and relied almost exclusively on dynamic HTTP endpoint probing. Without static analysis tokens to seed hidden leads, it remained blind to code-level flaws such as `AuthService::decodeToken` signature bypass (GT #18), `exportAll()` data dump (GT #19), MD5 hashing (GT #3), and mass assignment (GT #2).

2. **Deduplication Precision and Noise Reduction:**
   * **Claude Opus 4.8** exhibited the highest signal-to-noise ratio: 19 total reported findings yielded 18 Ground Truth matches and 1 valid default credential issue, with **0 false positives and 0 duplicate findings**.
   * **Claude Sonnet 5** achieved higher overall recall (95.7% vs 78.3%), but emitted 53 finding entries (driven by raw error reflection probes and unmerged sub-agent passes).

3. **Shallow Context History & Early Termination in GPT-5.6:**
   * MiniMax M3 accumulated **12.4M cached tokens** and Claude Sonnet 5 accumulated **15.5M cached tokens**, indicating long, context-rich reasoning chains.
   * GPT-5.6's reasoning policy concluded its hypothesis list was "sufficient" early in the run, stopping after generating 29 raw items. Because it terminated exploratory context cycles early, it never progressed to secondary recon phases.

---

## 5. Model Performance Ratings and Technical Commentary

### 1. Claude Sonnet 5
* **Overall Score:** `9.5 / 10`
* **Ground Truth Recall:** `95.7%` (22/23)
* **Exact Scan Cost:** `$11.6643`
* **Cost-Efficiency Value:** **$0.5302 per GT finding** (Highest Recall / Premium).
* **Evaluation:**
  * **Strengths:** Achieved the highest recall across all models. Was the only engine to detect stored XSS in `accounts.js` (GT #7) alongside signature validation omission in `AuthService::decodeToken` (GT #18). Advanced threat modeling synthesized multi-step attack paths, such as chaining profile mass assignment with email modification for full account takeover (Finding #40).
  * **Weaknesses:** Higher cost footprint ($11.6643) and finding redundancy (53 entries driven by raw error reflection probes and unmerged sub-agent passes).

### 2. MiniMax M3
* **Overall Score:** `8.5 / 10`
* **Ground Truth Recall:** `91.3%` (21/23)
* **Exact Scan Cost:** `$1.2598`
* **Cost-Efficiency Value:** **$0.0600 per GT finding** (Highest Value / Best Budget Model).
* **Evaluation:**
  * **Strengths:** Delivered 91.3% ground truth recall at 10.8% of the cost of Claude Sonnet 5 ($1.2598 vs $11.6643). Demonstrated static analysis precision by uncovering structural code flaws including JWT signature verification bypass (GT #18), unauthenticated database export (GT #19), and profile mass assignment (GT #2). Identified extra code-level vulnerabilities such as BOLA on `GET /api/accounts` (Finding #19) and account IDOR (Finding #17).
  * **Weaknesses:** Missed stored XSS in `accounts.js` (GT #7) and global audit logging deficiencies (GT #20).

### 3. Claude Opus 4.8
* **Overall Score:** `8.0 / 10`
* **Ground Truth Recall:** `78.3%` (18/23)
* **Exact Scan Cost:** `$5.9952`
* **Cost-Efficiency Value:** **$0.3331 per GT finding** (Highest Signal-to-Noise Ratio).
* **Evaluation:**
  * **Strengths:** Perfect precision with **zero false positives and zero duplicate findings** (19 total findings reported, matching 18 GT items + 1 valid default credentials finding). Accurately identified deep code flaws including JWT signature bypass (GT #18), unauthenticated export (GT #19), mass assignment (GT #2), SSRF (GT #21), and SQL injections. Operating cost ($5.9952) is 48.6% lower than Sonnet 5.
  * **Weaknesses:** Lower overall recall (78.3%) compared to Sonnet 5 (95.7%) and MiniMax M3 (91.3%). Missed client-side outdated dependencies (GT #13, #14), user enumeration (GT #15), account detail XSS (GT #7), and missing audit logging (GT #20).

### 4. GPT-5.6 Suite
* **Overall Score:** `5.5 / 10`
* **Ground Truth Recall:** `56.5%` (13/23)
* **Exact Scan Cost:** `$8.3148`
* **Cost-Efficiency Value:** **$0.6396 per GT finding** (Lowest Efficiency).
* **Evaluation:**
  * **Strengths:** Effective business logic testing, uncovering transfer idempotency race conditions (Finding #8), payee dropdown DOM XSS (Finding #9), and unrestricted loan balance creation (Finding #4).
  * **Weaknesses:** Weak static analysis despite an $8.3148 execution cost across Sol, Terra, and Luna sub-agents. Missed 10 ground truth items (outdated libraries GT #13/14, MD5 hashing GT #3, profile mass assignment GT #2, unauthenticated DB export GT #19, and stack trace disclosure GT #10). Misdiagnosed the root cause of JWT signature bypass (GT #18) as fallback secret guessing.
