# Installation

Deck Physics bundles compatibility components and configures how Steam starts your installed games. Setup reuses verified NVIDIA PhysX files or obtains them from NVIDIA on the Deck. See [how games launch](compatibility/README.md#how-games-launch) for the components used at runtime.

## Requirements

- Steam Deck running SteamOS with its built-in Steam client and at least one game from the [tested compatibility list](compatibility/README.md) installed through Steam.
- **Valve Proton 11.0-2e** (11.0.2) and **Steam Linux Runtime 4**. In Steam, open each game's **Properties → Compatibility**, select **Proton 11.0**, and let Steam finish installing the compatibility tool and runtime. Setup and launch both check for the exact Proton build.
- Desktop Mode and your regular user account for setup. The installer uses Python 3.11 or later, GTK 3 with PyGObject, Bubblewrap with read-only overlay support, 7-Zip, KDialog, and Zenity. The optional FPS counter uses MangoHud.

## Get the installer

Setup uses a single installer `.tar.gz`. Download it from **Releases** when a tagged release is available. For a development build, sign in to GitHub and open **Actions → Build installer**. Open a successful run with available artifacts, download `DeckPhysics-Proton11-<version>`, and extract the ZIP to get the installer `.tar.gz`.

## Install and launch

1. Close the games. In Desktop Mode, extract the installer `.tar.gz` and run `Install.sh` from the extracted folder. From Konsole in that folder, run `./Install.sh`.
2. Choose **Download Package** to download the official **NVIDIA PhysX 9.23.1019** package (about 29 MB). The progress window shows the download and SHA-256 verification. Setup reuses a verified local copy when available.
3. The top of the setup window shows the package status. Use **Check package** to verify it again or **Download package** when a verified copy is missing. Select each game to review its **Launch options** and **Patches**. **Skip intro videos** and **Show FPS counter** start enabled on first setup. New patches start unchecked. Click **Continue** to apply your selections.
4. Setup checks for the package if Alice or any selected Batman patch needs files that are missing. Review the license prompt when shown. If you chose **Skip Package**, setup leaves out the parts that still need it.
5. Copy the full command from the setup summary, including `%command%`. Paste it into **Properties → General → Launch Options** for each game listed in the summary.
6. Launch the game from Steam in Desktop Mode or Gaming Mode. Set **PhysX High** in the game to match the reference tests. Use Steam's performance menu to control its overlay and frame limit. The installer's **Show FPS counter** controls the MangoHud overlay requested by Deck Physics.

Run `Install.sh` again to change the settings. To return to a standard launch, restore your previous Steam launch options or clear the field if it was empty before setup.

## Optional game patches

The installer includes two optional patches for each tested game.

- **Six-CU graphics mask** limits graphics shaders to six compute units. Physics compute can still use all eight.
- **Blocking GPU waits** lets the CPU sleep while waiting for GPU work, which can reduce power draw.

### Add your own patches

Copy the game folder into `patches/` beside `Install.sh` and keep each patch archive zipped. The installer matches patches by Steam App ID.

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

Use **Search games** to find a game and select a patch row to see its details and dependencies. Use **Refresh patches** after copying, updating, or removing files while setup is open. It rescans the local folder and keeps selections for unchanged archives. New and changed archives start unchecked. Select files you trust, since enabled patches can run code during setup or launch. See the [package format](build.md#game-patch-format) to make a patch.
