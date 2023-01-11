from asyncio import sleep as async_sleep
from random import randint
from typing import Dict

from nonebot import get_bot, get_driver, require
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, MessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.plugin import on_command
from nonebot.typing import T_State

from .config import SCHED_HOUR, SCHED_MINUTE, WEEKLY_BOSS
from .data_source import (
    generate_calc_msg,
    generate_daily_msg,
    generate_weekly_msg,
    sub_helper,
    update_config,
)

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402

mt_daily_matcher = on_command("材料", priority=13)
mt_weekly_matcher = on_command("周本", priority=13)
mt_calc_matcher = on_command("原神计算", priority=13)
driver = get_driver()
driver.on_bot_connect(update_config)


@mt_daily_matcher.handle()
async def daily_material(bot: Bot, event: MessageEvent, state: T_State):
    # 获取不包含触发关键词的消息文本
    arg = str(state["_prefix"]["command_arg"])
    qq = str(event.get_user_id())

    # 单独响应订阅指令
    if arg.startswith("订阅"):
        is_delete = "删除" in arg
        is_group = isinstance(event, GroupMessageEvent)
        action = f"{'d' if is_delete else 'a'}{'g' if is_group else 'p'}"
        action_id = event.group_id if is_group else qq
        if (
            is_group
            and qq not in bot.config.superusers
            and event.sender.role not in ["admin", "owner"]
        ):
            await mt_daily_matcher.finish(
                f"你没有权限{'删除' if is_delete else '启用'}此群原神每日材料订阅！"
            )
        await mt_daily_matcher.finish(await sub_helper(action, action_id))  # type: ignore

    # 识别周几，也可以是纯数字
    weekday, timedelta = 0, 0
    week_keys = ["一", "四", "1", "4", "二", "五", "2", "5", "三", "六", "3", "6"]
    for idx, s in enumerate(week_keys):
        if s in arg:
            weekday = idx // 4 + 1
            arg = arg.replace(f"周{s}", "").replace(s, "").strip()
            break
    for idx, s in enumerate(["今", "明", "后"]):
        if s in arg:
            timedelta = idx
            arg = arg.replace(f"{s}天", "").replace(f"{s}日", "").strip()

    # 处理正常指令
    if any(x in arg for x in ["天赋", "角色"]):
        target = "avatar"
    elif any(x in arg for x in ["武器"]):
        target = "weapon"
    elif not arg:
        # 只发送了命令触发词，返回每日总图
        target = "all"
    else:
        # 发送了无法被识别为类型的内容，忽略
        await mt_daily_matcher.finish()

    # 获取每日材料图片
    msg = await generate_daily_msg(target, weekday, timedelta)
    await mt_daily_matcher.finish(
        MessageSegment.text(msg) if isinstance(msg, str) else MessageSegment.image(msg)
    )


@mt_weekly_matcher.handle()
async def weekly_material(bot: Bot, event: MessageEvent, state: T_State):
    # 获取不包含触发关键词的消息文本
    arg, target = str(state["_prefix"]["command_arg"]), ""
    # 处理输入
    for boss_alias in WEEKLY_BOSS:
        if arg in boss_alias:
            target = boss_alias[0]
            break
    if not arg:
        # 只发送了命令触发词，返回周本总图
        target = "all"
    elif not target:
        # 发送了无法被识别为周本名的内容，忽略
        await mt_weekly_matcher.finish()
    # 获取周本材料图片
    msg = await generate_weekly_msg(target)
    await mt_weekly_matcher.finish(
        MessageSegment.text(msg) if isinstance(msg, str) else MessageSegment.image(msg)
    )


@mt_calc_matcher.handle()
async def calc_material(bot: Bot, event: MessageEvent, state: T_State):
    arg = str(state["_prefix"]["command_arg"])
    msg = await generate_calc_msg(arg)
    await mt_weekly_matcher.finish(
        MessageSegment.text(msg) if isinstance(msg, str) else MessageSegment.image(msg)
    )


@scheduler.scheduled_job("cron", hour=int(SCHED_HOUR), minute=int(SCHED_MINUTE))
async def daily_push():
    bot = get_bot()
    # 获取订阅配置
    cfg = await sub_helper()
    assert isinstance(cfg, Dict)
    # 更新每日材料图片
    msg = await generate_daily_msg("update")
    message = (
        MessageSegment.text(msg) if isinstance(msg, str) else MessageSegment.image(msg)
    )
    # 推送
    for group in cfg.get("群组", []):
        await bot.send_group_msg(group_id=group, message=message)
        await async_sleep(randint(5, 10))
    for private in cfg.get("私聊", []):
        await bot.send_private_msg(user_id=private, message=message)
        await async_sleep(randint(5, 10))
