# Build the Steam Deck installer

Use a Linux x86-64 build host with Python 3.9 or later, a C compiler and GNU-compatible linker. On Steam Deck, installation uses Python 3.11 or later, Bubblewrap, 7-Zip, KDialog and Zenity from SteamOS.

Download `Proton-ZLUDA.tar.gz` from [chkuendig/Proton run 42497068005](https://github.com/chkuendig/Proton/actions/runs/42497068005) and the `GE-Proton11-7-zluda` ZIP artifact from [chkuendig/proton-ge-custom run 40906607864](https://github.com/chkuendig/proton-ge-custom/actions/runs/40906607864). Keep both inputs outside the source tree. Name the downloaded ZIP `GE-Proton11-7-zluda.zip`.

```sh
python3 Build-DeckPhysX.py \
  --proton ../inputs/Proton-ZLUDA.tar.gz \
  --ge ../inputs/GE-Proton11-7-zluda.zip
```

The script checks the archives and each extracted file against `upstream.json`, builds the HIP wait library, and creates `DeckPhysX-Proton11.tar.gz`. The GE archive supplies only `libnuma.so.1`. The Steam launch uses the Valve compatibility tool selected by the user. PhysX binaries are installed locally on the Deck.

## Sources and updates

The pinned [Proton workflow](https://github.com/chkuendig/Proton/blob/f8fe8a3d3fd83bad0c2285d31aa18374015119e7/.github/workflows/zluda.yml) builds [Wine e60892c](https://github.com/ValveSoftware/wine/tree/e60892cc2398b0a83c332a2078c7b85e47bdb42b), [ZLUDA-Wine bf80022](https://github.com/chkuendig/zluda-wine/tree/bf80022f07cf66fbec96445cf77c12d2081c32ee), [ZLUDA a309364](https://github.com/chkuendig/ZLUDA/tree/a309364cd2fc004d68bc409c331d7b411acc77cc) and [DXVK-NVAPI f9fdf26](https://github.com/jp7677/dxvk-nvapi/tree/f9fdf268e888d17ae9875a4f01908164ff05f740) together. The bridge repository carries the Wine and NVAPI patches. The source equivalent of the local PE32 patch is `alice-pe32-null-host-free.patch`.

Update the input pins on a separate branch. Check the Wine ABI, test both game launches and run the same PhysX High scenes before merging. Build releases from `main`. Before distributing a release, provide durable build inputs or a verified rebuild recipe, upstream notices, and the corresponding source for redistributed components. GitHub Actions artifacts expire.
