"""
Fichier de compatibilité pour decision_core.importer.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.io pour préserver la rétrocompatibilité des imports.
"""
from decision_core.io.importer import import_file, UnsupportedFileFormatError

__all__ = [
    "import_file",
    "UnsupportedFileFormatError",
]
