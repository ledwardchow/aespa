from __future__ import annotations

import pytest

from aespa.services import sast_workprogram


def _sink_names(line: str) -> set[str]:
    return {
        pattern.name
        for pattern in sast_workprogram._PATTERNS
        if pattern.kind == "sink" and pattern.regex.search(line)
    }


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("eval(userInput);", "Code or template evaluation"),
        ("const f = new Function('a', body);", "Code or template evaluation"),
        ("setTimeout('run(' + x + ')', 10);", "Code or template evaluation"),
        ("return render_template_string(tpl)", "Code or template evaluation"),
        ("exec(code, scope)", "Code or template evaluation"),
        ("$out = shell_exec($cmd);", "Command execution"),
        ("system($_GET['c']);", "Command execution"),
        ("subprocess.run(args, shell=True)", "Command execution"),
        ("os.system(cmd)", "Command execution"),
        ("child_process.exec(cmd)", "Command execution"),
        ("const cp = require('child_process');", "Command execution"),
        ('cmd := exec.Command("sh", "-c", arg)', "Command execution"),
        ("Runtime.getRuntime().exec(cmd);", "Command execution"),
        ("with open(path) as fh:", "Filesystem operation"),
        ("$data = file_get_contents($path);", "Filesystem operation"),
        ("include $page;", "Filesystem operation"),
        ("fs.readFileSync(p)", "Filesystem operation"),
        ("os.remove(target)", "Filesystem operation"),
        ("new FileInputStream(file)", "Filesystem operation"),
        ("res.sendFile(req.query.p)", "Filesystem operation"),
        ("return fetch(BASE + path, opts)", "Outbound request"),
        ("requests.get(url)", "Outbound request"),
        ("$ch = curl_init($url);", "Outbound request"),
        (
            "$content = @file_get_contents($data['url'], false, $ctx);",
            "Outbound request",
        ),
        ("resp, err := http.Get(u)", "Outbound request"),
        ("axios.post(url, body)", "Outbound request"),
        ("return md5($password);", "Cryptographic operation"),
        ("hashlib.md5(data)", "Cryptographic operation"),
        ('Cipher.getInstance("DES/ECB/PKCS5Padding")', "Cryptographic operation"),
        ("crypto.createHash('sha1')", "Cryptographic operation"),
        ("$t = JWT::encode($payload, $secret, 'HS256');", "Cryptographic operation"),
        ("jwt.verify(token, secret)", "Cryptographic operation"),
        ("const id = Math.random().toString(36);", "Cryptographic operation"),
        ("$token = rand(1000, 9999);", "Cryptographic operation"),
        ("password_verify($pw, $hash)", "Cryptographic operation"),
        ("$pdo->exec($schema);", "Database query"),
        ("cursor.execute(sql)", "Database query"),
    ],
)
def test_sink_patterns_match_real_sinks(line, expected):
    assert expected in _sink_names(line)


@pytest.mark.parametrize(
    ("line", "not_expected"),
    [
        ("BankOfEd.ProfilePage = (function () {", "Code or template evaluation"),
        (".finally(function () {", "Code or template evaluation"),
        ("const m = /a(b)/.exec(text);", "Code or template evaluation"),
        ("const m = pattern.exec(text);", "Command execution"),
        ("fontFamily: { sans: ['Inter', 'system-ui'] }", "Command execution"),
        (
            "getSettings: function () { return request('GET', '/system/settings'); },",
            "Command execution",
        ),
        ("$pdo->exec($schema);", "Command execution"),
        ("overlay.classList.remove('hidden');", "Filesystem operation"),
        ("window.open(url, '_blank');", "Filesystem operation"),
        (
            "$data = json_decode(file_get_contents('php://input'), true);",
            "Filesystem operation",
        ),
        ("$user = $stmt->fetch();", "Outbound request"),
        ("return (bool)$stmt->fetch();", "Outbound request"),
        ("$db = Database::getInstance();", "Cryptographic operation"),
        ("form.addEventListener('submit', verifyForm);", "Cryptographic operation"),
        ("const sign = amount < 0 ? '-' : '+';", "Cryptographic operation"),
    ],
)
def test_sink_patterns_ignore_common_look_alikes(line, not_expected):
    assert not_expected not in _sink_names(line)
