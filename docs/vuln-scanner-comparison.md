# BankOfEd — Vulnerability Scanner Comparison

Ground-truth analysis against 23 intentional OWASP Top 10 vulnerabilities · Generated 21 May 2026

---

## Overall Coverage

| Scanner | Found | Partial | Missed | Raw Findings |
|---|---|---|---|---|
| Single-Agent Sonnet | 8 / 23 (35%) | 4 | 11 | 35 |
| Multi-Agent Haiku | 4 / 23 (17%) | 4 | 15 | 57 |
| Multi-Agent Sonnet | 11 / 23 (48%) | 3 | 9 | 77 |

---

## Table 1 — Ground Truth Coverage

| # | Vulnerability | OWASP | Single-Agent Sonnet | Multi-Agent Haiku | Multi-Agent Sonnet |
|---|---|---|---|---|---|
| 1 | IDOR – transaction detail | A01 | Missed | Missed | **Found** |
| 2 | IDOR – profile mass assignment | A01 | Missed | Missed | Missed |
| 23 | IDOR – external transfer source account | A01 | **Found** | Partial | **Found** |
| 3 | MD5 password hashing | A02 | Missed | Missed | **Found** |
| 4 | Sensitive data in API – password_hash / totp_secret | A02 | **Found** | **Found** | **Found** |
| 5 | SQL injection – admin customer search | A03 | **Found** | Missed | **Found** |
| 22 | SQL injection – transaction sort parameter | A03 | **Found** | Missed | **Found** |
| 6 | Stored XSS – dashboard transaction list | A03 | Partial (static only) | Partial (static only) | Partial (static only) |
| 7 | Stored XSS – account detail table | A03 | Partial (static only) | Partial (static only) | Partial (static only) |
| 8 | TOTP bypass – external transfer | A04 | **Found** | Missed | **Found** |
| 9 | No balance check on external transfers | A04 | Missed | Missed | Missed |
| 10 | Stack trace leakage in error responses | A05 | Partial (indirect) | Missed | **Found** |
| 11 | Overly permissive CORS | A05 | **Found** | **Found** | **Found** |
| 12 | Unauthenticated config/secret leak – /api/health | A05 | **Found** | **Found** | **Found** |
| 13 | Downgraded JWT library (firebase/php-jwt v5) | A06 | Missed | Missed | Missed |
| 14 | Known-vulnerable PHPMailer 5.2 | A06 | Missed | Missed | Missed |
| 15 | User enumeration via login errors | A07 | **Found** | **Found** | **Found** |
| 16 | Weak password policy (minimum 1 character) | A07 | Missed | Missed | Missed |
| 17 | No brute-force / rate-limit protection | A07 | Missed | Missed | Missed |
| 18 | JWT signature bypass (no sig verification) | A08 | Partial (via health leak) | Partial (via health leak) | Partial (via health leak) |
| 19 | Unauthenticated full data export | A09 | Missed | Missed | Missed |
| 20 | No audit logging | A09 | Missed | Missed | Missed |
| 21 | SSRF – avatar proxy | A10 | Missed | Missed | Missed |

---

## Table 2 — Extra Findings Beyond Ground Truth

### Potentially real vulnerabilities not in VULNERABILITIES.md

| Finding | OWASP | Single-Agent Sonnet | Multi-Agent Haiku | Multi-Agent Sonnet |
|---|---|---|---|---|
| Default admin credentials (admin / admin123) | A07 | Found | — | Found |
| Admin DB reset endpoint – data destruction risk | A01 | Found | — | — |
| Admin JWT accepted by user-banking API (privilege boundary) | A01 | Found | — | — |
| Stored XSS in profile name & address fields | A03 | — | Found | — |
| Stored XSS in address-book nickname field | A03 | — | Found | — |
| Unrestricted loan account creation (infinite funds logic flaw) | A04 | — | — | Found |
| Missing Content-Security-Policy header | A05 | Found | — | Found |
| Verbose server / PHP version disclosure | A05 | — | Found | Found |

### Noise & quality indicators

| Metric | Single-Agent Sonnet | Multi-Agent Haiku | Multi-Agent Sonnet |
|---|---|---|---|
| Total raw findings | 35 | 57 | 77 |
| "Unauthenticated access" to public JS static files (false positives) | 3 | 3 | 4 |
| Unconfirmed static XSS sink reports (info / no evidence) | 13 | 26 | 13 |
| Duplicate findings for the same underlying vulnerability | Low | **High (8+)** | Moderate |

---

## Comparison & Verdict

### 1st — Multi-Agent Sonnet (11 / 23, 48%)

The strongest performer overall, covering the broadest range of vulnerability categories: both SQL injection instances, IDOR on external transfers and transaction detail, TOTP bypass, CORS, /api/health secret leak, password hash exposure, user enumeration, and stack trace leakage. It was the only scanner to find the transaction-detail IDOR (#1) and it uniquely surfaced a plausible business-logic flaw — unrestricted loan account creation — not in the original ground truth.

Its main weakness is signal-to-noise: 77 raw findings with noticeable duplication and several static-analysis XSS flags inflated to high severity without dynamic confirmation. Triage effort is higher than the other two.

### 2nd — Single-Agent Sonnet (8 / 23, 35%)

Punched above its weight given it operated as a single agent. Standout quality: uniquely discovered the admin privilege-boundary issue (admin JWT accepted by user banking API) and the database-reset endpoint — genuine vulnerabilities neither multiagent scanner found. The IDOR on external transfers came with actual proof of funds transferred. Evidence was generally the most concrete and actionable of the three.

The fewest raw findings (35) with the best dedup ratio. What it missed is largely things requiring dedicated targeted testing: outdated components, rate-limit policy, SSRF, the unauthenticated export endpoint, and no-balance-check logic. No brute-force or composer.json inspection was attempted.

### 3rd — Multi-Agent Haiku (4 / 23, 17%)

Weakest coverage by a significant margin. The scanner discovered /api/health with the exposed JWT secret early on, then spent most of its effort exploring downstream consequences of that single finding — generating 8+ duplicated critical/high findings all rooted in the same health-endpoint vulnerability. Both SQL injections, the TOTP bypass, the transaction-detail IDOR, and the stack-trace leak were all missed entirely.

The Haiku specialist agents did find dynamically confirmed stored XSS in profile and address-book fields — a legitimate extra discovery that the other scanners missed — but the overall quality cost was high: 57 findings with the most noise and duplication of the three.

---

**Universally missed by all three scanners:** The entire A06 (outdated / vulnerable components) category went undetected — none inspected composer.json for the downgraded JWT library or known-CVE PHPMailer version. Also missed: SSRF avatar proxy (A10), unauthenticated full data export (A09), no audit logging (A09), no balance check on external transfers (A04), weak password policy (A07), no brute-force protection (A07), and IDOR mass assignment on profile update (A01). These largely require source-code review or deliberate targeted testing, suggesting all three scanners operated purely in black-box dynamic mode.
