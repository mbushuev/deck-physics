# Installation

## Requirements

- Steam Deck running SteamOS with the native Steam client. See [tested compatibility](compatibility/README.md) for the validated hardware and game profiles.
- The exact **Valve Proton 11.0-2e** build (11.0.2) and **Steam Linux Runtime 4**. Select **Proton 11.0** under the game's **Properties → Compatibility** and let Steam finish both downloads. Deck Physics checks the Proton version and Wine binary before launch.
- Desktop Mode and your regular user account for setup. The installer uses Python 3.11 or later, GTK 3 with PyGObject, Bubblewrap, 7-Zip, KDialog, and Zenity from SteamOS. Batman's optional collision optimization uses `liblz4.so.1`. The optional FPS counter uses MangoHud.
- Internet access if the installer needs to download files for a game. Each [game profile](compatibility/README.md) describes its requirements.

## Setup

1. Close the games and extract the installer. Copy any [optional game patch folders](#optional-game-patches) before running `Install.sh` in Desktop Mode. See [BUILD.md](../BUILD.md) to build the installer from source.
2. Choose a game from the list, then select its launch options and patches. **Skip intro videos** and **Show FPS counter** start enabled for each game. New patch files start unchecked. Run the installer again to change your selection.
3. Complete any game-specific setup prompts. Copy the displayed line into **Launch Options** for each game listed in the installer summary.
4. Launch from Steam in Desktop Mode or Gaming Mode. Select **PhysX High** in the game to use the settings in the reference measurements. Steam's performance overlay and frame limit use their existing settings.

To return to a standard Steam launch, clear the Deck Physics entry from the game's **Launch Options**.

## Optional game patches

The installer includes the optional **Six-CU graphics mask** and **Blocking GPU waits** for each tested game. To add patches, merge each additional game's folder into `patches/` beside `Install.sh`.

```text
Install.sh
patches/
  batman-arkham-asylum-goty/
    gpu-mask.deckphysx.zip
    blocking-wait.deckphysx.zip
  alice-madness-returns/
    gpu-mask.deckphysx.zip
    blocking-wait.deckphysx.zip
```

Keep the patch files zipped. Select a game in the list or use **Search games** to find it. Select a patch row to see its details and dependencies. Use **Refresh patches** after copying, updating or removing files while setup is open. Setup rescans the local `patches/` folder and keeps selections for archives that match the previous scan. New and changed archives start unchecked. Select files you trust, since enabled patches can run code during installation or launch. See the [package format](../BUILD.md#game-patch-format) to make a patch.
