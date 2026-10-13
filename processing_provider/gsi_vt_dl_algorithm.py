import math
import os
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingMultiStepFeedback,
    QgsProcessingOutputMultipleLayers,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsRectangle,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QCoreApplication, QMetaType

from .. import settings

TMP_PATH = os.path.join(tempfile.gettempdir(), "vtdownloader")
SOURCE_LAYERS = settings.SOURCE_LAYERS
DEFAULT_MIN_ZOOM = settings.DEFAULT_MIN_ZOOM
DEFAULT_MAX_ZOOM = settings.DEFAULT_MAX_ZOOM
TILES_LIMIT = settings.TILES_LIMIT

# 404以外のエラーで取得できなかったタイルを試す回数
DOWNLOAD_ATTEMPTS = 3

# Webメルカトルで扱える範囲（EPSG:4326）
WEB_MERCATOR_BOUNDS = QgsRectangle(-180.0, -85.0511287798066, 180.0, 85.0511287798066)

NUMERIC_TYPES = (QMetaType.Type.Int, QMetaType.Type.LongLong, QMetaType.Type.Double)


class GSIVectorTileDownloadAlgorithm(QgsProcessingAlgorithm):
    INPUT_EXTENT = "INPUT_EXTENT"
    SOURCE_LAYER = "SOURCE_LAYER"
    ZOOM_LEVEL = "ZOOM_LEVEL"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    OUTPUT_LAYERS = "OUTPUT_LAYERS"

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
        return self.tr(
            """This QGIS plugin downloads vector tiles from the Geospatial Information Authority of Japan (GSI) and adds them as a layer to QGIS. You can find information about the GSI Vector Tiles on the following site: <a href='https://maps.gsi.go.jp/development/vt.html'>https://maps.gsi.go.jp/development/vt.html</a>"""
        )

    def initAlgorithm(self, config=None):
        # Download-extent
        self.addParameter(
            QgsProcessingParameterExtent(
                self.INPUT_EXTENT,
                self.tr("Download extent"),
                optional=False,
            )
        )

        # Source-layers
        layer_options = []
        for key in SOURCE_LAYERS.keys():
            display_name = self._get_display_name(key)
            layer_options.append(display_name)

        self.addParameter(
            QgsProcessingParameterEnum(
                self.SOURCE_LAYER,
                self.tr("Source layers"),
                allowMultiple=True,
                optional=False,
                options=layer_options,
            )
        )

        # Zoom-level
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ZOOM_LEVEL,
                self.tr("Zoom level"),
                type=QgsProcessingParameterNumber.Type.Integer,
                minValue=4,
                maxValue=16,
                defaultValue=14,
            )
        )

        # Output folder. If not specified, a temporary folder is used
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER, self.tr("Destination folder"), optional=False
            )
        )

        # GeoPackages written to the output folder, one per source layer
        self.addOutput(
            QgsProcessingOutputMultipleLayers(
                self.OUTPUT_LAYERS, self.tr("Output layers")
            )
        )

    def checkParameterValues(self, parameters, context):
        ok, message = super().checkParameterValues(parameters, context)
        if not ok:
            return ok, message
        error = self._validate_parameters(parameters, context)
        if error:
            return False, error
        return True, ""

    def processAlgorithm(self, parameters, context, feedback):
        # checkParameterValues() is not called by every caller, so validate again
        error = self._validate_parameters(parameters, context)
        if error:
            raise QgsProcessingException(error)

        layer_keys = self._selected_layer_keys(parameters, context)
        zoom_level = self.parameterAsInt(parameters, self.ZOOM_LEVEL, context)
        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        os.makedirs(output_folder, exist_ok=True)

        extent_crs = self.parameterAsExtentCrs(parameters, self.INPUT_EXTENT, context)
        feedback.pushInfo(f"Input extent CRS: {extent_crs.authid()}")
        extent = self._extent_in_wgs84(parameters, context)
        if not extent_crs.isValid():
            feedback.pushWarning(
                self.tr("The extent has no CRS. It is assumed to be EPSG:4326.")
            )
        elif extent_crs != QgsCoordinateReferenceSystem("EPSG:4326"):
            feedback.pushInfo(self.tr("Successfully transformed extent to EPSG:4326"))

        leftbottom_lonlat = [extent.xMinimum(), extent.yMinimum()]
        righttop_lonlat = [extent.xMaximum(), extent.yMaximum()]

        # タイルインデックス
        tileindex = self.create_tile_index_from_bbox(
            leftbottom_lonlat, righttop_lonlat, zoom_level
        )
        feedback.pushInfo(
            self.tr("Found {count} tiles to download").format(count=len(tileindex))
        )

        # ステップ0でタイルをダウンロードし、以降はレイヤごとに書き出す
        steps = QgsProcessingMultiStepFeedback(len(layer_keys) + 1, feedback)
        os.makedirs(TMP_PATH, exist_ok=True)
        tile_paths = self.download_tiles(tileindex, steps)

        bbox = self.make_bbox(leftbottom_lonlat, righttop_lonlat)
        rect = QgsRectangle(bbox[0], bbox[2], bbox[1], bbox[3])

        output_layers = []
        for step, layer_key in enumerate(layer_keys, start=1):
            if steps.isCanceled():
                break
            steps.setCurrentStep(step)
            feedback.pushInfo(
                self.tr("Extracting {layer_key} at zoom level {zoom_level}").format(
                    layer_key=layer_key, zoom_level=zoom_level
                )
            )

            layer_name = f"{layer_key}_z{zoom_level}"
            output_path = os.path.join(output_folder, f"{layer_name}.gpkg")
            count = self.write_layer(
                tile_paths, layer_key, rect, output_path, layer_name, context, steps
            )
            if count is None:  # canceled
                break
            if count == 0:
                feedback.pushWarning(
                    f"{layer_key}: "
                    + self.tr("No valid features found in the specified area")
                )
                continue

            feedback.pushInfo(self.tr("Final feature count: {}").format(count))
            feedback.pushInfo(self.tr("File saved : {}").format(output_path))
            output_layers.append(output_path)

            # Processing adds the layer to the project on the main thread
            # once the algorithm has finished
            if context.project() is not None:
                context.addLayerToLoadOnCompletion(
                    output_path,
                    QgsProcessingContext.LayerDetails(
                        layer_name, context.project(), self.OUTPUT_LAYERS
                    ),
                )

        if not output_layers and not feedback.isCanceled():
            raise QgsProcessingException(
                self.tr("No valid features found in the specified area")
            )

        return {self.OUTPUT_FOLDER: output_folder, self.OUTPUT_LAYERS: output_layers}

    def _selected_layer_keys(self, parameters, context):
        layer_keys = list(SOURCE_LAYERS.keys())
        indices = self.parameterAsEnums(parameters, self.SOURCE_LAYER, context)
        return [layer_keys[index] for index in indices]

    def _extent_in_wgs84(self, parameters, context):
        """ダウンロード範囲をEPSG:4326に変換し、Webメルカトルの範囲内に収めて返す"""
        extent = self.parameterAsExtent(parameters, self.INPUT_EXTENT, context)
        extent_crs = self.parameterAsExtentCrs(parameters, self.INPUT_EXTENT, context)
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        if extent_crs.isValid() and extent_crs != wgs84:
            transform = QgsCoordinateTransform(
                extent_crs, wgs84, context.transformContext()
            )
            extent = transform.transformBoundingBox(extent)
        return extent.intersect(WEB_MERCATOR_BOUNDS)

    def _validate_parameters(self, parameters, context):
        """ダウンロードできない指定であればエラーメッセージを返す"""
        zoom_level = self.parameterAsInt(parameters, self.ZOOM_LEVEL, context)

        # ズームレベルが対象レイヤーの範囲内かチェック
        unavailable = []
        for layer_key in self._selected_layer_keys(parameters, context):
            layer_info = SOURCE_LAYERS[layer_key]
            min_zoom = layer_info.get("minzoom", DEFAULT_MIN_ZOOM)
            max_zoom = layer_info.get("maxzoom", DEFAULT_MAX_ZOOM)
            if zoom_level < min_zoom or zoom_level > max_zoom:
                unavailable.append(f"{layer_key} (z{min_zoom}-{max_zoom})")
        if unavailable:
            return self.tr("Zoom level z{zoom} is not available for: {layers}").format(
                zoom=zoom_level, layers=", ".join(unavailable)
            )

        try:
            extent = self._extent_in_wgs84(parameters, context)
        except QgsCsException as e:
            return self.tr("Coordinate transformation error: {error}").format(
                error=str(e)
            )
        if extent.isNull():
            return self.tr("No tiles found for the specified extent")

        # タイル数はリストを作らずに数える（広い範囲では膨大になるため）
        x_start, x_end, y_start, y_end = self._tile_range(
            [extent.xMinimum(), extent.yMinimum()],
            [extent.xMaximum(), extent.yMaximum()],
            zoom_level,
        )
        tile_count = (x_end - x_start + 1) * (y_end - y_start + 1)
        if tile_count > TILES_LIMIT:
            return self.tr(
                "Too many tiles to download ({count} tiles, limit: {limit}). "
                "Specify a lower zoom level or a smaller extent."
            ).format(count=tile_count, limit=TILES_LIMIT)
        return None

    def create_tile_index_from_bbox(
        self, leftbottom_lonlat, righttop_lonlat, zoom_level
    ):
        """指定されたBBoxとズームレベルをカバーするタイルインデックスを作成"""
        x_start, x_end, y_start, y_end = self._tile_range(
            leftbottom_lonlat, righttop_lonlat, zoom_level
        )

        # タイルインデックスのリストを生成
        covering_tiles = []
        z = zoom_level

        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                covering_tiles.append([x, y, z])

        return covering_tiles

    def _tile_range(self, leftbottom_lonlat, righttop_lonlat, zoom_level):
        """指定されたBBoxをカバーするタイル座標の範囲を返す"""
        lon_min, lat_min = leftbottom_lonlat
        lon_max, lat_max = righttop_lonlat

        x_start_float, y_start_float = self._lonlat_to_tile_xy(
            lon_min, lat_max, zoom_level
        )

        x_end_float, y_end_float = self._lonlat_to_tile_xy(lon_max, lat_min, zoom_level)

        # 経度180度などの端はタイル範囲の外になるため、存在するタイルに収める
        max_index = 2**zoom_level - 1

        def to_index(value):
            return min(max(math.floor(value), 0), max_index)

        return (
            to_index(x_start_float),
            to_index(x_end_float),
            to_index(y_start_float),
            to_index(y_end_float),
        )

    def _lonlat_to_tile_xy(self, lon, lat, zoom_level):
        """緯度経度からタイル座標を計算"""
        lat_rad = math.radians(lat)
        n = 2.0**zoom_level

        tile_x = (lon + 180.0) / 360.0 * n
        log_term = math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad)))
        tile_y = (1.0 - log_term / math.pi) / 2.0 * n

        return tile_x, tile_y

    def lonlat_to_webmercator(self, lonlat):
        mercator_y = math.log(math.tan((90 + lonlat[1]) * math.pi / 360))
        return [
            lonlat[0] * 20037508.34 / 180,
            mercator_y / (math.pi / 180) * 20037508.34 / 180,
        ]

    def make_bbox(self, leftbottom_lonlat, righttop_lonlat):
        leftbottom_as_3857 = self.lonlat_to_webmercator(leftbottom_lonlat)
        righttop_as_3857 = self.lonlat_to_webmercator(righttop_lonlat)
        xMin = leftbottom_as_3857[0]
        xMax = righttop_as_3857[0]
        yMin = leftbottom_as_3857[1]
        yMax = righttop_as_3857[1]
        return [xMin, xMax, yMin, yMax]

    def download_tiles(self, tileindex, feedback):
        """タイルをダウンロードし（キャッシュ済みのものは再利用）、取得できたタイルのパスを返す"""
        tile_paths = []

        for i, xyz in enumerate(tileindex):
            if feedback.isCanceled():
                break
            feedback.setProgress(100 * i / len(tileindex))

            x, y, z = xyz
            target_path = os.path.join(TMP_PATH, str(z), str(x), f"{y}.pbf")

            if not os.path.exists(target_path) or os.path.getsize(target_path) == 0:
                pbfdata = self._fetch_tile(x, y, z, feedback)
                if not pbfdata:
                    continue

                # 書き込み途中のファイルがキャッシュとして残らないよう、書き終えてから置き換える。
                # 同じタイルを同時に取得する別の処理と衝突しないよう、一時ファイル名は一意にする
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                partial_path = f"{target_path}.{uuid.uuid4().hex}.part"
                try:
                    with open(partial_path, mode="xb") as f:
                        f.write(pbfdata)
                    os.replace(partial_path, target_path)
                except BaseException:
                    if os.path.exists(partial_path):
                        os.remove(partial_path)
                    raise

            tile_paths.append(target_path)

        return tile_paths

    def _fetch_tile(self, x, y, z, feedback):
        """タイルを取得する。データのないタイル（404）とキャンセル時はNoneを返す"""
        current_tileurl = settings.GIS_VECTOR_TILE_URL.format(z=z, x=x, y=y)
        for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
            try:
                # URL is generated from a fixed GSI HTTPS tile template.
                # Users control only tile coordinates derived from the selected map extent.
                response = urllib.request.urlopen(  # nosec B310
                    current_tileurl, timeout=settings.GIS_DOWNLOAD_TIMEOUT
                )
                return response.read()
            except urllib.error.HTTPError as e:
                # 404はデータのないタイル
                if e.code == 404:
                    feedback.pushDebugInfo(f"Tile not found (404): {x}/{y}/{z}")
                    return None
                error = f"HTTP {e.code} ({current_tileurl})"
            except Exception as e:
                error = f"{e} ({current_tileurl})"

            if feedback.isCanceled():
                return None
            feedback.pushDebugInfo(f"Download attempt {attempt} failed: {error}")
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(attempt)

        # 欠けたタイルがあるまま成功扱いにしない
        raise QgsProcessingException(
            self.tr(
                "Could not download tile {z}/{x}/{y} after {attempts} attempts: {error}"
            ).format(z=z, x=x, y=y, attempts=DOWNLOAD_ATTEMPTS, error=error)
        )

    def write_layer(
        self, tile_paths, layer_key, rect, output_path, layer_name, context, feedback
    ):
        """タイルから範囲内の地物を集めてGeoPackageに書き出し、地物数を返す（キャンセル時はNone）"""
        geometrytype = self.translate_gsitype_to_geometry(
            SOURCE_LAYERS[layer_key]["datatype"]
        )
        # 「範囲で抽出」（qgis:extractbyextent）と同じ条件
        request = (
            QgsFeatureRequest()
            .setFilterRect(rect)
            .setFlags(Qgis.FeatureRequestFlag.ExactIntersect)
        )

        # タイルごとに地物を読み込み、フィールドを1つのスキーマにまとめる
        fields_by_name = {}
        tiles = []
        crs = None
        wkb_type = None
        for i, tile_path in enumerate(tile_paths):
            if feedback.isCanceled():
                return None
            feedback.setProgress(50 * i / len(tile_paths))

            pbfuri = f"{tile_path}|layername={layer_key}|geometrytype={geometrytype}"
            pbflayer = QgsVectorLayer(pbfuri, "pbf", "ogr")
            if not pbflayer.isValid():
                continue
            features = list(pbflayer.getFeatures(request))
            if not features:
                continue

            self._merge_fields(fields_by_name, pbflayer.fields())
            tiles.append((pbflayer.fields(), features))
            if crs is None:
                crs = pbflayer.crs()
            # 線と面はタイルによって単一/マルチが混在するため、マルチに統一する
            wkb_type = QgsWkbTypes.promoteNonPointTypesToMulti(pbflayer.wkbType())

        if not tiles:
            return 0
        if feedback.isCanceled():
            return None

        fields = QgsFields()
        for field in fields_by_name.values():
            fields.append(field)

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer_name
        options.fileEncoding = "UTF-8"
        writer = QgsVectorFileWriter.create(
            output_path, fields, wkb_type, crs, context.transformContext(), options
        )
        if writer.hasError() != QgsVectorFileWriter.WriterError.NoError:
            raise QgsProcessingException(
                self.tr("Failed to save {}. Result : {}").format(
                    layer_name, writer.errorMessage()
                )
            )

        count = 0
        try:
            for i, (tile_fields, features) in enumerate(tiles):
                if feedback.isCanceled():
                    break
                indices = [tile_fields.lookupField(name) for name in fields.names()]
                out_features = []
                for feature in features:
                    geometry = feature.geometry()
                    if QgsWkbTypes.isMultiType(wkb_type):
                        geometry.convertToMultiType()
                    attributes = feature.attributes()
                    out_feature = QgsFeature(fields)
                    out_feature.setGeometry(geometry)
                    out_feature.setAttributes(
                        [attributes[index] if index >= 0 else None for index in indices]
                    )
                    out_features.append(out_feature)
                if not writer.addFeatures(out_features):
                    raise QgsProcessingException(
                        self.tr("Failed to save {}. Result : {}").format(
                            layer_name, writer.errorMessage()
                        )
                    )
                count += len(out_features)
                feedback.setProgress(50 + 50 * (i + 1) / len(tiles))
        finally:
            # 削除時にファイルが閉じられる
            del writer

        if feedback.isCanceled():
            # 途中までの地物しかないファイルは残さない
            os.remove(output_path)
            return None
        return count

    def _merge_fields(self, fields_by_name, tile_fields):
        """タイルのフィールドを追加する。タイル間で型が異なるフィールドは共通の型にする"""
        double_fields = getattr(settings, "DOUBLE_FIELDS", ())
        for tile_field in tile_fields:
            name = tile_field.name()
            # GeoPackageのフィールド名は大文字と小文字を区別しない
            key = name.lower()
            field_type = (
                QMetaType.Type.Double if name in double_fields else tile_field.type()
            )

            if key not in fields_by_name:
                if field_type == tile_field.type():
                    fields_by_name[key] = QgsField(tile_field)
                else:
                    fields_by_name[key] = QgsField(name, field_type)
                continue

            current = fields_by_name[key]
            if current.type() != field_type:
                common_type = self._common_field_type(current.type(), field_type)
                fields_by_name[key] = QgsField(current.name(), common_type)

    def _common_field_type(self, type_a, type_b):
        """2つのフィールド型の両方の値を表せる型を返す"""
        if type_a in NUMERIC_TYPES and type_b in NUMERIC_TYPES:
            if QMetaType.Type.Double in (type_a, type_b):
                return QMetaType.Type.Double
            return QMetaType.Type.LongLong
        return QMetaType.Type.QString

    def translate_gsitype_to_geometry(self, gsitype):
        if gsitype == "点":
            return "Point"
        elif gsitype == "線":
            return "LineString"
        else:
            return "Polygon"

    def name(self):
        return "gsi_vt_downloader"

    def displayName(self):
        return self.tr("Load GSI Vector Tiles")

    def createInstance(self):
        return GSIVectorTileDownloadAlgorithm()

    def tr(self, string):
        return QCoreApplication.translate("GSIVectorTileDownloadAlgorithm", string)
