import asyncio
import json
from datetime import datetime, timedelta
from hashlib import md5
from io import BytesIO
from pathlib import Path
from random import randint
from re import findall
from time import time
from typing import Dict, Literal, Optional, Tuple, Union

from httpx import AsyncClient, HTTPError
from PIL import Image

from nonebot.log import logger

from .config import AMBR, CONFIG_DIR, DL_CFG, DL_MIRROR, ITEM_ALIAS, MYS, TZ, WEEKLY_BOSS
from .material_draw import draw_calculator, draw_materials


async def sub_helper(
    mode: Literal["r", "ag", "ap", "dg", "dp"] = "r", id: Union[str, int] = ""
) -> Union[Dict, str]:
    """订阅配置助手，支持读取 ``r(ead)`` 配置、添加 ``a(dd)`` 群组 ``g(roup)`` 订阅、添加私聊 ``p(rivate)`` 订阅、删除 ``d(elete)`` 群组订阅、删除私聊订阅"""

    cfg_file = CONFIG_DIR / "sub.json"
    sub_cfg = json.loads(cfg_file.read_text(encoding="UTF-8"))

    # 读取订阅配置
    if mode == "r":
        return sub_cfg

    # 添加及删除订阅配置
    write_key = {"g": "群组", "p": "私聊"}[mode[1]]
    if mode[0] == "a":
        # 添加群组订阅或私聊订阅
        if int(id) in list(sub_cfg[write_key]):
            return f"已经添加过当前{write_key}的原神每日材料订阅辣！"
        sub_cfg[write_key].append(int(id))
    else:
        # 删除群组订阅或私聊订阅
        if int(id) not in list(sub_cfg[write_key]):
            return f"还没有添加过当前{write_key}的原神每日材料订阅哦.."
        sub_cfg[write_key].remove(int(id))

    # 更新写入
    cfg_file.write_text(
        json.dumps(sub_cfg, ensure_ascii=False, indent=2), encoding="UTF-8"
    )
    return f"已{'启用' if mode[0] == 'a' else '禁用'}当前{write_key}的原神每日材料订阅。"


async def cookies_helper(cookie: str = "") -> Dict[str, str]:
    """Cookie 配置助手，支持读取、刷新、写入"""

    cookie_file = CONFIG_DIR / "cookie.json"
    cookie_cfg: Dict[str, str] = json.loads(cookie_file.read_text(encoding="UTF-8"))
    standard_keys = [
        "account_id",
        "account_mid",
        "account_mid_v2",
        "cookie_token",
        "cookie_token_v2",
        "login_ticket",
        "login_ticket_v2",
        "login_uid",
        "login_uid_v2",
        "ltmid",
        "ltmid_v2",
        "ltoken",
        "ltoken_v2",
        "ltuid",
        "ltuid_v2",
        "mid",
        "stmid",
        "stmid_v2",
        "stoken",
        "stoken_v2",
        "stuid",
        "stuid_v2",
    ]

    # 读取
    if not cookie:
        if not cookie_cfg:
            return {"error": "养成计算器需要米游社 Cookie！"}
        else:
            # 蒙德飞行冠军安柏应该不会有人没有吧？
            check_res = await query_mys("技能", cookie_cfg, {"avatar_id": 10000021})
            if not check_res.get("error"):
                # 检验成功才返回，否则尝试刷新
                return cookie_cfg
    # 写入
    else:
        cookie_cfg.update(dict(i.strip().split("=", 1) for i in cookie.split(";")))
        check_res = await query_mys("技能", cookie_cfg, {"avatar_id": 10000021})
        # 检验成功保存并返回，否则尝试刷新
        if not check_res.get("error"):
            # 更新米游社用户 ID
            mys_id = (
                cookie_cfg.get("stuid")
                or cookie_cfg.get("ltuid")
                or cookie_cfg.get("login_uid")
                or cookie_cfg.get("account_id")
            )
            if mys_id:
                cookie_cfg.update(
                    {k: mys_id for k in ["stuid", "ltuid", "login_uid", "account_id"]}
                )
            # 精简 Cookie 字段
            simple_cookie_cfg = {
                k: cookie_cfg[k] for k in standard_keys if cookie_cfg.get(k)
            }
            # 写入更新
            cookie_cfg.update(simple_cookie_cfg)
            cookie_file.write_text(
                json.dumps(cookie_cfg, ensure_ascii=False, indent=2), encoding="UTF-8"
            )
            return cookie_cfg

    # 更新米游社用户 ID
    mys_id = (
        cookie_cfg.get("stuid")
        or cookie_cfg.get("ltuid")
        or cookie_cfg.get("login_uid")
        or cookie_cfg.get("account_id")
    )
    if mys_id:
        cookie_cfg.update(
            {k: mys_id for k in ["stuid", "ltuid", "login_uid", "account_id"]}
        )

    # 更新 cookie_token
    if not cookie_cfg.get("stoken") and not cookie_cfg.get("login_ticket"):
        # 同时缺少 login_ticket 和 stoken 直接结束
        return {"error": f"缺少 stoken 无法自动{'补全' if cookie else '更新过期的'}曲奇！"}
    elif not cookie_cfg.get("stoken"):
        # 通过 login_ticket 更新 stoken
        stoken_res = await query_mys(
            "_stoken",
            {},
            data={
                "login_ticket": cookie_cfg["login_ticket"],
                "token_types": "3",
                "uid": cookie_cfg["account_id"],
            },
            spec={"mys_id": cookie_cfg["account_id"], "cookie": ""},
        )
        if stoken_res.get("error"):
            return stoken_res
        try:
            cookie_cfg["stoken"] = stoken_res["list"][0]["token"]
            cookie_cfg["ltoken"] = stoken_res["list"][1]["token"]
        except Exception as e:
            logger.opt(exception=e).error("由 login_ticket 获取 stoken 出错")
            return {"error": "获取 stoken 出错，无法自动更新过期的曲奇！"}

    # 通过 stoken 更新 cookie_token
    user_id_type, user_id = (
        ("mid", cookie_cfg.get("mid"))
        if cookie_cfg["stoken"].startswith("v2_")
        else ("uid", cookie_cfg["account_id"])
    )
    if not user_id:
        # v2 stoken 需要与 mid 同时使用
        return {"error": f"stoken v2 缺少 mid 无法自动{'补全' if cookie else '更新过期的'}曲奇！"}
    cookie_token_res = await query_mys(
        "_cookie",
        {},
        data={"stoken": cookie_cfg["stoken"], user_id_type: user_id},
        spec={"mys_id": cookie_cfg["account_id"], "cookie": ""},
    )
    if cookie_token_res.get("error"):
        return cookie_token_res
    if cookie_token_res.get("cookie_token"):
        cookie_cfg["cookie_token"] = cookie_token_res["cookie_token"]
    else:
        return {
            "error": f"由 {'v2 ' if cookie_cfg['stoken'].startswith('v2_') else ''}stoken 获取 cookie_token 失败！"
        }

    # 精简 Cookie 字段
    simple_cookie_cfg = {k: cookie_cfg[k] for k in standard_keys if cookie_cfg.get(k)}
    # 写入更新
    cookie_cfg.update(simple_cookie_cfg)
    cookie_file.write_text(
        json.dumps(cookie_cfg, ensure_ascii=False, indent=2), encoding="UTF-8"
    )

    return cookie_cfg


async def query_ambr(
    type: Literal["每日采集", "升级材料", "角色列表", "武器列表", "材料列表"], retry: int = 3
) -> Dict:
    """安柏计划数据接口请求"""

    async with AsyncClient() as client:
        while retry:
            try:
                res = await client.get(AMBR[type], timeout=10.0)
                return res.json()["data"]
            except (HTTPError, json.decoder.JSONDecodeError, KeyError) as e:
                retry -= 1
                if retry:
                    await asyncio.sleep(2)
                else:
                    logger.opt(exception=e).error(f"安柏计划 {type} 接口请求出错")
    return {}


async def get_ds_headers(
    mys_id: str, cookie: str, body: str = "", query: str = ""
) -> Dict:
    """含 DS 请求头获取，仅用于补全 Cookie"""

    client = {
        "app_version": "2.36.1",
        "client_type": "5",
        "salt": "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs",
        "referer": "https://webstatic.mihoyo.com/bbs/event/signin-ys/index.html?bbs_auth_required=true&act_id=e202009291139501&utm_source=bbs&utm_medium=mys&utm_campaign=icon",
    }

    device = f"NB-{md5(mys_id.encode()).hexdigest()[:5]}"
    ua = (
        f"Mozilla/5.0 (Linux; Android 12; {device}) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/99.0.4844.73 Mobile Safari/537.36 "
        f"miHoYoBBS/{client['app_version']}"
    )

    s = client["salt"]
    t = str(int(time()))
    r = str(randint(100000, 200000))
    m = md5(f"salt={s}&t={t}&r={r}&b={body}&q={query}".encode()).hexdigest()

    return {
        "x-rpc-app_version": client["app_version"],
        "x-rpc-client_type": client["client_type"],
        "user-agent": ua,
        "referer": client["referer"],
        "ds": f"{t},{r},{m}",
        "cookie": cookie,
    }


async def query_mys(
    type: Literal["技能", "计算", "_stoken", "_cookie"],
    cookie: Dict,
    data: Dict,
    spec: Dict = {},
) -> Dict:
    """米游社计算器接口请求"""

    cookie_join = " ".join(f"{k}={v};" for k, v in cookie.items())
    headers = (
        await get_ds_headers(spec["mys_id"], spec["cookie"])
        if type.startswith("_")
        else {
            "cookie": cookie_join,  # 必需
            "host": "api-takumi.mihoyo.com",
            "origin": "https://webstatic.mihoyo.com",
            "referer": "https://webstatic.mihoyo.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": (
                "Mozilla/5.0 (Linux; Android 12; SM-G977N Build/SP1A.210812.016; wv) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
                "Chrome/107.0.5304.105 Mobile Safari/537.36 miHoYoBBS/2.40.1"
            ),
            "x-requested-with": "com.mihoyo.hyperion",
        }
    )

    async with AsyncClient() as client:
        res_dict = {}
        try:
            if type != "计算" or type.startswith("_"):
                res = await client.get(MYS[type], params=data, headers=headers)
            else:
                headers["content-type"] = "application/json;charset=UTF-8"
                res = await client.post(MYS[type], json=data, headers=headers)
            res_dict = res.json()
            return res_dict["data"] or {
                "error": "[{}] {}".format(
                    res_dict.get("retcode", "null"),
                    res_dict.get("message", f"米游社{type}接口请求出错！"),
                )
            }
        except (HTTPError, json.decoder.JSONDecodeError, KeyError) as e:
            logger.opt(exception=e).error(f"米游社 {type} 接口请求出错\n>>>>> {res_dict}")
            return {
                "error": "[{}] {}".format(
                    res_dict.get("retcode", "null"),
                    res_dict.get("message", f"米游社{type}接口请求出错！"),
                )
            }


async def download(
    url: str, type: str = "draw", rename: str = "", retry: int = 3
) -> Optional[Path]:
    """
    资源下载。图片资源使用 Pillow 保存
    * ``param url: str`` 下载链接
    * ``param type: str = "draw"`` 下载类型，根据类型决定保存的文件夹
    * ``param rename: str = ""`` 下载资源重命名，需要包含文件后缀
    * ``param retry: int = 3`` 下载失败重试次数
    - ``return: Optional[Path]`` 本地文件路径，出错时返回空
    """

    # 下载链接及保存路径处理
    if type == "draw":
        # 插件绘图素材，通过阿里云 CDN 下载
        f = CONFIG_DIR / "draw" / url
        url = f"https://cdn.monsterx.cn/bot/gsmaterial/{url}"
    elif type == "mihoyo":
        # 通过米游社下载的文件，主要为米游社计算器材料图标
        f = DL_CFG["item"]["dir"] / rename
    else:
        # 可通过镜像下载的文件，主要为角色头像、武器图标、天赋及武器突破材料图标
        f = DL_CFG[type]["dir"] / rename
        url = DL_MIRROR + url

    # 跳过下载本地已存在的文件
    if f.exists():
        # 测试角色图像为白色问号，该图片 st_size = 5105，小于 6KB 均视为无效图片
        if not (f.name.lower().endswith("png") and f.stat().st_size < 6144):
            return f

    # 远程文件下载
    async with AsyncClient(verify=False) as client:
        while retry:
            try:
                if type == "draw":
                    # 通过阿里云 CDN 下载，可能有字体文件等
                    async with client.stream("GET", url) as res:
                        with open(f, "wb") as fb:
                            async for chunk in res.aiter_bytes():
                                fb.write(chunk)
                else:
                    logger.info(f"正在下载文件 {f.name}\n>>>>> {url}")
                    headers = (
                        {
                            "host": "uploadstatic.mihoyo.com",
                            "referer": "https://webstatic.mihoyo.com/",
                            "sec-fetch-dest": "image",
                            "sec-fetch-mode": "no-cors",
                            "sec-fetch-site": "same-site",
                            "user-agent": (
                                "Mozilla/5.0 (Linux; Android 12; SM-G977N Build/SP1A.210812.016; wv) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
                                "Chrome/107.0.5304.105 Mobile Safari/537.36 miHoYoBBS/2.40.1"
                            ),
                            "x-requested-with": "com.mihoyo.hyperion",
                        }
                        if type == "mihoyo"
                        else {
                            "referer": "https://ambr.top/",
                            "user-agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
                                "like Gecko) Chrome/104.0.5112.81 Safari/537.36 Edg/104.0.1293.47"
                            ),
                        }
                    )
                    res = await client.get(url, headers=headers, timeout=20.0)
                    userImage = Image.open(BytesIO(res.content))
                    userImage.save(f, quality=100)
                return f
            except Exception as e:
                retry -= 1
                if retry:
                    await asyncio.sleep(2)
                else:
                    logger.opt(exception=e).error(f"文件 {f.name} 下载失败！")


async def update_config() -> None:
    """材料配置更新"""

    # 启动资源下载
    init_tasks = [
        download(file, "draw")
        for file in [
            "SmileySans-Oblique.ttf",
            "bg5.140.png",
            "bg4.140.png",
            "bg3.140.png",
        ]
    ]
    await asyncio.gather(*init_tasks)
    init_tasks.clear()

    logger.info("原神材料配置更新开始...")

    # 获取安柏计划数据
    logger.debug("安柏计划数据接口请求...")
    domain_res = await query_ambr("每日采集")
    update_res = await query_ambr("升级材料")
    avatar_res = await query_ambr("角色列表")
    weapon_res = await query_ambr("武器列表")
    material_res = await query_ambr("材料列表")
    if any(not x for x in [domain_res, avatar_res, weapon_res, update_res, material_res]):
        logger.info("安柏计划数据不全！更新任务被跳过")
        return

    config = {"avatar": {}, "weapon": {}, "weekly": {}, "time": 0}

    # 生成最新每日材料配置
    logger.debug("每日材料配置更新 & 对应图片下载...")
    for weekday, domains in domain_res.items():
        if weekday not in ["monday", "tuesday", "wednesday"]:
            # 跳过材料重复的日期
            continue
        day_num = {"monday": "1", "tuesday": "2", "wednesday": "3"}[weekday]
        config["avatar"][day_num], config["weapon"][day_num] = {}, {}
        # 按区域重新排序秘境
        # 约 3.2 版本起，安柏计划上游蒙德武器秘境返回的城市 ID 异常，手动纠正为 1
        config_order = sorted(
            domains,
            key=lambda x: (
                1
                if domains[x]["name"] in ["炼武秘境：水光之城", "炼武秘境：深没之谷", "炼武秘境：渴水的废都"]
                else domains[x]["city"]
            ),
        )
        # 遍历秘境填充对应的角色/武器数据
        for domain_key in config_order:
            if "精通秘境" in domains[domain_key]["name"]:
                item_type, trans = "avatar", avatar_res["items"]
            else:  # "炼武秘境" in domains[domain_key]["name"]
                item_type, trans = "weapon", weapon_res["items"]
            material_id = str(domains[domain_key]["reward"][-1])
            material_name = material_res["items"][material_id]["name"]
            use_this = [
                id_str
                for id_str in update_res[item_type]
                if material_id in update_res[item_type][id_str]["items"]
                and id_str.isdigit()  # 排除旅行者 "10000005-anemo" 等
            ]
            # 以 "5琴10000003,5优菈10000051,...,[rank][name][id]" 形式写入配置
            config[item_type][day_num][f"{material_name}-{material_id}"] = ",".join(
                f"{trans[i]['rank']}{trans[i]['name']}{i}" for i in use_this
            )
            # 下载图片
            domain_tasks = [
                download(
                    f"UI_ItemIcon_{material_id}.png",
                    "item",
                    "{}.{}".format(
                        material_id if DL_CFG["item"]["file"] == "id" else material_name,
                        DL_CFG["item"]["fmt"],
                    ),
                ),
                *[
                    download(
                        f"{trans[i]['icon']}.png",
                        item_type,
                        "{}.{}".format(
                            i if DL_CFG[item_type]["file"] == "id" else trans[i]["name"],
                            DL_CFG[item_type]["fmt"],
                        ),
                    )
                    for i in use_this
                ],
            ]
            await asyncio.gather(*domain_tasks)
            domain_tasks.clear()

    # 获取最新周本材料
    logger.debug("周本材料配置更新 & 对应图片下载...")
    weekly_material, weekly_tasks = [], []
    for material_id, material in material_res["items"].items():
        # 筛选周本材料
        if (
            material["rank"] != 5
            or material["type"] != "characterLevelUpMaterial"
            or int(material_id)
            in [
                104104,  # 璀璨原钻
                104114,  # 燃愿玛瑙
                104124,  # 涤净青金
                104134,  # 生长碧翡
                104144,  # 最胜紫晶
                104154,  # 自在松石
                104164,  # 哀叙冰玉
                104174,  # 坚牢黄玉
            ]
        ):
            # 包含计算器素材，但不在此处下载，后续计算时从米游社下载
            continue
        weekly_material.append(material_id)
        if material["icon"]:
            weekly_tasks.append(
                download(
                    f"{material['icon']}.png",
                    "item",
                    "{}.{}".format(
                        material_id
                        if DL_CFG["item"]["file"] == "id"
                        else material["name"],
                        DL_CFG["item"]["fmt"],
                    ),
                )
            )

    # 下载最新周本材料图片
    await asyncio.gather(*weekly_tasks)
    weekly_tasks.clear()

    # 固定已知周本的各个材料键名顺序
    config["weekly"] = {
        boss_info[0]: {
            f"{material_res['items'][material_id]['name']}-{material_id}": ""
            for material_id in weekly_material[boss_idx * 3 : boss_idx * 3 + 3]
        }
        for boss_idx, boss_info in enumerate(WEEKLY_BOSS)
    }
    # 未实装周本材料视为 BOSS "？？？" 的产物
    if len(weekly_material) > len(WEEKLY_BOSS * 3):
        config["weekly"]["？？？"] = {
            f"{material_res['items'][material_id]['name']}-{material_id}": ""
            for material_id in weekly_material[len(WEEKLY_BOSS * 3) :]
        }

    # 从升级材料中查找使用某周本材料的角色
    for avatar_id, avatar in update_res["avatar"].items():
        # 排除旅行者
        if not str(avatar_id).isdigit():
            continue
        # 将角色升级材料按消耗数量重新排序，周本材料 ID 将排在最后一位
        material_id = list(
            {k: v for k, v in sorted(avatar["items"].items(), key=lambda i: i[1])}
        )[-1]
        material_name = material_res["items"][material_id]["name"]
        # 确定 config["weekly"] 写入键名，第一层键名为周本 BOSS 名，第二层为 [name]-[id] 材料名
        _boss_idx = weekly_material.index(material_id) // 3
        _boss_name = WEEKLY_BOSS[_boss_idx][0] if _boss_idx < len(WEEKLY_BOSS) else "？？？"
        _material_name = f"{material_res['items'][material_id]['name']}-{material_id}"
        # 以 "5琴10000003,5迪卢克10000016,...,[rank][name][id]" 形式写入配置
        config["weekly"][_boss_name][_material_name] += "{}{}{}{}".format(
            "," if config["weekly"][_boss_name][_material_name] else "",
            avatar_res["items"][avatar_id]["rank"],
            avatar_res["items"][avatar_id]["name"],
            avatar_id,
        )

    # 生成每日图片缓存，仅每日配置更新时重绘
    config_file, redraw_daily, redraw_weekly = CONFIG_DIR / "config.json", True, True
    if config_file.exists():
        old_config: Dict = json.loads(config_file.read_text(encoding="UTF-8"))
        redraw_daily = any(
            old_config.get(key) != config[key] for key in ["avatar", "weapon"]
        )
        redraw_weekly = old_config.get("weekly") != config["weekly"]
    if redraw_daily:
        logger.debug("每日材料图片缓存生成...")
        daily_draw_tasks = [
            draw_materials(config, ["avatar", "weapon"], day) for day in [1, 2, 3]
        ]
        await asyncio.gather(*daily_draw_tasks)
        daily_draw_tasks.clear()
    if redraw_weekly:
        logger.debug("周本材料图片缓存生成...")
        await draw_materials(config, [b[0] for b in WEEKLY_BOSS])

    # 补充时间戳
    config["time"] = int(time())
    config_file.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="UTF-8"
    )
    logger.info("原神材料配置更新完成！")


def get_weekday(delta: int = 0) -> int:
    """周几整数获取，delta 为向后推迟几天"""

    today = datetime.now(TZ)  # 添加时区信息
    _delta = (delta - 1) if today.hour < 4 else delta
    return (today + timedelta(days=_delta)).weekday() + 1


async def generate_daily_msg(
    material: Literal["avatar", "weapon", "all", "update"],
    weekday: int = 0,
    delta: int = 0,
) -> Union[Path, str]:
    """原神每日材料图片生成入口"""

    # 时间判断
    weekday = weekday or get_weekday(delta)
    if weekday == 7:
        return "今天所有天赋培养、武器突破材料都可以获取哦~"
    day = weekday % 3 or 3

    # 存在图片缓存且非更新任务时使用缓存
    cache_pic = CONFIG_DIR / "cache" / f"daily.{day}.{material}.jpg"
    if material != "update" and cache_pic.exists():
        logger.info(f"使用缓存的原神材料图片 {cache_pic.name}")
        return cache_pic

    # 根据每日材料配置重新生成图片
    config = json.loads((CONFIG_DIR / "config.json").read_text(encoding="UTF-8"))
    need_types = [material] if material in ["avatar", "weapon"] else ["avatar", "weapon"]
    # 按需绘制素材图片
    try:
        return await draw_materials(config, need_types, day)
    except Exception as e:
        logger.opt(exception=e).error("原神每日材料图片生成出错")
        return f"[{e.__class__.__name__}] 原神每日材料生成失败"


async def generate_weekly_msg(boss: str) -> Union[Path, str]:
    """原神周本材料图片生成入口"""

    assert boss in ["all", "？？？", *[b[0] for b in WEEKLY_BOSS]]
    # 存在图片缓存且非更新任务时使用缓存
    cache_pic = CONFIG_DIR / f"cache/weekly.{boss}.jpg"
    if cache_pic.exists():
        logger.info(f"使用缓存的原神材料图片 {cache_pic.name}")
        return cache_pic

    # 根据每日材料配置重新生成图片
    config = json.loads((CONFIG_DIR / "config.json").read_text(encoding="UTF-8"))
    need_types = [boss] if boss != "all" else [b[0] for b in WEEKLY_BOSS]
    if not config["weekly"].get("？？？") and boss == "？？？":
        return "当前暂无未上线的周本"
    elif config["weekly"].get("？？？") and boss == "all":
        need_types.append("？？？")
    # 按需绘制素材图片
    try:
        return await draw_materials(config, need_types)
    except Exception as e:
        logger.opt(exception=e).error("原神周本材料图片生成出错")
        return f"[{e.__class__.__name__}] 原神周本材料生成失败"


async def get_target(alias: str) -> Tuple[int, str]:
    """升级目标 ID 及真实名称提取"""

    alias = alias.lower()
    for item_id, item_alias in ITEM_ALIAS.items():
        if alias in item_alias:
            return int(item_id), item_alias[0]
    return 0, alias


async def get_upgrade_target(cookies: Dict[str, str], target_id: int, msg: str) -> Dict:
    """计算器升级范围提取"""
    # cookie = " ".join(f"{k}={v};" for k, v in cookies.items() if k in ["account_id", "cookie_token"])

    lvl_regex = r"([0-9]{1,2})([-\s]([0-9]{1,2}))?"
    t_lvl_regex = r"(10|[1-9])(-(10|[1-9]))?"

    # 武器升级识别
    if target_id < 10000000:
        level_target = findall(lvl_regex, msg)
        if not level_target:
            _lvl_from, _lvl_to = 1, 90
        else:
            _target = level_target[0]
            _lvl_from, _lvl_to = (
                (int(_target[0]), int(_target[-1]))
                if _target[-1]
                else (1, int(_target[0]))
            )
        return (
            {"error": "武器等级超出限制~"}
            if _lvl_to > 90
            else {
                "weapon": {
                    "id": target_id,
                    "level_current": _lvl_from,
                    "level_target": _lvl_to,
                },
                # "reliquary_list": []
            }
        )

    # 角色升级识别
    # 角色等级，支持 90、70-90、70 90 三种格式
    level_input = (
        msg.split("天赋")[0].strip() if "天赋" in msg else msg.split(" ", 1)[0].strip()
    )
    level_targets = findall(lvl_regex, level_input)
    if not level_targets:
        # 消息直接以天赋开头视为不升级角色等级
        _lvl_from, _lvl_to = 90 if msg.startswith("天赋") else 1, 90
    elif len(level_targets) > 1:
        return {"error": f"无法识别的等级「{level_input}」"}
    else:
        _target = level_targets[0]
        _lvl_from, _lvl_to = (
            (int(_target[0]), int(_target[-1])) if _target[-1] else (1, int(_target[0]))
        )
    if _lvl_to > 90:
        return {"error": "伙伴等级超出限制~"}
    msg = msg.lstrip(level_input).strip()
    # 天赋等级，支持 8、888、81010、8 8 8、1-8、1-8 1-10 10 等
    if msg.startswith("天赋"):
        msg = msg.lstrip("天赋").strip()
    skill_targets = findall(t_lvl_regex, msg)
    if not skill_targets:
        _skill_target = [[1, 8]] * 3
    else:
        _skill_target = [
            [int(_matched[0]), int(_matched[-1])]
            if _matched[-1]
            else [1, int(_matched[0])]
            for _matched in skill_targets
        ]
    if len(_skill_target) > 3:
        return {"error": f"怎么会有 {len(_skill_target)} 个技能的角色呢？"}
    if any(_s[1] > 10 for _s in _skill_target):
        return {"error": "天赋等级超出限制~"}

    # 获取角色技能数据
    skill_list = await query_mys("技能", cookies, {"avatar_id": target_id})
    if skill_list.get("error"):
        return skill_list
    skill_ids = [
        skill["group_id"] for skill in skill_list["list"] if skill["max_level"] == 10
    ]

    return {
        "avatar_id": target_id,
        "avatar_level_current": _lvl_from,
        "avatar_level_target": _lvl_to,
        # "element_attr_id": 4,
        "skill_list": [
            {
                "id": skill_ids[idx],
                "level_current": skill_target[0],
                "level_target": skill_target[1],
            }
            for idx, skill_target in enumerate(_skill_target)
            # ...
        ]
        # "weapon": {
        #     "id": 15508,
        #     "level_current": 1,
        #     "level_target": 90
        # },
        # "reliquary_list": []
    }


async def generate_calc_msg(msg: str) -> Union[bytes, str]:
    """原神计算器材料图片生成入口"""

    # 检查 Cookie 中 cookie_token 是否失效并尝试更新
    cookie_dict = await cookies_helper()
    if cookie_dict.get("error"):
        return cookie_dict["error"]

    # 提取待升级物品 ID 及真实名称
    target_input = msg.split(" ", 1)[0]
    target_id, target_name = await get_target(target_input.strip())
    if not target_id:
        return f"无法识别的名称「{target_input}」"
    msg = msg.lstrip(target_input).strip()

    # 提取升级范围
    target = await get_upgrade_target(cookie_dict, target_id, msg)
    if target.get("error"):
        return target["error"]

    # 请求米游社计算器
    logger.info(f"{target_id}: {target}")
    calculate = await query_mys("计算", cookie_dict, target)
    if calculate.get("error"):
        return calculate["error"]

    # 下载计算器素材图片
    for key in calculate.keys():
        consume_tasks = [
            download(
                i["icon_url"],
                "mihoyo",
                f"{i[DL_CFG['item']['file']]}.{DL_CFG['item']['fmt']}",
            )
            for i in calculate[key]
        ]
        logger.info(f"正在下载计算器 {key} 消耗材料的 {len(consume_tasks)} 张图片")
        await asyncio.gather(*consume_tasks)
        consume_tasks.clear()

    # 绘制计算器材料图片
    return await draw_calculator(target_name, target, calculate)
