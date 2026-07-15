# Issue Export: test prompt adjustments for coverage on models which finished early

- Site: Bank of Ed
- Exported: 14/7/2026, 11:25:46 pm
- Total findings: 19

<!-- aespa-findings-json
%5B%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Default%20admin%20credentials%20accepted%22%2C%22description%22%3A%22POST%20%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20username%20admin%20%2F%20password%20admin123%20returned%20200%20with%20a%20valid%20admin%20token.%22%2C%22impact%22%3A%22Full%20administrative%20access%20to%20the%20banking%20admin%20panel%20using%20guessable%20default%20credentials%2C%20enabling%20customer%20data%20access%20and%20account%20manipulation.%22%2C%22likelihood%22%3A%22Confirmed%20%E2%80%94%20login%20succeeded%20with%20default%20credentials.%22%2C%22recommendation%22%3A%22Remove%2Frotate%20default%20admin%20credentials%2C%20enforce%20strong%20unique%20passwords%2C%20add%20MFA%20and%20rate%20limiting%20on%20admin%20login.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Fadmin%2Fauth%2Flogin%20%7Busername%3Aadmin%2Cpassword%3Aadmin123%7D%20returned%20200%20%7B%5C%22admin%5C%22%3A%7B%5C%22id%5C%22%3A1%2C%5C%22username%5C%22%3A%5C%22admin%5C%22%7D%2C%5C%22token%5C%22%3A...%7D.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fhealth%5Cnuse_session%3A%20(default)%20%20Cookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2013%3A17%3A02%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20280%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.3.31%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%5C%5C%2F2.4.58%20(Ubuntu)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22bankofed_app%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2F192.168.3.101%2Fapi%2Fhealth%5Cnuse_session%3A%20(default)%20%20Cookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2014%20Jul%202026%2013%3A17%3A02%20GMT%5Cnserver%3A%20Apache%2F2.4.58%20(Ubuntu)%5Cnx-content-type-options%3A%20nosniff%5Cnx-frame-options%3A%20DENY%5Cnx-xss-protection%3A%201%3B%20mode%3Dblock%5Cnreferrer-policy%3A%20strict-origin-when-cross-origin%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20280%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.3.31%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%5C%5C%2F2.4.58%20(Ubuntu)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22bankofed_app%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API7%3A2023%20Server%20Side%20Request%20Forgery%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Full-Read%20Server-Side%20Request%20Forgery%20(SSRF)%20in%20Avatar%20URL%20Fetch%20with%20Private-IP%20Filter%20Bypass%22%2C%22description%22%3A%22The%20avatar%20endpoint%20at%20POST%20%2Fapi%2Fprofile%2Favatar%20accepts%20a%20user-supplied%20URL%20in%20the%20JSON%20body%20and%20causes%20the%20server%20to%20fetch%20that%20URL%2C%20returning%20the%20full%20response%20body%20base64-encoded%20in%20the%20avatar_data%20field.%20The%20endpoint%20is%20reachable%20by%20any%20authenticated%20user%2C%20and%20account%20registration%20is%20open%20and%20self-service%20via%20%2Fapi%2Fauth%2Fregister.%20The%20fetch%20logic%20does%20not%20restrict%20schemes%2C%20hosts%2C%20or%20IP%20ranges%2C%20and%20any%20private%2Freserved-IP%20filtering%20that%20may%20exist%20is%20trivially%20bypassed%20using%20hexadecimal%20IP%20notation.%20Because%20the%20fetched%20response%20body%20is%20reflected%20back%20to%20the%20caller%2C%20this%20is%20a%20full-read%20(not%20blind)%20SSRF.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20coerce%20the%20server%20into%20issuing%20arbitrary%20HTTP%20requests%20to%20internal%20and%20external%20hosts%20and%20read%20the%20full%20response.%20This%20was%20demonstrated%20by%20retrieving%20the%20internal%20'The%20Bank%20of%20Ed'%20application%20served%20on%20127.0.0.1%3A80%2C%20which%20is%20not%20intended%20to%20be%20externally%20reachable.%20Such%20access%20enables%20enumeration%20and%20reading%20of%20loopback%20and%20internal-network%20services%2C%20admin%20panels%2C%20and%20other%20resources%20that%20trust%20the%20application%20server's%20network%20position.%20It%20also%20creates%20exposure%20to%20cloud%20metadata%20credential%20theft%20(e.g.%2C%20169.254.169.254%20%2F%20Azure%20IMDS%20%2F%20metadata.google.internal)%20where%20such%20an%20endpoint%20is%20reachable%20from%20the%20host.%22%2C%22likelihood%22%3A%22High.%20Registration%20is%20open%20with%20no%20approval%20step%2C%20no%20CSRF%20token%20or%20second%20factor%20is%20required%2C%20and%20exploitation%20is%20a%20single%20authenticated%20JSON%20POST.%20Observed%20behavior%20confirms%20no%20effective%20filtering%20blocks%20loopback%20or%20hex-encoded%20IPs.%22%2C%22recommendation%22%3A%22Do%20not%20pass%20user-supplied%20URLs%20directly%20to%20HTTP%20clients%20or%20file_get_contents.%20Enforce%20a%20scheme%20allowlist%20(only%20https)%20and%2C%20where%20possible%2C%20a%20host%20allowlist.%20Resolve%20DNS%20first%2C%20then%20validate%20the%20resolved%20IP%20against%20blocklists%20for%20private%2Freserved%2Flink-local%20ranges%20(127.0.0.0%2F8%2C%2010.0.0.0%2F8%2C%20172.16.0.0%2F12%2C%20192.168.0.0%2F16%2C%20169.254.0.0%2F16%2C%20%3A%3A1%2C%20fc00%3A%3A%2F7)%2C%20re-validating%20on%20each%20connection%20to%20defeat%20DNS%20rebinding.%20Canonicalize%20the%20host%20to%20defeat%20hex%2Foctal%2Fdecimal%2Fshort-form%20and%20userinfo%20(e.g.%2C%20evil.com%40127.0.0.1)%20bypasses.%20Disable%20or%20restrict%20redirect%20following%20to%20prevent%20redirect-based%20pivots%20to%20internal%20targets.%20Consider%20routing%20outbound%20fetches%20through%20an%20egress%20proxy%20that%20blocks%20metadata%20endpoints.%20Finally%2C%20validate%20that%20the%20fetched%20content-type%20is%20an%20image%20and%20store%20only%20the%20resulting%20image%20rather%20than%20arbitrary%20content.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AC%2FC%3AH%2FI%3AN%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%2Favatar%22%2C%22evidence%22%3A%22Authenticated%20(JWT%20from%20%2Fapi%2Fauth%2Fregister)%20POST%20%2Fapi%2Fprofile%2Favatar%20with%20%7B%5C%22url%5C%22%3A%5C%22https%3A%2F%2Fexample.com%5C%22%7D%20returned%20HTTP%20200%20with%20avatar_data%20base64%20decoding%20to%20the%20'Example%20Domain'%20page%20and%20source_url%3A%5C%22https%3A%2F%2Fexample.com%5C%22%2C%20proving%20arbitrary%20external%20fetch%20with%20reflected%20content.%20Differential%20internal%20probing%3A%20%7B%5C%22url%5C%22%3A%5C%22http%3A%2F%2F127.0.0.1%3A1%2F%5C%22%7D%20(dead%20port)%20returned%20HTTP%20400%20%7B%5C%22code%5C%22%3A%5C%22FETCH_FAILED%5C%22%7D%2C%20while%20%7B%5C%22url%5C%22%3A%5C%22http%3A%2F%2F127.0.0.1%3A80%2F%5C%22%7D%20(live)%20returned%20HTTP%20200%20with%20a%2039308-char%20body%20decoding%20to%20the%20internal%20'The%20Bank%20of%20Ed'%20application%20HTML.%20Filter%20bypass%3A%20%7B%5C%22url%5C%22%3A%5C%22http%3A%2F%2F0x7f000001%3A80%2F%5C%22%7D%20(hex-encoded%20127.0.0.1)%20returned%20HTTP%20200%20with%20the%20same%20internal%20Bank%20of%20Ed%20HTML%2C%20demonstrating%20no%20effective%20private-IP%20filtering.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fprofile%2Favatar%20HTTP%2F1.1%5CnHost%3A%20192.168.3.101%5CnAuthorization%3A%20Bearer%20%5BREDACTED_BEARER%5D%20(valid%20JWT%20from%20%2Fapi%2Fauth%2Fregister)%5CnContent-Type%3A%20application%2Fjson%5Cn%5Cn%7B%5C%22url%5C%22%3A%5C%22http%3A%2F%2F127.0.0.1%3A80%2F%5C%22%7D%22%2C%22response_evidence%22%3A%22HTTP%20200%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22avatar_data%5C%22%3A%5C%22data%3Atext%2Fhtml%3Bbase64%2CPCFET0NUWVBFIGh0bWw%2B...VGhlIEJhbmsgb2YgRWQ...%5C%22%2C%5C%22size%5C%22%3A...%2C%5C%22source_url%5C%22%3A%5C%22http%3A%2F%2F127.0.0.1%3A80%2F%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%5Cn%5CnCanary%20case%20(https%3A%2F%2Fexample.com)%3A%20base64%20decodes%20to%20%5C%22%3Ch1%3EExample%20Domain%3C%2Fh1%3E%3Cp%3EThis%20domain%20is%20for%20use%20in%20documentation%20examples%20without%20needing%20permission...%5C%22%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22JWT%20Signature%20Not%20Verified%20%E2%80%94%20Forged%20Token%20Enables%20Full%20Account%20Impersonation%22%2C%22description%22%3A%22The%20token%20validation%20routine%20(AuthService%3A%3AdecodeToken)%20at%20the%20%2Fapi%2Fprofile%20endpoint%20decodes%20the%20JWT%20payload%20and%20only%20checks%20the%20exp%20and%20jti%20claims.%20It%20never%20verifies%20the%20HMAC%20signature%20or%20the%20token%20algorithm.%20As%20a%20result%2C%20a%20JWT%20bearing%20an%20arbitrary%2Finvalid%20signature%20but%20containing%20a%20valid%20future%20exp%2C%20any%20jti%2C%20and%20an%20attacker-chosen%20sub%20is%20accepted%20as%20authentic%2C%20authorizing%20the%20request%20as%20whatever%20user%20ID%20is%20placed%20in%20the%20sub%20claim.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20can%20forge%20a%20token%20asserting%20any%20user%20ID%20(e.g.%2C%20sub%3D1)%20and%20be%20fully%20authenticated%20as%20that%20user%2C%20resulting%20in%20complete%20authentication%20bypass%20and%20account%20takeover%20of%20any%20customer%20or%20administrator%20across%20the%20application.%20In%20the%20observed%20case%20the%20response%20returned%20user%201's%20full%20profile%2C%20including%20their%20email%20and%20bcrypt%20password%20hash.%22%2C%22likelihood%22%3A%22high%22%2C%22recommendation%22%3A%22Verify%20the%20JWT%20signature%20and%20algorithm%20using%20a%20vetted%20library%20before%20trusting%20any%20claims%3A%20enforce%20an%20allowlist%20of%20expected%20algorithms%20(e.g.%2C%20HS256)%2C%20reject%20alg%3Dnone%20and%20algorithm-substitution%20attempts%2C%20and%20validate%20the%20HMAC%20signature%20against%20the%20server%20secret.%20Only%20after%20signature%2Falgorithm%20verification%20succeeds%20should%20exp%2C%20jti%2C%20sub%2C%20and%20other%20claims%20be%20evaluated.%20Additionally%2C%20ensure%20sensitive%20fields%20such%20as%20password_hash%20are%20never%20returned%20in%20profile%20responses.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22A%20JWT%20with%20claims%20%7B%5C%22exp%5C%22%3A4102444800%2C%5C%22sub%5C%22%3A1%2C%5C%22jti%5C%22%3A%5C%22forged-user1%5C%22%7D%20signed%20with%20an%20incorrect%20secret%20(%5C%22wrong-secret-signature-bypass-test%5C%22)%20was%20submitted%20as%20a%20Bearer%20token%20to%20GET%20%2Fapi%2Fprofile.%20The%20server%20responded%20HTTP%20200%20and%20returned%20user%201's%20full%20profile%3A%20%7B%5C%22id%5C%22%3A1%2C%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C...%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye...%5C%22%7D%2C%20confirming%20the%20signature%20was%20never%20validated.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fprofile%20Authorization%3A%20Bearer%20%3Ctoken%20with%20invalid%20signature%2C%20sub%3D1%2C%20jti%20set%3E%22%2C%22response_evidence%22%3A%22%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A1%2C%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C...%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unauthenticated%20%2Fapi%2Fhealth%20endpoint%20discloses%20JWT%20signing%20secret%20and%20database%20configuration%22%2C%22description%22%3A%22The%20publicly%20accessible%20%2Fapi%2Fhealth%20endpoint%20at%20http%3A%2F%2F192.168.3.101%2Fapi%2Fhealth%20returns%2C%20without%20any%20authentication%2C%20the%20application's%20JWT%20HMAC%20signing%20secret%20along%20with%20internal%20database%20connection%20details%20(host%2C%20database%20name%2C%20and%20database%20user)%20and%20the%20running%20environment%20(production).%20Because%20the%20JWT%20signing%20secret%20is%20a%20high-entropy%20credential%20used%20to%20sign%20authentication%20tokens%2C%20its%20disclosure%20allows%20an%20attacker%20to%20forge%20validly-signed%20JWTs%20for%20arbitrary%20user%20identities.%22%2C%22impact%22%3A%22An%20attacker%20in%20possession%20of%20the%20leaked%20JWT%20signing%20secret%20can%20mint%20validly-signed%20tokens%20for%20any%20user%2C%20including%20administrators%2C%20resulting%20in%20complete%20authentication%20bypass%20and%20account%20takeover.%20The%20disclosed%20database%20host%2C%20name%2C%20and%20user%20further%20assist%20follow-on%20attacks%20against%20the%20backend%20datastore.%22%2C%22likelihood%22%3A%22High.%20The%20endpoint%20is%20reachable%20over%20the%20network%20with%20no%20authentication%20and%20returns%20the%20secret%20directly%20in%20the%20HTTP%20200%20response%20body%2C%20making%20exploitation%20trivial%20and%20repeatable.%22%2C%22recommendation%22%3A%22Remove%20all%20secrets%20and%20internal%20configuration%20from%20the%20health%20endpoint%3B%20health%20checks%20should%20return%20only%20a%20minimal%20status%20indicator.%20Immediately%20rotate%20the%20exposed%20JWT%20signing%20secret%20and%20the%20database%20credentials%2C%20and%20invalidate%20any%20tokens%20signed%20with%20the%20compromised%20secret.%20Review%20other%20endpoints%20for%20similar%20unintended%20disclosure.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AC%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22GET%20%2Fapi%2Fhealth%20returned%20HTTP%20200%20with%20no%20authentication%20headers.%20Response%20body%20included%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.3.31%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%2F2.4.58%20(Ubuntu)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22bankofed_app%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%20%E2%80%94%20exposing%20the%20JWT%20signing%20secret%20and%20database%20configuration.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22jwt_secret%5C%22%3A%5C%22u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unauthenticated%20Admin%20User%20Export%20Exposes%20Password%20Hashes%2C%20TOTP%20Secrets%2C%20and%20PII%22%2C%22description%22%3A%22The%20GET%20%2Fapi%2Fadmin%2Fexport%2Fusers%20endpoint%20at%20http%3A%2F%2F192.168.3.101%2F%20returns%20the%20complete%20user%20directory%20without%20requiring%20any%20authentication%20or%20admin%20role.%20The%20response%20includes%20credential%20material%20(password_hash%2C%20totp_secret)%20and%20personally%20identifiable%20information%20(email%2C%20physical%20address%2C%20phone%20number)%20for%20every%20user.%20Any%20anonymous%2C%20unauthenticated%20caller%20can%20retrieve%20the%20entire%20user%20database.%22%2C%22impact%22%3A%22An%20attacker%20can%20obtain%20every%20user's%20password%20hashes%20and%20TOTP%20seeds%2C%20enabling%20offline%20password%20cracking%20and%202FA%20bypass%2C%20which%20together%20facilitate%20mass%20account%20takeover.%20The%20exposed%20PII%20(emails%2C%20addresses%2C%20phone%20numbers)%20additionally%20supports%20phishing%2C%20fraud%2C%20and%20privacy%20violations.%22%2C%22likelihood%22%3A%22High.%20The%20endpoint%20is%20reachable%20directly%20over%20the%20network%20with%20no%20cookies%2C%20session%2C%20or%20Authorization%20header.%20Both%20the%20deterministic%20authorization%20matrix%20and%20direct%20unauthenticated%20requests%20confirmed%20successful%20retrieval%20of%20sensitive%20fields%2C%20requiring%20no%20special%20conditions%20or%20user%20interaction.%22%2C%22recommendation%22%3A%22Enforce%20authentication%20and%20an%20explicit%20admin%20role%2Fauthorization%20check%20on%20%2Fapi%2Fadmin%2Fexport%2Fusers%20before%20returning%20any%20data.%20Remove%20credential%20material%20(password_hash%2C%20totp_secret)%20from%20all%20API%20serialization%20so%20it%20is%20never%20included%20in%20responses%20under%20any%20circumstance.%20Review%20other%20administrative%20and%20export%20endpoints%20for%20the%20same%20missing%20access%20control.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fexport%2Fusers%22%2C%22evidence%22%3A%22GET%20%2Fapi%2Fadmin%2Fexport%2Fusers%20returned%20HTTP%20200%20(content-type%3A%20application%2Fjson)%20with%20no%20authentication%20(no%20cookies%2C%20no%20Authorization%20header).%20The%20response%20contained%20all%20users'%20full%20records%2C%20including%20bcrypt%2FMD5%20password_hash%20values%2C%20TOTP%20secrets%2C%20emails%2C%20physical%20addresses%2C%20and%20phone%20numbers.%20Both%20the%20deterministic%20auth%20matrix%20and%20direct%20unauthenticated%20requests%20received%20200%20responses%20containing%20these%20sensitive%20fields.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22alice%22%2C%22validation_status%22%3A%22validating%22%2C%22validation_note%22%3A%22Validation%20running.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22IDOR%3A%20External%20Transfer%20Debits%20Any%20Customer's%20Account%20(from_account_id%20Not%20Ownership-Checked)%22%2C%22description%22%3A%22The%20POST%20%2Fapi%2Ftransfers%2Fexternal%20endpoint%20resolves%20the%20source%20account%20solely%20from%20the%20attacker-supplied%20from_account_id%20parameter%20(via%20Account%3A%3AfindById)%20without%20verifying%20that%20the%20account%20belongs%20to%20the%20authenticated%20user.%20As%20a%20result%2C%20an%20authenticated%20user%20can%20specify%20any%20account%20ID%20as%20the%20source%20of%20an%20external%20funds%20transfer%2C%20regardless%20of%20ownership.%20This%20is%20a%20broken%20object-level%20authorization%20(IDOR)%20flaw%20on%20a%20money-movement%20operation.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20debit%20funds%20from%20any%20customer's%20account%20and%20send%20them%20to%20an%20arbitrary%20external%20destination%20(BSB%20and%20account%20number)%2C%20enabling%20full%20theft%20of%20funds%20from%20arbitrary%20accounts.%20In%20the%20observed%20test%2C%20a%20transfer%20drove%20the%20victim%20account%20balance%20to%20-992788.50%2C%20demonstrating%20that%20the%20debit%20is%20applied%20with%20no%20ownership%20or%20balance%20restriction.%22%2C%22likelihood%22%3A%22High.%20Exploitation%20requires%20only%20an%20authenticated%20session%20and%20knowledge%20(or%20enumeration)%20of%20a%20target%20account_id%2C%20which%20are%20sequential%20integers.%20The%20attack%20was%20reproduced%20directly%20against%20the%20live%20endpoint%20with%20a%20single%20request%20and%20required%20no%20special%20conditions.%22%2C%22recommendation%22%3A%22Resolve%20the%20source%20account%20using%20a%20user-scoped%20query%20(e.g.%2C%20Account%3A%3AfindByIdForUser)%20that%20binds%20the%20lookup%20to%20the%20authenticated%20user's%20ID%2C%20and%20reject%20any%20request%20where%20from_account_id%20is%20not%20owned%20by%20the%20authenticated%20user%20with%20an%20authorization%20error.%20Apply%20the%20same%20ownership%20enforcement%20consistently%20across%20all%20account-referencing%20transfer%20and%20transaction%20endpoints%2C%20and%20add%20server-side%20balance%2Flimit%20validation.%22%2C%22cvss_score%22%3A9.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22Authenticated%20as%20user%201%20(owns%20accounts%201%2C2%2C3).%20POST%20%2Fapi%2Ftransfers%2Fexternal%20with%20%7B%5C%22from_account_id%5C%22%3A4%2C%5C%22amount%5C%22%3A999999%2C%5C%22to_bsb%5C%22%3A%5C%22063-100%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2244556677%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%7D%20returned%20HTTP%20201%3A%20%7B%5C%22transaction_id%5C%22%3A36%2C%5C%22from_account_id%5C%22%3A4%2C...%2C%5C%22new_from_balance%5C%22%3A%5C%22-992788.50%5C%22%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%7D.%20Account%204%20belongs%20to%20user%202%20per%20the%20data%20export%2C%20confirming%20an%20unauthorized%20cross-user%20debit.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20%7B%5C%22from_account_id%5C%22%3A4%2C%5C%22amount%5C%22%3A999999%2C...%7D%20(Bearer%20forged%20user1)%22%2C%22response_evidence%22%3A%22%7B%5C%22transaction_id%5C%22%3A36%2C%5C%22from_account_id%5C%22%3A4%2C...%2C%5C%22new_from_balance%5C%22%3A%5C%22-992788.50%5C%22%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unconfirmed%22%2C%22validation_note%22%3A%22The%20crawl%20did%20not%20record%20a%20user%20that%20could%20access%20this%20page%2C%20so%20there%20is%20no%20access-control%20baseline%20to%20compare%20against.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22External%20Transfer%20Missing%20Balance%20Validation%20Allows%20Unlimited%20Overdraft%22%2C%22description%22%3A%22The%20external%20transfer%20endpoint%20(POST%20%2Fapi%2Ftransfers%2Fexternal)%20validates%20only%20that%20the%20requested%20amount%20is%20positive.%20It%20does%20not%20verify%20that%20the%20debit%20amount%20does%20not%20exceed%20the%20source%20account's%20available%20balance%20before%20completing%20the%20transaction.%20As%20a%20result%2C%20a%20transfer%20far%20larger%20than%20the%20available%20funds%20is%20accepted%20and%20the%20source%20account%20is%20driven%20into%20a%20large%20negative%20balance.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20transfer%20amounts%20vastly%20exceeding%20the%20funds%20actually%20held%20in%20a%20source%20account%2C%20causing%20direct%20financial%20loss%20and%20negative%20account%20balances.%20If%20combined%20with%20the%20separately%20reported%20source-account%20IDOR%2C%20this%20weakness%20could%20be%20leveraged%20against%20accounts%20the%20attacker%20does%20not%20own%2C%20enabling%20large-scale%20fraud.%22%2C%22likelihood%22%3A%22High.%20The%20flaw%20was%20demonstrated%20with%20a%20single%20POST%20request%20requiring%20no%20special%20conditions%20beyond%20authenticated%20access%3B%20the%20server%20accepted%20the%20oversized%20debit%20and%20returned%20a%20completed%20status.%22%2C%22recommendation%22%3A%22Enforce%20a%20sufficient-funds%20check%20before%20debiting%20the%20source%20account%2C%20applying%20any%20account-type%20and%20overdraft-limit%20rules.%20Perform%20this%20validation%20atomically%20within%20the%20same%20database%20transaction%20that%20records%20the%20debit%20to%20prevent%20race%20conditions%2C%20and%20reject%20transfers%20that%20would%20exceed%20the%20permitted%20balance.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22A%20POST%20to%20%2Fapi%2Ftransfers%2Fexternal%20with%20%7B%5C%22from_account_id%5C%22%3A4%2C%5C%22amount%5C%22%3A999999%2C...%7D%20against%20account%204%20(balance%207210.50)%20returned%20HTTP%20201%20with%20%5C%22new_from_balance%5C%22%3A%5C%22-992788.50%5C%22%20and%20%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%20confirming%20the%20debit%20was%20accepted%20despite%20far%20exceeding%20the%20available%20balance.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20%7B%5C%22amount%5C%22%3A999999%2C%5C%22from_account_id%5C%22%3A4%2C...%7D%22%2C%22response_evidence%22%3A%22%5C%22new_from_balance%5C%22%3A%5C%22-992788.50%5C%22%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Server-Side%20TOTP%20Step-Up%20Enforcement%20Bypassed%20on%20External%20Transfers%22%2C%22description%22%3A%22The%20external%20transfer%20endpoint%20(%2Fapi%2Ftransfers%2Fexternal)%20fails%20to%20enforce%20the%20step-up%20TOTP%20requirement%20returned%20by%20%2Fapi%2Ftransfers%2Fcheck%20for%20manual%20transfers.%20When%20%2Fapi%2Ftransfers%2Fcheck%20reports%20requires_totp%3Dtrue%20for%20a%20manual%20transfer%2C%20the%20transfer%20can%20still%20be%20completed%20by%20submitting%20the%20transfer%20request%20with%20no%20totp_code.%20The%20MFA%20gate%20is%20evaluated%20client-side%20only%20and%20is%20not%20enforced%20server-side%2C%20allowing%20users%20with%20TOTP%20disabled%20(totp_configured%3Dfalse)%20or%20any%20request%20omitting%20the%20code%20to%20proceed%20unauthenticated%20by%20MFA.%22%2C%22impact%22%3A%22An%20attacker%20or%20account%20holder%20can%20execute%20high-risk%20manual%20external%20transfers%20without%20satisfying%20the%20intended%20step-up%20MFA%20control.%20This%20undermines%20transaction%20authorization%20for%20exactly%20the%20operations%20the%20control%20is%20designed%20to%20protect%2C%20enabling%20fraudulent%20or%20unauthorized%20fund%20movement%20without%20a%20valid%20TOTP.%22%2C%22likelihood%22%3A%22high%22%2C%22recommendation%22%3A%22Enforce%20the%20TOTP%20requirement%20server-side%20on%20%2Fapi%2Ftransfers%2Fexternal.%20Whenever%20checkTotpRequired%20(or%20equivalent%20logic)%20determines%20required%3Dtrue%2C%20the%20transfer%20handler%20must%20reject%20requests%20that%20lack%20a%20valid%2C%20freshly%20verified%20TOTP%20code%2C%20and%20must%20reject%20transfers%20from%20users%20who%20have%20no%20TOTP%20configured%20rather%20than%20defaulting%20to%20completion.%20Do%20not%20rely%20on%20the%20client%20to%20honor%20the%20requires_totp%20response%20from%20%2Fapi%2Ftransfers%2Fcheck.%22%2C%22cvss_score%22%3A7.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fcheck%20%7Btransfer_type%3A%5C%22manual%5C%22%7D%20returned%20%7B%5C%22requires_totp%5C%22%3Atrue%2C%5C%22reason%5C%22%3A%5C%22manual_entry%5C%22%2C%5C%22totp_configured%5C%22%3Afalse%7D.%20A%20subsequent%20POST%20%2Fapi%2Ftransfers%2Fexternal%20for%20a%20manual%20transfer%20with%20no%20totp_code%20returned%20201%20%7B%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22totp_verified%5C%22%3Afalse%7D%2C%20confirming%20the%20declared%20TOTP%20requirement%20was%20not%20enforced%20server-side.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20%7Btransfer_type%3A%5C%22manual%5C%22%7D%20with%20no%20totp_code%22%2C%22response_evidence%22%3A%22check%3A%20%5C%22requires_totp%5C%22%3Atrue%3B%20transfer%3A%20%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22totp_verified%5C%22%3Afalse%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SQL%20Injection%20in%20Admin%20Customer%20Search%20Parameter%20(%2Fapi%2Fadmin%2Fcustomers)%22%2C%22description%22%3A%22The%20%60search%60%20query%20parameter%20on%20the%20admin%20customer%20search%20endpoint%20(%60%2Fapi%2Fadmin%2Fcustomers%60)%20is%20concatenated%20directly%20into%20a%20LIKE-based%20WHERE%20clause%20and%20executed%20via%20PDO%3A%3Aquery()%20without%20bound%20parameters.%20This%20is%20confirmed%20in%20AdminUserController.php%20line%2028%2C%20where%20the%20unparameterized%20query%20construction%20allows%20attacker-controlled%20input%20to%20break%20out%20of%20the%20intended%20SQL%20context.%20Exploitation%20requires%20an%20admin-authenticated%20caller%20(Bearer%20token).%22%2C%22impact%22%3A%22An%20authenticated%20admin%20caller%20(or%20an%20attacker%20who%20has%20obtained%20admin%20access%20through%20credential%20compromise%20or%20auth%20weaknesses)%20can%20inject%20arbitrary%20SQL%2C%20enabling%20UNION-based%20and%20subquery%20data%20extraction%2C%20and%20potentially%20modification%20of%20arbitrary%20database%20records.%20Given%20this%20is%20a%20banking%20application%2C%20this%20could%20expose%20customer%20PII%2C%20account%20details%2C%20and%20transaction%20data.%22%2C%22likelihood%22%3A%22Medium.%20Exploitation%20is%20confirmed%20reachable%20but%20gated%20behind%20admin%20authentication%20(PR%3AH).%20The%20MySQL%20syntax%20error%20reflected%20from%20a%20single-quote%20payload%20demonstrates%20the%20input%20reaches%20the%20SQL%20parser%20unescaped%2C%20making%20injection%20straightforward%20for%20any%20actor%20with%20admin-level%20access.%22%2C%22recommendation%22%3A%22Replace%20the%20concatenated%20query%20with%20a%20parameterized%2Fprepared%20statement%20that%20binds%20the%20LIKE%20value%20as%20a%20bound%20parameter%20(e.g.%2C%20PDO%3A%3Aprepare%20with%20a%20placeholder%20and%20bound%20value%20such%20as%20'%25'%20.%20%24search%20.%20'%25').%20Never%20concatenate%20user-controlled%20input%20into%20SQL.%20Additionally%2C%20disable%20verbose%20database%20error%20output%20in%20production%20responses.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AH%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dx%22%2C%22evidence%22%3A%22GET%20%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dx'%20(with%20admin%20Bearer%20token)%20returned%20HTTP%20500%20with%20a%20MySQL%20error%3A%20%5C%22SQLSTATE%5B42000%5D%3A%20...1064...%20near%20'%25'%20OR%20last_name%20LIKE%20'%25x'%25'%20OR%20email%20LIKE%20'%25x'%25''%20at%20line%201%5C%22%20originating%20at%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FControllers%2FAdminUserController.php%20line%2028%20via%20PDO-%3Equery().%20The%20reflected%20query%20fragment%20shows%20the%20single%20quote%20terminating%20the%20string%20literal%2C%20confirming%20unparameterized%20concatenation%20of%20the%20search%20parameter%20into%20the%20SQL%20statement.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dx'%20(Bearer%20admin)%22%2C%22response_evidence%22%3A%221064%20...%20near%20'%25'%20OR%20last_name%20LIKE%20'%25x'%25'%20OR%20email%20LIKE%20'%25x'%25''%20at%20AdminUserController.php%3A28%20PDO-%3Equery()%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SQL%20Injection%20via%20ORDER%20BY%20sort%20parameter%20in%20%2Fapi%2Ftransactions%22%2C%22description%22%3A%22The%20GET%20%2Fapi%2Ftransactions%20endpoint%20interpolates%20the%20user-controlled%20'sort'%20query%20parameter%20directly%20into%20the%20ORDER%20BY%20clause%20of%20a%20MySQL%20query%20without%20validation%20or%20parameterization.%20The%20vulnerable%20code%20path%20is%20in%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FModels%2FTransaction.php%20(line%2055)%2C%20where%20the%20sort%20value%20is%20placed%20into%20the%20ORDER%20BY%20fragment.%20Because%20ORDER%20BY%20identifiers%20cannot%20be%20safely%20bound%20as%20query%20parameters%2C%20the%20injected%20value%20alters%20the%20SQL%20statement%20structure%20directly.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20(including%20one%20using%20the%20forged-JWT%20path%20observed%20during%20testing)%20can%20manipulate%20query%20structure%20via%20ORDER%20BY%20injection.%20This%20can%20be%20leveraged%20for%20data%20extraction%20from%20the%20transactions%20table%20using%20subquery-based%20or%20error-based%20techniques%2C%20potentially%20exposing%20financial%20records%20across%20users.%22%2C%22likelihood%22%3A%22High.%20The%20injection%20point%20is%20reachable%20by%20any%20authenticated%20caller%2C%20and%20the%20observed%20HTTP%20500%20MySQL%20syntax%20error%20confirms%20that%20unsanitized%20input%20breaks%20out%20of%20the%20ORDER%20BY%20clause.%20Error-based%20feedback%20is%20directly%20returned%2C%20materially%20simplifying%20exploitation.%22%2C%22recommendation%22%3A%22Never%20interpolate%20user%20input%20into%20SQL.%20Validate%20the%20'sort'%20parameter%20against%20a%20strict%20allowlist%20of%20permitted%20column%20names%20and%20map%20sort%20keys%20to%20fixed%2C%20server-side%20column%20identifiers.%20Reject%20any%20value%20not%20in%20the%20allowlist.%20Additionally%2C%20suppress%20verbose%20database%20errors%20in%20production%20responses.%22%2C%22cvss_score%22%3A8.6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransactions%3Fsort%3Did%22%2C%22evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Fsort%3Did%60%20(with%20a%20trailing%20backtick)%20returned%20HTTP%20500%20with%20a%20MySQL%20error%3A%20%5C%22SQLSTATE%5B42000%5D%3A%20Syntax%20error%20or%20access%20violation%3A%201064%20You%20have%20an%20error%20in%20your%20SQL%20syntax%3B%20...%20near%20'%60%20DESC%20LIMIT%20%3F%20OFFSET%20%3F'%20at%20line%204%5C%22%20originating%20at%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FModels%2FTransaction.php%20line%2055.%20The%20backtick-terminated%20value%20appearing%20inside%20the%20'%60%20DESC%20LIMIT%20%3F%20OFFSET%20%3F'%20fragment%20confirms%20the%20sort%20input%20is%20placed%20directly%20into%20the%20ORDER%20BY%20clause.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Fsort%3Did%60%20(Bearer%20forged%20user1)%22%2C%22response_evidence%22%3A%22SQLSTATE%5B42000%5D%3A%20...%201064%20You%20have%20an%20error%20in%20your%20SQL%20syntax%20...%20near%20'%60%20DESC%20...'%20at%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FModels%2FTransaction.php%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Broken%20Object%20Level%20Authorization%20in%20PUT%20%2Fapi%2Fprofile%20Allows%20Modification%20of%20Arbitrary%20User%20Profiles%22%2C%22description%22%3A%22The%20PUT%20%2Fapi%2Fprofile%20endpoint%20determines%20the%20record%20to%20update%20from%20a%20client-supplied%20user_id%20field%20in%20the%20JSON%20request%20body%20rather%20than%20from%20the%20authenticated%20session%20or%20token.%20The%20server%20does%20not%20verify%20that%20this%20user_id%20matches%20the%20authenticated%20user%2C%20so%20any%20authenticated%20user%20can%20update%20the%20profile%20attributes%20(phone%2C%20email%2C%20address)%20of%20any%20other%20user%20by%20specifying%20their%20ID.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20overwrite%20arbitrary%20users'%20contact%20details%2C%20including%20email%20addresses.%20Changing%20a%20victim's%20email%20can%20enable%20full%20account%20takeover%20via%20a%20subsequent%20password-reset%20flow%2C%20and%20arbitrary%20modification%20of%20profile%20data%20constitutes%20PII%20tampering%20across%20all%20accounts.%22%2C%22likelihood%22%3A%22High.%20Exploitation%20requires%20only%20a%20single%20authenticated%20request%20with%20a%20modified%20user_id%20in%20the%20body.%20This%20was%20confirmed%20in%20the%20observed%20context%3A%20authenticated%20as%20user%201%2C%20the%20tester%20modified%20user%202's%20record.%22%2C%22recommendation%22%3A%22Ignore%20any%20client-supplied%20user_id%20in%20the%20request%20body.%20Always%20resolve%20the%20update%20target%20from%20the%20authenticated%20user's%20identity%20(session%2Ftoken).%20Additionally%2C%20enforce%20server-side%20object-level%20authorization%20checks%20on%20all%20profile-modifying%20operations.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22Authenticated%20as%20user%201%2C%20sent%20PUT%20%2Fapi%2Fprofile%20with%20body%20%7B%5C%22phone%5C%22%3A%5C%220400000BOLA%5C%22%2C%5C%22user_id%5C%22%3A2%7D.%20The%20server%20responded%20HTTP%20200%20and%20returned%20user%202's%20record%20reflecting%20the%20injected%20value%3A%20%7B%5C%22id%5C%22%3A2%2C%5C%22email%5C%22%3A%5C%22wei.zhang%40example.com%5C%22%2C...%2C%5C%22phone%5C%22%3A%5C%220400000BOLA%5C%22%2C...%2C%5C%22message%5C%22%3A%5C%22Profile%20updated%20successfully%5C%22%7D%2C%20confirming%20a%20different%20user's%20profile%20was%20modified.%22%2C%22request_evidence%22%3A%22PUT%20%2Fapi%2Fprofile%20%7B%5C%22phone%5C%22%3A%5C%220400000BOLA%5C%22%2C%5C%22user_id%5C%22%3A2%7D%22%2C%22response_evidence%22%3A%22%7B%5C%22id%5C%22%3A2%2C%5C%22email%5C%22%3A%5C%22wei.zhang%40example.com%5C%22%2C...%2C%5C%22phone%5C%22%3A%5C%220400000BOLA%5C%22%2C...%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22Validation%20could%20not%20reproduce%20unauthorized%20access.%20Alternate%20users%20received%20an%20access%20denial%2C%20login%20response%2C%20generic%20SPA%20shell%2C%20or%20no%20protected%20content%20signal.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Passwords%20Stored%20as%20Unsalted%20MD5%20and%20Disclosed%20in%20API%20Responses%22%2C%22description%22%3A%22The%20registration%20endpoint%20at%20http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Fregister%20stores%20user%20passwords%20using%20unsalted%20MD5%2C%20a%20fast%20cryptographic%20hash%20unsuitable%20for%20password%20storage.%20Registering%20a%20user%20with%20the%20password%20%5C%22a%5C%22%20returned%20a%20201%20response%20containing%20password_hash%20%5C%22e7133e3cff94e11c1d48bf8c715660b3%5C%22%2C%20which%20is%20the%20exact%20MD5%20digest%20of%20%5C%22a%5C%22.%20This%20confirms%20both%20a%20weak%20hashing%20scheme%20and%20the%20disclosure%20of%20the%20stored%20password%20hash%20in%20the%20API%20response%20body.%20The%20same%20hash%20is%20additionally%20exposed%20via%20the%20export%20endpoint.%22%2C%22impact%22%3A%22Unsalted%20MD5%20hashes%20can%20be%20cracked%20at%20billions%20of%20guesses%20per%20second%20and%20are%20trivially%20reversible%20for%20common%20or%20short%20passwords.%20Because%20the%20hashes%20are%20directly%20disclosed%20in%20registration%20responses%20and%20via%20the%20export%20endpoint%2C%20an%20attacker%20can%20harvest%20hashes%20and%20perform%20offline%20cracking%20at%20scale%2C%20enabling%20mass%20credential%20recovery%20and%20password%20reuse%20attacks%20against%20other%20services.%22%2C%22likelihood%22%3A%22high%22%2C%22recommendation%22%3A%22Replace%20MD5%20with%20a%20password-adaptive%2C%20salted%20hashing%20algorithm%20such%20as%20bcrypt%2C%20scrypt%2C%20or%20Argon2%20with%20appropriate%20work%20factors.%20Migrate%20existing%20hashes%20on%20next%20login.%20Never%20include%20password_hash%20in%20API%20responses%20or%20export%20outputs.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Fauth%2Fregister%20with%20password%20%5C%22a%5C%22%20returned%20201%20with%20body%20containing%20%5C%22password_hash%5C%22%3A%5C%22e7133e3cff94e11c1d48bf8c715660b3%5C%22.%20This%2032-hex%20value%20equals%20md5(%5C%22a%5C%22)%2C%20confirming%20unsalted%20MD5%20storage%20and%20hash%20disclosure%20in%20the%20response.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Fregister%20%7B%5C%22password%5C%22%3A%5C%22a%5C%22%2C...%7D%22%2C%22response_evidence%22%3A%22%5C%22password_hash%5C%22%3A%5C%22e7133e3cff94e11c1d48bf8c715660b3%5C%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Sensitive%20credential%20material%20(password%20hash%20and%20TOTP%20secret)%20exposed%20in%20%2Fapi%2Fprofile%20response%22%2C%22description%22%3A%22The%20GET%20%2Fapi%2Fprofile%20endpoint%20(backed%20by%20User%3A%3AtoPublic)%20serializes%20the%20fields%20password_hash%20and%20totp_secret%20directly%20into%20its%20JSON%20response.%20Any%20authenticated%20caller%20presenting%20a%20bearer%20token%20receives%20the%20account's%20stored%20bcrypt%20password%20hash%20and%20TOTP%20secret.%20Observed%20against%20http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%2C%20the%20response%20for%20user%20amelia.chen%40example.com%20included%20the%20full%20password_hash%20value%3B%20the%20totp_secret%20field%20was%20present%20in%20the%20serialization%20(null%20for%20this%20account%20because%20MFA%20was%20not%20enabled).%22%2C%22impact%22%3A%22Exposure%20of%20the%20bcrypt%20password%20hash%20enables%20offline%20password%20cracking%20against%20affected%20accounts.%20Exposure%20of%20the%20TOTP%20secret%2C%20where%20MFA%20is%20enabled%2C%20allows%20an%20attacker%20to%20generate%20valid%20one-time%20codes%20and%20defeat%20the%20second%20factor.%20Because%20these%20secrets%20are%20returned%20to%20any%20bearer-token%20holder%2C%20an%20attacker%20who%20can%20obtain%20or%20forge%20tokens%20could%20harvest%20this%20material%20for%20multiple%20users.%22%2C%22likelihood%22%3A%22high%22%2C%22recommendation%22%3A%22Remove%20password_hash%20and%20totp_secret%20from%20all%20API%20serializations.%20Replace%20ad-hoc%20serialization%20with%20a%20strict%20output%20allowlist%20that%20returns%20only%20fields%20intended%20for%20client%20consumption.%20Audit%20User%3A%3AtoPublic%20and%20any%20similar%20serializers%20to%20ensure%20no%20secret%20or%20credential%20material%20is%20ever%20emitted.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22GET%20%2Fapi%2Fprofile%20returned%20a%20JSON%20body%20including%20%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%2F.og%2Fat2.uheWG%2Figi%5C%22%20and%20%5C%22totp_secret%5C%22%3Anull%20for%20user%20amelia.chen%40example.com%2C%20confirming%20credential%20fields%20are%20serialized%20in%20the%20response.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye...%5C%22%2C%5C%22totp_secret%5C%22%3Anull%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Stored%20Cross-Site%20Scripting%20via%20Transfer%20Description%20Field%22%2C%22description%22%3A%22The%20transfer%20description%20field%20accepted%20by%20POST%20%2Fapi%2Ftransfers%2Fexternal%20does%20not%20perform%20input%20validation%20or%20output%20encoding.%20User-supplied%20HTML%2FJavaScript%20is%20persisted%20verbatim%20and%20returned%20unescaped%20by%20the%20transaction%20APIs%20(e.g.%2C%20GET%20%2Fapi%2Ftransactions%2F%7Bid%7D).%20The%20front-end%20transaction%20renderers%20insert%20the%20raw%20value%20into%20the%20DOM%20via%20innerHTML%20without%20escaping%20%E2%80%94%20dashboard.js%20(line%2076%2C%20container.innerHTML%20%3D%20html)%20and%20accounts.js%20('%3Ctd%3E'%20%2B%20(tx.description%20%7C%7C%20'%E2%80%94')%20%2B%20'%3C%2Ftd%3E')%20%E2%80%94%20causing%20any%20stored%20script%20to%20execute%20when%20a%20transaction%20list%20is%20rendered.%20Because%20a%20transfer%20targeting%20another%20customer's%20account%20appears%20in%20that%20customer's%20transaction%20views%2C%20the%20payload%20executes%20in%20a%20victim's%20browser%20context%2C%20making%20this%20a%20stored%2C%20cross-user%20XSS.%22%2C%22impact%22%3A%22An%20attacker%20can%20initiate%20a%20transfer%20to%20a%20victim's%20account%20with%20a%20scripted%20description.%20When%20the%20victim%20(or%20an%20administrator%20reviewing%20transactions)%20loads%20their%20transaction%20list%2C%20the%20attacker-controlled%20JavaScript%20executes%20in%20their%20authenticated%20session.%20This%20enables%20theft%20of%20session%20tokens%20stored%20in%20localStorage%20(bankofed_token%2C%20bankofed_admin_token)%2C%20unauthorized%20account%20actions%20performed%20as%20the%20victim%2C%20and%20potential%20compromise%20of%20the%20admin%20panel.%22%2C%22likelihood%22%3A%22medium%22%2C%22recommendation%22%3A%22HTML-escape%20all%20user-supplied%20fields%20%E2%80%94%20especially%20the%20transfer%20description%20%E2%80%94%20before%20inserting%20them%20into%20the%20DOM.%20Prefer%20textContent%20over%20innerHTML%2C%20or%20use%20a%20vetted%20escaping%2Fsanitization%20helper%20when%20HTML%20rendering%20is%20required.%20Additionally%20enforce%20server-side%20input%20validation%20and%20contextual%20output%20encoding%20on%20the%20transfer%20and%20transaction%20APIs%2C%20and%20consider%20a%20restrictive%20Content-Security-Policy%20as%20defense%20in%20depth.%22%2C%22cvss_score%22%3A6.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AR%2FS%3AC%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20with%20description%20%5C%22%3Cimg%20src%3Dx%20onerror%3Dalert(document.domain)%3E%5C%22%20returned%20201%2C%20storing%20the%20payload%20verbatim%20(transaction_id%2037%2C%20to_account_id%204%20%3D%20user%202's%20account).%20GET%20%2Fapi%2Ftransactions%2F37%20returned%20%5C%22description%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3Dalert(document.domain)%3E%5C%22%20unescaped.%20The%20fetched%20dashboard.js%20renders%20transaction%20descriptions%20via%20innerHTML%20without%20escaping.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20%7B%5C%22description%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3Dalert(document.domain)%3E%5C%22%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_account_number%5C%22%3A%5C%2220000001%5C%22%2C%5C%22to_bsb%5C%22%3A%5C%22062-002%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22amount%5C%22%3A1%7D%22%2C%22response_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%2F37%20%E2%86%92%20%5C%22description%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3Dalert(document.domain)%3E%5C%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Weak%20Password%20Policy%3A%20Single-Character%20Passwords%20Accepted%20at%20Registration%22%2C%22description%22%3A%22The%20registration%20endpoint%20at%20%2Fapi%2Fauth%2Fregister%20does%20not%20enforce%20any%20minimum%20password%20length%20or%20complexity%20requirements.%20A%20registration%20request%20submitting%20a%20single-character%20password%20(%5C%22a%5C%22)%20was%20accepted%20and%20resulted%20in%20the%20successful%20creation%20of%20a%20new%20account%20(id%2017).%20This%20indicates%20the%20absence%20of%20server-side%20password%20strength%20validation.%22%2C%22impact%22%3A%22Users%20(and%20attackers)%20can%20create%20accounts%20protected%20by%20trivially%20weak%20passwords%2C%20substantially%20lowering%20the%20effort%20required%20for%20successful%20credential%20guessing%2C%20brute-force%2C%20and%20credential-stuffing%20attacks%20against%20the%20application's%20authentication%20surface.%22%2C%22likelihood%22%3A%22Medium.%20The%20weakness%20is%20trivially%20reproducible%20via%20a%20single%20unauthenticated%20API%20request%2C%20but%20actual%20account%20compromise%20still%20depends%20on%20targeting%20accounts%20that%20use%20weak%20passwords%20and%20on%20the%20presence%20(or%20absence)%20of%20rate%20limiting%20and%20lockout%20controls.%22%2C%22recommendation%22%3A%22Enforce%20a%20server-side%20password%20policy%20at%20registration%20and%20password-change%20endpoints%3A%20require%20a%20minimum%20length%20of%20at%20least%2012%20characters%2C%20and%20validate%20submitted%20passwords%20against%20a%20known-breached-password%20list%20(e.g.%2C%20HaveIBeenPwned%20range%20API)%20rather%20than%20relying%20solely%20on%20composition%20rules.%20Reject%20weak%20passwords%20with%20a%20clear%20error%2C%20and%20apply%20the%20same%20policy%20consistently%20across%20all%20account-creation%20and%20password-update%20flows.%22%2C%22cvss_score%22%3A4.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Fauth%2Fregister%20with%20%7B%5C%22password%5C%22%3A%5C%22a%5C%22%7D%20returned%20HTTP%20201%20and%20created%20account%20id%2017%20with%20response%20%7B%5C%22success%5C%22%3Atrue%2C...%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%2C%20confirming%20that%20no%20minimum%20length%20or%20complexity%20requirement%20is%20enforced.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Fregister%20%7B%5C%22password%5C%22%3A%5C%22a%5C%22%2C%5C%22email%5C%22%3A%5C%22aespa_4789e528%40example.invalid%5C%22%2C...%7D%22%2C%22response_evidence%22%3A%22%7B%5C%22success%5C%22%3Atrue%2C...%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%20(id%2017)%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Broken%20Object%20Level%20Authorization%20in%20GET%20%2Fapi%2Ftransactions%2F%7Bid%7D%20Exposes%20Other%20Customers'%20Transaction%20Details%22%2C%22description%22%3A%22The%20GET%20%2Fapi%2Ftransactions%2F%7Bid%7D%20endpoint%20looks%20up%20a%20transaction%20solely%20by%20its%20path%20ID%20and%20returns%20it%20without%20verifying%20that%20the%20authenticated%20caller%20owns%20the%20associated%20account.%20An%20authenticated%20user%20can%20enumerate%20sequential%20transaction%20IDs%20to%20retrieve%20transactions%20belonging%20to%20other%20customers.%20Authenticated%20as%20user%201%20(who%20owns%20accounts%201%2C%202%2C%20and%203)%2C%20a%20request%20to%20GET%20%2Fapi%2Ftransactions%2F10%20returned%20a%20transaction%20tied%20to%20account%209%2C%20which%20does%20not%20belong%20to%20user%201.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20enumerate%20transaction%20IDs%20to%20read%20arbitrary%20customers'%20financial%20records%2C%20disclosing%20transfer%20amounts%2C%20descriptions%2C%20and%20destination%20BSB%2Faccount%20numbers.%20This%20constitutes%20sensitive%20financial%20data%20leakage%20across%20customer%20boundaries.%22%2C%22likelihood%22%3A%22High.%20Transaction%20IDs%20are%20sequential%20and%20predictable%2C%20the%20endpoint%20requires%20only%20a%20valid%20authenticated%20session%2C%20and%20no%20ownership%20check%20is%20performed%2C%20making%20mass%20enumeration%20straightforward.%22%2C%22recommendation%22%3A%22Enforce%20object-level%20authorization%20on%20the%20endpoint%3A%20before%20returning%20a%20transaction%2C%20verify%20that%20its%20from_account_id%20(or%20otherwise%20associated%20account)%20belongs%20to%20the%20authenticated%20user.%20Reject%20unauthorized%20requests%20with%20HTTP%20403%2F404.%20Apply%20the%20same%20ownership%20check%20consistently%20across%20all%20object-scoped%20endpoints.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Ftransactions%2F10%22%2C%22evidence%22%3A%22Authenticated%20as%20user%201%20(owns%20accounts%201%2C2%2C3%20per%20export).%20GET%20%2Fapi%2Ftransactions%2F10%20returned%20HTTP%20200%3A%20%7B%5C%22id%5C%22%3A10%2C%5C%22from_account_id%5C%22%3A9%2C%5C%22to_bsb%5C%22%3A%5C%22063-100%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2244556677%5C%22%2C%5C%22amount%5C%22%3A%5C%22400.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Mum%20allowance%5C%22%2C...%7D.%20Account%209%20does%20not%20belong%20to%20user%201%2C%20confirming%20cross-customer%20access.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%2F10%20(Bearer%20forged%20user1)%22%2C%22response_evidence%22%3A%22%7B%5C%22id%5C%22%3A10%2C%5C%22from_account_id%5C%22%3A9%2C...%2C%5C%22description%5C%22%3A%5C%22Mum%20allowance%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22Validation%20could%20not%20reproduce%20unauthorized%20access.%20Alternate%20users%20received%20an%20access%20denial%2C%20login%20response%2C%20generic%20SPA%20shell%2C%20or%20no%20protected%20content%20signal.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20Rate-Limiting%20and%20Account%20Lockout%20on%20Login%20Endpoint%22%2C%22description%22%3A%22The%20authentication%20endpoint%20at%20%2Fapi%2Fauth%2Flogin%20does%20not%20enforce%20any%20rate-limiting%2C%20account%20lockout%2C%20progressive%20delay%2C%20or%20CAPTCHA.%20Six%20consecutive%20failed%20authentication%20attempts%20against%20a%20valid%20account%20(amelia.chen%40example.com)%20each%20returned%20an%20identical%20HTTP%20401%20response%2C%20with%20no%20throttling%2C%20no%20429%20Too%20Many%20Requests%2C%20and%20no%20lockout%20introduced%20even%20at%20the%20sixth%20attempt.%22%2C%22impact%22%3A%22The%20absence%20of%20anti-automation%20controls%20allows%20an%20attacker%20to%20submit%20high%20volumes%20of%20authentication%20attempts%20against%20known%20or%20guessed%20accounts%2C%20enabling%20credential-stuffing%20and%20brute-force%20attacks%20without%20impediment.%20The%20risk%20is%20compounded%20where%20password%20hashing%20and%20password-policy%20weaknesses%20reduce%20the%20effort%20required%20to%20recover%20valid%20credentials.%22%2C%22likelihood%22%3A%22medium%22%2C%22recommendation%22%3A%22Implement%20server-side%20rate-limiting%20on%20the%20login%20endpoint%20(per-IP%20and%20per-account)%2C%20account%20lockout%20or%20exponential%20backoff%20after%20a%20threshold%20of%20failed%20attempts%2C%20and%20CAPTCHA%20or%20step-up%20verification%20on%20repeated%20failures.%20Add%20monitoring%20and%20alerting%20for%20anomalous%20authentication%20failure%20patterns%20to%20detect%20credential-stuffing%20campaigns.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%226%20consecutive%20POST%20%2Fapi%2Fauth%2Flogin%20requests%20for%20amelia.chen%40example.com%20with%20incorrect%20passwords%20(wrong1..wrong6)%20each%20returned%20HTTP%20401%20with%20no%20throttling%2C%20delay%2C%20lockout%2C%20or%20429%20introduced%20by%20attempt%20%236.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20x6%20%7Bemail%3Aamelia.chen%40example.com%2C%20password%3Awrong1..wrong6%7D%22%2C%22response_evidence%22%3A%22All%206%20attempts%3A%20status%20401%2C%20no%20429%2Flockout%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Permissive%20CORS%3A%20Arbitrary%20Origin%20Reflected%20with%20Credentials%20on%20Authenticated%20Profile%20API%22%2C%22description%22%3A%22The%20endpoint%20at%20http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%20reflects%20an%20attacker-controlled%20request%20Origin%20into%20the%20Access-Control-Allow-Origin%20response%20header%20while%20also%20setting%20Access-Control-Allow-Credentials%3A%20true%20(with%20Access-Control-Allow-Headers%3A%20*%20observed%20on%20prior%20responses).%20This%20configuration%20permits%20any%20external%20website%20to%20issue%20credentialed%20cross-origin%20requests%20to%20the%20authenticated%20API%20and%20read%20the%20responses%20in%20the%20victim's%20browser%20context.%22%2C%22impact%22%3A%22A%20victim%20who%20is%20authenticated%20to%20the%20application%20and%20visits%20an%20attacker-controlled%20page%20could%20have%20their%20browser%20make%20credentialed%20cross-origin%20requests%20to%20%2Fapi%2Fprofile%2C%20allowing%20the%20attacker's%20JavaScript%20to%20read%20the%20authenticated%20profile%20response.%20The%20observed%20response%20body%20includes%20sensitive%20data%20such%20as%20password_hash%2C%20so%20this%20misconfiguration%20could%20expose%20PII%20and%20credential%20material%20to%20a%20malicious%20origin.%22%2C%22likelihood%22%3A%22Medium.%20The%20misconfiguration%20is%20confirmed%20by%20direct%20request%2Fresponse%20inspection%3A%20an%20arbitrary%20Origin%20is%20reflected%20and%20credentials%20are%20permitted.%20However%2C%20no%20in-browser%20proof-of-concept%20was%20captured%20demonstrating%20an%20actual%20cross-origin%20read%2C%20so%20practical%20exploitation%20depends%20on%20a%20victim%20being%20authenticated%20and%20lured%20to%20an%20attacker%20page.%22%2C%22recommendation%22%3A%22Do%20not%20reflect%20arbitrary%20Origins.%20Implement%20a%20strict%20allowlist%20of%20trusted%20origins%20and%20only%20emit%20Access-Control-Allow-Origin%20for%20exact%20matches.%20Never%20combine%20a%20wildcard%20or%20reflected%20Origin%20with%20Access-Control-Allow-Credentials%3A%20true.%20Additionally%2C%20avoid%20returning%20sensitive%20fields%20such%20as%20password_hash%20in%20API%20responses.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22GET%20%2Fapi%2Fprofile%20with%20header%20Origin%3A%20https%3A%2F%2Fevil.example%20returned%20access-control-allow-origin%3A%20https%3A%2F%2Fevil.example%20and%20the%20authenticated%20profile%20body%20(including%20password_hash).%20Prior%20responses%20also%20showed%20access-control-allow-credentials%3A%20true%20and%20access-control-allow-headers%3A%20*.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fprofile%20Origin%3A%20https%3A%2F%2Fevil.example%22%2C%22response_evidence%22%3A%22access-control-allow-origin%3A%20https%3A%2F%2Fevil.example%20(with%20ACAC%3Atrue%20observed)%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Verbose%20Error%20Handling%20Discloses%20Stack%20Traces%20and%20Filesystem%20Paths%22%2C%22description%22%3A%22The%20global%20exception%20handler%20at%20http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%20returns%20detailed%20diagnostic%20information%20in%20its%20JSON%20error%20response%20when%20an%20unhandled%20application%20exception%20occurs.%20Triggering%20an%20exception%20(by%20supplying%20a%20JWT%20lacking%20the%20'jti'%20claim)%20causes%20the%20API%20to%20return%20an%20HTTP%20500%20response%20containing%20the%20exception%20message%2C%20the%20source%20file%2C%20the%20line%20number%2C%20fully-qualified%20class%20and%20method%20names%2C%20and%20an%20internal%20call%20stack%20trace.%20This%20exposes%20internal%20implementation%20details%20to%20any%20unauthenticated%20caller%20who%20can%20induce%20an%20application%20error.%22%2C%22impact%22%3A%22An%20attacker%20can%20enumerate%20absolute%20filesystem%20paths%20(e.g.%2C%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2F...)%2C%20internal%20namespace%2Fclass%2Fmethod%20names%20(e.g.%2C%20BankOfEd%5C%5CServices%5C%5CAuthService%3A%3AisTokenRevoked)%2C%20and%20the%20application's%20call%20flow.%20This%20information%20reduces%20the%20effort%20required%20to%20map%20the%20application's%20internal%20structure%20and%20craft%20more%20targeted%20attacks.%20No%20secrets%2C%20credentials%2C%20or%20tokens%20are%20exposed%20in%20the%20observed%20response.%22%2C%22likelihood%22%3A%22Medium.%20The%20error%20is%20reachable%20by%20any%20unauthenticated%20caller%20who%20submits%20a%20malformed%20token%2C%20but%20exploitation%20yields%20only%20reconnaissance%20value%20rather%20than%20direct%20compromise%2C%20requiring%20further%20chaining%20to%20have%20real%20impact.%22%2C%22recommendation%22%3A%22Disable%20verbose%20error%20output%20in%20production.%20Return%20a%20generic%20error%20message%20(e.g.%2C%20%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INTERNAL_ERROR%5C%22%7D%7D)%20with%20no%20file%20paths%2C%20line%20numbers%2C%20class%20names%2C%20or%20stack%20traces.%20Log%20the%20full%20exception%20details%20server-side%20only.%20Additionally%2C%20validate%20the%20'jti'%20claim%20before%20passing%20it%20to%20AuthService%3A%3AisTokenRevoked()%20so%20that%20malformed%20tokens%20are%20rejected%20with%20a%20controlled%20401%20rather%20than%20triggering%20an%20unhandled%20type%20error.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2F192.168.3.101%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22GET%20%2Fapi%2Fprofile%20with%20a%20JWT%20lacking%20a%20'jti'%20claim%20returned%20HTTP%20500%20with%20a%20JSON%20body%20disclosing%20the%20exception%20message%2C%20file%20(%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FServices%2FAuthService.php)%2C%20line%2077%2C%20and%20a%20call%20stack%3A%20%5C%22trace%5C%22%3A%5C%22%230%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FMiddleware%2FAuthMiddleware.php(28)%3A%20BankOfEd%5C%5C%5C%5CServices%5C%5C%5C%5CAuthService%3A%3AisTokenRevoked()...%20%232%20%2Fvar%2Fwww%2Fbankofed%2Fpublic%2Findex.php(26)...%5C%22%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%5C%22trace%5C%22%3A%5C%22%230%20%2Fvar%2Fwww%2Fbankofed%2Fsrc%2FMiddleware%2FAuthMiddleware.php(28)%3A%20BankOfEd%5C%5C%5C%5CServices%5C%5C%5C%5CAuthService%3A%3AisTokenRevoked()...%5C%22%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Adversarial%20validator%20exhausted%20the%20step%20budget%20without%20finding%20a%20disproof.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%5D
-->

## 1. Default admin credentials accepted

- Severity: critical
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/health
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
POST /api/admin/auth/login with username admin / password admin123 returned 200 with a valid admin token.

### Impact
Full administrative access to the banking admin panel using guessable default credentials, enabling customer data access and account manipulation.

### Likelihood
Confirmed — login succeeded with default credentials.

### Recommendation
Remove/rotate default admin credentials, enforce strong unique passwords, add MFA and rate limiting on admin login.

### Evidence
```
POST /api/admin/auth/login {username:admin,password:admin123} returned 200 {"admin":{"id":1,"username":"admin"},"token":...}.

REQUEST:
GET http://192.168.3.101/api/health
use_session: (default)  Cookies: none
{"Origin": "https://evil.example"}

RESPONSE:
Status: 200
date: Tue, 14 Jul 2026 13:17:02 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 280
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"status":"ok","php_version":"8.3.31","server":"Apache\/2.4.58 (Ubuntu)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"bankofed_app","jwt_secret":"u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw","environment":"production"},"message":"OK"}
```

### Request Evidence
```
GET http://192.168.3.101/api/health
use_session: (default)  Cookies: none
{"Origin": "https://evil.example"}
```

### Response Evidence
```
Status: 200
date: Tue, 14 Jul 2026 13:17:02 GMT
server: Apache/2.4.58 (Ubuntu)
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 280
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"status":"ok","php_version":"8.3.31","server":"Apache\/2.4.58 (Ubuntu)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"bankofed_app","jwt_secret":"u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw","environment":"production"},"message":"OK"}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 2. Full-Read Server-Side Request Forgery (SSRF) in Avatar URL Fetch with Private-IP Filter Bypass

- Severity: critical
- OWASP: API7:2023 Server Side Request Forgery
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile/avatar
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:N/A:H)

### Description
The avatar endpoint at POST /api/profile/avatar accepts a user-supplied URL in the JSON body and causes the server to fetch that URL, returning the full response body base64-encoded in the avatar_data field. The endpoint is reachable by any authenticated user, and account registration is open and self-service via /api/auth/register. The fetch logic does not restrict schemes, hosts, or IP ranges, and any private/reserved-IP filtering that may exist is trivially bypassed using hexadecimal IP notation. Because the fetched response body is reflected back to the caller, this is a full-read (not blind) SSRF.

### Impact
An authenticated attacker can coerce the server into issuing arbitrary HTTP requests to internal and external hosts and read the full response. This was demonstrated by retrieving the internal 'The Bank of Ed' application served on 127.0.0.1:80, which is not intended to be externally reachable. Such access enables enumeration and reading of loopback and internal-network services, admin panels, and other resources that trust the application server's network position. It also creates exposure to cloud metadata credential theft (e.g., 169.254.169.254 / Azure IMDS / metadata.google.internal) where such an endpoint is reachable from the host.

### Likelihood
High. Registration is open with no approval step, no CSRF token or second factor is required, and exploitation is a single authenticated JSON POST. Observed behavior confirms no effective filtering blocks loopback or hex-encoded IPs.

### Recommendation
Do not pass user-supplied URLs directly to HTTP clients or file_get_contents. Enforce a scheme allowlist (only https) and, where possible, a host allowlist. Resolve DNS first, then validate the resolved IP against blocklists for private/reserved/link-local ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, ::1, fc00::/7), re-validating on each connection to defeat DNS rebinding. Canonicalize the host to defeat hex/octal/decimal/short-form and userinfo (e.g., evil.com@127.0.0.1) bypasses. Disable or restrict redirect following to prevent redirect-based pivots to internal targets. Consider routing outbound fetches through an egress proxy that blocks metadata endpoints. Finally, validate that the fetched content-type is an image and store only the resulting image rather than arbitrary content.

### Evidence
```
Authenticated (JWT from /api/auth/register) POST /api/profile/avatar with {"url":"https://example.com"} returned HTTP 200 with avatar_data base64 decoding to the 'Example Domain' page and source_url:"https://example.com", proving arbitrary external fetch with reflected content. Differential internal probing: {"url":"http://127.0.0.1:1/"} (dead port) returned HTTP 400 {"code":"FETCH_FAILED"}, while {"url":"http://127.0.0.1:80/"} (live) returned HTTP 200 with a 39308-char body decoding to the internal 'The Bank of Ed' application HTML. Filter bypass: {"url":"http://0x7f000001:80/"} (hex-encoded 127.0.0.1) returned HTTP 200 with the same internal Bank of Ed HTML, demonstrating no effective private-IP filtering.
```

### Request Evidence
```
POST /api/profile/avatar HTTP/1.1
Host: 192.168.3.101
Authorization: Bearer [REDACTED_BEARER] (valid JWT from /api/auth/register)
Content-Type: application/json

{"url":"http://127.0.0.1:80/"}
```

### Response Evidence
```
HTTP 200 {"success":true,"data":{"avatar_data":"data:text/html;base64,PCFET0NUWVBFIGh0bWw+...VGhlIEJhbmsgb2YgRWQ...","size":...,"source_url":"http://127.0.0.1:80/"},"message":"OK"}

Canary case (https://example.com): base64 decodes to "<h1>Example Domain</h1><p>This domain is for use in documentation examples without needing permission..."
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 3. JWT Signature Not Verified — Forged Token Enables Full Account Impersonation

- Severity: critical
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The token validation routine (AuthService::decodeToken) at the /api/profile endpoint decodes the JWT payload and only checks the exp and jti claims. It never verifies the HMAC signature or the token algorithm. As a result, a JWT bearing an arbitrary/invalid signature but containing a valid future exp, any jti, and an attacker-chosen sub is accepted as authentic, authorizing the request as whatever user ID is placed in the sub claim.

### Impact
An unauthenticated attacker can forge a token asserting any user ID (e.g., sub=1) and be fully authenticated as that user, resulting in complete authentication bypass and account takeover of any customer or administrator across the application. In the observed case the response returned user 1's full profile, including their email and bcrypt password hash.

### Likelihood
high

### Recommendation
Verify the JWT signature and algorithm using a vetted library before trusting any claims: enforce an allowlist of expected algorithms (e.g., HS256), reject alg=none and algorithm-substitution attempts, and validate the HMAC signature against the server secret. Only after signature/algorithm verification succeeds should exp, jti, sub, and other claims be evaluated. Additionally, ensure sensitive fields such as password_hash are never returned in profile responses.

### Evidence
```
A JWT with claims {"exp":4102444800,"sub":1,"jti":"forged-user1"} signed with an incorrect secret ("wrong-secret-signature-bypass-test") was submitted as a Bearer token to GET /api/profile. The server responded HTTP 200 and returned user 1's full profile: {"id":1,"email":"amelia.chen@example.com",...,"password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye..."}, confirming the signature was never validated.
```

### Request Evidence
```
GET /api/profile Authorization: Bearer <token with invalid signature, sub=1, jti set>
```

### Response Evidence
```
{"success":true,"data":{"id":1,"email":"amelia.chen@example.com",...}}
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 4. Unauthenticated /api/health endpoint discloses JWT signing secret and database configuration

- Severity: critical
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/health
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N)

### Description
The publicly accessible /api/health endpoint at http://192.168.3.101/api/health returns, without any authentication, the application's JWT HMAC signing secret along with internal database connection details (host, database name, and database user) and the running environment (production). Because the JWT signing secret is a high-entropy credential used to sign authentication tokens, its disclosure allows an attacker to forge validly-signed JWTs for arbitrary user identities.

### Impact
An attacker in possession of the leaked JWT signing secret can mint validly-signed tokens for any user, including administrators, resulting in complete authentication bypass and account takeover. The disclosed database host, name, and user further assist follow-on attacks against the backend datastore.

### Likelihood
High. The endpoint is reachable over the network with no authentication and returns the secret directly in the HTTP 200 response body, making exploitation trivial and repeatable.

### Recommendation
Remove all secrets and internal configuration from the health endpoint; health checks should return only a minimal status indicator. Immediately rotate the exposed JWT signing secret and the database credentials, and invalidate any tokens signed with the compromised secret. Review other endpoints for similar unintended disclosure.

### Evidence
```
GET /api/health returned HTTP 200 with no authentication headers. Response body included: {"success":true,"data":{"status":"ok","php_version":"8.3.31","server":"Apache/2.4.58 (Ubuntu)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"bankofed_app","jwt_secret":"u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw","environment":"production"},"message":"OK"} — exposing the JWT signing secret and database configuration.
```

### Response Evidence
```
jwt_secret":"u8CX2709PakoFlIGDxrtHK3CAiuMURdVfp6aPVsiecFxPfyLtU9ku7eOw","environment":"production"
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 5. Unauthenticated Admin User Export Exposes Password Hashes, TOTP Secrets, and PII

- Severity: critical
- OWASP: A01
- Source: A.L.I.C.E
- Validation: validating
- Affected URL: http://192.168.3.101/api/admin/export/users
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
The GET /api/admin/export/users endpoint at http://192.168.3.101/ returns the complete user directory without requiring any authentication or admin role. The response includes credential material (password_hash, totp_secret) and personally identifiable information (email, physical address, phone number) for every user. Any anonymous, unauthenticated caller can retrieve the entire user database.

### Impact
An attacker can obtain every user's password hashes and TOTP seeds, enabling offline password cracking and 2FA bypass, which together facilitate mass account takeover. The exposed PII (emails, addresses, phone numbers) additionally supports phishing, fraud, and privacy violations.

### Likelihood
High. The endpoint is reachable directly over the network with no cookies, session, or Authorization header. Both the deterministic authorization matrix and direct unauthenticated requests confirmed successful retrieval of sensitive fields, requiring no special conditions or user interaction.

### Recommendation
Enforce authentication and an explicit admin role/authorization check on /api/admin/export/users before returning any data. Remove credential material (password_hash, totp_secret) from all API serialization so it is never included in responses under any circumstance. Review other administrative and export endpoints for the same missing access control.

### Evidence
```
GET /api/admin/export/users returned HTTP 200 (content-type: application/json) with no authentication (no cookies, no Authorization header). The response contained all users' full records, including bcrypt/MD5 password_hash values, TOTP secrets, emails, physical addresses, and phone numbers. Both the deterministic auth matrix and direct unauthenticated requests received 200 responses containing these sensitive fields.
```

### Validation Note
Validation running.

## 6. IDOR: External Transfer Debits Any Customer's Account (from_account_id Not Ownership-Checked)

- Severity: critical
- OWASP: A01
- Source: Dynamic
- Validation: unconfirmed
- Affected URL: http://192.168.3.101/api/transfers/external
- CVSS: 9.3 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H)

### Description
The POST /api/transfers/external endpoint resolves the source account solely from the attacker-supplied from_account_id parameter (via Account::findById) without verifying that the account belongs to the authenticated user. As a result, an authenticated user can specify any account ID as the source of an external funds transfer, regardless of ownership. This is a broken object-level authorization (IDOR) flaw on a money-movement operation.

### Impact
An authenticated attacker can debit funds from any customer's account and send them to an arbitrary external destination (BSB and account number), enabling full theft of funds from arbitrary accounts. In the observed test, a transfer drove the victim account balance to -992788.50, demonstrating that the debit is applied with no ownership or balance restriction.

### Likelihood
High. Exploitation requires only an authenticated session and knowledge (or enumeration) of a target account_id, which are sequential integers. The attack was reproduced directly against the live endpoint with a single request and required no special conditions.

### Recommendation
Resolve the source account using a user-scoped query (e.g., Account::findByIdForUser) that binds the lookup to the authenticated user's ID, and reject any request where from_account_id is not owned by the authenticated user with an authorization error. Apply the same ownership enforcement consistently across all account-referencing transfer and transaction endpoints, and add server-side balance/limit validation.

### Evidence
```
Authenticated as user 1 (owns accounts 1,2,3). POST /api/transfers/external with {"from_account_id":4,"amount":999999,"to_bsb":"063-100","to_account_number":"44556677","transfer_type":"manual"} returned HTTP 201: {"transaction_id":36,"from_account_id":4,...,"new_from_balance":"-992788.50","status":"completed"}. Account 4 belongs to user 2 per the data export, confirming an unauthorized cross-user debit.
```

### Request Evidence
```
POST /api/transfers/external {"from_account_id":4,"amount":999999,...} (Bearer forged user1)
```

### Response Evidence
```
{"transaction_id":36,"from_account_id":4,...,"new_from_balance":"-992788.50","status":"completed"}
```

### Validation Note
The crawl did not record a user that could access this page, so there is no access-control baseline to compare against.

## 7. External Transfer Missing Balance Validation Allows Unlimited Overdraft

- Severity: high
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/transfers/external
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N)

### Description
The external transfer endpoint (POST /api/transfers/external) validates only that the requested amount is positive. It does not verify that the debit amount does not exceed the source account's available balance before completing the transaction. As a result, a transfer far larger than the available funds is accepted and the source account is driven into a large negative balance.

### Impact
An authenticated attacker can transfer amounts vastly exceeding the funds actually held in a source account, causing direct financial loss and negative account balances. If combined with the separately reported source-account IDOR, this weakness could be leveraged against accounts the attacker does not own, enabling large-scale fraud.

### Likelihood
High. The flaw was demonstrated with a single POST request requiring no special conditions beyond authenticated access; the server accepted the oversized debit and returned a completed status.

### Recommendation
Enforce a sufficient-funds check before debiting the source account, applying any account-type and overdraft-limit rules. Perform this validation atomically within the same database transaction that records the debit to prevent race conditions, and reject transfers that would exceed the permitted balance.

### Evidence
```
A POST to /api/transfers/external with {"from_account_id":4,"amount":999999,...} against account 4 (balance 7210.50) returned HTTP 201 with "new_from_balance":"-992788.50" and "status":"completed", confirming the debit was accepted despite far exceeding the available balance.
```

### Request Evidence
```
POST /api/transfers/external {"amount":999999,"from_account_id":4,...}
```

### Response Evidence
```
"new_from_balance":"-992788.50","status":"completed"
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 8. Server-Side TOTP Step-Up Enforcement Bypassed on External Transfers

- Severity: high
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/transfers/external
- CVSS: 7.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N)

### Description
The external transfer endpoint (/api/transfers/external) fails to enforce the step-up TOTP requirement returned by /api/transfers/check for manual transfers. When /api/transfers/check reports requires_totp=true for a manual transfer, the transfer can still be completed by submitting the transfer request with no totp_code. The MFA gate is evaluated client-side only and is not enforced server-side, allowing users with TOTP disabled (totp_configured=false) or any request omitting the code to proceed unauthenticated by MFA.

### Impact
An attacker or account holder can execute high-risk manual external transfers without satisfying the intended step-up MFA control. This undermines transaction authorization for exactly the operations the control is designed to protect, enabling fraudulent or unauthorized fund movement without a valid TOTP.

### Likelihood
high

### Recommendation
Enforce the TOTP requirement server-side on /api/transfers/external. Whenever checkTotpRequired (or equivalent logic) determines required=true, the transfer handler must reject requests that lack a valid, freshly verified TOTP code, and must reject transfers from users who have no TOTP configured rather than defaulting to completion. Do not rely on the client to honor the requires_totp response from /api/transfers/check.

### Evidence
```
POST /api/transfers/check {transfer_type:"manual"} returned {"requires_totp":true,"reason":"manual_entry","totp_configured":false}. A subsequent POST /api/transfers/external for a manual transfer with no totp_code returned 201 {"status":"completed","totp_verified":false}, confirming the declared TOTP requirement was not enforced server-side.
```

### Request Evidence
```
POST /api/transfers/external {transfer_type:"manual"} with no totp_code
```

### Response Evidence
```
check: "requires_totp":true; transfer: "status":"completed","totp_verified":false
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 9. SQL Injection in Admin Customer Search Parameter (/api/admin/customers)

- Severity: high
- OWASP: A03
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/admin/customers?search=x
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H)

### Description
The `search` query parameter on the admin customer search endpoint (`/api/admin/customers`) is concatenated directly into a LIKE-based WHERE clause and executed via PDO::query() without bound parameters. This is confirmed in AdminUserController.php line 28, where the unparameterized query construction allows attacker-controlled input to break out of the intended SQL context. Exploitation requires an admin-authenticated caller (Bearer token).

### Impact
An authenticated admin caller (or an attacker who has obtained admin access through credential compromise or auth weaknesses) can inject arbitrary SQL, enabling UNION-based and subquery data extraction, and potentially modification of arbitrary database records. Given this is a banking application, this could expose customer PII, account details, and transaction data.

### Likelihood
Medium. Exploitation is confirmed reachable but gated behind admin authentication (PR:H). The MySQL syntax error reflected from a single-quote payload demonstrates the input reaches the SQL parser unescaped, making injection straightforward for any actor with admin-level access.

### Recommendation
Replace the concatenated query with a parameterized/prepared statement that binds the LIKE value as a bound parameter (e.g., PDO::prepare with a placeholder and bound value such as '%' . $search . '%'). Never concatenate user-controlled input into SQL. Additionally, disable verbose database error output in production responses.

### Evidence
```
GET /api/admin/customers?search=x' (with admin Bearer token) returned HTTP 500 with a MySQL error: "SQLSTATE[42000]: ...1064... near '%' OR last_name LIKE '%x'%' OR email LIKE '%x'%'' at line 1" originating at /var/www/bankofed/src/Controllers/AdminUserController.php line 28 via PDO->query(). The reflected query fragment shows the single quote terminating the string literal, confirming unparameterized concatenation of the search parameter into the SQL statement.
```

### Request Evidence
```
GET /api/admin/customers?search=x' (Bearer admin)
```

### Response Evidence
```
1064 ... near '%' OR last_name LIKE '%x'%' OR email LIKE '%x'%'' at AdminUserController.php:28 PDO->query()
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 10. SQL Injection via ORDER BY sort parameter in /api/transactions

- Severity: high
- OWASP: A03
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/transactions?sort=id
- CVSS: 8.6 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N)

### Description
The GET /api/transactions endpoint interpolates the user-controlled 'sort' query parameter directly into the ORDER BY clause of a MySQL query without validation or parameterization. The vulnerable code path is in /var/www/bankofed/src/Models/Transaction.php (line 55), where the sort value is placed into the ORDER BY fragment. Because ORDER BY identifiers cannot be safely bound as query parameters, the injected value alters the SQL statement structure directly.

### Impact
An authenticated attacker (including one using the forged-JWT path observed during testing) can manipulate query structure via ORDER BY injection. This can be leveraged for data extraction from the transactions table using subquery-based or error-based techniques, potentially exposing financial records across users.

### Likelihood
High. The injection point is reachable by any authenticated caller, and the observed HTTP 500 MySQL syntax error confirms that unsanitized input breaks out of the ORDER BY clause. Error-based feedback is directly returned, materially simplifying exploitation.

### Recommendation
Never interpolate user input into SQL. Validate the 'sort' parameter against a strict allowlist of permitted column names and map sort keys to fixed, server-side column identifiers. Reject any value not in the allowlist. Additionally, suppress verbose database errors in production responses.

### Evidence
```
GET /api/transactions?sort=id` (with a trailing backtick) returned HTTP 500 with a MySQL error: "SQLSTATE[42000]: Syntax error or access violation: 1064 You have an error in your SQL syntax; ... near '` DESC LIMIT ? OFFSET ?' at line 4" originating at /var/www/bankofed/src/Models/Transaction.php line 55. The backtick-terminated value appearing inside the '` DESC LIMIT ? OFFSET ?' fragment confirms the sort input is placed directly into the ORDER BY clause.
```

### Request Evidence
```
GET /api/transactions?sort=id` (Bearer forged user1)
```

### Response Evidence
```
SQLSTATE[42000]: ... 1064 You have an error in your SQL syntax ... near '` DESC ...' at /var/www/bankofed/src/Models/Transaction.php
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 11. Broken Object Level Authorization in PUT /api/profile Allows Modification of Arbitrary User Profiles

- Severity: high
- OWASP: A01
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N)

### Description
The PUT /api/profile endpoint determines the record to update from a client-supplied user_id field in the JSON request body rather than from the authenticated session or token. The server does not verify that this user_id matches the authenticated user, so any authenticated user can update the profile attributes (phone, email, address) of any other user by specifying their ID.

### Impact
An authenticated attacker can overwrite arbitrary users' contact details, including email addresses. Changing a victim's email can enable full account takeover via a subsequent password-reset flow, and arbitrary modification of profile data constitutes PII tampering across all accounts.

### Likelihood
High. Exploitation requires only a single authenticated request with a modified user_id in the body. This was confirmed in the observed context: authenticated as user 1, the tester modified user 2's record.

### Recommendation
Ignore any client-supplied user_id in the request body. Always resolve the update target from the authenticated user's identity (session/token). Additionally, enforce server-side object-level authorization checks on all profile-modifying operations.

### Evidence
```
Authenticated as user 1, sent PUT /api/profile with body {"phone":"0400000BOLA","user_id":2}. The server responded HTTP 200 and returned user 2's record reflecting the injected value: {"id":2,"email":"wei.zhang@example.com",...,"phone":"0400000BOLA",...,"message":"Profile updated successfully"}, confirming a different user's profile was modified.
```

### Request Evidence
```
PUT /api/profile {"phone":"0400000BOLA","user_id":2}
```

### Response Evidence
```
{"id":2,"email":"wei.zhang@example.com",...,"phone":"0400000BOLA",...}
```

### Validation Note
Validation could not reproduce unauthorized access. Alternate users received an access denial, login response, generic SPA shell, or no protected content signal.

## 12. Passwords Stored as Unsalted MD5 and Disclosed in API Responses

- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/auth/register
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
The registration endpoint at http://192.168.3.101/api/auth/register stores user passwords using unsalted MD5, a fast cryptographic hash unsuitable for password storage. Registering a user with the password "a" returned a 201 response containing password_hash "e7133e3cff94e11c1d48bf8c715660b3", which is the exact MD5 digest of "a". This confirms both a weak hashing scheme and the disclosure of the stored password hash in the API response body. The same hash is additionally exposed via the export endpoint.

### Impact
Unsalted MD5 hashes can be cracked at billions of guesses per second and are trivially reversible for common or short passwords. Because the hashes are directly disclosed in registration responses and via the export endpoint, an attacker can harvest hashes and perform offline cracking at scale, enabling mass credential recovery and password reuse attacks against other services.

### Likelihood
high

### Recommendation
Replace MD5 with a password-adaptive, salted hashing algorithm such as bcrypt, scrypt, or Argon2 with appropriate work factors. Migrate existing hashes on next login. Never include password_hash in API responses or export outputs.

### Evidence
```
POST /api/auth/register with password "a" returned 201 with body containing "password_hash":"e7133e3cff94e11c1d48bf8c715660b3". This 32-hex value equals md5("a"), confirming unsalted MD5 storage and hash disclosure in the response.
```

### Request Evidence
```
POST /api/auth/register {"password":"a",...}
```

### Response Evidence
```
"password_hash":"e7133e3cff94e11c1d48bf8c715660b3"
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 13. Sensitive credential material (password hash and TOTP secret) exposed in /api/profile response

- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The GET /api/profile endpoint (backed by User::toPublic) serializes the fields password_hash and totp_secret directly into its JSON response. Any authenticated caller presenting a bearer token receives the account's stored bcrypt password hash and TOTP secret. Observed against http://192.168.3.101/api/profile, the response for user amelia.chen@example.com included the full password_hash value; the totp_secret field was present in the serialization (null for this account because MFA was not enabled).

### Impact
Exposure of the bcrypt password hash enables offline password cracking against affected accounts. Exposure of the TOTP secret, where MFA is enabled, allows an attacker to generate valid one-time codes and defeat the second factor. Because these secrets are returned to any bearer-token holder, an attacker who can obtain or forge tokens could harvest this material for multiple users.

### Likelihood
high

### Recommendation
Remove password_hash and totp_secret from all API serializations. Replace ad-hoc serialization with a strict output allowlist that returns only fields intended for client consumption. Audit User::toPublic and any similar serializers to ensure no secret or credential material is ever emitted.

### Evidence
```
GET /api/profile returned a JSON body including "password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi" and "totp_secret":null for user amelia.chen@example.com, confirming credential fields are serialized in the response.
```

### Response Evidence
```
"password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye...","totp_secret":null
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 14. Stored Cross-Site Scripting via Transfer Description Field

- Severity: medium
- OWASP: A03
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/transfers/external
- CVSS: 6.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N)

### Description
The transfer description field accepted by POST /api/transfers/external does not perform input validation or output encoding. User-supplied HTML/JavaScript is persisted verbatim and returned unescaped by the transaction APIs (e.g., GET /api/transactions/{id}). The front-end transaction renderers insert the raw value into the DOM via innerHTML without escaping — dashboard.js (line 76, container.innerHTML = html) and accounts.js ('<td>' + (tx.description || '—') + '</td>') — causing any stored script to execute when a transaction list is rendered. Because a transfer targeting another customer's account appears in that customer's transaction views, the payload executes in a victim's browser context, making this a stored, cross-user XSS.

### Impact
An attacker can initiate a transfer to a victim's account with a scripted description. When the victim (or an administrator reviewing transactions) loads their transaction list, the attacker-controlled JavaScript executes in their authenticated session. This enables theft of session tokens stored in localStorage (bankofed_token, bankofed_admin_token), unauthorized account actions performed as the victim, and potential compromise of the admin panel.

### Likelihood
medium

### Recommendation
HTML-escape all user-supplied fields — especially the transfer description — before inserting them into the DOM. Prefer textContent over innerHTML, or use a vetted escaping/sanitization helper when HTML rendering is required. Additionally enforce server-side input validation and contextual output encoding on the transfer and transaction APIs, and consider a restrictive Content-Security-Policy as defense in depth.

### Evidence
```
POST /api/transfers/external with description "<img src=x onerror=alert(document.domain)>" returned 201, storing the payload verbatim (transaction_id 37, to_account_id 4 = user 2's account). GET /api/transactions/37 returned "description":"<img src=x onerror=alert(document.domain)>" unescaped. The fetched dashboard.js renders transaction descriptions via innerHTML without escaping.
```

### Request Evidence
```
POST /api/transfers/external {"description":"<img src=x onerror=alert(document.domain)>","from_account_id":1,"to_account_number":"20000001","to_bsb":"062-002","transfer_type":"manual","amount":1}
```

### Response Evidence
```
GET /api/transactions/37 → "description":"<img src=x onerror=alert(document.domain)>"
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 15. Weak Password Policy: Single-Character Passwords Accepted at Registration

- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/auth/register
- CVSS: 4.3 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The registration endpoint at /api/auth/register does not enforce any minimum password length or complexity requirements. A registration request submitting a single-character password ("a") was accepted and resulted in the successful creation of a new account (id 17). This indicates the absence of server-side password strength validation.

### Impact
Users (and attackers) can create accounts protected by trivially weak passwords, substantially lowering the effort required for successful credential guessing, brute-force, and credential-stuffing attacks against the application's authentication surface.

### Likelihood
Medium. The weakness is trivially reproducible via a single unauthenticated API request, but actual account compromise still depends on targeting accounts that use weak passwords and on the presence (or absence) of rate limiting and lockout controls.

### Recommendation
Enforce a server-side password policy at registration and password-change endpoints: require a minimum length of at least 12 characters, and validate submitted passwords against a known-breached-password list (e.g., HaveIBeenPwned range API) rather than relying solely on composition rules. Reject weak passwords with a clear error, and apply the same policy consistently across all account-creation and password-update flows.

### Evidence
```
POST /api/auth/register with {"password":"a"} returned HTTP 201 and created account id 17 with response {"success":true,...,"message":"Registration successful"}, confirming that no minimum length or complexity requirement is enforced.
```

### Request Evidence
```
POST /api/auth/register {"password":"a","email":"aespa_4789e528@example.invalid",...}
```

### Response Evidence
```
{"success":true,...,"message":"Registration successful"} (id 17)
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 16. Broken Object Level Authorization in GET /api/transactions/{id} Exposes Other Customers' Transaction Details

- Severity: medium
- OWASP: A01
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://192.168.3.101/api/transactions/10
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The GET /api/transactions/{id} endpoint looks up a transaction solely by its path ID and returns it without verifying that the authenticated caller owns the associated account. An authenticated user can enumerate sequential transaction IDs to retrieve transactions belonging to other customers. Authenticated as user 1 (who owns accounts 1, 2, and 3), a request to GET /api/transactions/10 returned a transaction tied to account 9, which does not belong to user 1.

### Impact
An authenticated attacker can enumerate transaction IDs to read arbitrary customers' financial records, disclosing transfer amounts, descriptions, and destination BSB/account numbers. This constitutes sensitive financial data leakage across customer boundaries.

### Likelihood
High. Transaction IDs are sequential and predictable, the endpoint requires only a valid authenticated session, and no ownership check is performed, making mass enumeration straightforward.

### Recommendation
Enforce object-level authorization on the endpoint: before returning a transaction, verify that its from_account_id (or otherwise associated account) belongs to the authenticated user. Reject unauthorized requests with HTTP 403/404. Apply the same ownership check consistently across all object-scoped endpoints.

### Evidence
```
Authenticated as user 1 (owns accounts 1,2,3 per export). GET /api/transactions/10 returned HTTP 200: {"id":10,"from_account_id":9,"to_bsb":"063-100","to_account_number":"44556677","amount":"400.00","description":"Mum allowance",...}. Account 9 does not belong to user 1, confirming cross-customer access.
```

### Request Evidence
```
GET /api/transactions/10 (Bearer forged user1)
```

### Response Evidence
```
{"id":10,"from_account_id":9,...,"description":"Mum allowance"}
```

### Validation Note
Validation could not reproduce unauthorized access. Alternate users received an access denial, login response, generic SPA shell, or no protected content signal.

## 17. Missing Rate-Limiting and Account Lockout on Login Endpoint

- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/auth/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L)

### Description
The authentication endpoint at /api/auth/login does not enforce any rate-limiting, account lockout, progressive delay, or CAPTCHA. Six consecutive failed authentication attempts against a valid account (amelia.chen@example.com) each returned an identical HTTP 401 response, with no throttling, no 429 Too Many Requests, and no lockout introduced even at the sixth attempt.

### Impact
The absence of anti-automation controls allows an attacker to submit high volumes of authentication attempts against known or guessed accounts, enabling credential-stuffing and brute-force attacks without impediment. The risk is compounded where password hashing and password-policy weaknesses reduce the effort required to recover valid credentials.

### Likelihood
medium

### Recommendation
Implement server-side rate-limiting on the login endpoint (per-IP and per-account), account lockout or exponential backoff after a threshold of failed attempts, and CAPTCHA or step-up verification on repeated failures. Add monitoring and alerting for anomalous authentication failure patterns to detect credential-stuffing campaigns.

### Evidence
```
6 consecutive POST /api/auth/login requests for amelia.chen@example.com with incorrect passwords (wrong1..wrong6) each returned HTTP 401 with no throttling, delay, lockout, or 429 introduced by attempt #6.
```

### Request Evidence
```
POST /api/auth/login x6 {email:amelia.chen@example.com, password:wrong1..wrong6}
```

### Response Evidence
```
All 6 attempts: status 401, no 429/lockout
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 18. Permissive CORS: Arbitrary Origin Reflected with Credentials on Authenticated Profile API

- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The endpoint at http://192.168.3.101/api/profile reflects an attacker-controlled request Origin into the Access-Control-Allow-Origin response header while also setting Access-Control-Allow-Credentials: true (with Access-Control-Allow-Headers: * observed on prior responses). This configuration permits any external website to issue credentialed cross-origin requests to the authenticated API and read the responses in the victim's browser context.

### Impact
A victim who is authenticated to the application and visits an attacker-controlled page could have their browser make credentialed cross-origin requests to /api/profile, allowing the attacker's JavaScript to read the authenticated profile response. The observed response body includes sensitive data such as password_hash, so this misconfiguration could expose PII and credential material to a malicious origin.

### Likelihood
Medium. The misconfiguration is confirmed by direct request/response inspection: an arbitrary Origin is reflected and credentials are permitted. However, no in-browser proof-of-concept was captured demonstrating an actual cross-origin read, so practical exploitation depends on a victim being authenticated and lured to an attacker page.

### Recommendation
Do not reflect arbitrary Origins. Implement a strict allowlist of trusted origins and only emit Access-Control-Allow-Origin for exact matches. Never combine a wildcard or reflected Origin with Access-Control-Allow-Credentials: true. Additionally, avoid returning sensitive fields such as password_hash in API responses.

### Evidence
```
GET /api/profile with header Origin: https://evil.example returned access-control-allow-origin: https://evil.example and the authenticated profile body (including password_hash). Prior responses also showed access-control-allow-credentials: true and access-control-allow-headers: *.
```

### Request Evidence
```
GET /api/profile Origin: https://evil.example
```

### Response Evidence
```
access-control-allow-origin: https://evil.example (with ACAC:true observed)
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.

## 19. Verbose Error Handling Discloses Stack Traces and Filesystem Paths

- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://192.168.3.101/api/profile
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The global exception handler at http://192.168.3.101/api/profile returns detailed diagnostic information in its JSON error response when an unhandled application exception occurs. Triggering an exception (by supplying a JWT lacking the 'jti' claim) causes the API to return an HTTP 500 response containing the exception message, the source file, the line number, fully-qualified class and method names, and an internal call stack trace. This exposes internal implementation details to any unauthenticated caller who can induce an application error.

### Impact
An attacker can enumerate absolute filesystem paths (e.g., /var/www/bankofed/src/...), internal namespace/class/method names (e.g., BankOfEd\Services\AuthService::isTokenRevoked), and the application's call flow. This information reduces the effort required to map the application's internal structure and craft more targeted attacks. No secrets, credentials, or tokens are exposed in the observed response.

### Likelihood
Medium. The error is reachable by any unauthenticated caller who submits a malformed token, but exploitation yields only reconnaissance value rather than direct compromise, requiring further chaining to have real impact.

### Recommendation
Disable verbose error output in production. Return a generic error message (e.g., {"success":false,"error":{"code":"INTERNAL_ERROR"}}) with no file paths, line numbers, class names, or stack traces. Log the full exception details server-side only. Additionally, validate the 'jti' claim before passing it to AuthService::isTokenRevoked() so that malformed tokens are rejected with a controlled 401 rather than triggering an unhandled type error.

### Evidence
```
GET /api/profile with a JWT lacking a 'jti' claim returned HTTP 500 with a JSON body disclosing the exception message, file (/var/www/bankofed/src/Services/AuthService.php), line 77, and a call stack: "trace":"#0 /var/www/bankofed/src/Middleware/AuthMiddleware.php(28): BankOfEd\\Services\\AuthService::isTokenRevoked()... #2 /var/www/bankofed/public/index.php(26)..."
```

### Response Evidence
```
"trace":"#0 /var/www/bankofed/src/Middleware/AuthMiddleware.php(28): BankOfEd\\Services\\AuthService::isTokenRevoked()..."
```

### Validation Note
Adversarial validator exhausted the step budget without finding a disproof.
