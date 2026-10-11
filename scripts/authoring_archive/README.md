# Handoff authoring sources

These scripts preserve how the repository, paper update and slides were authored. They are historical authoring tools with machine-specific Codex/runtime paths. Do not run them blindly: some require a completed local vendor pipeline and assert the old manuscript text before editing. Use the portable examples and `scripts/verify_release.py` for a fresh clone.

The slide builder uses the Codex-bundled `@oai/artifact-tool` runtime. This library is not redistributed. The delivered PPTX retains editable native objects for ordinary PowerPoint editing. New export revisions use fresh final filenames and validation receipts.
