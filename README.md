# Ren'Py 发行版汉化 / 本地化工具链

给 **Ren'Py 官方发行的 PC/zip 版游戏**（无源码）做"中英双语对白"的可复制流程与工具集。
所有产物都是**新增文件**，靠 Ren'Py 的加载优先级生效，因此卸载 = 删文件，原文件零修改、存档兼容不破。

**优先级：时间 > token。** 仓库主人 2026-10-06 写死的口径是"我不缺 token，我缺时间"——
所以默认按**墙钟最短**决策：一次切满、并发拉满（上限 20）、该跑的游戏内实跑截图一次都别省、
风格闸门全表跑。不要拿 token 预算当理由砍质量动作或劝退需求；要用户拍板的只有**范围**
（译不译菜单、动不动对白框几何），不是成本。详见手册 §0.6。

**唯一入口是 [`RENPY_LOCALIZATION_PLAYBOOK.md`](RENPY_LOCALIZATION_PLAYBOOK.md)。**
§0.5 是默认需求口径，§14 是照抄即可的命令序列，§15 是用来估工时和判断异常的实测基线，其余章节是依据和踩过的坑。

## 三种模式

| | 判据 | 抽取 / 复用工具 |
| --- | --- | --- |
| **A 归档型** | `game/` 下只有 `*.rpa` + `tl/None/`，没有散落 `.rpy` | |
| **A-overlay 归档型且装了 mod/更新归档** | 同一个脚本在两个归档里各有一份（`zzscripts.rpa` 这类） | 抽取之后**必须**跑 `tools/precedence_check.py`：它按 §18 的引擎优先级还原"引擎真正加载的那份"，报告表里没有的串（这类发行版会译到读不到的那一份，界面静默留英文） `tools/extract.py`（解 RPA3 索引 + RPC2 容器 + stub unpickler 反序列化 AST），自带官方译文在归档里时按 identifier 连接 |
| **B 散文本型** | `game/*.rpy` 能直接读到明文 | `tools/rpy_extract.py`（只收 `label` 块内的 say 语句） |
| **B-compiled 散文本但带 `.rpyc`** | `game/` 下 `.rpy` 和 `.rpyc` 成对出现 | `tools/rpyc_extract.py`（反序列化引擎真正加载的 AST 取 `Say.what`；正则扫明文会因认不出说话人变量而整批漏句） |
| **B+ 散文本 + 自带明文官方译文** | `game/tl/<lang>/*.rpy` 也是明文 | 上一步之后接 `tools/tl_reuse.py`（按**内容**配对，省掉 99% 翻译量） |

三种模式共用同一份 `localization/en-zh.json` 记录结构，所以生成、校验、回滚三段完全一致。

## 用法

把 `RENPY_LOCALIZATION_PLAYBOOK.md` 和 `tools/` 一起复制到游戏根目录（**先确认游戏目录里没有旧版 `tools/`**：
`cp -r tools .` 在旧目录存在时会变成 `tools/tools/`，你会拿着一套过期工具跑完整项目——本轮就这么踩过，`diff` 两边才看得见）。

引擎实测覆盖：7.4.10 / 8.0.0 / 8.0.3 / 8.1.2 / 8.3.7 / 8.4.2 / 8.5.2 / 8.5.3。然后：

```bash
# 模式 B（散文本）示例。有 .rpyc 就换成 tools/rpyc_extract.py（多一个 --reuse）
python tools/rpy_extract.py --game game --out localization/en-zh.json
python tools/tl_reuse.py --tl game/tl/chinese --apply   # 仅 B+：游戏自带明文官方中文时
# …翻译写进 localization/out_NN.json（{id: 中文}）…
python tools/repair_json.py --in localization/out_11.json --group localization/groups/group_01.json
python tools/apply_trans.py          # 后到的 out_9x_*.json 可覆盖修正（审计发现的问题就地改）
python tools/align_check.py          # 必须 FAILURES: 0；刻意保留的外语/品牌写进 localization/leak_allow.txt
python tools/build_tl.py --lang zh --kinds say --layout zh-first \
    --font-mode tag --font-ref fonts/NotoSansSC-VariableFont_wght.ttf \
    --text-size <比 gui.text_size 小 1~2 档的值> --flag <项目缩写>_bi_off --clean
#   游戏没自带 CJK 字体时把 --font-ref 换成 --cjk-font "C:/Windows/Fonts/NotoSansSC-VF.ttf"（会复制一份进 tl/<lang>/font/）
#   对白框塞不下双语时只降字号（--text-size，最多 1~2 档），不要动窗口几何：
#   --textbox-height / --window-style / --window-ypos 留在工具里，只在用户明确要求改几何时才用（见手册 §5.2）。
#   降完还塞不下就让它溢出——中文行在上面，所以中文一定看得见。
python tools/qa.py                   # 必须 FAILURES: 0
python tools/uninstall.py --dry-run  # 必须恰好列出你新增的每个文件
```

只依赖标准库 + 本机 Python 3，不需要装任何包。

**拷完工具先跑一遍 `--help` 扫描**，把"模块顶层就能炸"的问题在开工前一次暴露：

```bash
for f in tools/*.py; do python "$f" --help >/dev/null 2>&1 || echo "FAIL $f"; done
```

这一轮就是靠它发现 `rpyc_extract.py` 和 `repair_json.py` 在 `import sys` 之前用了
`sys.stdout`（`NameError`，一跑就死）——它们上一次沉淀后从没被执行过。

## 顺手解锁图鉴 / CG / 动画回看

汉化任务常带的附加需求："不玩游戏也要能直接看 Extra 里的 CG 和动画"。
**先 grep 门控表达式，别急着填 `persistent`**——很多发行版留了自己没接上的总开关：

```bash
grep -rho "if .\{0,160\}" game/scripts/gallery/*.rpy | grep -E "persistent|UNLOCKED|BONUS"
grep -rn EXTRAS_GALLERY_UNLOCKED game --include=*.rpy      # 只有 default 一处 = 死开关
```

Carnal Contract 的 163 + 30 处门控全是 `... and BONUS_CODE_SEASSON_1 == 1 or EXTRAS_GALLERY_UNLOCKED == 1:`，
而 Python 的 `A and B or C` == `(A and B) or C`，所以**置 1 即全解锁**：一个新增 `.rpy`、
不写 `persistent.gallery`、不列 196 个 id、不动存档，删文件即还原。验证要断言**整个门控表达式**
（`first=False` 且 `whole=True` 才说明是靠我们的开关打开的）+ 一张真截图，不是只看 flag。

**这是默认动作**（用户 2026-10-06 定的口径，手册 §0.5 第 10 条）：汉化新游戏时顺手把锁起来的
CG / 图鉴 / 图片 / 动画回看一起解。但**不要硬解** —— 要做一个**游戏内可切换按钮**
（绿=全解锁 / 粉=按游戏原进度，状态存 `persistent`），让玩家自己决定。
两个实测坑：按钮标签里的中文必须包 `{font=}`（UI 字体没有 CJK 字形），
以及**验证必须走按钮的真实 action 链**——探针里直接改 `persistent` 字段屏幕不会重跑，
标签停在旧状态，会误判成"按钮没生效"。详见手册 §11.1 / §11.2
（含 `config.load_callbacks`、`ToggleField` 不在 `renpy.exports` 上这些版本坑）。

### 三条解锁路线，按这个顺序试

| 路线 | 做法 | 代价 | 什么时候用 |
| --- | --- | --- | --- |
| **A 翻开发者死开关** | grep 出 `XXX_UNLOCKED` 一类的总开关，新增 `.rpy` 置 1 | 一个文件、零条目 | 永远先试这个 |
| **B 反编译图鉴 screen 就地改门控** | `unrpyc` 把游戏的 gallery screen 反编译成 `.rpy`，手改 `if` 条件，靠 loose `.rpy` 覆盖归档 `.rpyc` | 条目要逐条搬，跟版本死绑 | A 找不到开关、门控写在 screen 内部时 |
| **C 直接填 `persistent.gallery`** | 枚举全部 id 写进存档字段 | 要动存档、换版本 id 就失效 | 前两条都不通才考虑，且别把它打进 mod |

Being-a-DiK 0.8.0 的社区 unlocker 是 B 路线的完整范本（1205 行，尾部标着
`# Decompiled by unrpyc`），值得直接抄的四件事：用 `renpy.loadable("…rpyc")` 探版本再决定加载哪段、
`persistent.x == None → False` 归一化、图鉴 screen 加 `tag menu` + 右键 `Return()`、
长列表用 `vpgrid` + `focus_mask`。它的反面教训是 **115 条手写条目把它钉死在 0.8.0**——
所以本仓库的 B 路线必须落成**生成器**（从游戏自己的脚本里扫条目），不要手抄。

B 路线还有一个只在“冷进场景”才暴露的坑：绕过进度直接跳进未硬化的场景时，游戏自己的
“已收集 X/Y”计数会对 `None` 做算术而崩；而 `Replay` 会 `clean_stores()`，把玩家起的名字退回
`define` 默认值。修法不是猜，是**从游戏自己的硬化场景里学**——扫 `if _in_replay:` 块里的
`var = persistent.x` 收集成播种表。详见手册 §11.3 / §11.4。

## 改文件之前：引擎到底加载哪一份

所有覆盖层做法（汉化叠加、图鉴解锁、路线书签）都假设"我放的 loose 文件会盖掉归档里的同名内容"。
这句假设只在特定条件下成立，而且**判据不是文件时间戳**：

- `.rpy` 与同名 `.rpyc` 并存时，引擎比的是 md5（`.rpy` 源文摘要 vs `.rpyc` 末尾 16 字节）。
  不等就现场编译 `.rpy` **并把这个 `.rpyc` 覆盖重写** —— 所以"复用游戏已有的文件名"不是纯新增，
  备份与还原都必须 `.rpy` + `.rpyc` **成对**处理。能起新名字就起新名字。
- 磁盘先于归档，但去重是按**完整路径名（含扩展名）**：放一个 loose `x.rpy` 挡不住归档里的
  `x.rpyc`，同一个脚本会被注册两次（8.x 下还会在 `script_files.sort()` 抛 `TypeError`）。
- 归档之间是 `sorted()` 再 `.reverse()` ⇒ 字典序最后者优先，所以官方更新包爱叫 `zz*.rpa`。
- 归档里的 `.rpy` 永远不会被当脚本加载，只有 `.rpyc` 有用。

`tools/override_audit.py` 把这四条原样实现了一遍，直接回答"哪一份真正生效 / 哪些条目存在但永远
读不到 / 我这次会不会重写游戏的 `.rpyc`"：

```bash
python tools/override_audit.py --game game
python tools/override_audit.py --game game --overlay /path/to/mod   # 模拟"装完这个 mod 之后"
```

研究社区 mod 时它就兑现了一次价值：作者往 `zzscripts.rpa` 里塞了打过补丁的 `update4`，但磁盘上
那对 `update4.rpy`/`.rpyc` 先占了名 ⇒ **他改的那两行从来没执行过，而且一声不响**。手册 §18。

## 工具清单

| 文件 | 职责 |
| --- | --- |
| `rpautil.py` | RPA3 索引 / RPC2 slot / stub unpickler / AST 遍历，模式 A 的公共底座 |
| `extract.py` | 模式 A 抽取，并按 identifier 连接归档里自带的官方译文 |
| `rpy_extract.py` | 模式 B 抽取（明文 `.rpy`） |
| `rpyc_extract.py` | 模式 B 但游戏带 `.rpyc` 时的抽取器：反序列化引擎真正加载的 AST 取 `Say.what` / `Menu` 标题（`old` 与引擎查表的字节完全一致），`--reuse` 按 identifier 连自带官方译文。`Character` 显示名回落到读 `.rpy`——8.1.2 的 AST 里源码只剩位置 |
| `textbox_fit.py` | 双语行数的量化决策：读 `gui.rpy` 的宽高与字号，从真源 JSON 统计"中文出框率 / 任一行出框率"，给出候选 `--text-size`（§5.2 第 1-2 步的数据来源） |
| `scan_bookmarks.py` | **路线书签的场景枚举器**：从引擎真正加载的 `.rpyc` AST 列出全部 `label`，报出每个场景的节点范围、`_in_replay` 头/尾守卫（`return` 与 `renpy.end_replay()` 两种都认）、作者自己的退出斜坡 `exit_ramps`、尾跳目标、区间外绕行清单、出场说话人，并自带守卫检测覆盖率自检；读了文件却 0 label 会直接报错而不是出一份空报表。用来回答"这个游戏的场景能不能直接进、有多少条值得做书签" |
| `build_bookmarks.py` | 把扫描结果 + 判定结果 + 规则编成游戏内读的 `game/cc_bookmark_data.rpy`；自动推导"每个 menu 该选第几项"（靠成对分支反查，推不出来进 review 不猜） |
| `repair_json.py` | 回收侧机械修复 agent 手写的 JSON（key 丢开引号、值里有未转义引号）；修完必须与 group 的 id 集合完全对齐才写回，否则退回重派 |
| `style_audit.py` | **跨批次风格闸门**（手册 §10.5）：20 个 agent 并行必然在括号全/半角、`...`→`……`、`--` 与 `——`、`{b}Diane's{/b}` 英文所有格残渣、`{b}` 里没译的强调词上分叉，而 `align_check` 只管错位和漏译、抓不到这些。`--apply` 只做机械项（并先备份真源 JSON），判不出来的一律只报告 |
| `override_audit.py` | **加载与覆盖审计**（手册 §18）：按引擎真实规则（磁盘按完整名遮蔽归档、归档 `sorted()+reverse()`、`.rpy`↔`.rpyc` 靠 md5 配对）算出每个逻辑脚本实际加载哪一份，报出“存在但读不到”、磁盘+归档双注册、会被就地重写的 `.rpyc` 三类问题；`--overlay` 模拟安装后的状态 |
| `make_selftest.py` + `selftest_template.rpy` | §9.0 的游戏内自检 harness：探针从真源 JSON 生成，走真实 say 屏幕，自动写 `translate_string` 命中报告 + 12 张截图 |
| `tl_reuse.py` | 模式 B+ 复用官方译文：解析明文 `translate <lang>` 块，按内容配对（含说话人前缀形态、未知转义保留反斜杠、折叠空白二次配对） |
| `denames.py` | 复用官方译文时，把音译人名还原成原文；`--seed` 可喂已知名字表出候选（**只出候选，别直接 `--apply`**，放宽闸门会抓出同句共现词） |
| `dump_groups.py` | 把未译条目按序切成大组，供批量派工 |
| `apply_trans.py` | 合并译文分片，做标签 / 插值 / 换行守恒预检，拒绝项进 `rejected/` |
| `align_check.py` | 对齐与漏译审计（标签守恒抓不到"错位一行"，这里补上）。硬失败只认**游戏自己的角色名**（默认从 `speakers.json` 读，也可 `--names` / `--only-names`），其余大小写猜测降级为告警；网址 / 邮箱不算漏译；刻意保留的外语与术语写进 `localization/leak_allow.txt`，报告里回显命中了哪些 |
| `build_tl.py` | 生成 `tl/<lang>/**.rpy` + 语言 / 字体 / 断行 / 对白框装配文件。`--text-size` 是双语塞不下时的唯一推荐手段（§5.2）；`--font-ref` 引用游戏已自带的字体（零新增文件）；`--window-style` / `--window-ypos` / `--textbox-height` 只在用户明确要求改几何时用，`--window-bg none` 对应 `style window` 本来就 `background None` 的游戏；`--marks` 输出路线徽章层（§16） |
| `qa.py` | BOM、`old` 唯一性、逐字节等于源串、双语对完整性、覆盖率；`--marks --badge-font` 时另查徽章是否被吃掉、徽章字形是否真的存在 |
| `scan_routes.py` | **路线标记**：读脚本算出每个选项实际改哪个数值 / 跳哪个 label，套 `route_rules.json` 判定，输出该标的选项串 + 一份"判不出来、要人确认"的清单。判不出来一律不猜 |
| `font_cmap.py` | 纯标准库读 TTF/OTF 的 `cmap`，回答"这个字形到底有没有"。任何非拉丁字符上屏前先过它（`⚑` `🚩` 在思源黑体里都没有，实测豆腐块） |
| `uninstall.py` | 一键回滚，扫 `tl/<lang>/` 下全部文件（含复制进去的字体） |

## 路线标记（玩的时候不用记攻略）

如果玩家要的某条剧情线（女S男M、某角色路线、某结局）藏在几百个选项里，可以把**决定性选项打上徽章**：
`localization/route_rules.json` 声明规则 → `tools/scan_routes.py` 读脚本判定 →
`tools/build_tl.py --marks` 在覆盖层里输出 `game/tl/zh/90choice_mark.rpy`，
游戏里就显示成 `★她主导 Let her win`、`☆你主导 Hold it` 这样。

- 本质是一次 `strings:` 替换（`new = 徽章 + 原文`），**选项文字不译**、几何不动、纯新增可回滚。
- 最值钱的一条判据是**读游戏自己的状态界面**：本项目 `_(" [mc]'s Submission: [alexLove]")`
  直接告诉了我们哪个数值是"男主服从度"，不用猜变量名。
- 判不出来的（尤其**极性反转**：某角色越跟她争她越占上风）一律进 `route_review.txt` 等人回填，工具不猜。
- 规则文件**实例**含剧透、逐字引用游戏文本 → 属衍生内容，不提交；本仓只放
  [`localization/route_rules.template.json`](localization/route_rules.template.json)。
- 详见手册 §16。

## 路线书签（直接跳进目标场景）

玩家不想玩别的剧情时，可以把某条线的**场景**做成游戏内可点的书签列表：
`tools/scan_bookmarks.py` 枚举场景并判断每个 label 能否安全直进 → 规则文件 + 并发内容判定
选出属于该路线的场景 → `tools/build_bookmarks.py` 生成数据 → `game/cc_bookmarks.rpy`
提供菜单入口、快捷键、**停车闸**和**自动选那条**。

- 点一条即进入真场景（对白 / 选项 / 动画都在原游戏里跑），场景演完自动回列表。
- 走引擎自己的 `Replay(label, scope=…)`：干净 store、逐场景播种、退出时 `sb.restore()`
  全量还原，回放期间 autosave 被抑制 —— **不影响主线进度**，这条不用自己实现。
- 停车闸是必需的：作者通常只给做进画廊的少数场景写了 `if _in_replay: return`，
  其余场景直进会顺着 `jump` 把后面的剧情一路播完。做法见手册 §17.3。
- 判定**必须读内容不能读 label 名**（实测有名字反着骗人的成对分支），
  并显式排除绑架/被捕这类"男性无力但不是 D/s"的剧情。
- 纯新增文件，删掉 `game/cc_bookmarks.rpy` 与 `game/cc_bookmark_data.rpy` 即还原。
- 详见手册 §17。

## 注意

`localization/` 只应包含**你自己的**术语表与翻译中间产物。仓库里只放了
[`localization/glossary.template.md`](localization/glossary.template.md) 模板——
换项目时复制成 `glossary.md` 重写内容。游戏原文、译文 JSON、报告都不要提交。

## 已验证项目

Sunset Rose 0.3（A，无官方译文，3,966 条）、Midnight Paradise 1.1（A，复用官方中文 53,762 / 59,201 条）、
The Tutor 1.0（B，323 条）、By Justice or Mercy v25（B+，18,164 条对白复用 18,544 条唯一串，真缺口 64 条）、Milfylicious 2 0.37（B 带 `.rpyc`，8.1.2，**20,543 条全量自译**）、
Carnal Contract Season One（B 带 `.rpyc`，**8.0.3**，13,090 条全量自译 + 图鉴/动画解锁 + `style_audit` 闸门）。  
引擎 8.5.3 / 8.5.2 / 8.4.2 / 8.3.7 / 8.1.2 / 8.0.3。工时与异常红线见手册 §15。
