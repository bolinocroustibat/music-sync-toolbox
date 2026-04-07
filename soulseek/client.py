from slskd_api import SlskdClient

from soulseek.config import Config


def make_client(cfg: Config) -> SlskdClient:
    """Build an authenticated SlskdClient from toolbox config."""
    return SlskdClient(
        cfg.host,
        api_key=cfg.api_key,
        url_base=cfg.url_base,
        verify_ssl=cfg.verify_ssl,
        timeout=cfg.request_timeout,
    )
