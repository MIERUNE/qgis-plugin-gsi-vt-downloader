import importlib.util
import os
import unittest
from string import Formatter
from urllib.parse import urlsplit

EXPECTED_SCHEME = "https"
EXPECTED_HOST = "cyberjapandata.gsi.go.jp"


def load_settings():
    """Load the plugin's settings.py directly from its file path.

    The plugin package itself cannot be imported here: processing_provider
    uses `from .. import settings`, and the repository directory name is not a
    valid Python identifier. Loading by path keeps this test independent of
    the import layout and of where CI mounts the plugin.
    """
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.py")
    )
    spec = importlib.util.spec_from_file_location("gsi_vt_settings", file_path)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load settings.py from %s" % file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


settings = load_settings()


class TestTileUrl(unittest.TestCase):
    """Guard the assumptions behind the `# nosec B310` suppression in
    processing_provider/gsi_vt_dl_algorithm.py.

    Bandit's B310 (audit_url_open) is suppressed at the urlopen() call site
    because the URL is built from a fixed HTTPS template and the caller only
    substitutes tile coordinates. Once that stops being true the suppression
    would silently hide a real file:// / ftp:// / SSRF issue, so these tests
    fail instead.
    """

    def test_template_scheme_is_https(self):
        """urlopen() must never be handed a file:// or ftp:// URL."""
        scheme = urlsplit(settings.GIS_VECTOR_TILE_URL).scheme
        self.assertEqual(
            scheme,
            EXPECTED_SCHEME,
            "GIS_VECTOR_TILE_URL must use %s, got %s. The `# nosec B310` "
            "suppression is only valid for a fixed HTTPS URL."
            % (EXPECTED_SCHEME, scheme),
        )

    def test_template_host_is_gsi(self):
        """The download target must stay the GSI tile server."""
        netloc = urlsplit(settings.GIS_VECTOR_TILE_URL).netloc
        self.assertEqual(
            netloc,
            EXPECTED_HOST,
            "GIS_VECTOR_TILE_URL must point at %s, got %s." % (EXPECTED_HOST, netloc),
        )

    def test_template_only_substitutes_tile_coordinates(self):
        """Only {z}/{x}/{y} may be substituted, and nothing else."""
        placeholders = {
            name
            for _, name, _, _ in Formatter().parse(settings.GIS_VECTOR_TILE_URL)
            if name is not None
        }
        self.assertEqual(
            placeholders,
            {"x", "y", "z"},
            "Unexpected placeholders in GIS_VECTOR_TILE_URL: %s. Anything "
            "beyond tile coordinates widens what a caller can control."
            % sorted(placeholders),
        )

    def test_scheme_and_host_are_not_substitutable(self):
        """The placeholders must sit in the path, not in the scheme or host."""
        parts = urlsplit(settings.GIS_VECTOR_TILE_URL)
        for label, component in (("scheme", parts.scheme), ("host", parts.netloc)):
            self.assertNotIn(
                "{",
                component,
                "The URL %s must be a literal, not a placeholder: %s"
                % (label, component),
            )

    def test_hostile_coordinates_cannot_leave_the_gsi_host(self):
        """Formatting is safe even for coordinates that look like URLs.

        Tile coordinates are integers in practice (create_tile_index_from_bbox
        returns math.floor() results), so this only pins down that the template
        shape itself gives a caller no way to redirect the request.
        """
        hostile_values = [
            "@evil.example.com",
            "..",
            "https://evil.example.com/",
            "file:///etc/passwd",
        ]
        for value in hostile_values:
            url = settings.GIS_VECTOR_TILE_URL.format(z=value, x=value, y=value)
            parts = urlsplit(url)
            self.assertEqual(parts.scheme, EXPECTED_SCHEME, url)
            self.assertEqual(parts.netloc, EXPECTED_HOST, url)

    def test_download_timeout_is_a_positive_number(self):
        """urlopen() gets this timeout; None would let a stalled tile hang."""
        timeout = settings.GIS_DOWNLOAD_TIMEOUT
        self.assertIsInstance(timeout, (int, float))
        self.assertGreater(timeout, 0)


if __name__ == "__main__":
    unittest.main()
