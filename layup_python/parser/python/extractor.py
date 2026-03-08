"""AST-based class and member extraction.

For each :class:`~layup_python.models.ParsedModule` (which has a ``file_path``
but no classes yet), :func:`extract_module` parses the source file with the
standard ``ast`` module and populates ``module.classes``.

Class-type detection rules (evaluated in priority order):
1. Base class is ``enum.Enum``, ``enum.IntEnum``, ``enum.Flag``,
   ``enum.IntFlag``, or ``enum.StrEnum``  →  ``NodeType.ENUM``
2. Base class is ``typing.Protocol`` or ``typing_extensions.Protocol``  →
   ``NodeType.INTERFACE``
3. Decorated with ``@abstractmethod`` members *or* base is ``abc.ABC`` /
   ``abc.ABCMeta``  →  ``NodeType.ABSTRACT_CLASS``
4. Everything else  →  ``NodeType.CLASS``

Visibility mapping:
- ``__name``  →  ``-``  (private)
- ``_name``   →  ``#``  (protected)
- ``name``    →  ``+``  (public)
- ``__name__`` (dunder) stays ``+``  (special methods are effectively public)
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

from layup_python.models import (
    MemberKind,
    MemberVisibility,
    NodeType,
    ParsedClass,
    ParsedMember,
    ParsedModule,
)

# ---------------------------------------------------------------------------
# Name sets for type detection
# ---------------------------------------------------------------------------

_ENUM_BASES: frozenset[str] = frozenset(
    {"Enum", "IntEnum", "Flag", "IntFlag", "StrEnum"}
)
_PROTOCOL_BASES: frozenset[str] = frozenset({"Protocol"})
_ABC_BASES: frozenset[str] = frozenset({"ABC", "ABCMeta"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unparse(node: ast.expr | None) -> str | None:
    """Return a compact string representation of an AST expression, or None."""
    if node is None:
        return None
    return ast.unparse(node)


def _base_name(node: ast.expr) -> str:
    """Extract the simple name from a base-class AST node.

    Handles plain names (``ABC``) and attribute accesses (``abc.ABC``,
    ``typing.Protocol``), returning only the rightmost segment.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ast.unparse(node)


def _visibility(name: str) -> MemberVisibility:
    """Map a Python identifier to a UML visibility marker.

    Dunder names (``__init__``, ``__str__``, …) are treated as public because
    they are part of the object's interface despite the leading underscores.
    """
    if name.startswith("__") and name.endswith("__"):
        return MemberVisibility.PUBLIC
    if name.startswith("__"):
        return MemberVisibility.PRIVATE
    if name.startswith("_"):
        return MemberVisibility.PROTECTED
    return MemberVisibility.PUBLIC


def _has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    """Return True if *node* has a decorator whose name equals *name*."""
    for dec in node.decorator_list:
        dec_name = _base_name(dec) if isinstance(dec, ast.Attribute) else (
            dec.id if isinstance(dec, ast.Name) else None
        )
        if dec_name == name:
            return True
    return False


def _has_staticmethod(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return _has_decorator(node, "staticmethod")


def _has_classmethod(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return _has_decorator(node, "classmethod")


def _has_abstractmethod(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return _has_decorator(node, "abstractmethod")


def _params_string(
    args: ast.arguments,
    is_static: bool,
) -> str:
    """Build a compact ``(param: type, …)`` string from an ``ast.arguments`` node.

    ``self`` / ``cls`` are omitted for non-static methods because they are
    implicit in UML diagrams.
    """
    parts: list[str] = []
    all_args = args.args + args.posonlyargs

    # Drop implicit first argument (self/cls) for non-static methods
    skip_first = not is_static and bool(all_args)
    start = 1 if skip_first else 0

    # Build annotation offset: defaults are right-aligned
    defaults_offset = len(all_args) - len(args.defaults)

    for idx, arg in enumerate(all_args[start:], start=start):
        annotation = _unparse(arg.annotation)
        default_idx = idx - defaults_offset
        default = _unparse(args.defaults[default_idx]) if 0 <= default_idx < len(args.defaults) else None

        part = arg.arg
        if annotation:
            part += f": {annotation}"
        if default is not None:
            part += f" = {default}"
        parts.append(part)

    # *args
    if args.vararg:
        va = args.vararg
        part = f"*{va.arg}"
        if va.annotation:
            part += f": {_unparse(va.annotation)}"
        parts.append(part)

    # **kwargs
    if args.kwarg:
        kw = args.kwarg
        part = f"**{kw.arg}"
        if kw.annotation:
            part += f": {_unparse(kw.annotation)}"
        parts.append(part)

    return f"({', '.join(parts)})"


# ---------------------------------------------------------------------------
# Node-type detection
# ---------------------------------------------------------------------------


def _detect_node_type(
    node: ast.ClassDef,
    has_abstract_members: bool,
) -> NodeType:
    """Determine the :class:`NodeType` for a class AST node."""
    base_names = {_base_name(b) for b in node.bases}

    if base_names & _ENUM_BASES:
        return NodeType.ENUM
    if base_names & _PROTOCOL_BASES:
        return NodeType.INTERFACE
    if has_abstract_members or bool(base_names & _ABC_BASES):
        return NodeType.ABSTRACT_CLASS
    return NodeType.CLASS


# ---------------------------------------------------------------------------
# Member extraction
# ---------------------------------------------------------------------------


def _extract_instance_attrs(
    init_node: ast.FunctionDef | ast.AsyncFunctionDef,
    class_id: str,
    seen_names: set[str],
) -> list[ParsedMember]:
    """Extract annotated ``self.attr: Type`` assignments from ``__init__``.

    Only processes direct-body statements (not nested blocks) to stay
    conservative.  Already-seen names (from class-level AnnAssign) are
    skipped to avoid duplicates.
    """
    members: list[ParsedMember] = []
    for stmt in init_node.body:
        if not (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Attribute)
            and isinstance(stmt.target.value, ast.Name)
            and stmt.target.value.id == "self"
        ):
            continue
        attr_name = stmt.target.attr
        if attr_name in seen_names:
            continue
        seen_names.add(attr_name)
        members.append(
            ParsedMember(
                id=f"{class_id}.{attr_name}",
                kind=MemberKind.ATTRIBUTE,
                visibility=_visibility(attr_name),
                name=attr_name,
                type_=_unparse(stmt.annotation),
            )
        )
    return members


def _extract_members(
    class_node: ast.ClassDef,
    class_id: str,
) -> tuple[list[ParsedMember], bool]:
    """Extract members from a class body.

    Returns a tuple of ``(members, has_abstract_members)``.
    """
    members: list[ParsedMember] = []
    has_abstract = False
    seen_attr_names: set[str] = set()

    for item in class_node.body:
        # Class-level annotated attribute: ``name: Type`` or ``name: Type = value``
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            attr_name = item.target.id
            seen_attr_names.add(attr_name)
            member = ParsedMember(
                id=f"{class_id}.{attr_name}",
                kind=MemberKind.ATTRIBUTE,
                visibility=_visibility(attr_name),
                name=attr_name,
                type_=_unparse(item.annotation),
            )
            members.append(member)

        # Method (sync or async)
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_name = item.name
            is_static = _has_staticmethod(item) or _has_classmethod(item)
            is_abstract = _has_abstractmethod(item)
            if is_abstract:
                has_abstract = True

            return_type = _unparse(item.returns)
            params = _params_string(item.args, is_static)

            member = ParsedMember(
                id=f"{class_id}.{fn_name}",
                kind=MemberKind.OPERATION,
                visibility=_visibility(fn_name),
                name=fn_name,
                type_=return_type,
                params=params,
                is_static=is_static,
                is_abstract=is_abstract,
            )
            members.append(member)

            # Also extract annotated ``self.attr: Type`` from __init__ body
            if fn_name == "__init__":
                instance_attrs = _extract_instance_attrs(item, class_id, seen_attr_names)
                members.extend(instance_attrs)

    return members, has_abstract


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_module(module: ParsedModule) -> None:
    """Parse *module*'s source file and populate ``module.classes`` in-place.

    Parameters
    ----------
    module:
        A :class:`~layup_python.models.ParsedModule` whose ``file_path``
        points to a readable ``.py`` file.  ``module.classes`` will be
        extended with the extracted :class:`~layup_python.models.ParsedClass`
        objects.

    Raises
    ------
    OSError
        If the file cannot be read.
    SyntaxError
        If the file cannot be parsed (propagated from ``ast.parse``).
    """
    source = Path(module.file_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=module.file_path)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Only process top-level classes (direct children of the module body)
        # to avoid extracting nested/local classes.
        if node not in tree.body:
            continue

        class_id = f"{module.id}.{node.name}"
        members, has_abstract = _extract_members(node, class_id)
        node_type = _detect_node_type(node, has_abstract)
        raw_bases = [_base_name(b) for b in node.bases]

        parsed_class = ParsedClass(
            id=class_id,
            name=node.name,
            module_id=module.id,
            node_type=node_type,
            members=members,
            bases=raw_bases,
        )
        module.classes.append(parsed_class)
