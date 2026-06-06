"""PDF 工具箱 — 桌面 GUI 应用入口"""

import sys
from PySide2.QtWidgets import QApplication
from ui import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PDF 工具箱")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
