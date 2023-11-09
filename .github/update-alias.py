import json
from pathlib import Path


def read(fn: str):
    return json.loads(Path(f"./{fn}").read_text(encoding="UTF-8"))


def pares_yml(file_path):
    with open(Path(f"./{file_path}"), "r", encoding="UTF-8") as file:
        lines = file.readlines()

    result = {}
    key = None
    for line in lines:
        line = line.strip()
        if line.endswith(":"):
            key = line[:-1]
            result[key] = []
        elif key is not None:
            if not any(
                line.endswith(suf)
                for suf in ["专武", "外观", "外观武器", "四星", "4星"]
            ):
                result[key].append(str(line).lstrip("- "))

    return result


GRE, YEL, END = "\033[32m", "\033[33m", "\033[0m"
AVATAR = read("AvatarExcelConfigData.json")
WEAPONS = read("WeaponExcelConfigData.json")
TEXTMAP_CHS = read("TextMapCHS.json")
AVATAR_DETAIL = read("Avatar.json")
AVATAR_DETAIL = {i["Id"]: i for i in AVATAR_DETAIL}
OLD_ALIAS_PATH = Path("../data/gsmaterial/item-alias.json")
OLD_ALIAS = json.loads(OLD_ALIAS_PATH.read_text(encoding="utf-8"))
AVATAR_ALIAS = read("char-alias.json")
WEAPON_ALIAS = pares_yml("wuqi_tujian.yaml")
Path("weapon_alias.json").write_text(
    json.dumps(WEAPON_ALIAS, ensure_ascii=False, indent=2), encoding="utf-8"
)

NEW_ALIAS_PATH = Path("./item-alias.json")
new_alias = {}

for avatar_data in AVATAR:
    avatar_id: int = avatar_data["id"]
    hs: int = avatar_data["nameTextMapHash"]
    name_cn: str = TEXTMAP_CHS.get(str(hs), "未知")
    if avatar_id in [10000005, 10000007]:
        print(f"角色 旅行者 被跳过")
    elif avatar_id > 11000000 or avatar_id == 10000001:
        print(f"角色 ({avatar_id}){name_cn} 被跳过")
    else:
        key = str(avatar_id)
        if not OLD_ALIAS.get(key):
            new_alias[key] = [name_cn] + AVATAR_ALIAS.get(name_cn, [])
            print(f"{GRE}新增角色 ({avatar_id}){name_cn}{END}")
        else:
            new_alias[key] = OLD_ALIAS[key]
            add = [x for x in AVATAR_ALIAS.get(name_cn, []) if x not in OLD_ALIAS[key]]
            remove = [
                x
                for x in OLD_ALIAS[key]
                if x not in AVATAR_ALIAS.get(name_cn, []) and x != name_cn
            ]
            if remove or add:
                print(
                    "{}角色 ({}){} 别名建议：{} {}{}".format(
                        YEL,
                        avatar_id,
                        name_cn,
                        " ".join(f"+{x}" for x in add),
                        " ".join(f"-{x}" for x in remove),
                        END,
                    )
                )

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
            new_alias[key] = [name_cn] + WEAPON_ALIAS.get(name_cn, [])
            print(f"{GRE}新增武器 ({weapon_id}){name_cn}{END}")
        else:
            new_alias[key] = OLD_ALIAS[key]
            add = [x for x in WEAPON_ALIAS.get(name_cn, []) if x not in OLD_ALIAS[key]]
            remove = [
                x
                for x in OLD_ALIAS[key]
                if x not in WEAPON_ALIAS.get(name_cn, []) and x != name_cn
            ]
            if remove or add:
                print(
                    "{}武器 ({}){} 别名建议：{} {}{}".format(
                        YEL,
                        weapon_id,
                        name_cn,
                        " ".join(f"+{x}" for x in add),
                        " ".join(f"-{x}" for x in remove),
                        END,
                    )
                )

new_alias = {k: v for k, v in sorted(new_alias.items(), key=lambda i: int(i[0]))}
NEW_ALIAS_PATH.write_text(
    json.dumps(new_alias, ensure_ascii=False, indent=2), encoding="utf-8"
)
