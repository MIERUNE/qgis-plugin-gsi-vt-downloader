import threading
import unittest

from qgis.PyQt.QtWidgets import QMessageBox

from ui.sub_dialog import SubDialog

from .utilities import get_qgis_app

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class MsgboxTester:
    def __init__(self):
        self.message = ""

    def execute_click(self):
        try:
            main = QGIS_APP.activeWindow()
            if isinstance(main, QMessageBox):
                self.message = main.text()
                close_button = main.button(QMessageBox.Ok)
                close_button.click()
        except Exception as e:
            # Qtの非同期処理で例外が発生した場合、Python/Qtがまとめてフリーズするので
            # テストでも例外処理をしておく
            print(e)


class TestMenu2(unittest.TestCase):
    def test_menu(self):
        sub_dialog = SubDialog()

        assert sub_dialog.isVisible() is False
        sub_dialog.show()
        assert sub_dialog.isVisible() is True
        sub_dialog.hide()
        assert sub_dialog.isVisible() is False

        # QMessageBoxなど、フォーカスを奪うUIは、非同期で操作する必要がある
        msgbox_tester = MsgboxTester()
        threading.Timer(1, msgbox_tester.execute_click).start()
        sub_dialog.get_and_show_input_text("sometext")

        assert msgbox_tester.message == sub_dialog.lineEdit.text() + "sometext"


if __name__ == "__main__":
    unittest.main()
