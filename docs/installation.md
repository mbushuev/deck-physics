# Installation

## Requirements

- Steam Deck running SteamOS with the native Steam client. See [tested compatibility](compatibility/README.md) for the validated hardware and game profiles.
- The exact **Valve Proton 11.0-2e** build (11.0.2) and **Steam Linux Runtime 4**. Select **Proton 11.0** under the game's **Properties → Compatibility** and let Steam finish both downloads. Deck PhysX checks the Proton version and Wine binary before launch.
- Desktop Mode and your regular user account for setup. The installer uses Python 3.11 or later, Bubblewrap, 7-Zip, KDialog, and Zenity from SteamOS. The optional FPS counter uses MangoHud.
- Internet access if the installer needs to download files for a game. Each [game profile](compatibility/README.md) describes its requirements.

## Setup

1. Close the games, extract the installer, and run `Install.sh` in Desktop Mode. See [BUILD.md](../BUILD.md) to build a package from source.
2. Choose the launch options you want. **Skip intro videos** and **Show FPS counter** start enabled. **Optimize performance and battery use** starts off. Run the installer again to change your selection.
3. Complete any game-specific setup prompts. Copy the displayed line into **Launch Options** for each game listed in the installer summary.
4. Launch from Steam in Desktop Mode or Gaming Mode. Select **PhysX High** in the game to use the settings in the reference measurements. Steam's performance overlay and frame limit use their existing settings.

To return to a standard Steam launch, clear the Deck PhysX entry from the game's **Launch Options**.

## Optional performance and battery optimizations

Selecting **Optimize performance and battery use** tunes GPU scheduling and reduces CPU activity while waiting for GPU work. With the option off, both profiles use the base GPU PhysX bridge. NVIDIA's license prompt for the PhysX download is separate from this choice.
