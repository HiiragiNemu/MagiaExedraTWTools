#!/usr/bin/env python3
"""JP entry point using independent pins and the shared verified installer."""
from tools import tw_original_installer as installer

if __name__ == "__main__":
    installer.configure_jp()
    raise SystemExit(installer.run_entrypoint())
