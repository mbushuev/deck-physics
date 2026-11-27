# Tested compatibility

| Game profile | Steam App ID | Launch paths tested on Steam Deck OLED | Performance reference |
| --- | --- | --- | --- |
| [Batman: Arkham Asylum GOTY](batman-arkham-asylum-goty.md) | 35140 | Steam library | **82.63 FPS** in the built-in benchmark with the graphics mask |
| [Alice: Madness Returns](alice-madness-returns.md) | 19680 | Steam library and Non-Steam shortcut | **77.05 FPS** in a Ruin encounter with the graphics mask |
| [Mafia II Classic](mafia-ii-classic.md) | 50130 | Steam library | **76.7 FPS** in the built-in benchmark with GPU Clothing and accelerated render packing |

Startup validation used SteamOS 3.9.5 in Desktop Mode with Valve Proton 11.0-2e and Steam Linux Runtime 4. Batman and Alice reached the title screen with intro skipping and the FPS counter enabled, then again with both settings disabled. The FPS values are averages from separate development tests with PhysX High. Each game page records the scene, settings, and patch configuration.

The installer configures the profiles listed here. Other titles may work with the upstream compatibility stack and have yet to be validated on Deck.

See the [installation guide](../installation.md) for setup requirements.

## How games launch

Deck Physics packages components from [Proton-ZLUDA](../build.md#sources-and-updates) for games launched with Valve Proton. The original NVIDIA PhysX runtime handles the simulation. ZLUDA translates its CUDA calls for the AMD GPU.

The launcher uses read-only mounts to supply the CUDA bridge, DXVK-NVAPI, and a compatible Wine component for the game session. The launcher [checks the selected Wine binaries and available Proton installations](../installation.md#proton-updates). It applies the Alice compatibility fix to a temporary copy of the 32-bit CUDA bridge. Optional patches can generate runtime files locally and mount them read-only for a session. Installed game files stay intact. The optional [Blocking GPU waits patch](../installation.md#optional-game-patches) uses a Deck Physics library to set the wait policy before GPU queues are created.

PhysX is a trademark of NVIDIA Corporation. Deck Physics is an independent project.
