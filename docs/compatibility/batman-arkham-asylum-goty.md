# Batman: Arkham Asylum GOTY

Steam App ID **35140**. Startup verified on Steam Deck OLED with Valve Proton 11.0-2e. [Test environment](README.md)

## Reference performance

The development build averaged **87.56 FPS** over 80 seconds of the built-in benchmark with PhysX High at 1280×787. The Deck was on AC power with automatic GPU clocks and frame limits disabled for the scored interval. The final five seconds averaged 71.8 FPS. The 99th-percentile frame time was 19.16 ms.

This is a benchmark result from the development runtime. Campaign scenes and frame-limit settings can yield different results.

## Battery performance

Four 80-second runs of the same built-in benchmark used Valve Proton 11.0-2e in Gaming Mode, battery power, PhysX High, matching screen brightness, automatic GPU clocks, and a 60 FPS cap.

| Development setup | Average FPS | Whole-device draw |
| --- | ---: | ---: |
| Unmodified Proton-ZLUDA stack | 59.23 | 12.89 W |
| Deck PhysX profile | 59.29 | 12.17 W |

The Deck PhysX profile used the graphics mask, cloth collision changes, and blocking waits. Together they reduced average draw by **0.72 W (5.6%)** in this comparison. A separate uncapped comparison of the wait policy alone saved **0.52 W** on average at similar frame rates.

## Profile details

- Uses PhysX 2.8.1.58 from the game's Proton prefix. If the required runtime is missing, the installer offers to set it up separately.
- The development profile used separate patches for collision bounds, triangle group rejection, and direct triangle and shape reads. The collision patches use a module generated from the installed PhysX library.
- The graphics mask and blocking HIP waits can be selected independently when their [patch files](../installation.md#optional-game-patches) are supplied.
