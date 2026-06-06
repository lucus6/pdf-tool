"""PDF 工具箱 — 桌面 GUI 应用入口"""

import os
import sys


def _fix_qt_dlls():
    """Dev-mode fix: resolve Anaconda Qt DLL conflicts."""
    if getattr(sys, "frozen", False):
        return  # PyInstaller bundles handle DLLs on their own
    import site
    for sp in site.getsitepackages():
        for lib in ("PySide6", "PySide2"):
            p = os.path.join(sp, lib)
            if os.path.isdir(p):
                os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]
                plug = os.path.join(p, "plugins", "platforms")
                if os.path.isdir(plug):
                    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plug
                return


_fix_qt_dlls()

from _qt_compat import QApplication  # noqa: E402
from ui import MainWindow              # noqa: E402


def main():
    # Enable high-DPI scaling. PySide6 does this by default, but PySide2
    # needs explicit opt-in for consistent window size across environments.
    try:
        from _qt_compat import Qt
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass  # PySide6 doesn't have these, but doesn't need them either

    app = QApplication(sys.argv)
    app.setApplicationName("PDF 工具箱")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
