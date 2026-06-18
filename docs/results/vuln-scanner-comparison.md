# BankOfEd — Vulnerability Scanner Comparison

Ground-truth analysis against 23 intentional OWASP Top 10 vulnerabilities · Generated 24 May 2026

---

## Overall Coverage

| Scanner | Found | Partial | Missed | Raw Findings |
|---|---|---|---|---|
| Multi-Agent Haiku | 4 / 23 (17%) | 4 | 15 | 57 |
| Single-Agent Sonnet | 8 / 23 (35%) | 4 | 11 | 35 |
| Multi-Agent Sonnet | 11 / 23 (48%) | 3 | 9 | 77 |
| Sonnet 4.6 Specialist | 13 / 23 (57%) | 1 | 9 | 59 |

---

## Table 1 — Ground Truth Coverage

| # | Vulnerability | OWASP | Single-Agent Sonnet | Multi-Agent Haiku | Multi-Agent Sonnet (21/May) | Multi-Agent Sonnet 24/May |
|---|---|---|---|---|---|---|
| 1 | IDOR – transaction detail | A01 | Missed | Missed | **Found** | **Found** |
| 2 | IDOR – profile mass assignment | A01 | Missed | Missed | Missed | Missed |
| 23 | IDOR – external transfer source account | A01 | **Found** | Partial | **Found** | **Found** |
| 3 | MD5 password hashing | A02 | Missed | Missed | **Found** | **Found** |
| 4 | Sensitive data in API – password_hash / totp_secret | A02 | **Found** | **Found** | **Found** | **Found** |
| 5 | SQL injection – admin customer search | A03 | **Found** | Missed | **Found** | **Found** |
| 22 | SQL injection – transaction sort parameter | A03 | **Found** | Missed | **Found** | **Found** |
| 6 | Stored XSS – dashboard transaction list | A03 | Partial (static only) | Partial (static only) | Partial (static only) | **Found** (dynamically confirmed) |
| 7 | Stored XSS – account detail table | A03 | Partial (static only) | Partial (static only) | Partial (static only) | Missed |
| 8 | TOTP bypass – external transfer | A04 | **Found** | Missed | **Found** | **Found** |
| 9 | No balance check on external transfers | A04 | Missed | Missed | Missed | **Found** |
| 10 | Stack trace leakage in error responses | A05 | Partial (indirect) | Missed | **Found** | **Found** |
| 11 | Overly permissive CORS | A05 | **Found** | **Found** | **Found** | **Found** |
| 12 | Unauthenticated config/secret leak – /api/health | A05 | **Found** | **Found** | **Found** | **Found** *(miscat. as A02)* |
| 13 | Downgraded JWT library (firebase/php-jwt v5) | A06 | Missed | Missed | Missed | Missed |
| 14 | Known-vulnerable PHPMailer 5.2 | A06 | Missed | Missed | Missed | Missed |
| 15 | User enumeration via login errors | A07 | **Found** | **Found** | **Found** | **Found** |
| 16 | Weak password policy (minimum 1 character) | A07 | Missed | Missed | Missed | Missed |
| 17 | No brute-force / rate-limit protection | A07 | Missed | Missed | Missed | Missed |
| 18 | JWT signature bypass (no sig verification) | A08 | Partial (via health leak) | Partial (via health leak) | Partial (via health leak) | Partial (adjacent: token expiry not validated) |
| 19 | Unauthenticated full data export | A09 | Missed | Missed | Missed | Missed |
| 20 | No audit logging | A09 | Missed | Missed | Missed | Missed |
| 21 | SSRF – avatar proxy | A10 | Missed | Missed | Missed | Missed |

---

## Table 2 — Extra Findings Beyond Ground Truth

### Potentially real vulnerabilities not in VULNERABILITIES.md

| Finding | OWASP | Single-Agent Sonnet | Multi-Agent Haiku | Multi-Agent Sonnet | Sonnet 4.6 Specialist |
|---|---|---|---|---|---|
| Default admin credentials (admin / admin123) | A07 | Found | — | Found | Found |
| Admin DB reset endpoint – data destruction risk | A01 | Found | — | — | — |
| Admin JWT accepted by user-banking API (privilege boundary) | A01 | Found | — | — | Found |
| IDOR – admin API allows direct account balance manipulation | A01 | — | — | — | Found |
| IDOR – admin API exposes full customer PII without scoping | A01 | — | — | — | Found |
| IDOR – unauthorized read access to other users' profile | A01 | — | — | — | Found |
| Admin JWT token expiry not validated | A07 | — | — | — | Found |
| TOTP setup endpoint accessible without authentication | A07 | — | — | — | Found |
| Stored XSS in profile name & address fields | A03 | — | Found | — | — |
| Stored XSS in address-book nickname field | A03 | — | Found | — | Found |
| Unrestricted loan account creation (infinite funds logic flaw) | A04 | — | — | Found | — |
| Admin panel accessible without network restriction | A05 | — | — | — | Found |
| Deleted / invalidated tokens accepted by some endpoints | A07 | — | — | — | Found |
| Missing Content-Security-Policy header | A05 | Found | — | Found | Found |
| Verbose server / PHP version disclosure | A05 | — | Found | Found | Found |

### Noise & quality indicators

| Metric | Single-Agent Sonnet | Multi-Agent Haiku | Multi-Agent Sonnet | Sonnet 4.6 Specialist |
|---|---|---|---|---|
| Total raw findings | 35 | 57 | 77 | 59 |
| "Unauthenticated access" to public JS static files (false positives) | 3 | 3 | 4 | — |
| Unconfirmed static XSS sink reports (no evidence) | 13 | 26 | 13 | ~5 (validating) |
| Duplicate findings for the same underlying vulnerability | Low | **Very High (8+)** | Moderate | **Very High (33 dups)** |

---

## Comparison & Verdict

### 1st — Sonnet 4.6 Specialist (13 / 23, 57%)

The strongest performer overall and the only scanner to dynamically confirm the dashboard XSS rather than flag it as a static-only partial. It also uniquely found the no-balance-check bypass on external transfers (#9) — missed by every other scanner — and surfaced the most secondary IDOR findings (admin balance manipulation, full customer PII exposure, unauthorized profile read). Coverage spans the widest range of OWASP categories of any run.

The main weakness is signal-to-noise: 59 raw findings collapse to 26 unique issues — a 56% duplication rate, the worst of the group. The validator appears to generate many parallel "re-confirms" of the same underlying vulnerability under different severity buckets. Triage effort is high.

### 2nd — Multi-Agent Sonnet (11 / 23, 48%)

Strong broad coverage: both SQL injections, both IDORs (transaction detail and external transfer), TOTP bypass, CORS, /api/health secret leak, password hash exposure, user enumeration, and stack trace leakage. It was the only previous scanner to find the transaction-detail IDOR and uniquely surfaced an unrestricted loan-account creation logic flaw not in the original ground truth.

Its weakness is also noise: 77 raw findings with moderate duplication and several static-analysis XSS flags elevated to high severity without dynamic confirmation.

### 3rd — Single-Agent Sonnet (8 / 23, 35%)

Punched above its weight given it operated as a single agent. Standout quality: uniquely discovered the admin privilege-boundary issue (admin JWT accepted by user banking API) and the database-reset endpoint — genuine vulnerabilities neither multi-agent scanner found. The IDOR on external transfers came with actual proof of funds transferred. Evidence was generally the most concrete and actionable of the four.

The fewest raw findings (35) with the best deduplication ratio. What it missed is largely things requiring deliberate targeted testing: outdated components, rate-limit policy, SSRF, the unauthenticated export endpoint, and the no-balance-check logic.

### 4th — Multi-Agent Haiku (4 / 23, 17%)

Weakest coverage by a significant margin. The scanner discovered /api/health with the exposed JWT secret early on, then spent most of its effort exploring downstream consequences of that single finding — generating 8+ duplicated critical/high findings all rooted in the same health-endpoint vulnerability. Both SQL injections, the TOTP bypass, the transaction-detail IDOR, and the stack-trace leak were all missed entirely.

The Haiku specialist agents did find dynamically confirmed stored XSS in profile and address-book fields — a legitimate extra discovery that Single-Agent Sonnet and Multi-Agent Sonnet missed — but the overall quality cost was high: 57 findings with the most noise and duplication of the four.

---

**Universally missed by all four scanners:** The entire A06 (outdated / vulnerable components) category went undetected — none inspected composer.json for the downgraded JWT library or known-CVE PHPMailer version. Also missed universally: SSRF avatar proxy (A10), unauthenticated full data export (A09), no audit logging (A09), weak password policy (A07), no brute-force protection (A07), and IDOR mass assignment on profile update (A01). These largely require source-code review or deliberate targeted testing, suggesting all four scanners operated purely in black-box dynamic mode.
