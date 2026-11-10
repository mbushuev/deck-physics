# Deck PhysX

GPU PhysX profiles for Batman: Arkham Asylum GOTY and Alice: Madness Returns on Steam Deck. Both profiles use Valve Proton 11.0-2e (11.0.2), the ZLUDA WoW64 bridge, a graphics CU mask of `0x3f`, and blocking HIP waits set before queue creation.

## Install

1. In Steam, select Valve Proton 11.0 for each game. Let Steam install Proton and Steam Linux Runtime 4.
2. In Desktop Mode, extract the installer archive and run `Install.sh` as your normal user with both games closed.
3. Copy the displayed line into each game's Steam Launch Options. Set PhysX to High in the game settings.
4. Launch the game from Steam. MangoHud displays FPS and frame time. Frame limits follow your Steam and game settings.

The installer detects Steam libraries and compatible PhysX files. When necessary, it downloads the verified PhysX 9.23.1019 installer from NVIDIA and displays its license. Alice uses the pinned 2.8.4.11 runtime and a bridge patch for `cuMemFreeHost(NULL)`. The installed package uses the existing Steam prefixes and campaign saves.

To return to the standard Steam launch, clear the Deck PhysX entry from the game's Launch Options. Steam will then use the compatibility tool selected in the game's properties.

See [BUILD.md](BUILD.md) for source and build details and [AGENTS.md](AGENTS.md) for the repository workflow.
