import os

from PyQt5.QtWidgets import QDialog, QLineEdit, QMessageBox, QPushButton
from qgis.PyQt import uic

ui_dialog, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "dialog.ui"))


class Dialog(QDialog, ui_dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # 型定義：UIファイルで定義されていてPythonから操作したいインスタンスはここに定義する
        self.pushButton_run: QPushButton = self.pushButton_run
        self.pushButton_cancel: QPushButton = self.pushButton_cancel
        self.lineEdit: QLineEdit = self.lineEdit

        # シグナルとスロットの接続
        self.pushButton_run.clicked.connect(self.get_and_show_input_text)
        self.pushButton_cancel.clicked.connect(self.close)

    def get_and_show_input_text(self):
        # テキストボックス値取得
        text_value = self.lineEdit.text()
        # テキストボックス値をメッセージ表示
        QMessageBox.information(self, "ウィンドウ名", text_value)
