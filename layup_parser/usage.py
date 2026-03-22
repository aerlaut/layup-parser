"""Usage (dependency) relationship resolution.

After the walker and extractor have fully populated a :class:`ParsedPackage`,
this module resolves type annotations on class members into concrete
:class:`UsageEdge` objects between known parsed classes.

Resolution strategy
-------------------
1. Build a lookup ``name → list[ParsedClass]`` across all modules.
2. For each class, collect all type annotation strings from its members:
   - ``ParsedMember.type_`` (attribute types and operation return types)
   - ``ParsedMember.params`` string (scan for known class names within it)
3. For each type name found that resolves to a known class:
   - Skip if it resolves to the class itself (no self-loops)
   - Skip duplicates — emit at most one ``UsageEdge`` per (source_id, target_id) pair
   - Set ``cross_module=True`` if source and target are in different modules
4. Return ``(edges, warnings)``.
"""

from __future__ import annotations

import itertools
import re

from layup_parser.models import ParsedClass, ParsedPackage, UsageEdge

# Matches a single Python identifier (potential class name)
_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


def resolve_usage(
    package: ParsedPackage,
) -> tuple[list[UsageEdge], list[str]]:
    """Resolve usage edges for all classes in *package*.

    Parameters
    ----------
    package:
        A fully-populated :class:`~layup_parser.models.ParsedPackage` (walker
        + extractor have already run).

    Returns
    -------
    edges:
        List of resolved :class:`UsageEdge` objects.
    warnings:
        Human-readable warning strings (currently empty; reserved for future
        use such as cross-module usage notices).
    """
    # Build lookup: simple name → list of ParsedClass (ordered by module name)
    name_to_classes: dict[str, list[ParsedClass]] = {}
    for mod in sorted(package.modules, key=lambda m: m.name):
        for cls in mod.classes:
            name_to_classes.setdefault(cls.name, []).append(cls)

    # Convenience: class id → module_id
    class_module: dict[str, str] = {
        cls.id: cls.module_id
        for mod in package.modules
        for cls in mod.classes
    }

    edges: list[UsageEdge] = []
    warnings: list[str] = []
    edge_counter = itertools.count(1)

    for mod in package.modules:
        for cls in mod.classes:
            # Track (source_id, target_id) pairs already emitted to deduplicate
            seen: set[str] = set()

            # Collect all type strings to scan
            type_strings: list[str] = []
            for member in cls.members:
                if member.type_ is not None:
                    type_strings.append(member.type_)
                if member.params is not None:
                    type_strings.append(member.params)

            for type_str in type_strings:
                for match in _IDENTIFIER_RE.finditer(type_str):
                    name = match.group(1)
                    candidates = name_to_classes.get(name)
                    if not candidates:
                        continue

                    # Prefer same-module candidate
                    same_mod = [c for c in candidates if c.module_id == cls.module_id]
                    target = same_mod[0] if same_mod else candidates[0]

                    # Skip self-loops
                    if target.id == cls.id:
                        continue

                    # Deduplicate
                    pair_key = f"{cls.id}\x00{target.id}"
                    if pair_key in seen:
                        continue
                    seen.add(pair_key)

                    cross = class_module.get(target.id) != cls.module_id
                    edge_id = f"usage_{next(edge_counter)}"

                    edges.append(
                        UsageEdge(
                            id=edge_id,
                            source_id=cls.id,
                            target_id=target.id,
                            cross_module=cross,
                        )
                    )

    return edges, warnings
