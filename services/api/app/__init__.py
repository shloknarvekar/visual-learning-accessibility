"""Visual Learning API: ingestion, AI lesson generation, and the HTTP API."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("visual-learning-api")
except PackageNotFoundError:  # running from a source tree without `pip install -e`
    __version__ = "0.0.0"
