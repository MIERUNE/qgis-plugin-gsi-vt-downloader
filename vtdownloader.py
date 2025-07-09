import contextlib

from qgis.core import QgsApplication
from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import QAction, QToolButton

from .processing_provider.gsi_vt_dl_provider import GSIVectorTileProvider

with contextlib.suppress(ImportError):
    from processing import execAlgorithmDialog


class VTDownloader:
    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def initGui(self):
        self.provider = GSIVectorTileProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        if self.iface:
            self.setup_algorithm_tool_button()

    def unload(self):
        self.teardown_algorithm_tool_button()
        QgsApplication.processingRegistry().removeProvider(self.provider)

    def setup_algorithm_tool_button(self):
        if hasattr(self, "toolButtonAction") and self.toolButtonAction:
            return

        tool_button = QToolButton()
        icon = self.provider.icon()
        default_action = QAction(
            icon, self.tr("gsi_vt_downloader"), self.iface.mainWindow()
        )
        default_action.triggered.connect(
            lambda: execAlgorithmDialog("gsivtdl:gsi_vt_downloader", {})
        )
        tool_button.setDefaultAction(default_action)

        self.toolButtonAction = self.iface.addToolBarWidget(tool_button)

    def teardown_algorithm_tool_button(self):
        if hasattr(self, "toolButtonAction"):
            self.iface.removeToolBarIcon(self.toolButtonAction)
            del self.toolButtonAction

    def tr(self, message):
        return QgsApplication.translate("GSI Vector Tiles Downloader", message)
