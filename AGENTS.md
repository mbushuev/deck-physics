# Repository rules

- Put the initial import and integration commits directly on `main`.
- After the initial integration, make changes on short, descriptive branches such as `installer-rollback` or `update-zluda`. Do not use tool or `codex` prefixes.
- Verify changes on their branch before merging them into `main`. Build and tag releases from tested commits on `main`.
- Write documentation, comments, and project descriptions in English. Use repository-relative paths in examples and documentation. Discover game and Steam library locations at runtime.
- Keep commits focused. Exclude personal data, machine-specific paths, game files, proprietary PhysX binaries and generated modules, credentials, saves, profiling captures, and unrelated experiments.
