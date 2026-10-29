import pytest

from app import rules
from app.samples import SAMPLES


def ids(code: str, lang: str) -> list[str]:
    return [f.rule.id for f in rules.find(code, lang)]


def fixed(code: str, lang: str) -> str:
    text, imports = rules.apply_fixes(code, rules.find(code, lang), lang)
    return rules.insert_imports(text, imports, lang)[0]


# (language, code, rule that must fire, or None for "nothing fires")
CASES = [
    ("python", 'DB_PASSWORD = "hunter2-prod"', "hardcoded-secret"),
    ("python", 'password: str = "s3cret!!"', "hardcoded-secret"),
    ("python", 'cfg = {"api_key": "abcd1234"}', "hardcoded-secret"),
    ("javascript", 'const apiKey = "live_8f3k2j5h";', "hardcoded-secret"),
    ("go", 'apiKey := "abcd1234"', "hardcoded-secret"),
    ("php", "$password = 'hunter22';", "hardcoded-secret"),
    ("python", 'password = os.environ["PASSWORD"]', None),
    ("python", 'PASSWORD_FIELD = "password"', None),
    ("python", 'api_key = "<your key here>"', None),
    ("python", '"""Set password = "hunter2" in the config."""', None),
    ("python", '# password = "hunter2"', None),
    ("python", 'if password == "hunter2": pass', None),
    ("other", "# AKIAABCDEFGHIJKLMNOP", "known-secret-format"),
    ("python", 'db.execute(f"SELECT * FROM users WHERE id = {uid}")', "sql-injection"),
    ("python", 'db.execute(f"SELECT {cols} FROM users")', "sql-injection"),
    ("python", 'db.execute("DELETE FROM t WHERE id = %s" % uid)', "sql-injection"),
    ("python", 'db.execute("SELECT * FROM t WHERE id = {}".format(uid))', "sql-injection"),
    ("java", 'q = "SELECT * FROM t WHERE name = \'" + name + "\'";', "sql-injection"),
    ("javascript", "db.query(`UPDATE t SET a = ${a} WHERE id = 1`)", "sql-injection"),
    ("go", 'fmt.Sprintf("SELECT * FROM t WHERE id = %d", id)', "sql-injection"),
    ("php", '$q = "SELECT * FROM t WHERE id = $id";', "sql-injection"),
    ("python", 'db.execute("SELECT * FROM t WHERE id = %s", (uid,))', None),
    ("javascript", 'db.query("SELECT * FROM t WHERE id = $1", [id])', None),
    ("python", 'print("Select an option: " + name)', None),
    ("go", 'exec.Command("sh", "-c", "ping "+host)', "shell-injection"),
    ("javascript", "exec(`convert ${file} out.png`)", "shell-injection"),
    ("javascript", 'execSync("rm -rf " + dir)', "shell-injection"),
    ("javascript", 'execFile("convert", [file, "out.png"])', None),
    ("python", "x = eval(user_input)", "py-eval"),
    ("python", "x = ast.literal_eval(s)", None),
    ("python", 'msg = "never eval(x)"', None),
    ("javascript", "const f = new Function(body);", "js-eval"),
    ("javascript", "re.exec(s)", None),
    ("python", "subprocess.run(cmd, shell=True)", "py-shell-true"),
    ("python", "os.system('ls ' + path)", "py-os-system"),
    ("python", "pickle.loads(blob)", "py-pickle"),
    ("python", "yaml.load(stream)", "py-yaml-load"),
    ("python", "yaml.load(stream, Loader=yaml.SafeLoader)", None),
    ("python", "requests.get(url, verify=False)", "tls-verify-disabled"),
    ("python", "hashlib.md5(password.encode())", "weak-hash"),
    ("javascript", "crypto.createHash('sha1')", "weak-hash"),
    ("python", "token = ''.join(random.choices(chars, k=16))", "insecure-random"),
    ("javascript", "const sessionToken = Math.random().toString(36);", "insecure-random"),
    ("javascript", "const x = Math.random();", None),
    ("python", "app.run(debug=True)", "debug-enabled"),
    ("javascript", "el.innerHTML = name;", "xss-sink"),
    ("javascript", "if (el.innerHTML === '') {}", None),
    ("php", "echo $_GET['q'];", "php-echo-input"),
    ("python", 'URL = "http://api.example.com/v1"', "insecure-http-url"),
    ("javascript", 'ns = "http://www.w3.org/2000/svg"', None),
    ("python", "try:\n    f()\nexcept:\n    pass", "py-bare-except"),
    ("python", "try:\n    f()\nexcept ValueError:\n    pass", "py-except-pass"),
    ("python", "def f(items=[]):\n    pass", "py-mutable-default"),
    ("python", "def f(items: list = None):\n    pass", None),
    ("javascript", "try { f() } catch (e) {}", "empty-catch"),
    ("javascript", "try { f() } catch (e) { /* fine, best effort */ }", None),
    ("javascript", "if (a == b) {}", "js-loose-equality"),
    ("javascript", "if (a === b || c !== d || e == null) {}", None),
    ("java", 'if (role == "admin") {}', "java-string-equality"),
    ("go", '_ = http.ListenAndServe(":8080", nil)', "go-ignored-error"),
    ("php", "mysql_query($q);", "php-mysql"),
    ("python", "if x == None:", "py-none-comparison"),
    ("javascript", "var a = 1;", "js-var"),
    ("typescript", "console.log(x);", "console-log"),
    ("typescript", "const d: any = JSON.parse(s);", "ts-any"),
    ("javascript", "const d: any = 1;", None),  # ts-any is TypeScript only
    ("java", "e.printStackTrace();", "java-print-stack-trace"),
    ("python", "x = 1  # TODO: remove", "todo-comment"),
    ("python", 'x = "TODO"', None),
]


@pytest.mark.parametrize("lang,code,rule", CASES)
def test_rule(lang, code, rule):
    found = ids(code, lang)
    if rule is None:
        assert found == [], found
    else:
        assert rule in found, found


@pytest.mark.parametrize(
    "lang,code,expected",
    [
        ("python", "if x == None:\n", "if x is None:\n"),
        ("python", "if x != None:\n", "if x is not None:\n"),
        (
            "python",
            "try:\n    f()\nexcept:\n    g()\n",
            "try:\n    f()\nexcept Exception:\n    g()\n",
        ),
        ("python", "requests.get(u, verify=False)\n", "requests.get(u, verify=True)\n"),
        ("python", "cfg = yaml.load(s, Loader=yaml.Loader)\n", "cfg = yaml.safe_load(s)\n"),
        ("javascript", "var a = b == c;\n", "let a = b === c;\n"),
        (
            "javascript",
            "https.request({ rejectUnauthorized: false })\n",
            "https.request({ rejectUnauthorized: true })\n",
        ),
        (
            "go",
            "c := tls.Config{InsecureSkipVerify: true}\n",
            "c := tls.Config{InsecureSkipVerify: false}\n",
        ),
        ("java", 'String apiKey = "abcd1234";\n', 'String apiKey = System.getenv("API_KEY");\n'),
        ("php", "$dbPassword = 'hunter22';\n", "$dbPassword = getenv('DB_PASSWORD');\n"),
    ],
)
def test_fixes(lang, code, expected):
    assert fixed(code, lang) == expected


def test_fixes_keep_line_numbers_and_add_imports_last():
    code = '"""Module doc."""\n\nAPI_KEY = "hunter2-prod"\nx = eval(s)\n'
    text, imports = rules.apply_fixes(code, rules.find(code, "python"), "python")
    assert text.count("\n") == code.count("\n")
    assert imports == ["import ast", "import os"]
    assert fixed(code, "python") == (
        '"""Module doc."""\nimport ast\nimport os\n\nAPI_KEY = os.environ["API_KEY"]\nx = ast.literal_eval(s)\n'
    )


def test_shift_maps_lines_both_ways():
    code = '"""Doc."""\nx = eval(s)\ny = 1\n'
    text, imports = rules.apply_fixes(code, rules.find(code, "python"), "python")
    out, shift = rules.insert_imports(text, imports, "python")
    assert out.split("\n")[1] == "import ast" and shift == rules.Shift(at=1, k=1)
    assert [shift.to_new(n) for n in (1, 2, 3)] == [1, 3, 4]
    assert [shift.to_old(n) for n in (1, 2, 3, 4)] == [1, 2, 2, 3]


def test_imports_go_before_existing_imports_and_are_not_duplicated():
    code = "#!/usr/bin/env python\nimport sys\n\napiKey = 'abcd1234'\nx = eval(s)\nimport os\n"
    assert fixed(code, "python") == (
        "#!/usr/bin/env python\nimport ast\nimport sys\n\n"
        'apiKey = os.environ["API_KEY"]\nx = ast.literal_eval(s)\nimport os\n'
    )


def test_patch_shows_the_whole_line():
    code = "def f(x):\n    return x == None\n"
    f = rules.find(code, "python")[0]
    assert f.to_dict(1, code)["patch"] == {
        "before": "    return x == None",
        "after": "    return x is None",
    }


def test_findings_point_at_the_right_line():
    code = "a = 1\n\n\ntry:\n    f()\nexcept:\n    pass\n"
    (f,) = rules.find(code, "python")
    assert (f.line, f.end_line, f.snippet) == (6, 6, "except:")


def test_each_rule_reports_at_most_25():
    code = "var a = 1;\n" * 40
    assert ids(code, "javascript").count("js-var") == rules.MAX_PER_RULE


EXPECTED = {
    "flask-api": {
        "hardcoded-secret",
        "sql-injection",
        "py-none-comparison",
        "py-yaml-load",
        "py-mutable-default",
        "py-eval",
        "py-bare-except",
        "debug-enabled",
    },
    "express-api": {
        "hardcoded-secret",
        "sql-injection",
        "console-log",
        "shell-injection",
        "js-var",
        "js-loose-equality",
        "empty-catch",
    },
    "ts-cart": {"js-loose-equality", "todo-comment", "ts-any"},
    "java-login": {
        "hardcoded-secret",
        "sql-injection",
        "weak-hash",
        "java-string-equality",
        "java-print-stack-trace",
    },
    "go-handler": {"sql-injection", "shell-injection", "tls-verify-disabled", "go-ignored-error"},
}


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s["id"])
def test_samples(sample):
    assert set(ids(sample["code"], sample["language"])) == EXPECTED[sample["id"]]


def test_catalogue():
    cat = rules.catalogue()
    assert len({r["id"] for r in cat}) == len(cat) == len(rules.RULES)
    assert all(r["severity"] in rules.SEVERITIES and r["category"] in rules.CATEGORIES for r in cat)
