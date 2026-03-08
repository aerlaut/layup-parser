"""Sanity tests for the IR dataclasses in models.py."""

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


def _make_member(suffix: str = "1") -> ParsedMember:
    return ParsedMember(
        id=f"member-{suffix}",
        kind=MemberKind.ATTRIBUTE,
        visibility=MemberVisibility.PUBLIC,
        name=f"attr_{suffix}",
        type_="int",
    )


def _make_class(suffix: str = "A") -> ParsedClass:
    return ParsedClass(
        id=f"mod1.Class{suffix}",
        name=f"Class{suffix}",
        module_id="mod1",
    )


class TestParsedMember:
    def test_defaults(self):
        m = _make_member()
        assert m.is_static is False
        assert m.is_abstract is False
        assert m.params is None

    def test_operation(self):
        m = ParsedMember(
            id="op1",
            kind=MemberKind.OPERATION,
            visibility=MemberVisibility.PRIVATE,
            name="__init__",
            params="(self, x: int)",
            type_="None",
        )
        assert m.kind == MemberKind.OPERATION
        assert m.visibility == MemberVisibility.PRIVATE

    def test_visibility_values(self):
        assert MemberVisibility.PUBLIC.value == "+"
        assert MemberVisibility.PRIVATE.value == "-"
        assert MemberVisibility.PROTECTED.value == "#"
        assert MemberVisibility.PACKAGE.value == "~"


class TestParsedClass:
    def test_defaults(self):
        c = _make_class()
        assert c.node_type == NodeType.CLASS
        assert c.members == []
        assert c.bases == []

    def test_with_members(self):
        c = _make_class("B")
        c.members.append(_make_member("1"))
        assert len(c.members) == 1

    def test_node_types(self):
        assert NodeType.ABSTRACT_CLASS.value == "abstract-class"
        assert NodeType.INTERFACE.value == "interface"
        assert NodeType.ENUM.value == "enum"
        assert NodeType.RECORD.value == "record"


class TestParsedModule:
    def test_empty(self):
        m = ParsedModule(id="mod1", name="mypkg.mod1", file_path="/src/mod1.py")
        assert m.classes == []

    def test_adds_classes(self):
        m = ParsedModule(id="mod1", name="mypkg.mod1", file_path="/src/mod1.py")
        m.classes.append(_make_class())
        assert len(m.classes) == 1


class TestParsedPackage:
    def test_structure(self):
        pkg = ParsedPackage(name="mypkg", root_path="/src/mypkg")
        mod = ParsedModule(id="mod1", name="mypkg.mod1", file_path="/src/mypkg/mod1.py")
        pkg.modules.append(mod)
        assert len(pkg.modules) == 1
        assert pkg.modules[0].name == "mypkg.mod1"


class TestInheritanceEdge:
    def test_same_module(self):
        edge = InheritanceEdge(id="e1", source_id="mod1.Child", target_id="mod1.Parent")
        assert edge.cross_module is False

    def test_cross_module(self):
        edge = InheritanceEdge(
            id="e2",
            source_id="mod2.Child",
            target_id="mod1.Parent",
            cross_module=True,
        )
        assert edge.cross_module is True
