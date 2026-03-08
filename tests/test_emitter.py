"""Tests for the Layup DiagramState emitter (v2 schema)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from layup_python._schema_path import SCHEMA_PATH, SCHEMA_VERSION
from layup_python.emitter.layup import emit_diagram_state
from layup_python.models import (
    InheritanceEdge,
    MemberKind,
    MemberVisibility,
    NodeType,
    ParsedClass,
    ParsedMember,
    ParsedModule,
    ParsedPackage,
)

# ---------------------------------------------------------------------------
# Load schema once
# ---------------------------------------------------------------------------

with SCHEMA_PATH.open() as _f:
    _SCHEMA = json.load(_f)


def _validate(obj: dict) -> None:
    jsonschema.validate(obj, _SCHEMA)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_package() -> ParsedPackage:
    """Minimal package: one module with two classes and one inheritance edge."""
    pkg = ParsedPackage(name="mypkg", root_path="/mypkg")

    mod = ParsedModule(id="mypkg__utils", name="mypkg.utils", file_path="/mypkg/utils.py")

    base = ParsedClass(id="mypkg__utils.Base", name="Base", module_id="mypkg__utils")
    child = ParsedClass(
        id="mypkg__utils.Child",
        name="Child",
        module_id="mypkg__utils",
        bases=["Base"],
    )
    child.members = [
        ParsedMember(
            id="mypkg__utils.Child.value",
            kind=MemberKind.ATTRIBUTE,
            visibility=MemberVisibility.PUBLIC,
            name="value",
            type_="int",
        ),
        ParsedMember(
            id="mypkg__utils.Child.compute",
            kind=MemberKind.OPERATION,
            visibility=MemberVisibility.PUBLIC,
            name="compute",
            type_="str",
            params="(x: int)",
        ),
    ]

    mod.classes = [base, child]
    pkg.modules = [mod]
    return pkg


def _simple_edges(pkg: ParsedPackage) -> list[InheritanceEdge]:
    return [
        InheritanceEdge(
            id="edge_1",
            source_id="mypkg__utils.Child",
            target_id="mypkg__utils.Base",
            cross_module=False,
        )
    ]


# ---------------------------------------------------------------------------
# Top-level DiagramState structure
# ---------------------------------------------------------------------------


class TestDiagramStateStructure:
    def setup_method(self):
        self.pkg = _simple_package()
        self.edges = _simple_edges(self.pkg)
        self.state = emit_diagram_state(self.pkg, self.edges)

    def test_version(self):
        assert self.state["version"] == SCHEMA_VERSION

    def test_current_level_is_component(self):
        assert self.state["currentLevel"] == "component"

    def test_selected_id_null(self):
        assert self.state["selectedId"] is None

    def test_pending_node_type_null(self):
        assert self.state["pendingNodeType"] is None

    def test_levels_key_present(self):
        assert "levels" in self.state

    def test_four_fixed_levels(self):
        assert set(self.state["levels"].keys()) == {"context", "container", "component", "code"}

    def test_no_root_id(self):
        assert "rootId" not in self.state

    def test_no_navigation_stack(self):
        assert "navigationStack" not in self.state

    def test_no_diagrams_key(self):
        assert "diagrams" not in self.state

    def test_schema_valid(self):
        _validate(self.state)


# ---------------------------------------------------------------------------
# Component level
# ---------------------------------------------------------------------------


class TestComponentLevel:
    def setup_method(self):
        self.pkg = _simple_package()
        self.state = emit_diagram_state(self.pkg, [])
        self.level = self.state["levels"]["component"]

    def test_level_key_is_component(self):
        assert self.level["level"] == "component"

    def test_one_node_per_module(self):
        assert len(self.level["nodes"]) == len(self.pkg.modules)

    def test_module_node_type_is_component(self):
        for node in self.level["nodes"]:
            assert node["type"] == "component"

    def test_module_node_has_no_child_diagram_id(self):
        for node in self.level["nodes"]:
            assert "childDiagramId" not in node

    def test_module_node_has_position(self):
        for node in self.level["nodes"]:
            pos = node["position"]
            assert "x" in pos and "y" in pos

    def test_no_edges(self):
        assert self.level["edges"] == []

    def test_empty_annotations(self):
        assert self.level["annotations"] == []


# ---------------------------------------------------------------------------
# Code level
# ---------------------------------------------------------------------------


class TestCodeLevel:
    def setup_method(self):
        self.pkg = _simple_package()
        self.edges = _simple_edges(self.pkg)
        self.state = emit_diagram_state(self.pkg, self.edges)
        self.level = self.state["levels"]["code"]

    def test_level_key_is_code(self):
        assert self.level["level"] == "code"

    def test_one_node_per_class(self):
        assert len(self.level["nodes"]) == 2

    def test_class_node_types(self):
        types = {n["type"] for n in self.level["nodes"]}
        assert "class" in types

    def test_class_nodes_have_parent_node_id(self):
        for node in self.level["nodes"]:
            assert "parentNodeId" in node
            assert node["parentNodeId"] == "mypkg__utils"

    def test_inheritance_edge_present(self):
        assert len(self.level["edges"]) == 1

    def test_inheritance_edge_source_target(self):
        edge = self.level["edges"][0]
        assert edge["source"] == "mypkg__utils.Child"
        assert edge["target"] == "mypkg__utils.Base"

    def test_inheritance_marker_end(self):
        edge = self.level["edges"][0]
        assert edge["markerEnd"] == "hollow-triangle"

    def test_members_serialised(self):
        child_node = next(n for n in self.level["nodes"] if n["label"] == "Child")
        members = child_node["members"]
        assert len(members) == 2
        kinds = {m["kind"] for m in members}
        assert kinds == {"attribute", "operation"}

    def test_member_visibility(self):
        child_node = next(n for n in self.level["nodes"] if n["label"] == "Child")
        for m in child_node["members"]:
            assert m["visibility"] == "+"

    def test_no_annotations(self):
        assert self.level["annotations"] == []


# ---------------------------------------------------------------------------
# Empty levels (context + container always present and always empty)
# ---------------------------------------------------------------------------


class TestEmptyLevels:
    def setup_method(self):
        self.pkg = _simple_package()
        self.state = emit_diagram_state(self.pkg, _simple_edges(self.pkg))

    def test_context_level_present(self):
        assert "context" in self.state["levels"]

    def test_container_level_present(self):
        assert "container" in self.state["levels"]

    def test_context_nodes_empty(self):
        assert self.state["levels"]["context"]["nodes"] == []

    def test_context_edges_empty(self):
        assert self.state["levels"]["context"]["edges"] == []

    def test_container_nodes_empty(self):
        assert self.state["levels"]["container"]["nodes"] == []

    def test_container_edges_empty(self):
        assert self.state["levels"]["container"]["edges"] == []


# ---------------------------------------------------------------------------
# Cross-module edge filtering
# ---------------------------------------------------------------------------


class TestCrossModuleEdgeFiltering:
    def test_cross_module_edge_not_rendered(self):
        pkg = ParsedPackage(name="pkg", root_path="/pkg")
        mod_a = ParsedModule(id="pkg__a", name="pkg.a", file_path="/pkg/a.py")
        mod_b = ParsedModule(id="pkg__b", name="pkg.b", file_path="/pkg/b.py")
        base = ParsedClass(id="pkg__a.Base", name="Base", module_id="pkg__a")
        child = ParsedClass(id="pkg__b.Child", name="Child", module_id="pkg__b")
        mod_a.classes = [base]
        mod_b.classes = [child]
        pkg.modules = [mod_a, mod_b]

        cross_edge = InheritanceEdge(
            id="cross_1",
            source_id="pkg__b.Child",
            target_id="pkg__a.Base",
            cross_module=True,
        )
        state = emit_diagram_state(pkg, [cross_edge])
        assert state["levels"]["code"]["edges"] == []

    def test_same_module_edge_is_rendered(self):
        pkg = ParsedPackage(name="pkg", root_path="/pkg")
        mod = ParsedModule(id="pkg__mod", name="pkg.mod", file_path="/pkg/mod.py")
        base = ParsedClass(id="pkg__mod.Base", name="Base", module_id="pkg__mod")
        child = ParsedClass(id="pkg__mod.Child", name="Child", module_id="pkg__mod")
        mod.classes = [base, child]
        pkg.modules = [mod]

        edge = InheritanceEdge(
            id="e1",
            source_id="pkg__mod.Child",
            target_id="pkg__mod.Base",
            cross_module=False,
        )
        state = emit_diagram_state(pkg, [edge])
        assert len(state["levels"]["code"]["edges"]) == 1


# ---------------------------------------------------------------------------
# Schema validation against real fixture
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_empty_package_validates(self):
        pkg = ParsedPackage(name="empty", root_path="/empty")
        mod = ParsedModule(id="empty__init", name="empty", file_path="/empty/__init__.py")
        pkg.modules = [mod]
        state = emit_diagram_state(pkg, [])
        _validate(state)

    def test_full_fixture_validates(self):
        from layup_python.parser.walker import walk_package
        from layup_python.parser.extractor import extract_module
        from layup_python.relationships import resolve_inheritance

        fixture = Path(__file__).parent / "fixtures" / "sample_pkg"
        pkg = walk_package(fixture)
        for mod in pkg.modules:
            extract_module(mod)
        edges, _ = resolve_inheritance(pkg)
        state = emit_diagram_state(pkg, edges)
        _validate(state)

    def test_all_node_types_validate(self):
        """Exercise every supported node_type through the emitter and validate."""
        pkg = ParsedPackage(name="types_pkg", root_path="/types")
        mod = ParsedModule(id="types_pkg__mod", name="types_pkg.mod", file_path="/types/mod.py")
        for node_type in NodeType:
            cls = ParsedClass(
                id=f"types_pkg__mod.{node_type.name}",
                name=node_type.name,
                module_id="types_pkg__mod",
                node_type=node_type,
            )
            mod.classes.append(cls)
        pkg.modules = [mod]
        state = emit_diagram_state(pkg, [])
        _validate(state)
