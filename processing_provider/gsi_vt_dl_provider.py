from pathlib import Path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .gsi_vt_dl_algorithm import GSIVectorTileDownloadAlgorithm


class GSIVectorTileProvider(QgsProcessingProvider):
    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(GSIVectorTileDownloadAlgorithm())

    def id(self, *args, **kwargs):
        return "gsivtdl"

    def name(self, *args, **kwargs):
        return self.tr("GSI Vector Tile Downloader")

    def icon(self):
        path = (Path(__file__).parent.parent / "imgs" / "icon.png").resolve()
        return QIcon(str(path))
