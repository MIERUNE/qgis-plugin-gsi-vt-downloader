from pathlib import Path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon

from .gsi_vt_dl_algorithm import GSIVectorTileDownloadAlgorithm


class GSIVectorTileProvider(QgsProcessingProvider):
    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(GSIVectorTileDownloadAlgorithm())

    def id(self, *args, **kwargs):
        return "gsivtdl"

    def name(self, *args, **kwargs):
        return "GSI Vector Tiles Downloader"

    def icon(self):
        path = (Path(__file__).parent.parent / "imgs" / "icon.png").resolve()
        return QIcon(str(path))

    def tr(self, string):
        return QCoreApplication.translate("GSIVectorTileProvider", string)
