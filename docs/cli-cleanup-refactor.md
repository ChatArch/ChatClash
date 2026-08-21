# ChatClash CLI Cleanup and Module/API Refactor

This PR tracks the ChatClash CLI cleanup and code-structure refactor.

## Registered CLI tree

The cleanup target is now enforced by the live Click registry. Use `chatclash --tree` for the signature-bearing view and `chatclash --tree-brief` for the same groups and leaves without signatures; the checked-in readback is maintained in [CLI Tree](cli-tree.md).

## Review requirements

This branch must satisfy the ChatArch CLI repository review points:

1. The ChatStyle full and brief CLI trees match the registered command surface.
2. Code is decoupled and layered; `cli.py` is a thin adapter.
3. CLI interaction follows ChatStyle conventions.
4. Major CLI capabilities have reusable Python APIs.
5. Secrets and private information are protected.
6. Tests and gates accurately cover the repository.

## Implementation direction

- Move command behavior out of `cli.py` into importable modules.
- Do not use Click command callback calls for behavior reuse.
- Keep package-specific CLI decisions in this repository's docs and tests.
- Keep ChatEnv/ChatStyle integration intact.
