# Deck Physics

Deck Physics sets up Steam Deck game profiles with per-game launch options and optional patches for performance and battery use.

**Version [0.1.0](VERSION)** · [Installation](docs/installation.md) · [Tested compatibility](docs/compatibility/README.md) · [Build from source](docs/build.md)

## Quick start

1. Get the [installer archive](docs/installation.md#get-the-installer) and extract the `.tar.gz` on the Deck.
2. In Steam, select **Proton 11.0** under the game's **Properties → Compatibility**. Deck Physics 0.1.0 requires **Valve Proton 11.0-2e** and **Steam Linux Runtime 4**.
3. In Desktop Mode, run `Install.sh`. Choose the settings for each detected game and click **Continue**.
4. Copy the command from the setup summary, including `%command%`, into the game's **Properties → General → Launch Options**. Start the game from Steam in Desktop Mode or Gaming Mode.

## Setup window

The game list on the left shows detected titles. Use **Search games** to find a title and select it to open its settings.

- Under **Launch options**, **Skip intro videos** and **Show FPS counter** are enabled on first setup.
- **Patches** lists optional changes. The **Six-CU graphics mask** tunes GPU scheduling, and **Blocking GPU waits** reduces CPU activity while waiting for GPU work.
- Select a patch row to view its details and dependencies. **Refresh patches** rescans the local patch folder.

Run `Install.sh` again to change your selections.

## Acknowledgments

Deck Physics builds on Christian's work across [Proton-ZLUDA](https://github.com/chkuendig/Proton-ZLUDA), [zluda-wine](https://github.com/chkuendig/zluda-wine), [ZLUDA](https://github.com/chkuendig/ZLUDA), and [llvm-project](https://github.com/chkuendig/llvm-project). See [upstream sources](docs/build.md#sources-and-updates) for the exact revisions.
