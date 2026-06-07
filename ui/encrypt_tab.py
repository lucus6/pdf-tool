import os
from _qt_compat import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                         QLabel, QLineEdit, QFileDialog, QMessageBox)

import engine
from ui.dropzone import DropZone
from ui.base_tab import BaseTab


class EncryptTab(BaseTab):
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
        row2.addWidget(QLabel("用户密码："))
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.setPlaceholderText("设置打开密码")
        self.input_password.textChanged.connect(self._update_button)
        row2.addWidget(self.input_password)

        btn_toggle = QPushButton("显示")
        btn_toggle.setCheckable(True)
        btn_toggle.toggled.connect(
            lambda checked: self.input_password.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        row2.addWidget(btn_toggle)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("确认密码："))
        self.input_confirm = QLineEdit()
        self.input_confirm.setEchoMode(QLineEdit.Password)
        self.input_confirm.setPlaceholderText("再次输入密码")
        self.input_confirm.textChanged.connect(self._update_button)
        row3.addWidget(self.input_confirm)
        layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("所有者密码（可选）："))
        self.input_owner = QLineEdit()
        self.input_owner.setEchoMode(QLineEdit.Password)
        self.input_owner.setPlaceholderText("留空则与用户密码相同")
        row4.addWidget(self.input_owner)
        layout.addLayout(row4)

        row5 = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出目录")
        row5.addWidget(self.lbl_out)
        row5.addStretch()
        btn_out = QPushButton("选择输出目录…")
        btn_out.clicked.connect(self._choose_output)
        row5.addWidget(btn_out)
        layout.addLayout(row5)

        self.btn_encrypt = QPushButton("加密 PDF")
        self.btn_encrypt.setMinimumHeight(36)
        self.btn_encrypt.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_encrypt.setEnabled(False)
        self.btn_encrypt.clicked.connect(self._run_encrypt)
        layout.addWidget(self.btn_encrypt)

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
        pwd = self.input_password.text()
        confirm = self.input_confirm.text()
        ok = bool(self.input_path and self.output_dir and pwd and pwd == confirm)
        self.btn_encrypt.setEnabled(ok)

    def _run_encrypt(self):
        pwd = self.input_password.text()
        owner = self.input_owner.text()

        def _done(path):
            self.lbl_status.setText(f"加密完成：{os.path.basename(path)}")
            self._update_button()

        self._start_worker(
            engine.encrypt_pdf, (self.input_path, pwd, owner, self.output_dir), _done,
            disable_btn=self.btn_encrypt, status_label=self.lbl_status
        )
