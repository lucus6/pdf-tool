import os
from _qt_compat import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                         QLabel, QLineEdit, QFileDialog, QMessageBox,
                         QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
                         QRadioButton, QButtonGroup, QStackedWidget, Qt)

import engine
from ui.dropzone import DropZone
from ui.base_tab import BaseTab


class WatermarkTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.input_path = None
        self.output_dir = None

        layout = QVBoxLayout(self)

        # Drop zone
        self.dropzone = DropZone("拖拽 PDF 文件到此处 或 点击浏览")
        self.dropzone.fileDropped.connect(self._on_file_selected)
        layout.addWidget(self.dropzone)

        # File info
        row1 = QHBoxLayout()
        self.lbl_file = QLabel("未选择文件")
        row1.addWidget(self.lbl_file)
        row1.addStretch()
        btn_browse = QPushButton("浏览 PDF…")
        btn_browse.clicked.connect(self._browse_input)
        row1.addWidget(btn_browse)
        layout.addLayout(row1)

        # Watermark type
        row_type = QHBoxLayout()
        row_type.addWidget(QLabel("水印类型："))
        self.radio_text = QRadioButton("文字")
        self.radio_image = QRadioButton("图片")
        self.radio_text.setChecked(True)
        self.type_group = QButtonGroup()
        self.type_group.addButton(self.radio_text, 0)
        self.type_group.addButton(self.radio_image, 1)
        self.type_group.buttonClicked.connect(self._on_type_changed)
        row_type.addWidget(self.radio_text)
        row_type.addWidget(self.radio_image)
        row_type.addStretch()
        layout.addLayout(row_type)

        # Stacked config
        self.stack = QStackedWidget()

        # -- Text config --
        text_widget = QWidget()
        t_layout = QVBoxLayout(text_widget)
        t_layout.setContentsMargins(0, 0, 0, 0)

        tr1 = QHBoxLayout()
        tr1.addWidget(QLabel("水印文字："))
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("例如：机密")
        self.input_text.textChanged.connect(self._update_button)
        tr1.addWidget(self.input_text)
        t_layout.addLayout(tr1)

        tr2 = QHBoxLayout()
        tr2.addWidget(QLabel("字体大小："))
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 200)
        self.spin_font_size.setValue(48)
        tr2.addWidget(self.spin_font_size)
        tr2.addStretch()
        t_layout.addLayout(tr2)

        self.stack.addWidget(text_widget)

        # -- Image config --
        img_widget = QWidget()
        i_layout = QVBoxLayout(img_widget)
        i_layout.setContentsMargins(0, 0, 0, 0)

        ir1 = QHBoxLayout()
        self.lbl_img = QLabel("未选择图片")
        ir1.addWidget(self.lbl_img)
        ir1.addStretch()
        btn_img = QPushButton("浏览图片…")
        btn_img.clicked.connect(self._browse_image)
        ir1.addWidget(btn_img)
        i_layout.addLayout(ir1)

        ir2 = QHBoxLayout()
        ir2.addWidget(QLabel("缩放比例："))
        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.05, 1.0)
        self.spin_scale.setValue(0.3)
        self.spin_scale.setSingleStep(0.05)
        ir2.addWidget(self.spin_scale)
        ir2.addStretch()
        i_layout.addLayout(ir2)

        self.stack.addWidget(img_widget)

        layout.addWidget(self.stack)

        # Common settings
        row_pos = QHBoxLayout()
        row_pos.addWidget(QLabel("位置："))
        self.combo_pos = QComboBox()
        self.combo_pos.addItems(["居中", "左上角", "右上角", "左下角", "右下角", "平铺"])
        row_pos.addWidget(self.combo_pos)
        row_pos.addStretch()
        layout.addLayout(row_pos)

        row_opacity = QHBoxLayout()
        row_opacity.addWidget(QLabel("透明度："))
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(5, 100)
        self.slider_opacity.setValue(30)
        self.lbl_opacity = QLabel("30%")
        self.slider_opacity.valueChanged.connect(
            lambda v: self.lbl_opacity.setText(f"{v}%")
        )
        row_opacity.addWidget(self.slider_opacity)
        row_opacity.addWidget(self.lbl_opacity)
        layout.addLayout(row_opacity)

        row_rot = QHBoxLayout()
        row_rot.addWidget(QLabel("旋转角度："))
        self.spin_rotation = QDoubleSpinBox()
        self.spin_rotation.setRange(-360, 360)
        self.spin_rotation.setValue(45)
        self.spin_rotation.setSuffix("°")
        row_rot.addWidget(self.spin_rotation)
        row_rot.addStretch()
        layout.addLayout(row_rot)

        # Output
        row_out = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出目录")
        row_out.addWidget(self.lbl_out)
        row_out.addStretch()
        btn_out = QPushButton("选择输出目录…")
        btn_out.clicked.connect(self._choose_output)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        # Execute
        self.btn_apply = QPushButton("应用水印")
        self.btn_apply.setMinimumHeight(36)
        self.btn_apply.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self._run_watermark)
        layout.addWidget(self.btn_apply)

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        layout.addStretch()

    def _on_type_changed(self, btn):
        self.stack.setCurrentIndex(self.type_group.id(btn))
        self._update_button()

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

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.lbl_img.setText(path)
            self._update_button()

    def _choose_output(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.output_dir = d
            self.lbl_out.setText(d)
        self._update_button()

    def _update_button(self):
        ok = bool(self.input_path and self.output_dir)
        if self.radio_text.isChecked():
            ok = ok and bool(self.input_text.text().strip())
        else:
            ok = ok and bool(self.lbl_img.text() != "未选择图片")
        self.btn_apply.setEnabled(ok)

    def _run_watermark(self):
        pos_map = {
            "居中": "center", "左上角": "top-left", "右上角": "top-right",
            "左下角": "bottom-left", "右下角": "bottom-right", "平铺": "tile"
        }
        position = pos_map[self.combo_pos.currentText()]
        opacity = self.slider_opacity.value() / 100.0
        rotation = self.spin_rotation.value()

        if self.radio_text.isChecked():
            text = self.input_text.text()
            font_size = self.spin_font_size.value()
            args = (self.input_path, text, position, opacity, rotation, font_size, self.output_dir)
            target = engine.add_text_watermark
        else:
            img_path = self.lbl_img.text()
            scale = self.spin_scale.value()
            args = (self.input_path, img_path, position, opacity, scale, rotation, self.output_dir)
            target = engine.add_image_watermark

        def _done(path):
            self.lbl_status.setText(f"水印已应用：{os.path.basename(path)}")
            self._update_button()

        self._start_worker(
            target, args, _done,
            disable_btn=self.btn_apply, status_label=self.lbl_status
        )
