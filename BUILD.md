# Build the Steam Deck installer

Use a Linux x86-64 build host with Python 3.9 or later and a C compiler. See the [installation requirements](docs/installation.md#requirements) for the Steam Deck environment.

From a clean checkout, run the builder.

```sh
python3 Build-DeckPhysX.py
```

The builder downloads the pinned [Proton-ZLUDA release asset][release] and verifies the archive and each selected runtime file against `upstream.json`. Use `--proton ../inputs/Proton-ZLUDA.tar.gz` to build with a local copy of the same asset. It builds the HIP wait library from `native/hip-wait-startup.c` and uses `bundled-patches/` to create the optional game patch files. The Steam launch uses the Valve compatibility tool selected by the user. PhysX binaries are installed locally on the Deck.

## Versions and releases

[`VERSION`](VERSION) records the project version. The installer archive includes that file and the documentation. For version `0.1.0`, the default filename is `DeckPhysX-Proton11-0.1.0.tar.gz`.

The [Build installer](.github/workflows/build.yml) workflow uploads two separate artifacts, `DeckPhysX-Proton11` for the installer and `DeckPhysX-Proton11-sources` for the corresponding source archive. Each includes its SHA-256 checksum. A matching tag such as `v0.1.0` on a tested commit from `main` publishes those files as GitHub Release assets. Update `VERSION` and the README version before tagging a new release.

After both uploads succeed, Actions keeps the new pair and removes superseded installer and source artifacts from completed runs of this workflow. Tagged builds clean up after publication. Pull requests from forks build the package for verification.

To build the corresponding source archive on its own, run `python3 Build-DeckPhysX.py --sources-only`. See [third-party software and corresponding source](licenses/SOURCES.md) for its contents and the bundled license notices.

## Game patch format

A `.deckphysx.zip` file in `patches/<game>/` contains `patch.json` and an optional `files/` payload. Each archive describes one patch for one Steam App ID.

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

`format`, `id`, `app_id`, `title` and `description` are required. IDs use lowercase letters, digits and hyphens and must be unique per game. Optional fields apply only when the patch is selected.

- `requires` lists other patch IDs that must also be selected for the same game.
- `details` provides additional plain text for the patch details panel. Line breaks are supported.
- `environment` supplies launch environment variables. Enabled patches for one game must use distinct variable names.
- `file_environment` supplies environment variables pointing to files relative to the extracted payload. Paths use `/` and cannot traverse outside the payload.
- `preload` is the relative path to a Linux shared library from the payload.
- `prepare` is the relative path to a Python script in the payload. The installer runs it in the patch directory with the Proton prefix and game executable paths as positional arguments. It can generate files referenced by `file_environment` or `preload`.

## Sources and updates

The pinned [Proton-ZLUDA source](https://github.com/chkuendig/Proton-ZLUDA/tree/799caed86a971786a0697e7dbe2b35e2df37d171) builds [Wine e60892c](https://github.com/ValveSoftware/wine/tree/e60892cc2398b0a83c332a2078c7b85e47bdb42b), [ZLUDA-Wine bf80022](https://github.com/chkuendig/zluda-wine/tree/bf80022f07cf66fbec96445cf77c12d2081c32ee), [ZLUDA 39ef5ce](https://github.com/chkuendig/ZLUDA/tree/39ef5ce92bb7c2363ba756b3316b8cfce65d5b65), [DXVK-NVAPI f9fdf26](https://github.com/jp7677/dxvk-nvapi/tree/f9fdf268e888d17ae9875a4f01908164ff05f740), and [numactl 2.0.18](https://github.com/numactl/numactl/tree/v2.0.18). The upstream dependency lock is [`make/zluda-deps.json`](https://github.com/chkuendig/Proton-ZLUDA/blob/799caed86a971786a0697e7dbe2b35e2df37d171/make/zluda-deps.json). The bridge repository carries the Wine and NVAPI patches. The source equivalent of the local PE32 patch is `alice-pe32-null-host-free.patch`.

ZLUDA pins [Christian's LLVM fork at c83b929](https://github.com/chkuendig/llvm-project/tree/c83b929aeff0aa6b9877c6712e9914d1275b1d36).

Update the input pins on a separate branch. Check the Wine ABI, test both game launches and run the same PhysX High scenes before merging. Build releases from `main` and provide upstream notices and corresponding source for redistributed components.

[release]: https://github.com/chkuendig/Proton-ZLUDA/releases/tag/proton-zluda-11.0-20261108-799caed8
