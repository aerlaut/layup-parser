"""Tests for the usage (dependency) relationship resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from layup_parser.models import (
    MemberKind,
    MemberVisibility,
    ParsedClass,
    ParsedMember,
    ParsedModule,
    ParsedPackage,
)
from layup_parser.usage import resolve_usage

FIXTURES = Path(__file__).parent / "fixtures" / "sample_pkg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_package(*module_defs):
    """Build a minimal ParsedPackage from (module_name, [(class_name, members)]) tuples.

    Each member is a (attr_name, type_str) pair for attributes, or
    (method_name, return_type, params_str) for operations.
    """
    pkg = ParsedPackage(name="pkg", root_path="/pkg")
    for mod_name, class_defs in module_defs:
        mod_id = mod_name.replace(".", "__")
        mod = ParsedModule(id=mod_id, name=mod_name, file_path=f"/pkg/{mod_name}.py")
        for class_name, members in class_defs:
            cls = ParsedClass(
                id=f"{mod_id}.{class_name}",
                name=class_name,
                module_id=mod_id,
            )
            for member in members:
                if len(member) == 2:
                    attr_name, type_str = member
                    cls.members.append(
                        ParsedMember(
                            id=f"{mod_id}.{class_name}.{attr_name}",
                            kind=MemberKind.ATTRIBUTE,
                            visibility=MemberVisibility.PUBLIC,
                            name=attr_name,
                            type_=type_str,
                        )
                    )
                else:
                    method_name, return_type, params_str = member
                    cls.members.append(
                        ParsedMember(
                            id=f"{mod_id}.{class_name}.{method_name}",
                            kind=MemberKind.OPERATION,
                            visibility=MemberVisibility.PUBLIC,
                            name=method_name,
                            type_=return_type,
                            params=params_str,
                        )
                    )
            mod.classes.append(cls)
        pkg.modules.append(mod)
    return pkg


# ---------------------------------------------------------------------------
# Unit tests with synthetic packages
# ---------------------------------------------------------------------------


class TestResolveUsageSynthetic:
    def test_no_classes(self):
        pkg = _make_package(("mod", []))
        edges, warnings = resolve_usage(pkg)
        assert edges == []
        assert warnings == []

    def test_no_members(self):
        pkg = _make_package(("mod", [("A", []), ("B", [])]))
        edges, warnings = resolve_usage(pkg)
        assert edges == []

    def test_unresolvable_type_dropped(self):
        """Types not in the package (stdlib, third-party) are silently skipped."""
        pkg = _make_package(("mod", [("A", [("x", "int")])]))
        edges, warnings = resolve_usage(pkg)
        assert edges == []
        assert warnings == []

    def test_same_module_usage_attribute_type(self):
        """Class A has attribute of type B → edge A→B."""
        pkg = _make_package(
            ("mod", [("B", []), ("A", [("item", "B")])])
        )
        edges, warnings = resolve_usage(pkg)
        assert len(edges) == 1
        e = edges[0]
        assert e.source_id == "mod.A"
        assert e.target_id == "mod.B"
        assert e.cross_module is False

    def test_same_module_usage_return_type(self):
        """Operation with return type B → edge A→B."""
        pkg = _make_package(
            ("mod", [("B", []), ("A", [("get_b", "B", "()")] )])
        )
        edges, warnings = resolve_usage(pkg)
        assert len(edges) == 1
        e = edges[0]
        assert e.source_id == "mod.A"
        assert e.target_id == "mod.B"

    def test_same_module_usage_param_type(self):
        """Operation with parameter of type B → edge A→B."""
        pkg = _make_package(
            ("mod", [("B", []), ("A", [("process", "None", "(b: B)")])])
        )
        edges, warnings = resolve_usage(pkg)
        assert len(edges) == 1
        e = edges[0]
        assert e.source_id == "mod.A"
        assert e.target_id == "mod.B"

    def test_deduplication(self):
        """Multiple members referencing same class → only one edge emitted."""
        pkg = _make_package(
            (
                "mod",
                [
                    ("B", []),
                    (
                        "A",
                        [
                            ("x", "B"),
                            ("y", "B"),
                            ("get_b", "B", "(z: B)"),
                        ],
                    ),
                ],
            )
        )
        edges, _ = resolve_usage(pkg)
        b_edges = [e for e in edges if e.target_id == "mod.B"]
        assert len(b_edges) == 1

    def test_self_reference_excluded(self):
        """A class referencing itself in a type annotation produces no edge."""
        pkg = _make_package(
            ("mod", [("A", [("next_", "A")])])
        )
        edges, _ = resolve_usage(pkg)
        assert edges == []

    def test_cross_module_usage(self):
        """Class in mod_b has attribute of type from mod_a → cross_module=True."""
        pkg = _make_package(
            ("mod_a", [("Target", [])]),
            ("mod_b", [("User", [("dep", "Target")])]),
        )
        edges, warnings = resolve_usage(pkg)
        assert len(edges) == 1
        e = edges[0]
        assert e.source_id == "mod_b.User"
        assert e.target_id == "mod_a.Target"
        assert e.cross_module is True

    def test_edge_ids_are_unique(self):
        pkg = _make_package(
            (
                "mod",
                [
                    ("B", []),
                    ("C", []),
                    ("A", [("b", "B"), ("c", "C")]),
                ],
            )
        )
        edges, _ = resolve_usage(pkg)
        ids = [e.id for e in edges]
        assert len(ids) == len(set(ids))

    def test_edge_id_prefix(self):
        """Usage edge IDs use 'usage_' prefix to distinguish from inheritance edges."""
        pkg = _make_package(
            ("mod", [("B", []), ("A", [("x", "B")])])
        )
        edges, _ = resolve_usage(pkg)
        assert all(e.id.startswith("usage_") for e in edges)

    def test_prefers_same_module_candidate(self):
        """When name exists in both modules, same-module candidate wins."""
        pkg = _make_package(
            ("mod_a", [("Helper", [])]),
            ("mod_b", [("Helper", []), ("User", [("h", "Helper")])]),
        )
        edges, _ = resolve_usage(pkg)
        assert len(edges) == 1
        assert edges[0].target_id == "mod_b.Helper"
        assert edges[0].cross_module is False

    def test_multiple_targets_from_one_class(self):
        """Class A referencing B and C produces two distinct edges."""
        pkg = _make_package(
            ("mod", [("B", []), ("C", []), ("A", [("b", "B"), ("c", "C")])])
        )
        edges, _ = resolve_usage(pkg)
        target_ids = {e.target_id for e in edges}
        assert "mod.B" in target_ids
        assert "mod.C" in target_ids


# ---------------------------------------------------------------------------
# Integration test against the real sample fixture
# ---------------------------------------------------------------------------


class TestResolveUsageFixture:
    def setup_method(self):
        from layup_parser.parser.extractor import extract_module
        from layup_parser.parser.walker import walk_package

        self.pkg = walk_package(FIXTURES)
        for mod in self.pkg.modules:
            extract_module(mod)
        self.edges, self.warnings = resolve_usage(self.pkg)

    def test_returns_edges(self):
        """Fixture has annotated members, so at least one usage edge expected."""
        assert len(self.edges) > 0

    def test_no_self_loops(self):
        for e in self.edges:
            assert e.source_id != e.target_id

    def test_no_duplicate_pairs(self):
        pairs = [(e.source_id, e.target_id) for e in self.edges]
        assert len(pairs) == len(set(pairs))

    def test_animal_uses_animal_kind(self):
        """Animal has _kind: AnimalKind → usage edge Animal→AnimalKind."""
        edges = [
            e for e in self.edges
            if "Animal" in e.source_id and "AnimalKind" in e.target_id
        ]
        assert edges, "Expected Animal→AnimalKind usage edge"
        assert edges[0].cross_module is False

    def test_vehicle_uses_animal_cross_module(self):
        """Vehicle.mascot: Animal → cross-module usage edge."""
        edges = [
            e for e in self.edges
            if "Vehicle" in e.source_id and "Animal" in e.target_id
        ]
        assert edges, "Expected Vehicle→Animal cross-module usage edge"
        assert edges[0].cross_module is True

    def test_warnings_list(self):
        assert isinstance(self.warnings, list)
