"""Disponibilize os módulos do frontend em uma única pasta previous/."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
# A raiz mantém a infraestrutura atual antes dos módulos das etapas anteriores.
PATHS = [str(ROOT), str(ROOT / "previous")]
sys.path[:] = PATHS + [path for path in sys.path if path not in PATHS]
