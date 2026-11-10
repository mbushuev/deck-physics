# Deck PhysX

GPU PhysX profiles for Batman: Arkham Asylum GOTY and Alice: Madness Returns on Steam Deck. Both profiles use the ZLUDA WoW64 bridge, a graphics CU mask of `0x3f`, and blocking HIP waits set before queue creation.

## Upstream projects

Deck PhysX builds on Christian's (`chkuendig`) Proton-ZLUDA stack. We use its CUDA components with Steam's Valve Proton and add the installer, game profiles, and local compatibility and performance patches.

- [Proton-ZLUDA](https://github.com/chkuendig/Proton-ZLUDA) supplies the release used to build Deck PhysX.
- [zluda-wine](https://github.com/chkuendig/zluda-wine) provides the Wine WoW64 CUDA bridge.
- [ZLUDA](https://github.com/chkuendig/ZLUDA) provides the CUDA backend for AMD GPUs.
- [llvm-project](https://github.com/chkuendig/llvm-project) provides the LLVM compiler backend used by ZLUDA.

Thanks to Christian for developing and sharing this work. See [BUILD.md](BUILD.md#sources-and-updates) for the exact revisions.

## Requirements

- An x86-64 Steam Deck running SteamOS with the native Steam client and at least one supported game installed.
- The exact **Valve Proton 11.0-2e** build (11.0.2). In each game's **Properties → Compatibility**, select **Proton 11.0** and let Steam finish installing it and **Steam Linux Runtime 4**. Deck PhysX checks the Proton version and Wine binary before launch.
- Desktop Mode for installation as your regular user. The installer uses Python 3.11 or later, Bubblewrap, 7-Zip, KDialog and Zenity from SteamOS. The optional FPS counter uses MangoHud.
- Internet access if the installer needs to download NVIDIA PhysX. Set the game's PhysX option to **High** and launch from Steam.

## Install

1. Close both games, extract the installer archive, and run `Install.sh` in Desktop Mode.
2. Choose whether to skip startup videos and whether to show the Deck PhysX FPS and frame-time counter. Both options start enabled. The choices apply to the games configured by the installer. Run `Install.sh` again to change them.
3. If prompted, choose which games to set up with NVIDIA PhysX. Copy the displayed line into **Launch Options** for each game listed in the installer summary.
4. Launch the game from Steam in Desktop Mode or Gaming Mode. Frame limits and Steam's performance overlay follow your Steam and game settings.

### NVIDIA PhysX files

The installer first looks for verified files already on the Deck. Alice uses PhysX 2.8.4.11 and the bridge patch for `cuMemFreeHost(NULL)`. If the files are missing, choose **Set Up Alice** to use the NVIDIA PhysX 9.23.1019 installer. Deck PhysX reuses a verified cached copy when available or downloads about 29 MB from NVIDIA. It shows the NVIDIA license before using the installer. If you skip Alice or decline the license, Deck PhysX cannot launch Alice until you run the installer again and complete its setup.

Batman uses PhysX 2.8.1 from its Proton prefix. If Batman's prefix needs PhysX, the installer asks separately. A ready Batman installation can proceed when Alice is skipped. Both games use their existing Steam prefixes and campaign saves.

To return to the standard Steam launch, clear the Deck PhysX entry from the game's Launch Options. Steam will then use the compatibility tool selected in the game's properties.

See [BUILD.md](BUILD.md) for source and build details and [AGENTS.md](AGENTS.md) for the repository workflow.
