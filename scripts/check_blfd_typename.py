from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.ingestion.providers.blfd import BLfDProvider


provider = BLfDProvider()
params = {
    "service": "WFS",
    "request": "GetCapabilities",
    "version": "2.0.0",
}
url = provider.WFS_URL + "?" + urlencode(params)
response = requests.get(url, timeout=120)
response.raise_for_status()
text = response.text

print("Saved response length:", len(text))
caps_path = ROOT / "data_workspace" / "blfd" / "reports" / "blfd_wfs_capabilities.xml"
caps_path.parent.mkdir(parents=True, exist_ok=True)
caps_path.write_text(text, encoding="utf-8")
print(caps_path)
print("Search the XML for FeatureType and Name values to choose the correct typename if ProtectedSites does not work.")
