# SPDX-License-Identifier: GPL-3.0-or-later
"""Point VeFi's config/data directories at throwaway temp dirs before import.

These env vars are read by ``vefi.config`` at import time, so they must be set
before any ``vefi`` module is imported.
"""
import os
import tempfile

os.environ.setdefault("VEFI_CONFIG_DIR", tempfile.mkdtemp(prefix="vefi_cfg_"))
os.environ.setdefault("VEFI_DATA_DIR", tempfile.mkdtemp(prefix="vefi_data_"))
