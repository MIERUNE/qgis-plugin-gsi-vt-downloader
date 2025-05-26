import unittest

from ui.dialog import Dialog

from .utilities import get_qgis_app

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestDialog(unittest.TestCase):
    def test_menu(self):
        dialog = Dialog()

        assert dialog.isVisible() is False
        dialog.show()
        assert dialog.isVisible() is True
        dialog.hide()
        assert dialog.isVisible() is False


if __name__ == "__main__":
    unittest.main()
