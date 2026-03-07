"""Tests for the hierarchical layout engine."""

from __future__ import annotations

from layup_python.layout.hierarchical import (
    CLASS_GAP_X,
    CLASS_GAP_Y,
    CLASS_NODE_W,
    MAX_COLUMNS,
    MODULE_GAP_X,
    MODULE_GAP_Y,
    MODULE_NODE_H,
    MODULE_NODE_W,
    PADDING_X,
    PADDING_Y,
    layout_classes,
    layout_modules,
)
from layup_python.models import InheritanceEdge, NodeType, ParsedClass, ParsedModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mod(name: str) -> ParsedModule:
    return ParsedModule(id=name.replace(".", "__"), name=name, file_path=f"/{name}.py")


def _cls(mod_id: str, name: str, bases: list[str] | None = None) -> ParsedClass:
    return ParsedClass(
        id=f"{mod_id}.{name}",
        name=name,
        module_id=mod_id,
        bases=bases or [],
    )


def _edge(child: ParsedClass, parent: ParsedClass, idx: int = 1) -> InheritanceEdge:
    return InheritanceEdge(
        id=f"e{idx}",
        source_id=child.id,
        target_id=parent.id,
        cross_module=child.module_id != parent.module_id,
    )


# ---------------------------------------------------------------------------
# Module (component-level) layout
# ---------------------------------------------------------------------------


class TestLayoutModules:
    def test_empty(self):
        assert layout_modules([]) == {}

    def test_single_module(self):
        m = _mod("pkg.mod")
        positions = layout_modules([m])
        assert m.id in positions
        pos = positions[m.id]
        assert pos.x == PADDING_X
        assert pos.y == PADDING_Y

    def test_two_modules_same_row(self):
        mods = [_mod("pkg.a"), _mod("pkg.b")]
        pos = layout_modules(mods)
        # Alphabetical: a comes first (col 0), b next (col 1)
        a_id = mods[0].id
        b_id = mods[1].id
        assert pos[a_id].y == pos[b_id].y  # same row
        assert pos[b_id].x > pos[a_id].x

    def test_grid_wraps_after_max_columns(self):
        mods = [_mod(f"pkg.m{i}") for i in range(MAX_COLUMNS + 1)]
        pos = layout_modules(mods)
        sorted_ids = [m.id for m in sorted(mods, key=lambda m: m.name)]
        # First MAX_COLUMNS modules are on row 0
        row0_y = PADDING_Y
        for mid in sorted_ids[:MAX_COLUMNS]:
            assert pos[mid].y == row0_y
        # The (MAX_COLUMNS+1)-th module wraps to row 1
        row1_y = PADDING_Y + MODULE_NODE_H + MODULE_GAP_Y
        assert pos[sorted_ids[MAX_COLUMNS]].y == row1_y

    def test_all_modules_have_unique_positions(self):
        mods = [_mod(f"pkg.m{i}") for i in range(8)]
        pos = layout_modules(mods)
        coords = [(p.x, p.y) for p in pos.values()]
        assert len(coords) == len(set(coords))

    def test_positions_are_sorted_alphabetically(self):
        mods = [_mod("pkg.zebra"), _mod("pkg.apple"), _mod("pkg.mango")]
        pos = layout_modules(mods)
        # apple → x=PADDING_X (col 0), mango → col 1, zebra → col 2
        apple_id = mods[1].id
        mango_id = mods[2].id
        zebra_id = mods[0].id
        assert pos[apple_id].x < pos[mango_id].x < pos[zebra_id].x

    def test_to_dict(self):
        pos = layout_modules([_mod("pkg.a")])[_mod("pkg.a").id]
        d = pos.to_dict()
        assert set(d.keys()) == {"x", "y"}


# ---------------------------------------------------------------------------
# Class (code-level) layout
# ---------------------------------------------------------------------------


class TestLayoutClasses:
    def test_empty(self):
        assert layout_classes([], []) == {}

    def test_single_isolated_class(self):
        cls = _cls("mod", "A")
        pos = layout_classes([cls], [])
        assert cls.id in pos
        p = pos[cls.id]
        assert p.x == PADDING_X
        assert p.y == PADDING_Y

    def test_all_isolated_same_layer(self):
        classes = [_cls("mod", n) for n in ["A", "B", "C"]]
        pos = layout_classes(classes, [])
        ys = {pos[c.id].y for c in classes}
        assert len(ys) == 1  # all on same layer

    def test_parent_above_child(self):
        parent = _cls("mod", "Parent")
        child = _cls("mod", "Child")
        edge = _edge(child, parent)
        pos = layout_classes([parent, child], [edge])
        assert pos[parent.id].y < pos[child.id].y

    def test_two_levels_gap(self):
        parent = _cls("mod", "P")
        child = _cls("mod", "C")
        edge = _edge(child, parent)
        pos = layout_classes([parent, child], [edge])
        # Gap between layers must be at least CLASS_GAP_Y
        y_diff = pos[child.id].y - pos[parent.id].y
        assert y_diff >= CLASS_GAP_Y

    def test_three_level_chain(self):
        a = _cls("mod", "A")
        b = _cls("mod", "B")
        c = _cls("mod", "C")
        edges = [_edge(b, a, 1), _edge(c, b, 2)]
        pos = layout_classes([a, b, c], edges)
        assert pos[a.id].y < pos[b.id].y < pos[c.id].y

    def test_siblings_on_same_row(self):
        parent = _cls("mod", "P")
        child1 = _cls("mod", "C1")
        child2 = _cls("mod", "C2")
        edges = [_edge(child1, parent, 1), _edge(child2, parent, 2)]
        pos = layout_classes([parent, child1, child2], edges)
        assert pos[child1.id].y == pos[child2.id].y
        assert pos[child1.id].x != pos[child2.id].x

    def test_cross_module_edges_ignored(self):
        """Cross-module edges should not affect layer assignment."""
        cls_a = _cls("mod_a", "A")
        cls_b = _cls("mod_b", "B")
        cross_edge = _edge(cls_b, cls_a)
        # Only one class from this module, cross edge should not influence it
        pos = layout_classes([cls_b], [cross_edge])
        # cls_b has no same-module parent → lands on layer 0
        assert pos[cls_b.id].y == PADDING_Y

    def test_diamond_inheritance(self):
        a = _cls("mod", "A")
        b = _cls("mod", "B")
        c = _cls("mod", "C")
        d = _cls("mod", "D")
        edges = [
            _edge(b, a, 1),
            _edge(c, a, 2),
            _edge(d, b, 3),
            _edge(d, c, 4),
        ]
        pos = layout_classes([a, b, c, d], edges)
        # A at top, B and C in middle, D at bottom
        assert pos[a.id].y < pos[b.id].y
        assert pos[a.id].y < pos[c.id].y
        assert pos[b.id].y < pos[d.id].y
        assert pos[c.id].y < pos[d.id].y

    def test_unique_positions(self):
        classes = [_cls("mod", f"C{i}") for i in range(6)]
        parent = classes[0]
        edges = [_edge(c, parent, i) for i, c in enumerate(classes[1:], 1)]
        pos = layout_classes(classes, edges)
        coords = [(p.x, p.y) for p in pos.values()]
        assert len(coords) == len(set(coords))
