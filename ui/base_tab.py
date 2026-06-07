from _qt_compat import QWidget, QMessageBox, QApplication, QThread

from worker import PdfWorker


class BaseTab(QWidget):
    """Shared worker-launch and error-handling logic for all tabs."""

    def _start_worker(self, target, args, on_finished, *, disable_btn=None,
                      status_label=None, status_text="处理中…"):
        """Launch target(*args) on a background QThread.

        Args:
            target: The engine function to call.
            args: Tuple of positional arguments for the target.
            on_finished: Callback receiving the return value.
            disable_btn: Button to disable during the operation.
            status_label: QLabel to show status text.
            status_text: Text to show while running.
        """
        if disable_btn:
            disable_btn.setEnabled(False)
        if status_label:
            status_label.setText(status_text)
        QApplication.processEvents()

        self._thread = QThread()
        self._worker = PdfWorker(target, *args)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._worker.finished.connect(on_finished)
        self._worker.error.connect(self._on_error)

        self._thread.start()

    def _on_error(self, msg):
        QMessageBox.critical(self, "操作失败", msg)
