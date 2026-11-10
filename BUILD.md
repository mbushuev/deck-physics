# Build the Steam Deck installer

Use a Linux x86-64 build host with Python 3.9 or later, a C compiler and GNU-compatible linker. See the [installation requirements](docs/installation.md#requirements) for the Steam Deck environment.

From a clean checkout, run the builder on a Linux x86-64 host.

```sh
python3 Build-DeckPhysX.py
```

The builder downloads the pinned [Proton-ZLUDA release asset][release], verifies the archive and each extracted file against `upstream.json`, and compiles the HIP wait library. Use `--proton ../inputs/Proton-ZLUDA.tar.gz` to build with a local copy of the same asset. The Steam launch uses the Valve compatibility tool selected by the user. PhysX binaries are installed locally on the Deck.

## Versions and releases

[`VERSION`](VERSION) records the project version. The installer archive includes that file and the documentation. For version `0.1.0`, the default filename is `DeckPhysX-Proton11-0.1.0.tar.gz`.

The [Build installer](.github/workflows/build.yml) workflow uploads the versioned installer and corresponding source archives with their SHA-256 checksums. A matching tag such as `v0.1.0` on a tested commit from `main` publishes those files as GitHub Release assets. Update `VERSION` and the README version before tagging a new release.

To build the corresponding source archive on its own, run `python3 Build-DeckPhysX.py --sources-only`. See [third-party software and corresponding source](licenses/SOURCES.md) for its contents and the bundled license notices.

## Sources and updates

The pinned [Proton-ZLUDA source](https://github.com/chkuendig/Proton-ZLUDA/tree/799caed86a971786a0697e7dbe2b35e2df37d171) builds [Wine e60892c](https://github.com/ValveSoftware/wine/tree/e60892cc2398b0a83c332a2078c7b85e47bdb42b), [ZLUDA-Wine bf80022](https://github.com/chkuendig/zluda-wine/tree/bf80022f07cf66fbec96445cf77c12d2081c32ee), [ZLUDA 39ef5ce](https://github.com/chkuendig/ZLUDA/tree/39ef5ce92bb7c2363ba756b3316b8cfce65d5b65), [DXVK-NVAPI f9fdf26](https://github.com/jp7677/dxvk-nvapi/tree/f9fdf268e888d17ae9875a4f01908164ff05f740), and [numactl 2.0.18](https://github.com/numactl/numactl/tree/v2.0.18). The upstream dependency lock is [`make/zluda-deps.json`](https://github.com/chkuendig/Proton-ZLUDA/blob/799caed86a971786a0697e7dbe2b35e2df37d171/make/zluda-deps.json). The bridge repository carries the Wine and NVAPI patches. The source equivalent of the local PE32 patch is `alice-pe32-null-host-free.patch`.

ZLUDA pins [Christian's LLVM fork at c83b929](https://github.com/chkuendig/llvm-project/tree/c83b929aeff0aa6b9877c6712e9914d1275b1d36).

Update the input pins on a separate branch. Check the Wine ABI, test both game launches and run the same PhysX High scenes before merging. Build releases from `main` and provide upstream notices and corresponding source for redistributed components.

[release]: https://github.com/chkuendig/Proton-ZLUDA/releases/tag/proton-zluda-11.0-20261108-799caed8
