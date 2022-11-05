import asyncio
import json
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from time import time
from traceback import format_exc
from typing import Dict, List, Literal, Union

from httpx import AsyncClient, HTTPError
from nonebot.log import logger
from PIL import Image

from .config import LOCAL_DIR
from .material_draw import drawItems, drawWeeks, toBase64

AMBR = {
    "每日采集": "https://api.ambr.top/v2/chs/dailyDungeon",
    "角色列表": "https://api.ambr.top/v2/chs/avatar",
    "武器列表": "https://api.ambr.top/v2/chs/weapon",
    "材料列表": "https://api.ambr.top/v2/chs/material",
    "角色详情": "https://api.ambr.top/v2/chs/avatar/{id}",
    "武器详情": "https://api.ambr.top/v2/chs/weapon/{id}",
    "材料详情": "https://api.ambr.top/v2/chs/material/{id}",
    "升级材料": "https://api.ambr.top/v2/static/upgrade",
    "通告": "https://api.ambr.top/assets/data/event.json",
}


async def download(url: str, local: Union[Path, str] = "") -> Union[Path, None]:
    """
    图片下载，使用 Pillow 保存图片
    * ``param url: str`` 指定下载链接
    * ``param local: Union[Path, str] = ""`` 指定本地目标路径，传入类型为 ``Path`` 时视为保存文件完整路径，传入类型为 ``str`` 时视为保存文件子文件夹名（默认下载至插件资源根目录）
    - ``return: Union[Path, None]`` 本地文件地址，出错时返回空
    """
    # 路径处理
    if not isinstance(local, Path):
        d = (LOCAL_DIR / local) if local else LOCAL_DIR
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
        f = d / url.split("/")[-1]
    else:
        if not local.parent.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
        f = local
    # 本地文件存在时便不再下载
    if f.exists():
        # 测试角色图像为白色问号，该图片 st_size = 5105，小于 6KB 均视为无效图片
        if not (f.name.lower().endswith("png") and f.stat().st_size < 6144):
            return f
    # 远程文件下载
    client = AsyncClient()
    retryCnt = 3
    while retryCnt:
        try:
            if "ambr.top" not in url:
                # 初始化时从阿里云 OSS 下载资源
                async with client.stream("GET", url) as res:
                    with open(f, "wb") as fb:
                        async for chunk in res.aiter_bytes():
                            fb.write(chunk)
            else:
                logger.info(f"安柏计划 {f.name} 正在下载\n>>>>> {url}")
                async with AsyncClient() as client:
                    res = await client.get(
                        url,
                        headers={
                            "referer": "https://ambr.top/",
                            "user-agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
                                "like Gecko) Chrome/104.0.5112.81 Safari/537.36 Edg/104.0.1293.47"
                            ),
                        },
                        timeout=20.0,
                    )
                    userImage = Image.open(BytesIO(res.content))
                    userImage.save(f, quality=100)
            return f
        except Exception as e:
            logger.error(f"安柏计划 {f.name} 资源下载出错 {e.__class__.__name__}\n{format_exc()}")
            retryCnt -= 1
            if retryCnt:
                await asyncio.sleep(2)
    return None


async def subHelper(
    mode: Literal["r", "ag", "ap", "dg", "dp"] = "r", id: Union[str, int] = ""
) -> Union[Dict, str]:
    """订阅配置助手，支持读取 ``r(ead)`` 配置、添加 ``a(dd)`` 群 ``g(roup)`` 订阅、添加私聊 ``p(rivate)`` 订阅、删除 ``d(elete)`` 群订阅、删除私聊订阅"""
    subFile = LOCAL_DIR / "sub.json"
    subCfg: Dict[str, List] = json.loads(subFile.read_text(encoding="UTF-8"))
    if mode == "r":
        return subCfg
    writeKey = {"g": "群组", "p": "私聊"}[mode[1]]
    if mode[0] == "a":
        if int(id) in list(subCfg[writeKey]):
            return f"已经添加过当前{writeKey}的原神每日材料订阅辣！"
        subCfg[writeKey].append(int(id))
        subFile.write_text(
            json.dumps(subCfg, ensure_ascii=False, indent=2), encoding="UTF-8"
        )
    else:
        if int(id) not in list(subCfg[writeKey]):
            return f"还没有添加过当前{writeKey}的原神每日材料订阅哦.."
        subCfg[writeKey].remove(int(id))
        subFile.write_text(
            json.dumps(subCfg, ensure_ascii=False, indent=2), encoding="UTF-8"
        )
    return f"已{'启用' if mode[0] == 'a' else '禁用'}当前{writeKey}的原神每日材料订阅。"


async def queryAmbr(
    type: Literal["每日采集", "升级材料", "角色列表", "武器列表", "材料列表"], retry: int = 3
) -> Dict:
    """请求安柏计划数据接口"""
    async with AsyncClient() as client:
        while retry:
            try:
                res = (await client.get(AMBR[type])).json()
                return res["data"]
            except (HTTPError or json.decoder.JSONDecodeError or KeyError):
                logger.info(f"安柏计划 {type} 接口请求出错，正在重试...")
                retry -= 1
                if retry:
                    await asyncio.sleep(2)
    return {}


async def updateConfig() -> None:
    """从安柏计划更新每日材料配置，顺便在启动时下载必需资源、生成周本图片"""
    # 启动资源下载
    oss = [
        "https://cdn.monsterx.cn/bot/gsmaterial/HYWH-65W.ttf",
        "https://cdn.monsterx.cn/bot/gsmaterial/weapon.png",
        "https://cdn.monsterx.cn/bot/gsmaterial/avatar.png",
        "https://cdn.monsterx.cn/bot/gsmaterial/bg5.140.png",
        "https://cdn.monsterx.cn/bot/gsmaterial/bg4.140.png",
        "https://cdn.monsterx.cn/bot/gsmaterial/bg3.140.png",
    ]
    initTask = [download(url, "draw") for url in oss]
    await asyncio.gather(*initTask)
    initTask.clear()

    # 获取安柏计划数据
    logger.debug("安柏计划数据接口请求...")
    domainRes = await queryAmbr("每日采集")
    updateRes = await queryAmbr("升级材料")
    avatarRes = await queryAmbr("角色列表")
    weaponRes = await queryAmbr("武器列表")
    materialRes = await queryAmbr("材料列表")
    if any(not x for x in [domainRes, avatarRes, weaponRes, updateRes]):
        logger.info("安柏计划数据更新数据不全！更新任务被跳过")
        return

    res = {"avatar": {}, "weapon": {}, "weekly": {}, "time": 0}

    # 生成最新每日材料配置
    logger.debug("每日材料配置生成及图片下载...")
    for dayKey in domainRes:
        if dayKey not in ["monday", "tuesday", "wednesday"]:
            # 跳过材料重复的日期
            continue
        dayNum = {"monday": "1", "tuesday": "2", "wednesday": "3"}[dayKey]
        dm = domainRes[dayKey]
        res["avatar"][dayNum], res["weapon"][dayNum] = {}, {}
        # 按区域重新排序秘境
        dmOrder = sorted(dm, key=lambda x: dm[x]["city"])
        # 遍历秘境填充对应的角色/武器数据
        for dmKey in dmOrder:
            if "精通秘境" in dm[dmKey]["name"]:
                itemType, trans = "avatar", avatarRes["items"]
            else:  # "炼武秘境" in dm[dmKey]["name"]
                itemType, trans = "weapon", weaponRes["items"]
            materialId = str(dm[dmKey]["reward"][-1])
            material = materialRes["items"][materialId]["name"]
            whoUse = [
                id
                for id in updateRes[itemType]
                if materialId in updateRes[itemType][id]["items"]
                and str(id).isdigit()  # 排除旅行者
            ]
            # 以 "5琴,5优菈,...,[rank][name]" 形式写入配置
            res[itemType][dayNum][material] = ",".join(
                str(trans[id]["rank"]) + trans[id]["name"] for id in whoUse
            )
            # 下载图片
            tmpTasks = [
                download(
                    f"https://api.ambr.top/assets/UI/UI_ItemIcon_{materialId}.png",
                    LOCAL_DIR / "item" / f"{material}.png",
                )
            ]
            tmpTasks.extend(
                [
                    download(
                        f"https://api.ambr.top/assets/UI/{trans[id]['icon']}.png",
                        LOCAL_DIR / itemType / f"{trans[id]['name']}.png",
                    )
                    for id in whoUse
                ]
            )
            await asyncio.gather(*tmpTasks)
            tmpTasks.clear()

    # 生成最新周本材料配置
    logger.debug("周本材料配置生成及图片下载...")
    weeklyBoss = [  # 暂时拿第一个作为标识
        ["风魔龙·特瓦林", "往日的天空之王", "深入风龙废墟", "追忆：暴风般狂啸之龙"],
        ["安德留斯", "奔狼的领主", "北风的王狼，奔狼的领主"],
        ["「公子」", "愚人众执行官末席", "进入「黄金屋」", "追忆：黄金与孤影"],
        ["若陀龙王", "被封印的岩龙之王", "「伏龙树」之底", "追忆：摇撼山岳之龙"],
        ["「女士」", "愚人众执行官第八席", "鸣神岛·天守", "追忆：红莲的真剑试合"],
        ["祸津御建鸣神命", "雷电之稻妻殿", "梦想乐土之殁", "追忆：永恒的守护者"],
        ["「正机之神」", "七叶寂照秘密主", "净琉璃工坊", "追忆：七叶中尊琉璃坛"],
    ]
    weeklyMaterial, weeklyTasks = [], []
    for mtId, mtInfo in materialRes["items"].items():
        # 筛选周本材料
        if mtInfo["rank"] != 5 or mtInfo["type"] != "characterLevelUpMaterial":
            continue
        # 去除 5 星角色突破材料
        if int(mtId) in [
            104104,  # 璀璨原钻
            104114,  # 燃愿玛瑙
            104124,  # 涤净青金
            104134,  # 生长碧翡
            104144,  # 最胜紫晶
            104154,  # 自在松石
            104164,  # 哀叙冰玉
            104174,  # 坚牢黄玉
        ]:
            continue
        weeklyMaterial.append(
            mtInfo["name"] if mtInfo["name"] != "？？？" else str(mtInfo["id"])
        )
        if mtInfo["icon"]:
            weeklyTasks.append(
                download(
                    f"https://api.ambr.top/assets/UI/{mtInfo['icon']}.png",
                    LOCAL_DIR / "item" / f"{mtInfo['name']}.png",
                )
            )
    await asyncio.gather(*weeklyTasks)
    weeklyTasks.clear()
    # 先填充已定义的周本下各个材料名称
    res["weekly"] = {
        bossKey[0]: {
            materialKey: "" for materialKey in weeklyMaterial[bIdx * 3 : (bIdx + 1) * 3]
        }
        for bIdx, bossKey in enumerate(weeklyBoss)
    }
    # 在补充未实装内容到名为 "？？？" 的周本下
    if len(weeklyMaterial) > len(weeklyBoss * 3):
        res["weekly"]["？？？"] = {
            betaKey: "" for betaKey in weeklyMaterial[len(weeklyBoss * 3) :]
        }
    for avatar in updateRes["avatar"]:
        # 排除旅行者
        if not str(avatar).isdigit():
            continue
        # 将角色升级材料按消耗数量重新排序，周本材料 ID 将排在最后一位
        mtKey = list(
            {
                k: v
                for k, v in sorted(
                    updateRes["avatar"][avatar]["items"].items(), key=lambda i: i[1]
                )
            }
        )[-1]
        mtName = materialRes["items"][mtKey]["name"]
        weeklyBossIdx = weeklyMaterial.index(mtName) // 3
        bossKey = (
            weeklyBoss[weeklyBossIdx]
            if weeklyBossIdx < len(weeklyBoss)
            else ["？？？", "尚未实装周本"]
        )
        # 以 "5琴,5迪卢克,...,[rank][name]" 形式写入配置
        res["weekly"][bossKey[0]][mtName if mtName != "？？？" else mtKey] += (
            (
                ","
                if res["weekly"][bossKey[0]][mtName if mtName != "？？？" else mtKey]
                else ""
            )
            + f"{avatarRes['items'][avatar]['rank']}{avatarRes['items'][avatar]['name']}"
        )

    # 生成每日图片缓存，仅每日配置更新时重绘
    needUpdate = True
    if (LOCAL_DIR / "config.json").exists():
        oldData = dict(
            json.loads((LOCAL_DIR / "config.json").read_text(encoding="UTF-8"))
        )
        needUpdate = any(oldData.get(key) != res[key] for key in ["avatar", "weapon"])
    if needUpdate:
        logger.debug("每日材料图片缓存生成...")
        dailyTasks = [drawItems(res, day, ["avatar", "weapon"]) for day in [1, 2, 3]]
        await asyncio.gather(*dailyTasks)
        dailyTasks.clear()

    # 生成周本图片缓存，仅周本配置更新时重绘
    oldWeekData = (
        dict(json.loads((LOCAL_DIR / "config.json").read_text(encoding="UTF-8"))).get(
            "weekly"
        )
        if (LOCAL_DIR / "config.json").exists()
        else {}
    )
    if oldWeekData != res["weekly"]:
        logger.debug("周本材料图片缓存生成...")
        await drawWeeks(res)

    # 补充时间戳
    res["time"] = int(time())
    logger.debug("原神材料配置写入...")
    (LOCAL_DIR / "config.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="UTF-8"
    )


async def genrMsg(needType: Literal["avatar", "weapon", "all", "update"]) -> str:
    """原神每日材料图片生成入口"""
    # 时间判断
    weekday = (
        (datetime.today() - timedelta(days=1)).weekday()
        if datetime.today().hour < 4
        else datetime.today().weekday()
    )
    if weekday == 6:
        return "今天所有天赋培养、武器突破材料都可以获取哦~"
    day = (weekday + 1) if (weekday < 3) else (weekday - 2)
    # 存在图片缓存且非更新任务时使用缓存
    cachePic = LOCAL_DIR / f"day{day}.{needType}.png"
    if needType != "update" and cachePic.exists():
        logger.info(f"使用缓存的原神材料图片 {cachePic.name}")
        return await toBase64(Image.open(cachePic))
    # 根据每日材料配置重新生成图片
    config = json.loads((LOCAL_DIR / "config.json").read_text(encoding="UTF-8"))
    needList = [needType] if needType in ["avatar", "weapon"] else ["avatar", "weapon"]
    # 按需绘制素材图片
    try:
        img = await drawItems(config, day, needList)
        return await toBase64(img)
    except Exception as e:
        logger.error(f"原神材料图片生成出错 {e.__class__.__name__}\n{format_exc()}")
        return f"[{e.__class__.__name__}]原神材料图片生成失败"


async def genrWeek(
    needType: Literal[
        "all", "风魔龙·特瓦林", "安德留斯", "「公子」", "若陀龙王", "「女士」", "祸津御建鸣神命", "「正机之神」"
    ]
) -> str:
    """原神周本材料图片生成入口"""
    # 存在图片缓存且非更新任务时使用缓存
    cachePic = LOCAL_DIR / f"week.{needType}.png"
    if cachePic.exists():
        logger.info(f"使用缓存的原神材料图片 {cachePic.name}")
        return await toBase64(Image.open(cachePic))
    else:
        return "原神周本材料图片尚未生成！"
    # # 根据周本材料配置重新生成图片
    # config = json.loads((LOCAL_DIR / "config.json").read_text(encoding="UTF-8"))
    # needList = (
    #     ["风魔龙·特瓦林", "安德留斯", "「公子」", "若陀龙王", "「女士」", "祸津御建鸣神命"]
    #     if needType == "all"
    #     else [needType]
    # )
    # # 按需绘制素材图片
    # try:
    #     img = await drawWeeks(config, needList)
    #     return await toBase64(img)
    # except Exception as e:
    #     logger.error(f"原神材料图片生成出错 {e.__class__.__name__}\n{format_exc()}")
    #     return f"[{e.__class__.__name__}]原神材料图片生成失败"
