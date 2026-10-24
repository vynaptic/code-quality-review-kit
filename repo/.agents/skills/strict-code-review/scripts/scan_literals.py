#!/usr/bin/env python3
"""Repeated-literal and data-modelling lead scanner for the strict-code-review skill.

Read-only. Runs `git` (diff, show, ls-files, rev-parse) and reads files; it never
writes, never touches the network, never changes the repository.

Finds leads for references/literals-and-data-carriers.md on the changed files of a
review: the same string or number repeated across production code (REP-STRING,
REP-NUMBER), several literals compared under one key (REP-CLOSED-SET -> enum),
raw copies of a value that already has a named constant, and MyBatis mapper
issues (`${}` substitution, map results, unguarded <foreach>, nested selects,
ordinal enum handlers, duplicated SQL). Also flags Python SQL f-strings and
JPA enums persisted by ordinal.

Counts are leads for the reviewer, not verdicts. Standard library only (3.8+).

Usage (same modes as scan_names.py):
  scan_literals.py                        # branch vs auto-detected base (+ uncommitted + untracked)
  scan_literals.py --base origin/develop
  scan_literals.py --staged
  scan_literals.py --files src/a.java src/mapper/RefundMapper.xml
  scan_literals.py --diff-file change.patch
  scan_literals.py --min-occurrences 2 --format json --fail-on medium
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_names import (  # noqa: E402  (same folder)
    GENERATED_PATH_RE, LANG_BY_EXT, RULES_PATH, TEST_PATH_RE, ScanError, detect_base, in_git_work_tree, is_tool_folder,
    iter_diff, optional_head, resolve_ref, run_git,
)

EXTRA_EXT = {".xml": "xml", ".sql": "sql"}
C_LIKE = {"java", "kotlin", "csharp", "go", "rust", "swift", "ts", "js"}
SINGLE_QUOTE_STRINGS = {"python", "ts", "js", "sql", "xml"}
CONF_ORDER = {"low": 0, "medium": 1, "high": 2}
CODE_LIKE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_./:-]{0,40}$")
STATE_KEYS = {"status", "state", "type", "kind", "mode", "role", "level", "category", "channel", "method", "scheme", "currency", "country", "provider", "action", "event", "code"}
CONTEXT_BEFORE_RE = re.compile(r"([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)*)\s*(?:===?|!==?|=|:|->|\bin\s*\(|\.equals(?:IgnoreCase)?\(|\.contains\(|\.containsKey\(|\.put\(|\.get\(|\.getOrDefault\(|\.header\(|\.getHeader\(|\.getProperty\(|\.set\(|\()\s*$")
CONTEXT_AFTER_RE = re.compile(r"^\s*\.equals(?:IgnoreCase)?\(\s*([A-Za-z_][\w.]*)")
CASE_RE = re.compile(r"\b(?:case|when)\s*$")
NUMBER_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
CONST_DEF_RES = {
    "c": re.compile(r"\b(?:static\s+final|final\s+static|const\s+val|const|val|let|var|readonly|static)\b[^=]*?\b([A-Z][A-Z0-9_]{1,})\s*(?::[^=]+)?=\s*$"),
    "python": re.compile(r"^([A-Z][A-Z0-9_]{1,})\s*(?::\s*[\w\[\], .]+)?\s*=\s*$"),
}
MAPPER_MARKERS = ("<mapper", "mybatis-3-mapper.dtd", "org.apache.ibatis")
STATEMENT_RE = re.compile(r"<(select|insert|update|delete)\b[^>]*>(.*?)</\1>", re.S | re.I)
SELECT_LIST_RE = re.compile(r"\bselect\s+(.*?)\s+from\b", re.S | re.I)


@dataclass
class Occurrence:
    file: str
    line: int
    added: bool
    context: str = ""


@dataclass
class Finding:
    rule: str
    confidence: str
    literal: str
    count: int
    locations: List[Dict[str, object]]
    note: str
    context_key: str = ""


@dataclass
class FileText:
    path: str
    lang: str
    lines: List[str]
    added: Set[int]          # new-side line numbers that are part of the change
    is_test: bool = False


# ----------------------------------------------------------------------------
# Rules
# ----------------------------------------------------------------------------

def load_literal_rules() -> dict:
    with open(RULES_PATH, encoding="utf-8") as fh:
        rules = json.load(fh).get("literals", {})
    rules.setdefault("min_occurrences", 3)
    rules.setdefault("min_string_length", 2)
    rules["_ignored_numbers"] = {str(n) for n in rules.get("ignored_numbers", [0, 1, -1, 2])}
    rules["_ignored_strings"] = set(rules.get("ignored_strings", []))
    rules.setdefault("closed_set_min_distinct", 2)
    rules["_message_prefixes"] = tuple(rules.get("message_call_prefixes", []))
    return rules


# ----------------------------------------------------------------------------
# Input collection (which files, which lines are "added")
# ----------------------------------------------------------------------------

def language_of(path: str) -> Optional[str]:
    suffix = Path(path).suffix
    return LANG_BY_EXT.get(suffix) or EXTRA_EXT.get(suffix)


def read_file(path: str) -> Optional[List[str]]:
    try:
        if os.path.getsize(path) > 1_000_000:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().split("\n")
    except OSError as exc:
        raise ScanError(f"cannot read {path!r}: {exc}") from exc


def staged_file(path: str) -> Optional[List[str]]:
    code, out = run_git(["show", ":" + path], allowed=(0, 128))
    return out.split("\n") if code == 0 else None


def files_from_diff(diff_text: str, reader) -> List[FileText]:
    """Group diff lines per file; load the full new-side text through `reader` when possible."""
    added: Dict[str, Set[int]] = defaultdict(set)
    diff_lines: Dict[str, Dict[int, str]] = defaultdict(dict)
    for path, line_no, text, is_added in iter_diff(diff_text):
        diff_lines[path][line_no] = text
        if is_added:
            added[path].add(line_no)
    out: List[FileText] = []
    for path, numbered in diff_lines.items():
        lang = language_of(path)
        if not lang:
            continue
        full = reader(path)
        if full is None:
            # fall back to the diff's own lines (context + added), keeping their line numbers
            size = max(numbered) if numbered else 0
            full = [numbered.get(i, "") for i in range(1, size + 1)]
        out.append(FileText(path.replace(os.sep, "/"), lang, full, added[path]))
    return out


def whole_files(paths: Iterable[str]) -> List[FileText]:
    out: List[FileText] = []
    for p in paths:
        lang = language_of(p)
        if not lang:
            continue
        lines = read_file(p)
        if lines is None:
            continue
        out.append(FileText(p.replace(os.sep, "/"), lang, lines, set(range(1, len(lines) + 1))))
    return out


def collect_input(args: argparse.Namespace) -> List[FileText]:
    if args.files:
        return whole_files(args.files)
    if args.diff_file:
        text = sys.stdin.read() if args.diff_file == "-" else Path(args.diff_file).read_text(encoding="utf-8", errors="surrogateescape")
        return files_from_diff(text, lambda p: read_file(p) if os.path.isfile(p) else None)
    if not in_git_work_tree():
        raise ScanError("not a git work tree (or git missing). Use --files or --diff-file.")
    diff_options = ["--unified=3", "--no-color", "--no-ext-diff", "--no-textconv", "--src-prefix=a/", "--dst-prefix=b/"]
    if args.staged:
        _, diff = run_git(["diff", "--cached", *diff_options, "--"])
        return files_from_diff(diff, staged_file)
    if args.base is not None:
        base = resolve_ref(args.base)
        _, mb = run_git(["merge-base", "HEAD", base])
        base = mb.strip()
    else:
        base = detect_base() or optional_head() or resolve_ref("HEAD")
    _, diff = run_git(["diff", base, *diff_options, "--"])
    files = files_from_diff(diff, lambda p: read_file(p) if os.path.isfile(p) else None)
    if not args.no_untracked:
        _, untracked = run_git(["ls-files", "-z", "--others", "--exclude-standard"])
        files.extend(whole_files(f for f in untracked.split("\0") if f and language_of(f)))
    print(f"scope: git diff {base[:12]} (+ uncommitted{'' if args.no_untracked else ' + untracked'})", file=sys.stderr)
    return files


# ----------------------------------------------------------------------------
# Tokenizing: string literals, numbers, comment stripping
# ----------------------------------------------------------------------------

@dataclass
class LineTokens:
    code: str                              # the line with string contents blanked out
    strings: List[Tuple[int, str]] = field(default_factory=list)   # (column, value)


def tokenize(line: str, lang: str, state: dict) -> LineTokens:
    """Extract string literals outside comments. `state` carries block-comment / triple-quote flags."""
    quotes = "\"'" if lang in SINGLE_QUOTE_STRINGS else '"'
    if lang in ("js", "ts"):
        quotes += "`"
    out_code: List[str] = []
    strings: List[Tuple[int, str]] = []
    i, n = 0, len(line)
    if state.get("triple"):
        if '"""' in line or "'''" in line:
            state["triple"] = False
        return LineTokens("")
    while i < n:
        ch = line[i]
        if state.get("block"):
            end = line.find("*/", i)
            if end < 0:
                return LineTokens("".join(out_code))
            state["block"] = False
            i = end + 2
            continue
        if lang in C_LIKE or lang == "sql" or lang == "xml":
            if line.startswith("/*", i) and lang != "xml":
                state["block"] = True
                i += 2
                continue
            if line.startswith("//", i) and lang != "sql":
                break
            if lang in ("sql", "xml") and line.startswith("--", i):
                break
            if lang == "xml" and line.startswith("<!--", i):
                end = line.find("-->", i)
                if end < 0:
                    return LineTokens("".join(out_code))
                i = end + 3
                continue
        elif lang == "python" and ch == "#":
            break
        if lang in ("python", "kotlin", "swift", "java", "rust") and line.startswith(('"""', "'''"), i):
            state["triple"] = True
            return LineTokens("".join(out_code))
        if ch in quotes:
            if lang in ("java", "kotlin", "csharp", "go", "rust", "swift") and ch == "'":
                out_code.append(ch)
                i += 1
                continue
            j = i + 1
            buf: List[str] = []
            while j < n and line[j] != ch:
                if line[j] == "\\" and j + 1 < n:
                    buf.append(line[j:j + 2])
                    j += 2
                    continue
                buf.append(line[j])
                j += 1
            value = "".join(buf)
            if j >= n:          # unterminated on this line (multi-line string); ignore
                out_code.append(ch)
                return LineTokens("".join(out_code), strings)
            if not (ch == "`" and "${" in value):
                strings.append((i, value))
            out_code.append(ch + " " * len(value) + ch)
            i = j + 1
            continue
        out_code.append(ch)
        i += 1
    return LineTokens("".join(out_code), strings)


def is_message_context(code_before: str, prefixes: Tuple[str, ...]) -> bool:
    tail = code_before[-160:]
    return any(p in tail for p in prefixes)


def context_key(code: str, col: int, length: int) -> str:
    before = code[:col]
    after = code[col + length + 2:]
    m = CONTEXT_AFTER_RE.match(after)
    if m:
        return m.group(1).split(".")[-1]
    if CASE_RE.search(before):
        return "case"
    m = CONTEXT_BEFORE_RE.search(before)
    if not m:
        return ""
    key = m.group(1).split(".")[-1]
    return key if key not in ("this", "self", "it", "new") else ""


# ----------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------

class Analyzer:
    def __init__(self, rules: dict, include_tests: bool) -> None:
        self.rules = rules
        self.include_tests = include_tests
        self.strings: Dict[str, List[Occurrence]] = defaultdict(list)
        self.numbers: Dict[str, List[Occurrence]] = defaultdict(list)
        self.constants: Dict[str, Tuple[str, str, int]] = {}      # literal -> (NAME, file, line)
        self.by_key: Dict[str, Dict[str, List[Occurrence]]] = defaultdict(lambda: defaultdict(list))
        self.findings: List[Finding] = []
        self.sql_literals: Dict[str, List[Occurrence]] = defaultdict(list)
        self.statement_bodies: Dict[str, List[Occurrence]] = defaultdict(list)
        self.select_lists: Dict[str, List[Occurrence]] = defaultdict(list)

    # -- entry -----------------------------------------------------------------
    def analyse(self, f: FileText) -> None:
        if GENERATED_PATH_RE.search(f.path) or is_tool_folder(f.path):
            return
        f.is_test = bool(TEST_PATH_RE.search(f.path))
        if f.is_test and not self.include_tests:
            return
        text = "\n".join(f.lines)
        if f.lang == "xml":
            if any(m in text for m in MAPPER_MARKERS):
                self.analyse_mapper(f, text)
            return
        if f.lang == "sql":
            self.analyse_sql_lines(f)
            return
        self.analyse_code(f, text)

    # -- general code ---------------------------------------------------------------
    def analyse_code(self, f: FileText, text: str) -> None:
        state: dict = {}
        mybatis_java = "org.apache.ibatis" in text
        for no, raw in enumerate(f.lines, start=1):
            s = raw.strip()
            if not s or s.startswith(("import ", "package ", "from ", "using ", "#include", "@file:")):
                continue
            tok = tokenize(raw, f.lang, state)
            if not tok.code.strip():
                continue
            added = no in f.added
            const_name = self.constant_definition(tok.code, f.lang)
            for col, value in tok.strings:
                if len(value) < self.rules["min_string_length"] or value in self.rules["_ignored_strings"]:
                    continue
                if value.count(" ") >= 3 or value.strip() == "":
                    continue                     # sentences are messages, not keys
                if is_message_context(tok.code[:col], self.rules["_message_prefixes"]):
                    continue
                if mybatis_java and "${" in value and added:
                    self.add("MYB-SUBSTITUTION", "high", value, [Occurrence(f.path, no, True)],
                             "`${}` string substitution in a MyBatis statement: injectable unless the value is a server-side constant. Use `#{}` or an allow-list (SEC-INJECTION).")
                if const_name:
                    self.constants.setdefault(value, (const_name, f.path, no))
                occ = Occurrence(f.path, no, added, context_key(tok.code, col, len(value)))
                self.strings[value].append(occ)
                if occ.context and CODE_LIKE_RE.match(value):
                    self.by_key[occ.context][value].append(occ)
            if not const_name:
                for m in NUMBER_RE.finditer(tok.code):
                    num = m.group(0)
                    if num in self.rules["_ignored_numbers"] or num.lstrip("-").startswith("0") and len(num.lstrip("-")) > 1:
                        continue
                    if is_message_context(tok.code[:m.start()], self.rules["_message_prefixes"]):
                        continue
                    self.numbers[num].append(Occurrence(f.path, no, added, context_key(tok.code, m.start(), len(num) - 2)))
            # framework one-liners
            if added and f.lang in ("java", "kotlin"):
                if "@Enumerated" in s and "STRING" not in s and "EnumType" not in s.replace("@Enumerated", ""):
                    self.add("JPA-ENUM-STRING", "medium", s[:60], [Occurrence(f.path, no, True)],
                             "`@Enumerated` without `EnumType.STRING` persists the ordinal; reordering the enum corrupts data. Use STRING or an AttributeConverter with an explicit code.")
                if "EnumOrdinalTypeHandler" in s:
                    self.add("MYB-ENUM-ORDINAL", "medium", "EnumOrdinalTypeHandler", [Occurrence(f.path, no, True)],
                             "Ordinal enum persistence; use a name- or code-based TypeHandler.")
            if added and f.lang == "python" and re.search(r"\b(execute|executemany|text|raw)\s*\(\s*(f[\"']|[\"'][^\"']*[\"']\s*%|[\"'][^\"']*[\"']\s*\+|.*\.format\()", s):
                self.add("PY-SQL-FSTRING", "high", s[:60], [Occurrence(f.path, no, True)],
                         "SQL assembled with f-string/format/concatenation; bind parameters instead (SEC-INJECTION).")

    def constant_definition(self, code: str, lang: str) -> Optional[str]:
        head = code.rstrip()
        # the literal was blanked; the definition is everything up to the first quote/number
        m = re.match(r"^(.*?[=:]\s*)(?=[\"'`]|-?\d)", head)
        if not m:
            return None
        prefix = m.group(1)
        rx = CONST_DEF_RES["python" if lang == "python" else "c"]
        dm = rx.search(prefix) if lang != "python" else rx.match(prefix)
        return dm.group(1) if dm else None

    # -- MyBatis mapper XML ----------------------------------------------------------
    def analyse_mapper(self, f: FileText, text: str) -> None:
        state: dict = {}
        for no, raw in enumerate(f.lines, start=1):
            added = no in f.added
            tok = tokenize(raw, "xml", state)
            code = tok.code
            if added and "${" in raw:
                self.add("MYB-SUBSTITUTION", "high", raw.strip()[:70], [Occurrence(f.path, no, True)],
                         "`${}` string substitution: injectable unless the value is a server-side constant or allow-listed. Use `#{}`; map dynamic columns/order through a fixed allow-list (SEC-INJECTION).")
            if added and re.search(r"resultType\s*=\s*\"(?:java\.util\.)?(?:Map|HashMap|map|hashmap)\"", raw):
                self.add("MYB-RESULT-MAP", "medium", raw.strip()[:70], [Occurrence(f.path, no, True)],
                         "Untyped map result; return a typed row class/record or an explicit <resultMap> (MODEL-RECORD).")
            if added and "<foreach" in raw:
                window = " ".join(f.lines[max(0, no - 4):no - 1])
                if not re.search(r"<if\s+test=\"[^\"]*(size|isEmpty|empty|length)", window):
                    self.add("MYB-FOREACH-EMPTY", "low", raw.strip()[:70], [Occurrence(f.path, no, True)],
                             "`IN (<foreach>)` without an empty-collection guard produces invalid SQL (`IN ()`); wrap in `<if test=\"ids != null and !ids.isEmpty()\">` or reject empty input upstream.")
            if added and re.search(r"<(collection|association)\b[^>]*\bselect\s*=", raw):
                self.add("MYB-NPLUS1", "low", raw.strip()[:70], [Occurrence(f.path, no, True)],
                         "Nested select runs one query per parent row; prefer a join with a nested <resultMap> or a batched query (PERF-NPLUS1).")
            if added and "EnumOrdinalTypeHandler" in raw:
                self.add("MYB-ENUM-ORDINAL", "medium", "EnumOrdinalTypeHandler", [Occurrence(f.path, no, True)],
                         "Ordinal enum persistence; use a name- or code-based TypeHandler.")
            # SQL string literals in statement bodies (not #{} bindings)
            for col, value in tok.strings:
                if raw.lstrip().startswith("<") and "=" in raw[:col]:      # attribute value, not SQL
                    continue
                if len(value) < self.rules["min_string_length"] or value in self.rules["_ignored_strings"] or " " in value.strip():
                    continue
                key = ""
                m = re.search(r"([A-Za-z_][\w.]*)\s*(?:=|<>|!=|\bin\s*\(|\blike)\s*$", code[:col], re.I)
                if m:
                    key = m.group(1).split(".")[-1].lower()
                occ = Occurrence(f.path, no, added, key)
                self.sql_literals[value].append(occ)
                if key:
                    self.by_key["sql:" + key][value].append(occ)
        # duplicated statement bodies and column lists across mappers
        for m in STATEMENT_RE.finditer(text):
            body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip().lower()
            line = text.count("\n", 0, m.start()) + 1
            if len(body) > 40:
                self.statement_bodies[body].append(Occurrence(f.path, line, any(line <= a <= line + m.group(0).count("\n") for a in f.added)))
            sm = SELECT_LIST_RE.search(body)
            if sm and len(sm.group(1)) > 30 and "*" not in sm.group(1):
                self.select_lists[sm.group(1)].append(Occurrence(f.path, line, any(line <= a <= line + m.group(0).count("\n") for a in f.added)))

    def analyse_sql_lines(self, f: FileText) -> None:
        state: dict = {}
        for no, raw in enumerate(f.lines, start=1):
            tok = tokenize(raw, "sql", state)
            for col, value in tok.strings:
                if len(value) < self.rules["min_string_length"] or " " in value.strip():
                    continue
                m = re.search(r"([A-Za-z_][\w.]*)\s*(?:=|<>|!=|\bin\s*\(|\blike)\s*$", tok.code[:col], re.I)
                key = m.group(1).split(".")[-1].lower() if m else ""
                occ = Occurrence(f.path, no, no in f.added, key)
                self.sql_literals[value].append(occ)
                if key:
                    self.by_key["sql:" + key][value].append(occ)

    # -- aggregation --------------------------------------------------------------------
    def add(self, rule: str, conf: str, literal: str, occs: List[Occurrence], note: str, key: str = "") -> None:
        locs = [{"file": o.file, "line": o.line, "added": o.added} for o in occs]
        self.findings.append(Finding(rule, conf, literal, len(occs), locs, note, key))

    def finalize(self) -> List[Finding]:
        minimum = int(self.rules["min_occurrences"])
        reported: Set[str] = set()
        # closed sets first (they explain the repeated strings they contain)
        for key, values in self.by_key.items():
            distinct = {v: o for v, o in values.items() if len(o) >= 1}
            if len(distinct) < int(self.rules["closed_set_min_distinct"]):
                continue
            occs = [o for v in distinct.values() for o in v]
            if not any(o.added for o in occs):
                continue
            bare = key.split(":")[-1]
            conf = "high" if (len(distinct) >= 3 or bare in STATE_KEYS) else "medium"
            rule = "MYB-LITERAL" if key.startswith("sql:") else "REP-CLOSED-SET"
            self.add(rule, conf, " | ".join(sorted(distinct)), sorted(occs, key=lambda o: (o.file, o.line)),
                     f"{len(distinct)} distinct values under `{bare}` form a closed set; model them as an enum (Java enum with code + fromCode, Python Enum/StrEnum, TS union) and persist by name/code. Unknown values must fail fast, not fall through.", key)
            reported.update(distinct)
        # raw copies of a named constant
        for value, (name, cfile, cline) in self.constants.items():
            raw_uses = [o for o in self.strings.get(value, []) if not (o.file == cfile and o.line == cline)]
            if raw_uses and any(o.added for o in raw_uses):
                self.add("REP-STRING", "high", value, raw_uses,
                         f"Raw copy of a value already named `{name}` ({cfile}:{cline}); use the constant.")
                reported.add(value)
        for value, occs in self.strings.items():
            if value in reported or len(occs) < minimum or not any(o.added for o in occs):
                continue
            files = {o.file for o in occs}
            conf = "medium" if CODE_LIKE_RE.match(value) else "low"
            self.add("REP-STRING", conf, value, sorted(occs, key=lambda o: (o.file, o.line)),
                     f"Repeated {len(occs)}× across {len(files)} file(s); one named constant (or an enum if it belongs to a set) owned by the concept's type.")
        for value, occs in self.sql_literals.items():
            if value in reported or len(occs) < minimum or not any(o.added for o in occs):
                continue
            self.add("MYB-LITERAL", "medium", value, sorted(occs, key=lambda o: (o.file, o.line)),
                     f"Hard-coded SQL value repeated {len(occs)}×; bind it (`#{{}}`) from an enum via a TypeHandler, or isolate it in one `<sql id>` fragment.")
        for num, occs in self.numbers.items():
            if len(occs) < minimum or not any(o.added for o in occs):
                continue
            self.add("REP-NUMBER", "low", num, sorted(occs, key=lambda o: (o.file, o.line)),
                     f"Magic number repeated {len(occs)}×; name it with its unit/meaning, or make it configuration if operators tune it.")
        for body, occs in self.statement_bodies.items():
            if len(occs) >= 2 and any(o.added for o in occs):
                self.add("MYB-DUPLICATE-SQL", "low", body[:60] + "…", occs, "Identical statement body in several places; keep one statement.")
        for cols, occs in self.select_lists.items():
            if len(occs) >= 2 and any(o.added for o in occs):
                self.add("MYB-FRAGMENT", "low", cols[:60] + "…", occs, "Same column list in several statements; extract `<sql id>` + `<include>`.")
        order = {"high": 0, "medium": 1, "low": 2}
        self.findings.sort(key=lambda f: (order[f.confidence], f.rule, f.literal))
        return self.findings


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------

def fmt_locations(locs: List[Dict[str, object]], limit: int = 4) -> str:
    shown = ", ".join(f"`{l['file']}:{l['line']}`" for l in locs[:limit])
    return shown + (f" +{len(locs) - limit} more" if len(locs) > limit else "")


def render_markdown(findings: List[Finding], min_conf: str) -> str:
    shown = [f for f in findings if CONF_ORDER[f.confidence] >= CONF_ORDER[min_conf]]
    if not shown:
        return "No repeated-literal or mapper leads on the changed files (at or above confidence '%s')." % min_conf
    lines = [
        f"Literal/data-modelling leads: {len(shown)}. Each needs the owner type and concrete drift risk before it becomes a finding "
        "(references/literals-and-data-carriers.md).",
        "",
        "| Conf | Rule | Literal / pattern | Count | Locations | Note |",
        "|---|---|---|---|---|---|",
    ]
    for f in shown:
        lit = f.literal.replace("|", "\\|").replace("`", "'")
        note = f.note.replace("|", "\\|")
        lines.append(f"| {f.confidence} | {f.rule} | `{lit[:80]}` | {f.count} | {fmt_locations(f.locations)} | {note} |")
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
    ap.add_argument("--min-occurrences", type=int, help="Repetitions needed for a lead (default from assets/naming-rules.json → literals).")
    ap.add_argument("--min-confidence", choices=["low", "medium", "high"], default="low")
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown")
    ap.add_argument("--fail-on", choices=["low", "medium", "high"], help="Exit 1 if any lead at/above this confidence.")
    args = ap.parse_args(argv)
    try:
        rules = load_literal_rules()
        if args.min_occurrences:
            rules["min_occurrences"] = max(1, args.min_occurrences)
        analyzer = Analyzer(rules, args.include_tests)
        for f in collect_input(args):
            analyzer.analyse(f)
        findings = analyzer.finalize()
    except (ScanError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    shown = [f for f in findings if CONF_ORDER[f.confidence] >= CONF_ORDER[args.min_confidence]]
    if args.format == "json":
        print(json.dumps({"findings": [asdict(f) for f in shown]}, indent=2))
    else:
        print(render_markdown(findings, args.min_confidence))
    if args.fail_on and any(CONF_ORDER[f.confidence] >= CONF_ORDER[args.fail_on] for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
