# Installation

Symphra Container supports pure Python environments with optional framework integrations.

## Core library
```bash
pip install symphra-container
```

## Optional integrations
Install extras as needed:
```bash
# FastAPI
pip install symphra-container[fastapi]

# Flask
pip install symphra-container[flask]

# Django
pip install symphra-container[django]

# All integrations
pip install symphra-container[all]
```

## Python requirements
- Python 3.10+ (3.11/3.12 recommended)

## Dependencies
- The core library has no mandatory third-party dependencies
- Integration modules import lazily and provide friendly errors if frameworks are missing

## Verify
```python
import symphra_container
print(symphra_container.__version__)
```
