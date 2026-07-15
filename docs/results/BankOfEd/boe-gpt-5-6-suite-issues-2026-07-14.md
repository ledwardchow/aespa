# Issue Export: GPT 5.6 suite

- Site: Bank of Ed
- Exported: 14/7/2026, 2:58:12 pm
- Total findings: 29

<!-- aespa-findings-json
%5B%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Administrative%20interface%20accessible%20with%20default%20credentials%22%2C%22description%22%3A%22The%20administrative%20login%20accepts%20the%20predictable%20credentials%20admin%2Fadmin123%20and%20issues%20a%20privileged%20JWT.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20could%20take%20control%20of%20the%20administrative%20interface%2C%20enumerate%20customers%20and%20their%20personal%20information%2C%20and%20potentially%20perform%20privileged%20account%20or%20system-management%20operations.%22%2C%22likelihood%22%3A%22Highly%20likely%20because%20the%20credentials%20are%20trivial%20to%20guess%20and%20were%20successfully%20used%20without%20any%20additional%20authentication%20factor.%22%2C%22recommendation%22%3A%22Disable%20all%20default%20credentials%2C%20require%20a%20unique%20high-entropy%20administrator%20password%20during%20deployment%2C%20rotate%20the%20exposed%20account%20credentials%2C%20require%20MFA%20for%20administrative%20access%2C%20and%20monitor%20for%20prior%20unauthorized%20logins.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20%7B%5C%22username%5C%22%3A%5C%22admin%5C%22%2C%5C%22password%5C%22%3A%5C%22admin123%5C%22%7D%20returned%20HTTP%20200%20and%20an%20admin%20JWT.%20The%20resulting%20session%20retrieved%20%2Fapi%2Fadmin%2Fcustomers%20and%20displayed%20names%2C%20email%20addresses%2C%20phone%20numbers%2C%20account%20counts%2C%20and%202FA%20status%20for%2015%20customers.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%5Cnuse_session%3A%20legit_admin%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A33%3A57%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20102%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D98%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%5Cnuse_session%3A%20legit_admin%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A33%3A57%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20102%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D98%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22External%20Transfer%20Endpoint%20Bypasses%20TOTP%20and%20Sufficient-Funds%20Validation%22%2C%22description%22%3A%22The%20external%20transfer%20workflow%20does%20not%20enforce%20mandatory%20TOTP%20verification%20or%20sufficient-funds%20validation%20at%20the%20final%20transfer%20endpoint.%20Although%20the%20preflight%20endpoint%20reported%20that%20TOTP%20was%20required%20for%20a%20manually%20entered%20transfer%2C%20the%20application%20completed%20a%20direct%20request%20to%20POST%20%2Fapi%2Ftransfers%2Fexternal%20without%20a%20totp_code.%20The%20same%20transaction%20reduced%20the%20source%20account%20balance%20below%20zero.%22%2C%22impact%22%3A%22An%20attacker%20with%20access%20to%20an%20authenticated%20session%20could%20complete%20external%20transfers%20without%20satisfying%20the%20required%20TOTP%20control.%20The%20missing%20balance%20validation%20also%20allows%20transfers%20that%20exceed%20the%20available%20account%20balance%2C%20resulting%20in%20unauthorized%20negative%20balances%20or%20overdrafts.%22%2C%22likelihood%22%3A%22High.%20Exploitation%20requires%20an%20authenticated%20session%20but%20only%20involves%20calling%20the%20external%20transfer%20endpoint%20directly%20while%20omitting%20the%20TOTP%20code.%20No%20additional%20bypass%20technique%20was%20required%20in%20the%20observed%20test.%22%2C%22recommendation%22%3A%22Enforce%20TOTP%20verification%20and%20all%20transfer%20prerequisites%20within%20the%20final%20transfer%20service%20rather%20than%20relying%20on%20preflight%20or%20client-side%20workflow%20checks.%20Before%20committing%20a%20transfer%2C%20atomically%20lock%20and%20revalidate%20the%20source%20account's%20ownership%2C%20active%20status%2C%20available%20balance%20or%20authorized%20overdraft%20limit%2C%20and%20required%20verification%20state.%20Reject%20the%20transaction%20if%20TOTP%20is%20required%20but%20absent%20or%20invalid%2C%20or%20if%20sufficient%20funds%20are%20unavailable.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fcheck%20returned%20%7B%5C%22requires_totp%5C%22%3Atrue%2C%5C%22reason%5C%22%3A%5C%22manual_entry%5C%22%2C%5C%22totp_configured%5C%22%3Afalse%7D.%20A%20direct%20POST%20to%20%2Fapi%2Ftransfers%2Fexternal%20without%20totp_code%20returned%20HTTP%20201%20and%20reported%20%5C%22totp_verified%5C%22%3Afalse%2C%20%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%20and%20%5C%22new_from_balance%5C%22%3A%5C%22-1.00%5C%22%2C%20together%20with%20the%20message%20%5C%22Transfer%20completed%20successfully%5C%22.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20%7B%5C%22from_account_id%5C%22%3A39%2C%5C%22to_bsb%5C%22%3A%5C%22062-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2212345678%5C%22%2C%5C%22payee_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22amount%5C%22%3A1%2C%5C%22description%5C%22%3A%5C%22direct%20without%20totp%5C%22%7D%20with%20no%20totp_code%22%2C%22response_evidence%22%3A%22HTTP%20201%20%7B%5C%22transaction_id%5C%22%3A36%2C...%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22new_from_balance%5C%22%3A%5C%22-1.00%5C%22%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%7D%2C%20%5C%22Transfer%20completed%20successfully%5C%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Hardcoded%20JWT%20Signing%20Secret%20Enables%20Authentication%20Bypass%22%2C%22description%22%3A%22The%20application%20uses%20the%20hardcoded%20fallback%20secret%20%60bankofed-dev-secret-change-in-production%60%20to%20validate%20HS256%20JWTs.%20The%20%60%2Fapi%2Fprofile%60%20endpoint%20accepted%20a%20locally%20forged%20token%20containing%20%60sub%3A%203%60%20without%20requiring%20authentication%20and%20returned%20the%20profile%20associated%20with%20that%20customer%20ID.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20who%20knows%20the%20shipped%20secret%20can%20forge%20valid%20JWTs%20for%20arbitrary%20customer%20IDs%2C%20impersonate%20customers%2C%20access%20their%20financial%20and%20personal%20information%2C%20and%20perform%20authenticated%20banking%20actions%20in%20their%20names.%22%2C%22likelihood%22%3A%22High.%20The%20signing%20secret%20is%20static%2C%20present%20in%20the%20application%20configuration%2C%20and%20was%20confirmed%20to%20be%20active%20in%20the%20tested%20deployment%20by%20successfully%20using%20it%20to%20forge%20an%20accepted%20JWT.%22%2C%22recommendation%22%3A%22Immediately%20replace%20the%20hardcoded%20secret%20with%20a%20cryptographically%20random%2C%20high-entropy%2C%20deployment-specific%20signing%20key.%20Remove%20all%20fallback%20signing%20secrets%20and%20require%20secure%20key%20configuration%20at%20startup%2C%20failing%20closed%20when%20it%20is%20absent.%20Rotate%20the%20exposed%20key%20and%20invalidate%20all%20JWTs%20signed%20with%20it.%20Store%20signing%20keys%20in%20an%20appropriate%20secrets-management%20system%20and%20establish%20a%20controlled%20key-rotation%20process.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22A%20locally%20forged%20HS256%20JWT%20signed%20with%20%60bankofed-dev-secret-change-in-production%60%20and%20containing%20claims%20%60%7B%5C%22iss%5C%22%3A%5C%22BankOfEd%5C%22%2C%5C%22sub%5C%22%3A3%2C%5C%22jti%5C%22%3A%5C%22sast-default-secret-probe-62%5C%22%2C%5C%22iat%5C%22%3A1784030000%2C%5C%22exp%5C%22%3A1784116400%7D%60%20was%20accepted%20by%20%60%2Fapi%2Fprofile%60.%20The%20endpoint%20returned%20HTTP%20200%20and%20profile%20data%20for%20%60zoe.williams%40example.com%60%2C%20demonstrating%20successful%20token%20forgery%20and%20impersonation%20of%20user%20ID%203.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fprofile%20with%20Authorization%3A%20Bearer%20%3Clocally%20forged%20HS256%20JWT%20signed%20using%20the%20shipped%20fallback%20secret%3E.%22%2C%22response_evidence%22%3A%22HTTP%20200%3A%20%60%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A3%2C%5C%22email%5C%22%3A%5C%22zoe.williams%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Zoe%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Williams%5C%22%2C...%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%60%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unrestricted%20Self-Issued%20Loans%20Credit%20Arbitrary%20Funds%22%2C%22description%22%3A%22The%20account%20creation%20endpoint%20accepts%20an%20attacker-controlled%20%60borrow_amount%60%20for%20loan%20accounts%20without%20enforcing%20a%20maximum%20loan%20value%2C%20underwriting%2C%20approval%2C%20or%20affordability%20controls.%20During%20testing%2C%20a%20disposable%20authenticated%20customer%20requested%20a%20loan%20of%20999%2C999%2C999%2C999.99%20AUD%2C%20and%20the%20application%20immediately%20credited%20the%20full%20amount%20to%20the%20specified%20transaction%20account.%22%2C%22impact%22%3A%22Any%20authenticated%20customer%20could%20create%20an%20effectively%20arbitrary%20account%20balance%20without%20authorization%20or%20legitimate%20funding.%20This%20compromises%20the%20application's%20financial%20integrity%20and%20could%20enable%20fraudulent%20transfers%20or%20withdrawals%2C%20resulting%20in%20severe%20financial%20loss%20and%20disruption.%22%2C%22likelihood%22%3A%22High.%20Customer%20registration%20is%20public%2C%20exploitation%20requires%20only%20a%20simple%20authenticated%20API%20request%2C%20and%20no%20privileged%20role%2C%20approval%2C%20or%20other%20special%20precondition%20was%20required%20in%20the%20observed%20workflow.%22%2C%22recommendation%22%3A%22Enforce%20strict%20server-side%20minimum%20and%20maximum%20loan%20limits%20using%20safe%20fixed-precision%20decimal%20validation.%20Require%20underwriting%2C%20affordability%20checks%2C%20credit%20approval%2C%20and%20maker-checker%20authorization%20before%20creating%20or%20disbursing%20a%20loan.%20Perform%20loan%20creation%20and%20disbursement%20through%20controlled%20transactional%20workflows%2C%20and%20block%20or%20alert%20on%20anomalous%20loan%20amounts%20and%20disbursements.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Faccounts%22%2C%22evidence%22%3A%22A%20POST%20request%20to%20%60%2Fapi%2Faccounts%60%20by%20disposable%20user%20ID%2016%20specified%20%60account_type%60%20as%20%60loan%60%2C%20%60borrow_amount%60%20as%20%60999999999999.99%60%2C%20and%20%60disbursement_account_id%60%20as%2039.%20The%20server%20returned%20HTTP%20201%20and%20created%20loan%20account%20ID%2040%20with%20a%20balance%20of%20%60-999999999999.99%60.%20A%20subsequent%20GET%20request%20for%20account%2039%20showed%20a%20balance%20of%20%60999999999999.99%60%20and%20transaction%20ID%2036%2C%20described%20as%20%60Loan%20proceeds%20disbursement%60%2C%20for%20the%20same%20amount.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Faccounts%5Cn%7B%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Excessive%20Loan%20Probe%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22borrow_amount%5C%22%3A%5C%22999999999999.99%5C%22%2C%5C%22disbursement_account_id%5C%22%3A39%7D%22%2C%22response_evidence%22%3A%22HTTP%20201%3A%20%60%7B%5C%22id%5C%22%3A40%2C...%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C...%2C%5C%22balance%5C%22%3A%5C%22-999999999999.99%5C%22%7D%60.%20Follow-up%20destination%20account%20response%3A%20%60%5C%22balance%5C%22%3A%5C%22999999999999.99%5C%22%60%20and%20%60%5C%22amount%5C%22%3A%5C%22999999999999.99%5C%22%2C%5C%22description%5C%22%3A%5C%22Loan%20proceeds%20disbursement%5C%22%60.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unauthenticated%20Health%20Endpoint%20Exposes%20JWT%20Signing%20Secret%20and%20Database%20Configuration%22%2C%22description%22%3A%22The%20unauthenticated%20health%20endpoint%20at%20%60%2Fapi%2Fhealth%60%20returns%20the%20production%20JWT%20HMAC%20signing%20secret%20and%20internal%20configuration%20details%2C%20including%20the%20database%20host%2C%20database%20name%2C%20database%20user%2C%20PHP%20version%2C%20Apache%20version%2C%20and%20deployment%20environment.%22%2C%22impact%22%3A%22An%20attacker%20who%20obtains%20the%20JWT%20signing%20secret%20could%20potentially%20forge%20valid%20authentication%20tokens%20and%20impersonate%20customers%20or%20administrators.%20The%20disclosed%20database%20and%20runtime%20metadata%20also%20provides%20useful%20information%20for%20follow-on%20attacks.%22%2C%22likelihood%22%3A%22High.%20The%20endpoint%20is%20remotely%20accessible%20without%20authentication%2C%20and%20a%20single%20GET%20request%20returns%20the%20JWT%20signing%20secret%20directly%20in%20the%20response%20body.%22%2C%22recommendation%22%3A%22Immediately%20rotate%20the%20exposed%20JWT%20signing%20secret%20and%20invalidate%20all%20tokens%20signed%20with%20the%20compromised%20value.%20Review%20logs%20for%20suspected%20token%20forgery%20or%20unauthorized%20access.%20Remove%20secrets%20and%20internal%20configuration%20data%20from%20health%20responses%2C%20returning%20only%20a%20minimal%20service-status%20indicator.%20Restrict%20operational%20health%20endpoints%20to%20authenticated%20monitoring%20systems%20or%20trusted%20management%20networks%2C%20and%20ensure%20secrets%20are%20stored%20and%20retrieved%20through%20an%20appropriate%20secrets-management%20mechanism.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22An%20unauthenticated%20GET%20request%20to%20%60%2Fapi%2Fhealth%60%20returned%20HTTP%20200%20and%20disclosed%20the%20production%20environment%2C%20PHP%20and%20Apache%20versions%2C%20database%20host%20(%60127.0.0.1%60)%2C%20database%20name%20(%60bankofed%60)%2C%20database%20user%20(%60bankofed_app%60)%2C%20and%20JWT%20signing%20secret%20(%60u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw%60)%20in%20the%20JSON%20response.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fhealth%20HTTP%2F1.1%5CnHost%3A%20192.168.3.101%5CnOrigin%3A%20https%3A%2F%2Fevil.example%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%20OK%5CnAccess-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%5CnAccess-Control-Allow-Credentials%3A%20true%5CnContent-Type%3A%20application%2Fjson%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.3.31%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%2F2.4.58%20(Ubuntu)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22bankofed_app%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22alice%22%2C%22validation_status%22%3A%22validating%22%2C%22validation_note%22%3A%22Validation%20running.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Administrative%20credentials%20and%20bearer%20tokens%20transmitted%20over%20cleartext%20HTTP%22%2C%22description%22%3A%22The%20administrative%20authentication%20flow%20operates%20over%20unencrypted%20HTTP.%20The%20login%20request%20contains%20the%20administrator%20password%20in%20plaintext%20at%20the%20transport%20layer%2C%20and%20the%20response%20returns%20a%20reusable%20bearer%20JWT%20over%20the%20same%20connection.%22%2C%22impact%22%3A%22An%20attacker%20able%20to%20observe%20or%20modify%20network%20traffic%20could%20steal%20the%20administrator%20password%20or%20JWT%2C%20hijack%20the%20administrative%20session%2C%20and%20access%20sensitive%20customer%20information.%22%2C%22likelihood%22%3A%22Practical%20for%20an%20attacker%20on%20the%20same%20or%20an%20intermediary%20network%20whenever%20an%20administrator%20signs%20in%20or%20uses%20the%20application.%22%2C%22recommendation%22%3A%22Serve%20the%20application%20exclusively%20over%20HTTPS%20using%20a%20valid%20certificate%2C%20redirect%20all%20HTTP%20traffic%20to%20HTTPS%2C%20enable%20HSTS%20after%20HTTPS%20is%20deployed%2C%20and%20rotate%20credentials%20and%20tokens%20previously%20transmitted%20over%20HTTP.%22%2C%22cvss_score%22%3A7.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AA%2FAC%3AL%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22The%20browser%20sent%20the%20admin%2Fadmin123%20login%20request%20to%20an%20http%3A%2F%2F%20URL%2C%20and%20the%20HTTP%20200%20response%20returned%20a%20reusable%20HS256%20JWT%20without%20transport%20encryption.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%5Cnuse_session%3A%20legit_admin%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A33%3A57%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20102%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D98%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%5Cnuse_session%3A%20legit_admin%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A33%3A57%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20102%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D98%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A10%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Avatar%20URL%20Import%20Permits%20SSRF%20to%20Loopback%20Services%20and%20Returns%20Response%20Content%22%2C%22description%22%3A%22The%20avatar%20import%20endpoint%20accepts%20an%20arbitrary%20URL%2C%20retrieves%20it%20server-side%2C%20and%20returns%20the%20response%20bytes%20as%20a%20base64-encoded%20data%20URI.%20The%20endpoint%20permits%20requests%20to%20loopback%20addresses%20and%20does%20not%20restrict%20imported%20content%20to%20images.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20access%20internal%20HTTP%20services%20that%20are%20not%20otherwise%20externally%20reachable%20and%20exfiltrate%20their%20responses%20through%20the%20application.%20In%20the%20observed%20case%2C%20this%20exposed%20internal%20health%20information%20containing%20a%20JWT%20secret%20and%20database%20configuration%20settings.%20Access%20to%20other%20internal%20services%20could%20expose%20additional%20sensitive%20data%20or%20administrative%20functionality.%22%2C%22likelihood%22%3A%22High.%20Exploitation%20requires%20only%20an%20authenticated%20request%20containing%20an%20internal%20URL.%20Successful%20access%20to%20a%20loopback%20service%20and%20retrieval%20of%20its%20response%20content%20were%20confirmed.%22%2C%22recommendation%22%3A%22Remove%20support%20for%20arbitrary%20server-side%20URL%20retrieval%20where%20possible.%20If%20remote%20avatar%20import%20is%20required%2C%20enforce%20a%20strict%20allowlist%20of%20trusted%20HTTPS%20image%20hosts.%20Resolve%20hostnames%20and%20block%20loopback%2C%20private%2C%20link-local%2C%20multicast%2C%20reserved%2C%20and%20cloud%20metadata%20address%20ranges%20before%20each%20request%20and%20after%20every%20redirect.%20Prevent%20DNS%20rebinding%2C%20restrict%20redirects%20and%20outbound%20network%20access%2C%20validate%20that%20responses%20are%20approved%20image%20types%2C%20enforce%20file-size%20and%20timeout%20limits%2C%20and%20run%20the%20fetcher%20in%20an%20isolated%20environment%20without%20access%20to%20sensitive%20internal%20services.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%2Favatar%22%2C%22evidence%22%3A%22A%20request%20for%20the%20loopback%20URL%20http%3A%2F%2F127.0.0.1%3A80%2Fapi%2Fhealth%20returned%20HTTP%20200%20and%20included%20the%20fetched%20response%20as%20an%20application%2Fjson%20base64%20data%20URI.%20Decoding%20the%20280-byte%20value%20disclosed%20db_host%2C%20db_name%2C%20db_user%2C%20jwt_secret%2C%20and%20environment.%20A%20request%20to%20the%20unused%20loopback%20port%20127.0.0.1%3A1%20returned%20FETCH_FAILED%2C%20further%20demonstrating%20server-side%20connection%20attempts.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fprofile%2Favatar%20%7B%5C%22url%5C%22%3A%5C%22http%3A%2F%2F127.0.0.1%3A80%2Fapi%2Fhealth%5C%22%7D%22%2C%22response_evidence%22%3A%22HTTP%20200%20%7B%5C%22avatar_data%5C%22%3A%5C%22data%3Aapplication%2Fjson%3B%20charset%3Dutf-8%3Bbase64%2C...%5C%22%2C%5C%22size%5C%22%3A280%2C%5C%22source_url%5C%22%3A%5C%22http%3A%2F%2F127.0.0.1%3A80%2Fapi%2Fhealth%5C%22%7D.%20Decoded%20data%20includes%20db_host%2C%20db_name%2C%20db_user%2C%20jwt_secret%2C%20and%20environment.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API6%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22External%20Transfer%20Endpoint%20Allows%20Duplicate%20Concurrent%20Submissions%22%2C%22description%22%3A%22The%20external%20transfer%20creation%20endpoint%20does%20not%20enforce%20idempotency%20when%20identical%20requests%20are%20submitted%20concurrently.%20Two%20simultaneous%20POST%20requests%20to%20%2Fapi%2Ftransfers%2Fexternal%20using%20the%20same%20Idempotency-Key%20and%20identical%20transfer%20details%20were%20each%20processed%20as%20separate%20completed%20transactions.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%2C%20network%20retry%20condition%2C%20or%20concurrent%20request%20burst%20could%20cause%20a%20transfer%20to%20be%20executed%20multiple%20times%2C%20resulting%20in%20repeated%20debits%20from%20the%20source%20account.%20The%20observed%20responses%20also%20indicated%20that%20the%20duplicate%20transfers%20completed%20without%20TOTP%20verification.%22%2C%22likelihood%22%3A%22High.%20Duplicate%20processing%20was%20reproduced%20using%20two%20simultaneous%20requests%20with%20the%20same%20Idempotency-Key%20and%20request%20body.%22%2C%22recommendation%22%3A%22Implement%20server-side%20idempotency%20controls%20for%20transfer%20creation.%20Require%20a%20cryptographically%20random%20idempotency%20key%20and%20atomically%20persist%20the%20key%2C%20a%20request%20fingerprint%2C%20and%20the%20resulting%20transaction%20identifier%20before%20executing%20the%20debit.%20For%20subsequent%20requests%20using%20the%20same%20key%2C%20return%20the%20original%20result%20without%20re-executing%20the%20transfer.%20Use%20transaction%20locking%20and%20database-level%20unique%20constraints%20to%20prevent%20race%20conditions%20and%20concurrent%20duplicate%20debits.%22%2C%22cvss_score%22%3A7.4%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22Two%20simultaneous%20POST%20requests%20to%20%2Fapi%2Ftransfers%2Fexternal%20used%20the%20identical%20request%20body%20and%20Idempotency-Key%3A%20repeatability-test-20260714.%20Both%20requests%20returned%20HTTP%20201%20and%20status%20%5C%22completed%5C%22%2C%20but%20generated%20separate%20transactions%3A%20transaction_id%2043%20with%20new_from_balance%20%5C%2218899.99%5C%22%20and%20transaction_id%2044%20with%20new_from_balance%20%5C%2218899.98%5C%22.%20Both%20responses%20included%20%5C%22totp_verified%5C%22%3A%20false%2C%20demonstrating%20sequential%20duplicate%20debits%20despite%20reuse%20of%20the%20same%20idempotency%20key.%22%2C%22request_evidence%22%3A%22Both%20requests%3A%20POST%20%2Fapi%2Ftransfers%2Fexternal%3B%20shared%20header%20%60Idempotency-Key%3A%20repeatability-test-20260714%60%3B%20body%20%60%7B%5C%22from_account_id%5C%22%3A2%2C%5C%22to_bsb%5C%22%3A%5C%22062-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2212345678%5C%22%2C%5C%22payee_name%5C%22%3A%5C%22Repeatability%20Test%5C%22%2C%5C%22amount%5C%22%3A0.01%2C%5C%22description%5C%22%3A%5C%22identical%20concurrent%20request%5C%22%7D%60.%22%2C%22response_evidence%22%3A%22HTTP%20201%20responses%20with%20different%20transaction%20IDs%2043%20and%2044%20and%20sequential%20balance%20debits.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Stored%20DOM%20XSS%20in%20Transfer%20Payee%20Dropdown%22%2C%22description%22%3A%22Authenticated%20users%20can%20store%20HTML%20markup%20in%20address-book%20%60nickname%60%20or%20%60payee_name%60%20fields.%20On%20the%20transfers%20page%2C%20address-book%20entries%20are%20used%20to%20construct%20%60%3Coption%3E%60%20elements%20through%20string%20concatenation%20and%20assigned%20with%20%60innerHTML%60.%20Because%20the%20label%20is%20not%20HTML-encoded%2C%20attacker-controlled%20content%20can%20close%20the%20intended%20option%20element%20and%20introduce%20executable%20markup.%22%2C%22impact%22%3A%22JavaScript%20can%20execute%20in%20the%20banking%20application's%20origin%20whenever%20a%20user%20loads%20the%20transfers%20page%20containing%20the%20malicious%20address-book%20entry.%20An%20attacker%20able%20to%20create%20or%20modify%20an%20address-book%20entry%20could%20perform%20actions%20with%20the%20affected%20user's%20authenticated%20browser%20context%2C%20including%20accessing%20page-readable%20banking%20information%20and%20issuing%20same-origin%20requests.%22%2C%22likelihood%22%3A%22High.%20The%20payload%20was%20successfully%20persisted%20and%20returned%20unencoded%20by%20the%20address-book%20API%2C%20and%20the%20transfers%20page%20loads%20address-book%20entries%20before%20inserting%20the%20resulting%20option%20markup%20through%20%60innerHTML%60.%20Exploitation%20requires%20an%20attacker%20to%20create%20or%20modify%20an%20address-book%20entry%20and%20a%20user%20to%20render%20the%20transfers%20page.%22%2C%22recommendation%22%3A%22Do%20not%20generate%20%60%3Coption%3E%60%20markup%20using%20string%20concatenation%20or%20assign%20untrusted%20values%20through%20%60innerHTML%60.%20Create%20options%20with%20%60document.createElement('option')%60%2C%20assign%20the%20identifier%20through%20%60option.value%60%2C%20and%20assign%20the%20display%20label%20through%20%60option.textContent%60.%20Apply%20context-appropriate%20output%20encoding%20in%20all%20address-book%20rendering%20views%20and%20enforce%20server-side%20validation%20for%20address-book%20names%20using%20a%20restrictive%20character%20policy%20where%20appropriate.%22%2C%22cvss_score%22%3A7.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AR%2FS%3AC%2FC%3AL%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fbanking%2F%23%2Ftransfers%22%2C%22evidence%22%3A%22A%20PUT%20request%20to%20%60%2Fapi%2Faddress-book%2F21%60%20set%20both%20%60nickname%60%20and%20%60payee_name%60%20to%20%60%3C%2Foption%3E%3Cimg%20src%3Dx%20onerror%3D%5C%22document.title%3D'AESPA_XSS_7419'%5C%22%3E%60.%20A%20subsequent%20HTTP%20200%20response%20from%20%60GET%20%2Fapi%2Faddress-book%2F21%60%20returned%20both%20values%20unchanged%20and%20unencoded.%20Static%20evidence%20from%20%60transfers.js%60%20shows%20%60entry.nickname%20%7C%7C%20entry.payee_name%60%20is%20incorporated%20into%20an%20%60%3Coption%3E%60%20string%20and%20inserted%20using%20%60sel.innerHTML%20%3D%20options%60.%20The%20transfers%20route%20calls%20%60Api.getAddressBook()%60%20and%20then%20%60populatePayeeDropdown()%60%2C%20connecting%20the%20persisted%20value%20to%20the%20vulnerable%20sink.%22%2C%22request_evidence%22%3A%22PUT%20%2Fapi%2Faddress-book%2F21%20JSON%20body%20used%20%60nickname%60%20and%20%60payee_name%60%20equal%20to%20%60%3C%2Foption%3E%3Cimg%20src%3Dx%20onerror%3D%5C%22document.title%3D'AESPA_XSS_7419'%5C%22%3E%60.%22%2C%22response_evidence%22%3A%22HTTP%20200%20from%20GET%20%2Fapi%2Faddress-book%2F21%3A%20%60%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A21%2C%5C%22nickname%5C%22%3A%5C%22%3C%5C%5C%2Foption%3E%3Cimg%20src%3Dx%20onerror%3D%5C%5C%5C%22document.title%3D'AESPA_XSS_7419'%5C%5C%5C%22%3E%5C%22%2C%5C%22payee_name%5C%22%3A%5C%22%3C%5C%5C%2Foption%3E%3Cimg%20src%3Dx%20onerror%3D%5C%5C%5C%22document.title%3D'AESPA_XSS_7419'%5C%5C%5C%22%3E%5C%22...%7D%7D%60.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthorized%20role%20access%20to%20admin%20endpoint%22%2C%22description%22%3A%22A%20credential%20that%20was%20not%20observed%20with%20access%20to%20this%20admin-looking%20endpoint%20received%20a%20successful%20direct%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%22%2C%22evidence%22%3A%22Actor%20%60http_token_7%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20HTTP%2F1.1%5CnActor%3A%20http_token_7%5CnCookies%3A%20none%5CnAuthorization%3A%20present%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A32%3A04%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%205962%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22accounts%5C%22%3A%5B%7B%5C%22id%5C%22%3A38%2C%5C%22bsb%5C%22%3A%5C%22062-015%5C%22%2C%5C%22account_number%5C%22%3A%5C%2225000003%5C%22%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Personal%20Loan%5C%22%2C%5C%22balance%5C%22%3A%5C%22-5200.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A15%2C%5C%22owner_first_name%5C%22%3A%5C%22Noah%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Campbell%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22noah.campbell%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A37%2C%5C%22bsb%5C%22%3A%5C%22062-015%5C%22%2C%5C%22account_number%5C%22%3A%5C%2225000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%2227500.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A15%2C%5C%22owner_first_name%5C%22%3A%5C%22Noah%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Campbell%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22noah.campbell%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A36%2C%5C%22bsb%5C%22%3A%5C%22062-015%5C%22%2C%5C%22account_number%5C%22%3A%5C%2225000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%223100.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A15%2C%5C%22owner_first_name%5C%22%3A%5C%22Noah%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Campbell%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22noah.campbell%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A35%2C%5C%22bsb%5C%22%3A%5C%22062-014%5C%22%2C%5C%22account_number%5C%22%3A%5C%2224000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Holiday%20Fund%5C%22%2C%5C%22balance%5C%22%3A%5C%2211200.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A14%2C%5C%22owner_first_name%5C%22%3A%5C%22Lucas%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Ferreira%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22lucas.ferreira%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A34%2C%5C%22bsb%5C%22%3A%5C%22062-014%5C%22%2C%5C%22account_number%5C%22%3A%5C%2224000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%226750.20%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A14%2C%5C%22owner_first_name%5C%22%3A%5C%22Lucas%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Ferreira%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22lucas.ferreira%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A33%2C%5C%22bsb%5C%22%3A%5C%22062-013%5C%22%2C%5C%22account_number%5C%22%3A%5C%2223000003%5C%22%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Car%20Loan%5C%22%2C%5C%22balance%5C%22%3A%5C%22-9800.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A13%2C%5C%22owner_first_name%5C%22%3A%5C%22Daniel%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Park%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22daniel.park%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A32%2C%5C%22bsb%5C%22%3A%5C%22062-013%5C%22%2C%5C%22account_number%5C%22%3A%5C%2223000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%228900.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A13%2C%5C%22owner_first_name%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20HTTP%2F1.1%5CnActor%3A%20http_token_7%5CnCookies%3A%20none%5CnAuthorization%3A%20present%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A32%3A04%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%205962%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22accounts%5C%22%3A%5B%7B%5C%22id%5C%22%3A38%2C%5C%22bsb%5C%22%3A%5C%22062-015%5C%22%2C%5C%22account_number%5C%22%3A%5C%2225000003%5C%22%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Personal%20Loan%5C%22%2C%5C%22balance%5C%22%3A%5C%22-5200.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A15%2C%5C%22owner_first_name%5C%22%3A%5C%22Noah%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Campbell%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22noah.campbell%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A37%2C%5C%22bsb%5C%22%3A%5C%22062-015%5C%22%2C%5C%22account_number%5C%22%3A%5C%2225000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%2227500.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A15%2C%5C%22owner_first_name%5C%22%3A%5C%22Noah%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Campbell%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22noah.campbell%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A36%2C%5C%22bsb%5C%22%3A%5C%22062-015%5C%22%2C%5C%22account_number%5C%22%3A%5C%2225000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%223100.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A15%2C%5C%22owner_first_name%5C%22%3A%5C%22Noah%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Campbell%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22noah.campbell%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A35%2C%5C%22bsb%5C%22%3A%5C%22062-014%5C%22%2C%5C%22account_number%5C%22%3A%5C%2224000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Holiday%20Fund%5C%22%2C%5C%22balance%5C%22%3A%5C%2211200.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A14%2C%5C%22owner_first_name%5C%22%3A%5C%22Lucas%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Ferreira%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22lucas.ferreira%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A34%2C%5C%22bsb%5C%22%3A%5C%22062-014%5C%22%2C%5C%22account_number%5C%22%3A%5C%2224000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%226750.20%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A14%2C%5C%22owner_first_name%5C%22%3A%5C%22Lucas%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Ferreira%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22lucas.ferreira%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A33%2C%5C%22bsb%5C%22%3A%5C%22062-013%5C%22%2C%5C%22account_number%5C%22%3A%5C%2223000003%5C%22%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Car%20Loan%5C%22%2C%5C%22balance%5C%22%3A%5C%22-9800.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A13%2C%5C%22owner_first_name%5C%22%3A%5C%22Daniel%5C%22%2C%5C%22owner_last_name%5C%22%3A%5C%22Park%5C%22%2C%5C%22owner_email%5C%22%3A%5C%22daniel.park%40example.com%5C%22%7D%2C%7B%5C%22id%5C%22%3A32%2C%5C%22bsb%5C%22%3A%5C%22062-013%5C%22%2C%5C%22account_number%5C%22%3A%5C%2223000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%228900.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22user_id%5C%22%3A13%2C%5C%22owner_first_name%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthorized%20role%20access%20to%20admin%20endpoint%22%2C%22description%22%3A%22A%20credential%20that%20was%20not%20observed%20with%20access%20to%20this%20admin-looking%20endpoint%20received%20a%20successful%20direct%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fcustomers%2F10%22%2C%22evidence%22%3A%22Actor%20%60http_token_7%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fcustomers%2F10%20HTTP%2F1.1%5CnActor%3A%20http_token_7%5CnCookies%3A%20none%5CnAuthorization%3A%20present%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A32%3A07%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20716%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22customer%5C%22%3A%7B%5C%22id%5C%22%3A10%2C%5C%22email%5C%22%3A%5C%22natasha.kowalski%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Natasha%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Kowalski%5C%22%2C%5C%22phone%5C%22%3A%5C%220411%20123%20456%5C%22%2C%5C%22address_line1%5C%22%3A%5C%2230%20St%20Kilda%20Rd%5C%22%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3A%5C%22St%20Kilda%5C%22%2C%5C%22state%5C%22%3A%5C%22VIC%5C%22%2C%5C%22postcode%5C%22%3A%5C%223182%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%5C%22accounts%5C%22%3A%5B%7B%5C%22id%5C%22%3A24%2C%5C%22bsb%5C%22%3A%5C%22062-010%5C%22%2C%5C%22account_number%5C%22%3A%5C%2211000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%223990.80%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%7D%2C%7B%5C%22id%5C%22%3A25%2C%5C%22bsb%5C%22%3A%5C%22062-010%5C%22%2C%5C%22account_number%5C%22%3A%5C%2211000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%2222100.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%7D%5D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fcustomers%2F10%20HTTP%2F1.1%5CnActor%3A%20http_token_7%5CnCookies%3A%20none%5CnAuthorization%3A%20present%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A32%3A07%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20716%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22customer%5C%22%3A%7B%5C%22id%5C%22%3A10%2C%5C%22email%5C%22%3A%5C%22natasha.kowalski%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Natasha%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Kowalski%5C%22%2C%5C%22phone%5C%22%3A%5C%220411%20123%20456%5C%22%2C%5C%22address_line1%5C%22%3A%5C%2230%20St%20Kilda%20Rd%5C%22%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3A%5C%22St%20Kilda%5C%22%2C%5C%22state%5C%22%3A%5C%22VIC%5C%22%2C%5C%22postcode%5C%22%3A%5C%223182%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%5C%22accounts%5C%22%3A%5B%7B%5C%22id%5C%22%3A24%2C%5C%22bsb%5C%22%3A%5C%22062-010%5C%22%2C%5C%22account_number%5C%22%3A%5C%2211000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%223990.80%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%7D%2C%7B%5C%22id%5C%22%3A25%2C%5C%22bsb%5C%22%3A%5C%22062-010%5C%22%2C%5C%22account_number%5C%22%3A%5C%2211000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22balance%5C%22%3A%5C%2222100.00%5C%22%2C%5C%22is_active%5C%22%3A1%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%7D%5D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthorized%20role%20access%20to%20admin%20endpoint%22%2C%22description%22%3A%22A%20credential%20that%20was%20not%20observed%20with%20access%20to%20this%20admin-looking%20endpoint%20received%20a%20successful%20direct%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22Actor%20%60http_token_7%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%20HTTP%2F1.1%5CnActor%3A%20http_token_7%5CnCookies%3A%20none%5CnAuthorization%3A%20present%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A32%3A33%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%202891%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22customers%5C%22%3A%5B%7B%5C%22id%5C%22%3A15%2C%5C%22email%5C%22%3A%5C%22noah.campbell%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Noah%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Campbell%5C%22%2C%5C%22phone%5C%22%3A%5C%220455%20555%20505%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A14%2C%5C%22email%5C%22%3A%5C%22lucas.ferreira%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Lucas%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Ferreira%5C%22%2C%5C%22phone%5C%22%3A%5C%220444%20555%20404%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A13%2C%5C%22email%5C%22%3A%5C%22daniel.park%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Daniel%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Park%5C%22%2C%5C%22phone%5C%22%3A%5C%220433%20555%20303%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A12%2C%5C%22email%5C%22%3A%5C%22marcus.webb%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Marcus%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Webb%5C%22%2C%5C%22phone%5C%22%3A%5C%220422%20555%20202%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A11%2C%5C%22email%5C%22%3A%5C%22liam.oconnor%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Liam%5C%22%2C%5C%22last_name%5C%22%3A%5C%22O'Connor%5C%22%2C%5C%22phone%5C%22%3A%5C%220411%20555%20101%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A10%2C%5C%22email%5C%22%3A%5C%22natasha.kowalski%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Natasha%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Kowalski%5C%22%2C%5C%22phone%5C%22%3A%5C%220411%20123%20456%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A9%2C%5C%22email%5C%22%3A%5C%22emma.obrien%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Emma%5C%22%2C%5C%22last_name%5C%22%3A%5C%22O'Brien%5C%22%2C%5C%22phone%5C%22%3A%5C%220499%20012%20345%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A8%2C%5C%22email%5C%22%3A%5C%22grace.kim%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Grace%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Kim%5C%22%2C%5C%22phone%5C%22%3A%5C%220488%20901%20234%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A7%2C%5C%22email%5C%22%3A%5C%22jing.wu%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Jing%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Wu%5C%22%2C%5C%22phone%5C%22%3A%5C%220477%20890%20123%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A6%2C%5C%22email%5C%22%3A%5C%22sophie.anderson%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Sophie%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Anderson%5C%22%2C%5C%22phone%5C%22%3A%5C%220466%20789%20012%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A5%2C%5C%22email%5C%22%3A%5C%22isabella.thompson%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Isabella%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Thompson%5C%22%2C%5C%22phone%5C%22%3A%5C%220455%20678%20901%5C%22%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%20HTTP%2F1.1%5CnActor%3A%20http_token_7%5CnCookies%3A%20none%5CnAuthorization%3A%20present%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A32%3A33%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%202891%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22customers%5C%22%3A%5B%7B%5C%22id%5C%22%3A15%2C%5C%22email%5C%22%3A%5C%22noah.campbell%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Noah%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Campbell%5C%22%2C%5C%22phone%5C%22%3A%5C%220455%20555%20505%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A14%2C%5C%22email%5C%22%3A%5C%22lucas.ferreira%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Lucas%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Ferreira%5C%22%2C%5C%22phone%5C%22%3A%5C%220444%20555%20404%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A13%2C%5C%22email%5C%22%3A%5C%22daniel.park%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Daniel%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Park%5C%22%2C%5C%22phone%5C%22%3A%5C%220433%20555%20303%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A12%2C%5C%22email%5C%22%3A%5C%22marcus.webb%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Marcus%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Webb%5C%22%2C%5C%22phone%5C%22%3A%5C%220422%20555%20202%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A11%2C%5C%22email%5C%22%3A%5C%22liam.oconnor%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Liam%5C%22%2C%5C%22last_name%5C%22%3A%5C%22O'Connor%5C%22%2C%5C%22phone%5C%22%3A%5C%220411%20555%20101%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A31%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A10%2C%5C%22email%5C%22%3A%5C%22natasha.kowalski%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Natasha%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Kowalski%5C%22%2C%5C%22phone%5C%22%3A%5C%220411%20123%20456%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A9%2C%5C%22email%5C%22%3A%5C%22emma.obrien%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Emma%5C%22%2C%5C%22last_name%5C%22%3A%5C%22O'Brien%5C%22%2C%5C%22phone%5C%22%3A%5C%220499%20012%20345%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A8%2C%5C%22email%5C%22%3A%5C%22grace.kim%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Grace%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Kim%5C%22%2C%5C%22phone%5C%22%3A%5C%220488%20901%20234%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A7%2C%5C%22email%5C%22%3A%5C%22jing.wu%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Jing%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Wu%5C%22%2C%5C%22phone%5C%22%3A%5C%220477%20890%20123%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A3%7D%2C%7B%5C%22id%5C%22%3A6%2C%5C%22email%5C%22%3A%5C%22sophie.anderson%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Sophie%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Anderson%5C%22%2C%5C%22phone%5C%22%3A%5C%220466%20789%20012%5C%22%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22created_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%2C%5C%22accounts_count%5C%22%3A2%7D%2C%7B%5C%22id%5C%22%3A5%2C%5C%22email%5C%22%3A%5C%22isabella.thompson%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Isabella%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Thompson%5C%22%2C%5C%22phone%5C%22%3A%5C%220455%20678%20901%5C%22%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthorized%20role%20access%20to%20admin%20endpoint%22%2C%22description%22%3A%22A%20credential%20that%20was%20not%20observed%20with%20access%20to%20this%20admin-looking%20endpoint%20received%20a%20successful%20direct%20response.%22%2C%22impact%22%3A%22Attackers%20may%20be%20able%20to%20access%20protected%20application%20functionality%20or%20sensitive%20operational%20data%20without%20the%20intended%20authentication%20or%20role%20checks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20request.%22%2C%22recommendation%22%3A%22Enforce%20server-side%20authentication%20and%20authorization%20on%20the%20endpoint.%20Do%20not%20rely%20on%20client-side%20route%20hiding%20or%20UI%20controls.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Ffx-rates%22%2C%22evidence%22%3A%22Actor%20%60http_token_7%60%20received%20HTTP%20200%20for%20a%20protected%2Fsensitive%20endpoint.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Ffx-rates%20HTTP%2F1.1%5CnActor%3A%20http_token_7%5CnCookies%3A%20none%5CnAuthorization%3A%20present%5Cn%5CnRESPONSE%3A%5CnHTTP%2F1.1%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A32%3A35%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%201297%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22currency_code%5C%22%3A%5C%22AUD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Australian%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%221.57000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A8%2C%5C%22currency_code%5C%22%3A%5C%22CAD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Canadian%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%221.36000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A9%2C%5C%22currency_code%5C%22%3A%5C%22CHF%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Swiss%20Franc%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%220.88500000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A10%2C%5C%22currency_code%5C%22%3A%5C%22CNY%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Chinese%20Yuan%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%227.24000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A2%2C%5C%22currency_code%5C%22%3A%5C%22EUR%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Euro%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%220.92500000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22currency_code%5C%22%3A%5C%22GBP%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22British%20Pound%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%220.79200000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A7%2C%5C%22currency_code%5C%22%3A%5C%22HKD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Hong%20Kong%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%227.81000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A4%2C%5C%22currency_code%5C%22%3A%5C%22JPY%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Japanese%20Yen%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%22149.50000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A5%2C%5C%22currency_code%5C%22%3A%5C%22NZD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22New%20Zealand%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%221.71000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A6%2C%5C%22currency_code%5C%22%3A%5C%22SGD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Singapore%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%221.34500000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%5D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Ffx-rates%20HTTP%2F1.1%5CnActor%3A%20http_token_7%5CnCookies%3A%20none%5CnAuthorization%3A%20present%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A32%3A35%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%201297%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22currency_code%5C%22%3A%5C%22AUD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Australian%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%221.57000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A8%2C%5C%22currency_code%5C%22%3A%5C%22CAD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Canadian%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%221.36000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A9%2C%5C%22currency_code%5C%22%3A%5C%22CHF%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Swiss%20Franc%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%220.88500000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A10%2C%5C%22currency_code%5C%22%3A%5C%22CNY%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Chinese%20Yuan%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%227.24000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A2%2C%5C%22currency_code%5C%22%3A%5C%22EUR%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Euro%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%220.92500000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22currency_code%5C%22%3A%5C%22GBP%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22British%20Pound%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%220.79200000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A7%2C%5C%22currency_code%5C%22%3A%5C%22HKD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Hong%20Kong%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%227.81000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A4%2C%5C%22currency_code%5C%22%3A%5C%22JPY%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Japanese%20Yen%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%22149.50000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A5%2C%5C%22currency_code%5C%22%3A%5C%22NZD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22New%20Zealand%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%221.71000000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%2C%7B%5C%22id%5C%22%3A6%2C%5C%22currency_code%5C%22%3A%5C%22SGD%5C%22%2C%5C%22currency_name%5C%22%3A%5C%22Singapore%20Dollar%5C%22%2C%5C%22rate_to_usd%5C%22%3A%5C%221.34500000%5C%22%2C%5C%22updated_at%5C%22%3A%5C%222026-07-14%2004%3A30%3A30%5C%22%7D%5D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20auth%20matrix%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API1%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Broken%20Object-Level%20Authorization%20Allows%20Unauthorized%20External%20Account%20Debits%22%2C%22description%22%3A%22The%20external%20transfer%20endpoint%20at%20%2Fapi%2Ftransfers%2Fexternal%20does%20not%20enforce%20that%20the%20client-supplied%20from_account_id%20belongs%20to%20the%20authenticated%20user.%20Under%20Amelia's%20authenticated%20session%2C%20the%20account%20listing%20returned%20only%20account%20IDs%201%2C%202%2C%20and%203%3B%20however%2C%20a%20transfer%20request%20specifying%20from_account_id%204%20was%20accepted%20and%20completed.%22%2C%22impact%22%3A%22An%20authenticated%20customer%20can%20initiate%20external%20transfers%20from%20accounts%20outside%20their%20authorized%20account%20list.%20This%20could%20enable%20unauthorized%20debits%20and%20transfers%20of%20funds%20from%20other%20customers'%20accounts%20to%20an%20attacker-controlled%20external%20destination%2C%20resulting%20in%20direct%20financial%20loss.%22%2C%22likelihood%22%3A%22High.%20The%20issue%20was%20directly%20demonstrated%20using%20a%20valid%20authenticated%20session%20and%20a%20modified%20source%20account%20identifier%2C%20without%20requiring%20additional%20interaction%20or%20bypass%20techniques.%22%2C%22recommendation%22%3A%22At%20the%20final%20transfer-processing%20endpoint%2C%20derive%20eligible%20source%20accounts%20from%20the%20authenticated%20principal%20and%20enforce%20account%20ownership%20and%20active%2Ftransfer-eligible%20status%20within%20the%20same%20transaction%20as%20the%20debit.%20Do%20not%20rely%20on%20client-provided%20account%20IDs%20or%20prior%20authorization%20checks.%20Reject%20non-owned%20source%20accounts%20with%20a%20generic%20authorization%20error%20and%20log%20attempted%20cross-account%20debit%20requests.%22%2C%22cvss_score%22%3A8.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22Authenticated%20GET%20%2Fapi%2Faccounts%20returned%20only%20account%20IDs%201%2C%202%2C%20and%203.%20Using%20Amelia's%20authenticated%20session%2C%20POST%20%2Fapi%2Ftransfers%2Fexternal%20with%20from_account_id%20set%20to%204%20returned%20HTTP%20201%20and%20reported%20a%20completed%20transfer%3A%20transaction_id%2039%2C%20from_account_id%204%2C%20amount%200.01%2C%20new_from_balance%207210.49%2C%20and%20status%20completed.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20sent%20%60%7B%5C%22from_account_id%5C%22%3A4%2C%5C%22to_bsb%5C%22%3A%5C%22062-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2212345678%5C%22%2C%5C%22payee_name%5C%22%3A%5C%22Ownership%20Test%5C%22%2C%5C%22amount%5C%22%3A0.01%2C%5C%22description%5C%22%3A%5C%22non-owned-source-no-totp%5C%22%7D%60%20under%20Amelia's%20authenticated%20session.%22%2C%22response_evidence%22%3A%22HTTP%20201%20with%20%60%5C%22from_account_id%5C%22%3A4%60%2C%20%60%5C%22new_from_balance%5C%22%3A%5C%227210.49%5C%22%60%2C%20and%20%60%5C%22status%5C%22%3A%5C%22completed%5C%22%60.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22unconfirmed%22%2C%22validation_note%22%3A%22The%20crawl%20did%20not%20record%20a%20user%20that%20could%20access%20this%20page%2C%20so%20there%20is%20no%20access-control%20baseline%20to%20compare%20against.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Own-Account%20Transfers%20Bypass%20Loan%20Credit%20Limits%20and%20TOTP%20Authorization%22%2C%22description%22%3A%22The%20own-account%20transfer%20endpoint%20does%20not%20enforce%20available-credit%20or%20balance%20limits%20when%20the%20source%20is%20a%20loan%20account.%20It%20also%20completed%20the%20observed%20transfer%20without%20a%20TOTP%20value.%20A%20loan%20account%20with%20a%20balance%20of%20-999%2C999%2C999%2C999.99%20was%20debited%20by%20an%20additional%201.00%2C%20resulting%20in%20a%20balance%20of%20-1%2C000%2C000%2C000%2C000.99%2C%20while%20the%20destination%20transaction%20account%20was%20credited.%22%2C%22impact%22%3A%22An%20authenticated%20customer%20with%20both%20loan%20and%20transaction%20accounts%20could%20transfer%20funds%20beyond%20the%20loan's%20approved%20principal%20or%20credit%20limit.%20Repeated%20exploitation%20could%20create%20unbounded%20account%20credit%20and%20compromise%20financial%20ledger%20integrity.%22%2C%22likelihood%22%3A%22High.%20The%20endpoint%20accepted%20a%20direct%20request%20from%20an%20authenticated%20customer%2C%20completed%20the%20transfer%20without%20TOTP%20authorization%2C%20and%20did%20not%20reject%20a%20debit%20that%20further%20exceeded%20the%20loan%20account's%20already-negative%20balance.%22%2C%22recommendation%22%3A%22Explicitly%20model%20and%20enforce%20approved%20loan%20principal%2C%20drawdown%20limits%2C%20and%20available%20credit%20before%20processing%20any%20transfer.%20Apply%20consistent%20balance%20and%20credit-limit%20validation%20across%20all%20source%20account%20types.%20Require%20server-side%20step-up%20authorization%2C%20including%20TOTP%20where%20policy%20requires%20it%2C%20for%20high-risk%20transfers.%20Process%20debit%20and%20credit%20operations%20atomically%20and%20enforce%20ledger%20invariants%20so%20that%20a%20transfer%20cannot%20complete%20if%20any%20authorization%20or%20limit%20check%20fails.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransfers%2Fown%22%2C%22evidence%22%3A%22A%20POST%20request%20transferred%201.00%20from%20loan%20account%2040%2C%20whose%20balance%20was%20-999999999999.99%2C%20to%20transaction%20account%2039%20without%20supplying%20a%20TOTP%20value.%20The%20endpoint%20returned%20HTTP%20201%20with%20status%20%60completed%60%2C%20a%20new%20source%20balance%20of%20%60-1000000000000.99%60%2C%20and%20a%20new%20destination%20balance%20of%20%601000000000000.99%60.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fown%5Cn%7B%5C%22from_account_id%5C%22%3A40%2C%5C%22to_account_id%5C%22%3A39%2C%5C%22amount%5C%22%3A%5C%221.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Loan%20negative-balance%20transfer%20probe%5C%22%7D%22%2C%22response_evidence%22%3A%22HTTP%20201%3A%20%60%7B%5C%22transaction_id%5C%22%3A37%2C%5C%22from_account_id%5C%22%3A40%2C%5C%22to_account_id%5C%22%3A39%2C%5C%22amount%5C%22%3A%5C%221.00%5C%22%2C...%2C%5C%22new_from_balance%5C%22%3A%5C%22-1000000000000.99%5C%22%2C%5C%22new_to_balance%5C%22%3A%5C%221000000000000.99%5C%22%2C...%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%7D%60%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unconfirmed%22%2C%22validation_note%22%3A%22The%20crawl%20did%20not%20record%20a%20user%20that%20could%20access%20this%20page%2C%20so%20there%20is%20no%20access-control%20baseline%20to%20compare%20against.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Administrative%20Endpoint%20Allows%20Unrestricted%20Balance%20Modification%22%2C%22description%22%3A%22The%20administrative%20endpoint%20at%20%60%2Fapi%2Fadmin%2Faccounts%2F39%2Fbalance%60%20permits%20an%20authenticated%20administrator%20to%20set%20an%20account%20balance%20directly%20to%20an%20unrestricted%20numeric%20value.%20The%20update%20is%20applied%20immediately%20without%20a%20maximum-value%20restriction%2C%20secondary%20approval%2C%20or%20transaction-based%20adjustment%20workflow.%20Testing%20was%20limited%20to%20a%20disposable%20account%20created%20during%20the%20assessment.%22%2C%22impact%22%3A%22A%20compromised%20or%20malicious%20administrator%20could%20create%20arbitrary%20funds%20or%20alter%20customer%20balances%2C%20undermining%20the%20integrity%20and%20auditability%20of%20the%20banking%20ledger.%20Extreme%20balance%20changes%20could%20also%20disrupt%20downstream%20processes%20that%20rely%20on%20valid%20account%20values.%22%2C%22likelihood%22%3A%22High%20in%20the%20observed%20environment%20because%20the%20endpoint%20is%20directly%20accessible%20through%20the%20API%20and%20the%20assessment%20had%20already%20confirmed%20predictable%20administrator%20credentials.%20Exploitation%20requires%20administrative%20privileges%20but%20is%20otherwise%20straightforward%20and%20requires%20only%20a%20single%20request.%22%2C%22recommendation%22%3A%22Remove%20the%20ability%20to%20set%20account%20balances%20directly.%20Implement%20balance%20changes%20as%20balanced%2C%20auditable%20ledger%20adjustment%20transactions%20with%20strict%20value%20limits%2C%20reason%20codes%2C%20and%20immutable%20audit%20records.%20Require%20maker-checker%20approval%20and%20step-up%20authentication%20for%20high-risk%20adjustments%2C%20and%20generate%20alerts%20for%20unusual%20values%20or%20activity.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AH%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Faccounts%2F39%2Fbalance%22%2C%22evidence%22%3A%22While%20authenticated%20as%20an%20administrator%2C%20a%20PUT%20request%20set%20disposable%20transaction%20account%2039's%20balance%20to%20%609999999999999.99%60.%20The%20API%20returned%20HTTP%20200%20and%20echoed%20the%20updated%20balance%2C%20with%20no%20secondary%20confirmation%20or%20limit%20rejection.%22%2C%22request_evidence%22%3A%22PUT%20%2Fapi%2Fadmin%2Faccounts%2F39%2Fbalance%5Cn%7B%5C%22balance%5C%22%3A%5C%229999999999999.99%5C%22%7D%22%2C%22response_evidence%22%3A%22HTTP%20200%3A%20%60%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A39%2C...%2C%5C%22balance%5C%22%3A%5C%229999999999999.99%5C%22%2C...%7D%2C%5C%22message%5C%22%3A%5C%22Balance%20updated%20successfully%5C%22%7D%60%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22Validation%20could%20not%20reproduce%20unauthorized%20access.%20Alternate%20users%20received%20an%20access%20denial%2C%20login%20response%2C%20generic%20SPA%20shell%2C%20or%20no%20protected%20content%20signal.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Broken%20Object-Level%20Authorization%20Exposes%20Other%20Customers'%20Transactions%22%2C%22description%22%3A%22The%20transaction%20detail%20endpoint%20retrieves%20transactions%20by%20numeric%20ID%20without%20verifying%20that%20the%20requested%20transaction%20belongs%20to%20an%20account%20owned%20by%20the%20authenticated%20user.%20A%20newly%20registered%20customer%20could%20access%20an%20unrelated%20customer's%20transaction%20by%20changing%20the%20transaction%20ID%20in%20the%20request.%22%2C%22impact%22%3A%22Any%20authenticated%20customer%20could%20enumerate%20and%20view%20other%20customers'%20sensitive%20transaction%20data%2C%20including%20source%20and%20destination%20account%20relationships%2C%20destination%20bank%20details%2C%20transaction%20amounts%2C%20descriptions%2C%20transfer%20types%2C%20and%20timestamps.%22%2C%22likelihood%22%3A%22High.%20Exploitation%20requires%20only%20a%20valid%20customer%20account%20and%20modification%20of%20a%20numeric%20transaction%20ID.%20The%20observed%20IDs%20were%20sequential%2C%20and%20the%20endpoint%20returned%20a%20foreign%20transaction%20directly%20with%20HTTP%20200.%22%2C%22recommendation%22%3A%22Enforce%20object-level%20authorization%20on%20every%20transaction%20lookup.%20Scope%20database%20queries%20to%20transactions%20associated%20with%20accounts%20owned%20by%20the%20authenticated%20user%20rather%20than%20retrieving%20records%20directly%20by%20primary%20key.%20Return%20a%20consistent%20HTTP%20404%20response%20when%20a%20transaction%20does%20not%20exist%20or%20the%20user%20is%20not%20authorized%20to%20access%20it%2C%20and%20add%20automated%20authorization%20tests%20covering%20cross-customer%20access%20attempts.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransactions%2F35%22%2C%22evidence%22%3A%22Newly%20registered%20user%20ID%2016%20owned%20account%2039%20and%20transaction%2036.%20Using%20that%20user's%20bearer%20token%2C%20GET%20%2Fapi%2Ftransactions%2F35%20returned%20HTTP%20200%20and%20disclosed%20transaction%2035%2C%20whose%20from_account_id%20was%2037%20and%20to_account_id%20was%2036.%20The%20response%20also%20exposed%20destination%20BSB%20062-015%2C%20destination%20account%20number%2025000001%2C%20amount%20400.00%2C%20and%20description%20%5C%22Bills%20top-up%2C%5C%22%20demonstrating%20access%20to%20a%20foreign%20transaction.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%2F35%20using%20the%20bearer%20token%20for%20newly%20registered%20user%20id%2016%22%2C%22response_evidence%22%3A%22HTTP%20200%20%7B%5C%22id%5C%22%3A35%2C%5C%22from_account_id%5C%22%3A37%2C%5C%22to_bsb%5C%22%3A%5C%22062-015%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2225000001%5C%22%2C%5C%22to_account_id%5C%22%3A36%2C%5C%22amount%5C%22%3A%5C%22400.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Bills%20top-up%5C%22%2C...%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22Validation%20could%20not%20reproduce%20unauthorized%20access.%20Alternate%20users%20received%20an%20access%20denial%2C%20login%20response%2C%20generic%20SPA%20shell%2C%20or%20no%20protected%20content%20signal.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Authenticated%20SQL%20Injection%20in%20Administrative%20Customer%20Search%22%2C%22description%22%3A%22The%20%60search%60%20parameter%20of%20the%20administrative%20customer%20listing%20API%20is%20incorporated%20into%20a%20SQL%20%60LIKE%60%20clause%20without%20safe%20parameterization.%20Supplying%20a%20single%20quote%20caused%20a%20MySQL%20syntax%20error%20and%20exposed%20the%20generated%20query%20fragment%2C%20confirming%20that%20attacker-controlled%20input%20reached%20the%20SQL%20statement.%20The%20error%20response%20also%20disclosed%20an%20internal%20source%20path%2C%20line%20number%2C%20and%20PHP%20stack%20trace.%22%2C%22impact%22%3A%22An%20authenticated%20administrator%20may%20be%20able%20to%20manipulate%20the%20customer%20search%20query%20and%20access%20or%20modify%20database%20information%20within%20the%20application's%20database%20privileges.%20The%20verbose%20error%20response%20additionally%20reveals%20internal%20paths%20and%20implementation%20details%20that%20could%20assist%20further%20exploitation.%22%2C%22likelihood%22%3A%22The%20issue%20is%20practically%20exploitable%20by%20an%20authenticated%20administrator%20because%20the%20vulnerable%20parameter%20is%20exposed%20through%20a%20routine%20administrative%20API%2C%20requires%20only%20a%20crafted%20search%20value%2C%20and%20produced%20a%20database%20syntax%20error%20demonstrating%20unsafe%20SQL%20construction.%20The%20captured%20evidence%20did%20not%20demonstrate%20successful%20data%20extraction%20or%20modification.%22%2C%22recommendation%22%3A%22Replace%20dynamic%20SQL%20construction%20with%20prepared%20statements%20and%20bound%20parameters%20for%20all%20search%20values.%20When%20using%20%60LIKE%60%2C%20bind%20the%20search%20pattern%20as%20data%20and%20escape%20%60%25%60%20and%20%60_%60%20when%20they%20should%20be%20treated%20literally.%20Disable%20detailed%20database%20and%20stack-trace%20responses%20in%20production%2C%20return%20a%20generic%20error%20to%20clients%2C%20and%20record%20full%20exception%20details%20only%20in%20protected%20server-side%20logs.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AH%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%26search%3D%2527%22%2C%22evidence%22%3A%22An%20authenticated%20GET%20request%20with%20%60search%3D%2527%60%20returned%20HTTP%20500%20and%20the%20MySQL%20error%20%60SQLSTATE%5B42000%5D%3A%20Syntax%20error%20or%20access%20violation%3A%201064%20...%20near%20'%25'%20OR%20last_name%20LIKE%20'%25'%25'%20OR%20email%20LIKE%20'%25'%25''%20at%20line%201%60.%20The%20response%20also%20disclosed%20%60%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FControllers%2FAdminUserController.php%60%2C%20line%2028%2C%20%60PDO-%3Equery()%60%2C%20and%20a%20PHP%20stack%20trace.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%26search%3D%2527%20with%20an%20authenticated%20admin%20bearer%20token.%22%2C%22response_evidence%22%3A%22HTTP%20500%3A%20%60SQLSTATE%5B42000%5D%3A%20Syntax%20error%20or%20access%20violation%3A%201064%20...%20near%20'%25'%20OR%20last_name%20LIKE%20'%25'%25'%20OR%20email%20LIKE%20'%25'%25''%20at%20line%201%60%3B%20details%20included%20%60file%5C%22%3A%5C%22%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FControllers%2FAdminUserController.php%5C%22%2C%5C%22line%5C%22%3A28%2C%5C%22trace%5C%22%3A%5C%22%230%20...%20PDO-%3Equery()%60.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Profile%20API%20Exposes%20Authentication%20Internals%22%2C%22description%22%3A%22The%20authenticated%20profile%20endpoint%20returns%20internal%20authentication%20fields%20that%20should%20not%20be%20included%20in%20client-facing%20responses.%20The%20observed%20response%20disclosed%20the%20user's%20bcrypt%20password%20hash%20and%20included%20the%20TOTP%20secret%20field%2C%20although%20its%20value%20was%20null%20for%20the%20tested%20account.%22%2C%22impact%22%3A%22Disclosure%20of%20password%20hashes%20may%20enable%20offline%20password%20cracking%20and%20subsequent%20credential-reuse%20attacks.%20Returning%20the%20TOTP%20secret%20field%20also%20creates%20a%20risk%20that%20MFA%20seeds%20could%20be%20disclosed%20for%20accounts%20where%20the%20field%20is%20populated%2C%20potentially%20allowing%20an%20attacker%20with%20profile%20access%20to%20reproduce%20one-time%20codes.%22%2C%22likelihood%22%3A%22Any%20authenticated%20user%2C%20or%20an%20attacker%20who%20obtains%20a%20valid%20bearer%20session%2C%20can%20access%20the%20affected%20response.%20Password-hash%20disclosure%20was%20directly%20confirmed%3B%20disclosure%20of%20a%20populated%20TOTP%20secret%20was%20not%20demonstrated%20because%20the%20tested%20account%20had%20TOTP%20disabled%20and%20the%20field%20was%20null.%22%2C%22recommendation%22%3A%22Define%20explicit%20response%20DTOs%20or%20serialization%20allowlists%20for%20profile%20data.%20Permanently%20exclude%20password%20hashes%2C%20TOTP%20seeds%2C%20password-reset%20tokens%2C%20session%20secrets%2C%20and%20all%20other%20authentication%20internals%20from%20API%20responses.%20Review%20other%20API%20endpoints%20for%20similar%20unsafe%20serialization%20and%20add%20automated%20tests%20that%20verify%20sensitive%20fields%20are%20never%20returned.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22An%20authenticated%20GET%20request%20to%20%2Fapi%2Fprofile%20returned%20HTTP%20200%20for%20user%20ID%203%20and%20included%20the%20bcrypt%20password_hash%20value%20%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%5C%5C%2F.og%5C%5C%2Fat2.uheWG%5C%5C%2Figi%5C%22.%20The%20response%20also%20serialized%20%5C%22totp_secret%5C%22%3Anull%20and%20indicated%20%5C%22totp_enabled%5C%22%3Afalse.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fprofile%20with%20a%20customer%20bearer%20session%22%2C%22response_evidence%22%3A%22%7B%5C%22id%5C%22%3A3%2C%5C%22email%5C%22%3A%5C%22zoe.williams%40example.com%5C%22%2C...%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%5C%5C%2F.og%5C%5C%2Fat2.uheWG%5C%5C%2Figi%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Registration%20Permits%20One-Character%20Passwords%22%2C%22description%22%3A%22The%20registration%20endpoint%20does%20not%20enforce%20an%20effective%20minimum%20password%20length.%20An%20account%20was%20successfully%20created%20through%20POST%20%2Fapi%2Fauth%2Fregister%20using%20the%20one-character%20password%20%5C%22a%5C%22.%22%2C%22impact%22%3A%22Users%20can%20create%20accounts%20with%20trivially%20guessable%20passwords%2C%20increasing%20the%20risk%20of%20unauthorized%20account%20access%20through%20password%20guessing.%22%2C%22likelihood%22%3A%22High.%20The%20unauthenticated%20registration%20endpoint%20accepted%20a%20one-character%20password%20and%20returned%20a%20successful%20account%20creation%20response.%22%2C%22recommendation%22%3A%22Enforce%20a%20server-side%20minimum%20password%20length%20of%20at%20least%2012%20characters%20and%20reject%20common%20or%20known-compromised%20passwords.%20Apply%20the%20same%20password%20policy%20consistently%20to%20registration%2C%20password%20reset%2C%20and%20password%20change%20workflows.%22%2C%22cvss_score%22%3A5.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22The%20endpoint%20returned%20HTTP%20201%20with%20the%20message%20%5C%22Registration%20successful%5C%22%20after%20receiving%20matching%20password%20and%20password_confirmation%20values%20of%20%5C%22a%5C%22.%20The%20response%20included%20the%20newly%20created%20user%20with%20ID%2016%20and%20an%20authentication%20token.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Fregister%20with%20password%3D%5C%22a%5C%22%20and%20password_confirmation%3D%5C%22a%5C%22%22%2C%22response_evidence%22%3A%22Status%20201%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A16%2C%5C%22email%5C%22%3A%5C%22aespa_9c959f18%40example.invalid%5C%22%2C...%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Sensitive%20data%20exposed%20in%20API%20response%22%2C%22description%22%3A%22The%20response%20contains%20field%20names%20commonly%20associated%20with%20secrets%2C%20hashes%2C%20tokens%2C%20debug%20state%2C%20or%20privileged%20metadata.%22%2C%22impact%22%3A%22Attackers%20can%20use%20leaked%20secrets%20or%20implementation%20details%20to%20compromise%20accounts%20or%20chain%20further%20attacks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20response%20analysis.%22%2C%22recommendation%22%3A%22Remove%20sensitive%20fields%20from%20client-facing%20responses%20and%20enforce%20response%20DTO%20allow-lists.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22REQUEST%3A%5CnREGISTER_ACCOUNT%20http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Fregister%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20201%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A16%2C%5C%22email%5C%22%3A%5C%22aespa_9c959f18%40example.invalid%5C%22%2C%5C%22first_name%5C%22%3A%5C%22A%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Tester%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22ff573fd9f7f93747e5d0f4b93a6e9dbd%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%22%2C%22request_evidence%22%3A%22REGISTER_ACCOUNT%20http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Fregister%22%2C%22response_evidence%22%3A%22Status%3A%20201%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A16%2C%5C%22email%5C%22%3A%5C%22aespa_9c959f18%40example.invalid%5C%22%2C%5C%22first_name%5C%22%3A%5C%22A%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Tester%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22ff573fd9f7f93747e5d0f4b93a6e9dbd%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Sensitive%20data%20exposed%20in%20API%20response%22%2C%22description%22%3A%22The%20response%20contains%20field%20names%20commonly%20associated%20with%20secrets%2C%20hashes%2C%20tokens%2C%20debug%20state%2C%20or%20privileged%20metadata.%22%2C%22impact%22%3A%22Attackers%20can%20use%20leaked%20secrets%20or%20implementation%20details%20to%20compromise%20accounts%20or%20chain%20further%20attacks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20response%20analysis.%22%2C%22recommendation%22%3A%22Remove%20sensitive%20fields%20from%20client-facing%20responses%20and%20enforce%20response%20DTO%20allow-lists.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fdebug%22%2C%22evidence%22%3A%22REQUEST%3A%5CnGET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fdebug%5Cnuse_session%3A%20(default)%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20404%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A22%3A50%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2078%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D95%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22Endpoint%20not%20found.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fdebug%5Cnuse_session%3A%20(default)%20%20Cookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20404%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A22%3A50%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2078%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D95%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22Endpoint%20not%20found.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Sensitive%20data%20exposed%20in%20API%20response%22%2C%22description%22%3A%22The%20response%20contains%20field%20names%20commonly%20associated%20with%20secrets%2C%20hashes%2C%20tokens%2C%20debug%20state%2C%20or%20privileged%20metadata.%22%2C%22impact%22%3A%22Attackers%20can%20use%20leaked%20secrets%20or%20implementation%20details%20to%20compromise%20accounts%20or%20chain%20further%20attacks.%22%2C%22likelihood%22%3A%22Confirmed%20by%20deterministic%20response%20analysis.%22%2C%22recommendation%22%3A%22Remove%20sensitive%20fields%20from%20client-facing%20responses%20and%20enforce%20response%20DTO%20allow-lists.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22REQUEST%3A%5CnPOST%20http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Flogin%5Cnuse_session%3A%20(default)%20%20Cookies%3A%20none%5Cn%7B%5C%22Content-Type%5C%22%3A%20%5C%22application%2Fjson%5C%22%7D%5Cn%7B%5C%22email%5C%22%3A%20%5C%22zoe.williams%40example.com%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22password%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A48%3A40%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20639%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D98%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A3%2C%5C%22email%5C%22%3A%5C%22zoe.williams%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Zoe%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Williams%5C%22%2C%5C%22address_line1%5C%22%3A%5C%223%20Queen%20St%5C%22%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3A%5C%22Brisbane%5C%22%2C%5C%22state%5C%22%3A%5C%22QLD%5C%22%2C%5C%22postcode%5C%22%3A%5C%224000%5C%22%2C%5C%22phone%5C%22%3A%5C%220433%20456%20789%5C%22%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%5C%5C%2F.og%5C%5C%2Fat2.uheWG%5C%5C%2Figi%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Login%20successful%5C%22%7D%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Flogin%5Cnuse_session%3A%20(default)%20%20Cookies%3A%20none%5Cn%7B%5C%22Content-Type%5C%22%3A%20%5C%22application%2Fjson%5C%22%7D%5Cn%7B%5C%22email%5C%22%3A%20%5C%22zoe.williams%40example.com%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22password%5C%22%7D%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2004%3A48%3A40%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20639%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D98%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A3%2C%5C%22email%5C%22%3A%5C%22zoe.williams%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Zoe%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Williams%5C%22%2C%5C%22address_line1%5C%22%3A%5C%223%20Queen%20St%5C%22%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3A%5C%22Brisbane%5C%22%2C%5C%22state%5C%22%3A%5C%22QLD%5C%22%2C%5C%22postcode%5C%22%3A%5C%224000%5C%22%2C%5C%22phone%5C%22%3A%5C%220433%20456%20789%5C%22%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%5C%5C%2F.og%5C%5C%2Fat2.uheWG%5C%5C%2Figi%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Login%20successful%5C%22%7D%22%2C%22finding_source%22%3A%22deterministic_probe%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20by%20deterministic%20module.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Authenticated%20Error-Based%20SQL%20Injection%20in%20Transaction%20Sort%20Parameter%22%2C%22description%22%3A%22The%20authenticated%20GET%20%2Fapi%2Ftransactions%20endpoint%20incorporates%20the%20user-controlled%20sort%20parameter%20into%20the%20SQL%20ORDER%20BY%20clause%20without%20restricting%20it%20to%20permitted%20values.%20A%20grammar-compatible%20EXTRACTVALUE%20payload%20was%20evaluated%20by%20MySQL%2C%20and%20the%20resulting%20error%20disclosed%20the%20value%20of%20DATABASE().%20The%20endpoint%20also%20returns%20verbose%20database%20exceptions%2C%20application%20file%20paths%2C%20line%20numbers%2C%20and%20stack-trace%20details.%22%2C%22impact%22%3A%22A%20low-privileged%20authenticated%20customer%20can%20evaluate%20attacker-controlled%20SQL%20expressions%20and%20retrieve%20database%20values%20through%20error%20messages.%20This%20could%20allow%20access%20to%20database%20information%20beyond%20the%20customer's%20authorized%20transaction%20scope%2C%20depending%20on%20the%20privileges%20of%20the%20application's%20database%20account.%20Crafted%20expressions%20could%20also%20consume%20database%20resources%20and%20affect%20service%20availability.%22%2C%22likelihood%22%3A%22High.%20Exploitation%20requires%20only%20a%20normal%20authenticated%20customer%20session%20and%20a%20crafted%20sort%20parameter.%20The%20demonstrated%20payload%20executed%20without%20user%20interaction%20or%20a%20race%20condition%2C%20and%20the%20resulting%20database%20value%20was%20returned%20directly%20in%20the%20HTTP%20response.%22%2C%22recommendation%22%3A%22Map%20the%20sort%20parameter%20to%20a%20strict%20server-side%20allowlist%20of%20permitted%20column%20names%20and%20sort%20directions.%20Select%20fixed%20ORDER%20BY%20fragments%20in%20application%20logic%20rather%20than%20concatenating%20user%20input%2C%20and%20return%20HTTP%20400%20for%20unsupported%20values.%20Continue%20to%20parameterize%20all%20SQL%20value%20inputs.%20Disable%20detailed%20exception%20responses%20in%20production%2C%20return%20generic%20errors%20to%20clients%2C%20and%20retain%20full%20diagnostics%20only%20in%20server-side%20logs.%20Review%20and%20minimize%20the%20application%20database%20account's%20privileges.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransactions%3Fsort%3Dcreated_at%252CEXTRACTVALUE(1%252CCONCAT(0x7e%252CDATABASE()))%26per_page%3D10%22%2C%22evidence%22%3A%22A%20baseline%20request%20using%20sort%3Dcreated_at%20returned%20HTTP%20200.%20Using%20sort%3D%2527%20returned%20HTTP%20500%20with%20SQLSTATE%5B42000%5D%2C%20the%20path%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FModels%2FTransaction.php%2C%20line%2055%2C%20and%20a%20stack%20trace.%20The%20payload%20sort%3Dcreated_at%2CEXTRACTVALUE(1%2CCONCAT(0x7e%2CDATABASE()))%20returned%20HTTP%20500%20with%20%5C%22XPATH%20syntax%20error%3A%20'~bankofed'%5C%22%2C%20demonstrating%20execution%20of%20the%20injected%20SQL%20expression%20and%20disclosure%20of%20the%20current%20database%20name.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Fsort%3Dcreated_at%252CEXTRACTVALUE(1%252CCONCAT(0x7e%252CDATABASE()))%26per_page%3D10%20(authenticated%20customer%20token)%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20500%20Internal%20Server%20Error%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INTERNAL_ERROR%5C%22%2C%5C%22message%5C%22%3A%5C%22SQLSTATE%5BHY000%5D%3A%20General%20error%3A%201105%20XPATH%20syntax%20error%3A%20'~bankofed'%5C%22%2C%5C%22details%5C%22%3A%7B%5C%22file%5C%22%3A%5C%22%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FModels%2FTransaction.php%5C%22%2C%5C%22line%5C%22%3A55%2C%5C%22trace%5C%22%3A%5C%22...%5C%22%7D%7D%7D%22%2C%22finding_source%22%3A%22alice%22%2C%22validation_status%22%3A%22validating%22%2C%22validation_note%22%3A%22Validation%20running.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22API%20reflects%20arbitrary%20CORS%20origins%20for%20sensitive%20authenticated%20responses%22%2C%22description%22%3A%22The%20API%20reflects%20attacker-controlled%20Origin%20values%20on%20authenticated%20responses%20and%20permits%20broad%20cross-origin%20methods%2Fheaders.%20The%20profile%20response%20contains%20PII%20and%20authentication%20internals.%22%2C%22impact%22%3A%22The%20policy%20unnecessarily%20permits%20arbitrary%20websites%20to%20issue%20and%20read%20API%20requests%20when%20they%20can%20supply%20or%20obtain%20a%20bearer%20token%2C%20increasing%20the%20impact%20of%20token%20leakage%20and%20cross-origin%20attack%20chains.%22%2C%22likelihood%22%3A%22Moderate%3B%20browser%20exploitation%20requires%20access%20to%20a%20valid%20bearer%20token%20because%20the%20application%20stores%20JWTs%20in%20localStorage.%22%2C%22recommendation%22%3A%22Allow%20only%20explicitly%20trusted%20application%20origins%2C%20restrict%20methods%20and%20headers%20per%20endpoint%2C%20and%20do%20not%20enable%20credentials%20for%20wildcard%2Fdynamic%20origins.%22%2C%22cvss_score%22%3A2.6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AL%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22GET%20%2Fapi%2Fprofile%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20returned%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20the%20complete%20profile.%20OPTIONS%20for%20the%20same%20origin%20returned%20HTTP%20200.%20Captured%20API%20responses%20also%20advertise%20Access-Control-Allow-Credentials%3A%20true%2C%20Access-Control-Allow-Headers%3A%20*%2C%20and%20broad%20methods.%5Cn%5CnREQUEST%3A%5CnGET%20%2Fapi%2Fprofile%20with%20Authorization%20bearer%20token%20and%20Origin%3A%20https%3A%2F%2Fevil.example%3B%20OPTIONS%20%2Fapi%2Fprofile%20with%20requested%20Authorization%20header%5Cn%5CnRESPONSE%3A%5CnHTTP%20200%2C%20access-control-allow-origin%3A%20https%3A%2F%2Fevil.example%2C%20body%20included%20email%2C%20password_hash%2C%20and%20totp_secret.%20Preflight%20returned%20HTTP%20200.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fprofile%20with%20Authorization%20bearer%20token%20and%20Origin%3A%20https%3A%2F%2Fevil.example%3B%20OPTIONS%20%2Fapi%2Fprofile%20with%20requested%20Authorization%20header%22%2C%22response_evidence%22%3A%22HTTP%20200%2C%20access-control-allow-origin%3A%20https%3A%2F%2Fevil.example%2C%20body%20included%20email%2C%20password_hash%2C%20and%20totp_secret.%20Preflight%20returned%20HTTP%20200.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Insufficient%20Login%20Rate%20Limiting%20and%20Account%20Lockout%22%2C%22description%22%3A%22The%20login%20endpoint%20did%20not%20apply%20observable%20rate%20limiting%2C%20progressive%20delays%2C%20CAPTCHA%20challenges%2C%20or%20account%20lockout%20after%20six%20consecutive%20failed%20authentication%20attempts%20against%20a%20known%20account.%20Each%20attempt%20received%20the%20same%20immediate%20HTTP%20401%20wrong-password%20response.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20could%20conduct%20sustained%20password-guessing%20or%20credential-stuffing%20attacks%20against%20customer%20accounts%2C%20increasing%20the%20risk%20of%20account%20compromise%20when%20weak%20or%20reused%20credentials%20are%20present.%22%2C%22likelihood%22%3A%22High.%20The%20authentication%20endpoint%20is%20publicly%20accessible%2C%20and%20no%20defensive%20response%20was%20observed%20during%20six%20consecutive%20failed%20attempts.%20The%20application%20also%20permits%20valid-user%20enumeration%2C%20which%20can%20help%20attackers%20select%20accounts%20to%20target.%22%2C%22recommendation%22%3A%22Implement%20layered%20authentication%20abuse%20protections%2C%20including%20per-account%20and%20per-source%20throttling%2C%20progressive%20or%20exponential%20backoff%2C%20risk-based%20CAPTCHA%20or%20step-up%20challenges%2C%20monitoring%20and%20alerting%2C%20and%20temporary%20account%20lockouts.%20Design%20lockout%20controls%20to%20minimize%20account%20denial-of-service%20risk%2C%20and%20return%20consistent%20authentication%20errors%20that%20do%20not%20facilitate%20user%20enumeration.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Exactly%20six%20consecutive%20login%20requests%20were%20submitted%20for%20zoe.williams%40example.com%20using%20distinct%20incorrect%20passwords.%20All%20returned%20HTTP%20401%20with%20the%20WRONG_PASSWORD%20response%20in%20approximately%20103-127%20ms.%20Attempt%201%20completed%20in%20115%20ms%20and%20attempt%206%20in%20103%20ms%2C%20with%20no%20HTTP%20429%20response%2C%20increasing%20delay%2C%20or%20account%20lockout%20observed.%22%2C%22request_evidence%22%3A%22Exactly%206%20consecutive%20POST%20%2Fapi%2Fauth%2Flogin%20requests%20for%20zoe.williams%40example.com%20with%20distinct%20incorrect%20passwords%22%2C%22response_evidence%22%3A%22Attempt%201%3A%20%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%2C%20115ms.%20Attempt%206%3A%20identical%20response%2C%20103ms.%20No%20429%20or%20lockout.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Insufficient%20Rate%20Limiting%20on%20Administrative%20Login%22%2C%22description%22%3A%22The%20administrative%20login%20endpoint%20did%20not%20impose%20observable%20rate%20limiting%20or%20account%20lockout%20after%20six%20consecutive%20failed%20authentication%20attempts%20against%20the%20%60admin%60%20username.%20Each%20attempt%20returned%20the%20same%20HTTP%20401%20response%20without%20an%20HTTP%20429%20response%2C%20progressive%20delay%2C%20CAPTCHA%2C%20lockout%2C%20or%20other%20challenge.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20could%20repeatedly%20attempt%20password%20guessing%20or%20credential-stuffing%20attacks%20against%20the%20privileged%20administrator%20account.%20If%20valid%20credentials%20are%20discovered%2C%20the%20attacker%20could%20gain%20access%20to%20sensitive%20customer%20and%20financial%20administration%20functions.%22%2C%22likelihood%22%3A%22The%20endpoint%20is%20reachable%20without%20authentication%20and%20the%20tested%20%60admin%60%20username%20is%20predictable.%20Although%20testing%20was%20intentionally%20limited%20to%20six%20attempts%20and%20does%20not%20establish%20behavior%20at%20higher%20thresholds%2C%20no%20defensive%20control%20was%20observed%20within%20the%20tested%20sequence.%22%2C%22recommendation%22%3A%22Implement%20layered%20protections%20for%20administrative%20authentication%2C%20including%20per-account%20and%20per-source%20rate%20limits%2C%20progressive%20delays%2C%20and%20temporary%20account%20lockouts.%20Require%20MFA%20for%20administrative%20accounts%2C%20monitor%20and%20alert%20on%20repeated%20authentication%20failures%2C%20and%20use%20consistent%20failure%20responses%20that%20do%20not%20disclose%20account%20state.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Exactly%20six%20consecutive%20login%20attempts%20were%20submitted%20for%20username%20%60admin%60%2C%20each%20using%20a%20distinct%20invalid%20password%20(%60wrong-aespa-1%60%20through%20%60wrong-aespa-6%60).%20Attempts%201%20through%206%20all%20returned%20HTTP%20401%20with%20%60success%3Dfalse%60%3B%20no%20HTTP%20429%20response%2C%20lockout%2C%20CAPTCHA%2C%20or%20other%20change%20in%20response%20behavior%20was%20observed.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20JSON%20username%20%60admin%60%20and%20six%20distinct%20invalid%20passwords%20(%60wrong-aespa-1%60%20through%20%60wrong-aespa-6%60).%22%2C%22response_evidence%22%3A%22Attempt%20statuses%3A%20401%2C%20401%2C%20401%2C%20401%2C%20401%2C%20401%3B%20all%20reported%20success%3Dfalse%20and%20no%20throttling%20response.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Login%20Endpoint%20Permits%20Email%20Address%20Enumeration%22%2C%22description%22%3A%22The%20unauthenticated%20login%20endpoint%20discloses%20whether%20an%20email%20address%20is%20registered%20by%20returning%20different%20error%20codes%20and%20messages%20for%20known%20and%20unknown%20addresses.%20The%20tested%20responses%20also%20exhibited%20a%20timing%20difference.%22%2C%22impact%22%3A%22An%20attacker%20could%20identify%20registered%20customer%20email%20addresses%20and%20use%20this%20information%20to%20target%20password-guessing%2C%20credential-stuffing%2C%20or%20phishing%20attacks.%22%2C%22likelihood%22%3A%22High%3B%20enumeration%20requires%20only%20unauthenticated%20login%20requests%20and%20can%20be%20performed%20by%20comparing%20the%20returned%20error%20codes%20and%20messages.%22%2C%22recommendation%22%3A%22Return%20the%20same%20generic%20message%2C%20application%20error%20code%2C%20and%20HTTP%20status%20for%20all%20failed%20authentication%20attempts%2C%20regardless%20of%20whether%20the%20account%20exists.%20Ensure%20that%20authentication%20failure%20paths%20have%20comparable%20processing%20times%20and%20apply%20rate%20limiting%20and%20monitoring%20to%20repeated%20login%20attempts.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22A%20login%20attempt%20for%20the%20known%20address%20zoe.williams%40example.com%20returned%20HTTP%20401%20with%20%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%20in%20115%20ms.%20Using%20the%20same%20incorrect%20password%20for%20nonexistent-aespa%40example.com%20returned%20HTTP%20401%20with%20%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D%20in%2016%20ms.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20with%20the%20same%20wrong%20password%2C%20first%20for%20a%20known%20email%20and%20then%20an%20unknown%20email%22%2C%22response_evidence%22%3A%22Known%3A%20HTTP%20401%20%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%3B%20unknown%3A%20HTTP%20401%20%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20Browser%20Security%20Headers%20and%20Apache%20Version%20Disclosure%22%2C%22description%22%3A%22The%20HTML%20response%20at%20the%20application%20root%20omits%20the%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy%20headers.%20The%20response%20also%20discloses%20the%20exact%20web%20server%20and%20operating%20system%20distribution%20through%20the%20Server%20header%3A%20Apache%2F2.4.58%20(Ubuntu).%22%2C%22impact%22%3A%22The%20missing%20headers%20reduce%20browser-side%20defense%20in%20depth%20against%20framing%2C%20content-type%20confusion%2C%20referrer%20leakage%2C%20and%20the%20impact%20of%20potential%20content%20injection.%20The%20detailed%20Server%20header%20provides%20information%20that%20may%20assist%20attacker%20reconnaissance.%20Exploitation%20of%20the%20missing%20headers%20generally%20requires%20user%20interaction%20or%20an%20additional%20application%20weakness.%22%2C%22likelihood%22%3A%22The%20omissions%20and%20version%20disclosure%20are%20directly%20observable%20by%20any%20unauthenticated%20remote%20user.%20However%2C%20meaningful%20security%20impact%20depends%20on%20browser%20interaction%20or%20another%20exploitable%20weakness.%22%2C%22recommendation%22%3A%22Define%20a%20restrictive%20Content-Security-Policy%20appropriate%20for%20the%20application%2C%20including%20a%20frame-ancestors%20directive%20such%20as%20frame-ancestors%20'none'%20where%20framing%20is%20not%20required.%20Alternatively%2C%20set%20X-Frame-Options%3A%20DENY.%20Add%20X-Content-Type-Options%3A%20nosniff%20and%20Referrer-Policy%3A%20strict-origin-when-cross-origin.%20Configure%20Apache%20to%20suppress%20detailed%20version%20and%20operating%20system%20information%20in%20the%20Server%20header.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2F%22%2C%22evidence%22%3A%22A%20GET%20request%20to%20%2F%20returned%20HTTP%20200%20with%20Server%3A%20Apache%2F2.4.58%20(Ubuntu).%20The%20response%20did%20not%20include%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20or%20Referrer-Policy%20headers.%22%2C%22request_evidence%22%3A%22GET%20%2F%22%2C%22response_evidence%22%3A%22HTTP%20200%20headers%20included%20server%3A%20Apache%2F2.4.58%20(Ubuntu)%20and%20omitted%20the%20listed%20security%20headers.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%5D
-->

## 1. Administrative interface accessible with default credentials

- Severity: critical
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The administrative login accepts the predictable credentials admin/admin123 and issues a privileged JWT.

### Impact
An unauthenticated attacker could take control of the administrative interface, enumerate customers and their personal information, and potentially perform privileged account or system-management operations.

### Likelihood
Highly likely because the credentials are trivial to guess and were successfully used without any additional authentication factor.

### Recommendation
Disable all default credentials, require a unique high-entropy administrator password during deployment, rotate the exposed account credentials, require MFA for administrative access, and monitor for prior unauthorized logins.

### Evidence
```
POST /api/admin/auth/login with {"username":"admin","password":"admin123"} returned HTTP 200 and an admin JWT. The resulting session retrieved /api/admin/customers and displayed names, email addresses, phone numbers, account counts, and 2FA status for 15 customers.

REQUEST:
GET http://192.168.3.101/api/profile
use_session: legit_admin  Cookies: none
{}

RESPONSE:
Status: 401
date: Tue, 14 Jul 2026 04:33:57 GMT
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
content-length: 102
keep-alive: timeout=5, max=98
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Missing or invalid Authorization header."}}
```

### Request Evidence
```
GET http://192.168.3.101/api/profile
use_session: legit_admin  Cookies: none
{}
```

### Response Evidence
```
Status: 401
date: Tue, 14 Jul 2026 04:33:57 GMT
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
content-length: 102
keep-alive: timeout=5, max=98
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Missing or invalid Authorization header."}}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 2. External Transfer Endpoint Bypasses TOTP and Sufficient-Funds Validation

- Severity: critical
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/transfers/external
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N)

### Description
The external transfer workflow does not enforce mandatory TOTP verification or sufficient-funds validation at the final transfer endpoint. Although the preflight endpoint reported that TOTP was required for a manually entered transfer, the application completed a direct request to POST /api/transfers/external without a totp_code. The same transaction reduced the source account balance below zero.

### Impact
An attacker with access to an authenticated session could complete external transfers without satisfying the required TOTP control. The missing balance validation also allows transfers that exceed the available account balance, resulting in unauthorized negative balances or overdrafts.

### Likelihood
High. Exploitation requires an authenticated session but only involves calling the external transfer endpoint directly while omitting the TOTP code. No additional bypass technique was required in the observed test.

### Recommendation
Enforce TOTP verification and all transfer prerequisites within the final transfer service rather than relying on preflight or client-side workflow checks. Before committing a transfer, atomically lock and revalidate the source account's ownership, active status, available balance or authorized overdraft limit, and required verification state. Reject the transaction if TOTP is required but absent or invalid, or if sufficient funds are unavailable.

### Evidence
```
POST /api/transfers/check returned {"requires_totp":true,"reason":"manual_entry","totp_configured":false}. A direct POST to /api/transfers/external without totp_code returned HTTP 201 and reported "totp_verified":false, "status":"completed", and "new_from_balance":"-1.00", together with the message "Transfer completed successfully".
```

### Request Evidence
```
POST /api/transfers/external {"from_account_id":39,"to_bsb":"062-000","to_account_number":"12345678","payee_name":"Test","amount":1,"description":"direct without totp"} with no totp_code
```

### Response Evidence
```
HTTP 201 {"transaction_id":36,...,"totp_verified":false,"new_from_balance":"-1.00","status":"completed"}, "Transfer completed successfully"
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 3. Hardcoded JWT Signing Secret Enables Authentication Bypass

- Severity: critical
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The application uses the hardcoded fallback secret `bankofed-dev-secret-change-in-production` to validate HS256 JWTs. The `/api/profile` endpoint accepted a locally forged token containing `sub: 3` without requiring authentication and returned the profile associated with that customer ID.

### Impact
An unauthenticated attacker who knows the shipped secret can forge valid JWTs for arbitrary customer IDs, impersonate customers, access their financial and personal information, and perform authenticated banking actions in their names.

### Likelihood
High. The signing secret is static, present in the application configuration, and was confirmed to be active in the tested deployment by successfully using it to forge an accepted JWT.

### Recommendation
Immediately replace the hardcoded secret with a cryptographically random, high-entropy, deployment-specific signing key. Remove all fallback signing secrets and require secure key configuration at startup, failing closed when it is absent. Rotate the exposed key and invalidate all JWTs signed with it. Store signing keys in an appropriate secrets-management system and establish a controlled key-rotation process.

### Evidence
```
A locally forged HS256 JWT signed with `bankofed-dev-secret-change-in-production` and containing claims `{"iss":"BankOfEd","sub":3,"jti":"sast-default-secret-probe-62","iat":1784030000,"exp":1784116400}` was accepted by `/api/profile`. The endpoint returned HTTP 200 and profile data for `zoe.williams@example.com`, demonstrating successful token forgery and impersonation of user ID 3.
```

### Request Evidence
```
GET /api/profile with Authorization: Bearer <locally forged HS256 JWT signed using the shipped fallback secret>.
```

### Response Evidence
```
HTTP 200: `{"success":true,"data":{"id":3,"email":"zoe.williams@example.com","first_name":"Zoe","last_name":"Williams",...},"message":"OK"}`
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 4. Unrestricted Self-Issued Loans Credit Arbitrary Funds

- Severity: critical
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/accounts
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H)

### Description
The account creation endpoint accepts an attacker-controlled `borrow_amount` for loan accounts without enforcing a maximum loan value, underwriting, approval, or affordability controls. During testing, a disposable authenticated customer requested a loan of 999,999,999,999.99 AUD, and the application immediately credited the full amount to the specified transaction account.

### Impact
Any authenticated customer could create an effectively arbitrary account balance without authorization or legitimate funding. This compromises the application's financial integrity and could enable fraudulent transfers or withdrawals, resulting in severe financial loss and disruption.

### Likelihood
High. Customer registration is public, exploitation requires only a simple authenticated API request, and no privileged role, approval, or other special precondition was required in the observed workflow.

### Recommendation
Enforce strict server-side minimum and maximum loan limits using safe fixed-precision decimal validation. Require underwriting, affordability checks, credit approval, and maker-checker authorization before creating or disbursing a loan. Perform loan creation and disbursement through controlled transactional workflows, and block or alert on anomalous loan amounts and disbursements.

### Evidence
```
A POST request to `/api/accounts` by disposable user ID 16 specified `account_type` as `loan`, `borrow_amount` as `999999999999.99`, and `disbursement_account_id` as 39. The server returned HTTP 201 and created loan account ID 40 with a balance of `-999999999999.99`. A subsequent GET request for account 39 showed a balance of `999999999999.99` and transaction ID 36, described as `Loan proceeds disbursement`, for the same amount.
```

### Request Evidence
```
POST /api/accounts
{"account_type":"loan","account_name":"Excessive Loan Probe","currency":"AUD","borrow_amount":"999999999999.99","disbursement_account_id":39}
```

### Response Evidence
```
HTTP 201: `{"id":40,...,"account_type":"loan",...,"balance":"-999999999999.99"}`. Follow-up destination account response: `"balance":"999999999999.99"` and `"amount":"999999999999.99","description":"Loan proceeds disbursement"`.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 5. Unauthenticated Health Endpoint Exposes JWT Signing Secret and Database Configuration

- Severity: critical
- OWASP: A05
- Source: A.L.I.C.E
- Validation: validating
- Affected URL: http://192.168.3.101/api/health
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
The unauthenticated health endpoint at `/api/health` returns the production JWT HMAC signing secret and internal configuration details, including the database host, database name, database user, PHP version, Apache version, and deployment environment.

### Impact
An attacker who obtains the JWT signing secret could potentially forge valid authentication tokens and impersonate customers or administrators. The disclosed database and runtime metadata also provides useful information for follow-on attacks.

### Likelihood
High. The endpoint is remotely accessible without authentication, and a single GET request returns the JWT signing secret directly in the response body.

### Recommendation
Immediately rotate the exposed JWT signing secret and invalidate all tokens signed with the compromised value. Review logs for suspected token forgery or unauthorized access. Remove secrets and internal configuration data from health responses, returning only a minimal service-status indicator. Restrict operational health endpoints to authenticated monitoring systems or trusted management networks, and ensure secrets are stored and retrieved through an appropriate secrets-management mechanism.

### Evidence
```
An unauthenticated GET request to `/api/health` returned HTTP 200 and disclosed the production environment, PHP and Apache versions, database host (`127.0.0.1`), database name (`bankofed`), database user (`bankofed_app`), and JWT signing secret (`u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw`) in the JSON response.
```

### Request Evidence
```
GET /api/health HTTP/1.1
Host: 192.168.3.101
Origin: https://evil.example
```

### Response Evidence
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://evil.example
Access-Control-Allow-Credentials: true
Content-Type: application/json

{"success":true,"data":{"status":"ok","php_version":"8.3.31","server":"Apache/2.4.58 (Ubuntu)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"bankofed_app","jwt_secret":"u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw","environment":"production"},"message":"OK"}
```

### Validation Note
Validation running.

## 6. Administrative credentials and bearer tokens transmitted over cleartext HTTP

- Severity: high
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 7.3 (CVSS:3.1/AV:A/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N)

### Description
The administrative authentication flow operates over unencrypted HTTP. The login request contains the administrator password in plaintext at the transport layer, and the response returns a reusable bearer JWT over the same connection.

### Impact
An attacker able to observe or modify network traffic could steal the administrator password or JWT, hijack the administrative session, and access sensitive customer information.

### Likelihood
Practical for an attacker on the same or an intermediary network whenever an administrator signs in or uses the application.

### Recommendation
Serve the application exclusively over HTTPS using a valid certificate, redirect all HTTP traffic to HTTPS, enable HSTS after HTTPS is deployed, and rotate credentials and tokens previously transmitted over HTTP.

### Evidence
```
The browser sent the admin/admin123 login request to an http:// URL, and the HTTP 200 response returned a reusable HS256 JWT without transport encryption.

REQUEST:
GET http://192.168.3.101/api/profile
use_session: legit_admin  Cookies: none
{}

RESPONSE:
Status: 401
date: Tue, 14 Jul 2026 04:33:57 GMT
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
content-length: 102
keep-alive: timeout=5, max=98
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Missing or invalid Authorization header."}}
```

### Request Evidence
```
GET http://192.168.3.101/api/profile
use_session: legit_admin  Cookies: none
{}
```

### Response Evidence
```
Status: 401
date: Tue, 14 Jul 2026 04:33:57 GMT
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
content-length: 102
keep-alive: timeout=5, max=98
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Missing or invalid Authorization header."}}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 7. Avatar URL Import Permits SSRF to Loopback Services and Returns Response Content

- Severity: high
- OWASP: A10
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile/avatar
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N)

### Description
The avatar import endpoint accepts an arbitrary URL, retrieves it server-side, and returns the response bytes as a base64-encoded data URI. The endpoint permits requests to loopback addresses and does not restrict imported content to images.

### Impact
An authenticated attacker can access internal HTTP services that are not otherwise externally reachable and exfiltrate their responses through the application. In the observed case, this exposed internal health information containing a JWT secret and database configuration settings. Access to other internal services could expose additional sensitive data or administrative functionality.

### Likelihood
High. Exploitation requires only an authenticated request containing an internal URL. Successful access to a loopback service and retrieval of its response content were confirmed.

### Recommendation
Remove support for arbitrary server-side URL retrieval where possible. If remote avatar import is required, enforce a strict allowlist of trusted HTTPS image hosts. Resolve hostnames and block loopback, private, link-local, multicast, reserved, and cloud metadata address ranges before each request and after every redirect. Prevent DNS rebinding, restrict redirects and outbound network access, validate that responses are approved image types, enforce file-size and timeout limits, and run the fetcher in an isolated environment without access to sensitive internal services.

### Evidence
```
A request for the loopback URL http://127.0.0.1:80/api/health returned HTTP 200 and included the fetched response as an application/json base64 data URI. Decoding the 280-byte value disclosed db_host, db_name, db_user, jwt_secret, and environment. A request to the unused loopback port 127.0.0.1:1 returned FETCH_FAILED, further demonstrating server-side connection attempts.
```

### Request Evidence
```
POST /api/profile/avatar {"url":"http://127.0.0.1:80/api/health"}
```

### Response Evidence
```
HTTP 200 {"avatar_data":"data:application/json; charset=utf-8;base64,...","size":280,"source_url":"http://127.0.0.1:80/api/health"}. Decoded data includes db_host, db_name, db_user, jwt_secret, and environment.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 8. External Transfer Endpoint Allows Duplicate Concurrent Submissions

- Severity: high
- OWASP: API6
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/transfers/external
- CVSS: 7.4 (CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:H/A:H)

### Description
The external transfer creation endpoint does not enforce idempotency when identical requests are submitted concurrently. Two simultaneous POST requests to /api/transfers/external using the same Idempotency-Key and identical transfer details were each processed as separate completed transactions.

### Impact
An authenticated attacker, network retry condition, or concurrent request burst could cause a transfer to be executed multiple times, resulting in repeated debits from the source account. The observed responses also indicated that the duplicate transfers completed without TOTP verification.

### Likelihood
High. Duplicate processing was reproduced using two simultaneous requests with the same Idempotency-Key and request body.

### Recommendation
Implement server-side idempotency controls for transfer creation. Require a cryptographically random idempotency key and atomically persist the key, a request fingerprint, and the resulting transaction identifier before executing the debit. For subsequent requests using the same key, return the original result without re-executing the transfer. Use transaction locking and database-level unique constraints to prevent race conditions and concurrent duplicate debits.

### Evidence
```
Two simultaneous POST requests to /api/transfers/external used the identical request body and Idempotency-Key: repeatability-test-20260714. Both requests returned HTTP 201 and status "completed", but generated separate transactions: transaction_id 43 with new_from_balance "18899.99" and transaction_id 44 with new_from_balance "18899.98". Both responses included "totp_verified": false, demonstrating sequential duplicate debits despite reuse of the same idempotency key.
```

### Request Evidence
```
Both requests: POST /api/transfers/external; shared header `Idempotency-Key: repeatability-test-20260714`; body `{"from_account_id":2,"to_bsb":"062-000","to_account_number":"12345678","payee_name":"Repeatability Test","amount":0.01,"description":"identical concurrent request"}`.
```

### Response Evidence
```
HTTP 201 responses with different transaction IDs 43 and 44 and sequential balance debits.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 9. Stored DOM XSS in Transfer Payee Dropdown

- Severity: high
- OWASP: A03
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://192.168.3.101/banking/#/transfers
- CVSS: 7.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:H/A:N)

### Description
Authenticated users can store HTML markup in address-book `nickname` or `payee_name` fields. On the transfers page, address-book entries are used to construct `<option>` elements through string concatenation and assigned with `innerHTML`. Because the label is not HTML-encoded, attacker-controlled content can close the intended option element and introduce executable markup.

### Impact
JavaScript can execute in the banking application's origin whenever a user loads the transfers page containing the malicious address-book entry. An attacker able to create or modify an address-book entry could perform actions with the affected user's authenticated browser context, including accessing page-readable banking information and issuing same-origin requests.

### Likelihood
High. The payload was successfully persisted and returned unencoded by the address-book API, and the transfers page loads address-book entries before inserting the resulting option markup through `innerHTML`. Exploitation requires an attacker to create or modify an address-book entry and a user to render the transfers page.

### Recommendation
Do not generate `<option>` markup using string concatenation or assign untrusted values through `innerHTML`. Create options with `document.createElement('option')`, assign the identifier through `option.value`, and assign the display label through `option.textContent`. Apply context-appropriate output encoding in all address-book rendering views and enforce server-side validation for address-book names using a restrictive character policy where appropriate.

### Evidence
```
A PUT request to `/api/address-book/21` set both `nickname` and `payee_name` to `</option><img src=x onerror="document.title='AESPA_XSS_7419'">`. A subsequent HTTP 200 response from `GET /api/address-book/21` returned both values unchanged and unencoded. Static evidence from `transfers.js` shows `entry.nickname || entry.payee_name` is incorporated into an `<option>` string and inserted using `sel.innerHTML = options`. The transfers route calls `Api.getAddressBook()` and then `populatePayeeDropdown()`, connecting the persisted value to the vulnerable sink.
```

### Request Evidence
```
PUT /api/address-book/21 JSON body used `nickname` and `payee_name` equal to `</option><img src=x onerror="document.title='AESPA_XSS_7419'">`.
```

### Response Evidence
```
HTTP 200 from GET /api/address-book/21: `{"success":true,"data":{"id":21,"nickname":"<\/option><img src=x onerror=\"document.title='AESPA_XSS_7419'\">","payee_name":"<\/option><img src=x onerror=\"document.title='AESPA_XSS_7419'\">"...}}`.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 10. Unauthorized role access to admin endpoint

- Severity: high
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/admin/accounts?page=1&per_page=20
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
A credential that was not observed with access to this admin-looking endpoint received a successful direct response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `http_token_7` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://192.168.3.101/api/admin/accounts?page=1&per_page=20 HTTP/1.1
Actor: http_token_7
Cookies: none
Authorization: present

RESPONSE:
HTTP/1.1 200
date: Tue, 14 Jul 2026 04:32:04 GMT
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
content-length: 5962
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"accounts":[{"id":38,"bsb":"062-015","account_number":"25000003","account_type":"loan","account_name":"Personal Loan","balance":"-5200.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":15,"owner_first_name":"Noah","owner_last_name":"Campbell","owner_email":"noah.campbell@example.com"},{"id":37,"bsb":"062-015","account_number":"25000002","account_type":"transaction","account_name":"Savings Account","balance":"27500.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":15,"owner_first_name":"Noah","owner_last_name":"Campbell","owner_email":"noah.campbell@example.com"},{"id":36,"bsb":"062-015","account_number":"25000001","account_type":"transaction","account_name":"Everyday Account","balance":"3100.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":15,"owner_first_name":"Noah","owner_last_name":"Campbell","owner_email":"noah.campbell@example.com"},{"id":35,"bsb":"062-014","account_number":"24000002","account_type":"transaction","account_name":"Holiday Fund","balance":"11200.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":14,"owner_first_name":"Lucas","owner_last_name":"Ferreira","owner_email":"lucas.ferreira@example.com"},{"id":34,"bsb":"062-014","account_number":"24000001","account_type":"transaction","account_name":"Everyday Account","balance":"6750.20","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":14,"owner_first_name":"Lucas","owner_last_name":"Ferreira","owner_email":"lucas.ferreira@example.com"},{"id":33,"bsb":"062-013","account_number":"23000003","account_type":"loan","account_name":"Car Loan","balance":"-9800.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":13,"owner_first_name":"Daniel","owner_last_name":"Park","owner_email":"daniel.park@example.com"},{"id":32,"bsb":"062-013","account_number":"23000002","account_type":"transaction","account_name":"Savings Account","balance":"8900.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":13,"owner_first_name
```

### Request Evidence
```
GET http://192.168.3.101/api/admin/accounts?page=1&per_page=20 HTTP/1.1
Actor: http_token_7
Cookies: none
Authorization: present
```

### Response Evidence
```
HTTP/1.1 200
date: Tue, 14 Jul 2026 04:32:04 GMT
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
content-length: 5962
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"accounts":[{"id":38,"bsb":"062-015","account_number":"25000003","account_type":"loan","account_name":"Personal Loan","balance":"-5200.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":15,"owner_first_name":"Noah","owner_last_name":"Campbell","owner_email":"noah.campbell@example.com"},{"id":37,"bsb":"062-015","account_number":"25000002","account_type":"transaction","account_name":"Savings Account","balance":"27500.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":15,"owner_first_name":"Noah","owner_last_name":"Campbell","owner_email":"noah.campbell@example.com"},{"id":36,"bsb":"062-015","account_number":"25000001","account_type":"transaction","account_name":"Everyday Account","balance":"3100.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":15,"owner_first_name":"Noah","owner_last_name":"Campbell","owner_email":"noah.campbell@example.com"},{"id":35,"bsb":"062-014","account_number":"24000002","account_type":"transaction","account_name":"Holiday Fund","balance":"11200.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":14,"owner_first_name":"Lucas","owner_last_name":"Ferreira","owner_email":"lucas.ferreira@example.com"},{"id":34,"bsb":"062-014","account_number":"24000001","account_type":"transaction","account_name":"Everyday Account","balance":"6750.20","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":14,"owner_first_name":"Lucas","owner_last_name":"Ferreira","owner_email":"lucas.ferreira@example.com"},{"id":33,"bsb":"062-013","account_number":"23000003","account_type":"loan","account_name":"Car Loan","balance":"-9800.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":13,"owner_first_name":"Daniel","owner_last_name":"Park","owner_email":"daniel.park@example.com"},{"id":32,"bsb":"062-013","account_number":"23000002","account_type":"transaction","account_name":"Savings Account","balance":"8900.00","is_active":1,"created_at":"2026-07-14 04:30:31","user_id":13,"owner_first_name
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 11. Unauthorized role access to admin endpoint

- Severity: high
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/admin/customers/10
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
A credential that was not observed with access to this admin-looking endpoint received a successful direct response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `http_token_7` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://192.168.3.101/api/admin/customers/10 HTTP/1.1
Actor: http_token_7
Cookies: none
Authorization: present

RESPONSE:
HTTP/1.1 200
date: Tue, 14 Jul 2026 04:32:07 GMT
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
content-length: 716
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"customer":{"id":10,"email":"natasha.kowalski@example.com","first_name":"Natasha","last_name":"Kowalski","phone":"0411 123 456","address_line1":"30 St Kilda Rd","address_line2":null,"suburb":"St Kilda","state":"VIC","postcode":"3182","totp_enabled":false,"created_at":"2026-07-14 04:30:30"},"accounts":[{"id":24,"bsb":"062-010","account_number":"11000001","account_type":"transaction","account_name":"Everyday Account","balance":"3990.80","is_active":1,"created_at":"2026-07-14 04:30:31"},{"id":25,"bsb":"062-010","account_number":"11000002","account_type":"transaction","account_name":"Savings Account","balance":"22100.00","is_active":1,"created_at":"2026-07-14 04:30:31"}]},"message":"OK"}
```

### Request Evidence
```
GET http://192.168.3.101/api/admin/customers/10 HTTP/1.1
Actor: http_token_7
Cookies: none
Authorization: present
```

### Response Evidence
```
HTTP/1.1 200
date: Tue, 14 Jul 2026 04:32:07 GMT
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
content-length: 716
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"customer":{"id":10,"email":"natasha.kowalski@example.com","first_name":"Natasha","last_name":"Kowalski","phone":"0411 123 456","address_line1":"30 St Kilda Rd","address_line2":null,"suburb":"St Kilda","state":"VIC","postcode":"3182","totp_enabled":false,"created_at":"2026-07-14 04:30:30"},"accounts":[{"id":24,"bsb":"062-010","account_number":"11000001","account_type":"transaction","account_name":"Everyday Account","balance":"3990.80","is_active":1,"created_at":"2026-07-14 04:30:31"},{"id":25,"bsb":"062-010","account_number":"11000002","account_type":"transaction","account_name":"Savings Account","balance":"22100.00","is_active":1,"created_at":"2026-07-14 04:30:31"}]},"message":"OK"}
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 12. Unauthorized role access to admin endpoint

- Severity: high
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/admin/customers?page=1&per_page=15
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
A credential that was not observed with access to this admin-looking endpoint received a successful direct response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `http_token_7` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://192.168.3.101/api/admin/customers?page=1&per_page=15 HTTP/1.1
Actor: http_token_7
Cookies: none
Authorization: present

RESPONSE:
HTTP/1.1 200
date: Tue, 14 Jul 2026 04:32:33 GMT
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
content-length: 2891
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"customers":[{"id":15,"email":"noah.campbell@example.com","first_name":"Noah","last_name":"Campbell","phone":"0455 555 505","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":3},{"id":14,"email":"lucas.ferreira@example.com","first_name":"Lucas","last_name":"Ferreira","phone":"0444 555 404","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":2},{"id":13,"email":"daniel.park@example.com","first_name":"Daniel","last_name":"Park","phone":"0433 555 303","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":3},{"id":12,"email":"marcus.webb@example.com","first_name":"Marcus","last_name":"Webb","phone":"0422 555 202","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":2},{"id":11,"email":"liam.oconnor@example.com","first_name":"Liam","last_name":"O'Connor","phone":"0411 555 101","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":3},{"id":10,"email":"natasha.kowalski@example.com","first_name":"Natasha","last_name":"Kowalski","phone":"0411 123 456","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":2},{"id":9,"email":"emma.obrien@example.com","first_name":"Emma","last_name":"O'Brien","phone":"0499 012 345","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":3},{"id":8,"email":"grace.kim@example.com","first_name":"Grace","last_name":"Kim","phone":"0488 901 234","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":2},{"id":7,"email":"jing.wu@example.com","first_name":"Jing","last_name":"Wu","phone":"0477 890 123","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":3},{"id":6,"email":"sophie.anderson@example.com","first_name":"Sophie","last_name":"Anderson","phone":"0466 789 012","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":2},{"id":5,"email":"isabella.thompson@example.com","first_name":"Isabella","last_name":"Thompson","phone":"0455 678 901"
```

### Request Evidence
```
GET http://192.168.3.101/api/admin/customers?page=1&per_page=15 HTTP/1.1
Actor: http_token_7
Cookies: none
Authorization: present
```

### Response Evidence
```
HTTP/1.1 200
date: Tue, 14 Jul 2026 04:32:33 GMT
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
content-length: 2891
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"customers":[{"id":15,"email":"noah.campbell@example.com","first_name":"Noah","last_name":"Campbell","phone":"0455 555 505","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":3},{"id":14,"email":"lucas.ferreira@example.com","first_name":"Lucas","last_name":"Ferreira","phone":"0444 555 404","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":2},{"id":13,"email":"daniel.park@example.com","first_name":"Daniel","last_name":"Park","phone":"0433 555 303","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":3},{"id":12,"email":"marcus.webb@example.com","first_name":"Marcus","last_name":"Webb","phone":"0422 555 202","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":2},{"id":11,"email":"liam.oconnor@example.com","first_name":"Liam","last_name":"O'Connor","phone":"0411 555 101","totp_enabled":false,"created_at":"2026-07-14 04:30:31","accounts_count":3},{"id":10,"email":"natasha.kowalski@example.com","first_name":"Natasha","last_name":"Kowalski","phone":"0411 123 456","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":2},{"id":9,"email":"emma.obrien@example.com","first_name":"Emma","last_name":"O'Brien","phone":"0499 012 345","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":3},{"id":8,"email":"grace.kim@example.com","first_name":"Grace","last_name":"Kim","phone":"0488 901 234","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":2},{"id":7,"email":"jing.wu@example.com","first_name":"Jing","last_name":"Wu","phone":"0477 890 123","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":3},{"id":6,"email":"sophie.anderson@example.com","first_name":"Sophie","last_name":"Anderson","phone":"0466 789 012","totp_enabled":false,"created_at":"2026-07-14 04:30:30","accounts_count":2},{"id":5,"email":"isabella.thompson@example.com","first_name":"Isabella","last_name":"Thompson","phone":"0455 678 901"
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 13. Unauthorized role access to admin endpoint

- Severity: high
- OWASP: A01
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/admin/fx-rates
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
A credential that was not observed with access to this admin-looking endpoint received a successful direct response.

### Impact
Attackers may be able to access protected application functionality or sensitive operational data without the intended authentication or role checks.

### Likelihood
Confirmed by deterministic auth matrix request.

### Recommendation
Enforce server-side authentication and authorization on the endpoint. Do not rely on client-side route hiding or UI controls.

### Evidence
```
Actor `http_token_7` received HTTP 200 for a protected/sensitive endpoint.

REQUEST:
GET http://192.168.3.101/api/admin/fx-rates HTTP/1.1
Actor: http_token_7
Cookies: none
Authorization: present

RESPONSE:
HTTP/1.1 200
date: Tue, 14 Jul 2026 04:32:35 GMT
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
content-length: 1297
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":[{"id":1,"currency_code":"AUD","currency_name":"Australian Dollar","rate_to_usd":"1.57000000","updated_at":"2026-07-14 04:30:30"},{"id":8,"currency_code":"CAD","currency_name":"Canadian Dollar","rate_to_usd":"1.36000000","updated_at":"2026-07-14 04:30:30"},{"id":9,"currency_code":"CHF","currency_name":"Swiss Franc","rate_to_usd":"0.88500000","updated_at":"2026-07-14 04:30:30"},{"id":10,"currency_code":"CNY","currency_name":"Chinese Yuan","rate_to_usd":"7.24000000","updated_at":"2026-07-14 04:30:30"},{"id":2,"currency_code":"EUR","currency_name":"Euro","rate_to_usd":"0.92500000","updated_at":"2026-07-14 04:30:30"},{"id":3,"currency_code":"GBP","currency_name":"British Pound","rate_to_usd":"0.79200000","updated_at":"2026-07-14 04:30:30"},{"id":7,"currency_code":"HKD","currency_name":"Hong Kong Dollar","rate_to_usd":"7.81000000","updated_at":"2026-07-14 04:30:30"},{"id":4,"currency_code":"JPY","currency_name":"Japanese Yen","rate_to_usd":"149.50000000","updated_at":"2026-07-14 04:30:30"},{"id":5,"currency_code":"NZD","currency_name":"New Zealand Dollar","rate_to_usd":"1.71000000","updated_at":"2026-07-14 04:30:30"},{"id":6,"currency_code":"SGD","currency_name":"Singapore Dollar","rate_to_usd":"1.34500000","updated_at":"2026-07-14 04:30:30"}],"message":"OK"}
```

### Request Evidence
```
GET http://192.168.3.101/api/admin/fx-rates HTTP/1.1
Actor: http_token_7
Cookies: none
Authorization: present
```

### Response Evidence
```
HTTP/1.1 200
date: Tue, 14 Jul 2026 04:32:35 GMT
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
content-length: 1297
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":[{"id":1,"currency_code":"AUD","currency_name":"Australian Dollar","rate_to_usd":"1.57000000","updated_at":"2026-07-14 04:30:30"},{"id":8,"currency_code":"CAD","currency_name":"Canadian Dollar","rate_to_usd":"1.36000000","updated_at":"2026-07-14 04:30:30"},{"id":9,"currency_code":"CHF","currency_name":"Swiss Franc","rate_to_usd":"0.88500000","updated_at":"2026-07-14 04:30:30"},{"id":10,"currency_code":"CNY","currency_name":"Chinese Yuan","rate_to_usd":"7.24000000","updated_at":"2026-07-14 04:30:30"},{"id":2,"currency_code":"EUR","currency_name":"Euro","rate_to_usd":"0.92500000","updated_at":"2026-07-14 04:30:30"},{"id":3,"currency_code":"GBP","currency_name":"British Pound","rate_to_usd":"0.79200000","updated_at":"2026-07-14 04:30:30"},{"id":7,"currency_code":"HKD","currency_name":"Hong Kong Dollar","rate_to_usd":"7.81000000","updated_at":"2026-07-14 04:30:30"},{"id":4,"currency_code":"JPY","currency_name":"Japanese Yen","rate_to_usd":"149.50000000","updated_at":"2026-07-14 04:30:30"},{"id":5,"currency_code":"NZD","currency_name":"New Zealand Dollar","rate_to_usd":"1.71000000","updated_at":"2026-07-14 04:30:30"},{"id":6,"currency_code":"SGD","currency_name":"Singapore Dollar","rate_to_usd":"1.34500000","updated_at":"2026-07-14 04:30:30"}],"message":"OK"}
```

### Validation Note
Confirmed by deterministic auth matrix module.

## 14. Broken Object-Level Authorization Allows Unauthorized External Account Debits

- Severity: high
- OWASP: API1
- Source: specialist agent
- Validation: unconfirmed
- Affected URL: http://192.168.3.101/api/transfers/external
- CVSS: 8.8 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H)

### Description
The external transfer endpoint at /api/transfers/external does not enforce that the client-supplied from_account_id belongs to the authenticated user. Under Amelia's authenticated session, the account listing returned only account IDs 1, 2, and 3; however, a transfer request specifying from_account_id 4 was accepted and completed.

### Impact
An authenticated customer can initiate external transfers from accounts outside their authorized account list. This could enable unauthorized debits and transfers of funds from other customers' accounts to an attacker-controlled external destination, resulting in direct financial loss.

### Likelihood
High. The issue was directly demonstrated using a valid authenticated session and a modified source account identifier, without requiring additional interaction or bypass techniques.

### Recommendation
At the final transfer-processing endpoint, derive eligible source accounts from the authenticated principal and enforce account ownership and active/transfer-eligible status within the same transaction as the debit. Do not rely on client-provided account IDs or prior authorization checks. Reject non-owned source accounts with a generic authorization error and log attempted cross-account debit requests.

### Evidence
```
Authenticated GET /api/accounts returned only account IDs 1, 2, and 3. Using Amelia's authenticated session, POST /api/transfers/external with from_account_id set to 4 returned HTTP 201 and reported a completed transfer: transaction_id 39, from_account_id 4, amount 0.01, new_from_balance 7210.49, and status completed.
```

### Request Evidence
```
POST /api/transfers/external sent `{"from_account_id":4,"to_bsb":"062-000","to_account_number":"12345678","payee_name":"Ownership Test","amount":0.01,"description":"non-owned-source-no-totp"}` under Amelia's authenticated session.
```

### Response Evidence
```
HTTP 201 with `"from_account_id":4`, `"new_from_balance":"7210.49"`, and `"status":"completed"`.
```

### Validation Note
The crawl did not record a user that could access this page, so there is no access-control baseline to compare against.

## 15. Own-Account Transfers Bypass Loan Credit Limits and TOTP Authorization

- Severity: high
- OWASP: A04
- Source: Dynamic
- Validation: unconfirmed
- Affected URL: http://192.168.3.101/api/transfers/own
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H)

### Description
The own-account transfer endpoint does not enforce available-credit or balance limits when the source is a loan account. It also completed the observed transfer without a TOTP value. A loan account with a balance of -999,999,999,999.99 was debited by an additional 1.00, resulting in a balance of -1,000,000,000,000.99, while the destination transaction account was credited.

### Impact
An authenticated customer with both loan and transaction accounts could transfer funds beyond the loan's approved principal or credit limit. Repeated exploitation could create unbounded account credit and compromise financial ledger integrity.

### Likelihood
High. The endpoint accepted a direct request from an authenticated customer, completed the transfer without TOTP authorization, and did not reject a debit that further exceeded the loan account's already-negative balance.

### Recommendation
Explicitly model and enforce approved loan principal, drawdown limits, and available credit before processing any transfer. Apply consistent balance and credit-limit validation across all source account types. Require server-side step-up authorization, including TOTP where policy requires it, for high-risk transfers. Process debit and credit operations atomically and enforce ledger invariants so that a transfer cannot complete if any authorization or limit check fails.

### Evidence
```
A POST request transferred 1.00 from loan account 40, whose balance was -999999999999.99, to transaction account 39 without supplying a TOTP value. The endpoint returned HTTP 201 with status `completed`, a new source balance of `-1000000000000.99`, and a new destination balance of `1000000000000.99`.
```

### Request Evidence
```
POST /api/transfers/own
{"from_account_id":40,"to_account_id":39,"amount":"1.00","description":"Loan negative-balance transfer probe"}
```

### Response Evidence
```
HTTP 201: `{"transaction_id":37,"from_account_id":40,"to_account_id":39,"amount":"1.00",...,"new_from_balance":"-1000000000000.99","new_to_balance":"1000000000000.99",...,"status":"completed"}`
```

### Validation Note
The crawl did not record a user that could access this page, so there is no access-control baseline to compare against.

## 16. Administrative Endpoint Allows Unrestricted Balance Modification

- Severity: high
- OWASP: A01
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://192.168.3.101/api/admin/accounts/39/balance
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:N/I:H/A:H)

### Description
The administrative endpoint at `/api/admin/accounts/39/balance` permits an authenticated administrator to set an account balance directly to an unrestricted numeric value. The update is applied immediately without a maximum-value restriction, secondary approval, or transaction-based adjustment workflow. Testing was limited to a disposable account created during the assessment.

### Impact
A compromised or malicious administrator could create arbitrary funds or alter customer balances, undermining the integrity and auditability of the banking ledger. Extreme balance changes could also disrupt downstream processes that rely on valid account values.

### Likelihood
High in the observed environment because the endpoint is directly accessible through the API and the assessment had already confirmed predictable administrator credentials. Exploitation requires administrative privileges but is otherwise straightforward and requires only a single request.

### Recommendation
Remove the ability to set account balances directly. Implement balance changes as balanced, auditable ledger adjustment transactions with strict value limits, reason codes, and immutable audit records. Require maker-checker approval and step-up authentication for high-risk adjustments, and generate alerts for unusual values or activity.

### Evidence
```
While authenticated as an administrator, a PUT request set disposable transaction account 39's balance to `9999999999999.99`. The API returned HTTP 200 and echoed the updated balance, with no secondary confirmation or limit rejection.
```

### Request Evidence
```
PUT /api/admin/accounts/39/balance
{"balance":"9999999999999.99"}
```

### Response Evidence
```
HTTP 200: `{"success":true,"data":{"id":39,...,"balance":"9999999999999.99",...},"message":"Balance updated successfully"}`
```

### Validation Note
Validation could not reproduce unauthorized access. Alternate users received an access denial, login response, generic SPA shell, or no protected content signal.

## 17. Broken Object-Level Authorization Exposes Other Customers' Transactions

- Severity: high
- OWASP: A01
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://192.168.3.101/api/transactions/35
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The transaction detail endpoint retrieves transactions by numeric ID without verifying that the requested transaction belongs to an account owned by the authenticated user. A newly registered customer could access an unrelated customer's transaction by changing the transaction ID in the request.

### Impact
Any authenticated customer could enumerate and view other customers' sensitive transaction data, including source and destination account relationships, destination bank details, transaction amounts, descriptions, transfer types, and timestamps.

### Likelihood
High. Exploitation requires only a valid customer account and modification of a numeric transaction ID. The observed IDs were sequential, and the endpoint returned a foreign transaction directly with HTTP 200.

### Recommendation
Enforce object-level authorization on every transaction lookup. Scope database queries to transactions associated with accounts owned by the authenticated user rather than retrieving records directly by primary key. Return a consistent HTTP 404 response when a transaction does not exist or the user is not authorized to access it, and add automated authorization tests covering cross-customer access attempts.

### Evidence
```
Newly registered user ID 16 owned account 39 and transaction 36. Using that user's bearer token, GET /api/transactions/35 returned HTTP 200 and disclosed transaction 35, whose from_account_id was 37 and to_account_id was 36. The response also exposed destination BSB 062-015, destination account number 25000001, amount 400.00, and description "Bills top-up," demonstrating access to a foreign transaction.
```

### Request Evidence
```
GET /api/transactions/35 using the bearer token for newly registered user id 16
```

### Response Evidence
```
HTTP 200 {"id":35,"from_account_id":37,"to_bsb":"062-015","to_account_number":"25000001","to_account_id":36,"amount":"400.00","description":"Bills top-up",...}
```

### Validation Note
Validation could not reproduce unauthorized access. Alternate users received an access denial, login response, generic SPA shell, or no protected content signal.

## 18. Authenticated SQL Injection in Administrative Customer Search

- Severity: medium
- OWASP: A03
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/admin/customers?page=1&per_page=15&search=%27
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:N)

### Description
The `search` parameter of the administrative customer listing API is incorporated into a SQL `LIKE` clause without safe parameterization. Supplying a single quote caused a MySQL syntax error and exposed the generated query fragment, confirming that attacker-controlled input reached the SQL statement. The error response also disclosed an internal source path, line number, and PHP stack trace.

### Impact
An authenticated administrator may be able to manipulate the customer search query and access or modify database information within the application's database privileges. The verbose error response additionally reveals internal paths and implementation details that could assist further exploitation.

### Likelihood
The issue is practically exploitable by an authenticated administrator because the vulnerable parameter is exposed through a routine administrative API, requires only a crafted search value, and produced a database syntax error demonstrating unsafe SQL construction. The captured evidence did not demonstrate successful data extraction or modification.

### Recommendation
Replace dynamic SQL construction with prepared statements and bound parameters for all search values. When using `LIKE`, bind the search pattern as data and escape `%` and `_` when they should be treated literally. Disable detailed database and stack-trace responses in production, return a generic error to clients, and record full exception details only in protected server-side logs.

### Evidence
```
An authenticated GET request with `search=%27` returned HTTP 500 and the MySQL error `SQLSTATE[42000]: Syntax error or access violation: 1064 ... near '%' OR last_name LIKE '%'%' OR email LIKE '%'%'' at line 1`. The response also disclosed `/var/www/bankofed/src/Controllers/AdminUserController.php`, line 28, `PDO->query()`, and a PHP stack trace.
```

### Request Evidence
```
GET /api/admin/customers?page=1&per_page=15&search=%27 with an authenticated admin bearer token.
```

### Response Evidence
```
HTTP 500: `SQLSTATE[42000]: Syntax error or access violation: 1064 ... near '%' OR last_name LIKE '%'%' OR email LIKE '%'%'' at line 1`; details included `file":"/var/www/bankofed/src/Controllers/AdminUserController.php","line":28,"trace":"#0 ... PDO->query()`.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 19. Profile API Exposes Authentication Internals

- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The authenticated profile endpoint returns internal authentication fields that should not be included in client-facing responses. The observed response disclosed the user's bcrypt password hash and included the TOTP secret field, although its value was null for the tested account.

### Impact
Disclosure of password hashes may enable offline password cracking and subsequent credential-reuse attacks. Returning the TOTP secret field also creates a risk that MFA seeds could be disclosed for accounts where the field is populated, potentially allowing an attacker with profile access to reproduce one-time codes.

### Likelihood
Any authenticated user, or an attacker who obtains a valid bearer session, can access the affected response. Password-hash disclosure was directly confirmed; disclosure of a populated TOTP secret was not demonstrated because the tested account had TOTP disabled and the field was null.

### Recommendation
Define explicit response DTOs or serialization allowlists for profile data. Permanently exclude password hashes, TOTP seeds, password-reset tokens, session secrets, and all other authentication internals from API responses. Review other API endpoints for similar unsafe serialization and add automated tests that verify sensitive fields are never returned.

### Evidence
```
An authenticated GET request to /api/profile returned HTTP 200 for user ID 3 and included the bcrypt password_hash value "$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC\/.og\/at2.uheWG\/igi". The response also serialized "totp_secret":null and indicated "totp_enabled":false.
```

### Request Evidence
```
GET /api/profile with a customer bearer session
```

### Response Evidence
```
{"id":3,"email":"zoe.williams@example.com",...,"totp_enabled":false,"password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC\/.og\/at2.uheWG\/igi","totp_secret":null}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 20. Registration Permits One-Character Passwords

- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/auth/register
- CVSS: 5.3 (CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N)

### Description
The registration endpoint does not enforce an effective minimum password length. An account was successfully created through POST /api/auth/register using the one-character password "a".

### Impact
Users can create accounts with trivially guessable passwords, increasing the risk of unauthorized account access through password guessing.

### Likelihood
High. The unauthenticated registration endpoint accepted a one-character password and returned a successful account creation response.

### Recommendation
Enforce a server-side minimum password length of at least 12 characters and reject common or known-compromised passwords. Apply the same password policy consistently to registration, password reset, and password change workflows.

### Evidence
```
The endpoint returned HTTP 201 with the message "Registration successful" after receiving matching password and password_confirmation values of "a". The response included the newly created user with ID 16 and an authentication token.
```

### Request Evidence
```
POST /api/auth/register with password="a" and password_confirmation="a"
```

### Response Evidence
```
Status 201: {"success":true,"data":{"user":{"id":16,"email":"aespa_9c959f18@example.invalid",...},"token":"[REDACTED_JWT]"},"message":"Registration successful"}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 21. Sensitive data exposed in API response

- Severity: medium
- OWASP: A02
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/auth/register
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

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
REGISTER_ACCOUNT http://192.168.3.101/api/auth/register

RESPONSE:
Status: 201
{"success":true,"data":{"user":{"id":16,"email":"aespa_9c959f18@example.invalid","first_name":"A","last_name":"Tester","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"ff573fd9f7f93747e5d0f4b93a6e9dbd","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Registration successful"}
```

### Request Evidence
```
REGISTER_ACCOUNT http://192.168.3.101/api/auth/register
```

### Response Evidence
```
Status: 201
{"success":true,"data":{"user":{"id":16,"email":"aespa_9c959f18@example.invalid","first_name":"A","last_name":"Tester","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"ff573fd9f7f93747e5d0f4b93a6e9dbd","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Registration successful"}
```

### Validation Note
Confirmed by deterministic module.

## 22. Sensitive data exposed in API response

- Severity: medium
- OWASP: A02
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/debug
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

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
GET http://192.168.3.101/api/debug
use_session: (default)  Cookies: none
{}

RESPONSE:
Status: 404
date: Tue, 14 Jul 2026 04:22:50 GMT
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
content-length: 78
keep-alive: timeout=5, max=95
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"NOT_FOUND","message":"Endpoint not found."}}
```

### Request Evidence
```
GET http://192.168.3.101/api/debug
use_session: (default)  Cookies: none
{}
```

### Response Evidence
```
Status: 404
date: Tue, 14 Jul 2026 04:22:50 GMT
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
content-length: 78
keep-alive: timeout=5, max=95
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"NOT_FOUND","message":"Endpoint not found."}}
```

### Validation Note
Confirmed by deterministic module.

## 23. Sensitive data exposed in API response

- Severity: medium
- OWASP: A02
- Source: Deterministic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/auth/login
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

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
POST http://192.168.3.101/api/auth/login
use_session: (default)  Cookies: none
{"Content-Type": "application/json"}
{"email": "zoe.williams@example.com", "password": "password"}

RESPONSE:
Status: 200
date: Tue, 14 Jul 2026 04:48:40 GMT
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
content-length: 639
keep-alive: timeout=5, max=98
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"user":{"id":3,"email":"zoe.williams@example.com","first_name":"Zoe","last_name":"Williams","address_line1":"3 Queen St","address_line2":null,"suburb":"Brisbane","state":"QLD","postcode":"4000","phone":"0433 456 789","avatar_url":null,"totp_enabled":false,"password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC\/.og\/at2.uheWG\/igi","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Login successful"}
```

### Request Evidence
```
POST http://192.168.3.101/api/auth/login
use_session: (default)  Cookies: none
{"Content-Type": "application/json"}
{"email": "zoe.williams@example.com", "password": "password"}
```

### Response Evidence
```
Status: 200
date: Tue, 14 Jul 2026 04:48:40 GMT
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
content-length: 639
keep-alive: timeout=5, max=98
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"user":{"id":3,"email":"zoe.williams@example.com","first_name":"Zoe","last_name":"Williams","address_line1":"3 Queen St","address_line2":null,"suburb":"Brisbane","state":"QLD","postcode":"4000","phone":"0433 456 789","avatar_url":null,"totp_enabled":false,"password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC\/.og\/at2.uheWG\/igi","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Login successful"}
```

### Validation Note
Confirmed by deterministic module.

## 24. Authenticated Error-Based SQL Injection in Transaction Sort Parameter

- Severity: medium
- OWASP: A03
- Source: A.L.I.C.E
- Validation: validating
- Affected URL: http://192.168.3.101/api/transactions?sort=created_at%2CEXTRACTVALUE(1%2CCONCAT(0x7e%2CDATABASE()))&per_page=10
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The authenticated GET /api/transactions endpoint incorporates the user-controlled sort parameter into the SQL ORDER BY clause without restricting it to permitted values. A grammar-compatible EXTRACTVALUE payload was evaluated by MySQL, and the resulting error disclosed the value of DATABASE(). The endpoint also returns verbose database exceptions, application file paths, line numbers, and stack-trace details.

### Impact
A low-privileged authenticated customer can evaluate attacker-controlled SQL expressions and retrieve database values through error messages. This could allow access to database information beyond the customer's authorized transaction scope, depending on the privileges of the application's database account. Crafted expressions could also consume database resources and affect service availability.

### Likelihood
High. Exploitation requires only a normal authenticated customer session and a crafted sort parameter. The demonstrated payload executed without user interaction or a race condition, and the resulting database value was returned directly in the HTTP response.

### Recommendation
Map the sort parameter to a strict server-side allowlist of permitted column names and sort directions. Select fixed ORDER BY fragments in application logic rather than concatenating user input, and return HTTP 400 for unsupported values. Continue to parameterize all SQL value inputs. Disable detailed exception responses in production, return generic errors to clients, and retain full diagnostics only in server-side logs. Review and minimize the application database account's privileges.

### Evidence
```
A baseline request using sort=created_at returned HTTP 200. Using sort=%27 returned HTTP 500 with SQLSTATE[42000], the path /var/www/bankofed/src/Models/Transaction.php, line 55, and a stack trace. The payload sort=created_at,EXTRACTVALUE(1,CONCAT(0x7e,DATABASE())) returned HTTP 500 with "XPATH syntax error: '~bankofed'", demonstrating execution of the injected SQL expression and disclosure of the current database name.
```

### Request Evidence
```
GET /api/transactions?sort=created_at%2CEXTRACTVALUE(1%2CCONCAT(0x7e%2CDATABASE()))&per_page=10 (authenticated customer token)
```

### Response Evidence
```
HTTP/1.1 500 Internal Server Error
{"success":false,"error":{"code":"INTERNAL_ERROR","message":"SQLSTATE[HY000]: General error: 1105 XPATH syntax error: '~bankofed'","details":{"file":"/var/www/bankofed/src/Models/Transaction.php","line":55,"trace":"..."}}}
```

### Validation Note
Validation running.

## 25. API reflects arbitrary CORS origins for sensitive authenticated responses

- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 2.6 (CVSS:3.1/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:N/A:N)

### Description
The API reflects attacker-controlled Origin values on authenticated responses and permits broad cross-origin methods/headers. The profile response contains PII and authentication internals.

### Impact
The policy unnecessarily permits arbitrary websites to issue and read API requests when they can supply or obtain a bearer token, increasing the impact of token leakage and cross-origin attack chains.

### Likelihood
Moderate; browser exploitation requires access to a valid bearer token because the application stores JWTs in localStorage.

### Recommendation
Allow only explicitly trusted application origins, restrict methods and headers per endpoint, and do not enable credentials for wildcard/dynamic origins.

### Evidence
```
GET /api/profile with Origin: https://evil.example returned Access-Control-Allow-Origin: https://evil.example and the complete profile. OPTIONS for the same origin returned HTTP 200. Captured API responses also advertise Access-Control-Allow-Credentials: true, Access-Control-Allow-Headers: *, and broad methods.

REQUEST:
GET /api/profile with Authorization bearer token and Origin: https://evil.example; OPTIONS /api/profile with requested Authorization header

RESPONSE:
HTTP 200, access-control-allow-origin: https://evil.example, body included email, password_hash, and totp_secret. Preflight returned HTTP 200.
```

### Request Evidence
```
GET /api/profile with Authorization bearer token and Origin: https://evil.example; OPTIONS /api/profile with requested Authorization header
```

### Response Evidence
```
HTTP 200, access-control-allow-origin: https://evil.example, body included email, password_hash, and totp_secret. Preflight returned HTTP 200.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 26. Insufficient Login Rate Limiting and Account Lockout

- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/auth/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L)

### Description
The login endpoint did not apply observable rate limiting, progressive delays, CAPTCHA challenges, or account lockout after six consecutive failed authentication attempts against a known account. Each attempt received the same immediate HTTP 401 wrong-password response.

### Impact
An unauthenticated attacker could conduct sustained password-guessing or credential-stuffing attacks against customer accounts, increasing the risk of account compromise when weak or reused credentials are present.

### Likelihood
High. The authentication endpoint is publicly accessible, and no defensive response was observed during six consecutive failed attempts. The application also permits valid-user enumeration, which can help attackers select accounts to target.

### Recommendation
Implement layered authentication abuse protections, including per-account and per-source throttling, progressive or exponential backoff, risk-based CAPTCHA or step-up challenges, monitoring and alerting, and temporary account lockouts. Design lockout controls to minimize account denial-of-service risk, and return consistent authentication errors that do not facilitate user enumeration.

### Evidence
```
Exactly six consecutive login requests were submitted for zoe.williams@example.com using distinct incorrect passwords. All returned HTTP 401 with the WRONG_PASSWORD response in approximately 103-127 ms. Attempt 1 completed in 115 ms and attempt 6 in 103 ms, with no HTTP 429 response, increasing delay, or account lockout observed.
```

### Request Evidence
```
Exactly 6 consecutive POST /api/auth/login requests for zoe.williams@example.com with distinct incorrect passwords
```

### Response Evidence
```
Attempt 1: {"code":"WRONG_PASSWORD","message":"Incorrect password."}, 115ms. Attempt 6: identical response, 103ms. No 429 or lockout.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 27. Insufficient Rate Limiting on Administrative Login

- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/admin/auth/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L)

### Description
The administrative login endpoint did not impose observable rate limiting or account lockout after six consecutive failed authentication attempts against the `admin` username. Each attempt returned the same HTTP 401 response without an HTTP 429 response, progressive delay, CAPTCHA, lockout, or other challenge.

### Impact
An unauthenticated attacker could repeatedly attempt password guessing or credential-stuffing attacks against the privileged administrator account. If valid credentials are discovered, the attacker could gain access to sensitive customer and financial administration functions.

### Likelihood
The endpoint is reachable without authentication and the tested `admin` username is predictable. Although testing was intentionally limited to six attempts and does not establish behavior at higher thresholds, no defensive control was observed within the tested sequence.

### Recommendation
Implement layered protections for administrative authentication, including per-account and per-source rate limits, progressive delays, and temporary account lockouts. Require MFA for administrative accounts, monitor and alert on repeated authentication failures, and use consistent failure responses that do not disclose account state.

### Evidence
```
Exactly six consecutive login attempts were submitted for username `admin`, each using a distinct invalid password (`wrong-aespa-1` through `wrong-aespa-6`). Attempts 1 through 6 all returned HTTP 401 with `success=false`; no HTTP 429 response, lockout, CAPTCHA, or other change in response behavior was observed.
```

### Request Evidence
```
POST /api/admin/auth/login with JSON username `admin` and six distinct invalid passwords (`wrong-aespa-1` through `wrong-aespa-6`).
```

### Response Evidence
```
Attempt statuses: 401, 401, 401, 401, 401, 401; all reported success=false and no throttling response.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 28. Login Endpoint Permits Email Address Enumeration

- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/auth/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The unauthenticated login endpoint discloses whether an email address is registered by returning different error codes and messages for known and unknown addresses. The tested responses also exhibited a timing difference.

### Impact
An attacker could identify registered customer email addresses and use this information to target password-guessing, credential-stuffing, or phishing attacks.

### Likelihood
High; enumeration requires only unauthenticated login requests and can be performed by comparing the returned error codes and messages.

### Recommendation
Return the same generic message, application error code, and HTTP status for all failed authentication attempts, regardless of whether the account exists. Ensure that authentication failure paths have comparable processing times and apply rate limiting and monitoring to repeated login attempts.

### Evidence
```
A login attempt for the known address zoe.williams@example.com returned HTTP 401 with {"code":"WRONG_PASSWORD","message":"Incorrect password."} in 115 ms. Using the same incorrect password for nonexistent-aespa@example.com returned HTTP 401 with {"code":"USER_NOT_FOUND","message":"No account found with this email address."} in 16 ms.
```

### Request Evidence
```
POST /api/auth/login with the same wrong password, first for a known email and then an unknown email
```

### Response Evidence
```
Known: HTTP 401 {"code":"WRONG_PASSWORD","message":"Incorrect password."}; unknown: HTTP 401 {"code":"USER_NOT_FOUND","message":"No account found with this email address."}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 29. Missing Browser Security Headers and Apache Version Disclosure

- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The HTML response at the application root omits the Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy headers. The response also discloses the exact web server and operating system distribution through the Server header: Apache/2.4.58 (Ubuntu).

### Impact
The missing headers reduce browser-side defense in depth against framing, content-type confusion, referrer leakage, and the impact of potential content injection. The detailed Server header provides information that may assist attacker reconnaissance. Exploitation of the missing headers generally requires user interaction or an additional application weakness.

### Likelihood
The omissions and version disclosure are directly observable by any unauthenticated remote user. However, meaningful security impact depends on browser interaction or another exploitable weakness.

### Recommendation
Define a restrictive Content-Security-Policy appropriate for the application, including a frame-ancestors directive such as frame-ancestors 'none' where framing is not required. Alternatively, set X-Frame-Options: DENY. Add X-Content-Type-Options: nosniff and Referrer-Policy: strict-origin-when-cross-origin. Configure Apache to suppress detailed version and operating system information in the Server header.

### Evidence
```
A GET request to / returned HTTP 200 with Server: Apache/2.4.58 (Ubuntu). The response did not include Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, or Referrer-Policy headers.
```

### Request Evidence
```
GET /
```

### Response Evidence
```
HTTP 200 headers included server: Apache/2.4.58 (Ubuntu) and omitted the listed security headers.
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.
