<img src="docs/media/deck-physics-mark.svg" width="84" height="84" align="right" alt="">

# Deck Physics

Deck Physics sets up performance profiles for classic games on Steam Deck. Configure launch options and optional performance and battery patches for each game.

**Version [0.1.0](VERSION)** · [Installation](docs/installation.md) · [Tested compatibility](docs/compatibility/README.md) · [Build from source](docs/build.md) · [Changelog](CHANGELOG.md)

## Quick start

1. Get the [installer archive](docs/installation.md#get-the-installer) and extract the `.tar.gz` on the Deck.
2. In Steam, select **Proton 11.0** under the game's **Properties → Compatibility**. Deck Physics 0.1.0 requires **Valve Proton 11.0-2e** and **Steam Linux Runtime 4**.
3. In Desktop Mode, run `Install.sh`. Select a game, review its launch options and patches, then click **Set Up Game**.
4. Copy the command from the setup summary, including `%command%`, into the game's **Launch Options** in Steam. Launch from Desktop Mode or Gaming Mode.

## Setup window

The game list shows the available profiles and marks detected Steam installations. To use a separate installation, choose its executable and launch it through a [Non-Steam shortcut](docs/installation.md#set-up-a-manual-copy).

- Under **Launch options**, set intro skipping and the FPS counter. Alice also has a frame rate selector.
- **Patches** lists optional changes. The **Six-CU graphics mask** tunes GPU scheduling, and **Blocking GPU waits** reduces CPU activity while waiting for GPU work.
- Select a patch row to view its details and dependencies. **Refresh patches** rescans the local patch folder.

Run `Install.sh` again to set up another game or update its settings.

## License

The original Deck Physics code is available under the [MIT License](LICENSE). Third-party components retain their respective licenses. See the [third-party notices](licenses/SOURCES.md).

## Acknowledgments

Deck Physics builds on Christian's work across [Proton-ZLUDA](https://github.com/chkuendig/Proton-ZLUDA), [zluda-wine](https://github.com/chkuendig/zluda-wine), [ZLUDA](https://github.com/chkuendig/ZLUDA), and [llvm-project](https://github.com/chkuendig/llvm-project). See [upstream sources](docs/build.md#sources-and-updates) for the exact revisions.
