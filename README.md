# verity-quick-demo

This repository contains a small demo of Verity protocol components: a CLI for creating DID documents and verifiable claims, signing them, and storing claims using a mock IPFS/registry middleware. The code is intentionally small and focused on demonstrating the core flows: claim generation, signing, and storing.

Goals

- Demonstrate claim creation from a short message or a file (without embedding large files in the claim)
- Sign claims with a local private key (demo only)
- Store the signed claim via a mock IPFS gateway
- Keep the code simple, readable and maintainable

Prerequisites

- Python 3.11+ (tests used with 3.13 in CI)
- Install dependencies (you likely already have them if you ran tests previously):
  - pydantic
  - requests
  - eth-account
  - fastapi (optional)
  - uvicorn (optional)
  - pytest (for running tests)

Note: By design there is no `requirements.txt` in this repo — install packages into a virtual environment as needed.

Quick start — Interactive CLI

1.Open a Python virtual environment and install deps (example):

```bash
python -m venv .venv
source .venv/Scripts/activate  # on Windows use: .venv\\Scripts\\activate
pip install pydantic requests eth-account pytest
```

2.Run the CLI interactively:

```bash
python -m src.main.cli
```

Follow prompts to create an account, create DID documents, sign messages, and store documents.

Headless usage — create / sign / store claim from command line
You can run the CLI in headless mode to create, sign and store claims non-interactively.

Examples:

- Create and sign a claim from a message, store it, and exit:

```bash
python -m src.main.cli --message "Election result verified" --issuer "did:example:org" --sign-priv <PRIVATE_KEY_HEX> --store --no-interactive
```

- Create a claim from a file and print the claim id (do not store):

```bash
python -m src.main.cli --claim-file /path/to/file.pdf --issuer did:example:org
```

Security note

- The demo accepts a private key via the `--sign-priv` flag for convenience; the code does not persist private keys by default. Do NOT use real production keys with this demo.

Testing

- Run the unit tests (they cover middleware, claim utils, CLI headless flows and basic end-to-end with mocks):

```bash
pytest -q src/main
```

Project structure (relevant files)

- `src/main/cli.py` — interactive CLI and headless entrypoint
- `src/main/middleware.py` — simple HTTP client for registry/IPFS mocks (with timeouts, retries and pydantic returns)
- `src/main/claim_model.py` — pydantic schema for `VerityClaim`
- `src/main/claim_utils.py` — helpers to build, sign and store claims
- `src/main/*_test.py` — unit tests for the components
