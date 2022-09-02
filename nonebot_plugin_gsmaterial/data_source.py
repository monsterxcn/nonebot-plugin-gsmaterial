import asyncio
import json
from base64 import b64encode
from datetime import datetime, timedelta
from io import BytesIO
from math import ceil
from pathlib import Path
from time import time
from typing import Dict, List, Literal, Union

from httpx import AsyncClient, HTTPError
from nonebot import get_driver
from nonebot.log import logger
from PIL import Image, ImageDraw, ImageFont

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


def font(size: int):
    """Pillow 绘制字体设置"""
    return ImageFont.truetype(str(LOCAL_DIR / "draw" / "HYWH-65W.ttf"), size=size)


async def circleCorner(markImg: Image.Image, radius: int = 30) -> Image.Image:
    """图片圆角处理"""
    markImg = markImg.convert("RGBA")
    w, h = markImg.size
    circle = Image.new("L", (radius * 2, radius * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)
    alpha = Image.new("L", markImg.size, 255)
    alpha.paste(circle.crop((0, 0, radius, radius)), (0, 0))
    alpha.paste(circle.crop((radius, 0, radius * 2, radius)), (w - radius, 0))
    alpha.paste(
        circle.crop((radius, radius, radius * 2, radius * 2)),
        (w - radius, h - radius),
    )
    alpha.paste(circle.crop((0, radius, radius, radius * 2)), (0, h - radius))
    markImg.putalpha(alpha)
    return markImg


async def toBase64(pic: Image.Image) -> str:
    """``Image`` 图像转 Base64 字符串"""
    buf = BytesIO()
    pic.convert("RGB").save(buf, format="JPEG", quality=80)
    logger.info(f"图片大小 {buf.tell()} 字节")
    base64_str = b64encode(buf.getbuffer()).decode()
    return "base64://" + base64_str


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
            logger.error(f"安伯计划 {f.name} 资源下载出错 {type(e)}：{e}")
            retryCnt -= 1
            if retryCnt:
                await asyncio.sleep(2)
    return None


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
    """从安伯计划更新每日材料配置，顺便在启动时下载必需资源"""
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

    # 获取安伯计划数据
    domainRes = await queryAmbr("每日采集")
    updateRes = await queryAmbr("升级材料")
    avatarRes = await queryAmbr("角色列表")
    weaponRes = await queryAmbr("武器列表")
    materialRes = await queryAmbr("材料列表")
    if any(not x for x in [domainRes, avatarRes, weaponRes, updateRes]):
        logger.info("安柏计划数据更新数据不全！更新任务被跳过")
        return

    # 生成最新每日材料配置
    res = {"avatar": {}, "weapon": {}, "time": 0}
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
            _ = await download(
                f"https://api.ambr.top/assets/UI/UI_ItemIcon_{materialId}.png",
                LOCAL_DIR / "item" / f"{material}.png",
            )
            _ = {
                trans[id]["name"]: str(
                    await download(
                        f"https://api.ambr.top/assets/UI/{trans[id]['icon']}.png",
                        LOCAL_DIR / itemType / f"{trans[id]['name']}.png",
                    )
                )
                for id in whoUse
            }
    # 补充时间戳
    res["time"] = int(time())
    (LOCAL_DIR / "config.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="UTF-8"
    )


async def drawItems(config: Dict, day: int, need: List) -> Image.Image:
    """Pillow 绘制原神每日材料图片"""
    imgs = []
    for itemType in need:
        # 计算待绘制图片的高度，每行绘制 7 个角色或武器
        thisCfg = config[itemType][str(day)]
        if SKIP_THREE:
            thisCfg = {  # 剔除 3 星武器
                key: ",".join(s for s in value.split(",") if s[0] != "3")
                for key, value in dict(thisCfg).items()
            }
        lineCnt = sum(ceil(len(thisCfg[key].split(",")) / 7) for key in thisCfg)
        totalH = 148 + len(thisCfg) * 90 + lineCnt * (130 + 40 + 20) + 60

        # 开始绘制！
        img = Image.new("RGBA", (1048, totalH), "#FBFBFB")

        # 粘贴 Header 图片
        img.paste(Image.open(LOCAL_DIR / "draw" / f"{itemType}.png"), (0, 0))

        # 绘制每个分组
        startH = 148
        for key in thisCfg:
            # 绘制分组所属材料的图片
            try:
                bgImg = Image.open(
                    LOCAL_DIR
                    / "draw"
                    / f"bg{'4' if itemType == 'avatar' else '5'}.140.png"
                )
                keyImg = Image.open(LOCAL_DIR / "item" / f"{key}.png").resize(
                    (140, 140), Image.LANCZOS
                )
                bgImg.paste(keyImg, (0, 0), keyImg)
                groupImg = (await circleCorner(bgImg, radius=30)).resize(
                    (70, 70), Image.LANCZOS
                )
                img.paste(groupImg, (25, startH), groupImg)
            except:  # noqa: E722
                pass
            ImageDraw.Draw(img).text(
                (110, startH + int((70 - font(36).getsize("高")[1]) / 2)),
                key,
                font=font(36),
                fill="#333",
            )

            # 绘制当前分组的所有角色/武器
            startH += 90
            drawX, drawY, cnt = 25, startH, 0
            drawOrder = sorted(
                thisCfg[key].split(","), key=lambda x: x[0], reverse=True
            )
            for item in drawOrder:
                rank, name = item[0], item[1:]  # 5雷电将军,5八重神子,...
                # 角色/武器图片
                try:
                    bgImg = Image.open(LOCAL_DIR / "draw" / f"bg{rank}.140.png")
                    itemImg = Image.open(LOCAL_DIR / itemType / f"{name}.png").resize(
                        (140, 140), Image.LANCZOS
                    )
                    bgImg.paste(itemImg, (0, 0), itemImg)
                    itemImg = (await circleCorner(bgImg, radius=15)).resize(
                        (128, 128), Image.LANCZOS
                    )
                    img.paste(itemImg, (drawX, drawY), itemImg)
                except:  # noqa: E722
                    pass
                # 角色/武器名称，根据名称长度自动调整绘制字号
                s = 30 if len(name) <= 4 else 24
                ImageDraw.Draw(img).text(
                    (
                        int(drawX + (128 - font(s).getsize(name)[0]) / 2),
                        int(drawY + 130 + (40 - font(s).getsize("高")[1]) / 2),
                    ),
                    name,
                    font=font(s),
                    fill="#333",
                )
                # 按照 7 个角色/武器一行绘制
                drawX += 128 + 17
                cnt += 1
                if cnt == 7:
                    drawX, cnt = 25, 0
                    drawY += 130 + 40 + 20

            # 一组角色/武器绘制完毕
            startH += (130 + 40 + 20) * ceil(len(thisCfg[key].split(",")) / 7) + 20

        # 全部绘制完毕，保存图片
        img.save(LOCAL_DIR / f"day{day}.{itemType}.png")
        logger.info(f"素材图片生成完毕 day{day}.{itemType}.png")
        imgs.append(img)

    # 仅有一张图片时直接返回
    if len(imgs) == 1:
        return imgs[0]

    # 存在多张图片时横向合并
    height = max(imgs[0].size[1], imgs[1].size[1])
    merge = Image.new("RGBA", (1048 * 2, height), "#FBFBFB")
    for idx, img in enumerate(imgs):
        merge.paste(img, (1048 * idx, 0))  # int((height - img.size[1]) / 2)
    merge.save(LOCAL_DIR / f"day{day}.all.png")
    logger.info(f"素材图片合并完毕 day{day}.all.png")
    return merge


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
        logger.error(f"原神材料图片生成出错 {type(e)}: {e}")
        return f"[{e.__class__.__name__}]原神材料图片生成失败"
