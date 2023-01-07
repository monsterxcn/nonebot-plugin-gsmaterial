import json
from pathlib import Path
from typing import Tuple

from httpx import Client
from pytz import UnknownTimeZoneError, timezone

from nonebot import get_driver
from nonebot.log import logger

_driver = get_driver()


def _init_picture_dir(env_key: str, config_dir: Path) -> Tuple[str, str, Path]:
    """根据本地文件决定后续下载文件路径及命名"""

    env_value = getattr(_driver.config, env_key, None)
    if not env_value:
        sub_dirs = {
            "gsmaterial_avatar": "avatar",
            "gsmaterial_weapon": "weapon",
            "gsmaterial_item": "item",
        }
        return "name", "png", config_dir / sub_dirs[env_key]
    env_value = Path(env_value)
    if not env_value.exists():
        raise ValueError(f".env 文件中 {env_key} 填写的路径不存在！")
    elif env_value.is_file():
        pic_name = "id" if str(env_value.name[0]).isdigit() else "name"
        pic_fmt = env_value.name.split(".")[-1]
        pic_dir = env_value.parent
        return pic_name, pic_fmt, pic_dir
    elif env_value.is_dir():
        pic_name, pic_fmt = "name", "png"
        for already_have in env_value.iterdir():
            pic_name = "id" if str(already_have.name[0]).isdigit() else "name"
            pic_fmt = already_have.name.split(".")[-1]
            break
        return pic_name, pic_fmt, env_value
    raise ValueError(f".env 文件中 {env_key} 填写的值异常！应填写图片文件或文件夹路径")


# 时区设定
# TZ="Asia/Shanghai"
try:
    TZ = timezone(str(getattr(_driver.config, "tz", "Asia/Shanghai")))
except UnknownTimeZoneError:
    TZ = timezone("Asia/Shanghai")

# 材料下载镜像
# GSMATERIAL_MIRROR="https://api.ambr.top/assets/UI/"
DL_MIRROR = str(
    getattr(_driver.config, "gsmaterial_mirror", "https://api.ambr.top/assets/UI/")
)

# 每日推送时间
# GSMATERIAL_SCHEDULER="8:10"
SCHEDULER_TIME = str(getattr(_driver.config, "gsmaterial_scheduler", "8:10"))
SCHED_HOUR, SCHED_MINUTE = SCHEDULER_TIME.split(":")

# 每日材料绘制是否跳过三星物品
# GSMATERIAL_SKIP_THREE=True
SKIP_THREE = bool(getattr(_driver.config, "gsmaterial_skip_three", True))

# 配置缓存路径
# GSMATERIAL_CONFIG="/path/to/data/gsmaterial"
_default_dir = Path() / "data" / "gsmaterial"
CONFIG_DIR = Path(getattr(_driver.config, "gsmaterial_config", _default_dir))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
(CONFIG_DIR / "draw").mkdir(parents=True, exist_ok=True)
(CONFIG_DIR / "cache").mkdir(parents=True, exist_ok=True)

# 下载缓存路径
# GSMATERIAL_AVATAR="/path/to/avatars"
# GSMATERIAL_AVATAR="/path/to/avatars/10000002.png"
# GSMATERIAL_AVATAR="/path/to/avatars/神里绫华.png"
_avatar, _avatar_fmt, _avatar_dir = _init_picture_dir("gsmaterial_avatar", CONFIG_DIR)
_weapon, _weapon_fmt, _weapon_dir = _init_picture_dir("gsmaterial_weapon", CONFIG_DIR)
_item, _item_fmt, _item_dir = _init_picture_dir("gsmaterial_item", CONFIG_DIR)
_avatar_dir.mkdir(parents=True, exist_ok=True)
_weapon_dir.mkdir(parents=True, exist_ok=True)
_item_dir.mkdir(parents=True, exist_ok=True)
DL_CFG = {
    "avatar": {"dir": _avatar_dir, "file": _avatar, "fmt": _avatar_fmt},
    "weapon": {"dir": _weapon_dir, "file": _weapon, "fmt": _weapon_fmt},
    "item": {"dir": _item_dir, "file": _item, "fmt": _item_fmt},
}
logger.info(f"图片缓存规则：\n{DL_CFG}")

# 配置文件初始化
if not (CONFIG_DIR / "sub.json").exists():
    (CONFIG_DIR / "sub.json").write_text(
        json.dumps({"群组": [], "私聊": []}, ensure_ascii=False, indent=2), encoding="UTF-8"
    )
if not (CONFIG_DIR / "cookie.json").exists():
    (CONFIG_DIR / "cookie.json").write_text(
        json.dumps({}, ensure_ascii=False, indent=2), encoding="UTF-8"
    )

# 角色别名、武器别名初始化
_client = Client(verify=False)
ITEM_ALIAS = _client.get("https://cdn.monsterx.cn/bot/gsmaterial/item-alias.json").json()
(CONFIG_DIR / "item-alias.json").write_text(
    json.dumps(ITEM_ALIAS, ensure_ascii=False, indent=2), encoding="utf-8"
)

# 素材主键
WEEKLY_BOSS = [  # 暂时拿第一个作为标识
    ["风魔龙·特瓦林", "往日的天空之王", "深入风龙废墟", "追忆：暴风般狂啸之龙", "风龙", "风魔龙"],
    ["安德留斯", "奔狼的领主", "北风的王狼，奔狼的领主", "狼", "北风狼", "王狼"],
    ["「公子」", "愚人众执行官末席", "进入「黄金屋」", "追忆：黄金与孤影", "公子", "达达利亚", "可达鸭", "鸭鸭"],
    ["若陀龙王", "被封印的岩龙之王", "「伏龙树」之底", "追忆：摇撼山岳之龙", "若托", "若陀", "龙王"],
    ["「女士」", "愚人众执行官第八席", "鸣神岛·天守", "追忆：红莲的真剑试合", "女士", "罗莎琳", "魔女"],
    ["祸津御建鸣神命", "雷电之稻妻殿", "梦想乐土之殁", "追忆：永恒的守护者", "雷神", "雷电", "雷军", "将军"],
    ["「正机之神」", "七叶寂照秘密主", "净琉璃工坊", "追忆：七叶中尊琉璃坛", "正机", "散兵", "伞兵", "秘密主"],
]

# API 地址
AMBR = {
    "每日采集": "https://api.ambr.top/v2/chs/dailyDungeon",
    "角色列表": "https://api.ambr.top/v2/chs/avatar",
    "角色详情": "https://api.ambr.top/v2/chs/avatar/{id}",
    "武器列表": "https://api.ambr.top/v2/chs/weapon",
    "武器详情": "https://api.ambr.top/v2/chs/weapon/{id}",
    "材料列表": "https://api.ambr.top/v2/chs/material",
    "材料详情": "https://api.ambr.top/v2/chs/material/{id}",
    "圣遗物列表": "https://api.ambr.top/v2/chs/reliquary",
    "圣遗物详情": "https://api.ambr.top/v2/chs/reliquary/{id}",
    "升级材料": "https://api.ambr.top/v2/static/upgrade",
    "通告": "https://api.ambr.top/assets/data/event.json",
}
MYS = {
    "技能": "https://api-takumi.mihoyo.com/event/e20200928calculate/v1/avatarSkill/list",
    "计算": "https://api-takumi.mihoyo.com/event/e20200928calculate/v2/compute",
    "_stoken": "https://api-takumi.mihoyo.com/auth/api/getMultiTokenByLoginTicket",
    "_cookie": "https://api-takumi.mihoyo.com/auth/api/getCookieAccountInfoBySToken",
}
