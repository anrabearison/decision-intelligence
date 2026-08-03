"""
Package d'import pour decision-core.

Ce package gère l'import de fichiers CSV et Excel avec support
des conventions françaises (encodage, virgule décimale, valeurs manquantes).
"""
from decision_core.io.importer import import_file, UnsupportedFileFormatError

__all__ = [
    "import_file",
    "UnsupportedFileFormatError",
]
