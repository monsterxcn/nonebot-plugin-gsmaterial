import json
from pathlib import Path


def read(fn: str):
    return json.loads(Path(f"./{fn}").read_text(encoding="UTF-8"))


GRE, END = "\033[32m", "\033[0m"
AVATAR = read("AvatarExcelConfigData.json")
WEAPONS = read("WeaponExcelConfigData.json")
TEXTMAP_CHS = read("TextMapCHS.json")
AVATAR_ALIAS = read("char-alias.json")
AVATAR_DETAIL = read("Avatar.json")
AVATAR_DETAIL = {i["Id"]: i for i in AVATAR_DETAIL}
ALIAS_PATH = Path("../data/gsmaterial/item-alias.json")
OLD_ALIAS = json.loads(ALIAS_PATH.read_text(encoding="utf-8"))

for avatar_data in AVATAR:
    avatar_id: int = avatar_data["id"]
    hs: int = avatar_data["nameTextMapHash"]
    name_cn: str = TEXTMAP_CHS.get(str(hs), "未知")
    if avatar_id in [10000005, 10000007]:
        OLD_ALIAS["10000007"] = ["旅行者"]
    elif avatar_id > 11000000:
        print(f"角色 ({avatar_id}){name_cn} 在黑名单中被跳过")
    else:
        key = str(avatar_id)
        if not OLD_ALIAS.get(key):
            print(f"{GRE}新增角色 ({avatar_id}){name_cn}{END}")
            OLD_ALIAS[key] = [name_cn] + AVATAR_ALIAS.get(name_cn, [])

for weapon_data in WEAPONS:
    weapon_id: int = weapon_data["id"]
    hs: int = weapon_data["nameTextMapHash"]
    name_cn: str = TEXTMAP_CHS.get(str(hs), "未知")
    if name_cn == "未知":
        print(f"武器 ({weapon_id}) 尚无名称被跳过")
    elif weapon_id in [11419, 11420]:
        print(f"武器 ({weapon_id})「一心传」名刀 被跳过")
    elif name_cn.startswith("(test)"):
        print(f"武器 ({weapon_id}){name_cn} 被跳过")
    else:
        key = str(weapon_id)
        if not OLD_ALIAS.get(key):
            print(f"{GRE}新增武器 ({weapon_id}){name_cn}{END}")
            OLD_ALIAS[key] = [name_cn]

OLD_ALIAS = {k: v for k, v in sorted(OLD_ALIAS.items(), key=lambda i: int(i[0]))}
ALIAS_PATH.write_text(
    json.dumps(OLD_ALIAS, ensure_ascii=False, indent=2), encoding="utf-8"
)
