"""Tests for the AST extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from layup_python.models import MemberKind, MemberVisibility, NodeType, ParsedModule
from layup_python.parser.python.extractor import extract_module

FIXTURES = Path(__file__).parent / "fixtures" / "sample_pkg"


def _module(name: str, rel_path: str) -> ParsedModule:
    path = (FIXTURES / rel_path).resolve()
    return ParsedModule(id=name.replace(".", "__"), name=name, file_path=str(path))


def _get_class(module: ParsedModule, name: str):
    matches = [c for c in module.classes if c.name == name]
    assert matches, f"Class '{name}' not found in module. Found: {[c.name for c in module.classes]}"
    return matches[0]


def _get_member(cls, name: str):
    matches = [m for m in cls.members if m.name == name]
    assert matches, f"Member '{name}' not found. Found: {[m.name for m in cls.members]}"
    return matches[0]


# ---------------------------------------------------------------------------
# animals.py
# ---------------------------------------------------------------------------


class TestAnimalsModule:
    def setup_method(self):
        self.mod = _module("sample_pkg.animals", "animals.py")
        extract_module(self.mod)

    def test_finds_all_classes(self):
        names = {c.name for c in self.mod.classes}
        assert names == {"AnimalKind", "Flyable", "Animal", "Dog", "Parrot"}

    def test_enum_detection(self):
        cls = _get_class(self.mod, "AnimalKind")
        assert cls.node_type == NodeType.ENUM

    def test_protocol_detection(self):
        cls = _get_class(self.mod, "Flyable")
        assert cls.node_type == NodeType.INTERFACE

    def test_abstract_class_via_abc(self):
        cls = _get_class(self.mod, "Animal")
        assert cls.node_type == NodeType.ABSTRACT_CLASS

    def test_concrete_class(self):
        cls = _get_class(self.mod, "Dog")
        assert cls.node_type == NodeType.CLASS

    def test_class_with_multiple_bases(self):
        cls = _get_class(self.mod, "Parrot")
        assert cls.node_type == NodeType.CLASS  # Protocol is a mixin here

    # Members — Animal
    def test_abstract_method_flagged(self):
        cls = _get_class(self.mod, "Animal")
        speak = _get_member(cls, "speak")
        assert speak.is_abstract is True
        assert speak.kind == MemberKind.OPERATION

    def test_static_method_flagged(self):
        cls = _get_class(self.mod, "Animal")
        total = _get_member(cls, "total")
        assert total.is_static is True

    def test_class_attribute_visibility(self):
        cls = _get_class(self.mod, "Animal")
        count = _get_member(cls, "_count")
        assert count.visibility == MemberVisibility.PROTECTED
        assert count.kind == MemberKind.ATTRIBUTE

    def test_return_type_captured(self):
        cls = _get_class(self.mod, "Animal")
        describe = _get_member(cls, "describe")
        assert describe.type_ == "str"

    # Members — Dog
    def test_dog_public_attribute(self):
        cls = _get_class(self.mod, "Dog")
        breed = _get_member(cls, "breed")
        assert breed.visibility == MemberVisibility.PUBLIC
        assert breed.type_ == "str"

    def test_dog_method_params(self):
        cls = _get_class(self.mod, "Dog")
        fetch = _get_member(cls, "fetch")
        assert "item" in fetch.params
        assert fetch.type_ == "str"

    # Members — Parrot (private dunder-mangled attribute)
    def test_private_attribute(self):
        cls = _get_class(self.mod, "Parrot")
        secret = _get_member(cls, "__secret")
        assert secret.visibility == MemberVisibility.PRIVATE

    # Bases
    def test_dog_bases(self):
        cls = _get_class(self.mod, "Dog")
        assert "Animal" in cls.bases

    def test_animal_bases(self):
        cls = _get_class(self.mod, "Animal")
        assert "ABC" in cls.bases

    def test_parrot_bases(self):
        cls = _get_class(self.mod, "Parrot")
        assert "Animal" in cls.bases
        assert "Flyable" in cls.bases


# ---------------------------------------------------------------------------
# subpkg/vehicles.py
# ---------------------------------------------------------------------------


class TestVehiclesModule:
    def setup_method(self):
        self.mod = _module("sample_pkg.subpkg.vehicles", "subpkg/vehicles.py")
        extract_module(self.mod)

    def test_finds_all_classes(self):
        names = {c.name for c in self.mod.classes}
        assert names == {"Vehicle", "Car", "ElectricCar"}

    def test_vehicle_is_abstract(self):
        cls = _get_class(self.mod, "Vehicle")
        assert cls.node_type == NodeType.ABSTRACT_CLASS

    def test_car_is_concrete(self):
        cls = _get_class(self.mod, "Car")
        assert cls.node_type == NodeType.CLASS

    def test_electric_car_inherits_car(self):
        cls = _get_class(self.mod, "ElectricCar")
        assert "Car" in cls.bases

    def test_electric_car_private_attr(self):
        cls = _get_class(self.mod, "ElectricCar")
        battery = _get_member(cls, "__battery_kwh")
        assert battery.visibility == MemberVisibility.PRIVATE

    def test_protected_attribute(self):
        cls = _get_class(self.mod, "Vehicle")
        speed = _get_member(cls, "_speed")
        assert speed.visibility == MemberVisibility.PROTECTED


# ---------------------------------------------------------------------------
# Dunder methods are public
# ---------------------------------------------------------------------------


class TestDunderVisibility:
    def test_init_is_public(self):
        mod = _module("sample_pkg.animals", "animals.py")
        extract_module(mod)
        dog = _get_class(mod, "Dog")
        init = _get_member(dog, "__init__")
        assert init.visibility == MemberVisibility.PUBLIC


# ---------------------------------------------------------------------------
# Edge cases via synthetic sources
# ---------------------------------------------------------------------------


def _parse_source(source: str) -> ParsedModule:
    """Helper: create a temporary module from source string."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
        f.write(source)
        tmp = f.name
    mod = ParsedModule(id="tmp__mod", name="tmp.mod", file_path=tmp)
    try:
        extract_module(mod)
    finally:
        os.unlink(tmp)
    return mod


class TestSyntheticSources:
    def test_empty_file(self):
        mod = _parse_source("")
        assert mod.classes == []

    def test_no_classes(self):
        mod = _parse_source("x = 1\ndef foo(): pass\n")
        assert mod.classes == []

    def test_simple_class_no_members(self):
        mod = _parse_source("class Empty: pass\n")
        assert len(mod.classes) == 1
        assert mod.classes[0].name == "Empty"
        assert mod.classes[0].members == []

    def test_nested_class_excluded(self):
        src = "class Outer:\n    class Inner:\n        pass\n"
        mod = _parse_source(src)
        names = {c.name for c in mod.classes}
        assert "Outer" in names
        assert "Inner" not in names

    def test_params_no_self(self):
        src = "class C:\n    def greet(self, name: str, age: int = 0) -> str: ...\n"
        mod = _parse_source(src)
        greet = _get_member(mod.classes[0], "greet")
        assert "self" not in greet.params
        assert "name: str" in greet.params
        assert "age: int = 0" in greet.params

    def test_static_method_keeps_all_params(self):
        src = "class C:\n    @staticmethod\n    def add(a: int, b: int) -> int: ...\n"
        mod = _parse_source(src)
        add = _get_member(mod.classes[0], "add")
        assert "a: int" in add.params
        assert "b: int" in add.params

    def test_abstract_base_detection_via_abstractmethod(self):
        src = (
            "from abc import abstractmethod\n"
            "class MyBase:\n"
            "    @abstractmethod\n"
            "    def do(self) -> None: ...\n"
        )
        mod = _parse_source(src)
        assert mod.classes[0].node_type == NodeType.ABSTRACT_CLASS
