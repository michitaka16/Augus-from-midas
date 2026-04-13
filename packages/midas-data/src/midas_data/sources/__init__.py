"""Data source adapters for Midas data fabric."""

from midas_data.sources.eodhd import EODHDClient
from midas_data.sources.fred import FREDClient
from midas_data.sources.yahoo import YahooClient
from midas_data.sources.perplexity import PerplexityClient
from midas_data.sources.ibkr_spread import IBKRSpreadProxy

__all__ = ["EODHDClient", "FREDClient", "YahooClient", "PerplexityClient", "IBKRSpreadProxy"]
