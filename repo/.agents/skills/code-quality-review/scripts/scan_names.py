#!/usr/bin/env python3
"""Naming pre-scan for the code-quality-review skill.

Scans ADDED lines of a change (git diff vs. base, staged changes, a diff file, or
whole files) and reports CANDIDATE naming violations for methods/functions and
types. Regex-based and language-aware, standard library only (Python 3.8+).

The output is a list of leads for the reviewer, not verdicts: confirm each one
against references/naming-conventions.md before reporting it.

Languages: Java, Kotlin, C#, TypeScript/JavaScript, Python, Go, Rust, Swift.

Usage:
  scan_names.py                       # current branch vs auto-detected base (+ uncommitted + untracked)
  scan_names.py --base origin/develop
  scan_names.py --staged
  scan_names.py --files src/a.ts src/b.py
  scan_names.py --diff-file change.patch
  scan_names.py --format json --fail-on high
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

SKILL_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = SKILL_DIR / "assets" / "naming-rules.json"

LANG_BY_EXT = {
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".cs": "csharp",
    ".ts": "ts", ".tsx": "ts", ".mts": "ts", ".cts": "ts",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".py": "python", ".go": "go", ".rs": "rust", ".swift": "swift",
}

TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|testing|androidTest|testFixtures)/"
    r"|_test\.go$|\.(test|spec)\.[cm]?[jt]sx?$|(^|/)test_[^/]*\.py$|_test\.py$"
    r"|Tests?\.(java|kt|cs|swift)$|(^|/)conftest\.py$"
)
GENERATED_PATH_RE = re.compile(r"(^|/)(generated|gen|build|dist|node_modules|vendor|target|migrations?)/|\.g\.(cs|dart)$|\.pb\.go$|_pb2\.py$|\.d\.ts$")

CONF_ORDER = {"low": 0, "medium": 1, "high": 2}

# ----------------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    identifier: str
    kind: str          # method | type
    rule: str
    confidence: str    # high | medium | low
    message: str


@dataclass
class FileContext:
    path: str
    lang: str
    prev_lines: List[str] = field(default_factory=list)   # recent non-blank lines (context + added)
    current_type: Optional[str] = None


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

WORD_RE = re.compile(r"[A-Z]+\d*(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+\d*|[A-Z]+\d*|\d+")


def split_words(name: str) -> List[str]:
    core = name.strip("_#$")
    if not core:
        return []
    parts: List[str] = []
    for chunk in re.split(r"_+", core):
        if chunk:
            parts.extend(WORD_RE.findall(chunk))
    return parts


def load_rules() -> dict:
    with open(RULES_PATH, encoding="utf-8") as fh:
        rules = json.load(fh)
    rules["_verbs"] = set(rules["approved_verbs"])
    rules["_vague"] = set(rules["vague_verbs"])
    rules["_pred"] = set(rules["predicate_prefixes"])
    ap = rules["allowed_prefixes"]
    rules["_prefix_ok"] = set(ap["conversion"]) | set(ap["event"]) | set(ap["hook"])
    rules["_prefix_next"] = set(ap["next_word_must_be_verb"])
    rules["_exempt"] = set(rules["exempt_method_names"])
    rules["_type_verbs"] = set(rules["type_verb_prefixes"])
    rules["_flag_exempt"] = set(rules["flag_argument_exempt_verbs"])
    rules["_phrasal"] = set(rules.get("phrasal_verbs", []))
    rules["_vague_nouns"] = set(rules.get("vague_nouns", []))
    rules["_worker"] = set(ap.get("template_worker", []))
    rules["_repo_counts"] = {}          # filled by repo_convention_counts()
    rules["_repo_min"] = int(rules.get("repo_consistency", {}).get("min_occurrences", 3))
    return rules


# ----------------------------------------------------------------------------
# Repo-consistency: what the base tree already does (repo convention wins)
# ----------------------------------------------------------------------------

TYPE_DECL_GREP = r"(^|[^A-Za-z0-9_])(class|interface|enum|record|struct|trait|protocol|object)[[:space:]]+[A-Z][A-Za-z0-9_]*"  # POSIX ERE: no \b
TYPE_DECL_PARSE = re.compile(r"\b(class|interface|enum|record|struct|trait|protocol|object)\s+([A-Z][A-Za-z0-9_]*)")
DECL_PREFIX = re.compile(r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:(?:public|private|protected|internal|static|final|abstract|synchronized|default|override|open|suspend|async|fun|def|func|pub|fn)\s+)*(?:[\w<>\[\],?.*&]+\s+)?(?:\(\s*\w+\s+\*?\w+\s*\)\s*)?(?:(?:check|handle|process|do|perform|manage)[A-Z_]\w*)\s*\(")
GIT_GREP_PATHSPECS = ["*.java", "*.kt", "*.kts", "*.cs", "*.ts", "*.tsx", "*.js", "*.jsx", "*.py", "*.go", "*.rs", "*.swift"]


def is_tool_folder(norm_path: str) -> bool:
    """Paths under dot-folders (.agents/.claude/.factory/.github/…) hold tooling, not the codebase."""
    return any(seg.startswith(".") for seg in norm_path.split("/")[:-1])


def _git_grep_lines(regex: str, ref: str) -> List[Tuple[str, str]]:
    """Return (path, line_text) for lines in `ref` matching `regex` (ERE)."""
    code, out = run_git(["grep", "-I", "-n", "-E", regex, ref, "--", *GIT_GREP_PATHSPECS])
    if code not in (0, 1):
        return []
    rows: List[Tuple[str, str]] = []
    for raw in out.splitlines():
        # format: <ref>:<path>:<line>:<text>
        parts = raw.split(":", 3)
        if len(parts) < 4:
            continue
        rows.append((parts[1], parts[3]))
    return rows


def repo_convention_counts(ref: Optional[str], rules: dict) -> Dict[str, int]:
    """Count how often the base tree already uses conventions this scanner would otherwise flag."""
    counts: Dict[str, int] = {}
    if not ref:
        return counts
    rc = rules.get("repo_consistency", {})
    suffixes = set(rc.get("type_suffixes", []))
    vague = set(rc.get("vague_verbs", []))
    for path, text in _git_grep_lines(TYPE_DECL_GREP, ref):
        norm = path.replace(os.sep, "/")
        if TEST_PATH_RE.search(norm) or GENERATED_PATH_RE.search(norm) or is_tool_folder(norm):
            continue
        m = TYPE_DECL_PARSE.search(text)
        if not m:
            continue
        kw, name = m.group(1), m.group(2)
        words = split_words(name)
        if words and words[-1] in suffixes:
            counts["suffix:" + words[-1]] = counts.get("suffix:" + words[-1], 0) + 1
        if kw in ("interface", "protocol", "trait") and re.match(r"^I[A-Z][a-z]", name) and not norm.endswith(".cs"):
            counts["iprefix"] = counts.get("iprefix", 0) + 1
    if vague:
        alt = "|".join(sorted(vague))
        for path, text in _git_grep_lines(r"(^|[^A-Za-z0-9_.])(" + alt + r")[A-Z_][A-Za-z0-9_]*[[:space:]]*\(", ref):
            norm = path.replace(os.sep, "/")
            if TEST_PATH_RE.search(norm) or GENERATED_PATH_RE.search(norm) or is_tool_folder(norm) or text.rstrip().endswith(";"):
                continue
            dm = DECL_PREFIX.match(text)
            if not dm:
                continue
            vm = re.search(r"\b(" + alt + r")[A-Z_]", text)
            if vm:
                counts["verb:" + vm.group(1)] = counts.get("verb:" + vm.group(1), 0) + 1
    return counts


def repo_note(rules: dict, key: str, what: str) -> Optional[str]:
    n = rules["_repo_counts"].get(key, 0)
    if n >= rules["_repo_min"]:
        return f" Established in this repo ({n} existing {what}); repo convention wins unless .agents/review-overrides.md says otherwise."
    return None


def is_comment(line: str, lang: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith(("//", "/*", "*", "*/")):
        return True
    if lang == "python" and (s.startswith("#") or s.startswith(('"""', "'''"))):
        return True
    if lang in ("csharp",) and s.startswith("#"):
        return True
    if lang == "rust" and s.startswith("#"):
        return True
    return False


def matching_paren(text: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(text)):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def params_and_rest(line: str, name_end: int) -> Tuple[Optional[str], Optional[str]]:
    """Return (params_text, text_after_params) for the first '(' at/after name_end."""
    open_idx = line.find("(", name_end)
    if open_idx < 0:
        return None, None
    close_idx = matching_paren(line, open_idx)
    if close_idx < 0:
        return line[open_idx + 1:], None   # signature continues on next line
    return line[open_idx + 1:close_idx], line[close_idx + 1:]


BOOL_NAMES = ("boolean", "Boolean", "bool", "Bool")
BOOL_RET_RE = re.compile(r"^\s*(?:(?:Promise|Task|ValueTask|Mono|Single|Future|CompletableFuture|Deferred|Observable)\s*<\s*)?(boolean|Boolean|bool|Bool)\s*>?\s*\??\s*$")
VOID_RET_RE = re.compile(r"^\s*(?:(?:Promise|Task|ValueTask|Mono|Future|CompletableFuture)\s*<\s*)?(void|Void|Unit|None|\(\s*\))\s*>?\s*$")


def return_type(lang: str, java_like_type: Optional[str], rest: Optional[str]) -> Optional[str]:
    """Best-effort return type. '' means 'known to be void'. None means unknown."""
    if lang in ("java", "csharp"):
        if java_like_type is None:
            return None
        t = java_like_type.strip()
        if lang == "csharp" and t in ("Task", "ValueTask"):
            return ""
        return "" if t == "void" else t
    if rest is None:
        return None
    r = rest.strip()
    if lang in ("kotlin", "ts", "js"):
        m = re.match(r"^:\s*([^{=;]+?)\s*(?:[{=;]|$)", r)
        if m:
            return m.group(1).strip()
        if lang == "kotlin" and r.startswith("{"):
            return ""   # block body without declared type => Unit
        return None
    if lang == "python":
        m = re.match(r"^->\s*([^:]+):", r)
        return m.group(1).strip() if m else None
    if lang in ("swift", "rust"):
        m = re.match(r"^(?:async\s+)?(?:throws\s+)?(?:rethrows\s+)?->\s*([^{;]+)", r)
        if m:
            return re.split(r"\s+where\s+", m.group(1))[0].strip()
        if re.match(r"^(?:async\s+)?(?:throws\s+)?(?:\{|;|$)", r):
            return ""
        return None
    if lang == "go":
        if "{" not in r and r:
            return None  # interface method or signature continues
        return r.split("{", 1)[0].strip()   # '' => no return values
    return None


def is_bool_type(t: Optional[str]) -> bool:
    return bool(t) and bool(BOOL_RET_RE.match(t))


def is_void_type(t: Optional[str]) -> bool:
    return t == "" or (bool(t) and bool(VOID_RET_RE.match(t)))


def has_bool_flag_param(lang: str, params: Optional[str]) -> bool:
    if not params:
        return False
    if lang == "python":
        # keyword-only arguments (after a bare '*') are fine
        star = re.search(r"(^|,)\s*\*\s*(,|$)", params)
        scope = params[:star.start()] if star else params
        return bool(re.search(r"\b\w+\s*:\s*bool\b", scope))
    if lang in ("java", "csharp"):
        return bool(re.search(r"(^|[,(])\s*(?:final\s+)?(boolean|bool|Boolean)\s+\w+", params))
    if lang == "go":
        return bool(re.search(r"\b\w+\s+bool\b", params))
    if lang == "swift":
        # only flag when the external label is suppressed with '_'
        return bool(re.search(r"\b_\s+\w+\s*:\s*Bool\b", params))
    return bool(re.search(r"\b\w+\s*\??\s*:\s*(boolean|Boolean|bool)\b", params))


def expected_method_case(lang: str, name: str) -> Optional[str]:
    core = name.lstrip("_#")
    if not core:
        return None
    if lang in ("java", "kotlin", "ts", "js", "swift"):
        if not re.match(r"^[a-z][a-zA-Z0-9]*$", core):
            return "lowerCamelCase"
    elif lang == "csharp":
        if not re.match(r"^[A-Z][A-Za-z0-9]*$", core):
            return "PascalCase"
    elif lang == "go":
        if not re.match(r"^[A-Za-z][A-Za-z0-9]*$", core):
            return "MixedCaps (no underscores)"
    elif lang in ("python", "rust"):
        if not re.match(r"^[a-z][a-z0-9_]*$", core):
            return "snake_case"
    return None


# ----------------------------------------------------------------------------
# Declaration extraction
# ----------------------------------------------------------------------------

JAVA_MODS = r"public|private|protected|static|final|abstract|synchronized|native|default|strictfp|transient"
CS_MODS = r"public|private|protected|internal|static|sealed|abstract|virtual|override|async|extern|new|unsafe|partial|readonly|ref"
JAVA_LIKE_METHOD = re.compile(
    r"^\s*(?:(?:@[\w.]+(?:\([^)]*\))?|\[[^\]]*\])\s*)*"
    r"((?:(?:" + JAVA_MODS + "|" + CS_MODS + r")\s+)*)"
    r"(?:<[^>]+>\s+)?"
    r"([\w.?]+(?:\s*<[^()]*>)?(?:\[\])*\??)\s+"
    r"(\w+)\s*(?:<[^>()]*>\s*)?\("
)
MODIFIER_WORDS = set((JAVA_MODS + "|" + CS_MODS).split("|"))
NOT_A_TYPE = {"return", "new", "throw", "else", "case", "await", "yield", "goto", "using", "lock",
              "package", "import", "assert", "var", "val", "let", "const", "in", "is", "as", "out", "not", "and", "or"}
CONTROL_WORDS = {"if", "for", "while", "switch", "catch", "foreach", "using", "lock", "return", "fixed",
                 "when", "synchronized", "function", "super", "this", "typeof", "sizeof", "nameof", "do",
                 "else", "with", "await", "new", "delete", "void", "constructor", "try", "throw", "yield"}

KOTLIN_FUN = re.compile(r"^(\s*)(?:[\w@]+\s+)*fun\s+(?:<[^>]*>\s*)?(?:([\w.<>?, ]+?)\.)?(\w+|`[^`]+`)\s*\(")
PY_DEF = re.compile(r"^(\s*)(?:async\s+)?def\s+(\w+)\s*\(")
GO_FUNC = re.compile(r"^func\s+(\(([^)]*)\)\s*)?(\w+)\s*(?:\[[^\]]*\])?\s*\(")
RUST_FN = re.compile(r"^(\s*)(?:pub(?:\([^)]*\))?\s+)?(?:default\s+)?(?:const\s+)?(?:async\s+)?(?:unsafe\s+)?(?:extern\s+\"[^\"]*\"\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(")
SWIFT_FUNC = re.compile(r"^(\s*)(?:@\w+(?:\([^)]*\))?\s+)*(?:(?:public|private|fileprivate|internal|open|static|class|final|override|mutating|nonmutating|convenience|required|nonisolated|dynamic)\s+)*func\s+(\w+)\s*(?:<[^>]*>)?\s*\(")
JS_FUNCTION = re.compile(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)\s*(?:<[^>]*>)?\s*\(")
JS_ARROW_VAR = re.compile(r"^(\s*)(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*[^=]+?)?=\s*(?:async\s+)?(?:\(|\w+\s*=>)")
JS_CLASS_FIELD_ARROW = re.compile(r"^(\s+)(?:(?:public|private|protected|readonly|static|override)\s+)*(#?\w+)\s*(?::\s*[^=]+?)?=\s*(?:async\s+)?\(")
JS_METHOD = re.compile(r"^(\s+)((?:(?:public|private|protected|static|async|readonly|override|abstract|declare|get|set)\s+)*)\*?\s*(#?\w+)\s*(?:<[^>()]*>)?\s*\(")

TYPE_PATTERNS = {
    "java": re.compile(r"^\s*(?:@[\w.]+(?:\([^)]*\))?\s+)*(?:(?:public|private|protected|static|final|abstract|sealed|non-sealed|strictfp)\s+)*(class|interface|enum|record|@interface)\s+(\w+)(.*)$"),
    "kotlin": re.compile(r"^\s*(?:(?:public|private|internal|protected|open|abstract|sealed|data|enum|annotation|inner|value|inline|expect|actual|fun)\s+)*(class|interface|object)\s+(\w+)(.*)$"),
    "csharp": re.compile(r"^\s*(?:\[[^\]]*\]\s*)*(?:(?:public|private|protected|internal|static|sealed|abstract|partial|readonly|ref|unsafe|new|file)\s+)*(class|interface|struct|record(?:\s+struct|\s+class)?|enum)\s+(\w+)(.*)$"),
    "ts": re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:declare\s+)?(?:abstract\s+)?(?:const\s+)?(class|interface|enum|type)\s+(\w+)(.*)$"),
    "js": re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(class)\s+(\w+)(.*)$"),
    "python": re.compile(r"^\s*class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:"),
    "go": re.compile(r"^\s*(?:type\s+)?(\w+)\s+(?:\[[^\]]*\]\s*)?(struct|interface)\s*\{"),
    "rust": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(struct|enum|trait|type|union)\s+(\w+)(.*)$"),
    "swift": re.compile(r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:(?:public|private|fileprivate|internal|open|final|indirect)\s+)*(class|struct|protocol|enum|actor)\s+(\w+)(.*)$"),
}


@dataclass
class MethodDecl:
    name: str
    name_end: int
    top_level: bool
    accessor: bool
    params: Optional[str]
    ret: Optional[str]          # '' void, None unknown
    receiver_type: Optional[str] = None


def extract_method(line: str, ctx: FileContext) -> Optional[MethodDecl]:
    lang = ctx.lang
    prev = ctx.prev_lines[-1].strip() if ctx.prev_lines else ""

    if lang in ("java", "csharp"):
        m = JAVA_LIKE_METHOD.match(line)
        if not m:
            return None
        mods, rtype, name = m.group(1), m.group(2), m.group(3)
        if rtype in MODIFIER_WORDS or rtype in NOT_A_TYPE or name in CONTROL_WORDS:
            return None  # constructor, statement, or keyword
        if re.search(r"=", line[:m.start(3)]):
            return None
        params, rest = params_and_rest(line, m.end(3))
        if rest is not None and not re.match(r"^\s*(?:throws\b[^{;]*)?(?:where\b[^{;]*)?\s*(?:\{|;|=>|$)", rest):
            return None  # e.g. a call expression followed by more code
        return MethodDecl(name, m.end(3), False, False, params, return_type(lang, rtype, rest))

    if lang == "kotlin":
        m = KOTLIN_FUN.match(line)
        if not m:
            return None
        name = m.group(3)
        if name.startswith("`"):
            return None  # backtick test names
        params, rest = params_and_rest(line, m.end(3))
        top = len(m.group(1)) == 0 and not m.group(2)
        return MethodDecl(name, m.end(3), top, False, params, return_type(lang, None, rest), m.group(2))

    if lang == "python":
        m = PY_DEF.match(line)
        if not m:
            return None
        name = m.group(2)
        accessor = prev.startswith(("@property", "@cached_property", "@functools.cached_property")) or bool(re.match(r"@\w+\.(setter|getter|deleter)", prev))
        params, rest = params_and_rest(line, m.end(2))
        return MethodDecl(name, m.end(2), len(m.group(1)) == 0, accessor, params, return_type(lang, None, rest))

    if lang == "go":
        m = GO_FUNC.match(line)
        if not m:
            return None
        name = m.group(3)
        params, rest = params_and_rest(line, m.end(3))
        has_receiver = bool(m.group(1))
        getter = has_receiver and params is not None and params.strip() == ""
        recv = None
        if has_receiver:
            rm = re.search(r"\*?\s*([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*$", m.group(2) or "")
            recv = rm.group(1) if rm else None
        return MethodDecl(name, m.end(3), not has_receiver, getter, params, return_type(lang, None, rest), recv)

    if lang == "rust":
        m = RUST_FN.match(line)
        if not m:
            return None
        name = m.group(2)
        params, rest = params_and_rest(line, m.end(2))
        getter = params is not None and params.strip() in ("&self", "&mut self", "self")
        return MethodDecl(name, m.end(2), len(m.group(1)) == 0, getter, params, return_type(lang, None, rest))

    if lang == "swift":
        m = SWIFT_FUNC.match(line)
        if not m:
            return None
        name = m.group(2)
        params, rest = params_and_rest(line, m.end(2))
        return MethodDecl(name, m.end(2), len(m.group(1)) == 0, False, params, return_type(lang, None, rest))

    if lang in ("ts", "js"):
        for rx, top_group in ((JS_FUNCTION, True), (JS_ARROW_VAR, True)):
            m = rx.match(line)
            if m:
                name = m.group(2)
                if rx is JS_ARROW_VAR and "=>" not in line:
                    return None
                params, rest = params_and_rest(line, m.end(2) if rx is JS_FUNCTION else line.find("=", m.end(2)))
                if rx is JS_ARROW_VAR:
                    rest = None  # arrow return types are rarely on a simple form
                return MethodDecl(name, m.end(2), len(m.group(1)) == 0, False, params, return_type(lang, None, rest))
        m = JS_CLASS_FIELD_ARROW.match(line)
        if m and "=>" in line and m.group(2) not in CONTROL_WORDS:
            params, _ = params_and_rest(line, line.find("=", m.end(2)))
            return MethodDecl(m.group(2), m.end(2), False, False, params, None)
        m = JS_METHOD.match(line)
        if m:
            mods, name = m.group(2) or "", m.group(3)
            if name in CONTROL_WORDS or name.lstrip("#") in CONTROL_WORDS:
                return None
            params, rest = params_and_rest(line, m.end(3))
            if rest is None:
                return None
            r = rest.strip()
            # declaration: optional ': ReturnType' then a body '{…' or ';' (interface/abstract signature)
            if not re.match(r"^(?::[^{;=]+)?\s*(\{.*|;\s*)$", r):
                return None  # call statement or expression, not a declaration
            if r.startswith(";"):
                return None  # 'foo(x);' is a call, not a signature
            accessor = bool(re.search(r"\b(get|set)\s+$", mods))
            return MethodDecl(name, m.end(3), False, accessor, params, return_type(lang, None, rest))
    return None


@dataclass
class TypeDecl:
    name: str
    keyword: str
    is_interface: bool
    is_abstract: bool
    exception_base: bool


def extract_type(line: str, ctx: FileContext) -> Optional[TypeDecl]:
    lang = ctx.lang
    rx = TYPE_PATTERNS.get(lang)
    if not rx:
        return None
    m = rx.match(line)
    if not m:
        return None
    if lang == "python":
        name, bases = m.group(1), (m.group(2) or "")
        base_names = [b.strip().split("[")[0].split(".")[-1] for b in bases.split(",") if b.strip() and "=" not in b]
        is_iface = any(b in ("Protocol", "ABC") for b in base_names)
        is_abstract = any(b in ("ABC",) for b in base_names) or "ABCMeta" in bases
        exc = any(re.search(r"(Exception|Error)$", b) for b in base_names)
        return TypeDecl(name, "class", is_iface, is_abstract, exc)
    if lang == "go":
        name, kw = m.group(1), m.group(2)
        if name in ("type", "struct", "interface"):
            return None
        return TypeDecl(name, kw, kw == "interface", False, False)
    kw, name, rest = m.group(1), m.group(2), m.group(3) or ""
    if lang == "kotlin" and kw == "object" and name == "companion":
        return None
    is_iface = (kw in ("interface", "trait", "protocol")) and not (lang == "java" and kw == "@interface")
    is_abstract = bool(re.search(r"\babstract\b", line[:m.start(1)])) or (lang == "kotlin" and "sealed" in line[:m.start(1)])
    exc = False
    if lang in ("java", "ts", "js"):
        b = re.search(r"\bextends\s+([\w.]+)", rest)
        exc = bool(b and re.search(r"(Exception|Error|Throwable)$", b.group(1)))
    elif lang == "kotlin":
        b = re.search(r":\s*([\w.]+)\s*\(", rest)
        exc = bool(b and re.search(r"(Exception|Error|Throwable)$", b.group(1)))
    elif lang == "csharp":
        b = re.search(r":\s*([\w.]+)", rest)
        exc = bool(b and re.search(r"Exception$", b.group(1)))
    elif lang == "swift":
        exc = bool(re.search(r":\s*[^{]*\b(Error|LocalizedError)\b", rest))
    return TypeDecl(name, kw, is_iface, is_abstract, exc)


# ----------------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------------

def is_verb(word: str, verbs: set) -> bool:
    """Accept base forms and simple third-person forms (loads, matches, applies)."""
    if word in verbs:
        return True
    if word.endswith("ies") and word[:-3] + "y" in verbs:
        return True
    if word.endswith("es") and word[:-2] in verbs:
        return True
    return word.endswith("s") and not word.endswith("ss") and word[:-1] in verbs


def cased(lang: str, words: List[str]) -> str:
    """Join words into an identifier using the language's method casing."""
    lw = [w.lower() for w in words]
    if lang in ("python", "rust"):
        return "_".join(lw)
    if lang in ("csharp", "go"):
        return "".join(w.capitalize() for w in lw)
    return lw[0] + "".join(w.capitalize() for w in lw[1:])


def verb_examples(lang: str, noun_words: List[str]) -> str:
    return ", ".join(cased(lang, [v] + noun_words) for v in ("get", "fetch", "calculate"))


def check_method(decl: MethodDecl, ctx: FileContext, line_no: int, rules: dict, out: List[Finding]) -> None:
    lang, name = ctx.lang, decl.name
    raw = name.lstrip("_#")
    if not raw or (name.startswith("__") and name.endswith("__")):
        return
    if raw in rules["_exempt"] or name in rules["_exempt"]:
        return
    if lang in ("ts", "js") and raw[:1].isupper():
        return  # React component or constructor function
    if lang == "go" and (raw.startswith(("Test", "Benchmark", "Example", "Fuzz")) or re.match(r"^[Nn]ew([A-Z]|$)", raw)):
        return  # Go tests and NewX constructors

    def add(rule: str, conf: str, msg: str) -> None:
        out.append(Finding(ctx.path, line_no, name, "method", rule, conf, msg))

    case = expected_method_case(lang, name)
    if case:
        add("NAME-CASE", "high", f"Method/function name should be {case} in this language.")

    words = split_words(name)
    if not words:
        return
    lw = [w.lower() for w in words]
    first = lw[0]
    verbs, vague, pred = rules["_verbs"], rules["_vague"], rules["_pred"]

    # predicate prefixes: the boolean contract must hold
    if first in pred:
        if decl.ret is not None and not is_bool_type(decl.ret):
            label = "nothing (void)" if is_void_type(decl.ret) else f"'{decl.ret}'"
            add("NAME-M2", "high" if is_void_type(decl.ret) else "medium",
                f"'{words[0]}…' promises a boolean but the declaration returns {label}. Rename, or return a boolean.")
        return

    # verb contract: get* returning nothing
    if first == "get" and len(words) > 1 and decl.ret is not None and is_void_type(decl.ret):
        add("NAME-M2", "high", "'get…' returns nothing; a getter that does not return is misleading. Use a command verb (load/refresh/apply…).")

    # flag arguments
    if has_bool_flag_param(lang, decl.params) and first not in rules["_flag_exempt"]:
        conf = "low" if lang in ("kotlin", "csharp") else ("medium" if lang in ("python", "swift") else "high")
        add("NAME-M5", conf, "Boolean flag parameter: split into two intention-revealing methods or use an enum/named option.")

    # redundant context (method name ends with the enclosing type's name)
    owner = decl.receiver_type if lang == "go" else ctx.current_type
    if owner and not decl.top_level and len(words) > 1:
        tl = [w.lower() for w in split_words(owner)]
        if tl and len(tl) < len(lw) and lw[-len(tl):] == tl:
            add("NAME-M6", "low", f"Repeats the type name '{owner}'; the receiver already supplies it (e.g. '{cased(lang, words[:-len(tl)])}()').")

    if decl.accessor:
        return  # properties and Go/Rust getters are nouns by idiom

    # idiomatic non-verb prefixes and conversions (intToBytes, timestamp_to_datetime)
    if first in rules["_prefix_ok"]:
        return
    if len(lw) >= 3 and "to" in lw[1:-1]:
        return
    idx = 1 if (first in rules["_prefix_next"] and not is_verb(first, verbs) and len(lw) > 1) else 0
    verb = lw[idx]
    nxt = lw[idx + 1] if idx + 1 < len(lw) else None
    phrasal = nxt is not None and f"{verb} {nxt}" in rules["_phrasal"]
    noun_start = idx + (2 if phrasal else 1)

    # boolean-returning method that is not a predicate
    if is_bool_type(decl.ret) and (verb in ("get", "check") or (not is_verb(verb, verbs) and verb not in vague and not phrasal)):
        if verb == "get" and nxt in pred:
            hint = cased(lang, words[idx + 1:])                      # getIsEmpty -> isEmpty
        elif verb in ("get", "check") or any(w in pred for w in lw[idx + 1:]):
            hint = cased(lang, ["is"]) + "…/" + cased(lang, ["has"]) + "…/" + cased(lang, ["can"]) + "…"
        else:
            hint = cased(lang, ["is"] + words[idx:])                 # valid -> isValid
        add("NAME-M4", "medium", f"Returns a boolean; name it as a predicate, e.g. {hint}.")
        return

    if verb in rules["_worker"] and nxt is not None and is_verb(nxt, verbs) and not decl.top_level:
        add("NAME-M3", "low", f"'{name}' looks like a template-method worker (Spring idiom: '{cased(lang, words[idx + 1:])}' delegates to '{name}'). OK only if that public method exists; otherwise the 'do' prefix is noise.")
        return

    if verb in vague and not phrasal:
        nouns = words[idx + 1:]
        note = repo_note(rules, "verb:" + verb, f"methods start with '{verb}'")
        if verb == "handle" and nouns and nouns[0] not in rules["_vague_nouns"]:
            add("NAME-M3", "low", "'handle' is acceptable only for event/command/UI handlers (handleOrderPlaced, handleClick). Otherwise name the outcome." + (note or ""))
        elif note:
            add("NAME-M3", "low", f"Vague verb '{words[idx]}' by default." + note)
        else:
            add("NAME-M3", "medium", f"Vague verb '{words[idx]}': say what actually happens (validate…, save…, send…, calculate…, parse…, authorize…).")
        return

    if not is_verb(verb, verbs) and not phrasal:
        nouns = words[idx:]
        n_params = None if decl.params is None else len([p for p in decl.params.split(",") if p.strip() and p.strip() not in ("self", "&self", "cls")])
        returns_value = decl.ret not in (None, "") and not is_void_type(decl.ret)
        accessor_like = returns_value and n_params is not None and (n_params == 0 or (lang == "go" and n_params == 1))
        if accessor_like:
            add("NAME-M1", "low", f"Starts with '{words[idx]}', not an action verb. Acceptable only as a pure accessor on a value object/record; otherwise use verb+noun ({verb_examples(lang, nouns)}).")
        else:
            add("NAME-M1", "medium", f"Starts with '{words[idx]}', not an action verb. Use verb+noun whose verb states the contract, e.g. {verb_examples(lang, nouns)}; if '{verb}' is a legitimate domain verb, add it to assets/naming-rules.json.")
        return

    # verb without a noun on a free/top-level function
    if decl.top_level and len(words) <= noun_start:
        add("NAME-M1", "low", f"Free function '{name}' is a bare verb; add the object it acts on (e.g. {cased(lang, words[idx:noun_start] + ['Invoice'])}).")


def check_type(decl: TypeDecl, ctx: FileContext, line_no: int, rules: dict, out: List[Finding]) -> None:
    lang, name = ctx.lang, decl.name

    def add(rule: str, conf: str, msg: str) -> None:
        out.append(Finding(ctx.path, line_no, name, "type", rule, conf, msg))

    core = name.lstrip("_")
    if lang == "go":
        ok_case = re.match(r"^[A-Za-z][A-Za-z0-9]*$", core)
    else:
        ok_case = re.match(r"^[A-Z][A-Za-z0-9]*$", core)
    if not ok_case:
        add("NAME-CASE", "high", "Type names should be PascalCase (Go: MixedCaps).")

    words = split_words(core)
    if not words:
        return
    last, first = words[-1], words[0]

    # interfaces
    i_prefixed = bool(re.match(r"^I[A-Z][a-z]", core))
    if decl.is_interface:
        if lang == "csharp" and not i_prefixed:
            add("NAME-T3", "high", "C# interfaces must start with 'I' (e.g. IPaymentGateway).")
        elif lang != "csharp" and i_prefixed:
            note = repo_note(rules, "iprefix", "'I'-prefixed interfaces")
            add("NAME-T3", "low" if note else "medium", f"Drop the 'I' prefix; in this language interfaces are named by role (e.g. '{core[1:]}')." + (note or ""))
        if last in ("Interface", "Iface", "Contract") and len(words) > 1:
            add("NAME-T3", "medium", "Don't encode 'Interface' in the name; name the role/capability.")

    # banned suffixes
    banned = rules["banned_type_suffixes"]
    if len(words) > 1 or last in ("Manager", "Helper", "Helpers", "Util", "Utils", "Utility", "Utilities", "Misc", "Stuff", "Thing"):
        if last in banned:
            info = banned[last]
            if last == "Handler" and len(words) > 1 and (words[-2] in rules["handler_ok_previous_words"] or words[-2].endswith("ed")):
                pass
            else:
                note = repo_note(rules, "suffix:" + last, f"types end in '{last}'")
                add("NAME-T2", "low" if note else info["confidence"], f"Suffix '{last}' is vague. {info['hint']}" + (note or ""))
    for pfx, info in rules["banned_type_prefixes"].items():
        if first == pfx and len(words) > 1:
            add("NAME-T2", info["confidence"], f"Prefix '{pfx}' is vague. {info['hint']}")

    if first == "Base" and len(words) > 1 and not decl.is_abstract and not decl.is_interface and lang not in ("go", "rust"):
        add("NAME-T2", "medium", "'Base…' on a non-abstract type; make it abstract or name it for what it is.")

    if re.search(r"\d+$", core) and not re.search(r"(V\d+|Http2|Utf8|Base64|Sha\d+|Md5|Oauth2|S3|Ec2|X509|Iso\d+|B2b|B2c|P2p)$", core, re.I):
        add("NAME-T2", "low", "Numbered type name suggests a parallel implementation; use a meaningful distinction.")

    # verb-named types
    if first.lower() in rules["_type_verbs"] and len(words) > 1 and last not in rules["type_verb_allowed_suffixes"]:
        add("NAME-T5", "medium", f"Type name starts with the verb '{first}'. Types are nouns ({first}{''.join(words[1:])} → e.g. a '…{'Calculator' if first.lower() in ('calculate', 'compute') else 'Service'}'), unless it is a Command/Query/UseCase/Request.")

    # exceptions
    if decl.exception_base and not re.search(r"(Exception|Error|Failure|Fault)$", core):
        suffix = "Error" if lang in ("python", "swift", "ts", "js") else "Exception"
        add("NAME-T1", "medium", f"Exception/error type should end with '{suffix}' (e.g. {core}{suffix}).")

    # enums with plural names
    if decl.keyword == "enum" and last.endswith("s") and not last.endswith(("ss", "us", "is")) and lang != "rust":
        add("NAME-T1", "low", "Enum names are usually singular (PaymentStatus, not PaymentStatuses).")
    if decl.keyword == "enum" and last == "Enum":
        add("NAME-T1", "medium", "Don't encode 'Enum' in the name.")


# ----------------------------------------------------------------------------
# Input: diffs and files
# ----------------------------------------------------------------------------

def run_git(args: List[str]) -> Tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
        return p.returncode, p.stdout
    except FileNotFoundError:
        return 127, ""


def detect_base() -> Optional[str]:
    for cand in ("origin/main", "origin/master", "origin/develop", "main", "master", "develop"):
        code, out = run_git(["merge-base", "HEAD", cand])
        if code == 0 and out.strip():
            return out.strip()
    return None


def iter_diff(diff_text: str) -> Iterable[Tuple[str, int, str, bool]]:
    """Yield (path, new_line_no, text, is_added) for context and added lines."""
    path: Optional[str] = None
    new_no = 0
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            path = None
            continue
        if raw.startswith("+++ "):
            p = raw[4:].strip()
            if p == "/dev/null":
                path = None
            else:
                path = p[2:] if p.startswith("b/") else p
                path = path.split("\t")[0]
            continue
        if raw.startswith("--- "):
            continue
        if raw.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            new_no = int(m.group(1)) if m else 0
            continue
        if path is None:
            continue
        if raw.startswith("+"):
            yield path, new_no, raw[1:], True
            new_no += 1
        elif raw.startswith(" "):
            yield path, new_no, raw[1:], False
            new_no += 1
        elif raw.startswith("-") or raw.startswith("\\"):
            continue


def iter_files(paths: List[str]) -> Iterable[Tuple[str, int, str, bool]]:
    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for i, text in enumerate(fh, start=1):
                    yield p, i, text.rstrip("\n"), True
        except OSError as exc:
            print(f"warning: cannot read {p}: {exc}", file=sys.stderr)


def in_git_work_tree() -> bool:
    code, _ = run_git(["rev-parse", "--is-inside-work-tree"])
    return code == 0


def collect_input(args: argparse.Namespace) -> Tuple[Iterable[Tuple[str, int, str, bool]], Optional[str]]:
    """Return (lines to scan, git ref of the base tree used for repo-consistency counts or None)."""
    if args.files:
        return iter_files(args.files), (args.repo_ref or ("HEAD" if in_git_work_tree() else None))
    if args.diff_file:
        text = sys.stdin.read() if args.diff_file == "-" else Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
        return iter_diff(text), (args.repo_ref or ("HEAD" if in_git_work_tree() else None))
    if not in_git_work_tree():
        sys.exit("error: not a git repository (or git missing). Use --files or --diff-file.")
    if args.staged:
        _, diff = run_git(["diff", "--cached", "--unified=3", "--no-color"])
        return iter_diff(diff), (args.repo_ref or "HEAD")
    base = args.base
    if base:
        code, mb = run_git(["merge-base", "HEAD", base])
        base = mb.strip() if code == 0 and mb.strip() else base
    else:
        base = detect_base() or "HEAD"
    _, diff = run_git(["diff", base, "--unified=3", "--no-color"])
    chunks: List[Iterable[Tuple[str, int, str, bool]]] = [iter_diff(diff)]
    if not args.no_untracked:
        _, untracked = run_git(["ls-files", "--others", "--exclude-standard"])
        files = [f for f in untracked.splitlines() if Path(f).suffix in LANG_BY_EXT]
        chunks.append(iter_files(files))
    print(f"scope: git diff {base[:12]} (+ uncommitted{'' if args.no_untracked else ' + untracked'})", file=sys.stderr)
    return (item for chunk in chunks for item in chunk), (args.repo_ref or base)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def scan(lines: Iterable[Tuple[str, int, str, bool]], rules: dict, include_tests: bool) -> List[Finding]:
    findings: List[Finding] = []
    contexts: Dict[str, FileContext] = {}
    for path, line_no, text, added in lines:
        lang = LANG_BY_EXT.get(Path(path).suffix)
        if not lang:
            continue
        norm = path.replace(os.sep, "/")
        if GENERATED_PATH_RE.search(norm) or is_tool_folder(norm):
            continue
        if not include_tests and TEST_PATH_RE.search(norm):
            continue
        ctx = contexts.setdefault(path, FileContext(path=norm, lang=lang))
        if not is_comment(text, lang):
            tdecl = extract_type(text, ctx)
            if tdecl:
                ctx.current_type = tdecl.name
                if added:
                    check_type(tdecl, ctx, line_no, rules, findings)
            elif added:
                mdecl = extract_method(text, ctx)
                if mdecl:
                    check_method(mdecl, ctx, line_no, rules, findings)
        if text.strip():
            ctx.prev_lines.append(text)
            if len(ctx.prev_lines) > 3:
                ctx.prev_lines.pop(0)
    # de-duplicate (same file/line/rule)
    seen = set()
    unique = []
    for f in findings:
        key = (f.file, f.line, f.rule, f.identifier, f.message)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    unique.sort(key=lambda f: (f.file, f.line, -CONF_ORDER[f.confidence]))
    return unique


def render_repo_conventions(rules: dict) -> str:
    hits = {k: v for k, v in rules["_repo_counts"].items() if v >= rules["_repo_min"]}
    if not hits:
        return ""
    parts = []
    for key, n in sorted(hits.items(), key=lambda kv: -kv[1]):
        kind, _, what = key.partition(":")
        label = {"suffix": f"*{what} types", "verb": f"{what}* methods", "iprefix": "I*-prefixed interfaces"}.get(kind, key)
        parts.append(f"{label} ×{n}")
    return ("Repo conventions detected in the base tree (matching candidates downgraded to 'low'; see references/repo-conventions.md): "
            + ", ".join(parts) + ".")


def render_markdown(findings: List[Finding], min_conf: str, rules: Optional[dict] = None) -> str:
    shown = [f for f in findings if CONF_ORDER[f.confidence] >= CONF_ORDER[min_conf]]
    conv = render_repo_conventions(rules) if rules else ""
    if not shown:
        return (conv + "\n\n" if conv else "") + "No naming candidates found on added lines (at or above confidence '%s')." % min_conf
    counts = {c: sum(1 for f in shown if f.confidence == c) for c in ("high", "medium", "low")}
    lines = [
        f"Naming candidates: {len(shown)} (high {counts['high']}, medium {counts['medium']}, low {counts['low']}). "
        "Confirm each against references/naming-conventions.md before reporting.",
    ]
    if conv:
        lines.append(conv)
    lines += [
        "",
        "| Conf | Rule | Location | Identifier | Note |",
        "|---|---|---|---|---|",
    ]
    for f in shown:
        note = f.message.replace("|", "\\|")
        lines.append(f"| {f.confidence} | {f.rule} | `{f.file}:{f.line}` | `{f.identifier}` | {note} |")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--base", help="Base ref to diff against (merge-base with HEAD is used).")
    src.add_argument("--staged", action="store_true", help="Scan staged changes only.")
    src.add_argument("--files", nargs="+", help="Scan whole files instead of a diff.")
    src.add_argument("--diff-file", help="Read a unified diff from a file ('-' for stdin).")
    ap.add_argument("--no-untracked", action="store_true", help="Ignore untracked files in branch mode.")
    ap.add_argument("--include-tests", action="store_true", help="Also scan test files.")
    ap.add_argument("--min-confidence", choices=["low", "medium", "high"], default="low")
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown")
    ap.add_argument("--fail-on", choices=["low", "medium", "high"], help="Exit 1 if any finding at/above this confidence (for CI).")
    ap.add_argument("--repo-ref", help="Git ref whose tree defines the repo's existing conventions (default: the diff base, or HEAD).")
    ap.add_argument("--ignore-repo-conventions", action="store_true", help="Do not downgrade candidates that match an established repo convention.")
    args = ap.parse_args(argv)

    rules = load_rules()
    lines, ref = collect_input(args)
    if not args.ignore_repo_conventions:
        rules["_repo_counts"] = repo_convention_counts(ref, rules)
    findings = scan(lines, rules, args.include_tests)
    shown = [f for f in findings if CONF_ORDER[f.confidence] >= CONF_ORDER[args.min_confidence]]
    if args.format == "json":
        print(json.dumps({"repo_conventions": {k: v for k, v in rules["_repo_counts"].items() if v >= rules["_repo_min"]},
                          "findings": [asdict(f) for f in shown]}, indent=2))
    else:
        print(render_markdown(findings, args.min_confidence, rules))
    if args.fail_on and any(CONF_ORDER[f.confidence] >= CONF_ORDER[args.fail_on] for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
