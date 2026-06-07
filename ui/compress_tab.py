import os
from _qt_compat import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                         QLabel, QFileDialog, QMessageBox, QComboBox)

import engine
from ui.dropzone import DropZone
from ui.base_tab import BaseTab


class CompressTab(BaseTab):
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
        row2.addWidget(QLabel("压缩级别："))
        self.combo_quality = QComboBox()
        self.combo_quality.addItem("低（无损，仅去除冗余）", "low")
        self.combo_quality.addItem("中（推荐，轻度压缩图片）", "medium")
        self.combo_quality.addItem("高（最大压缩，图片质量降低）", "high")
        row2.addWidget(self.combo_quality)
        row2.addStretch()
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出目录")
        row3.addWidget(self.lbl_out)
        row3.addStretch()
        btn_out = QPushButton("选择输出目录…")
        btn_out.clicked.connect(self._choose_output)
        row3.addWidget(btn_out)
        layout.addLayout(row3)

        self.btn_compress = QPushButton("压缩 PDF")
        self.btn_compress.setMinimumHeight(36)
        self.btn_compress.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_compress.setEnabled(False)
        self.btn_compress.clicked.connect(self._run_compress)
        layout.addWidget(self.btn_compress)

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
            size_kb = os.path.getsize(path) / 1024
            if size_kb > 1024:
                size_str = f"{size_kb / 1024:.1f} MB"
            else:
                size_str = f"{size_kb:.0f} KB"
            self.lbl_file.setText(f"{os.path.basename(path)} （{count} 页，{size_str}）")
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
        self.btn_compress.setEnabled(bool(self.input_path and self.output_dir))

    def _run_compress(self):
        quality = self.combo_quality.currentData()
        orig_size = os.path.getsize(self.input_path)

        def _done(path):
            new_size = os.path.getsize(path)
            ratio = (1 - new_size / orig_size) * 100 if orig_size > 0 else 0
            self.lbl_status.setText(
                f"压缩完成：{orig_size / 1024:.0f} KB → {new_size / 1024:.0f} KB"
                f"（减小 {ratio:.0f}%）"
            )
            self._update_button()

        self._start_worker(
            engine.compress_pdf, (self.input_path, quality, self.output_dir), _done,
            disable_btn=self.btn_compress, status_label=self.lbl_status
        )
