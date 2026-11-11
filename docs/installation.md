# Installation

Deck Physics bundles compatibility components and configures how Steam starts your installed games. Setup reuses verified NVIDIA PhysX files or obtains them from NVIDIA on the Deck. See [how games launch](compatibility/README.md#how-games-launch) for the components used at runtime.

## Requirements

- Steam Deck running SteamOS with its built-in Steam client and a copy of a game from the [tested compatibility list](compatibility/README.md).
- **Valve Proton 11.0-2e** (11.0.2) and **Steam Linux Runtime 4**. In Steam, open each game's **Properties → Compatibility**, select **Proton 11.0**, and let Steam finish installing the compatibility tool and runtime. Setup and launch both check for the exact Proton build.
- Desktop Mode and your regular user account for setup. The installer uses Python 3.11 or later, GTK 3 with PyGObject, Bubblewrap with read-only overlay support, 7-Zip, KDialog, and Zenity. The optional FPS counter uses MangoHud.

## Get the installer

Setup uses a single installer `.tar.gz`. Download it from **Releases** when a tagged release is available. For a development build, sign in to GitHub and open **Actions → Build installer**. Open a successful run with available artifacts, download `DeckPhysics-Proton11-<version>`, and extract the ZIP to get the installer `.tar.gz`.

## Install and launch

1. Close the game you want to set up. In Desktop Mode, extract the installer `.tar.gz` and run `Install.sh` from the extracted folder. From Konsole in that folder, run `./Install.sh`.
2. Choose **Download Package** to download the official **NVIDIA PhysX 9.23.1019** package (about 29 MB). The prompt shows the destination, and the progress window shows the download and SHA-256 verification. Setup reuses a verified local copy when available.
3. The top of the setup window shows the package status and the path to the verified copy. Use **Check package** to verify it again or **Download package** when a verified copy is missing. The **Supported games** list shows every available profile and marks installations found in the Steam library. Select a game to review its **Launch options** and **Patches**. **Skip intro videos** and **Show FPS counter** start enabled on first setup. New patches start unchecked. Click **Set Up Game** to apply the settings and patches for the selected game.
4. Setup checks for the package if Alice or any selected Batman patch needs files that are missing. Review the license prompt when shown. If you chose **Skip Package**, setup leaves out the parts that still need it.
5. The setup summary shows the selected game. Copy the command, including `%command%`, and paste it into its **Properties → General → Launch Options**. For a Non-Steam shortcut, paste it into **Properties → Shortcut → Launch Options**.
6. Launch the game from Steam in Desktop Mode or Gaming Mode. Set **PhysX High** in the game to match the reference tests. Use Steam's performance menu to control its overlay and frame limit. The installer's **Show FPS counter** controls the MangoHud overlay requested by Deck Physics.

For Alice, **Frame rate** offers **Game default** (about 30 FPS), **60 FPS**, **90 FPS**, and **Uncapped**. The setting applies at launch. VSync and the Steam frame limit still apply.

Run `Install.sh` again to set up another game or change a game’s settings. To return to a standard launch, restore your previous Steam launch options or clear the field if it was empty before setup.

## Set up a manual copy

1. Select its title under **Supported games**. Enter the full path to the game's Windows executable or choose it with **Browse…**. Choose a copy you trust. Compatibility depends on the selected game version. Click **Set Up Game**.
2. In Steam, add the same `.exe` as a **Non-Steam Game**. In the shortcut's **Compatibility** settings, force **Proton 11.0**, then paste the shared launch command into its **Launch Options**.

Each manual executable gets a separate Proton prefix for Deck Physics. Saves stored in an existing Steam or Non-Steam prefix remain in that prefix. Select the detected Steam executable or choose **Use Steam copy** to use the existing Steam installation and prefix.

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
