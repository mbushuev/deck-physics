# Repository rules

- Keep related changes together on an existing branch. Create a short, descriptively named branch only when work needs isolation or separate review. Do not use tool or `codex` prefixes.
- Verify changes before merging them into `main`. Once `main` contains the commits, delete the merged topic branches locally and on GitHub. Build and tag releases from tested commits on `main`.
- Write documentation, comments, and project descriptions in English. Use repository-relative paths in examples and documentation. Discover game and Steam library locations at runtime.
- Keep commits focused. Exclude personal data, machine-specific paths, game files, proprietary PhysX binaries and generated modules, credentials, saves, profiling captures, and unrelated experiments.
