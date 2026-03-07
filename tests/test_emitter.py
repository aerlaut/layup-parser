"""Tests for the Layup DiagramState emitter."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from layup_python._schema_path import SCHEMA_PATH, SCHEMA_VERSION
from layup_python.emitter.layup import ROOT_DIAGRAM_ID, emit_diagram_state
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

    def test_root_id(self):
        assert self.state["rootId"] == ROOT_DIAGRAM_ID

    def test_navigation_stack(self):
        assert self.state["navigationStack"] == [ROOT_DIAGRAM_ID]

    def test_selected_id_null(self):
        assert self.state["selectedId"] is None

    def test_pending_node_type_null(self):
        assert self.state["pendingNodeType"] is None

    def test_diagrams_key_present(self):
        assert "diagrams" in self.state

    def test_root_diagram_in_diagrams(self):
        assert ROOT_DIAGRAM_ID in self.state["diagrams"]

    def test_module_diagram_in_diagrams(self):
        assert "mypkg__utils" in self.state["diagrams"]

    def test_schema_valid(self):
        _validate(self.state)


# ---------------------------------------------------------------------------
# Root (component-level) diagram
# ---------------------------------------------------------------------------


class TestRootDiagram:
    def setup_method(self):
        self.pkg = _simple_package()
        self.state = emit_diagram_state(self.pkg, [])
        self.root = self.state["diagrams"][ROOT_DIAGRAM_ID]

    def test_level_is_component(self):
        assert self.root["level"] == "component"

    def test_label_defaults_to_package_name(self):
        assert self.root["label"] == "mypkg"

    def test_custom_root_label(self):
        state = emit_diagram_state(self.pkg, [], root_label="My Diagram")
        assert state["diagrams"][ROOT_DIAGRAM_ID]["label"] == "My Diagram"

    def test_one_node_per_module(self):
        assert len(self.root["nodes"]) == len(self.pkg.modules)

    def test_module_node_type_is_component(self):
        for node in self.root["nodes"]:
            assert node["type"] == "component"

    def test_module_node_has_child_diagram_id(self):
        for node in self.root["nodes"]:
            assert "childDiagramId" in node
            assert node["childDiagramId"] == node["id"]

    def test_module_node_has_position(self):
        for node in self.root["nodes"]:
            pos = node["position"]
            assert "x" in pos and "y" in pos

    def test_root_has_no_edges(self):
        assert self.root["edges"] == []

    def test_root_has_empty_annotations(self):
        assert self.root["annotations"] == []


# ---------------------------------------------------------------------------
# Code-level (module) diagram
# ---------------------------------------------------------------------------


class TestModuleDiagram:
    def setup_method(self):
        self.pkg = _simple_package()
        self.edges = _simple_edges(self.pkg)
        self.state = emit_diagram_state(self.pkg, self.edges)
        self.mod_diag = self.state["diagrams"]["mypkg__utils"]

    def test_level_is_code(self):
        assert self.mod_diag["level"] == "code"

    def test_label_is_module_name(self):
        assert self.mod_diag["label"] == "mypkg.utils"

    def test_one_node_per_class(self):
        assert len(self.mod_diag["nodes"]) == 2

    def test_class_node_types(self):
        types = {n["type"] for n in self.mod_diag["nodes"]}
        assert "class" in types

    def test_inheritance_edge_present(self):
        assert len(self.mod_diag["edges"]) == 1

    def test_inheritance_edge_source_target(self):
        edge = self.mod_diag["edges"][0]
        assert edge["source"] == "mypkg__utils.Child"
        assert edge["target"] == "mypkg__utils.Base"

    def test_inheritance_marker_end(self):
        edge = self.mod_diag["edges"][0]
        assert edge["markerEnd"] == "hollow-triangle"

    def test_members_serialised(self):
        child_node = next(n for n in self.mod_diag["nodes"] if n["label"] == "Child")
        members = child_node["members"]
        assert len(members) == 2
        kinds = {m["kind"] for m in members}
        assert kinds == {"attribute", "operation"}

    def test_member_visibility(self):
        child_node = next(n for n in self.mod_diag["nodes"] if n["label"] == "Child")
        for m in child_node["members"]:
            assert m["visibility"] == "+"

    def test_no_annotations(self):
        assert self.mod_diag["annotations"] == []


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
        # Neither module diagram should contain the cross-module edge
        for mod_id in ["pkg__a", "pkg__b"]:
            assert state["diagrams"][mod_id]["edges"] == []

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
        assert len(state["diagrams"]["pkg__mod"]["edges"]) == 1


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
