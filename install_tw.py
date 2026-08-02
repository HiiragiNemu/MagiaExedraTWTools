#!/usr/bin/env python3
"""Double-clickable interactive entry point for the TW original-client wizard."""

from tools.tw_original_installer import run_entrypoint


if __name__ == "__main__":
    raise SystemExit(run_entrypoint())
