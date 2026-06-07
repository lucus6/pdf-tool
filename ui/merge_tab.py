import os
from _qt_compat import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                         QLabel, QListWidget, QFileDialog, QMessageBox,
                         QAbstractItemView, QApplication)

import engine
from ui.base_tab import BaseTab


class MergeTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.output_path = None

        layout = QVBoxLayout(self)

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
        self.list_widget.dropEvent = self._list_drop_event
        self.list_widget.dragEnterEvent = self._list_drag_enter
        layout.addWidget(self.list_widget)

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

        row_out = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出文件")
        row_out.addWidget(self.lbl_out)
        row_out.addStretch()
        btn_out = QPushButton("选择输出位置…")
        btn_out.clicked.connect(self._choose_output)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        self.btn_merge = QPushButton("合并 PDF")
        self.btn_merge.setMinimumHeight(36)
        self.btn_merge.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_merge.setEnabled(False)
        self.btn_merge.clicked.connect(self._run_merge)
        layout.addWidget(self.btn_merge)

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

        def _done(p):
            self.lbl_status.setText(f"合并完成：{os.path.basename(p)}")
            self._update_button()

        self._start_worker(
            engine.merge_pdfs, (paths, self.output_path), _done,
            disable_btn=self.btn_merge, status_label=self.lbl_status
        )
