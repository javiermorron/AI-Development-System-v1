"""
ReviewerAgent — stage 3 of the example pipeline.

Input : {"files": {"<filename>": "<source code>", ...}}
Output: {
    "approved": bool,
    "score": float,          # 0.0 – 10.0
    "summary": str,
    "findings": list[Finding],
    "metrics": {
        "files_reviewed": int,
        "classes_found": int,
        "functions_found": int,
        "docstring_coverage": str,  # "n/m"
        "not_implemented_count": int,
        "todo_count": int,
    },
}

Uses Python's ast module for real static analysis — no LLM required.
In v3, replace / extend _analyze_file() with an LLM-based review call.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

from src.agents.base import AgentTask, BaseAgent
from src.agents.registry import register


@dataclass
class Finding:
    severity: str        # "INFO" | "WARNING" | "ERROR"
    file: str
    line: int            # 0 = file-level
    message: str

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "message": self.message,
        }


@register
class ReviewerAgent(BaseAgent):
    """
    Reviews generated Python source files using AST static analysis.
    Stage 3 of 3 in the example pipeline.
    """

    name = "reviewer-agent"
    allowed_tools = ["read_file"]

    def execute(self, task: AgentTask) -> dict[str, Any]:
        files: dict[str, str] = task.input.get("files", {})
        if not files:
            raise ValueError("Input 'files' must be a non-empty dict of filename→code.")

        all_findings: list[Finding] = []
        total_classes = total_functions = total_with_docstring = 0
        total_not_implemented = total_todo = 0

        for filename, source in files.items():
            if not filename.endswith(".py"):
                continue   # skip requirements.txt, README.md, etc.
            findings, metrics = self._analyze_file(filename, source)
            all_findings.extend(findings)
            total_classes         += metrics["classes"]
            total_functions       += metrics["functions"]
            total_with_docstring  += metrics["with_docstring"]
            total_not_implemented += metrics["not_implemented"]
            total_todo            += metrics["todos"]

        errors   = [f for f in all_findings if f.severity == "ERROR"]
        warnings = [f for f in all_findings if f.severity == "WARNING"]

        # Score: start at 10, deduct per finding
        score = 10.0 - (len(errors) * 2.0) - (len(warnings) * 0.5)
        score = max(0.0, round(score, 1))

        approved = len(errors) == 0 and score >= 6.0

        return {
            "approved": approved,
            "score": score,
            "summary": self._make_summary(score, approved, all_findings,
                                          total_functions, total_not_implemented),
            "findings": [f.as_dict() for f in all_findings],
            "metrics": {
                "files_reviewed":      len(files),
                "classes_found":       total_classes,
                "functions_found":     total_functions,
                "docstring_coverage":  f"{total_with_docstring}/{total_functions}",
                "not_implemented_count": total_not_implemented,
                "todo_count":          total_todo,
            },
        }

    # ------------------------------------------------------------------
    # File-level analysis
    # ------------------------------------------------------------------

    def _analyze_file(
        self, filename: str, source: str
    ) -> tuple[list[Finding], dict[str, int]]:
        findings: list[Finding] = []
        metrics = {
            "classes": 0, "functions": 0,
            "with_docstring": 0, "not_implemented": 0, "todos": 0,
        }

        # --- Parse ---
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as exc:
            findings.append(Finding(
                severity="ERROR", file=filename, line=exc.lineno or 0,
                message=f"SyntaxError: {exc.msg}",
            ))
            return findings, metrics

        # --- Walk AST ---
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
                self._check_function(node, filename, findings, metrics)

            elif isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
                self._check_class(node, filename, findings)

            elif isinstance(node, ast.Raise):
                if self._is_not_implemented(node):
                    metrics["not_implemented"] += 1

        # --- Regex checks on raw source ---
        for i, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if "TODO" in stripped or "FIXME" in stripped:
                metrics["todos"] += 1
            if "print(" in stripped and filename != "routes.py":
                findings.append(Finding(
                    severity="WARNING", file=filename, line=i,
                    message="Debug print() found — use logging instead",
                ))
            if re.search(r'(password|secret|api_key)\s*=\s*["\'][^"\']+["\']', stripped, re.I):
                findings.append(Finding(
                    severity="ERROR", file=filename, line=i,
                    message="Hardcoded credential detected — use environment variables",
                ))

        return findings, metrics

    # ------------------------------------------------------------------
    # Node-level checks
    # ------------------------------------------------------------------

    def _check_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        filename: str,
        findings: list[Finding],
        metrics: dict[str, int],
    ) -> None:
        has_docstring = (
            isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ) if node.body else False

        if has_docstring:
            metrics["with_docstring"] += 1
        elif not node.name.startswith("_"):
            # Public function without docstring — INFO only (generated code is OK)
            findings.append(Finding(
                severity="INFO", file=filename, line=node.lineno,
                message=f"Public function '{node.name}' has no docstring",
            ))

        # Check return type annotation on public functions
        if not node.returns and not node.name.startswith("_"):
            findings.append(Finding(
                severity="WARNING", file=filename, line=node.lineno,
                message=f"Function '{node.name}' is missing a return type annotation",
            ))

        # Check arg type annotations
        unannotated = [
            a.arg for a in node.args.args
            if a.annotation is None and a.arg not in ("self", "cls")
        ]
        if unannotated:
            findings.append(Finding(
                severity="WARNING", file=filename, line=node.lineno,
                message=(
                    f"Function '{node.name}' has unannotated parameters: "
                    f"{', '.join(unannotated)}"
                ),
            ))

    def _check_class(
        self, node: ast.ClassDef, filename: str, findings: list[Finding]
    ) -> None:
        has_docstring = (
            isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ) if node.body else False

        if not has_docstring:
            findings.append(Finding(
                severity="INFO", file=filename, line=node.lineno,
                message=f"Class '{node.name}' has no docstring",
            ))

    def _is_not_implemented(self, node: ast.Raise) -> bool:
        if node.exc is None:
            return False
        exc = node.exc
        # raise NotImplementedError   or   raise NotImplementedError(...)
        if isinstance(exc, ast.Name):
            return exc.id == "NotImplementedError"
        if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
            return exc.func.id == "NotImplementedError"
        return False

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _make_summary(
        self,
        score: float,
        approved: bool,
        findings: list[Finding],
        total_functions: int,
        not_implemented: int,
    ) -> str:
        errors   = sum(1 for f in findings if f.severity == "ERROR")
        warnings = sum(1 for f in findings if f.severity == "WARNING")
        infos    = sum(1 for f in findings if f.severity == "INFO")
        verdict  = "APPROVED" if approved else "NEEDS WORK"
        stub_pct = (
            f"{not_implemented}/{total_functions} functions are stubs (NotImplementedError)"
            if total_functions else "no functions found"
        )
        return (
            f"Score {score}/10 — {verdict}. "
            f"{errors} error(s), {warnings} warning(s), {infos} info(s). "
            f"{stub_pct}."
        )
