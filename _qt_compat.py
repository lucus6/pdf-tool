"""Compatibility shim: try PySide6 first, fall back to PySide2."""

try:
    from PySide6.QtWidgets import *  # noqa: F401, F403
    from PySide6.QtCore import *     # noqa: F401, F403
    from PySide6.QtGui import *      # noqa: F401, F403
    _QT_LIB = "PySide6"
except ImportError:
    from PySide2.QtWidgets import *  # noqa: F401, F403
    from PySide2.QtCore import *     # noqa: F401, F403
    from PySide2.QtGui import *      # noqa: F401, F403
    _QT_LIB = "PySide2"
