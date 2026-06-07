import os
from _qt_compat import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                         QLabel, QLineEdit, QListWidget, QFileDialog, QMessageBox,
                         QComboBox, QSpinBox, QTabWidget, QAbstractItemView)

import engine
from ui.dropzone import DropZone
from ui.base_tab import BaseTab


class PdfImageTab(QWidget):
    """Combined tab with sub-tabs for Images→PDF and PDF→Images."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        subtabs = QTabWidget()
        subtabs.addTab(Img2PdfSubTab(), "图片 → PDF")
        subtabs.addTab(Pdf2ImgSubTab(), "PDF → 图片")
        layout.addWidget(subtabs)


class Img2PdfSubTab(BaseTab):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        lbl = QLabel("拖拽图片到下方列表，或点击按钮添加（可按 ▲▼ 调整顺序）")
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setMinimumHeight(120)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.model().rowsInserted.connect(self._update_button)
        self.list_widget.model().rowsRemoved.connect(self._update_button)
        self.list_widget.dropEvent = self._list_drop_event
        self.list_widget.dragEnterEvent = self._list_drag_enter
        layout.addWidget(self.list_widget)

        row_btns = QHBoxLayout()
        btn_add = QPushButton("添加图片…")
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

        row_size = QHBoxLayout()
        row_size.addWidget(QLabel("页面大小："))
        self.combo_size = QComboBox()
        self.combo_size.addItems(["自动（图片原始大小）", "A4", "Letter"])
        row_size.addWidget(self.combo_size)
        row_size.addStretch()
        layout.addLayout(row_size)

        row_out = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出文件")
        row_out.addWidget(self.lbl_out)
        row_out.addStretch()
        btn_out = QPushButton("选择输出位置…")
        btn_out.clicked.connect(self._choose_output)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        self.btn_convert = QPushButton("转换为 PDF")
        self.btn_convert.setMinimumHeight(36)
        self.btn_convert.setStyleSheet("QPushButton { font-size: 14px; }")
        self.btn_convert.setEnabled(False)
        self.btn_convert.clicked.connect(self._run_convert)
        layout.addWidget(self.btn_convert)

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        layout.addStretch()

    def _list_drag_enter(self, event):
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                if u.toLocalFile().lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
                    event.acceptProposedAction()
                    return
        QListWidget.dragEnterEvent(self.list_widget, event)

    def _list_drop_event(self, event):
        paths = []
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                p = u.toLocalFile()
                if p.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
                    paths.append(p)
        if paths:
            self._add_paths(paths)
        else:
            QListWidget.dropEvent(self.list_widget, event)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
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
            self, "保存 PDF", "images.pdf", "PDF 文件 (*.pdf)"
        )
        if path:
            self.lbl_out.setText(path)
            self._update_button()

    def _update_button(self, *args):
        has_out = "未选择" not in self.lbl_out.text()
        self.btn_convert.setEnabled(self.list_widget.count() >= 1 and has_out)

    def _run_convert(self):
        paths = self._get_paths()
        output_path = self.lbl_out.text()
        size_text = self.combo_size.currentText()
        size_map = {"自动（图片原始大小）": "auto", "A4": "A4", "Letter": "Letter"}
        page_size = size_map.get(size_text, "auto")

        def _done(path):
            self.lbl_status.setText(f"转换完成：{os.path.basename(path)}")
            self._update_button()

        self._start_worker(
            engine.images_to_pdf, (paths, output_path, page_size), _done,
            disable_btn=self.btn_convert, status_label=self.lbl_status
        )


class Pdf2ImgSubTab(BaseTab):
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
        row2.addWidget(QLabel("DPI："))
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 600)
        self.spin_dpi.setValue(200)
        row2.addWidget(self.spin_dpi)
        row2.addStretch()
        row2.addWidget(QLabel("格式："))
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems(["PNG", "JPEG"])
        row2.addWidget(self.combo_fmt)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.lbl_out = QLabel("未选择输出目录")
        row3.addWidget(self.lbl_out)
        row3.addStretch()
        btn_out = QPushButton("选择输出目录…")
        btn_out.clicked.connect(self._choose_output)
        row3.addWidget(btn_out)
        layout.addLayout(row3)

        self.btn_convert = QPushButton("转换为图片")
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
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.output_dir = d
            self.lbl_out.setText(d)
        self._update_button()

    def _update_button(self):
        self.btn_convert.setEnabled(bool(self.input_path and self.output_dir))

    def _run_convert(self):
        dpi = self.spin_dpi.value()
        fmt = self.combo_fmt.currentText()

        def _done(paths):
            self.lbl_status.setText(f"已导出 {len(paths)} 张图片")
            self._update_button()

        self._start_worker(
            engine.pdf_to_images, (self.input_path, self.output_dir, dpi, fmt), _done,
            disable_btn=self.btn_convert, status_label=self.lbl_status
        )
