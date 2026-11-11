# Alice: Madness Returns

Steam App ID **19680**. Startup verified on Steam Deck OLED with Valve Proton 11.0-2e. [Test environment](README.md)

## Reference performance

The development build averaged **77.05 FPS** over a 15-second Ruin encounter with PhysX High. The test used the Six-CU graphics mask, automatic GPU clocks, and the default renderer settings. The player fired the Pepper Grinder and dodged during the capture. The 99th-percentile frame time was 15.41 ms.

This is a gameplay sample from the development runtime. Effects, camera position, and player movement change the workload during a fight.

## Battery performance

The bundled **Blocking GPU waits** patch lets CPU threads sleep while waiting for GPU work. Enable it under [Patches](../installation.md#optional-game-patches).

## Profile details

- Uses NVIDIA PhysX 2.8.4.11 and a WoW64 bridge fix for `cuMemFreeHost(NULL)`. A read-only overlay makes the verified NVIDIA runtime DLLs available in the game directory for this launch. The installed game files remain unchanged.
- The installer includes the [Six-CU graphics mask](../installation.md#optional-game-patches) as a separate option.
- Reuses verified PhysX files from Steam Proton prefixes or a previous Deck Physics installation. If the files are missing, **Set Up Alice** extracts them from NVIDIA PhysX 9.23.1019 after license acceptance. Setup reuses a verified cached installer when available or downloads about 29 MB from NVIDIA. Choosing **Skip Alice** leaves the profile out of setup until the required files are available.
