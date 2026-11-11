# Tested compatibility

| Game profile | Steam App ID | Startup on Steam Deck OLED | Performance reference |
| --- | --- | --- | --- |
| [Batman: Arkham Asylum GOTY](batman-arkham-asylum-goty.md) | 35140 | Passed | **82.63 FPS** in the built-in benchmark with the graphics mask |
| [Alice: Madness Returns](alice-madness-returns.md) | 19680 | Passed | **77.05 FPS** in a Ruin encounter with the graphics mask |

Startup validation used SteamOS 3.9.5 in Desktop Mode with Valve Proton 11.0-2e and Steam Linux Runtime 4. Both games reached the title screen with intro skipping and the FPS counter enabled, then again with both settings disabled. The FPS values are averages from separate development tests with PhysX High. Each game page records the scene, settings, and patch configuration.

The installer configures the profiles listed here. Other titles may work with the upstream compatibility stack and have yet to be validated on Deck.

See the [installation guide](../installation.md) for setup requirements.

## How games launch

Deck Physics packages components from [Proton-ZLUDA](../build.md#sources-and-updates) for games launched with Valve Proton. The original NVIDIA PhysX runtime handles the simulation. ZLUDA translates its CUDA calls for the AMD GPU.

The launcher uses read-only mounts to supply the CUDA bridge, DXVK-NVAPI, and a compatible Wine component for the game session. It applies the Alice compatibility fix to a temporary copy of the 32-bit CUDA bridge. The game executables and NVIDIA PhysX libraries are used as supplied. The optional [Blocking GPU waits patch](../installation.md#optional-game-patches) uses a Deck Physics library to set the wait policy before GPU queues are created.

PhysX is a trademark of NVIDIA Corporation. Deck Physics is an independent project.
