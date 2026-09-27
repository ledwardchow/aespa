# Issue Export: Run #36

- Site: Bank of Ed
- Exported: 27/09/2026, 12:39:44
- Total findings: 24

<!-- aespa-findings-json
%5B%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22External%20transfers%20permit%20unauthorized%20account%20debits%20and%20unbounded%20overdrafts%22%2C%22description%22%3A%22The%20external%20transfer%20endpoint%20does%20not%20verify%20that%20the%20requested%20source%20account%20belongs%20to%20the%20authenticated%20user%20and%20does%20not%20enforce%20an%20available-balance%20limit%20before%20completing%20the%20debit.%22%2C%22impact%22%3A%22An%20authenticated%20user%20may%20debit%20another%20user's%20account%20and%20create%20a%20large%20negative%20balance%2C%20causing%20direct%20financial%20loss%20and%20corrupting%20account%20state.%22%2C%22likelihood%22%3A%22High%20in%20the%20observed%20context%3A%20one%20authenticated%20request%20naming%20an%20account%20absent%20from%20the%20user's%20account%20list%20completed%20successfully%20and%20produced%20a%20negative%20balance.%22%2C%22recommendation%22%3A%22Load%20the%20source%20account%20through%20the%20authenticated%20user's%20ownership%20relation%20and%20reject%20accounts%20outside%20that%20relation.%20Enforce%20positive%20available-balance%20and%20transaction-limit%20checks%20in%20the%20same%20database%20transaction%20as%20the%20debit.%20Reject%20the%20request%20before%20creating%20the%20transaction%20when%20either%20check%20fails.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AC%2FC%3AN%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22For%20authenticated%20user%20Amelia%20Chen%20(user%20id%201)%2C%20GET%20%2Fapi%2Faccounts%20returned%20account%20IDs%201%2C%202%2C%203%2C%20and%2051%2C%20excluding%20account%206.%20A%20POST%20to%20the%20external%20transfer%20endpoint%20using%20from_account_id%206%20and%20amount%2099999999%20returned%20HTTP%20201%20with%20success%3Dtrue%2C%20transaction_id%3D39%2C%20status%3Dcompleted%2C%20and%20new_from_balance%3D-99998123.82.%22%2C%22request_evidence%22%3A%22%7B%5C%22from_account_id%5C%22%3A6%2C%5C%22to_bsb%5C%22%3A%5C%22000-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2230000001%5C%22%2C%5C%22amount%5C%22%3A99999999%2C%5C%22description%5C%22%3A%5C%22safe%20ownership%20upper-bound%20probe%5C%22%2C%5C%22totp_code%5C%22%3A%5C%22000000%5C%22%7D%22%2C%22response_evidence%22%3A%22%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22transaction_id%5C%22%3A39%2C%5C%22from_account_id%5C%22%3A6%2C%5C%22amount%5C%22%3A%5C%2299999999%5C%22%2C%5C%22new_from_balance%5C%22%3A%5C%22-99998123.82%5C%22%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Transfer%20completed%20successfully%5C%22%7D%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20live%20admin%20session's%20account%20list%20contained%201%2C%202%2C%203%2C%20and%2051%2C%20while%20GET%20%2Fapi%2Faccounts%2F6%20returned%20NOT_FOUND%2C%20yet%20a%20POST%20using%20from_account_id%206%20completed%20and%20returned%20a%20new%20balance%20of%20-99998123.84.%20A%20separate%20controlled%20check%20exhausted%20the%20balance-control%20explanation%3A%20after%20account%201%20reached%200.00%2C%20a%200.01%20external%20transfer%20still%20returned%20201%20and%20produced%20-0.01.%20The%20ordinary%20Amelia%20session%20labels%20were%20unavailable%20and%20returned%20401%2C%20so%20the%20exact%20Amelia%20replay%20could%20not%20be%20made%2C%20but%20the%20endpoint's%20live%20behavior%20independently%20proves%20both%20missing%20balance%20enforcement%20and%20acceptance%20of%20a%20source%20account%20inaccessible%20through%20the%20authenticated%20account%20API.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20administrative%20user%20export%22%2C%22description%22%3A%22The%20administrative%20user%20export%20at%20%2Fapi%2Fadmin%2Fexport%2Fusers%20can%20be%20accessed%20without%20authentication%20or%20administrator%20authorization.%20It%20returns%20multiple%20user%20records%2C%20including%20password%20hashes%20and%20persona%20data.%22%2C%22impact%22%3A%22An%20unauthenticated%20attacker%20can%20download%20account%20data%20for%20all%20users%2C%20causing%20privacy%20harm%20and%20enabling%20offline%20password-cracking%20attempts%20against%20the%20exposed%20hashes.%22%2C%22likelihood%22%3A%22High%3A%20an%20anonymous%20GET%20request%20returned%20the%20export%20with%20HTTP%20200%20and%20no%20authorization%20or%20cookies.%22%2C%22recommendation%22%3A%22Require%20authentication%20and%20an%20explicit%20administrator%20authorization%20check%20before%20serving%20the%20export.%20Return%20only%20the%20fields%20required%20for%20the%20export%2C%20exclude%20password%20hashes%20and%20TOTP%20secrets%2C%20and%20audit%20access%20to%20the%20route.%22%2C%22cvss_score%22%3A9.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20returned%20HTTP%20200%20with%20a%2038%2C685-character%20JSON%20export%20containing%20multiple%20users%2C%20including%20password_hash%20values%2C%20email%20addresses%2C%20names%2C%20addresses%2C%20phone%20numbers%2C%20and%20account%20metadata.%20The%20response%20began%20with%20a%20successful%20users%20export%20containing%20user%20ID%201%20and%20a%20bcrypt%20password%20hash.%5Cn%5CnSpecialist%20evidence%3A%5CnTwo%20bounded%20anonymous%20GET%20probes%20returned%20HTTP%20200%20and%20large%20JSON%20user%20exports.%20The%20response%20included%20a%20users%20array%20with%20password_hash%2C%20email%2C%20address%2C%20phone%2C%20TOTP%20status%2C%20and%20timestamps%20for%20multiple%20accounts.%5Cn%5CnSpecialist%20evidence%3A%5CnA%20wire-level%20GET%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%20using%20the%20anonymous%20session%20had%20Authorization%3A%20none%20and%20Cookies%3A%20none%2C%20yet%20returned%20HTTP%20200%20with%20%7B%5C%22success%5C%22%3Atrue%7D.%20The%20users%20array%20included%20password_hash%2C%20email%2C%20address%2C%20phone%2C%20avatar_url%2C%20totp_secret%2C%20and%20totp_enabled%20fields.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%3B%20use_session%3Danonymous.%5Cn%5CnSpecialist%20request%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%5CnAuthorization%3A%20none%5CnCookies%3A%20none%5CnSession%3A%20anonymous%5Cn%5CnSpecialist%20request%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%22%2C%22response_evidence%22%3A%22HTTP%20200.%20The%20response%20begins%20with%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22users%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%2F.og%2Fat2.uheWG%2Figi%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Amelia%5C%22%2C%5C%22address_line1%5C%22%3A%5C%2214%20Harbour%20View%20Tce%5C%22%2C%5C%22phone%5C%22%3A%5C%220411%20234%20567%5C%22%7D%2C%20...%5D%7D%7D.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20200%3B%20response%20size%2044%2C714%20characters%3B%20response%20began%20with%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22users%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%2F.og%2Fat2.uheWG%2Figi%5C%22%2C...%20and%20included%20records%20for%20users%201%20through%20at%20least%2010.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20200%20JSON%20response%2C%2047%2C683%20characters%2C%20with%20success%3Atrue%20and%20a%20users%20array%20containing%20password_hash%20and%20personal%20contact%2Faddress%20fields.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20credential-free%20GET%20with%20no%20Authorization%20header%20and%20no%20cookies%20returned%20HTTP%20200%20JSON%2C%20not%20a%20generic%20SPA%20shell.%20The%20response%20contained%20a%20multi-user%20export%20with%20Amelia%20Chen's%20email%20and%20bcrypt%20password_hash%2C%20plus%20address%20and%20phone%20fields%2C%20so%20the%20endpoint%20is%20exposing%20administrative%20data%20without%20authentication.%20The%20first%20disproof%20assumption%20therefore%20failed%3A%20this%20was%20not%20session%20confusion%20or%20a%20frontend-shell%20response%2C%20and%20the%20data%20is%20not%20a%20public%20catalogue%20object.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202070%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-010%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Unauthenticated%20access%20to%20administrative%20user%20export%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%20returned%20HTTP%20200%20to%20an%20anonymous%20request%20with%20no%20Authorization%20header%20or%20cookies%20and%20returned%20a%2038%2C685-character%20JSON%20export%20containing%20users%2C%20password_hash%2C%20email%2C%20address%2C%20and%20phone%20fields.%20An%20anonymous%20OPTIONS%20request%20to%20the%20same%20route%20also%20returned%20HTTP%20200%20with%20an%20empty%20body.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%3B%20use_session%3Danonymous.%20Follow-up%3A%20OPTIONS%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%2C%20obligation_id%3D7016.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22GET%20response%3A%20HTTP%20200%20with%20JSON%20containing%20users%2C%20password_hash%2C%20email%2C%20address%2C%20and%20phone%20fields.%20OPTIONS%20response%3A%20HTTP%20200%20with%20an%20empty%20body.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22A%20direct%20anonymous%20GET%20with%20no%20Authorization%20header%20or%20cookies%20returned%20HTTP%20200%20and%20a%20non-empty%20JSON%20export%20containing%20multiple%20users'%20password_hash%2C%20email%2C%20address%2C%20and%20phone%20fields.%20The%20response%20was%20identical%20when%20compared%20with%20the%20listed%20ordinary%20user%20session%2C%20so%20this%20is%20not%20a%20login%20redirect%2C%20empty%20placeholder%2C%20or%20admin-only%20response%20accidentally%20observed%20through%20an%20authenticated%20context.%20The%20endpoint%20is%20therefore%20exposing%20meaningful%20administrative%20data%20without%20authentication%20or%20authorization.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Unauthenticated%20health%20endpoint%20exposes%20JWT%20secret%20and%20database%20configuration%22%2C%22description%22%3A%22The%20unauthenticated%20GET%20%2Fapi%2Fhealth%20endpoint%2C%20including%20%2Fapi%2Fhealth%3Fauth_probe%3D1%2C%20returns%20sensitive%20runtime%20configuration%3A%20the%20JWT%20signing%20secret%2C%20database%20host%2C%20name%20and%20user%2C%20PHP%20and%20Apache%20versions%2C%20and%20the%20production%20environment%20label.%22%2C%22impact%22%3A%22An%20attacker%20who%20can%20reach%20the%20endpoint%20can%20obtain%20the%20JWT%20secret%20and%20may%20forge%20authentication%20tokens.%20The%20disclosed%20database%20and%20server%20details%20can%20also%20support%20follow-on%20attacks.%22%2C%22likelihood%22%3A%22High%20because%20the%20endpoint%20is%20reachable%20anonymously%20and%20returns%20the%20JWT%20secret%20directly.%22%2C%22recommendation%22%3A%22Return%20only%20a%20minimal%20health%20status.%20Protect%20diagnostic%20details%20with%20authentication%20and%20network%20restrictions%2C%20rotate%20the%20exposed%20JWT%20secret%2C%20and%20invalidate%20tokens%20signed%20with%20it.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AH%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20request%20returned%20HTTP%20200%20and%20exposed%20jwt_secret%3Dbankofed-dev-secret-change-in-production%2C%20db_host%3D127.0.0.1%2C%20db_name%3Dbankofed%2C%20db_user%3Droot%2C%20PHP%208.4.25%2C%20Apache%2F2.4.68%2C%20and%20environment%3Dproduction.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%20200%20response%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.4.25%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%2F2.4.68%20(Unix)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22root%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22bankofed-dev-secret-change-in-production%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20fresh%20anonymous%20request%20returned%20HTTP%20200%20with%20the%20JWT%20secret%20in%20plain%20JSON%2C%20along%20with%20database%20connection%20details%20and%20production%2Fversion%20information.%20The%20same%20sensitive%20body%20was%20returned%20with%20the%20provided%20admin%20session%2C%20so%20the%20data%20is%20not%20gated%20by%20authentication.%20The%20body%20is%20populated%20and%20specific%2C%20which%20rules%20out%20an%20empty%20health%20response%20or%20a%20scanner-only%20status-code%20mismatch%3B%20no%20benign%20explanation%20remains%20for%20publishing%20the%20signing%20secret%20from%20an%20unauthenticated%20endpoint.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202121%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-061%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Unauthenticated%20health%20endpoint%20exposes%20JWT%20signing%20secret%20and%20database%20details%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20unauthenticated%20request%20to%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%20returned%20HTTP%20200%20with%20jwt_secret%3D%5C%5C%5C%22bankofed-dev-secret-change-in-production%5C%5C%5C%22%2C%20db_user%3D%5C%5C%5C%22root%5C%5C%5C%22%2C%20db_host%3D%5C%5C%5C%22127.0.0.1%5C%5C%5C%22%2C%20and%20db_name%3D%5C%5C%5C%22bankofed%5C%5C%5C%22%20in%20the%20JSON%20response.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20anonymous%20HTTP%20probe%20returned%20200%20and%20the%20full%20JSON%20body%20included%20jwt_secret%3D%5C%5C%5C%22bankofed-dev-secret-change-in-production%5C%5C%5C%22%2C%20db_host%3D%5C%5C%5C%22127.0.0.1%5C%5C%5C%22%2C%20db_name%3D%5C%5C%5C%22bankofed%5C%5C%5C%22%2C%20db_user%3D%5C%5C%5C%22root%5C%5C%5C%22%2C%20environment%3D%5C%5C%5C%22production%5C%5C%5C%22%2C%20PHP%208.4.25%2C%20and%20Apache%202.4.68%20details.%20The%20request%20used%20the%20anonymous%20session%2C%20so%20no%20Authorization%20header%20or%20cookies%20were%20supplied.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%20using%20use_session%3D'anonymous'%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20response%20body%3A%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Atrue%2C%5C%5C%5C%22data%5C%5C%5C%22%3A%7B%5C%5C%5C%22status%5C%5C%5C%22%3A%5C%5C%5C%22ok%5C%5C%5C%22%2C%5C%5C%5C%22php_version%5C%5C%5C%22%3A%5C%5C%5C%228.4.25%5C%5C%5C%22%2C%5C%5C%5C%22server%5C%5C%5C%22%3A%5C%5C%5C%22Apache%2F2.4.68%20(Unix)%5C%5C%5C%22%2C%5C%5C%5C%22db_host%5C%5C%5C%22%3A%5C%5C%5C%22127.0.0.1%5C%5C%5C%22%2C%5C%5C%5C%22db_name%5C%5C%5C%22%3A%5C%5C%5C%22bankofed%5C%5C%5C%22%2C%5C%5C%5C%22db_user%5C%5C%5C%22%3A%5C%5C%5C%22root%5C%5C%5C%22%2C%5C%5C%5C%22jwt_secret%5C%5C%5C%22%3A%5C%5C%5C%22bankofed-dev-secret-change-in-production%5C%5C%5C%22%2C%5C%5C%5C%22environment%5C%5C%5C%22%3A%5C%5C%5C%22production%5C%5C%5C%22%7D%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22OK%5C%5C%5C%22%7D%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20200%3B%20response%20JSON%20included%20jwt_secret%2C%20db_host%2C%20db_name%2C%20and%20db_user.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22A%20direct%20anonymous%20request%20returned%20HTTP%20200%20with%20jwt_secret%2C%20db_user%2C%20db_host%2C%20and%20db_name%20in%20the%20live%20JSON%20response%2C%20with%20no%20Authorization%20header%20or%20cookies.%20A%20second%20anonymous%20request%20with%20a%20cache-busting%20query%20parameter%20returned%20the%20same%20fields%2C%20so%20this%20is%20not%20a%20stale%20scanner%20artifact%20or%20an%20access-controlled%20debug%20response.%20The%20response%20also%20labels%20the%20environment%20as%20production%2C%20and%20no%20benign%20explanation%20accounts%20for%20exposing%20the%20signing%20secret%20and%20database%20details.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202124%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-064%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Unauthenticated%20health%20endpoint%20exposes%20JWT%20secret%20and%20database%20configuration%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22critical%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20GET%20request%20returned%20HTTP%20200%20with%20JSON%20containing%20php_version%208.4.25%2C%20server%20Apache%2F2.4.68%20(Unix)%2C%20db_host%20127.0.0.1%2C%20db_name%20bankofed%2C%20db_user%20root%2C%20jwt_secret%20bankofed-dev-secret-change-in-production%2C%20and%20environment%20production.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%5C%5CnAuthorization%3A%20none%5C%5CnCookies%3A%20none%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200.%20JSON%20data%20included%20php_version%208.4.25%2C%20server%20Apache%2F2.4.68%20(Unix)%2C%20db_host%20127.0.0.1%2C%20db_name%20bankofed%2C%20db_user%20root%2C%20jwt_secret%20bankofed-dev-secret-change-in-production%2C%20and%20environment%20production.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22A%20direct%20anonymous%20request%20returned%20HTTP%20200%20and%20the%20complete%20JSON%20payload%2C%20including%20jwt_secret%2C%20db_host%2C%20db_name%2C%20db_user%2C%20and%20environment%3Dproduction%3B%20it%20was%20not%20an%20empty%20or%20login%20response.%20Comparing%20the%20same%20request%20with%20the%20provided%20admin_test%20session%20produced%20an%20identical%20body%2C%20so%20the%20fields%20are%20not%20gated%20by%20authentication.%20A%20public%20liveness%20check%20is%20a%20benign%20explanation%20for%20the%20status%20field%2C%20but%20it%20does%20not%20explain%20returning%20the%20JWT%20signing%20secret%20and%20database%20configuration%20to%20anonymous%20callers%2C%20and%20the%20disclosed%20value%20is%20an%20operational-looking%20default%20secret%20explicitly%20marked%20for%20replacement%20in%20production.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202134%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-074%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Unauthenticated%20health%20endpoint%20discloses%20JWT%20signing%20secret%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22critical%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3Fauth_probe%3D1%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20request%20returned%20HTTP%20200%20with%20JSON%20containing%20db_host%3D127.0.0.1%2C%20db_name%3Dbankofed%2C%20db_user%3Droot%2C%20and%20jwt_secret%3Dbankofed-dev-secret-change-in-production.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3Fauth_probe%3D1%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20JSON%20response%20contained%20jwt_secret%20and%20db_host%2Fdb_name%2Fdb_user.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20exact%20anonymous%20request%20returned%20the%20JWT%20secret%20and%20database%20metadata%2C%20and%20the%20same%20disclosure%20occurred%20on%20the%20normal%20health%20URL%20without%20auth_probe%2C%20so%20the%20scanner%20parameter%20is%20not%20the%20cause.%20I%20also%20checked%20the%20likely%20HTTPS%20front-door%20ports%20443%20and%208443%3B%20neither%20was%20reachable%2C%20and%20no%20evidence%20provided%20a%20benign%20proxy%20or%20placeholder%20explanation.%20The%20live%20response%20labels%20the%20value%20jwt_secret%20and%20reports%20environment%3Dproduction%2C%20which%20confirms%20an%20unauthenticated%20secret%20disclosure.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Admin%20account%20accepts%20the%20common%20password%20%60password%60%22%2C%22description%22%3A%22The%20existing%20admin%40example.com%20account%20can%20be%20authenticated%20through%20POST%20%2Fapi%2Fauth%2Flogin%20using%20the%20widely%20known%20password%20%60password%60.%20The%20successful%20response%20returns%20an%20admin%20bearer%20token%20and%20the%20admin%20user%20record.%22%2C%22impact%22%3A%22An%20attacker%20who%20guesses%20or%20obtains%20this%20password%20can%20access%20the%20administrator%20account%20and%20its%20banking%20functions.%22%2C%22likelihood%22%3A%22High%20because%20%60password%60%20is%20a%20widely%20known%2C%20common%20password%20and%20the%20endpoint%20accepts%20it%20for%20a%20privileged%20account.%22%2C%22recommendation%22%3A%22Force%20the%20admin%20account%20to%20use%20a%20strong%2C%20unique%20password.%20Reject%20common%20and%20breached%20passwords%2C%20require%20MFA%20for%20privileged%20accounts%2C%20and%20add%20login%20throttling%20and%20monitoring.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20email%20admin%40example.com%20and%20password%20%60password%60%20returned%20HTTP%20200%20with%20success%3Atrue.%20The%20response%20included%20data.user.email%3Dadmin%40example.com%2C%20data.user.id%3D19%2C%20data.user.totp_enabled%3Dfalse%2C%20and%20a%20bearer%20token.%5Cn%5CnSpecialist%20evidence%3A%5CnThe%20shared%20tester%20ledger%20records%20a%20confirmed%20successful%20admin%20authentication%20using%20the%20common%20password%20%60password%60%3B%20the%20associated%20login%20probe%20returned%20HTTP%20200%20and%20the%20authenticated%20profile%20probe%20returned%20HTTP%20200%20before%20logout.%5Cn%5CnSpecialist%20evidence%3A%5CnThe%20shared%20tester%20ledger%20contains%20the%20confirmed%20claim%3A%20Admin%20account%20accepts%20the%20common%20password%20%60password%60.%20The%20same%20ledger%20records%20a%20successful%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20HTTP%20200.%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20email%20admin%40example.com%20and%20password%20password.%5Cn%5CnSpecialist%20request%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20using%20the%20confirmed%20admin%20account%20and%20password%20%60password%60.%22%2C%22response_evidence%22%3A%22HTTP%20200%3B%20success%3Atrue%3B%20data.user.email%3Dadmin%40example.com%3B%20data.user.id%3D19%3B%20data.user.totp_enabled%3Dfalse%3B%20data.token%20present.%5Cn%5CnSpecialist%20response%3A%5CnThe%20login%20returned%20HTTP%20200%20and%20the%20subsequent%20authenticated%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20returned%20HTTP%20200%3B%20logout%20then%20returned%20200%20and%20profile%20returned%20401.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20exact%20anonymous%20login%20request%20returned%20HTTP%20200%2C%20success%3Atrue%2C%20the%20admin%20user%20record%2C%20and%20a%20bearer%20token.%20A%20control%20request%20with%20a%20clearly%20wrong%20password%20returned%20HTTP%20401%20WRONG_PASSWORD%2C%20so%20the%20handler%20is%20validating%20the%20supplied%20password%20rather%20than%20returning%20a%20canned%20response.%20The%20issued%20token%20was%20accepted%20by%20the%20read-only%20GET%20%2Fapi%2Faccounts%20endpoint%2C%20and%20the%20returned%20user%20record%20shows%20the%20admin%20account%20has%20TOTP%20disabled%3B%20the%20response%20also%20exposes%20the%20MD5%20hash%20for%20password%2C%20which%20matches%20the%20supplied%20common%20password.%20These%20checks%20rule%20out%20the%20main%20benign%20explanations.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22email%5C%22%3A%5C%22admin%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22password%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A10%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Authenticated%20avatar%20import%20performs%20server-side%20requests%20to%20arbitrary%20URLs%22%2C%22description%22%3A%22The%20authenticated%20avatar%20import%20endpoint%20at%20%2Fapi%2Fprofile%2Favatar%20accepts%20a%20caller-controlled%20URL%20and%20fetches%20it%20from%20the%20server.%22%2C%22impact%22%3A%22An%20authenticated%20user%20can%20make%20the%20server%20request%20reachable%20services%20and%20receive%20response%20bodies%2C%20potentially%20exposing%20internal%20web%20content%20or%20service%20credentials%20where%20network%20access%20permits.%22%2C%22likelihood%22%3A%22High%20where%20an%20authenticated%20user%20can%20reach%20the%20endpoint%20and%20the%20server%20has%20access%20to%20internal%20services.%22%2C%22recommendation%22%3A%22Allow%20only%20approved%20image%20schemes%20and%20hosts.%20Resolve%20and%20validate%20destinations%20before%20connecting%2C%20block%20loopback%2C%20private%2C%20and%20link-local%20ranges%20after%20DNS%20resolution%2C%20limit%20redirects%2C%20enforce%20response%20size%20and%20content-type%20limits%2C%20and%20do%20not%20return%20fetched%20content%20to%20the%20client.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%2Favatar%22%2C%22evidence%22%3A%22An%20authenticated%20POST%20with%20%7B%5C%22url%5C%22%3A%5C%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%5C%22%7D%20returned%20HTTP%20200%20and%20a%2055%2C420-byte%20JSON%20response.%20The%20data.avatar_data%20value%20began%20with%20data%3Atext%2Fhtml%3Bbase64%20and%20decoded%20to%20the%20Bank%20of%20Ed%20banking%20page.%20A%20URL%20containing%20an%20injected%20query%20string%20also%20returned%20success%2C%20showing%20the%20URL%20was%20used%20as%20supplied.%22%2C%22request_evidence%22%3A%22Authenticated%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%2Favatar%20with%20JSON%20url%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F.%22%2C%22response_evidence%22%3A%22HTTP%20200%3B%20response%20data.avatar_data%20is%20a%20large%20data%3Atext%2Fhtml%3Bbase64%20value%20containing%20the%20fetched%20banking%20HTML.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20valid%20external%20PNG%20URL%20returned%20imported%20image%20bytes%2C%20proving%20this%20endpoint%20performs%20a%20server-side%20fetch%20rather%20than%20echoing%20the%20submitted%20URL.%20The%20same%20authenticated%20request%20to%20localhost%3A8081%2Fbanking%2F%20returned%20a%20data%3Atext%2Fhtml%20value%20containing%20the%20Bank%20of%20Ed%20page%2C%20and%20the%20equivalent%20127.0.0.1%20URL%20behaved%20the%20same%20way.%20The%20internal%20response%20is%20fetched%20content%2C%20not%20a%20static%20error%20message%2C%20and%20private-address%20filtering%20is%20absent.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Bearer%20token%20stored%20in%20script-readable%20localStorage%22%2C%22description%22%3A%22The%20banking%20authentication%20workflow%20and%20client%20code%20at%20%2Fbanking%2F%23%2Flogin%2C%20%2Fauth%2Flogin%2C%20%2Fapi%2Fadmin%2Fauth%2Flogin%2C%20%2Fbanking%2Fjs%2Fapi.js%3Fv%3D20260213-2%2C%20and%20%2Fbanking%2Fjs%2Fpages%2Fauth.js%20store%20the%20server-issued%20bearer%20token%20in%20localStorage%20under%20bankofed_token%2C%20alongside%20the%20user%20object%20in%20the%20login%20flow.%20The%20client%20reads%20it%20for%20API%20requests%2C%20so%20any%20JavaScript%20running%20in%20the%20application%20origin%20can%20read%20the%20token.%22%2C%22impact%22%3A%22An%20XSS%20vulnerability%20or%20compromised%20third-party%20script%20on%20the%20origin%20could%20steal%20the%20token%20and%20perform%20authenticated%20actions%20as%20the%20user.%22%2C%22likelihood%22%3A%22Medium%20in%20the%20observed%20context%2C%20increasing%20to%20high%20if%20script%20injection%20or%20third-party%20script%20compromise%20is%20present.%22%2C%22recommendation%22%3A%22Store%20session%20credentials%20in%20Secure%2C%20HttpOnly%2C%20SameSite%20cookies%20where%20possible.%20Rotate%20potentially%20exposed%20tokens%20and%20reduce%20the%20number%20and%20privileges%20of%20scripts%20trusted%20on%20the%20origin.%22%2C%22cvss_score%22%3A7.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fpages%2Fauth.js%22%2C%22evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fpages%2Fauth.js%20returned%20200.%20The%20confirmed%20script%20behavior%20stores%20the%20bearer%20token%20in%20script-readable%20localStorage.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fpages%2Fauth.js%20returned%20200.%22%2C%22response_evidence%22%3A%22The%20confirmed%20script%20behavior%20stores%20the%20bearer%20token%20in%20localStorage.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20live%20auth.js%20response%20passes%20res.data.token%20to%20Api.setToken%20on%20both%20login%20and%20registration.%20The%20same-origin%20api.js%20implementation%20writes%20that%20argument%20directly%20to%20localStorage%20under%20bankofed_token%2C%20and%20the%20banking%20entry%20page%20loads%20api.js%20before%20auth.js%20as%20executable%20JavaScript.%20I%20also%20verified%20with%20the%20provided%20admin%20session%20that%20the%20resulting%20bearer%20credential%20is%20accepted%20by%20GET%20%2Fapi%2Fprofile%2C%20so%20this%20is%20not%20dead%20code%20or%20a%20non-authentication%20value%3B%20HTTPS%20or%20a%20TLS-terminating%20proxy%20would%20not%20prevent%20same-origin%20JavaScript%20from%20reading%20localStorage.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202082%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-022%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Bearer%20token%20stored%20in%20script-readable%20localStorage%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%23%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20%2Fbanking%2Fjs%2Fapi.js%20returned%20client%20code%20where%20getToken()%20reads%20localStorage%20key%20bankofed_token%20and%20setToken(token)%20writes%20that%20key.%20GET%20%2Fbanking%2Fjs%2Fpages%2Fauth.js%20returned%20code%20that%20calls%20Api.setToken(res.data.token)%20and%20Api.setUser(res.data.user)%20after%20login.%20No%20login%20or%20account%20state%20was%20changed.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fapi.js%20and%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fpages%2Fauth.js.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22The%20returned%20client%20source%20explicitly%20uses%20localStorage%20for%20bankofed_token%20and%20stores%20res.data.token%20after%20login.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20live%20API%20client%20reads%20and%20writes%20the%20bearer%20credential%20under%20the%20script-readable%20localStorage%20key%20bankofed_token%2C%20and%20the%20live%20login%20handler%20stores%20res.data.token%20there%20after%20a%20successful%20login.%20This%20is%20not%20inert%20UI%20state%3A%20anonymous%20GET%20%2Fapi%2Fprofile%20returns%20401%2C%20while%20the%20provided%20admin%20session%20is%20accepted%20and%20returns%20a%20user%20profile%2C%20confirming%20that%20the%20corresponding%20credential%20authorizes%20protected%20data%20access.%20Several%20other%20supplied%20sessions%20were%20stale%20or%20missing%20a%20header%2C%20but%20that%20does%20not%20provide%20a%20benign%20explanation%20for%20the%20valid%20bearer-token%20flow.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202085%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-025%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Bearer%20token%20stored%20in%20script-readable%20localStorage%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20%2Fbanking%2Fjs%2Fapi.js%20defines%20getToken()%20and%20setToken(token)%20using%20localStorage.getItem('bankofed_token')%20and%20localStorage.setItem('bankofed_token'%2C%20token).%20GET%20%2Fbanking%2Fjs%2Fpages%2Fauth.js%20calls%20Api.setToken(res.data.token)%20after%20Api.login(data)%20succeeds.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20records%20a%20confirmed%20observation%20that%20the%20bearer%20token%20from%20this%20login%20workflow%20is%20stored%20in%20script-readable%20localStorage.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fapi.js%20and%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fpages%2Fauth.js%20returned%20the%20client%20source%20used%20by%20the%20login%20flow.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22api.js%20contains%20localStorage%20token%20access%2C%20and%20auth.js%20contains%20Api.login(data).then(function%20(res)%20%7B%20Api.setToken(res.data.token)%3B%20...%20%7D).%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20served%20api.js%20is%20live%20and%20defines%20both%20localStorage.setItem('bankofed_token'%2C%20token)%20and%20an%20Authorization%20Bearer%20header%20sourced%20from%20that%20value.%20The%20served%20auth.js%20calls%20Api.setToken(res.data.token)%20after%20login%2C%20and%20the%20reported%20POST%20login%20route%20is%20live%20and%20validates%20credentials.%20I%20also%20verified%20the%20bearer%20session%20protects%20sensitive%20account%20data%3A%20anonymous%20GET%20%2Fapi%2Fadmin%2Faccounts%20returns%20401%20while%20the%20provided%20admin%20session%20returns%20200%20with%20account%20numbers%2C%20balances%2C%20and%20owner%20data.%20These%20checks%20rule%20out%20a%20stale%20script%2C%20dead%20login%20path%2C%20or%20non-sensitive%20stored%20value.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202090%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-030%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Bearer%20token%20stored%20in%20script-readable%20localStorage%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fapi.js%3Fv%3D20260213-2%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22The%20API%20client%20defines%20setToken(token)%20as%20localStorage.setItem('bankofed_token'%2C%20token)%2C%20getToken()%20as%20localStorage.getItem('bankofed_token')%2C%20and%20adds%20an%20Authorization%3A%20Bearer%20%3Ctoken%3E%20header%20when%20a%20token%20is%20present.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20browser%20replay%20fetched%20this%20script%20and%20showed%20getToken()%20reading%20localStorage.getItem('bankofed_token')%20and%20setToken(token)%20calling%20localStorage.setItem('bankofed_token'%2C%20token).%20The%20shared%20tester%20ledger%20also%20records%20this%20as%20confirmed.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fapi.js%3Fv%3D20260213-2%20with%20Range%3A%20bytes%3D0-1500%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20206%3B%20the%20response%20contains%20the%20token%20storage%20helpers%20and%20the%20Authorization%20header%20construction.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnResponse%20source%20contains%20localStorage.getItem('bankofed_token')%20and%20localStorage.setItem('bankofed_token'%2C%20token).%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20reported%20asset%20is%20live%20and%20returns%20the%20exact%20token%20storage%20and%20retrieval%20code%2C%20including%20localStorage.setItem('bankofed_token'%2C%20token)%2C%20localStorage.getItem('bankofed_token')%2C%20and%20an%20Authorization%3A%20Bearer%20header.%20This%20is%20not%20an%20unused%20static%20match%3A%20the%20protected%20%2Fapi%2Fprofile%20endpoint%20returned%20401%20anonymously%20and%20returned%20Amelia%20Chen's%20profile%20with%20the%20provided%20admin%20session%2C%20whose%20request%20included%20Authorization.%20I%20also%20checked%20the%20TLS%20explanation%3A%20HTTPS%20on%20port%208081%20fails%20with%20a%20protocol%20error%20and%20localhost%3A443%20has%20no%20listener%2C%20so%20there%20is%20no%20evidence%20that%20this%20direct%20HTTP%20asset%20is%20only%20an%20internal%20hop%20behind%20TLS.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202107%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-047%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Bearer%20token%20stored%20in%20script-readable%20localStorage%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fauth%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22Prior%20direct%20browser%20and%20workflow%20evidence%20confirmed%20that%20a%20bearer%20token%20from%20the%20login%20workflow%20is%20stored%20in%20script-readable%20localStorage.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22The%20login%20workflow%20was%20associated%20with%20http%3A%2F%2Flocalhost%3A8081%2Fauth%2Flogin.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22Confirmed%20claim%20from%20prior%20direct%20browser%2Fworkflow%20evidence%3A%20a%20bearer%20token%20was%20stored%20in%20script-readable%20localStorage.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20reported%20%2Fauth%2Flogin%20path%20is%20a%20client-side%20route%20under%20%2Fbanking%2C%20so%20its%20direct%20404%20does%20not%20explain%20away%20the%20finding.%20The%20live%20API%20client%20stores%20the%20login%20token%20in%20localStorage%20and%20sends%20that%20value%20as%20an%20Authorization%20Bearer%20credential%3B%20the%20live%20login%20handler%20calls%20Api.setToken(res.data.token).%20An%20anonymous%20request%20to%20%2Fapi%2Fprofile%20is%20rejected%2C%20while%20the%20listed%20admin%20session%20reaches%20the%20same%20endpoint%20with%20status%20200%2C%20showing%20that%20the%20credential%20is%20operational.%20HTTPS%20on%20ports%20443%2C%208443%2C%20and%208081%20did%20not%20provide%20an%20innocent%20TLS-fronting%20explanation%2C%20and%20no%20benign%20interpretation%20of%20the%20storage%20code%20remains.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fapi.js%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Cleartext%20HTTP%20used%20across%20the%20banking%20application%20and%20APIs%22%2C%22description%22%3A%22The%20service%20at%20http%3A%2F%2Flocalhost%3A8081%20exposes%20web%20pages%20and%20APIs%20over%20plain%20HTTP%20without%20requiring%20HTTPS%20or%20redirecting%20HTTP%20clients.%20This%20includes%20the%20administrative%20login%20page%20at%20%2Fadmin%2F%23%2Flogin%20and%20the%20authenticated%20customer%20endpoint%20at%20%2Fapi%2Fadmin%2Fcustomers%2F16%2C%20which%20returns%20sensitive%20customer%20and%20account%20data.%22%2C%22impact%22%3A%22An%20observer%20on%20the%20network%20path%20can%20read%20the%20exported%20account%20data%20in%20transit.%20Password%20hashes%20may%20support%20offline%20password%20attacks%2C%20and%20exposed%20personal%20data%20creates%20a%20privacy%20risk.%22%2C%22likelihood%22%3A%22High%20on%20network%20paths%20where%20traffic%20to%20the%20HTTP%20service%20can%20be%20observed.%22%2C%22recommendation%22%3A%22Serve%20the%20application%20and%20export%20endpoint%20only%20over%20HTTPS.%20Redirect%20or%20reject%20HTTP%2C%20enable%20HSTS%20at%20the%20TLS%20termination%20point%2C%20and%20remove%20password%20hashes%20and%20unnecessary%20sensitive%20fields%20from%20the%20export.%22%2C%22cvss_score%22%3A8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2F%22%2C%22evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%20returned%20an%20export%20containing%20password_hash%2C%20email%2C%20address_line1%2C%20suburb%2C%20state%2C%20postcode%2C%20and%20phone%20over%20the%20http%3A%2F%2F%20scheme.%20A%20follow-up%20HEAD%20request%20to%20the%20same%20URL%20returned%20HTTP%20200%2C%20confirming%20the%20route%20is%20served%20over%20cleartext%20HTTP.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%20returned%20the%20sensitive%20export%20over%20the%20http%3A%2F%2F%20scheme.%20Follow-up%3A%20HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%20with%20use_session%3Danonymous%2C%20obligation_id%3D7015.%22%2C%22response_evidence%22%3A%22The%20GET%20response%20contained%20fields%20including%20password_hash%2C%20email%2C%20address_line1%2C%20suburb%2C%20state%2C%20postcode%2C%20and%20phone.%20The%20HEAD%20response%20was%20HTTP%20200%20at%20the%20same%20http%3A%2F%2F%20URL.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20live%20authenticated%20GET%20over%20http%3A%2F%2F%20returned%20status%20200%20with%20password_hash%20and%20personal%20fields%20in%20the%20response%20body%2C%20so%20this%20is%20not%20evidence%20from%20a%20static%20log%20or%20template.%20I%20checked%20the%20default%20HTTPS%20port%20and%20alternate%20port%208443%2C%20and%20no%20TLS%20service%20was%20reachable%3B%20HTTPS%20on%20port%208081%20returned%20a%20TLS%20wrong-version%20error%2C%20while%20a%20live%20HEAD%20on%20the%20reported%20HTTP%20route%20returned%20200%20with%20no%20redirect%20or%20HSTS%20header.%20The%20export%20is%20therefore%20served%20directly%20over%20cleartext%20HTTP%20with%20no%20verified%20TLS%20front%20door%20to%20provide%20the%20innocent%20reverse-proxy%20explanation.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202062%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-002%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Accounts%20API%20accepts%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20returned%20a%20shared%20200%20baseline.%20HEAD%20over%20HTTP%20returned%20401%20without%20redirecting.%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20failed%20TLS%20negotiation%20with%20SSL%3A%20WRONG_VERSION_NUMBER%2C%20confirming%20the%20endpoint%20speaks%20plain%20HTTP.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20records%20a%20direct%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20response%20of%20200%20and%20marks%20the%20cleartext-HTTP%20claim%20confirmed.%20The%20corresponding%20HTTPS%20probe%20returned%20unknown.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20authenticated%20baseline%20recorded%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20-%3E%20201.%20A%20new%20HEAD%20request%20to%20the%20HTTP%20endpoint%20returned%20401%2C%20while%20the%20corresponding%20HEAD%20request%20to%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20failed%20with%20'%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number'.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20records%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20-%3E%20200%20and%20marks%20the%20cleartext%20acceptance%20as%20confirmed.%20The%20replayed%20browser%20request%20to%20the%20same%20HTTP%20URL%20returned%20401%2C%20showing%20the%20endpoint%20is%20reachable%20over%20HTTP%20even%20when%20authentication%20is%20missing.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20records%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20-%3E%20201%20(baseline%20strength%201)%20and%20HEAD%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20-%3E%20unknown.%20This%20shows%20the%20sensitive%20account%20operation%20is%20available%20over%20cleartext%20HTTP%20while%20TLS%20availability%20was%20not%20observed.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%3B%20HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%3B%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnHEAD%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%3B%20HEAD%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20over%20HTTP%20returned%20status%20200%20in%20the%20shared%20baseline.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20returned%20HTTP%20201%20according%20to%20the%20shared%20tester%20ledger.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22Shared%20baseline%3A%20HTTP%20GET%20status%20200.%20HTTP%20HEAD%20status%20401%20with%20no%20redirect.%20HTTPS%20request%20failed%20during%20TLS%20negotiation%20with%20WRONG_VERSION_NUMBER.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20200%3B%20the%20shared%20ledger%20separately%20records%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20as%20unknown.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20endpoint%3A%20401.%20HTTPS%20endpoint%3A%20TLS%20failure%2C%20WRONG_VERSION_NUMBER.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnShared%20ledger%3A%20successful%20HTTP%20response%2C%20status%20200.%20Browser%20replay%3A%20HTTP%20response%20status%20401%20with%20an%20authorization%20error%20body.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20201%20baseline%20response%20recorded%20for%20the%20account%20creation%20operation%3B%20HTTPS%20HEAD%20was%20recorded%20as%20unknown.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20direct%20endpoint%20consistently%20accepts%20plain%20HTTP%20and%20returns%20an%20application%20response%20with%20no%20redirect%20or%20Strict-Transport-Security%20header.%20I%20checked%20HTTPS%20on%20the%20host's%20standard%20port%20using%20both%20localhost%20and%20127.0.0.1%2C%20and%20also%20checked%208443%3B%20none%20exposed%20a%20reachable%20TLS%20front%20end.%20The%20available%20evidence%20gives%20no%20concrete%20benign%20explanation%20such%20as%20a%20TLS-terminating%20proxy%20for%20this%20service%2C%20so%20the%20cleartext%20transport%20finding%20remains%20confirmed.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202063%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-003%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22SSO%20endpoint%20accepts%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%20returned%20an%20HTTP%20401%20JSON%20response%2C%20while%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%20failed%20with%20'%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number'.%20The%20shared%20authenticated%20baseline%20for%20this%20operation%20is%20HTTP%20200.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnShared%20tester%20ledger%3A%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%20returned%20200%2C%20and%20the%20ledger%20claim%20is%20confirmed%20-%20SSO%20endpoint%20accepts%20cleartext%20HTTP.%20The%20HTTPS%20comparison%20was%20unknown%2C%20so%20HTTPS%20enforcement%20could%20not%20be%20established.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20baseline%20recorded%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%20-%3E%20200.%20The%20preserved%20browser%20state%20recorded%20the%20same%20HTTP%20URL%20returning%20401%20rather%20than%20redirecting.%20A%20follow-up%20request%20to%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%20failed%20with%20SSL%20WRONG_VERSION_NUMBER%2C%20showing%20the%20service%20is%20speaking%20plain%20HTTP%20on%20this%20port.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%3B%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso%3B%20follow-up%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Finsurance%2Fsso.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20JSON%20response%20over%20HTTP%3B%20HTTPS%20connection%20failed%20with%20TLS%20wrong-version%20error.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20200%20from%20the%20SSO%20endpoint.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20baseline%20returned%20200%3B%20browser%20HTTP%20request%20returned%20401%20with%20an%20application%20JSON%20error%3B%20HTTPS%20failed%20with%20%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20valid%20admin%20session%20reproduced%20the%20documented%20HTTP%20200%20and%20the%20response%20contains%20a%20generated%20SSO%20URL%20beginning%20with%20http%3A%2F%2F%20and%20carrying%20a%20signed%20token%20in%20the%20query%20string%2C%20so%20cleartext%20is%20used%20for%20the%20SSO%20handoff%20itself.%20I%20checked%20the%20standard%20HTTPS%20entry%20point%20on%20port%20443%2C%20the%20explicit%20IPv4%20loopback%20on%20443%2C%20and%20common%20alternate%20TLS%20ports%208443%20and%208080%3B%20none%20exposed%20a%20TLS-terminating%20front%20end%2C%20and%20port%2080%20was%20also%20unreachable.%20The%20response%20is%20therefore%20not%20explained%20by%20a%20reachable%20HTTPS%20proxy%20in%20front%20of%20%3A8081.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202064%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-004%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Financial%20data%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2F%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20GET%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2F%20returned%20HTTP%20200%20and%20included%20'Total%20Balance%20%2442%2C816.50'%2C%20'Everyday%20Account%20062-001%20%5C%5Cu00b7%2012345678'%2C%20'%248%2C241.50'%2C%20'Savings%20062-001%20%5C%5Cu00b7%2087654321'%2C%20and%20'%2434%2C575.00'.%20A%20follow-up%20HEAD%20request%20also%20returned%20HTTP%20200.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20and%20HEAD%20requests%20used%20the%20literal%20http%3A%2F%2Flocalhost%3A8081%2F%20URL.%20The%20anonymous%20GET%20used%20Authorization%3A%20none%20and%20Cookies%3A%20none.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20for%20the%20cleartext%20endpoint%3B%20the%20GET%20response%20body%20contains%20financial%20balances%20and%20account%20identifiers.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22false_positive%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20reported%20strings%20are%20hard-coded%20in%20the%20anonymous%20root%20page's%20marketing%20hero%20preview%20for%20%5C%5Cu201cThe%20Bank%20of%20Ed%2C%5C%5Cu201d%20alongside%20public%20copy%20such%20as%20%5C%5Cu201cNow%20accepting%20customers%2C%5C%5Cu201d%20%5C%5Cu201cGet%20Started%20Free%2C%5C%5Cu201d%20and%20%5C%5Cu201cAccount%20created.%5C%5Cu201d%20The%20live%20HTML%20serves%20these%20fixed%20illustrative%20values%20as%20presentation%20content%2C%20with%20no%20user%20identity%2C%20session%2C%20or%20account%20lookup%20involved%2C%20so%20the%20scanner%20misclassified%20demo%20landing-page%20data%20as%20a%20user's%20financial%20data.%20HTTPS%20is%20also%20not%20available%20on%20port%20443%2C%20but%20that%20does%20not%20make%20this%20public%20static%20marketing%20preview%20sensitive%20financial%20information.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202065%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-005%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Admin%20accounts%20API%20is%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22The%20supplied%20authenticated%20baseline%20returned%20200%20for%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20.%20An%20HTTPS%20request%20to%20the%20same%20port%20failed%20with%20SSL%20WRONG_VERSION_NUMBER%2C%20showing%20that%20port%208081%20serves%20plain%20HTTP.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20records%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20returning%20200%2C%20and%20separately%20records%20the%20HTTPS%20variant%20as%20unknown.%20The%20current%20browser%20replay%20also%20used%20the%20cleartext%20HTTP%20URL%20and%20captured%20a%20401%20response%20from%20that%20HTTP%20endpoint.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20baseline%20records%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20-%3E%20200.%20A%20bounded%20follow-up%20HEAD%20request%20to%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20failed%20with%20'%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number'%2C%20showing%20that%20the%20service%20on%20this%20port%20is%20cleartext%20HTTP%20rather%20than%20HTTPS.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20-%3E%20200%20in%20the%20supplied%20baseline.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20-%3E%20200%20from%20the%20supplied%20tester%20ledger%3B%20HEAD%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20was%20used%20as%20the%20transport%20follow-up.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTPS%20on%20the%20same%20port%20failed%20with%20SSL%20WRONG_VERSION_NUMBER.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnShared%20ledger%3A%20HTTP%20request%20returned%20200.%20Browser%20replay%3A%20HTTP%20request%20returned%20401%20with%20an%20unauthorized%20JSON%20response.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20baseline%3A%20200.%20HTTPS%20follow-up%3A%20TLS%20failure%20'%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number%20(_ssl.c%3A1081)'.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20valid%20admin%20session%20returned%20account%20numbers%20and%20balances%20over%20HTTP%20from%20localhost%3A8081.%20HTTPS%20on%20the%20same%20port%20failed%20with%20WRONG_VERSION_NUMBER%2C%20and%20HTTPS%20on%20localhost%3A443%20and%20localhost%3A8443%20was%20unavailable%3B%20the%20Apache%20response%20also%20showed%20no%20redirect%20or%20HSTS%20header.%20The%20loopback%20URL%20therefore%20appears%20to%20be%20the%20only%20reachable%20service%20endpoint%2C%20with%20no%20evidence%20of%20a%20TLS-terminating%20proxy%20protecting%20this%20route.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202067%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-007%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Address-book%20API%20accepts%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%20returned%20HTTP%20200%20in%20the%20supplied%20authenticated%20baseline.%20Follow-up%20anonymous%20requests%20to%20the%20same%20HTTP%20URL%20returned%20HTTP%20401%20with%20UNAUTHORIZED%2C%20confirming%20the%20authentication%20boundary%20while%20showing%20that%20authenticated%20responses%20are%20available%20over%20cleartext%20HTTP.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20records%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%20-%3E%20200%20for%20the%20authenticated%20baseline%20and%20separately%20confirms%3A%20Address-book%20API%20accepts%20cleartext%20HTTP.%20Anonymous%20access%20returned%20401%2C%20so%20the%20issue%20is%20transport%20protection%20rather%20than%20an%20authentication%20bypass.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnShared%20tester%20evidence%20recorded%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%20-%3E%20200%20and%20confirmed%20that%20the%20address-book%20API%20accepts%20cleartext%20HTTP.%20The%20HTTPS%20follow-up%20to%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%20failed%20with%20SSL%20WRONG_VERSION_NUMBER%2C%20indicating%20that%20this%20listener%20is%20serving%20plain%20HTTP%20rather%20than%20TLS.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%20-%3E%20200%20(shared%20authenticated%20baseline).%20Anonymous%20confirmation%20used%20GET%20over%20the%20same%20http%3A%2F%2F%20URL.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%20using%20the%20authenticated%20session%3B%20recorded%20result%3A%20HTTP%20200.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%20-%3E%20200%20(shared%20baseline)%3B%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%20(bounded%20scheme%20follow-up).%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22Anonymous%20GET%20returned%20HTTP%20401%20with%20UNAUTHORIZED.%20The%20shared%20authenticated%20baseline%20establishes%20that%20the%20same%20operation%20is%20available%20over%20HTTP%20when%20authenticated.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnRecorded%20response%20status%3A%20HTTP%20200%20over%20an%20http%3A%2F%2F%20URL.%20The%20ledger%20also%20records%20anonymous%20GET%20as%20HTTP%20401.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20baseline%3A%20200.%20HTTPS%20follow-up%3A%20Request%20failed%3A%20%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number%20(_ssl.c%3A1081).%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20exact%20HTTP%20endpoint%20returned%20status%20200%20and%20address-book%20records%20when%20replayed%20with%20the%20supplied%20%60admin%60%20session%2C%20including%20the%20distinctive%20payee%20%60Pyrmont%20Properties%60.%20I%20checked%20the%20standard%20HTTPS%20endpoint%20on%20port%20443%2C%20alternate%20TLS%20ports%208443%20and%208080%2C%20and%20HTTPS%20directly%20on%20port%208081%3B%20no%20TLS%20front%20end%20was%20reachable%2C%20and%20port%208081%20explicitly%20spoke%20plain%20HTTP.%20The%20response%20had%20no%20redirect%20or%20HSTS%20header%2C%20so%20there%20is%20no%20concrete%20benign%20explanation%20for%20treating%20this%20authenticated%20data%20path%20as%20protected%20in%20transit.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202069%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-009%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Transactions%20endpoint%20is%20available%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20authenticated%20GET%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%20returned%20HTTP%20200.%20The%20equivalent%20HTTPS%20request%20failed%20with%20%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnShared%20tester%20evidence%20shows%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%20returned%20HTTP%20200.%20The%20ledger%20also%20records%20the%20cleartext%20HTTP%20exposure%20as%20confirmed.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnShared%20tester%20evidence%20confirms%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%20returned%20200%20with%20transaction%20data.%20The%20ledger%20also%20records%20the%20claim%20that%20the%20endpoint%20is%20available%20over%20cleartext%20HTTP.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%3Faccount_id%3D1%26page%3D1%26per_page%3D15%20returned%20200%20in%20the%20authenticated%20baseline%3B%20the%20same%20URL%20with%20https%20was%20then%20requested%20once.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20baseline%20status%20200%3B%20HTTPS%20follow-up%20failed%20with%20TLS%20WRONG_VERSION_NUMBER.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20200%20from%20the%20cleartext%20HTTP%20endpoint.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20200%20response%20containing%20transaction%20data%20over%20the%20http%3A%2F%2F%20scheme.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20valid%20admin%20session%20returned%20HTTP%20200%20and%20transaction%20records%20over%20cleartext%20HTTP%20on%20port%208081.%20The%20equivalent%20HTTPS%20request%20on%208081%20failed%20with%20TLS%20WRONG_VERSION_NUMBER%2C%20and%20HTTPS%20listeners%20on%20localhost%20ports%20443%20and%208443%20were%20unreachable%3B%20the%20response%20also%20had%20no%20Strict-Transport-Security%20header.%20This%20rules%20out%20the%20plausible%20explanation%20that%208081%20is%20merely%20a%20TLS-fronted%20endpoint%20or%20that%20the%20request%20is%20harmless%20because%20it%20is%20unauthenticated.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202071%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-011%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Bearer%20tokens%20transmitted%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fsystem%2Fsettings%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20%2Fbanking%2Fjs%2Fapi.js%3Fv%3D20260213-2%20returned%20client%20code%20that%20adds%20Authorization%3A%20Bearer%20tokens.%20HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fsystem%2Fsettings%20returned%20HTTP%20401%20directly%20over%20HTTP%20with%20no%20HTTPS%20redirect.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnDirect%20deployment%20evidence%3A%20the%20assigned%20focus%20URL%20is%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fsystem%2Fsettings.%20Shared%20probe%20claim%3A%20confirmed%20-%20Bearer%20tokens%20transmitted%20over%20cleartext%20HTTP.%20The%20route%20responds%20to%20HTTP%20requests%20and%20returned%20401%20for%20anonymous%20GET%2C%20showing%20the%20HTTP%20deployment%20is%20active.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fsystem%2Fsettings%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fsystem%2Fsettings%20over%20cleartext%20HTTP%3B%20anonymous%20request%20returned%20401.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20with%20no%20HTTPS%20redirect.%20GET%20%2Fbanking%2Fjs%2Fapi.js%3Fv%3D20260213-2%20returned%20the%20Bearer-token%20request%20code.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20401%20with%20JSON%20error%3A%20Missing%20or%20invalid%20Authorization%20header.%20Shared%20evidence%20confirms%20bearer%20tokens%20are%20transmitted%20over%20cleartext%20HTTP.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22false_positive%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22Validation%20could%20not%20reproduce%20unauthorized%20access.%20Alternate%20users%20received%20an%20access%20denial%2C%20login%20response%2C%20generic%20application%20shell%2C%20or%20no%20protected%20content%20signal.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202072%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-012%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Banking%20application%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22Anonymous%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20returned%20HTTP%20200%20with%20the%20title%20'The%20Bank%20of%20Ed%20-%20Internet%20Banking'.%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20failed%20with%20'%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number'%2C%20showing%20that%20secure%20transport%20is%20not%20working%20on%20this%20port.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnDirect%20HTTP%20probe%20to%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20returned%20HTTP%20200%20and%20the%20full%20banking%20HTML%20document.%20The%20shared%20tester%20ledger%20also%20records%20the%20HTTPS%20probe%20as%20unknown%20and%20confirms%20the%20cleartext%20HTTP%20claim.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20returned%20HTTP%20200.%20The%20public%20api.js%20source%20shows%20that%20when%20a%20token%20exists%20it%20sends%20%60Authorization%3A%20Bearer%20%60%20plus%20the%20token%2C%20and%20calls%20the%20relative%20%60%2Fapi%60%20base.%20The%20target%20and%20focus%20route%20use%20the%20http%3A%2F%2F%20scheme.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20saved%20HTTP%20baseline%20recorded%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20responses%20with%20status%20200%20and%20206.%20A%20follow-up%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20failed%20with%20SSL%20error%20WRONG_VERSION_NUMBER.%20The%20replayed%20browser%20loaded%20the%20banking%20HTML%20and%20JavaScript%20over%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%3B%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20over%20HTTP%20returned%20200%2F206%20in%20the%20shared%20baseline.%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20was%20attempted%20as%20the%20TLS%20comparison.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20for%20the%20cleartext%20banking%20page%3B%20HTTPS%20request%20failed%20during%20TLS%20negotiation.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20200%20and%20banking%20HTML%3B%20api.js%20loaded%20from%20the%20same%20HTTP%20origin%20uses%20a%20bearer%20Authorization%20header%20for%20relative%20%2Fapi%20calls.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20served%20the%20banking%20application.%20The%20HTTPS%20request%20failed%3A%20%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number%20(_ssl.c%3A1081).%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20exact%20affected%20URL%20still%20returns%20the%20banking%20HTML%20anonymously%20over%20cleartext%20HTTP%20with%20status%20200%2C%20no%20Location%20header%2C%20and%20no%20HSTS%20header.%20The%20corresponding%20HTTPS%20request%20on%20port%208081%20independently%20fails%20with%20TLS%20WRONG_VERSION_NUMBER%2C%20while%20HTTPS%20on%20ports%20443%20and%208443%20is%20unreachable%2C%20so%20the%20reverse-proxy%2FTLS-termination%20explanation%20is%20not%20supported.%20The%20response%20is%20the%20claimed%20banking%20page%2C%20so%20this%20is%20not%20a%20generic%20or%20unrelated%20public%20page.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202073%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-013%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Admin%20credentials%20transmitted%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22Browser%20traffic%20recorded%20a%20POST%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20over%20HTTP%20with%20credentials%20in%20the%20request%20body.%20The%20server%20returned%20HTTP%20200%20with%20%5C%5C%5C%22Login%20successful%5C%5C%5C%22.%20The%20same%20session%20loaded%20the%20admin%20shell%20from%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%20with%20HTTP%20200.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20preserved%20admin%20page%20loaded%20at%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Flogin.%20A%20browser%20probe%20submitted%20a%20username%20and%20password%20and%20captured%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20-%3E%20401%20with%20request%20body%20%7B%5C%5C%5C%22username%5C%5C%5C%22%3A%5C%5C%5C%22admin%5C%5C%5C%22%2C%5C%5C%5C%22password%5C%5C%5C%22%3A%5C%5C%5C%22%3Csvg%2Fonload%3Dalert(1)%3E%5C%5C%5C%22%7D.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20over%20HTTP%20with%20credentials%20in%20the%20request%20body.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20over%20http%3A%2F%2Flocalhost%3A8081%20with%20a%20username%20and%20password%20in%20the%20JSON%20request%20body.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20response%3A%20Login%20successful.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20401%20with%20generic%20INVALID_CREDENTIALS%3B%20the%20issue%20is%20the%20cleartext%20transport%20of%20the%20request%2C%20independent%20of%20authentication%20success.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20admin%20shell%20is%20served%20with%20HTTP%20200%20and%20no%20HTTPS%20redirect%2C%20and%20the%20login%20endpoint%20accepts%20a%20credential-shaped%20POST%20directly%20over%20HTTP.%20HTTPS%20on%20port%20443%20was%20unavailable%2C%20HTTPS%20on%20port%208081%20returned%20a%20TLS%20wrong-version%20error%2C%20and%20the%20conventional%20HTTPS%20port%208443%20was%20also%20unavailable.%20The%20cleartext%20transport%20is%20therefore%20reachable%20and%20there%20is%20no%20live%20TLS%20listener%20or%20redirect%20providing%20a%20benign%20reverse-proxy%20explanation.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202074%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-014%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Admin%20login%20accepts%20credentials%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20direct%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20sent%20JSON%20credentials%20over%20HTTP%20and%20was%20processed%20by%20the%20server%2C%20which%20returned%20HTTP%20401.%20The%20request%20URL%20remained%20HTTP.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20browser%20replay%20loaded%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Flogin%20with%20HTTP%20200.%20The%20public%20admin%20API%20client%20defines%20POST%20%2Fapi%2Fadmin%2Fauth%2Flogin.%20A%20bounded%20POST%20to%20that%20URL%20over%20HTTP%20returned%20HTTP%20401%20INVALID_CREDENTIALS%2C%20confirming%20the%20login%20operation%20is%20active%20on%20the%20cleartext%20origin.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnA%20direct%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20dummy%20credentials%20returned%20HTTP%20401%20INVALID_CREDENTIALS%2C%20confirming%20the%20credential-bearing%20login%20endpoint%20is%20active%20on%20an%20unencrypted%20HTTP%20URL.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20supplied%20tester%20ledger%20records%20a%20confirmed%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20accepting%20credentials%20over%20cleartext%20HTTP.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20assigned%20endpoint%20uses%20the%20http%3A%2F%2F%20scheme.%20A%20direct%20POST%20with%20JSON%20credentials%20returned%20HTTP%20401%20INVALID_CREDENTIALS%2C%20showing%20that%20credentials%20are%20accepted%20and%20processed%20on%20the%20cleartext%20route.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20Content-Type%3A%20application%2Fjson%20and%20a%20JSON%20username%2Fpassword%20body.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20a%20non-real%20username%20and%20password%20over%20HTTP.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%3B%20JSON%20body%20contained%20username%20and%20password%20fields%20using%20non-real%20probe%20values.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20over%20http%3A%2F%2F%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20with%20Content-Type%3A%20application%2Fjson%20and%20a%20username%2Fpassword%20JSON%20body.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20with%20application%20response%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22INVALID_CREDENTIALS%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Invalid%20username%20or%20password.%5C%5C%5C%22%7D%7D%3B%20the%20request%20was%20handled%20over%20the%20cleartext%20HTTP%20endpoint.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20401%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22INVALID_CREDENTIALS%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Invalid%20username%20or%20password.%5C%5C%5C%22%7D%7D%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnThe%20login%20operation%20was%20reachable%20and%20returned%20an%20authentication%20response%20over%20the%20same%20cleartext%20transport.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20401%20with%20%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22INVALID_CREDENTIALS%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Invalid%20username%20or%20password.%5C%5C%5C%22%7D%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20exact%20HTTP%20login%20route%20accepted%20a%20JSON%20username%20and%20password%20and%20returned%20an%20application-level%20INVALID_CREDENTIALS%20response%20with%20no%20redirect%20or%20HTTPS-required%20response%2C%20so%20the%20body%20was%20processed%20over%20cleartext%20HTTP.%20I%20checked%20HTTPS%20on%20the%20affected%20port%20and%20on%20ports%20443%2C%208443%2C%20and%208080%3B%20the%20affected%20port%20spoke%20plain%20HTTP%20and%20the%20other%20TLS%20endpoints%20were%20unavailable.%20The%20standard%20HTTP%20port%20was%20also%20unavailable%2C%20so%20I%20found%20no%20TLS-terminating%20front%20door%20or%20transport%20enforcement%20that%20would%20provide%20an%20innocent%20explanation.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202075%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-015%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Admin%20customer%20API%20is%20available%20only%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dzoe%26per_page%3D15%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20direct%20request%20to%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dzoe%26per_page%3D15%20failed%20with%20%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number.%20The%20corresponding%20operation%20is%20addressed%20over%20http%3A%2F%2Flocalhost%3A8081%2F%2C%20and%20no%20HTTPS%20response%20was%20available.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20records%20a%20confirmed%20result%20that%20the%20admin%20customer%20API%20is%20available%20only%20over%20cleartext%20HTTP.%20The%20anonymous%20request%20to%20the%20HTTP%20URL%20returned%20401%2C%20showing%20the%20route%20is%20reachable%20over%20HTTP.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20HTTP%20baseline%20reached%20GET%20%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dzoe%26per_page%3D15%20and%20returned%20401%20UNAUTHORIZED.%20The%20shared%20ledger%20records%20the%20HTTPS%20request%20as%20unknown%20and%20includes%20the%20confirmed%20claim%3A%20Admin%20customer%20API%20is%20available%20only%20over%20cleartext%20HTTP.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dzoe%26per_page%3D15.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fsearch%3Dzoe%26per_page%3D15%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22TLS%20negotiation%20failed%20with%20WRONG_VERSION_NUMBER%3B%20no%20HTTPS%20response%20was%20available.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20request%20reached%20the%20admin%20API%20over%20cleartext%20and%20returned%20401%3B%20the%20ledger%20claim%20marks%20cleartext%20HTTP%20availability%20as%20confirmed.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20401%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22UNAUTHORIZED%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%5C%5C%22%7D%7D%3B%20shared%20ledger%20confirms%20no%20working%20HTTPS%20variant.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22false_positive%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20scanner%20is%20testing%20a%20loopback%20backend%20URL%2C%20not%20a%20client-facing%20HTTPS%20origin.%20The%20admin%20request%20succeeds%20only%20on%20the%20local%20HTTP%20listener%20at%20127.0.0.1%3A8081%3B%20HTTPS%20on%20that%20port%20returns%20WRONG_VERSION_NUMBER%2C%20while%20the%20standard%2Ffront-door%20ports%20443%2C%208443%2C%208080%2C%20and%2080%20have%20no%20listener.%20This%20is%20a%20local%20development%2Ftest%20service%20intentionally%20exposed%20over%20HTTP%2C%20so%20the%20probe%20does%20not%20show%20that%20a%20deployed%20user-facing%20API%20lacks%20TLS.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202076%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-016%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Login%20credentials%20sent%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20bounded%20POST%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20used%20JSON%20email%20and%20password%20fields%20and%20received%20HTTP%20401%20USER_NOT_FOUND.%20This%20confirms%20that%20the%20live%20login%20handler%20processed%20credential-bearing%20input%20over%20the%20HTTP%20origin.%20The%20public%20authentication%20client%20also%20calls%20POST%20%2Fapi%2Fauth%2Flogin%20on%20the%20current%20HTTP%20origin.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnDirect%20probe%3A%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20synthetic%20credentials%20returned%20HTTP%20401%20and%20USER_NOT_FOUND.%20Both%20the%20focus%20page%20and%20the%20login%20API%20use%20the%20http%3A%2F%2F%20scheme.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20contains%20the%20confirmed%20claim%3A%20%5C%5C%5C%22Login%20credentials%20sent%20over%20cleartext%20HTTP.%5C%5C%5C%22%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%3B%20Content-Type%3A%20application%2Fjson%3B%20body%20contained%20synthetic%20email%20and%20password%20fields.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20over%20HTTP%20with%20JSON%20credentials%3A%20deep-worker-invalid%40example.invalid%20%2F%20wrong-password-2026.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20was%20used%20for%20login%20attempts%20over%20an%20http%3A%2F%2F%20URL.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20with%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22USER_NOT_FOUND%5C%5C%5C%22%2C...%7D%7D%20confirms%20the%20live%20login%20handler%20processed%20the%20request%20over%20the%20HTTP%20origin.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20401%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22USER_NOT_FOUND%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22No%20account%20found%20with%20this%20email%20address.%5C%5C%5C%22%7D%7D%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnConfirmed%20claim%20from%20prior%20direct%20traffic%3A%20login%20credentials%20were%20sent%20over%20cleartext%20HTTP.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20exact%20reported%20port%20rejected%20HTTPS%20with%20a%20TLS%20version%20error%2C%20and%20https%3A%2F%2Flocalhost%2Fapi%2Fauth%2Flogin%20on%20the%20standard%20TLS%20port%20was%20unreachable%2C%20so%20I%20found%20no%20TLS-terminating%20alternate%20origin.%20A%20fresh%20anonymous%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20returned%20401%20USER_NOT_FOUND%20and%20the%20response%20had%20no%20HTTPS%20redirect%20or%20Strict-Transport-Security%20header%2C%20confirming%20that%20the%20live%20handler%20processes%20credential-bearing%20JSON%20over%20cleartext%20HTTP.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202078%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-018%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Login%20credentials%20transmitted%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20direct%20probe%20sent%20a%20POST%20request%20with%20email%20and%20password%20JSON%20fields%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin.%20The%20server%20processed%20the%20request%20and%20returned%20HTTP%20401%20with%20USER_NOT_FOUND%2C%20confirming%20that%20credentials%20are%20accepted%20over%20cleartext%20HTTP.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnA%20direct%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20reached%20the%20login%20handler%20and%20returned%20HTTP%20422%20with%20validation%20errors%20for%20the%20email%20and%20password%20fields.%20The%20client%20API%20code%20calls%20the%20same-origin%20%2Fapi%2Fauth%2Flogin%20route%20and%20sends%20JSON%20credentials.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5C%5CnContent-Type%3A%20application%2Fjson%5C%5Cn%7B%5C%5C%5C%22email%5C%5C%5C%22%3A%5C%5C%5C%22probe.invalid%40example.test%5C%5C%5C%22%2C%5C%5C%5C%22password%5C%5C%5C%22%3A%5C%5C%5C%22Wrong-Only-For-Bounded-Probe-9f3c%5C%5C%5C%22%7D%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20Content-Type%3A%20application%2Fjson%20and%20body%20%7B%7D%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%5C%5Cn%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22USER_NOT_FOUND%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22No%20account%20found%20with%20this%20email%20address.%5C%5C%5C%22%7D%7D%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20422%3B%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22VALIDATION_ERROR%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Validation%20failed%5C%5C%5C%22%2C%5C%5C%5C%22details%5C%5C%5C%22%3A%7B%5C%5C%5C%22email%5C%5C%5C%22%3A%5B%5C%5C%5C%22The%20email%20field%20is%20required.%5C%5C%5C%22%5D%2C%5C%5C%5C%22password%5C%5C%5C%22%3A%5B%5C%5C%5C%22The%20password%20field%20is%20required.%5C%5C%5C%22%5D%7D%7D%7D%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20HTTP%20listener%20independently%20accepted%20a%20JSON%20email%20and%20password%20and%20returned%20the%20application-level%20USER_NOT_FOUND%20response%2C%20so%20this%20was%20not%20a%20redirect%20or%20a%20transport%20error.%20HTTPS%20was%20unavailable%20on%20port%20443%20and%20port%208443%2C%20and%20using%20TLS%20on%20port%208081%20returned%20WRONG_VERSION_NUMBER%3B%20the%20HTTP%20response%20also%20had%20no%20Strict-Transport-Security%20header.%20These%20checks%20did%20not%20provide%20an%20innocent%20explanation%20for%20a%20login%20endpoint%20that%20accepts%20credentials%20over%20cleartext%20HTTP.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202080%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-020%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Administrative%20FX-rates%20API%20is%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Ffx-rates%3Ftransport_check%3D1%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20GET%20over%20HTTP%20returned%20HTTP%20401%20with%20an%20UNAUTHORIZED%20error.%20The%20equivalent%20HTTPS%20request%20failed%20with%20'%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number'%2C%20confirming%20cleartext%20HTTP%20service%20without%20demonstrating%20unauthenticated%20access.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Ffx-rates%3Ftransport_check%3D1%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Ffx-rates%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20on%20the%20HTTP%20URL%3B%20TLS%20request%20failed%20with%20WRONG_VERSION_NUMBER.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20possible%20TLS-terminating%20proxy%20explanation%20was%20tested%20on%20localhost%20HTTPS%20port%20443%20and%20alternate%20port%208443%3B%20both%20had%20no%20reachable%20TLS%20listener.%20The%20exact%20HTTP%20endpoint%20also%20returned%20200%20and%20the%20FX-rate%20records%20when%20replayed%20with%20the%20supplied%20valid%20admin%20session%2C%20with%20no%20redirect%20or%20HTTPS-only%20behavior.%20This%20proves%20privileged%20data%20and%20the%20bearer%20credential%20path%20are%20usable%20over%20cleartext%20HTTP%2C%20so%20the%20finding%20is%20not%20explained%20by%20the%20anonymous%20401%20or%20by%20a%20TLS%20proxy%20on%20the%20standard%20ports.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202086%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-026%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Registration%20credentials%20and%20bearer%20token%20sent%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20direct%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20included%20JSON%20field%20password%3A%20password%20and%20received%20HTTP%20201%20with%20data.token%20containing%20a%20bearer%20JWT%20in%20the%20same%20cleartext%20HTTP%20exchange.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20saved%20page%20was%20loaded%20as%20HTTP%20200%20from%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%23%2Fregister%2C%20and%20the%20registration%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20returned%20HTTP%20201%20over%20HTTP.%20The%20client%20uses%20a%20relative%20%2Fapi%20base%2C%20so%20it%20follows%20the%20cleartext%20origin.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnDirect%20wire%20evidence%20from%20the%20bounded%20registration%20probe%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister.%20Authorization%3A%20none.%20Cookies%3A%20none.%20The%20request%20body%20contained%20password%3D%5C%5C%5C%22123456%5C%5C%5C%22%20and%20the%20HTTP%20201%20response%20contained%20a%20live%20JWT%20in%20data.token.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%3B%20JSON%20included%20the%20user's%20password.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20with%20JSON%20containing%20a%20password.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20using%20use_session%3D'anonymous'%3B%20URL%20scheme%20is%20http%3B%20body%20included%20%7B%5C%5C%5C%22email%5C%5C%5C%22%3A%5C%5C%5C%22deep-campaign-20260913-01%40example.test%5C%5C%5C%22%2C%5C%5C%5C%22password%5C%5C%5C%22%3A%5C%5C%5C%22123456%5C%5C%5C%22%2C%5C%5C%5C%22first_name%5C%5C%5C%22%3A%5C%5C%5C%22Deep%5C%5C%5C%22%2C%5C%5C%5C%22last_name%5C%5C%5C%22%3A%5C%5C%5C%22Campaign%5C%5C%5C%22%7D.%20Authorization%3A%20none.%20Cookies%3A%20none.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20201%20response%20included%20%60data.token%60%20as%20a%20bearer%20JWT.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20201%20from%20the%20cleartext%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20endpoint.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20201%20from%20cleartext%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20returned%20data.token%3D%5C%5C%5C%22eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...%5C%5C%5C%22%20and%20the%20registration%20success%20payload.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20affected%20listener%20is%20directly%20reachable%20over%20HTTP%3A%20HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20returned%20405%20from%20Apache%2FPHP%20with%20no%20HTTPS%20redirect%20or%20HSTS%20header.%20HTTPS%20on%20localhost%3A443%20and%208443%20was%20unavailable%2C%20HTTPS%20on%20port%208081%20returned%20WRONG_VERSION_NUMBER%2C%20and%20the%20same%20port-443%20check%20using%20127.0.0.1%20also%20failed%2C%20so%20there%20is%20no%20reachable%20TLS%20termination%20that%20explains%20the%20scanner%20result.%20Combined%20with%20the%20supplied%20live%20POST%20evidence%20showing%20the%20password%20in%20the%20request%20and%20a%20JWT%20in%20the%20201%20response%2C%20I%20found%20no%20benign%20transport%20explanation.%20I%20am%20omitting%20a%20PoC%20because%20reproducing%20the%20only%20decisive%20POST%20would%20create%20another%20account%2C%20which%20the%20validation%20instructions%20prohibit.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202089%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-029%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Banking%20API%20accepts%20bearer-authenticated%20requests%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20returned%20HTTP%20401%2C%20confirming%20that%20the%20API%20listener%20accepts%20plain%20HTTP.%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20failed%20with%20SSL%20WRONG_VERSION_NUMBER%2C%20confirming%20that%20port%208081%20is%20not%20serving%20TLS.%20The%20loaded%20API%20client%20sends%20Authorization%3A%20Bearer%20%3Ctoken%3E%20for%20API%20requests.%20No%20authenticated%20sensitive%20response%20was%20collected.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20over%20HTTP%3B%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20over%20HTTPS.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22UNAUTHORIZED%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%5C%5C%22%7D%7D%20over%20HTTP%3B%20HTTPS%20request%20failed%3A%20%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20supplied%20admin%20bearer%20session%20received%20HTTP%20200%20from%20the%20cleartext%20URL%20and%20the%20response%20contained%20a%20full%20profile%20with%20PII%20and%20a%20password_hash%20field.%20The%20exact%20HTTPS%20URL%20on%20port%208081%20failed%20with%20WRONG_VERSION_NUMBER%2C%20and%20HTTPS%20on%20ports%20443%2C%208443%2C%20and%208080%20was%20unavailable%3B%20port%2080%20was%20also%20unavailable%2C%20so%20no%20reachable%20TLS%20front%20door%20provides%20an%20innocent%20deployment%20explanation.%20The%20HTTP%20response%20had%20no%20Strict-Transport-Security%20header%2C%20and%20the%20endpoint%20did%20not%20redirect%20to%20HTTPS.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202093%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-033%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Administrative%20login%20is%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%20returned%20HTTP%20200%20and%20rendered%20the%20Username%2C%20Password%2C%20and%20Sign%20In%20form.%20HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%20also%20returned%20HTTP%20200%20without%20an%20HTTPS%20redirect.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%20returned%20HTTP%20200.%20The%20page%20contains%20the%20Username%20and%20Password%20login%20form.%20The%20publicly%20served%20admin%20API%20client%20uses%20fetch(BASE%20%2B%20path)%20with%20BASE%3D'%2Fapi%2Fadmin'%2C%20so%20login%20requests%20stay%20on%20the%20cleartext%20HTTP%20origin.%20The%20instrumented%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%20was%20sent%20over%20that%20origin%20and%20returned%20HTTP%20401.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20%2Fadmin%2F%20HTTP%2F1.1%5C%5CnHost%3A%20localhost%3A8081%5C%5CnAuthorization%3A%20none%5C%5CnCookies%3A%20none%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%3B%20saved%20browser%20evidence%3A%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%20-%3E%20200%20and%20the%20login%20form%20was%20rendered.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20200%5C%5CnContent-Type%3A%20text%2Fhtml%5C%5CnThe%20response%20contains%20the%20admin%20login%20form%20with%20Username%20and%20Password%20fields.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20direct%20GET%20returned%20the%20administrative%20login%20HTML%20over%20cleartext%20HTTP%20with%20status%20200%2C%20and%20HEAD%20returned%20the%20same%20status%20without%20an%20HTTPS%20redirect%20or%20transport-security%20headers.%20I%20tested%20HTTPS%20on%20the%20default%20port%2C%20the%20reported%20port%2C%20port%208443%2C%20and%20127.0.0.1%3B%20no%20usable%20TLS%20endpoint%20served%20this%20path%2C%20while%20HTTPS%20on%208081%20explicitly%20failed%20because%20that%20listener%20speaks%20plain%20HTTP.%20There%20is%20therefore%20no%20live%20TLS-terminating%20endpoint%20or%20other%20benign%20transport%20explanation%20for%20this%20localhost%20service.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202096%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-036%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Sensitive%20banking%20data%20exposed%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2F%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2F%20returned%20HTTP%20200%20and%20exposed%20Total%20Balance%20%2442%2C816.50%2C%20Everyday%20Account%20062-001%20%5C%5Cu00b7%2012345678%2C%20and%20Savings%20062-001%20%5C%5Cu00b7%2087654321.%20A%20follow-up%20GET%20https%3A%2F%2Flocalhost%3A8081%2F%20failed%20with%20SSL%20error%20WRONG_VERSION_NUMBER%2C%20confirming%20that%20the%20tested%20port%20serves%20plain%20HTTP%20rather%20than%20HTTPS.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnDirect%20probes%20to%20http%3A%2F%2Flocalhost%3A8081%2F%20returned%20HTTP%20200.%20An%20anonymous%20GET%20response%20included%20Total%20Balance%20%2442%2C816.50%2C%20Everyday%20Account%20062-001%20%5C%5Cu00b7%2012345678%2C%20and%20Savings%20062-001%20%5C%5Cu00b7%2087654321.%20A%20follow-up%20HEAD%20request%20to%20the%20same%20HTTP%20URL%20also%20returned%20200%2C%20confirming%20no%20redirect%20to%20HTTPS.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2F%20-%3E%20200%3B%20follow-up%20GET%20https%3A%2F%2Flocalhost%3A8081%2F%20-%3E%20SSL%20failure%3A%20WRONG_VERSION_NUMBER.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnHEAD%20http%3A%2F%2Flocalhost%3A8081%2F%20with%20use_session%3D'anonymous'%20returned%20HTTP%20200.%20The%20preceding%20anonymous%20GET%20used%20the%20same%20cleartext%20HTTP%20origin.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22The%20HTTP%20response%20returned%20the%20banking%20HTML%20and%20account%20data%3B%20the%20HTTPS%20request%20could%20not%20establish%20TLS.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20200%20for%20HEAD%20with%20no%20HTTPS%20redirect%3B%20anonymous%20GET%20response%20body%20contained%20balances%20and%20account%20numbers.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22false_positive%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20report%20assumes%20the%20HTML%20values%20are%20live%20customer%20account%20data.%20An%20anonymous%20GET%20returned%20a%20static%20Apache-served%20landing%20page%20titled%20%5C%5C%5C%22The%20Bank%20of%20Ed%5C%5C%5C%22%3B%20the%20values%20are%20embedded%20under%20a%20%60%3C!--%20Hero%20visual%20--%3E%60%20marketing%20section%2C%20use%20obvious%20sequential%20placeholder%20account%20numbers%2C%20and%20the%20total%20equals%20the%20two%20displayed%20card%20values.%20Comparing%20anonymous%20and%20%60admin_test%60%20requests%20returned%20the%20same%20200%20response%20length%2C%20ETag%2C%20and%20body%20content%2C%20so%20this%20is%20public%20demo%20markup%20rather%20than%20user-specific%20banking%20data.%20HTTPS%20on%208081%20fails%20and%20ports%20443%2F8443%20were%20unavailable%2C%20but%20that%20does%20not%20make%20the%20synthetic%20landing-page%20preview%20sensitive%20banking%20data.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202097%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-037%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Authenticated%20profile%20endpoint%20accepts%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20returned%20an%20HTTP%20401%20JSON%20error%20response%20over%20the%20cleartext%20HTTP%20endpoint.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20shared%20tester%20ledger%20records%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20-%3E%20200%20in%20the%20authenticated%20baseline.%20The%20profile%20page%20source%20states%20that%20GET%20%2Fapi%2Fprofile%20returns%20a%20user%20object%20in%20res.data%20and%20reads%20first_name%2C%20last_name%2C%20email%2C%20phone%2C%20address_line1%2C%20address_line2%2C%20suburb%2C%20state%2C%20and%20postcode.%20A%20direct%20HTTPS%20request%20to%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20failed%20with%20SSL%20WRONG_VERSION_NUMBER%2C%20confirming%20the%20port%20is%20serving%20plain%20HTTP%20rather%20than%20TLS.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20(authenticated%20baseline%2C%20200)%3B%20comparison%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20with%20JSON%20error%20response%20from%20the%20HTTP%20endpoint.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnAuthenticated%20baseline%20status%20200%20is%20recorded%20in%20the%20shared%20ledger.%20HTTPS%20comparison%20failed%3A%20SSL%20WRONG_VERSION_NUMBER.%20The%20profile%20renderer%20consumes%20PII%20fields%20from%20res.data.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20anonymous%20401%20alone%20was%20inconclusive%2C%20so%20I%20tested%20the%20supplied%20sessions%20and%20found%20that%20%60admin%60%20receives%20a%20200%20response%20with%20profile%20data%20over%20cleartext%20HTTP%2C%20including%20a%20password%20hash.%20I%20checked%20HTTPS%20on%20localhost%3A443%2C%20127.0.0.1%3A443%2C%20and%20localhost%3A8443%3B%20none%20accepted%20a%20connection%2C%20so%20there%20is%20no%20reachable%20TLS-terminating%20proxy%20that%20explains%20the%20HTTP%20listener.%20The%20decisive%20HTTP%20request%20therefore%20exposes%20authenticated%20profile%20data%20without%20transport%20encryption.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202098%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-038%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Banking%20login%20traffic%20is%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22The%20shared%20browser%20ledger%20recorded%20a%20200%20response%20for%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%23%2Flogin.%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20over%20HTTP%20returned%20an%20HTTP%20422%20JSON%20validation%20response%2C%20confirming%20that%20the%20login%20endpoint%20accepts%20cleartext%20HTTP.%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20failed%20with%20SSL%20WRONG_VERSION_NUMBER%2C%20showing%20that%20TLS%20was%20unavailable%20on%20the%20target%20port.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20assigned%20page%20was%20served%20as%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20with%20HTTP%20200.%20The%20shared%20tester%20ledger%20records%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20HTTP%20200%20and%20HTTP%20401%20responses.%20A%20direct%20HTTPS%20follow-up%20to%20https%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20failed%20with%20SSL%20WRONG_VERSION_NUMBER%2C%20showing%20the%20service%20is%20speaking%20plain%20HTTP%20on%20that%20port.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20over%20http%3A%2F%2F%20with%20an%20invalid%20email%20marker.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20422%20JSON%20validation%20response%20over%20http%3A%2F%2F%3B%20https%3A%2F%2Flocalhost%3A8081%20returned%20an%20SSL%20WRONG_VERSION_NUMBER%20error.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20login%20API%20processed%20an%20empty%20JSON%20request%20over%20cleartext%20HTTP%20and%20returned%20its%20normal%20validation%20response%2C%20proving%20the%20authentication%20route%20is%20reachable%20without%20TLS.%20HTTPS%20on%20localhost%3A443%20and%20localhost%3A8443%20was%20unavailable%2C%20while%20the%20service%20also%20answered%20on%200.0.0.0%3A8081%2C%20so%20this%20is%20not%20explained%20by%20a%20TLS%20reverse%20proxy%20or%20a%20loopback-only%20listener.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202102%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-042%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Banking%20login%20page%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%3Fcleartext_probe%3D1%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20bounded%20GET%20request%20over%20HTTP%20returned%20HTTP%20200.%20The%20response%20body%20contained%20the%20Bank%20of%20Ed%20Internet%20Banking%20page%20with%20%3Cinput%20type%3D%5C%5C%5C%22email%5C%5C%5C%22%3E%20and%20%3Cinput%20type%3D%5C%5C%5C%22password%5C%5C%5C%22%3E%20controls.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%3Fcleartext_probe%3D1%20over%20http%3A%2F%2F.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20response%20body%20contains%20the%20Bank%20of%20Ed%20Internet%20Banking%20page%20and%20%3Cinput%20type%3D%5C%5C%5C%22email%5C%5C%5C%22%3E%20and%20%3Cinput%20type%3D%5C%5C%5C%22password%5C%5C%5C%22%3E%20controls.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20exact%20affected%20URL%20returned%20HTTP%20200%20with%20the%20Bank%20of%20Ed%20Internet%20Banking%20HTML%20and%20no%20redirect%20or%20HSTS%20header.%20HTTPS%20on%20the%20canonical%20localhost%20port%20443%20and%20alternate%20port%208443%20was%20unreachable%2C%20and%20attempting%20TLS%20on%20the%20affected%20port%208081%20returned%20WRONG_VERSION_NUMBER%2C%20confirming%20that%20this%20service%20is%20cleartext-only%20rather%20than%20a%20TLS-terminating%20endpoint.%20The%20response%20is%20therefore%20an%20exposed%20login%20page%20over%20HTTP%2C%20not%20a%20scanner%20artifact.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202103%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-043%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Registration%20credentials%20and%20bearer%20tokens%20sent%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20returned%20HTTP%20200.%20The%20returned%20HTML%20contains%20a%20registration%20password%20input%2C%20and%20the%20page%20and%20API%20client%20use%20the%20http%3A%2F%2Flocalhost%3A8081%20origin.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20with%20registration%20password%20input%20in%20the%20returned%20HTML.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20HTTP%20page%20returns%20200%20without%20redirect%2C%20its%20live%20API%20client%20uses%20the%20relative%20BASE%20'%2Fapi'%2C%20and%20the%20live%20registration%20handler%20passes%20the%20form%20data%2C%20including%20the%20password%2C%20to%20that%20client.%20A%20deliberately%20invalid%20login%20was%20processed%20at%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%2C%20and%20a%20valid%20provided%20admin%20session%20sent%20an%20Authorization%20header%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20over%20HTTP%20and%20received%20200%20with%20the%20authenticated%20profile.%20HTTPS%20on%20ports%20443%20and%208443%20was%20unreachable%2C%20while%20TLS%20on%208081%20failed%20with%20WRONG_VERSION_NUMBER%2C%20so%20the%20reverse-proxy%20and%20protocol-upgrade%20explanations%20were%20not%20supported.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202106%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-046%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Internet%20Banking%20login%20page%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22Browser%20replay%20captured%20an%20HTTP%20200%20response%20for%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20over%20http%3A%2F%2Flocalhost%3A8081%2F%20and%20rendered%20the%20Internet%20Banking%20login%20form.%20The%20shared%20tester%20ledger%20also%20confirms%20that%20banking%20login%20traffic%20is%20served%20over%20cleartext%20HTTP.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20over%20http%3A%2F%2Flocalhost%3A8081%2F%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20response%20containing%20the%20Internet%20Banking%20login%20form.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20reported%20page%20returns%20HTTP%20200%20with%20the%20Internet%20Banking%20login%20form%20and%20no%20HTTPS%20redirect%20or%20HSTS%20header.%20Its%20live%20JavaScript%20uses%20a%20relative%20%2Fapi%20base%2C%20and%20a%20harmless%20invalid%20login%20was%20processed%20at%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%2C%20returning%20401%20over%20cleartext.%20HTTPS%20on%20ports%20443%2C%208081%2C%20and%208443%20was%20unavailable%2C%20while%20port%208081%20returned%20WRONG_VERSION_NUMBER%20for%20TLS%2C%20so%20the%20evidence%20is%20not%20explained%20by%20a%20TLS%20listener%20or%20redirect.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202108%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-048%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Administrative%20customer%20API%20is%20exposed%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F3%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20HEAD%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F3%20returned%20HTTP%20401%20over%20cleartext%20HTTP.%20A%20separate%20anonymous%20GET%20request%20to%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F3%20failed%20during%20TLS%20negotiation%20with%20SSL%20WRONG_VERSION_NUMBER%2C%20showing%20that%20the%20target%20port%20has%20no%20HTTPS%20listener.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20supplied%20traffic%20ledger%20records%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F3%20-%3E%20401%20and%20separately%20records%20the%20claim%20that%20the%20administrative%20customer%20API%20is%20exposed%20over%20cleartext%20HTTP.%20The%20401%20JSON%20response%20is%20an%20application%20response%20from%20the%20HTTP%20listener%2C%20not%20a%20TLS%20or%20connection%20failure.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F3%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%20Separate%20probe%3A%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F3%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F3%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20for%20the%20HTTP%20request%3B%20HTTPS%20request%20failed%20with%20TLS%20WRONG_VERSION_NUMBER.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20401%3B%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22UNAUTHORIZED%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%5C%5C%22%7D%7D%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20endpoint%20returns%20customer%20PII%20and%20account%20balances%20over%20plain%20HTTP%20with%20the%20supplied%20admin%20session%2C%20and%20the%20response%20has%20no%20HTTPS%20redirect%20or%20HSTS%20header.%20HTTPS%20on%20localhost%3A443%2C%20127.0.0.1%3A443%2C%20and%20localhost%3A8443%20was%20unavailable%3B%20the%20same%20cleartext%20response%20also%20worked%20via%200.0.0.0%3A8081%2C%20so%20I%20found%20no%20TLS-terminating%20front%20door%20or%20loopback-only%20explanation%20for%20this%20service.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202110%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-050%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Registration%20credentials%20and%20bearer%20token%20transmitted%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22The%20direct%20browser%20probe%20reached%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20over%20HTTP.%20The%20shared%20tester%20ledger%20confirmed%20that%20registration%20credentials%20and%20a%20bearer%20token%20were%20sent%20over%20cleartext%20HTTP%20with%20a%20successful%20201%20registration%20response.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20was%20exercised%20in%20the%20shared%20tester%20workflow%3B%20the%20assigned%20target%20URL%20uses%20the%20http%20scheme.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22Confirmed%20tester%20claim%3A%20registration%20credentials%20and%20bearer%20token%20sent%20over%20cleartext%20HTTP.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20endpoint%20is%20a%20cleartext%20HTTP%20listener%3A%20HTTPS%20on%20port%20443%20and%208443%20was%20unreachable%2C%20HTTPS%20on%20port%208081%20returned%20an%20SSL%20wrong-version%20error%2C%20and%20HTTP%20did%20not%20redirect%20to%20TLS%20or%20include%20HSTS.%20A%20live%20POST%20over%20HTTP%20was%20processed%20by%20the%20registration%20API%20with%20a%20password%20in%20the%20request%20body%3B%20the%20intentionally%20invalid%20email%20caused%20validation%20before%20account%20creation.%20This%20is%20consistent%20with%20the%20supplied%20evidence%20that%20a%20valid%20request%20on%20the%20same%20cleartext%20route%20returned%20201%20and%20a%20bearer%20token%2C%20and%20no%20innocent%20TLS-termination%20or%20loopback-only%20explanation%20was%20found.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202111%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-051%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Banking%20account%20data%20exposed%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2F%23security%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20browser%20GET%20to%20http%3A%2F%2Flocalhost%3A8081%2F%23security%20returned%20HTTP%20200%20and%20rendered%20'Total%20Balance'%2C%20'%2442%2C816.50'%2C%20'Everyday%20Account'%2C%20'062-001%20%5C%5Cu00b7%2012345678'%2C%20'Savings'%2C%20and%20'062-001%20%5C%5Cu00b7%2087654321'.%20A%20follow-up%20anonymous%20GET%20to%20http%3A%2F%2Flocalhost%3A8081%2F%3F__aespa_transport_probe%3D1%23security%20also%20returned%20HTTP%20200%20with%20the%20full%20banking%20page%20HTML.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2F%3F__aespa_transport_probe%3D1%23security%20using%20the%20anonymous%20session.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%3B%20the%20response%20body%20is%20the%20banking%20landing%20page%2C%20and%20the%20browser-rendered%20response%20contains%20the%20balance%20and%20account%20numbers%20listed%20above.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22false_positive%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20HTTP%20response%20is%20a%20static%20Apache%20landing%20page%2C%20not%20an%20authenticated%20account%20page.%20The%20reported%20values%20appear%20inside%20a%20hard-coded%20%60%3C!--%20Hero%20visual%20--%3E%60%20marketing%20card%20next%20to%20public%20copy%20such%20as%20%5C%5Cu201cGet%20Started%20Free%5C%5Cu201d%20and%20%5C%5Cu201cNo%20KYC%20required%5C%5Cu201d%3B%20the%20same%2028%2C964-byte%20HTML%20and%20ETag%20were%20returned%20anonymously%20and%20with%20the%20%60amelia_chen_example_com_e18e7d%60%20session.%20These%20are%20sample%20values%20used%20in%20a%20public%20product%20mockup%2C%20so%20the%20response%20does%20not%20expose%20a%20user's%20banking%20data.%20HTTPS%20is%20not%20available%20on%20the%20tested%20ports%2C%20but%20that%20does%20not%20turn%20these%20clearly%20static%20sample%20values%20into%20account%20data.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202112%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-052%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Banking%20API%20accepts%20bearer-authenticated%20requests%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22Existing%20direct%20tester%20evidence%20recorded%20a%20bearer-authenticated%20request%20sent%20to%20the%20http%3A%2F%2Flocalhost%3A8081%20origin.%20The%20endpoint%20returned%20HTTP%20200%20with%20content%20type%20application%2Fjson%2C%20and%20the%20shared%20tester%20ledger%20confirmed%20acceptance%20over%20cleartext%20HTTP.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22Request%20context%20recorded%20by%20the%20shared%20tester%3A%20bearer-authenticated%20API%20request%20sent%20to%20the%20http%3A%2F%2Flocalhost%3A8081%20origin.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22Shared%20tester%20ledger%20records%20the%20cleartext%20HTTP%20acceptance%20as%20confirmed.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20standard%20HTTPS%20endpoint%20on%20localhost%3A443%20was%20unreachable%2C%20and%20HTTPS%20on%20port%208081%20returned%20a%20TLS%20WRONG_VERSION_NUMBER%20error%2C%20so%20the%20affected%20service%20has%20no%20reachable%20TLS%20alternative%20at%20the%20tested%20origin.%20The%20listed%20admin%20bearer%20session%20returned%20HTTP%20200%20application%2Fjson%20over%20cleartext%20HTTP%20with%20account%20balances%20and%20card%20data%20including%20a%20CVV%2C%20while%20the%20anonymous%20request%20returned%20401%2C%20proving%20this%20is%20an%20authenticated-only%20resource%20exposed%20over%20cleartext.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202114%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-054%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Sensitive%20banking%20data%20transmitted%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F1%3Ftransport%3Dcleartext-check%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20GET%20request%20to%20the%20affected%20HTTP%20endpoint%20returned%20HTTP%20200%20with%20JSON%20containing%20account%20number%20%6010000001%60%2C%20BSB%2C%20balance%2C%20and%20recent%20transaction%20records.%20The%20request%20used%20a%20supplied%20bearer%20token%20and%20no%20cookies%3B%20the%20response%20was%20delivered%20over%20the%20http%3A%2F%2F%20origin.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F1%3Ftransport%3Dcleartext-check%3B%20Authorization%3A%20supplied%20bearer%20token%3B%20Cookies%3A%20none%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20JSON%20containing%20account%20number%2C%20BSB%2C%20balance%2C%20and%20transaction%20history%20over%20the%20http%3A%2F%2F%20origin.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20supplied%20admin%20session%20returned%20HTTP%20200%20over%20http%3A%2F%2Flocalhost%3A8081%20with%20account%20number%2C%20BSB%2C%20balance%2C%20and%20transaction%20history%2C%20and%20the%20endpoint%20did%20not%20redirect%20or%20include%20an%20HSTS%20header.%20I%20checked%20HTTPS%20on%20the%20standard%20port%20by%20hostname%20and%20loopback%20IP%2C%20retried%20TLS%20on%20port%208081%2C%20and%20checked%20alternate%20HTTPS%20port%208443%3B%20there%20was%20no%20reachable%20TLS%20route%2C%20while%20port%208081%20identified%20itself%20as%20plain%20HTTP.%20The%20endpoint%20is%20authenticated%2C%20so%20it%20is%20not%20an%20intentionally%20public%20response%20that%20would%20explain%20away%20the%20exposure.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202123%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-063%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Payment%20data%20and%20bearer%20credential%20accepted%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Fprocess%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20direct%20HTTP%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Fprocess%20included%20Authorization%3A%20Bearer%20mch_face_insurance_secret_key_2026%20and%20JSON%20fields%20merchant_id%2C%20card_number%3D0000000000000000%2C%20expiry%3D00%2F00%2C%20and%20amount%3D0.%20The%20endpoint%20returned%20HTTP%20400%20with%20INVALID_AMOUNT%2C%20showing%20that%20the%20cleartext%20request%20reached%20payment%20validation%20without%20TLS.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Fprocess%20over%20http%3A%2F%2F%20with%20JSON%20payment%20fields%20and%20bearer%20authorization.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20400%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22INVALID_AMOUNT%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Payment%20amount%20must%20be%20greater%20than%200.%5C%5C%5C%22%7D%7D%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20exact%20evidence%20bearer%20reproduced%20HTTP%20400%20INVALID_AMOUNT%20on%20the%20reported%20http%3A%2F%2Flocalhost%3A8081%20route%2C%20so%20the%20request%20reached%20the%20payment%20handler%20over%20cleartext.%20The%20standard%20TLS%20alternatives%20https%3A%2F%2Flocalhost%3A443%20and%20https%3A%2F%2Flocalhost%3A8443%20were%20unreachable%2C%20and%20TLS%20on%20port%208081%20failed%20with%20WRONG_VERSION_NUMBER%3B%20the%20HTTP%20response%20also%20had%20no%20HSTS%20header%20or%20HTTPS%20redirect.%20The%20listed%20sessions%20did%20not%20contain%20a%20bearer%20accepted%20by%20this%20machine-token%20endpoint%2C%20so%20I%20am%20omitting%20a%20PoC%20rather%20than%20recording%20the%20live%20credential%20from%20the%20finding.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202125%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-065%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Unauthenticated%20health%20endpoint%20exposes%20JWT%20signing%20secret%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3Ftransport_probe%3D1%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20unauthenticated%20GET%20request%20returned%20HTTP%20200%20over%20http%3A%2F%2F%20and%20included%20jwt_secret%3D%5C%5C%5C%22bankofed-dev-secret-change-in-production%5C%5C%5C%22%20plus%20db_host%3D%5C%5C%5C%22127.0.0.1%5C%5C%5C%22%2C%20db_name%3D%5C%5C%5C%22bankofed%5C%5C%5C%22%2C%20and%20db_user%3D%5C%5C%5C%22root%5C%5C%5C%22.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3Ftransport_probe%3D1%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20response%20body%3A%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Atrue%2C%5C%5C%5C%22data%5C%5C%5C%22%3A%7B%5C%5C%5C%22status%5C%5C%5C%22%3A%5C%5C%5C%22ok%5C%5C%5C%22%2C%5C%5C%5C%22php_version%5C%5C%5C%22%3A%5C%5C%5C%228.4.25%5C%5C%5C%22%2C%5C%5C%5C%22server%5C%5C%5C%22%3A%5C%5C%5C%22Apache%2F2.4.68%20(Unix)%5C%5C%5C%22%2C%5C%5C%5C%22db_host%5C%5C%5C%22%3A%5C%5C%5C%22127.0.0.1%5C%5C%5C%22%2C%5C%5C%5C%22db_name%5C%5C%5C%22%3A%5C%5C%5C%22bankofed%5C%5C%5C%22%2C%5C%5C%5C%22db_user%5C%5C%5C%22%3A%5C%5C%5C%22root%5C%5C%5C%22%2C%5C%5C%5C%22jwt_secret%5C%5C%5C%22%3A%5C%5C%5C%22bankofed-dev-secret-change-in-production%5C%5C%5C%22%2C%5C%5C%5C%22environment%5C%5C%5C%22%3A%5C%5C%5C%22production%5C%5C%5C%22%7D%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22OK%5C%5C%5C%22%7D%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20exact%20unauthenticated%20request%20returned%20HTTP%20200%20with%20the%20JWT%20secret%20and%20database%20connection%20fields%20in%20a%20live%20JSON%20response.%20The%20same%20disclosure%20occurs%20without%20transport_probe%3D1%2C%20so%20it%20is%20not%20a%20scanner-specific%20diagnostic%20variation.%20HTTPS%20on%20localhost%3A443%20and%20127.0.0.1%3A443%20was%20unavailable%2C%20the%20reported%20port%20speaks%20cleartext%20HTTP%2C%20and%20the%20response%20had%20no%20HSTS%20header%3B%20therefore%20I%20found%20no%20benign%20explanation%20for%20the%20reported%20exposure.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202128%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-068%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Sensitive%20transfer%20endpoint%20available%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Ftransfer%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22Anonymous%20requests%20were%20sent%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Ftransfer%20with%20no%20Authorization%20header%20or%20cookies.%20GET%20returned%20HTTP%20405%2C%20OPTIONS%20returned%20HTTP%20200%2C%20and%20POST%20returned%20HTTP%20401.%20No%20HTTPS%20redirect%20was%20observed.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22Anonymous%20requests%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fpayments%2Ftransfer%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%20Methods%20tested%3A%20GET%2C%20OPTIONS%2C%20POST.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22GET%3A%20HTTP%20405%20with%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Afalse%2C%5C%5C%5C%22error%5C%5C%5C%22%3A%7B%5C%5C%5C%22code%5C%5C%5C%22%3A%5C%5C%5C%22METHOD_NOT_ALLOWED%5C%5C%5C%22%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Method%20not%20allowed.%5C%5C%5C%22%7D%7D%3B%20OPTIONS%3A%20HTTP%20200%3B%20POST%3A%20HTTP%20401%20with%20an%20authorization%20error.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20cleartext%20route%20is%20reachable%20and%20performs%20application-level%20authentication%3A%20an%20anonymous%20POST%20with%20an%20empty%20JSON%20body%20returned%20HTTP%20401%20with%20the%20API's%20%5C%5C%5C%22Missing%20or%20invalid%20Authorization%20header%5C%5C%5C%22%20message.%20TLS%20on%20the%20reported%20port%20failed%20with%20WRONG_VERSION_NUMBER%2C%20and%20HTTPS%20checks%20on%20ports%20443%2C%208443%2C%20and%208080%20could%20not%20connect%3B%20the%20default%20HTTP%20port%20also%20had%20no%20redirecting%20listener.%20These%20results%20did%20not%20provide%20a%20TLS-terminating%20proxy%20or%20other%20benign%20explanation%20for%20the%20exposed%20backend%20endpoint.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202129%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-069%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Sensitive%20transfer%20data%20accepted%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22The%20control%20ledger%20records%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%20returning%20HTTP%20201.%20A%20live%20GET%20to%20the%20same%20HTTP%20route%20returned%20HTTP%20405%20with%20a%20normal%20application%20JSON%20response%2C%20confirming%20the%20route%20is%20served%20over%20cleartext%20HTTP%20rather%20than%20requiring%20an%20HTTPS-only%20entry%20point.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%20(successful%20control%2C%20HTTP%20201)%3B%20live%20probe%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22Successful%20control%3A%20HTTP%20201.%20Live%20HTTP%20route%3A%20HTTP%20405%20with%20a%20normal%20application%20JSON%20response.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20cleartext%20endpoint%20returned%20a%20normal%20405%20response%20with%20no%20HTTPS%20redirect%2C%20HTTPS%20on%20port%208081%20failed%20with%20a%20TLS%20wrong-version%20error%2C%20and%20standard%20HTTPS%20ports%20443%20and%208443%20were%20unreachable.%20Using%20the%20supplied%20admin%20session%2C%20a%20minimum%20positive%20external%20transfer%20POST%20over%20http%3A%2F%2F%20returned%20201%20and%20completed%20successfully.%20This%20rules%20out%20a%20scheme-only%20scanner%20error%20or%20HTTPS-only%20enforcement%3B%20the%20sensitive%20operation%20is%20accepted%20over%20cleartext%20HTTP.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202131%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-071%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Sensitive%20transfer%20security%20data%20exposed%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20authenticated%20POST%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%20with%20%7B%5C%5C%5C%22transfer_type%5C%5C%5C%22%3A%5C%5C%5C%22manual%5C%5C%5C%22%7D%20returned%20HTTP%20200%20and%20%7B%5C%5C%5C%22requires_totp%5C%5C%5C%22%3Atrue%2C%5C%5C%5C%22reason%5C%5C%5C%22%3A%5C%5C%5C%22manual_entry%5C%5C%5C%22%2C%5C%5C%5C%22totp_configured%5C%5C%5C%22%3Afalse%7D.%20The%20equivalent%20HTTPS%20request%20failed%20with%20%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number%2C%20showing%20that%20the%20target%20port%20serves%20cleartext%20HTTP%20instead%20of%20TLS.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20%2Fapi%2Ftransfers%2Fcheck%20over%20HTTP%20with%20JSON%20body%20%7B%5C%5C%5C%22transfer_type%5C%5C%5C%22%3A%5C%5C%5C%22manual%5C%5C%5C%22%7D%20and%20a%20valid%20bearer%20token.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20JSON%20response%20with%20requires_totp%2C%20reason%2C%20and%20totp_configured%20fields%3B%20HTTPS%20comparison%20failed%20with%20WRONG_VERSION_NUMBER.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20valid%20admin%20session%20returned%20HTTP%20200%20with%20the%20transfer%20security%20decision%20over%20cleartext%20HTTP%2C%20and%20the%20response%20included%20the%20TOTP%20configuration%20state.%20HTTPS%20on%20the%20affected%20port%20failed%20with%20WRONG_VERSION_NUMBER%2C%20and%20HTTPS%20on%20localhost%20ports%20443%2C%208443%2C%208080%2C%20and%2080%20was%20unavailable%3B%20the%20same%20HTTP%20service%20also%20responded%20via%200.0.0.0%2C%20so%20this%20is%20not%20explained%20by%20a%20loopback-only%20hostname.%20No%20TLS-terminating%20front%20door%20or%20redirect%20was%20reachable.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202132%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-072%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Sensitive%20health%20response%20served%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%20returned%20HTTP%20200%20with%20jwt_secret%3D%5C%5C%5C%22bankofed-dev-secret-change-in-production%5C%5C%5C%22%2C%20db_host%3D%5C%5C%5C%22127.0.0.1%5C%5C%5C%22%2C%20db_name%3D%5C%5C%5C%22bankofed%5C%5C%5C%22%2C%20and%20db_user%3D%5C%5C%5C%22root%5C%5C%5C%22.%20A%20follow-up%20GET%20to%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%20failed%20with%20SSL%20error%20WRONG_VERSION_NUMBER%2C%20showing%20that%20the%20service%20on%20this%20port%20speaks%20plain%20HTTP%20rather%20than%20HTTPS.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3B%20follow-up%20GET%20https%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20request%20returned%20200%20and%20sensitive%20JSON%3B%20HTTPS%20request%20failed%20with%20%5BSSL%3A%20WRONG_VERSION_NUMBER%5D%20wrong%20version%20number.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20live%20anonymous%20HTTP%20response%20contains%20the%20JWT%20signing%20secret%20and%20database%20host%2C%20name%2C%20and%20root%20user%20in%20JSON.%20The%20exact%20HTTPS%20request%20to%20port%208081%20fails%20with%20WRONG_VERSION_NUMBER%2C%20and%20the%20standard%20HTTPS%20endpoint%20on%20port%20443%20was%20unreachable%2C%20so%20I%20found%20no%20TLS-terminating%20frontend%20that%20explains%20away%20the%20exposed%20listener.%20The%20response%20also%20lacks%20transport%20protections%20such%20as%20Strict-Transport-Security.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202135%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-075%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22JWT%20signing%20secret%20and%20database%20metadata%20exposed%20over%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3Fcleartext_probe%3D1%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22Browser%20replay%20and%20an%20anonymous%20GET%20returned%20HTTP%20200%20over%20http%3A%2F%2F.%20The%20response%20exposed%20jwt_secret%3Dbankofed-dev-secret-change-in-production%20together%20with%20db_host%2C%20db_name%2C%20and%20db_user.%20No%20Authorization%20header%20or%20cookies%20were%20supplied.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%3Fcleartext_probe%3D1%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20over%20http%3A%2F%2F%20returned%20jwt_secret%3Dbankofed-dev-secret-change-in-production%20plus%20db_host%2Fdb_name%2Fdb_user.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22An%20anonymous%20replay%20of%20the%20affected%20HTTP%20service%20returned%20the%20literal%20jwt_secret%2C%20db_host%2C%20db_name%2C%20and%20db_user%20in%20the%20live%20JSON%20body.%20Removing%20cleartext_probe%3D1%20produced%20the%20same%20response%2C%20so%20the%20exposure%20is%20not%20a%20probe-only%20fixture%20or%20a%20static%20log%20artifact.%20I%20also%20checked%20localhost%20and%20127.0.0.1%20on%20HTTPS%20443%20and%20localhost%20on%208443%3B%20no%20TLS%20listener%20was%20reachable%2C%20while%20the%20direct%20Apache%20HTTP%20listener%20remained%20exposed.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202139%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-079%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Bearer%20token%20transmitted%20over%20cleartext%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20authenticated%20POST%20request%20to%20%60http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%60%20used%20%60Authorization%3A%20Bearer%20login-issued%20JWT%60%20over%20the%20%60http%60%20scheme%20and%20returned%20HTTP%20200%20with%20the%20transfer-check%20result.%20No%20cookies%20were%20present%2C%20so%20the%20bearer%20credential%20was%20transmitted%20over%20a%20cleartext%20connection.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%3B%20scheme%20%60http%60%3B%20Authorization%3A%20Bearer%20login-issued%20JWT%3B%20Cookies%3A%20none%3B%20body%20%7B%5C%5C%5C%22transfer_type%5C%5C%5C%22%3A%5C%5C%5C%22manual%5C%5C%5C%22%7D.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%3B%20response%20%60%7Bsuccess%3Atrue%2Cdata%3A%7Brequires_totp%3Atrue%2Creason%3A%5C%5C%5C%22manual_entry%5C%5C%5C%22%2Ctotp_configured%3Afalse%7D%2Cmessage%3A%5C%5C%5C%22OK%5C%5C%5C%22%7D%60.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22A%20valid%20listed%20admin%20session%20was%20accepted%20over%20cleartext%20HTTP%20and%20the%20near-no-op%20request%20returned%20200%20with%20the%20transfer-check%20result.%20The%20HTTP%20response%20had%20no%20Strict-Transport-Security%20header%2C%20and%20TLS%20was%20unavailable%20on%20ports%20443%2C%208443%2C%2080%2C%208080%2C%20and%20the%20reported%208081%20port%20rejected%20TLS%3B%20no%20HTTPS%20front%20door%20or%20redirect%20provided%20an%20innocent%20explanation.%20The%20decisive%20request%20is%20reproducible%20with%20the%20admin%20bearer%20session.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202099%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-039%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Administrative%20login%20page%20is%20available%20over%20unencrypted%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Flogin%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20browser%20replay%20requested%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%20and%20reached%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Flogin%20with%20HTTP%20200.%20The%20page%20rendered%20Username%2C%20Password%2C%20and%20Sign%20In%20fields%2C%20confirming%20that%20the%20administrative%20login%20is%20available%20over%20cleartext%20HTTP.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%20via%20browser%20replay%3B%20final%20URL%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%23%2Flogin.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%3B%20login%20form%20rendered%20with%20Username%20and%20Password%20fields.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20standard%20HTTPS%20endpoint%20on%20port%20443%20and%20the%20alternate%208443%20endpoint%20were%20unreachable%2C%20HTTPS%20on%20port%208081%20returned%20WRONG_VERSION_NUMBER%2C%20and%20the%20HTTP%20response%20had%20no%20redirect%20or%20HSTS.%20The%20live%20admin%20JavaScript%20uses%20the%20same-origin%20%60%2Fapi%2Fadmin%60%20base%2C%20and%20the%20invalid-credential%20POST%20reached%20%60%2Fapi%2Fadmin%2Fauth%2Flogin%60%20over%20HTTP%20and%20returned%20a%20real%20authentication%20response%2C%20so%20the%20form%20is%20not%20a%20harmless%20disconnected%20shell.%20No%20TLS%20front%20end%20or%20HTTPS-only%20submission%20path%20could%20be%20established%20to%20provide%20an%20innocent%20explanation.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202116%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-056%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Administrative%20customer%20data%20exposed%20over%20HTTP%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F16%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20authenticated%20GET%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F16%20returned%20HTTP%20200%20over%20http%3A%2F%2F%20with%20customer%20email%20face%40example.com%2C%20phone%201300%20000%20322%2C%20address%20data%2C%20and%20account%20balance%20100000000.00.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F16%20with%20a%20valid%20admin%20bearer%20token.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20JSON%20response%20contained%20customer%20PII%20and%20an%20account%20balance.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20endpoint%20returned%20the%20customer%20email%2C%20phone%2C%20address%2C%20account%20number%2C%20and%20balance%20in%20a%20200%20response%20over%20plaintext%20HTTP.%20HTTPS%20on%20port%20443%20was%20unavailable%3B%20TLS%20on%20port%208081%20failed%20with%20WRONG_VERSION_NUMBER%2C%20and%20ports%208443%20and%208080%20were%20also%20unavailable.%20Requests%20through%20localhost%20and%20127.0.0.1%20returned%20identical%20sensitive%20bodies%20and%20headers%2C%20including%20no%20HSTS%2C%20so%20the%20result%20was%20not%20a%20proxy-only%20downgrade%20or%20a%20TLS-covered%20endpoint.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fexport%2Fusers%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20header%20or%20browser%20storage.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20banking%20account%20data%22%2C%22description%22%3A%22The%20unauthenticated%20root%20page%20at%20http%3A%2F%2Flocalhost%3A8081%2F%20returns%20a%20banking%20dashboard%20containing%20total%20and%20individual%20account%20balances%20plus%20full%20BSB%20and%20account%20numbers.%22%2C%22impact%22%3A%22Anyone%20who%20can%20reach%20the%20service%20can%20view%20sensitive%20banking%20balances%20and%20account%20identifiers%20without%20logging%20in.%22%2C%22likelihood%22%3A%22High%3A%20the%20data%20is%20returned%20directly%20to%20an%20anonymous%20request%20with%20no%20authentication%20or%20session%20credentials.%22%2C%22recommendation%22%3A%22Require%20authentication%20and%20authorization%20before%20rendering%20or%20returning%20account%20data.%20Keep%20any%20public%20landing%20page%20separate%20from%20authenticated%20account%20views%20and%20return%20only%20minimal%20public%20content%20to%20unauthenticated%20users.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2F%22%2C%22evidence%22%3A%22An%20anonymous%20GET%20to%20http%3A%2F%2Flocalhost%3A8081%2F%20returned%20HTTP%20200%20with%20no%20Authorization%20header%20or%20cookies.%20The%20response%20and%20browser%20replay%20exposed%20'Total%20Balance%20%2442%2C816.50'%2C%20'Everyday%20Account%20062-001%20%C2%B7%2012345678'%2C%20'%248%2C241.50'%2C%20'Savings%20062-001%20%C2%B7%2087654321'%2C%20and%20'%2434%2C575.00'.%5Cn%5CnSpecialist%20evidence%3A%5CnThe%20anonymous%20wire%20probe%20GET%20http%3A%2F%2Flocalhost%3A8081%2F%20returned%20HTTP%20200%20with%20Authorization%3A%20none%20and%20Cookies%3A%20none.%20Its%20HTML%20contained%20the%20Bank%20of%20Ed%20landing%20page%20and%20the%20account%20data%20rendered%20in%20the%20preserved%20browser%20replay%3A%20Total%20Balance%20%2442%2C816.50%3B%20Everyday%20Account%20062-001%20%C2%B7%2012345678%20with%20%248%2C241.50%3B%20Savings%20062-001%20%C2%B7%2087654321%20with%20%2434%2C575.00.%5Cn%5CnSpecialist%20evidence%3A%5CnAn%20explicit%20anonymous%20HTTP%20probe%20returned%20200%20and%20served%20the%20account%20data%20in%20the%20response%20body.%20The%20response%20contained%20Total%20Balance%20%2442%2C816.50%2C%20Everyday%20Account%20062-001%20%C2%B7%2012345678%2C%20%248%2C241.50%2C%20Savings%20062-001%20%C2%B7%2087654321%2C%20and%20%2434%2C575.00.%20The%20same%20content%20rendered%20at%20http%3A%2F%2Flocalhost%3A8081%2F%23accounts%20without%20authentication.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2F%20with%20use_session%3Danonymous.%20Wire%20identity%3A%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5Cn%5CnSpecialist%20request%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2F%20-%3E%20200%3B%20use_session%3Danonymous%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5Cn%5CnSpecialist%20request%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2F%20with%20use_session%3D'anonymous'%3B%20wire%20state%20explicitly%20had%20Authorization%3A%20none%20and%20Cookies%3A%20none.%22%2C%22response_evidence%22%3A%22HTTP%20200.%20The%20response%20body%20contains%20the%20banking%20account%20balances%20and%20account%20identifiers%20listed%20above.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20200%20HTML%20response%20for%20the%20anonymous%20request%3B%20the%20preserved%20page%20rendered%20the%20total%20balance%2C%20BSB%2Faccount%20numbers%2C%20and%20individual%20balances%20before%20sign-in.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20200%20response%20body%20included%20Total%20Balance%20%2442%2C816.50%2C%20Everyday%20Account%20062-001%20%C2%B7%2012345678%2C%20and%20Savings%20062-001%20%C2%B7%2087654321.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20credential-free%20request%20to%20the%20exact%20affected%20URL%20returned%20HTTP%20200%20with%20content%20matching%20the%20protected%20response%20baseline.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2F%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Weak%20registration%20password%20policy%20issues%20live%20session%20tokens%22%2C%22description%22%3A%22The%20unauthenticated%20registration%20endpoint%20accepts%20the%20common%20password%20%60password%60%20and%20immediately%20returns%20a%20bearer%20JWT.%20No%20meaningful%20password%20policy%20was%20enforced.%22%2C%22impact%22%3A%22Attackers%20can%20create%20accounts%20with%20guessable%20credentials%20and%20obtain%20authenticated%20sessions%2C%20enabling%20automated%20abuse%20and%20increasing%20the%20risk%20of%20account%20compromise.%22%2C%22likelihood%22%3A%22High.%20The%20endpoint%20is%20unauthenticated%20and%20accepted%20the%20trivial%20password%20in%20a%20direct%20request.%22%2C%22recommendation%22%3A%22Enforce%20a%20strong%20password%20policy%2C%20reject%20common%20and%20breached%20passwords%2C%20add%20registration%20rate%20limits%20and%20abuse%20controls%2C%20and%20review%20whether%20registration%20should%20issue%20a%20session%20token%20immediately.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22An%20anonymous%20POST%20to%20%60%2Fapi%2Fauth%2Fregister%60%20with%20email%20%60admin%40example.com%60%2C%20password%20%60password%60%2C%20first_name%20%60Admin%60%2C%20and%20last_name%20%60User%60%20returned%20HTTP%20201%20with%20%60success%3Atrue%60%2C%20%60Registration%20successful%60%2C%20and%20a%20JWT%20in%20%60data.token%60.%20Retrying%20the%20same%20request%20returned%20HTTP%20409%20%60DUPLICATE_ENTRY%60%2C%20confirming%20that%20the%20first%20request%20created%20the%20account.%5Cn%5CnSpecialist%20evidence%3A%5CnA%20POST%20with%20email%20deep-weak-probe-20260913%40example.invalid%2C%20password%20%5C%221%5C%22%2C%20first_name%20Probe%2C%20and%20last_name%20User%20returned%20HTTP%20201%20and%20%5C%22Registration%20successful%5C%22.%20The%20response%20included%20user%20id%2020.%5Cn%5CnSpecialist%20evidence%3A%5CnDirect%20wire%20evidence%20from%20a%20bounded%20anonymous%20probe.%20Authorization%3A%20none.%20Cookies%3A%20none.%20POST%20with%20password%3D%5C%22123456%5C%22%20returned%20HTTP%20201%20and%20data.token.%5Cn%5CnSpecialist%20evidence%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20with%20email%20probe-weak%40example.invalid%20and%20password%201234567%20returned%20HTTP%20201%20with%20%5C%22Registration%20successful%5C%22.%20The%20public%20HTML%20for%20the%20same%20flow%20contains%20password%20minlength%3D%5C%228%5C%22.%20The%20response%20included%20a%20new%20user%20id%2025%2C%20confirming%20the%20short%20password%20was%20accepted.%5Cn%5CnSpecialist%20evidence%3A%5CnThe%20shared%20tester%20ledger%20contains%20the%20confirmed%20claim%3A%20weak%20registration%20password%20policy%20issues%20live%20session%20tokens.%20It%20also%20records%20successful%20201%20responses%20from%20POST%20%2Fapi%2Fauth%2Fregister.%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%3B%20JSON%20password%3A%20%60password%60.%5Cn%5CnSpecialist%20request%3A%5CnPOST%20%2Fapi%2Fauth%2Fregister%20with%20JSON%20%7B%5C%22email%5C%22%3A%5C%22deep-weak-probe-20260913%40example.invalid%5C%22%2C%5C%22password%5C%22%3A%5C%221%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Probe%5C%22%2C%5C%22last_name%5C%22%3A%5C%22User%5C%22%7D%5Cn%5CnSpecialist%20request%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20using%20use_session%3D'anonymous'%3B%20body%20%7B%5C%22email%5C%22%3A%5C%22deep-campaign-20260913-01%40example.test%5C%22%2C%5C%22password%5C%22%3A%5C%22123456%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Deep%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Campaign%5C%22%7D.%20Authorization%3A%20none.%20Cookies%3A%20none.%5Cn%5CnSpecialist%20request%3A%5CnPOST%20%2Fapi%2Fauth%2Fregister%20with%20JSON%20first_name%3DProbe%2C%20last_name%3DWeak%2C%20email%3Dprobe-weak%40example.invalid%2C%20password%3D1234567.%5Cn%5CnSpecialist%20request%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20succeeded%20with%20HTTP%20201%20in%20the%20shared%20tester%20workflow.%22%2C%22response_evidence%22%3A%22Initial%20response%3A%20HTTP%20201%20with%20%60success%3Atrue%60%2C%20%60Registration%20successful%60%2C%20and%20%60data.token%60%20containing%20a%20JWT.%20Retry%20response%3A%20HTTP%20409%20with%20%60DUPLICATE_ENTRY%60.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20201%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A20%2C...%7D%2C%5C%22token%5C%22%3A%5C%22...%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20201%20response%20contained%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A24%2C...%2C%5C%22password_hash%5C%22%3A%5C%22e10adc3949ba59abbe56e057f20f883e%5C%22%7D%2C%5C%22token%5C%22%3A%5C%22eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...%5C%22%7D%7D.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20201%3B%20success%3Dtrue%3B%20data.user.id%3D25%3B%20message%3DRegistration%20successful.%5Cn%5CnSpecialist%20response%3A%5CnConfirmed%20tester%20claim%3A%20weak%20registration%20password%20policy%20issues%20live%20session%20tokens.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20public%20registration%20endpoint%20is%20expected%20to%20be%20unauthenticated%2C%20but%20that%20does%20not%20explain%20accepting%20the%20common%20password.%20The%20created%20account%20authenticated%20with%20password%2C%20returned%20a%20JWT%2C%20and%20that%20JWT%20was%20accepted%20by%20the%20protected%20GET%20%2Fapi%2Fprofile%20endpoint%3B%20an%20intentionally%20wrong%20password%20was%20rejected%20with%20WRONG_PASSWORD%2C%20so%20authentication%20was%20not%20ignoring%20the%20password.%20The%20duplicate%20response%20also%20confirms%20the%20original%20registration%20persisted%20the%20account%2C%20leaving%20no%20benign%20explanation%20for%20the%20weak%20password%20policy%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22email%5C%22%3A%5C%22admin%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22password%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22JWT%20signature%20validation%20bypass%22%2C%22description%22%3A%22JWT%20signature%20validation%20is%20bypassable%20on%20protected%20endpoints.%20GET%20%2Fapi%2Faccounts%2F6%20accepts%20an%20unsigned%20JWT%20using%20alg%3Dnone%20with%20subject%2021%20and%20an%20empty%20signature%2C%20and%20GET%20%2Fapi%2Fprofile%20accepted%20a%20token%20after%20only%20its%20final%20signature%20character%20was%20changed.%20The%20endpoints%20reached%20authenticated%20request%20paths%20instead%20of%20rejecting%20the%20invalid%20signature.%22%2C%22impact%22%3A%22An%20attacker%20could%20forge%20authentication%20tokens%20and%20impersonate%20another%20user%20on%20routes%20that%20trust%20the%20JWT%20subject%2C%20including%20account%20and%20transfer-related%20API%20routes.%22%2C%22likelihood%22%3A%22High.%20The%20endpoint%20accepted%20a%20forged%20token%20without%20requiring%20a%20server-issued%20signature%2C%20and%20exploitation%20requires%20no%20prior%20authentication.%22%2C%22recommendation%22%3A%22Allow%20only%20a%20fixed%2C%20expected%20JWT%20algorithm%20and%20verify%20the%20signature%20before%20authorization.%20Also%20validate%20the%20issuer%2C%20audience%2C%20expiry%2C%20and%20subject%20claims.%20Reject%20alg%3Dnone%20and%20invalid%20or%20unsigned%20tokens%20with%20HTTP%20401.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F6%22%2C%22evidence%22%3A%22Anonymous%20GET%20%2Fapi%2Faccounts%2F6%20returned%20HTTP%20401%20with%20a%20missing%20or%20invalid%20Authorization%20header.%20A%20valid%20signed%20token%20returned%20HTTP%20404%20Account%20not%20found%2C%20while%20an%20unsigned%20alg%3Dnone%20token%20for%20subject%2021%20returned%20the%20same%20authenticated-path%20HTTP%20404%20response.%20A%20token%20with%20the%20original%20signature%20and%20a%20changed%20subject%20also%20reached%20the%20authenticated%20path.%20This%20indicates%20the%20server%20accepted%20the%20request%20without%20validating%20a%20valid%20server-issued%20signature.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F6%20with%20Authorization%3A%20Bearer%20%3CJWT%20header%20alg%3Dnone%2C%20payload%20sub%3D21%2C%20empty%20signature%3E.%22%2C%22response_evidence%22%3A%22HTTP%20404%20%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22Account%20not%20found.%5C%22%7D%7D%3B%20anonymous%20baseline%20for%20the%20same%20route%20was%20HTTP%20401%20with%20Missing%20or%20invalid%20Authorization%20header.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22Validation%20could%20not%20reproduce%20unauthorized%20access.%20Alternate%20users%20received%20an%20access%20denial%2C%20login%20response%2C%20generic%20application%20shell%2C%20or%20no%20protected%20content%20signal.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202120%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-060%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22JWT%20signature%20validation%20bypass%20on%20profile%20endpoint%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22high%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20recorded%20valid%20token%20for%20user%20id%2034%20returned%20HTTP%20200%20from%20GET%20%2Fapi%2Fprofile.%20The%20same%20request%20with%20only%20the%20signature%20suffix%20changed%20from%20...bWU-CYJS9k%20to%20...bWU-CYJS9A%20also%20returned%20HTTP%20200%20with%20success%3Atrue%20and%20data.id%3A34.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20with%20Authorization%3A%20Bearer%20%3Crecorded%20valid%20JWT%3E%20returned%20200.%20Follow-up%20used%20the%20same%20header%20and%20path%2C%20changing%20only%20the%20signature%20suffix%20from%20...bWU-CYJS9k%20to%20...bWU-CYJS9A.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22Valid%20token%3A%20HTTP%20200%2C%20success%3Atrue%2C%20data.id%3A34.%20Altered-signature%20token%3A%20HTTP%20200%2C%20success%3Atrue%2C%20data.id%3A34%2C%20message%3AOK.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22Replaying%20the%20explicitly%20invalid_sig_user2%20session%20returned%20HTTP%20200%20with%20success%3Atrue%20and%20a%20full%20profile%20for%20user%20id%202.%20The%20other%20bearer%20sessions%20http_token%20and%20http_token_2%20returned%20HTTP%20401%20with%20%5C%5C%5C%22Invalid%20or%20expired%20token%5C%5C%5C%22%20for%20the%20same%20endpoint%2C%20so%20this%20is%20not%20an%20intentionally%20public%20profile%20route%20or%20a%20generic%20authorization-header%20fallback.%20The%20live%20result%20matches%20the%20reported%20behavior%20that%20a%20token%20with%20an%20invalid%20signature%20is%20still%20trusted.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Authentication%20responses%20expose%20password%20hashes%20and%20session%20tokens%22%2C%22description%22%3A%22The%20authentication%20responses%20expose%20the%20user's%20password_hash%20together%20with%20session%20tokens.%20POST%20%2Fapi%2Fauth%2Flogin%20includes%20password_hash%20in%20data.user%2C%20and%20the%20profile%20and%20registration%20responses%20also%20expose%20it%3B%20registration%20returns%20a%20live%20JWT%20and%20the%20new%20user's%20hash.%20The%20observed%20hash%20is%20an%20unsalted%20MD5%20digest.%22%2C%22impact%22%3A%22Anyone%20who%20can%20read%20the%20response%20obtains%20a%20password%20verifier%20that%20can%20be%20attacked%20offline.%20The%20response%20also%20contains%20the%20user's%20session%20token%2C%20which%20could%20enable%20authenticated%20access%20if%20it%20is%20obtained%20by%20an%20unauthorized%20party.%22%2C%22likelihood%22%3A%22Medium.%20The%20data%20is%20returned%20directly%20by%20successful%20authentication%20and%20profile%20requests%2C%20so%20exposure%20depends%20on%20access%20to%20those%20responses.%22%2C%22recommendation%22%3A%22Remove%20password_hash%20and%20other%20credential%20material%20from%20all%20user%20serializers%20and%20API%20responses.%20Store%20passwords%20using%20a%20modern%20adaptive%20password-hashing%20algorithm%20such%20as%20Argon2id%2C%20bcrypt%2C%20or%20scrypt%20with%20a%20unique%20salt.%20Protect%20session%20tokens%20from%20disclosure%20and%20return%20them%20only%20where%20required%20for%20authentication.%22%2C%22cvss_score%22%3A5.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20with%20%7B%5C%22email%5C%22%3A%5C%22deep-weak-probe-20260913%40example.invalid%5C%22%2C%5C%22password%5C%22%3A%5C%221%5C%22%7D%20returned%20HTTP%20200%20and%20data.user.password_hash%3D%5C%22c4ca4238a0b923820dcc509a6f75849b%5C%22%20together%20with%20a%20token.%20The%20profile%20response%20also%20returned%20password_hash.%5Cn%5CnSpecialist%20evidence%3A%5CnThe%20successful%20HTTP%20200%20login%20response%20for%20admin%40example.com%20contained%20data.user.password_hash%3D5f4dcc3b5aa765d61d8327deb882cf99.%5Cn%5CnSpecialist%20evidence%3A%5CnDirect%20tool%20response%20from%20HTTP%20200%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20included%20data.user.password_hash%20alongside%20the%20normal%20profile%20fields.%20The%20earlier%20HTTP%20201%20POST%20%2Fapi%2Fauth%2Fregister%20response%20included%20the%20same%20field.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20with%20JSON%20%7B%5C%22email%5C%22%3A%5C%22deep-weak-probe-20260913%40example.invalid%5C%22%2C%5C%22password%5C%22%3A%5C%221%5C%22%7D%5Cn%5CnSpecialist%20request%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20admin%40example.com%20and%20password%20password.%5Cn%5CnSpecialist%20request%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20a%20disposable%20test%20identity%3B%20password%20omitted%20from%20the%20report.%22%2C%22response_evidence%22%3A%22HTTP%20200%20response%20data.user%20contained%20password_hash%20and%20the%20token%3B%20profile%20GET%20also%20returned%20password_hash.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20200%20JSON%20included%20data.user.password_hash%20and%20data.token.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20200%20JSON%20success%20response%20contained%20data.user.password_hash%20with%20a%2032-character%20hexadecimal%20value.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Replaying%20the%20scanner's%20exact%20unauthenticated%20login%20request%20returned%20HTTP%20200%20with%20data.user.password_hash%20set%20to%20c4ca4238a0b923820dcc509a6f75849b%20and%20a%20session%20token%2C%20so%20this%20is%20live%20response%20data%20rather%20than%20a%20static%20log%20or%20export.%20The%20supplied%20admin%20session%20also%20returned%20a%20real%20authenticated%20profile%20containing%20password_hash%2C%20showing%20the%20exposure%20is%20part%20of%20the%20response%20schema%20and%20not%20limited%20to%20the%20disposable%20probe%20account.%20The%20profile%20route%20guesses%20that%20returned%20404%20and%20the%20expired%20alternate%20sessions%20do%20not%20provide%20a%20benign%20explanation%20for%20the%20confirmed%20login%20and%20admin-profile%20disclosures.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202081%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-021%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Registration%20response%20discloses%20password%20hash%20and%20session%20token%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20POST%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20returned%20HTTP%20201%20with%20data.token%20set%20to%20a%20JWT%20and%20data.user.password_hash%20set%20to%205f4dcc3b5aa765d61d8327deb882cf99%2C%20the%20MD5%20digest%20of%20password.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnPOST%20%2Fapi%2Fauth%2Fregister%20with%20password%20%5C%5C%5C%221%5C%5C%5C%22%20returned%20user.password_hash%3D%5C%5C%5C%22c4ca4238a0b923820dcc509a6f75849b%5C%5C%5C%22.%20That%20value%20is%20the%20MD5%20digest%20of%20%5C%5C%5C%221%5C%5C%5C%22%20and%20was%20returned%20again%20by%20POST%20%2Fapi%2Fauth%2Flogin.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnDirect%20wire%20evidence%20from%20a%20bounded%20anonymous%20registration%20probe.%20Authorization%3A%20none.%20Cookies%3A%20none.%20Request%20returned%20HTTP%20201%20and%20included%20user.password_hash%3D%5C%5C%5C%22e10adc3949ba59abbe56e057f20f883e%5C%5C%5C%22%20together%20with%20data.token%20containing%20a%20JWT.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20assigned%20tester%20ledger%20contains%20a%20confirmed%20claim%20for%20POST%20%2Fapi%2Fauth%2Fregister%3A%20the%20registration%20response%20discloses%20a%20password%20hash%20and%20session%20token.%20The%20same%20ledger%20records%20a%20successful%20201%20response%20for%20this%20operation.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnDirect%20HTTP%20evidence%20from%20the%20bounded%20fresh-registration%20request%3A%20the%20unauthenticated%20POST%20returned%20HTTP%20201%20and%20JSON%20containing%20data.user.password_hash%20%3D%20%5C%5C%5C%227f6612a5f5a18815d7d99dee38bc384b%5C%5C%5C%22.%20The%20response%20also%20returned%20the%20complete%20user%20object%20to%20the%20registration%20client.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnA%20bounded%20anonymous%20registration%20request%20returned%20HTTP%20201%20and%20the%20JSON%20response%20included%20data.user.password_hash%20as%20a%2032-character%20hexadecimal%20value.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnThe%20controlled%20POST%20returned%20HTTP%20201%20and%20JSON%20data.user.password_hash%20%3D%20%5C%5C%5C%2258f4f18e68c90af327ce4ba7004ed55f%5C%5C%5C%22.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%3B%20JSON%20password%3A%20%60password%60.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20%2Fapi%2Fauth%2Fregister%20JSON%20included%20password%20%5C%5C%5C%221%5C%5C%5C%22.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20using%20use_session%3D'anonymous'%20with%20Content-Type%3A%20application%2Fjson%20and%20body%20%7B%5C%5C%5C%22email%5C%5C%5C%22%3A%5C%5C%5C%22deep-campaign-20260913-01%40example.test%5C%5C%5C%22%2C%5C%5C%5C%22password%5C%5C%5C%22%3A%5C%5C%5C%22123456%5C%5C%5C%22%2C%5C%5C%5C%22first_name%5C%5C%5C%22%3A%5C%5C%5C%22Deep%5C%5C%5C%22%2C%5C%5C%5C%22last_name%5C%5C%5C%22%3A%5C%5C%5C%22Campaign%5C%5C%5C%22%7D.%20Authorization%3A%20none.%20Cookies%3A%20none.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20with%20a%20valid%20registration%20body%20produced%20HTTP%20201%20in%20the%20shared%20tester%20evidence.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%20with%20use_session%3D'anonymous'%3B%20wire%20context%3A%20Authorization%3A%20none%3B%20Cookies%3A%20none.%20Body%20contained%20the%20required%20fields%20and%20a%20fresh%20test%20email.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20%2Fapi%2Fauth%2Fregister%20with%20the%20disposable%20registration%20JSON%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%3B%20session%3A%20anonymous.%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnPOST%20%2Fapi%2Fauth%2Fregister%20with%20a%20fresh%20synthetic%20registration%3A%20first_name%3DReplay%2C%20last_name%3DProbe%2C%20email%3Dreplay-555-cmp-20260913%40example.invalid%2C%20username%3Dreplay555cmp20260913%2C%20password%3DSafeReplay!2026x.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20201%20response%20contained%20%60data.token%60%20and%20%60data.user.password_hash%60%20in%20the%20JSON%20body.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20201%20response%20data.user.password_hash%20was%20c4ca4238a0b923820dcc509a6f75849b.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20201%20response%3A%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Atrue%2C%5C%5C%5C%22data%5C%5C%5C%22%3A%7B%5C%5C%5C%22user%5C%5C%5C%22%3A%7B%5C%5C%5C%22id%5C%5C%5C%22%3A24%2C%5C%5C%5C%22email%5C%5C%5C%22%3A%5C%5C%5C%22deep-campaign-20260913-01%40example.test%5C%5C%5C%22%2C...%2C%5C%5C%5C%22password_hash%5C%5C%5C%22%3A%5C%5C%5C%22e10adc3949ba59abbe56e057f20f883e%5C%5C%5C%22%2C...%7D%2C%5C%5C%5C%22token%5C%5C%5C%22%3A%5C%5C%5C%22eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...%5C%5C%5C%22%7D%7D.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnConfirmed%20tester%20claim%3A%20registration%20response%20discloses%20password%20hash%20and%20session%20token.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20201%20response%20included%20data.user.password_hash%20in%20the%20response%20body.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20201%20response%20contained%20data.user.password_hash%3D%5C%5C%5C%2243158bdb26822ef7efb787ad854584%5C%5C%5C%22.%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20201%20response%20included%20data.user.password_hash%20alongside%20the%20user%20profile%20and%20token.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22A%20fresh%20anonymous%20registration%20returned%20HTTP%20201%20with%20both%20a%20live%20JWT%20and%20password_hash%20set%20to%20the%20MD5%20digest%20of%20the%20supplied%20password.%20An%20empty%20request%20produced%20normal%20validation%20errors%2C%20and%20registering%20the%20listed%20existing%20email%20produced%20a%20duplicate-account%20response%2C%20which%20rules%20out%20a%20static%20unconditional%20disclosure.%20The%20HTTPS%20check%20on%20port%20443%20did%20not%20provide%20an%20innocent%20explanation%2C%20and%20the%20successful%20response%20directly%20confirms%20the%20reported%20issue.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22email%5C%22%3A%5C%22deep-weak-probe-20260913%40example.invalid%5C%22%2C%5C%22password%5C%22%3A%5C%221%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Customer%20updates%20accept%20stale%20If-Match%20values%22%2C%22description%22%3A%22PUT%20%2Fapi%2Fadmin%2Fcustomers%2F9%20and%20PUT%20%2Fapi%2Fadmin%2Fcustomers%2F8%20accept%20deliberately%20stale%20If-Match%20values%20instead%20of%20rejecting%20updates%20whose%20precondition%20does%20not%20match%20the%20current%20record%20version.%22%2C%22impact%22%3A%22A%20valid%20admin%20session%20can%20replay%20an%20earlier%20customer%20edit%20after%20a%20newer%20change%20and%20silently%20overwrite%20updated%20customer%20fields.%20Invalid%20or%20missing%20Authorization%20was%20rejected%2C%20so%20this%20is%20a%20concurrency%20and%20workflow%20issue%20rather%20than%20an%20authorization%20bypass.%22%2C%22likelihood%22%3A%22Medium%20during%20concurrent%20administration%20or%20when%20browser%20workflows%20are%20retried%20with%20stale%20form%20data.%22%2C%22recommendation%22%3A%22Persist%20a%20version%20or%20ETag%20for%20each%20customer%20record.%20Require%20If-Match%20to%20equal%20the%20current%20value%20and%20return%20HTTP%20409%20or%20412%20on%20mismatch.%20Tie%20the%20update%20response%20to%20the%20version%20that%20was%20checked.%22%2C%22cvss_score%22%3A4.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F%7Bid%7D%22%2C%22evidence%22%3A%22A%20valid%20admin%20request%20to%20PUT%20%2Fapi%2Fadmin%2Fcustomers%2F9%20with%20If-Match%3A%20%5C%22definitely-stale%5C%22%20and%20the%20existing%20values%20for%20customer%209%20returned%20HTTP%20200%20with%20success%3Atrue%20and%20%5C%22Customer%20updated%20successfully%5C%22.%20The%20workflow%20also%20recorded%20a%20replay%20with%20If-Match%3A%20%5C%22stale-0%5C%22%20and%20an%20exact%20replay%20of%20the%20valid%20PUT%2C%20both%20returning%20HTTP%20200.%20Requests%20with%20an%20invalid%20token%20or%20missing%20Authorization%20returned%20401.%22%2C%22request_evidence%22%3A%22PUT%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F9%3B%20If-Match%3A%20%5C%22definitely-stale%5C%22%3B%20JSON%20body%20contained%20the%20existing%20values%20for%20customer%209%3A%20Emma%20O'Brien%2C%20emma.obrien%40example.com%2C%200499%20012%20345%2C%2042%20Peel%20St%2C%20Newtown%20NSW%202042.%22%2C%22response_evidence%22%3A%22HTTP%20200%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A9%2C...%7D%2C%5C%22message%5C%22%3A%5C%22Customer%20updated%20successfully%5C%22%7D.%20Saved%20authorization%20comparisons%20returned%20401%20for%20an%20invalid%20token%20and%20for%20a%20missing%20Authorization%20header.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20first%20tested%20the%20benign%20explanation%20that%20this%20was%20only%20an%20unsupported%20conditional%20header%3A%20GET%20and%20HEAD%20exposed%20no%20ETag%20or%20version%2C%20and%20a%20no-op%20update%20with%20a%20stale%20value%20still%20returned%20200.%20I%20then%20committed%20a%20reversible%20phone%20change%20and%20replayed%20the%20prior%20customer%20representation%20with%20If-Match%3A%20stale-0%3B%20the%20stale%20request%20returned%20200%20and%20overwrote%20the%20newer%20phone%20value%2C%20proving%20a%20lost-update%20path%20rather%20than%20a%20harmless%20no-op.%20The%20decisive%20proof%20requires%20PUT%2C%20so%20I%20am%20omitting%20poc_request%20because%20the%20verifier%20only%20accepts%20GET%2C%20HEAD%2C%20or%20POST.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202119%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-059%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Customer%20updates%20accept%20stale%20If-Match%20values%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F8%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20fresh%20authenticated%20GET%20returned%20customer%208%20as%20Grace%20Kim%20with%20phone%200488%20901%20234%20and%20address%206%20Smith%20St%2C%20Darwin%20NT%200800.%20An%20authenticated%20PUT%20using%20the%20current%20values%20and%20If-Match%3A%20%5C%5C%5C%22stale-0%5C%5C%5C%22%20returned%20HTTP%20200%20with%20%5C%5C%5C%22Customer%20updated%20successfully%5C%5C%5C%22.%20Replaying%20the%20request%20returned%20the%20same%20response.%20The%20no-token%20request%20returned%20HTTP%20401%20with%20%5C%5C%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%5C%5C%22%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22PUT%20%2Fapi%2Fadmin%2Fcustomers%2F8%20with%20Authorization%3A%20Bearer%20%3Cfresh%20admin%20JWT%3E%2C%20Content-Type%3A%20application%2Fjson%2C%20and%20If-Match%3A%20%5C%5C%5C%22stale-0%5C%5C%5C%22%3B%20body%20contained%20the%20current%20customer%208%20values.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%3A%20%7B%5C%5C%5C%22success%5C%5C%5C%22%3Atrue%2C%5C%5C%5C%22data%5C%5C%5C%22%3A%7B%5C%5C%5C%22id%5C%5C%5C%22%3A8%2C...%7D%2C%5C%5C%5C%22message%5C%5C%5C%22%3A%5C%5C%5C%22Customer%20updated%20successfully%5C%5C%5C%22%7D%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22false_positive%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20endpoint%20does%20not%20implement%20HTTP%20conditional%20updates%3A%20the%20fresh%20authenticated%20GET%20returned%20no%20ETag%2C%20Last-Modified%2C%20or%20version%20field%2C%20and%20the%20authenticated%20PUT%20returned%20the%20same%20200%20response%20with%20current%20values%20both%20without%20If-Match%20and%20with%20If-Match%3A%20%5C%5C%5C%22stale-0%5C%5C%5C%22.%20Therefore%20%5C%5C%5C%22stale-0%5C%5C%5C%22%20is%20not%20a%20stale%20server-issued%20validator%3B%20it%20is%20an%20unsupported%20header%20that%20this%20non-versioned%20endpoint%20ignores.%20The%20no-token%20401%20behavior%20also%20confirms%20the%20update%20remains%20protected%20by%20authentication.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Login%20endpoint%20lacks%20visible%20throttling%20after%20repeated%20failures%22%2C%22description%22%3A%22POST%20%2Fapi%2Fauth%2Flogin%20continued%20returning%20the%20normal%20authentication%20failure%20after%20six%20consecutive%20attempts%20with%20the%20same%20invalid%20credentials.%20No%20lockout%2C%20delay%2C%20challenge%2C%20or%20rate-limit%20response%20was%20observed.%22%2C%22impact%22%3A%22Attackers%20may%20automate%20password-guessing%20and%20credential-stuffing%20attempts%2C%20increasing%20the%20risk%20of%20account%20takeover.%22%2C%22likelihood%22%3A%22Medium%20to%20high%20when%20the%20endpoint%20is%20reachable%20by%20untrusted%20clients.%22%2C%22recommendation%22%3A%22Apply%20server-side%20throttling%20by%20account%20and%20source.%20Return%20HTTP%20429%20after%20a%20small%20failure%20budget%2C%20add%20progressive%20delays%20or%20a%20challenge%2C%20and%20monitor%20repeated%20failures.%20Do%20not%20rely%20only%20on%20IP-based%20limits.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22A%20bounded%20login-rate-limit%20probe%20sent%20six%20repeated%20POST%20requests%20with%20the%20same%20invalid%20credentials.%20Each%20response%20remained%20HTTP%20401%20with%20USER_NOT_FOUND%2C%20and%20no%20429%20response%2C%20retry%20delay%2C%20challenge%2C%20or%20lockout%20signal%20was%20returned.%5Cn%5CnSpecialist%20evidence%3A%5CnThe%20login-rate-limit-admin%20repeat%20sequence%20was%20issued%20to%20POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20admin%40example.com%20and%20credential-stuffing-invalid.%20The%20observed%20response%20remained%20HTTP%20401%20with%20code%20WRONG_PASSWORD.%5Cn%5CnSpecialist%20evidence%3A%5CnThe%20bounded%20repeat%20probe%20used%20repeat_sequence%3Dlogin-rate-limit-followup%20with%20a%20maximum%20of%20six%20POST%20requests.%20The%20direct%20tool%20result%20remained%20HTTP%20401%20with%20USER_NOT_FOUND%20and%20did%20not%20show%20a%20429%2C%20lockout%2C%20or%20retry%20response.%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5Cn%7B%5C%22email%5C%22%3A%5C%22probe.invalid%40example.test%5C%22%2C%5C%22password%5C%22%3A%5C%22Wrong-Only-For-Bounded-Probe-9f3c%5C%22%7D%5Cnrepeat_sequence%3Dlogin-rate-limit%2C%20repeat_limit%3D6%5Cn%5CnSpecialist%20request%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20a%20synthetic%20invalid%20email%20and%20password%2C%20bounded%20by%20repeat_limit%206.%5Cn%5CnSpecialist%20request%3A%5CnBounded%20repeat_sequence%3Dlogin-rate-limit-admin%2C%20repeat_limit%3D6%2C%20POST%20%2Fapi%2Fauth%2Flogin%20for%20the%20confirmed%20admin%20account.%5Cn%5CnSpecialist%20request%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%20with%20email%20rate-followup%40example.com%20and%20an%20incorrect%20password%2C%20repeated%20at%20most%20six%20times.%22%2C%22response_evidence%22%3A%22HTTP%20401%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D%7D%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20401%20USER_NOT_FOUND%20was%20returned%20and%20the%20response%20did%20not%20indicate%20throttling%20or%20temporary%20blocking.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20401%20%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%7D%3B%20no%20rate-limit%20or%20lockout%20response%20was%20observed.%5Cn%5CnSpecialist%20response%3A%5CnHTTP%20401%20response%3A%20%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20initial%20body-shape%20concern%20was%20ruled%20out%3A%20the%20endpoint%20requires%20%60email%60%2C%20and%20validly%20shaped%20invalid%20requests%20returned%20the%20expected%20authentication%20errors.%20I%20then%20repeated%20six%20anonymous%2C%20cookie-free%20failures%20for%20the%20known%20account%20%60amelia.chen%40example.com%60%20using%20an%20invalid%20password%2C%20followed%20by%20additional%20identical%20attempts%3B%20every%20response%20stayed%20HTTP%20401%20with%20%60WRONG_PASSWORD%60%2C%20no%20%60Retry-After%60%20or%20rate-limit%20headers%20appeared%2C%20and%20response%20times%20remained%20about%2070-80%20ms.%20This%20rules%20out%20the%20scanner%20merely%20testing%20a%20nonexistent%20account%20or%20missing%20a%20delay-only%20control.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A06%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Outdated%20and%20unpinned%20third-party%20JavaScript%20on%20the%20banking%20page%22%2C%22description%22%3A%22The%20banking%20page%20at%20%2Fbanking%2F%20and%20%2Fbanking%2Findex.html%20loads%20jQuery%203.3.1%2C%20Moment.js%202.29.1%2C%20QRCode.js%201.5.3%2C%20and%20Tailwind%20CSS%20from%20public%20CDNs.%20Tailwind%20is%20loaded%20from%20an%20unversioned%20URL%2C%20and%20%2Fbanking%2Fjs%2Futils.js%20identifies%20bundled%20Moment%20usage.%22%2C%22impact%22%3A%22Users%20loading%20the%20banking%20page%20execute%20dependencies%20that%20are%20old%20or%20can%20change%20outside%20a%20controlled%20application%20release.%20No%20exploit%20of%20the%20loaded%20libraries%20was%20demonstrated.%22%2C%22likelihood%22%3A%22Low.%20Exploitation%20would%20require%20a%20weakness%20in%20a%20loaded%20dependency%20or%20an%20unsafe%20change%20to%20unpinned%20CDN%20content%2C%20and%20the%20captured%20evidence%20does%20not%20demonstrate%20either%20condition.%22%2C%22recommendation%22%3A%22Upgrade%20jQuery%20and%20Moment.js%20to%20supported%20releases%20or%20replace%20them%20where%20practical.%20Review%20the%20QRCode.js%20version.%20Pin%20every%20third-party%20asset%20to%20a%20reviewed%20version%2C%20and%20prefer%20self-hosting%20or%20a%20controlled%20asset%20pipeline%20with%20integrity%20checks%20instead%20of%20the%20unversioned%20Tailwind%20CDN%20script.%22%2C%22cvss_score%22%3A4.6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%22%2C%22evidence%22%3A%22A%20bounded%20GET%20of%20%2Fbanking%2F%20with%20Range%3A%20bytes%3D-3000%20returned%20imports%20for%20jquery%403.3.1%2C%20moment%402.29.1%2C%20qrcode%401.5.3%2C%20and%20https%3A%2F%2Fcdn.tailwindcss.com.%20A%20GET%20of%20%2Fbanking%2Fjs%2Futils.js%20returned%20the%20comment%20%5C%22Formatted%20with%20moment.js%20(bundled%20moment%202.29.1)%5C%22.%20The%20banking%20HTML%20also%20contained%20a%20Tailwind%20configuration%20block%20while%20loading%20the%20unversioned%20Tailwind%20script.%22%2C%22request_evidence%22%3A%22GET%20%2Fbanking%2F%20with%20Range%3A%20bytes%3D-3000%3B%20GET%20%2Fbanking%2Fjs%2Futils.js%22%2C%22response_evidence%22%3A%22HTTP%20206%20response%20exposed%20the%20third-party%20script%20URLs%20and%20versions%3B%20HTTP%20200%20response%20from%20%2Fbanking%2Fjs%2Futils.js%20explicitly%20names%20bundled%20Moment%202.29.1.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20reported%20strings%20are%20live%20executable%20imports%2C%20not%20stale%20or%20commented%20text%3A%20the%20page%20loads%20jquery%403.3.1%2C%20moment%402.29.1%2C%20qrcode%401.5.3%2C%20and%20the%20unversioned%20cdn.tailwindcss.com%20script.%20utils.js%20also%20calls%20moment()%20for%20date%20formatting%2C%20and%20the%20page%20contains%20an%20active%20Tailwind%20configuration%20block.%20I%20checked%20the%20npm%20registry%20metadata%20as%20a%20disproof%20attempt%3B%20Moment's%20latest%20is%202.30.1%20and%20jQuery's%20latest%20is%204.0.0%2C%20so%20the%20pinned%20versions%20are%20genuinely%20old.%20The%20anonymous%20200%20response%20and%20absence%20of%20any%20runtime%20gating%20do%20not%20provide%20a%20benign%20explanation%20for%20the%20dependency%20finding.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202136%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-076%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Banking%20page%20loads%20outdated%20jQuery%20and%20Moment%20versions%20from%20CDN%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22medium%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Findex.html%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20requests%20to%20the%20banking%20entry%20page%20showed%20exact%20CDN%20references%20to%20jquery%403.3.1%2C%20moment%402.29.1%2C%20and%20qrcode%401.5.3.%20The%20utils.js%20source%20included%20the%20comment%20%5C%5C%5C%22Formatted%20with%20moment.js%20(bundled%20moment%202.29.1)%5C%5C%5C%22%20and%20calls%20to%20moment(iso).format(...).%20The%20profile.js%20source%20included%20QRCode.toCanvas(...).%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Findex.html%3Fasset-review%3D1%3B%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Futils.js%3Fasset-review%3D1%3B%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2Fjs%2Fpages%2Fprofile.js%3Fasset-review%3D2%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20206%20for%20the%20bounded%20HTML%2Fsource%20reads.%20The%20HTML%20contains%20the%20exact%20jquery%403.3.1%2C%20moment%402.29.1%2C%20qrcode%401.5.3%20CDN%20URLs%3B%20the%20source%20reads%20show%20Moment%20and%20QRCode%20runtime%20references.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20live%20page%20still%20includes%20the%20exact%20jquery%403.3.1%20and%20moment%402.29.1%20CDN%20URLs%2C%20and%20both%20URLs%20return%20HTTP%20200%20with%20matching%20jsDelivr%20version%20headers.%20npm%20reports%20newer%20releases%2C%20so%20these%20are%20not%20current%20versions.%20The%20outdated%20Moment%20dependency%20is%20reachable%20because%20the%20live%20utils.js%20calls%20moment(...).format(...)%3B%20the%20QRCode%20URL%20currently%20returns%20404%2C%20but%20that%20does%20not%20explain%20away%20the%20separate%20jQuery%20and%20Moment%20finding.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Address-book%20nickname%20can%20inject%20JavaScript%20into%20the%20delete%20handler%22%2C%22description%22%3A%22The%20address-book%20page%20builds%20delete%20buttons%20with%20list.innerHTML%20and%20inserts%20the%20nickname%20into%20a%20single-quoted%20inline%20onclick%20handler.%20escapeHtml%20converts%20apostrophes%20to%20%26%2339%3B%2C%20but%20the%20HTML%20parser%20decodes%20that%20entity%20before%20compiling%20the%20handler%2C%20so%20the%20nickname%20can%20terminate%20the%20string%20and%20add%20JavaScript.%22%2C%22impact%22%3A%22A%20user%20who%20can%20create%20or%20influence%20a%20nickname%20could%20execute%20script%20in%20the%20banking%20origin%20when%20another%20user%20opens%20the%20address%20book%20or%20activates%20the%20affected%20button.%20The%20script%20could%20access%20page%20data%20and%20tokens%20available%20to%20that%20origin.%22%2C%22likelihood%22%3A%22Medium.%20Exploitation%20depends%20on%20controlling%20an%20address-book%20nickname%2C%20but%20the%20vulnerable%20client-side%20construction%20is%20directly%20visible%20in%20the%20served%20source.%22%2C%22recommendation%22%3A%22Remove%20the%20inline%20onclick%20handler%20and%20attach%20the%20delete%20action%20with%20addEventListener.%20Insert%20the%20nickname%20as%20text%20or%20a%20DOM%20property.%20If%20a%20value%20must%20be%20placed%20in%20an%20attribute%2C%20use%20encoding%20appropriate%20to%20that%20context%20and%20do%20not%20rely%20on%20HTML%20entity%20encoding%20for%20JavaScript%20strings.%22%2C%22cvss_score%22%3A6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%23%2Faddressbook%22%2C%22evidence%22%3A%22GET%20requests%20for%20addressbook.js%20and%20utils.js%20returned%20source%20showing%20list.innerHTML%2C%20insertion%20of%20U.escapeHtml(entry.nickname)%20into%20a%20single-quoted%20onclick%20handler%2C%20escapeHtml%20mapping%20apostrophes%20to%20%26%2339%3B%2C%20and%20a%20pre-parser%20.replace(%2F'%2Fg%2C%20%5C%22%5C%5C%5C%5C'%5C%22)%20call.%20The%20encoded%20apostrophe%20is%20therefore%20decoded%20when%20the%20onclick%20attribute%20is%20parsed%2C%20allowing%20the%20nickname%20to%20break%20out%20of%20the%20JavaScript%20string.%20No%20payload%20was%20created%20or%20executed%20because%20authenticated%20browser%20state%20was%20unavailable.%22%2C%22request_evidence%22%3A%22GET%20%2Fbanking%2Fjs%2Fpages%2Faddressbook.js%3Fv%3D20260213-2%20and%20GET%20%2Fbanking%2Fjs%2Futils.js%3Fv%3D20260213-2.%22%2C%22response_evidence%22%3A%22HTTP%20200%20responses%20contained%20the%20inline%20handler%20construction%2C%20%60list.innerHTML%20%3D%20html%60%2C%20the%20%60%26%2339%3B%60%20escape%20map%2C%20and%20the%20pre-parser%20%60.replace(%2F'%2Fg%2C%20%5C%22%5C%5C%5C%5C'%5C%22)%60%20logic.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22unconfirmed%22%2C%22validation_note%22%3A%22The%20JavaScript%20source%20shows%20a%20potentially%20unsafe%20construction%3A%20an%20escaped%20nickname%20is%20placed%20into%20a%20single-quoted%20inline%20onclick%20handler%2C%20and%20the%20source-level%20parser-decoding%20concern%20is%20plausible.%20However%2C%20the%20collected%20runtime%20evidence%20contains%20only%20baseline%20address-book%20data%20for%20the%20valid%20%60admin%60%20session%3B%20no%20attacker-controlled%20nickname%20was%20created%20or%20updated%2C%20and%20no%20browser%20execution%20of%20a%20payload%20was%20observed.%20The%20material%20proof%20gap%20is%20whether%20a%20stored%20nickname%20can%20reach%20this%20renderer%20and%20execute%20JavaScript%20in%20the%20target%20browser%20context.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Apache%20server%20version%20disclosed%20in%20error%20responses%22%2C%22description%22%3A%22Unauthenticated%20error%20responses%20disclose%20the%20Apache%20server%20banner%2C%20including%20Apache%2F2.4.68%20(Unix)%2C%20version%20and%20operating-system%20details%2C%20hostname%2C%20and%20listening%20port.%20The%20disclosure%20was%20observed%20at%20%2Fadmin%2Fjs%2F%2C%20%2Fopenapi.json%2C%20%2Fapi%2Faccounts%2F%2500%2C%20%2Fapi%2Faddress-book%2F%2500%2C%20and%20the%20missing%20%2Frobots.txt%20resource.%22%2C%22impact%22%3A%22This%20gives%20unauthenticated%20users%20precise%20server%20software%20and%20version%20information%20for%20reconnaissance%20and%20targeted%20research.%22%2C%22likelihood%22%3A%22Low.%20The%20disclosure%20alone%20does%20not%20provide%20direct%20access%20or%20exploitation%2C%20and%20no%20related%20server%20vulnerability%20was%20demonstrated.%22%2C%22recommendation%22%3A%22Configure%20Apache%20or%20the%20front%20server%20to%20remove%20or%20generalize%20the%20Server%20header%20and%20server%20signatures%20in%20generated%20error%20pages.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2Fjs%2F%22%2C%22evidence%22%3A%22Without%20authorization%20or%20cookies%2C%20GET%20%2Fadmin%2Fjs%2F%20returned%20HTTP%20403%20with%20an%20HTML%20error%20page%20containing%20%5C%22Apache%2F2.4.68%20(Unix)%20Server%20at%20localhost%20Port%208081%5C%22.%20GET%20%2Fopenapi.json%20returned%20a%20404%20page%20with%20the%20same%20banner.%22%2C%22request_evidence%22%3A%22GET%20%2Fadmin%2Fjs%2F%20HTTP%2F1.1%5CnHost%3A%20localhost%3A8081%5CnAuthorization%3A%20none%5CnCookies%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%20403%5Cn%3C!DOCTYPE%20HTML%20PUBLIC%20%5C%22-%2F%2FW3C%2F%2FDTD%20HTML%204.01%2F%2FEN%5C%22%3E%5Cn%3Caddress%3EApache%2F2.4.68%20(Unix)%20Server%20at%20localhost%20Port%208081%3C%2Faddress%3E%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20re-requested%20both%20reported%20endpoints%20anonymously%20and%20also%20checked%20a%20separate%20nonexistent%20path.%20All%20three%20responses%20were%20Apache-generated%20error%20pages%20that%20exposed%20the%20exact%20version%20in%20both%20the%20Server%20header%20and%20HTML%20body%2C%20so%20the%20result%20is%20repeatable%20and%20does%20not%20depend%20on%20authentication%20or%20a%20route-specific%20application%20message.%20The%20broader%20error-page%20behavior%20does%20not%20provide%20a%20benign%20explanation%3B%20it%20confirms%20global%20Apache%20version%20disclosure.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202094%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-034%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Apache%20version%20disclosed%20in%20404%20response%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22info%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F%2500%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20unauthenticated%20GET%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F%2500%20returned%20HTTP%20404%20with%20an%20HTML%20footer%20containing%20%5C%5C%5C%22Apache%2F2.4.68%20(Unix)%20Server%20at%20localhost%20Port%208081%5C%5C%5C%22.%5C%5Cn%5C%5CnSpecialist%20evidence%3A%5C%5CnShared%20tester%20ledger%20records%3A%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F%2500%20-%3E%20404%2C%20with%20the%20confirmed%20claim%20that%20the%20404%20response%20disclosed%20the%20Apache%20version.%20A%20separate%20malformed-byte%20follow-up%2C%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F%25FF%2C%20returned%20a%20generic%20404%20JSON%20error.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20%2Fapi%2Faccounts%2F%2500%5C%5CnAuthorization%3A%20none%5C%5CnCookies%3A%20none%5C%5Cn%5C%5CnSpecialist%20request%3A%5C%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F%2500%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20404%20HTML%20response%20containing%20Apache%2F2.4.68%20(Unix).%5C%5Cn%5C%5CnSpecialist%20response%3A%5C%5CnHTTP%20404%3B%20the%20ledger%20confirms%20Apache%20version%20disclosure%20in%20this%20response.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22skipped%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202109%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-049%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Apache%20server%20version%20disclosed%20in%20404%20response%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22info%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%2F%2500%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%2F%2500%20returned%20HTTP%20404%20with%20an%20HTML%20error%20page%20containing%20'%3Caddress%3EApache%2F2.4.68%20(Unix)%20Server%20at%20localhost%20Port%208081%3C%2Faddress%3E'.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faddress-book%2F%2500%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20404%20Apache%20error%20page%20with%20exact%20version%20disclosure.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22skipped%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202126%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-066%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Apache%20server%20version%20disclosed%20in%20404%20responses%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22info%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Frobots.txt%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20GET%20request%20to%20%2Frobots.txt%20returned%20a%20404%20response%20whose%20body%20contained%3A%20%3Caddress%3EApache%2F2.4.68%20(Unix)%20Server%20at%20localhost%20Port%208081%3C%2Faddress%3E%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Frobots.txt%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20404%20response%20body%20contains%3A%20%3Caddress%3EApache%2F2.4.68%20(Unix)%20Server%20at%20localhost%20Port%208081%3C%2Faddress%3E%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22skipped%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2Fjs%2F%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Authenticated%20transfer%20check%20exposes%20stack%20traces%20and%20server%20paths%22%2C%22description%22%3A%22The%20authenticated%20%60%2Fapi%2Ftransfers%2Fcheck%60%20endpoint%20returns%20a%20detailed%20HTTP%20500%20error%20when%20an%20%60address_book%60%20request%20omits%20the%20required%20%60address_book_id%60.%20The%20response%20exposes%20exception%20text%2C%20PHP%20source%20paths%2C%20class%20and%20controller%20names%2C%20and%20a%20full%20stack%20trace.%22%2C%22impact%22%3A%22An%20authenticated%20user%20can%20learn%20server%20filesystem%20paths%20and%20backend%20control%20flow%20from%20a%20malformed%20request.%20This%20information%20may%20assist%20later%20attacks.%22%2C%22likelihood%22%3A%22high%22%2C%22recommendation%22%3A%22Validate%20that%20%60address_book_id%60%20is%20present%20and%20valid%20before%20invoking%20the%20address-book%20lookup%20or%20model.%20Return%20a%20controlled%204xx%20response%20for%20missing%20or%20unknown%20payees%2C%20and%20omit%20file%20paths%2C%20line%20numbers%2C%20class%20names%2C%20and%20stack%20traces%20from%20API%20responses.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%22%2C%22evidence%22%3A%22With%20a%20valid%20login-issued%20bearer%20token%2C%20a%20POST%20request%20containing%20%60%7B%5C%22transfer_type%5C%22%3A%5C%22address_book%5C%22%7D%60%20returned%20HTTP%20500.%20The%20JSON%20error%20exposed%20%60AddressBookEntry%3A%3AfindByIdAndUser()%3A%20Argument%20%231%20(%24id)%20must%20be%20of%20type%20int%2C%20null%20given%60%2C%20%60%2Fvar%2Fwww%2Fhtml%2Fsrc%2FModels%2FAddressBookEntry.php%3A18%60%2C%20%60%2Fvar%2Fwww%2Fhtml%2Fsrc%2FServices%2FTransferService.php%3A27%60%2C%20controller%20and%20router%20names%2C%20and%20a%20full%20trace.%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%3B%20Authorization%3A%20Bearer%20login-issued%20token%3B%20Cookies%3A%20none%3B%20Content-Type%3A%20application%2Fjson%3B%20body%20%7B%5C%22transfer_type%5C%22%3A%5C%22address_book%5C%22%7D.%22%2C%22response_evidence%22%3A%22HTTP%20500%20with%20error.details.file%2C%20error.details.trace%2C%20internal%20PHP%20source%20paths%2C%20and%20implementation-level%20exception%20text.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Several%20listed%20sessions%20returned%20401%20before%20reaching%20the%20endpoint%2C%20so%20those%20probes%20were%20not%20evidence%20either%20way.%20The%20listed%20%60admin%60%20session%20authenticated%20and%20the%20exact%20malformed%20request%20returned%20HTTP%20500%20with%20the%20PHP%20exception%2C%20source%20paths%2C%20controller%20and%20router%20names%2C%20and%20a%20full%20stack%20trace.%20This%20is%20direct%20confirmation%20of%20verbose%20authenticated%20error%20disclosure%3B%20no%20benign%20formatting%20or%20proxy%20explanation%20accounts%20for%20the%20live%20response.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Credentialed%20CORS%20reflects%20arbitrary%20origins%22%2C%22description%22%3A%22The%20protected%20endpoints%20%2Fapi%2Fprofile%20and%20%2Fapi%2Ffx%2Frates%20reflect%20arbitrary%20Origin%20values%20and%20return%20Access-Control-Allow-Credentials%3A%20true.%20This%20permits%20credentialed%20cross-origin%20requests%20from%20attacker-controlled%20origins.%22%2C%22impact%22%3A%22If%20an%20authenticated%20session%20is%20accepted%2C%20an%20attacker-controlled%20website%20may%20be%20able%20to%20read%20profile%20data%20cross-origin.%20No%20authenticated%20data%20read%20was%20demonstrated%20in%20the%20captured%20evidence.%22%2C%22likelihood%22%3A%22The%20behavior%20reproduced%20with%20an%20untrusted%20origin%20on%20a%20protected%20route%2C%20although%20the%20observed%20request%20used%20an%20anonymous%20session%20and%20returned%20401.%22%2C%22recommendation%22%3A%22Allow%20only%20explicitly%20trusted%20origins.%20Return%20Access-Control-Allow-Origin%20only%20for%20allowlisted%20origins%2C%20and%20enable%20credentials%20only%20where%20authenticated%20cross-origin%20access%20is%20required.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22A%20GET%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20with%20Origin%3A%20https%3A%2F%2Fattacker.example%20returned%20HTTP%20401%20with%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fattacker.example%20and%20Access-Control-Allow-Credentials%3A%20true.%20The%20same%20route%20also%20reflected%20Origin%3A%20http%3A%2F%2Flocalhost%3A8081%2C%20confirming%20arbitrary%20origin%20reflection%20rather%20than%20a%20fixed%20allowlist.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20with%20Origin%3A%20https%3A%2F%2Fattacker.example%2C%20using%20an%20anonymous%20session.%22%2C%22response_evidence%22%3A%22HTTP%20401%20with%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fattacker.example%20and%20Access-Control-Allow-Credentials%3A%20true.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20unauthenticated%20evidence%20did%20not%20by%20itself%20prove%20impact%2C%20so%20I%20tested%20the%20protected%20branch%20with%20the%20supplied%20sessions%20and%20found%20a%20valid%20admin%20session.%20With%20that%20session%2C%20GET%20%2Fapi%2Fprofile%20returned%20HTTP%20200%20and%20meaningful%20profile%20data%20including%20password_hash%2C%20while%20reflecting%20https%3A%2F%2Fattacker.example%20in%20Access-Control-Allow-Origin%20and%20returning%20Access-Control-Allow-Credentials%3A%20true.%20The%20401%20responses%20from%20other%20sessions%20therefore%20do%20not%20provide%20a%20benign%20explanation%20for%20the%20authenticated%20response.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202133%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-073%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Credentialed%20CORS%20reflects%20arbitrary%20origins%20on%20FX%20rates%20API%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ffx%2Frates%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22A%20GET%20request%20to%20%2Fapi%2Ffx%2Frates%20with%20Origin%3A%20https%3A%2F%2Fthird-party.example%20returned%20HTTP%20401%20while%20reflecting%20that%20origin%20in%20Access-Control-Allow-Origin%20and%20setting%20Access-Control-Allow-Credentials%3A%20true.%20The%20response%20also%20allowed%20multiple%20methods%20and%20wildcard%20headers.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ffx%2Frates%20with%20Origin%3A%20https%3A%2F%2Fthird-party.example%2C%20using%20an%20anonymous%20session.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20401%20with%20Access-Control-Allow-Origin%3A%20https%3A%2F%2Fthird-party.example%20and%20Access-Control-Allow-Credentials%3A%20true.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22confirmed%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20anonymous%20request%20is%20correctly%20rejected%20with%20401%2C%20but%20the%20listed%20admin%20session%20is%20valid%20and%20returns%20the%20protected%20FX%20table.%20With%20that%20session%2C%20both%20a%20trusted-looking%20origin%20and%20a%20distinct%20attacker%20origin%20are%20reflected%20verbatim%2C%20while%20Access-Control-Allow-Credentials%20remains%20true%3B%20the%20preflight%20also%20returns%20the%20permissive%20CORS%20policy.%20This%20is%20not%20an%20empty%20or%20login%20response%2C%20so%20the%20endpoint's%20authenticated%20data%20is%20reachable%20under%20the%20reported%20arbitrary-origin%20policy.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-H%20'Origin%3A%20https%3A%2F%2Fattacker.example'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20supplied%20admin%20test%20user%2C%20then%20copy%20its%20Authorization%20bearer%20header%20from%20the%20profile%20request%20in%20the%20browser%20DevTools%20Network%20tab%20and%20provide%20it%20to%20the%20verifier.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Login%20endpoint%20enables%20email%20account%20enumeration%22%2C%22description%22%3A%22The%20unauthenticated%20login%20endpoint%20returns%20different%20error%20codes%20and%20messages%20for%20an%20unknown%20email%20address%20and%20a%20known%20email%20address%20with%20an%20incorrect%20password.%22%2C%22impact%22%3A%22An%20attacker%20can%20identify%20registered%20email%20addresses%20and%20use%20that%20information%20to%20target%20password%20attacks%20or%20phishing.%22%2C%22likelihood%22%3A%22High.%20The%20distinction%20is%20remotely%20observable%20without%20authentication%20using%20a%20single%20login%20request%20for%20each%20candidate%20address.%22%2C%22recommendation%22%3A%22Return%20the%20same%20HTTP%20status%2C%20error%20code%2C%20message%2C%20and%2C%20where%20practical%2C%20similar%20response%20timing%20for%20unknown%20users%20and%20incorrect%20passwords.%20Avoid%20revealing%20whether%20the%20submitted%20email%20address%20is%20registered.%22%2C%22cvss_score%22%3A3.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Two%20unauthenticated%20requests%20produced%20distinguishable%20401%20responses.%20The%20unknown%20address%20audit-probe%40example.invalid%20returned%20USER_NOT_FOUND%20with%20%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%2C%20while%20the%20known%20address%20admin%40example.com%20with%20an%20incorrect%20password%20returned%20WRONG_PASSWORD%20with%20%5C%22Incorrect%20password.%5C%22%5Cn%5CnSpecialist%20evidence%3A%5CnBoth%20failed%20requests%20were%20sent%20with%20Authorization%3A%20none%20and%20Cookies%3A%20none.%20The%20nonexistent%20email%20returned%20HTTP%20401%20code%20USER_NOT_FOUND%20and%20message%20%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%20The%20known%20test%20account%20email%20with%20a%20wrong%20password%20returned%20HTTP%20401%20code%20WRONG_PASSWORD%20and%20message%20%5C%22Incorrect%20password.%5C%22.%5Cn%5CnSpecialist%20evidence%3A%5CnAnonymous%20wire%20probes%20explicitly%20used%20Authorization%3A%20none%20and%20Cookies%3A%20none.%20POST%20with%20deep-worker-invalid%40example.invalid%20returned%20HTTP%20401%20code%20USER_NOT_FOUND%2C%20while%20POST%20with%20admin%40example.com%20and%20a%20wrong%20password%20returned%20HTTP%20401%20code%20WRONG_PASSWORD.%22%2C%22request_evidence%22%3A%22Authorization%3A%20none%3B%20Cookies%3A%20none.%20POST%20%2Fapi%2Fauth%2Flogin%20JSON%20%7B%5C%22email%5C%22%3A%5C%22audit-probe%40example.invalid%5C%22%2C%5C%22password%5C%22%3A%5C%22definitely-wrong%5C%22%7D%3B%20POST%20%2Fapi%2Fauth%2Flogin%20JSON%20%7B%5C%22email%5C%22%3A%5C%22admin%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22admin%5C%22%7D.%5Cn%5CnSpecialist%20request%3A%5CnAuthorization%3A%20none%3B%20Cookies%3A%20none.%20POST%20%2Fapi%2Fauth%2Flogin%20with%20%7B%5C%22email%5C%22%3A%5C%22deep-audit-probe%40example.invalid%5C%22%2C%5C%22password%5C%22%3A%5C%22WrongPassword!123%5C%22%7D%3B%20then%20Authorization%3A%20none%3B%20Cookies%3A%20none.%20POST%20%2Fapi%2Fauth%2Flogin%20with%20%7B%5C%22email%5C%22%3A%5C%22deep-weak-probe-20260913%40example.invalid%5C%22%2C%5C%22password%5C%22%3A%5C%22WrongPassword!123%5C%22%7D.%5Cn%5CnSpecialist%20request%3A%5CnAuthorization%3A%20none%3B%20Cookies%3A%20none.%20Anonymous%20POST%20%2Fapi%2Fauth%2Flogin%20with%20the%20two%20bounded%20synthetic%20credential%20cases.%22%2C%22response_evidence%22%3A%22401%20%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D%7D%20versus%20401%20%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%7D.%5Cn%5CnSpecialist%20response%3A%5CnUnknown%20email%3A%20HTTP%20401%20USER_NOT_FOUND%2C%20%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%20Known%20email%20with%20wrong%20password%3A%20HTTP%20401%20WRONG_PASSWORD%2C%20%5C%22Incorrect%20password.%5C%22.%5Cn%5CnSpecialist%20response%3A%5CnUnknown%20email%3A%20%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%7D%3B%20known%20email%3A%20%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%7D.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20login%20route%20is%20correctly%20unauthenticated%20by%20design%2C%20but%20its%20failures%20reveal%20account%20existence.%20Anonymous%2C%20cookie-free%20requests%20with%20the%20same%20invalid%20password%20returned%20USER_NOT_FOUND%20for%20audit-probe-2%40example.invalid%20and%20WRONG_PASSWORD%20for%20the%20known%20account%20amelia.chen%40example.com%3B%20the%20same%20distinction%20also%20reproduced%20for%20admin%40example.com.%20This%20rules%20out%20session%20carryover%20and%20an%20admin-only%20special%20case%2C%20so%20the%20endpoint%20supports%20email%20account%20enumeration.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22%2C%5C%22password%5C%22%3A%5C%22same-invalid-password%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20browser%20security%20headers%20on%20banking%20HTML%20shell%22%2C%22description%22%3A%22The%20unauthenticated%20HTML%20shell%20at%20%2Fbanking%2F%20is%20served%20without%20common%20browser%20security%20headers%2C%20including%20CSP%2C%20HSTS%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy.%22%2C%22impact%22%3A%22The%20page%20has%20fewer%20browser-enforced%20protections%20against%20clickjacking%2C%20MIME%20sniffing%2C%20referrer%20leakage%2C%20and%20the%20impact%20of%20script%20injection.%22%2C%22likelihood%22%3A%22Medium%22%2C%22recommendation%22%3A%22Configure%20HTML%20responses%20with%20a%20restrictive%20Content-Security-Policy%2C%20Strict-Transport-Security%20where%20HTTPS%20is%20enforced%2C%20X-Content-Type-Options%3A%20nosniff%2C%20frame-ancestors%20or%20X-Frame-Options%2C%20and%20an%20appropriate%20Referrer-Policy.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%22%2C%22evidence%22%3A%22An%20anonymous%20HEAD%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%20returned%20HTTP%20200%20without%20authorization%20or%20cookies.%20Direct%20header%20inspection%20showed%20only%20Date%2C%20Server%2C%20Last-Modified%2C%20ETag%2C%20Accept-Ranges%2C%20Content-Length%2C%20Keep-Alive%2C%20Connection%2C%20and%20Content-Type.%20Strict-Transport-Security%2C%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy%20were%20absent.%22%2C%22request_evidence%22%3A%22HEAD%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%3B%20the%20HTTP%20probe%20recorded%20Authorization%3A%20none%20and%20Cookies%3A%20none.%22%2C%22response_evidence%22%3A%22HTTP%20200%3B%20Content-Type%3A%20text%2Fhtml%3B%20no%20CSP%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20or%20Referrer-Policy%20headers.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20direct%20anonymous%20GET%20to%20the%20local%20Apache%20origin%20reproduced%20the%20reported%20200%20response%20and%20the%20same%20absence%20of%20CSP%2C%20HSTS%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy.%20A%20byte-range%20fetch%20of%20the%20HTML%20head%20showed%20no%20meta-tag%20equivalent%2C%20and%20the%20response%20identifies%20Apache%20on%20localhost%20rather%20than%20a%20CDN-layer%20response%20that%20could%20be%20adding%20protection.%20HSTS%20is%20inapplicable%20to%20this%20HTTP-only%20origin%2C%20but%20the%20other%20reported%20headers%20remain%20absent%2C%20so%20there%20is%20no%20concrete%20benign%20explanation%20for%20the%20finding.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Verbose%20authentication%20errors%20disclose%20stack%20traces%20and%20server%20paths%22%2C%22description%22%3A%22Submitting%20a%20malformed%20bearer%20token%20without%20a%20jti%20value%20to%20GET%20%2Fapi%2Faccounts%2F6%20causes%20the%20authentication%20middleware%20to%20return%20an%20HTTP%20500%20response%20containing%20a%20PHP%20stack%20trace%2C%20absolute%20filesystem%20paths%2C%20class%20and%20method%20names%2C%20and%20source%20line%20numbers.%22%2C%22impact%22%3A%22An%20unauthenticated%20caller%20can%20learn%20server%20and%20middleware%20implementation%20details%20that%20may%20assist%20targeted%20attacks.%22%2C%22likelihood%22%3A%22medium%22%2C%22recommendation%22%3A%22Return%20a%20generic%20HTTP%20400%20or%20401%20response%20for%20invalid%20tokens.%20Disable%20stack%20traces%20and%20internal%20error%20details%20in%20production%20responses%2C%20while%20recording%20diagnostic%20details%20in%20server-side%20logs.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%2F6%22%2C%22evidence%22%3A%22A%20GET%20request%20to%20%2Fapi%2Faccounts%2F6%20with%20an%20alg%3Dnone%20bearer%20token%20lacking%20jti%20returned%20HTTP%20500.%20The%20response%20exposed%20the%20error%20%60AuthService%3A%3AisTokenRevoked()%3A%20Argument%20%231%20(%24jti)%20must%20be%20of%20type%20string%2C%20null%20given%60%2C%20the%20paths%20%60%2Fvar%2Fwww%2Fhtml%2Fsrc%2FMiddleware%2FAuthMiddleware.php%60%20and%20%60%2Fvar%2Fwww%2Fhtml%2Fsrc%2FServices%2FAuthService.php%60%2C%20lines%2028%20and%2077%2C%20and%20the%20full%20call%20chain.%22%2C%22request_evidence%22%3A%22Authorization%3A%20supplied%20malformed%20alg%3Dnone%20bearer%20token%20without%20jti%3B%20Cookies%3A%20none%3B%20GET%20%2Fapi%2Faccounts%2F6%22%2C%22response_evidence%22%3A%22HTTP%20500%20JSON%20error%20with%20AuthService%20and%20AuthMiddleware%20stack%20trace%2C%20absolute%20paths%2C%20and%20line%20numbers.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20structurally%20complete%20alg%3Dnone%20token%20with%20standard%20identity%20and%20time%20claims%2C%20but%20no%20jti%2C%20reproduced%20the%20reported%20500%20and%20exposed%20the%20PHP%20exception%2C%20absolute%20paths%2C%20line%20numbers%2C%20and%20call%20trace.%20A%20valid%20supplied%20admin%20session%20reached%20the%20route%20normally%2C%20and%20adding%20a%20string%20jti%20changed%20the%20result%20to%20the%20normal%20404%20account%20response%2C%20so%20this%20is%20specific%20to%20the%20missing-jti%20path%20rather%20than%20a%20generic%20malformed-token%20or%20nonexistent-account%20response.%20The%20response%20therefore%20directly%20confirms%20verbose%20authentication%20error%20disclosure.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22No%20observable%20rate%20limiting%20on%20transfer%20checks%22%2C%22description%22%3A%22The%20authenticated%20POST%20%2Fapi%2Ftransfers%2Fcheck%20endpoint%20accepted%20six%20repeated%20requests%20with%20the%20same%20valid%20manual-transfer%20check%20without%20throttling%20or%20changing%20its%20response.%22%2C%22impact%22%3A%22Repeated%20checks%20may%20consume%20application%20resources%20and%20support%20high-volume%20probing%20of%20transfer%20policy%20state.%20The%20endpoint%20does%20not%20accept%20an%20OTP%20or%20move%20funds%2C%20limiting%20the%20observed%20impact.%22%2C%22likelihood%22%3A%22Medium.%20The%20behavior%20was%20reproduced%20with%20an%20authenticated%20user%20using%20six%20bounded%20requests%3B%20no%20bulk%20traffic%20was%20sent.%22%2C%22recommendation%22%3A%22Apply%20per-user%20and%20per-IP%20throttling%20to%20transfer-check%20requests.%20Return%20HTTP%20429%20with%20a%20Retry-After%20header%20when%20limits%20are%20exceeded%2C%20and%20monitor%20bursts%20of%20repeated%20checks.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AL%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%22%2C%22evidence%22%3A%22A%20repeat_sequence%20named%20transfer-check-rate-limit%20sent%20six%20authenticated%20POST%20requests%20with%20body%20%7B%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%7D.%20Every%20request%20returned%20HTTP%20200%20with%20the%20same%20result%3A%20%7Brequires_totp%3Atrue%2Creason%3A%5C%22manual_entry%5C%22%2Ctotp_configured%3Afalse%7D.%20No%20429%20response%20or%20Retry-After%20header%20was%20observed.%22%2C%22request_evidence%22%3A%22Six%20bounded%20POST%20requests%20to%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fcheck%3B%20Authorization%3A%20Bearer%20login-issued%20JWT%3B%20body%20%7B%5C%22transfer_type%5C%22%3A%5C%22manual%5C%22%7D.%22%2C%22response_evidence%22%3A%22HTTP%20200%20with%20the%20same%20successful%20check%20result%3B%20no%20rate-limit%20status%20or%20retry%20guidance.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20endpoint%20is%20a%20stateless%2C%20authenticated%20preflight%20policy%20lookup%2C%20not%20the%20transfer%20operation.%20Live%20checks%20show%20it%20only%20accepts%20the%20documented%20enum%20values%20(own%2C%20address_book%2C%20manual)%20and%20returns%20a%20policy%20result%20that%20changes%20with%20the%20selector%3B%20the%20manual%20check%20returns%20no%20transfer%20identifier%2C%20token%2C%20or%20state%20transition.%20Repeating%20this%20harmless%20read-only%20check%20six%20times%20therefore%20has%20a%20concrete%20benign%20explanation%3A%20it%20is%20intentionally%20idempotent%20and%20does%20not%20need%20a%20transaction-style%20rate%20limit%2C%20so%20identical%20200%20responses%20do%20not%20demonstrate%20an%20insecure%20business-logic%20flaw.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22TRACE%20method%20enabled%20on%20admin%20accounts%20route%22%2C%22description%22%3A%22The%20unauthenticated%20admin%20accounts%20route%20accepts%20TRACE%20requests%20and%20reflects%20the%20request%20line%20and%20headers%20in%20the%20response%20body.%22%2C%22impact%22%3A%22An%20attacker%20may%20obtain%20request%20headers%20if%20a%20client%20or%20intermediary%20sends%20sensitive%20values%20through%20this%20TRACE-capable%20route.%20The%20route%20also%20exposes%20an%20unnecessary%20diagnostic%20method.%22%2C%22likelihood%22%3A%22Low%20to%20medium.%20Exploitation%20depends%20on%20sensitive%20headers%20being%20sent%20through%20a%20client%20or%20proxy%20that%20permits%20TRACE.%22%2C%22recommendation%22%3A%22Disable%20TRACE%20at%20the%20web%20server%20and%20reverse%20proxy.%20Restrict%20the%20route%20to%20only%20the%20HTTP%20methods%20required%20by%20the%20API.%22%2C%22cvss_score%22%3A3.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%22%2C%22evidence%22%3A%22An%20anonymous%20TRACE%20request%20to%20the%20affected%20URL%20returned%20HTTP%20200%20and%20reflected%20the%20request%20line%20'TRACE%20%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%20HTTP%2F1.1'%20and%20the%20header%20'X-Aespa-Probe%3A%20admin-route-metadata-proof'.%20No%20Authorization%20header%20or%20cookies%20were%20sent.%22%2C%22request_evidence%22%3A%22TRACE%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Faccounts%3Fpage%3D1%26per_page%3D20%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%3B%20X-Aespa-Probe%3A%20admin-route-metadata-proof.%22%2C%22response_evidence%22%3A%22HTTP%20200%20with%20a%20response%20body%20reflecting%20the%20TRACE%20request%20line%20and%20synthetic%20header.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20response%20is%20a%20generic%20Apache%20TRACE%20echo%2C%20not%20an%20application%20response%20from%20the%20admin%20route%3A%20it%20has%20%60Server%3A%20Apache%2F2.4.68%60%2C%20%60Content-Type%3A%20message%2Fhttp%60%2C%20and%20the%20same%20200%20echo%20is%20returned%20for%20a%20nonexistent%20unrelated%20path.%20The%20underlying%20anonymous%20GET%20to%20%60%2Fapi%2Fadmin%2Faccounts%60%20returns%20401%20with%20%60UNAUTHORIZED%60%20and%20no%20account%20data%2C%20and%20the%20echo%20is%20unchanged%20when%20using%20the%20listed%20%60admin_test%60%20session%20except%20for%20reflecting%20its%20headers.%20This%20is%20a%20server-wide%20TRACE%20configuration%20issue%2C%20not%20unauthenticated%20access%20to%20the%20admin%20accounts%20route.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Unauthenticated%20access%20to%20admin%20SPA%20shell%20and%20assets%22%2C%22description%22%3A%22Unauthenticated%20requests%20to%20%2Fadmin%2F%20and%20%2Fadmin%2F%3Froute_exposure_check%3D1%20return%20the%20administration-panel%20HTML%20shell%2C%20login%20form%2C%20and%20client-side%20system-route%20assets%20before%20login.%20The%20administrative%20login%20page%20is%20publicly%20reachable%20over%20HTTP.%22%2C%22impact%22%3A%22An%20attacker%20can%20inspect%20the%20admin%20application%20structure%2C%20route%20names%2C%20and%20client-side%20API%20details.%20The%20tested%20admin%20APIs%20returned%20HTTP%20401%2C%20so%20this%20does%20not%20demonstrate%20access%20to%20admin%20data%20or%20an%20authentication%20bypass.%22%2C%22likelihood%22%3A%22high%22%2C%22recommendation%22%3A%22Keep%20authorization%20checks%20on%20every%20admin%20API.%20If%20the%20panel%20should%20not%20be%20publicly%20discoverable%2C%20protect%20its%20static%20entry%20point%20and%20assets%20with%20the%20same%20access%20boundary%20or%20a%20separate%20access%20gateway.%22%2C%22cvss_score%22%3A3.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%22%2C%22evidence%22%3A%22Without%20an%20Authorization%20header%20or%20cookies%2C%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%3Froute%3D%252Fsystem%20returned%20HTTP%20200%20with%20the%20title%20'The%20Bank%20of%20Ed%20-%20Admin'%2C%20administration-panel%20markup%2C%20and%20a%20login%20form.%20HTTP%20200%20was%20also%20recorded%20for%20%2Fadmin%2Fjs%2Fpages%2Fsystem.js%2C%20%2Fadmin%2Fjs%2Fapp.js%2C%20%2Fadmin%2Fjs%2Frouter.js%2C%20and%20%2Fadmin%2Fjs%2Fapi.js.%20Protected%20admin%20API%20baselines%20returned%20HTTP%20401.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%3Froute%3D%252Fsystem%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none%22%2C%22response_evidence%22%3A%22HTTP%20200%3B%20administration-panel%20HTML%20and%20login%20form%20returned%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20200%20response%20is%20the%20intended%20unauthenticated%20bootstrap%20for%20a%20client-side%20admin%20application%3A%20it%20serves%20static%20HTML%20with%20a%20login%20view%20and%20public%20JavaScript%2C%20not%20an%20authenticated%20admin%20session%20or%20administrative%20data.%20The%20public%20API%20client%20explicitly%20stores%20a%20token%20and%20sends%20it%20as%20Authorization%2C%20and%20direct%20anonymous%20requests%20to%20both%20%2Fapi%2Fadmin%2Fcustomers%20and%20the%20exact%20system%20resource%20%2Fapi%2Fadmin%2Fsystem%2Fsettings%20returned%20401%20with%20%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%20The%20system.js%20asset%20only%20calls%20that%20protected%20settings%20API%2C%20so%20the%20shell%20and%20route%20assets%20being%20downloadable%20do%20not%20bypass%20the%20authorization%20boundary.%22%2C%22merged_instances%22%3A%22%5B%7B%5C%22finding_id%5C%22%3A%202079%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-019%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Unauthenticated%20admin%20console%20shell%20exposure%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20GET%20request%20to%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%20with%20no%20Authorization%20header%20or%20cookies%20returned%20HTTP%20200%20and%20the%2019%2C733-character%20'The%20Bank%20of%20Ed%20-%20Admin'%20shell.%20The%20response%20contained%20the%20login%20form%20and%20references%20to%20router.js%2C%20api.js%2C%20customers.js%2C%20accounts.js%2C%20system.js%2C%20and%20fx-rates.js.%20An%20anonymous%20request%20to%20%2Fadmin%20returned%20the%20same%20shell.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20with%20the%20admin%20shell%20and%20login%20form.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22false_positive%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20admin%20URL%20is%20a%20public%20single-page-app%20bootstrap%20that%20serves%20the%20login%20form%20and%20static%20JavaScript%20before%20a%20user%20signs%20in.%20The%20referenced%20API%20client%20uses%20%2Fapi%2Fadmin%20and%20sends%20a%20bearer%20token%20only%20after%20login%3B%20an%20anonymous%20GET%20to%20the%20client-derived%20customer%20endpoint%2C%20%2Fapi%2Fadmin%2Fcustomers%2C%20returned%20401%20with%20%5C%5C%5C%22Missing%20or%20invalid%20Authorization%20header%5C%5C%5C%22%20and%20no%20customer%20data.%20This%20is%20an%20intentional%20public%20login%20shell%2C%20while%20the%20privileged%20admin%20data%20boundary%20is%20enforced%20by%20the%20API.%5C%22%7D%2C%20%7B%5C%22finding_id%5C%22%3A%202084%2C%20%5C%22finding_reference%5C%22%3A%20%5C%22JUQE-024%5C%22%2C%20%5C%22title%5C%22%3A%20%5C%22Unauthenticated%20administrative%20login%20page%20exposure%5C%22%2C%20%5C%22severity%5C%22%3A%20%5C%22low%5C%22%2C%20%5C%22affected_url%5C%22%3A%20%5C%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%3Froute_exposure_check%3D1%5C%22%2C%20%5C%22evidence%5C%22%3A%20%5C%22An%20anonymous%20GET%20request%20to%20the%20affected%20URL%20returned%20HTTP%20200%20and%20an%20HTML%20page%20identifying%20'The%20Bank%20of%20Ed%20-%20Admin'%2C%20'Administration%20Panel'%2C%20and%20a%20username%2Fpassword%20login%20form.%20The%20route%20was%20also%20recorded%20as%20GET%20%2Fadmin%2F%20-%3E%20200.%5C%22%2C%20%5C%22request_evidence%5C%22%3A%20%5C%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%3Froute_exposure_check%3D1%3B%20Authorization%3A%20none%3B%20Cookies%3A%20none.%5C%22%2C%20%5C%22response_evidence%5C%22%3A%20%5C%22HTTP%20200%20with%20an%20admin%20title%2C%20'Administration%20Panel'%2C%20and%20username%2Fpassword%20login%20form.%5C%22%2C%20%5C%22validation_status%5C%22%3A%20%5C%22false_positive%5C%22%2C%20%5C%22validation_note%5C%22%3A%20%5C%22The%20reported%20URL%20serves%20the%20intended%20public%20administrative%20login%20shell%2C%20which%20must%20be%20reachable%20before%20authentication.%20The%20admin%20client%20marks%20only%20the%20login%20route%20as%20unauthenticated%2C%20and%20a%20direct%20anonymous%20request%20to%20the%20protected%20customer%20API%20returned%20401%20with%20%5C%5C%5C%22Missing%20or%20invalid%20Authorization%20header%5C%5C%5C%22%20instead%20of%20administrative%20data.%20This%20is%20a%20public%20login%20entry%20point%20with%20the%20data%2FAPI%20boundary%20still%20enforced%2C%20so%20the%20200%20response%20is%20not%20an%20administrative%20access%20exposure.%5C%22%7D%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%5D
-->

## 1. External transfers permit unauthorized account debits and unbounded overdrafts

- Finding reference: JUQE-057
- Severity: critical
- OWASP: A04
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transfers/external
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:N/I:H/A:H)

### Description
The external transfer endpoint does not verify that the requested source account belongs to the authenticated user and does not enforce an available-balance limit before completing the debit.

### Impact
An authenticated user may debit another user's account and create a large negative balance, causing direct financial loss and corrupting account state.

### Likelihood
High in the observed context: one authenticated request naming an account absent from the user's account list completed successfully and produced a negative balance.

### Recommendation
Load the source account through the authenticated user's ownership relation and reject accounts outside that relation. Enforce positive available-balance and transaction-limit checks in the same database transaction as the debit. Reject the request before creating the transaction when either check fails.

### Evidence
```
For authenticated user Amelia Chen (user id 1), GET /api/accounts returned account IDs 1, 2, 3, and 51, excluding account 6. A POST to the external transfer endpoint using from_account_id 6 and amount 99999999 returned HTTP 201 with success=true, transaction_id=39, status=completed, and new_from_balance=-99998123.82.
```

### Request Evidence
```
{"from_account_id":6,"to_bsb":"000-000","to_account_number":"30000001","amount":99999999,"description":"safe ownership upper-bound probe","totp_code":"000000"}
```

### Response Evidence
```
{"success":true,"data":{"transaction_id":39,"from_account_id":6,"amount":"99999999","new_from_balance":"-99998123.82","status":"completed"},"message":"Transfer completed successfully"}
```

### Validation Note
The live admin session's account list contained 1, 2, 3, and 51, while GET /api/accounts/6 returned NOT_FOUND, yet a POST using from_account_id 6 completed and returned a new balance of -99998123.84. A separate controlled check exhausted the balance-control explanation: after account 1 reached 0.00, a 0.01 external transfer still returned 201 and produced -0.01. The ordinary Amelia session labels were unavailable and returned 401, so the exact Amelia replay could not be made, but the endpoint's live behavior independently proves both missing balance enforcement and acceptance of a source account inaccessible through the authenticated account API.

## 2. Unauthenticated access to administrative user export

- Finding reference: JUQE-006
- Severity: critical
- OWASP: A01
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/export/users
- CVSS: 9.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The administrative user export at /api/admin/export/users can be accessed without authentication or administrator authorization. It returns multiple user records, including password hashes and persona data.

### Impact
An unauthenticated attacker can download account data for all users, causing privacy harm and enabling offline password-cracking attempts against the exposed hashes.

### Likelihood
High: an anonymous GET request returned the export with HTTP 200 and no authorization or cookies.

### Recommendation
Require authentication and an explicit administrator authorization check before serving the export. Return only the fields required for the export, exclude password hashes and TOTP secrets, and audit access to the route.

### Evidence
```
An anonymous GET returned HTTP 200 with a 38,685-character JSON export containing multiple users, including password_hash values, email addresses, names, addresses, phone numbers, and account metadata. The response began with a successful users export containing user ID 1 and a bcrypt password hash.

Specialist evidence:
Two bounded anonymous GET probes returned HTTP 200 and large JSON user exports. The response included a users array with password_hash, email, address, phone, TOTP status, and timestamps for multiple accounts.

Specialist evidence:
A wire-level GET to http://localhost:8081/api/admin/export/users using the anonymous session had Authorization: none and Cookies: none, yet returned HTTP 200 with {"success":true}. The users array included password_hash, email, address, phone, avatar_url, totp_secret, and totp_enabled fields.
```

### Request Evidence
```
GET http://localhost:8081/api/admin/export/users; Authorization: none; Cookies: none; use_session=anonymous.

Specialist request:
GET http://localhost:8081/api/admin/export/users
Authorization: none
Cookies: none
Session: anonymous

Specialist request:
GET http://localhost:8081/api/admin/export/users; Authorization: none; Cookies: none.
```

### Response Evidence
```
HTTP 200. The response begins with {"success":true,"data":{"users":[{"id":1,"email":"amelia.chen@example.com","password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi","first_name":"Amelia","address_line1":"14 Harbour View Tce","phone":"0411 234 567"}, ...]}}.

Specialist response:
HTTP 200; response size 44,714 characters; response began with {"success":true,"data":{"users":[{"id":1,"email":"amelia.chen@example.com","password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi",... and included records for users 1 through at least 10.

Specialist response:
HTTP 200 JSON response, 47,683 characters, with success:true and a users array containing password_hash and personal contact/address fields.
```

### Validation Note
A credential-free GET with no Authorization header and no cookies returned HTTP 200 JSON, not a generic SPA shell. The response contained a multi-user export with Amelia Chen's email and bcrypt password_hash, plus address and phone fields, so the endpoint is exposing administrative data without authentication. The first disproof assumption therefore failed: this was not session confusion or a frontend-shell response, and the data is not a public catalogue object.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/admin/export/users
```

### Additional Instances

- **Instance 2:** `—`

```
GET http://localhost:8081/api/admin/export/users; Authorization: none; Cookies: none; use_session=anonymous. Follow-up: OPTIONS http://localhost:8081/api/admin/export/users, obligation_id=7016.
```


## 3. Unauthenticated health endpoint exposes JWT secret and database configuration

- Finding reference: JUQE-062
- Severity: critical
- OWASP: A05
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/health
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

### Description
The unauthenticated GET /api/health endpoint, including /api/health?auth_probe=1, returns sensitive runtime configuration: the JWT signing secret, database host, name and user, PHP and Apache versions, and the production environment label.

### Impact
An attacker who can reach the endpoint can obtain the JWT secret and may forge authentication tokens. The disclosed database and server details can also support follow-on attacks.

### Likelihood
High because the endpoint is reachable anonymously and returns the JWT secret directly.

### Recommendation
Return only a minimal health status. Protect diagnostic details with authentication and network restrictions, rotate the exposed JWT secret, and invalidate tokens signed with it.

### Evidence
```
An anonymous GET request returned HTTP 200 and exposed jwt_secret=bankofed-dev-secret-change-in-production, db_host=127.0.0.1, db_name=bankofed, db_user=root, PHP 8.4.25, Apache/2.4.68, and environment=production.
```

### Request Evidence
```
GET http://localhost:8081/api/health; Authorization: none; Cookies: none
```

### Response Evidence
```
HTTP 200 response: {"success":true,"data":{"status":"ok","php_version":"8.4.25","server":"Apache/2.4.68 (Unix)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"root","jwt_secret":"bankofed-dev-secret-change-in-production","environment":"production"},"message":"OK"}
```

### Validation Note
A fresh anonymous request returned HTTP 200 with the JWT secret in plain JSON, along with database connection details and production/version information. The same sensitive body was returned with the provided admin session, so the data is not gated by authentication. The body is populated and specific, which rules out an empty health response or a scanner-only status-code mismatch; no benign explanation remains for publishing the signing secret from an unauthenticated endpoint.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/health
```

### Additional Instances

- **Instance 2:** `—`

```
GET http://localhost:8081/api/health; Authorization: none; Cookies: none

Specialist request:
GET http://localhost:8081/api/health using use_session='anonymous'; Authorization: none; Cookies: none.
```

- **Instance 3:** `—`

```
GET http://localhost:8081/api/health
Authorization: none
Cookies: none
```

- **Instance 4:** `—`

```
GET http://localhost:8081/api/health?auth_probe=1; Authorization: none; Cookies: none.
```


## 4. Admin account accepts the common password `password`

- Finding reference: JUQE-028
- Severity: high
- OWASP: A07
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
The existing admin@example.com account can be authenticated through POST /api/auth/login using the widely known password `password`. The successful response returns an admin bearer token and the admin user record.

### Impact
An attacker who guesses or obtains this password can access the administrator account and its banking functions.

### Likelihood
High because `password` is a widely known, common password and the endpoint accepts it for a privileged account.

### Recommendation
Force the admin account to use a strong, unique password. Reject common and breached passwords, require MFA for privileged accounts, and add login throttling and monitoring.

### Evidence
```
POST http://localhost:8081/api/auth/login with email admin@example.com and password `password` returned HTTP 200 with success:true. The response included data.user.email=admin@example.com, data.user.id=19, data.user.totp_enabled=false, and a bearer token.

Specialist evidence:
The shared tester ledger records a confirmed successful admin authentication using the common password `password`; the associated login probe returned HTTP 200 and the authenticated profile probe returned HTTP 200 before logout.

Specialist evidence:
The shared tester ledger contains the confirmed claim: Admin account accepts the common password `password`. The same ledger records a successful POST to http://localhost:8081/api/auth/login with HTTP 200.
```

### Request Evidence
```
POST http://localhost:8081/api/auth/login with email admin@example.com and password password.

Specialist request:
POST http://localhost:8081/api/auth/login using the confirmed admin account and password `password`.
```

### Response Evidence
```
HTTP 200; success:true; data.user.email=admin@example.com; data.user.id=19; data.user.totp_enabled=false; data.token present.

Specialist response:
The login returned HTTP 200 and the subsequent authenticated GET http://localhost:8081/api/profile returned HTTP 200; logout then returned 200 and profile returned 401.
```

### Validation Note
The exact anonymous login request returned HTTP 200, success:true, the admin user record, and a bearer token. A control request with a clearly wrong password returned HTTP 401 WRONG_PASSWORD, so the handler is validating the supplied password rather than returning a canned response. The issued token was accepted by the read-only GET /api/accounts endpoint, and the returned user record shows the admin account has TOTP disabled; the response also exposes the MD5 hash for password, which matches the supplied common password. These checks rule out the main benign explanations.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"email":"admin@example.com","password":"password"}' http://localhost:8081/api/auth/login
```

## 5. Authenticated avatar import performs server-side requests to arbitrary URLs

- Finding reference: JUQE-055
- Severity: high
- OWASP: A10
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile/avatar
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The authenticated avatar import endpoint at /api/profile/avatar accepts a caller-controlled URL and fetches it from the server.

### Impact
An authenticated user can make the server request reachable services and receive response bodies, potentially exposing internal web content or service credentials where network access permits.

### Likelihood
High where an authenticated user can reach the endpoint and the server has access to internal services.

### Recommendation
Allow only approved image schemes and hosts. Resolve and validate destinations before connecting, block loopback, private, and link-local ranges after DNS resolution, limit redirects, enforce response size and content-type limits, and do not return fetched content to the client.

### Evidence
```
An authenticated POST with {"url":"http://localhost:8081/banking/"} returned HTTP 200 and a 55,420-byte JSON response. The data.avatar_data value began with data:text/html;base64 and decoded to the Bank of Ed banking page. A URL containing an injected query string also returned success, showing the URL was used as supplied.
```

### Request Evidence
```
Authenticated POST http://localhost:8081/api/profile/avatar with JSON url http://localhost:8081/banking/.
```

### Response Evidence
```
HTTP 200; response data.avatar_data is a large data:text/html;base64 value containing the fetched banking HTML.
```

### Validation Note
A valid external PNG URL returned imported image bytes, proving this endpoint performs a server-side fetch rather than echoing the submitted URL. The same authenticated request to localhost:8081/banking/ returned a data:text/html value containing the Bank of Ed page, and the equivalent 127.0.0.1 URL behaved the same way. The internal response is fetched content, not a static error message, and private-address filtering is absent.

## 6. Bearer token stored in script-readable localStorage

- Finding reference: JUQE-035
- Severity: high
- OWASP: A02
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/banking/js/pages/auth.js
- CVSS: 7.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N)

### Description
The banking authentication workflow and client code at /banking/#/login, /auth/login, /api/admin/auth/login, /banking/js/api.js?v=20260213-2, and /banking/js/pages/auth.js store the server-issued bearer token in localStorage under bankofed_token, alongside the user object in the login flow. The client reads it for API requests, so any JavaScript running in the application origin can read the token.

### Impact
An XSS vulnerability or compromised third-party script on the origin could steal the token and perform authenticated actions as the user.

### Likelihood
Medium in the observed context, increasing to high if script injection or third-party script compromise is present.

### Recommendation
Store session credentials in Secure, HttpOnly, SameSite cookies where possible. Rotate potentially exposed tokens and reduce the number and privileges of scripts trusted on the origin.

### Evidence
```
GET http://localhost:8081/banking/js/pages/auth.js returned 200. The confirmed script behavior stores the bearer token in script-readable localStorage.
```

### Request Evidence
```
GET http://localhost:8081/banking/js/pages/auth.js returned 200.
```

### Response Evidence
```
The confirmed script behavior stores the bearer token in localStorage.
```

### Validation Note
The live auth.js response passes res.data.token to Api.setToken on both login and registration. The same-origin api.js implementation writes that argument directly to localStorage under bankofed_token, and the banking entry page loads api.js before auth.js as executable JavaScript. I also verified with the provided admin session that the resulting bearer credential is accepted by GET /api/profile, so this is not dead code or a non-authentication value; HTTPS or a TLS-terminating proxy would not prevent same-origin JavaScript from reading localStorage.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/banking/js/api.js
```

### Additional Instances

- **Instance 2:** `—`

```
GET http://localhost:8081/banking/js/api.js and GET http://localhost:8081/banking/js/pages/auth.js.
```

- **Instance 3:** `—`

```
GET http://localhost:8081/banking/js/api.js and GET http://localhost:8081/banking/js/pages/auth.js returned the client source used by the login flow.
```

- **Instance 4:** `—`

```
GET http://localhost:8081/banking/js/api.js?v=20260213-2 with Range: bytes=0-1500
```

- **Instance 5:** `—`

```
The login workflow was associated with http://localhost:8081/auth/login.
```


## 7. Cleartext HTTP used across the banking application and APIs

- Finding reference: JUQE-008
- Severity: high
- OWASP: A02
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/
- CVSS: 8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The service at http://localhost:8081 exposes web pages and APIs over plain HTTP without requiring HTTPS or redirecting HTTP clients. This includes the administrative login page at /admin/#/login and the authenticated customer endpoint at /api/admin/customers/16, which returns sensitive customer and account data.

### Impact
An observer on the network path can read the exported account data in transit. Password hashes may support offline password attacks, and exposed personal data creates a privacy risk.

### Likelihood
High on network paths where traffic to the HTTP service can be observed.

### Recommendation
Serve the application and export endpoint only over HTTPS. Redirect or reject HTTP, enable HSTS at the TLS termination point, and remove password hashes and unnecessary sensitive fields from the export.

### Evidence
```
GET http://localhost:8081/api/admin/export/users returned an export containing password_hash, email, address_line1, suburb, state, postcode, and phone over the http:// scheme. A follow-up HEAD request to the same URL returned HTTP 200, confirming the route is served over cleartext HTTP.
```

### Request Evidence
```
GET http://localhost:8081/api/admin/export/users returned the sensitive export over the http:// scheme. Follow-up: HEAD http://localhost:8081/api/admin/export/users with use_session=anonymous, obligation_id=7015.
```

### Response Evidence
```
The GET response contained fields including password_hash, email, address_line1, suburb, state, postcode, and phone. The HEAD response was HTTP 200 at the same http:// URL.
```

### Validation Note
A live authenticated GET over http:// returned status 200 with password_hash and personal fields in the response body, so this is not evidence from a static log or template. I checked the default HTTPS port and alternate port 8443, and no TLS service was reachable; HTTPS on port 8081 returned a TLS wrong-version error, while a live HEAD on the reported HTTP route returned 200 with no redirect or HSTS header. The export is therefore served directly over cleartext HTTP with no verified TLS front door to provide the innocent reverse-proxy explanation.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/admin/export/users -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user and copy the bearer token from the Authorization header or browser storage.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

### Additional Instances

- **Instance 2:** `—`

```
GET http://localhost:8081/api/accounts; HEAD http://localhost:8081/api/accounts; GET https://localhost:8081/api/accounts

Specialist request:
HEAD http://localhost:8081/api/accounts; HEAD https://localhost:8081/api/accounts

Specialist request:
GET http://localhost:8081/api/accounts over HTTP returned status 200 in the shared baseline.

Specialist request:
POST http://localhost:8081/api/accounts returned HTTP 201 according to the shared tester ledger.
```

- **Instance 3:** `—`

```
GET http://localhost:8081/api/insurance/sso; GET https://localhost:8081/api/insurance/sso

Specialist request:
GET http://localhost:8081/api/insurance/sso; follow-up GET https://localhost:8081/api/insurance/sso.
```

- **Instance 4:** `—`

```
GET and HEAD requests used the literal http://localhost:8081/ URL. The anonymous GET used Authorization: none and Cookies: none.
```

- **Instance 5:** `—`

```
GET http://localhost:8081/api/admin/accounts?page=1&per_page=20 -> 200 in the supplied baseline.

Specialist request:
GET http://localhost:8081/api/admin/accounts?page=1&per_page=20 -> 200 from the supplied tester ledger; HEAD https://localhost:8081/api/admin/accounts?page=1&per_page=20 was used as the transport follow-up.
```

- **Instance 6:** `—`

```
GET http://localhost:8081/api/address-book -> 200 (shared authenticated baseline). Anonymous confirmation used GET over the same http:// URL.

Specialist request:
GET http://localhost:8081/api/address-book using the authenticated session; recorded result: HTTP 200.

Specialist request:
GET http://localhost:8081/api/address-book -> 200 (shared baseline); GET https://localhost:8081/api/address-book (bounded scheme follow-up).
```

- **Instance 7:** `—`

```
GET http://localhost:8081/api/transactions?account_id=1&page=1&per_page=15 returned 200 in the authenticated baseline; the same URL with https was then requested once.
```

- **Instance 8:** `—`

```
HEAD http://localhost:8081/api/admin/system/settings

Specialist request:
GET http://localhost:8081/api/admin/system/settings over cleartext HTTP; anonymous request returned 401.
```

- **Instance 9:** `—`

```
GET http://localhost:8081/banking/; GET https://localhost:8081/banking/

Specialist request:
GET http://localhost:8081/banking/ over HTTP returned 200/206 in the shared baseline. GET https://localhost:8081/banking/ was attempted as the TLS comparison.
```

- **Instance 10:** `—`

```
POST http://localhost:8081/api/admin/auth/login over HTTP with credentials in the request body.

Specialist request:
POST http://localhost:8081/api/admin/auth/login over http://localhost:8081 with a username and password in the JSON request body.
```

- **Instance 11:** `—`

```
POST http://localhost:8081/api/admin/auth/login with Content-Type: application/json and a JSON username/password body.

Specialist request:
POST http://localhost:8081/api/admin/auth/login with a non-real username and password over HTTP.

Specialist request:
POST http://localhost:8081/api/admin/auth/login; JSON body contained username and password fields using non-real probe values.

Specialist request:
POST http://localhost:8081/api/admin/auth/login over http://

Specialist request:
POST http://localhost:8081/api/admin/auth/login with Content-Type: application/json and a username/password JSON body.
```

- **Instance 12:** `—`

```
GET https://localhost:8081/api/admin/customers?search=zoe&per_page=15.

Specialist request:
GET http://localhost:8081/api/admin/customers?search=zoe&per_page=15
```

- **Instance 13:** `—`

```
POST http://localhost:8081/api/auth/login; Content-Type: application/json; body contained synthetic email and password fields.

Specialist request:
POST http://localhost:8081/api/auth/login over HTTP with JSON credentials: deep-worker-invalid@example.invalid / wrong-password-2026.

Specialist request:
POST http://localhost:8081/api/auth/login was used for login attempts over an http:// URL.
```

- **Instance 14:** `—`

```
POST http://localhost:8081/api/auth/login
Content-Type: application/json
{"email":"probe.invalid@example.test","password":"Wrong-Only-For-Bounded-Probe-9f3c"}

Specialist request:
POST http://localhost:8081/api/auth/login with Content-Type: application/json and body {}
```

- **Instance 15:** `—`

```
GET http://localhost:8081/api/admin/fx-rates?transport_check=1; Authorization: none; Cookies: none. GET https://localhost:8081/api/admin/fx-rates; Authorization: none; Cookies: none.
```

- **Instance 16:** `—`

```
POST http://localhost:8081/api/auth/register; Authorization: none; Cookies: none; JSON included the user's password.

Specialist request:
POST http://localhost:8081/api/auth/register with JSON containing a password.

Specialist request:
POST http://localhost:8081/api/auth/register using use_session='anonymous'; URL scheme is http; body included {"email":"deep-campaign-20260913-01@example.test","password":"123456","first_name":"Deep","last_name":"Campaign"}. Authorization: none. Cookies: none.
```

- **Instance 17:** `—`

```
GET http://localhost:8081/api/profile over HTTP; GET https://localhost:8081/api/profile over HTTPS.
```

- **Instance 18:** `—`

```
HEAD http://localhost:8081/admin/

Specialist request:
GET /admin/ HTTP/1.1
Host: localhost:8081
Authorization: none
Cookies: none
```

- **Instance 19:** `—`

```
GET http://localhost:8081/ -> 200; follow-up GET https://localhost:8081/ -> SSL failure: WRONG_VERSION_NUMBER.

Specialist request:
HEAD http://localhost:8081/ with use_session='anonymous' returned HTTP 200. The preceding anonymous GET used the same cleartext HTTP origin.
```

- **Instance 20:** `—`

```
GET http://localhost:8081/api/profile

Specialist request:
GET http://localhost:8081/api/profile (authenticated baseline, 200); comparison GET https://localhost:8081/api/profile.
```

- **Instance 21:** `—`

```
POST http://localhost:8081/api/auth/login over http:// with an invalid email marker.
```

- **Instance 22:** `—`

```
GET http://localhost:8081/banking/?cleartext_probe=1 over http://.
```

- **Instance 23:** `—`

```
GET http://localhost:8081/banking/
```

- **Instance 24:** `—`

```
GET http://localhost:8081/banking/ over http://localhost:8081/
```

- **Instance 25:** `—`

```
HEAD http://localhost:8081/api/admin/customers/3; Authorization: none; Cookies: none. Separate probe: GET https://localhost:8081/api/admin/customers/3; Authorization: none; Cookies: none.

Specialist request:
GET http://localhost:8081/api/admin/customers/3
```

- **Instance 26:** `—`

```
POST http://localhost:8081/api/auth/register was exercised in the shared tester workflow; the assigned target URL uses the http scheme.
```

- **Instance 27:** `—`

```
GET http://localhost:8081/?__aespa_transport_probe=1#security using the anonymous session.
```

- **Instance 28:** `—`

```
Request context recorded by the shared tester: bearer-authenticated API request sent to the http://localhost:8081 origin.
```

- **Instance 29:** `—`

```
GET http://localhost:8081/api/accounts/1?transport=cleartext-check; Authorization: supplied bearer token; Cookies: none
```

- **Instance 30:** `—`

```
POST http://localhost:8081/api/payments/process over http:// with JSON payment fields and bearer authorization.
```

- **Instance 31:** `—`

```
GET http://localhost:8081/api/health?transport_probe=1; Authorization: none; Cookies: none
```

- **Instance 32:** `—`

```
Anonymous requests to http://localhost:8081/api/payments/transfer; Authorization: none; Cookies: none. Methods tested: GET, OPTIONS, POST.
```

- **Instance 33:** `—`

```
POST http://localhost:8081/api/transfers/external (successful control, HTTP 201); live probe GET http://localhost:8081/api/transfers/external.
```

- **Instance 34:** `—`

```
POST /api/transfers/check over HTTP with JSON body {"transfer_type":"manual"} and a valid bearer token.
```

- **Instance 35:** `—`

```
GET http://localhost:8081/api/health; follow-up GET https://localhost:8081/api/health.
```

- **Instance 36:** `—`

```
GET http://localhost:8081/api/health?cleartext_probe=1; Authorization: none; Cookies: none.
```

- **Instance 37:** `—`

```
POST http://localhost:8081/api/transfers/check; scheme `http`; Authorization: Bearer login-issued JWT; Cookies: none; body {"transfer_type":"manual"}.
```

- **Instance 38:** `—`

```
GET http://localhost:8081/admin/ via browser replay; final URL http://localhost:8081/admin/#/login.
```

- **Instance 39:** `—`

```
GET http://localhost:8081/api/admin/customers/16 with a valid admin bearer token.
```


## 8. Unauthenticated access to banking account data

- Finding reference: JUQE-001
- Severity: high
- OWASP: A01
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
The unauthenticated root page at http://localhost:8081/ returns a banking dashboard containing total and individual account balances plus full BSB and account numbers.

### Impact
Anyone who can reach the service can view sensitive banking balances and account identifiers without logging in.

### Likelihood
High: the data is returned directly to an anonymous request with no authentication or session credentials.

### Recommendation
Require authentication and authorization before rendering or returning account data. Keep any public landing page separate from authenticated account views and return only minimal public content to unauthenticated users.

### Evidence
```
An anonymous GET to http://localhost:8081/ returned HTTP 200 with no Authorization header or cookies. The response and browser replay exposed 'Total Balance $42,816.50', 'Everyday Account 062-001 · 12345678', '$8,241.50', 'Savings 062-001 · 87654321', and '$34,575.00'.

Specialist evidence:
The anonymous wire probe GET http://localhost:8081/ returned HTTP 200 with Authorization: none and Cookies: none. Its HTML contained the Bank of Ed landing page and the account data rendered in the preserved browser replay: Total Balance $42,816.50; Everyday Account 062-001 · 12345678 with $8,241.50; Savings 062-001 · 87654321 with $34,575.00.

Specialist evidence:
An explicit anonymous HTTP probe returned 200 and served the account data in the response body. The response contained Total Balance $42,816.50, Everyday Account 062-001 · 12345678, $8,241.50, Savings 062-001 · 87654321, and $34,575.00. The same content rendered at http://localhost:8081/#accounts without authentication.
```

### Request Evidence
```
GET http://localhost:8081/ with use_session=anonymous. Wire identity: Authorization: none; Cookies: none.

Specialist request:
GET http://localhost:8081/ -> 200; use_session=anonymous; Authorization: none; Cookies: none.

Specialist request:
GET http://localhost:8081/ with use_session='anonymous'; wire state explicitly had Authorization: none and Cookies: none.
```

### Response Evidence
```
HTTP 200. The response body contains the banking account balances and account identifiers listed above.

Specialist response:
HTTP 200 HTML response for the anonymous request; the preserved page rendered the total balance, BSB/account numbers, and individual balances before sign-in.

Specialist response:
HTTP 200 response body included Total Balance $42,816.50, Everyday Account 062-001 · 12345678, and Savings 062-001 · 87654321.
```

### Validation Note
A credential-free request to the exact affected URL returned HTTP 200 with content matching the protected response baseline.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/
```

## 9. Weak registration password policy issues live session tokens

- Finding reference: JUQE-017
- Severity: high
- OWASP: A07
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/register
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
The unauthenticated registration endpoint accepts the common password `password` and immediately returns a bearer JWT. No meaningful password policy was enforced.

### Impact
Attackers can create accounts with guessable credentials and obtain authenticated sessions, enabling automated abuse and increasing the risk of account compromise.

### Likelihood
High. The endpoint is unauthenticated and accepted the trivial password in a direct request.

### Recommendation
Enforce a strong password policy, reject common and breached passwords, add registration rate limits and abuse controls, and review whether registration should issue a session token immediately.

### Evidence
```
An anonymous POST to `/api/auth/register` with email `admin@example.com`, password `password`, first_name `Admin`, and last_name `User` returned HTTP 201 with `success:true`, `Registration successful`, and a JWT in `data.token`. Retrying the same request returned HTTP 409 `DUPLICATE_ENTRY`, confirming that the first request created the account.

Specialist evidence:
A POST with email deep-weak-probe-20260913@example.invalid, password "1", first_name Probe, and last_name User returned HTTP 201 and "Registration successful". The response included user id 20.

Specialist evidence:
Direct wire evidence from a bounded anonymous probe. Authorization: none. Cookies: none. POST with password="123456" returned HTTP 201 and data.token.

Specialist evidence:
POST http://localhost:8081/api/auth/register with email probe-weak@example.invalid and password 1234567 returned HTTP 201 with "Registration successful". The public HTML for the same flow contains password minlength="8". The response included a new user id 25, confirming the short password was accepted.

Specialist evidence:
The shared tester ledger contains the confirmed claim: weak registration password policy issues live session tokens. It also records successful 201 responses from POST /api/auth/register.
```

### Request Evidence
```
POST http://localhost:8081/api/auth/register; Authorization: none; Cookies: none; JSON password: `password`.

Specialist request:
POST /api/auth/register with JSON {"email":"deep-weak-probe-20260913@example.invalid","password":"1","first_name":"Probe","last_name":"User"}

Specialist request:
POST http://localhost:8081/api/auth/register using use_session='anonymous'; body {"email":"deep-campaign-20260913-01@example.test","password":"123456","first_name":"Deep","last_name":"Campaign"}. Authorization: none. Cookies: none.

Specialist request:
POST /api/auth/register with JSON first_name=Probe, last_name=Weak, email=probe-weak@example.invalid, password=1234567.

Specialist request:
POST http://localhost:8081/api/auth/register succeeded with HTTP 201 in the shared tester workflow.
```

### Response Evidence
```
Initial response: HTTP 201 with `success:true`, `Registration successful`, and `data.token` containing a JWT. Retry response: HTTP 409 with `DUPLICATE_ENTRY`.

Specialist response:
HTTP 201: {"success":true,"data":{"user":{"id":20,...},"token":"..."},"message":"Registration successful"}

Specialist response:
HTTP 201 response contained {"success":true,"data":{"user":{"id":24,...,"password_hash":"e10adc3949ba59abbe56e057f20f883e"},"token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}}.

Specialist response:
HTTP 201; success=true; data.user.id=25; message=Registration successful.

Specialist response:
Confirmed tester claim: weak registration password policy issues live session tokens.
```

### Validation Note
The public registration endpoint is expected to be unauthenticated, but that does not explain accepting the common password. The created account authenticated with password, returned a JWT, and that JWT was accepted by the protected GET /api/profile endpoint; an intentionally wrong password was rejected with WRONG_PASSWORD, so authentication was not ignoring the password. The duplicate response also confirms the original registration persisted the account, leaving no benign explanation for the weak password policy finding.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"email":"admin@example.com","password":"password"}' http://localhost:8081/api/auth/login
```

## 10. JWT signature validation bypass

- Finding reference: JUQE-032
- Severity: high
- OWASP: A01
- Source: specialist agent
- Validation: false_positive
- Affected URL: http://localhost:8081/api/accounts/6
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
JWT signature validation is bypassable on protected endpoints. GET /api/accounts/6 accepts an unsigned JWT using alg=none with subject 21 and an empty signature, and GET /api/profile accepted a token after only its final signature character was changed. The endpoints reached authenticated request paths instead of rejecting the invalid signature.

### Impact
An attacker could forge authentication tokens and impersonate another user on routes that trust the JWT subject, including account and transfer-related API routes.

### Likelihood
High. The endpoint accepted a forged token without requiring a server-issued signature, and exploitation requires no prior authentication.

### Recommendation
Allow only a fixed, expected JWT algorithm and verify the signature before authorization. Also validate the issuer, audience, expiry, and subject claims. Reject alg=none and invalid or unsigned tokens with HTTP 401.

### Evidence
```
Anonymous GET /api/accounts/6 returned HTTP 401 with a missing or invalid Authorization header. A valid signed token returned HTTP 404 Account not found, while an unsigned alg=none token for subject 21 returned the same authenticated-path HTTP 404 response. A token with the original signature and a changed subject also reached the authenticated path. This indicates the server accepted the request without validating a valid server-issued signature.
```

### Request Evidence
```
GET http://localhost:8081/api/accounts/6 with Authorization: Bearer <JWT header alg=none, payload sub=21, empty signature>.
```

### Response Evidence
```
HTTP 404 {"success":false,"error":{"code":"NOT_FOUND","message":"Account not found."}}; anonymous baseline for the same route was HTTP 401 with Missing or invalid Authorization header.
```

### Validation Note
Validation could not reproduce unauthorized access. Alternate users received an access denial, login response, generic application shell, or no protected content signal.

### Additional Instances

- **Instance 2:** `—`

```
GET http://localhost:8081/api/profile with Authorization: Bearer <recorded valid JWT> returned 200. Follow-up used the same header and path, changing only the signature suffix from ...bWU-CYJS9k to ...bWU-CYJS9A.
```


## 11. Authentication responses expose password hashes and session tokens

- Finding reference: JUQE-027
- Severity: medium
- OWASP: A02
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 5.3 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

### Description
The authentication responses expose the user's password_hash together with session tokens. POST /api/auth/login includes password_hash in data.user, and the profile and registration responses also expose it; registration returns a live JWT and the new user's hash. The observed hash is an unsalted MD5 digest.

### Impact
Anyone who can read the response obtains a password verifier that can be attacked offline. The response also contains the user's session token, which could enable authenticated access if it is obtained by an unauthorized party.

### Likelihood
Medium. The data is returned directly by successful authentication and profile requests, so exposure depends on access to those responses.

### Recommendation
Remove password_hash and other credential material from all user serializers and API responses. Store passwords using a modern adaptive password-hashing algorithm such as Argon2id, bcrypt, or scrypt with a unique salt. Protect session tokens from disclosure and return them only where required for authentication.

### Evidence
```
POST /api/auth/login with {"email":"deep-weak-probe-20260913@example.invalid","password":"1"} returned HTTP 200 and data.user.password_hash="c4ca4238a0b923820dcc509a6f75849b" together with a token. The profile response also returned password_hash.

Specialist evidence:
The successful HTTP 200 login response for admin@example.com contained data.user.password_hash=5f4dcc3b5aa765d61d8327deb882cf99.

Specialist evidence:
Direct tool response from HTTP 200 POST http://localhost:8081/api/auth/login included data.user.password_hash alongside the normal profile fields. The earlier HTTP 201 POST /api/auth/register response included the same field.
```

### Request Evidence
```
POST /api/auth/login with JSON {"email":"deep-weak-probe-20260913@example.invalid","password":"1"}

Specialist request:
POST http://localhost:8081/api/auth/login with admin@example.com and password password.

Specialist request:
POST http://localhost:8081/api/auth/login with a disposable test identity; password omitted from the report.
```

### Response Evidence
```
HTTP 200 response data.user contained password_hash and the token; profile GET also returned password_hash.

Specialist response:
HTTP 200 JSON included data.user.password_hash and data.token.

Specialist response:
HTTP 200 JSON success response contained data.user.password_hash with a 32-character hexadecimal value.
```

### Validation Note
Replaying the scanner's exact unauthenticated login request returned HTTP 200 with data.user.password_hash set to c4ca4238a0b923820dcc509a6f75849b and a session token, so this is live response data rather than a static log or export. The supplied admin session also returned a real authenticated profile containing password_hash, showing the exposure is part of the response schema and not limited to the disposable probe account. The profile route guesses that returned 404 and the expired alternate sessions do not provide a benign explanation for the confirmed login and admin-profile disclosures.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"email":"deep-weak-probe-20260913@example.invalid","password":"1"}' http://localhost:8081/api/auth/login
```

### Additional Instances

- **Instance 2:** `—`

```
POST http://localhost:8081/api/auth/register; Authorization: none; Cookies: none; JSON password: `password`.

Specialist request:
POST /api/auth/register JSON included password "1".

Specialist request:
POST http://localhost:8081/api/auth/register using use_session='anonymous' with Content-Type: application/json and body {"email":"deep-campaign-20260913-01@example.test","password":"123456","first_name":"Deep","last_name":"Campaign"}. Authorization: none. Cookies: none.

Specialist request:
POST http://localhost:8081/api/auth/register with a valid registration body produced HTTP 201 in the shared tester evidence.

Specialist request:
POST http://localhost:8081/api/auth/register with use_session='anonymous'; wire context: Authorization: none; Cookies: none. Body contained the required fields and a fresh test email.

Specialist request:
POST /api/auth/register with the disposable registration JSON; Authorization: none; Cookies: none; session: anonymous.

Specialist request:
POST /api/auth/register with a fresh synthetic registration: first_name=Replay, last_name=Probe, email=replay-555-cmp-20260913@example.invalid, username=replay555cmp20260913, password=SafeReplay!2026x.
```


## 12. Customer updates accept stale If-Match values

- Finding reference: JUQE-058
- Severity: medium
- OWASP: A04
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/customers/{id}
- CVSS: 4.3 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:N)

### Description
PUT /api/admin/customers/9 and PUT /api/admin/customers/8 accept deliberately stale If-Match values instead of rejecting updates whose precondition does not match the current record version.

### Impact
A valid admin session can replay an earlier customer edit after a newer change and silently overwrite updated customer fields. Invalid or missing Authorization was rejected, so this is a concurrency and workflow issue rather than an authorization bypass.

### Likelihood
Medium during concurrent administration or when browser workflows are retried with stale form data.

### Recommendation
Persist a version or ETag for each customer record. Require If-Match to equal the current value and return HTTP 409 or 412 on mismatch. Tie the update response to the version that was checked.

### Evidence
```
A valid admin request to PUT /api/admin/customers/9 with If-Match: "definitely-stale" and the existing values for customer 9 returned HTTP 200 with success:true and "Customer updated successfully". The workflow also recorded a replay with If-Match: "stale-0" and an exact replay of the valid PUT, both returning HTTP 200. Requests with an invalid token or missing Authorization returned 401.
```

### Request Evidence
```
PUT http://localhost:8081/api/admin/customers/9; If-Match: "definitely-stale"; JSON body contained the existing values for customer 9: Emma O'Brien, emma.obrien@example.com, 0499 012 345, 42 Peel St, Newtown NSW 2042.
```

### Response Evidence
```
HTTP 200: {"success":true,"data":{"id":9,...},"message":"Customer updated successfully"}. Saved authorization comparisons returned 401 for an invalid token and for a missing Authorization header.
```

### Validation Note
I first tested the benign explanation that this was only an unsupported conditional header: GET and HEAD exposed no ETag or version, and a no-op update with a stale value still returned 200. I then committed a reversible phone change and replayed the prior customer representation with If-Match: stale-0; the stale request returned 200 and overwrote the newer phone value, proving a lost-update path rather than a harmless no-op. The decisive proof requires PUT, so I am omitting poc_request because the verifier only accepts GET, HEAD, or POST.

### Additional Instances

- **Instance 2:** `—`

```
PUT /api/admin/customers/8 with Authorization: Bearer <fresh admin JWT>, Content-Type: application/json, and If-Match: "stale-0"; body contained the current customer 8 values.
```


## 13. Login endpoint lacks visible throttling after repeated failures

- Finding reference: JUQE-023
- Severity: medium
- OWASP: A07
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
POST /api/auth/login continued returning the normal authentication failure after six consecutive attempts with the same invalid credentials. No lockout, delay, challenge, or rate-limit response was observed.

### Impact
Attackers may automate password-guessing and credential-stuffing attempts, increasing the risk of account takeover.

### Likelihood
Medium to high when the endpoint is reachable by untrusted clients.

### Recommendation
Apply server-side throttling by account and source. Return HTTP 429 after a small failure budget, add progressive delays or a challenge, and monitor repeated failures. Do not rely only on IP-based limits.

### Evidence
```
A bounded login-rate-limit probe sent six repeated POST requests with the same invalid credentials. Each response remained HTTP 401 with USER_NOT_FOUND, and no 429 response, retry delay, challenge, or lockout signal was returned.

Specialist evidence:
The login-rate-limit-admin repeat sequence was issued to POST http://localhost:8081/api/auth/login with admin@example.com and credential-stuffing-invalid. The observed response remained HTTP 401 with code WRONG_PASSWORD.

Specialist evidence:
The bounded repeat probe used repeat_sequence=login-rate-limit-followup with a maximum of six POST requests. The direct tool result remained HTTP 401 with USER_NOT_FOUND and did not show a 429, lockout, or retry response.
```

### Request Evidence
```
POST http://localhost:8081/api/auth/login
{"email":"probe.invalid@example.test","password":"Wrong-Only-For-Bounded-Probe-9f3c"}
repeat_sequence=login-rate-limit, repeat_limit=6

Specialist request:
POST http://localhost:8081/api/auth/login with a synthetic invalid email and password, bounded by repeat_limit 6.

Specialist request:
Bounded repeat_sequence=login-rate-limit-admin, repeat_limit=6, POST /api/auth/login for the confirmed admin account.

Specialist request:
POST http://localhost:8081/api/auth/login with email rate-followup@example.com and an incorrect password, repeated at most six times.
```

### Response Evidence
```
HTTP 401
{"success":false,"error":{"code":"USER_NOT_FOUND","message":"No account found with this email address."}}

Specialist response:
HTTP 401 USER_NOT_FOUND was returned and the response did not indicate throttling or temporary blocking.

Specialist response:
HTTP 401 {"success":false,"error":{"code":"WRONG_PASSWORD","message":"Incorrect password."}}; no rate-limit or lockout response was observed.

Specialist response:
HTTP 401 response: {"success":false,"error":{"code":"USER_NOT_FOUND","message":"No account found with this email address."}}
```

### Validation Note
The initial body-shape concern was ruled out: the endpoint requires `email`, and validly shaped invalid requests returned the expected authentication errors. I then repeated six anonymous, cookie-free failures for the known account `amelia.chen@example.com` using an invalid password, followed by additional identical attempts; every response stayed HTTP 401 with `WRONG_PASSWORD`, no `Retry-After` or rate-limit headers appeared, and response times remained about 70-80 ms. This rules out the scanner merely testing a nonexistent account or missing a delay-only control.

## 14. Outdated and unpinned third-party JavaScript on the banking page

- Finding reference: JUQE-067
- Severity: medium
- OWASP: A06
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/banking/
- CVSS: 4.6 (CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The banking page at /banking/ and /banking/index.html loads jQuery 3.3.1, Moment.js 2.29.1, QRCode.js 1.5.3, and Tailwind CSS from public CDNs. Tailwind is loaded from an unversioned URL, and /banking/js/utils.js identifies bundled Moment usage.

### Impact
Users loading the banking page execute dependencies that are old or can change outside a controlled application release. No exploit of the loaded libraries was demonstrated.

### Likelihood
Low. Exploitation would require a weakness in a loaded dependency or an unsafe change to unpinned CDN content, and the captured evidence does not demonstrate either condition.

### Recommendation
Upgrade jQuery and Moment.js to supported releases or replace them where practical. Review the QRCode.js version. Pin every third-party asset to a reviewed version, and prefer self-hosting or a controlled asset pipeline with integrity checks instead of the unversioned Tailwind CDN script.

### Evidence
```
A bounded GET of /banking/ with Range: bytes=-3000 returned imports for jquery@3.3.1, moment@2.29.1, qrcode@1.5.3, and https://cdn.tailwindcss.com. A GET of /banking/js/utils.js returned the comment "Formatted with moment.js (bundled moment 2.29.1)". The banking HTML also contained a Tailwind configuration block while loading the unversioned Tailwind script.
```

### Request Evidence
```
GET /banking/ with Range: bytes=-3000; GET /banking/js/utils.js
```

### Response Evidence
```
HTTP 206 response exposed the third-party script URLs and versions; HTTP 200 response from /banking/js/utils.js explicitly names bundled Moment 2.29.1.
```

### Validation Note
The reported strings are live executable imports, not stale or commented text: the page loads jquery@3.3.1, moment@2.29.1, qrcode@1.5.3, and the unversioned cdn.tailwindcss.com script. utils.js also calls moment() for date formatting, and the page contains an active Tailwind configuration block. I checked the npm registry metadata as a disproof attempt; Moment's latest is 2.30.1 and jQuery's latest is 4.0.0, so the pinned versions are genuinely old. The anonymous 200 response and absence of any runtime gating do not provide a benign explanation for the dependency finding.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/banking/
```

### Additional Instances

- **Instance 2:** `—`

```
GET http://localhost:8081/banking/index.html?asset-review=1; GET http://localhost:8081/banking/js/utils.js?asset-review=1; GET http://localhost:8081/banking/js/pages/profile.js?asset-review=2
```


## 15. Address-book nickname can inject JavaScript into the delete handler

- Finding reference: JUQE-040
- Severity: medium
- OWASP: A03
- Source: specialist agent
- Validation: unconfirmed
- Affected URL: http://localhost:8081/banking/#/addressbook
- CVSS: 6 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The address-book page builds delete buttons with list.innerHTML and inserts the nickname into a single-quoted inline onclick handler. escapeHtml converts apostrophes to &#39;, but the HTML parser decodes that entity before compiling the handler, so the nickname can terminate the string and add JavaScript.

### Impact
A user who can create or influence a nickname could execute script in the banking origin when another user opens the address book or activates the affected button. The script could access page data and tokens available to that origin.

### Likelihood
Medium. Exploitation depends on controlling an address-book nickname, but the vulnerable client-side construction is directly visible in the served source.

### Recommendation
Remove the inline onclick handler and attach the delete action with addEventListener. Insert the nickname as text or a DOM property. If a value must be placed in an attribute, use encoding appropriate to that context and do not rely on HTML entity encoding for JavaScript strings.

### Evidence
```
GET requests for addressbook.js and utils.js returned source showing list.innerHTML, insertion of U.escapeHtml(entry.nickname) into a single-quoted onclick handler, escapeHtml mapping apostrophes to &#39;, and a pre-parser .replace(/'/g, "\\'") call. The encoded apostrophe is therefore decoded when the onclick attribute is parsed, allowing the nickname to break out of the JavaScript string. No payload was created or executed because authenticated browser state was unavailable.
```

### Request Evidence
```
GET /banking/js/pages/addressbook.js?v=20260213-2 and GET /banking/js/utils.js?v=20260213-2.
```

### Response Evidence
```
HTTP 200 responses contained the inline handler construction, `list.innerHTML = html`, the `&#39;` escape map, and the pre-parser `.replace(/'/g, "\\'")` logic.
```

### Validation Note
The JavaScript source shows a potentially unsafe construction: an escaped nickname is placed into a single-quoted inline onclick handler, and the source-level parser-decoding concern is plausible. However, the collected runtime evidence contains only baseline address-book data for the valid `admin` session; no attacker-controlled nickname was created or updated, and no browser execution of a payload was observed. The material proof gap is whether a stored nickname can reach this renderer and execute JavaScript in the target browser context.

## 16. Apache server version disclosed in error responses

- Finding reference: JUQE-045
- Severity: low
- OWASP: A05
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/admin/js/
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
Unauthenticated error responses disclose the Apache server banner, including Apache/2.4.68 (Unix), version and operating-system details, hostname, and listening port. The disclosure was observed at /admin/js/, /openapi.json, /api/accounts/%00, /api/address-book/%00, and the missing /robots.txt resource.

### Impact
This gives unauthenticated users precise server software and version information for reconnaissance and targeted research.

### Likelihood
Low. The disclosure alone does not provide direct access or exploitation, and no related server vulnerability was demonstrated.

### Recommendation
Configure Apache or the front server to remove or generalize the Server header and server signatures in generated error pages.

### Evidence
```
Without authorization or cookies, GET /admin/js/ returned HTTP 403 with an HTML error page containing "Apache/2.4.68 (Unix) Server at localhost Port 8081". GET /openapi.json returned a 404 page with the same banner.
```

### Request Evidence
```
GET /admin/js/ HTTP/1.1
Host: localhost:8081
Authorization: none
Cookies: none
```

### Response Evidence
```
HTTP 403
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<address>Apache/2.4.68 (Unix) Server at localhost Port 8081</address>
```

### Validation Note
I re-requested both reported endpoints anonymously and also checked a separate nonexistent path. All three responses were Apache-generated error pages that exposed the exact version in both the Server header and HTML body, so the result is repeatable and does not depend on authentication or a route-specific application message. The broader error-page behavior does not provide a benign explanation; it confirms global Apache version disclosure.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/admin/js/
```

### Additional Instances

- **Instance 2:** `—`

```
GET /api/accounts/%00
Authorization: none
Cookies: none

Specialist request:
GET http://localhost:8081/api/accounts/%00
```

- **Instance 3:** `—`

```
GET http://localhost:8081/api/address-book/%00
```

- **Instance 4:** `—`

```
GET http://localhost:8081/robots.txt; Authorization: none; Cookies: none
```


## 17. Authenticated transfer check exposes stack traces and server paths

- Finding reference: JUQE-078
- Severity: low
- OWASP: A05
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transfers/check
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:N/A:N)

### Description
The authenticated `/api/transfers/check` endpoint returns a detailed HTTP 500 error when an `address_book` request omits the required `address_book_id`. The response exposes exception text, PHP source paths, class and controller names, and a full stack trace.

### Impact
An authenticated user can learn server filesystem paths and backend control flow from a malformed request. This information may assist later attacks.

### Likelihood
high

### Recommendation
Validate that `address_book_id` is present and valid before invoking the address-book lookup or model. Return a controlled 4xx response for missing or unknown payees, and omit file paths, line numbers, class names, and stack traces from API responses.

### Evidence
```
With a valid login-issued bearer token, a POST request containing `{"transfer_type":"address_book"}` returned HTTP 500. The JSON error exposed `AddressBookEntry::findByIdAndUser(): Argument #1 ($id) must be of type int, null given`, `/var/www/html/src/Models/AddressBookEntry.php:18`, `/var/www/html/src/Services/TransferService.php:27`, controller and router names, and a full trace.
```

### Request Evidence
```
POST http://localhost:8081/api/transfers/check; Authorization: Bearer login-issued token; Cookies: none; Content-Type: application/json; body {"transfer_type":"address_book"}.
```

### Response Evidence
```
HTTP 500 with error.details.file, error.details.trace, internal PHP source paths, and implementation-level exception text.
```

### Validation Note
Several listed sessions returned 401 before reaching the endpoint, so those probes were not evidence either way. The listed `admin` session authenticated and the exact malformed request returned HTTP 500 with the PHP exception, source paths, controller and router names, and a full stack trace. This is direct confirmation of verbose authenticated error disclosure; no benign formatting or proxy explanation accounts for the live response.

## 18. Credentialed CORS reflects arbitrary origins

- Finding reference: JUQE-070
- Severity: low
- OWASP: A05
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The protected endpoints /api/profile and /api/fx/rates reflect arbitrary Origin values and return Access-Control-Allow-Credentials: true. This permits credentialed cross-origin requests from attacker-controlled origins.

### Impact
If an authenticated session is accepted, an attacker-controlled website may be able to read profile data cross-origin. No authenticated data read was demonstrated in the captured evidence.

### Likelihood
The behavior reproduced with an untrusted origin on a protected route, although the observed request used an anonymous session and returned 401.

### Recommendation
Allow only explicitly trusted origins. Return Access-Control-Allow-Origin only for allowlisted origins, and enable credentials only where authenticated cross-origin access is required.

### Evidence
```
A GET request to http://localhost:8081/api/profile with Origin: https://attacker.example returned HTTP 401 with Access-Control-Allow-Origin: https://attacker.example and Access-Control-Allow-Credentials: true. The same route also reflected Origin: http://localhost:8081, confirming arbitrary origin reflection rather than a fixed allowlist.
```

### Request Evidence
```
GET http://localhost:8081/api/profile with Origin: https://attacker.example, using an anonymous session.
```

### Response Evidence
```
HTTP 401 with Access-Control-Allow-Origin: https://attacker.example and Access-Control-Allow-Credentials: true.
```

### Validation Note
The unauthenticated evidence did not by itself prove impact, so I tested the protected branch with the supplied sessions and found a valid admin session. With that session, GET /api/profile returned HTTP 200 and meaningful profile data including password_hash, while reflecting https://attacker.example in Access-Control-Allow-Origin and returning Access-Control-Allow-Credentials: true. The 401 responses from other sessions therefore do not provide a benign explanation for the authenticated response.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -H 'Origin: https://attacker.example' http://localhost:8081/api/profile -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the supplied admin test user, then copy its Authorization bearer header from the profile request in the browser DevTools Network tab and provide it to the verifier.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

### Additional Instances

- **Instance 2:** `—`

```
GET http://localhost:8081/api/fx/rates with Origin: https://third-party.example, using an anonymous session.
```


## 19. Login endpoint enables email account enumeration

- Finding reference: JUQE-031
- Severity: low
- OWASP: A07
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 3.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The unauthenticated login endpoint returns different error codes and messages for an unknown email address and a known email address with an incorrect password.

### Impact
An attacker can identify registered email addresses and use that information to target password attacks or phishing.

### Likelihood
High. The distinction is remotely observable without authentication using a single login request for each candidate address.

### Recommendation
Return the same HTTP status, error code, message, and, where practical, similar response timing for unknown users and incorrect passwords. Avoid revealing whether the submitted email address is registered.

### Evidence
```
Two unauthenticated requests produced distinguishable 401 responses. The unknown address audit-probe@example.invalid returned USER_NOT_FOUND with "No account found with this email address.", while the known address admin@example.com with an incorrect password returned WRONG_PASSWORD with "Incorrect password."

Specialist evidence:
Both failed requests were sent with Authorization: none and Cookies: none. The nonexistent email returned HTTP 401 code USER_NOT_FOUND and message "No account found with this email address." The known test account email with a wrong password returned HTTP 401 code WRONG_PASSWORD and message "Incorrect password.".

Specialist evidence:
Anonymous wire probes explicitly used Authorization: none and Cookies: none. POST with deep-worker-invalid@example.invalid returned HTTP 401 code USER_NOT_FOUND, while POST with admin@example.com and a wrong password returned HTTP 401 code WRONG_PASSWORD.
```

### Request Evidence
```
Authorization: none; Cookies: none. POST /api/auth/login JSON {"email":"audit-probe@example.invalid","password":"definitely-wrong"}; POST /api/auth/login JSON {"email":"admin@example.com","password":"admin"}.

Specialist request:
Authorization: none; Cookies: none. POST /api/auth/login with {"email":"deep-audit-probe@example.invalid","password":"WrongPassword!123"}; then Authorization: none; Cookies: none. POST /api/auth/login with {"email":"deep-weak-probe-20260913@example.invalid","password":"WrongPassword!123"}.

Specialist request:
Authorization: none; Cookies: none. Anonymous POST /api/auth/login with the two bounded synthetic credential cases.
```

### Response Evidence
```
401 {"success":false,"error":{"code":"USER_NOT_FOUND","message":"No account found with this email address."}} versus 401 {"success":false,"error":{"code":"WRONG_PASSWORD","message":"Incorrect password."}}.

Specialist response:
Unknown email: HTTP 401 USER_NOT_FOUND, "No account found with this email address." Known email with wrong password: HTTP 401 WRONG_PASSWORD, "Incorrect password.".

Specialist response:
Unknown email: {"code":"USER_NOT_FOUND"}; known email: {"code":"WRONG_PASSWORD"}.
```

### Validation Note
The login route is correctly unauthenticated by design, but its failures reveal account existence. Anonymous, cookie-free requests with the same invalid password returned USER_NOT_FOUND for audit-probe-2@example.invalid and WRONG_PASSWORD for the known account amelia.chen@example.com; the same distinction also reproduced for admin@example.com. This rules out session carryover and an admin-only special case, so the endpoint supports email account enumeration.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"email":"amelia.chen@example.com","password":"same-invalid-password"}' http://localhost:8081/api/auth/login
```

## 20. Missing browser security headers on banking HTML shell

- Finding reference: JUQE-077
- Severity: low
- OWASP: A05
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/banking/
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The unauthenticated HTML shell at /banking/ is served without common browser security headers, including CSP, HSTS, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy.

### Impact
The page has fewer browser-enforced protections against clickjacking, MIME sniffing, referrer leakage, and the impact of script injection.

### Likelihood
Medium

### Recommendation
Configure HTML responses with a restrictive Content-Security-Policy, Strict-Transport-Security where HTTPS is enforced, X-Content-Type-Options: nosniff, frame-ancestors or X-Frame-Options, and an appropriate Referrer-Policy.

### Evidence
```
An anonymous HEAD request to http://localhost:8081/banking/ returned HTTP 200 without authorization or cookies. Direct header inspection showed only Date, Server, Last-Modified, ETag, Accept-Ranges, Content-Length, Keep-Alive, Connection, and Content-Type. Strict-Transport-Security, Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy were absent.
```

### Request Evidence
```
HEAD http://localhost:8081/banking/; the HTTP probe recorded Authorization: none and Cookies: none.
```

### Response Evidence
```
HTTP 200; Content-Type: text/html; no CSP, X-Frame-Options, X-Content-Type-Options, or Referrer-Policy headers.
```

### Validation Note
A direct anonymous GET to the local Apache origin reproduced the reported 200 response and the same absence of CSP, HSTS, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy. A byte-range fetch of the HTML head showed no meta-tag equivalent, and the response identifies Apache on localhost rather than a CDN-layer response that could be adding protection. HSTS is inapplicable to this HTTP-only origin, but the other reported headers remain absent, so there is no concrete benign explanation for the finding.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/banking/
```

## 21. Verbose authentication errors disclose stack traces and server paths

- Finding reference: JUQE-053
- Severity: low
- OWASP: A05
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/accounts/6
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
Submitting a malformed bearer token without a jti value to GET /api/accounts/6 causes the authentication middleware to return an HTTP 500 response containing a PHP stack trace, absolute filesystem paths, class and method names, and source line numbers.

### Impact
An unauthenticated caller can learn server and middleware implementation details that may assist targeted attacks.

### Likelihood
medium

### Recommendation
Return a generic HTTP 400 or 401 response for invalid tokens. Disable stack traces and internal error details in production responses, while recording diagnostic details in server-side logs.

### Evidence
```
A GET request to /api/accounts/6 with an alg=none bearer token lacking jti returned HTTP 500. The response exposed the error `AuthService::isTokenRevoked(): Argument #1 ($jti) must be of type string, null given`, the paths `/var/www/html/src/Middleware/AuthMiddleware.php` and `/var/www/html/src/Services/AuthService.php`, lines 28 and 77, and the full call chain.
```

### Request Evidence
```
Authorization: supplied malformed alg=none bearer token without jti; Cookies: none; GET /api/accounts/6
```

### Response Evidence
```
HTTP 500 JSON error with AuthService and AuthMiddleware stack trace, absolute paths, and line numbers.
```

### Validation Note
A structurally complete alg=none token with standard identity and time claims, but no jti, reproduced the reported 500 and exposed the PHP exception, absolute paths, line numbers, and call trace. A valid supplied admin session reached the route normally, and adding a string jti changed the result to the normal 404 account response, so this is specific to the missing-jti path rather than a generic malformed-token or nonexistent-account response. The response therefore directly confirms verbose authentication error disclosure.

## 22. No observable rate limiting on transfer checks

- Finding reference: JUQE-080
- Severity: low
- OWASP: A04
- Source: specialist agent
- Validation: false_positive
- Affected URL: http://localhost:8081/api/transfers/check
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:N/A:L)

### Description
The authenticated POST /api/transfers/check endpoint accepted six repeated requests with the same valid manual-transfer check without throttling or changing its response.

### Impact
Repeated checks may consume application resources and support high-volume probing of transfer policy state. The endpoint does not accept an OTP or move funds, limiting the observed impact.

### Likelihood
Medium. The behavior was reproduced with an authenticated user using six bounded requests; no bulk traffic was sent.

### Recommendation
Apply per-user and per-IP throttling to transfer-check requests. Return HTTP 429 with a Retry-After header when limits are exceeded, and monitor bursts of repeated checks.

### Evidence
```
A repeat_sequence named transfer-check-rate-limit sent six authenticated POST requests with body {"transfer_type":"manual"}. Every request returned HTTP 200 with the same result: {requires_totp:true,reason:"manual_entry",totp_configured:false}. No 429 response or Retry-After header was observed.
```

### Request Evidence
```
Six bounded POST requests to http://localhost:8081/api/transfers/check; Authorization: Bearer login-issued JWT; body {"transfer_type":"manual"}.
```

### Response Evidence
```
HTTP 200 with the same successful check result; no rate-limit status or retry guidance.
```

### Validation Note
The endpoint is a stateless, authenticated preflight policy lookup, not the transfer operation. Live checks show it only accepts the documented enum values (own, address_book, manual) and returns a policy result that changes with the selector; the manual check returns no transfer identifier, token, or state transition. Repeating this harmless read-only check six times therefore has a concrete benign explanation: it is intentionally idempotent and does not need a transaction-style rate limit, so identical 200 responses do not demonstrate an insecure business-logic flaw.

## 23. TRACE method enabled on admin accounts route

- Finding reference: JUQE-044
- Severity: low
- OWASP: A05
- Source: specialist agent
- Validation: false_positive
- Affected URL: http://localhost:8081/api/admin/accounts?page=1&per_page=20
- CVSS: 3.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The unauthenticated admin accounts route accepts TRACE requests and reflects the request line and headers in the response body.

### Impact
An attacker may obtain request headers if a client or intermediary sends sensitive values through this TRACE-capable route. The route also exposes an unnecessary diagnostic method.

### Likelihood
Low to medium. Exploitation depends on sensitive headers being sent through a client or proxy that permits TRACE.

### Recommendation
Disable TRACE at the web server and reverse proxy. Restrict the route to only the HTTP methods required by the API.

### Evidence
```
An anonymous TRACE request to the affected URL returned HTTP 200 and reflected the request line 'TRACE /api/admin/accounts?page=1&per_page=20 HTTP/1.1' and the header 'X-Aespa-Probe: admin-route-metadata-proof'. No Authorization header or cookies were sent.
```

### Request Evidence
```
TRACE http://localhost:8081/api/admin/accounts?page=1&per_page=20; Authorization: none; Cookies: none; X-Aespa-Probe: admin-route-metadata-proof.
```

### Response Evidence
```
HTTP 200 with a response body reflecting the TRACE request line and synthetic header.
```

### Validation Note
The response is a generic Apache TRACE echo, not an application response from the admin route: it has `Server: Apache/2.4.68`, `Content-Type: message/http`, and the same 200 echo is returned for a nonexistent unrelated path. The underlying anonymous GET to `/api/admin/accounts` returns 401 with `UNAUTHORIZED` and no account data, and the echo is unchanged when using the listed `admin_test` session except for reflecting its headers. This is a server-wide TRACE configuration issue, not unauthenticated access to the admin accounts route.

## 24. Unauthenticated access to admin SPA shell and assets

- Finding reference: JUQE-041
- Severity: low
- OWASP: A05
- Source: specialist agent
- Validation: false_positive
- Affected URL: http://localhost:8081/admin/
- CVSS: 3.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
Unauthenticated requests to /admin/ and /admin/?route_exposure_check=1 return the administration-panel HTML shell, login form, and client-side system-route assets before login. The administrative login page is publicly reachable over HTTP.

### Impact
An attacker can inspect the admin application structure, route names, and client-side API details. The tested admin APIs returned HTTP 401, so this does not demonstrate access to admin data or an authentication bypass.

### Likelihood
high

### Recommendation
Keep authorization checks on every admin API. If the panel should not be publicly discoverable, protect its static entry point and assets with the same access boundary or a separate access gateway.

### Evidence
```
Without an Authorization header or cookies, GET http://localhost:8081/admin/?route=%2Fsystem returned HTTP 200 with the title 'The Bank of Ed - Admin', administration-panel markup, and a login form. HTTP 200 was also recorded for /admin/js/pages/system.js, /admin/js/app.js, /admin/js/router.js, and /admin/js/api.js. Protected admin API baselines returned HTTP 401.
```

### Request Evidence
```
GET http://localhost:8081/admin/?route=%2Fsystem; Authorization: none; Cookies: none
```

### Response Evidence
```
HTTP 200; administration-panel HTML and login form returned
```

### Validation Note
The 200 response is the intended unauthenticated bootstrap for a client-side admin application: it serves static HTML with a login view and public JavaScript, not an authenticated admin session or administrative data. The public API client explicitly stores a token and sends it as Authorization, and direct anonymous requests to both /api/admin/customers and the exact system resource /api/admin/system/settings returned 401 with "Missing or invalid Authorization header." The system.js asset only calls that protected settings API, so the shell and route assets being downloadable do not bypass the authorization boundary.

### Additional Instances

- **Instance 2:** `—`

```
GET http://localhost:8081/admin/; Authorization: none; Cookies: none.
```

- **Instance 3:** `—`

```
GET http://localhost:8081/admin/?route_exposure_check=1; Authorization: none; Cookies: none.
```

