import os
from _qt_compat import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                         QLabel, QLineEdit, QFileDialog, QMessageBox)

import engine
from ui.dropzone import DropZone
from ui.base_tab import BaseTab


class SplitTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.input_path = None
        self.output_dir = None

        layout = QVBoxLayout(self)

        self.dropzone = DropZone("拖拽 PDF 文件到此处 或 点击浏览")
        self.dropzone.fileDropped.connect(self._on_file_selected)
        layout.addWidget(self.dropzone)

        row1 = QHBoxLayout()
        self.lbl_file = QLabel("未选择文件")
        row1.addWidget(self.lbl_file)
        row1.addStretch()
        btn_browse = QPushButton("浏览 PDF…")
        btn_browse.clicked.connect(self._browse_input)
        row1.addWidget(btn_browse)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("页码范围（例: 1-3,5-7）："))
        self.input_ranges = QLineEdit()
        self.input_ranges.setPlaceholderText("1-3,5-7")
        self.input_ranges.textChanged.connect(self._update_button)
        row2.addWidget(self.input_ranges)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出目录")
        row3.addWidget(self.lbl_out)
        row3.addStretch()
        btn_out = QPushButton("选择输出目录…")
        btn_out.clicked.connect(self._choose_output)
        row3.addWidget(btn_out)
        layout.addLayout(row3)

        self.btn_split = QPushButton("拆分 PDF")
        self.btn_split.setMinimumHeight(36)
        self.btn_split.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_split.setEnabled(False)
        self.btn_split.clicked.connect(self._run_split)
        layout.addWidget(self.btn_split)

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
            engine.split_pdf, (self.input_path, ranges, self.output_dir), _done,
            disable_btn=self.btn_split, status_label=self.lbl_status
        )
