# cqrs-kit

[![PyPI version](https://img.shields.io/pypi/v/trysac-cqrs-kit)](https://pypi.org/project/trysac-cqrs-kit/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-cqrs-kit)](LICENSE)
[![CI](https://github.com/Trysac/u241-cqrs-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u241-cqrs-kit/actions/workflows/ci.yml)

Typed command, query and event buses for Python: exact-type handler lookup, onion middleware, events published only after a command succeeds, bounded nesting

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-cqrs-kit
# or
uv add trysac-cqrs-kit
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import cqrs_kit

# normalize() trims surrounding whitespace and lower-cases the text.
print(cqrs_kit.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    cqrs_kit.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
