from copy import deepcopy
from io import BytesIO
from math import ceil
from pathlib import Path
from typing import Dict, List, Union

from PIL import Image, ImageDraw, ImageFont

from nonebot.log import logger
from nonebot.utils import run_sync

from .config import CONFIG_DIR, DL_CFG, SKIP_THREE

RESAMPLING = getattr(Image, "Resampling", Image).LANCZOS


def font(size: int) -> ImageFont.FreeTypeFont:
    """Pillow 绘制字体设置"""

    return ImageFont.truetype(
        str(CONFIG_DIR / "draw" / "SmileySans-Oblique.ttf"), size=size  # HYWH-65W
    )


@run_sync
def circle_corner(mark_img: Image.Image, radius: int = 30) -> Image.Image:
    """图片圆角处理"""

    mark_img = mark_img.convert("RGBA")
    scale, radius = 5, radius * 5
    mark_img = mark_img.resize(
        (mark_img.size[0] * scale, mark_img.size[1] * scale), RESAMPLING
    )
    w, h = mark_img.size
    circle = Image.new("L", (radius * 2, radius * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)
    alpha = Image.new("L", mark_img.size, 255)
    alpha.paste(circle.crop((0, 0, radius, radius)), (0, 0))
    alpha.paste(circle.crop((radius, 0, radius * 2, radius)), (w - radius, 0))
    alpha.paste(
        circle.crop((radius, radius, radius * 2, radius * 2)),
        (w - radius, h - radius),
    )
    alpha.paste(circle.crop((0, radius, radius, radius * 2)), (0, h - radius))
    mark_img.putalpha(alpha)
    return mark_img.resize((int(w / scale), int(h / scale)), RESAMPLING)


async def draw_materials(config: Dict, needs: List[str], day: int = 0) -> Path:
    """原神秘境材料图片绘制"""

    cache_dir = CONFIG_DIR / "cache"
    is_weekly, img_and_path = day == 0, []
    rank_bg = {
        "3": Image.open(CONFIG_DIR / "draw/bg3.140.png"),
        "4": Image.open(CONFIG_DIR / "draw/bg4.140.png"),
        "5": Image.open(CONFIG_DIR / "draw/bg5.140.png"),
    }
    for need in needs:
        raw_config = config["weekly" if is_weekly else need][
            need if is_weekly else str(day)
        ]
        draw_config = {  # 剔除 3 星武器
            key: ",".join(s for s in value.split(",") if not SKIP_THREE or s[0] != "3")
            for key, value in dict(raw_config).items()
            if value
        }

        # 计算待绘制图片的宽度
        title = (
            need
            if is_weekly
            else {1: "周一/周四 {}材料", 2: "周二/周五 {}材料", 3: "周三/周六 {}材料"}[day].format(
                "天赋培养" if need == "avatar" else "武器突破"
            )
        )
        title_bbox = font(50).getbbox(title)
        total_width = max(
            title_bbox[-2] + 50,
            max([(font(40).getlength(_key.split("-")[0]) + 150) for _key in draw_config]),
            max([len(draw_config[_key].split(",")[:6]) for _key in draw_config])
            * (170 + 10)
            + 10,
        )

        # 计算待绘制图片的高度，每行绘制 6 个角色或武器
        line_cnt = sum(
            ceil(len(draw_config[_key].split(",")) / 6) for _key in draw_config
        )
        total_height = 150 + len(draw_config) * 90 + line_cnt * (160 + 40 + 20)

        # 开始绘制！
        img = Image.new("RGBA", (total_width, total_height), "#FBFBFB")
        drawer = ImageDraw.Draw(img)

        # 绘制标题
        drawer.text(
            (int((total_width - title_bbox[-2]) / 2), int((150 - title_bbox[-1]) / 2)),
            title,
            fill="black",
            font=font(50),
            stroke_fill="grey",
            stroke_width=2,
        )

        # 绘制每个分组
        startH = 150
        for key in draw_config:
            # 绘制分组所属材料的图片
            key_name, key_id = key.split("-")
            try:
                _key_icon = deepcopy(rank_bg["4" if need == "avatar" else "5"])
                _key_icon_path = DL_CFG["item"]["dir"] / "{}.{}".format(
                    key_id if DL_CFG["item"]["file"] == "id" else key_name,
                    DL_CFG["item"]["fmt"],
                )
                _key_icon_img = Image.open(_key_icon_path).resize((140, 140), RESAMPLING)
                _key_icon.paste(_key_icon_img, (0, 0), _key_icon_img)
                _key_icon = (await circle_corner(_key_icon, radius=30)).resize(
                    (80, 80), RESAMPLING
                )
                img.paste(_key_icon, (25, startH), _key_icon)
            except:  # noqa: E722
                pass
            # 绘制分组所属材料的名称
            ImageDraw.Draw(img).text(
                (125, startH + int((80 - font(40).getbbox("高")[-1]) / 2)),
                key_name,
                font=font(40),
                fill="#333",
            )

            # 绘制当前分组的所有角色/武器
            startH += 90
            draw_X, draw_Y, cnt = 10, startH, 0
            draw_order = sorted(
                draw_config[key].split(","), key=lambda x: x[0], reverse=True
            )
            for item in draw_order:
                # 5雷电将军10000052,5八重神子10000058,...
                _split = -5 if need == "weapon" else -8
                rank, name, this_id = item[0], item[1:_split], item[_split:]
                # 角色/武器图片
                try:
                    _dl_cfg_key = "avatar" if need not in ["avatar", "weapon"] else need
                    _icon = deepcopy(rank_bg[str(rank)])
                    _icon_path = DL_CFG[_dl_cfg_key]["dir"] / "{}.{}".format(
                        this_id if DL_CFG[_dl_cfg_key]["file"] == "id" else name,
                        DL_CFG[_dl_cfg_key]["fmt"],
                    )
                    _icon_img = Image.open(_icon_path).resize((140, 140), RESAMPLING)
                    _icon.paste(_icon_img, (0, 0), _icon_img)
                    _icon = (await circle_corner(_icon, radius=10)).resize(
                        (150, 150), RESAMPLING  # 140
                    )
                    img.paste(_icon, (draw_X + 10, draw_Y + 10), _icon)
                except:  # noqa: E722
                    pass
                # 角色/武器名称
                name_bbox = font(30).getbbox(name)
                ImageDraw.Draw(img).text(
                    (
                        int(draw_X + (170 - name_bbox[-2]) / 2),
                        int(draw_Y + 160 + (40 - name_bbox[-1]) / 2),
                    ),
                    name,
                    font=font(30),
                    fill="#333",
                )
                # 按照 6 个角色/武器一行绘制
                draw_X += 170 + 10
                cnt += 1
                if cnt == 6:
                    draw_X, cnt = 10, 0
                    draw_Y += 160 + 40 + 20

            # 一组角色/武器绘制完毕
            startH += (160 + 40 + 20) * ceil(len(draw_config[key].split(",")) / 6)

        # 全部绘制完毕，保存图片
        cache_file = cache_dir / (
            f"weekly.{need}.jpg" if is_weekly else f"daily.{day}.{need}.jpg"
        )
        img.convert("RGB").save(cache_file)
        logger.debug(f"{'周本' if is_weekly else '每日'}材料图片生成完毕 {cache_file.name}")
        img_and_path.append([img, cache_file])

    # 仅有一张图片时直接返回
    if len(img_and_path) == 1:
        return img_and_path[0][1]

    # 存在多张图片时横向合并
    width = sum([i[0].size[0] for i in img_and_path]) + (len(img_and_path) - 1) * 25
    _weight, height = 0, max([i[0].size[1] for i in img_and_path])
    merge = Image.new("RGBA", (width, height), "#FBFBFB")
    for i in img_and_path:
        merge.paste(i[0], (_weight, 0), i[0])
        _weight += i[0].size[0] + 25
    merge_file = cache_dir / ("weekly.all.jpg" if is_weekly else f"daily.{day}.all.jpg")
    merge.convert("RGB").save(merge_file)
    logger.info(f"{'周本' if is_weekly else '每日'}材料图片合并完毕 {merge_file.name}")
    return merge_file


async def draw_calculator(name: str, target: Dict, calculate: Dict) -> Union[bytes, str]:
    """原神计算器材料图片绘制"""
    height = sum(80 + ceil(len(v) / 2) * 70 + 20 for _, v in calculate.items() if v) + 20
    img = Image.new("RGBA", (800, height), "#FEFEFE")
    drawer = ImageDraw.Draw(img)

    icon_bg = Image.new("RGBA", (100, 100))
    ImageDraw.Draw(icon_bg).rounded_rectangle(
        (0, 0, 100, 100), radius=10, fill="#a58d83", width=0
    )
    icon_bg = icon_bg.resize((50, 50), RESAMPLING)

    draw_X, draw_Y = 20, 20
    for key, consume in calculate.items():
        if not consume:
            continue

        # 背景纯色
        block_height = 80 + ceil(len(consume) / 2) * 70
        drawer.rectangle(
            ((20, draw_Y), (800 - 20 - 1, draw_Y + block_height)), fill="#f1ede4", width=0
        )

        # 标题
        if key == "avatar_consume":
            title_left, title_right = (
                f"{name}·角色消耗",
                f"Lv.{target['avatar_level_current']} >>> Lv.{target['avatar_level_target']}",
            )
        elif key == "avatar_skill_consume":
            title_left, title_right = f"{name}·天赋消耗", "   ".join(
                f"Lv.{_skill['level_current']}>{_skill['level_target']}"
                for _skill in target["skill_list"]
                if _skill["level_current"] != _skill["level_target"]
            )
        elif key == "weapon_consume":
            title_left, title_right = (
                f"{name}·升级消耗",
                f"Lv.{target['weapon']['level_current']} >>> Lv.{target['weapon']['level_target']}",
            )
        else:
            raise ValueError("材料计算器无法计算圣遗物消耗")
        # 左侧标题
        drawer.text(
            (draw_X + 40, int(draw_Y + (80 - font(40).getbbox("高")[-1]) / 2)),
            title_left,
            fill="#8b7770",
            font=font(40),
        )
        # 右侧标题字体大小自适应
        _size = 40 - len(title_right.split("   ")) * 3
        _text_width, _text_height = font(_size).getbbox(title_right)[-2:]
        drawer.text(
            (800 - 70 - _text_width, int(draw_Y + (80 - _text_height) / 2)),
            title_right,
            fill="#8b7770",
            font=font(_size),
        )

        # 材料
        is_left, _draw_X, _draw_Y = True, draw_X + 30, draw_Y + 80 + 10
        for cost in consume:
            # 图标背景
            img.paste(icon_bg, (_draw_X, _draw_Y), icon_bg)
            # 图标
            _icon_path = DL_CFG["item"]["dir"] / "{}.{}".format(
                cost["id"] if DL_CFG["item"]["file"] == "id" else cost["name"],
                DL_CFG["item"]["fmt"],
            )
            _icon_img = Image.open(_icon_path).resize((50, 50), RESAMPLING)
            img.paste(_icon_img, (_draw_X, _draw_Y), _icon_img)
            # 名称 × 数量
            cost_str = f"{cost['name']} × {cost['num']}"
            drawer.text(
                (_draw_X + 65, _draw_Y + int((50 - font(30).getbbox(cost_str)[-1]) / 2)),
                cost_str,
                fill="#967b68",
                font=font(30),
            )
            if is_left:
                _draw_X += 370
            else:
                _draw_X = draw_X + 30
                _draw_Y += 70
            is_left = not is_left

        draw_Y += block_height + 20

    buf = BytesIO()
    img.save(buf, format="PNG", quality=100)
    return buf.getvalue()
