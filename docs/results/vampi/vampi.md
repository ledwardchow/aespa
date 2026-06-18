# Vampi Run Results - 2026/06/18

A run of https://github.com/erev0s/VAmPI through AESPA API scanning.


### Model
Claude Sonnet 4.6 (via Bedrock Converse)

### Run time

An ALICE prompt was run to address duplicate findings after the scan completed ("AI Review Issues" feature). The execution time of that prompt is included.

| Phase | Start | End | Duration |
|---|---|---|---|
| SAST scan | 2026-06-18 10:42:00 AEST | 2026-06-18 10:44:30 AEST | ~2m 30s |
| API scan — Test Lead | 2026-06-18 10:45:41 AEST | 2026-06-18 11:13:00 AEST | ~27m 19s |
| ALICE — re-rating prompts | 2026-06-18 10:57 AEST | 2026-06-18 10:58 AEST | 1m |



### Token Usage 

| Input (uncached) | Input (cache read) | Input (cache write) | Output | Total | USD Cost |
|---|---|---|---|---|---|
| 35,398| 17,944,572 | 275,564 | 135,291 | 18,390,825 | $8.55 |


---

### SAST Leads

SAST run #2 `SAST – Vampi - with SAST` — 9 leads, all **confirmed**. Source archive: `VAmPI-master.zip`.

| # | Severity | OWASP | Conf. | Title | Location |
|---|---|---|---|---|---|
| 9 | High | A03 | 0.98 | SQL Injection in `GET /users/v1/{username}` | `models/user_model.py:67` |
| 10 | High | A01 | 0.98 | Unauthenticated sensitive data exposure via debug endpoint | `api_views/users.py:24` |
| 11 | High | A01 | 0.97 | Privilege escalation via mass assignment in user registration | `api_views/users.py:55` |
| 12 | High | A01 | 0.97 | BOLA/IDOR — Authenticated user can change any user's password | `api_views/users.py:183` |
| 13 | High | A01 | 0.97 | BOLA — Any authenticated user can read another user's book secret | `api_views/books.py:47` |
| 14 | High | A07 | 0.95 | Hardcoded weak JWT secret key allows token forgery | `config.py:12` |
| 15 | High | A02 | 0.95 | Plaintext password storage and comparison | `api_views/users.py:80` |
| 17 | High | A05 | 0.90 | Unauthenticated database reset endpoint allows data destruction and credential reset | `api_views/main.py:7` |
| 16 | Medium | A03 | 0.90 | Username enumeration via distinct login error messages | `api_views/users.py:88` |

**By severity:** 8 High · 1 Medium

---

### Findings Summary

Run `2026-06-18 00:45` — 13 findings. Full report: [vampi-issues-2026-06-18.md](runs/vampi/vampi-issues-2026-06-18.md)

**By severity:** 5 Critical · 2 High · 1 Medium · 5 Low

| # | Severity | OWASP | Title | CVSS | Source |
|---|---|---|---|---|---|
| 1 | Critical | API2 | Hardcoded Weak JWT Secret Enables Arbitrary Token Forgery | 9.8 | Dynamic |
| 2 | Critical | API3 | Mass Assignment: Unauthenticated User Can Self-Assign Admin Privileges at Registration | 9.5 | ALICE API |
| 3 | Critical | API10 | SQL Injection via Unsanitised Path Parameter in `GET /users/v1/{username}` | 9.8 | Dynamic |
| 4 | Critical | API5 | Unauthenticated `/createdb` Endpoint Allows Full Database Wipe and Reset | 9.5 | ALICE API |
| 5 | Critical | API5 | Unauthenticated Debug Endpoint Exposes Full User Credential Database in Plaintext | 9.8 | Dynamic |
| 6 | High | API1 | BOLA: Authenticated User Can Change Any Other User's Password via Unvalidated Path Parameter | 8.8 | Dynamic |
| 7 | High | API2 | Plaintext Password Storage and Exposure | 8.0 | ALICE API |
| 8 | Medium | API1 | BOLA: Authenticated User Can Read Any Other User's Book Secret via Unvalidated Path Parameter | 6.5 | Dynamic |
| 9 | Low | API4 | Missing Rate Limiting on Login Endpoint Permits Brute-Force Attacks | 3.7 | Dynamic |
| 10 | Low | API8 | Missing Security Headers and Server Version Disclosure | 3.7 | Dynamic |
| 11 | Low | API4 | No Rate Limiting on User Registration Endpoint Enables Mass Account Creation | 3.7 | Dynamic |
| 12 | Low | API2 | Username Enumeration via Distinct Login Error Messages | 3.7 | Dynamic |
| 13 | Low | API8 | Werkzeug Debug Mode Enabled — Stack Traces and Potential RCE | 3.7 | ALICE API |


---

