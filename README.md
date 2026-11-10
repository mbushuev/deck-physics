# Deck Physics

Deck Physics provides guided setup and tested game profiles for Steam Deck.

**Version [0.1.0](VERSION)** · [Installation](docs/installation.md) · [Tested compatibility](docs/compatibility/README.md) · [Build from source](BUILD.md)

## Tested compatibility

The following profiles have passed startup validation on **Steam Deck OLED** with **Valve Proton 11.0-2e**.

| Game | OLED reference performance |
| --- | --- |
| [Batman: Arkham Asylum GOTY](docs/compatibility/batman-arkham-asylum-goty.md) | **87.56 FPS** average in the built-in benchmark |
| [Alice: Madness Returns](docs/compatibility/alice-madness-returns.md) | **77.05 FPS** average in a Ruin encounter |

Reference FPS comes from development builds in the named scenes. See each game page for the settings and validation scope. Compatibility for other titles is unverified. The list will grow as more game profiles are tested and tuned on Steam Deck.

### Battery performance

In the [Batman battery comparison](docs/compatibility/batman-arkham-asylum-goty.md#battery-performance), Deck Physics reduced whole-device power draw by **5.6%** while both development setups averaged about **59 FPS** under the same 60 FPS cap.

## Getting started

1. Select **Proton 11.0** in Steam and let Steam finish installing the compatibility tool and runtime.
2. Run `Install.sh` in Desktop Mode and choose your launch settings.
3. Copy the launch option from the installer into Steam for each configured game.

See the [installation guide](docs/installation.md) for requirements and setup details.

## Acknowledgments

Deck Physics builds on Christian's work across [Proton-ZLUDA](https://github.com/chkuendig/Proton-ZLUDA), [zluda-wine](https://github.com/chkuendig/zluda-wine), [ZLUDA](https://github.com/chkuendig/ZLUDA), and [llvm-project](https://github.com/chkuendig/llvm-project). See [upstream sources](BUILD.md#sources-and-updates) for the exact revisions.
