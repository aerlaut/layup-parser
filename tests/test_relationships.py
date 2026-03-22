"""Tests for the inheritance relationship resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from layup_parser.models import ParsedClass, ParsedModule, ParsedPackage, NodeType
from layup_parser.parser.extractor import extract_module
from layup_parser.parser.walker import walk_package
from layup_parser.relationships import resolve_inheritance

FIXTURES = Path(__file__).parent / "fixtures" / "sample_pkg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_package(*module_defs: tuple[str, list[tuple[str, list[str]]]]) -> ParsedPackage:
    """Build a minimal ParsedPackage from (module_name, [(class_name, [bases])]) tuples."""
    pkg = ParsedPackage(name="pkg", root_path="/pkg")
    for mod_name, class_defs in module_defs:
        mod_id = mod_name.replace(".", "__")
        mod = ParsedModule(id=mod_id, name=mod_name, file_path=f"/pkg/{mod_name}.py")
        for class_name, bases in class_defs:
            cls = ParsedClass(
                id=f"{mod_id}.{class_name}",
                name=class_name,
                module_id=mod_id,
                bases=bases,
            )
            mod.classes.append(cls)
        pkg.modules.append(mod)
    return pkg


# ---------------------------------------------------------------------------
# Unit tests with synthetic packages
# ---------------------------------------------------------------------------


class TestResolveInheritanceSynthetic:
    def test_no_classes(self):
        pkg = _make_package(("mod", []))
        edges, warnings = resolve_inheritance(pkg)
        assert edges == []
        assert warnings == []

    def test_no_bases(self):
        pkg = _make_package(("mod", [("A", []), ("B", [])]))
        edges, warnings = resolve_inheritance(pkg)
        assert edges == []

    def test_unresolved_base_dropped(self):
        """Stdlib / third-party bases that don't exist in the package → silently skipped."""
        pkg = _make_package(("mod", [("A", ["SomeExternalBase"])]))
        edges, warnings = resolve_inheritance(pkg)
        assert edges == []
        assert warnings == []

    def test_same_module_inheritance(self):
        pkg = _make_package(("mod", [("Parent", []), ("Child", ["Parent"])]))
        edges, warnings = resolve_inheritance(pkg)
        assert len(edges) == 1
        e = edges[0]
        assert e.source_id == "mod.Child"
        assert e.target_id == "mod.Parent"
        assert e.cross_module is False
        assert warnings == []

    def test_cross_module_inheritance(self):
        pkg = _make_package(
            ("mod_a", [("Base", [])]),
            ("mod_b", [("Derived", ["Base"])]),
        )
        edges, warnings = resolve_inheritance(pkg)
        assert len(edges) == 1
        e = edges[0]
        assert e.source_id == "mod_b.Derived"
        assert e.target_id == "mod_a.Base"
        assert e.cross_module is True
        assert len(warnings) == 1
        assert "Cross-module" in warnings[0]
        assert "not rendered" not in warnings[0]

    def test_multiple_inheritance(self):
        """Both bases resolved → two edges."""
        pkg = _make_package(
            ("mod", [("A", []), ("B", []), ("C", ["A", "B"])])
        )
        edges, warnings = resolve_inheritance(pkg)
        source_ids = [e.source_id for e in edges]
        target_ids = [e.target_id for e in edges]
        assert source_ids.count("mod.C") == 2
        assert "mod.A" in target_ids
        assert "mod.B" in target_ids

    def test_self_loop_excluded(self):
        """A class listing itself as a base (malformed source) is not emitted."""
        pkg = _make_package(("mod", [("A", ["A"])]))
        edges, _ = resolve_inheritance(pkg)
        assert edges == []

    def test_prefers_same_module_over_cross(self):
        """When a name exists in both modules, same-module candidate is preferred."""
        pkg = _make_package(
            ("mod_a", [("Helper", [])]),
            ("mod_b", [("Helper", []), ("Child", ["Helper"])]),
        )
        edges, warnings = resolve_inheritance(pkg)
        # Child should resolve Helper from mod_b (same module), not mod_a
        assert len(edges) == 1
        assert edges[0].target_id == "mod_b.Helper"
        assert edges[0].cross_module is False
        assert warnings == []

    def test_edge_ids_are_unique(self):
        pkg = _make_package(
            ("mod", [("A", []), ("B", ["A"]), ("C", ["A"])])
        )
        edges, _ = resolve_inheritance(pkg)
        ids = [e.id for e in edges]
        assert len(ids) == len(set(ids))

    def test_diamond_inheritance(self):
        """A → B, A → C, D → B, D → C — four edges expected."""
        pkg = _make_package(
            (
                "mod",
                [
                    ("A", []),
                    ("B", ["A"]),
                    ("C", ["A"]),
                    ("D", ["B", "C"]),
                ],
            )
        )
        edges, _ = resolve_inheritance(pkg)
        assert len(edges) == 4


# ---------------------------------------------------------------------------
# Integration test against the real sample fixture
# ---------------------------------------------------------------------------


class TestResolveInheritanceFixture:
    def setup_method(self):
        from layup_parser.parser.extractor import extract_module

        self.pkg = walk_package(FIXTURES)
        for mod in self.pkg.modules:
            extract_module(mod)
        self.edges, self.warnings = resolve_inheritance(self.pkg)

    def test_dog_inherits_animal(self):
        sources = {e.source_id for e in self.edges}
        # Dog inherits Animal (same module)
        dog_edges = [e for e in self.edges if "Dog" in e.source_id and "Animal" in e.target_id]
        assert dog_edges, "Expected Dog→Animal edge"
        assert dog_edges[0].cross_module is False

    def test_electric_car_inherits_car(self):
        ec_edges = [e for e in self.edges if "ElectricCar" in e.source_id and "Car" in e.target_id]
        assert ec_edges
        assert ec_edges[0].cross_module is False

    def test_cross_module_edges_produce_warnings(self):
        # sample_pkg fixture has no cross-module inheritance in same-module
        # resolved edges; verify warnings only exist for true cross-module refs
        for w in self.warnings:
            assert "Cross-module" in w

    def test_abc_base_dropped(self):
        """abc.ABC is not in the package → should not appear as an edge target."""
        target_ids = {e.target_id for e in self.edges}
        assert not any("ABC" in t for t in target_ids)
