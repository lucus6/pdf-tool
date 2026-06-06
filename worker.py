"""QThread-based async worker for non-blocking PDF operations."""

from PySide2.QtCore import QObject, Signal


class PdfWorker(QObject):
    finished = Signal(object)  # emits the result (list of paths, or single path)
    error    = Signal(str)     # emits error message string

    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._target(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
