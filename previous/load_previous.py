"""Compatibilidade para executar módulos anteriores com o frontend plano."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
PATHS = [str(ROOT), str(ROOT / "previous")]
sys.path[:] = PATHS + [path for path in sys.path if path not in PATHS]
