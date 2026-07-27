"""InstructLint: static analysis for coding-agent instructions."""

from .engine import scan_repository
from .models import Diagnostic, InstructionFile, ScanResult

__all__ = ["Diagnostic", "InstructionFile", "ScanResult", "scan_repository"]
__version__ = "0.1.0"
