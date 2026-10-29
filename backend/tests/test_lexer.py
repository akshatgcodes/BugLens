from app.lexer import MASK, scan


def show(s: str) -> str:
    return s.replace(MASK, "~")


def test_python_strings_and_comments():
    v = scan("x = \"eval(1)\"  # eval(2)\ny = 'a\\'b'\n", "python")
    assert show(v.code).split("\n")[0] == 'x = "~~~~~~~"           '
    assert v.comment.split("\n")[0].strip() == "# eval(2)"
    assert show(v.code).split("\n")[1] == "y = '~~~~'"
    assert len(v.code) == len(v.raw) == len(v.comment)


def test_triple_quotes_span_lines_but_plain_quotes_dont():
    v = scan('"""doc\neval(x)\n"""\nz = "open\nw = 1\n', "python")
    lines = show(v.code).split("\n")
    assert lines[1] == "~~~~~~~"  # inside the docstring
    assert lines[3] == 'z = "~~~~'  # unterminated: stops at the end of its line
    assert lines[4] == "w = 1"


def test_js_block_comments_and_template_literals():
    v = scan("/* eval(a)\n */ let s = `x\n${y}`; // hi\n", "javascript")
    lines = show(v.code).split("\n")
    assert lines[0].strip() == "" and "eval(a)" in v.comment
    assert lines[1].strip().startswith("let s = `~")
    assert lines[2] == "~~~~`;      "


def test_go_raw_strings_have_no_escapes():
    v = scan("a := `C:\\path`\nb := 1\n", "go")
    assert show(v.code).split("\n") == ["a := `~~~~~~~`", "b := 1", ""]


def test_php_hash_comments_and_line_of():
    v = scan("<?php\n# eval($x)\n$y = 1;\n", "php")
    assert "eval" not in v.code and "eval" in v.comment
    assert v.line_of(v.raw.index("$y")) == 3
