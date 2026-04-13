"""Paper trading adapter — same IBKR API, paper account."""
from midas_broker.ibkr.client import IBKRClient
import structlog
logger = structlog.get_logger(__name__)

class PaperTradingClient(IBKRClient):
    """Wraps IBKRClient for paper trading."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("paper.client_initialized")
    @property
    def is_paper(self) -> bool:
        return True

