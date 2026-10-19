#!/usr/bin/env python3
"""Convention Profile generator for the code-quality-review skill.

Reads the repository (git ls-files, or a directory walk) and prints a DRAFT
Convention Profile: what this codebase already does for naming, packaging,
modules, exceptions, logging, nullability, dependency injection, validation,
immutability, transactions, HTTP APIs, tests, documentation and formatting.

The reviewer confirms the draft against documented rules and neighbouring
files, then records it under "Conventions applied" in the review report
(see references/repo-conventions.md). Standard library only (Python 3.8+).

Java and Kotlin are profiled in depth; C#, TypeScript/JavaScript, Python, Go,
Rust and Swift get the language-neutral parts (type suffixes, verbs, tests,
logging and test libraries).

Usage:
  scan_conventions.py                      # whole repository (current directory)
  scan_conventions.py --root services/billing
  scan_conventions.py --format json
  scan_conventions.py --max-files 3000 --include-tests
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_names import (  # noqa: E402  (same folder)
    GENERATED_PATH_RE, LANG_BY_EXT, TEST_PATH_RE, FileContext, extract_method, extract_type, is_comment, split_words,
)

BUILD_FILES = {
    "pom.xml": "maven", "build.gradle": "gradle", "build.gradle.kts": "gradle-kotlin",
    "settings.gradle": "gradle", "settings.gradle.kts": "gradle-kotlin",
    "package.json": "npm", "go.mod": "go", "Cargo.toml": "cargo", "pyproject.toml": "python",
    "setup.py": "python", "requirements.txt": "python", "Package.swift": "swiftpm",
}
CONFIG_PATTERNS = {
    "checkstyle": re.compile(r"checkstyle[^/]*\.xml$"),
    "pmd": re.compile(r"(^|/)pmd[^/]*\.xml$|(^|/)ruleset[^/]*\.xml$"),
    "editorconfig": re.compile(r"(^|/)\.editorconfig$"),
    "eslint": re.compile(r"(^|/)(\.eslintrc[^/]*|eslint\.config\.[cm]?[jt]s)$"),
    "prettier": re.compile(r"(^|/)\.prettierrc[^/]*$|(^|/)prettier\.config\.[cm]?js$"),
    "ruff": re.compile(r"(^|/)ruff\.toml$"),
    "golangci": re.compile(r"(^|/)\.golangci\.ya?ml$"),
    "detekt": re.compile(r"(^|/)detekt[^/]*\.ya?ml$"),
    "ktlint": re.compile(r"(^|/)\.ktlint[^/]*$"),
    "pre-commit": re.compile(r"(^|/)\.pre-commit-config\.ya?ml$"),
    "archunit": re.compile(r"Arch(itecture)?(Rules?|Test|Tests)\.(java|kt)$"),
    "adr": re.compile(r"(^|/)docs?/adrs?/"),
    "contributing": re.compile(r"(^|/)CONTRIBUTING\.md$", re.I),
    "agents-md": re.compile(r"(^|/)(AGENTS|CLAUDE|REVIEW)\.md$"),
    "review-overrides": re.compile(r"(^|/)\.agents/review-overrides\.md$"),
    "sonar": re.compile(r"(^|/)sonar-project\.properties$"),
}
APP_CONFIG_RE = re.compile(r"(^|/)(application|bootstrap)[^/]*\.(properties|ya?ml)$")
SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", "out", "vendor", ".gradle", ".idea", ".vscode", "__pycache__", ".venv", "venv", ".mvn", "bin", "obj"}

LAYER_WORDS = {
    "controller", "controllers", "web", "rest", "api", "service", "services", "repository", "repositories", "repo", "dao",
    "persistence", "infrastructure", "infra", "domain", "model", "models", "entity", "entities", "dto", "dtos", "mapper",
    "mappers", "config", "configuration", "util", "utils", "exception", "exceptions", "application", "usecase",
    "usecases", "adapter", "adapters", "port", "ports", "client", "clients", "event", "events", "messaging",
    "validation", "handler", "handlers", "resource", "resources", "endpoint", "endpoints", "facade",
    "scheduler", "job", "jobs", "batch",
}  # 'common', 'shared', 'core', 'internal', 'impl', 'support', 'security', 'integration' are neutral (used by both layouts)
HEX_WORDS = {"domain", "application", "infrastructure", "adapter", "adapters", "port", "ports"}
READ_VERBS = ["get", "find", "fetch", "load", "retrieve", "query", "search", "lookup", "read", "obtain", "resolve", "determine"]
DTO_SUFFIXES = ["Dto", "DTO", "Request", "Response", "Payload", "Resource", "Representation", "View", "Projection", "Command", "Query", "Event", "Model"]
TEST_CLASS_SUFFIX_RE = re.compile(r"(Tests|Test|IT|Spec|TestCase|Specification)$")
UNCHECKED_BASES = {"RuntimeException", "IllegalArgumentException", "IllegalStateException", "UnsupportedOperationException",
                   "NestedRuntimeException", "DataAccessException", "ResponseStatusException", "Error", "AssertionError"}
CHECKED_BASES = {"Exception", "IOException", "SQLException", "TimeoutException", "InterruptedException", "GeneralSecurityException"}

LOG_IMPORTS = {
    "org.slf4j": "SLF4J", "lombok.extern.slf4j.Slf4j": "SLF4J (Lombok @Slf4j)", "org.apache.logging.log4j": "Log4j2 API",
    "lombok.extern.log4j.Log4j2": "Log4j2 (Lombok)", "java.util.logging": "JUL", "org.apache.commons.logging": "commons-logging",
    "io.github.oshai.kotlinlogging": "kotlin-logging", "mu.KotlinLogging": "kotlin-logging (mu)", "ch.qos.logback": "Logback (direct)",
    "org.jboss.logging": "JBoss Logging", "io.micronaut.logging": "Micronaut logging",
    # other languages
    "winston": "winston", "pino": "pino", "bunyan": "bunyan", "loguru": "loguru", "structlog": "structlog",
    "import logging": "python logging", "go.uber.org/zap": "zap", "github.com/sirupsen/logrus": "logrus",
    "github.com/rs/zerolog": "zerolog", "log/slog": "slog", "Microsoft.Extensions.Logging": "MS.Extensions.Logging",
    "Serilog": "Serilog", "NLog": "NLog", "os.log": "os.log (Swift)", "tracing": "tracing (Rust)", "log::": "log (Rust)",
}
NULL_IMPORTS = {
    "org.jspecify": "JSpecify", "javax.annotation.Nullable": "JSR-305", "javax.annotation.Nonnull": "JSR-305",
    "jakarta.annotation.Nullable": "Jakarta annotations", "org.springframework.lang.Nullable": "Spring @Nullable",
    "org.springframework.lang.NonNull": "Spring @NonNull", "org.checkerframework": "Checker Framework",
    "org.jetbrains.annotations": "JetBrains annotations", "androidx.annotation": "AndroidX annotations",
    "edu.umd.cs.findbugs.annotations": "SpotBugs annotations",
}
TEST_IMPORTS = {
    "org.junit.jupiter": "JUnit 5", "org.junit.Test": "JUnit 4", "org.assertj": "AssertJ", "org.hamcrest": "Hamcrest",
    "com.google.common.truth": "Truth", "org.mockito": "Mockito", "io.mockk": "MockK", "org.testcontainers": "Testcontainers",
    "spock.lang": "Spock", "io.kotest": "Kotest", "org.springframework.boot.test": "Spring Boot Test", "io.rest-assured": "REST Assured",
    "org.wiremock": "WireMock", "com.github.tomakehurst.wiremock": "WireMock", "com.tngtech.archunit": "ArchUnit",
    "org.junit.jupiter.params": "JUnit 5 params", "org.jqwik": "jqwik",
    "@jest/globals": "Jest", "vitest": "Vitest", "mocha": "Mocha", "chai": "Chai", "@testing-library": "Testing Library",
    "import pytest": "pytest", "import unittest": "unittest", "from unittest": "unittest", "hypothesis": "Hypothesis",
    "github.com/stretchr/testify": "testify", "Xunit": "xUnit", "NUnit": "NUnit", "Microsoft.VisualStudio.TestTools": "MSTest",
    "FluentAssertions": "FluentAssertions", "Moq": "Moq", "NSubstitute": "NSubstitute", "XCTest": "XCTest",
}
LIB_MARKERS = {  # build-file or import markers → library label
    "spring-boot": "Spring Boot", "org.springframework.boot": "Spring Boot", "org.springframework": "Spring Framework",
    "spring-modulith": "Spring Modulith", "jakarta.persistence": "JPA (Jakarta)", "javax.persistence": "JPA (javax)",
    "org.hibernate": "Hibernate", "org.jooq": "jOOQ", "mybatis": "MyBatis", "spring-data": "Spring Data", "lombok": "Lombok",
    "mapstruct": "MapStruct", "org.modelmapper": "ModelMapper", "micronaut": "Micronaut", "quarkus": "Quarkus",
    "jakarta.validation": "Bean Validation (Jakarta)", "javax.validation": "Bean Validation (javax)",
    "resilience4j": "Resilience4j", "openfeign": "Feign", "spring-webflux": "WebFlux", "reactor": "Reactor",
    "kotlinx.coroutines": "Kotlin coroutines", "com.fasterxml.jackson": "Jackson", "com.google.gson": "Gson",
    "com.google.guava": "Guava", "org.apache.commons": "Apache Commons", "shedlock": "ShedLock", "flyway": "Flyway",
    "liquibase": "Liquibase", "springdoc": "springdoc-openapi", "io.swagger": "Swagger", "errorprone": "Error Prone",
    "spotless": "Spotless", "checkstyle": "Checkstyle", "pmd": "PMD", "jacoco": "JaCoCo", "sonarqube": "Sonar",
    "detekt": "detekt", "ktlint": "ktlint", "archunit": "ArchUnit", "jspecify": "JSpecify",
    "nestjs": "NestJS", "express": "Express", "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "gin-gonic": "Gin", "actix": "Actix", "axum": "Axum", "Microsoft.AspNetCore": "ASP.NET Core",
}
HTTP_CLIENTS = ["RestTemplate", "RestClient", "WebClient", "FeignClient", "OkHttpClient", "java.net.http.HttpClient", "HttpClient", "Retrofit", "axios", "fetch(", "requests.", "httpx", "net/http"]
JAVA_LIKE = {"java", "kotlin"}


# ----------------------------------------------------------------------------
# File collection
# ----------------------------------------------------------------------------

def run_git(args: List[str], cwd: str) -> Tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, check=False, cwd=cwd)
        return p.returncode, p.stdout
    except FileNotFoundError:
        return 127, ""


def collect_files(root: str, max_files: int) -> Tuple[List[str], str]:
    """Return (relative paths, source) where source is 'git' or 'walk'."""
    code, out = run_git(["ls-files", "-z", "--", "."], root)
    if code == 0:
        files = [f for f in out.split("\0") if f]
        return files[:max_files * 4], "git"
    files: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/")
            files.append(rel)
            if len(files) >= max_files * 4:
                return files, "walk"
    return files, "walk"


def read_text(path: str, limit: int = 512_000) -> Optional[str]:
    try:
        if os.path.getsize(path) > limit:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


# ----------------------------------------------------------------------------
# Profile accumulator
# ----------------------------------------------------------------------------

class Profile:
    def __init__(self) -> None:
        self.languages: Counter = Counter()
        self.build_tools: Counter = Counter()
        self.build_files: List[str] = []
        self.java_baseline: Counter = Counter()
        self.kotlin_version: Counter = Counter()
        self.modules: List[str] = []
        self.libraries: Counter = Counter()
        self.configs: Dict[str, List[str]] = defaultdict(list)
        self.app_config: Dict[str, str] = {}
        self.main_files = 0
        self.test_files = 0
        self.packages_main: Counter = Counter()
        self.packages_test: Counter = Counter()
        self.type_suffix: Counter = Counter()
        self.type_kinds: Counter = Counter()
        self.impl_types: List[str] = []
        self.iprefix_interfaces = 0
        self.interfaces = 0
        self.test_class_suffix: Counter = Counter()
        self.dto_suffix: Counter = Counter()
        self.method_verbs: Counter = Counter()
        self.read_verbs: Counter = Counter()
        self.vague_verbs: Counter = Counter()
        self.test_method_style: Counter = Counter()
        self.exception_bases: Counter = Counter()
        self.exception_types: Dict[str, str] = {}
        self.raw_throws: Counter = Counter()
        self.broad_catches: Counter = Counter()
        self.print_stack = 0
        self.error_handlers: Counter = Counter()
        self.error_code_enums = 0
        self.log_facades: Counter = Counter()
        self.logger_decls: Counter = Counter()
        self.log_styles: Counter = Counter()
        self.sysout = 0
        self.mdc = 0
        self.null_annotations: Counter = Counter()
        self.null_marked = 0
        self.optional_usage: Counter = Counter()
        self.di: Counter = Counter()
        self.validation: Counter = Counter()
        self.immutability: Counter = Counter()
        self.tx: Counter = Counter()
        self.api: Counter = Counter()
        self.path_styles: Counter = Counter()
        self.jpa: Counter = Counter()
        self.async_: Counter = Counter()
        self.http_clients: Counter = Counter()
        self.test_libs: Counter = Counter()
        self.test_kinds: Counter = Counter()
        self.javadoc_public = 0
        self.public_types = 0
        self.doc_tags: Counter = Counter()
        self.todo: Counter = Counter()
        self.wildcard_imports = 0
        self.this_prefix: Counter = Counter()
        self.files_scanned = 0
        self.files_skipped = 0


# ----------------------------------------------------------------------------
# Build and config files
# ----------------------------------------------------------------------------

def analyse_build_file(path: str, text: str, prof: Profile) -> None:
    name = os.path.basename(path)
    tool = BUILD_FILES.get(name)
    if tool:
        prof.build_tools[tool] += 1
        prof.build_files.append(path)
    low = text.lower()
    for marker, label in LIB_MARKERS.items():
        if marker.lower() in low:
            prof.libraries[label] += 1
    if name == "pom.xml":
        for tag in ("maven.compiler.release", "maven.compiler.source", "maven.compiler.target", "java.version", "release", "source"):
            for m in re.finditer(r"<%s>\s*(?:1\.)?(\d{1,2})\s*</%s>" % (re.escape(tag), re.escape(tag)), text):
                prof.java_baseline["Java " + m.group(1)] += 1
                break
        for m in re.finditer(r"<module>\s*([^<\s]+)\s*</module>", text):
            prof.modules.append(m.group(1))
        km = re.search(r"<kotlin\.version>\s*([\d.]+)", text)
        if km:
            prof.kotlin_version["Kotlin " + km.group(1)] += 1
    elif name.startswith(("build.gradle", "settings.gradle")):
        for rx in (r"JavaLanguageVersion\.of\(\s*(\d{1,2})\s*\)", r"jvmToolchain\(\s*(\d{1,2})\s*\)",
                   r"sourceCompatibility\s*=?\s*(?:JavaVersion\.VERSION_)?(?:1_|1\.)?(\d{1,2})",
                   r"options\.release(?:\.set)?\(?\s*=?\s*(\d{1,2})", r"\brelease\s*=\s*(\d{1,2})\b", r"jvmTarget\s*=\s*['\"]?(?:1\.)?(\d{1,2})"):
            m = re.search(rx, text)
            if m:
                prof.java_baseline["Java " + m.group(1)] += 1
                break
        km = re.search(r"kotlin\(\"jvm\"\)\s+version\s+\"([\d.]+)\"|org\.jetbrains\.kotlin\.jvm[\"']?\)?\s+version\s+[\"']([\d.]+)", text)
        if km:
            prof.kotlin_version["Kotlin " + (km.group(1) or km.group(2))] += 1
        if name.startswith("settings.gradle"):
            for m in re.finditer(r"include\s*\(?\s*([^)\n]+)", text):
                for part in re.findall(r"[\"']([^\"']+)[\"']", m.group(1)):
                    prof.modules.append(part.lstrip(":"))
    elif name == "package.json":
        try:
            data = json.loads(text)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for d in deps:
                for marker, label in LIB_MARKERS.items():
                    if marker in d:
                        prof.libraries[label] += 1
                for marker, label in TEST_IMPORTS.items():
                    if marker.strip("@") in d:
                        prof.test_libs[label] += 1
                for marker, label in LOG_IMPORTS.items():
                    if marker == d:
                        prof.log_facades[label] += 1
        except ValueError:
            pass


def analyse_app_config(path: str, text: str, prof: Profile) -> None:
    for key in ("spring.jpa.open-in-view", "open-in-view", "spring.jackson", "logging.pattern", "logging.level.root", "spring.mvc.problemdetails.enabled", "management.endpoints"):
        m = re.search(re.escape(key) + r"\s*[:=]\s*(\S+)", text)
        if m:
            prof.app_config.setdefault(key, m.group(1))
        elif key in text:
            prof.app_config.setdefault(key, "(present)")


# ----------------------------------------------------------------------------
# Source file analysis
# ----------------------------------------------------------------------------

LOGGER_DECL_RE = re.compile(r"^\s*((?:private|protected|public|internal)\s+)?(static\s+)?(final\s+)?(?:val\s+|var\s+)?(?:Logger|Log|KLogger|ILogger<[^>]*>|ILogger)\s+(\w+)\s*(?::\s*\w+)?\s*=")
KOTLIN_LOGGER_RE = re.compile(r"^\s*(private\s+)?(val)\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(?:KotlinLogging\.logger|LoggerFactory\.getLogger|getLogger)")
LOG_CALL_RE = re.compile(r"\b(log|logger|LOG|LOGGER|_log|_logger|mLogger)\.(trace|debug|info|warn|warning|error|fatal|severe|fine|atDebug|atInfo|atWarn|atError|atTrace)\s*\(")
METHOD_DECL_CONTEXT = 5


def analyse_source(path: str, text: str, lang: str, is_test: bool, prof: Profile) -> None:
    lines = text.splitlines()
    ctx = FileContext(path=path, lang=lang)
    imports = [ln for ln in lines[:400] if ln.lstrip().startswith(("import ", "from ", "using ", "require(", "const ", "use "))]
    joined_imports = "\n".join(imports)

    # --- libraries, logging, nullability, tests (by import) ---
    for marker, label in LOG_IMPORTS.items():
        if marker in joined_imports or (marker.startswith("import ") and marker in text[:4000]):
            prof.log_facades[label] += 1
    for marker, label in NULL_IMPORTS.items():
        if marker in joined_imports:
            prof.null_annotations[label] += 1
    for marker, label in TEST_IMPORTS.items():
        if marker in joined_imports or (marker.startswith(("import ", "from ")) and marker in text[:4000]):
            prof.test_libs[label] += 1
    for marker, label in LIB_MARKERS.items():
        if marker in joined_imports:
            prof.libraries[label] += 1
    if lang in JAVA_LIKE:
        prof.wildcard_imports += sum(1 for ln in imports if ln.rstrip().endswith(".*;") or ln.rstrip().endswith(".*"))
    if "@NullMarked" in text:
        prof.null_marked += 1

    # --- package ---
    pkg = None
    if lang in JAVA_LIKE:
        m = re.search(r"^\s*package\s+([\w.]+)", text, re.M)
        if m:
            pkg = m.group(1)
            (prof.packages_test if is_test else prof.packages_main)[pkg] += 1

    # --- per-line scan ---
    current_type: Optional[str] = None
    type_names_in_file: List[str] = []
    pending_annotations: List[str] = []
    prev_nonblank = ""
    in_constructor = False
    for i, raw in enumerate(lines):
        ln = raw.rstrip("\n")
        s = ln.strip()
        if not s:
            continue
        if is_comment(ln, lang):
            if "TODO" in s or "FIXME" in s:
                prof.todo["with ticket" if re.search(r"[A-Z]{2,}-\d+|#\d+", s) else "without ticket"] += 1
            if lang in JAVA_LIKE and s.startswith("*"):
                for tag in ("@since", "@author", "@param", "@return", "@throws", "@deprecated"):
                    if tag in s:
                        prof.doc_tags[tag] += 1
            prev_nonblank = s
            continue
        if s.startswith("@"):
            pending_annotations.append(s)
        tdecl = extract_type(ln, ctx)
        if tdecl:
            current_type = tdecl.name
            type_names_in_file.append(tdecl.name)
            anns = " ".join(pending_annotations)
            pending_annotations = []
            is_public = bool(re.search(r"\bpublic\b", ln)) or lang in ("go", "python", "kotlin")
            if is_test:
                m = TEST_CLASS_SUFFIX_RE.search(tdecl.name)
                prof.test_class_suffix[m.group(1) if m else "(no suffix)"] += 1
                for ann in ("@SpringBootTest", "@WebMvcTest", "@DataJpaTest", "@JsonTest", "@WebFluxTest", "@RestClientTest", "@ExtendWith(MockitoExtension", "@Testcontainers", "@MockitoBean", "@MockBean"):
                    if ann in anns or ann in text:
                        prof.test_kinds[ann.rstrip("(")] += 1
            else:
                prof.type_kinds[tdecl.keyword] += 1
                words = split_words(tdecl.name)
                if words:
                    prof.type_suffix[words[-1]] += 1
                if tdecl.name.endswith("Impl"):
                    prof.impl_types.append(tdecl.name)
                if tdecl.is_interface:
                    prof.interfaces += 1
                    if re.match(r"^I[A-Z][a-z]", tdecl.name):
                        prof.iprefix_interfaces += 1
                for suf in DTO_SUFFIXES:
                    if tdecl.name.endswith(suf) and len(tdecl.name) > len(suf):
                        prof.dto_suffix[suf] += 1
                if lang in JAVA_LIKE:
                    if is_public and not re.search(r"^\s+", ln):
                        prof.public_types += 1
                        if prev_nonblank.endswith("*/") or prev_nonblank.startswith("@") and any(l.strip().endswith("*/") for l in lines[max(0, i - 6):i]):
                            prof.javadoc_public += 1
                    if tdecl.keyword == "record":
                        prof.immutability["record"] += 1
                    elif tdecl.keyword == "class":
                        prof.immutability["final class" if re.search(r"\bfinal\s+class\b", ln) else ("abstract class" if "abstract" in ln else "class")] += 1
                    if lang == "kotlin" and re.search(r"\bdata\s+class\b", ln):
                        prof.immutability["data class"] += 1
                    for ann in ("@Data", "@Value", "@Builder", "@Getter", "@Setter", "@RequiredArgsConstructor", "@AllArgsConstructor", "@NoArgsConstructor"):
                        if ann in anns:
                            prof.immutability["Lombok " + ann] += 1
                    for ann in ("@RestController", "@Controller", "@Service", "@Repository", "@Component", "@Configuration", "@Entity", "@ControllerAdvice", "@RestControllerAdvice", "@ConfigurationProperties"):
                        if ann in anns:
                            (prof.error_handlers if "Advice" in ann else prof.api if ann in ("@RestController", "@Controller", "@ConfigurationProperties") else prof.jpa if ann == "@Entity" else prof.di)[ann] += 1
                    # exceptions
                    base = None
                    bm = re.search(r"\bextends\s+([\w.]+)", ln) or (lang == "kotlin" and re.search(r":\s*([\w.]+)\s*\(", ln))
                    if bm:
                        base = bm.group(1).split(".")[-1]
                    if base and re.search(r"(Exception|Error|Throwable)$", base):
                        prof.exception_bases[base] += 1
                        prof.exception_types[tdecl.name] = base
                    if tdecl.keyword == "enum" and re.search(r"(ErrorCode|ErrorType|ErrorKind|Errors)$", tdecl.name):
                        prof.error_code_enums += 1
            prev_nonblank = s
            continue
        if s.startswith("@"):
            prev_nonblank = s
            continue

        # constructors (Java/Kotlin) to spot field injection vs constructor injection
        if lang == "java" and current_type and re.match(r"^\s*(?:public|protected|private)?\s*" + re.escape(current_type) + r"\s*\(", ln):
            in_constructor = True
            anns = " ".join(pending_annotations)
            prof.di["constructor" + (" (@Autowired)" if "@Autowired" in anns or "@Inject" in anns else "")] += 1
            pending_annotations = []
            prev_nonblank = s
            continue
        if in_constructor and s.startswith("}"):
            in_constructor = False

        mdecl = extract_method(ln, ctx) if not is_test or lang in JAVA_LIKE or lang in ("python", "go", "ts", "js", "csharp", "kotlin", "rust", "swift") else None
        if mdecl:
            anns = " ".join(pending_annotations)
            pending_annotations = []
            words = split_words(mdecl.name)
            first = words[0].lower() if words else ""
            if is_test:
                nm = mdecl.name
                if re.match(r"^should[A-Z_]", nm):
                    style = "shouldX"
                elif re.match(r"^test[A-Z_0-9]", nm):
                    style = "testX"
                elif re.search(r"given.*when.*then", nm, re.I):
                    style = "givenWhenThen"
                elif "_" in nm and nm.islower():
                    style = "snake_case sentence"
                elif "_" in nm:
                    style = "mixed_with_underscores"
                elif nm[:1].islower():
                    style = "camelCase sentence"
                else:
                    style = "other"
                prof.test_method_style[style] += 1
            else:
                if first:
                    prof.method_verbs[first] += 1
                    if first in READ_VERBS:
                        prof.read_verbs[first] += 1
                    if first in ("do", "process", "handle", "check", "manage", "perform"):
                        prof.vague_verbs[first] += 1
                if lang in JAVA_LIKE and "@Transactional" in anns:
                    owner = current_type or "?"
                    kind = "Service" if owner.endswith(("Service", "UseCase", "Handler", "Facade")) else "Controller" if owner.endswith(("Controller", "Resource", "Endpoint")) else "Repository" if owner.endswith(("Repository", "Dao")) else "other"
                    prof.tx["method on " + kind] += 1
                    if "readOnly" in anns:
                        prof.tx["readOnly used"] += 1
                if lang in JAVA_LIKE and "@Async" in anns:
                    prof.async_["@Async"] += 1
                if lang in JAVA_LIKE and mdecl.ret and mdecl.ret.startswith("Optional<"):
                    prof.optional_usage["return type"] += 1
                if lang in JAVA_LIKE and mdecl.params and "Optional<" in mdecl.params:
                    prof.optional_usage["parameter (smell)"] += 1
            # mapping paths
            if lang in JAVA_LIKE:
                for m in re.finditer(r"@(?:Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?\"([^\"]*)\"", anns):
                    p = m.group(1)
                    prof.api["endpoint"] += 1
                    if re.search(r"/v\d+(/|$)", p):
                        prof.api["versioned path"] += 1
                    seg = re.sub(r"\{[^}]*\}", "", p)
                    if "-" in seg:
                        prof.path_styles["kebab-case"] += 1
                    elif "_" in seg:
                        prof.path_styles["snake_case"] += 1
                    elif re.search(r"[a-z][A-Z]", seg):
                        prof.path_styles["camelCase"] += 1
                    elif seg.strip("/"):
                        prof.path_styles["single-word"] += 1
            prev_nonblank = s
            continue

        if lang in JAVA_LIKE:
            # class-level annotations on fields: @Autowired/@Inject field injection
            if ("@Autowired" in prev_nonblank or "@Inject" in prev_nonblank) and re.match(r"^\s*(private|protected|public)?\s*(final\s+)?[\w<>\[\], ?.]+\s+\w+\s*;", ln):
                prof.di["field injection (@Autowired/@Inject on field)"] += 1
            if "@Transactional" in s and current_type and not pending_annotations:
                pass
            if re.search(r"^\s*@Transactional\b", s) and prev_nonblank and (prev_nonblank.startswith("@") or prev_nonblank.endswith(("{", ";", "}"))):
                pending_annotations.append(s)
            if "@Transactional" in s and current_type:
                kind = "Service" if current_type.endswith(("Service", "UseCase", "Handler", "Facade")) else "Controller" if current_type.endswith(("Controller", "Resource", "Endpoint")) else "Repository" if current_type.endswith(("Repository", "Dao")) else "other"
                if s.startswith("@Transactional"):
                    prof.tx["annotation on " + kind] += 1
            # logger declarations
            lm = LOGGER_DECL_RE.match(ln) or (lang == "kotlin" and KOTLIN_LOGGER_RE.match(ln))
            if lm:
                if lm.re is LOGGER_DECL_RE:
                    mods = "".join(x.strip() + " " for x in lm.groups()[:3] if x).strip()
                    prof.logger_decls[f"{mods or 'instance'} … {lm.group(4)}"] += 1
                else:
                    prof.logger_decls[f"{(lm.group(1) or '').strip() or 'val'} val … {lm.group(3)} (Kotlin)"] += 1
            if "@Slf4j" in s or "@Log4j2" in s or "@CommonsLog" in s:
                prof.logger_decls["Lombok " + s.split("(")[0]] += 1
            # log call style
            if LOG_CALL_RE.search(ln):
                if "{}" in ln:
                    prof.log_styles["{} placeholders"] += 1
                elif re.search(r"\"\s*\+|\+\s*\"", ln):
                    prof.log_styles["string concatenation"] += 1
                elif "String.format(" in ln or "format(" in ln:
                    prof.log_styles["String.format"] += 1
                elif lang == "kotlin" and "${" in ln:
                    prof.log_styles["Kotlin string template"] += 1
                else:
                    prof.log_styles["constant message"] += 1
            if re.search(r"\bSystem\.(out|err)\.print", ln):
                prof.sysout += 1
            if ".printStackTrace()" in ln:
                prof.print_stack += 1
            if re.search(r"\bMDC\.(put|get)", ln):
                prof.mdc += 1
            # exceptions usage
            for raw_ex in ("RuntimeException", "Exception", "IllegalStateException", "IllegalArgumentException", "UnsupportedOperationException", "ResponseStatusException"):
                if re.search(r"\bthrow\s+new\s+" + raw_ex + r"\s*\(", ln) or (lang == "kotlin" and re.search(r"\bthrow\s+" + raw_ex + r"\s*\(", ln)):
                    prof.raw_throws[raw_ex] += 1
            cm = re.search(r"\bcatch\s*\(\s*(?:final\s+)?([\w.]+(?:\s*\|\s*[\w.]+)*)", ln) or (lang == "kotlin" and re.search(r"\bcatch\s*\(\s*\w+\s*:\s*([\w.]+)", ln))
            if cm:
                caught = cm.group(1).split(".")[-1]
                if caught in ("Exception", "Throwable", "RuntimeException", "Error"):
                    prof.broad_catches[caught] += 1
            if "ProblemDetail" in ln:
                prof.error_handlers["ProblemDetail"] += 1
            if "ResponseEntity<" in ln:
                prof.api["ResponseEntity"] += 1
            # validation
            for marker, label in ((r"(?<![\w.])Assert\.(notNull|hasText|isTrue|state|notEmpty|hasLength|isNull|noNullElements)", "Spring Assert"), (r"\bObjects\.requireNonNull", "Objects.requireNonNull"), (r"\bPreconditions\.", "Guava Preconditions"), (r"\bValidate\.", "commons-lang Validate"), (r"@Valid\b", "Bean Validation @Valid"), (r"@(NotNull|NotBlank|NotEmpty|Size|Min|Max|Pattern|Positive|Email)\b", "Bean Validation constraints"), (r"(?<![\w.])require\(", "Kotlin require()"), (r"(?<![\w.])check\(", "Kotlin check()")):
                if re.search(marker, ln) and (not marker.endswith(r"\(") or lang == "kotlin"):
                    prof.validation[label] += 1
            # JPA
            if "FetchType.EAGER" in ln:
                prof.jpa["FetchType.EAGER"] += 1
            if "FetchType.LAZY" in ln:
                prof.jpa["FetchType.LAZY"] += 1
            if "@EntityGraph" in ln or "JOIN FETCH" in ln.upper():
                prof.jpa["fetch join/@EntityGraph"] += 1
            # async / concurrency
            for marker in ("CompletableFuture", "Mono<", "Flux<", "suspend fun", "Executors.new", "new Thread(", "@Scheduled", "ExecutorService", "ReentrantLock", "synchronized", "ConcurrentHashMap", "newVirtualThreadPerTaskExecutor", "@Async"):
                if marker in ln:
                    prof.async_[marker] += 1
            # http clients
            for marker in HTTP_CLIENTS[:8]:
                if re.search(r"(?<![\w.])" + re.escape(marker) + r"\b", ln) and ("new " in ln or "private" in ln or "val " in ln or "import" in ln):
                    prof.http_clients[marker] += 1
            if re.search(r"\bthis\.\w+\s*=", ln):
                prof.this_prefix["this.x = …"] += 1
            elif in_constructor and re.match(r"^\s*\w+\s*=\s*\w+\s*;", ln):
                prof.this_prefix["x = … (no this)"] += 1
        else:
            # light-weight generic checks for other languages
            if lang == "python":
                if re.search(r"\bexcept\s*(Exception|BaseException)?\s*:", ln):
                    prof.broad_catches["except Exception/bare"] += 1
                if re.search(r"\bprint\(", ln):
                    prof.sysout += 1
                if re.search(r"\b(logger|log|logging)\.(debug|info|warning|error|exception)\(", ln):
                    prof.log_styles["%s/%-style" if "%s" in ln or "%d" in ln else ("f-string" if re.search(r"\bf[\"']", ln) else "other")] += 1
            elif lang in ("ts", "js"):
                if "console." in ln:
                    prof.sysout += 1
                if re.search(r"\bcatch\s*(\(\s*\w*\s*\))?\s*\{\s*\}", ln):
                    prof.broad_catches["empty catch"] += 1
            elif lang == "go":
                if re.search(r"\b_\s*=\s*\w+\(|,\s*_\s*:?=", ln) and "err" in ln:
                    prof.broad_catches["ignored err"] += 1
                if "fmt.Print" in ln:
                    prof.sysout += 1
            elif lang == "csharp":
                if re.search(r"\bcatch\s*(\(\s*Exception\b|\{)", ln):
                    prof.broad_catches["catch Exception/bare"] += 1
                if "Console.Write" in ln:
                    prof.sysout += 1
        prev_nonblank = s

    # exception checked/unchecked classification (file-local; refined in finalize)
    return None


def classify_exceptions(prof: Profile) -> Counter:
    """Resolve custom exception bases transitively into checked/unchecked/unknown."""
    out: Counter = Counter()
    for name, base in prof.exception_types.items():
        seen = set()
        cur = base
        kind = "unknown base"
        while cur and cur not in seen:
            seen.add(cur)
            if cur in UNCHECKED_BASES or cur.endswith("RuntimeException"):
                kind = "unchecked"
                break
            if cur in CHECKED_BASES:
                kind = "checked"
                break
            cur = prof.exception_types.get(cur)
        out[kind] += 1
    return out


def package_layout(prof: Profile) -> Dict[str, object]:
    pkgs = prof.packages_main
    if not pkgs:
        return {"layout": "n/a (no Java/Kotlin packages found)"}
    split = {p: p.split(".") for p in pkgs}
    # common base package
    parts = list(split.values())
    base: List[str] = []
    for i in range(min(len(p) for p in parts)):
        seg = parts[0][i]
        if all(p[i] == seg for p in parts):
            base.append(seg)
        else:
            break
    base_pkg = ".".join(base)
    total = sum(pkgs.values())
    with_layer = 0
    feature_first = 0
    layer_first = 0
    hex_hits = 0
    top_level: Counter = Counter()
    special: Counter = Counter()
    for p, segs in split.items():
        n = pkgs[p]
        rest = segs[len(base):]
        if rest:
            top_level[rest[0]] += n
        for s in rest:
            if s in ("internal", "impl", "api", "spi"):
                special[s] += n
        layer_idx = next((i for i, s in enumerate(rest) if s in LAYER_WORDS), None)
        if any(s in HEX_WORDS for s in rest):
            hex_hits += n
        if layer_idx is None:
            continue
        with_layer += n
        if layer_idx > 0:
            feature_first += n
        else:
            layer_first += n
    if with_layer / total < 0.3:
        layout = "package-by-feature (few or no layer-named packages)"
    elif feature_first > layer_first:
        layout = "package-by-feature with layer sub-packages (<feature>/<layer>)"
    else:
        layout = "package-by-layer (<layer>/… or flat layers)"
    if hex_hits / total > 0.3:
        layout += "; hexagonal/clean naming (domain/application/infrastructure/adapter) present"
    test_mirror = None
    if prof.packages_test:
        mirrored = sum(n for p, n in prof.packages_test.items() if p in pkgs)
        test_mirror = round(100 * mirrored / sum(prof.packages_test.values()))
    return {
        "base_package": base_pkg or "(none)",
        "layout": layout,
        "files_with_layer_package_pct": round(100 * with_layer / total),
        "top_level_packages": top_level.most_common(12),
        "api_internal_impl_packages": dict(special),
        "tests_mirror_main_packages_pct": test_mirror,
    }


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def profile_repo(root: str, max_files: int, include_tests: bool) -> Tuple[Profile, Dict[str, object]]:
    prof = Profile()
    files, source = collect_files(root, max_files)
    src_count = 0
    for rel in files:
        norm = rel.replace(os.sep, "/")
        abs_path = os.path.join(root, rel)
        base = os.path.basename(norm)
        for key, rx in CONFIG_PATTERNS.items():
            if rx.search(norm):
                prof.configs[key].append(norm)
        if any(seg.startswith(".") for seg in norm.split("/")[:-1]):
            continue  # tool folders (.agents/.claude/.factory/.github/…) are not the codebase
        if base in BUILD_FILES or base.endswith((".csproj", ".sln", ".fsproj")):
            text = read_text(abs_path)
            if text is not None:
                analyse_build_file(norm, text, prof)
            continue
        if APP_CONFIG_RE.search(norm):
            text = read_text(abs_path)
            if text is not None:
                analyse_app_config(norm, text, prof)
            continue
        lang = LANG_BY_EXT.get(Path(norm).suffix)
        if not lang or GENERATED_PATH_RE.search(norm):
            continue
        is_test = bool(TEST_PATH_RE.search(norm))
        if is_test and not include_tests and prof.test_files > max_files // 2:
            continue
        if src_count >= max_files:
            prof.files_skipped += 1
            continue
        text = read_text(abs_path)
        if text is None:
            prof.files_skipped += 1
            continue
        src_count += 1
        prof.files_scanned += 1
        prof.languages[lang] += 1
        if is_test:
            prof.test_files += 1
        else:
            prof.main_files += 1
        analyse_source(norm, text, lang, is_test, prof)
    meta = {"root": os.path.abspath(root), "file_source": source, "files_listed": len(files)}
    return prof, meta


def fmt_counter(c: Counter, n: int = 8, sep: str = ", ") -> str:
    if not c:
        return "none found"
    return sep.join(f"{k} ×{v}" for k, v in c.most_common(n))


def pct(part: int, whole: int) -> str:
    return "n/a" if not whole else f"{round(100 * part / whole)}%"


def build_summary(prof: Profile, layout: Dict[str, object], exc_kinds: Counter) -> List[str]:
    """≤ 8 bullets the reviewer can paste into 'Conventions applied' after confirming."""
    bullets: List[str] = []
    langs = ", ".join(f"{k} ({v})" for k, v in prof.languages.most_common(3))
    baseline = ", ".join(prof.java_baseline) if prof.java_baseline else "baseline not detected"
    tools = ", ".join(prof.build_tools) or "no build file detected"
    mods = f"; {len(set(prof.modules))} modules" if prof.modules else ""
    bullets.append(f"Stack: {langs}; {tools}; {baseline}{mods}; libs: {', '.join(k for k, _ in prof.libraries.most_common(6)) or 'n/a'}.")
    if "layout" in layout and layout["layout"] != "n/a (no Java/Kotlin packages found)":
        bullets.append(f"Packaging: {layout['layout']}; base `{layout['base_package']}`; top-level: {', '.join(f'{k} ({v})' for k, v in layout['top_level_packages'][:6])}.")
    naming = f"Naming: top type suffixes {fmt_counter(prof.type_suffix, 6)}"
    if prof.impl_types:
        naming += f"; `*Impl` ×{len(prof.impl_types)}"
    if prof.iprefix_interfaces:
        naming += f"; `I*` interfaces ×{prof.iprefix_interfaces}/{prof.interfaces}"
    naming += f"; read verbs {fmt_counter(prof.read_verbs, 5)}"
    if prof.vague_verbs:
        naming += f"; vague verbs in use {fmt_counter(prof.vague_verbs, 4)}"
    if prof.dto_suffix:
        naming += f"; DTO suffixes {fmt_counter(prof.dto_suffix, 4)}"
    bullets.append(naming + ".")
    exc = f"Exceptions: bases {fmt_counter(prof.exception_bases, 5)}; {dict(exc_kinds) or 'no custom exceptions'}"
    if prof.raw_throws:
        exc += f"; raw throws {fmt_counter(prof.raw_throws, 4)}"
    if prof.broad_catches:
        exc += f"; broad catches {fmt_counter(prof.broad_catches, 3)}"
    if prof.error_handlers:
        exc += f"; handlers {fmt_counter(prof.error_handlers, 3)}"
    if prof.error_code_enums:
        exc += f"; error-code enums ×{prof.error_code_enums}"
    bullets.append(exc + ".")
    log = f"Logging: facade {fmt_counter(prof.log_facades, 3)}; declaration {fmt_counter(prof.logger_decls, 3)}; style {fmt_counter(prof.log_styles, 4)}"
    if prof.sysout:
        log += f"; System.out/print ×{prof.sysout}"
    if prof.print_stack:
        log += f"; printStackTrace ×{prof.print_stack}"
    if prof.mdc:
        log += f"; MDC ×{prof.mdc}"
    bullets.append(log + ".")
    null = f"Nullability: {fmt_counter(prof.null_annotations, 3)}" + (f"; @NullMarked ×{prof.null_marked}" if prof.null_marked else "") + f"; Optional {fmt_counter(prof.optional_usage, 3)}"
    di = f"DI: {fmt_counter(prof.di, 5)}"
    val = f"Validation: {fmt_counter(prof.validation, 4)}"
    imm = f"Immutability: {fmt_counter(prof.immutability, 5)}"
    bullets.append(f"{null}. {di}. {val}. {imm}.")
    tx_api = []
    if prof.tx:
        tx_api.append(f"Transactions: {fmt_counter(prof.tx, 5)}")
    if prof.api or prof.path_styles:
        tx_api.append(f"API: {fmt_counter(prof.api, 5)}; paths {fmt_counter(prof.path_styles, 3)}")
    if prof.jpa:
        tx_api.append(f"JPA: {fmt_counter(prof.jpa, 4)}")
    if prof.http_clients:
        tx_api.append(f"HTTP clients: {fmt_counter(prof.http_clients, 3)}")
    if prof.async_:
        tx_api.append(f"Async/concurrency: {fmt_counter(prof.async_, 5)}")
    if tx_api:
        bullets.append(". ".join(tx_api) + ".")
    tests = f"Tests: {fmt_counter(prof.test_libs, 6)}; classes {fmt_counter(prof.test_class_suffix, 3)}; methods {fmt_counter(prof.test_method_style, 3)}"
    if prof.test_kinds:
        tests += f"; kinds {fmt_counter(prof.test_kinds, 4)}"
    bullets.append(tests + ".")
    docs = f"Docs: Javadoc on public top-level types {pct(prof.javadoc_public, prof.public_types)} ({prof.javadoc_public}/{prof.public_types}); tags {fmt_counter(prof.doc_tags, 4)}; TODOs {fmt_counter(prof.todo, 2)}"
    fmt = ", ".join(k for k in prof.configs if k in ("checkstyle", "pmd", "editorconfig", "eslint", "prettier", "ruff", "golangci", "detekt", "ktlint", "pre-commit", "sonar")) or "none"
    spotless = "Spotless" if "Spotless" in prof.libraries else ""
    ep = "Error Prone" if "Error Prone" in prof.libraries else ""
    tools_fmt = ", ".join(x for x in (fmt, spotless, ep) if x and x != "none") or "none"
    docs += f". Formatters/linters: {tools_fmt} (do not review what they enforce)"
    if prof.wildcard_imports:
        docs += f"; wildcard imports ×{prof.wildcard_imports}"
    if prof.this_prefix:
        docs += f"; `this.` style {fmt_counter(prof.this_prefix, 2)}"
    bullets.append(docs + ".")
    docs_present = [k for k in ("agents-md", "contributing", "adr", "review-overrides", "archunit") if k in prof.configs]
    if docs_present:
        bullets.append("Documented sources to read first: " + "; ".join(f"{k}: {', '.join(prof.configs[k][:3])}" for k in docs_present) + ".")
    return bullets[:9]


def render_markdown(prof: Profile, meta: Dict[str, object]) -> str:
    layout = package_layout(prof)
    exc_kinds = classify_exceptions(prof)
    out: List[str] = []
    out.append("# Convention Profile (draft) — confirm against documented rules and neighbouring files")
    out.append(f"Root: `{meta['root']}` · files listed: {meta['files_listed']} ({meta['file_source']}) · source files scanned: {prof.files_scanned} (main {prof.main_files}, test {prof.test_files}; skipped {prof.files_skipped})")
    out.append("")
    out.append("## Profile summary (paste into the report's **Conventions applied** after confirming)")
    for b in build_summary(prof, layout, exc_kinds):
        out.append(f"- {b}")
    out.append("")
    out.append("## Evidence")
    out.append(f"- **Languages:** {fmt_counter(prof.languages)}")
    out.append(f"- **Build:** {fmt_counter(prof.build_tools)}; files: {', '.join(prof.build_files[:6]) or 'n/a'}")
    out.append(f"- **Java baseline:** {fmt_counter(prof.java_baseline)}; {fmt_counter(prof.kotlin_version)}")
    if prof.modules:
        out.append(f"- **Modules ({len(set(prof.modules))}):** {', '.join(sorted(set(prof.modules))[:30])}")
    out.append(f"- **Libraries/frameworks:** {fmt_counter(prof.libraries, 20)}")
    out.append(f"- **Config present:** " + ("; ".join(f"{k}: {', '.join(v[:2])}" for k, v in prof.configs.items()) or "none"))
    if prof.app_config:
        out.append(f"- **App config keys:** " + "; ".join(f"{k}={v}" for k, v in prof.app_config.items()))
    out.append("")
    out.append("### Packaging and modules")
    for k, v in layout.items():
        out.append(f"- {k}: {v}")
    out.append("")
    out.append("### Naming")
    out.append(f"- Type kinds: {fmt_counter(prof.type_kinds)}")
    out.append(f"- Type suffixes (last word): {fmt_counter(prof.type_suffix, 25)}")
    out.append(f"- `*Impl` types: {len(prof.impl_types)} ({', '.join(prof.impl_types[:8])}{'…' if len(prof.impl_types) > 8 else ''})")
    out.append(f"- Interfaces: {prof.interfaces}; with `I` prefix: {prof.iprefix_interfaces}")
    out.append(f"- DTO-ish suffixes: {fmt_counter(prof.dto_suffix)}")
    out.append(f"- Method first words (main code): {fmt_counter(prof.method_verbs, 25)}")
    out.append(f"- Read verbs: {fmt_counter(prof.read_verbs, 12)}")
    out.append(f"- Vague verbs in use (repo may legitimise them): {fmt_counter(prof.vague_verbs)}")
    out.append("")
    out.append("### Exceptions")
    out.append(f"- Custom exception bases: {fmt_counter(prof.exception_bases, 12)}")
    out.append(f"- Checked/unchecked: {dict(exc_kinds) or 'n/a'}")
    out.append(f"- Raw `throw new …`: {fmt_counter(prof.raw_throws)}")
    out.append(f"- Broad catches: {fmt_counter(prof.broad_catches)}; printStackTrace: {prof.print_stack}")
    out.append(f"- Handlers/error bodies: {fmt_counter(prof.error_handlers)}; error-code enums: {prof.error_code_enums}")
    out.append("")
    out.append("### Logging")
    out.append(f"- Facades (by import): {fmt_counter(prof.log_facades)}")
    out.append(f"- Logger declarations: {fmt_counter(prof.logger_decls, 8)}")
    out.append(f"- Call styles: {fmt_counter(prof.log_styles)}; System.out/console/print: {prof.sysout}; MDC: {prof.mdc}")
    out.append("")
    out.append("### Nullability, DI, validation, immutability")
    out.append(f"- Nullability annotations: {fmt_counter(prof.null_annotations)}; @NullMarked: {prof.null_marked}; Optional: {fmt_counter(prof.optional_usage)}")
    out.append(f"- DI: {fmt_counter(prof.di, 10)}")
    out.append(f"- Validation: {fmt_counter(prof.validation, 10)}")
    out.append(f"- Immutability / data carriers: {fmt_counter(prof.immutability, 10)}")
    out.append("")
    out.append("### Transactions, API, JPA, async, HTTP clients")
    out.append(f"- Transactions: {fmt_counter(prof.tx, 10)}")
    out.append(f"- API: {fmt_counter(prof.api, 10)}; path styles: {fmt_counter(prof.path_styles)}")
    out.append(f"- JPA: {fmt_counter(prof.jpa)}")
    out.append(f"- Async/concurrency markers: {fmt_counter(prof.async_, 12)}")
    out.append(f"- HTTP clients: {fmt_counter(prof.http_clients)}")
    out.append("")
    out.append("### Tests")
    out.append(f"- Libraries: {fmt_counter(prof.test_libs, 12)}")
    out.append(f"- Test class suffixes: {fmt_counter(prof.test_class_suffix)}; kinds: {fmt_counter(prof.test_kinds)}")
    out.append(f"- Test method naming: {fmt_counter(prof.test_method_style)}")
    out.append("")
    out.append("### Documentation and style")
    out.append(f"- Javadoc on public top-level types: {prof.javadoc_public}/{prof.public_types} ({pct(prof.javadoc_public, prof.public_types)}); tags: {fmt_counter(prof.doc_tags)}")
    out.append(f"- TODO style: {fmt_counter(prof.todo)}; wildcard imports: {prof.wildcard_imports}; `this.` in assignments: {fmt_counter(prof.this_prefix)}")
    out.append("")
    out.append("_Counts are heuristics over added-up declarations; confirm anything you rely on by opening the files. A convention is 'established' at ≥3 occurrences with no stronger competitor (references/repo-conventions.md §1)._")
    return "\n".join(out)


def to_json(prof: Profile, meta: Dict[str, object]) -> str:
    layout = package_layout(prof)
    data = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in vars(prof).items()}
    data["configs"] = dict(prof.configs)
    data["packages_main"] = dict(prof.packages_main.most_common(200))
    data["packages_test"] = dict(prof.packages_test.most_common(200))
    data["exception_kinds"] = dict(classify_exceptions(prof))
    data["package_layout"] = layout
    data["summary"] = build_summary(prof, layout, classify_exceptions(prof))
    data["meta"] = meta
    return json.dumps(data, indent=2, default=str)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="Directory to profile (default: current directory).")
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown")
    ap.add_argument("--max-files", type=int, default=4000, help="Maximum source files to read (default 4000).")
    ap.add_argument("--include-tests", action="store_true", help="Read all test files even when there are many.")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        sys.exit(f"error: {args.root} is not a directory")
    prof, meta = profile_repo(args.root, args.max_files, args.include_tests)
    print(to_json(prof, meta) if args.format == "json" else render_markdown(prof, meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
