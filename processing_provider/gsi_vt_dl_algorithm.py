import math
import os
import tempfile
import urllib.error
import urllib.request

import processing
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant

from .. import settings

TMP_PATH = os.path.join(tempfile.gettempdir(), "vtdownloader")
SOURCE_LAYERS = settings.SOURCE_LAYERS
DEFAULT_MIN_ZOOM = settings.DEFAULT_MIN_ZOOM
DEFAULT_MAX_ZOOM = settings.DEFAULT_MAX_ZOOM

_DESCRIPTION = """
This QGIS plugin downloads vector tiles from the Geospatial Information Authority of Japan (GSI) and adds them as a layer to QGIS.
You can find information about the GSI Vector Tiles on the following site: <a href='https://maps.gsi.go.jp/development/vt.html'>https://maps.gsi.go.jp/development/vt.html</a>

--------------------------------------------------------------------

このQGISプラグインは、国土地理院（GSI）のベクトルタイルをダウンロードし、QGISにレイヤとして追加します。
国土地理院ベクトルタイルに関する情報は、以下のサイトから確認できます。
<a href='https://maps.gsi.go.jp/development/vt.html'>https://maps.gsi.go.jp/development/vt.html</a>

"""
TILES_LIMIT = settings.TILES_LIMIT


class GSIVectorTileDownloadAlgorithm(QgsProcessingAlgorithm):
    INPUT_EXTENT = "INPUT_EXTENT"
    SOURCE_LAYER = "SOURCE_LAYER"
    ZOOM_LEVEL = "ZOOM_LEVEL"
    OUTPUT = "OUTPUT"

    def _get_display_name(self, layer_key):
        layer_value = SOURCE_LAYERS[layer_key]
        category = layer_value.get("category", "")
        datatype = layer_value.get("datatype", "")
        minzoom = layer_value.get("minzoom", "")
        maxzoom = layer_value.get("maxzoom", "")
        if category:
            return f"{layer_key}: {category}（{datatype}）z{minzoom}-{maxzoom}"
        else:
            return layer_key

    def shortHelpString(self):
        return _DESCRIPTION

    def initAlgorithm(self, config=None):
        # Download-extent
        self.addParameter(
            QgsProcessingParameterExtent(
                self.INPUT_EXTENT,
                self.tr("Download-extent"),
                optional=False,
            )
        )

        # Source-layer
        layer_options = []
        for key in SOURCE_LAYERS.keys():
            display_name = self._get_display_name(key)
            layer_options.append(display_name)

        self.addParameter(
            QgsProcessingParameterEnum(
                self.SOURCE_LAYER,
                self.tr("Source-layer"),
                optional=False,
                options=layer_options,
            )
        )

        # Zoom-level
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ZOOM_LEVEL,
                self.tr("Zoom-level"),
                type=QgsProcessingParameterNumber.Integer,
                minValue=4,
                maxValue=16,
                defaultValue=14,
            )
        )

        # Output-layer
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Output layer"),
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        # parameters
        extent = self.parameterAsExtent(parameters, self.INPUT_EXTENT, context)
        source_layer_index = self.parameterAsEnum(
            parameters, self.SOURCE_LAYER, context
        )
        zoom_level = self.parameterAsInt(parameters, self.ZOOM_LEVEL, context)

        # convert extent to EPSG: 4326
        extent_crs = self.parameterAsExtentCrs(parameters, self.INPUT_EXTENT, context)
        feedback.pushInfo(f"Input extent CRS: {extent_crs.authid()}")

        if extent_crs.authid() != "EPSG:4326":
            transform = QgsCoordinateTransform(
                extent_crs, QgsCoordinateReferenceSystem("EPSG:4326"), context.project()
            )
            try:
                extent = transform.transformBoundingBox(extent)
                feedback.pushInfo("Successfully transformed extent to EPSG:4326")
            except Exception as e:
                feedback.reportError(f"Coordinate transformation error: {str(e)}")
                return {}

        leftbottom_lonlat = [extent.xMinimum(), extent.yMinimum()]
        righttop_lonlat = [extent.xMaximum(), extent.yMaximum()]

        layer_keys = list(SOURCE_LAYERS.keys())
        layer_key = layer_keys[source_layer_index]

        data_name = SOURCE_LAYERS[layer_key].get("category", "")

        # ズームレベルが対象レイヤーの範囲内かチェック
        layer_info = SOURCE_LAYERS[layer_key]
        min_zoom = layer_info.get("minzoom", DEFAULT_MIN_ZOOM)
        max_zoom = layer_info.get("maxzoom", DEFAULT_MAX_ZOOM)
        if zoom_level < min_zoom or zoom_level > max_zoom:
            feedback.reportError(
                f"Specified zoom level (z{zoom_level}) is not available "
                f"for data '{layer_key} ({data_name})' \n"
                f"Available zoom levels: {min_zoom}-{max_zoom} \n"
                f"Process stopping..."
            )
            return {}

        feedback.pushInfo(f"Downloading {layer_key} at zoom level {zoom_level}")

        # タイルインデックス
        tileindex = self.create_tile_index_from_bbox(
            leftbottom_lonlat, righttop_lonlat, zoom_level
        )

        if not tileindex:
            feedback.reportError("No tiles found for the specified extent")
            return {}

        feedback.pushInfo(f"Found {len(tileindex)} tiles to download")

        if len(tileindex) > TILES_LIMIT:
            feedback.reportError(
                f"Too many tiles to download (Tiles limit: {TILES_LIMIT}).\n"
                f"Please specified a zoom level lower than z{zoom_level} "
                "or a smaller extent.\nProcess stopping..."
            )
            return {}

        # ダウンロード実行
        os.makedirs(TMP_PATH, exist_ok=True)
        mergedlayer = self.download_tiles(tileindex, layer_key, feedback)

        if mergedlayer is None:
            feedback.reportError("No valid features found in the specified area")
            return {}

        # クリップ処理
        bbox = self.make_bbox(leftbottom_lonlat, righttop_lonlat)
        mergedlayer = self.clip_vlayer(bbox, mergedlayer)
        feedback.pushInfo("✓ Successfully clipped features to specified extent")
        feedback.pushInfo(f"Final feature count: {mergedlayer.featureCount()}")

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            mergedlayer.fields(),
            mergedlayer.wkbType(),
            mergedlayer.crs(),
        )

        if sink is not None:
            features = mergedlayer.getFeatures()
            for feature in features:
                sink.addFeature(feature)

            # Set layer name for temporary scratch layer
            layer_name = f"{layer_key}_z{zoom_level}"
            if context.willLoadLayerOnCompletion(dest_id):
                layer_details = context.layerToLoadOnCompletionDetails(dest_id)
                layer_details.name = layer_name
            return {self.OUTPUT: dest_id}
        else:
            return {self.OUTPUT: mergedlayer}

    def create_tile_index_from_bbox(
        self, leftbottom_lonlat, righttop_lonlat, zoom_level
    ):
        """指定されたBBoxとズームレベルをカバーするタイルインデックスを作成"""
        lon_min, lat_min = leftbottom_lonlat
        lon_max, lat_max = righttop_lonlat

        x_start_float, y_start_float = self._lonlat_to_tile_xy(
            lon_min, lat_max, zoom_level
        )

        x_end_float, y_end_float = self._lonlat_to_tile_xy(lon_max, lat_min, zoom_level)

        x_start = math.floor(x_start_float)
        x_end = math.floor(x_end_float)
        y_start = math.floor(y_start_float)
        y_end = math.floor(y_end_float)

        # タイルインデックスのリストを生成
        covering_tiles = []
        z = zoom_level

        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                covering_tiles.append([x, y, z])

        return covering_tiles

    def _lonlat_to_tile_xy(self, lon, lat, zoom_level):
        """緯度経度からタイル座標を計算"""
        lat_rad = math.radians(lat)
        n = 2.0**zoom_level

        tile_x = (lon + 180.0) / 360.0 * n
        tile_y = (
            (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
            / 2.0
            * n
        )

        return tile_x, tile_y

    def lonlat_to_webmercator(self, lonlat):
        return [
            lonlat[0] * 20037508.34 / 180,
            math.log(math.tan((90 + lonlat[1]) * math.pi / 360))
            / (math.pi / 180)
            * 20037508.34
            / 180,
        ]

    def make_rectangle_of(self, leftbottom, righttop):
        x1 = leftbottom[0]
        y1 = leftbottom[1]
        x2 = righttop[0]
        y2 = righttop[1]
        rectangle = {
            "type": "Polygon",
            "coordinates": [[[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]],
        }
        return rectangle

    def make_bbox(self, leftbottom_lonlat, righttop_lonlat):
        leftbottom_as_3857 = self.lonlat_to_webmercator(leftbottom_lonlat)
        righttop_as_3857 = self.lonlat_to_webmercator(righttop_lonlat)
        xMin = leftbottom_as_3857[0]
        xMax = righttop_as_3857[0]
        yMin = leftbottom_as_3857[1]
        yMax = righttop_as_3857[1]
        return [xMin, xMax, yMin, yMax]

    def download_tiles(self, tileindex, layer_key, feedback):
        self.make_xyz_dirs(tileindex)

        pbflayers = []
        total_tiles = len(tileindex)

        feedback.pushInfo(
            f"Starting download of {total_tiles} tiles for layer '{layer_key}'"
        )

        for i, xyz in enumerate(tileindex):
            if feedback.isCanceled():
                break

            # ダウンロードフェーズ
            download_progress = int(i * 70 / total_tiles)
            feedback.setProgress(download_progress)

            x, y, z = xyz
            current_tileurl = settings.GIS_VECTOR_TILE_URL.format(z=z, x=x, y=y)
            target_path = os.path.join(TMP_PATH, str(z), str(x), f"{y}.pbf")

            feedback.pushInfo(f"Processing tile {i + 1}/{total_tiles}: {x}/{y}/{z}")
            feedback.pushInfo(f"URL: {current_tileurl}")

            if os.path.exists(target_path):
                if os.path.getsize(target_path) == 0:
                    feedback.pushInfo(f"Removing empty file: {target_path}")
                    os.remove(target_path)
                else:
                    feedback.pushInfo(
                        f"File already exists: {target_path} (size: {os.path.getsize(target_path)} bytes)"
                    )

            if not os.path.exists(target_path):
                try:
                    feedback.pushInfo(f"Downloading from: {current_tileurl}")
                    response = urllib.request.urlopen(
                        current_tileurl, timeout=settings.GIS_DOWNLOAD_TIMEOUT
                    )
                    pbfdata = response.read()

                    if len(pbfdata) > 0:
                        with open(target_path, mode="wb") as f:
                            f.write(pbfdata)
                        feedback.pushInfo(
                            f"Downloaded {len(pbfdata)} bytes to {target_path}"
                        )
                    else:
                        feedback.pushInfo(f"Empty response for tile {x}/{y}/{z}")
                        continue

                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        feedback.pushInfo(f"Tile not found (404): {x}/{y}/{z}")
                    else:
                        feedback.pushInfo(f"HTTP error {e.code} for tile {x}/{y}/{z}")
                    continue
                except Exception as e:
                    feedback.pushInfo(f"Download error for tile {x}/{y}/{z}: {str(e)}")
                    continue

            if not os.path.exists(target_path):
                feedback.pushInfo(
                    f"File not found after download attempt: {target_path}"
                )
                continue

            try:
                feedback.pushInfo(f"Processing PBF file: {target_path}")

                file_size = os.path.getsize(target_path)
                feedback.pushInfo(f"PBF file size: {file_size} bytes")

                if file_size == 0:
                    feedback.pushInfo(f"Empty PBF file, skipping: {target_path}")
                    continue

                if layer_key not in SOURCE_LAYERS:
                    feedback.pushInfo(
                        f"Layer key '{layer_key}' not found in SOURCE_LAYERS"
                    )
                    feedback.pushInfo(f"Available keys: {list(SOURCE_LAYERS.keys())}")
                    continue

                geometrytype = self.translate_gsitype_to_geometry(
                    SOURCE_LAYERS[layer_key]["datatype"]
                )
                feedback.pushInfo(f"Geometry type for {layer_key}: {geometrytype}")

                pbfuri = (
                    target_path
                    + "|layername="
                    + layer_key
                    + "|geometrytype="
                    + geometrytype
                )
                feedback.pushInfo(f"PBF URI: {pbfuri}")

                pbflayer = QgsVectorLayer(pbfuri, "pbf", "ogr")

                feedback.pushInfo(f"Layer valid: {pbflayer.isValid()}")
                feedback.pushInfo(
                    f"Data provider valid: {pbflayer.dataProvider().isValid()}"
                )
                feedback.pushInfo(f"Feature count: {pbflayer.featureCount()}")

                if not pbflayer.isValid():
                    feedback.pushInfo(f"Invalid layer for tile {x}/{y}/{z}")

                    feedback.pushInfo("Trying to get layer info from PBF...")
                    try:
                        from osgeo import ogr

                        ds = ogr.Open(target_path)
                        if ds:
                            feedback.pushInfo(
                                f"OGR can open file. Layer count: {ds.GetLayerCount()}"
                            )
                            for i in range(ds.GetLayerCount()):
                                layer = ds.GetLayer(i)
                                feedback.pushInfo(
                                    f"Layer {i}: {layer.GetName()}, features: {layer.GetFeatureCount()}"
                                )
                        else:
                            feedback.pushInfo("OGR cannot open file")
                    except Exception as e:
                        feedback.pushInfo(f"OGR error: {str(e)}")
                    continue

                if pbflayer.dataProvider().isValid() and pbflayer.featureCount() > 0:
                    feedback.pushInfo(
                        f"Valid layer with {pbflayer.featureCount()} features"
                    )

                    expressions = []
                    fields = pbflayer.dataProvider().fields()
                    feedback.pushInfo(f"Field count: {fields.count()}")

                    for j in range(fields.count()):
                        field = fields.at(j)
                        feedback.pushInfo(
                            f"Field {j}: {field.name()} ({field.typeName()})"
                        )

                        expression = {
                            "expression": f'"{field.name()}"',
                            "length": 0,
                            "name": f"{field.name()}",
                            "precision": 0,
                            "type": field.type(),
                        }
                        if (
                            hasattr(settings, "DOUBLE_FIELDS")
                            and field.name() in settings.DOUBLE_FIELDS
                        ):
                            expression["type"] = QVariant.Double
                        expressions.append(expression)

                    refactored = processing.run(
                        "qgis:refactorfields",
                        {
                            "INPUT": pbflayer,
                            "OUTPUT": "TEMPORARY_OUTPUT",
                            "FIELDS_MAPPING": expressions,
                        },
                    )["OUTPUT"]
                    pbflayers.append(refactored)
                    feedback.pushInfo(
                        f"Added refactored layer to collection. Total layers: {len(pbflayers)}"
                    )
                else:
                    feedback.pushInfo(
                        f"Layer has no features or is invalid for tile {x}/{y}/{z}"
                    )

            except Exception as e:
                feedback.pushInfo(f"Error processing tile {x}/{y}/{z}: {str(e)}")
                import traceback

                feedback.pushInfo(f"Traceback: {traceback.format_exc()}")
                continue

        feedback.setProgress(90)
        feedback.pushInfo(f"Download completed. Total valid layers: {len(pbflayers)}")

        if not pbflayers:
            feedback.pushInfo(
                "No valid PBF layers found. Check the debug messages above."
            )
            return None
        elif len(pbflayers) == 1:
            mergedlayer = pbflayers[0]
            feedback.pushInfo("Using single layer")
        else:
            feedback.pushInfo(f"Merging {len(pbflayers)} layers")
            merged_result = processing.run(
                "native:mergevectorlayers",
                {
                    "LAYERS": pbflayers,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
            mergedlayer = merged_result["OUTPUT"]

        feedback.setProgress(100)
        return mergedlayer

    def make_xyz_dirs(self, tileindex):
        for xyz in tileindex:
            x = str(xyz[0])
            z = str(xyz[2])
            os.makedirs(os.path.join(TMP_PATH, z, x), exist_ok=True)

    def translate_gsitype_to_geometry(self, gsitype):
        if gsitype == "点":
            return "Point"
        elif gsitype == "線":
            return "LineString"
        else:
            return "Polygon"

    def clip_vlayer(self, bbox, vlayer):
        cliped = processing.run(
            "qgis:extractbyextent",
            {
                "INPUT": vlayer,
                "CLIP": False,
                "EXTENT": "%s,%s,%s,%s" % (bbox[0], bbox[1], bbox[2], bbox[3]),
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]
        return cliped

    def name(self):
        return "gsi_vt_downloader"

    def displayName(self):
        return self.tr("GSI Vector Tiles Downloader")

    def createInstance(self):
        return GSIVectorTileDownloadAlgorithm()

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)
