import contextlib
import os

from qgis.core import QgsApplication, QgsSettings
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, QLocale, QTranslator
from qgis.PyQt.QtWidgets import QAction, QToolButton

from .processing_provider.gsi_vt_dl_provider import GSIVectorTileProvider

with contextlib.suppress(ImportError):
    from processing import execAlgorithmDialog


class VTDownloader:
    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.provider = None
        self.translator = None
        self._setup_translation()

    def _setup_translation(self):
        locale = QgsSettings().value("locale/userLocale", QLocale().name())
        locale_path = os.path.join(
            os.path.dirname(__file__),
            "i18n",
            f"vtdownloader_{locale[:2]}.qm",
        )

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def initProcessing(self):
        # Called on its own by qgis_process, which does not call initGui()
        self.provider = GSIVectorTileProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        if self.iface:
            self.setup_algorithm_tool_button()

    def unload(self):
        self.teardown_algorithm_tool_button()
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def setup_algorithm_tool_button(self):
        if hasattr(self, "toolButtonAction") and self.toolButtonAction:
            return

        tool_button = QToolButton()
        icon = self.provider.icon()
        default_action = QAction(
            icon, self.tr("Load GSI vector tiles"), self.iface.mainWindow()
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
        return QgsApplication.translate("VTDownloader", message)
