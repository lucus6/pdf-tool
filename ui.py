"""GUI components: DropZone, SplitTab, MergeTab, DeleteTab, MainWindow."""

import os
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QFileDialog,
    QMessageBox, QStatusBar, QMenuBar, QAction, QAbstractItemView,
    QApplication,
)
from PySide2.QtCore import Qt, Signal, QThread
from PySide2.QtGui import QFont, QDragEnterEvent, QDropEvent

import engine
from worker import PdfWorker


# ── DropZone ──────────────────────────────────────────────────────────────

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

    # Provide Python 3.7 compatible slot signatures
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


# ── SplitTab ───────────────────────────────────────────────────────────────

class SplitTab(QWidget):
    def __init__(self):
        super().__init__()
        self.input_path = None
        self.output_dir = None
        self._thread = None

        layout = QVBoxLayout(self)

        # Drop zone
        self.dropzone = DropZone("拖拽 PDF 文件到此处 或 点击浏览")
        self.dropzone.fileDropped.connect(self._on_file_selected)
        layout.addWidget(self.dropzone)

        # File info + browse
        row1 = QHBoxLayout()
        self.lbl_file = QLabel("未选择文件")
        row1.addWidget(self.lbl_file)
        row1.addStretch()
        btn_browse = QPushButton("浏览 PDF…")
        btn_browse.clicked.connect(self._browse_input)
        row1.addWidget(btn_browse)
        layout.addLayout(row1)

        # Page range input
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("页码范围（例: 1-3,5-7）："))
        self.input_ranges = QLineEdit()
        self.input_ranges.setPlaceholderText("1-3,5-7")
        self.input_ranges.textChanged.connect(self._update_button)
        row2.addWidget(self.input_ranges)
        layout.addLayout(row2)

        # Output directory
        row3 = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出目录")
        row3.addWidget(self.lbl_out)
        row3.addStretch()
        btn_out = QPushButton("选择输出目录…")
        btn_out.clicked.connect(self._choose_output)
        row3.addWidget(btn_out)
        layout.addLayout(row3)

        # Action button
        self.btn_split = QPushButton("拆分 PDF")
        self.btn_split.setMinimumHeight(36)
        self.btn_split.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_split.setEnabled(False)
        self.btn_split.clicked.connect(self._run_split)
        layout.addWidget(self.btn_split)

        # Status
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        layout.addStretch()

    def _on_file_selected(self, path):
        self._set_input(path)

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 PDF 文件", "", "PDF 文件 (*.pdf)"
        )
        if path:
            self._set_input(path)

    def _set_input(self, path):
        self.input_path = path
        try:
            count = engine.get_page_count(path)
            self.lbl_file.setText(f"{os.path.basename(path)} （{count} 页）")
            self._update_button()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取 PDF 文件：{e}")
            self.input_path = None

    def _choose_output(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.output_dir = d
            self.lbl_out.setText(d)
        self._update_button()

    def _update_button(self):
        ok = bool(self.input_path and self.output_dir and self.input_ranges.text().strip())
        if ok:
            try:
                engine.parse_page_ranges(self.input_ranges.text())
            except ValueError:
                ok = False
        self.btn_split.setEnabled(ok)

    def _run_split(self):
        try:
            ranges = engine.parse_page_ranges(self.input_ranges.text())
            total = engine.get_page_count(self.input_path)
            for s, e in ranges:
                if e > total:
                    raise ValueError(f"页码范围 {s}-{e} 超出 PDF 总页数 ({total})")
        except ValueError as e:
            QMessageBox.warning(self, "页码范围错误", str(e))
            return

        def _done(paths):
            self.lbl_status.setText(
                f"已生成 {len(paths)} 个文件：\n" +
                "\n".join(os.path.basename(p) for p in paths)
            )
            self._update_button()

        self._start_worker(
            engine.split_pdf, (self.input_path, ranges, self.output_dir), _done
        )

    def _start_worker(self, target, args, on_finished):
        """Common worker-launch logic shared by all tabs."""
        self.btn_split.setEnabled(False)
        self.lbl_status.setText("处理中…")
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
        self.lbl_status.setText("")
        self._update_button()
        QMessageBox.critical(self, "操作失败", msg)


# ── MergeTab ────────────────────────────────────────────────────────────────

class MergeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.output_path = None
        self._thread = None

        layout = QVBoxLayout(self)

        # File list
        lbl_hint = QLabel("拖拽 PDF 文件到下方列表，或点击按钮添加（可按 ▲▼ 调整顺序）")
        layout.addWidget(lbl_hint)

        self.list_widget = QListWidget()
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setMinimumHeight(150)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.model().rowsInserted.connect(self._update_button)
        self.list_widget.model().rowsRemoved.connect(self._update_button)
        self.list_widget.model().rowsMoved.connect(self._update_button)
        # intercept drops for external files
        self.list_widget.dropEvent = self._list_drop_event
        self.list_widget.dragEnterEvent = self._list_drag_enter
        layout.addWidget(self.list_widget)

        # Buttons
        row_btns = QHBoxLayout()
        btn_add = QPushButton("添加 PDF…")
        btn_add.clicked.connect(self._add_files)
        row_btns.addWidget(btn_add)

        btn_remove = QPushButton("移除")
        btn_remove.clicked.connect(self._remove_selected)
        row_btns.addWidget(btn_remove)

        btn_up = QPushButton("▲ 上移")
        btn_up.clicked.connect(self._move_up)
        row_btns.addWidget(btn_up)

        btn_down = QPushButton("▼ 下移")
        btn_down.clicked.connect(self._move_down)
        row_btns.addWidget(btn_down)

        row_btns.addStretch()
        layout.addLayout(row_btns)

        # Output
        row_out = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出文件")
        row_out.addWidget(self.lbl_out)
        row_out.addStretch()
        btn_out = QPushButton("选择输出位置…")
        btn_out.clicked.connect(self._choose_output)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        # Action button
        self.btn_merge = QPushButton("合并 PDF")
        self.btn_merge.setMinimumHeight(36)
        self.btn_merge.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_merge.setEnabled(False)
        self.btn_merge.clicked.connect(self._run_merge)
        layout.addWidget(self.btn_merge)

        # Status
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        layout.addStretch()

    def _list_drag_enter(self, event):
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                if u.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        QListWidget.dragEnterEvent(self.list_widget, event)

    def _list_drop_event(self, event):
        paths = []
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                p = u.toLocalFile()
                if p.lower().endswith(".pdf"):
                    paths.append(p)
        if paths:
            self._add_paths(paths)
        else:
            QListWidget.dropEvent(self.list_widget, event)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择 PDF 文件", "", "PDF 文件 (*.pdf)"
        )
        if paths:
            self._add_paths(paths)

    def _add_paths(self, paths):
        for p in paths:
            self.list_widget.addItem(f"{os.path.basename(p)}  —  {p}")
        self._update_button()

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)

    def _get_paths(self):
        """Extract file paths from list items (format: 'name  —  path')."""
        paths = []
        for i in range(self.list_widget.count()):
            text = self.list_widget.item(i).text()
            paths.append(text.split("  —  ", 1)[1])
        return paths

    def _choose_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存合并文件", "merged.pdf", "PDF 文件 (*.pdf)"
        )
        if path:
            self.output_path = path
            self.lbl_out.setText(path)
        self._update_button()

    def _update_button(self, *args):
        ok = self.list_widget.count() >= 2 and bool(self.output_path)
        self.btn_merge.setEnabled(ok)

    def _run_merge(self):
        paths = self._get_paths()
        for p in paths:
            if not os.path.exists(p):
                QMessageBox.warning(self, "错误", f"文件不存在：{p}")
                return

        self.btn_merge.setEnabled(False)
        self.lbl_status.setText("处理中…")
        QApplication.processEvents()

        self._thread = QThread()
        self._worker = PdfWorker(engine.merge_pdfs, paths, self.output_path)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        def _done(p):
            self.lbl_status.setText(f"合并完成：{os.path.basename(p)}")
            self._update_button()
        self._worker.finished.connect(_done)
        self._worker.error.connect(self._on_error)
        self._thread.start()

    def _on_error(self, msg):
        self.lbl_status.setText("")
        self._update_button()
        QMessageBox.critical(self, "操作失败", msg)


# ── DeleteTab ───────────────────────────────────────────────────────────────

class DeleteTab(QWidget):
    def __init__(self):
        super().__init__()
        self.input_path = None
        self.output_dir = None
        self._thread = None

        layout = QVBoxLayout(self)

        # Drop zone
        self.dropzone = DropZone("拖拽 PDF 文件到此处 或 点击浏览")
        self.dropzone.fileDropped.connect(self._on_file_selected)
        layout.addWidget(self.dropzone)

        # File info + browse
        row1 = QHBoxLayout()
        self.lbl_file = QLabel("未选择文件")
        row1.addWidget(self.lbl_file)
        row1.addStretch()
        btn_browse = QPushButton("浏览 PDF…")
        btn_browse.clicked.connect(self._browse_input)
        row1.addWidget(btn_browse)
        layout.addLayout(row1)

        # Page numbers
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("要删除的页码（例: 2,5,7）："))
        self.input_pages = QLineEdit()
        self.input_pages.setPlaceholderText("2,5,7")
        self.input_pages.textChanged.connect(self._update_button)
        row2.addWidget(self.input_pages)
        layout.addLayout(row2)

        # Output
        row3 = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出目录")
        row3.addWidget(self.lbl_out)
        row3.addStretch()
        btn_out = QPushButton("选择输出目录…")
        btn_out.clicked.connect(self._choose_output)
        row3.addWidget(btn_out)
        layout.addLayout(row3)

        # Action button
        self.btn_delete = QPushButton("删除指定页")
        self.btn_delete.setMinimumHeight(36)
        self.btn_delete.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._run_delete)
        layout.addWidget(self.btn_delete)

        # Status
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        layout.addStretch()

    def _on_file_selected(self, path):
        self._set_input(path)

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 PDF 文件", "", "PDF 文件 (*.pdf)"
        )
        if path:
            self._set_input(path)

    def _set_input(self, path):
        self.input_path = path
        try:
            count = engine.get_page_count(path)
            self.lbl_file.setText(f"{os.path.basename(path)} （{count} 页）")
            self._update_button()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取 PDF 文件：{e}")
            self.input_path = None

    def _choose_output(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.output_dir = d
            self.lbl_out.setText(d)
        self._update_button()

    def _update_button(self):
        ok = bool(self.input_path and self.output_dir and self.input_pages.text().strip())
        if ok:
            try:
                engine.parse_page_numbers(self.input_pages.text())
            except ValueError:
                ok = False
        self.btn_delete.setEnabled(ok)

    def _run_delete(self):
        try:
            pages = engine.parse_page_numbers(self.input_pages.text())
            total = engine.get_page_count(self.input_path)
            for p in pages:
                if p > total:
                    raise ValueError(f"页码 {p} 超出 PDF 总页数 ({total})")
        except ValueError as e:
            QMessageBox.warning(self, "页码错误", str(e))
            return

        self.btn_delete.setEnabled(False)
        self.lbl_status.setText("处理中…")
        QApplication.processEvents()

        self._thread = QThread()
        self._worker = PdfWorker(
            engine.delete_pages, self.input_path, pages, self.output_dir
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        def _done(p):
            self.lbl_status.setText(
                f"已生成：{os.path.basename(p)} （{engine.get_page_count(p)} 页）"
            )
            self._update_button()
        self._worker.finished.connect(_done)
        self._worker.error.connect(self._on_error)
        self._thread.start()

    def _on_error(self, msg):
        self.lbl_status.setText("")
        self._update_button()
        QMessageBox.critical(self, "操作失败", msg)


# ── MainWindow ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 工具箱")
        self.resize(560, 520)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(
            lambda: QMessageBox.about(self, "关于", "PDF 工具箱 v1.0\n支持 PDF 拆分、合并、删除页面")
        )
        help_menu.addAction(about_action)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(SplitTab(), "拆分 PDF")
        tabs.addTab(MergeTab(), "合并 PDF")
        tabs.addTab(DeleteTab(), "删除页面")
        self.setCentralWidget(tabs)

        # Status bar
        self.statusBar().showMessage("就绪")
