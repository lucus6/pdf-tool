from _qt_compat import QMainWindow, QTabWidget, QAction, QMessageBox

from ui.split_tab import SplitTab
from ui.merge_tab import MergeTab
from ui.delete_tab import DeleteTab
from ui.rotate_tab import RotateTab
from ui.extract_tab import ExtractTab
from ui.compress_tab import CompressTab
from ui.encrypt_tab import EncryptTab
from ui.decrypt_tab import DecryptTab
from ui.watermark_tab import WatermarkTab
from ui.pdf_image_tab import PdfImageTab
from ui.pdf_to_word_tab import PdfToWordTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 工具箱")
        self.resize(700, 560)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(
            lambda: QMessageBox.about(self, "关于", "PDF 工具箱 v2.0\n支持 PDF 拆分、合并、删除页面、旋转、提取、压缩、加密解密、水印、图片互转、转 Word")
        )
        help_menu.addAction(about_action)

        tabs = QTabWidget()
        tabs.addTab(SplitTab(), "拆分 PDF")
        tabs.addTab(MergeTab(), "合并 PDF")
        tabs.addTab(DeleteTab(), "删除页面")
        tabs.addTab(RotateTab(), "旋转页面")
        tabs.addTab(ExtractTab(), "提取页面")
        tabs.addTab(CompressTab(), "压缩 PDF")
        tabs.addTab(EncryptTab(), "加密 PDF")
        tabs.addTab(DecryptTab(), "解密 PDF")
        tabs.addTab(WatermarkTab(), "添加水印")
        tabs.addTab(PdfImageTab(), "图片互转")
        tabs.addTab(PdfToWordTab(), "转 Word")
        self.setCentralWidget(tabs)

        self.statusBar().showMessage("就绪")
