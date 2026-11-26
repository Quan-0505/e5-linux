import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
document = json.loads(path.read_text(encoding="utf-8"))
files = document["luci-app-appdpi"]["read"]["file"]
for directory in ("/var/run/appdpi", "/tmp/run/appdpi", "/tmp/appdpi"):
    assert "read" in files[directory + "/status.json"], directory
    for name in ("devices.json", "ips.json"):
        files[directory + "/" + name] = ["read"]
path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
