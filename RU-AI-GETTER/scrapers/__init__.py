"""Load only the selected scraper, keeping OCR optional for PDF readers."""
from importlib import import_module

_MODULES = {
    'RestaurantScraper': 'base_scraper',
    'BlumenauScraper': 'blumenau_scraper',
    'CuritibanosScraper': 'curitibanos_scraper',
    'FlorianopolisCCAScraper': 'florianopolis_cca_scraper',
    'FlorianopolisTrindadeScraper': 'florianopolis_trindade_scraper',
    'JoinvilleScraper': 'joinville_scraper',
}
__all__ = list(_MODULES)


def __getattr__(name):
    if name not in _MODULES:
        raise AttributeError(name)
    value = getattr(import_module(f'.{_MODULES[name]}', __name__), name)
    globals()[name] = value
    return value
