# Issue Export: Run 2026-06-18 00:45

- Exported: 18/6/2026, 11:44:45 am
- Total findings: 13

<!-- aespa-findings-json
%5B%7B%22owasp_category%22%3A%22API2%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Hardcoded%20Weak%20JWT%20Secret%20Enables%20Arbitrary%20Token%20Forgery%22%2C%22description%22%3A%22The%20application's%20JWT%20signing%20secret%20is%20hardcoded%20as%20the%20trivially%20guessable%20string%20%60'random'%60%20in%20%60config.py%60.%20Because%20the%20secret%20is%20static%20and%20weak%2C%20an%20attacker%20can%20craft%20a%20valid%20JWT%20with%20arbitrary%20claims%20%E2%80%94%20including%20elevated%20privileges%20%E2%80%94%20and%20sign%20it%20locally%20without%20possessing%20any%20legitimate%20credentials.%20The%20forged%20token%20is%20accepted%20by%20all%20authenticated%20API%20endpoints.%22%2C%22impact%22%3A%22Complete%20authentication%20bypass.%20An%20attacker%20can%20impersonate%20any%20user%2C%20including%20administrators%2C%20by%20forging%20a%20JWT%20signed%20with%20the%20known%20secret.%20As%20demonstrated%2C%20a%20token%20carrying%20%60%7B%5C%22sub%5C%22%3A%20%5C%22admin%5C%22%7D%60%20was%20accepted%20by%20the%20API%2C%20returning%20the%20admin%20account's%20email%20address%20and%20confirming%20the%20%60admin%3A%20true%60%20flag%20%E2%80%94%20granting%20unrestricted%20access%20to%20all%20protected%20resources%20and%20data.%22%2C%22likelihood%22%3A%22High.%20The%20secret%20value%20%60'random'%60%20would%20be%20recovered%20almost%20instantly%20by%20dictionary%20or%20brute-force%20attack%20against%20any%20captured%20token%2C%20and%20is%20trivially%20known%20to%20anyone%20with%20access%20to%20the%20source%20code.%20No%20authentication%20material%20or%20special%20network%20position%20is%20required%20to%20exploit%20this.%22%2C%22recommendation%22%3A%221.%20Replace%20the%20hardcoded%20secret%20immediately%20with%20a%20cryptographically%20random%20value%20of%20at%20least%20256%20bits%20(e.g.%2C%20generated%20via%20%60secrets.token_hex(32)%60%20in%20Python).%202.%20Store%20the%20secret%20exclusively%20in%20an%20environment%20variable%20or%20a%20dedicated%20secrets%20manager%20%E2%80%94%20never%20in%20source%20code%20or%20version%20control.%203.%20Invalidate%20and%20rotate%20all%20currently%20issued%20tokens%20after%20the%20secret%20is%20changed.%204.%20Consider%20migrating%20to%20asymmetric%20signing%20(RS256%2FES256)%20so%20that%20the%20private%20signing%20key%20is%20never%20distributed%20to%20verifying%20services.%205.%20Enforce%20a%20minimum%20token%20expiry%20and%20validate%20the%20%60exp%60%20claim%20strictly%20to%20limit%20the%20window%20of%20any%20future%20token%20compromise.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Flogin%22%2C%22evidence%22%3A%22A%20JWT%20was%20forged%20locally%20using%20the%20secret%20%60'random'%60%20and%20the%20claims%20%60%7B%5C%22sub%5C%22%3A%20%5C%22admin%5C%22%2C%20%5C%22exp%5C%22%3A%209999999999%7D%60.%20When%20this%20token%20was%20submitted%20to%20%60GET%20%2Fme%60%2C%20the%20server%20returned%20HTTP%20200%20with%20%60%7B%5C%22data%5C%22%3A%20%7B%5C%22admin%5C%22%3A%20true%2C%20%5C%22email%5C%22%3A%20%5C%22admin%40mail.com%5C%22%2C%20%5C%22username%5C%22%3A%20%5C%22admin%5C%22%7D%2C%20%5C%22status%5C%22%3A%20%5C%22success%5C%22%7D%60%2C%20confirming%20full%20administrative%20access%20without%20any%20valid%20credentials.%22%2C%22request_evidence%22%3A%22GET%20%2Fme%20HTTP%2F1.1%5C%5CnAuthorization%3A%20Bearer%20%5Bforged_jwt_signed_with_secret_random%5D%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%20OK%5C%5Cn%7B%5C%22data%5C%22%3A%20%7B%5C%22admin%5C%22%3A%20true%2C%20%5C%22email%5C%22%3A%20%5C%22admin%40mail.com%5C%22%2C%20%5C%22username%5C%22%3A%20%5C%22admin%5C%22%7D%2C%20%5C%22status%5C%22%3A%20%5C%22success%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API3%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Mass%20Assignment%3A%20Unauthenticated%20User%20Can%20Self-Assign%20Admin%20Privileges%20at%20Registration%22%2C%22description%22%3A%22The%20POST%20%2Fusers%2Fv1%2Fregister%20endpoint%20accepts%20and%20honours%20an%20admin%20field%20in%20the%20JSON%20request%20body%20that%20should%20be%20a%20server-controlled%20read-only%20property.%20When%20submitted%20with%20value%20true%20the%20newly%20created%20account%20is%20granted%20full%20admin%20privileges.%20Any%20anonymous%20user%20can%20become%20an%20administrator%20in%20a%20single%20unauthenticated%20request.%22%2C%22impact%22%3A%22Complete%20privilege%20escalation%20to%20administrator%20with%20no%20prior%20authentication.%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Strip%20server-controlled%20fields%20such%20as%20admin%20and%20role%20from%20user-supplied%20registration%20input%20server-side.%22%2C%22cvss_score%22%3A9.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Fregister%22%2C%22evidence%22%3A%22POST%20%2Fusers%2Fv1%2Fregister%20with%20body%20%7Busername%3Aeviluser%2Cpassword%3Aevil123%2Cemail%3Aevil%40evil.com%2Cadmin%3Atrue%7D%20returns%20HTTP%20200%20and%20GET%20%2Fusers%2Fv1%2Feviluser%20confirms%20admin%3Atrue.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22alice_api%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22SQL%20Injection%20via%20Unsanitised%20Path%20Parameter%20in%20GET%20%2Fusers%2Fv1%2F%7Busername%7D%22%2C%22description%22%3A%22The%20%60GET%20%2Fusers%2Fv1%2F%7Busername%7D%60%20endpoint%20constructs%20its%20database%20query%20by%20interpolating%20the%20URL%20path%20parameter%20directly%20into%20a%20raw%20SQL%20string%3A%20%60f%5C%22SELECT%20*%20FROM%20users%20WHERE%20username%20%3D%20'%7Busername%7D'%5C%22%60.%20No%20parameterisation%2C%20escaping%2C%20or%20input%20validation%20is%20applied.%20Because%20the%20application%20also%20runs%20with%20Werkzeug%20debug%20mode%20enabled%2C%20SQL%20injection%20payloads%20that%20trigger%20errors%20cause%20the%20full%20Python%20stack%20trace%2C%20the%20raw%20SQL%20query%20string%2C%20and%20the%20Werkzeug%20interactive%20debugger%20PIN%20to%20be%20returned%20in%20the%20HTTP%20500%20response%20body.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20can%20read%2C%20modify%2C%20or%20delete%20arbitrary%20data%20in%20the%20underlying%20database.%20The%20UNION-based%20vector%20demonstrated%20during%20testing%20allows%20extraction%20of%20all%20usernames%20and%20password%20hashes%20in%20a%20single%20request.%20The%20exposed%20Werkzeug%20debugger%20PIN%20(%606ZIN4YOjkLHB44E3SJSp%60)%20additionally%20enables%20the%20attacker%20to%20execute%20arbitrary%20Python%20code%20on%20the%20server%20through%20the%20interactive%20debugger%20console%2C%20escalating%20the%20impact%20to%20full%20remote%20code%20execution%20and%20host%20compromise.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20no%20authentication%2C%20no%20special%20tooling%2C%20and%20no%20user%20interaction.%20Both%20an%20OR-based%20tautology%20injection%20and%20a%20UNION-based%20data-extraction%20payload%20were%20confirmed%20to%20work%20against%20the%20live%20endpoint%2C%20demonstrating%20trivial%2C%20reliable%20exploitability%20from%20the%20public%20network.%22%2C%22recommendation%22%3A%221.%20Replace%20all%20string-interpolated%20SQL%20with%20parameterised%20queries%20or%20ORM%20methods%20(e.g.%2C%20%60cursor.execute('SELECT%20*%20FROM%20users%20WHERE%20username%20%3D%20%3F'%2C%20(username%2C))%60)%20so%20user-supplied%20input%20is%20never%20treated%20as%20SQL%20syntax.%5Cn2.%20Disable%20Werkzeug%20debug%20mode%20in%20all%20non-development%20environments%20by%20setting%20%60DEBUG%3DFalse%60%20and%20ensuring%20the%20%60WERKZEUG_RUN_MAIN%60%20environment%20variable%20is%20not%20set%20in%20production.%5Cn3.%20Rotate%20or%20invalidate%20the%20exposed%20Werkzeug%20debugger%20PIN%20(%606ZIN4YOjkLHB44E3SJSp%60)%20immediately.%5Cn4.%20Implement%20strict%20input%20validation%20on%20the%20%60username%60%20path%20parameter%20(e.g.%2C%20allowlist%20of%20alphanumeric%20characters%20and%20limited%20punctuation).%5Cn5.%20Ensure%20application%20error%20responses%20return%20generic%20messages%20to%20clients%20and%20log%20detailed%20errors%20server-side%20only.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Fname1%22%2C%22evidence%22%3A%22Two%20injection%20payloads%20were%20confirmed%20against%20the%20live%20endpoint.%20(1)%20OR-based%20tautology%3A%20%60GET%20%2Fusers%2Fv1%2F'%20OR%20'1'%3D'1%60%20returned%20HTTP%20200%20with%20user%20record%20data%2C%20confirming%20the%20injection%20alters%20query%20logic.%20(2)%20UNION-based%20extraction%3A%20%60GET%20%2Fusers%2Fv1%2Fname1'%20UNION%20SELECT%20username%2Cpassword%20FROM%20users--%60%20returned%20HTTP%20500%20with%20a%20full%20Werkzeug%20debugger%20page%20that%20included%20the%20raw%20SQL%20string%20%60SELECT%20*%20FROM%20users%20WHERE%20username%20%3D%20'name1'%20UNION%20SELECT%20username%2Cpassword%20FROM%20users--'%60%2C%20a%20complete%20Python%20stack%20trace%2C%20and%20the%20Werkzeug%20debugger%20PIN%20%606ZIN4YOjkLHB44E3SJSp%60.%22%2C%22request_evidence%22%3A%22GET%20%2Fusers%2Fv1%2F'%20OR%20'1'%3D'1%20HTTP%2F1.1%20%E2%86%92%20HTTP%20200%20with%20user%20data%5C%5CnGET%20%2Fusers%2Fv1%2Fname1'%20UNION%20SELECT%20username%2Cpassword%20FROM%20users--%20%E2%86%92%20HTTP%20500%20with%20SQL%20in%20error%22%2C%22response_evidence%22%3A%22HTTP%20200%3A%20%7B%5C%22username%5C%22%3A%20%5C%22name1%5C%22%2C%20%5C%22email%5C%22%3A%20%5C%22mail1%40mail.com%5C%22%7D%20(OR%20injection)%5C%5CnHTTP%20500%3A%20Werkzeug%20debugger%20with%20SQL%3A%20SELECT%20*%20FROM%20users%20WHERE%20username%20%3D%20'name1'%20UNION%20SELECT%20username%2Cpassword%20FROM%20users--'%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API5%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unauthenticated%20%2Fcreatedb%20Endpoint%20Allows%20Full%20Database%20Wipe%20and%20Reset%22%2C%22description%22%3A%22The%20GET%20%2Fcreatedb%20endpoint%20drops%20and%20recreates%20the%20entire%20application%20database%20with%20no%20authentication%20or%20authorisation%20check.%20Any%20unauthenticated%20attacker%20can%20call%20it%20to%20instantly%20destroy%20all%20user%20and%20book%20data%20and%20reset%20the%20application%20to%20its%20default%20state%2C%20including%20resetting%20admin%20credentials%20to%20known%20defaults.%22%2C%22impact%22%3A%22Complete%20data%20destruction%20and%20service%20disruption.%20Resets%20admin%20password%20to%20a%20known%20default%2C%20enabling%20immediate%20account%20takeover%20of%20the%20administrator%20account.%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Remove%20or%20disable%20this%20endpoint%20entirely%20in%20any%20non-development%20environment.%20If%20required%20for%20ops%2C%20protect%20it%20behind%20strong%20authentication%20and%20restrict%20access%20by%20IP.%22%2C%22cvss_score%22%3A9.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fcreatedb%22%2C%22evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A5000%2Fcreatedb%20returns%20HTTP%20200%20with%20no%20authentication%20required.%20All%20user%20and%20book%20records%20are%20wiped%20and%20recreated%20with%20default%20values.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22alice_api%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API5%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unauthenticated%20Debug%20Endpoint%20Exposes%20Full%20User%20Credential%20Database%20in%20Plaintext%22%2C%22description%22%3A%22The%20API%20endpoint%20%60GET%20%2Fusers%2Fv1%2F_debug%60%20is%20accessible%20without%20any%20authentication%20or%20authorization%20and%20returns%20a%20complete%20dump%20of%20all%20user%20records.%20Each%20record%20includes%20the%20username%2C%20email%20address%2C%20plaintext%20password%2C%20and%20admin%20flag.%20No%20credentials%2C%20tokens%2C%20or%20session%20state%20are%20required%20to%20retrieve%20this%20data.%22%2C%22impact%22%3A%22Any%20unauthenticated%20attacker%20with%20network%20access%20to%20the%20application%20can%20retrieve%20every%20user's%20credentials%20in%20a%20single%20HTTP%20request.%20The%20exposed%20data%20includes%20plaintext%20passwords%20and%20admin%20account%20credentials%2C%20enabling%20immediate%20account%20takeover%20for%20all%20users%20%E2%80%94%20including%20administrative%20accounts%20%E2%80%94%20as%20well%20as%20credential-stuffing%20attacks%20against%20other%20services%20if%20passwords%20are%20reused.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20no%20skill%2C%20tooling%2C%20or%20prior%20knowledge%20beyond%20knowing%20the%20endpoint%20path.%20The%20endpoint%20responds%20with%20HTTP%20200%20and%20a%20full%20JSON%20payload%20to%20an%20anonymous%20GET%20request%2C%20making%20this%20trivially%20and%20reliably%20exploitable%20by%20any%20attacker%20who%20discovers%20or%20guesses%20the%20URL.%22%2C%22recommendation%22%3A%22Remove%20the%20debug%20endpoint%20entirely%20from%20the%20production%20codebase.%20If%20the%20endpoint%20must%20exist%20in%20non-production%20environments%2C%20restrict%20access%20to%20localhost%20or%20internal%20networks%20via%20network%20controls%2C%20require%20strong%20authentication%2C%20and%20ensure%20it%20is%20never%20deployed%20to%20production.%20Independently%20of%20this%20endpoint%2C%20passwords%20must%20never%20be%20stored%20or%20transmitted%20in%20plaintext%3B%20apply%20a%20strong%20adaptive%20hashing%20algorithm%20(e.g.%2C%20bcrypt%2C%20Argon2)%20for%20all%20stored%20credentials%20and%20audit%20all%20API%20responses%20to%20confirm%20that%20password%20fields%20are%20never%20serialised%20in%20any%20response.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2F_debug%22%2C%22evidence%22%3A%22An%20unauthenticated%20GET%20request%20to%20%2Fusers%2Fv1%2F_debug%20returned%20HTTP%20200%20with%20a%20full%20JSON%20dump%20of%20all%20user%20records%2C%20including%20plaintext%20passwords%20and%20admin%20flags.%20Three%20accounts%20were%20exposed%3A%20name1%20(mail1%40mail.com%2C%20password%3A%20pass1)%2C%20name2%20(mail2%40mail.com%2C%20password%3A%20pass2)%2C%20and%20the%20admin%20account%20(admin%40mail.com%2C%20password%3A%20pass1%2C%20admin%3A%20true).%22%2C%22request_evidence%22%3A%22GET%20%2Fusers%2Fv1%2F_debug%20HTTP%2F1.1%5C%5CnHost%3A%20localhost%3A5000%5C%5Cn(No%20Authorization%20header)%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%20OK%5C%5Cn%7B%5C%22users%5C%22%3A%20%5B%7B%5C%22admin%5C%22%3A%20false%2C%20%5C%22email%5C%22%3A%20%5C%22mail1%40mail.com%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22pass1%5C%22%2C%20%5C%22username%5C%22%3A%20%5C%22name1%5C%22%7D%2C%20%7B%5C%22admin%5C%22%3A%20true%2C%20%5C%22email%5C%22%3A%20%5C%22admin%40mail.com%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22pass1%5C%22%2C%20%5C%22username%5C%22%3A%20%5C%22admin%5C%22%7D%2C%20...%5D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API1%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22BOLA%3A%20Authenticated%20User%20Can%20Change%20Any%20Other%20User's%20Password%20via%20Unvalidated%20Path%20Parameter%22%2C%22description%22%3A%22The%20%60PUT%20%2Fusers%2Fv1%2F%7Busername%7D%2Fpassword%60%20endpoint%20identifies%20the%20target%20account%20using%20the%20%60username%60%20URL%20path%20parameter%20rather%20than%20the%20authenticated%20user's%20identity%20derived%20from%20the%20JWT%20token.%20No%20ownership%20or%20authorization%20check%20is%20performed%2C%20so%20any%20authenticated%20user%20can%20supply%20an%20arbitrary%20username%20in%20the%20path%20%E2%80%94%20including%20%60admin%60%20%E2%80%94%20to%20change%20that%20account's%20password.%22%2C%22impact%22%3A%22Any%20authenticated%20low-privileged%20user%20can%20take%20over%20any%20account%2C%20including%20the%20administrator%20account%2C%20by%20setting%20an%20arbitrary%20new%20password.%20This%20enables%20full%20privilege%20escalation%20and%20complete%20account%20takeover%20across%20the%20entire%20user%20base.%22%2C%22likelihood%22%3A%22High.%20Exploitation%20requires%20only%20a%20valid%20JWT%20for%20any%20account%20and%20knowledge%20of%20a%20target%20username.%20No%20elevated%20privileges%2C%20user%20interaction%2C%20or%20complex%20conditions%20are%20needed.%22%2C%22recommendation%22%3A%22Authorize%20password%20change%20requests%20by%20extracting%20the%20target%20user%20identity%20exclusively%20from%20the%20validated%20JWT%20claims%20(e.g.%2C%20%60sub%60)%2C%20never%20from%20a%20caller-supplied%20URL%20parameter.%20Additionally%2C%20enforce%20a%20server-side%20check%20that%20the%20requesting%20user%20is%20either%20the%20account%20owner%20or%20holds%20an%20administrative%20role%20before%20processing%20the%20change.%20Reject%20requests%20where%20the%20path%20parameter%20does%20not%20match%20the%20authenticated%20identity%20unless%20the%20caller%20is%20an%20admin.%22%2C%22cvss_score%22%3A8.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Fadmin%2Fpassword%22%2C%22evidence%22%3A%22A%20%60PUT%20%2Fusers%2Fv1%2Fadmin%2Fpassword%60%20request%20authenticated%20with%20a%20JWT%20belonging%20to%20the%20low-privileged%20user%20%60name1%60%20and%20a%20body%20of%20%60%7B%5C%22password%5C%22%3A%20%5C%22hacked123%5C%22%7D%60%20returned%20%60HTTP%20204%20No%20Content%60%2C%20indicating%20success.%20A%20subsequent%20%60GET%20%2Fusers%2Fv1%2F_debug%60%20confirmed%20that%20the%20admin%20account's%20password%20had%20been%20changed%20to%20%60hacked123%60%2C%20proving%20full%20account%20takeover%20without%20any%20administrative%20privilege.%22%2C%22request_evidence%22%3A%22PUT%20%2Fusers%2Fv1%2Fadmin%2Fpassword%20HTTP%2F1.1%5C%5CnAuthorization%3A%20Bearer%20%5Bname1_jwt%5D%5C%5CnContent-Type%3A%20application%2Fjson%5C%5Cn%5C%5Cn%7B%5C%22password%5C%22%3A%20%5C%22hacked123%5C%22%7D%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20204%20No%20Content%5C%5Cn(Admin%20password%20changed%20to%20%5C%22hacked123%5C%22%20confirmed%20via%20debug%20endpoint)%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API2%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Plaintext%20Password%20Storage%20and%20Exposure%22%2C%22description%22%3A%22User%20passwords%20are%20stored%20and%20compared%20in%20plaintext%20throughout%20the%20application.%20The%20login%20endpoint%20performs%20a%20direct%20string%20equality%20check%20against%20the%20stored%20plaintext%20value%20rather%20than%20comparing%20a%20salted%20hash.%20Passwords%20are%20also%20returned%20in%20plaintext%20via%20the%20unauthenticated%20debug%20endpoint%20and%20are%20directly%20extractable%20via%20the%20confirmed%20SQL%20injection%20vulnerability.%22%2C%22impact%22%3A%22Any%20attacker%20who%20gains%20read%20access%20to%20the%20database%20%E2%80%94%20via%20SQLi%2C%20the%20debug%20endpoint%2C%20or%20a%20backup%20%E2%80%94%20obtains%20all%20user%20passwords%20immediately%20with%20no%20cracking%20required.%20Passwords%20are%20likely%20reused%20across%20other%20services.%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Hash%20all%20passwords%20using%20bcrypt%2C%20scrypt%2C%20or%20Argon2%20with%20a%20per-user%20salt%20before%20storage.%20Never%20store%20or%20log%20plaintext%20passwords.%22%2C%22cvss_score%22%3A8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Flogin%22%2C%22evidence%22%3A%22GET%20%2Fusers%2Fv1%2F_debug%20returns%20all%20user%20records%20with%20plaintext%20password%20fields.%20SQL%20injection%20on%20GET%20%2Fusers%2Fv1%2F%7Busername%7D%20also%20returns%20plaintext%20password%20column%20values.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22alice_api%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API1%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22BOLA%3A%20Authenticated%20User%20Can%20Read%20Any%20Other%20User's%20Book%20Secret%20via%20Unvalidated%20Path%20Parameter%22%2C%22description%22%3A%22The%20%60GET%20%2Fbooks%2Fv1%2F%7Bbook_title%7D%60%20endpoint%20returns%20a%20book's%20secret%20content%20based%20solely%20on%20the%20book%20title%20supplied%20in%20the%20URL%20path.%20The%20API%20performs%20no%20ownership%20validation%20%E2%80%94%20it%20does%20not%20verify%20that%20the%20authenticated%20user's%20identity%20(as%20expressed%20in%20the%20JWT%20%60sub%60%20claim)%20matches%20the%20book's%20recorded%20owner%20before%20returning%20the%20%60secret%60%20field.%20As%20a%20result%2C%20any%20authenticated%20user%20can%20retrieve%20the%20secret%20content%20of%20any%20book%20by%20guessing%20or%20knowing%20its%20title.%22%2C%22impact%22%3A%22Any%20authenticated%20user%20can%20read%20the%20private%20secret%20content%20of%20books%20belonging%20to%20other%20users%2C%20including%20administrative%20accounts.%20Demonstrated%20evidence%20shows%20user%20%60name1%60%20successfully%20retrieved%20the%20secret%20for%20%60admin%60's%20book%20(%60bookTitle68%60)%20and%20%60name2%60's%20book%20(%60bookTitle59%60)%2C%20fully%20compromising%20the%20confidentiality%20of%20all%20book%20secrets%20stored%20in%20the%20application.%22%2C%22likelihood%22%3A%22High.%20Exploitation%20requires%20only%20a%20valid%20JWT%20and%20knowledge%20of%20a%20target%20book%20title.%20Book%20titles%20appear%20to%20follow%20a%20predictable%20naming%20pattern%20(e.g.%2C%20%60bookTitle68%60)%2C%20making%20enumeration%20trivial.%20No%20additional%20privileges%20or%20user%20interaction%20are%20needed.%22%2C%22recommendation%22%3A%22Enforce%20object-level%20ownership%20checks%20in%20the%20%60GET%20%2Fbooks%2Fv1%2F%7Bbook_title%7D%60%20handler.%20After%20authenticating%20the%20request%2C%20extract%20the%20user%20identity%20from%20the%20JWT%20%60sub%60%20claim%20and%20compare%20it%20against%20the%20book's%20stored%20owner%20field.%20Return%20the%20%60secret%60%20field%20%E2%80%94%20or%20a%20403%20Forbidden%20response%20%E2%80%94%20only%20when%20the%20two%20values%20match.%20Additionally%2C%20consider%20whether%20book%20titles%20should%20be%20non-guessable%20(e.g.%2C%20UUIDs)%20to%20reduce%20enumeration%20risk.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fbooks%2Fv1%2FbookTitle68%22%2C%22evidence%22%3A%22Authenticated%20as%20%60name1%60%2C%20a%20GET%20request%20to%20%60%2Fbooks%2Fv1%2FbookTitle68%60%20returned%20the%20secret%20content%20of%20a%20book%20owned%20by%20%60admin%60%3A%20%60%7B%5C%22book_title%5C%22%3A%20%5C%22bookTitle68%5C%22%2C%20%5C%22owner%5C%22%3A%20%5C%22admin%5C%22%2C%20%5C%22secret%5C%22%3A%20%5C%22secret%20for%20bookTitle68%5C%22%7D%60.%20A%20second%20request%20to%20%60%2Fbooks%2Fv1%2FbookTitle59%60%20similarly%20returned%20%60name2%60's%20book%20secret%20to%20%60name1%60.%20In%20both%20cases%20the%20API%20returned%20HTTP%20200%20with%20no%20ownership%20enforcement.%22%2C%22request_evidence%22%3A%22GET%20%2Fbooks%2Fv1%2FbookTitle68%20HTTP%2F1.1%5C%5CnAuthorization%3A%20Bearer%20%5Bname1_jwt%5D%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%20OK%5C%5Cn%7B%5C%22book_title%5C%22%3A%20%5C%22bookTitle68%5C%22%2C%20%5C%22owner%5C%22%3A%20%5C%22admin%5C%22%2C%20%5C%22secret%5C%22%3A%20%5C%22secret%20for%20bookTitle68%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API4%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20Rate%20Limiting%20on%20Login%20Endpoint%20Permits%20Brute-Force%20Attacks%22%2C%22description%22%3A%22The%20login%20endpoint%20at%20POST%20%2Fusers%2Fv1%2Flogin%20enforces%20no%20rate%20limiting%2C%20account%20lockout%2C%20or%20CAPTCHA%20challenge.%20Six%20consecutive%20authentication%20attempts%20using%20incorrect%20passwords%20were%20submitted%20in%20rapid%20succession%2C%20and%20each%20returned%20an%20identical%20HTTP%20200%20response%20with%20no%20throttling%20delay%2C%20no%20lockout%20signal%2C%20and%20no%20change%20in%20server%20behaviour.%20An%20unauthenticated%20attacker%20can%20therefore%20submit%20an%20unbounded%20number%20of%20password%20guesses%20against%20any%20known%20username.%22%2C%22impact%22%3A%22An%20attacker%20can%20automate%20credential-stuffing%20or%20dictionary%20attacks%20against%20user%20accounts%20without%20restriction.%20When%20combined%20with%20username%20enumeration%2C%20this%20allows%20systematic%20offline-style%20password%20guessing%20entirely%20online%2C%20increasing%20the%20probability%20of%20account%20compromise%20over%20time.%22%2C%22likelihood%22%3A%22High%20%E2%80%94%20no%20technical%20control%20prevents%20automated%20submission%20of%20authentication%20requests%3B%20exploitation%20requires%20only%20a%20valid%20username%20and%20a%20scripted%20HTTP%20client.%22%2C%22recommendation%22%3A%221.%20Enforce%20rate%20limiting%20on%20the%20login%20endpoint%2C%20for%20example%20a%20maximum%20of%205%20failed%20attempts%20per%20IP%20address%20per%20minute%2C%20returning%20HTTP%20429%20with%20a%20Retry-After%20header%20on%20breach.%202.%20Implement%20progressive%20account%20lockout%20(e.g.%2C%20temporary%20lockout%20after%2010%20consecutive%20failures%20for%20a%20given%20username).%203.%20Consider%20requiring%20a%20CAPTCHA%20challenge%20after%20a%20configurable%20number%20of%20failures.%204.%20Log%20repeated%20failure%20patterns%20and%20alert%20on%20anomalous%20authentication%20volumes.%205.%20Ensure%20lockout%20and%20rate-limit%20state%20is%20enforced%20server-side%20and%20cannot%20be%20bypassed%20by%20rotating%20headers%20such%20as%20X-Forwarded-For.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Flogin%22%2C%22evidence%22%3A%22Six%20consecutive%20POST%20requests%20to%20%2Fusers%2Fv1%2Flogin%2C%20each%20supplying%20an%20incorrect%20password%2C%20all%20returned%20HTTP%20200%20with%20the%20body%20%7B%5C%22status%5C%22%3A%20%5C%22fail%5C%22%2C%20%5C%22message%5C%22%3A%20%5C%22Password%20is%20not%20correct%20for%20the%20given%20username.%5C%22%7D.%20No%20rate-limit%20header%2C%20no%20lockout%20response%2C%20and%20no%20observable%20delay%20were%20present%20in%20any%20of%20the%20six%20responses.%22%2C%22request_evidence%22%3A%226x%20POST%20%2Fusers%2Fv1%2Flogin%20with%20wrong%20passwords%22%2C%22response_evidence%22%3A%22All%206%20returned%20HTTP%20200%20%7B%5C%22status%5C%22%3A%20%5C%22fail%5C%22%2C%20%5C%22message%5C%22%3A%20%5C%22Password%20is%20not%20correct%20for%20the%20given%20username.%5C%22%7D%20with%20no%20throttling%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API8%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20Security%20Headers%20and%20Server%20Version%20Disclosure%22%2C%22description%22%3A%22All%20responses%20from%20the%20application%20at%20http%3A%2F%2Flocalhost%3A5000%2F%20omit%20standard%20defensive%20HTTP%20security%20headers%20and%20include%20a%20verbose%20%60Server%60%20header%20that%20identifies%20the%20exact%20framework%20and%20runtime%20version%20in%20use%20(%60Werkzeug%2F2.2.3%20Python%2F3.11.15%60).%20The%20following%20headers%20were%20absent%20from%20every%20observed%20response%3A%20%60X-Content-Type-Options%60%2C%20%60X-Frame-Options%60%2C%20%60Content-Security-Policy%60%2C%20%60Strict-Transport-Security%60%2C%20and%20%60X-XSS-Protection%60.%22%2C%22impact%22%3A%22Disclosure%20of%20the%20precise%20framework%20and%20Python%20version%20allows%20an%20attacker%20to%20quickly%20narrow%20a%20search%20for%20publicly%20known%20vulnerabilities%20affecting%20those%20specific%20releases.%20The%20absence%20of%20security%20headers%20increases%20client-side%20attack%20surface%3A%20without%20%60X-Frame-Options%60%20or%20a%20%60frame-ancestors%60%20CSP%20directive%20the%20application%20is%20susceptible%20to%20clickjacking%3B%20without%20%60X-Content-Type-Options%3A%20nosniff%60%20browsers%20may%20perform%20MIME-type%20sniffing%20on%20responses%2C%20potentially%20enabling%20content-injection%20attacks.%22%2C%22likelihood%22%3A%22The%20version%20disclosure%20is%20passively%20observable%20in%20every%20response%20with%20no%20authentication%20required.%20Exploitation%20of%20the%20missing%20headers%20requires%20additional%20attacker-controlled%20conditions%20(e.g.%2C%20a%20malicious%20page%20embedding%20the%20application%20in%20a%20frame)%2C%20making%20practical%20exploitation%20low%20to%20medium%20effort.%22%2C%22recommendation%22%3A%221.%20Suppress%20or%20replace%20the%20%60Server%60%20response%20header%20so%20it%20does%20not%20reveal%20framework%20or%20runtime%20details%20(e.g.%2C%20set%20it%20to%20a%20generic%20value%20or%20remove%20it%20entirely%20via%20Werkzeug's%20%60ServerHeader%60%20configuration%20or%20a%20reverse%20proxy).%202.%20Add%20the%20following%20headers%20to%20all%20responses%3A%20%60X-Content-Type-Options%3A%20nosniff%60%2C%20%60X-Frame-Options%3A%20DENY%60%2C%20a%20suitable%20%60Content-Security-Policy%60%2C%20and%20%60Strict-Transport-Security%60%20(once%20HTTPS%20is%20enforced).%203.%20Consider%20using%20the%20Flask-Talisman%20extension%2C%20which%20applies%20a%20secure%20header%20baseline%20with%20minimal%20configuration.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2F%22%2C%22evidence%22%3A%22A%20GET%20request%20to%20http%3A%2F%2Flocalhost%3A5000%2F%20returned%20a%20%60Server%3A%20Werkzeug%2F2.2.3%20Python%2F3.11.15%60%20header.%20No%20%60X-Content-Type-Options%60%2C%20%60X-Frame-Options%60%2C%20%60Content-Security-Policy%60%2C%20%60Strict-Transport-Security%60%2C%20or%20%60X-XSS-Protection%60%20headers%20were%20present%20in%20the%20response.%22%2C%22request_evidence%22%3A%22GET%20%2F%20HTTP%2F1.1%22%2C%22response_evidence%22%3A%22server%3A%20Werkzeug%2F2.2.3%20Python%2F3.11.15%20(no%20security%20headers%20present)%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API4%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22No%20Rate%20Limiting%20on%20User%20Registration%20Endpoint%20Enables%20Mass%20Account%20Creation%22%2C%22description%22%3A%22The%20user%20registration%20endpoint%20at%20http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Fregister%20does%20not%20enforce%20any%20rate%20limiting%20or%20throttling.%20An%20unauthenticated%20attacker%20can%20submit%20an%20unlimited%20number%20of%20registration%20requests%20in%20rapid%20succession%20without%20receiving%20any%20error%2C%20delay%2C%20or%20block%20response.%22%2C%22impact%22%3A%22An%20attacker%20can%20automate%20mass%20account%20creation%20to%20exhaust%20server-side%20resources%20(storage%2C%20database%20capacity)%2C%20generate%20spam%20accounts%2C%20or%20enumerate%20already-registered%20usernames%20by%20observing%20distinct%20error%20responses%20when%20a%20chosen%20username%20is%20already%20taken.%22%2C%22likelihood%22%3A%22The%20absence%20of%20rate%20limiting%20is%20trivially%20exploitable%20with%20standard%20HTTP%20tooling%20and%20requires%20no%20authentication%20or%20special%20privileges.%20Exploitation%20is%20straightforward%20and%20low-effort.%22%2C%22recommendation%22%3A%22Implement%20rate%20limiting%20on%20POST%20%2Fusers%2Fv1%2Fregister%2C%20for%20example%20by%20restricting%20requests%20per%20IP%20address%20to%20a%20small%20number%20per%20minute%20(e.g.%2C%205%E2%80%9310)%20and%20returning%20HTTP%20429%20when%20the%20threshold%20is%20exceeded.%20Additionally%2C%20consider%20requiring%20email%20verification%20to%20prevent%20bulk%20account%20creation%20from%20a%20single%20address%2C%20and%20evaluate%20CAPTCHA%20for%20high-risk%20registration%20flows.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Fregister%22%2C%22evidence%22%3A%22Six%20consecutive%20POST%20requests%20to%20%2Fusers%2Fv1%2Fregister%2C%20each%20using%20a%20distinct%20username%2C%20all%20returned%20HTTP%20200%20with%20%7B%5C%22message%5C%22%3A%20%5C%22Successfully%20registered.%5C%22%2C%20%5C%22status%5C%22%3A%20%5C%22success%5C%22%7D.%20No%20rate-limit%20headers%20(e.g.%2C%20Retry-After%2C%20X-RateLimit-*)%20were%20observed%20and%20no%20request%20was%20throttled%20or%20rejected.%22%2C%22request_evidence%22%3A%226x%20POST%20%2Fusers%2Fv1%2Fregister%20with%20different%20usernames%22%2C%22response_evidence%22%3A%22All%206%20returned%20HTTP%20200%20%7B%5C%22message%5C%22%3A%20%5C%22Successfully%20registered.%5C%22%2C%20%5C%22status%5C%22%3A%20%5C%22success%5C%22%7D%20with%20no%20throttling%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API2%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Username%20Enumeration%20via%20Distinct%20Login%20Error%20Messages%22%2C%22description%22%3A%22The%20login%20endpoint%20at%20%60POST%20%2Fusers%2Fv1%2Flogin%60%20returns%20different%20error%20messages%20depending%20on%20whether%20the%20submitted%20username%20exists%20in%20the%20system.%20An%20unauthenticated%20attacker%20can%20distinguish%20between%20a%20valid%20username%20with%20a%20wrong%20password%20and%20a%20completely%20unknown%20username%20by%20inspecting%20the%20JSON%20response%20body.%22%2C%22impact%22%3A%22An%20attacker%20can%20systematically%20probe%20the%20login%20endpoint%20to%20compile%20a%20list%20of%20valid%20usernames.%20This%20list%20can%20then%20be%20used%20to%20focus%20credential-stuffing%20or%20brute-force%20attacks%2C%20reducing%20the%20effort%20required%20to%20achieve%20account%20compromise.%22%2C%22likelihood%22%3A%22An%20automated%20script%20can%20iterate%20over%20a%20wordlist%20and%20classify%20each%20probe%20in%20a%20single%20HTTP%20round-trip%20with%20no%20authentication%20required.%20The%20technique%20is%20straightforward%20and%20well-documented%2C%20making%20exploitation%20practical%20for%20any%20motivated%20attacker.%22%2C%22recommendation%22%3A%22Return%20a%20single%2C%20generic%20error%20message%20for%20all%20failed%20login%20attempts%20regardless%20of%20the%20failure%20reason%20%E2%80%94%20for%20example%2C%20%60%5C%22Invalid%20username%20or%20password.%5C%22%60%20%E2%80%94%20so%20that%20the%20response%20provides%20no%20signal%20about%20whether%20the%20username%20exists.%20Apply%20the%20same%20principle%20to%20any%20related%20endpoints%20such%20as%20password%20reset%20flows.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2Fusers%2Fv1%2Flogin%22%2C%22evidence%22%3A%22Two%20POST%20requests%20were%20sent%20to%20%60%2Fusers%2Fv1%2Flogin%60%20with%20identical%20wrong%20passwords%20but%20different%20usernames.%20When%20the%20username%20existed%20the%20response%20was%20%60%7B%5C%22message%5C%22%3A%20%5C%22Password%20is%20not%20correct%20for%20the%20given%20username.%5C%22%7D%60%2C%20and%20when%20the%20username%20did%20not%20exist%20the%20response%20was%20%60%7B%5C%22message%5C%22%3A%20%5C%22Username%20does%20not%20exist%5C%22%7D%60%2C%20confirming%20that%20the%20endpoint%20leaks%20account%20existence.%22%2C%22request_evidence%22%3A%22POST%20%2Fusers%2Fv1%2Flogin%20with%20%7B%5C%22username%5C%22%3A%20%5C%22name1%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22wrong%5C%22%7D%20vs%20%7B%5C%22username%5C%22%3A%20%5C%22nonexistent%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22wrong%5C%22%7D%22%2C%22response_evidence%22%3A%22Existing%20user%3A%20%7B%5C%22message%5C%22%3A%20%5C%22Password%20is%20not%20correct%20for%20the%20given%20username.%5C%22%7D%5C%5CnNon-existent%3A%20%7B%5C%22message%5C%22%3A%20%5C%22Username%20does%20not%20exist%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22API8%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Werkzeug%20Debug%20Mode%20Enabled%20%E2%80%94%20Stack%20Traces%20and%20Potential%20RCE%22%2C%22description%22%3A%22The%20Flask%2FWerkzeug%20application%20is%20running%20with%20debug%3DTrue%20in%20a%20production-accessible%20environment.%20When%20an%20unhandled%20exception%20is%20triggered%20the%20Werkzeug%20interactive%20debugger%20is%20exposed%2C%20revealing%20full%20stack%20traces%2C%20local%20variable%20values%2C%20and%20SQL%20query%20strings.%20The%20interactive%20debugger%20console%20can%20potentially%20be%20unlocked%20using%20a%20PIN%20derivable%20from%20server%20metadata%2C%20yielding%20unauthenticated%20remote%20code%20execution.%22%2C%22impact%22%3A%22Stack%20traces%20accelerate%20exploitation%20of%20all%20other%20vulnerabilities.%20If%20the%20debugger%20PIN%20is%20obtained%2C%20an%20attacker%20achieves%20unauthenticated%20remote%20code%20execution%20on%20the%20server.%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Set%20debug%3DFalse%20in%20all%20production%20deployments.%20Use%20a%20proper%20WSGI%20server%20such%20as%20gunicorn%20or%20uWSGI%20rather%20than%20the%20Werkzeug%20development%20server.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A5000%2F%22%2C%22evidence%22%3A%22Triggering%20a%20500%20error%20returns%20a%20full%20Werkzeug%20debug%20traceback%20in%20the%20response%20body%20including%20source%20file%20paths%2C%20variable%20values%2C%20and%20framework%20internals.%20Server%20header%20confirms%20Werkzeug%20version.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22alice_api%22%2C%22validation_status%22%3A%22unvalidated%22%2C%22validation_note%22%3Anull%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%5D
-->

## 1. Hardcoded Weak JWT Secret Enables Arbitrary Token Forgery

- Severity: critical
- OWASP: API2
- OWASP API: API2
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/login
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The application's JWT signing secret is hardcoded as the trivially guessable string `'random'` in `config.py`. Because the secret is static and weak, an attacker can craft a valid JWT with arbitrary claims — including elevated privileges — and sign it locally without possessing any legitimate credentials. The forged token is accepted by all authenticated API endpoints.

### Impact
Complete authentication bypass. An attacker can impersonate any user, including administrators, by forging a JWT signed with the known secret. As demonstrated, a token carrying `{"sub": "admin"}` was accepted by the API, returning the admin account's email address and confirming the `admin: true` flag — granting unrestricted access to all protected resources and data.

### Likelihood
High. The secret value `'random'` would be recovered almost instantly by dictionary or brute-force attack against any captured token, and is trivially known to anyone with access to the source code. No authentication material or special network position is required to exploit this.

### Recommendation
1. Replace the hardcoded secret immediately with a cryptographically random value of at least 256 bits (e.g., generated via `secrets.token_hex(32)` in Python). 2. Store the secret exclusively in an environment variable or a dedicated secrets manager — never in source code or version control. 3. Invalidate and rotate all currently issued tokens after the secret is changed. 4. Consider migrating to asymmetric signing (RS256/ES256) so that the private signing key is never distributed to verifying services. 5. Enforce a minimum token expiry and validate the `exp` claim strictly to limit the window of any future token compromise.

### Evidence
```
A JWT was forged locally using the secret `'random'` and the claims `{"sub": "admin", "exp": 9999999999}`. When this token was submitted to `GET /me`, the server returned HTTP 200 with `{"data": {"admin": true, "email": "admin@mail.com", "username": "admin"}, "status": "success"}`, confirming full administrative access without any valid credentials.
```

### Request Evidence
```
GET /me HTTP/1.1\nAuthorization: Bearer [forged_jwt_signed_with_secret_random]
```

### Response Evidence
```
HTTP/1.1 200 OK\n{"data": {"admin": true, "email": "admin@mail.com", "username": "admin"}, "status": "success"}
```

## 2. Mass Assignment: Unauthenticated User Can Self-Assign Admin Privileges at Registration

- Severity: critical
- OWASP: API3
- OWASP API: API3
- Source: alice api
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/register
- CVSS: 9.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The POST /users/v1/register endpoint accepts and honours an admin field in the JSON request body that should be a server-controlled read-only property. When submitted with value true the newly created account is granted full admin privileges. Any anonymous user can become an administrator in a single unauthenticated request.

### Impact
Complete privilege escalation to administrator with no prior authentication.

### Likelihood
—

### Recommendation
Strip server-controlled fields such as admin and role from user-supplied registration input server-side.

### Evidence
```
POST /users/v1/register with body {username:eviluser,password:evil123,email:evil@evil.com,admin:true} returns HTTP 200 and GET /users/v1/eviluser confirms admin:true.
```

## 3. SQL Injection via Unsanitised Path Parameter in GET /users/v1/{username}

- Severity: critical
- OWASP: A03
- OWASP API: API10
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/name1
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The `GET /users/v1/{username}` endpoint constructs its database query by interpolating the URL path parameter directly into a raw SQL string: `f"SELECT * FROM users WHERE username = '{username}'"`. No parameterisation, escaping, or input validation is applied. Because the application also runs with Werkzeug debug mode enabled, SQL injection payloads that trigger errors cause the full Python stack trace, the raw SQL query string, and the Werkzeug interactive debugger PIN to be returned in the HTTP 500 response body.

### Impact
An unauthenticated attacker can read, modify, or delete arbitrary data in the underlying database. The UNION-based vector demonstrated during testing allows extraction of all usernames and password hashes in a single request. The exposed Werkzeug debugger PIN (`6ZIN4YOjkLHB44E3SJSp`) additionally enables the attacker to execute arbitrary Python code on the server through the interactive debugger console, escalating the impact to full remote code execution and host compromise.

### Likelihood
Exploitation requires no authentication, no special tooling, and no user interaction. Both an OR-based tautology injection and a UNION-based data-extraction payload were confirmed to work against the live endpoint, demonstrating trivial, reliable exploitability from the public network.

### Recommendation
1. Replace all string-interpolated SQL with parameterised queries or ORM methods (e.g., `cursor.execute('SELECT * FROM users WHERE username = ?', (username,))`) so user-supplied input is never treated as SQL syntax.
2. Disable Werkzeug debug mode in all non-development environments by setting `DEBUG=False` and ensuring the `WERKZEUG_RUN_MAIN` environment variable is not set in production.
3. Rotate or invalidate the exposed Werkzeug debugger PIN (`6ZIN4YOjkLHB44E3SJSp`) immediately.
4. Implement strict input validation on the `username` path parameter (e.g., allowlist of alphanumeric characters and limited punctuation).
5. Ensure application error responses return generic messages to clients and log detailed errors server-side only.

### Evidence
```
Two injection payloads were confirmed against the live endpoint. (1) OR-based tautology: `GET /users/v1/' OR '1'='1` returned HTTP 200 with user record data, confirming the injection alters query logic. (2) UNION-based extraction: `GET /users/v1/name1' UNION SELECT username,password FROM users--` returned HTTP 500 with a full Werkzeug debugger page that included the raw SQL string `SELECT * FROM users WHERE username = 'name1' UNION SELECT username,password FROM users--'`, a complete Python stack trace, and the Werkzeug debugger PIN `6ZIN4YOjkLHB44E3SJSp`.
```

### Request Evidence
```
GET /users/v1/' OR '1'='1 HTTP/1.1 → HTTP 200 with user data\nGET /users/v1/name1' UNION SELECT username,password FROM users-- → HTTP 500 with SQL in error
```

### Response Evidence
```
HTTP 200: {"username": "name1", "email": "mail1@mail.com"} (OR injection)\nHTTP 500: Werkzeug debugger with SQL: SELECT * FROM users WHERE username = 'name1' UNION SELECT username,password FROM users--'
```

## 4. Unauthenticated /createdb Endpoint Allows Full Database Wipe and Reset

- Severity: critical
- OWASP: API5
- OWASP API: API5
- Source: alice api
- Validation: unvalidated
- Affected URL: http://localhost:5000/createdb
- CVSS: 9.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The GET /createdb endpoint drops and recreates the entire application database with no authentication or authorisation check. Any unauthenticated attacker can call it to instantly destroy all user and book data and reset the application to its default state, including resetting admin credentials to known defaults.

### Impact
Complete data destruction and service disruption. Resets admin password to a known default, enabling immediate account takeover of the administrator account.

### Likelihood
—

### Recommendation
Remove or disable this endpoint entirely in any non-development environment. If required for ops, protect it behind strong authentication and restrict access by IP.

### Evidence
```
GET http://localhost:5000/createdb returns HTTP 200 with no authentication required. All user and book records are wiped and recreated with default values.
```

## 5. Unauthenticated Debug Endpoint Exposes Full User Credential Database in Plaintext

- Severity: critical
- OWASP: API5
- OWASP API: API5
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/_debug
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The API endpoint `GET /users/v1/_debug` is accessible without any authentication or authorization and returns a complete dump of all user records. Each record includes the username, email address, plaintext password, and admin flag. No credentials, tokens, or session state are required to retrieve this data.

### Impact
Any unauthenticated attacker with network access to the application can retrieve every user's credentials in a single HTTP request. The exposed data includes plaintext passwords and admin account credentials, enabling immediate account takeover for all users — including administrative accounts — as well as credential-stuffing attacks against other services if passwords are reused.

### Likelihood
Exploitation requires no skill, tooling, or prior knowledge beyond knowing the endpoint path. The endpoint responds with HTTP 200 and a full JSON payload to an anonymous GET request, making this trivially and reliably exploitable by any attacker who discovers or guesses the URL.

### Recommendation
Remove the debug endpoint entirely from the production codebase. If the endpoint must exist in non-production environments, restrict access to localhost or internal networks via network controls, require strong authentication, and ensure it is never deployed to production. Independently of this endpoint, passwords must never be stored or transmitted in plaintext; apply a strong adaptive hashing algorithm (e.g., bcrypt, Argon2) for all stored credentials and audit all API responses to confirm that password fields are never serialised in any response.

### Evidence
```
An unauthenticated GET request to /users/v1/_debug returned HTTP 200 with a full JSON dump of all user records, including plaintext passwords and admin flags. Three accounts were exposed: name1 (mail1@mail.com, password: pass1), name2 (mail2@mail.com, password: pass2), and the admin account (admin@mail.com, password: pass1, admin: true).
```

### Request Evidence
```
GET /users/v1/_debug HTTP/1.1\nHost: localhost:5000\n(No Authorization header)
```

### Response Evidence
```
HTTP/1.1 200 OK\n{"users": [{"admin": false, "email": "mail1@mail.com", "password": "pass1", "username": "name1"}, {"admin": true, "email": "admin@mail.com", "password": "pass1", "username": "admin"}, ...]}
```

## 6. BOLA: Authenticated User Can Change Any Other User's Password via Unvalidated Path Parameter

- Severity: high
- OWASP: API1
- OWASP API: API1
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/admin/password
- CVSS: 8.8 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H)

### Description
The `PUT /users/v1/{username}/password` endpoint identifies the target account using the `username` URL path parameter rather than the authenticated user's identity derived from the JWT token. No ownership or authorization check is performed, so any authenticated user can supply an arbitrary username in the path — including `admin` — to change that account's password.

### Impact
Any authenticated low-privileged user can take over any account, including the administrator account, by setting an arbitrary new password. This enables full privilege escalation and complete account takeover across the entire user base.

### Likelihood
High. Exploitation requires only a valid JWT for any account and knowledge of a target username. No elevated privileges, user interaction, or complex conditions are needed.

### Recommendation
Authorize password change requests by extracting the target user identity exclusively from the validated JWT claims (e.g., `sub`), never from a caller-supplied URL parameter. Additionally, enforce a server-side check that the requesting user is either the account owner or holds an administrative role before processing the change. Reject requests where the path parameter does not match the authenticated identity unless the caller is an admin.

### Evidence
```
A `PUT /users/v1/admin/password` request authenticated with a JWT belonging to the low-privileged user `name1` and a body of `{"password": "hacked123"}` returned `HTTP 204 No Content`, indicating success. A subsequent `GET /users/v1/_debug` confirmed that the admin account's password had been changed to `hacked123`, proving full account takeover without any administrative privilege.
```

### Request Evidence
```
PUT /users/v1/admin/password HTTP/1.1\nAuthorization: Bearer [name1_jwt]\nContent-Type: application/json\n\n{"password": "hacked123"}
```

### Response Evidence
```
HTTP/1.1 204 No Content\n(Admin password changed to "hacked123" confirmed via debug endpoint)
```

## 7. Plaintext Password Storage and Exposure

- Severity: high
- OWASP: API2
- OWASP API: API2
- Source: alice api
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/login
- CVSS: 8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
User passwords are stored and compared in plaintext throughout the application. The login endpoint performs a direct string equality check against the stored plaintext value rather than comparing a salted hash. Passwords are also returned in plaintext via the unauthenticated debug endpoint and are directly extractable via the confirmed SQL injection vulnerability.

### Impact
Any attacker who gains read access to the database — via SQLi, the debug endpoint, or a backup — obtains all user passwords immediately with no cracking required. Passwords are likely reused across other services.

### Likelihood
—

### Recommendation
Hash all passwords using bcrypt, scrypt, or Argon2 with a per-user salt before storage. Never store or log plaintext passwords.

### Evidence
```
GET /users/v1/_debug returns all user records with plaintext password fields. SQL injection on GET /users/v1/{username} also returns plaintext password column values.
```

## 8. BOLA: Authenticated User Can Read Any Other User's Book Secret via Unvalidated Path Parameter

- Severity: medium
- OWASP: API1
- OWASP API: API1
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/books/v1/bookTitle68
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The `GET /books/v1/{book_title}` endpoint returns a book's secret content based solely on the book title supplied in the URL path. The API performs no ownership validation — it does not verify that the authenticated user's identity (as expressed in the JWT `sub` claim) matches the book's recorded owner before returning the `secret` field. As a result, any authenticated user can retrieve the secret content of any book by guessing or knowing its title.

### Impact
Any authenticated user can read the private secret content of books belonging to other users, including administrative accounts. Demonstrated evidence shows user `name1` successfully retrieved the secret for `admin`'s book (`bookTitle68`) and `name2`'s book (`bookTitle59`), fully compromising the confidentiality of all book secrets stored in the application.

### Likelihood
High. Exploitation requires only a valid JWT and knowledge of a target book title. Book titles appear to follow a predictable naming pattern (e.g., `bookTitle68`), making enumeration trivial. No additional privileges or user interaction are needed.

### Recommendation
Enforce object-level ownership checks in the `GET /books/v1/{book_title}` handler. After authenticating the request, extract the user identity from the JWT `sub` claim and compare it against the book's stored owner field. Return the `secret` field — or a 403 Forbidden response — only when the two values match. Additionally, consider whether book titles should be non-guessable (e.g., UUIDs) to reduce enumeration risk.

### Evidence
```
Authenticated as `name1`, a GET request to `/books/v1/bookTitle68` returned the secret content of a book owned by `admin`: `{"book_title": "bookTitle68", "owner": "admin", "secret": "secret for bookTitle68"}`. A second request to `/books/v1/bookTitle59` similarly returned `name2`'s book secret to `name1`. In both cases the API returned HTTP 200 with no ownership enforcement.
```

### Request Evidence
```
GET /books/v1/bookTitle68 HTTP/1.1\nAuthorization: Bearer [name1_jwt]
```

### Response Evidence
```
HTTP/1.1 200 OK\n{"book_title": "bookTitle68", "owner": "admin", "secret": "secret for bookTitle68"}
```

## 9. Missing Rate Limiting on Login Endpoint Permits Brute-Force Attacks

- Severity: low
- OWASP: API4
- OWASP API: API4
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L)

### Description
The login endpoint at POST /users/v1/login enforces no rate limiting, account lockout, or CAPTCHA challenge. Six consecutive authentication attempts using incorrect passwords were submitted in rapid succession, and each returned an identical HTTP 200 response with no throttling delay, no lockout signal, and no change in server behaviour. An unauthenticated attacker can therefore submit an unbounded number of password guesses against any known username.

### Impact
An attacker can automate credential-stuffing or dictionary attacks against user accounts without restriction. When combined with username enumeration, this allows systematic offline-style password guessing entirely online, increasing the probability of account compromise over time.

### Likelihood
High — no technical control prevents automated submission of authentication requests; exploitation requires only a valid username and a scripted HTTP client.

### Recommendation
1. Enforce rate limiting on the login endpoint, for example a maximum of 5 failed attempts per IP address per minute, returning HTTP 429 with a Retry-After header on breach. 2. Implement progressive account lockout (e.g., temporary lockout after 10 consecutive failures for a given username). 3. Consider requiring a CAPTCHA challenge after a configurable number of failures. 4. Log repeated failure patterns and alert on anomalous authentication volumes. 5. Ensure lockout and rate-limit state is enforced server-side and cannot be bypassed by rotating headers such as X-Forwarded-For.

### Evidence
```
Six consecutive POST requests to /users/v1/login, each supplying an incorrect password, all returned HTTP 200 with the body {"status": "fail", "message": "Password is not correct for the given username."}. No rate-limit header, no lockout response, and no observable delay were present in any of the six responses.
```

### Request Evidence
```
6x POST /users/v1/login with wrong passwords
```

### Response Evidence
```
All 6 returned HTTP 200 {"status": "fail", "message": "Password is not correct for the given username."} with no throttling
```

## 10. Missing Security Headers and Server Version Disclosure

- Severity: low
- OWASP: API8
- OWASP API: API8
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
All responses from the application at http://localhost:5000/ omit standard defensive HTTP security headers and include a verbose `Server` header that identifies the exact framework and runtime version in use (`Werkzeug/2.2.3 Python/3.11.15`). The following headers were absent from every observed response: `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, and `X-XSS-Protection`.

### Impact
Disclosure of the precise framework and Python version allows an attacker to quickly narrow a search for publicly known vulnerabilities affecting those specific releases. The absence of security headers increases client-side attack surface: without `X-Frame-Options` or a `frame-ancestors` CSP directive the application is susceptible to clickjacking; without `X-Content-Type-Options: nosniff` browsers may perform MIME-type sniffing on responses, potentially enabling content-injection attacks.

### Likelihood
The version disclosure is passively observable in every response with no authentication required. Exploitation of the missing headers requires additional attacker-controlled conditions (e.g., a malicious page embedding the application in a frame), making practical exploitation low to medium effort.

### Recommendation
1. Suppress or replace the `Server` response header so it does not reveal framework or runtime details (e.g., set it to a generic value or remove it entirely via Werkzeug's `ServerHeader` configuration or a reverse proxy). 2. Add the following headers to all responses: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, a suitable `Content-Security-Policy`, and `Strict-Transport-Security` (once HTTPS is enforced). 3. Consider using the Flask-Talisman extension, which applies a secure header baseline with minimal configuration.

### Evidence
```
A GET request to http://localhost:5000/ returned a `Server: Werkzeug/2.2.3 Python/3.11.15` header. No `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, or `X-XSS-Protection` headers were present in the response.
```

### Request Evidence
```
GET / HTTP/1.1
```

### Response Evidence
```
server: Werkzeug/2.2.3 Python/3.11.15 (no security headers present)
```

## 11. No Rate Limiting on User Registration Endpoint Enables Mass Account Creation

- Severity: low
- OWASP: API4
- OWASP API: API4
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/register
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L)

### Description
The user registration endpoint at http://localhost:5000/users/v1/register does not enforce any rate limiting or throttling. An unauthenticated attacker can submit an unlimited number of registration requests in rapid succession without receiving any error, delay, or block response.

### Impact
An attacker can automate mass account creation to exhaust server-side resources (storage, database capacity), generate spam accounts, or enumerate already-registered usernames by observing distinct error responses when a chosen username is already taken.

### Likelihood
The absence of rate limiting is trivially exploitable with standard HTTP tooling and requires no authentication or special privileges. Exploitation is straightforward and low-effort.

### Recommendation
Implement rate limiting on POST /users/v1/register, for example by restricting requests per IP address to a small number per minute (e.g., 5–10) and returning HTTP 429 when the threshold is exceeded. Additionally, consider requiring email verification to prevent bulk account creation from a single address, and evaluate CAPTCHA for high-risk registration flows.

### Evidence
```
Six consecutive POST requests to /users/v1/register, each using a distinct username, all returned HTTP 200 with {"message": "Successfully registered.", "status": "success"}. No rate-limit headers (e.g., Retry-After, X-RateLimit-*) were observed and no request was throttled or rejected.
```

### Request Evidence
```
6x POST /users/v1/register with different usernames
```

### Response Evidence
```
All 6 returned HTTP 200 {"message": "Successfully registered.", "status": "success"} with no throttling
```

## 12. Username Enumeration via Distinct Login Error Messages

- Severity: low
- OWASP: API2
- OWASP API: API2
- Source: Dynamic
- Validation: unvalidated
- Affected URL: http://localhost:5000/users/v1/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The login endpoint at `POST /users/v1/login` returns different error messages depending on whether the submitted username exists in the system. An unauthenticated attacker can distinguish between a valid username with a wrong password and a completely unknown username by inspecting the JSON response body.

### Impact
An attacker can systematically probe the login endpoint to compile a list of valid usernames. This list can then be used to focus credential-stuffing or brute-force attacks, reducing the effort required to achieve account compromise.

### Likelihood
An automated script can iterate over a wordlist and classify each probe in a single HTTP round-trip with no authentication required. The technique is straightforward and well-documented, making exploitation practical for any motivated attacker.

### Recommendation
Return a single, generic error message for all failed login attempts regardless of the failure reason — for example, `"Invalid username or password."` — so that the response provides no signal about whether the username exists. Apply the same principle to any related endpoints such as password reset flows.

### Evidence
```
Two POST requests were sent to `/users/v1/login` with identical wrong passwords but different usernames. When the username existed the response was `{"message": "Password is not correct for the given username."}`, and when the username did not exist the response was `{"message": "Username does not exist"}`, confirming that the endpoint leaks account existence.
```

### Request Evidence
```
POST /users/v1/login with {"username": "name1", "password": "wrong"} vs {"username": "nonexistent", "password": "wrong"}
```

### Response Evidence
```
Existing user: {"message": "Password is not correct for the given username."}\nNon-existent: {"message": "Username does not exist"}
```

## 13. Werkzeug Debug Mode Enabled — Stack Traces and Potential RCE

- Severity: low
- OWASP: API8
- OWASP API: API8
- Source: alice api
- Validation: unvalidated
- Affected URL: http://localhost:5000/
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The Flask/Werkzeug application is running with debug=True in a production-accessible environment. When an unhandled exception is triggered the Werkzeug interactive debugger is exposed, revealing full stack traces, local variable values, and SQL query strings. The interactive debugger console can potentially be unlocked using a PIN derivable from server metadata, yielding unauthenticated remote code execution.

### Impact
Stack traces accelerate exploitation of all other vulnerabilities. If the debugger PIN is obtained, an attacker achieves unauthenticated remote code execution on the server.

### Likelihood
—

### Recommendation
Set debug=False in all production deployments. Use a proper WSGI server such as gunicorn or uWSGI rather than the Werkzeug development server.

### Evidence
```
Triggering a 500 error returns a full Werkzeug debug traceback in the response body including source file paths, variable values, and framework internals. Server header confirms Werkzeug version.
```
