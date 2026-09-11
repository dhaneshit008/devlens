"""Syntax extraction only. Resolution is a separate conservative analysis pass."""

import ast
from dataclasses import dataclass, field
from typing import Literal

import tree_sitter_javascript as ts_js
import tree_sitter_typescript as ts_ts
from tree_sitter import Language, Node, Parser

from devlens.ingestion import SourceFile
from devlens.models import Evidence, GraphNode, Limitation


@dataclass
class ImportReference:
    specifier: str
    line: int
    end_line: int
    level: int = 0
    names: list[str] = field(default_factory=list)


@dataclass
class ParsedFile:
    symbols: list[GraphNode] = field(default_factory=list)
    imports: list[ImportReference] = field(default_factory=list)
    limitations: list[Limitation] = field(default_factory=list)


def declaration(
    source: SourceFile,
    kind: Literal["function", "class", "method", "interface"],
    name: str,
    start: int,
    end: int,
    column: int,
    method: str,
) -> GraphNode:
    return GraphNode(
        id=f"symbol:{source.path}:{start}:{column}:{kind}",
        kind=kind,
        label=name,
        path=source.path,
        language=source.language,
        evidence=Evidence(path=source.path, start_line=start, end_line=end, method=method),
    )


def parse_python(source: SourceFile) -> ParsedFile:
    result = ParsedFile()
    try:
        root = ast.parse(source.content, filename=source.path)
    except (SyntaxError, ValueError, RecursionError) as exc:
        result.limitations.append(
            Limitation(
                path=source.path,
                line=getattr(exc, "lineno", 1) or 1,
                reason="Python parse failed; file dependencies are incomplete.",
            )
        )
        return result

    def visit(node: ast.AST, parent: ast.AST | None = None) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind: Literal["function", "class", "method", "interface"] = "function"
            if isinstance(node, ast.ClassDef):
                kind = "class"
            elif isinstance(parent, ast.ClassDef):
                kind = "method"
            result.symbols.append(
                declaration(
                    source,
                    kind,
                    node.name,
                    node.lineno,
                    node.end_lineno or node.lineno,
                    node.col_offset,
                    "python.ast declaration",
                )
            )
        if isinstance(node, ast.Import):
            result.imports.extend(
                ImportReference(a.name, node.lineno, node.end_lineno or node.lineno)
                for a in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            result.imports.append(
                ImportReference(
                    node.module or "",
                    node.lineno,
                    node.end_lineno or node.lineno,
                    node.level,
                    [a.name for a in node.names],
                )
            )
        elif isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Name) and node.func.id == "__import__") or (
                isinstance(node.func, ast.Attribute) and node.func.attr == "import_module"
            ):
                result.limitations.append(
                    Limitation(
                        path=source.path,
                        line=node.lineno,
                        reason="Dynamic Python import is not resolved.",
                    )
                )
        for child in ast.iter_child_nodes(node):
            visit(child, node)

    try:
        visit(root)
    except RecursionError:
        result.limitations.append(
            Limitation(
                path=source.path,
                line=1,
                reason="Syntax nesting limit reached; extraction is partial.",
            )
        )
    return result


def parse_javascript(source: SourceFile) -> ParsedFile:
    language = (
        Language(ts_js.language())
        if source.language == "JavaScript"
        else Language(
            ts_ts.language_tsx() if source.path.endswith(".tsx") else ts_ts.language_typescript()
        )
    )
    data = source.content.encode("utf-8")
    tree = Parser(language).parse(data)
    result = ParsedFile()
    if tree.root_node.has_error:
        result.limitations.append(
            Limitation(
                path=source.path, line=1, reason="Syntax errors detected; extraction is partial."
            )
        )

    def text(node: Node | None) -> str:
        return data[node.start_byte : node.end_byte].decode("utf-8") if node else ""

    def add_import(node: Node, literal: Node | None) -> None:
        if literal is None or literal.type != "string":
            result.limitations.append(
                Limitation(
                    path=source.path,
                    line=node.start_point.row + 1,
                    reason="Computed import is not resolved.",
                )
            )
            return
        raw = text(literal)[1:-1]
        if "\\" in raw:
            result.limitations.append(
                Limitation(
                    path=source.path,
                    line=node.start_point.row + 1,
                    reason="Escaped import specifier is not resolved.",
                )
            )
            return
        result.imports.append(
            ImportReference(raw, node.start_point.row + 1, node.end_point.row + 1)
        )

    stack = [tree.root_node]
    kinds: dict[str, Literal["function", "class", "method", "interface"]] = {
        "function_declaration": "function",
        "generator_function_declaration": "function",
        "class_declaration": "class",
        "abstract_class_declaration": "class",
        "method_definition": "method",
        "interface_declaration": "interface",
    }
    while stack:
        node = stack.pop()
        kind = kinds.get(node.type)
        name = node.child_by_field_name("name")
        if node.type == "variable_declarator":
            value = node.child_by_field_name("value")
            if value and value.type in {
                "arrow_function",
                "function_expression",
                "generator_function",
            }:
                kind = "function"
        if (
            kind
            and name
            and name.type
            in {
                "identifier",
                "type_identifier",
                "property_identifier",
                "private_property_identifier",
            }
        ):
            result.symbols.append(
                declaration(
                    source,
                    kind,
                    text(name),
                    node.start_point.row + 1,
                    node.end_point.row + 1,
                    node.start_point.column,
                    "tree-sitter declaration",
                )
            )
        if node.type in {"import_statement", "export_statement"}:
            literal = node.child_by_field_name("source")
            if literal:
                add_import(node, literal)
        elif node.type == "call_expression":
            function = node.child_by_field_name("function")
            if function and text(function) in {"require", "import"}:
                arguments = node.child_by_field_name("arguments")
                literal = (
                    arguments.named_children[0] if arguments and arguments.named_children else None
                )
                # require may be shadowed; preserve it as unresolved rather than a confirmed edge.
                if text(function) == "require":
                    result.limitations.append(
                        Limitation(
                            path=source.path,
                            line=node.start_point.row + 1,
                            reason="CommonJS require is not resolved (binding may be shadowed).",
                            specifier=text(literal),
                        )
                    )
                else:
                    add_import(node, literal)
        stack.extend(reversed(node.named_children))
    return result


def parse(source: SourceFile) -> ParsedFile:
    return parse_python(source) if source.language == "Python" else parse_javascript(source)
