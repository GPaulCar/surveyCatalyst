from data.ingestion.providers.itiner_e import ItinerEProvider
from data.ingestion.providers.viabundus import ViabundusProvider
from data.ingestion.providers.blfd import BLfDProvider
from data.ingestion.providers.gesis import GESISProvider

PROVIDERS = {
    "itiner_e": ItinerEProvider,
    "viabundus": ViabundusProvider,
    "blfd": BLfDProvider,
    "gesis": GESISProvider,
}

def get_provider(source_key: str):
    provider_cls = PROVIDERS.get(source_key)
    if provider_cls is None:
        raise KeyError(f"Unknown provider: {source_key}")
    return provider_cls
