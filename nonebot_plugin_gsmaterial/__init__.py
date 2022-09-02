from nonebot import get_bot, get_driver
from nonebot.log import logger
from nonebot.plugin import on_command
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

try:
    from nonebot.adapters.onebot.v11 import Bot
    from nonebot.adapters.onebot.v11.event import MessageEvent
    from nonebot.adapters.onebot.v11.message import MessageSegment
except ImportError:
    from nonebot.adapters.cqhttp import Bot, MessageSegment  # type: ignore
    from nonebot.adapters.cqhttp.event import MessageEvent  # type: ignore

from .data_source import genrMsg, updateConfig

driver = get_driver()
materialMatcher = on_command("今天打什么", aliases={"今日"}, priority=13)


@driver.on_startup
async def materialStartup() -> None:
    logger.info("Genshin Material 正在执行数据更新...")
    await updateConfig()
    logger.info("Genshin Material 数据初始化 / 更新完成！")


@materialMatcher.handle()
async def material(bot: Bot, event: MessageEvent, state: T_State):
    argsMsg = (  # 获取不包含触发关键词的消息文本
        str(state["_prefix"]["command_arg"])
        if "command_arg" in list(state.get("_prefix", {}))
        else str(event.get_plaintext())
    )
    if any(x in argsMsg for x in ["天赋", "角色"]):
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


@scheduler.scheduled_job("cron", hour=8, minute=10, second=0)
async def dailyMaterialPush():
    bot = get_bot()
    msg = await genrMsg("update")
    # await bot.send_group_msg(
    #     group_id=12345,
    #     message=(
    #         MessageSegment.image(msg) if "base64" in msg else MessageSegment.text(msg)
    #     ),
    # )
