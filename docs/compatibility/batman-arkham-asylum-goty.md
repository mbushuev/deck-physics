# Batman: Arkham Asylum GOTY

Steam App ID **35140**. Startup verified on Steam Deck OLED with Valve Proton 11.0-2e. [Test environment](README.md)

## Reference performance

The built-in benchmark ran with PhysX High at 1280×787 on AC power, with automatic GPU clocks and frame limits disabled for the scored 80 seconds.

| Test configuration | Average FPS | Final five seconds | 99th-percentile frame time |
| --- | ---: | ---: | ---: |
| Default graphics scheduling | 71.25 | 55.0 FPS | 21.49 ms |
| Six-CU graphics mask | 82.63 | 71.4 FPS | 18.56 ms |

Both runs used the same bridge and PhysX runtime. Campaign performance varies by scene and frame-limit settings.

## Battery performance

The bundled **Blocking GPU waits** patch lets CPU threads sleep while waiting for GPU work. Enable it under [Patches](../installation.md#optional-game-patches).

## Profile details

- Starts the original game executable in Valve Proton using the [shared launch setup](README.md#how-games-launch).
- Uses registered PhysX 2.8.1.58 from the game's Proton prefix. If it is missing, **Set Up Batman** uses a verified cached copy of the NVIDIA installer or downloads it, then runs it in the game's prefix after license acceptance.
- The installer includes the [Six-CU graphics mask](../installation.md#optional-game-patches) as a separate option.
