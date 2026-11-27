# Mafia II Classic

The development installer detects the original game under Steam App ID **50130** and its `pc/mafia2.exe`. Mafia II: Definitive Edition uses a different executable and profile.

## Setup

1. Launch the game from Steam once so its original prerequisites can finish installing, then close it.
2. In Deck Physics, select **Mafia II (Classic)** and choose **Set Up Game**. The optional **Six-CU graphics mask** and **Blocking GPU waits** use the same components as the other profiles.
3. Paste the launch command into the game's Steam launch options. Select **Proton 11.0** in Steam and set **APEX PhysX** to **High** in the game. See [Proton updates](../installation.md#proton-updates) for the GPU bridge requirements.

The profile uses the installed game and its PhysX files. It can show the FPS counter and skip `Logos.bik` and `NVidia_logo.bik` for the game session. Other videos stay available.

## Experimental performance work

The base profile can run compatible PhysX workloads through the GPU bridge. Mafia II's APEX clothing route, inactive profiling guard, selected HIP fill and vertex packing experiments act on specific versions of the game and physics modules. The base profile uses the original clothing route and game code. A performance package for those experiments would need its own game and input verification and can be developed separately from this installer.
