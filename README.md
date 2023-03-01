<h1 align="center">NoneBot Plugin GsMaterial</h1></br>


<p align="center">🤖 用于展示原神游戏<b>秘境材料</b>和<b>升级消耗</b>数据的 NoneBot2 插件</p></br>


<p align="center">
  <a href="https://raw.githubusercontent.com/monsterxcn/nonebot-plugin-gsmaterial/master/LICENSE"><img src="https://img.shields.io/github/license/monsterxcn/nonebot-plugin-gsmaterial" alt="license" /></a>
  <a href="https://pypi.python.org/pypi/nonebot-plugin-gsmaterial"><img src="https://img.shields.io/pypi/v/nonebot-plugin-gsmaterial" alt="pypi" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.8+-blue" alt="python" /></a>
  <a href="https://jq.qq.com/?_wv=1027&k=GF2vqPgf"><img src="https://img.shields.io/badge/QQ%E7%BE%A4-662597191-orange" alt="QQ Chat Group" /></a><br />
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black" /></a>
  <a href="https://pycqa.github.io/isort"><img src="https://img.shields.io/badge/%20imports-isort-%231674b1?&labelColor=ef8336" alt="Imports: isort" /></a>
  <a href="https://flake8.pycqa.org/"><img src="https://img.shields.io/badge/lint-flake8-&labelColor=4c9c39" alt="Lint: flake8" /></a>
  <a href="https://results.pre-commit.ci/latest/github/monsterxcn/nonebot-plugin-gsmaterial/main"><img src="https://results.pre-commit.ci/badge/github/monsterxcn/nonebot-plugin-gsmaterial/main.svg" alt="pre-commit" /></a>
</p></br>


| ![示例](https://user-images.githubusercontent.com/22407052/222161789-a9b09aaa-0ec3-4b1e-ba2b-3d7107f1f9d4.jpg) |
|:--:|


## 安装方法


如果你正在使用 2.0.0.beta1 以上版本 NoneBot2，推荐使用以下命令安装：


```bash
# 从 nb_cli 安装
python -m nb_cli plugin install nonebot-plugin-gsmaterial

# 或从 PyPI 安装
python -m pip install nonebot-plugin-gsmaterial
```


## 插件配置


### 环境变量


一般来说，插件安装完成后无需设置环境变量，只需重启 Bot 即可开始使用。你也可以在 NoneBot2 当前使用的 `.env` 文件中添加下面的环境变量，对插件进行更多配置。环境变量修改后需要重启 Bot 才能生效。


 - `tz` 时区设置，默认为 `"Asia/Shanghai"`
   
   如果定时任务时区异常，请查看 [@nonebot/plugin-apscheduler](https://github.com/nonebot/plugin-apscheduler) 文档添加该依赖插件的 `apscheduler_config` 环境变量配置
   
 - `gsmaterial_mirror` 角色及武器图标下载镜像，需提供 `UI_AvatarIcon_Layla.png` 等形式的图片，可供选择的镜像有：
   
   + `https://api.ambr.top/assets/UI/` 安柏计划（默认）
   + `https://enka.network/ui/` Enka.Network
   + `http://file.microgg.cn/ui/` 小灰灰
   
 - `gsmaterial_scheduler` 每日材料订阅推送时间，默认为 `"8:10"`
   
 - `gsmaterial_skip_three` 每日材料是否忽略三星物品，默认为 `true`
   
 - `gsmaterial_config` 插件缓存目录，默认为 NoneBot2 根目录下 `data/gsmaterial` 文件夹，**填写时路径中的反斜杠 `\` 务必全部替换为正斜杠 `/`**
   
 - `gsmaterial_avatar` `gsmaterial_weapon` `gsmaterial_item`
   
   分别为角色图标、武器图标、物品图标文件夹或文件路径。**一般情况不需要配置**。这些配置针对的是已经使用 [@KimigaiiWuyi/GenshinUID](https://github.com/KimigaiiWuyi/GenshinUID) 等插件在本地下载了 GsMaterial 所需资源的用户，合理配置这些环境变量可以避免 GsMaterial 重复下载。如果启用了这些配置，请注意检查 NoneBot2 启动时由此插件输出的 `图片缓存规则`，确保插件正确识别！配置具体填写的形式如下：
   + `/path/to/avatars` 指定某个文件夹。如果 GsMaterial 后续需要补充下载文件，文件命名与当前已有文件的格式一致。如果该文件夹内尚无文件，则 GsMaterial 会在此文件夹下载以 `中文名称.png` 形式命名的文件
   + `/path/to/avatars/10000002.png` 指定某个文件。如果 GsMaterial 后续需要补充下载文件，文件命名规则为 `数字 ID.png`。与此同理，如果填入形如 `../神里绫华.jpg`，后续补充下载文件的命名规则就为 `中文名称.jpg`
   
   [@KimigaiiWuyi/GenshinUID](https://github.com/KimigaiiWuyi/GenshinUID) 用户安装 GsMaterial 后推荐配置：
   ```
   gsmaterial_avatar="/path/to/GenshinUID/resource/chars"  # 填 chars 文件夹实际路径，不要照抄
   gsmaterial_weapon="/path/to/GenshinUID/resource/weapon"  # 填 weapon 文件夹实际路径，不要照抄
   ```


### Cookie 配置


如需使用材料计算功能，请在 `gsmaterial_config` 配置的目录下 cookie.json 文件中以字典形式填入米游社 Cookie，文件中至少需要有 `account_id` 和 `cookie_token`。考虑到 `cookie_token` 有效期比较玄学，建议再多配置一个 `stoken` 来自动更新 `cookie_token`。如果获取到的 `stoken` 以 `v2_` 开头，则还需要再配置一个 `mid`。

**注意**，Cookie 配置不需要普通用户单独配置，只需要 Bot 拥有者配置一个公共 Cookie！

最终你可能写入一个像这样的 cookie.json 文件：


<details><summary><i>最普通的一种</i></summary></br>


```json
{
  "account_id": "272894075",
  "cookie_token": "PV6zzXj28UUSUHetJZO2sqEff4sqwdzDAA3Wz3xY",
  "stoken": "5CzsKTYLuoCy4Pf5t7y3bHkS0MjljkOm89rOYfGh"
}
```


</details>


<details><summary><i>使用 stoken v2 的那种</i></summary></br>


```json
{
  "account_id": "272894075",
  "cookie_token_v2": "PV6zzXj28UUSUHetJZO2sqEff4sqwdzDAA3Wz3xY",
  "stoken": "v2_efTJdH0uiaDIcoVSINjZY9lHOtSRS5NcfREpDUpXX-AQlLujTP2HWbi14TXHrH_dA1Dxw9TdTGG0LiRONpW=",
  "mid": "0cckyppmwl_mhy"
}
```


</details>


<details><summary><i>使用 login_ticket 的那种</i></summary></br>


login_ticket 获取方式请参考 https://github.com/monsterxcn/nonebot-plugin-gsmaterial/issues/8#issuecomment-1365705339


```json
{
  "account_id": "272894075",
  "login_ticket": "5CzsKTYLuoCy4Pf5t7y3bHkS0MjljkOm89rOYfGh",
  "mid": "0cckyppmwl_mhy"
}
```


</details>


## 命令说明


插件响应以下形式的消息：


 - 以 `材料` 开头的消息
   
   | 附带参数 | 说明 |
   |:-------|:----|
   | 空 | 返回今日天赋培养与武器突破材料总图 |
   | `天赋` / `角色` | 返回今日天赋培养材料图片 |
   | `武器` | 返回今日武器突破材料图片 |
   | `周一` / `1` / ... | 返回指定日期的天赋培养与武器突破材料总图 |
   | `订阅` | 启用当前消息来源的每日材料订阅，群组内仅 Bot 管理员、群组创建者、群组管理员可操作 |
   | `订阅删除` | 禁用当前消息来源的每日材料订阅，群组内仅 Bot 管理员、群组创建者、群组管理员可操作 |
   
 - 以 `周本` 开头的消息
   
   | 附带参数 | 说明 |
   |:-------|:----|
   | 空 | 返回周本材料总图 |
   | `风龙` / `风魔龙` | 返回 *风魔龙·特瓦林* 掉落材料图片 |
   | `狼` / `北风狼` / `王狼` | 返回 *安德留斯* 掉落材料图片 |
   | `公子` / `达达利亚` / `可达鸭` / `鸭鸭` | 返回 *「公子」* 掉落材料图片 |
   | `若托` / `若陀` / `龙王` | 返回 *若陀龙王* 掉落材料图片 |
   | `女士` / `罗莎琳` / `魔女` | 返回 *「女士」* 掉落材料图片 |
   | `雷神` / `雷电` / `雷军` / `将军` | 返回 *祸津御建鸣神命* 掉落材料图片 |
   | `正机` / `散兵` / `伞兵` / `秘密主` | 返回 *「正机之神」* 掉落材料图片 |
   | `测试` / `未知` / `未实装` / `未上线` | 返回 *尚未实装周本* 掉落材料图片（如果有） |
   
   ![周本总图](https://user-images.githubusercontent.com/22407052/222161368-ac5b7c34-9583-47ec-82ef-6447273770e6.jpg)

 - 以 `原神计算` 开头的消息
   
   第一个附带参数 **必须** 为角色名称或武器名称（支持别名），并且与后面的参数 **用空格隔开**。
   
   计算角色时：
   
   + 角色等级允许的输入包括 `90`、`81-90` 等
   + 天赋等级允许的输入包括 `8`、`1-8`、`888`、`81010`、`8 8 8`、`1-8 1-10 10` 等
   + 只计算等级消耗时，可以使用 `111` 作为天赋等级
   + 只计算天赋消耗时，可以使用 `1` 作为角色等级，或者不输入角色等级并在天赋等级前添加「天赋」二字
   + 同时限定天赋等级和天赋等级时，**必须** 角色等级在前、天赋等级在后，中间用空格或「天赋」二字隔开
   + 未限定等级范围时，默认计算角色等级 1-81、三个天赋等级 1-8 消耗的材料
   
   计算武器时：
   
   + 武器等级允许的输入包括 `90`、`81-90`、`81 90` 等
   + 未限定等级范围时，默认计算武器等级 1-90 消耗的材料
   
   此指令附带参数较为复杂，下面是一些举例：
   
   + `原神计算琴` 计算 *琴* 角色等级 1-90、三个天赋等级 1-8 消耗材料
   + `原神计算琴 81` 计算 *琴* 角色等级 1-**81**、三个天赋等级 1-8 消耗材料
   + `原神计算琴 81 111` 计算 *琴* 角色等级 1-**81** 消耗材料
   + `原神计算琴 81-90 111` 计算 *琴* 角色等级 **81**-**90** 消耗材料
   + `原神计算琴 90 8 8-10 10` 计算 *琴* 角色等级 1-**90**、天赋等级 1-**8** **8**-**10** 1-**10** 消耗材料
   + `原神计算琴 1 10` 计算 *琴* 天赋等级 1-**10** 消耗材料
   + `原神计算琴 天赋101010` 计算 *琴* 三个天赋等级均 1-**10** 消耗材料
   + `原神计算琴 天赋 10 1-8 1-10` 计算 *琴* 天赋等级 1-**10** **1**-**8**、**1**-**10** 消耗材料
   + `原神计算狼末 81` 计算 *狼的末路* 等级 1-**81** 消耗材料
   + `原神计算狼末 81 88` 计算 *狼的末路* 等级 **81**-**88** 消耗材料
   
   
   <details><summary><i>计算角色示例</i></summary></br>
   <img src="https://user-images.githubusercontent.com/22407052/205485052-688953df-1609-467c-b106-dafc32a79bb7.png" height="300px">
   </details>
   
   <details><summary><i>计算武器示例</i></summary></br>
   <img src="https://user-images.githubusercontent.com/22407052/205486180-25706def-8f23-4305-a2b6-5cb1056b5d2e.png" height="300px">
   </details>


## 其他说明


 - 插件秘境材料数据来源为 [Project Amber](https://ambr.top/chs)，所有未实装角色及武器的数据均由该数据库提供。
   
 - 插件升级材料数据来源为 [米游社养成计算器](#)，使用此功能需要有效的 `account_id` 和 `cookie_token`。
   
 - 插件使用的所有角色及武器图标会在 Bot 连接建立后从环境变量 `GSMATERIAL_MIRROR` 下载，所有计算器所需图标会在查询时从米游社下载。这些资源通常只需下载一次，其下载路径及保存文件名均可通过环境变量控制，具体说明请查看 [环境变量](#环境变量) 第 5 条。
   
 - 插件的原神每日材料定时推送基于 [@nonebot/plugin-apscheduler](https://github.com/nonebot/plugin-apscheduler)，如果 NoneBot2 启动时插件的定时任务未正常注册，可能需要额外添加该插件的环境变量 `apscheduler_autostart=true` 来使 `scheduler` 自动启动。


## 特别鸣谢


[@Mrs4s/go-cqhttp](https://github.com/Mrs4s/go-cqhttp) | [@nonebot/nonebot2](https://github.com/nonebot/nonebot2) | [@nonebot/plugin-apscheduler](https://github.com/nonebot/plugin-apscheduler) | [Project Amber](https://ambr.top/chs)
