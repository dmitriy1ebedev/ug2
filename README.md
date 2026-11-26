# UG2 — independent browser compatibility project

Portable, local browser runtime research for Astra Linux and Windows. The public snapshot currently contains only independent archive verification tooling and synthetic tests. It is not a playable game release, does not include a game or game-specific engine build, and requires no proprietary inputs to run its tests.

Users must supply lawfully obtained data. UG2 is not affiliated with or endorsed by Electronic Arts. See [public source boundary](docs/PUBLIC-SCOPE.md) and [upstream license notice](docs/UPSTREAM-LICENSE.txt).

## Development

- Python 3.12 CI with a strict public path allowlist.
- `python3 tools/public_source_gate.py`
- `python3 -m unittest discover -s tests -v`

Further independent components will be published after source and license review. Game-specific runtime publication remains on hold.

## License and mirrors

The independently authored public UG2 source is distributed under the [MIT License](LICENSE) (SPDX: MIT). Third-party notices remain applicable. This does not license the game, its assets, trademarks, or game-derived artifacts. See [public source boundary](docs/PUBLIC-SCOPE.md).

GitHub is the primary public source; GitVerse is intended to mirror the same reviewed public snapshot. The internal development repository is not a public mirror.
