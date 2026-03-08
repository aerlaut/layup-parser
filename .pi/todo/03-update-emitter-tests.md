# Task 3: Update Emitter Tests for New Schema (v2)

## Motivation

`tests/test_emitter.py` is tightly coupled to the old `DiagramState`
structure (version 1). After tasks 1 and 2 land, many tests will fail because
they reference removed keys (`rootId`, `navigationStack`, `diagrams`) and
removed helpers (`ROOT_DIAGRAM_ID`). The tests must be updated to validate
the new structure while keeping full coverage of the emitter's behaviour.

## Files to change

### `tests/test_emitter.py`

#### Imports
- Remove `ROOT_DIAGRAM_ID` from the `layup_python.emitter.layup` import.

#### `TestDiagramStateStructure`
| Old test | Action |
|---|---|
| `test_root_id` — checks `state["rootId"]` | **Remove** |
| `test_navigation_stack` — checks `state["navigationStack"]` | **Remove** |
| `test_diagrams_key_present` — checks `"diagrams" in state` | **Replace** with `test_levels_key_present` asserting `"levels" in state` |
| `test_root_diagram_in_diagrams` | **Replace** with `test_current_level_is_component` asserting `state["currentLevel"] == "component"` |
| `test_module_diagram_in_diagrams` | **Replace** with `test_four_fixed_levels` asserting `set(state["levels"].keys()) == {"context", "container", "component", "code"}` |
| `test_schema_valid` | Keep unchanged |

#### `TestRootDiagram` → rename to `TestComponentLevel`
- Access via `self.state["levels"]["component"]` instead of
  `self.state["diagrams"][ROOT_DIAGRAM_ID]`.
- Remove `test_label_defaults_to_package_name` and `test_custom_root_label`
  (DiagramLevel no longer has a `label` field).
- Remove `test_module_node_has_child_diagram_id` (field removed).
- Add `test_module_node_has_no_child_diagram_id` asserting
  `"childDiagramId" not in node` for every node.
- Keep: node count, node type, position, no edges, empty annotations.

#### `TestModuleDiagram` → rename to `TestCodeLevel`
- Access via `self.state["levels"]["code"]` instead of
  `self.state["diagrams"]["mypkg__utils"]`.
- Remove `test_level_is_code` / `test_label_is_module_name` — replace with
  `test_level_key_is_code` asserting
  `self.state["levels"]["code"]["level"] == "code"`.
- **Add** `test_class_nodes_have_parent_node_id` — every class node in the
  code level should have a `parentNodeId` equal to the module id
  (`"mypkg__utils"`).
- Keep: node count, node types, edge presence, edge source/target, marker,
  member serialisation, visibility, no annotations.

#### `TestCrossModuleEdgeFiltering`
- Update dict access from `state["diagrams"][mod_id]["edges"]` to
  `state["levels"]["code"]["edges"]` (single code level now).
- For `test_cross_module_edge_not_rendered`: assert
  `state["levels"]["code"]["edges"] == []`.
- For `test_same_module_edge_is_rendered`: assert
  `len(state["levels"]["code"]["edges"]) == 1`.

#### `TestEmptyLevels` (new test class)
- Add a test asserting that `context` and `container` levels are always
  present and always have `nodes == []` and `edges == []`.

#### `TestSchemaValidation`
- No changes needed to test logic; they exercise `jsonschema.validate` which
  will pick up all structural constraints from the updated schema.

## Acceptance criteria

- All tests in `test_emitter.py` pass with the new emitter.
- No test references `rootId`, `navigationStack`, `diagrams`, or
  `ROOT_DIAGRAM_ID`.
- Schema-validation tests (`TestSchemaValidation`) continue to pass.
- `TestCodeLevel` includes a `test_class_nodes_have_parent_node_id` assertion.
