from _qt_compat import QLabel, Qt, Signal, QDragEnterEvent, QDropEvent


class DropZone(QLabel):
    """A label area that accepts .pdf file drops."""

    fileDropped = Signal(str)

    def __init__(self, text="拖拽 PDF 文件到此处"):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(100)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #fafafa;
                color: #888;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #4a9eff;
                color: #4a9eff;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    self.setStyleSheet(self.styleSheet().replace(
                        "background-color: #fafafa;",
                        "background-color: #e8f0fe;"
                    ))
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace(
            "background-color: #e8f0fe;",
            "background-color: #fafafa;"
        ))

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self.styleSheet().replace(
            "background-color: #e8f0fe;",
            "background-color: #fafafa;"
        ))
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.fileDropped.emit(path)
                return
