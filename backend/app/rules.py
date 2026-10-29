"""Static checks that run before the model: instant, free, and the same every time.

Each rule is a regex matched against one view of the source (see lexer.py), plus an
optional `when` that looks at the match in context and an optional `fix` that returns
replacement text for the matched span. Fixes are deliberately small and local, so they
can be applied without understanding the program; anything bigger is left to the model.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from app.lexer import MASK, Views, scan

SEVERITIES = ("critical", "warning", "info")
CATEGORIES = ("security", "bug", "smell", "performance")
MAX_PER_RULE = 25

PY = frozenset({"python"})
JS = frozenset({"javascript", "typescript"})
TS = frozenset({"typescript"})


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str
    category: str
    pattern: re.Pattern
    explanation: str
    suggestion: str = ""
    languages: frozenset[str] | None = None  # None: every language
    view: str = "code"  # raw · code · comment
    when: Callable[[re.Match, Views], bool] | None = None
    fix: Callable[[re.Match, str, str], str | None] | None = None  # (match, raw span, lang)
    imports: dict[str, str] = field(default_factory=dict)  # what a fix needs, per language


@dataclass
class Finding:
    rule: Rule
    line: int
    end_line: int
    start: int
    end: int
    snippet: str
    replacement: str | None

    def patch(self, code: str) -> dict | None:
        """The affected lines before and after this finding's fix."""
        if self.replacement is None:
            return None
        a = code.rfind("\n", 0, self.start) + 1
        b = code.find("\n", self.end)
        b = len(code) if b == -1 else b
        after = code[a : self.start] + self.replacement + code[self.end : b]
        return {"before": code[a:b], "after": after}

    def to_dict(self, n: int, code: str) -> dict:
        r = self.rule
        return {
            "id": f"r{n}",
            "source": "rule",
            "rule_id": r.id,
            "severity": r.severity,
            "category": r.category,
            "line": self.line,
            "end_line": self.end_line,
            "title": r.title,
            "explanation": r.explanation,
            "suggestion": r.suggestion,
            "snippet": self.snippet,
            "fixable": self.replacement is not None,
            "patch": self.patch(code),
        }


# --- helpers for `when` ----------------------------------------------------------------


def in_code(pos: int, v: Views) -> bool:
    """True if the character at pos is real code: not inside a string or a comment."""
    return v.code[pos] != MASK and v.comment[pos] == " "


def starts_in_code(m: re.Match, v: Views) -> bool:
    return in_code(m.start(), v)


SQL_SECOND_KEYWORD = re.compile(r"(?i)\b(from|into|set|where|values)\b")


def _sql_when(m: re.Match, v: Views) -> bool:
    # "Select an option: " + name isn't SQL; a second keyword makes it much more likely
    return starts_in_code(m, v) and bool(SQL_SECOND_KEYWORD.search(m.group(0)))


PLACEHOLDER = re.compile(
    r"(?i)^(x+|\*+|\.+|<.*>|\$\{.*\}|\{\{.*\}\}|%\(?\w*\)?s|your[-_ ].*|changeme|change[-_]me"
    r"|placeholder|redacted|dummy|example.*|none|null|undefined)$"
)
# Names that describe a secret without holding one: password_field, API_KEY_HEADER, ...
METADATA_NAME = re.compile(
    r"(?i)(field|header|name|param|label|url|uri|path|file|env|var|prompt|pattern|regex"
    r"|type|length|len|min|max|policy|hint|id)$"
)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _secret_when(m: re.Match, v: Views) -> bool:
    name, value = m.group("name"), m.group("value")
    if v.comment[m.start("name")] != " ":
        return False  # in a comment
    if v.code[m.start("q")] == MASK:
        return False  # the whole thing sits inside a bigger string, e.g. a docstring
    if PLACEHOLDER.match(value) or METADATA_NAME.search(name):
        return False
    n, val = _norm(name), _norm(value)
    return not (val in n or n in val)


def _env_name(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name.lstrip("$")).upper()


def _secret_fix(m: re.Match, span: str, lang: str) -> str | None:
    var = _env_name(m.group("name"))
    expr = {
        "python": f'os.environ["{var}"]',
        "javascript": f"process.env.{var}",
        "typescript": f"process.env.{var}",
        "java": f'System.getenv("{var}")',
        "php": f"getenv('{var}')",
    }.get(lang)
    if not expr:
        return None
    cut = m.start("q") - m.start()
    return span[:cut] + expr


def _yaml_fix(m: re.Match, span: str, lang: str) -> str | None:
    args = re.sub(r",\s*Loader\s*=\s*[\w.]+", "", m.group("args")).strip()
    if not args or "," in args:
        return None
    return f"yaml.safe_load({args})"


SECRET_NAME = (
    r"\w*(?:password|passwd|pwd|secret|api_?key|apikey|access_?key|private_?key"
    r"|auth_?token|access_?token|client_?secret)\w*"
)

RULES: list[Rule] = [
    # --- secrets ------------------------------------------------------------------------
    Rule(
        "hardcoded-secret",
        "Hardcoded secret",
        "critical",
        "security",
        re.compile(
            rf"(?i)(?<![\w$])\$?(?P<name>{SECRET_NAME})[\"']?\s*(?::\s*[\w\[\]|. ]+?\s*)?"
            r"(?::=|=>|=(?!=)|:)\s*(?P<q>[\"'`])(?P<value>[^\"'`\\\n]{4,})(?P=q)"
        ),
        "A password, key or token is written into the source. Anyone who can read the "
        "code, its history or a build artifact has it, and rotating it means a code change.",
        "Read it from an environment variable or a secret manager.",
        view="raw",
        when=_secret_when,
        fix=_secret_fix,
        imports={"python": "import os"},
    ),
    Rule(
        "known-secret-format",
        "Credential in source",
        "critical",
        "security",
        re.compile(
            r"AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,}"
            r"|xox[abprs]-[A-Za-z0-9-]{10,}|sk_live_[A-Za-z0-9]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}"
            r"|gsk_[A-Za-z0-9]{40,}|AIza[0-9A-Za-z_-]{35}"
            r"|-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
        ),
        "This matches the format of a real credential (AWS, GitHub, Slack, Stripe, OpenAI, "
        "Groq or Google key, or a private key). Even in a comment, it's exposed to everyone "
        "with the code.",
        "Revoke it with the provider now, then load the new one from the environment.",
        view="raw",
    ),
    # --- injection ----------------------------------------------------------------------
    Rule(
        "sql-injection",
        "SQL built from strings",
        "critical",
        "security",
        re.compile(
            # Each branch takes the whole string literal, so the second-keyword check sees it
            r"\b[fF](?P<q1>[\"'])\s*(?i:select|insert|update|delete)\b"
            r"(?=(?:(?!(?P=q1)).)*\{)(?:(?!(?P=q1)).)*"
            r"|(?P<q2>[\"'])\s*(?i:select|insert|update|delete)\b(?:(?!(?P=q2)).)*(?P=q2)"
            r"\s*(?:\+|%\s*[\w(]|\.format\()"
            r"|`\s*(?i:select|insert|update|delete)\b(?=[^`]*\$\{)[^`]*"
            r"|\"\s*(?i:select|insert|update|delete)\b(?=[^\"\n]*\$[A-Za-z_{])[^\"\n]*"
            r"|\b(?:fmt\.Sprintf|String\.format)\(\s*\"\s*(?i:select|insert|update|delete)\b"
            r"(?=[^\"\n]*%[svdq])[^\"\n]*"
        ),
        "Values are pasted into the SQL text. If any of them comes from a user, they can "
        "change the query: read other rows, bypass a login or drop a table.",
        "Use query parameters or a prepared statement, e.g. "
        'cursor.execute("... WHERE id = %s", (user_id,)).',
        view="raw",
        when=_sql_when,
    ),
    Rule(
        "shell-injection",
        "Shell command built from a string",
        "warning",
        "security",
        re.compile(
            r"exec\.Command\(\s*\"(?:/bin/)?(?:sh|bash)\"\s*,\s*\"-c\""
            r"|\bexec(?:Sync)?\s*\(\s*(?:`[^`]*\$\{|[\"'][^\"'\n]*[\"']\s*\+)"
        ),
        "The command goes through a shell with values mixed in, so a value containing ; or "
        "$(...) runs extra commands.",
        "Run the program directly with an argument list (execFile / spawn, exec.Command with "
        "separate args).",
        languages=frozenset({"go", "javascript", "typescript"}),
        view="raw",
        when=starts_in_code,
    ),
    Rule(
        "py-eval",
        "eval() / exec() runs arbitrary code",
        "critical",
        "security",
        re.compile(r"(?<![\w.])(?P<fn>eval|exec)\s*\("),
        "Whatever string reaches this call is executed as Python, with the program's full "
        "permissions.",
        "To parse a literal (a number, list or dict), use ast.literal_eval; for JSON, json.loads.",
        languages=PY,
        fix=lambda m, span, lang: "ast.literal_eval(" if m.group("fn") == "eval" else None,
        imports={"python": "import ast"},
    ),
    Rule(
        "js-eval",
        "eval() runs arbitrary code",
        "critical",
        "security",
        re.compile(r"(?<![\w.$])eval\s*\(|\bnew\s+Function\s*\("),
        "The string is executed as code. If any part of it comes from a user or a "
        "response, that's code injection.",
        "To parse data use JSON.parse; otherwise restructure so no code is built from strings.",
        languages=frozenset({"javascript", "typescript", "php"}),
    ),
    Rule(
        "py-shell-true",
        "subprocess with shell=True",
        "warning",
        "security",
        re.compile(r"\bshell\s*=\s*True\b"),
        "The command runs through /bin/sh, so quotes, ; and $(...) in any value are "
        "interpreted by the shell.",
        "Pass the command as a list, e.g. subprocess.run(['ls', path]), without shell=True.",
        languages=PY,
    ),
    Rule(
        "py-os-system",
        "os.system / os.popen",
        "warning",
        "security",
        re.compile(r"\bos\.(?:system|popen)\s*\("),
        "Runs the string through a shell and gives you no error handling beyond an exit code.",
        "Use subprocess.run([...], check=True) with an argument list.",
        languages=PY,
    ),
    Rule(
        "py-pickle",
        "Unpickling data",
        "warning",
        "security",
        re.compile(r"\b(?:pickle|cPickle|dill)\.loads?\s*\("),
        "Loading a pickle can run arbitrary code. That's fine for files you wrote yourself, "
        "never for uploads, requests or anything from the network.",
        "Use JSON (or another data-only format) for untrusted input.",
        languages=PY,
    ),
    Rule(
        "py-yaml-load",
        "yaml.load can build arbitrary objects",
        "critical",
        "security",
        re.compile(r"\byaml\.load\s*\((?P<args>[^()\n]*)\)"),
        "With the default or full loader, a YAML document can construct Python objects and "
        "run code.",
        "Use yaml.safe_load.",
        languages=PY,
        when=lambda m, v: "SafeLoader" not in m.group("args"),
        fix=_yaml_fix,
    ),
    Rule(
        "tls-verify-disabled",
        "TLS certificate check turned off",
        "warning",
        "security",
        re.compile(
            r"\bverify\s*=\s*False\b|\brejectUnauthorized\s*:\s*false\b"
            r"|\bInsecureSkipVerify\s*:\s*true\b"
        ),
        "Without certificate checks anyone on the network path can impersonate the server "
        "and read or change the traffic.",
        "Leave verification on; for a private CA, point the client at its certificate.",
        languages=frozenset({"python", "javascript", "typescript", "go"}),
        fix=lambda m, span, lang: re.sub(
            r"\b(False|false|true)\b",
            lambda b: {"False": "True", "false": "true", "true": "false"}[b.group()],
            span,
        ),
    ),
    Rule(
        "weak-hash",
        "MD5 / SHA-1",
        "warning",
        "security",
        re.compile(
            r"\bhashlib\.(?:md5|sha1)\s*\(|\bcreateHash\(\s*['\"](?:md5|sha1)['\"]"
            r"|MessageDigest\.getInstance\(\s*\"(?:MD5|SHA-?1)\""
            r"|\b(?:md5|sha1)\.(?:New|Sum)\(|(?<![\w.>$])(?:md5|sha1)\s*\("
        ),
        "Both are broken for anything security-related: collisions are practical and "
        "password hashes made with them are cracked quickly. Fine for non-security checksums.",
        "For passwords use bcrypt or argon2; for signatures and integrity use SHA-256.",
        view="raw",
        when=starts_in_code,
    ),
    Rule(
        "insecure-random",
        "Predictable random value for a secret",
        "warning",
        "security",
        re.compile(
            r"(?i)^[^\n]*\b\w*(?:token|password|secret|otp|nonce|salt)\w*\b[^\n]*"
            r"(?:\brandom\.(?:random|randint|randrange|choice|choices|getrandbits)\s*\("
            r"|\bMath\.random\s*\()",
            re.M,
        ),
        "random and Math.random are not cryptographically secure; their output can be "
        "predicted from earlier values.",
        "Use the secrets module (secrets.token_urlsafe) or crypto.randomUUID / "
        "crypto.getRandomValues.",
        languages=frozenset({"python", "javascript", "typescript"}),
    ),
    Rule(
        "debug-enabled",
        "Debug mode on",
        "warning",
        "security",
        re.compile(r"\bdebug\s*=\s*True\b|^DEBUG\s*=\s*True\b", re.M),
        "Debug mode shows stack traces and, in Flask and Django, can expose an interactive "
        "console or settings to anyone who triggers an error.",
        "Read it from configuration and keep it off in production.",
        languages=PY,
        fix=lambda m, span, lang: span.replace("True", "False"),
    ),
    Rule(
        "xss-sink",
        "HTML written from a string",
        "warning",
        "security",
        re.compile(
            r"\.(?:innerHTML|outerHTML)\s*=(?!=)|\binsertAdjacentHTML\s*\("
            r"|\bdocument\.write(?:ln)?\s*\(|\bdangerouslySetInnerHTML\b"
        ),
        "If any part of the string comes from a user or an API, it can inject script into "
        "the page (XSS).",
        "Use textContent, or sanitise with a library such as DOMPurify first.",
        languages=JS,
    ),
    Rule(
        "php-echo-input",
        "Request input echoed into the page",
        "critical",
        "security",
        re.compile(r"\b(?:echo|print)\b[^;\n]*\$_(?:GET|POST|REQUEST|COOKIE)\b"),
        "Printing request data without escaping lets anyone put script in a link (XSS).",
        "Escape it: echo htmlspecialchars($value, ENT_QUOTES, 'UTF-8').",
        languages=frozenset({"php"}),
        view="raw",
        when=starts_in_code,
    ),
    Rule(
        "insecure-http-url",
        "Plain http:// URL",
        "info",
        "security",
        re.compile(
            r"[\"'`]http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|www\.w3\.org|schemas\.)"
            r"[^\s\"'`]+"
        ),
        "Traffic to this URL isn't encrypted, so it can be read or changed in transit.",
        "Use https:// if the server supports it.",
        view="raw",
        when=starts_in_code,
    ),
    # --- bugs ---------------------------------------------------------------------------
    Rule(
        "py-bare-except",
        "Bare except",
        "warning",
        "bug",
        re.compile(r"^[ \t]*except[ \t]*:", re.M),
        "Catches everything, including KeyboardInterrupt and SystemExit, and hides real "
        "bugs behind whatever the handler does.",
        "Catch the exceptions you expect, or at least `except Exception:`.",
        languages=PY,
        fix=lambda m, span, lang: re.sub(r"except[ \t]*:", "except Exception:", span),
    ),
    Rule(
        "py-except-pass",
        "Exception silently ignored",
        "warning",
        "bug",
        re.compile(r"^[ \t]*except\b[ \t]+[^\n:]*:[ \t]*\n[ \t]*pass\b", re.M),
        "The error disappears without a trace, so failures show up later as wrong data.",
        "Log it, handle it, or let it propagate.",
        languages=PY,
    ),
    Rule(
        "py-mutable-default",
        "Mutable default argument",
        "warning",
        "bug",
        re.compile(
            r"\bdef\s+\w+\s*\([^)]*?\w+\s*(?::\s*[^=)]+)?=\s*(?:\[\]|\{\}|list\(\)|dict\(\)|set\(\))"
        ),
        "The default is created once, when the function is defined, and shared by every "
        "call. Changes made in one call leak into the next.",
        "Default to None and create the list or dict inside the function.",
        languages=PY,
    ),
    Rule(
        "empty-catch",
        "Empty catch block",
        "warning",
        "bug",
        re.compile(r"\bcatch\s*(?:\([^)]*\))?\s*\{\s*\}"),
        "The error is swallowed, so failures surface later somewhere unrelated.",
        "Log or handle the error; if ignoring it is intended, say why in a comment.",
        languages=frozenset({"javascript", "typescript", "java", "php"}),
        # A comment inside the braces means someone decided to ignore it
        when=lambda m, v: not v.comment[m.start() : m.end()].strip(),
    ),
    Rule(
        "js-loose-equality",
        "== instead of ===",
        "info",
        "bug",
        re.compile(r"(?<![=!<>])(?P<op>==|!=)(?!=)(?!\s*(?:null|undefined)\b)"),
        "== converts types before comparing, so 0 == '' and '1' == 1 are both true.",
        "Use === and !== (x == null is the one common exception, and is left alone).",
        languages=JS,
        fix=lambda m, span, lang: span + "=",
    ),
    Rule(
        "java-string-equality",
        "Strings compared with ==",
        "warning",
        "bug",
        re.compile(r"(?<![=!])(?:==|!=)\s*\"|\"\s*(?:==|!=)(?!=)"),
        "== compares object identity, not contents, so two equal strings can compare false.",
        'Use .equals(), e.g. "admin".equals(role).',
        languages=frozenset({"java"}),
    ),
    Rule(
        "go-ignored-error",
        "Error discarded",
        "warning",
        "bug",
        re.compile(r"^[ \t]*_[ \t]*=[ \t]*[\w.]+\(", re.M),
        "The return value thrown away here is usually an error, so a failure goes unnoticed.",
        "Check it: if err := f(); err != nil { ... }.",
        languages=frozenset({"go"}),
    ),
    Rule(
        "php-mysql",
        "Removed mysql_* functions",
        "warning",
        "bug",
        re.compile(r"\bmysql_\w+\s*\("),
        "The mysql_* extension was removed in PHP 7, and it had no prepared statements.",
        "Use PDO or mysqli with prepared statements.",
        languages=frozenset({"php"}),
    ),
    # --- smells -------------------------------------------------------------------------
    Rule(
        "py-none-comparison",
        "Comparison to None with ==",
        "info",
        "smell",
        re.compile(r"(?P<op>==|!=)\s*None\b"),
        "== can be overridden by the class; `is` checks for None itself.",
        "Use `is None` / `is not None`.",
        languages=PY,
        fix=lambda m, span, lang: ("is" if m.group("op") == "==" else "is not") + " None",
    ),
    Rule(
        "js-var",
        "var declaration",
        "info",
        "smell",
        re.compile(r"\bvar\s+(?=[\w$])"),
        "var is function-scoped and hoisted, which causes surprises in loops and closures.",
        "Use let, or const if it's never reassigned.",
        languages=JS,
        fix=lambda m, span, lang: "let ",
    ),
    Rule(
        "console-log",
        "Leftover console.log",
        "info",
        "smell",
        re.compile(r"\bconsole\.(?:log|debug|trace)\s*\("),
        "Debug output left in code clutters the console and can leak data in production.",
        "Remove it or use a logger with levels.",
        languages=JS,
    ),
    Rule(
        "ts-any",
        "any type",
        "info",
        "smell",
        re.compile(r":\s*any\b|\bas\s+any\b|<any>"),
        "any switches off type checking for this value and everything it touches.",
        "Use a real type, or unknown and narrow it.",
        languages=TS,
    ),
    Rule(
        "java-print-stack-trace",
        "printStackTrace()",
        "info",
        "smell",
        re.compile(r"\.printStackTrace\s*\(\s*\)"),
        "Writes to stderr with no context and bypasses logging configuration.",
        'Log it with a logger: log.error("...", e).',
        languages=frozenset({"java"}),
    ),
    Rule(
        "todo-comment",
        "TODO / FIXME left in",
        "info",
        "smell",
        re.compile(r"\b(?:TODO|FIXME|HACK|XXX)\b"),
        "Marks unfinished or known-broken code.",
        "Finish it or track it in an issue.",
        view="comment",
    ),
]

BY_ID = {r.id: r for r in RULES}
assert len(BY_ID) == len(RULES), "rule ids must be unique"


def find(code: str, language: str) -> list[Finding]:
    views = scan(code, language)
    lines = code.split("\n")
    out: list[Finding] = []
    for rule in RULES:
        if rule.languages is not None and language not in rule.languages:
            continue
        text = getattr(views, rule.view)
        count = 0
        for m in rule.pattern.finditer(text):
            if rule.when and not rule.when(m, views):
                continue
            matched = m.group(0)
            start = m.start() + len(matched) - len(matched.lstrip())
            line = views.line_of(start)
            end_line = views.line_of(max(start, m.end() - 1))
            replacement = rule.fix(m, code[m.start() : m.end()], language) if rule.fix else None
            out.append(
                Finding(
                    rule, line, end_line, m.start(), m.end(), lines[line - 1].strip(), replacement
                )
            )
            count += 1
            if count >= MAX_PER_RULE:
                break
    out.sort(key=lambda f: (f.line, SEVERITIES.index(f.rule.severity)))
    return out


def insert_imports(code: str, needed: list[str], language: str) -> str:
    if language != "python" or not needed:
        return code
    lines = code.split("\n")
    present = {ln.strip() for ln in lines}
    missing = sorted(imp for imp in set(needed) if imp not in present)
    if not missing:
        return code
    at = next((i for i, ln in enumerate(lines) if re.match(r"(import|from)\s", ln)), None)
    if at is None:
        at = 0
        if lines and lines[0].startswith("#!"):
            at = 1
        # Keep a module docstring first
        if at < len(lines) and lines[at].lstrip().startswith(('"""', "'''")):
            q = lines[at].lstrip()[:3]
            rest = lines[at].lstrip()[3:]
            end = (
                at
                if q in rest
                else next((i for i in range(at + 1, len(lines)) if q in lines[i]), at)
            )
            at = end + 1
    return "\n".join(lines[:at] + missing + lines[at:])


def apply_fixes(code: str, findings: list[Finding], language: str) -> tuple[str, list[str]]:
    """The source with every non-overlapping rule fix applied, and the imports they need.

    Fixes stay within their lines, so line numbers don't move; imports are added at the
    very end (insert_imports), after the model's fixes, for the same reason.
    """
    out, pos, needed = [], 0, []
    for f in sorted((f for f in findings if f.replacement is not None), key=lambda f: f.start):
        if f.start < pos:
            continue
        out += [code[pos : f.start], f.replacement]
        pos = f.end
        if language in f.rule.imports:
            needed.append(f.rule.imports[language])
    out.append(code[pos:])
    return "".join(out), sorted(set(needed))


def catalogue() -> list[dict]:
    return [
        {
            "id": r.id,
            "title": r.title,
            "severity": r.severity,
            "category": r.category,
            "languages": sorted(r.languages) if r.languages else [],
            "explanation": r.explanation,
            "suggestion": r.suggestion,
            "fixable": r.fix is not None,
        }
        for r in RULES
    ]
