import json
from pathlib import Path

from nonebot import get_driver

driver = get_driver()
SKIP_THREE = (
    bool(driver.config.gsmaterial_skip_three)
    if hasattr(driver.config, "gsmaterial_skip_three")
    else True
)
LOCAL_DIR = (
    (Path(driver.config.resources_dir) / "gsmaterial")
    if hasattr(driver.config, "resources_dir")
    else (Path() / "data" / "gsmaterial")
)
if not LOCAL_DIR.exists():
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
if not (LOCAL_DIR / "sub.json").exists():
    (LOCAL_DIR / "sub.json").write_text(
        json.dumps({"群组": [], "私聊": []}, ensure_ascii=False, indent=2), encoding="UTF-8"
    )
