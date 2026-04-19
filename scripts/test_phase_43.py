import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backup.manifest_service import BackupManifestService

path = BackupManifestService().write_manifest(ROOT / "backup_manifest.json")
print(path)
