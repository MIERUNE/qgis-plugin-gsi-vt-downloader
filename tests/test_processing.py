"""Tests for the GSI vector tiles Processing algorithm.

The tiles are generated with the GDAL MVT driver into a temporary tile cache,
and downloads are stubbed out, so the tests do not access the GSI server.
"""

import importlib
import importlib.util
import io
import os
import sys
import urllib.error

import pytest
from osgeo import gdal, ogr, osr
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsField,
    QgsFields,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QMetaType

PACKAGE_NAME = "gsivtdownloader"


def load_plugin():
    """Load the plugin root as the `gsivtdownloader` package.

    processing_provider uses relative imports (`from .. import settings`), and
    the repository directory name is not a valid Python identifier, so the
    plugin is loaded from its file path under the package name used for
    releases.
    """
    if PACKAGE_NAME in sys.modules:
        return sys.modules[PACKAGE_NAME]
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        os.path.join(plugin_dir, "__init__.py"),
        submodule_search_locations=[plugin_dir],
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load the plugin from %s" % plugin_dir)
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)
    return module


gsivtdownloader = load_plugin()
gsi_vt_dl_algorithm = importlib.import_module(
    PACKAGE_NAME + ".processing_provider.gsi_vt_dl_algorithm"
)

ALGORITHM_ID = "gsivtdl:gsi_vt_downloader"
LAYER_KEYS = list(gsi_vt_dl_algorithm.SOURCE_LAYERS.keys())

ZOOM = 16
ORIGIN = 20037508.342789244
TILE_SIZE = 2 * ORIGIN / 2**ZOOM
# Two neighbouring z16 tiles around Tokyo Station
TILE_A = (58210, 25806)
TILE_B = (58211, 25806)


def tile_center(tile):
    x, y = tile
    return -ORIGIN + (x + 0.5) * TILE_SIZE, ORIGIN - (y + 0.5) * TILE_SIZE


def extent_around_centers():
    """An EPSG:3857 extent covering the centers of TILE_A and TILE_B only"""
    ax, ay = tile_center(TILE_A)
    bx, _ = tile_center(TILE_B)
    return f"{ax - 100},{bx + 100},{ay - 100},{ay + 100} [EPSG:3857]"


def add_feature(layer, wkt, **attributes):
    feature = ogr.Feature(layer.GetLayerDefn())
    for name, value in attributes.items():
        feature.SetField(name, value)
    feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
    layer.CreateFeature(feature)


@pytest.fixture
def tile_cache(tmp_path, monkeypatch):
    """Write GSI-like z16 tiles into a temporary tile cache, and stub downloads"""
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    source_path = str(tmp_path / "source.gpkg")
    source = ogr.GetDriverByName("GPKG").CreateDataSource(source_path)

    ax, ay = tile_center(TILE_A)
    bx, by = tile_center(TILE_B)

    road = source.CreateLayer("road", srs, ogr.wkbLineString)
    road.CreateField(ogr.FieldDefn("ftCode", ogr.OFTInteger))
    road.CreateField(ogr.FieldDefn("Width", ogr.OFTInteger))
    add_feature(
        road, f"LINESTRING({ax - 50} {ay},{ax + 50} {ay})", ftCode=2701, Width=25
    )
    add_feature(
        road, f"LINESTRING({bx - 50} {by},{bx + 50} {by})", ftCode=2703, Width=30
    )
    # inside TILE_A, but outside the extent
    add_feature(
        road, f"LINESTRING({ax - 250} {ay + 250},{ax - 200} {ay + 250})", ftCode=2701
    )

    label = source.CreateLayer("label", srs, ogr.wkbPoint)
    label.CreateField(ogr.FieldDefn("knj", ogr.OFTString))
    label.CreateField(ogr.FieldDefn("arrngAgl", ogr.OFTInteger))
    add_feature(label, f"POINT({ax} {ay})", knj="東京駅", arrngAgl=0)
    source = None

    cache_dir = tmp_path / "tiles"
    gdal.VectorTranslate(
        str(cache_dir),
        source_path,
        format="MVT",
        datasetCreationOptions=[f"MINZOOM={ZOOM}", f"MAXZOOM={ZOOM}", "COMPRESS=NO"],
    )
    monkeypatch.setattr(gsi_vt_dl_algorithm, "TMP_PATH", str(cache_dir))

    requested = []

    def urlopen(url, timeout=None):
        requested.append(url)
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(gsi_vt_dl_algorithm.urllib.request, "urlopen", urlopen)
    return requested


@pytest.fixture
def plugin(qgis_app):
    plugin = gsivtdownloader.classFactory(None)
    plugin.initProcessing()
    yield plugin
    plugin.unload()
    QgsProject.instance().clear()


def create_context():
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    return context


def run(parameters, feedback=None):
    alg = QgsApplication.processingRegistry().createAlgorithmById(ALGORITHM_ID)
    context = create_context()
    ok, message = alg.checkParameterValues(parameters, context)
    assert ok, message
    results, ok = alg.run(parameters, context, feedback or QgsProcessingFeedback())
    return results, ok, context


def parameters(layer_keys, output_folder, zoom=ZOOM, extent=None):
    return {
        "INPUT_EXTENT": extent or extent_around_centers(),
        "SOURCE_LAYER": [LAYER_KEYS.index(key) for key in layer_keys],
        "ZOOM_LEVEL": zoom,
        "OUTPUT_FOLDER": str(output_folder),
    }


def test_init_processing_registers_provider(qgis_app):
    """qgis_process only calls initProcessing(), not initGui()"""
    registry = QgsApplication.processingRegistry()
    plugin = gsivtdownloader.classFactory(None)
    plugin.initProcessing()
    assert registry.algorithmById(ALGORITHM_ID) is not None

    plugin.unload()
    assert registry.providerById("gsivtdl") is None


def test_outputs(plugin):
    alg = QgsApplication.processingRegistry().algorithmById(ALGORITHM_ID)
    assert {output.name() for output in alg.outputDefinitions()} == {
        "OUTPUT_FOLDER",
        "OUTPUT_LAYERS",
    }


def test_rejects_unavailable_zoom_level(plugin, tmp_path):
    alg = QgsApplication.processingRegistry().algorithmById(ALGORITHM_ID)
    ok, message = alg.checkParameterValues(
        parameters(["road", "building"], tmp_path, zoom=12), create_context()
    )
    assert not ok
    assert "building (z13-16)" in message
    assert "road" not in message


def test_rejects_too_many_tiles(plugin, tmp_path):
    alg = QgsApplication.processingRegistry().algorithmById(ALGORITHM_ID)
    ok, message = alg.checkParameterValues(
        parameters(["road"], tmp_path, extent="122,154,20,46 [EPSG:4326]"),
        create_context(),
    )
    assert not ok
    assert str(gsi_vt_dl_algorithm.TILES_LIMIT) in message


def test_writes_layers_and_loads_them_on_completion(plugin, tile_cache, tmp_path):
    output_folder = tmp_path / "output"
    results, ok, context = run(parameters(["road", "building", "label"], output_folder))
    assert ok

    road_path = str(output_folder / "road_z16.gpkg")
    label_path = str(output_folder / "label_z16.gpkg")
    assert results["OUTPUT_FOLDER"] == str(output_folder)
    # building has no features in the tiles, so no layer is written for it
    assert results["OUTPUT_LAYERS"] == [road_path, label_path]
    assert not os.path.exists(output_folder / "building_z16.gpkg")

    # the algorithm leaves adding the layers to Processing
    assert QgsProject.instance().count() == 0
    assert set(context.layersToLoadOnCompletion()) == {road_path, label_path}
    # the tiles were read from the cache
    assert tile_cache == []

    road = QgsVectorLayer(road_path, "road", "ogr")
    assert road.featureCount() == 2  # the feature outside the extent is excluded
    assert road.wkbType() == Qgis.WkbType.MultiLineString
    width = road.fields().field("Width")
    assert width.type() == QMetaType.Type.Double  # settings.DOUBLE_FIELDS
    assert sorted(f["Width"] for f in road.getFeatures()) == [25.0, 30.0]

    label = QgsVectorLayer(label_path, "label", "ogr")
    assert label.featureCount() == 1
    assert label.wkbType() == Qgis.WkbType.Point
    feature = next(label.getFeatures())
    assert feature["knj"] == "東京駅"
    assert label.fields().field("arrngAgl").type() == QMetaType.Type.Double


def test_fails_when_no_features_are_found(plugin, tile_cache, tmp_path):
    output_folder = tmp_path / "output"
    _, ok, _ = run(parameters(["building"], output_folder))
    assert not ok
    assert not os.path.exists(output_folder / "building_z16.gpkg")


def test_fails_when_a_tile_cannot_be_downloaded(plugin, tmp_path, monkeypatch):
    monkeypatch.setattr(gsi_vt_dl_algorithm, "TMP_PATH", str(tmp_path / "cache"))
    monkeypatch.setattr(gsi_vt_dl_algorithm.time, "sleep", lambda seconds: None)
    requested = []

    def urlopen(url, timeout=None):
        requested.append(url)
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", None, None)

    monkeypatch.setattr(gsi_vt_dl_algorithm.urllib.request, "urlopen", urlopen)

    output_folder = tmp_path / "output"
    _, ok, _ = run(parameters(["road"], output_folder))
    assert not ok
    # retried, then stopped without requesting the remaining tile
    assert len(requested) == gsi_vt_dl_algorithm.DOWNLOAD_ATTEMPTS
    assert not os.path.exists(output_folder / "road_z16.gpkg")


def test_retries_a_failed_download(plugin, tile_cache, tmp_path, monkeypatch):
    x, y = TILE_A
    tile_path = os.path.join(
        gsi_vt_dl_algorithm.TMP_PATH, str(ZOOM), str(x), f"{y}.pbf"
    )
    with open(tile_path, "rb") as f:
        tile_data = f.read()
    os.remove(tile_path)

    monkeypatch.setattr(gsi_vt_dl_algorithm.time, "sleep", lambda seconds: None)
    requested = []

    def urlopen(url, timeout=None):
        requested.append(url)
        # the first attempt fails, the second one succeeds
        if len(requested) == 1:
            raise urllib.error.HTTPError(url, 503, "Service Unavailable", None, None)
        return io.BytesIO(tile_data)

    monkeypatch.setattr(gsi_vt_dl_algorithm.urllib.request, "urlopen", urlopen)

    results, ok, _ = run(parameters(["road"], tmp_path / "output"))
    assert ok
    assert len(requested) == 2
    road = QgsVectorLayer(results["OUTPUT_LAYERS"][0], "road", "ogr")
    assert road.featureCount() == 2


def test_cancel_leaves_no_partial_file(plugin, tile_cache, tmp_path):
    output_folder = tmp_path / "output"
    feedback = QgsProcessingFeedback()
    # 2 steps (download, road): cancel while the road layer is being written
    feedback.progressChanged.connect(
        lambda progress: feedback.cancel() if progress > 80 else None
    )
    results, ok, _ = run(parameters(["road"], output_folder), feedback)

    assert feedback.isCanceled()
    assert results["OUTPUT_LAYERS"] == []
    assert not os.path.exists(output_folder / "road_z16.gpkg")


def test_merge_fields_unifies_types_across_tiles(qgis_app):
    alg = gsi_vt_dl_algorithm.GSIVectorTileDownloadAlgorithm()

    def fields(*definitions):
        result = QgsFields()
        for name, field_type in definitions:
            result.append(QgsField(name, field_type))
        return result

    fields_by_name = {}
    alg._merge_fields(
        fields_by_name,
        fields(
            ("ratio", QMetaType.Type.Int),
            ("code", QMetaType.Type.Int),
            ("note", QMetaType.Type.QString),
            ("alti", QMetaType.Type.Int),
        ),
    )
    alg._merge_fields(
        fields_by_name,
        fields(
            ("ratio", QMetaType.Type.Double),
            ("code", QMetaType.Type.LongLong),
            ("note", QMetaType.Type.Int),
        ),
    )

    types = {field.name(): field.type() for field in fields_by_name.values()}
    assert types == {
        "ratio": QMetaType.Type.Double,
        "code": QMetaType.Type.LongLong,
        "note": QMetaType.Type.QString,
        "alti": QMetaType.Type.Double,  # settings.DOUBLE_FIELDS
    }
