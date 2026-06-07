import os
from _qt_compat import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                         QLabel, QFileDialog, QMessageBox)

import engine
from ui.dropzone import DropZone
from ui.base_tab import BaseTab


class PdfToWordTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.input_path = None
        self.output_path = None

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
        self.lbl_out = QLabel("未选择输出文件")
        row2.addWidget(self.lbl_out)
        row2.addStretch()
        btn_out = QPushButton("选择输出位置…")
        btn_out.clicked.connect(self._choose_output)
        row2.addWidget(btn_out)
        layout.addLayout(row2)

        self.btn_convert = QPushButton("转换为 Word (.docx)")
        self.btn_convert.setMinimumHeight(36)
        self.btn_convert.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_convert.setEnabled(False)
        self.btn_convert.clicked.connect(self._run_convert)
        layout.addWidget(self.btn_convert)

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
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 Word 文件", "output.docx", "Word 文件 (*.docx)"
        )
        if path:
            self.output_path = path
            self.lbl_out.setText(path)
        self._update_button()

    def _update_button(self):
        self.btn_convert.setEnabled(bool(self.input_path and self.output_path))

    def _run_convert(self):
        def _done(path):
            self.lbl_status.setText(f"转换完成：{os.path.basename(path)}")
            self._update_button()

        self._start_worker(
            engine.pdf_to_docx, (self.input_path, self.output_path), _done,
            disable_btn=self.btn_convert, status_label=self.lbl_status
        )
