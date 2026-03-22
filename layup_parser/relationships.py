"""Inheritance relationship resolution.

After the walker and extractor have fully populated a :class:`ParsedPackage`,
this module resolves raw base-class name strings into concrete
:class:`InheritanceEdge` objects between known parsed classes.

Resolution strategy
-------------------
1. Build a lookup ``name → list[ParsedClass]`` across all modules (a name can
   appear in multiple modules).
2. For each class C with base name B, attempt to find B in the lookup:
   a. Prefer a class in the **same module** as C.
   b. Fall back to the first class found across all modules (alphabetical by
      module name for determinism).
3. If B cannot be resolved (stdlib / third-party / unknown), the base is
   silently dropped — no phantom nodes.
4. Cross-module edges (source and target in different modules) are recorded
   with ``cross_module=True`` and reported via the returned warning list.
   All resolved edges are rendered by the emitter.
"""

from __future__ import annotations

import itertools

from layup_parser.models import InheritanceEdge, ParsedClass, ParsedPackage


def resolve_inheritance(
    package: ParsedPackage,
) -> tuple[list[InheritanceEdge], list[str]]:
    """Resolve inheritance edges for all classes in *package*.

    Parameters
    ----------
    package:
        A fully-populated :class:`~layup_parser.models.ParsedPackage` (walker
        + extractor have already run).

    Returns
    -------
    edges:
        List of resolved :class:`InheritanceEdge` objects.
    warnings:
        Human-readable warning strings for cross-module edges and any other
        noteworthy resolution issues.
    """
    # ------------------------------------------------------------------
    # Build lookup: simple name → list of ParsedClass (ordered by module name
    # for determinism)
    # ------------------------------------------------------------------
    name_to_classes: dict[str, list[ParsedClass]] = {}
    for mod in sorted(package.modules, key=lambda m: m.name):
        for cls in mod.classes:
            name_to_classes.setdefault(cls.name, []).append(cls)

    # Convenience: id → module_id for fast lookup
    class_module: dict[str, str] = {
        cls.id: cls.module_id
        for mod in package.modules
        for cls in mod.classes
    }

    edges: list[InheritanceEdge] = []
    warnings: list[str] = []
    edge_counter = itertools.count(1)

    for mod in package.modules:
        for cls in mod.classes:
            for base_name in cls.bases:
                candidates = name_to_classes.get(base_name)
                if not candidates:
                    # Unresolved — stdlib or third-party, skip silently
                    continue

                # Prefer same-module candidate
                same_mod = [c for c in candidates if c.module_id == cls.module_id]
                target = same_mod[0] if same_mod else candidates[0]

                # Avoid self-loops (shouldn't happen, but guard anyway)
                if target.id == cls.id:
                    continue

                cross = class_module.get(target.id) != cls.module_id
                edge_id = f"edge_{next(edge_counter)}"

                edge = InheritanceEdge(
                    id=edge_id,
                    source_id=cls.id,
                    target_id=target.id,
                    cross_module=cross,
                )
                edges.append(edge)

                if cross:
                    warnings.append(
                        f"Cross-module inheritance: "
                        f"{cls.id} → {target.id}"
                    )

    return edges, warnings
