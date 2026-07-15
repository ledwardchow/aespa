# Issue Export: Sonnet 5

- Site: Bank of Ed
- Exported: 14/7/2026, 11:40:05 pm
- Total findings: 29

<!-- aespa-findings-json
%5B%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Default%20Admin%20Credentials%20(admin%2Fadmin123)%20Grant%20Full%20Admin%20Panel%20Access%22%2C%22description%22%3A%22The%20admin%20authentication%20endpoint%20at%20%2Fapi%2Fadmin%2Fauth%2Flogin%20accepts%20the%20trivial%2C%20well-known%20default%20credential%20pair%20admin%2Fadmin123.%20Successful%20authentication%20returns%20a%20valid%20session%20token%20and%20grants%20full%20access%20to%20the%20administrative%20panel%20of%20the%20banking%20application.%22%2C%22impact%22%3A%22An%20attacker%20can%20log%20in%20as%20an%20administrator%20using%20a%20guessable%20default%20credential%2C%20obtaining%20full%20administrative%20access%20to%20the%20application.%20This%20includes%20access%20to%20all%20customer%20records%2C%20accounts%2C%20FX%20rate%20configuration%2C%20and%20system%20reset%20functionality%20(admin%2F%23%2Fsystem)%2C%20representing%20a%20complete%20compromise%20of%20the%20admin%20interface%20and%20the%20sensitive%20data%2Ffunctions%20it%20controls.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20the%20credential%20pair%20admin%2Fadmin123%20was%20submitted%20to%20the%20login%20endpoint%20and%20authenticated%20successfully%2C%20returning%20a%20valid%20admin%20token.%22%2C%22recommendation%22%3A%22Remove%20or%20disable%20default%20admin%20credentials%20immediately.%20Enforce%20a%20strong%20password%20policy%20with%20mandatory%20password%20change%20on%20first%20login%20for%20all%20admin%20accounts.%20Add%20rate%20limiting%20and%20account%20lockout%20on%20the%20admin%20login%20endpoint.%20Implement%20MFA%20for%20admin%20accounts.%20Audit%20for%20any%20other%20default%20or%20weak%20credentials%20across%20the%20application.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fadmin%2Fauth%2Flogin%22%2C%22evidence%22%3A%22POST%20http%3A%2F%2F100.96.0.19%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20body%20%7B%5C%22username%5C%22%3A%5C%22admin%5C%22%2C%5C%22password%5C%22%3A%5C%22admin123%5C%22%7D%20returned%20200%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22admin%5C%22%3A%7B%5C%22id%5C%22%3A1%2C%5C%22username%5C%22%3A%5C%22admin%5C%22%7D%2C%5C%22token%5C%22%3A%5C%22%5BJWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Login%20successful%5C%22%7D%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Full%20Authentication%20Bypass%20via%20Forged%20JWT%20Using%20Leaked%20Signing%20Secret%20%E2%80%94%20Confirmed%20Cross-Account%20Takeover%22%2C%22description%22%3A%22The%20application's%20JWT%20signing%20secret%20was%20previously%20found%20to%20be%20disclosed%20via%20the%20unauthenticated%20GET%20%2Fapi%2Fhealth%20endpoint.%20This%20finding%20demonstrates%20that%20the%20leaked%20secret%20is%20live%20and%20valid%3A%20it%20was%20used%20to%20forge%20an%20HS256-signed%20JWT%20for%20an%20arbitrary%20customer_id%2Fsub%2C%20and%20that%20forged%20token%20was%20accepted%20by%20the%20authenticated%20API%20at%20%2Fapi%2Fprofile%2C%20granting%20full%20account%20access%20with%20no%20login%2C%20password%2C%20or%20valid%20session%20ever%20required.%22%2C%22impact%22%3A%22Any%20attacker%20possessing%20the%20leaked%20jwt_secret%20can%20forge%20a%20validly-signed%20JWT%20for%20any%20customer_id%2Fsub%20value%20and%20gain%20complete%20authenticated%20access%20to%20that%20customer's%20account%20%E2%80%94%20profile%20data%2C%20accounts%2C%20balances%2C%20transactions%2C%20address%20book%2C%20and%20the%20ability%20to%20initiate%20transfers%20%E2%80%94%20without%20a%20password%20or%20session.%20Customer%20IDs%201%E2%80%9321%20were%20observed%20to%20exist%2C%20meaning%20an%20attacker%20could%20forge%20tokens%20for%20and%20fully%20compromise%20every%20customer%20in%20the%20database.%20Combined%20with%20other%20confirmed%20issues%20(missing%20insufficient-funds%20validation%2C%20TOTP%20bypass%20on%20external%20transfers)%2C%20this%20secret%20alone%20is%20sufficient%20to%20drain%20or%20manipulate%20every%20account%20in%20the%20bank.%20This%20confirms%20the%20%2Fapi%2Fhealth%20secret%20leak%20as%20a%20fully%20weaponized%2C%20complete%20authentication%20bypass%20rather%20than%20a%20theoretical%20risk.%22%2C%22likelihood%22%3A%22Confirmed%20via%20live%20exploitation%3A%20a%20forged%20token%20was%20accepted%20by%20the%20server%20and%20returned%20another%20user's%20private%20profile%20data%2C%20including%20their%20bcrypt%20password%20hash%2C%20with%20zero%20valid%20credentials%20used.%22%2C%22recommendation%22%3A%22Immediately%20rotate%20the%20JWT%20signing%20secret%20and%20remove%20it%20from%20the%20%2Fapi%2Fhealth%20response%20(see%20related%20finding%20on%20the%20%2Fapi%2Fhealth%20secret%20leak).%20Additionally%3A%20store%20secrets%20in%20environment%20variables%20or%20a%20secrets%20manager%20that%20is%20never%20exposed%20via%20any%20API%20response%3B%20implement%20short-lived%20access%20tokens%20with%20refresh%20token%20rotation%3B%20ensure%20server-side%20token%20revocation%20(jti%20tracking)%20is%20enforced%20consistently%3B%20and%20ensure%20malformed%20or%20incomplete%20claims%20fail%20closed%20(return%20401)%20rather%20than%20causing%20unhandled%20server%20errors.%22%2C%22cvss_score%22%3A10%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AC%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22Using%20the%20jwt_secret%20leaked%20from%20unauthenticated%20GET%20%2Fapi%2Fhealth%20(%5C%22Jj9XUzmBPzn8VcJEgzD9kC9koZTs1OV6XadreivDDrykIUuLimoQNqQnBdNE4Uv%5C%22)%2C%20an%20HS256%20JWT%20was%20forged%20with%20claims%20%7B%5C%22customer_id%5C%22%3A1%2C%5C%22exp%5C%22%3A2000000000%2C%5C%22jti%5C%22%3A%5C%22aespa-test-jti-001%5C%22%2C%5C%22sub%5C%22%3A1%7D%20without%20any%20legitimate%20login.%20Sending%20GET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%20with%20this%20forged%20token%20as%20Authorization%3A%20Bearer%20returned%20HTTP%20200%20with%20the%20full%20profile%20of%20customer%20%231%20(Amelia%20Chen)%2C%20including%20email%2C%20address%2C%20phone%2C%20and%20bcrypt%20password%20hash%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A1%2C%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Amelia%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Chen%5C%22%2C%5C%22address_line1%5C%22%3A%5C%2214%20Harbour%20View%20Tce%5C%22%2C...%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%2F.og%2Fat2.uheWG%2Figi%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%20%E2%80%94%20confirming%20full%20unauthorized%20account%20access%20achieved%20purely%20by%20offline%20token%20forgery%20using%20the%20leaked%20secret.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22JWT%20Signing%20Secret%20and%20Database%20Credentials%20Exposed%20via%20Unauthenticated%20%2Fapi%2Fhealth%20Endpoint%22%2C%22description%22%3A%22The%20%2Fapi%2Fhealth%20endpoint%20on%20the%20application%20server%20returns%20sensitive%20backend%20configuration%20data%2C%20including%20the%20JWT%20HMAC%20signing%20secret%20and%20internal%20database%20connection%20details%2C%20to%20any%20unauthenticated%20requester.%20No%20authentication%2C%20session%2C%20or%20network%20restriction%20is%20enforced%20on%20this%20endpoint.%22%2C%22impact%22%3A%22Possession%20of%20the%20JWT%20HMAC%20signing%20secret%20allows%20an%20attacker%20to%20forge%20arbitrary%2C%20validly-signed%20JSON%20Web%20Tokens%20for%20any%20user%20or%20administrator%20account%2C%20resulting%20in%20complete%20authentication%20bypass%20and%20full%20account%20takeover%20across%20the%20application.%20The%20disclosed%20database%20host%2C%20database%20name%2C%20and%20application%20database%20username%20further%20expose%20internal%20infrastructure%20details%20that%20could%20facilitate%20follow-on%20attacks%20(e.g.%2C%20targeted%20SQL%20injection%20or%20SSRF%20attempts%20against%20the%20database)%2C%20and%20combined%20with%20the%20leaked%20application%20context%2C%20meaningfully%20lower%20the%20bar%20for%20a%20full%20compromise%20of%20the%20platform.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20reproducible%20with%20a%20single%20unauthenticated%20GET%20request%3B%20no%20preconditions%2C%20authentication%2C%20or%20special%20access%20required.%22%2C%22recommendation%22%3A%22Immediately%20rotate%20the%20exposed%20JWT%20signing%20secret%20and%20invalidate%20all%20existing%20tokens.%20Remove%20jwt_secret%2C%20db_host%2C%20db_name%2C%20and%20db_user%20(and%20any%20other%20configuration%2Fenvironment%20values)%20from%20the%20%2Fapi%2Fhealth%20response%20body%20%E2%80%94%20health%20checks%20should%20return%20only%20minimal%2C%20non-sensitive%20status%20information%20(e.g.%2C%20%5C%22ok%5C%22%2F%5C%22degraded%5C%22).%20Audit%20the%20codebase%20for%20other%20endpoints%20that%20may%20leak%20configuration%20or%20environment%20data.%20Restrict%20any%20endpoint%20that%20must%20return%20diagnostic%2Fconfiguration%20data%20to%20authenticated%20internal%20callers%20or%20internal-network-only%20access%2C%20and%20add%20this%20endpoint%20to%20secret-scanning%2FCI%20checks%20to%20catch%20regressions.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fhealth%20(no%20auth)%20returned%20HTTP%20200%20with%20body%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.3.31%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%2F2.4.58%20(Ubuntu)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22bankofed_app%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22Jj9XUzmBPzn8VcJEgzD9kC9koZTs1OV6XadreivDDrykIUuLimoQNqQnBdNE4Uv%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%20%E2%80%94%20exposing%20the%20live%20JWT%20signing%20secret%20and%20database%20connection%20details%20without%20authentication.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22SQL%20Injection%20via%20'search'%20Parameter%20on%20%2Fapi%2Fadmin%2Fcustomers%20(Unparameterized%20PDO%20Query%2C%20Full%20Error%20Disclosure)%22%2C%22description%22%3A%22The%20admin%20customer%20listing%20endpoint%20%2Fapi%2Fadmin%2Fcustomers%20builds%20a%20raw%20SQL%20query%20by%20directly%20concatenating%20the%20'search'%20query%20parameter%20into%20a%20PDO-%3Equery()%20call%20(AdminUserController.php%2C%20line%2028)%20rather%20than%20using%20a%20parameterized%2Fprepared%20statement.%20Injecting%20a%20single%20apostrophe%20and%20SQL%20metacharacters%20into%20the%20'search'%20parameter%20breaks%20out%20of%20the%20intended%20query%20and%20is%20reflected%20back%20verbatim%20in%20the%20resulting%20MySQL%20syntax%20error%2C%20confirming%20the%20parameter%20is%20not%20sanitized%20or%20bound.%22%2C%22impact%22%3A%22An%20authenticated%20admin-level%20user%20(or%20an%20attacker%20who%20has%20obtained%2Fcompromised%20admin%20credentials)%20can%20manipulate%20the%20underlying%20SQL%20query%20to%20read%2C%20modify%2C%20or%20exfiltrate%20arbitrary%20data%20from%20the%20bankofed%20database%2C%20including%20customer%20PII%2C%20account%20balances%2C%20and%20password%20hashes%2C%20and%20potentially%20escalate%20via%20UNION-based%20extraction%20or%20stacked%20queries.%20The%20unhandled%20error%20response%20also%20discloses%20internal%20file%20paths%2C%20class%2Fmethod%20names%2C%20and%20stack%20traces%2C%20which%20aid%20further%20exploitation%20of%20this%20and%20other%20endpoints.%22%2C%22likelihood%22%3A%22Confirmed.%20A%20single%20injected%20payload%20(test'%3B%20SELECT%20SLEEP(3)--)%20produced%20an%20unhandled%20MySQL%20syntax%20error%20with%20the%20injected%20query%20fragment%20reflected%20back%2C%20demonstrating%20direct%20concatenation%20into%20the%20SQL%20statement%20and%20exploitability%20by%20anyone%20with%20access%20to%20this%20admin%20endpoint.%22%2C%22recommendation%22%3A%22Refactor%20AdminUserController%3A%3Aindex()%20to%20use%20PDO-%3Eprepare()%20with%20bound%20parameters%20for%20the%20'search'%20filter%20instead%20of%20building%20the%20query%20via%20string%20concatenation%20and%20PDO-%3Equery().%20Apply%20the%20same%20fix%20to%20any%20other%20endpoints%20using%20similar%20patterns.%20Disable%20verbose%20error%2Fstack-trace%20disclosure%20in%20production%3B%20return%20a%20generic%20error%20message%20to%20clients%20and%20log%20detailed%20errors%20server-side%20only.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AH%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3D%22%2C%22evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dtest%2527%253B%2520SELECT%2520SLEEP(3)--%20returned%20HTTP%20500%20with%20body%3A%20SQLSTATE%5B42000%5D%3A%20Syntax%20error%20...%20near%20'SELECT%20SLEEP(3)--%25'%20OR%20last_name%20LIKE%20'%25test'%3B%20SELECT%20SLEEP(3)--%25'%20OR%20email%20LIKE'%20at%20line%201%2C%20plus%20stack%20trace%20showing%20PDO-%3Equery()%20called%20at%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FControllers%2FAdminUserController.php%20line%2028.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Business%20Logic%20Bypass%20%E2%80%94%20TOTP%20Step-Up%20Requirement%20for%20External%20Transfers%20Not%20Enforced%20Server-Side%22%2C%22description%22%3A%22The%20application%20exposes%20a%20%2Fapi%2Ftransfers%2Fcheck%20endpoint%20that%20evaluates%20whether%20a%20proposed%20external%20transfer%20requires%20TOTP%20step-up%20authentication%20(e.g.%2C%20for%20manually-entered%20destination%20accounts%20not%20in%20the%20address%20book).%20However%2C%20the%20actual%20transfer%20execution%20endpoint%2C%20%2Fapi%2Ftransfers%2Fexternal%2C%20does%20not%20independently%20enforce%20this%20requirement.%20It%20accepts%20and%20processes%20transfers%20without%20a%20totp_code%20parameter%20even%20when%20%2Ftransfers%2Fcheck%20indicates%20requires_totp%3Atrue%20and%20the%20account%20has%20no%20TOTP%20configured%2C%20allowing%20the%20step-up%20control%20to%20be%20trivially%20bypassed%20by%20simply%20not%20calling%20the%20advisory%20check%20endpoint%20or%20ignoring%20its%20result.%22%2C%22impact%22%3A%22Any%20authenticated%20user%20or%20attacker%20with%20a%20valid%20session%2Ftoken%20(obtained%20via%20any%20means%2C%20including%20XSS%2C%20token%20theft%2C%20or%20CSRF%20vulnerabilities%20present%20elsewhere%20in%20the%20application)%20can%20execute%20arbitrary-amount%20external%20transfers%20to%20any%20destination%20BSB%2Faccount%20number%20without%20providing%20the%20second%20factor%20the%20application%20itself%20flags%20as%20mandatory%20for%20manually-entered%20transfers.%20This%20defeats%20the%20step-up%20authentication%20control%20intended%20to%20protect%20large%20or%20non-address-book%20transfers%2C%20materially%20increasing%20the%20risk%20of%20unauthorized%20fund%20movement.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20reproduced%20by%20directly%20comparing%20%2Ftransfers%2Fcheck%20output%20against%20a%20subsequent%20%2Ftransfers%2Fexternal%20call%20using%20identical%20parameters%20and%20no%20totp_code%20field%2C%20resulting%20in%20a%20successful%20funds%20transfer.%22%2C%22recommendation%22%3A%22Enforce%20the%20TOTP%20requirement%20server-side%20within%20the%20%2Ftransfers%2Fexternal%20(and%20%2Ftransfers%2Fown%2C%20if%20applicable)%20handler%20itself%20rather%20than%20relying%20on%20the%20client%20to%20call%20%2Ftransfers%2Fcheck%20first.%20The%20transfer%20execution%20endpoint%20should%20re-evaluate%20the%20same%20requires_totp%20logic%20and%20reject%20the%20request%20with%20a%20403%2F422%20if%20TOTP%20is%20required%20but%20no%20valid%20totp_code%20was%20supplied%20and%20verified.%20The%20check-and-enforce%20logic%20should%20be%20atomic%20and%20performed%20entirely%20server-side%20within%20the%20transaction%20path.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fcheck%20with%20%7B%5C%22amount%5C%22%3A50000%2C%5C%22from_account_id%5C%22%3A39%2C%5C%22to_account_number%5C%22%3A%5C%2299999999%5C%22%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%7D%20returned%20200%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22requires_totp%5C%22%3Atrue%2C%5C%22reason%5C%22%3A%5C%22manual_entry%5C%22%2C%5C%22totp_configured%5C%22%3Afalse%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D.%20Immediately%20after%2C%20POST%20%2Fapi%2Ftransfers%2Fexternal%20with%20the%20SAME%20parameters%20and%20NO%20totp_code%20field%20returned%20201%20Created%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transaction_id%5C%22%3A37%2C%5C%22from_account_id%5C%22%3A39%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2299999999%5C%22%2C%5C%22amount%5C%22%3A%5C%2250000%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22new_from_balance%5C%22%3A%5C%22999949949.00%5C%22%2C...%7D%2C%5C%22message%5C%22%3A%5C%22Transfer%20completed%20successfully%5C%22%7D.%20The%20transfer%20succeeded%20despite%20the%20check%20endpoint%20declaring%20TOTP%20was%20required%20and%20the%20account%20never%20having%20TOTP%20configured.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Missing%20Insufficient-Funds%20Check%20on%20External%20Transfers%20Allows%20Overdrafting%20Transaction%20Accounts%22%2C%22description%22%3A%22The%20external%20transfer%20endpoint%20(POST%20%2Fapi%2Ftransfers%2Fexternal)%20does%20not%20validate%20that%20the%20source%20account%20holds%20sufficient%20funds%20before%20debiting%20it.%20Standard%20'transaction'%20type%20accounts%2C%20which%20are%20not%20credit%2Floan%20products%20and%20should%20never%20carry%20a%20negative%20balance%2C%20can%20be%20debited%20below%20zero%20by%20any%20authenticated%20customer%20initiating%20a%20transfer%2C%20as%20the%20server%20processes%20the%20debit%20without%20checking%20the%20pre-transfer%20balance%20against%20the%20requested%20amount.%22%2C%22impact%22%3A%22Any%20authenticated%20customer%20can%20move%20arbitrary%20amounts%20of%20money%20out%20of%20a%20zero-%20or%20low-balance%20transaction%20account%20to%20an%20arbitrary%20external%20destination%20account%2FBSB%2C%20driving%20the%20source%20account%20into%20an%20unauthorized%20negative%20balance.%20This%20undermines%20the%20core%20money-movement%20logic%20of%20the%20application%20and%20could%20be%20abused%20to%20extract%20unbacked%20funds%2C%20commit%20accounting%20fraud%2C%20or%20launder%20money%20by%20transferring%20out%20funds%20with%20no%20real%20balance%20behind%20them.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20reproduced%20end-to-end%20by%20provisioning%20a%20fresh%20%240.00-balance%20transaction%20account%20and%20successfully%20executing%20a%20%24500%20external%20transfer%20from%20it%2C%20with%20no%20additional%20privileges%20or%20timing%20tricks%20required.%22%2C%22recommendation%22%3A%22Enforce%20a%20server-side%20balance%20check%20for%20all%20non-credit%2Fnon-loan%20account%20types%20prior%20to%20executing%20any%20debit%20operation%20(transfer%2C%20withdrawal%2C%20payment).%20Reject%20the%20request%20with%20an%20INSUFFICIENT_FUNDS%20error%20if%20the%20resulting%20balance%20would%20go%20negative%20for%20account_type%20not%20in%20('loan'%2C'credit').%20Perform%20the%20balance%20check%20and%20balance%20update%20atomically%20within%20a%20single%20database%20transaction%20using%20row-level%20locking%20(e.g.%2C%20SELECT%20...%20FOR%20UPDATE)%20to%20prevent%20race-condition%20double-spend%20exploitation.%22%2C%22cvss_score%22%3A8.6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22Created%20a%20fresh%20transaction-type%20account%20(id%3D40)%20with%20%240.00%20balance%20via%20POST%20%2Fapi%2Faccounts.%20POST%20%2Fapi%2Ftransfers%2Fexternal%20with%20%7B%5C%22amount%5C%22%3A%5C%22500.00%5C%22%2C%5C%22from_account_id%5C%22%3A40%2C%5C%22to_account_number%5C%22%3A%5C%2299999999%5C%22%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%7D%20returned%20201%20Created%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transaction_id%5C%22%3A39%2C%5C%22from_account_id%5C%22%3A40%2C%5C%22amount%5C%22%3A%5C%22500.00%5C%22%2C%5C%22new_from_balance%5C%22%3A%5C%22-500.00%5C%22%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Transfer%20completed%20successfully%5C%22%7D.%20The%20transfer%20succeeded%2C%20leaving%20the%20account%20balance%20at%20-500.00%20despite%20zero%20starting%20funds%20and%20a%20non-credit%20account%20type.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A10%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SSRF%20via%20Avatar%20Import%20URL%20(%2Fapi%2Fprofile%2Favatar)%20%E2%80%94%20Internal%20Loopback%20and%20Arbitrary%20External%20Fetch%20Confirmed%22%2C%22description%22%3A%22The%20avatar-import-by-URL%20feature%20at%20%2Fapi%2Fprofile%2Favatar%20accepts%20a%20user-supplied%20'url'%20parameter%20and%20performs%20a%20server-side%20HTTP%20fetch%20of%20that%20URL%2C%20returning%20the%20fetched%20content%20(base64-encoded)%20to%20the%20requesting%20client.%20No%20validation%20is%20performed%20to%20restrict%20the%20destination%20to%20trusted%20image%20hosts%2C%20allowing%20the%20server%20to%20be%20used%20as%20an%20SSRF%20proxy%20against%20both%20internal%20and%20external%20targets.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20force%20the%20backend%20to%20issue%20arbitrary%20outbound%20HTTP%20requests%2C%20including%20to%20internal-only%2Floopback%20addresses%20not%20reachable%20from%20the%20internet%2C%20and%20retrieve%20the%20response%20content.%20This%20enables%3A%20(1)%20access%20to%20internal-only%20services%2Fendpoints%20and%20exfiltration%20of%20their%20responses%2C%20(2)%20potential%20pivoting%20to%20cloud%20metadata%20services%20or%20other%20internal%20APIs%20depending%20on%20network%20topology%2C%20and%20(3)%20internal%20network%20reconnaissance%2Fport-scanning%20via%20differential%20success%20(200)%20vs%20FETCH_FAILED%20responses.%20In%20this%20environment%20it%20was%20confirmed%20to%20disclose%20the%20target's%20own%20internal%20web%20content%20via%20a%20loopback%20request.%22%2C%22likelihood%22%3A%22Confirmed%20and%20trivially%20reproducible%20%E2%80%94%20two%20distinct%20payloads%20(http%3A%2F%2F127.0.0.1%3A80%2F%20and%20https%3A%2F%2Fexample.com)%20both%20returned%20200%20with%20the%20fetched%20remote%2Finternal%20content%20verbatim%20in%20the%20response%20body%2C%20requiring%20only%20a%20low-privilege%20authenticated%20request%20with%20no%20user%20interaction.%22%2C%22recommendation%22%3A%22Implement%20strict%20allow-listing%20of%20permitted%20destination%20hosts%2Fschemes%20for%20the%20avatar-import%20feature%20(e.g.%2C%20only%20allow%20specific%20trusted%20image%20CDNs%20over%20HTTPS).%20Resolve%20the%20destination%20hostname%20to%20an%20IP%20and%20validate%20it%20is%20not%20within%20private%2Floopback%2Flink-local%2Freserved%20ranges%20(127.0.0.0%2F8%2C%2010.0.0.0%2F8%2C%20172.16.0.0%2F12%2C%20192.168.0.0%2F16%2C%20169.254.0.0%2F16%2C%20%3A%3A1)%20before%20issuing%20the%20server-side%20request%2C%20and%20re-validate%20after%20any%20redirects%20(disable%20or%20strictly%20limit%20redirect%20following).%20Enforce%20that%20only%20image%20content-types%20are%20fetched%20and%20stored%2C%20rejecting%20text%2Fhtml%20and%20other%20non-image%20responses%20outright.%20Consider%20routing%20outbound%20fetches%20through%20a%20dedicated%20egress%20proxy%20with%20network-level%20restrictions%20to%20internal%20address%20ranges.%22%2C%22cvss_score%22%3A8.6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%2Favatar%22%2C%22evidence%22%3A%22POST%20http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%2Favatar%20with%20body%20%7B%5C%22url%5C%22%3A%5C%22http%3A%2F%2F127.0.0.1%3A80%2F%5C%22%7D%20returned%20200%20with%20base64-encoded%20avatar_data%20that%20decodes%20to%20the%20target's%20own%20banking%20marketing%20homepage%20HTML%20(title%20%5C%22The%20Bank%20of%20Ed%20-%20Banking%20Without%20Borders%5C%22)%2C%20proving%20the%20server%20made%20an%20internal%20loopback%20HTTP%20request%20on%20behalf%20of%20the%20client.%20POST%20with%20body%20%7B%5C%22url%5C%22%3A%5C%22https%3A%2F%2Fexample.com%5C%22%7D%20returned%20200%20with%20avatar_data%20decoding%20to%20the%20literal%20%5C%22Example%20Domain%5C%22%20IANA%20page%20content%20and%20source_url%3A%5C%22https%3A%2F%2Fexample.com%5C%22%2C%20confirming%20the%20server%20fetches%20attacker-supplied%20URLs%20server-side%20and%20returns%20the%20fetched%20content%20to%20the%20client.%20AWS%20metadata%20endpoint%20(169.254.169.254)%20and%20port%2022%20returned%20FETCH_FAILED%2C%20suggesting%20either%20no%20route%20to%20that%20IP%20from%20this%20host%20or%20content-type%2Fresponse%20filtering%2C%20but%20internal%20loopback%20fetch%20(127.0.0.1%3A80)%20was%20fully%20successful.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Stored%20XSS%20via%20Unsanitized%20Transfer%20'description'%20Field%20Rendered%20in%20Dashboard%20Recent%20Activity%22%2C%22description%22%3A%22The%20transfer%20'description'%20field%20accepted%20by%20%2Fapi%2Ftransfers%2Fexternal%20(and%20%2Ftransfers%2Fown)%20is%20stored%20server-side%20without%20HTML%20sanitization%20or%20encoding.%20When%20a%20transaction%20is%20later%20rendered%20on%20the%20Dashboard%2C%20banking%2Fjs%2Fpages%2Fdashboard.js's%20renderTransactions()%20function%20concatenates%20tx.description%20directly%20into%20an%20HTML%20string%20('%3Cp%20class%3D%5C%22font-medium%20text-slate-900%20truncate%5C%22%3E'%20%2B%20(tx.description%20%7C%7C%20tx.type)%20%2B%20'%3C%2Fp%3E')%20without%20calling%20the%20U.escapeHtml()%20helper%20that%20is%20used%20elsewhere%20in%20the%20same%20file%20for%20acc.account_name%2C%20acc.bsb%2C%20and%20acc.account_number.%20The%20resulting%20HTML%20string%20is%20then%20assigned%20via%20container.innerHTML%2C%20creating%20an%20unescaped%20DOM%20sink%20for%20attacker-controlled%20input.%22%2C%22impact%22%3A%22Any%20authenticated%20user%20can%20set%20a%20transfer%20description%20to%20arbitrary%20HTML%2FJavaScript.%20The%20payload%20executes%20in%20the%20browser%20session%20of%20anyone%20who%20subsequently%20views%20that%20transaction%20on%20their%20Dashboard%20%E2%80%94%20the%20sender%2C%20a%20recipient%20with%20a%20real%20internal%20to_account_id%2C%20or%20an%20admin%2Fsupport%20user%20reviewing%20customer%20transaction%20history.%20Because%20the%20application%20stores%20its%20authentication%20JWT%20in%20localStorage%20(directly%20readable%20by%20injected%20script)%2C%20successful%20exploitation%20enables%20theft%20of%20session%20tokens%2C%20account%20takeover%2C%20and%20unauthorized%20actions%20performed%20with%20the%20victim's%20valid%20session%20(e.g.%2C%20initiating%20further%20transfers).%20This%20represents%20a%20critical-impact%20vector%20in%20a%20banking%20application%2C%20reachable%20entirely%20through%20a%20self-service%20field.%22%2C%22likelihood%22%3A%22Confirmed%20exploitable%3A%20the%20payload%20was%20successfully%20stored%20via%20the%20transfer%20API%20and%20persisted%20unescaped%20server-side%2C%20and%20the%20exact%20vulnerable%20client-side%20rendering%20code%20(unescaped%20concatenation%20into%20innerHTML)%20was%20located%20and%20reviewed%20in%20dashboard.js.%20Exploitation%20requires%20only%20that%20a%20victim%20(self%2C%20counterparty%2C%20or%20admin)%20view%20the%20transaction%20in%20the%20UI.%22%2C%22recommendation%22%3A%22In%20dashboard.js%20renderTransactions()%2C%20sanitize%20tx.description%20(and%20the%20tx.type%20fallback)%20with%20U.escapeHtml()%20before%20concatenating%20into%20the%20HTML%20string%2C%20consistent%20with%20the%20existing%20handling%20of%20acc.account_name%2Fbsb%2Faccount_number%20in%20renderAccounts().%20Apply%20the%20same%20fix%20to%20any%20other%20views%20that%20render%20transaction%20descriptions%20(transactions.js%2C%20accounts.js%20detail%20views%2C%20admin%20equivalents).%20Additionally%2C%20validate%2Fencode%20the%20description%20field%20server-side%20at%20the%20API%20layer%20as%20defense-in-depth%2C%20and%20avoid%20storing%20the%20JWT%20in%20localStorage%20where%20it%20is%20reachable%20by%20injected%20script%20%E2%80%94%20prefer%20httpOnly%2C%20SameSite%20cookies%20for%20session%20tokens.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AR%2FS%3AC%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fbanking%2F%23%2Fdashboard%22%2C%22evidence%22%3A%22Server-side%3A%20POST%20http%3A%2F%2F100.96.0.19%2Fapi%2Ftransfers%2Fexternal%20with%20body%20%7B%5C%22amount%5C%22%3A10%2C%5C%22description%5C%22%3A%5C%22%3Cscript%3Ealert(document.domain)%3C%2Fscript%3E%5C%22%2C%5C%22from_account_id%5C%22%3A39%2C%5C%22to_account_number%5C%22%3A%5C%2299999999%5C%22%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%7D%20returned%20201%20with%20the%20payload%20echoed%20back%20completely%20unescaped%3B%20GET%20%2Fapi%2Ftransactions%2F38%20confirmed%20the%20same%20raw%20payload%20persisted%20server-side.%20Client-side%20sink%3A%20dashboard.js%20renderTransactions()%20builds%20HTML%20via%20string%20concatenation%20'%3Cp%20class%3D%5C%22font-medium%20text-slate-900%20truncate%5C%22%3E'%20%2B%20(tx.description%20%7C%7C%20tx.type)%20%2B%20'%3C%2Fp%3E'%20with%20no%20call%20to%20U.escapeHtml()%20(unlike%20acc.account_name%2C%20acc.bsb%2C%20acc.account_number%20in%20the%20same%20file)%2C%20before%20assignment%20via%20container.innerHTML%20%3D%20html.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Stored%20XSS%20via%20unsanitized%20transfer%20'description'%20field%20rendered%20through%20innerHTML%20on%20Dashboard%2FAccount%20pages%22%2C%22description%22%3A%22The%20external%20transfer%20creation%20endpoint%20(POST%20%2Fapi%2Ftransfers%2Fexternal)%20accepts%20an%20arbitrary%2C%20unvalidated%20'description'%20field%20and%20stores%20it%20verbatim%2C%20including%20HTML%2FJS%20payloads%20such%20as%20%3Cscript%3Ealert(document.domain)%3C%2Fscript%3E.%20The%20value%20is%20returned%20unescaped%20both%20in%20the%20transfer%20creation%20response%20and%20on%20subsequent%20reads%20(GET%20%2Fapi%2Ftransactions%2F%3Aid).%20On%20the%20client%2C%20banking%2Fjs%2Fpages%2Fdashboard.js%20(renderTransactions)%20and%20banking%2Fjs%2Fpages%2Faccounts.js%20(account%20detail%20transaction%20table)%20concatenate%20tx.description%20directly%20into%20HTML%20strings%20that%20are%20assigned%20via%20.innerHTML%2C%20without%20calling%20the%20U.escapeHtml()%20helper%20that%20is%20used%20for%20other%20fields%20(e.g.%20account_name%2C%20bsb%2C%20account_number)%20in%20the%20same%20code.%20As%20a%20result%2C%20any%20user%20able%20to%20submit%20a%20transfer%20description%20controls%20script%20execution%20in%20the%20browser%20of%20anyone%20who%20later%20views%20the%20affected%20transaction%20history%20(transferring%20account%2C%20and%20potentially%20the%20receiving%20account%20depending%20on%20which%20account's%20history%20is%20rendered).%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20store%20a%20malicious%20script%20in%20a%20transfer%20description%20that%20executes%20in%20the%20context%20of%20any%20user's%20session%20(own%20or%2C%20depending%20on%20transaction-history%20visibility%2C%20the%20transfer%20recipient's)%20when%20they%20load%20the%20Dashboard%20(%23%2Fdashboard)%20or%20Account%20Detail%20(%23%2Faccounts%2F%3Aid)%20page.%20Since%20this%20is%20a%20banking%20application%2C%20successful%20execution%20could%20exfiltrate%20the%20session%20token%20(bankofed_token%2C%20stored%20in%20browser%20storage)%20or%20other%20sensitive%20data%2C%20enabling%20session%20hijacking%2C%20unauthorized%20transfers%20performed%20as%20the%20victim%2C%20or%20broader%20account%20compromise.%22%2C%22likelihood%22%3A%22High.%20The%20injection%20point%20is%20reached%20through%20the%20standard%2C%20authenticated%20external%20transfer%20API%20with%20no%20special%20privileges%20or%20bypass%20required%2C%20and%20confirmed%20unsanitized%20on%20write%2C%20on%20read%2C%20and%20in%20the%20specific%20client-side%20rendering%20sinks%20(dashboard.js%20and%20accounts.js)%20that%20assign%20attacker-controlled%20content%20directly%20to%20.innerHTML.%22%2C%22recommendation%22%3A%221.%20Sanitize%2Fvalidate%20the%20description%20field%20server-side%20on%20write%20(HTML-encode%20or%20strip%20angle%20brackets%3B%20consider%20a%20strict%20allow-list%20of%20characters%20such%20as%20alphanumeric%2C%20spaces%2C%20and%20basic%20punctuation).%202.%20Client-side%2C%20apply%20the%20existing%20U.escapeHtml()%20helper%20to%20tx.description%20before%20concatenating%20it%20into%20innerHTML%20strings%20in%20dashboard.js%20and%20accounts.js%2C%20consistent%20with%20how%20other%20fields%20(account_name%2C%20bsb%2C%20account_number)%20are%20already%20handled%2C%20or%20refactor%20rendering%20to%20use%20textContent%2FDOM%20APIs%20instead%20of%20innerHTML%20string%20concatenation%20for%20any%20user-controlled%20value.%203.%20Audit%20and%20apply%20the%20same%20escaping%20to%20every%20other%20page%2Fcomponent%20that%20renders%20tx.description%20(transaction%20lists%2C%20statements%2C%20notifications%2C%20exports).%22%2C%22cvss_score%22%3A8.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AR%2FS%3AC%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22Write%3A%20POST%20%2Fapi%2Ftransfers%2Fexternal%20with%20description%3D%5C%22%3Cscript%3Ealert(document.domain)%3C%2Fscript%3E%5C%22%20returned%20201%20with%20the%20payload%20stored%20and%20returned%20raw%2Funescaped.%20Read%3A%20GET%20%2Fapi%2Ftransactions%2F38%20returned%20the%20same%20unescaped%20payload%2C%20confirming%20no%20server-side%20output%20encoding.%20Client-side%20sinks%3A%20dashboard.js%20renderTransactions()%20and%20accounts.js%20account-detail%20transaction%20table%20both%20concatenate%20tx.description%20directly%20into%20HTML%20strings%20assigned%20to%20.innerHTML%2C%20without%20the%20U.escapeHtml()%20call%20used%20for%20other%20fields%20in%20the%20same%20files%2C%20confirming%20an%20exploitable%20stored%20XSS%20chain%20from%20write%20to%20render.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20HTTP%2F1.1%5Cn%7B%5C%22amount%5C%22%3A10%2C%5C%22description%5C%22%3A%5C%22%3Cscript%3Ealert(document.domain)%3C%2Fscript%3E%5C%22%2C%5C%22from_account_id%5C%22%3A39%2C%5C%22to_account_number%5C%22%3A%5C%2299999999%5C%22%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%7D%22%2C%22response_evidence%22%3A%22%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transaction_id%5C%22%3A38%2C...%2C%5C%22description%5C%22%3A%5C%22%3Cscript%3Ealert(document.domain)%3C%5C%5C%2Fscript%3E%5C%22%2C...%7D%2C%5C%22message%5C%22%3A%5C%22Transfer%20completed%20successfully%5C%22%7D%5CnGET%20%2Fapi%2Ftransactions%2F38%20-%3E%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A38%2C...%2C%5C%22description%5C%22%3A%5C%22%3Cscript%3Ealert(document.domain)%3C%5C%5C%2Fscript%3E%5C%22%2C...%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Password%20Hash%20and%20TOTP%20Secret%20Fields%20Exposed%20in%20Registration%20API%20Response%22%2C%22description%22%3A%22The%20registration%20endpoint%20at%20%2Fapi%2Fauth%2Fregister%20returns%20the%20full%20user%20object%20in%20its%20response%2C%20including%20the%20password_hash%20and%20totp_secret%20fields.%20These%20credential-related%20fields%20should%20be%20stripped%20server-side%20before%20serialization%20and%20never%20transmitted%20to%20the%20client.%20The%20exposed%20password_hash%20is%20a%2032-character%20hexadecimal%20string%20with%20no%20visible%20salt%2C%20consistent%20with%20an%20unsalted%20MD5%20hash%2C%20indicating%20weak%20server-side%20password%20hashing%20in%20addition%20to%20the%20unnecessary%20exposure.%22%2C%22impact%22%3A%22Returning%20password_hash%20and%20totp_secret%20to%20the%20client%20unnecessarily%20increases%20the%20attack%20surface%20for%20credential%20compromise%3A%20the%20value%20can%20be%20captured%20via%20logs%2C%20proxies%2C%20browser%20history%2Fcache%2C%20or%20any%20man-in-the-middle%20position%2C%20and%20%E2%80%94%20because%20the%20hash%20appears%20to%20be%20unsalted%20MD5%20%E2%80%94%20it%20would%20be%20trivially%20crackable%20offline%20if%20obtained.%20If%20this%20same%20serialization%20behavior%20is%20present%20on%20other%20endpoints%20that%20return%20other%20users'%20records%20(e.g.%20profile%20or%20admin%20endpoints)%2C%20an%20attacker%20could%20harvest%20password%20hashes%20at%20scale%20for%20offline%20cracking.%20In%20the%20confirmed%20case%2C%20only%20the%20requesting%20user's%20own%20hash%20was%20observed%20being%20disclosed.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20password_hash%20and%20totp_secret%20were%20observed%20directly%20in%20the%20registration%20API%20response%20for%20a%20freshly%20created%20test%20account.%20Broader%20impact%20(harvesting%20other%20users'%20hashes)%20would%20require%20an%20additional%20read%20primitive%20such%20as%20an%20IDOR%2C%20which%20was%20not%20demonstrated%20as%20part%20of%20this%20finding.%22%2C%22recommendation%22%3A%22Remove%20password_hash%2C%20totp_secret%2C%20and%20any%20other%20credential%2Fsecret%20fields%20from%20all%20API%20response%20payloads%20(registration%2C%20login%2C%20profile%2C%20admin)%20by%20enforcing%20an%20explicit%20allow-list%20serializer%2FDTO%20for%20user-facing%20objects%20rather%20than%20returning%20ORM%2Fdatabase%20objects%20directly.%20Replace%20the%20password%20hashing%20scheme%20with%20a%20strong%20adaptive%20algorithm%20(bcrypt%2C%20scrypt%2C%20or%20Argon2)%20using%20a%20unique%20per-user%20salt%2C%20and%20rehash%20existing%20credentials%20during%20the%20next%20password%20change%20or%20a%20forced%20reset.%20Audit%20all%20endpoints%20that%20return%20user%20objects%20for%20similar%20over-exposure%20of%20sensitive%20fields.%22%2C%22cvss_score%22%3A5.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22POST%20http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Fregister%20returned%20201%20with%20body%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A16%2C%5C%22email%5C%22%3A%5C%22aespa_4992abe4%40example.invalid%5C%22%2C...%2C%5C%22password_hash%5C%22%3A%5C%22ac3d2a6c23e811af791469aa6c772cd6%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BJWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D.%20The%20password_hash%20is%20a%2032-hex-char%20string%20consistent%20with%20unsalted%20MD5.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Sensitive%20data%20exposed%20in%20API%20response%22%2C%22description%22%3A%22The%20response%20contains%20field%20names%20commonly%20associated%20with%20secrets%2C%20hashes%2C%20tokens%2C%20debug%20state%2C%20or%20privileged%20metadata.%22%2C%22impact%22%3A%22Attackers%20can%20use%20leaked%20secrets%20or%20implementation%20details%20to%20compromise%20accounts%20or%20chain%20further%20attacks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20response%20analysis.%22%2C%22recommendation%22%3A%22Remove%20sensitive%20fields%20from%20client-facing%20responses%20and%20enforce%20response%20DTO%20allow-lists.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22REQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fhealth%5Cnuse_session%3A%20(default)%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A38%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20286%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.994%5Cncf-team%3A%202fbdb4b008000483be005c9400000001%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.3.31%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%5C%5C%2F2.4.58%20(Ubuntu)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22bankofed_app%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22Jj9XUzmBPzn8VcJEgzD9kC9koZTs1OV6XadreivDDrykIUuLimoQNqQnBdNE4Uv%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fhealth%5Cnuse_session%3A%20(default)%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A38%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20286%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.994%5Cncf-team%3A%202fbdb4b008000483be005c9400000001%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.3.31%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%5C%5C%2F2.4.58%20(Ubuntu)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22bankofed_app%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22Jj9XUzmBPzn8VcJEgzD9kC9koZTs1OV6XadreivDDrykIUuLimoQNqQnBdNE4Uv%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Sensitive%20data%20exposed%20in%20API%20response%22%2C%22description%22%3A%22The%20response%20contains%20field%20names%20commonly%20associated%20with%20secrets%2C%20hashes%2C%20tokens%2C%20debug%20state%2C%20or%20privileged%20metadata.%22%2C%22impact%22%3A%22Attackers%20can%20use%20leaked%20secrets%20or%20implementation%20details%20to%20compromise%20accounts%20or%20chain%20further%20attacks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20response%20analysis.%22%2C%22recommendation%22%3A%22Remove%20sensitive%20fields%20from%20client-facing%20responses%20and%20enforce%20response%20DTO%20allow-lists.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22REQUEST%3A%5CnREGISTER_ACCOUNT%20http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Fregister%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20201%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A16%2C%5C%22email%5C%22%3A%5C%22aespa_4992abe4%40example.invalid%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22last_name%5C%22%3A%5C%22User%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22ac3d2a6c23e811af791469aa6c772cd6%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%22%2C%22request_evidence%22%3A%22REGISTER_ACCOUNT%20http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Fregister%22%2C%22response_evidence%22%3A%22Status%3A%20201%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A16%2C%5C%22email%5C%22%3A%5C%22aespa_4992abe4%40example.invalid%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22last_name%5C%22%3A%5C%22User%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22ac3d2a6c23e811af791469aa6c772cd6%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Sensitive%20data%20exposed%20in%20API%20response%22%2C%22description%22%3A%22The%20response%20contains%20field%20names%20commonly%20associated%20with%20secrets%2C%20hashes%2C%20tokens%2C%20debug%20state%2C%20or%20privileged%20metadata.%22%2C%22impact%22%3A%22Attackers%20can%20use%20leaked%20secrets%20or%20implementation%20details%20to%20compromise%20accounts%20or%20chain%20further%20attacks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20response%20analysis.%22%2C%22recommendation%22%3A%22Remove%20sensitive%20fields%20from%20client-facing%20responses%20and%20enforce%20response%20DTO%20allow-lists.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22REQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%5Cnuse_session%3A%20victim1%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A20%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20335%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D12.659%5Cncf-team%3A%202fbdb7ed4f000483be0a45a400000001%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A16%2C%5C%22email%5C%22%3A%5C%22aespa_4992abe4%40example.invalid%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22last_name%5C%22%3A%5C%22User%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22ac3d2a6c23e811af791469aa6c772cd6%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%5Cnuse_session%3A%20victim1%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A20%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20335%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D12.659%5Cncf-team%3A%202fbdb7ed4f000483be0a45a400000001%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A16%2C%5C%22email%5C%22%3A%5C%22aespa_4992abe4%40example.invalid%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22last_name%5C%22%3A%5C%22User%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22ac3d2a6c23e811af791469aa6c772cd6%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fapp.js%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fapp.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Mon%2C%2016%20Feb%202026%2008%3A52%3A02%20GMT%5Cnetag%3A%20%5C%22806-64aed11869080-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%20728%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D6.604%5Cncf-team%3A%202fbdb47e76000483beffe63400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20App%20Bootstrap%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.App%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%20%20var%20Router%20%3D%20BankOfEdAdmin.Router%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20init()%20%7B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Flogin'%2C%20function%20()%20%7B%20BankOfEdAdmin.AuthPage.show()%3B%20%7D%2C%20%7B%20auth%3A%20false%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Fcustomers'%2C%20function%20()%20%7B%20BankOfEdAdmin.CustomersPage.show()%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Fcustomers%2F%3Aid'%2C%20function%20(params)%20%7B%20BankOfEdAdmin.CustomersPage.showDetail(params)%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Faccounts'%2C%20function%20()%20%7B%20BankOfEdAdmin.AccountsPage.show()%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Ffx-rates'%2C%20function%20()%20%7B%20BankOfEdAdmin.FxRatesPage.show()%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Fsystem'%2C%20function%20()%20%7B%20BankOfEdAdmin.SystemPage.show()%3B%20%7D)%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20if%20(Api.isLoggedIn())%20updateSidebar()%3B%5Cr%5Cn%20%20%20%20Router.start()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20updateSidebar()%20%7B%5Cr%5Cn%20%20%20%20var%20admin%20%3D%20Api.getAdmin()%3B%5Cr%5Cn%20%20%20%20if%20(!admin)%20return%3B%5Cr%5Cn%20%20%20%20var%20avatar%20%3D%20U.%24('sidebar-avatar')%3B%5Cr%5Cn%20%20%20%20var%20name%20%3D%20U.%24('sidebar-admin-name')%3B%5Cr%5Cn%20%20%20%20if%20(avatar)%20avatar.textContent%20%3D%20(admin.username%20%7C%7C%20'A')%5B0%5D.toUpperCase()%3B%5Cr%5Cn%20%20%20%20if%20(name)%20name.textContent%20%3D%20admin.username%20%7C%7C%20'Admin'%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20toggleSidebar()%20%7B%5Cr%5Cn%20%20%20%20var%20sidebar%20%3D%20U.%24('sidebar')%3B%5Cr%5Cn%20%20%20%20var%20overlay%20%3D%20U.%24('sidebar-overlay')%3B%5Cr%5Cn%20%20%20%20if%20(sidebar.classList.contains('-translate-x-full'))%20%7B%5Cr%5Cn%20%20%20%20%20%20sidebar.classList.remove('-translate-x-full')%3B%5Cr%5Cn%20%20%20%20%20%20overlay.classList.remove('hidden')%3B%5Cr%5Cn%20%20%20%20%7D%20else%20%7B%5Cr%5Cn%20%20%20%20%20%20sidebar.classList.add('-translate-x-full')%3B%5Cr%5Cn%20%20%20%20%20%20overlay.classList.add('hidden')%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20logout()%20%7B%5Cr%5Cn%20%20%20%20Api.logout().catch(function%20()%20%7B%7D).finally(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20Api.clearToken()%3B%20Api.clearAdmin()%3B%5Cr%5Cn%20%20%20%20%20%20U.toast('Signed%20out.'%2C%20'info')%3B%5Cr%5Cn%20%20%20%20%20%20window.location.hash%20%3D%20'%23%2Flogin'%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20if%20(document.readyState%20%3D%3D%3D%20'loading')%20document.addEventListener('DOMContentLoaded'%2C%20init)%3B%5Cr%5Cn%20%20else%20init()%3B%5Cr%5Cn%5Cr%5Cn%20%20return%20%7B%20init%3A%20init%2C%20updateSidebar%3A%20updateSidebar%2C%20to%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fapp.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Mon%2C%2016%20Feb%202026%2008%3A52%3A02%20GMT%5Cnetag%3A%20%5C%22806-64aed11869080-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%20728%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D6.604%5Cncf-team%3A%202fbdb47e76000483beffe63400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20App%20Bootstrap%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.App%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%20%20var%20Router%20%3D%20BankOfEdAdmin.Router%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20init()%20%7B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Flogin'%2C%20function%20()%20%7B%20BankOfEdAdmin.AuthPage.show()%3B%20%7D%2C%20%7B%20auth%3A%20false%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Fcustomers'%2C%20function%20()%20%7B%20BankOfEdAdmin.CustomersPage.show()%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Fcustomers%2F%3Aid'%2C%20function%20(params)%20%7B%20BankOfEdAdmin.CustomersPage.showDetail(params)%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Faccounts'%2C%20function%20()%20%7B%20BankOfEdAdmin.AccountsPage.show()%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Ffx-rates'%2C%20function%20()%20%7B%20BankOfEdAdmin.FxRatesPage.show()%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20Router.addRoute('%2Fsystem'%2C%20function%20()%20%7B%20BankOfEdAdmin.SystemPage.show()%3B%20%7D)%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20if%20(Api.isLoggedIn())%20updateSidebar()%3B%5Cr%5Cn%20%20%20%20Router.start()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20updateSidebar()%20%7B%5Cr%5Cn%20%20%20%20var%20admin%20%3D%20Api.getAdmin()%3B%5Cr%5Cn%20%20%20%20if%20(!admin)%20return%3B%5Cr%5Cn%20%20%20%20var%20avatar%20%3D%20U.%24('sidebar-avatar')%3B%5Cr%5Cn%20%20%20%20var%20name%20%3D%20U.%24('sidebar-admin-name')%3B%5Cr%5Cn%20%20%20%20if%20(avatar)%20avatar.textContent%20%3D%20(admin.username%20%7C%7C%20'A')%5B0%5D.toUpperCase()%3B%5Cr%5Cn%20%20%20%20if%20(name)%20name.textContent%20%3D%20admin.username%20%7C%7C%20'Admin'%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20toggleSidebar()%20%7B%5Cr%5Cn%20%20%20%20var%20sidebar%20%3D%20U.%24('sidebar')%3B%5Cr%5Cn%20%20%20%20var%20overlay%20%3D%20U.%24('sidebar-overlay')%3B%5Cr%5Cn%20%20%20%20if%20(sidebar.classList.contains('-translate-x-full'))%20%7B%5Cr%5Cn%20%20%20%20%20%20sidebar.classList.remove('-translate-x-full')%3B%5Cr%5Cn%20%20%20%20%20%20overlay.classList.remove('hidden')%3B%5Cr%5Cn%20%20%20%20%7D%20else%20%7B%5Cr%5Cn%20%20%20%20%20%20sidebar.classList.add('-translate-x-full')%3B%5Cr%5Cn%20%20%20%20%20%20overlay.classList.add('hidden')%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20logout()%20%7B%5Cr%5Cn%20%20%20%20Api.logout().catch(function%20()%20%7B%7D).finally(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20Api.clearToken()%3B%20Api.clearAdmin()%3B%5Cr%5Cn%20%20%20%20%20%20U.toast('Signed%20out.'%2C%20'info')%3B%5Cr%5Cn%20%20%20%20%20%20window.location.hash%20%3D%20'%23%2Flogin'%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20if%20(document.readyState%20%3D%3D%3D%20'loading')%20document.addEventListener('DOMContentLoaded'%2C%20init)%3B%5Cr%5Cn%20%20else%20init()%3B%5Cr%5Cn%5Cr%5Cn%20%20return%20%7B%20init%3A%20init%2C%20updateSidebar%3A%20updateSidebar%2C%20to%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Faccounts.js%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Faccounts.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%2218a2-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%202048%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.805%5Cncf-team%3A%202fbdb47ecb000483beffe6f400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Accounts%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.AccountsPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%20%20var%20currentPage%20%3D%201%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEdAdmin.Router.showPage('accounts'%2C%20'accounts')%3B%5Cr%5Cn%20%20%20%20currentPage%20%3D%201%3B%5Cr%5Cn%20%20%20%20loadAccounts()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20loadAccounts()%20%7B%5Cr%5Cn%20%20%20%20Api.getAccounts(%7B%20page%3A%20currentPage%2C%20per_page%3A%2020%20%7D).then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20renderTable(res.data.accounts%20%7C%7C%20%5B%5D)%3B%5Cr%5Cn%20%20%20%20%20%20renderPagination(res.data.pagination%20%7C%7C%20%7B%7D)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20accounts.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20renderTable(accounts)%20%7B%5Cr%5Cn%20%20%20%20var%20container%20%3D%20U.%24('accounts-table')%3B%5Cr%5Cn%20%20%20%20if%20(!accounts.length)%20%7B%5Cr%5Cn%20%20%20%20%20%20container.innerHTML%20%3D%20'%3Cdiv%20class%3D%5C%22p-8%20text-center%20text-dark-400%5C%22%3ENo%20accounts%20found%3C%2Fdiv%3E'%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20html%20%3D%20'%3Cdiv%20class%3D%5C%22overflow-x-auto%5C%22%3E%3Ctable%20class%3D%5C%22w-full%20text-sm%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cthead%3E%3Ctr%20class%3D%5C%22text-left%20text-xs%20text-dark-400%20uppercase%20tracking-wide%20border-b%20border-dark-100%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EID%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EOwner%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EAccount%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EType%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3EBalance%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3EActions%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3C%2Ftr%3E%3C%2Fthead%3E%3Ctbody%3E'%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20accounts.forEach(function%20(a)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20badgeCls%20%3D%20a.account_type%20%3D%3D%3D%20'loan'%20%3F%20'badge-loan'%20%3A%20'badge-transaction'%3B%5Cr%5Cn%20%20%20%20%20%20var%20balColor%20%3D%20parseFloat(a.balance)%20%3E%3D%200%20%3F%20'text-dark-900'%20%3A%20'text-red-600'%3B%5Cr%5Cn%20%20%20%20%20%20html%20%2B%3D%20'%3Ctr%20class%3D%5C%22tx-row%20border-b%20border-dark-50%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-dark-400%20font-mono%20text-xs%5C%22%3E%23'%20%2B%20a.id%20%2B%20'%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%5C%22%3E%3Cspan%20class%3D%5C%22font-medium%20text-dark-900%5C%22%3E'%20%2B%20U.escapeHtml((a.owner_first_name%20%7C%7C%20'')%20%2B%20'%20'%20%2B%20(a.owner_last_name%20%7C%7C%20''))%20%2B%20'%3C%2Fspan%3E%3Cbr%3E%3Cspan%20class%3D%5C%22text-xs%20text-dark-400%5C%22%3E'%20%2B%20U.escapeHtml(a.owner_email)%20%2B%20'%3C%2Fspan%3E%3C%2Ftd%3E'%20%2B%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Faccounts.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%2218a2-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%202048%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.805%5Cncf-team%3A%202fbdb47ecb000483beffe6f400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Accounts%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.AccountsPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%20%20var%20currentPage%20%3D%201%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEdAdmin.Router.showPage('accounts'%2C%20'accounts')%3B%5Cr%5Cn%20%20%20%20currentPage%20%3D%201%3B%5Cr%5Cn%20%20%20%20loadAccounts()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20loadAccounts()%20%7B%5Cr%5Cn%20%20%20%20Api.getAccounts(%7B%20page%3A%20currentPage%2C%20per_page%3A%2020%20%7D).then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20renderTable(res.data.accounts%20%7C%7C%20%5B%5D)%3B%5Cr%5Cn%20%20%20%20%20%20renderPagination(res.data.pagination%20%7C%7C%20%7B%7D)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20accounts.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20renderTable(accounts)%20%7B%5Cr%5Cn%20%20%20%20var%20container%20%3D%20U.%24('accounts-table')%3B%5Cr%5Cn%20%20%20%20if%20(!accounts.length)%20%7B%5Cr%5Cn%20%20%20%20%20%20container.innerHTML%20%3D%20'%3Cdiv%20class%3D%5C%22p-8%20text-center%20text-dark-400%5C%22%3ENo%20accounts%20found%3C%2Fdiv%3E'%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20html%20%3D%20'%3Cdiv%20class%3D%5C%22overflow-x-auto%5C%22%3E%3Ctable%20class%3D%5C%22w-full%20text-sm%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cthead%3E%3Ctr%20class%3D%5C%22text-left%20text-xs%20text-dark-400%20uppercase%20tracking-wide%20border-b%20border-dark-100%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EID%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EOwner%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EAccount%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EType%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3EBalance%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3EActions%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3C%2Ftr%3E%3C%2Fthead%3E%3Ctbody%3E'%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20accounts.forEach(function%20(a)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20badgeCls%20%3D%20a.account_type%20%3D%3D%3D%20'loan'%20%3F%20'badge-loan'%20%3A%20'badge-transaction'%3B%5Cr%5Cn%20%20%20%20%20%20var%20balColor%20%3D%20parseFloat(a.balance)%20%3E%3D%200%20%3F%20'text-dark-900'%20%3A%20'text-red-600'%3B%5Cr%5Cn%20%20%20%20%20%20html%20%2B%3D%20'%3Ctr%20class%3D%5C%22tx-row%20border-b%20border-dark-50%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-dark-400%20font-mono%20text-xs%5C%22%3E%23'%20%2B%20a.id%20%2B%20'%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%5C%22%3E%3Cspan%20class%3D%5C%22font-medium%20text-dark-900%5C%22%3E'%20%2B%20U.escapeHtml((a.owner_first_name%20%7C%7C%20'')%20%2B%20'%20'%20%2B%20(a.owner_last_name%20%7C%7C%20''))%20%2B%20'%3C%2Fspan%3E%3Cbr%3E%3Cspan%20class%3D%5C%22text-xs%20text-dark-400%5C%22%3E'%20%2B%20U.escapeHtml(a.owner_email)%20%2B%20'%3C%2Fspan%3E%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fauth.js%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fauth.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%223de-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%20484%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D8.032%5Cncf-team%3A%202fbdb47f20000483beffe87400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Auth%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.AuthPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%20BankOfEdAdmin.Router.showPage('auth')%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20handleLogin(e)%20%7B%5Cr%5Cn%20%20%20%20e.preventDefault()%3B%5Cr%5Cn%20%20%20%20var%20form%20%3D%20e.target%3B%5Cr%5Cn%20%20%20%20var%20btn%20%3D%20form.querySelector('button%5Btype%3D%5C%22submit%5C%22%5D')%3B%5Cr%5Cn%20%20%20%20var%20data%20%3D%20U.getFormData(form)%3B%5Cr%5Cn%20%20%20%20U.showErrors('login-errors'%2C%20null)%3B%5Cr%5Cn%20%20%20%20U.setButtonLoading(btn%2C%20true)%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20Api.login(data).then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20Api.setToken(res.data.token)%3B%5Cr%5Cn%20%20%20%20%20%20Api.setAdmin(res.data.admin)%3B%5Cr%5Cn%20%20%20%20%20%20U.toast('Welcome%2C%20'%20%2B%20res.data.admin.username%20%2B%20'!'%2C%20'success')%3B%5Cr%5Cn%20%20%20%20%20%20window.location.hash%20%3D%20'%23%2Fcustomers'%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20(err)%20%7B%5Cr%5Cn%20%20%20%20%20%20U.showErrors('login-errors'%2C%20err)%3B%5Cr%5Cn%20%20%20%20%7D).finally(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.setButtonLoading(btn%2C%20false)%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20return%20%7B%20show%3A%20show%2C%20handleLogin%3A%20handleLogin%20%7D%3B%5Cr%5Cn%7D)()%3B%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fauth.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%223de-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%20484%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D8.032%5Cncf-team%3A%202fbdb47f20000483beffe87400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Auth%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.AuthPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%20BankOfEdAdmin.Router.showPage('auth')%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20handleLogin(e)%20%7B%5Cr%5Cn%20%20%20%20e.preventDefault()%3B%5Cr%5Cn%20%20%20%20var%20form%20%3D%20e.target%3B%5Cr%5Cn%20%20%20%20var%20btn%20%3D%20form.querySelector('button%5Btype%3D%5C%22submit%5C%22%5D')%3B%5Cr%5Cn%20%20%20%20var%20data%20%3D%20U.getFormData(form)%3B%5Cr%5Cn%20%20%20%20U.showErrors('login-errors'%2C%20null)%3B%5Cr%5Cn%20%20%20%20U.setButtonLoading(btn%2C%20true)%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20Api.login(data).then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20Api.setToken(res.data.token)%3B%5Cr%5Cn%20%20%20%20%20%20Api.setAdmin(res.data.admin)%3B%5Cr%5Cn%20%20%20%20%20%20U.toast('Welcome%2C%20'%20%2B%20res.data.admin.username%20%2B%20'!'%2C%20'success')%3B%5Cr%5Cn%20%20%20%20%20%20window.location.hash%20%3D%20'%23%2Fcustomers'%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20(err)%20%7B%5Cr%5Cn%20%20%20%20%20%20U.showErrors('login-errors'%2C%20err)%3B%5Cr%5Cn%20%20%20%20%7D).finally(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.setButtonLoading(btn%2C%20false)%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20return%20%7B%20show%3A%20show%2C%20handleLogin%3A%20handleLogin%20%7D%3B%5Cr%5Cn%7D)()%3B%5Cr%5Cn%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fcustomers.js%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fcustomers.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%223d8c-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%203617%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D8.748%5Cncf-team%3A%202fbdb47f77000483beffea0400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Customers%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.CustomersPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%20%20var%20currentPage%20%3D%201%3B%5Cr%5Cn%20%20var%20searchTerm%20%3D%20''%3B%5Cr%5Cn%20%20var%20searchTimer%20%3D%20null%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEdAdmin.Router.showPage('customers'%2C%20'customers')%3B%5Cr%5Cn%20%20%20%20currentPage%20%3D%201%3B%5Cr%5Cn%20%20%20%20searchTerm%20%3D%20''%3B%5Cr%5Cn%20%20%20%20var%20searchInput%20%3D%20U.%24('customer-search')%3B%5Cr%5Cn%20%20%20%20if%20(searchInput)%20searchInput.value%20%3D%20''%3B%5Cr%5Cn%20%20%20%20loadCustomers()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20handleSearch(e)%20%7B%5Cr%5Cn%20%20%20%20clearTimeout(searchTimer)%3B%5Cr%5Cn%20%20%20%20searchTimer%20%3D%20setTimeout(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20searchTerm%20%3D%20e.target.value%3B%5Cr%5Cn%20%20%20%20%20%20currentPage%20%3D%201%3B%5Cr%5Cn%20%20%20%20%20%20loadCustomers()%3B%5Cr%5Cn%20%20%20%20%7D%2C%20300)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20loadCustomers()%20%7B%5Cr%5Cn%20%20%20%20Api.getCustomers(%7B%20page%3A%20currentPage%2C%20per_page%3A%2015%2C%20search%3A%20searchTerm%20%7D).then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20renderTable(res.data.customers%20%7C%7C%20%5B%5D)%3B%5Cr%5Cn%20%20%20%20%20%20renderPagination(res.data.pagination%20%7C%7C%20%7B%7D)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20customers.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20renderTable(customers)%20%7B%5Cr%5Cn%20%20%20%20var%20container%20%3D%20U.%24('customers-table')%3B%5Cr%5Cn%20%20%20%20if%20(!customers.length)%20%7B%5Cr%5Cn%20%20%20%20%20%20container.innerHTML%20%3D%20'%3Cdiv%20class%3D%5C%22p-8%20text-center%20text-dark-400%5C%22%3ENo%20customers%20found%3C%2Fdiv%3E'%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20html%20%3D%20'%3Cdiv%20class%3D%5C%22overflow-x-auto%5C%22%3E%3Ctable%20class%3D%5C%22w-full%20text-sm%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cthead%3E%3Ctr%20class%3D%5C%22text-left%20text-xs%20text-dark-400%20uppercase%20tracking-wide%20border-b%20border-dark-100%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EID%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EName%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EEmail%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EAccounts%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3E2FA%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EJoined%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3EActions%3C%2Fth%3E%3C%2Ftr%3E%3C%2Fthead%3E%3Ctbody%3E'%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20customers.forEach(function%20(c)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20twofaBadge%20%3D%20c.totp_enabled%5Cr%5Cn%20%20%20%20%20%20%20%20%3F%20'%3Cspan%20class%3D%5C%22inline-flex%20items-center%20gap-1%20text-green-600%20text-xs%20font-semibold%5C%22%3E%3Csvg%20class%3D%5C%22w-3.5%20h%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fcustomers.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%223d8c-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%203617%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D8.748%5Cncf-team%3A%202fbdb47f77000483beffea0400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Customers%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.CustomersPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%20%20var%20currentPage%20%3D%201%3B%5Cr%5Cn%20%20var%20searchTerm%20%3D%20''%3B%5Cr%5Cn%20%20var%20searchTimer%20%3D%20null%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEdAdmin.Router.showPage('customers'%2C%20'customers')%3B%5Cr%5Cn%20%20%20%20currentPage%20%3D%201%3B%5Cr%5Cn%20%20%20%20searchTerm%20%3D%20''%3B%5Cr%5Cn%20%20%20%20var%20searchInput%20%3D%20U.%24('customer-search')%3B%5Cr%5Cn%20%20%20%20if%20(searchInput)%20searchInput.value%20%3D%20''%3B%5Cr%5Cn%20%20%20%20loadCustomers()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20handleSearch(e)%20%7B%5Cr%5Cn%20%20%20%20clearTimeout(searchTimer)%3B%5Cr%5Cn%20%20%20%20searchTimer%20%3D%20setTimeout(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20searchTerm%20%3D%20e.target.value%3B%5Cr%5Cn%20%20%20%20%20%20currentPage%20%3D%201%3B%5Cr%5Cn%20%20%20%20%20%20loadCustomers()%3B%5Cr%5Cn%20%20%20%20%7D%2C%20300)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20loadCustomers()%20%7B%5Cr%5Cn%20%20%20%20Api.getCustomers(%7B%20page%3A%20currentPage%2C%20per_page%3A%2015%2C%20search%3A%20searchTerm%20%7D).then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20renderTable(res.data.customers%20%7C%7C%20%5B%5D)%3B%5Cr%5Cn%20%20%20%20%20%20renderPagination(res.data.pagination%20%7C%7C%20%7B%7D)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20customers.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20renderTable(customers)%20%7B%5Cr%5Cn%20%20%20%20var%20container%20%3D%20U.%24('customers-table')%3B%5Cr%5Cn%20%20%20%20if%20(!customers.length)%20%7B%5Cr%5Cn%20%20%20%20%20%20container.innerHTML%20%3D%20'%3Cdiv%20class%3D%5C%22p-8%20text-center%20text-dark-400%5C%22%3ENo%20customers%20found%3C%2Fdiv%3E'%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20html%20%3D%20'%3Cdiv%20class%3D%5C%22overflow-x-auto%5C%22%3E%3Ctable%20class%3D%5C%22w-full%20text-sm%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cthead%3E%3Ctr%20class%3D%5C%22text-left%20text-xs%20text-dark-400%20uppercase%20tracking-wide%20border-b%20border-dark-100%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EID%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EName%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EEmail%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EAccounts%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3E2FA%3C%2Fth%3E%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EJoined%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3EActions%3C%2Fth%3E%3C%2Ftr%3E%3C%2Fthead%3E%3Ctbody%3E'%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20customers.forEach(function%20(c)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20twofaBadge%20%3D%20c.totp_enabled%5Cr%5Cn%20%20%20%20%20%20%20%20%3F%20'%3Cspan%20class%3D%5C%22inline-flex%20items-center%20gap-1%20text-green-600%20text-xs%20font-semibold%5C%22%3E%3Csvg%20class%3D%5C%22w-3.5%20h%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Ffx-rates.js%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Ffx-rates.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Mon%2C%2016%20Feb%202026%2008%3A49%3A41%20GMT%5Cnetag%3A%20%5C%222876-64aed091f1340-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%202247%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.332%5Cncf-team%3A%202fbdb47fce000483beffeb0400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20FX%20Rates%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.FxRatesPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEdAdmin.Router.showPage('fx-rates'%2C%20'fx-rates')%3B%5Cr%5Cn%20%20%20%20loadRates()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20loadRates()%20%7B%5Cr%5Cn%20%20%20%20Api.getFxRates().then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20rates%20%3D%20Array.isArray(res.data)%20%3F%20res.data%20%3A%20%5B%5D%3B%5Cr%5Cn%20%20%20%20%20%20renderTable(rates)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20FX%20rates.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20renderTable(rates)%20%7B%5Cr%5Cn%20%20%20%20var%20container%20%3D%20U.%24('fx-rates-table')%3B%5Cr%5Cn%20%20%20%20if%20(!rates.length)%20%7B%5Cr%5Cn%20%20%20%20%20%20container.innerHTML%20%3D%20'%3Cdiv%20class%3D%5C%22p-8%20text-center%20text-dark-400%5C%22%3ENo%20FX%20rates%20configured%20yet.%3C%2Fdiv%3E'%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20html%20%3D%20'%3Cdiv%20class%3D%5C%22table-scroll%5C%22%3E%3Ctable%20class%3D%5C%22w-full%20text-sm%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cthead%3E%3Ctr%20class%3D%5C%22text-left%20text-xs%20text-dark-400%20uppercase%20tracking-wide%20border-b%20border-dark-100%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3ECurrency%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EName%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3ERate%20to%20USD%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EUpdated%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3EActions%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3C%2Ftr%3E%3C%2Fthead%3E%3Ctbody%3E'%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20rates.forEach(function%20(rate)%20%7B%5Cr%5Cn%20%20%20%20%20%20html%20%2B%3D%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Ctr%20class%3D%5C%22border-b%20border-dark-50%20hover%3Abg-dark-50%2F50%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%5C%22%3E%3Cspan%20class%3D%5C%22font-mono%20font-semibold%20text-dark-900%5C%22%3E'%20%2B%20U.escapeHtml(rate.currency_code)%20%2B%20'%3C%2Fspan%3E%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-dark-600%5C%22%3E'%20%2B%20U.escapeHtml(rate.currency_name)%20%2B%20'%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-right%20font-mono%20text-dark-900%5C%22%3E'%20%2B%20Number(rate.rate_to_usd).toFixed(8)%20%2B%20'%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-dark-400%20text-xs%5C%22%3E'%20%2B%20U.formatDateTime(rate.updated_at)%20%2B%20'%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-right%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Ffx-rates.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A25%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Mon%2C%2016%20Feb%202026%2008%3A49%3A41%20GMT%5Cnetag%3A%20%5C%222876-64aed091f1340-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%202247%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.332%5Cncf-team%3A%202fbdb47fce000483beffeb0400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20FX%20Rates%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.FxRatesPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEdAdmin.Router.showPage('fx-rates'%2C%20'fx-rates')%3B%5Cr%5Cn%20%20%20%20loadRates()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20loadRates()%20%7B%5Cr%5Cn%20%20%20%20Api.getFxRates().then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20rates%20%3D%20Array.isArray(res.data)%20%3F%20res.data%20%3A%20%5B%5D%3B%5Cr%5Cn%20%20%20%20%20%20renderTable(rates)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20FX%20rates.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20renderTable(rates)%20%7B%5Cr%5Cn%20%20%20%20var%20container%20%3D%20U.%24('fx-rates-table')%3B%5Cr%5Cn%20%20%20%20if%20(!rates.length)%20%7B%5Cr%5Cn%20%20%20%20%20%20container.innerHTML%20%3D%20'%3Cdiv%20class%3D%5C%22p-8%20text-center%20text-dark-400%5C%22%3ENo%20FX%20rates%20configured%20yet.%3C%2Fdiv%3E'%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20html%20%3D%20'%3Cdiv%20class%3D%5C%22table-scroll%5C%22%3E%3Ctable%20class%3D%5C%22w-full%20text-sm%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3Cthead%3E%3Ctr%20class%3D%5C%22text-left%20text-xs%20text-dark-400%20uppercase%20tracking-wide%20border-b%20border-dark-100%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3ECurrency%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EName%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3ERate%20to%20USD%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%5C%22%3EUpdated%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Cth%20class%3D%5C%22px-6%20py-3%20text-right%5C%22%3EActions%3C%2Fth%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20'%3C%2Ftr%3E%3C%2Fthead%3E%3Ctbody%3E'%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20rates.forEach(function%20(rate)%20%7B%5Cr%5Cn%20%20%20%20%20%20html%20%2B%3D%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Ctr%20class%3D%5C%22border-b%20border-dark-50%20hover%3Abg-dark-50%2F50%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%5C%22%3E%3Cspan%20class%3D%5C%22font-mono%20font-semibold%20text-dark-900%5C%22%3E'%20%2B%20U.escapeHtml(rate.currency_code)%20%2B%20'%3C%2Fspan%3E%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-dark-600%5C%22%3E'%20%2B%20U.escapeHtml(rate.currency_name)%20%2B%20'%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-right%20font-mono%20text-dark-900%5C%22%3E'%20%2B%20Number(rate.rate_to_usd).toFixed(8)%20%2B%20'%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-dark-400%20text-xs%5C%22%3E'%20%2B%20U.formatDateTime(rate.updated_at)%20%2B%20'%3C%2Ftd%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Ctd%20class%3D%5C%22px-6%20py-3.5%20text-right%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fsystem.js%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fsystem.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A26%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%223fc-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%20449%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D6.566%5Cncf-team%3A%202fbdb48024000483beffec3400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20System%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.SystemPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEdAdmin.Router.showPage('system'%2C%20'system')%3B%5Cr%5Cn%20%20%20%20var%20input%20%3D%20U.%24('reset-confirm-input')%3B%5Cr%5Cn%20%20%20%20if%20(input)%20input.value%20%3D%20''%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20handleReset()%20%7B%5Cr%5Cn%20%20%20%20var%20input%20%3D%20U.%24('reset-confirm-input')%3B%5Cr%5Cn%20%20%20%20if%20(!input%20%7C%7C%20input.value%20!%3D%3D%20'RESET')%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Please%20type%20RESET%20to%20confirm.'%2C%20'warning')%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20btn%20%3D%20U.%24('reset-btn')%3B%5Cr%5Cn%20%20%20%20U.setButtonLoading(btn%2C%20true)%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20Api.resetDatabase().then(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20input.value%20%3D%20''%3B%5Cr%5Cn%20%20%20%20%20%20U.toast('Database%20reset%20successfully!'%2C%20'success')%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20(err)%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast(err.message%20%7C%7C%20'Reset%20failed.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D).finally(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.setButtonLoading(btn%2C%20false)%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20return%20%7B%20show%3A%20show%2C%20handleReset%3A%20handleReset%20%7D%3B%5Cr%5Cn%7D)()%3B%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fpages%2Fsystem.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A26%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%223fc-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%20449%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D6.566%5Cncf-team%3A%202fbdb48024000483beffec3400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20System%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.SystemPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEdAdmin.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEdAdmin.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEdAdmin.Router.showPage('system'%2C%20'system')%3B%5Cr%5Cn%20%20%20%20var%20input%20%3D%20U.%24('reset-confirm-input')%3B%5Cr%5Cn%20%20%20%20if%20(input)%20input.value%20%3D%20''%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20handleReset()%20%7B%5Cr%5Cn%20%20%20%20var%20input%20%3D%20U.%24('reset-confirm-input')%3B%5Cr%5Cn%20%20%20%20if%20(!input%20%7C%7C%20input.value%20!%3D%3D%20'RESET')%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Please%20type%20RESET%20to%20confirm.'%2C%20'warning')%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20btn%20%3D%20U.%24('reset-btn')%3B%5Cr%5Cn%20%20%20%20U.setButtonLoading(btn%2C%20true)%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20Api.resetDatabase().then(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20input.value%20%3D%20''%3B%5Cr%5Cn%20%20%20%20%20%20U.toast('Database%20reset%20successfully!'%2C%20'success')%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20(err)%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast(err.message%20%7C%7C%20'Reset%20failed.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D).finally(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.setButtonLoading(btn%2C%20false)%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20return%20%7B%20show%3A%20show%2C%20handleReset%3A%20handleReset%20%7D%3B%5Cr%5Cn%7D)()%3B%5Cr%5Cn%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Frouter.js%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Frouter.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A26%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%22927-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%20901%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.635%5Cncf-team%3A%202fbdb48077000483beffed2400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Router%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.Router%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20routes%20%3D%20%5B%5D%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20addRoute(pattern%2C%20handler%2C%20options)%20%7B%5Cr%5Cn%20%20%20%20options%20%3D%20options%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%20%20%20%20var%20keys%20%3D%20%5B%5D%3B%5Cr%5Cn%20%20%20%20var%20re%20%3D%20pattern.replace(%2F%3A(%5B%5E%2F%5D%2B)%2Fg%2C%20function%20(_%2C%20key)%20%7B%20keys.push(key)%3B%20return%20'(%5B%5E%2F%5D%2B)'%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20routes.push(%7B%20regex%3A%20new%20RegExp('%5E'%20%2B%20re%20%2B%20'%24')%2C%20keys%3A%20keys%2C%20handler%3A%20handler%2C%20auth%3A%20options.auth%20!%3D%3D%20false%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20navigate(hash)%20%7B%20window.location.hash%20%3D%20hash%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20resolve()%20%7B%5Cr%5Cn%20%20%20%20var%20hash%20%3D%20window.location.hash.slice(1)%20%7C%7C%20'%2Flogin'%3B%5Cr%5Cn%20%20%20%20for%20(var%20i%20%3D%200%3B%20i%20%3C%20routes.length%3B%20i%2B%2B)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20route%20%3D%20routes%5Bi%5D%3B%5Cr%5Cn%20%20%20%20%20%20var%20match%20%3D%20hash.match(route.regex)%3B%5Cr%5Cn%20%20%20%20%20%20if%20(match)%20%7B%5Cr%5Cn%20%20%20%20%20%20%20%20if%20(route.auth%20%26%26%20!BankOfEdAdmin.Api.isLoggedIn())%20%7B%20navigate('%23%2Flogin')%3B%20return%3B%20%7D%5Cr%5Cn%20%20%20%20%20%20%20%20if%20(!route.auth%20%26%26%20BankOfEdAdmin.Api.isLoggedIn()%20%26%26%20hash%20%3D%3D%3D%20'%2Flogin')%20%7B%20navigate('%23%2Fcustomers')%3B%20return%3B%20%7D%5Cr%5Cn%20%20%20%20%20%20%20%20var%20params%20%3D%20%7B%7D%3B%5Cr%5Cn%20%20%20%20%20%20%20%20route.keys.forEach(function%20(key%2C%20idx)%20%7B%20params%5Bkey%5D%20%3D%20match%5Bidx%20%2B%201%5D%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20%20%20%20%20route.handler(params)%3B%5Cr%5Cn%20%20%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%20%20%7D%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%20%20%20%20navigate(BankOfEdAdmin.Api.isLoggedIn()%20%3F%20'%23%2Fcustomers'%20%3A%20'%23%2Flogin')%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20showPage(pageId%2C%20navKey)%20%7B%5Cr%5Cn%20%20%20%20document.querySelectorAll('%5Bid%5E%3D%5C%22page-%5C%22%5D').forEach(function%20(p)%20%7B%20p.classList.add('hidden')%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20var%20page%20%3D%20document.getElementById('page-'%20%2B%20pageId)%3B%5Cr%5Cn%20%20%20%20if%20(page)%20%7B%20page.classList.remove('hidden')%3B%20page.classList.add('page-fade-in')%3B%20setTimeout(function%20()%20%7B%20page.classList.remove('page-fade-in')%3B%20%7D%2C%20250)%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20viewAuth%20%3D%20document.getElementById('view-auth')%3B%5Cr%5Cn%20%20%20%20var%20appShell%20%3D%20document.getElementById('app-shell')%3B%5Cr%5Cn%20%20%20%20if%20(pageId%20%3D%3D%3D%20'auth')%20%7B%20viewAuth.classList.remove('hidden')%3B%20appShell.classList.add('hidden')%3B%20%7D%5Cr%5Cn%20%20%20%20else%20%7B%20viewAuth.classList.add('hidden')%3B%20appShell.classList.remove('hidden')%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20if%20(navKey)%20%7B%5Cr%5Cn%20%20%20%20%20%20document.querySelectorAll('.nav-link').forEach(function%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Frouter.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A26%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%22927-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%20901%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.635%5Cncf-team%3A%202fbdb48077000483beffed2400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Router%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.Router%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20routes%20%3D%20%5B%5D%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20addRoute(pattern%2C%20handler%2C%20options)%20%7B%5Cr%5Cn%20%20%20%20options%20%3D%20options%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%20%20%20%20var%20keys%20%3D%20%5B%5D%3B%5Cr%5Cn%20%20%20%20var%20re%20%3D%20pattern.replace(%2F%3A(%5B%5E%2F%5D%2B)%2Fg%2C%20function%20(_%2C%20key)%20%7B%20keys.push(key)%3B%20return%20'(%5B%5E%2F%5D%2B)'%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20routes.push(%7B%20regex%3A%20new%20RegExp('%5E'%20%2B%20re%20%2B%20'%24')%2C%20keys%3A%20keys%2C%20handler%3A%20handler%2C%20auth%3A%20options.auth%20!%3D%3D%20false%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20navigate(hash)%20%7B%20window.location.hash%20%3D%20hash%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20resolve()%20%7B%5Cr%5Cn%20%20%20%20var%20hash%20%3D%20window.location.hash.slice(1)%20%7C%7C%20'%2Flogin'%3B%5Cr%5Cn%20%20%20%20for%20(var%20i%20%3D%200%3B%20i%20%3C%20routes.length%3B%20i%2B%2B)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20route%20%3D%20routes%5Bi%5D%3B%5Cr%5Cn%20%20%20%20%20%20var%20match%20%3D%20hash.match(route.regex)%3B%5Cr%5Cn%20%20%20%20%20%20if%20(match)%20%7B%5Cr%5Cn%20%20%20%20%20%20%20%20if%20(route.auth%20%26%26%20!BankOfEdAdmin.Api.isLoggedIn())%20%7B%20navigate('%23%2Flogin')%3B%20return%3B%20%7D%5Cr%5Cn%20%20%20%20%20%20%20%20if%20(!route.auth%20%26%26%20BankOfEdAdmin.Api.isLoggedIn()%20%26%26%20hash%20%3D%3D%3D%20'%2Flogin')%20%7B%20navigate('%23%2Fcustomers')%3B%20return%3B%20%7D%5Cr%5Cn%20%20%20%20%20%20%20%20var%20params%20%3D%20%7B%7D%3B%5Cr%5Cn%20%20%20%20%20%20%20%20route.keys.forEach(function%20(key%2C%20idx)%20%7B%20params%5Bkey%5D%20%3D%20match%5Bidx%20%2B%201%5D%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20%20%20%20%20route.handler(params)%3B%5Cr%5Cn%20%20%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%20%20%7D%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%20%20%20%20navigate(BankOfEdAdmin.Api.isLoggedIn()%20%3F%20'%23%2Fcustomers'%20%3A%20'%23%2Flogin')%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20showPage(pageId%2C%20navKey)%20%7B%5Cr%5Cn%20%20%20%20document.querySelectorAll('%5Bid%5E%3D%5C%22page-%5C%22%5D').forEach(function%20(p)%20%7B%20p.classList.add('hidden')%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20var%20page%20%3D%20document.getElementById('page-'%20%2B%20pageId)%3B%5Cr%5Cn%20%20%20%20if%20(page)%20%7B%20page.classList.remove('hidden')%3B%20page.classList.add('page-fade-in')%3B%20setTimeout(function%20()%20%7B%20page.classList.remove('page-fade-in')%3B%20%7D%2C%20250)%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20var%20viewAuth%20%3D%20document.getElementById('view-auth')%3B%5Cr%5Cn%20%20%20%20var%20appShell%20%3D%20document.getElementById('app-shell')%3B%5Cr%5Cn%20%20%20%20if%20(pageId%20%3D%3D%3D%20'auth')%20%7B%20viewAuth.classList.remove('hidden')%3B%20appShell.classList.add('hidden')%3B%20%7D%5Cr%5Cn%20%20%20%20else%20%7B%20viewAuth.classList.add('hidden')%3B%20appShell.classList.remove('hidden')%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20if%20(navKey)%20%7B%5Cr%5Cn%20%20%20%20%20%20document.querySelectorAll('.nav-link').forEach(function%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Futils.js%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Futils.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A26%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%22f5a-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%201412%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.338%5Cncf-team%3A%202fbdb480cb000483beffede400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Utilities%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.Utils%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20currencyFmt%20%3D%20new%20Intl.NumberFormat('en-AU'%2C%20%7B%20style%3A%20'currency'%2C%20currency%3A%20'AUD'%20%7D)%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20formatCurrency(amount)%20%7B%20return%20currencyFmt.format(Number(amount)%20%7C%7C%200)%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20formatDate(iso)%20%7B%5Cr%5Cn%20%20%20%20if%20(!iso)%20return%20'%E2%80%94'%3B%5Cr%5Cn%20%20%20%20return%20new%20Date(iso).toLocaleDateString('en-AU'%2C%20%7B%20day%3A%20'numeric'%2C%20month%3A%20'short'%2C%20year%3A%20'numeric'%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20var%20escMap%20%3D%20%7B%20'%26'%3A%20'%26amp%3B'%2C%20'%3C'%3A%20'%26lt%3B'%2C%20'%3E'%3A%20'%26gt%3B'%2C%20'%5C%22'%3A%20'%26quot%3B'%2C%20%5C%22'%5C%22%3A%20'%26%2339%3B'%20%7D%3B%5Cr%5Cn%20%20function%20escapeHtml(str)%20%7B%5Cr%5Cn%20%20%20%20return%20String(str%20%7C%7C%20'').replace(%2F%5B%26%3C%3E%5C%22'%5D%2Fg%2C%20function%20(c)%20%7B%20return%20escMap%5Bc%5D%3B%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20toast(message%2C%20type)%20%7B%5Cr%5Cn%20%20%20%20type%20%3D%20type%20%7C%7C%20'info'%3B%5Cr%5Cn%20%20%20%20var%20container%20%3D%20document.getElementById('toast-container')%3B%5Cr%5Cn%20%20%20%20var%20colors%20%3D%20%7B%20success%3A%20'bg-green-600'%2C%20error%3A%20'bg-red-600'%2C%20info%3A%20'bg-dark-700'%2C%20warning%3A%20'bg-amber-500'%20%7D%3B%5Cr%5Cn%20%20%20%20var%20el%20%3D%20document.createElement('div')%3B%5Cr%5Cn%20%20%20%20el.className%20%3D%20'toast-enter%20flex%20items-center%20gap-3%20px-5%20py-3.5%20rounded-xl%20text-white%20shadow-lg%20text-sm%20max-w-sm%20'%20%2B%20(colors%5Btype%5D%20%7C%7C%20colors.info)%3B%5Cr%5Cn%20%20%20%20el.innerHTML%20%3D%20'%3Cspan%3E'%20%2B%20escapeHtml(message)%20%2B%20'%3C%2Fspan%3E'%3B%5Cr%5Cn%20%20%20%20container.appendChild(el)%3B%5Cr%5Cn%20%20%20%20setTimeout(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20el.classList.remove('toast-enter')%3B%5Cr%5Cn%20%20%20%20%20%20el.classList.add('toast-exit')%3B%5Cr%5Cn%20%20%20%20%20%20el.addEventListener('animationend'%2C%20function%20()%20%7B%20el.remove()%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20%7D%2C%203500)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20openModal(html)%20%7B%5Cr%5Cn%20%20%20%20var%20overlay%20%3D%20document.getElementById('modal-overlay')%3B%5Cr%5Cn%20%20%20%20document.getElementById('modal-content').innerHTML%20%3D%20html%3B%5Cr%5Cn%20%20%20%20overlay.classList.remove('hidden')%3B%5Cr%5Cn%20%20%20%20requestAnimationFrame(function%20()%20%7B%20overlay.classList.add('show')%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20overlay.onclick%20%3D%20function%20(e)%20%7B%20if%20(e.target%20%3D%3D%3D%20overlay)%20closeModal()%3B%20%7D%3B%5Cr%5Cn%20%20%20%20document._modalEsc%20%3D%20function%20(e)%20%7B%20if%20(e.key%20%3D%3D%3D%20'Escape')%20closeModal()%3B%20%7D%3B%5Cr%5Cn%20%20%20%20document.addEventListener('keydown'%2C%20document._modalEsc)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20closeModal()%20%7B%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Futils.js%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A26%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Fri%2C%2013%20Feb%202026%2009%3A37%3A38%20GMT%5Cnetag%3A%20%5C%22f5a-64ab15b147c80-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%201412%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D7.338%5Cncf-team%3A%202fbdb480cb000483beffede400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20Admin%20-%20Utilities%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEdAdmin%20%3D%20window.BankOfEdAdmin%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEdAdmin.Utils%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20currencyFmt%20%3D%20new%20Intl.NumberFormat('en-AU'%2C%20%7B%20style%3A%20'currency'%2C%20currency%3A%20'AUD'%20%7D)%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20formatCurrency(amount)%20%7B%20return%20currencyFmt.format(Number(amount)%20%7C%7C%200)%3B%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20formatDate(iso)%20%7B%5Cr%5Cn%20%20%20%20if%20(!iso)%20return%20'%E2%80%94'%3B%5Cr%5Cn%20%20%20%20return%20new%20Date(iso).toLocaleDateString('en-AU'%2C%20%7B%20day%3A%20'numeric'%2C%20month%3A%20'short'%2C%20year%3A%20'numeric'%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20var%20escMap%20%3D%20%7B%20'%26'%3A%20'%26amp%3B'%2C%20'%3C'%3A%20'%26lt%3B'%2C%20'%3E'%3A%20'%26gt%3B'%2C%20'%5C%22'%3A%20'%26quot%3B'%2C%20%5C%22'%5C%22%3A%20'%26%2339%3B'%20%7D%3B%5Cr%5Cn%20%20function%20escapeHtml(str)%20%7B%5Cr%5Cn%20%20%20%20return%20String(str%20%7C%7C%20'').replace(%2F%5B%26%3C%3E%5C%22'%5D%2Fg%2C%20function%20(c)%20%7B%20return%20escMap%5Bc%5D%3B%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20toast(message%2C%20type)%20%7B%5Cr%5Cn%20%20%20%20type%20%3D%20type%20%7C%7C%20'info'%3B%5Cr%5Cn%20%20%20%20var%20container%20%3D%20document.getElementById('toast-container')%3B%5Cr%5Cn%20%20%20%20var%20colors%20%3D%20%7B%20success%3A%20'bg-green-600'%2C%20error%3A%20'bg-red-600'%2C%20info%3A%20'bg-dark-700'%2C%20warning%3A%20'bg-amber-500'%20%7D%3B%5Cr%5Cn%20%20%20%20var%20el%20%3D%20document.createElement('div')%3B%5Cr%5Cn%20%20%20%20el.className%20%3D%20'toast-enter%20flex%20items-center%20gap-3%20px-5%20py-3.5%20rounded-xl%20text-white%20shadow-lg%20text-sm%20max-w-sm%20'%20%2B%20(colors%5Btype%5D%20%7C%7C%20colors.info)%3B%5Cr%5Cn%20%20%20%20el.innerHTML%20%3D%20'%3Cspan%3E'%20%2B%20escapeHtml(message)%20%2B%20'%3C%2Fspan%3E'%3B%5Cr%5Cn%20%20%20%20container.appendChild(el)%3B%5Cr%5Cn%20%20%20%20setTimeout(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20el.classList.remove('toast-enter')%3B%5Cr%5Cn%20%20%20%20%20%20el.classList.add('toast-exit')%3B%5Cr%5Cn%20%20%20%20%20%20el.addEventListener('animationend'%2C%20function%20()%20%7B%20el.remove()%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20%7D%2C%203500)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20openModal(html)%20%7B%5Cr%5Cn%20%20%20%20var%20overlay%20%3D%20document.getElementById('modal-overlay')%3B%5Cr%5Cn%20%20%20%20document.getElementById('modal-content').innerHTML%20%3D%20html%3B%5Cr%5Cn%20%20%20%20overlay.classList.remove('hidden')%3B%5Cr%5Cn%20%20%20%20requestAnimationFrame(function%20()%20%7B%20overlay.classList.add('show')%3B%20%7D)%3B%5Cr%5Cn%20%20%20%20overlay.onclick%20%3D%20function%20(e)%20%7B%20if%20(e.target%20%3D%3D%3D%20overlay)%20closeModal()%3B%20%7D%3B%5Cr%5Cn%20%20%20%20document._modalEsc%20%3D%20function%20(e)%20%7B%20if%20(e.key%20%3D%3D%3D%20'Escape')%20closeModal()%3B%20%7D%3B%5Cr%5Cn%20%20%20%20document.addEventListener('keydown'%2C%20document._modalEsc)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20closeModal()%20%7B%5Cr%5Cn%20%20%20%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fbanking%2Fjs%2Fpages%2Faccounts.js%3Fv%3D20260213-2%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fbanking%2Fjs%2Fpages%2Faccounts.js%3Fv%3D20260213-2%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A30%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Sat%2C%2020%20Jun%202026%2011%3A44%3A23%20GMT%5Cnetag%3A%20%5C%223bda-654adee3833c0-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%203823%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D8.352%5Cncf-team%3A%202fbdb4914a000483be001af400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20-%20Accounts%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEd%20%3D%20window.BankOfEd%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEd.AccountsPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEd.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEd.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEd.Router.showPage('accounts'%2C%20'accounts')%3B%5Cr%5Cn%20%20%20%20loadAccounts()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20loadAccounts()%20%7B%5Cr%5Cn%20%20%20%20Api.getAccounts().then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20accounts%20%3D%20Array.isArray(res.data)%20%3F%20res.data%20%3A%20(res.data.accounts%20%7C%7C%20%5B%5D)%3B%5Cr%5Cn%20%20%20%20%20%20renderList(accounts)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20accounts.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20renderList(accounts)%20%7B%5Cr%5Cn%20%20%20%20var%20list%20%3D%20U.%24('accounts-list')%3B%5Cr%5Cn%20%20%20%20var%20empty%20%3D%20U.%24('accounts-empty')%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20if%20(!accounts.length)%20%7B%5Cr%5Cn%20%20%20%20%20%20list.innerHTML%20%3D%20''%3B%5Cr%5Cn%20%20%20%20%20%20empty.classList.remove('hidden')%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20empty.classList.add('hidden')%3B%5Cr%5Cn%20%20%20%20var%20html%20%3D%20''%3B%5Cr%5Cn%20%20%20%20accounts.forEach(function%20(acc)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20balanceColor%20%3D%20parseFloat(acc.balance)%20%3E%3D%200%20%3F%20'text-slate-900'%20%3A%20'text-red-600'%3B%5Cr%5Cn%20%20%20%20%20%20var%20currency%20%3D%20acc.currency%20%7C%7C%20'AUD'%3B%5Cr%5Cn%20%20%20%20%20%20html%20%2B%3D%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Ca%20href%3D%5C%22%23%2Faccounts%2F'%20%2B%20acc.id%20%2B%20'%5C%22%20class%3D%5C%22account-card%20bg-white%20rounded-2xl%20shadow-sm%20border%20border-slate-100%20p-5%20flex%20items-center%20justify-between%20gap-4%20block%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Cdiv%20class%3D%5C%22flex-1%20min-w-0%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-1%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20'%3Ch3%20class%3D%5C%22font-semibold%20text-slate-900%20truncate%5C%22%3E'%20%2B%20U.escapeHtml(acc.account_name)%20%2B%20'%3C%2Fh3%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20U.accountTypeBadge(acc.account_type%2C%20currency)%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3C%2Fdiv%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cp%20class%3D%5C%22text-sm%20text-slate-400%20font-mono%5C%22%3EBSB%3A%20'%20%2B%20U.escapeHtml(acc.bsb)%20%2B%20'%20%26nbsp%3B%20Acc%3A%20'%20%2B%20U.escapeHtml(acc.account_number)%20%2B%20'%3C%2Fp%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3C%2Fdiv%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Cdiv%20class%3D%5C%22text-right%20flex-shrink-0%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cp%20class%3D%5C%22text-xl%20font-bold%20'%20%2B%20balanceColor%20%2B%20'%5C%22%3E'%20%2B%20U.formatCurrency(acc.balance%2C%20currency)%20%2B%20'%3C%2Fp%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cp%20class%3D%5C%22text-xs%20text-slate-400%20mt-1%5C%22%3EAvailable%3C%2Fp%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3C%2Fdiv%3E'%20%2B%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fbanking%2Fjs%2Fpages%2Faccounts.js%3Fv%3D20260213-2%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A30%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Sat%2C%2020%20Jun%202026%2011%3A44%3A23%20GMT%5Cnetag%3A%20%5C%223bda-654adee3833c0-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%203823%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D8.352%5Cncf-team%3A%202fbdb4914a000483be001af400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20-%20Accounts%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEd%20%3D%20window.BankOfEd%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEd.AccountsPage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEd.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEd.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEd.Router.showPage('accounts'%2C%20'accounts')%3B%5Cr%5Cn%20%20%20%20loadAccounts()%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20loadAccounts()%20%7B%5Cr%5Cn%20%20%20%20Api.getAccounts().then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20accounts%20%3D%20Array.isArray(res.data)%20%3F%20res.data%20%3A%20(res.data.accounts%20%7C%7C%20%5B%5D)%3B%5Cr%5Cn%20%20%20%20%20%20renderList(accounts)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20accounts.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20renderList(accounts)%20%7B%5Cr%5Cn%20%20%20%20var%20list%20%3D%20U.%24('accounts-list')%3B%5Cr%5Cn%20%20%20%20var%20empty%20%3D%20U.%24('accounts-empty')%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20if%20(!accounts.length)%20%7B%5Cr%5Cn%20%20%20%20%20%20list.innerHTML%20%3D%20''%3B%5Cr%5Cn%20%20%20%20%20%20empty.classList.remove('hidden')%3B%5Cr%5Cn%20%20%20%20%20%20return%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20%20%20empty.classList.add('hidden')%3B%5Cr%5Cn%20%20%20%20var%20html%20%3D%20''%3B%5Cr%5Cn%20%20%20%20accounts.forEach(function%20(acc)%20%7B%5Cr%5Cn%20%20%20%20%20%20var%20balanceColor%20%3D%20parseFloat(acc.balance)%20%3E%3D%200%20%3F%20'text-slate-900'%20%3A%20'text-red-600'%3B%5Cr%5Cn%20%20%20%20%20%20var%20currency%20%3D%20acc.currency%20%7C%7C%20'AUD'%3B%5Cr%5Cn%20%20%20%20%20%20html%20%2B%3D%5Cr%5Cn%20%20%20%20%20%20%20%20'%3Ca%20href%3D%5C%22%23%2Faccounts%2F'%20%2B%20acc.id%20%2B%20'%5C%22%20class%3D%5C%22account-card%20bg-white%20rounded-2xl%20shadow-sm%20border%20border-slate-100%20p-5%20flex%20items-center%20justify-between%20gap-4%20block%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Cdiv%20class%3D%5C%22flex-1%20min-w-0%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-1%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20'%3Ch3%20class%3D%5C%22font-semibold%20text-slate-900%20truncate%5C%22%3E'%20%2B%20U.escapeHtml(acc.account_name)%20%2B%20'%3C%2Fh3%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20U.accountTypeBadge(acc.account_type%2C%20currency)%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3C%2Fdiv%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cp%20class%3D%5C%22text-sm%20text-slate-400%20font-mono%5C%22%3EBSB%3A%20'%20%2B%20U.escapeHtml(acc.bsb)%20%2B%20'%20%26nbsp%3B%20Acc%3A%20'%20%2B%20U.escapeHtml(acc.account_number)%20%2B%20'%3C%2Fp%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3C%2Fdiv%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3Cdiv%20class%3D%5C%22text-right%20flex-shrink-0%5C%22%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cp%20class%3D%5C%22text-xl%20font-bold%20'%20%2B%20balanceColor%20%2B%20'%5C%22%3E'%20%2B%20U.formatCurrency(acc.balance%2C%20currency)%20%2B%20'%3C%2Fp%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20%20%20'%3Cp%20class%3D%5C%22text-xs%20text-slate-400%20mt-1%5C%22%3EAvailable%3C%2Fp%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%20%20%20'%3C%2Fdiv%3E'%20%2B%5Cr%5Cn%20%20%20%20%20%20%20%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20protected%20endpoint%22%2C%22description%22%3A%22The%20deterministic%20auth%20matrix%20requested%20a%20protected%20or%20sensitive-looking%20endpoint%20without%20cookies%20or%20Authorization%20and%20received%20a%20successful%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fbanking%2Fjs%2Fpages%2Fprofile.js%3Fv%3D20260213-2%22%2C%22evidence%22%3A%22Actor%20%60anonymous%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F100.96.0.19%2Fbanking%2Fjs%2Fpages%2Fprofile.js%3Fv%3D20260213-2%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A30%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Sun%2C%2021%20Jun%202026%2005%3A33%3A56%20GMT%5Cnetag%3A%20%5C%223db5-654bcdf3a7900-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%203658%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D9.664%5Cncf-team%3A%202fbdb491a5000483be001d3400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20-%20Profile%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEd%20%3D%20window.BankOfEd%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEd.ProfilePage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEd.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEd.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20isEditing%20%3D%20false%3B%5Cr%5Cn%20%20var%20currentProfile%20%3D%20null%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEd.Router.showPage('profile'%2C%20'profile')%3B%5Cr%5Cn%20%20%20%20isEditing%20%3D%20false%3B%5Cr%5Cn%20%20%20%20setFieldsEditable(false)%3B%5Cr%5Cn%20%20%20%20U.%24('profile-actions').classList.add('hidden')%3B%5Cr%5Cn%20%20%20%20U.%24('profile-edit-btn').textContent%20%3D%20'Edit'%3B%5Cr%5Cn%20%20%20%20U.showErrors('profile-errors'%2C%20null)%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20%2F%2F%20Load%20profile%20%E2%80%94%20API%20returns%20user%20object%20directly%20in%20res.data%5Cr%5Cn%20%20%20%20Api.getProfile().then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20currentProfile%20%3D%20res.data%3B%5Cr%5Cn%20%20%20%20%20%20populateProfile(currentProfile)%3B%5Cr%5Cn%20%20%20%20%20%20renderTotpSection(currentProfile)%3B%5Cr%5Cn%20%20%20%20%20%20loadAvatar(currentProfile)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20profile.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20populateProfile(user)%20%7B%5Cr%5Cn%20%20%20%20U.%24('profile-first-name').value%20%3D%20user.first_name%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-last-name').value%20%3D%20user.last_name%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-email').value%20%3D%20user.email%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-phone').value%20%3D%20user.phone%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-address1').value%20%3D%20user.address_line1%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-address2').value%20%3D%20user.address_line2%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-suburb').value%20%3D%20user.suburb%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-state').value%20%3D%20user.state%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-postcode').value%20%3D%20user.postcode%20%7C%7C%20''%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20toggleEdit()%20%7B%5Cr%5Cn%20%20%20%20if%20(isEditing)%20%7B%5Cr%5Cn%20%20%20%20%20%20cancelEdit()%3B%5Cr%5Cn%20%20%20%20%7D%20else%20%7B%5Cr%5Cn%20%20%20%20%20%20isEditing%20%3D%20true%3B%5Cr%5Cn%20%20%20%20%20%20setFieldsEditable(true)%3B%5Cr%5Cn%20%20%20%20%20%20U.%24('profile-actions').classList.remove('hidden')%3B%5Cr%5Cn%20%20%20%20%20%20U.%24('profile-edit-btn').textContent%20%3D%20'Cancel'%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20cancelEdit()%20%7B%5Cr%5Cn%20%20%20%20isEditing%20%3D%20false%3B%5Cr%5Cn%20%20%20%20setFieldsEditable(false)%3B%5Cr%5Cn%20%20%20%20U.%24('profile-actions').classList.add('hidden')%3B%5Cr%5Cn%20%20%20%20U.%24('profile-edit-btn').textContent%20%3D%20'Edit'%3B%5Cr%5Cn%20%20%20%20U.showErrors('profile-errors'%2C%20null)%3B%5Cr%5Cn%20%20%20%20if%20(currentProfile)%20populateProfile(currentProfil%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fbanking%2Fjs%2Fpages%2Fprofile.js%3Fv%3D20260213-2%20HTTP%2F1.1%5CnActor%3A%20anonymous%5CnCookies%3A%20none%5CnAuthorization%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Wed%2C%2001%20Jul%202026%2005%3A16%3A30%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnlast-modified%3A%20Sun%2C%2021%20Jun%202026%2005%3A33%3A56%20GMT%5Cnetag%3A%20%5C%223db5-654bcdf3a7900-gzip%5C%22%5Cnaccept-ranges%3A%20bytes%5Cnvary%3A%20Accept-Encoding%5Cncontent-encoding%3A%20gzip%5Cncontent-length%3A%203658%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fjavascript%5Cnserver-timing%3A%20cfReqDur%3Bdur%3D9.664%5Cncf-team%3A%202fbdb491a5000483be001d3400000001%5Cn%5Cn%2F**%5Cr%5Cn%20*%20BankOfEd%20-%20Profile%20Page%5Cr%5Cn%20*%2F%5Cr%5Cnwindow.BankOfEd%20%3D%20window.BankOfEd%20%7C%7C%20%7B%7D%3B%5Cr%5Cn%5Cr%5CnBankOfEd.ProfilePage%20%3D%20(function%20()%20%7B%5Cr%5Cn%20%20'use%20strict'%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20U%20%3D%20BankOfEd.Utils%3B%5Cr%5Cn%20%20var%20Api%20%3D%20BankOfEd.Api%3B%5Cr%5Cn%5Cr%5Cn%20%20var%20isEditing%20%3D%20false%3B%5Cr%5Cn%20%20var%20currentProfile%20%3D%20null%3B%5Cr%5Cn%5Cr%5Cn%20%20function%20show()%20%7B%5Cr%5Cn%20%20%20%20BankOfEd.Router.showPage('profile'%2C%20'profile')%3B%5Cr%5Cn%20%20%20%20isEditing%20%3D%20false%3B%5Cr%5Cn%20%20%20%20setFieldsEditable(false)%3B%5Cr%5Cn%20%20%20%20U.%24('profile-actions').classList.add('hidden')%3B%5Cr%5Cn%20%20%20%20U.%24('profile-edit-btn').textContent%20%3D%20'Edit'%3B%5Cr%5Cn%20%20%20%20U.showErrors('profile-errors'%2C%20null)%3B%5Cr%5Cn%5Cr%5Cn%20%20%20%20%2F%2F%20Load%20profile%20%E2%80%94%20API%20returns%20user%20object%20directly%20in%20res.data%5Cr%5Cn%20%20%20%20Api.getProfile().then(function%20(res)%20%7B%5Cr%5Cn%20%20%20%20%20%20currentProfile%20%3D%20res.data%3B%5Cr%5Cn%20%20%20%20%20%20populateProfile(currentProfile)%3B%5Cr%5Cn%20%20%20%20%20%20renderTotpSection(currentProfile)%3B%5Cr%5Cn%20%20%20%20%20%20loadAvatar(currentProfile)%3B%5Cr%5Cn%20%20%20%20%7D).catch(function%20()%20%7B%5Cr%5Cn%20%20%20%20%20%20U.toast('Failed%20to%20load%20profile.'%2C%20'error')%3B%5Cr%5Cn%20%20%20%20%7D)%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20populateProfile(user)%20%7B%5Cr%5Cn%20%20%20%20U.%24('profile-first-name').value%20%3D%20user.first_name%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-last-name').value%20%3D%20user.last_name%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-email').value%20%3D%20user.email%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-phone').value%20%3D%20user.phone%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-address1').value%20%3D%20user.address_line1%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-address2').value%20%3D%20user.address_line2%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-suburb').value%20%3D%20user.suburb%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-state').value%20%3D%20user.state%20%7C%7C%20''%3B%5Cr%5Cn%20%20%20%20U.%24('profile-postcode').value%20%3D%20user.postcode%20%7C%7C%20''%3B%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20toggleEdit()%20%7B%5Cr%5Cn%20%20%20%20if%20(isEditing)%20%7B%5Cr%5Cn%20%20%20%20%20%20cancelEdit()%3B%5Cr%5Cn%20%20%20%20%7D%20else%20%7B%5Cr%5Cn%20%20%20%20%20%20isEditing%20%3D%20true%3B%5Cr%5Cn%20%20%20%20%20%20setFieldsEditable(true)%3B%5Cr%5Cn%20%20%20%20%20%20U.%24('profile-actions').classList.remove('hidden')%3B%5Cr%5Cn%20%20%20%20%20%20U.%24('profile-edit-btn').textContent%20%3D%20'Cancel'%3B%5Cr%5Cn%20%20%20%20%7D%5Cr%5Cn%20%20%7D%5Cr%5Cn%5Cr%5Cn%20%20function%20cancelEdit()%20%7B%5Cr%5Cn%20%20%20%20isEditing%20%3D%20false%3B%5Cr%5Cn%20%20%20%20setFieldsEditable(false)%3B%5Cr%5Cn%20%20%20%20U.%24('profile-actions').classList.add('hidden')%3B%5Cr%5Cn%20%20%20%20U.%24('profile-edit-btn').textContent%20%3D%20'Edit'%3B%5Cr%5Cn%20%20%20%20U.showErrors('profile-errors'%2C%20null)%3B%5Cr%5Cn%20%20%20%20if%20(currentProfile)%20populateProfile(currentProfil%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Weak%20Password%20Policy%20%E2%80%94%20Single-Character%20Passwords%20Accepted%2C%20Unsalted%20MD5%20Password%20Hashing%22%2C%22description%22%3A%22The%20registration%20endpoint%20at%20%2Fapi%2Fauth%2Fregister%20does%20not%20enforce%20any%20minimum%20length%20or%20complexity%20requirement%20on%20user-supplied%20passwords.%20A%20registration%20request%20using%20the%20single-character%20password%20%5C%22a%5C%22%20was%20accepted%20and%20a%20new%20account%20was%20created.%20Additionally%2C%20the%20server-side%20password%20hashing%20scheme%20was%20confirmed%20to%20be%20unsalted%20MD5%2C%20a%20fast%2C%20cryptographically%20broken%20algorithm%20unsuitable%20for%20password%20storage.%22%2C%22impact%22%3A%22The%20absence%20of%20password%20length%2Fcomplexity%20enforcement%20makes%20accounts%20significantly%20more%20susceptible%20to%20credential%20guessing%20and%20brute-force%20attacks.%20The%20use%20of%20unsalted%20MD5%20for%20password%20storage%20compounds%20this%20risk%3A%20MD5%20hashes%20are%20trivially%20reversible%20via%20precomputed%20rainbow%20tables%20and%20can%20be%20brute-forced%20at%20very%20high%20speed.%20This%20is%20especially%20severe%20combined%20with%20a%20separately%20identified%20issue%20in%20this%20assessment%20where%20the%20password_hash%20field%20is%20leaked%20in%20API%20responses%2C%20as%20it%20would%20allow%20rapid%20offline%20recovery%20of%20plaintext%20passwords%20for%20any%20account%20whose%20hash%20is%20exposed.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20a%20single%20registration%20request%20with%20a%201-character%20password%20was%20accepted%20and%20returned%20an%20MD5%20hash%20matching%20the%20known%20unsalted%20MD5%20digest%20of%20%5C%22a%5C%22%2C%20requiring%20no%20special%20access%20or%20conditions%20to%20reproduce.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20minimum%20password%20length%20(12%2B%20characters)%20and%20complexity%2Fbreach-list%20checks%20at%20both%20the%20registration%20and%20password-change%20endpoints.%20Replace%20MD5%20with%20a%20modern%20adaptive%20password%20hashing%20algorithm%20(bcrypt%2C%20scrypt%2C%20or%20argon2id)%20using%20a%20unique%20per-user%20salt%20and%20an%20appropriate%20work%20factor.%20Rehash%20existing%20stored%20passwords%20upon%20next%20successful%20login%20using%20the%20new%20scheme.%22%2C%22cvss_score%22%3A5.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22POST%20http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Fregister%20with%20body%20%7B%5C%22email%5C%22%3A%5C%22weakpass_test1%40example.invalid%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Weak%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Pass%5C%22%2C%5C%22password%5C%22%3A%5C%22a%5C%22%7D%20returned%20201%20Created%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A18%2C...%2C%5C%22password_hash%5C%22%3A%5C%220cc175b9c0f1b6a831c399e269772661%5C%22%2C...%7D%2C%5C%22token%5C%22%3A%5C%22%5BJWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D.%20The%20password_hash%200cc175b9c0f1b6a831c399e269772661%20is%20the%20well-known%20unsalted%20MD5%20digest%20of%20the%20string%20%5C%22a%5C%22%2C%20confirming%20both%20single-character%20password%20acceptance%20and%20use%20of%20unsalted%20MD5%20hashing.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22CORS%20Misconfiguration%20%E2%80%94%20Arbitrary%20Origin%20Reflected%20with%20Access-Control-Allow-Credentials%3A%20true%22%2C%22description%22%3A%22The%20%2Fapi%2Fprofile%20endpoint%20dynamically%20reflects%20any%20client-supplied%20Origin%20header%20value%20into%20the%20Access-Control-Allow-Origin%20response%20header%20while%20also%20setting%20Access-Control-Allow-Credentials%3A%20true.%20This%20behavior%20was%20confirmed%20on%20both%20a%20simple%20GET%20request%20and%20an%20OPTIONS%20preflight%20request%2C%20indicating%20the%20misconfiguration%20applies%20broadly%20to%20the%20endpoint%20rather%20than%20a%20single%20request%20type.%22%2C%22impact%22%3A%22Combining%20unrestricted%20Origin%20reflection%20with%20Access-Control-Allow-Credentials%3A%20true%20is%20a%20known%20anti-pattern%20that%2C%20if%20credentials%20are%20attached%20automatically%20by%20the%20browser%20(e.g.%20stored%20cookies)%20or%20become%20reachable%20from%20a%20malicious%20page%2Fscript%20context%2C%20would%20allow%20an%20attacker-controlled%20site%20to%20issue%20credentialed%20cross-origin%20requests%20and%20read%20authenticated%20response%20data%20(this%20endpoint%20has%20previously%20been%20shown%20to%20return%20sensitive%20profile%20fields%20such%20as%20password_hash%20and%20totp_secret).%20No%20browser-based%20proof-of-concept%20demonstrating%20successful%20credentialed%20cross-origin%20data%20exfiltration%20was%20performed%20in%20this%20assessment%2C%20so%20exploitability%20under%20the%20application's%20actual%20authentication%20model%20(e.g.%20Bearer-token-in-header)%20is%20unconfirmed%20but%20the%20misconfiguration%20itself%20is%20a%20real%20weakening%20of%20the%20browser's%20same-origin%20protections.%22%2C%22likelihood%22%3A%22Confirmed%20via%20direct%20request%2Fresponse%20header%20inspection%20on%20both%20GET%20and%20OPTIONS%20preflight%20requests.%20Practical%20exploitability%20depends%20on%20how%20the%20victim's%20session%2Ftoken%20is%20attached%20in-browser%20(e.g.%20cookie-based%20auth%20or%20a%20script%20able%20to%20read%20a%20stored%20token)%20%E2%80%94%20this%20was%20not%20demonstrated%20end-to-end%2C%20so%20likelihood%20of%20a%20full%20credentialed%20cross-origin%20data%20leak%20in%20the%20current%20auth%20model%20is%20uncertain%20but%20plausible%20for%20future%20or%20alternate%20auth%20flows.%22%2C%22recommendation%22%3A%22Do%20not%20reflect%20arbitrary%20Origin%20headers.%20Maintain%20an%20explicit%20allow-list%20of%20trusted%20origins%20(the%20application's%20own%20domains)%20and%20only%20set%20Access-Control-Allow-Origin%20to%20a%20matching%20value%20from%20that%20list.%20Never%20combine%20wildcard%20or%20reflected-origin%20values%20with%20Access-Control-Allow-Credentials%3A%20true.%20Apply%20the%20fix%20consistently%20across%20both%20simple%20and%20preflighted%20(OPTIONS)%20requests.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fprofile%20with%20header%20Origin%3A%20https%3A%2F%2Fevil.example%20returned%20access-control-allow-origin%3A%20https%3A%2F%2Fevil.example%20and%20access-control-allow-credentials%3A%20true.%20Identical%20reflected-origin%20plus%20allow-credentials%3Atrue%20behavior%20confirmed%20on%20OPTIONS%20preflight%20request.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20Content-Security-Policy%20and%20Strict-Transport-Security%20Headers%22%2C%22description%22%3A%22The%20application%20at%20http%3A%2F%2F100.96.0.19%2Fbanking%2F%20and%20its%20API%20(e.g.%20%2Fapi%2Fhealth)%20do%20not%20return%20Content-Security-Policy%20or%20Strict-Transport-Security%20headers%20on%20any%20tested%20response.%20Present%20security%20headers%20are%20limited%20to%20x-content-type-options%2C%20x-frame-options%2C%20x-xss-protection%2C%20and%20referrer-policy%3B%20CSP%20and%20HSTS%20were%20absent%20across%20all%20captured%20traffic%20during%20this%20assessment.%22%2C%22impact%22%3A%22The%20absence%20of%20a%20Content-Security-Policy%20removes%20a%20defense-in-depth%20control%20that%20could%20otherwise%20restrict%20script%20execution%20and%20mitigate%20the%20impact%20of%20the%20confirmed%20stored%20XSS%20findings%20(transfer%20description%20and%20profile%20fields)%2C%20as%20there%20is%20no%20script-src%20restriction%20to%20block%20injected%20inline%20scripts.%20The%20absence%20of%20HSTS%20means%20users%20connecting%20over%20plain%20HTTP%2C%20or%20subjected%20to%20an%20SSL-stripping%20MITM%20attack%2C%20are%20not%20automatically%20upgraded%20to%20HTTPS%2C%20which%20for%20a%20banking%20application%20increases%20the%20risk%20of%20credential%20and%20session%20token%20interception%20in%20a%20network-level%20attack%20scenario.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20header%20absence%20was%20directly%20observed%20across%20all%20captured%20HTTP%20responses%20in%20this%20assessment%20via%20history_search%2C%20with%20no%20additional%20exploitation%20steps%20required%20to%20verify.%22%2C%22recommendation%22%3A%22Add%20a%20restrictive%20Content-Security-Policy%20header%20(e.g.%20default-src%20'self'%3B%20script-src%20'self'%3B%20object-src%20'none'%3B%20frame-ancestors%20'none')%20to%20all%20HTML%20and%20API%20responses%2C%20avoiding%20unsafe-inline%20and%20unsafe-eval%20directives.%20Add%20Strict-Transport-Security%3A%20max-age%3D31536000%3B%20includeSubDomains%20once%20the%20application%20is%20served%20exclusively%20over%20HTTPS.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fbanking%2F%22%2C%22evidence%22%3A%22GET%20http%3A%2F%2F100.96.0.19%2Fbanking%2F%20and%20GET%20http%3A%2F%2F100.96.0.19%2Fapi%2Fhealth%20response%20headers%20do%20not%20include%20Content-Security-Policy%20or%20Strict-Transport-Security.%20Observed%20headers%20on%20these%20and%20other%20tested%20endpoints%20only%20include%20x-content-type-options%2C%20x-frame-options%2C%20x-xss-protection%2C%20and%20referrer-policy%20%E2%80%94%20no%20CSP%20or%20HSTS%20header%20was%20present%20in%20any%20response%20captured%20during%20this%20assessment%20(confirmed%20via%20history_search%20across%20all%20captured%20traffic).%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20Rate-Limiting%20on%20Login%20Endpoint%20Enables%20Brute-Force%20Attacks%22%2C%22description%22%3A%22The%20authentication%20endpoint%20at%20%2Fapi%2Fauth%2Flogin%20does%20not%20implement%20rate-limiting%2C%20progressive%20delays%2C%20CAPTCHA%2C%20or%20account%20lockout%20after%20repeated%20failed%20login%20attempts.%20This%20allows%20unrestricted%20password-guessing%20against%20any%20known%20account.%22%2C%22impact%22%3A%22An%20attacker%20who%20has%20identified%20a%20valid%20account%20(e.g.%20via%20the%20confirmed%20user-enumeration%20issue)%20can%20perform%20unlimited%20password-guessing%20or%20credential-stuffing%20attempts%20against%20that%20account%20without%20triggering%20any%20throttling%2C%20lockout%2C%20or%20alerting%20mechanism.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%206%20consecutive%20failed%20login%20attempts%20against%20a%20valid%20account%20all%20returned%20identical%20unthrottled%20401%20responses%20with%20consistent%20response%20times%20(110-180ms)%2C%20demonstrating%20no%20throttling%20controls%20are%20in%20place.%20Exploitation%20would%20still%20require%20sustained%20automated%20requests%20and%20a%20valid%20or%20guessed%20account%20identifier.%22%2C%22recommendation%22%3A%22Implement%20account-%20and%20IP-based%20rate%20limiting%20on%20%2Fapi%2Fauth%2Flogin%20and%20other%20sensitive%20endpoints%20(password%20reset%2C%20OTP%20verification)%2C%20e.g.%20via%20a%20Redis%20token%20bucket%20or%20similar%20mechanism.%20Add%20progressive%20delays%20or%20CAPTCHA%20after%20a%20small%20number%20of%20failed%20attempts%2C%20and%20temporary%20account%20lockout%20with%20alerting%20on%20repeated%20failures.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Sent%206%20consecutive%20POST%20requests%20to%20%2Fapi%2Fauth%2Flogin%20with%20email%3Damelia.chen%40example.com%20and%20incrementing%20wrong%20passwords%20(wrongpass1..wrongpass6).%20Attempt%20%231%20response%3A%20401%20%7B%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%7D.%20Attempt%20%236%20response%3A%20identical%20401%20%7B%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%7D.%20No%20CAPTCHA%2C%20lockout%2C%20429%2C%20or%20increasing%20delay%20was%20observed%20across%20any%20of%20the%206%20attempts%20(response%20times%20stayed%20in%20the%20110-180ms%20range%20throughout).%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22User%20Enumeration%20via%20Distinct%20Login%20Error%20Codes%22%2C%22description%22%3A%22The%20login%20endpoint%20at%20%2Fapi%2Fauth%2Flogin%20returns%20distinct%2C%20machine-readable%20error%20codes%20and%20messages%20depending%20on%20whether%20the%20submitted%20email%20address%20corresponds%20to%20an%20existing%20account.%20A%20request%20with%20a%20valid%20email%20and%20an%20incorrect%20password%20returns%20a%20WRONG_PASSWORD%20error%2C%20while%20a%20request%20with%20a%20non-existent%20email%20returns%20a%20USER_NOT_FOUND%20error%2C%20allowing%20an%20attacker%20to%20distinguish%20valid%20from%20invalid%20accounts.%22%2C%22impact%22%3A%22An%20attacker%20can%20enumerate%20valid%20customer%20email%20addresses%2Fusernames%20by%20submitting%20login%20attempts%20and%20observing%20the%20differing%20error%20codes%2Fmessages.%20Confirmed%20valid%20accounts%20can%20then%20be%20targeted%20more%20efficiently%20for%20credential%20stuffing%2C%20password%20brute-forcing%2C%20or%20phishing%20campaigns.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20reproduced%20with%20two%20direct%20login%20requests%2C%20one%20against%20a%20known%20valid%20account%20and%20one%20against%20a%20non-existent%20account%2C%20each%20returning%20a%20distinct%2C%20distinguishable%20error%20code%20and%20message.%22%2C%22recommendation%22%3A%22Return%20a%20single%20generic%20error%20response%20(e.g.%20HTTP%20401%20with%20a%20message%20such%20as%20%5C%22Invalid%20email%20or%20password%5C%22)%20regardless%20of%20whether%20the%20email%20exists%20or%20the%20password%20is%20incorrect.%20Avoid%20distinguishing%20error%20codes%2Fmessages%20between%20the%20two%20cases.%20Normalize%20response%20timing%20between%20the%20two%20scenarios%20to%20prevent%20timing-based%20enumeration%2C%20and%20consider%20rate-limiting%2Flockout%20controls%20on%20the%20login%20endpoint%20to%20further%20hinder%20enumeration%20and%20brute-force%20attempts.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20%7B%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22wrongpass1%5C%22%7D%20%E2%86%92%20401%20%7B%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%7D.%20POST%20%2Fapi%2Fauth%2Flogin%20%7B%5C%22email%5C%22%3A%5C%22nonexistent_user_xyz%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22wrongpass1%5C%22%7D%20%E2%86%92%20401%20%7B%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D%7D.%20Distinct%20error%20codes%2Fmessages%20disclose%20account%20existence.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Static%20JavaScript%20Assets%20Served%20Without%20Authentication%20(Auth-Matrix%20Noise%20Finding)%22%2C%22description%22%3A%22The%20web%20server%20returns%20static%20JavaScript%20asset%20files%20for%20both%20the%20admin%20and%20banking%20frontends%20without%20requiring%20any%20authentication%20(cookies%20or%20Authorization%20header).%20Examples%20observed%20during%20the%20unauthenticated%20auth-matrix%20sweep%20include%3A%20%2Fadmin%2Fjs%2Fapp.js%2C%20%2Fadmin%2Fjs%2Fpages%2Faccounts.js%2C%20%2Fadmin%2Fjs%2Fpages%2Fauth.js%2C%20%2Fadmin%2Fjs%2Fpages%2Fcustomers.js%2C%20%2Fadmin%2Fjs%2Fpages%2Ffx-rates.js%2C%20%2Fadmin%2Fjs%2Fpages%2Fsystem.js%2C%20%2Fadmin%2Fjs%2Frouter.js%2C%20%2Fadmin%2Fjs%2Futils.js%2C%20%2Fbanking%2Fjs%2Fpages%2Faccounts.js%2C%20%2Fbanking%2Fjs%2Fpages%2Fprofile.js.%5Cn%5CnThis%20is%20expected%2Fnormal%20behavior%20for%20static%20asset%20paths%20(the%20server%20does%20not%20enforce%20auth%20on%20.js%20files)%20and%20does%20not%20by%20itself%20represent%20an%20authentication%20bypass%20%E2%80%94%20authentication%20is%20enforced%20on%20the%20dynamic%20API%20endpoints%20(e.g.%20%2Fapi%2Fadmin%2F*%2C%20%2Fapi%2Fprofile%2C%20%2Fapi%2Ftransactions%2F*)%2C%20not%20on%20the%20JS%20bundles%20the%20SPA%20loads.%20The%20finding%20is%20recorded%20here%20for%20completeness%20because%20the%20deterministic%20auth-matrix%20flagged%20all%20ten%20paths%3B%20the%20actual%20risk%20surface%20is%20the%20application%20logic%20the%20JS%20files%20reveal%20(admin%20route%20structure%2C%20customer-side%20page%20modules)%2C%20not%20the%20unauthenticated%20retrieval%20of%20those%20files.%20No%20exploitation%20is%20possible%20from%20this%20alone.%22%2C%22impact%22%3A%22No%20direct%20impact.%20Static%20JS%20retrieval%20without%20auth%20is%20expected.%20The%20indirectly%20disclosed%20information%20(route%20names%2C%20page%20module%20structure)%20is%20the%20same%20information%20a%20user%20would%20receive%20by%20loading%20the%20public%20landing%20page%20or%20by%20inspecting%20the%20bundled%20SPA.%22%2C%22likelihood%22%3A%22low%22%2C%22recommendation%22%3A%22No%20remediation%20required.%20If%20desired%20for%20defence-in-depth%2C%20the%20web%20server%20can%20serve%20static%20assets%20with%20restrictive%20Cache-Control%20headers%20and%20the%20API%20endpoints%20already%20enforce%20authentication%20correctly.%20Real%20authorization%20controls%20are%20(and%20should%20remain)%20on%20%2Fapi%2F*%20dynamic%20routes.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F100.96.0.19%2Fadmin%2Fjs%2Fapp.js%22%2C%22evidence%22%3A%22Auth-matrix%20sweep%20returned%20HTTP%20200%20for%20all%20ten%20static%20JS%20paths%20when%20probed%20without%20cookies%20or%20Authorization%20headers.%20This%20is%20identical%20to%20the%20response%20observed%20for%20any%20normal%20browser%20request%20that%20loads%20the%20SPA%20shell%20%E2%80%94%20no%20protected%20data%20is%20returned%2C%20only%20client-side%20code.%20Example%3A%20GET%20%2Fadmin%2Fjs%2Fpages%2Fcustomers.js%20-%3E%20200%2C%20body%20contains%20the%20customer-listing%20page%20module%20(not%20user%20records).%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22alice%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%5D
-->

## 1. Default Admin Credentials (admin/admin123) Grant Full Admin Panel Access

- Severity: critical
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/admin/auth/login
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The admin authentication endpoint at /api/admin/auth/login accepts the trivial, well-known default credential pair admin/admin123. Successful authentication returns a valid session token and grants full access to the administrative panel of the banking application.

### Impact
An attacker can log in as an administrator using a guessable default credential, obtaining full administrative access to the application. This includes access to all customer records, accounts, FX rate configuration, and system reset functionality (admin/#/system), representing a complete compromise of the admin interface and the sensitive data/functions it controls.

### Likelihood
Confirmed — the credential pair admin/admin123 was submitted to the login endpoint and authenticated successfully, returning a valid admin token.

### Recommendation
Remove or disable default admin credentials immediately. Enforce a strong password policy with mandatory password change on first login for all admin accounts. Add rate limiting and account lockout on the admin login endpoint. Implement MFA for admin accounts. Audit for any other default or weak credentials across the application.

### Evidence
```
POST http://100.96.0.19/api/admin/auth/login with body {"username":"admin","password":"admin123"} returned 200: {"success":true,"data":{"admin":{"id":1,"username":"admin"},"token":"[JWT]"},"message":"Login successful"}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 2. Full Authentication Bypass via Forged JWT Using Leaked Signing Secret — Confirmed Cross-Account Takeover

- Severity: critical
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/profile
- CVSS: 10 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H)

### Description
The application's JWT signing secret was previously found to be disclosed via the unauthenticated GET /api/health endpoint. This finding demonstrates that the leaked secret is live and valid: it was used to forge an HS256-signed JWT for an arbitrary customer_id/sub, and that forged token was accepted by the authenticated API at /api/profile, granting full account access with no login, password, or valid session ever required.

### Impact
Any attacker possessing the leaked jwt_secret can forge a validly-signed JWT for any customer_id/sub value and gain complete authenticated access to that customer's account — profile data, accounts, balances, transactions, address book, and the ability to initiate transfers — without a password or session. Customer IDs 1–21 were observed to exist, meaning an attacker could forge tokens for and fully compromise every customer in the database. Combined with other confirmed issues (missing insufficient-funds validation, TOTP bypass on external transfers), this secret alone is sufficient to drain or manipulate every account in the bank. This confirms the /api/health secret leak as a fully weaponized, complete authentication bypass rather than a theoretical risk.

### Likelihood
Confirmed via live exploitation: a forged token was accepted by the server and returned another user's private profile data, including their bcrypt password hash, with zero valid credentials used.

### Recommendation
Immediately rotate the JWT signing secret and remove it from the /api/health response (see related finding on the /api/health secret leak). Additionally: store secrets in environment variables or a secrets manager that is never exposed via any API response; implement short-lived access tokens with refresh token rotation; ensure server-side token revocation (jti tracking) is enforced consistently; and ensure malformed or incomplete claims fail closed (return 401) rather than causing unhandled server errors.

### Evidence
```
Using the jwt_secret leaked from unauthenticated GET /api/health ("Jj9XUzmBPzn8VcJEgzD9kC9koZTs1OV6XadreivDDrykIUuLimoQNqQnBdNE4Uv"), an HS256 JWT was forged with claims {"customer_id":1,"exp":2000000000,"jti":"aespa-test-jti-001","sub":1} without any legitimate login. Sending GET http://100.96.0.19/api/profile with this forged token as Authorization: Bearer returned HTTP 200 with the full profile of customer #1 (Amelia Chen), including email, address, phone, and bcrypt password hash: {"success":true,"data":{"id":1,"email":"amelia.chen@example.com","first_name":"Amelia","last_name":"Chen","address_line1":"14 Harbour View Tce",...,"password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi","totp_secret":null},"message":"OK"} — confirming full unauthorized account access achieved purely by offline token forgery using the leaked secret.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 3. JWT Signing Secret and Database Credentials Exposed via Unauthenticated /api/health Endpoint

- Severity: critical
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/health
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The /api/health endpoint on the application server returns sensitive backend configuration data, including the JWT HMAC signing secret and internal database connection details, to any unauthenticated requester. No authentication, session, or network restriction is enforced on this endpoint.

### Impact
Possession of the JWT HMAC signing secret allows an attacker to forge arbitrary, validly-signed JSON Web Tokens for any user or administrator account, resulting in complete authentication bypass and full account takeover across the application. The disclosed database host, database name, and application database username further expose internal infrastructure details that could facilitate follow-on attacks (e.g., targeted SQL injection or SSRF attempts against the database), and combined with the leaked application context, meaningfully lower the bar for a full compromise of the platform.

### Likelihood
Confirmed — reproducible with a single unauthenticated GET request; no preconditions, authentication, or special access required.

### Recommendation
Immediately rotate the exposed JWT signing secret and invalidate all existing tokens. Remove jwt_secret, db_host, db_name, and db_user (and any other configuration/environment values) from the /api/health response body — health checks should return only minimal, non-sensitive status information (e.g., "ok"/"degraded"). Audit the codebase for other endpoints that may leak configuration or environment data. Restrict any endpoint that must return diagnostic/configuration data to authenticated internal callers or internal-network-only access, and add this endpoint to secret-scanning/CI checks to catch regressions.

### Evidence
```
GET http://100.96.0.19/api/health (no auth) returned HTTP 200 with body: {"success":true,"data":{"status":"ok","php_version":"8.3.31","server":"Apache/2.4.58 (Ubuntu)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"bankofed_app","jwt_secret":"Jj9XUzmBPzn8VcJEgzD9kC9koZTs1OV6XadreivDDrykIUuLimoQNqQnBdNE4Uv","environment":"production"},"message":"OK"} — exposing the live JWT signing secret and database connection details without authentication.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 4. SQL Injection via 'search' Parameter on /api/admin/customers (Unparameterized PDO Query, Full Error Disclosure)

- Severity: critical
- OWASP: A03
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/admin/customers?search=
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H)

### Description
The admin customer listing endpoint /api/admin/customers builds a raw SQL query by directly concatenating the 'search' query parameter into a PDO->query() call (AdminUserController.php, line 28) rather than using a parameterized/prepared statement. Injecting a single apostrophe and SQL metacharacters into the 'search' parameter breaks out of the intended query and is reflected back verbatim in the resulting MySQL syntax error, confirming the parameter is not sanitized or bound.

### Impact
An authenticated admin-level user (or an attacker who has obtained/compromised admin credentials) can manipulate the underlying SQL query to read, modify, or exfiltrate arbitrary data from the bankofed database, including customer PII, account balances, and password hashes, and potentially escalate via UNION-based extraction or stacked queries. The unhandled error response also discloses internal file paths, class/method names, and stack traces, which aid further exploitation of this and other endpoints.

### Likelihood
Confirmed. A single injected payload (test'; SELECT SLEEP(3)--) produced an unhandled MySQL syntax error with the injected query fragment reflected back, demonstrating direct concatenation into the SQL statement and exploitability by anyone with access to this admin endpoint.

### Recommendation
Refactor AdminUserController::index() to use PDO->prepare() with bound parameters for the 'search' filter instead of building the query via string concatenation and PDO->query(). Apply the same fix to any other endpoints using similar patterns. Disable verbose error/stack-trace disclosure in production; return a generic error message to clients and log detailed errors server-side only.

### Evidence
```
GET http://100.96.0.19/api/admin/customers?search=test%27%3B%20SELECT%20SLEEP(3)-- returned HTTP 500 with body: SQLSTATE[42000]: Syntax error ... near 'SELECT SLEEP(3)--%' OR last_name LIKE '%test'; SELECT SLEEP(3)--%' OR email LIKE' at line 1, plus stack trace showing PDO->query() called at /var/www/bankofed/src/Controllers/AdminUserController.php line 28.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 5. Business Logic Bypass — TOTP Step-Up Requirement for External Transfers Not Enforced Server-Side

- Severity: high
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/transfers/external
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N)

### Description
The application exposes a /api/transfers/check endpoint that evaluates whether a proposed external transfer requires TOTP step-up authentication (e.g., for manually-entered destination accounts not in the address book). However, the actual transfer execution endpoint, /api/transfers/external, does not independently enforce this requirement. It accepts and processes transfers without a totp_code parameter even when /transfers/check indicates requires_totp:true and the account has no TOTP configured, allowing the step-up control to be trivially bypassed by simply not calling the advisory check endpoint or ignoring its result.

### Impact
Any authenticated user or attacker with a valid session/token (obtained via any means, including XSS, token theft, or CSRF vulnerabilities present elsewhere in the application) can execute arbitrary-amount external transfers to any destination BSB/account number without providing the second factor the application itself flags as mandatory for manually-entered transfers. This defeats the step-up authentication control intended to protect large or non-address-book transfers, materially increasing the risk of unauthorized fund movement.

### Likelihood
Confirmed — reproduced by directly comparing /transfers/check output against a subsequent /transfers/external call using identical parameters and no totp_code field, resulting in a successful funds transfer.

### Recommendation
Enforce the TOTP requirement server-side within the /transfers/external (and /transfers/own, if applicable) handler itself rather than relying on the client to call /transfers/check first. The transfer execution endpoint should re-evaluate the same requires_totp logic and reject the request with a 403/422 if TOTP is required but no valid totp_code was supplied and verified. The check-and-enforce logic should be atomic and performed entirely server-side within the transaction path.

### Evidence
```
POST /api/transfers/check with {"amount":50000,"from_account_id":39,"to_account_number":"99999999","to_bsb":"062-001","transfer_type":"manual"} returned 200: {"success":true,"data":{"requires_totp":true,"reason":"manual_entry","totp_configured":false},"message":"OK"}. Immediately after, POST /api/transfers/external with the SAME parameters and NO totp_code field returned 201 Created: {"success":true,"data":{"transaction_id":37,"from_account_id":39,"to_bsb":"062-001","to_account_number":"99999999","amount":"50000","transfer_type":"manual","totp_verified":false,"new_from_balance":"999949949.00",...},"message":"Transfer completed successfully"}. The transfer succeeded despite the check endpoint declaring TOTP was required and the account never having TOTP configured.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 6. Missing Insufficient-Funds Check on External Transfers Allows Overdrafting Transaction Accounts

- Severity: high
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/transfers/external
- CVSS: 8.6 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N)

### Description
The external transfer endpoint (POST /api/transfers/external) does not validate that the source account holds sufficient funds before debiting it. Standard 'transaction' type accounts, which are not credit/loan products and should never carry a negative balance, can be debited below zero by any authenticated customer initiating a transfer, as the server processes the debit without checking the pre-transfer balance against the requested amount.

### Impact
Any authenticated customer can move arbitrary amounts of money out of a zero- or low-balance transaction account to an arbitrary external destination account/BSB, driving the source account into an unauthorized negative balance. This undermines the core money-movement logic of the application and could be abused to extract unbacked funds, commit accounting fraud, or launder money by transferring out funds with no real balance behind them.

### Likelihood
Confirmed — reproduced end-to-end by provisioning a fresh $0.00-balance transaction account and successfully executing a $500 external transfer from it, with no additional privileges or timing tricks required.

### Recommendation
Enforce a server-side balance check for all non-credit/non-loan account types prior to executing any debit operation (transfer, withdrawal, payment). Reject the request with an INSUFFICIENT_FUNDS error if the resulting balance would go negative for account_type not in ('loan','credit'). Perform the balance check and balance update atomically within a single database transaction using row-level locking (e.g., SELECT ... FOR UPDATE) to prevent race-condition double-spend exploitation.

### Evidence
```
Created a fresh transaction-type account (id=40) with $0.00 balance via POST /api/accounts. POST /api/transfers/external with {"amount":"500.00","from_account_id":40,"to_account_number":"99999999","to_bsb":"062-001"} returned 201 Created: {"success":true,"data":{"transaction_id":39,"from_account_id":40,"amount":"500.00","new_from_balance":"-500.00","status":"completed"},"message":"Transfer completed successfully"}. The transfer succeeded, leaving the account balance at -500.00 despite zero starting funds and a non-credit account type.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 7. SSRF via Avatar Import URL (/api/profile/avatar) — Internal Loopback and Arbitrary External Fetch Confirmed

- Severity: high
- OWASP: A10
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/profile/avatar
- CVSS: 8.6 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The avatar-import-by-URL feature at /api/profile/avatar accepts a user-supplied 'url' parameter and performs a server-side HTTP fetch of that URL, returning the fetched content (base64-encoded) to the requesting client. No validation is performed to restrict the destination to trusted image hosts, allowing the server to be used as an SSRF proxy against both internal and external targets.

### Impact
An authenticated attacker can force the backend to issue arbitrary outbound HTTP requests, including to internal-only/loopback addresses not reachable from the internet, and retrieve the response content. This enables: (1) access to internal-only services/endpoints and exfiltration of their responses, (2) potential pivoting to cloud metadata services or other internal APIs depending on network topology, and (3) internal network reconnaissance/port-scanning via differential success (200) vs FETCH_FAILED responses. In this environment it was confirmed to disclose the target's own internal web content via a loopback request.

### Likelihood
Confirmed and trivially reproducible — two distinct payloads (http://127.0.0.1:80/ and https://example.com) both returned 200 with the fetched remote/internal content verbatim in the response body, requiring only a low-privilege authenticated request with no user interaction.

### Recommendation
Implement strict allow-listing of permitted destination hosts/schemes for the avatar-import feature (e.g., only allow specific trusted image CDNs over HTTPS). Resolve the destination hostname to an IP and validate it is not within private/loopback/link-local/reserved ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, ::1) before issuing the server-side request, and re-validate after any redirects (disable or strictly limit redirect following). Enforce that only image content-types are fetched and stored, rejecting text/html and other non-image responses outright. Consider routing outbound fetches through a dedicated egress proxy with network-level restrictions to internal address ranges.

### Evidence
```
POST http://100.96.0.19/api/profile/avatar with body {"url":"http://127.0.0.1:80/"} returned 200 with base64-encoded avatar_data that decodes to the target's own banking marketing homepage HTML (title "The Bank of Ed - Banking Without Borders"), proving the server made an internal loopback HTTP request on behalf of the client. POST with body {"url":"https://example.com"} returned 200 with avatar_data decoding to the literal "Example Domain" IANA page content and source_url:"https://example.com", confirming the server fetches attacker-supplied URLs server-side and returns the fetched content to the client. AWS metadata endpoint (169.254.169.254) and port 22 returned FETCH_FAILED, suggesting either no route to that IP from this host or content-type/response filtering, but internal loopback fetch (127.0.0.1:80) was fully successful.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 8. Stored XSS via Unsanitized Transfer 'description' Field Rendered in Dashboard Recent Activity

- Severity: high
- OWASP: A03
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/banking/#/dashboard
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:N)

### Description
The transfer 'description' field accepted by /api/transfers/external (and /transfers/own) is stored server-side without HTML sanitization or encoding. When a transaction is later rendered on the Dashboard, banking/js/pages/dashboard.js's renderTransactions() function concatenates tx.description directly into an HTML string ('<p class="font-medium text-slate-900 truncate">' + (tx.description || tx.type) + '</p>') without calling the U.escapeHtml() helper that is used elsewhere in the same file for acc.account_name, acc.bsb, and acc.account_number. The resulting HTML string is then assigned via container.innerHTML, creating an unescaped DOM sink for attacker-controlled input.

### Impact
Any authenticated user can set a transfer description to arbitrary HTML/JavaScript. The payload executes in the browser session of anyone who subsequently views that transaction on their Dashboard — the sender, a recipient with a real internal to_account_id, or an admin/support user reviewing customer transaction history. Because the application stores its authentication JWT in localStorage (directly readable by injected script), successful exploitation enables theft of session tokens, account takeover, and unauthorized actions performed with the victim's valid session (e.g., initiating further transfers). This represents a critical-impact vector in a banking application, reachable entirely through a self-service field.

### Likelihood
Confirmed exploitable: the payload was successfully stored via the transfer API and persisted unescaped server-side, and the exact vulnerable client-side rendering code (unescaped concatenation into innerHTML) was located and reviewed in dashboard.js. Exploitation requires only that a victim (self, counterparty, or admin) view the transaction in the UI.

### Recommendation
In dashboard.js renderTransactions(), sanitize tx.description (and the tx.type fallback) with U.escapeHtml() before concatenating into the HTML string, consistent with the existing handling of acc.account_name/bsb/account_number in renderAccounts(). Apply the same fix to any other views that render transaction descriptions (transactions.js, accounts.js detail views, admin equivalents). Additionally, validate/encode the description field server-side at the API layer as defense-in-depth, and avoid storing the JWT in localStorage where it is reachable by injected script — prefer httpOnly, SameSite cookies for session tokens.

### Evidence
```
Server-side: POST http://100.96.0.19/api/transfers/external with body {"amount":10,"description":"<script>alert(document.domain)</script>","from_account_id":39,"to_account_number":"99999999","to_bsb":"062-001"} returned 201 with the payload echoed back completely unescaped; GET /api/transactions/38 confirmed the same raw payload persisted server-side. Client-side sink: dashboard.js renderTransactions() builds HTML via string concatenation '<p class="font-medium text-slate-900 truncate">' + (tx.description || tx.type) + '</p>' with no call to U.escapeHtml() (unlike acc.account_name, acc.bsb, acc.account_number in the same file), before assignment via container.innerHTML = html.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 9. Stored XSS via unsanitized transfer 'description' field rendered through innerHTML on Dashboard/Account pages

- Severity: high
- OWASP: A03
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/transfers/external
- CVSS: 8.7 (CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:N)

### Description
The external transfer creation endpoint (POST /api/transfers/external) accepts an arbitrary, unvalidated 'description' field and stores it verbatim, including HTML/JS payloads such as <script>alert(document.domain)</script>. The value is returned unescaped both in the transfer creation response and on subsequent reads (GET /api/transactions/:id). On the client, banking/js/pages/dashboard.js (renderTransactions) and banking/js/pages/accounts.js (account detail transaction table) concatenate tx.description directly into HTML strings that are assigned via .innerHTML, without calling the U.escapeHtml() helper that is used for other fields (e.g. account_name, bsb, account_number) in the same code. As a result, any user able to submit a transfer description controls script execution in the browser of anyone who later views the affected transaction history (transferring account, and potentially the receiving account depending on which account's history is rendered).

### Impact
An authenticated attacker can store a malicious script in a transfer description that executes in the context of any user's session (own or, depending on transaction-history visibility, the transfer recipient's) when they load the Dashboard (#/dashboard) or Account Detail (#/accounts/:id) page. Since this is a banking application, successful execution could exfiltrate the session token (bankofed_token, stored in browser storage) or other sensitive data, enabling session hijacking, unauthorized transfers performed as the victim, or broader account compromise.

### Likelihood
High. The injection point is reached through the standard, authenticated external transfer API with no special privileges or bypass required, and confirmed unsanitized on write, on read, and in the specific client-side rendering sinks (dashboard.js and accounts.js) that assign attacker-controlled content directly to .innerHTML.

### Recommendation
1. Sanitize/validate the description field server-side on write (HTML-encode or strip angle brackets; consider a strict allow-list of characters such as alphanumeric, spaces, and basic punctuation). 2. Client-side, apply the existing U.escapeHtml() helper to tx.description before concatenating it into innerHTML strings in dashboard.js and accounts.js, consistent with how other fields (account_name, bsb, account_number) are already handled, or refactor rendering to use textContent/DOM APIs instead of innerHTML string concatenation for any user-controlled value. 3. Audit and apply the same escaping to every other page/component that renders tx.description (transaction lists, statements, notifications, exports).

### Evidence
```
Write: POST /api/transfers/external with description="<script>alert(document.domain)</script>" returned 201 with the payload stored and returned raw/unescaped. Read: GET /api/transactions/38 returned the same unescaped payload, confirming no server-side output encoding. Client-side sinks: dashboard.js renderTransactions() and accounts.js account-detail transaction table both concatenate tx.description directly into HTML strings assigned to .innerHTML, without the U.escapeHtml() call used for other fields in the same files, confirming an exploitable stored XSS chain from write to render.
```

### Request Evidence
```
POST /api/transfers/external HTTP/1.1
{"amount":10,"description":"<script>alert(document.domain)</script>","from_account_id":39,"to_account_number":"99999999","to_bsb":"062-001"}
```

### Response Evidence
```
{"success":true,"data":{"transaction_id":38,...,"description":"<script>alert(document.domain)<\/script>",...},"message":"Transfer completed successfully"}
GET /api/transactions/38 -> {"success":true,"data":{"id":38,...,"description":"<script>alert(document.domain)<\/script>",...},"message":"OK"}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 10. Password Hash and TOTP Secret Fields Exposed in Registration API Response

- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/auth/register
- CVSS: 5.3 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The registration endpoint at /api/auth/register returns the full user object in its response, including the password_hash and totp_secret fields. These credential-related fields should be stripped server-side before serialization and never transmitted to the client. The exposed password_hash is a 32-character hexadecimal string with no visible salt, consistent with an unsalted MD5 hash, indicating weak server-side password hashing in addition to the unnecessary exposure.

### Impact
Returning password_hash and totp_secret to the client unnecessarily increases the attack surface for credential compromise: the value can be captured via logs, proxies, browser history/cache, or any man-in-the-middle position, and — because the hash appears to be unsalted MD5 — it would be trivially crackable offline if obtained. If this same serialization behavior is present on other endpoints that return other users' records (e.g. profile or admin endpoints), an attacker could harvest password hashes at scale for offline cracking. In the confirmed case, only the requesting user's own hash was observed being disclosed.

### Likelihood
Confirmed — password_hash and totp_secret were observed directly in the registration API response for a freshly created test account. Broader impact (harvesting other users' hashes) would require an additional read primitive such as an IDOR, which was not demonstrated as part of this finding.

### Recommendation
Remove password_hash, totp_secret, and any other credential/secret fields from all API response payloads (registration, login, profile, admin) by enforcing an explicit allow-list serializer/DTO for user-facing objects rather than returning ORM/database objects directly. Replace the password hashing scheme with a strong adaptive algorithm (bcrypt, scrypt, or Argon2) using a unique per-user salt, and rehash existing credentials during the next password change or a forced reset. Audit all endpoints that return user objects for similar over-exposure of sensitive fields.

### Evidence
```
POST http://100.96.0.19/api/auth/register returned 201 with body: {"success":true,"data":{"user":{"id":16,"email":"aespa_4992abe4@example.invalid",...,"password_hash":"ac3d2a6c23e811af791469aa6c772cd6","totp_secret":null},"token":"[JWT]"},"message":"Registration successful"}. The password_hash is a 32-hex-char string consistent with unsalted MD5.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 11. Sensitive data exposed in API response

- Severity: medium
- OWASP: A02
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/health
- CVSS: 6.5

### Description
The response contains field names commonly associated with secrets, hashes, tokens, debug state, or privileged metadata.

### Impact
Attackers can use leaked secrets or implementation details to compromise accounts or chain further attacks.

### Likelihood
Confirmed by deterministic response analysis.

### Recommendation
Remove sensitive fields from client-facing responses and enforce response DTO allow-lists.

### Evidence
```
REQUEST:
GET http://100.96.0.19/api/health
use_session: (default)  Cookies: none
{}

RESPONSE:
Status: 200
date: Wed, 01 Jul 2026 05:16:38 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 286
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8
server-timing: cfReqDur;dur=7.994
cf-team: 2fbdb4b008000483be005c9400000001

{"success":true,"data":{"status":"ok","php_version":"8.3.31","server":"Apache\/2.4.58 (Ubuntu)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"bankofed_app","jwt_secret":"Jj9XUzmBPzn8VcJEgzD9kC9koZTs1OV6XadreivDDrykIUuLimoQNqQnBdNE4Uv","environment":"production"},"message":"OK"}
```

### Request Evidence
```
GET http://100.96.0.19/api/health
use_session: (default)  Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Wed, 01 Jul 2026 05:16:38 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 286
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8
server-timing: cfReqDur;dur=7.994
cf-team: 2fbdb4b008000483be005c9400000001

{"success":true,"data":{"status":"ok","php_version":"8.3.31","server":"Apache\/2.4.58 (Ubuntu)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"bankofed_app","jwt_secret":"Jj9XUzmBPzn8VcJEgzD9kC9koZTs1OV6XadreivDDrykIUuLimoQNqQnBdNE4Uv","environment":"production"},"message":"OK"}
```

### Validation Note
Confirmed by deterministic module.

## 12. Sensitive data exposed in API response

- Severity: medium
- OWASP: A02
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/auth/register
- CVSS: 6.5

### Description
The response contains field names commonly associated with secrets, hashes, tokens, debug state, or privileged metadata.

### Impact
Attackers can use leaked secrets or implementation details to compromise accounts or chain further attacks.

### Likelihood
Confirmed by deterministic response analysis.

### Recommendation
Remove sensitive fields from client-facing responses and enforce response DTO allow-lists.

### Evidence
```
REQUEST:
REGISTER_ACCOUNT http://100.96.0.19/api/auth/register

RESPONSE:
Status: 201
{"success":true,"data":{"user":{"id":16,"email":"aespa_4992abe4@example.invalid","first_name":"Test","last_name":"User","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"ac3d2a6c23e811af791469aa6c772cd6","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Registration successful"}
```

### Request Evidence
```
REGISTER_ACCOUNT http://100.96.0.19/api/auth/register
```

### Response Evidence
```
Status: 201
{"success":true,"data":{"user":{"id":16,"email":"aespa_4992abe4@example.invalid","first_name":"Test","last_name":"User","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"ac3d2a6c23e811af791469aa6c772cd6","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Registration successful"}
```

### Validation Note
Confirmed by deterministic module.

## 13. Sensitive data exposed in API response

- Severity: medium
- OWASP: A02
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/profile
- CVSS: 6.5

### Description
The response contains field names commonly associated with secrets, hashes, tokens, debug state, or privileged metadata.

### Impact
Attackers can use leaked secrets or implementation details to compromise accounts or chain further attacks.

### Likelihood
Confirmed by deterministic response analysis.

### Recommendation
Remove sensitive fields from client-facing responses and enforce response DTO allow-lists.

### Evidence
```
REQUEST:
GET http://100.96.0.19/api/profile
use_session: victim1  Cookies: none
{}

RESPONSE:
Status: 200
date: Wed, 01 Jul 2026 05:20:10 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 335
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8
server-timing: cfReqDur;dur=12.659
cf-team: 2fbdb7ed4f000483be0a45a400000001

{"success":true,"data":{"id":16,"email":"aespa_4992abe4@example.invalid","first_name":"Test","last_name":"User","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"ac3d2a6c23e811af791469aa6c772cd6","totp_secret":null},"message":"OK"}
```

### Request Evidence
```
GET http://100.96.0.19/api/profile
use_session: victim1  Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Wed, 01 Jul 2026 05:20:10 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 335
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8
server-timing: cfReqDur;dur=12.659
cf-team: 2fbdb7ed4f000483be0a45a400000001

{"success":true,"data":{"id":16,"email":"aespa_4992abe4@example.invalid","first_name":"Test","last_name":"User","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"ac3d2a6c23e811af791469aa6c772cd6","totp_secret":null},"message":"OK"}
```

### Validation Note
Confirmed by deterministic module.

## 14. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/admin/js/app.js
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/admin/js/app.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Mon, 16 Feb 2026 08:52:02 GMT
etag: "806-64aed11869080-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 728
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=6.604
cf-team: 2fbdb47e76000483beffe63400000001

/**
 * BankOfEd Admin - App Bootstrap
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.App = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;
  var Router = BankOfEdAdmin.Router;

  function init() {
    Router.addRoute('/login', function () { BankOfEdAdmin.AuthPage.show(); }, { auth: false });
    Router.addRoute('/customers', function () { BankOfEdAdmin.CustomersPage.show(); });
    Router.addRoute('/customers/:id', function (params) { BankOfEdAdmin.CustomersPage.showDetail(params); });
    Router.addRoute('/accounts', function () { BankOfEdAdmin.AccountsPage.show(); });
    Router.addRoute('/fx-rates', function () { BankOfEdAdmin.FxRatesPage.show(); });
    Router.addRoute('/system', function () { BankOfEdAdmin.SystemPage.show(); });

    if (Api.isLoggedIn()) updateSidebar();
    Router.start();
  }

  function updateSidebar() {
    var admin = Api.getAdmin();
    if (!admin) return;
    var avatar = U.$('sidebar-avatar');
    var name = U.$('sidebar-admin-name');
    if (avatar) avatar.textContent = (admin.username || 'A')[0].toUpperCase();
    if (name) name.textContent = admin.username || 'Admin';
  }

  function toggleSidebar() {
    var sidebar = U.$('sidebar');
    var overlay = U.$('sidebar-overlay');
    if (sidebar.classList.contains('-translate-x-full')) {
      sidebar.classList.remove('-translate-x-full');
      overlay.classList.remove('hidden');
    } else {
      sidebar.classList.add('-translate-x-full');
      overlay.classList.add('hidden');
    }
  }

  function logout() {
    Api.logout().catch(function () {}).finally(function () {
      Api.clearToken(); Api.clearAdmin();
      U.toast('Signed out.', 'info');
      window.location.hash = '#/login';
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  return { init: init, updateSidebar: updateSidebar, to
```

### Request Evidence
```
GET http://100.96.0.19/admin/js/app.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Mon, 16 Feb 2026 08:52:02 GMT
etag: "806-64aed11869080-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 728
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=6.604
cf-team: 2fbdb47e76000483beffe63400000001

/**
 * BankOfEd Admin - App Bootstrap
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.App = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;
  var Router = BankOfEdAdmin.Router;

  function init() {
    Router.addRoute('/login', function () { BankOfEdAdmin.AuthPage.show(); }, { auth: false });
    Router.addRoute('/customers', function () { BankOfEdAdmin.CustomersPage.show(); });
    Router.addRoute('/customers/:id', function (params) { BankOfEdAdmin.CustomersPage.showDetail(params); });
    Router.addRoute('/accounts', function () { BankOfEdAdmin.AccountsPage.show(); });
    Router.addRoute('/fx-rates', function () { BankOfEdAdmin.FxRatesPage.show(); });
    Router.addRoute('/system', function () { BankOfEdAdmin.SystemPage.show(); });

    if (Api.isLoggedIn()) updateSidebar();
    Router.start();
  }

  function updateSidebar() {
    var admin = Api.getAdmin();
    if (!admin) return;
    var avatar = U.$('sidebar-avatar');
    var name = U.$('sidebar-admin-name');
    if (avatar) avatar.textContent = (admin.username || 'A')[0].toUpperCase();
    if (name) name.textContent = admin.username || 'Admin';
  }

  function toggleSidebar() {
    var sidebar = U.$('sidebar');
    var overlay = U.$('sidebar-overlay');
    if (sidebar.classList.contains('-translate-x-full')) {
      sidebar.classList.remove('-translate-x-full');
      overlay.classList.remove('hidden');
    } else {
      sidebar.classList.add('-translate-x-full');
      overlay.classList.add('hidden');
    }
  }

  function logout() {
    Api.logout().catch(function () {}).finally(function () {
      Api.clearToken(); Api.clearAdmin();
      U.toast('Signed out.', 'info');
      window.location.hash = '#/login';
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  return { init: init, updateSidebar: updateSidebar, to
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 15. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/admin/js/pages/accounts.js
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/admin/js/pages/accounts.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "18a2-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 2048
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=7.805
cf-team: 2fbdb47ecb000483beffe6f400000001

/**
 * BankOfEd Admin - Accounts Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.AccountsPage = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;
  var currentPage = 1;

  function show() {
    BankOfEdAdmin.Router.showPage('accounts', 'accounts');
    currentPage = 1;
    loadAccounts();
  }

  function loadAccounts() {
    Api.getAccounts({ page: currentPage, per_page: 20 }).then(function (res) {
      renderTable(res.data.accounts || []);
      renderPagination(res.data.pagination || {});
    }).catch(function () {
      U.toast('Failed to load accounts.', 'error');
    });
  }

  function renderTable(accounts) {
    var container = U.$('accounts-table');
    if (!accounts.length) {
      container.innerHTML = '<div class="p-8 text-center text-dark-400">No accounts found</div>';
      return;
    }

    var html = '<div class="overflow-x-auto"><table class="w-full text-sm">' +
      '<thead><tr class="text-left text-xs text-dark-400 uppercase tracking-wide border-b border-dark-100">' +
      '<th class="px-6 py-3">ID</th><th class="px-6 py-3">Owner</th><th class="px-6 py-3">Account</th>' +
      '<th class="px-6 py-3">Type</th><th class="px-6 py-3 text-right">Balance</th><th class="px-6 py-3 text-right">Actions</th>' +
      '</tr></thead><tbody>';

    accounts.forEach(function (a) {
      var badgeCls = a.account_type === 'loan' ? 'badge-loan' : 'badge-transaction';
      var balColor = parseFloat(a.balance) >= 0 ? 'text-dark-900' : 'text-red-600';
      html += '<tr class="tx-row border-b border-dark-50">' +
        '<td class="px-6 py-3.5 text-dark-400 font-mono text-xs">#' + a.id + '</td>' +
        '<td class="px-6 py-3.5"><span class="font-medium text-dark-900">' + U.escapeHtml((a.owner_first_name || '') + ' ' + (a.owner_last_name || '')) + '</span><br><span class="text-xs text-dark-400">' + U.escapeHtml(a.owner_email) + '</span></td>' +
```

### Request Evidence
```
GET http://100.96.0.19/admin/js/pages/accounts.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "18a2-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 2048
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=7.805
cf-team: 2fbdb47ecb000483beffe6f400000001

/**
 * BankOfEd Admin - Accounts Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.AccountsPage = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;
  var currentPage = 1;

  function show() {
    BankOfEdAdmin.Router.showPage('accounts', 'accounts');
    currentPage = 1;
    loadAccounts();
  }

  function loadAccounts() {
    Api.getAccounts({ page: currentPage, per_page: 20 }).then(function (res) {
      renderTable(res.data.accounts || []);
      renderPagination(res.data.pagination || {});
    }).catch(function () {
      U.toast('Failed to load accounts.', 'error');
    });
  }

  function renderTable(accounts) {
    var container = U.$('accounts-table');
    if (!accounts.length) {
      container.innerHTML = '<div class="p-8 text-center text-dark-400">No accounts found</div>';
      return;
    }

    var html = '<div class="overflow-x-auto"><table class="w-full text-sm">' +
      '<thead><tr class="text-left text-xs text-dark-400 uppercase tracking-wide border-b border-dark-100">' +
      '<th class="px-6 py-3">ID</th><th class="px-6 py-3">Owner</th><th class="px-6 py-3">Account</th>' +
      '<th class="px-6 py-3">Type</th><th class="px-6 py-3 text-right">Balance</th><th class="px-6 py-3 text-right">Actions</th>' +
      '</tr></thead><tbody>';

    accounts.forEach(function (a) {
      var badgeCls = a.account_type === 'loan' ? 'badge-loan' : 'badge-transaction';
      var balColor = parseFloat(a.balance) >= 0 ? 'text-dark-900' : 'text-red-600';
      html += '<tr class="tx-row border-b border-dark-50">' +
        '<td class="px-6 py-3.5 text-dark-400 font-mono text-xs">#' + a.id + '</td>' +
        '<td class="px-6 py-3.5"><span class="font-medium text-dark-900">' + U.escapeHtml((a.owner_first_name || '') + ' ' + (a.owner_last_name || '')) + '</span><br><span class="text-xs text-dark-400">' + U.escapeHtml(a.owner_email) + '</span></td>' +
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 16. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/admin/js/pages/auth.js
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/admin/js/pages/auth.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "3de-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 484
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=8.032
cf-team: 2fbdb47f20000483beffe87400000001

/**
 * BankOfEd Admin - Auth Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.AuthPage = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;

  function show() { BankOfEdAdmin.Router.showPage('auth'); }

  function handleLogin(e) {
    e.preventDefault();
    var form = e.target;
    var btn = form.querySelector('button[type="submit"]');
    var data = U.getFormData(form);
    U.showErrors('login-errors', null);
    U.setButtonLoading(btn, true);

    Api.login(data).then(function (res) {
      Api.setToken(res.data.token);
      Api.setAdmin(res.data.admin);
      U.toast('Welcome, ' + res.data.admin.username + '!', 'success');
      window.location.hash = '#/customers';
    }).catch(function (err) {
      U.showErrors('login-errors', err);
    }).finally(function () {
      U.setButtonLoading(btn, false);
    });
  }

  return { show: show, handleLogin: handleLogin };
})();
```

### Request Evidence
```
GET http://100.96.0.19/admin/js/pages/auth.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "3de-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 484
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=8.032
cf-team: 2fbdb47f20000483beffe87400000001

/**
 * BankOfEd Admin - Auth Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.AuthPage = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;

  function show() { BankOfEdAdmin.Router.showPage('auth'); }

  function handleLogin(e) {
    e.preventDefault();
    var form = e.target;
    var btn = form.querySelector('button[type="submit"]');
    var data = U.getFormData(form);
    U.showErrors('login-errors', null);
    U.setButtonLoading(btn, true);

    Api.login(data).then(function (res) {
      Api.setToken(res.data.token);
      Api.setAdmin(res.data.admin);
      U.toast('Welcome, ' + res.data.admin.username + '!', 'success');
      window.location.hash = '#/customers';
    }).catch(function (err) {
      U.showErrors('login-errors', err);
    }).finally(function () {
      U.setButtonLoading(btn, false);
    });
  }

  return { show: show, handleLogin: handleLogin };
})();
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 17. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/admin/js/pages/customers.js
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/admin/js/pages/customers.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "3d8c-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 3617
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=8.748
cf-team: 2fbdb47f77000483beffea0400000001

/**
 * BankOfEd Admin - Customers Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.CustomersPage = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;
  var currentPage = 1;
  var searchTerm = '';
  var searchTimer = null;

  function show() {
    BankOfEdAdmin.Router.showPage('customers', 'customers');
    currentPage = 1;
    searchTerm = '';
    var searchInput = U.$('customer-search');
    if (searchInput) searchInput.value = '';
    loadCustomers();
  }

  function handleSearch(e) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      searchTerm = e.target.value;
      currentPage = 1;
      loadCustomers();
    }, 300);
  }

  function loadCustomers() {
    Api.getCustomers({ page: currentPage, per_page: 15, search: searchTerm }).then(function (res) {
      renderTable(res.data.customers || []);
      renderPagination(res.data.pagination || {});
    }).catch(function () {
      U.toast('Failed to load customers.', 'error');
    });
  }

  function renderTable(customers) {
    var container = U.$('customers-table');
    if (!customers.length) {
      container.innerHTML = '<div class="p-8 text-center text-dark-400">No customers found</div>';
      return;
    }

    var html = '<div class="overflow-x-auto"><table class="w-full text-sm">' +
      '<thead><tr class="text-left text-xs text-dark-400 uppercase tracking-wide border-b border-dark-100">' +
      '<th class="px-6 py-3">ID</th><th class="px-6 py-3">Name</th><th class="px-6 py-3">Email</th>' +
      '<th class="px-6 py-3">Accounts</th><th class="px-6 py-3">2FA</th><th class="px-6 py-3">Joined</th>' +
      '<th class="px-6 py-3 text-right">Actions</th></tr></thead><tbody>';

    customers.forEach(function (c) {
      var twofaBadge = c.totp_enabled
        ? '<span class="inline-flex items-center gap-1 text-green-600 text-xs font-semibold"><svg class="w-3.5 h
```

### Request Evidence
```
GET http://100.96.0.19/admin/js/pages/customers.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "3d8c-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 3617
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=8.748
cf-team: 2fbdb47f77000483beffea0400000001

/**
 * BankOfEd Admin - Customers Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.CustomersPage = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;
  var currentPage = 1;
  var searchTerm = '';
  var searchTimer = null;

  function show() {
    BankOfEdAdmin.Router.showPage('customers', 'customers');
    currentPage = 1;
    searchTerm = '';
    var searchInput = U.$('customer-search');
    if (searchInput) searchInput.value = '';
    loadCustomers();
  }

  function handleSearch(e) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      searchTerm = e.target.value;
      currentPage = 1;
      loadCustomers();
    }, 300);
  }

  function loadCustomers() {
    Api.getCustomers({ page: currentPage, per_page: 15, search: searchTerm }).then(function (res) {
      renderTable(res.data.customers || []);
      renderPagination(res.data.pagination || {});
    }).catch(function () {
      U.toast('Failed to load customers.', 'error');
    });
  }

  function renderTable(customers) {
    var container = U.$('customers-table');
    if (!customers.length) {
      container.innerHTML = '<div class="p-8 text-center text-dark-400">No customers found</div>';
      return;
    }

    var html = '<div class="overflow-x-auto"><table class="w-full text-sm">' +
      '<thead><tr class="text-left text-xs text-dark-400 uppercase tracking-wide border-b border-dark-100">' +
      '<th class="px-6 py-3">ID</th><th class="px-6 py-3">Name</th><th class="px-6 py-3">Email</th>' +
      '<th class="px-6 py-3">Accounts</th><th class="px-6 py-3">2FA</th><th class="px-6 py-3">Joined</th>' +
      '<th class="px-6 py-3 text-right">Actions</th></tr></thead><tbody>';

    customers.forEach(function (c) {
      var twofaBadge = c.totp_enabled
        ? '<span class="inline-flex items-center gap-1 text-green-600 text-xs font-semibold"><svg class="w-3.5 h
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 18. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/admin/js/pages/fx-rates.js
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/admin/js/pages/fx-rates.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Mon, 16 Feb 2026 08:49:41 GMT
etag: "2876-64aed091f1340-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 2247
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=7.332
cf-team: 2fbdb47fce000483beffeb0400000001

/**
 * BankOfEd Admin - FX Rates Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.FxRatesPage = (function () {
  'use strict';

  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;

  function show() {
    BankOfEdAdmin.Router.showPage('fx-rates', 'fx-rates');
    loadRates();
  }

  function loadRates() {
    Api.getFxRates().then(function (res) {
      var rates = Array.isArray(res.data) ? res.data : [];
      renderTable(rates);
    }).catch(function () {
      U.toast('Failed to load FX rates.', 'error');
    });
  }

  function renderTable(rates) {
    var container = U.$('fx-rates-table');
    if (!rates.length) {
      container.innerHTML = '<div class="p-8 text-center text-dark-400">No FX rates configured yet.</div>';
      return;
    }

    var html = '<div class="table-scroll"><table class="w-full text-sm">' +
      '<thead><tr class="text-left text-xs text-dark-400 uppercase tracking-wide border-b border-dark-100">' +
        '<th class="px-6 py-3">Currency</th>' +
        '<th class="px-6 py-3">Name</th>' +
        '<th class="px-6 py-3 text-right">Rate to USD</th>' +
        '<th class="px-6 py-3">Updated</th>' +
        '<th class="px-6 py-3 text-right">Actions</th>' +
      '</tr></thead><tbody>';

    rates.forEach(function (rate) {
      html +=
        '<tr class="border-b border-dark-50 hover:bg-dark-50/50">' +
          '<td class="px-6 py-3.5"><span class="font-mono font-semibold text-dark-900">' + U.escapeHtml(rate.currency_code) + '</span></td>' +
          '<td class="px-6 py-3.5 text-dark-600">' + U.escapeHtml(rate.currency_name) + '</td>' +
          '<td class="px-6 py-3.5 text-right font-mono text-dark-900">' + Number(rate.rate_to_usd).toFixed(8) + '</td>' +
          '<td class="px-6 py-3.5 text-dark-400 text-xs">' + U.formatDateTime(rate.updated_at) + '</td>' +
          '<td class="px-6 py-3.5 text-right">' +
            '<button onclick="BankOfEdAdmin
```

### Request Evidence
```
GET http://100.96.0.19/admin/js/pages/fx-rates.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:25 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Mon, 16 Feb 2026 08:49:41 GMT
etag: "2876-64aed091f1340-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 2247
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=7.332
cf-team: 2fbdb47fce000483beffeb0400000001

/**
 * BankOfEd Admin - FX Rates Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.FxRatesPage = (function () {
  'use strict';

  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;

  function show() {
    BankOfEdAdmin.Router.showPage('fx-rates', 'fx-rates');
    loadRates();
  }

  function loadRates() {
    Api.getFxRates().then(function (res) {
      var rates = Array.isArray(res.data) ? res.data : [];
      renderTable(rates);
    }).catch(function () {
      U.toast('Failed to load FX rates.', 'error');
    });
  }

  function renderTable(rates) {
    var container = U.$('fx-rates-table');
    if (!rates.length) {
      container.innerHTML = '<div class="p-8 text-center text-dark-400">No FX rates configured yet.</div>';
      return;
    }

    var html = '<div class="table-scroll"><table class="w-full text-sm">' +
      '<thead><tr class="text-left text-xs text-dark-400 uppercase tracking-wide border-b border-dark-100">' +
        '<th class="px-6 py-3">Currency</th>' +
        '<th class="px-6 py-3">Name</th>' +
        '<th class="px-6 py-3 text-right">Rate to USD</th>' +
        '<th class="px-6 py-3">Updated</th>' +
        '<th class="px-6 py-3 text-right">Actions</th>' +
      '</tr></thead><tbody>';

    rates.forEach(function (rate) {
      html +=
        '<tr class="border-b border-dark-50 hover:bg-dark-50/50">' +
          '<td class="px-6 py-3.5"><span class="font-mono font-semibold text-dark-900">' + U.escapeHtml(rate.currency_code) + '</span></td>' +
          '<td class="px-6 py-3.5 text-dark-600">' + U.escapeHtml(rate.currency_name) + '</td>' +
          '<td class="px-6 py-3.5 text-right font-mono text-dark-900">' + Number(rate.rate_to_usd).toFixed(8) + '</td>' +
          '<td class="px-6 py-3.5 text-dark-400 text-xs">' + U.formatDateTime(rate.updated_at) + '</td>' +
          '<td class="px-6 py-3.5 text-right">' +
            '<button onclick="BankOfEdAdmin
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 19. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/admin/js/pages/system.js
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/admin/js/pages/system.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:26 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "3fc-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 449
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=6.566
cf-team: 2fbdb48024000483beffec3400000001

/**
 * BankOfEd Admin - System Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.SystemPage = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;

  function show() {
    BankOfEdAdmin.Router.showPage('system', 'system');
    var input = U.$('reset-confirm-input');
    if (input) input.value = '';
  }

  function handleReset() {
    var input = U.$('reset-confirm-input');
    if (!input || input.value !== 'RESET') {
      U.toast('Please type RESET to confirm.', 'warning');
      return;
    }

    var btn = U.$('reset-btn');
    U.setButtonLoading(btn, true);

    Api.resetDatabase().then(function () {
      input.value = '';
      U.toast('Database reset successfully!', 'success');
    }).catch(function (err) {
      U.toast(err.message || 'Reset failed.', 'error');
    }).finally(function () {
      U.setButtonLoading(btn, false);
    });
  }

  return { show: show, handleReset: handleReset };
})();
```

### Request Evidence
```
GET http://100.96.0.19/admin/js/pages/system.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:26 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "3fc-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 449
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=6.566
cf-team: 2fbdb48024000483beffec3400000001

/**
 * BankOfEd Admin - System Page
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.SystemPage = (function () {
  'use strict';
  var U = BankOfEdAdmin.Utils;
  var Api = BankOfEdAdmin.Api;

  function show() {
    BankOfEdAdmin.Router.showPage('system', 'system');
    var input = U.$('reset-confirm-input');
    if (input) input.value = '';
  }

  function handleReset() {
    var input = U.$('reset-confirm-input');
    if (!input || input.value !== 'RESET') {
      U.toast('Please type RESET to confirm.', 'warning');
      return;
    }

    var btn = U.$('reset-btn');
    U.setButtonLoading(btn, true);

    Api.resetDatabase().then(function () {
      input.value = '';
      U.toast('Database reset successfully!', 'success');
    }).catch(function (err) {
      U.toast(err.message || 'Reset failed.', 'error');
    }).finally(function () {
      U.setButtonLoading(btn, false);
    });
  }

  return { show: show, handleReset: handleReset };
})();
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 20. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/admin/js/router.js
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/admin/js/router.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:26 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "927-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 901
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=7.635
cf-team: 2fbdb48077000483beffed2400000001

/**
 * BankOfEd Admin - Router
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.Router = (function () {
  'use strict';

  var routes = [];

  function addRoute(pattern, handler, options) {
    options = options || {};
    var keys = [];
    var re = pattern.replace(/:([^/]+)/g, function (_, key) { keys.push(key); return '([^/]+)'; });
    routes.push({ regex: new RegExp('^' + re + '$'), keys: keys, handler: handler, auth: options.auth !== false });
  }

  function navigate(hash) { window.location.hash = hash; }

  function resolve() {
    var hash = window.location.hash.slice(1) || '/login';
    for (var i = 0; i < routes.length; i++) {
      var route = routes[i];
      var match = hash.match(route.regex);
      if (match) {
        if (route.auth && !BankOfEdAdmin.Api.isLoggedIn()) { navigate('#/login'); return; }
        if (!route.auth && BankOfEdAdmin.Api.isLoggedIn() && hash === '/login') { navigate('#/customers'); return; }
        var params = {};
        route.keys.forEach(function (key, idx) { params[key] = match[idx + 1]; });
        route.handler(params);
        return;
      }
    }
    navigate(BankOfEdAdmin.Api.isLoggedIn() ? '#/customers' : '#/login');
  }

  function showPage(pageId, navKey) {
    document.querySelectorAll('[id^="page-"]').forEach(function (p) { p.classList.add('hidden'); });
    var page = document.getElementById('page-' + pageId);
    if (page) { page.classList.remove('hidden'); page.classList.add('page-fade-in'); setTimeout(function () { page.classList.remove('page-fade-in'); }, 250); }

    var viewAuth = document.getElementById('view-auth');
    var appShell = document.getElementById('app-shell');
    if (pageId === 'auth') { viewAuth.classList.remove('hidden'); appShell.classList.add('hidden'); }
    else { viewAuth.classList.add('hidden'); appShell.classList.remove('hidden'); }

    if (navKey) {
      document.querySelectorAll('.nav-link').forEach(function
```

### Request Evidence
```
GET http://100.96.0.19/admin/js/router.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:26 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "927-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 901
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=7.635
cf-team: 2fbdb48077000483beffed2400000001

/**
 * BankOfEd Admin - Router
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.Router = (function () {
  'use strict';

  var routes = [];

  function addRoute(pattern, handler, options) {
    options = options || {};
    var keys = [];
    var re = pattern.replace(/:([^/]+)/g, function (_, key) { keys.push(key); return '([^/]+)'; });
    routes.push({ regex: new RegExp('^' + re + '$'), keys: keys, handler: handler, auth: options.auth !== false });
  }

  function navigate(hash) { window.location.hash = hash; }

  function resolve() {
    var hash = window.location.hash.slice(1) || '/login';
    for (var i = 0; i < routes.length; i++) {
      var route = routes[i];
      var match = hash.match(route.regex);
      if (match) {
        if (route.auth && !BankOfEdAdmin.Api.isLoggedIn()) { navigate('#/login'); return; }
        if (!route.auth && BankOfEdAdmin.Api.isLoggedIn() && hash === '/login') { navigate('#/customers'); return; }
        var params = {};
        route.keys.forEach(function (key, idx) { params[key] = match[idx + 1]; });
        route.handler(params);
        return;
      }
    }
    navigate(BankOfEdAdmin.Api.isLoggedIn() ? '#/customers' : '#/login');
  }

  function showPage(pageId, navKey) {
    document.querySelectorAll('[id^="page-"]').forEach(function (p) { p.classList.add('hidden'); });
    var page = document.getElementById('page-' + pageId);
    if (page) { page.classList.remove('hidden'); page.classList.add('page-fade-in'); setTimeout(function () { page.classList.remove('page-fade-in'); }, 250); }

    var viewAuth = document.getElementById('view-auth');
    var appShell = document.getElementById('app-shell');
    if (pageId === 'auth') { viewAuth.classList.remove('hidden'); appShell.classList.add('hidden'); }
    else { viewAuth.classList.add('hidden'); appShell.classList.remove('hidden'); }

    if (navKey) {
      document.querySelectorAll('.nav-link').forEach(function
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 21. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/admin/js/utils.js
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/admin/js/utils.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:26 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "f5a-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 1412
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=7.338
cf-team: 2fbdb480cb000483beffede400000001

/**
 * BankOfEd Admin - Utilities
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.Utils = (function () {
  'use strict';

  var currencyFmt = new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' });

  function formatCurrency(amount) { return currencyFmt.format(Number(amount) || 0); }

  function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  var escMap = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  function escapeHtml(str) {
    return String(str || '').replace(/[&<>"']/g, function (c) { return escMap[c]; });
  }

  function toast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    var colors = { success: 'bg-green-600', error: 'bg-red-600', info: 'bg-dark-700', warning: 'bg-amber-500' };
    var el = document.createElement('div');
    el.className = 'toast-enter flex items-center gap-3 px-5 py-3.5 rounded-xl text-white shadow-lg text-sm max-w-sm ' + (colors[type] || colors.info);
    el.innerHTML = '<span>' + escapeHtml(message) + '</span>';
    container.appendChild(el);
    setTimeout(function () {
      el.classList.remove('toast-enter');
      el.classList.add('toast-exit');
      el.addEventListener('animationend', function () { el.remove(); });
    }, 3500);
  }

  function openModal(html) {
    var overlay = document.getElementById('modal-overlay');
    document.getElementById('modal-content').innerHTML = html;
    overlay.classList.remove('hidden');
    requestAnimationFrame(function () { overlay.classList.add('show'); });
    overlay.onclick = function (e) { if (e.target === overlay) closeModal(); };
    document._modalEsc = function (e) { if (e.key === 'Escape') closeModal(); };
    document.addEventListener('keydown', document._modalEsc);
  }

  function closeModal() {
```

### Request Evidence
```
GET http://100.96.0.19/admin/js/utils.js HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:26 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Fri, 13 Feb 2026 09:37:38 GMT
etag: "f5a-64ab15b147c80-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 1412
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=7.338
cf-team: 2fbdb480cb000483beffede400000001

/**
 * BankOfEd Admin - Utilities
 */
window.BankOfEdAdmin = window.BankOfEdAdmin || {};

BankOfEdAdmin.Utils = (function () {
  'use strict';

  var currencyFmt = new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' });

  function formatCurrency(amount) { return currencyFmt.format(Number(amount) || 0); }

  function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  var escMap = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  function escapeHtml(str) {
    return String(str || '').replace(/[&<>"']/g, function (c) { return escMap[c]; });
  }

  function toast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    var colors = { success: 'bg-green-600', error: 'bg-red-600', info: 'bg-dark-700', warning: 'bg-amber-500' };
    var el = document.createElement('div');
    el.className = 'toast-enter flex items-center gap-3 px-5 py-3.5 rounded-xl text-white shadow-lg text-sm max-w-sm ' + (colors[type] || colors.info);
    el.innerHTML = '<span>' + escapeHtml(message) + '</span>';
    container.appendChild(el);
    setTimeout(function () {
      el.classList.remove('toast-enter');
      el.classList.add('toast-exit');
      el.addEventListener('animationend', function () { el.remove(); });
    }, 3500);
  }

  function openModal(html) {
    var overlay = document.getElementById('modal-overlay');
    document.getElementById('modal-content').innerHTML = html;
    overlay.classList.remove('hidden');
    requestAnimationFrame(function () { overlay.classList.add('show'); });
    overlay.onclick = function (e) { if (e.target === overlay) closeModal(); };
    document._modalEsc = function (e) { if (e.key === 'Escape') closeModal(); };
    document.addEventListener('keydown', document._modalEsc);
  }

  function closeModal() {
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 22. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/banking/js/pages/accounts.js?v=20260213-2
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/banking/js/pages/accounts.js?v=20260213-2 HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:30 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Sat, 20 Jun 2026 11:44:23 GMT
etag: "3bda-654adee3833c0-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 3823
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=8.352
cf-team: 2fbdb4914a000483be001af400000001

/**
 * BankOfEd - Accounts Page
 */
window.BankOfEd = window.BankOfEd || {};

BankOfEd.AccountsPage = (function () {
  'use strict';

  var U = BankOfEd.Utils;
  var Api = BankOfEd.Api;

  function show() {
    BankOfEd.Router.showPage('accounts', 'accounts');
    loadAccounts();
  }

  function loadAccounts() {
    Api.getAccounts().then(function (res) {
      var accounts = Array.isArray(res.data) ? res.data : (res.data.accounts || []);
      renderList(accounts);
    }).catch(function () {
      U.toast('Failed to load accounts.', 'error');
    });
  }

  function renderList(accounts) {
    var list = U.$('accounts-list');
    var empty = U.$('accounts-empty');

    if (!accounts.length) {
      list.innerHTML = '';
      empty.classList.remove('hidden');
      return;
    }

    empty.classList.add('hidden');
    var html = '';
    accounts.forEach(function (acc) {
      var balanceColor = parseFloat(acc.balance) >= 0 ? 'text-slate-900' : 'text-red-600';
      var currency = acc.currency || 'AUD';
      html +=
        '<a href="#/accounts/' + acc.id + '" class="account-card bg-white rounded-2xl shadow-sm border border-slate-100 p-5 flex items-center justify-between gap-4 block">' +
          '<div class="flex-1 min-w-0">' +
            '<div class="flex items-center gap-3 mb-1">' +
              '<h3 class="font-semibold text-slate-900 truncate">' + U.escapeHtml(acc.account_name) + '</h3>' +
              U.accountTypeBadge(acc.account_type, currency) +
            '</div>' +
            '<p class="text-sm text-slate-400 font-mono">BSB: ' + U.escapeHtml(acc.bsb) + ' &nbsp; Acc: ' + U.escapeHtml(acc.account_number) + '</p>' +
          '</div>' +
          '<div class="text-right flex-shrink-0">' +
            '<p class="text-xl font-bold ' + balanceColor + '">' + U.formatCurrency(acc.balance, currency) + '</p>' +
            '<p class="text-xs text-slate-400 mt-1">Available</p>' +
          '</div>' +
```

### Request Evidence
```
GET http://100.96.0.19/banking/js/pages/accounts.js?v=20260213-2 HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:30 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Sat, 20 Jun 2026 11:44:23 GMT
etag: "3bda-654adee3833c0-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 3823
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=8.352
cf-team: 2fbdb4914a000483be001af400000001

/**
 * BankOfEd - Accounts Page
 */
window.BankOfEd = window.BankOfEd || {};

BankOfEd.AccountsPage = (function () {
  'use strict';

  var U = BankOfEd.Utils;
  var Api = BankOfEd.Api;

  function show() {
    BankOfEd.Router.showPage('accounts', 'accounts');
    loadAccounts();
  }

  function loadAccounts() {
    Api.getAccounts().then(function (res) {
      var accounts = Array.isArray(res.data) ? res.data : (res.data.accounts || []);
      renderList(accounts);
    }).catch(function () {
      U.toast('Failed to load accounts.', 'error');
    });
  }

  function renderList(accounts) {
    var list = U.$('accounts-list');
    var empty = U.$('accounts-empty');

    if (!accounts.length) {
      list.innerHTML = '';
      empty.classList.remove('hidden');
      return;
    }

    empty.classList.add('hidden');
    var html = '';
    accounts.forEach(function (acc) {
      var balanceColor = parseFloat(acc.balance) >= 0 ? 'text-slate-900' : 'text-red-600';
      var currency = acc.currency || 'AUD';
      html +=
        '<a href="#/accounts/' + acc.id + '" class="account-card bg-white rounded-2xl shadow-sm border border-slate-100 p-5 flex items-center justify-between gap-4 block">' +
          '<div class="flex-1 min-w-0">' +
            '<div class="flex items-center gap-3 mb-1">' +
              '<h3 class="font-semibold text-slate-900 truncate">' + U.escapeHtml(acc.account_name) + '</h3>' +
              U.accountTypeBadge(acc.account_type, currency) +
            '</div>' +
            '<p class="text-sm text-slate-400 font-mono">BSB: ' + U.escapeHtml(acc.bsb) + ' &nbsp; Acc: ' + U.escapeHtml(acc.account_number) + '</p>' +
          '</div>' +
          '<div class="text-right flex-shrink-0">' +
            '<p class="text-xl font-bold ' + balanceColor + '">' + U.formatCurrency(acc.balance, currency) + '</p>' +
            '<p class="text-xs text-slate-400 mt-1">Available</p>' +
          '</div>' +
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 23. Unauthenticated access to protected endpoint

- Severity: medium
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://100.96.0.19/banking/js/pages/profile.js?v=20260213-2
- CVSS: 6.5

### Description
The deterministic auth matrix requested a protected or sensitive-looking endpoint without cookies or Authorization and received a successful response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `anonymous` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://100.96.0.19/banking/js/pages/profile.js?v=20260213-2 HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none

RESPONSE:
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:30 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Sun, 21 Jun 2026 05:33:56 GMT
etag: "3db5-654bcdf3a7900-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 3658
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=9.664
cf-team: 2fbdb491a5000483be001d3400000001

/**
 * BankOfEd - Profile Page
 */
window.BankOfEd = window.BankOfEd || {};

BankOfEd.ProfilePage = (function () {
  'use strict';

  var U = BankOfEd.Utils;
  var Api = BankOfEd.Api;

  var isEditing = false;
  var currentProfile = null;

  function show() {
    BankOfEd.Router.showPage('profile', 'profile');
    isEditing = false;
    setFieldsEditable(false);
    U.$('profile-actions').classList.add('hidden');
    U.$('profile-edit-btn').textContent = 'Edit';
    U.showErrors('profile-errors', null);

    // Load profile — API returns user object directly in res.data
    Api.getProfile().then(function (res) {
      currentProfile = res.data;
      populateProfile(currentProfile);
      renderTotpSection(currentProfile);
      loadAvatar(currentProfile);
    }).catch(function () {
      U.toast('Failed to load profile.', 'error');
    });
  }

  function populateProfile(user) {
    U.$('profile-first-name').value = user.first_name || '';
    U.$('profile-last-name').value = user.last_name || '';
    U.$('profile-email').value = user.email || '';
    U.$('profile-phone').value = user.phone || '';
    U.$('profile-address1').value = user.address_line1 || '';
    U.$('profile-address2').value = user.address_line2 || '';
    U.$('profile-suburb').value = user.suburb || '';
    U.$('profile-state').value = user.state || '';
    U.$('profile-postcode').value = user.postcode || '';
  }

  function toggleEdit() {
    if (isEditing) {
      cancelEdit();
    } else {
      isEditing = true;
      setFieldsEditable(true);
      U.$('profile-actions').classList.remove('hidden');
      U.$('profile-edit-btn').textContent = 'Cancel';
    }
  }

  function cancelEdit() {
    isEditing = false;
    setFieldsEditable(false);
    U.$('profile-actions').classList.add('hidden');
    U.$('profile-edit-btn').textContent = 'Edit';
    U.showErrors('profile-errors', null);
    if (currentProfile) populateProfile(currentProfil
```

### Request Evidence
```
GET http://100.96.0.19/banking/js/pages/profile.js?v=20260213-2 HTTP/1.1
Actor: anonymous
Cookies: none
Authorization: none
```

### Response Evidence
```
HTTP/1.1 200
date: Wed, 01 Jul 2026 05:16:30 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
last-modified: Sun, 21 Jun 2026 05:33:56 GMT
etag: "3db5-654bcdf3a7900-gzip"
accept-ranges: bytes
vary: Accept-Encoding
content-encoding: gzip
content-length: 3658
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/javascript
server-timing: cfReqDur;dur=9.664
cf-team: 2fbdb491a5000483be001d3400000001

/**
 * BankOfEd - Profile Page
 */
window.BankOfEd = window.BankOfEd || {};

BankOfEd.ProfilePage = (function () {
  'use strict';

  var U = BankOfEd.Utils;
  var Api = BankOfEd.Api;

  var isEditing = false;
  var currentProfile = null;

  function show() {
    BankOfEd.Router.showPage('profile', 'profile');
    isEditing = false;
    setFieldsEditable(false);
    U.$('profile-actions').classList.add('hidden');
    U.$('profile-edit-btn').textContent = 'Edit';
    U.showErrors('profile-errors', null);

    // Load profile — API returns user object directly in res.data
    Api.getProfile().then(function (res) {
      currentProfile = res.data;
      populateProfile(currentProfile);
      renderTotpSection(currentProfile);
      loadAvatar(currentProfile);
    }).catch(function () {
      U.toast('Failed to load profile.', 'error');
    });
  }

  function populateProfile(user) {
    U.$('profile-first-name').value = user.first_name || '';
    U.$('profile-last-name').value = user.last_name || '';
    U.$('profile-email').value = user.email || '';
    U.$('profile-phone').value = user.phone || '';
    U.$('profile-address1').value = user.address_line1 || '';
    U.$('profile-address2').value = user.address_line2 || '';
    U.$('profile-suburb').value = user.suburb || '';
    U.$('profile-state').value = user.state || '';
    U.$('profile-postcode').value = user.postcode || '';
  }

  function toggleEdit() {
    if (isEditing) {
      cancelEdit();
    } else {
      isEditing = true;
      setFieldsEditable(true);
      U.$('profile-actions').classList.remove('hidden');
      U.$('profile-edit-btn').textContent = 'Cancel';
    }
  }

  function cancelEdit() {
    isEditing = false;
    setFieldsEditable(false);
    U.$('profile-actions').classList.add('hidden');
    U.$('profile-edit-btn').textContent = 'Edit';
    U.showErrors('profile-errors', null);
    if (currentProfile) populateProfile(currentProfil
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 24. Weak Password Policy — Single-Character Passwords Accepted, Unsalted MD5 Password Hashing

- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/auth/register
- CVSS: 5.3 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The registration endpoint at /api/auth/register does not enforce any minimum length or complexity requirement on user-supplied passwords. A registration request using the single-character password "a" was accepted and a new account was created. Additionally, the server-side password hashing scheme was confirmed to be unsalted MD5, a fast, cryptographically broken algorithm unsuitable for password storage.

### Impact
The absence of password length/complexity enforcement makes accounts significantly more susceptible to credential guessing and brute-force attacks. The use of unsalted MD5 for password storage compounds this risk: MD5 hashes are trivially reversible via precomputed rainbow tables and can be brute-forced at very high speed. This is especially severe combined with a separately identified issue in this assessment where the password_hash field is leaked in API responses, as it would allow rapid offline recovery of plaintext passwords for any account whose hash is exposed.

### Likelihood
Confirmed — a single registration request with a 1-character password was accepted and returned an MD5 hash matching the known unsalted MD5 digest of "a", requiring no special access or conditions to reproduce.

### Recommendation
Enforce server-side minimum password length (12+ characters) and complexity/breach-list checks at both the registration and password-change endpoints. Replace MD5 with a modern adaptive password hashing algorithm (bcrypt, scrypt, or argon2id) using a unique per-user salt and an appropriate work factor. Rehash existing stored passwords upon next successful login using the new scheme.

### Evidence
```
POST http://100.96.0.19/api/auth/register with body {"email":"weakpass_test1@example.invalid","first_name":"Weak","last_name":"Pass","password":"a"} returned 201 Created: {"success":true,"data":{"user":{"id":18,...,"password_hash":"0cc175b9c0f1b6a831c399e269772661",...},"token":"[JWT]"},"message":"Registration successful"}. The password_hash 0cc175b9c0f1b6a831c399e269772661 is the well-known unsalted MD5 digest of the string "a", confirming both single-character password acceptance and use of unsalted MD5 hashing.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 25. CORS Misconfiguration — Arbitrary Origin Reflected with Access-Control-Allow-Credentials: true

- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/profile
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The /api/profile endpoint dynamically reflects any client-supplied Origin header value into the Access-Control-Allow-Origin response header while also setting Access-Control-Allow-Credentials: true. This behavior was confirmed on both a simple GET request and an OPTIONS preflight request, indicating the misconfiguration applies broadly to the endpoint rather than a single request type.

### Impact
Combining unrestricted Origin reflection with Access-Control-Allow-Credentials: true is a known anti-pattern that, if credentials are attached automatically by the browser (e.g. stored cookies) or become reachable from a malicious page/script context, would allow an attacker-controlled site to issue credentialed cross-origin requests and read authenticated response data (this endpoint has previously been shown to return sensitive profile fields such as password_hash and totp_secret). No browser-based proof-of-concept demonstrating successful credentialed cross-origin data exfiltration was performed in this assessment, so exploitability under the application's actual authentication model (e.g. Bearer-token-in-header) is unconfirmed but the misconfiguration itself is a real weakening of the browser's same-origin protections.

### Likelihood
Confirmed via direct request/response header inspection on both GET and OPTIONS preflight requests. Practical exploitability depends on how the victim's session/token is attached in-browser (e.g. cookie-based auth or a script able to read a stored token) — this was not demonstrated end-to-end, so likelihood of a full credentialed cross-origin data leak in the current auth model is uncertain but plausible for future or alternate auth flows.

### Recommendation
Do not reflect arbitrary Origin headers. Maintain an explicit allow-list of trusted origins (the application's own domains) and only set Access-Control-Allow-Origin to a matching value from that list. Never combine wildcard or reflected-origin values with Access-Control-Allow-Credentials: true. Apply the fix consistently across both simple and preflighted (OPTIONS) requests.

### Evidence
```
GET http://100.96.0.19/api/profile with header Origin: https://evil.example returned access-control-allow-origin: https://evil.example and access-control-allow-credentials: true. Identical reflected-origin plus allow-credentials:true behavior confirmed on OPTIONS preflight request.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 26. Missing Content-Security-Policy and Strict-Transport-Security Headers

- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/banking/
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The application at http://100.96.0.19/banking/ and its API (e.g. /api/health) do not return Content-Security-Policy or Strict-Transport-Security headers on any tested response. Present security headers are limited to x-content-type-options, x-frame-options, x-xss-protection, and referrer-policy; CSP and HSTS were absent across all captured traffic during this assessment.

### Impact
The absence of a Content-Security-Policy removes a defense-in-depth control that could otherwise restrict script execution and mitigate the impact of the confirmed stored XSS findings (transfer description and profile fields), as there is no script-src restriction to block injected inline scripts. The absence of HSTS means users connecting over plain HTTP, or subjected to an SSL-stripping MITM attack, are not automatically upgraded to HTTPS, which for a banking application increases the risk of credential and session token interception in a network-level attack scenario.

### Likelihood
Confirmed — header absence was directly observed across all captured HTTP responses in this assessment via history_search, with no additional exploitation steps required to verify.

### Recommendation
Add a restrictive Content-Security-Policy header (e.g. default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none') to all HTML and API responses, avoiding unsafe-inline and unsafe-eval directives. Add Strict-Transport-Security: max-age=31536000; includeSubDomains once the application is served exclusively over HTTPS.

### Evidence
```
GET http://100.96.0.19/banking/ and GET http://100.96.0.19/api/health response headers do not include Content-Security-Policy or Strict-Transport-Security. Observed headers on these and other tested endpoints only include x-content-type-options, x-frame-options, x-xss-protection, and referrer-policy — no CSP or HSTS header was present in any response captured during this assessment (confirmed via history_search across all captured traffic).
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 27. Missing Rate-Limiting on Login Endpoint Enables Brute-Force Attacks

- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/auth/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L)

### Description
The authentication endpoint at /api/auth/login does not implement rate-limiting, progressive delays, CAPTCHA, or account lockout after repeated failed login attempts. This allows unrestricted password-guessing against any known account.

### Impact
An attacker who has identified a valid account (e.g. via the confirmed user-enumeration issue) can perform unlimited password-guessing or credential-stuffing attempts against that account without triggering any throttling, lockout, or alerting mechanism.

### Likelihood
Confirmed — 6 consecutive failed login attempts against a valid account all returned identical unthrottled 401 responses with consistent response times (110-180ms), demonstrating no throttling controls are in place. Exploitation would still require sustained automated requests and a valid or guessed account identifier.

### Recommendation
Implement account- and IP-based rate limiting on /api/auth/login and other sensitive endpoints (password reset, OTP verification), e.g. via a Redis token bucket or similar mechanism. Add progressive delays or CAPTCHA after a small number of failed attempts, and temporary account lockout with alerting on repeated failures.

### Evidence
```
Sent 6 consecutive POST requests to /api/auth/login with email=amelia.chen@example.com and incrementing wrong passwords (wrongpass1..wrongpass6). Attempt #1 response: 401 {"error":{"code":"WRONG_PASSWORD","message":"Incorrect password."}}. Attempt #6 response: identical 401 {"error":{"code":"WRONG_PASSWORD","message":"Incorrect password."}}. No CAPTCHA, lockout, 429, or increasing delay was observed across any of the 6 attempts (response times stayed in the 110-180ms range throughout).
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 28. User Enumeration via Distinct Login Error Codes

- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://100.96.0.19/api/auth/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The login endpoint at /api/auth/login returns distinct, machine-readable error codes and messages depending on whether the submitted email address corresponds to an existing account. A request with a valid email and an incorrect password returns a WRONG_PASSWORD error, while a request with a non-existent email returns a USER_NOT_FOUND error, allowing an attacker to distinguish valid from invalid accounts.

### Impact
An attacker can enumerate valid customer email addresses/usernames by submitting login attempts and observing the differing error codes/messages. Confirmed valid accounts can then be targeted more efficiently for credential stuffing, password brute-forcing, or phishing campaigns.

### Likelihood
Confirmed — reproduced with two direct login requests, one against a known valid account and one against a non-existent account, each returning a distinct, distinguishable error code and message.

### Recommendation
Return a single generic error response (e.g. HTTP 401 with a message such as "Invalid email or password") regardless of whether the email exists or the password is incorrect. Avoid distinguishing error codes/messages between the two cases. Normalize response timing between the two scenarios to prevent timing-based enumeration, and consider rate-limiting/lockout controls on the login endpoint to further hinder enumeration and brute-force attempts.

### Evidence
```
POST /api/auth/login {"email":"amelia.chen@example.com","password":"wrongpass1"} → 401 {"error":{"code":"WRONG_PASSWORD","message":"Incorrect password."}}. POST /api/auth/login {"email":"nonexistent_user_xyz@example.com","password":"wrongpass1"} → 401 {"error":{"code":"USER_NOT_FOUND","message":"No account found with this email address."}}. Distinct error codes/messages disclose account existence.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 29. Static JavaScript Assets Served Without Authentication (Auth-Matrix Noise Finding)

- Severity: info
- OWASP: A05
- Source: A.L.I.C.E
- Validation: unvalidated
- Affected URL: http://100.96.0.19/admin/js/app.js
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The web server returns static JavaScript asset files for both the admin and banking frontends without requiring any authentication (cookies or Authorization header). Examples observed during the unauthenticated auth-matrix sweep include: /admin/js/app.js, /admin/js/pages/accounts.js, /admin/js/pages/auth.js, /admin/js/pages/customers.js, /admin/js/pages/fx-rates.js, /admin/js/pages/system.js, /admin/js/router.js, /admin/js/utils.js, /banking/js/pages/accounts.js, /banking/js/pages/profile.js.

This is expected/normal behavior for static asset paths (the server does not enforce auth on .js files) and does not by itself represent an authentication bypass — authentication is enforced on the dynamic API endpoints (e.g. /api/admin/*, /api/profile, /api/transactions/*), not on the JS bundles the SPA loads. The finding is recorded here for completeness because the deterministic auth-matrix flagged all ten paths; the actual risk surface is the application logic the JS files reveal (admin route structure, customer-side page modules), not the unauthenticated retrieval of those files. No exploitation is possible from this alone.

### Impact
No direct impact. Static JS retrieval without auth is expected. The indirectly disclosed information (route names, page module structure) is the same information a user would receive by loading the public landing page or by inspecting the bundled SPA.

### Likelihood
low

### Recommendation
No remediation required. If desired for defence-in-depth, the web server can serve static assets with restrictive Cache-Control headers and the API endpoints already enforce authentication correctly. Real authorization controls are (and should remain) on /api/* dynamic routes.

### Evidence
```
Auth-matrix sweep returned HTTP 200 for all ten static JS paths when probed without cookies or Authorization headers. This is identical to the response observed for any normal browser request that loads the SPA shell — no protected data is returned, only client-side code. Example: GET /admin/js/pages/customers.js -> 200, body contains the customer-listing page module (not user records).
```
