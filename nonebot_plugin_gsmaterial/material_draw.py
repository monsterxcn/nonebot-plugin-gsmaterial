from base64 import b64encode
from io import BytesIO
from math import ceil
from typing import Dict, List

from nonebot.log import logger
from PIL import Image, ImageDraw, ImageFont

from .config import LOCAL_DIR, SKIP_THREE


def font(size: int) -> ImageFont.FreeTypeFont:
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
    pic.convert("RGB").save(buf, format="PNG", quality=100)
    logger.debug(f"图片大小 {buf.tell()} 字节")
    base64_str = b64encode(buf.getbuffer()).decode()
    return "base64://" + base64_str


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
            # 排除无内容的材料（thisCfg[key] == ""
            if not thisCfg[key]:
                continue
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
            drawOrder = sorted(thisCfg[key].split(","), key=lambda x: x[0], reverse=True)
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
        logger.debug(f"素材图片生成完毕 day{day}.{itemType}.png")
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
    logger.debug(f"素材图片合并完毕 day{day}.all.png")
    return merge


async def drawWeeks(
    config: Dict,
    need: List = ["风魔龙·特瓦林", "安德留斯", "「公子」", "若陀龙王", "「女士」", "祸津御建鸣神命", "「正机之神」", "？？？"],
) -> Image.Image:
    """Pillow 绘制原神周本材料图片"""
    imgs = []
    for boss in need:
        # 排除无内容的周本
        if not config["weekly"].get(boss):
            continue
        # 计算待绘制图片的高度、宽度，一行绘制全部角色
        thisCfg: Dict = config["weekly"][boss]
        bossSize = font(50).getbbox(boss)
        totalW = 50 + max(
            bossSize[-2],
            max([(font(36).getlength(key) + 135) for key in thisCfg if thisCfg[key]]),
            max([len(thisCfg[key].split(",")) for key in thisCfg if thisCfg[key]])
            * (128 + 17)
            - 17,
        )
        lineCnt = sum(1 for key in thisCfg if thisCfg[key])
        totalH = 148 + len(thisCfg) * 90 + lineCnt * (130 + 40 + 20) + 60

        # 开始绘制！
        img = Image.new("RGBA", (int(totalW), totalH), "#FBFBFB")

        # 绘制 Header 文字
        ImageDraw.Draw(img).text(
            (int((totalW - bossSize[-2]) / 2), int((148 - bossSize[-1]) / 2)),
            boss,
            font=font(50),
            fill="black",
        )

        # 绘制每个分组
        startH = 148
        for key in thisCfg:
            # 排除无内容的周本材料（thisCfg[key] == ""
            if not thisCfg[key]:
                continue
            # 绘制分组所属材料的图片
            try:
                bgImg = Image.open(LOCAL_DIR / "draw" / "bg5.140.png")
                keyImg = Image.open(LOCAL_DIR / "item" / f"{key}.png").resize(
                    (140, 140), Image.LANCZOS
                )
                bgImg.paste(keyImg, (0, 0), keyImg)
                groupImg = (await circleCorner(bgImg, radius=30)).resize(
                    (70, 70), Image.LANCZOS
                )
                img.paste(groupImg, (25, startH), groupImg)
                titleStart = 110
            except:  # noqa: E722
                titleStart = 25
                pass
            ImageDraw.Draw(img).text(
                (titleStart, startH + int((70 - font(36).getsize("高")[1]) / 2)),
                key,
                font=font(36),
                fill="#333",
            )

            # 绘制当前分组的所有角色
            startH += 90
            drawX, drawY = 25, startH
            drawOrder = sorted(thisCfg[key].split(","), key=lambda x: x[0], reverse=True)
            for item in drawOrder:
                rank, name = item[0], item[1:]  # 5琴,5迪卢克,...
                # 角色图片
                try:
                    bgImg = Image.open(LOCAL_DIR / "draw" / f"bg{rank}.140.png")
                    itemImg = Image.open(LOCAL_DIR / "avatar" / f"{name}.png").resize(
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
            drawY += 130 + 40 + 20

            # 一组角色/武器绘制完毕
            startH += (130 + 40 + 20) * 1 + 20

        # 全部绘制完毕，保存图片
        img.save(LOCAL_DIR / f"week.{boss}.png")
        logger.debug(f"周本图片生成完毕 week.{boss}.png")
        imgs.append(img)

    # # 仅有一张图片时直接返回
    # if len(imgs) == 1:
    #     return imgs[0]

    # 存在多张图片时横向合并
    weight = 0
    merge = Image.new(
        "RGBA",
        (
            sum([img.size[0] for img in imgs]) + (len(imgs) - 1) * 25,
            max([img.size[1] for img in imgs]),
        ),
        "#FBFBFB",
    )
    for img in imgs:
        merge.paste(img, (weight, 0))  # int((height - img.size[1]) / 2)
        weight += img.size[0] + 25
    merge.save(LOCAL_DIR / "week.all.png")
    logger.debug("周本图片合并完毕 week.all.png")
    return merge
