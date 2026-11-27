# Mafia II Classic

Deck Physics detects the Steam release of Mafia II Classic under App ID **50130**.
The GPU Clothing patch targets this release and its installed PhysX 2.8.3 runtime.
Mafia II: Definitive Edition is outside the tested profile.

## Setup

1. Launch the game from Steam once so its original prerequisites can finish installing, then close it.
2. In Deck Physics, select **Mafia II (Classic)**. Click **Download patches**, select
   **GPU Clothing**, **Six-CU graphics mask**, and **Blocking GPU waits**, then click **Set Up Game**.
3. Paste the resulting command into the game's Steam launch options. Select **Proton 11.0**
   in Steam and set **APEX PhysX** to **High** in the game. See
   [Proton updates](../installation.md#proton-updates) for the GPU bridge requirements.

The profile can show the FPS counter and skip the publisher and NVIDIA intro videos.
The GPU Clothing patch prepares compatible files from the installed game and
mounts them for the session. The game runs its original executable.

## Performance reference

The built-in benchmark averaged **73.8 FPS** on a Steam Deck OLED on battery
with GPU clocks in automatic mode. The run used 1280 × 800, Valve Proton 11.0-2e,
APEX PhysX High, all effects, the three patches above, and VSync and antialiasing
off. Returning to the main menu from gameplay and interrupting the benchmark
were also verified with the patch active.

See the [GPU Clothing patch and benchmark details](https://github.com/mbushuev/deck-physics-patches/blob/main/docs/mafia-ii-benchmarks.md).
