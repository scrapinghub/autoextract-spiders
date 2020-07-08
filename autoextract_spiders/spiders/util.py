import os
import re
import logging
from enum import Enum
from typing import Iterable
from urllib.parse import urlsplit
from datetime import datetime, timezone
try:
    import ujson as json
except ImportError:
    import json

import requests
from .config import CONFIG_PER_NETLOC

logger = logging.getLogger(__name__)


def utc_iso_date() -> datetime:
    dt = datetime.utcnow().replace(tzinfo=timezone.utc, microsecond=0)
    return dt.isoformat()


def is_valid_url(url: str) -> bool:
    """
    Minimal validation of URLs
    Unfortunately urllib.parse.urlparse(...) is not identifying correct URLs
    """
    return isinstance(url, (str, bytes)) and len(url) > 8 and url.split('://', 1)[0] in ('http', 'https')


def is_blacklisted_url(url: str) -> bool:
    netloc = urlsplit(url).netloc
    for key, config in CONFIG_PER_NETLOC.items():
        if netloc.endswith(key) and 'blacklisted' in config:
            return True
    return False


def is_autoextract_request(request):
    if request.meta.get('autoextract') \
            and isinstance(request.meta['autoextract'], dict) \
            and request.meta['autoextract'].get('original_url'):
        return True
    return False


def is_index_url(url: str) -> bool:
    """
    Check if the URL is an index page
    """
    return urlsplit(url).path in ('', '/', '/index.html', '/index.htm', '/index.php')


def could_be_content_page(url: str) -> bool:
    """
    Try to guess if the link is a content page.
    It's not a perfect check, but it can identify URLs that are obviously not content.
    """
    url = url.lower().rstrip('/')
    if url.endswith('/signin') or url.endswith('/login') or \
            url.endswith('/login-page') or url.endswith('/logout'):
        return False
    if url.endswith('/my-account') or url.endswith('/my-wishlist'):
        return False
    if re.search('/(lost|forgot)[_-]password$', url):
        return False
    if url.endswith('/search') or url.endswith('/archive'):
        return False
    if url.endswith('/privacy-policy') or url.endswith('/cookie-policy') or \
            url.endswith('/terms-conditions'):
        return False
    if url.endswith('/tos') or re.search('/terms[_-]of[_-](service|use)$', url):
        return False
    # Yei, it might be a content page
    return True


def maybe_is_product(url: str) -> bool:
    """
    Try to guess if the link is a product page.
    """
    if not could_be_content_page(url):
        return False
    if re.search('/about-?(us)?$', url) or re.search('/contact-?(us)?$', url):
        return False
    if url.endswith('/rss') or url.endswith('/feed'):
        return False
    return True


def maybe_is_article(url: str) -> bool:
    """
    Try to guess if the link is an article page.
    """
    if not could_be_content_page(url):
        return False
    if re.search('/contact-?(us)?$', url):
        return False
    if url.endswith('/shipping') or url.endswith('/returns'):
        return False
    if url.endswith('/pricing') or url.endswith('/best-deals'):
        return False
    if url.endswith('/cart') or url.endswith('/shop') or url.endswith('/checkout'):
        return False
    # Yei, it might be an article
    return True


def maybe_is_job_posting(url: str) -> bool:
    """
    Try to guess if the link is a job posting page.
    """
    if not could_be_content_page(url):
        return False
    if url.endswith('/rss') or url.endswith('/feed'):
        return False
    if url.endswith('/shipping') or url.endswith('/returns'):
        return False
    if url.endswith('/pricing') or url.endswith('/best-deals'):
        return False
    if url.endswith('/cart') or url.endswith('/shop') or url.endswith('/checkout'):
        return False
    return True


def load_sources(fname: str) -> Iterable:
    """
    Load article/ product URLs from a file, or a remote URL.
    The file must be either a JSON, or JL file, in the form:
        {"url": "https://www.whatever.com/...", "etc": "..."}
    In case of JSON, if the data is a Dict, only the values are used.
    """
    # Load from remote URL
    if is_valid_url(fname):
        # Using Requests lib because Scrapy Requests refuses to parse Google Drive links
        headers = {
            'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en,en-UK;q=0.8,en-US;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Upgrade-Insecure-Requests': '1',
        }
        text = requests.get(fname, headers=headers).text
        yield from _load_from_text(text)
    # Load from local file
    elif os.path.isfile(fname):
        with open(fname) as fd:
            text = fd.read()
        yield from _load_from_text(text)
    else:
        raise ValueError(f'Invalid sources file: {fname}')


def _load_from_text(text: str) -> Iterable:
    try:
        data = _load_json(text)
    except Exception:
        data = _load_jl(text)
    for item in data:
        if isinstance(item, dict) and is_valid_url(item.get('url')):
            yield item['url']
        elif isinstance(item, str) and is_valid_url(item):
            yield item
        else:
            logger.warning('Invalid source object: %s', item)


def _load_json(text: str) -> Iterable:
    links = json.loads(text)
    if isinstance(links, dict):
        return links.values()
    elif isinstance(links, list):
        return links
    else:
        raise ValueError(f'Invalid source data type: {type(links)}')


def _load_jl(data: str) -> Iterable:
    for line in data.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line[0] == '#':
            continue
        try:
            # Try JSON lines
            yield json.loads(line)
        except Exception:
            # Try one URL per line
            if line[:4] == 'http':
                yield {'url': line}
            else:
                logger.warning('Invalid source URL: %s', line)


class FingerprintPrefix(Enum):
    """
    Prefixes to use in fingerprinting given the type of request performed.
    Allows to have independent deduplication for Scrapy and AutoExtract requests.
    """
    SCRAPY = 's'  # For Scrapy requests
    AUTOEXTRACT = 'a'  # For AutoExtract requests