# Build the Steam Deck installer

Use a Linux x86-64 build host with Python 3.9 or later, a C compiler, and a GNU-compatible linker. See the [installation requirements](installation.md#requirements) for the Steam Deck environment.

From the root of a clean checkout, run the builder.

```sh
python3 packaging/Build-DeckPhysics.py
```

The builder downloads the pinned [Proton-ZLUDA release asset][release] and verifies the archive and each selected runtime file against [the input manifest](../packaging/upstream.json). Use `--proton ../inputs/Proton-ZLUDA.tar.gz` to build with a local copy of the same asset. It compiles the HIP wait library from `packaging/native/hip-wait-startup.c` and uses `packaging/bundled-patches/` to create the optional game patch files. The Steam launch uses the Valve compatibility tool selected by the user. PhysX binaries are installed locally on the Deck.

## Versions and releases

[`VERSION`](../VERSION) records the project version. The installer archive includes that file and the documentation. For version `0.1.0`, the default filename is `DeckPhysics-Proton11-0.1.0.tar.gz`.

The **Build installer** workflow in GitHub Actions uploads separate versioned ZIP downloads for the installer and the corresponding source archive. Each ZIP contains its `.tar.gz` and SHA-256 checksum. A matching tag such as `v0.1.0` on a tested commit from `main` publishes the two `.tar.gz` files, their checksums, and the versioned SVG poster.

Before tagging a release, update `VERSION` and the README version, add an entry to [the changelog](../CHANGELOG.md), and write the release notes in `docs/release-notes/<version>.md`. Use `0.1.1` for a fix release and `0.2.0` for a feature release in the initial series.

Save each poster as `.github/artwork/releases/deck-physics-<version>.svg`. Keep the [project mark](media/deck-physics-mark.svg), a solid background, the project name, and the version. Preserve earlier posters. The release workflow embeds the new poster and uses that version's notes.

After both uploads succeed, Actions keeps the new pair and removes superseded installer and source artifacts from completed runs of this workflow. Tagged builds clean up after publication. Pull requests from forks build the package for verification.

To build the corresponding source archive on its own, run `python3 packaging/Build-DeckPhysics.py --sources-only`. That archive contains the [source inputs for bundled LGPL components](../licenses/SOURCES.md). Use a checkout of this repository to build the installer itself.

## Game patch format

A `.deckphysx.zip` file in `patches/<game>/` contains `patch.json` and an optional `files/` payload. Each archive describes one patch for one Steam App ID.

Deck Physics bundles the graphics mask and blocking GPU waits. Additional patch downloads can ship as a versioned per-game ZIP with a `patches/<game>/` directory. Document the supported game version and prerequisites, then follow the [patch installation steps](installation.md#add-your-own-patches).

```json
{
  "format": 1,
  "id": "gpu-mask",
  "app_id": "35140",
  "title": "Six-CU graphics mask",
  "description": "Limits graphics shaders to six compute units.",
  "environment": {"AMD_CU_MASK": "0x3f"}
}
```

`format`, `id`, `app_id`, `title`, and `description` are required. Use the integer `1` for `format` and a string for the numeric Steam App ID. Patch IDs consist of lowercase letters and digits with optional hyphen separators. Each ID must be unique per game. Optional fields apply only when the patch is selected.

- `requires` lists other patch IDs that must also be selected for the same game.
- `details` provides additional plain text for the patch details panel. Line breaks are supported.
- `environment` supplies launch environment variables. Enabled patches for one game must use distinct variable names.
- `file_environment` supplies environment variables pointing to files relative to the extracted payload. Paths use `/` and cannot traverse outside the payload.
- `preload` is the relative path to a Linux shared library from the payload.
- `prepare` is the relative path to a Python script in the payload. The installer runs it in the patch directory with the Proton prefix and game executable paths as positional arguments. It can generate files referenced by `file_environment` or `preload`.
- `requires_nvidia_physx` is a boolean for Batman patches that need the runtime from the official NVIDIA PhysX package. Set it to `false` for preparation scripts that do not use that runtime. For compatibility with existing archives, Batman patches with a `prepare` script default to `true` when the field is omitted. Other patches default to `false`.

## Sources and updates

The pinned [Proton-ZLUDA source](https://github.com/chkuendig/Proton-ZLUDA/tree/799caed86a971786a0697e7dbe2b35e2df37d171) builds [Wine e60892c](https://github.com/ValveSoftware/wine/tree/e60892cc2398b0a83c332a2078c7b85e47bdb42b), [ZLUDA-Wine bf80022](https://github.com/chkuendig/zluda-wine/tree/bf80022f07cf66fbec96445cf77c12d2081c32ee), [ZLUDA 39ef5ce](https://github.com/chkuendig/ZLUDA/tree/39ef5ce92bb7c2363ba756b3316b8cfce65d5b65), [DXVK-NVAPI f9fdf26](https://github.com/jp7677/dxvk-nvapi/tree/f9fdf268e888d17ae9875a4f01908164ff05f740), and [numactl 2.0.18](https://github.com/numactl/numactl/tree/v2.0.18). The upstream dependency lock is [`make/zluda-deps.json`](https://github.com/chkuendig/Proton-ZLUDA/blob/799caed86a971786a0697e7dbe2b35e2df37d171/make/zluda-deps.json). The bridge repository carries the Wine and NVAPI patches. See the [Alice bridge patch](../packaging/upstream-patches/alice-pe32-null-host-free.patch) for the source equivalent of the local PE32 fix.

ZLUDA pins [Christian's LLVM fork at c83b929](https://github.com/chkuendig/llvm-project/tree/c83b929aeff0aa6b9877c6712e9914d1275b1d36).

Update the input pins on a separate branch. Check the Wine ABI, test both game launches and run the same PhysX High scenes before merging. Build releases from `main` and provide upstream notices and corresponding source for redistributed components.

[release]: https://github.com/chkuendig/Proton-ZLUDA/releases/tag/proton-zluda-11.0-20261108-799caed8
