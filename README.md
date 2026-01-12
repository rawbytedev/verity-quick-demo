# verity-quick-demo
[![Python application](https://github.com/Verity-Foundation/verity-quick-demo/actions/workflows/python-app.yml/badge.svg)](https://github.com/Verity-Foundation/verity-quick-demo/actions/workflows/python-app.yml)[![Pylint](https://github.com/Verity-Foundation/verity-quick-demo/actions/workflows/pylint.yml/badge.svg)](https://github.com/Verity-Foundation/verity-quick-demo/actions/workflows/pylint.yml)

This repository contains a small demo of Verity protocol components: a CLI for creating DID documents and verifiable claims, signing them, and storing claims using a mock IPFS/registry middleware. The code is intentionally small and focused on demonstrating the core flows: claim generation, signing, and storing.

## Goals

- Demonstrate claim creation from a short message or a file (without embedding large files in the claim)
- Sign claims with a local private key (demo only)
- Store the signed claim via a mock IPFS gateway
- Keep the code simple, readable and maintainable

## Prerequisites

- Python 3.11+ (tests used with 3.13 in CI)
- Install dependencies:
  - pydantic
  - requests
  - eth-account
  - fastapi
  - uvicorn
  - pytest (for running tests)

## Quick start — Interactive CLI

### 1.Open a Python virtual environment and install deps (example)

```bash
python -m venv .venv
source .venv/Scripts/activate  # on Windows use: .venv\\Scripts\\activate
pip install -r requirements
```

### 2.Run Servers(In another terminal)

```bash
./demo.sh 
```

### 3.Run UI

```bash
python ui_main.py 
```

### 4.Run CLI

```bash
python cli_main.py 
```

## How to use (steps)

make sure to use the UI first

### steps(normal workflow)

1- create an account
2- select the account
3- create a diddoc and specifie the account address in the verification methods
4- check sign and register
5- click on register DIDDOC
6- go to claims
7- select the account to use for claim creation
8- select issuer(if it doesn't appear then reload page or select 'account' then back)
9- then choose the content to create claim for message or file
10- press create claim it should return dict which will contain an verificaton url
11- you can copy claim id and head to verifier to verify

## Testing

### Run the unit tests

```bash
pytest -q src/
```

### Project structure (relevant files)

- `src/cli/` — interactive CLI and headless entrypoint
- `src/middleware/` — simple client for registry/IPFS mocks (with timeouts, retries and pydantic returns)
- `src/core/` — contains all core requirements (models, exceptions, io, crypto...)
- `src/backend/` — Interact with all Services and client
- `src/*_test.py` — unit tests for the components
- `src/services/` — Contains all additionnal services
