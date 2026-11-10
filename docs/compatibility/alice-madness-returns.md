# Alice: Madness Returns

Steam App ID **19680**. Startup verified on Steam Deck OLED with Valve Proton 11.0-2e. [Test environment](README.md)

## Reference performance

The development build averaged **77.05 FPS** over a 15-second Ruin encounter with PhysX High. The player fired the Pepper Grinder and dodged during the capture. The GPU used automatic clocks and the default renderer. The 99th-percentile frame time was 15.41 ms.

This is a gameplay sample from the development runtime. Effects, camera position, and player movement change the workload during a fight.

## Battery performance

The optional blocking wait patch uses the same startup wait policy as Batman to reduce CPU activity while waiting for GPU work. Battery draw in Alice is outside the current paired-test coverage.

## Profile details

- Uses NVIDIA PhysX 2.8.4.11 and a WoW64 bridge fix for `cuMemFreeHost(NULL)`.
- The graphics mask and blocking HIP waits can be selected independently when their [patch files](../installation.md#optional-game-patches) are supplied.
- Reuses verified PhysX files already on the Deck. If they are missing, **Set Up Alice** offers NVIDIA PhysX 9.23.1019, about 29 MB if a download is needed. The installer presents the NVIDIA license before using the package. Skipping setup leaves the Alice profile unavailable until its PhysX files are set up.
