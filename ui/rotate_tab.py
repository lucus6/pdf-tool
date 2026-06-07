import os
from _qt_compat import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                         QLabel, QLineEdit, QFileDialog, QMessageBox, QComboBox)

import engine
from ui.dropzone import DropZone
from ui.base_tab import BaseTab


class RotateTab(BaseTab):
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
        row2.addWidget(QLabel("要旋转的页码（例: 2,5,7）："))
        self.input_pages = QLineEdit()
        self.input_pages.setPlaceholderText("2,5,7")
        self.input_pages.textChanged.connect(self._update_button)
        row2.addWidget(self.input_pages)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("旋转角度："))
        self.combo_angle = QComboBox()
        self.combo_angle.addItem("顺时针 90°", 90)
        self.combo_angle.addItem("顺时针 180°", 180)
        self.combo_angle.addItem("顺时针 270°（逆时针 90°）", 270)
        self.combo_angle.currentIndexChanged.connect(self._update_button)
        row3.addWidget(self.combo_angle)
        row3.addStretch()
        layout.addLayout(row3)

        row4 = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出目录")
        row4.addWidget(self.lbl_out)
        row4.addStretch()
        btn_out = QPushButton("选择输出目录…")
        btn_out.clicked.connect(self._choose_output)
        row4.addWidget(btn_out)
        layout.addLayout(row4)

        self.btn_rotate = QPushButton("旋转页面")
        self.btn_rotate.setMinimumHeight(36)
        self.btn_rotate.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_rotate.setEnabled(False)
        self.btn_rotate.clicked.connect(self._run_rotate)
        layout.addWidget(self.btn_rotate)

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
        self.btn_rotate.setEnabled(ok)

    def _run_rotate(self):
        try:
            pages = engine.parse_page_numbers(self.input_pages.text())
            total = engine.get_page_count(self.input_path)
            for p in pages:
                if p > total:
                    raise ValueError(f"页码 {p} 超出 PDF 总页数 ({total})")
        except ValueError as e:
            QMessageBox.warning(self, "页码错误", str(e))
            return

        angle = self.combo_angle.currentData()

        def _done(paths):
            self.lbl_status.setText(f"旋转完成：{os.path.basename(paths[0])}")
            self._update_button()

        self._start_worker(
            engine.rotate_pages, (self.input_path, pages, angle, self.output_dir), _done,
            disable_btn=self.btn_rotate, status_label=self.lbl_status
        )
