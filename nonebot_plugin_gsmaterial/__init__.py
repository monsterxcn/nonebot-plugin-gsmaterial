from asyncio import sleep as async_sleep
from random import randint
from typing import Dict

from nonebot import get_bot, get_driver
from nonebot.log import logger
from nonebot.plugin import on_command
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

try:
    from nonebot.adapters.onebot.v11 import Bot
    from nonebot.adapters.onebot.v11.event import GroupMessageEvent, MessageEvent
    from nonebot.adapters.onebot.v11.message import MessageSegment
except ImportError:
    from nonebot.adapters.cqhttp import Bot, MessageSegment  # type: ignore
    from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent  # type: ignore

from .data_source import genrMsg, subHelper, updateConfig

materialMatcher = on_command("原神材料", aliases={"今日"}, priority=13)
driver = get_driver()
SCHEDULER_TIME = (
    str(driver.config.gsmaterial_scheduler)
    if hasattr(driver.config, "gsmaterial_scheduler")
    else "8:10"
)
hour, minute = SCHEDULER_TIME.split(":")


@driver.on_startup
async def materialStartup() -> None:
    logger.info("Genshin Material 正在执行数据更新...")
    await updateConfig()
    logger.info("Genshin Material 数据初始化 / 更新完成！")


@materialMatcher.handle()
async def material(bot: Bot, event: MessageEvent, state: T_State):
    qq = str(event.get_user_id())
    argsMsg = (  # 获取不包含触发关键词的消息文本
        str(state["_prefix"]["command_arg"])
        if "command_arg" in list(state.get("_prefix", {}))
        else str(event.get_plaintext())
    )
    # 处理订阅指令
    if argsMsg == "订阅删除":
        if not isinstance(event, GroupMessageEvent):
            await materialMatcher.finish(str(await subHelper("dp", qq)))
        elif qq not in bot.config.superusers and event.sender.role not in [
            "admin",
            "owner",
        ]:
            await materialMatcher.finish("你没有权限删除此群原神每日材料订阅！")
        await materialMatcher.finish(await subHelper("dg", event.group_id))  # type: ignore
    elif argsMsg == "订阅":
        if not isinstance(event, GroupMessageEvent):
            await materialMatcher.finish(str(await subHelper("ap", qq)))
        elif qq not in bot.config.superusers and event.sender.role not in [
            "admin",
            "owner",
        ]:
            await materialMatcher.finish("你没有权限启用此群原神每日材料订阅！")
        await materialMatcher.finish(await subHelper("ag", event.group_id))  # type: ignore
    # 处理正常指令
    elif any(x in argsMsg for x in ["天赋", "角色"]):
        mtType = "avatar"
    elif any(x in argsMsg for x in ["武器"]):
        mtType = "weapon"
    elif not argsMsg:
        mtType = "all"
    else:
        await materialMatcher.finish()
    # 获取今日素材图片
    msg = await genrMsg(mtType)
    await materialMatcher.finish(
        MessageSegment.image(msg) if "base64" in msg else MessageSegment.text(msg)
    )


@scheduler.scheduled_job("cron", hour=int(hour), minute=int(minute))
async def dailyMaterialPush():
    bot = get_bot()
    msg = await genrMsg("update")
    message = MessageSegment.image(msg) if "base64" in msg else MessageSegment.text(msg)
    cfg = await subHelper()
    assert isinstance(cfg, Dict)
    for group in cfg.get("群组", []):
        await bot.send_group_msg(group_id=group, message=message)
        await async_sleep(randint(5, 10))
    for private in cfg.get("私聊", []):
        await bot.send_private_msg(user_id=private, message=message)
        await async_sleep(randint(5, 10))
