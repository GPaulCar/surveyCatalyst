import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.ingestion.download_manifest_service import DownloadManifestService

workspace = ROOT / "data_workspace"
workspace.mkdir(exist_ok=True)
sample = workspace / "sample_download.txt"
sample.write_text("sample artifact\n", encoding="utf-8")

svc = DownloadManifestService(workspace)
entry = svc.build_manifest_entry(
    source_key="sample_source",
    remote_url="https://example.com/sample_download.txt",
    local_path=sample,
    version_label="test-1",
)
manifest_path = svc.write_manifest("sample_source", entry)
print(manifest_path)
print(json.dumps(entry, indent=2))
