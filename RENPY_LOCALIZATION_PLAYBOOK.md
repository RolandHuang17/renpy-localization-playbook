# Ren'Py 发行版汉化 / 本地化施工手册

> 面向执行者（人或编码 agent）的可复制流程。适用于 **Ren'Py 官方发行的 PC/zip 版游戏**（含打包脚本、无源码）。
> **默认需求全在 §0.5，优先级口径（时间 > token）在 §0.6**——只丢这份 md 时那 10 条就是需求，不用等补充说明。**要开工请直接看 §14「新项目执行手册」**（A/B 两条分支的命令顺序 + 换项目要改的参数），§15 是可用来估工时和判断异常的真实基线，其余章节是依据和坑。
> 本文件由 Sunset Rose 0.3 汉化任务（2026-10-04，3966 条 / 21.4 万字符）实测沉淀，在 Midnight Paradise 1.1 任务（2026-10-04，**59,201 条对白 / 300 万字符**，其中 53,762 条直接复用官方译文）上复验与修正，又在 The Tutor 1.0 任务（2026-10-05，**323 条对白 / 3.9 万字符，散文本 `.rpy` 无归档**）上补齐了"小项目 + 固定高度对白框"这条分支，再在 By Justice or Mercy v25（2026-10-05，**散文本 + 自带明文官方中文：18,164 条对白，复用 99.65%**）上补齐了模式 B 的译文复用（`tl_reuse.py`）、`--font-ref`、`--text-size`、§5.2 的"对白框几何不许动"这条口径，与 §9.0 的探针方法学；最新的 Milfylicious 2 0.37（2026-10-06，**20,543 条对白 / 162 万字符，散文本但带 `.rpyc`、无官方中文**）补上了 §0 的 AST 抽取分支、§14.1 的分阶段派工，以及 §8 的子 agent 跑偏判据。
> 引擎结论在 Ren'Py **8.5.3 / 8.5.2 / 8.4.2 / 8.3.7 / 8.1.2 / 8.0.3** 上都验证过；标注版本相关的条目换版本需复验。
> 配套工具集（16 个纯标准库 Python 文件 + 1 个自检 harness 模板，可直接复制）见 §12；参考实现留在 Midnight Paradise（归档型）、The Tutor（散文本型）、By Justice or Mercy（散文本 + 自带明文官方译文型）、Milfylicious 2（散文本 + 自带 `.rpyc`、无官方中文、全量自译型）与 Carnal Contract（散文本 + 8.0.3 + 图鉴解锁型）五个项目的 `tools/` 下。
>
> **2026-10-06 Carnal Contract Season One 新增**：13,090 条对白 / 48.6 万字符、引擎 **8.0.3**、无官方中文、游戏只带拉丁字体、散文本带 `.rpyc`。
> 这一轮补了 §6.4（老引擎根本没有 `config.font_name_map`）、§7.1（双语退回开关必须放 `game/`，放 `tl/<lang>/` 会自我注销）、
> §8 的"恰好 3 次工具调用"派工契约 + 20 并发硬上限 + "别信 agent 自报的条数"、§10.5（`tools/style_audit.py`：跨批次风格闸门）、
> §11.1（**图鉴/CG 解锁：优先找开发者自己留的死开关**），以及 §15 的 8.0.3 基线。

---

## 0.5 默认需求（用户口径，丢这份 md 就是全套要求，不要再问）

新项目只丢这个文件、不带任何说明时，以下就是需求本身：

1. **只汉化人物对白**：`say` 正文 + 无说话人的旁白（两者都渲染在对白框里）。
2. **菜单、工具栏、设置页、HUD、按钮、图鉴、标题卡一律不译**，保持英文。不是"暂时不做"，是**明确不要做**。
3. **英文人名不翻译**：不音译（`Ava→艾娃` ❌）、不双语化（`Ava / 艾娃` ❌）。称谓可译并接原名：`Ms. Ava → Ava 老师`；亲属称谓例外（`Mom → 妈妈`）。
4. **最终效果是中英双语**：中文行在上、英文原文在下，两行都显示，不是替换。
5. **翻译要贴合游戏氛围**：先判断题材与语域再下笔。旁白用书面腔，角色之间语域必须拉开（谁痞、谁端着、谁先绷不住），内心独白保持独白的视觉与语气。露骨内容按原文语气直译，不回避不美化——这是用户自有游戏的虚构文本本地化，回避会造成剧情断裂。
6. **一切改动纯新增、可一键撤销**，原文件零修改（见 §11）。
7. 做完先自检再交付（§9 + §12 的 qa/align），**不要**在没跑过游戏的情况下说"做好了"。
10. **汉化新游戏时，顺手把锁起来的 CG / 图鉴 / 图片 / 动画回看一起解锁**（用户 2026-10-06 定为默认，
    不用再问）。但**不要硬解锁**：要做一个**游戏内可切换的按钮**，让玩家自己在
    "按游戏原进度（锁着）"和"全部打开"之间选，状态存 `persistent`。做法见 §11.2。
    成就页的开关是另一回事（只剧透成就名、没有画面），要单独问。
9. **玩家要的是"玩的时候不用记攻略"**：如果用户提过他想走某条剧情线（女S男M、某角色路线、某结局），
   就把那条线的**决定性选项在游戏里直接标出来**（§16），而不是给他一份文字攻略让他对着看。
   标记是覆盖层里的字符串替换，纯新增、可回滚，且**默认只加前缀不改选项文字**（不违反"菜单不译"）。
8. **对白框的几何属于游戏设计，不许为了容纳双语去动它**（不高、不移、不改 `ysize`/`ypos`）。
   塞不下时的唯一手段是**降字号，最多降 1~2 号**（中英共用一个 `say_dialogue` 样式，一个数就同时改两行）；
   降完还塞不下就**让它溢出**——中文行排在上面，所以"中文一定看得见"这个底线天然成立（§5.1）。

## 0.6 优先级：时间 > token（用户 2026-10-06 写死的默认口径）

> 原话："**我不缺 token，我缺时间。**" 以及同日的"我的 token 非常非常多，用快速的方法，不用考虑节省 token"。

**默认按墙钟最短决策。不要为了省 token 做下面这些事：**

- 不要把批次开小、分几轮派 —— **一次切满、并发拉满**（硬上限 20，见 §8.1）。批次尺寸的选择依据是
  "总轮数最少"，不是"固定开销最小"。
- 不要跳过第二轮质检、不要跳过游戏内实跑截图、不要用"简化自检"代替真代码路径（§9）。
  多启动一次 ≈ 30 秒；少返工一次 ≈ 一小时。
- 不要"够用就行"：风格闸门全表跑（§10.5）、agent 自报的缺陷逐条落实、漂移条目手工改写。
- 需要用户拍板的只有**范围**（译不译菜单、动不动对白框几何、要不要剧透成就），
  不是预算。规模再大也先报数、再按 §14 分阶段做，但**不要**把"这要花多少 token"当劝退理由。

**§8.1 的"恰好三次工具调用"照旧严格执行** —— 但理由换了：一个跑偏的 agent
（实测 14 次调用 / 297 万 token）真正贵的是**它霸占一个并发槽 5-10 分钟**，
把本来能并行的那一组推到下一波。省 token 是次要收益，**省墙钟才是目的**。

**不要因为"token 多"就扩范围**：菜单 / UI / 图鉴条目不译、人名不音译、对白框几何不动，
这些是 §0.5 的需求口径，与预算无关。

---

## 0. 先判断适用性

按这个顺序看目录，决定走哪条路：

| 观察 | 结论 |
| --- | --- |
| `game/` 下同时有 `.rpy` **和** `.rpyc`（发行包自带编译产物） | **模式 B 改走 `tools/rpyc_extract.py`，不要正则扫明文**：引擎加载的是时间戳更新的那份（通常是 `.rpyc`），而正则靠 `Character("字面量")` 认说话人，`x = Character(动态名)` / 玩家命名的主角整个认不出来——实测漏 2,541 条（占全部对白 12.6%），漏的正好是台词最多的主角 |
| 有 `game/saves/`、`game/.../` 且能读到 `.rpy` 明文 | **模式 B**：用 `tools/rpy_extract.py`（§14 的 B 分支）。不需要解归档，但**仍然走 `tl/` 覆盖层**，不要直接改源码——改了就没法一键撤销 |
| 模式 B 且 `game/tl/<lang>/*.rpy` 是**明文**（不是归档里的 `.rpyc`） | **模式 B + 自带官方译文**：`rpy_extract.py` 抽源文，再用 `tools/tl_reuse.py` 按内容配对官方译文（§3.6）。这是 By Justice or Mercy v25 的形态，18,608 条里 18,544 条直接复用，缺口只剩 64 条 |
| `game/` 下只有 `*.rpa` + `tl/None/`，无散落 `.rpy` | **本手册的主场景**：脚本被编译进归档，必须走提取 + `tl/` 覆盖层 |
| 归档索引里出现 `tl/<语言名>/**.rpyc` | **先别翻译**：游戏自带官方译文，按 §3.5 复用，通常能省掉 90%+ 的翻译量 |
| 只有 `.rpa` 且是加密/魔改格式 | 先确认 RPA 版本头，见 §2 |

关键原则：**永远不要修改归档或原脚本**。所有本地化都是"新增文件"，靠 Ren'Py 的加载优先级生效，这样卸载 = 删文件，且不会破坏存档兼容。

---

## 1. 侦察清单（动手前必做）

0. **归档里有没有现成译文**：解析索引后按 `tl/<lang>/` 前缀分组计数（Midnight Paradise：1476 个 `.rpyc` 里 1305 个是 `tl/`，8 种语言，中文 162 个文件 / 5.99MB）。有 → 走 §3.5，翻译量可能从 6 万条降到 5 千条。
1. 引擎版本：读 `log.txt`（发行包自带）首几行、`game/script_version.txt`，或 `*.exe --version`。版本决定字体 API 与样式行为。
2. 归档内容：解析 `*.rpa` 索引，列出文件名。**要数出 `.rpyc` 的个数和大小**——最大的那几个就是剧情文本所在。注意媒体归档（本项目 `images.rpa` 6.9GB）只需读索引，别整文件读进内存。
3. 字体：`ls game/fonts` + 扫归档里的 `.ttf/.otf`。若只有拉丁字体（OpenSans / Roboto / 自定义），**不解决字体就是满屏豆腐块**，这是第一优先级。若游戏自带 CJK 译文，它多半也把 CJK 字体打进了 `tl/<lang>/fonts/`（见 §6.1）。
4. 现有语言：`ls game/tl/`。只有 `None/` 说明游戏从未做过本地化，`strings:` 表是空的，可自由使用。磁盘上的 `tl/` 可能只剩 `.rar` 之类的残留，**真实译文在归档里**，以索引为准。
5. 游戏自己的设置界面有没有语言项（搜 `LanguagePreference`、以及游戏自定义的 `define languages = {}` 注册表）。没有的话，开关要自己加（§7）。

侦察脚本要点见 §3。

---

## 2. 归档与脚本格式（实测可用的解析路径）

### RPA-3.0 索引
```
文件头 40 字节：b"RPA-3.0 " + 16位十六进制索引偏移 + 空格 + 8位十六进制混淆key
index = pickle.loads(zlib.decompress(读(索引偏移)))
真实 offset = 存储offset ^ key ; 真实 size = 存储size ^ key
```
- 索引的**值是一个 list**（同名文件可被拆成多段，逐段读再拼接），list 里每项是 **2 元组或 3 元组**。3 元组的第三项 `start` 是**要跳过的前缀垃圾**：
  `blob = f.read(len(start) + size)[len(start):]`。漏了这一步会解出 `RENPY RPC2` 之外的乱码。
- 对照实现：`renpy/loader.py` 的 `RPAv3ArchiveHandler.read_index`。
- 读索引只需 `seek(索引偏移)` 后读到文件尾，所以对 6.9GB 的媒体归档也是毫秒级，可以全量扫描所有 `.rpa`。

### `.rpyc` = `RENPY RPC2` 容器
```
10 字节魔数 + 三条 12 字节记录 (slot, start, length)   # slot==0 结束
payload = zlib.decompress(raw[start:start+length])
(data, stmts) = unpickle(payload)
```
- **slot 2 优先于 slot 1**：slot 1 是转换前 AST，slot 2 是 `renpy.translation.restructure()` 之后的（`renpy/script.py` 的 `load_file` 里 `for slot in [2, 1]`）。要拿翻译相关的节点必须用 slot 2。

### 不需要引擎运行时就能反序列化 AST
用 stub unpickler，避免导入 `renpy.ast`（那会拉起显示/音频子系统）：

```python
class Stub:
    def __new__(cls, *a, **k): return object.__new__(cls)
    def __init__(self, *a, **k):
        # REDUCE 构造的对象必须把构造参数留住，否则 PyExpr 的源码会被丢掉
        if a: self._reduce_args = a
    def __setstate__(self, state):
        # AST 节点用 __slots__，picklev2 状态是 (None|dict, slots_dict)
        parts = [p for p in state if isinstance(p, dict)] if isinstance(state, tuple) and len(state) == 2 else []
        if parts:
            for p in parts: self.__dict__.update(p)
        elif isinstance(state, dict): self.__dict__.update(state)
        else: self.__dict__["_state"] = state

def find_class(module, name):
    # renpy.revertable.Revertable{Dict,List,Set} -> 内建 dict/list/set
    # collections.defaultdict -> 真的 defaultdict
    # 其余一律返回一个带 __stubname__ = f"{module}.{name}" 的 Stub 子类
```

两个必须特殊处理的类：
- `renpy.ast.PyCode`：`__getstate__` 返回 `(1, <PyExpr或str>, (filename, linenumber), mode, py, hashcode, col_offset)` → **源码在 `state[1]`**，而 8.4.2 里 `state[1]` 通常是个 `PyExpr` 对象（要递归取其 `_reduce_args[0]`），不是字符串。
- `renpy.astsupport.PyExpr`：通过 `REDUCE` 构造，**Python 源码是构造参数 `args[0]`**。`__init__` 不保存 args 的话，节点 `__dict__` 会是空的 `{}`——这是最容易踩的坑（本项目第一次跑 `speaker variables: 0`、`uwrap` 全空就是这个原因）。

> 8.5.2 里 `renpy/astsupport.py` 甚至没有随包发布，只能靠 `__reduce__` 的元数据反推。**先打印一个节点的原始 state 再写解析代码**，别猜。
>
> **8.1.2 的第三种形态**：`PyCode.__getstate__` 的 source 既不是字符串，也不是带 `_reduce_args` 的 PyExpr，而是 `renpy.ast.PyExpr(filename, linenumber, py)`——**源码只留在 `.rpy` 里，AST 里只有位置**。所以 `pycode_source()` 在这种版本上必然返回 `None`，`uwrap` 抽取必须回落到读 `.rpy`；但 `Say.what` 是**普通字符串**，对白抽取完全不受影响。`rpyc_extract.py` 的取舍即由此而来：串取 AST，`Character` 显示名取 `.rpy`。

---

## 3. 要抽取哪些文本（以及各自的翻译价值）

| 节点/来源 | kind | 是否适合双语 | 说明 |
| --- | --- | --- | --- |
| `renpy.ast.TranslateSay` / `Say` 的 `what` | `say` | ✅ 是 | 对白正文，双语收益最大 |
| `renpy.ast.Menu` 的 `items[i][0]` | `menu` | ✅ 是 | 选择支，框会自适应 |
| `PyCode`/`PyExpr` 源码里 `_("...")` 的字符串常量 | `uwrap` | ⚠️ **逐条看容器** | 人名、导航栏、HUD、图鉴、目标面板、界面广告语 |
| `define`/`default` 里的裸字符串（无 `_()`） | — | ❌ 不能走 `tl/` | 是数据不是可译上下文，只能改数据（不建议） |

**最容易漏的一条**：`uwrap` 不止在 `Define`/`Python` 节点里，**screen 语言节点（`renpy.sl2.slast.SLScreen` / `SLDisplayable`）的字段里也挂着 PyExpr**，界面上看到的 `Text("...")` 文案几乎都在那里。遍历时字段名要覆盖：
`block, children, statements, true, false, second, body, items, child, code, screen`。

**为什么 `uwrap` 能被翻译**：屏幕上的 `Text` 也走 `renpy.substitutions.substitute(..., translate=True)` → `translate_string`（`renpy/text/text.py`、`renpy/character.py`）。所以只要字符串是 `_()` 包的字面量，`strings:` 表就能命中。

**去重要求**：`translate <lang> strings:` 是**按英文串内容**全局匹配的，所以同一份英文在任何地方只会有一个译文。批量派工时必须在 prompt 里写死"同一份输入里英文完全相同的句子，译文必须完全相同"，并在生成阶段做 canonicalize。

**两个会让统计失真的坑（都踩过）**：
- 遍历时**必须排除 `tl/**` 的 `.rpyc`**，否则每种官方语言的译文都会被当成"待译英文"。本项目未排除时数是 112,687 条 / 570 万字符，排除后真实源文本只有 **59,201 条 / 300 万字符**——差了近一倍，且会把法/俄/土语句子混进英文表。
- 过滤"非英文"时**不要用 `is_ascii()`**：英文原文里大量出现 `’ “ ” – é` 等非 ASCII 字符，用 ASCII 判定会静默丢掉整批对白。正确判据是"不含 CJK"。

---

## 3.5 复用游戏自带的官方译文（能省 90% 以上工作量）

发行版若已带 `tl/chinese/`（或 `zh`、`繁体`等），**优先复用而不是重译**：官方译文是人工校对过的，质量高于任何批量机翻，且已经处理好 `[插值]` 与 `{标签}`。

**用 identifier 做连接，不要重建哈希**：
- 源文件里 `renpy.ast.TranslateSay` 节点自带 `identifier`（restructure 阶段生成，如 `thorne_1_kyleenvelopesjail_dialogue_e7e64fd1`）。
- `tl/<lang>/**.rpyc` 里的译文节点是**同一个 identifier**（本项目 story_02：源 796 个、译文 796 个、交集 796，100% 命中）。
- 于是 `(en ← 源.what, zh ← 译.what)` 直接配对，**完全不需要**去复现 §4 说的 `md5(get_code())`，绕开了最脆的一环。
- 另外收集 `renpy.ast.TranslateString`（官方 `strings:` 块）作为兜底，按英文内容配对。

**冲突与覆盖**：
- 同一条英文在不同上下文被译成不同中文时，用**多数表决**（并列取字典序最小保证可复现），并计数上报（本项目 ambiguous=30 / 59,201）。
- 覆盖率按 `zh` 非空计数，缺口（本项目 5,439 条 / 25.2 万字符，集中在新增的 `sandboxevents/`）才交给 agent 翻译。
- 生成时用**新的语言代码**（如 `zh`）而不是复用官方 `chinese`：官方用的是 id 块，同语言下 id 块会**优先于** `strings:` 表（`renpy/ast.py` `TranslateSay.execute`：查到 block 译文就 `next_node(node)`，根本不走字符串表），复用同名会让你的双语 `new` 被静默忽略。

**去音译（当需求是"人名保持原文"时必做）**：官方译文通常把人名音译了（`Kyle→凯尔`、`Ruby→鲁比`、`Sofia→索菲娅`）。`tools/denames.py` 的做法：
1. 候选英文名 = 英文侧**句中**大写词（句首大写不算证据），且不是功能词。
2. 判别式对齐：A=含该名的行的译文，B=不含的其余译文；某 CJK n-gram 在 A 中频率高、在 B 中≈0 → 它就是该名的音译。这一步能自动排除 `早上/妈妈/先生` 这类普通词。
3. 但**光靠判别式会漏**：需要一张"音译用字表"（尔娅莎琳茜丝蒂塔尼…）做二次闸门；反过来该表也会漏 `鲁比/索恩/夏子/光环` 这类不含闸门字的译法 → **必须再出一份不过滤的候选表给人看**，人工补 `names_manual.tsv`。
4. 应用时：**最长优先**（`哈丁塔` 要先于 `哈丁`），并自动补**所有格变体**（`鲁比斯` = Ruby's）；一个名字常有多个变体（Eliana 出现 伊莱安娜/埃莉安娜/伊莱亚娜），漏一个就会留下 `Eliana 亚娜` 这种残渣。
5. 收尾必须**回归验证**：替换后全表扫描"名字紧邻 CJK"的行，残渣数应为 0；本项目 1,758 行被改写，最终残留 0。
6. **`0 candidates matched` 不等于"官方没音译人名"**（本项目第一遍就是这么误判的）。自动候选要求"句中大写 + 出现 ≥25 次 + 音译闸门字"，
   而发行版官方译文常常是**部分音译**：By Justice or Mercy 里主要角色保持拉丁原样（`Ava`、`Leah` 直接出现在中文里），
   但一次性人名全被音译——`Clara Vogel→克拉拉·沃格尔`、`Nakamura→中村`、`Smith→史密斯`、`Emma→艾玛`、`Mia→米娅`、`Tiffany→蒂芙尼`。
7. 抓这类残留的**可靠路径不是 denames 的自动探测**，而是：
   `align_check.py --only-names --names <speakers.json 的显示名>` 列出"英文有名字、中文没有"的行 → 逐行看中文里占住名字位置的是什么 CJK →
   再用一次全表计数确认该 CJK 只出现在人名位置（`陈`、`李` 这类单字姓氏会被 `陈腐` 之类普通词污染，必须排除在批量替换之外、单独按行改）→
   写进 `names_manual.tsv` → `denames.py --apply`（不带 `--seed`，只让手工表生效）。
   `denames.py --seed` 已加进来（跳过频率计数和音译闸门字），但实测**放宽闸门后判别式会抓出同句共现词当译名**
   （`Harper→项提议加上几`、`Man→天啊`），所以它只适合出候选，不适合直接 `--apply`。
   顺带：`·`（间隔号）是西方人名音译的强信号，一行 `grep '·'` 就能捞出全部残留（本项目 3 行）。


---

## 3.6 模式 B 的官方译文复用：`tools/tl_reuse.py`（明文 `translate <lang>` 块）

归档型项目按 identifier 连（§3.5）；散文本项目的官方译文通常是 `renpy translate` 命令生成的**明文 `.rpy`**，
形态是"id 块 + 上面一行注释放着原文"，于是**按内容配对即可，identifier 和 md5 完全不用碰**：

```rpy
# game/script.rpy:6
translate chinese start_9f50295d:

    # "Would you like to see the tutorial?"
    "你想看新手教程吗？"
```

三条实测要点，少一条就会把复用率从 99.6% 掉到 12%（本项目第一版就踩全了）：

1. **绝大多数块带说话人变量前缀**：`# mc "Yeah..."` / `mc "嗯……"`。
   只匹配 `# "..."` + `"..."` 的话，23,673 个块里只能收割到 2,746 个。正则要给引号前加可选的 `[A-Za-z_][\w.]*\s+`。
2. **未知转义必须连反斜杠一起保留**：Python 里 `"\%"` 求值成两个字符 `\%`，所以源文里的 `100\%` 在译文注释里也是 `100\%`。
   自定义 unescape 若把未知转义写成"只留后一个字符"，`100\%` 变成 `100%`，这类串**全部静默失配**。
   判据：跑完看 `still untranslated`，如果剩下的成簇地都带同一个转义，就是解码不一致而不是"官方没译"。
3. **官方译文往往比源码旧一版**（本项目 tl 头写着 2026-05-25，游戏是 8 月的 v25），差异经常只是空白：
   `what about you?` vs `what  about you?`。所以配对要两级：精确 → **折叠空白**（`" ".join(s.split())`）再试一次。
   本项目第二级又捞回 12 条。

**顺带**：如果 `denames.py` 报 `0 candidates matched`，说明官方译者根本没音译人名（本项目即是，`Ava`/`Leah` 原样出现在中文里），
去音译这一步可以整段跳过——别为了"走完流程"硬造映射。

```bash
python tools/rpy_extract.py --game game --out localization/en-zh.json
python tools/tl_reuse.py --tl game/tl/chinese            # 先看报告
python tools/tl_reuse.py --tl game/tl/chinese --apply     # 再写回真源 JSON
```

## 4. 翻译机制：只用 `translate <lang> strings:`

```rpy
# game/tl/<lang>/scripts/story/story_1.rpy
translate zh strings:

    # game/scripts/story/story_1.rpy:9
    old "It's a hot, sunny afternoon in Valley."
    new "这是 Valley 一个炎热晴朗的午后。\nIt's a hot, sunny afternoon in Valley."
```

为什么不用 id 块（`translate zh <identifier>:`）：
- `strings:` 在**变量插值之前**匹配，`[name]`、`[mc.money()]` 这类插值会原样保留并在之后代入 ✅。
- id 块要精确重建 `get_code()`（who / attributes / `@temp` / `nointeract` / arguments / `with`），identifier 后缀是 `md5("\r\n".join(get_code()))[:8]`，重建错一个字符就静默失效。
- 反例：`config.say_menu_text_filter` 拿到的是**已插值**的文本，带变量的句子必然失配，只能当兜底。

写文件的硬规定：
- **UTF-8 带 BOM**（`\ufeff` 开头），和 `renpy/translation/generation.py` 一致。
- 转义按 `encode_say_string` / `quote_unicode`：`\`→`\\`、换行→`\n`、`"`→`\"`，`\t\r\a\b\f\v` 同理。**先替换反斜杠**（`renpy/translation/__init__.py:497` 的顺序就是 `\\` 在最前）。
- **同一种语言内 `old` 绝对不可重复**：`StringTranslator.add()`（`renpy/translation/__init__.py:528`）遇到重复 key 会 **直接 raise**，游戏启动即崩，不是"后者覆盖前者"。跨 kind、跨文件都要按英文内容去重后再落盘。
- 镜像源文件路径生成（纯为可读，功能上 `tl/<lang>/` 下任何 `.rpy` 都会被加载）。规模参考：59,201 条双语 = 12MB `.rpy` / 124 个文件，启动时 `Loading script` 从约 2s 涨到 14s，可接受。

---

## 5. 范围决策：哪些东西**不能**做双语

这是本项目返工最多的一环，先记住结论再动手：

> **固定单行高的容器一旦变成两行，第二行会和第一行重叠，看起来像渲染 bug。**

已知会踩的容器：
- **说话人名字标签**（namebox / `say_label`）→ 人名一律不译。
- **导航栏按钮**（Back / History / Skip / Auto / Save / Prefs）→ 不译。
- **设置页条目**（Music / Sound / Mouse icon / Hour format…）→ 不译。

安全的：对白正文窗口（Frame 自适应高度，实测 6 行不裁切）、选择支列表。

**做法**：把"是否输出"做成生成器的参数（`--kinds say,menu`），而不是删译文。译文全部留在真源 JSON 里，将来某个界面确认能容纳两行，只要加一个 kind 重新生成，**不需要重译**。

**双语的一个反例**：呻吟 / 拟声 / 只有人名的句子（`Mhmmm~`、`Ahhh!!!!`、`Isabel?! Connor?!`）本来就没有可译内容，拼成两行会在对白框里**把同一句英文显示两遍**。生成器规则：译文不含任何 CJK 时，`new` 只输出原文一行（本项目 786 / 59,201 条命中此规则）。

**行数量化后再决定排版**：按虚拟分辨率宽度估每行字符数（经验值：1920 宽、默认字号下中文约 42 字/行、拉丁约 90 字符/行），统计双语后的行数分布。本项目结果 2 行 2600 条 / 3 行 395 条 / ≥5 行仅 23 条 → 不需要额外缩小英文行。

### 5.1 固定高度对白框 = 第二语言被推到屏幕外（The Tutor 踩到的头号问题）

上一段的前提是"对白框会自适应高度"。**很多模板的 `style window` 写死了 `ysize gui.textbox_height`**（The Tutor：278px、字号 29、`dialogue_ypos 75`、`dialogue_width 1316` → 实际只装得下约 5 行）。原文单语言刚好不超，双语后长句必然溢出，而窗口 `yalign 1.0` 贴屏幕底边 → **溢出的部分直接掉出画面，看起来像文本消失**。

判断方法：`grep -n "ysize\|textbox_height" game/*.rpy`，只要 `style window`（或 `say_window`）里有固定 `ysize` 就要处理。

修法（全部走 `translate <lang> style`，不改原文件）：

```rpy
translate zh style say_window:
    ysize 400           # 固定值，比原来的 278 高，够装最长那条双语
    background Frame("gui/textbox.png", 430, 20, xalign=0.5, yalign=1.0)
```

**绝对不要用 `ysize None` 做"自适应高度"。** 直觉上 `ysize None` + `yminimum 278` 才是优雅解法，实测是灾难：stock say 屏幕的那个 `window` 里有**两个子节点**（namebox 的 window + 正文 text），SL 会隐式套一个 `Fixed`，而 **`Fixed` 把整个可用区域报告为自己的尺寸** → 窗口直接变成全屏高，`yalign 1.0` 失去意义，namebox 跑到屏幕顶端，被拉满的 `Frame` 底图把整个画面压暗，游戏没法玩。必须给**固定的 `ysize`**。

`ysize` 怎么定（别拍脑袋，按全表算）：

```python
每行字符数：拉丁 ≈ 1316/(0.52*size)，CJK ≈ 1316/(1.02*size)   # size 取该条实际字号
行数 = ceil(英文/拉丁每行) + ceil(中文/CJK每行)
ysize = max(行数 * size * 1.32) + dialogue_ypos，再留 ~15% 余量
```

The Tutor 实测：最长 7 行（中 3 + 英 4）= 267px，加 `ypos 75` = 342 → 取 **400**。

- 目标样式选 **`say_window`**，不要动 `window`：`style say_window is window` 是引擎给的（`renpy/common/00style.rpy`），`Character(window_style="say_window")` 默认就用它，所以只影响对白框，不会波及设置页/存档页。
- 背景必须换成 `Frame`：原图（1920×277）在更高的窗口里是**底对齐绘制**的，顶部会露出一条没有背景的缝隙，前几行字压在立绘上。`Frame` 的左右边框要**够宽**以保住美术两侧的渐隐（这里 430×2 < 1920），上下边框给小值（20）让中间拉伸——竖向渐变被拉长几乎看不出来。
- 构建参数：`build_tl.py --textbox-height <算出来的固定高度> --window-bg <底图路径> --window-borders <左右,上下>` 生成上面这块。

### 5.2 但是：默认**不要**动对白框几何（用户 2026-10-05 明确定的规矩）

上面那套"增高/换底图"是**技术可行**，不等于**该做**。设计者把对白框做成这个高度是有道理的：
框越高越挡画面、越不像这个游戏。**双语塞不下时的处理顺序是固定的**：

1. **什么都不改**，先看原版框能容几行（按 §5.1 的公式估行数分布）。绝大多数条目 1~2 行，本来就塞得下。
2. 塞不下的比例太高时，**降字号**：`build_tl.py --text-size <比 gui.text_size 小 1~2 档的值>`。
   中英两行共用同一个 `say_dialogue` 样式，所以一个数同时缩小两行；`--text-size` 会顺带带上 `nvl_dialogue`。
   本项目实测：`gui.text_size 35 → 30` 后，典型对白（中 1 行 + 英 1 行）在原框里余量充足。
> Milfylicious 2（1920×1080、`dialogue_width 1116`、`gui.text_size 38`、`textbox_height 278`）实测的阶梯：字号 38 / 34 / 32 / 30 下**中文出框率都是 0.0%**（中文紧凑、又排在上面，20,086 条里一条都没有），只有英文参考行会掉出去：20.8% / 13.9% / 11.0% / **0.6%**。所以"降两档"在这类游戏里一步就把问题基本消掉了，不必动框。数字用 `tools/textbox_fit.py` 出，别估。
3. **最多降两档，再塞不下就让它溢出。** 溢出是可接受的结果，因为中文行排在上面（`--layout zh-first`），
   所以"中文一定看得见"这条底线自动成立，掉的只会是英文那一半——而英文玩家看的是原文，本来就读得懂。
4. `--window-style` / `--window-ypos` 这两个开关留在工具里，但**只在用户明确要求改几何时使用**。
   By Justice or Mercy 第一版就用 `--window-ypos 725` 把框整体上移了 110px，用户实玩后否掉了：
   "很难受玩的，游戏设计者设计那么高的对话框是有道理的"。

> 顺带记两个纯技术事实，将来真要动几何时用得上：
> ① 模板的 `window:` 走 `say_window`，但很多发行版把窗口写死成 `style "window"` / `"window1"`（按 `persistent.color` 二选一），
> 这时 `translate <lang> style say_window` **完全无效**，得用 `--window-style window,window1`。
> ② 背景若写在 screen 里（`background Image(im.Alpha("gui/textbox.png", l_alpha))`），样式层的 `background Frame(...)` 压不过它——
> screen 属性优先级高于样式，于是"增高 + 换 Frame"这条主路整个走不通，只能上移（`--window-ypos`）。

---

## 6. 字体与断行（两个独立问题，都要解决）

### 6.1 字形缺失 = 豆腐块
Ren'Py 8.x 的事实：
- `style.text.font` **不接受列表**，没有"字体回退链"这回事（`renpy/text/text.py`）。
- **没有缺字自动回退**；只有当指定字体文件找不到、且 `config.developer` 为 False 或 `config.allow_sysfonts` 为真时，才会去搜系统字体。
- 逐字符回退要自己构造 `renpy.text.font.FontGroup`（按 unicode 区间分派），成本高。

所以：**用一个同时含拉丁与 CJK 字形的字体**（思源黑体 / Noto Sans SC，OFL 授权可自由分发；本机若已装可直接复制，省一次下载）。

**最省事的一种情况**：游戏自带官方中文时，`tl/chinese/fonts/NotoSansSC-{Regular,Medium,SemiBold,Black}.ttf` 往往**已经打在归档里**（字体走 `renpy.loader`，归档内文件可直接作为字体路径加载）。直接引用这些路径即可，**一个字节的新文件都不用加**，也不会违反"不覆盖原文件"。按文件名后缀做字重匹配（`-Black`/`-SemiBold`/`-Medium`/`-Regular`）把游戏原有的每个拉丁字体映射到同字重的 CJK 字体。

挂载要**三层一起上**（`config.font_name_map` / `config.font_replacement_map` 在 8.4.2 与 8.5.2 都存在，已核对 `renpy/text/font.py:712`、`renpy/text/text.py:258`）：
```python
config.font_name_map[<原字体路径>] = <CJK字体路径>                       # 样式解析层
config.font_replacement_map[(<原>, bold, italic)] = (<CJK>, bold, italic) # 字体加载层
```
```rpy
translate zh style say_dialogue:
    font "fonts/NotoSansSC-VF.ttf"
```

第三层是**必需**的，不是冗余：`renpy.change_language()` 内部会恢复 `gui.*` 变量并调用 `gui._apply_rebuild()`（`renpy/translation/__init__.py`），**把 init 阶段设置的样式全部冲掉**。只有 `translate <lang> style` 块在主题重建之后执行。

> 另一个更省事的办法是直接覆盖 `game/fonts/` 里的字体文件（它们通常是散文件、不在归档里）。**有效但违反"不覆盖原文件"原则**，除非有备份+一键还原，否则别用。

### 6.2 两种字体策略：`map`（全局替换）vs `tag`（只给中文行换字体）

| | `--font-mode map` | `--font-mode tag` |
| --- | --- | --- |
| 做法 | `config.font_name_map` + `font_replacement_map` + `translate <lang> style`，把游戏每个拉丁字体换成 CJK 字体 | 译文里只把**中文那一行**包进 `{font=tl/zh/font/XXX.ttf}…{/font}`，英文行不动 |
| 原版拉丁字形 | **会变**（DejaVu → Noto 之类） | 完全不变 |
| 风险 | 会连带命中游戏用 `{font=…}` 显式指定的字体（标题卡、打字机字体的过场字），把它们也换掉 → 视觉回归 | 无全局副作用 |
| 适用 | 游戏自带官方 CJK 译文、字体本就是 CJK 的归档型项目 | **散文本小项目、或游戏对某些文字显式指定了字体**（例如用打字机字体做 "~ To Be Continued ~" 这类标题卡，属于此类） |

`tag` 模式的三个要点：

1. 字体文件复制到 `game/tl/<lang>/font/` 下（纯新增），`renpy.loader` 能直接从 `tl/` 子目录加载，`{font=tl/zh/font/NotoSansSC-VF.ttf}` 实测可用（8.3.7）。
   **但先确认游戏是不是本来就带了一份 CJK 字体**：带官方多语言译文的发行版几乎都会打进来
   （By Justice or Mercy：`game/fonts/NotoSansSC-VariableFont_wght.ttf`，17MB）。这种场合用
   `build_tl.py --font-mode tag --font-ref fonts/NotoSansSC-VariableFont_wght.ttf`
   ——路径由 `renpy.loader` 按游戏内路径解析，**一个字节都不新增**，`uninstall.py --dry-run` 里也不会多出字体。
   `--cjk-font` 只用于"游戏确实没有 CJK 字体"的情况。
   另一条同样零成本的路子：**照抄游戏自己的惯例**。有些游戏在 `options.rpy` 里写了
   `translate <lang> python: gui.text_font = "fonts/NotoSansSC-..."`（本项目 219 行起，为 chinese/japanese/korean/russian 各写一块），
   给新语言补一块 `translate zh python:` 即可——它天然在 `gui._apply_rebuild()` 之后执行（§6.1 第三层要解决的问题它已经解决了），
   代价是中英两行都换成 CJK 字体，原版拉丁字形会变（所以默认还是 `--font-ref` 的 tag 方案）。

2. **换行要包在标签外面**：`{font=…}{i}{color=…}{size=25}中文{/color}{/size}{/i}{/font}` 这种嵌套是合法的，且因为 `{size=}`/`{color=}` 是逐行生效的，中文行会继承原文独白的斜体/灰色/小号字——**视觉上中英两行同一语域**，这是"贴合氛围"的一部分。
3. 因此 **`zh` 字段里要连标签一起存**（不只是散文），生成器才能退化成一行 `new = wrap(zh) + "\n" + en`；顺带让 `apply_trans.py` 的"标签多重集必须相等"变成真正的守恒闸门。

Windows 本机可直接取用（OFL，可自由分发）：`C:\Windows\Fonts\NotoSansSC-VF.ttf`、`NotoSerifSC-VF.ttf`。

### 6.3 中文不断行
中文没有空格，默认按空格断行会导致整段不折行、撑破画面：
```python
style.text.language = "eastasian"   # 走 UAX#14 断行，见 renpy/text/text.py 的 annotate_unicode
```
`"unicode"` 也可以；`"japanese-*"` 是更严的禁则。纯拉丁文本用 `eastasian` 不会变差（仍只在合法位置断行）。

### 6.4 老引擎根本没有 `config.font_name_map`（8.0.3 实测，会让 `--font-mode map` 直接崩）

手册原先写的"三层挂载"里，`config.font_name_map` 这一层是**新版本才有的**：

| 引擎 | `config.font_name_map` | `config.font_replacement_map` |
| --- | --- | --- |
| 8.0.3 | **不存在**（`renpy/config.py` 里只有 `font_replacement_map`，见该文件 228 行） | 有 |
| 8.1.2 / 8.4.2 / 8.5.2 | 有（`renpy/text/font.py`） | 有 |

`renpy/config.py` 对未知属性走 `__getattr__` 并 **raise Exception('config.%s is not a known configuration variable')**，
所以在这类老引擎上写 `config.font_name_map[...] = ...` 不是"没生效"，是 **init 阶段抛异常、游戏启动即崩**。
症状和 §9 第 9 条一样：`traceback.txt` 新生成，游戏开不了。

**取舍**：老引擎（或任何没核对过的版本）上默认用 `--font-mode tag`（只给中文行包 `{font=}`，
完全不碰字体映射层），既避开这个坑，也保住原版拉丁字形。要上 `map` 就先
`grep -n "font_name_map" renpy/config.py` 确认它存在，或用 `getattr` + `dict` 兜底。
`tools/build_tl.py` 目前只在 `map` 模式下输出这些行，所以**只要选对模式就安全**。

---

## 7. 启用语言与开关

```python
init -2000 python:
    config.default_language = "zh"      # 见下方警告：单设这一条不可靠

init -1000 python:
    renpy.game.preferences.language = None if persistent.rr_lang_off else "zh"
```
- **实测修正（8.4.2）**：`config.default_language` 单独用会失效两次——① `renpy/common/00defaults.rpy:39` 在自己的 init 里又把它赋回 `None`；② `_apply_default_preferences()` 整体被 `if not persistent._set_preferences:` 包着，**只有首次运行才执行**，老玩家（persistent 已存在）根本走不到 `_preferences.language = config.default_language`。所以必须自己在**晚于 00defaults 的优先级**（init -1000）直接写 `renpy.game.preferences.language`，实测生效。
- 这样做的代价要交代：每次启动都会强制回到双语，玩家在游戏内语言菜单改的选择下次启动被覆盖。留后路 = 加 persistent 开关（`if not persistent.xx_lang_off: ...`）。
- 有些游戏另有自己的语言注册表：`define languages = {}`，各 `tl/<lang>/<lang>.rpy` 往里写 `languages["chinese"] = ("中文", "<字体路径>")`。**顺手补一条 `languages["zh"] = ("中文 / English", <字体路径>)`**，新语言就会出现在游戏自己的语言菜单里，不必自己造 UI；用 `try/except` 包住，没有该变量的游戏也不报错。
- 语言目录 `game/tl/zh/` 一旦存在，`known_languages()` 就会自动收录（实测 `['chinese','french',...,'zh']`）。
- `renpy.change_language(None)` 的 `None` 表示**源语言（原文）**，不是"默认语言"——读 `renpy/exports/scriptexports.py:load_language` 确认，别信 docstring 措辞。
- 全局快捷键要自己挂屏幕：`config.always_shown_screens.append(...)` + 屏幕里 `key "..." action Function(...)`。
  **组合键名不是 `ctrl_l`**，那会静默失效。两种可用写法：直接写引擎符号 `ctrl_noshift_K_l`（格式见 `renpy/common/00keymap.rpy`：`<修饰键>_<shift态>_K_<键>`），或注册 `config.keymap["动作名"] = ["ctrl_noshift_K_l"]` 后在屏幕里 `key "动作名"`（本项目用后者，真实键盘实测有效）。
  **注意测试假阴性**：自动化工具合成的 Ctrl 组合键和鼠标点击都可能送不进 SDL 窗口（普通按键如 space/方向键可以），所以"按了没反应"先怀疑输入通路，别急着判定绑定写错——交给真人按一次最省事。
- 环境变量 `RENPY_LANGUAGE` 优先级最高
- 环境变量 `RENPY_LANGUAGE` 优先级最高
### 7.1 退回英文的开关**不能**放在 `game/tl/<lang>/` 里（会自我注销）

覆盖层装好之后玩家就没了退路：不少发行版**自带一个语言菜单屏幕，但入口是注释掉的死 UI**
（Carnal Contract：`game/screens.rpy:1679 screen language_select()` 存在，`screens.rpy:766-768`
的 `ShowMenu("language_select")` 整块被注释）。这种游戏里 `known_languages()` 只有你新加的 `zh`，
玩家唯一的退回手段是删文件——太粗。

**做法**：加一个全局热键（本项目 `Ctrl+L`），翻 `persistent.<项目缩写>_bi_off` 并 `renpy.change_language()`。
关键一条：**这个文件必须落在 `game/`，不能落在 `game/tl/<lang>/`。**
`tl/<lang>/**.rpy` 只在**当前语言等于该语言时**才加载；把热键屏幕写进去，玩家一按"退回英文"，
`tl/zh/` 整个不再加载，热键屏幕跟着消失，**再也切不回来**（症状：只能删文件）。
`build_tl.py` 生成的 `00zz_bilingual.rpy` 里有 `if not persistent.xx_bi_off: preferences.language = "zh"`，
但那段本身也在 `tl/zh/` 里，所以"启动时强制语言"这件事也要在 `game/` 的那份里再做一遍才在两种状态下都成立。

组合键名的写法见上面第 7 条（`ctrl_noshift_K_l`，不是 `ctrl_l`）。
**自动化测不了真按键**（§9 第 3 条：合成输入送不进 SDL 窗口），所以验证方式是探针里直接调那个函数，
断言 `preferences.language` 在 `'zh'` 与 `None` 之间来回翻，再让人按一次确认键位。

- 环境变量 `RENPY_LANGUAGE` 优先级最高（`00start.rpy` 的 `_init_language`），可做零逻辑的启动脚本开关。
- 提前设 `default_language` 还有额外收益：游戏在 `init` 阶段用 `_()` 求值的 `define` 数据（目标标题、事件描述）也会跟着翻译。

---

---

## 8. 批量翻译的工程做法

- **批次要大，大到"一轮装得下全量"**（本项目每组 ~420 条；Carnal Contract 用 550 条 × 22 组，
  正好塞满 20 个并发槽 + 一波尾巴）。判据是**总轮数最少**（见 §0.6），不是单组最省钱：7 条的批次实测 30 万 token，420 条的批次 25–77 万。Midnight Paradise 缺口 5,439 条切成 13 组（每组 ≤430 条 / ≤27,000 字符），单组实测 23 万–155 万 token、3.5–7.5 分钟，**13 组后台并发一次跑完**。
- **并发用后台 agent**（`run_in_background`），主线程同时做去音译、QA、构建，不空等。
- **跑偏判据看 `tool_uses`，不看条数**：正常一组（~500 条 / 4 万字符）是 **3-4 次工具调用**（读 glossary、读 group、写 out、结束）。Milfylicious 2 的 35 组里有 3 组跑到 14/22/33 次，token 分别 260 万 / 370 万 / 630 万，而正常组只要 30-60 万——**这 3 组吃掉了全程约六成的量**。它们产出上没有任何差异（回收后同样 0 缺失），纯粹是反复读回、分片写、自我校验。所以：把"一次 Write 写完"写成 prompt 里的硬约束，回收后按 `tool_uses` 反查异常组。
- **执行契约写进 glossary，不写进 prompt**：35 个 agent 共用一份 `localization/glossary.md`，prompt 只留 6 行（读哪两个文件、写哪一个、别自检）。契约放在共享文件里既省重复，也让"输出格式"这件事只有一个真源。
- **prompt 要精简并明确禁止自检**：写死"不要写校验脚本、不要读真源 JSON、一次读完一次写完"。允许 agent 自我校验会让 token 翻几倍（第 11 组自己跑了校验，用到 155 万 token，是均值 2 倍）。
- 每个 agent 只喂：术语表 + 该组 `{id, who, file, line, en}`；只回 `{id: 译文}`，不输出英文、不解释。
- 给 agent 的上下文顺序：同一 `file` 内按 `line` 升序＝剧情发生顺序，必须连读，否则代词/时态/称呼全乱。
- 术语表要显式列出：说话人变量→显示名、`[...]`/`{...}` 必须原样保留、换行处数保持、重复英文串必须同译、露骨内容按原文语气直译（不写清"这是用户自有游戏的虚构文本本地化"，模型会回避）。
- **人名/专有名词按需求写死**：本项目的规则是"人名一律保持英文原样、不音译"，术语表里要给出正反例（`我和 Kyle 约好了` ✅ / `我和凯尔约好了` ❌），并说明亲属称谓例外（Mom→妈妈）。
- 回收侧的校验器要能容忍"合法的非译文"：纯拟声、纯人名行（`Isabel?! Connor?!`）译完仍不含 CJK，`no-cjk` 判定要先看原文有没有可译的词，否则会误退一批（本项目首跑退了 2 条，都是这种）。
- 进度用"真源 JSON 里 zh 非空计数"记账，天然可断点续跑（生成器只输出已译条目，未译自动保持原文）。

### 8.1 派工 prompt 的"恰好三次调用"写法（2026-10-06 实测，把跑偏率从 2/4 降到 0/22）

> 按 §0.6 理解这一节：约束 agent 是为了**缩短墙钟**（跑偏组霸占并发槽），不是为了省 token。

上一轮的经验是"prompt 里写死禁止自检"。Carnal Contract 阶段 1 用普通措辞派 4 组，
**两组跑偏**（17 与 12 次工具调用，170 万 / 164 万 token，正常是 3-5 次 / 30-60 万）。
把 prompt 改成"你恰好有三次工具调用，然后停"这种**明示预算**的写法后，22 组里 21 组落在 3-6 次。

有效的措辞（按重要性排序）：

1. **`You get exactly THREE tool calls, in this order, then you stop: 1. Read glossary 2. Read group 3. Write out`**
   —— 把预算写成数字而不是一句"别自检"。
2. **`do NOT edit the file after writing it`** —— 跑偏的主因是"写完发现 JSON 坏了要回头修"。
3. **`do NOT re-read anything, do NOT read en-zh.json, do NOT split the output across multiple Write calls`**。
4. **回复格式限死**：`Reply with one line: the number of keys you wrote`，
   再给一条上限 `at most 3 more lines if you had to invent a rule the glossary lacks`。
   这样既拿到术语表空缺（下一轮要补进 glossary），又不让它写小作文。
   上一版写的是"report any judgment calls"，结果每组回 8-13 条，主线读回来也是开销。

**JSON 引号是这一轮最贵的单一失败模式。** 22 组里至少 6 组发出过非法 JSON（值内部裸 `"`、key 少开引号），
被迫多花 1-11 次工具调用回修，其中一组因此烧到 297 万 token。
治法两条：① 把"**值内部绝对不要出现英文双引号**，要引用就用中文引号"写进 **glossary 的执行契约段**（不是 prompt）；
② `tools/repair_json.py` 兜语法，但它**必须**同时校验 key 集合（见 §10.4 的修复）。

**别信 agent 自报的条数。** 有 3 组报"555 keys"（组文件只有 550 条），实际文件里是 550/550 对齐的；
也有组报"已完成"但少 1 条。回收侧一律用 `repair_json.py --in out_NN.json --group group_NN.json`
量一遍 missing/extra/empty，**以文件为准**。

**并发硬上限：20 个子 agent（2026-10-06 实测）。** 一条消息里派 22 个，第 21、22 个直接返回
`Error: Concurrent subagent limit reached. You can run 20 subagents at once. Do not retry.`
—— **不排队、不重试、不报错给后续**，很容易当成"已经在跑"而漏掉两组译文。
所以：分片数 >20 时先派 20 个，剩下的一收到完成通知就补派，并在心里记"已派 N / 总 M"。
上限由 `QODERCN_CLI_MAX_CONCURRENT_SUBAGENTS` 控制（改它属于用户环境，要先问）。

### 8.5 小语料不要派 agent；以及"错位"是唯一抓不到的错

- **≤ 约 500 条对白时，在主线程里自己翻**（The Tutor：323 条 / 3.9 万字符，切 3 个 `out_NN.json` 分片直接写）。派 agent 的固定开销（每个 agent 都要重读术语表 + 分组文件）换不来收益，而且一条连续剧情拆给多个 agent，人称、称呼、语域一定会飘。§8 的并发方案是给"几千到几万条缺口"用的。
- **`apply_trans.py` 的标签守恒挡不住整对错位**：把 A 行的译文挂到 B 行上，只要两行标签结构相同就照样通过。本项目靠 `tools/align_check.py` 兜底，两条判据：
  1. 英文里出现的专名，中文里必须原样出现（漏了 = 大概率错位一行）。
  2. 中文里不许残留小写英文单词（`preceding`/`deliberate`/`overwhelming` 这种"半句没翻"的漏网之鱼，人眼很容易滑过去）。
- **专名集合要三条过滤同时用**，单条都会误报：出现 ≥2 次、其小写形式在语料里从不出现（挡掉 `But/See/Her/You`）、**至少一次真的在句中**（前面紧跟小写词且中间没有句号，挡掉 `Honestly/Holy/Ugh/Mmm` 这类句首感叹词）。另外匹配要用"左右都不是字母"的边界，否则 `Le` 会在 `Leo` 里命中，制造一片假阳性。
- **严重度分档（By Justice or Mercy 把这条改掉了）**：自动探测出来的"专名"里混着 `*Giggle*`、`Mmm`、`Pregnancy`、`Trans`、`Dom/Sub`、`Gala`、`CEO` 这类**拟声词和游戏术语**，官方译者对它们做术语翻译（咯咯笑/怀孕/变性/支配）是正确行为，不是错位——所以自动探测的 MISSING-NAME 一律降级为 **warn**。硬失败只留给 `--only-names`（用 `speakers.json` 的显示名当唯一权威名单）命中的行。同时：
  - `[插值]` 里的标识符（`[mcshort]`、`[groupname]`、`[mnnickname]`）**不是漏译**，LEAK 判定要先剥掉 `[...]`（本项目 201 条 LEAK 全是这个假阳性）。
  - `--names` 要接受逗号分隔（原来 `split()` 只按空白切，传逗号串会整串变成一个永不命中的名字，**看起来"跑了"其实没生效**）。
  - 报告含中文时 `print()` 在 Windows GBK 控制台直接崩（`UnicodeEncodeError`），文件已经写出去了但退出码非零。工具开头统一 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`。
  - 跑完剩下的 LEAK 要逐条看：本项目 12 条全是**故意的**（剧情里的法语点单台词、`死亡flag` 这种玩家黑话），不要机械去"修"。


---

## 9. 验证（含"点不动鼠标"时的替代路径）

自动化验证的坑，按可用度排序：

0. **首选"让游戏自己截图"，不要指望外部截屏工具**：Ren'Py 用 SDL+OpenGL 开窗，Windows 的 WGC / BitBlt / PrintWindow **三条截屏路径全部返回纯黑帧**（本项目实测，NVIDIA + 独显）。可行做法是临时加一个高优先级 init，把回调挂到 `config.periodic_callbacks`，在里面调 `renpy.screenshot(<绝对路径>.png)` + 写一份文本自检报告：
   ```python
   init 9999 python:
       def _probe():
           n = state["n"] + 1; state["n"] = n
           if n % 40: return
           renpy.screenshot(os.path.join(renpy.config.renpy_base, "localization/shots/shot_%04d.png" % n))
       config.periodic_callbacks.append(_probe)
   ```
   同一个回调里用 `renpy.translation.translate_string("<真实英文行>")` 直接断言译文——**这比对截图更有说服力**，因为它走的就是对白实际使用的那条查找路径。再配 `renpy.game.preferences.language`、`renpy.translation.known_languages()`、`config.font_name_map` 三项，能一次确认"语言生效 / 表命中 / 字体映射就位"。
   **这个临时文件用完必须删干净**（见第 5 条）。
   **修正（8.3.7 复验）**：`renpy.screenshot()` 从回调里拿到的是**真实画面**，不是黑帧——"三条截屏路径全黑"说的是**外部**截屏工具打不进 SDL/GL 窗口，内部截图不受影响。所以"游戏自己截图"这条路在每个版本都可信。
> **8.1.2 上写 harness 会撞到的四个 API 坑**（都表现为"我写的东西没生效"而不是报错）：① 自动前进的字段是 `preferences.afm_enable`，**`auto_forward` 这个名字在整个 8.x 里都不存在**（写错就是静默无效，症状是 12 张截图一模一样）；② `renpy.get_time()` 取不到——store 里的 `renpy` 是 `renpy.exports`，没有这个函数，改用 `import time` 自己计时；③ `renpy.translation.X` 不保证可用，但 `renpy.translate_string` / `renpy.known_languages` / `renpy.screenshot` / `renpy.jump_out_of_context` 都是 exports 上的直接名字，用它们；④ `init python` 块里 `import json` 不跨块共享，**每个 `init python:` 自己 import 一次**。
   **同一批复验里踩到的 API 坑**（都会让回调静默失败，症状是"报告没写出来"）：
   - `renpy.get_screen` / `renpy.style.get` 在 `init python` 块里**取不到**（`renpy` 包上没有这些属性）。要用 `renpy.exports.get_screen`，或 `import renpy.display.style`（8.3.7 里这个模块名不存在，样式断言别写死，改成"取不到就跳过"）。
   - 因此**别把布局验证建在样式自省上**，直接截图看。
   - **布局验证必须走真实的 say 屏幕。** 踩过一次假通过：另开一个临时 screen，里面每个 `window` 只放**一个** `text`，截图看着一切正常 —— 而真实游戏里那个 window 有两个子节点（namebox + 正文），`ysize None` 触发隐式 `Fixed` 撑满全屏，直接把游戏搞坏。**单子节点的复现不出来多子节点的布局**，这种"看起来更省事"的合成验证等于没验证。
     另一种同样不算真实路径的做法：自建 screen 里 `use say(who, what)` 再挂进 `config.always_shown_screens`。
     那样窗口脱离了它自己的布局上下文，实测会出现"没有 textbox 背景 + namebox 压在正文第一行上"的**假故障**，
     而真正的溢出问题反而看不出来（8.5.3 复验）。
   - 正确做法：在临时文件里写一个真的 `label`，用真 `Character` + 真 say 语句走真实路径，逐条截图。**首选 `interact=False`**：

     ```rpy
     label zz_selftest:
         python:
             for i, r in enumerate(_ZZ_CASES):
                 who = renpy.store.__dict__.get(r["who"])          # 真的 Character 对象
                 tr = R.translation.translate_string(r["en"])      # 真的查找路径
                 renpy.say(who, tr, interact=False)                # 显示但不等点击
                 renpy.pause(0.4)
                 renpy.screenshot(os.path.join(shots, "rs_%02d.png" % i))
     ```

     `interact=False` 是关键开关（`renpy/exports/sayexports.py:87` 的 docstring 写了）：合成点击送不进 SDL 窗口，
     而它走完真实 say 路径又不会卡住等点击，截图时机由 `renpy.pause` 决定，确定性的。
     备选写法（要逐字复制源英文时）：开自动前进逐条走

     ```rpy
     label zz_lines:
         $ renpy.game.preferences.afm_enable = True
         $ renpy.game.preferences.afm_time = 4.0
         $ renpy.game.preferences.text_cps = 0
         "…这里必须是逐字复制的源英文，标点也要一样…"
     ```

     回调里等 `renpy.exports.get_screen("say")` 为真、且 `renpy.game.context().current` 变化后再**等约 1.6s** 才截图（立刻截会只拿到黑屏，文字还没画出来）。
     探针字符串/文本**一律从 `localization/en-zh.json` 里程序化取**，不要手敲：手敲会把 `’` 打成 `'`，`strings:` 表按内容匹配，一个字符不同就静默不译，你会误判成"翻译没生效"。按"最长 / 含 `{i}` / 含 `[插值]` / 最短 / 无标签"挑样本。
   - **`init python` 里不要 `import renpy`**：store 上的 `renpy` 名字指向的是 `renpy.exports`，
     一句 `import renpy` 会把它换成包对象，引擎自己的 `renpy/common/00start.rpy:211`
     立刻崩 `AttributeError: module 'renpy' has no attribute 'execute_default_statement'`（错误处理里还会二次崩在 `renpy.get_side_image`）。
     需要包级 API 时用别名：`_R = sys.modules["renpy"]`、`_X = sys.modules["renpy.exports"]`。
   - **`default persistent.x = ...` 只在游戏上下文里生效**（如 By Justice or Mercy 的 `screens.rpy:1127 default persistent.color = True`，
     而 `screen say` 就是靠它挑窗口样式/背景的）。在主菜单里做探针会走到"两个分支都不成立"的畸形渲染。
     所以布局探针必须先 `_X.jump_out_of_context("zz_selftest")` 进真实上下文，再在自己的 label 里渲染。
   **探针自己的状态要放 `renpy.session`，不要放 store 里的 dict**（8.0.3 复踩）：
   `jump_out_of_context()` 会开新 context，store 被重置回 init 快照，存在 store 里的
   `state["phase"]` 计数器直接归零，症状是"跳转之后探针就不动了"。
   `renpy.session.setdefault("zz", {...})` 不受 store 重置影响，跨 context 可靠。
   **截图时机必须卡在 `renpy.get_screen("main_menu")` 为真之后**：本作 `label splashscreen`
   是 11s + 5s + 1s 三段 `renpy.pause(hard=True)`，按固定 tick 数走会正好在过场里跳转，
   于是 `JumpOutException` 冒出 `run_context` 写 traceback（就是上面第 2 条的限定条件）。
   另外 `renpy.show_screen("menu_gallery")` 在 splashscreen 期间调会**静默无事发生**，
   截图抓到过场动画，看起来像"图鉴是黑的"——这也是要卡主菜单的第二个理由。
1. **`RENPY_AUTO_LOAD=<存档名>` 环境变量**：启动即载入存档，直接进真实游戏界面。最有用的一招（前提是 `game/saves/` 里有存档；全新发行包通常没有）。
> **启动方式会影响结论**：`setsid ./Game.exe &` 起的 Ren'Py 拿不到前台，`config.periodic_callbacks` 不再触发（harness 什么都不写，容易被误判成"代码没生效"）；直接 `./Game.exe > /dev/null 2>&1 &` 留在同一个 shell 里就正常。另外别把"生成 harness + 清报告 + 启动"整条链一起后台化，那会让轮询读到上一轮的旧报告——**生成和清理放前台，只后台化启动那一步**。
2. **没有存档时怎么进剧情**：在 periodic 回调里执行 `renpy.jump_out_of_context("start")` —— 它 raise 的 `JumpOutException` 会冒泡到主菜单 context 的主循环并被正确处理，**等价于点 START**，且不像 `renpy.jump()` 那样跳过 store 初始化（见第 4 条）。实测能稳定进入 prologue 对白。
   **限定条件（8.3.7 实测）**：只有当前 context 是**主菜单**时才"被正确处理"。很多发行版在 `00start.rpy` 里先 `call _splashscreen`，而游戏的 `splashscreen` 是十几秒的警告视频 + 开场动画；在这期间抛 `JumpOutException` 会一路冒出 `run_context`，直接写 `traceback.txt` 崩给玩家看。所以要么用 `renpy.exports.get_screen("main_menu")` 卡住时机，要么把 tick 数给得足够晚（本项目 32s 才安全）。**回调里 catch 异常时务必把 `JumpOutException` 原样 raise 出去**，否则你吞掉的就是跳转本身，症状是"跳转没生效"。
3. **键盘/鼠标合成都不可信**：合成鼠标点击送不进 SDL 窗口；方向键+回车**看起来**生效过，但对照实验证明那次进入剧情其实是第 2 条的 jump 造成的——**别把脚手架的效果记成输入的功劳**。`config.say_callbacks` 在 8.4.2 **不存在**（会抛 `config.say_callbacks is not a known configuration variable`，整个 init 块静默失败、回调根本没挂上），要抓对白请用 `config.allcharactercallbacks` 或直接放弃。
4. **`--warp game/xxx.rpy:LINE`** 需要 `config.developer`，正式版为 False。可在**高优先级** init 里临时打开：`init 9999 python: config.developer = True`（写 -1500 会被游戏自己的 init 覆盖）。
5. **不要用 `renpy.jump("some_label")` 模拟开局**：会跳过 `label start` 的运行时初始化，游戏自定义样式（如 namebox）尚未注册，报 `Style 'xxx' does not exist`——这是**测试脚手架的假故障**，别误判成自己改坏了。做对照实验（移除本地化层再跑一次）来区分。
6. 临时脚本用完必须**同时删 `.rpy` 和它编译出的 `.rpyc`**——只删 `.rpy` 时 Ren'Py 仍会加载同名 `.rpyc`，"已删除"的调试代码继续生效，会让人对着幽灵现象查半天。
7. 检查 `log.txt`（有无 ParseError / Traceback）与 `traceback.txt` 是否新生成。`log.txt` 里的 `Loading script took Ns` 顺带量化你的译文层体积成本。
8. 静态核对优先于截图：把生成的 `old` 全部导出，`grep -cxF` 逐个确认"不该译的串确实没进表"，比截图更有说服力。
9. 启动即崩的第一嫌疑是 **`old` 重复**（`StringTranslator.add` 直接 raise），第二是 init 块里引用了不存在的 config 变量（整块静默失败，症状是"我写的东西没生效"而不是报错）。

---

## 10. 构建脚本自身的两个必查 bug

- **输出路径要归一化后再分组**：源文件名可能同时出现 `foo.rpy` 和归档名 `foo.rpyc`，若按原始名分组、按归一化名落盘，**后写的会整文件覆盖先写的**（本项目丢过 25 条）。正确做法：先归一化成目标路径，再按路径分组。
- **重建要连孤儿 `.rpyc` 一起清**：`clean` 逻辑只删 `.rpy` 会留下旧缓存，导致上一次的翻译范围复活。

---

### 10.4 `repair_json.py` 在"语法合法"这条路上原本会跳过 key 集合校验

老版本 `main()` 第一件事是 `json.loads(text)`，成功就 `print("already valid JSON"); return 0`。
于是**一份语法正确但少了 40 条的分片会静默通过**，缺口一路带到 `build_tl`（那里只输出已译条目，
少的那 40 条就永远是英文）。现在两条路径都会跑 `missing / extra / empty` 校验，
只有"语法合法且对齐"才 return 0。回收侧一律带上 `--group`，别偷懒不传。

### 10.5 跨批次风格漂移：`tools/style_audit.py`（20 组并发必然出现，`align_check` 抓不到）

`align_check.py` 管两件事：专名错位、中文里残留小写英文词。它**不管风格**，
而 20 个 agent 并行必然在风格上分叉——本项目阶段 1 只有 4 组就已经分叉：

| 漂移点 | 实测规模 | 能不能机械修 |
| --- | --- | --- |
| 括号独白 `(...)` 用半角还是全角 `（）` | 317 条 | ✅ 机械（标签/插值外的 `(`→`（`） |
| `...` 译成 `……` 还是 `…`（源文两种都有，术语表要钉死） | 47 条 | ✅ 单向（只把孤立 `…` 升成 `……`，反向不改，因为 `……` 也是正常中文） |
| 打断号 `--` 被改成 `——` | 少量 | ✅ 机械 |
| `{b}Diane's{/b}` 里英文所有格残渣 | 84 条 | ✅ 机械（只删 `'s`，标签字节不动） |
| `{b}WERE{/b}` `{b}NOW{/b}` 这类**强调词没译** | 35 条 | ❌ 要人/模型逐条改 |
| `daddy` 被译成 `爸爸`（和本作的 `Dad→爸爸` 撞车） | 2 条 | ❌ 逐条 |

**关键收获：要守恒的是标签本身（`{b}`/`{/b}`/`{color=…}` 的数量与顺序），不是标签里的英文字节。**
手册原来把"标签逐字节照抄"写得太宽，导致有 agent 把 `{b}Diane's{/b}` 整个照抄进中文行。
正确口径分三类：① 人名和 `[插值]` 保留原文；② 所有格丢掉 `'s`、把"的"写中文；
③ 普通强调词（`{b}CAN{/b}`、`{b}WAIT{/b}`）**要译**，标签照留。
`apply_trans.py` 的标签多重集检查对这三类都放行，所以它是真闸门而不是"禁止改字节"。

`--apply` 只做机械项，并先把真源 JSON 备份成 `en-zh.before_style.json`；
判不出来的一律只报告。误报要当场处理掉（本项目 `{b}Cass{/b}` 曾被所有格正则当成 `Ca+'s`，
`Minotaur→弥诺陶洛斯` 曾被专名检查当成漏译）——**报告里剩下的每一条都要有结论**，否则下一个人不敢信它。

**顺序**：`apply_trans` → `style_audit --apply` → 手工修剩下的 → `build_tl` → `qa` → `align_check`。
放在 `build_tl` 之前，因为生成器只认 JSON。

## 11. 回滚与可逆性

- 全部产物是新增文件：`game/tl/<lang>/**`、一个挂载用 `.rpy`、一个字体。卸载 = 删这几样。
- 提供 `tools/uninstall.py`：删新增文件 + 从 `localization/backup/` 还原任何被替换过的原文件，并写一份操作日志。
- 永远不改：`*.rpa`、`renpy/`、`game/saves/`。

---

### 11.1 顺手解锁图鉴 / CG / 动画回看：先找开发者自己留的死开关

汉化任务里常带的附加需求："不玩游戏也要能直接看 Extra 里的 CG 和动画"。
这是**同一套可逆覆盖层**的活儿，不要改原文件，也不要写 persistent。

**第一步永远是 grep 门控表达式本身**，而不是猜存档字段：

```bash
grep -rho "if .\{0,160\}" game/scripts/gallery/*.rpy | grep -E "persistent|UNLOCKED|BONUS"   | sed -E 's/EP[0-9_A-Za-z]+/EP_ID/g' | sort | uniq -c | sort -rn
```

Carnal Contract 的结果是 163 + 30 处全部长同一个形状：

```rpy
if EP01_BECKY_e1i341 in persistent.gallery["Becky"] and BONUS_CODE_SEASSON_1 == 1 or EXTRAS_GALLERY_UNLOCKED == 1:
```

注意 Python 的优先级：`A and B or C` == `(A and B) or C`。所以 **`C` 单独成立就全解锁**，
而 `EXTRAS_GALLERY_UNLOCKED` / `EXTRAS_REPLAY_UNLOCKED` 只在 `configuration.rpy` 里
`default ... = 0`，**全脚本从未再赋值** —— 是开发者留给自己调试的死开关。
`grep -rn EXTRAS_GALLERY_UNLOCKED game --include=*.rpy` 确认它只有 default 一处，就能放心用。

于是解锁 = 置 1，一条 `.add()` 都不用写，196 个 id 一个都不用列：

```rpy
init 10000 python:
    def _cc_unlock_extras():
        store.EXTRAS_GALLERY_UNLOCKED = 1
        store.EXTRAS_REPLAY_UNLOCKED = 1
    _cc_unlock_extras()
    config.after_load_callbacks.append(_cc_unlock_extras)   # 读档时存档里的 0 会盖掉 init
    config.start_callbacks.append(_cc_unlock_extras)
```

三个坑，都踩过：

1. **`config.load_callbacks` 这个名字不存在**（8.0.3 只有 `start_callbacks` / `after_load_callbacks`，
   定义在 `renpy/common/00start.rpy:34,57`，`init -1600`）。写错不是"没生效"，
   是 **init 阶段抛异常、游戏启动即崩**（同 §6.4 的机制）。**动手前先 `grep -n "_callbacks" renpy/config.py`。**
2. **为什么要 `init 10000`**：`default` 语句在 init 阶段执行，而"新游戏时重置 store"用的快照
   是 **init 全部跑完之后**才拍的，所以高优先级 init 的赋值会进快照、跟着新游戏活下来；
   但**读旧存档**时存档里的值是 0，会盖掉快照，所以还要挂 `after_load_callbacks` 再设一次。
3. **成就页的开关别顺手打开**：`ACHIEVEMENTS_UNLOCKED` 只会把成就名剧透出来，没有画面，
   用户要的是 CG，不是成就列表。要就单独问。

**验证不能只看 flag == 1**，要断言门控表达式整体：

```python
rep = {
  "gate_first_clause": key in persistent.gallery["Becky"] and BONUS_CODE_SEASSON_1 == 1,
  "gate_whole_expression": (key in persistent.gallery["Becky"] and BONUS_CODE_SEASSON_1 == 1)
                            or EXTRAS_GALLERY_UNLOCKED == 1,
  "gallery_sizes": {k: len(v) for k, v in persistent.gallery.items()},
}
```

`first=False` 且 `whole=True` 才是"靠我们的开关打开的"；同时 `gallery_sizes` 每项都是 1
（只有 `"default"`）证明玩家确实没进度。**再看一张真图**：用 §9 的老办法等主菜单出来后
`renpy.jump_out_of_context("galleryDiane")` 截图，缩略图是彩色 CG 而不是锁图标才算完。
动画那一页同理（`jump_out_of_context("galleryScenes")`），
并且可以在探针里直接 `Replay("e1scene01_suck", locked=False)()` —— 实测从没通关的状态能直接播出来。
**一次运行只 jump 得了一次**：第二次 `JumpOutException` 已经没有主菜单 context 兜底，会写 traceback 崩给玩家（§9 第 2 条的限定条件）。

### 11.2 解锁要做成**游戏内可切换按钮**，不要硬解（默认口径 §0.5 第 10 条）

玩家要的是"我能自己决定这一局要不要看"，不是一个被永久改掉的存档状态。形状：

```rpy
default persistent.cc_gallery_unlocked = True      ## 默认全解锁

init 10000 python:
    def _cc_apply_gallery_unlock():
        on = bool(getattr(persistent, "cc_gallery_unlocked", True))
        store.EXTRAS_GALLERY_UNLOCKED = 1 if on else 0
        store.EXTRAS_REPLAY_UNLOCKED = 1 if on else 0
    _cc_apply_gallery_unlock()
    config.after_load_callbacks.append(_cc_apply_gallery_unlock)
    config.start_callbacks.append(_cc_apply_gallery_unlock)
    config.always_shown_screens.append("cc_gallery_unlock_button")

screen cc_gallery_unlock_button():
    zorder 100
    if _cc_menu_up():                                ## 只在菜单类界面露出，正片里不常驻
        textbutton "…全解锁…":
            align (0.995, 0.28)
            anchor (1.0, 0.0)
            action [ToggleField(persistent, "cc_gallery_unlocked"),
                    Function(_cc_apply_gallery_unlock)]
```

四条实测要点：

1. **标签里的中文必须包 `{font=…}`**。UI 字体（本作是 `SourceSansPro` / `Lato`）没有 CJK 字形，
   不包就是豆腐块 —— 和 §16.5 徽章那条是同一个闸门，先过 `tools/font_cmap.py`。
2. **只在菜单界面显示**：`if _cc_menu_up()` 里查 `renpy.get_screen("main_menu"/"preferences"/…)`。
   正片屏幕上常驻一个可点的东西会挡画面也挡点击。位置用截图挑（本作右上 `align (0.995, 0.28)`
   正好在 Steam/Discord 下面、logo 上面，不压任何原 UI）。
3. **验证开关类 UI 必须走真实 action 链**。从探针里直接 `persistent.x = False` 再截图，
   **屏幕不会重跑**，标签还停在旧状态（我第一版就是这么误判"按钮没生效"）。
   正确做法是把按钮 `action` 列表里的那几个对象取出来自己调一遍：
   `[store.ToggleField(persistent, "cc_gallery_unlocked"), store.Function(_cc_apply)]` → 逐个 `()`，
   再截图看标签有没有翻。合成鼠标点击送不进 SDL（§9 第 3 条），所以这是唯一的自动化真路径。
4. **`ToggleField` / `Function` 不在 `renpy.exports` 上**（8.0.3 实测 `AttributeError`），
   它们是 store / `renpy.commonactions` 里的名字。探针里要用 `renpy.store.ToggleField`。

状态机验证到位的样子（三个截图 + 一行报告）：`flag=1 persistent=True` → `flag=0 persistent=False`
→ `flag=1 persistent=True`，并且**第二张截图的标签文案确实变了**。

**回滚**：这个 `.rpy`（和引擎给它生成的 `.rpyc`）手动 `printf` 进 `localization/generated_files.txt`，
`uninstall.py` 就会连它一起删。**但要想清楚**：汉化层和解锁层是两个功能，合成一条卸载命令
意味着"取消汉化"会顺手把解锁也撤掉。要么接受并在交付说明里写清"解锁 = 删这两个文件"，
要么分开放。本项目选了合并 + 明说。


### 11.3 三条解锁路线，按成本排序（第 2 条是参照社区 mod 学到的）

| | 做法 | 适用条件 | 成本 / 风险 |
| --- | --- | --- | --- |
| **A. 翻开发者死开关**（§11.1） | `grep` 门控表达式，找 `or XXX_UNLOCKED == 1` 这类从未赋值的总开关，置 1 | 作者留了开关（不少发行版都有） | 最低；不写 persistent，删文件即还原 |
| **B. 反编译游戏自己的图鉴 screen，就地改门控**（本节） | 用 [unrpyc](https://github.com/CensoredUsername/unrpyc) 解出游戏的 `gallery.rpy`，把每条的 `Replay(lbl)` 改成 `Replay(lbl, locked=False)`、把 `if persistent.x:` 的判断去掉，然后把这份 `.rpy` 放进 `game/` 覆盖归档里的 `.rpyc` | **没有死开关**、门控散落在每个条目上 | 中；要维护一整屏 UI，游戏更新后行号/条目会变 |
| C. 自己另写一个图鉴页 | 完全自建 screen + 按钮 | 想顺便改布局/加筛选 | 最高，等于重做 UI |

Being a DiK 的社区 Gallery_Unlocker 是 **B 的范本**（`gallery.rpy`，1205 行，尾部就写着
`# Decompiled by unrpyc`）。拆开看它的四个决定，每一条都可以直接抄：

```rpy
init:
    $ persistent.totalScenes = 50
    if renpy.loadable("season2/scripts/update7.rpyc"):      # ①版本探测
        $ persistent.totalScenes_s2 = 67
    if persistent.ep1_josy_lewd_chick == None:              # ②None 归一化
        $ persistent.ep1_josy_lewd_chick = False
    ...
screen scenes:
    tag menu                                                # ③参与菜单栈
    key "mouseup_2" action Return()                         #   右键就能退出
    vpgrid:                                                 # ④网格 + 滚动
        cols 5
        draggable True
        mousewheel True
        scrollbars "vertical"
        vbox:
            imagebutton:
                focus_mask True                             # 不规则缩略图要按像素遮罩判定点击
                idle Transform ("images/gallery/ep1_josy.png")
                action Replay("ep1_josy_lewd", locked=False)  # 核心就这一句
```

1. **`renpy.loadable("<归档内路径>.rpyc")` 做版本/内容探测**，而不是把数量写死。
   它靠"这个文件在不在"决定 `totalScenes` 是 50 还是 67，一个 mod 同时适配多个更新版。
   同理运行时防呆用 `renpy.has_label(label)`：游戏更新后 label 改名/搬走时，
   书签应当 `renpy.notify()` 提示，而不是抛异常崩在玩家面前。
2. **绕过门控进未解锁场景之前，先把 `None` 归一化。** 游戏的"已收集 X / Y"这类计数
   会对 `persistent.x` 做算术，未解锁时它是 `None` → 直接崩。社区 mod 用两百行
   `if persistent.x == None: $ persistent.x = False` 专门处理这件事。
   **凡是让玩家可以跳过进度去进场景的功能，都要检查游戏自己有没有这种计数。**
3. **`tag menu` + 右键 `Return()`**：自建的全屏菜单要给一个不用找按钮的出口。
4. **`vpgrid` + `focus_mask True`**：条目多到几十上百时用网格而不是 vbox 列表；
   非矩形缩略图必须开 `focus_mask`，否则透明区域也会吃掉点击。

**反面教训**：那个 mod 把 115 个条目**逐个手抄**成 1205 行，绑死在 0.8.0 这一个版本上 ——
游戏一更新就得重做。所以本仓库的 B 路线要落成**生成器**（`tools/build_bookmarks.py` 就是这个思路：
条目、范围、门控、播种全部从 `.rpyc` AST 里读出来再生成），而不是手写覆盖层。

### 11.4 冷进"未硬化"场景要补作者自己补的那几个变量

这条是 §11.3 第 2 点的进阶版，也是 Being a DiK 那个 mod 没做、但本作必须做的一件事。

作者把场景做进画廊时会写头守卫来重播种（因为 `Replay` 会 `clean_stores()`，
store 回到 `define` 值，玩家起的名字会退回默认）：

```rpy
label e1scene01_suck:
    if _in_replay:
        $ name = persistent.name        # ← 没有这行，名字框显示 "Dotty"
```

**而没被做进画廊的场景没有这行。** Carnal Contract 的 10 条书签**全部属于这种**，
所以冷进去之后对白里 `[name]` 渲染成 `define name = "Dotty"`，不是玩家起的名字 ——
不崩，但一眼假。

做法：**让生成器从游戏自己的头守卫里学播种**，运行时经 `Replay(scope=…)` 注入：

```python
# tools/build_bookmarks.py：扫遍硬化场景的 seed_lines，收集 `var = <含 persistent 的表达式>`
game_seed = {}
for sc in scenes.values():
    for line in sc.get("seed_lines") or []:
        m = re.match(r"\$\s*([A-Za-z_]\w*)\s*=\s*(.+)$", line.strip())
        if m and "persistent" in m.group(2):
            game_seed[m.group(1)] = m.group(2).strip()      # {'name': 'persistent.name'}
```

```rpy
# 运行时：在**外面**（正常 store）求值，再把值塞进 scope
for var, expr in (entry.get("seed") or {}).items():
    try:
        scope[var] = eval(expr)
    except Exception:
        pass
Replay(entry["label"], scope=scope, locked=False)()
```

实测：把 `persistent.name` 设成 `Zedtest` 后冷进未硬化场景 `n_bjj_n_1`，
回放里读 `store.name` 得到 `'Zedtest'`（没播种会是 `'Dotty'`），退出后 `persistent.name` 未被改动。

**求值要在进入回放之前做**：`scope` 是"设值"，不是"贴代码"，所以 `eval` 发生在正常 store 里，
回放内不需要那个表达式所依赖的东西存在。

---

## 12. 文件契约（复制到新项目时的最小工具集）

| 文件 | 职责 | 输入 → 输出 |
| --- | --- | --- |
| `tools/rpautil.py` | RPA3 索引 / RPC2 slot / stub unpickler / AST 遍历，其余工具的公共底座 | — |
| `tools/extract.py` | 解析全部 rpa+rpyc，抽源文本待译串，**同时**按 identifier 连接归档里自带的各语言译文并多数表决 | `game/*.rpa` → `en-zh.json` + `speakers.json` + `extract_report.txt` |
| `tools/denames.py` | 复用官方译文时把音译人名还原成原文（判别式对齐 + 音译字闸门 + 人工补充表 + 所有格变体 + 最长优先） | JSON → 就地改写 + `names_proposed.tsv`（不过滤版供人工复核） |
| `tools/dump_groups.py` | 把未译条目按序切成大组 | JSON → `localization/groups/group_NN.json` |
| `tools/apply_trans.py` | 合并 agent 回传的译文分片，做标签/插值/换行守恒预检，拒绝项进 `rejected/` 保留原文便于复跑 | `out_NN.json` → 写回真源 JSON |
| `tools/build_tl.py` | 生成 `tl` 文件 + 语言/字体/断行装配文件；`--layout`（zh-first / en-first / zh-only）、`--kinds`、`--clean`、`--limit`（冒烟测试）；`--font-mode map\|tag` + `--cjk-font`（复制字体）或 `--font-ref`（**引用游戏已自带的路径，零新增文件**）；`--text-size`（中英共用 `say_dialogue` 的字号，双语溢出时的唯一手段）；`--window-style` / `--window-ypos` 保留但**默认不用**（§5.2）；自动扫描归档内已有 CJK 字体并按字重建映射 | JSON → `game/tl/<lang>/**.rpy` + `generated_files.txt` |
| `tools/qa.py` | 校验：BOM、**`old` 无重复（重复=启动即崩）**、每个 `old` 确实等于某条真实源串、双语对里英文未丢失、标签/插值守恒、覆盖率 | → `qa_report.txt`，非零退出码表示有问题 |
| `tools/rpy_extract.py` | **模式 B**：游戏直接给散文本 `.rpy` 时的抽取器。先收集 `Character(...)` 变量名，只认"裸字符串"或"已知角色变量 + 字符串"两种语句，并且**只收 `label` 块内的**——`screen`/`style` 块里的裸字符串（`"bottom_left"` 这类）会被误判成对白，缩进栈判上下文可以挡住它 | `game/**/*.rpy` → 与 `extract.py` 完全同构的 `en-zh.json` |
| `tools/tl_reuse.py` | **模式 B 复用官方译文**：解析明文 `game/tl/<lang>/*.rpy` 里的 id 块 / `strings` 块，按**内容**配对（§3.6）。说话人前缀形态、未知转义保留反斜杠、折叠空白二次配对是它的三条命门 | `tl/<lang>/*.rpy` + JSON → 就地填 `zh` + `reuse_report.txt` |
| `tools/rpyc_extract.py` | **模式 B 的默认抽取器**（游戏带 `.rpyc` 时优先于 `rpy_extract.py`）：反序列化引擎真正加载的 AST，取 `Say.what` / `Menu` 标题——这就是引擎查 `strings:` 表时用的那几个字节，所以 `old` 不可能失配。`Character` 显示名回落到读 `.rpy`（8.1.2 的 AST 里源码只剩位置，见 §2）。`--reuse` 顺手按 identifier 连自带官方译文 |
| `tools/textbox_fit.py` | §5.2 第 1-2 步的数据来源：从真源 JSON 统计"中文出框率 / 任一行出框率"，给出候选 `--text-size` 和（万一真要动几何时）所需 `ysize`，不拍脑袋 |
| `tools/style_audit.py` | **跨批次风格闸门**（§10.5）：括号全/半角、`...`→`……`、`--` 不许变 `——`、`{b}X's{/b}` 英文所有格残渣、`{b}` 里没译的强调词、`daddy` 撞 `爸爸`。`--apply` 只做机械项并先备份真源 JSON，其余只报告 | 真源 JSON → 就地改写 + 分类计数报告 |
| `tools/scan_bookmarks.py` | **路线书签的场景枚举器**（§17）：从引擎真正加载的 `.rpyc` AST 列出全部 `label`，给出每个场景的节点范围、`_in_replay` 头/尾守卫、尾跳目标、区间外绕行清单（`escapes`）、出场说话人、作者自己的状态播种行；`--dump-candidates` 按规则词表出候选批次喂判定 agent。自带覆盖率自检（`.rpy` 里 `_in_replay` 出现数 vs 扫到数），检测一滑会直接告警而不是静默少报 | `game/**/*.rpyc` → `scenes.json` + `scenes_report.txt` + 候选批 |
| `tools/build_bookmarks.py` | 把 `scenes.json` + `verdicts_*.json` + `bookmark_rules.json` 编成 `game/cc_bookmark_data.rpy`（`define cc_bm_entries`）。最值钱的是 **picks 推导**：对每对成对分支，找一个 menu 的两个选项分别跳到这两个 label，记下该选第几项；推不出来就进 review 不猜。第二个增量是 **播种学习**：扫硬化场景的 `if _in_replay:` 块收集 `var = persistent.x`，写进每条书签的 `seed`（§11.4）。两份输入路径都写错时它会直接报错而不是产出空数据文件。jump 从 `.rpy` 文本解析，因为 `Menu.items` 第二项是条件串不是块（§17.7） | 三份输入 → 数据 `.rpy` + `bookmark_review.txt` |
| `tools/repair_json.py` | 回收侧机械修复：agent 手写的几百行 JSON 会出现"key 丢了开引号""值里有未转义引号"。按行修好后**必须与 group 的 id 集合完全对齐才写回**，对不上就退回重派——重派一组比误信一次修复便宜 |
| `tools/make_selftest.py` + `tools/selftest_template.rpy` | §9.0 的现成 harness。探针语句从真源 JSON 生成；`mix` 模式按排版风险各取一条（最长行 / 带 `{size=26}` 补述 / 带名字框的台词 / 纯拟声单行）。跑完自动写 `selftest_report.txt`（`preferences.language`、`known_languages`、`font_name_map`、每条 `translate_string` 命中与否）和 12 张截图 |
| `tools/align_check.py` | 对齐与漏译审计（见 §8.5）。`apply_trans.py` 的标签守恒**抓不到"整对错位一行"**，因为错位后标签仍然相等；这里用"英文里出现的专名必须也出现在中文里"+"中文里不许残留小写英文单词"两个判据补上。`--only-names` 让显示名表成为唯一硬判据，`[...]` 插值不算漏译 | JSON → `align_report.txt`，非零退出码表示有硬失败 |
| `tools/uninstall.py` | 一键回滚（按 manifest + 扫 `tl/<lang>/` 双保险）。**扫描要收目录下全部文件**，不能只挑 `.rpy`/`.rpyc`——`--cjk-font` 复制进去的字体也在 `tl/<lang>/font/` 里，漏了就不是"零残留" | — |
| `tools/scan_routes.py` | **路线标记**：解析 `menu:` 与 `screen choiceN()`，算出每个选项实际改哪个统计量/跳哪个 label，套 `route_rules.json` 判定，出"该标的选项串"+ 一份"规则判不出来、要人确认"的清单。**判不出来一律不猜** | `game/**.rpy` + rules → `route_marks.json` + `route_review.txt` |
| `tools/font_cmap.py` | 纯 stdlib 读 TTF/OTF 的 `cmap`，回答"这个字形到底有没有"。任何要上屏的非拉丁字符（符号/emoji/生僻字）先过它 | 字体路径 + 文本 → 缺字列表，非零退出码 |
| `localization/route_rules.json` | 某款游戏的路线规则实例（含剧情走向，**属衍生内容不外传**；公开仓放 `route_rules.template.json`） | 人写 + `route_review.txt` 回填 |
| `localization/glossary.md` | 人名表（保持原文，不音译）+ 硬约束 + 风格基线，直接喂给翻译 agent | — |
| `localization/names_manual.tsv` | 去音译的人工补充映射，含 `前缀~禁止后接字` 语法 | — |

**改引擎相关代码前先读源码定位行号**：`renpy/loader.py`（RPA3 索引）、`renpy/script.py`（RPC2 slot）、`renpy/translation/__init__.py`（`create_translate` 的 identifier 算法、`change_language` 的 `gui._apply_rebuild`）、`renpy/text/text.py`（`style.language` 断行、`font_name_map`）、`renpy/text/font.py`（`font_replacement_map`、`FontGroup`）、`renpy/parser.py`（`translate` 语句的三种形态：`strings` / `python` / `style <样式名>:`）。

---

## 13. 一句话检查表

1. **归档里有 `tl/<lang>/` 吗** → 有 → 按 identifier 连接复用官方译文（§3.5），只翻译缺口；这一步能省掉 90%+ 的量。
2. 提取时排除 `tl/**`，过滤条件用"不含 CJK"而不是"纯 ASCII"。
3. 脚本在归档里吗 → 是 → 自研提取，别用 `renpy translate` 命令（它对归档文件会整批跳过）。
4. 有中文字形吗 → 没有 → 先看归档里有没有现成 CJK 字体（`tl/<lang>/fonts/`），有就直接引用；再三层挂字体 + `style.*.language = "eastasian"`。
5. 双语会落进固定单行框吗 → 会 → 该串不译，用 `--kinds` 控制输出而不是删译文；人名标签一律不译。
6. 译文不含 CJK 的（拟声/纯人名）只输出原文一行，别把英文显示两遍。
7. 译文只存中文，双语由生成器拼接 → 版式随时可改，永不重译。
8. `old` 必须全表唯一（重复=启动崩），且必须逐字节等于源串（不等=静默不生效）。
9. 启用语言：`config.default_language` 只在建档首次运行生效，必须自己在 init -1000 写 `preferences.language`；有 `languages` 注册表的游戏顺手加一条。
10. 每次重建：删 `.rpy` **和** `.rpyc`，路径归一化后分组。
11. 验证：外部截屏对 SDL/GL 窗口全黑 → 用 `config.periodic_callbacks` + `renpy.screenshot()` + `translate_string()` 自检；进剧情用 `jump_out_of_context("start")`，不是 `jump()`；临时文件连 `.rpyc` 一起删。
12. 一切改动可一键回滚，原文件零修改。
13. **对白框塞不下双语时，只降字号（`--text-size`，最多 1~2 档），绝不动几何**。降完还塞不下就让它溢出——中文在上面所以中文必然看得见（§5.2）。
14. **游戏有没有对某些文字显式 `{font=}`**（标题卡/打字机字体）→ 有就用 `--font-mode tag`，别用全局字体映射把它们一起换掉（§6.2）。
15. `zh` 字段连 `{标签}` 一起存，让标签守恒成为真闸门；生成器只负责拼中英两行。
16. 翻完跑 `align_check.py`：标签检查抓不到"错位一行"，专名与漏译检查能。
17. 交付前 `uninstall.py --dry-run` 列出的必须**恰好**是你新增的文件，包含复制进去的字体。
18. **游戏带 `.rpyc` 就用 `rpyc_extract.py`**，别正则扫 `.rpy`：说话人变量认不出来就会整批静默漏句（实测漏 12.6%，漏的全是台词最多的主角）。
19. **回收后按 `tool_uses` 反查异常组**（正常 3-4 次），并对每个分片跑 `repair_json.py` 对齐 id 集合；缺 key 的组要么补要么重派，不要带着缺口进生成。
20. 审查报出的 `LEAK` 分两类：**普通英文词被偷懒留下 = 必须翻**（`dinner`、`intensity`、`Holy shit`）；**角色原话的外语、品牌 / 网址 / 游戏自造术语 = 保留并写进 `localization/leak_allow.txt`**，报告里回显命中了哪些，让豁免本身可审。还有一类是 `grand[m]` 这种**插值当词素用**的（`[m]` 是玩家填的 "mother"，合起来才是 grandmother），中文拆不出来，只能原样留 + 记账。
18. **模式 B 且 `game/tl/<lang>/*.rpy` 是明文** → 用 `tl_reuse.py` 按内容配对官方译文（§3.6）；收割正则要能吃 `# mc "old"` / `mc "new"` 的说话人前缀形态，未知转义要连反斜杠一起保留，配对失败先试折叠空白。
19. **布局自检必须走真 `renpy.say(who, tr, interact=False)`**（在真实游戏上下文里），`always_shown` + `use say(...)` 的自建 screen 是假故障制造机（§9.0）。
20. **`denames.py` 报 0 candidates ≠ 官方没音译人名**。再 `grep '·'` 一次，并用 `align_check --only-names` 的"英文有名字、中文没有"清单逐行确认（§3.5 第 6/7 条）。
22. **要上屏的每个非拉丁字形都先过 `tools/font_cmap.py`**。`⚑`(U+2691) 和 `🚩`(U+1F6A9) 在思源黑体里**都没有**，实测就是豆腐块；`★ ☆ ⚠ ▲ ● ◆ → 【】` 有。
23. **标记层必须和译文层共用一个写者**（`build_tl.py --marks`），否则同一个 `old` 可能被两边各写一次 → `StringTranslator.add` 直接 raise、游戏启动即崩。跨 kind 撞的串（`Yes`/`No` 同时是 say 和 menu）要在生成期挡掉。
24. 路线标记**判不出来就进 review 清单，不许猜**。极性反转是常态（本游戏 Alex：跟她争=涨 `alexDom` 才进她被绑的那场），只靠"蓝色=温柔"推不出来。
21. **改对白框之前先读 `screen say` 用的是哪个样式名**：`style "window"` 的游戏对 `say_window` 的覆盖完全无感；背景写在 screen 里时样式层也改不到它（§5.1）。

25. **老引擎先 grep 再写**：`config.font_name_map` 在 8.0.3 不存在、`config.load_callbacks` 也不存在，
    写上去不是静默失效而是 **init 抛异常、启动即崩**。`grep -n "font_name_map" renpy/config.py`、
    `grep -n "_callbacks" renpy/config.py` 两条命令换一次重启（§6.4、§11.1）。
26. **双语退回开关放 `game/`，不放 `game/tl/<lang>/`**：后者只在当前语言匹配时加载，
    切回英文的同时把自己的热键注销了（§7.1）。游戏自带的语言菜单经常是**注释掉的死 UI**。
27. **20 组以上并发要知道硬上限是 20**，超出的调用直接报错、不排队；
    派工 prompt 写"恰好三次工具调用"，并把"JSON 值内不要出现英文双引号"写进 glossary 契约（§8.1）。
28. **回收以文件为准，不信 agent 自报条数**：`repair_json.py --in out_NN --group group_NN` 必须带 `--group`，
    它现在两条路径都会校验 key 集合（§10.4）。
29. **翻完跑 `style_audit.py --apply` 再建层**：20 个并行 agent 必然在括号、省略号、所有格、
    强调词上分叉，`align_check` 抓不到这些；机械项自动修，剩下的人工过（§10.5）。
32. **解锁是默认动作，但必须可切换**：做成游戏内按钮 + `persistent` 存状态（§11.2），
    别硬解。验证要**走按钮的真实 action 链**再截图——探针里直接改 `persistent` 字段，
    屏幕不会重跑，标签停在旧状态，会误判成"按钮没生效"。
34. **书签的停车闸要"落进本场景才开始盯"，且回调里一律 `getattr(store, …)`**：
    `default` 名在 init 期不存在，而 `statement_callbacks` 在 init 期就会被调用，
    直接 `renpy.store.X` 会让游戏启动即崩（§17.3）。允许范围走 `Replay(scope=…)` 注入，
    靠引擎 `sb.restore()` 自动解除武装；另加语句计数熔断，写错范围时最坏是提前结束。
35. **自动选的唯一切点是 `renpy.store.menu`**；patch `renpy.exports.display_menu` 无效，
    `interact=False` 返回 `None` 会**静默跳过选择**，不能拿来自动选（§17.4）。
    判不出方向必须落回真菜单弹给玩家。
36. **`label` 名会骗人，书签判定必须读内容**；绑架/被捕这类"男性无力但不是 D/s"要显式排除；
    喂给判定 agent 的场景文本要按**全部 label** 划边界，按候选划会越界（本项目整批作废重跑）。（§17.5）
37. **改完 `.rpy` 先 `"<游戏>.exe" --lint`**：parse 错误只进 `log.txt` 并弹错误框，
    只查 `traceback.txt` 的自检会假通过。（§17.7）
38. **书签 UI 截图必须走真实 `ShowMenu()`**，`show_screen` 会让 `get_screen()` 为真但画面没渲染；
    `ShowMenu` 阻塞期间 periodic 回调仍跑，正好在那里截图。探针写过的 `persistent` 开关会存盘泄漏，
    每轮要显式设定并复原。（§17.6）
30. **解锁图鉴优先找开发者留的死开关**（`grep` 门控表达式，看 `or XXX_UNLOCKED == 1`），
    比填 persistent 干净；验证要断言整个门控表达式 + 真截图，不是只看 flag（§11.1）。
33. **工具复制过来先跑一遍 `--help` 扫描**（§14 第 0 步）。这一轮 `rpyc_extract.py` 和 `repair_json.py`
    都是 `import sys` 之前就用了 `sys.stdout`，一跑就 `NameError` —— 说明它们在上一次沉淀后**从没被执行过**。

39. **没有死开关就走 B 路线**：反编译游戏自己的图鉴 screen、就地改门控、用 `.rpy` 覆盖归档
    `.rpyc`（§11.3）。但**条目必须由生成器产出**，不要像社区 mod 那样手抄 115 个按钮 ——
    那玩意儿绑死单一版本，游戏一更新就整份作废。
40. **跳过进度进场景前，先查游戏自己有没有"已收集 X/Y"这类计数**：未解锁的 `persistent.x`
    是 `None`，参与算术会崩，要 `== None → False` 归一化（§11.3 第 2 条）。
41. **冷进未硬化场景要补作者的播种行**：`Replay` 会 `clean_stores()`，玩家起的名字会退回
    `define` 默认值。让生成器从硬化场景的 `if _in_replay:` 块里学出 `var = persistent.x`，
    运行时在**回放外**求值后经 `scope=` 注入（§11.4，实测 `Zedtest` vs `Dotty`）。
42. **运行时用 `renpy.has_label()` 防呆、用 `renpy.loadable("...rpyc")` 探测版本**，
    游戏更新后标签搬走时提示而不是崩（§11.3 第 1 条）。

---

## 14. 新项目执行手册（照抄顺序即可）

前提：把 `tools/`（20 个 `.py` + 1 个 harness 模板）和这份 md 一起复制到新游戏根目录，`cd` 到该目录。所有脚本只依赖标准库 + 本机 Python 3，不需要装包。

**第 0 步：拷完工具先做一次 `--help` 扫描**，把"模块顶层就能炸"的问题在开工前一次性暴露：

```bash
for f in tools/*.py; do python "$f" --help >/dev/null 2>&1 || echo "FAIL $f"; done
```

`make_selftest.py` 用的是位置参数、不认 `--help`，它出现在 FAIL 里是正常的（会去 open 一个
叫 `--help` 的文件）。其余每一个都必须过——这一轮就是靠它发现两个新工具在 `import sys`
之前用了 `sys.stdout`，而那类 bug 会让整条流水线在跑了两小时之后才断。

```bash
# 1) 侦察 + 抽取（含"游戏自带译文"自动识别）
python tools/extract.py --game game --out localization/en-zh.json
#   看 localization/extract_report.txt 的三行关键输出：
#     shipped languages : ...      → 有 chinese/zh 就走第 2 步，没有就跳过 denames
#     chosen for reuse  : chinese  → 官方译文被自动接上
#     say ... untranslated=N        → N 才是真正要花钱翻译的量

# 2) 去音译（只在"人名保持原文"这类需求下做）
python tools/denames.py                       # 只生成候选表，不写数据
#   人工过 localization/names_proposed_all.tsv（不过滤版），把漏的写进 localization/names_manual.tsv
python tools/denames.py --apply               # 就地改写，自动备份 en-zh.before_denames.json

# 3) 切批次 + 派工
python tools/dump_groups.py --size 430 --chars 27000
#   每组一个后台 agent：读 localization/glossary.md + groups/group_NN.json → 写 out_NN.json
#   prompt 只给"读这两个文件、写那个文件、不要自检"，见 §8

# 4) 回收 + 生成 + 校验
python tools/apply_trans.py                   # 看 apply_report.txt；rejected/ 里的组要重派
python tools/build_tl.py --lang zh --kinds say --layout zh-first --clean
python tools/qa.py                            # 必须 FAILURES: 0 才算完事

# 5) 游戏内自检（§9.0 的临时 harness），确认 translate_string + 截图后删掉临时文件
rm game/tl/zh/99zz_selftest.rpy game/tl/zh/99zz_selftest.rpyc

# 6) 交付前最后一眼
python tools/uninstall.py --dry-run           # 列出的必须全在你新增的目录里
```

**换项目只需要动这几处**（其余一律不用改）：

| 位置 | 改什么 |
| --- | --- |
| `--lang` | 语言代码。若游戏自带 `chinese`，**必须另起一个名**（`zh`），否则你的 `strings:` 会被官方 id 块压掉（§3.5） |
| `--kinds` | 只译对白用 `say`；要连选择支一起译用 `say,menu`；`uwrap`（HUD/图鉴/系统文案）默认**不要**开，见 §5 |
| `build_tl.py --picker-name/--flag` | 语言菜单里显示的名字、persistent 开关变量名（用项目缩写，如 `cc_bi_off`） |
| `build_tl.py --font-mode` | 游戏自带 CJK 字体 → `--font-ref`；没带 → `--cjk-font` 从系统复制。**引擎版本不确定时用 `tag`**（§6.4） |
| `localization/glossary.md` | 每个游戏的术语、人名表、语域基线，**以及给 agent 的执行契约**（§8.1）——这是唯一需要重写的文本 |
| 图鉴解锁（§11.1/§11.2） | 先 `grep` 出这个游戏的门控表达式和它自己留的总开关名（本作 `EXTRAS_GALLERY_UNLOCKED` / `EXTRAS_REPLAY_UNLOCKED`），再把 `persistent.<缩写>_gallery_unlocked`、按钮文案和 `align` 位置换成这个游戏的；位置必须截图确认不压原 UI |
| `localization/leak_allow.txt` | 本项目**故意**保留拉丁字的词（游戏内标题、品牌、外语原话、纯拟声），让 `align_check` 的 LEAK 归零且豁免本身可审（§13 第 21 条） |
| `localization/names_manual.tsv` | 只在复用官方译文时用到：音译变体，第一次跑完候选表后人工填一次 |
| `localization/route_rules.json` | 只在用户要"路线标记"时用到（§16）。实例含剧透，**不外传**，公开仓只放 `route_rules.template.json` |

> 这张表曾经被我从 §12 的工具契约表粘进来两行三列的内容（`scan_routes.py` / `font_cmap.py`），
> markdown 渲染是坏的。改表的时候注意列数要和表头一致。

**分支判断（决定工作量的唯一变量）**：
- 归档里有官方中文 → 翻译量 = `untranslated` 缺口（本项目 5,439 条，约 20 分钟 agent 时间）。
- 没有官方中文 → 翻译量 = 全部 `say` 条数（按 §15 的 token 基线估算，Sunset Rose 3,966 条约 40 分钟）。
- 字体：归档里已有 CJK 字体 → 零新增文件；没有 → 从系统复制一份 OFL 字体到 `game/tl/zh/fonts/` 再映射。

### 14.1 模式 B：散文本 `.rpy`（无归档）的完整命令序列

判据：`find game -name '*.rpa'` 为空、`game/*.rpy` 能直接读到明文。**仍然不要改源码**，产物照旧落在 `game/tl/<lang>/`。

```bash
# 1) 抽取。目录下有 .rpyc 就用 AST 版（引擎真正加载的是它，正则扫明文会漏说话人）
python tools/rpyc_extract.py --game game --out localization/en-zh.json --reuse
#   只有明文、没有 .rpyc 时才是：python tools/rpy_extract.py --game game --out localization/en-zh.json
#   extract_report.txt 里确认三件事：
#     character vars   : 只列出了真正的说话人变量
#     say statements   : unique N，duplicate-old 应为 0（不为 0 说明有整句重复，已自动去重）
#     然后跑一遍反向核对：源文件里的 say 行是否全部进了表（漏一行 = 少译一行）

# 1b) 如果 game/tl/<官方语言>/*.rpy 是明文（自带官方译文）——先复用再翻译（§3.6）
python tools/tl_reuse.py --tl game/tl/chinese            # 只看报告
python tools/tl_reuse.py --tl game/tl/chinese --apply     # 本项目：18,608 条里 18,544 条直接复用
#   然后 grep '·' localization/en-zh.json 查音译残留，按 §3.5 第 6/7 条手工补 names_manual.tsv

# 2) 翻译。<=500 条主线程直接写；上千条切批派 agent（§8），但**先做一小片再全量**：
#    先只派主线那几个文件，跑通第 3-5 步、亲眼看过截图，再派其余的（省掉一次全量返工）
python tools/dump_groups.py --files "script.rpy,route_intro.rpy" --size 500 --chars 42000
python tools/repair_json.py --in localization/out_11.json --group localization/groups/group_01.json
python tools/apply_trans.py          # 标签/插值/换行守恒预检；后到的 out_9x_*.json 用于覆盖修正
python tools/align_check.py --only-names --names "$(python -c "...")"   # 硬失败必须 0

# 2b) 可选：路线标记（玩家要求"把某条线的选项直接标出来"时才做，见 §16）
python tools/scan_routes.py --rules localization/route_rules.json      # 先看 route_review.txt
python tools/scan_routes.py --rules ... --merge-json                   # 把抽取器没见过的 screen 选项补进真源 JSON
#   把 review 里 INVERTED-POLARITY / UNRESOLVED-CHAIN 的条目人工确认后回填 route_rules.json

# 3) 生成 + 校验
python tools/build_tl.py --lang zh --kinds say --layout zh-first     --marks localization/route_marks.json \
    --font-mode tag --font-ref fonts/NotoSansSC-VariableFont_wght.ttf \
    --text-size <比 gui.text_size 小 1~2 档的值> --flag <项目缩写>_bi_off --clean
#   游戏没自带 CJK 字体时把 --font-ref 换成 --cjk-font "C:/Windows/Fonts/NotoSansSC-VF.ttf"（复制一份进 tl/<lang>/font/）
#   对白框塞不下双语就靠 --text-size 解决；--textbox-height / --window-ypos 不要主动用（§5.2）
python tools/qa.py                   # 必须 FAILURES: 0

# 4) 游戏内自检（§9）：现成 harness，探针从真源 JSON 取
python tools/make_selftest.py localization/en-zh.json mix
#   启动游戏（别用 setsid，见 §9），等 selftest_report.txt 里 hits N/N 和 shots/ 出现
#   截图要亲眼看过：中文出框、名字框、纯拟声单行、豆腐块
#   用完连 .rpyc 一起删：rm game/tl/zh/99zz_selftest.rpy game/tl/zh/99zz_selftest.rpyc
# 5) python tools/uninstall.py --dry-run  # 必须恰好列出你新增的每个文件（含字体）
```

`--font-ref` 与 `--cjk-font` 二选一：游戏已经带了 CJK 字体就用前者（零新增文件），没带才用后者（复制一份进 `tl/zh/font/`）。

模式 B 下 `--kinds say` 就够了：散文本项目的选择支/界面文案本来就不在抽取范围内（抽取器只认 `label` 块里的 say 语句），符合 §0.5 第 2 条"菜单不译"。

---

## 15. 实测基线（用来估工作量和判断异常）

| 指标 | Sunset Rose 0.3（无自带译文） | Midnight Paradise 1.1（有自带官方中文） |
| --- | --- | --- |
| 引擎 | 8.5.2 | 8.4.2 |
| 待译对白 | 3,966 条 / 21.4 万字符 | 59,201 条 / 300 万字符 |
| 实际翻译量 | 全部 3,966 | 缺口 5,439 条 / 25.2 万字符（复用 53,762） |
| 批次 | 每组 ~420 条 | 13 组 × ≤430 条 / ≤27,000 字符 |
| 单组 token | 25–77 万（自检过的组会翻几倍） | 23 万–155 万 |
| 单组耗时 | — | 3.5–7.5 分钟，13 组并发 ≈ 8 分钟 |
| 生成产物 | — | 124 个 `.rpy` / 12MB / 59,201 对 |
| 启动成本 | — | `Loading script` 冷 14s、热 5.5s（原始约 2s） |
| 全程墙钟 | — | 约 80 分钟（含侦察、字体、两轮返工、游戏内验证） |

**模式 B 基线（The Tutor 1.0，2026-10-05，引擎 8.3.7）**：323 条对白 / 3.89 万字符 / 0 条自带译文 → 全部主线程翻译（3 个分片），无 agent 派发；产物 1 个 `script.rpy`（strings 表）+ 1 个 `00zz_bilingual.rpy` + 1 个字体，共 5 个新增文件；`qa.py` 与 `align_check.py` 均 FAILURES 0；游戏内一次启动即出双语，无 traceback。墙钟约 40 分钟，其中 3 次启动自检占了大头（每次 ~1.5 分钟，因为要等过场动画）。

**模式 B + 自带明文官方译文基线（By Justice or Mercy v25，2026-10-05，引擎 8.5.3）**：
18,608 条唯一串 / 18,164 条对白 / 64.9 万字符 → `tl_reuse.py` 复用 **18,544 条（99.65%）**，
真缺口 64 条 / 1,629 字符（其中只有 20 条有实义，其余是拟声、`img:thumbN.png` 这类画廊占位串和 `[mc]~`）；
主线程翻 20 条 + 修 4 条官方译文自身的问题（1 条 `不不不…` 重复 300 多字的破损条目、3 条西方人名音译）
+ 去音译 36 个名字（`names_manual.tsv` 36 行、`denames --apply` 两轮共改写 102 行）。音译变体是**多对一**的：`Rob` 同时被写成 `罗伯` 和 `罗布`，`Alex` 有 `亚历克斯` 和 `艾利克斯`，所以第一遍改完必须再跑一次 `align_check --only-names`，本项目第二轮又抓出 4 个变体。产物 4 个 `.rpy`（18,117 对，含 120 条"无实义只出原文一行"）
+ 0 个新字体（`--font-ref` 用游戏自带的 NotoSansSC），`qa.py` / `align_check.py --only-names` 均硬失败 0，
`uninstall.py --dry-run` 恰好 10 个文件。墙钟约 45 分钟，其中 3 次启动自检 + 一次探针方法学返工（见 §9.0 的 always_shown 假故障）占了一半。

**对白框容量实测（用来判断要不要降字号）**：`gui.text_size 35`、`dialogue_width 1116`、`dialogue_ypos 65`、
`textbox_height 278`、`window ypos 835` → 行距实测 58px，正文起点 900，屏幕 1080 → **只有 3 行可见**；
双语行数分布 2 行 16,262 / 3 行 1,471 / 4 行 303 / ≥5 行 55。
第一版用 `--window-ypos 725` 上移换到 5 行，**用户实玩后否掉**（"很难受玩的，设计者做这个高度是有道理的"），
最终形态是**几何零改动 + `--text-size 30`**：典型对白（中 1 行 + 英 1 行）在原框里余量充足，
≥6 行的 4 条极端长句英文那一半掉出框外——按 §0.5 第 8 条这是可接受结果，中文在上面所以中文必然看得见。

**这条基线用来判断"小项目该花多久"**：散文本 + 几百条对白，正常应该在 1 小时内收工；如果超过，多半是（a）在对白框高度上返工（先读 `style window` 再动手）、或（b）反复重启游戏等过场（改用 §9 的临时 screen 验证布局，不必推进剧情）。

**无官方译文的大项目基线（Milfylicious 2 0.37，2026-10-06，引擎 8.1.2，散文本 + 自带 `.rpyc`）**：
20,543 条待译（say 20,090 / menu 453 / 162 万字符），自带语言只有 es 和 portuguese，**没有任何可复用的中文**。
分两阶段做：先 8 组 2,954 条（主线 + 最短的一条 route）跑通全链路并亲眼看过截图，确认字号与语域后再派 35 组 17,136 条。
产物 8 个 `.rpy`（5.98MB）+ 1 个字体，20,086 对双语，覆盖率 99.98%（剩 4 条纯呻吟，按规则原样输出单行）。
`qa.py` FAILURES 0；`align_check.py` FAILURES 0 / warnings 117（全是语料启发式的名字告警）。
几何按 §5.2：框完全不动，`--text-size 30`（38 降两档），中文出框 0 条、英文出框 0.6%。
热缓存下 `Loading script` 3.81s（未加覆盖层的冷启动是 5.83s，**不同条件不能直接比**，要量对照得两次都热）。
墙钟约 80 分钟，其中 35 组翻译的并发等待约 25 分钟。
token：正常组 **30-60 万/组**，3 个跑偏组 260 / 370 / 630 万，全程约 2,400 万——**跑偏的 3 组占掉六成**，
所以 §8 的 `tool_uses` 反查是这类项目最值钱的一条成本控制。

**8.0.3 + 全量自译 + 图鉴解锁基线（Carnal Contract Season One，2026-10-06）**：
13,415 条唯一串（**say 13,090 条 / 48.6 万字符**，menu 325 条按口径不译），散文本带 `.rpyc`，
`game/tl/` 只有 `None/common.rpym` → **没有任何可复用译文**，游戏只带 4 个拉丁字体（`ade1.ttf` 对白、
`toxigenesis_bd.otf` 名字框、`SourceSansPro` 界面、`Lato` 按钮）。

- **两阶段派工**：阶段 1 只翻 `chapter01 + tutorials`（1,512 条 / 4 组）跑通全链路并亲眼看过截图；
  阶段 2 剩余 11,587 条切 **22 组**（`--size 550 --chars 35000`，count 是绑定约束，550 条平均只有 2 万字符）。
- **token**：阶段 1 用普通措辞，4 组里 **2 组跑偏**（17 / 12 次工具调用，170 / 164 万 token）。
  阶段 2 换成"恰好三次工具调用"的写法（§8.1），22 组里 **21 组落在 3-6 次 / 18-87 万**，
  只有 1 组因为自己写出非法 JSON 被迫回修，跑到 14 次 / 297 万。全程约 **1,100 万 token**。
- **墙钟**：阶段 1 约 9 分钟（4 组并发），阶段 2 约 12 分钟（受 20 并发上限，22 组分两波）。
- **回收**：`apply_trans` 共写入 13,004 条，**rejected 86 条全是 `no-cjk`**（纯呻吟/纯人名喊话，
  按规则原样输出英文，属正确行为）；另有 1 条 `tag-mismatch`（agent 把 `X is just being X` 意译成
  一句中文，标签少了一半）→ 拒收后手改，这是标签守恒闸门**真正拦下来**的一例。
- **风格闸门**：`style_audit --apply` 三轮共改写 467 条（括号全角 317、省略号、`——`、英文所有格 84），
  手工改 47 条（`{b}` 里没译的强调词 35 + `daddy` 2 + `*whispers*` 5 + 零散 5）。
  最终 `latin-inside-bold` 剩 6 条，其中 5 条是**故意**的（`MILF` ×4、游戏内节目名 `WOULD YOU RATHER!`），
  已进 `TERM_OK` 白名单。
- **校验**：`qa.py` FAILURES 0；`align_check --only-names` 硬失败 0 / 告警 0
  （**注意**：本作的 `Character` 显示名里混着 `Man` / `Dad` / `Waiter` / `Master` 这类普通名词，
  照抄进 `--names` 会造出 42 条假 MISSING-NAME，见 §13 第 16 条的严重度分档）。
- **几何零改动**：`gui.text_size 30`、`dialogue_width 1116`、`dialogue_ypos 75`、`textbox_height 208`
  → 正文可视约 133px ≈ 3 行。`textbox_fit.py` 全表实测：**中文出框 0 条（0.0%）**，
  英文参考行出框 114 条（0.9%），所以**既没动框也没降字号**（30 是原版值）。
  最长那条 188 字符实测中文 2 行完整可读、英文尾部压到快捷菜单那一行 —— 按 §0.5 第 8 条这就是可接受终态。
- **产物**：10 个 `.rpy`（`tl/zh/scripts/` 按章节镜像）+ `00zz_bilingual.rpy` + 1 个字体，
  `game/tl/zh` 共 20MB（其中字体 17MB）。`uninstall.py --dry-run` 恰好 37 个文件（含两个 `game/cc_*.rpy` 及其 `.rpyc`）。
- **启动成本**：`Loading script` 冷 **2.70s**（首次要把 10 个 `.rpy` 编成 `.rpyc`），之后热 **0.90–0.92s**。
  对照"移除覆盖层"的一次冷测是 1.10s —— **单次测量、方差主导，不能当基线**；要量冷/冷对照得两次都清缓存。
- **图鉴解锁**（§11.1/§11.2）：163 处画廊门 + 30 处回放门，全部靠两个从未赋值的死开关；
  新增 1 个 `game/ccg_unlock.rpy`，不写 `persistent.gallery`、不动存档。
  按 §0.5 第 10 条做成**游戏内按钮**（右上，绿=全解锁 / 粉=按进度，状态进 `persistent`），
  验证走的是按钮真实 action 链：`flag 1→0→1` 且**第二张截图的文案确实跟着翻了**。
  实测 `Replay()` 从没通关状态能直接播出动画，画廊页 193 张缩略图全彩。
  踩到的新坑：`ToggleField` / `Function` 不在 `renpy.exports` 上（8.0.3 `AttributeError`），
  探针里得用 `renpy.store.*`；UI 字体没有 CJK，按钮标签不包 `{font=}` 就是豆腐块。

**路线书签基线（Carnal Contract Season One，2026-10-06，引擎 8.0.3）**：
392 个 label → 扫描器报出 23 个双守卫 / 7 个仅播种 / 17 个仅停车守卫；
按放宽词表 + 排除表初筛出 16 条候选 → 3 个并发判定 agent（每组 5-6 条，3-6 次调用 / 19-40 万 token）
→ 4 yes / 6 unsure / 8 no → 10 条书签，全部依赖停车闸（**没有一条是作者做过回放守卫的**）。
picks 自动推导出 2 处（ch8 `menu:7055` → #1 Submissive.；ch2 `menu:2017` → #1）。
墙钟：扫描+初筛约 3 分钟，判定约 5 分钟（并发），停车闸/自动选/UI 三轮实机验证约 25 分钟，
其中两次返工都是被 §17.7 的坑拖的（screen 语言续行、`[f()]` 插值）。
实测结论：本作的这类内容总量本来就少（10 条，其中 6 条待确认），**"书签能不能做出来"和
"这款游戏值不值得做"是两个独立判断** —— 扫描器的 `safe cold entry` 计数和候选数是先验指标，
开工前先跑一次扫描器再决定。

**用来判断"哪里不对"的红线**：
- `extract` 的 say 条数比 `.rpyc` 源文件数×合理对白量高出一个数量级 → 大概率没排除 `tl/**`（§3）。
- 单组 token 超过 100 万 → agent 在自我校验，prompt 里把"禁止自检"写得更硬（§8）。
- `qa.py` 报 `dup` → 生成器去重跨 kind 没做好，游戏会启动即崩（§4）。
- `qa.py` 报 `ghost` → `old` 和源串不逐字节相等，多半是转义顺序或 `\n` 处理错（§4），这类条目会静默不生效。
- 截图满屏豆腐块 → 字体三层挂载缺一层，尤其 `translate <lang> style`（§6.1）。


---

## 16. 路线标记：把玩家想走的那条线的选项，在游戏里直接标出来

> 需求来源：用户玩这些游戏时不想记攻略，他要的是"看到这个标记就点它"。

### 16.1 为什么用覆盖层做，而不是给玩家写一份文字攻略

标记本身就是一次**字符串替换**：`old = 选项原文`，`new = 徽章 + 选项原文`。所以它天然满足本手册的全部约束——
纯新增、走 `translate <lang> strings:`、可 `uninstall.py` 一键删、不改任何原文件、不动任何几何（§5.2）。
**选项文字保持英文原样**，只在前面加一段带 `{font=}` 的徽章，所以不违反"菜单不译"的口径。

### 16.2 判定从哪来：读脚本，不读译文

`tools/scan_routes.py` 要解析两套**完全不同**的语法，这是最容易写错的地方：

1. **`menu:` 语句**：`"{color=#00b4d8}Let her win (Femdom)":` 开一项，它的 body 是缩进更深的后续行，
   直到下一个同缩进项或 dedent。从 body 里取 `$ var += N`、`jump/call LABEL`、`Jump("LABEL")`；
   body 里出现过 `if/elif` 的降一档置信度。
   注意 `{color=...}` **不带闭合**也是合法选项文字，`en` 必须逐字节照抄，否则和真源 JSON 对不上（`qa.py` 报 ghost）。
2. **`screen choiceN()`**（很多发行版把关键分岔做成图片按钮屏）：
   `if _preferences.language is None:` 那一支是**把英文烧在图里**的 `imagebutton auto "choice9_button1_%s"`，整支丢掉；
   只有 `else:` 支是 `fixed:` → `imagebutton`(+`action ... Jump("X")`) + `text _("...")` + `color "#..."`。
   **按 `fixed:` 容器分组配对**，不能按行序（有的屏是 `text` 在前、`imagebutton` 在后）。
   覆盖层把语言设成 `zh` 之后玩家看到的正是 else 支，所以这一支才是可标记的。
   正则坑：定义行是 `screen choice1():`，带括号，`^screen\s+(\w+)\s*:` 匹配不到。

**抽取器会漏掉第 2 类**：`rpy_extract.py` 只收 `label` 上下文里的 say 语句，`text _("...")` 既不被 `SAY_RE` 认（`_(` 挡在引号前），也不在 label 下。
所以 `scan_routes.py --merge-json` 负责把这些串以 `kind:"menu"`、`zh:""` 追加进真源 JSON
（`zh` 留空 → 译文层不输出它们；但 `qa.py` 的 ghost 检查要求 `old` 必须在 JSON 里，所以**必须先补再建**）。
追加时**只能 append 新 id，绝不重跑抽取**——重跑会重排顺序 id，让已回收的译文分片全部错位（§8 的记账方式就是按 id）。

### 16.3 规则文件：能自动推的自动推，推不出来的一律进 review

`route_rules.json` + `classify()` 的优先级（顺序本身就是判据，写错顺序就判反）：

1. **扣分检测**：body 里有 `$ *Favor -= N` / `*publicOpinion -= N` → `favor_loss`。
2. **声明的极性反转优先于轴标签**：`characters.alex.she_leads_var = "alexDom"` → 涨 alexDom 标"她主导"。
   这条必须排在轴标签**之前**，否则 `Dominance` 轴会先把 alexDom 判成"你主导"，正好判反。
3. **轴标签**：`axis_ui_labels` 用正则去**读游戏自己的关系菜单文本**。例：
   `_(" [mc]'s Submission: [alexLove]")` → `alexLove` 是服从轴 → 涨它标"她主导"；
   `_("Dominance: [naomiDom]")` → 标"你主导"。
   这是跨项目最值钱的一条：**游戏往往会亲口告诉你这个数值叫什么**，不必猜变量名。
   本项目就是靠它自动发现"只有 Alex / Jessica / Naomi 三人把 Love 轴改名叫 Submission"。
4. **love 轴承载女S变体的角色**（`love_is_she_leads`）：本项目 hana / emma——她们的女S内容不在独立数值轴上，
   而在 `if xLove >= xDom and femdomDisabled == 0` 那个分支里（`scenes.rpy:7828`、`script.rpy:4905`）。
5. **选项文字自报**（`(Femdom)`）、**跳转 label 词表**（`femdom`/`submi` 必须**先于** `dom`/`dominate` 判，
   否则 `femdom` 被 `dom` 吃掉）、**flag 桥接**（`wonAgainstAlex = 1` → 若干行后 `day14specialcondition` → `day14AlexFemdom`）。

两条实测必须加的护栏：

- **`$ xDom = 99` 这类是画廊/开发跳板，不是玩家选项**：按 `abs(delta) >= 10` 剔除，否则会标出一堆假分岔（本项目 20 条）。
- **颜色不能单独当判据**。本游戏蓝=涨 Love、粉=涨 Domination 全局成立（187 个带色选项验证），
  但"粉对 Alex 反而是女S"，所以颜色推不出路线，只能作低置信度线索进 review。

`route_review.txt` 逐行输出 `mark | 置信度 | file:line | 选项 | 证据`，并把
`INVERTED-POLARITY`、`UNRESOLVED-CHAIN`（flag 桥接超过一跳）、`BROAD-MARK`（撞串站点数 >3）单列出来给人回填。
**判不出来的东西工具一律不许猜**——猜错的标记比没有标记更糟，因为玩家会照着点。

### 16.4 撞串与 `old` 唯一性（这里处理不好会直接崩游戏）

`strings:` 表按**英文内容全局匹配**，于是：

- 一个串在 11 处当选项（`Yes`），标一次 11 处全变。用户口径是"宁误不漏"，所以默认全标，但站点数必须写进 review。
- **同一个 `old` 在 `tl/<lang>/**` 出现两次，`StringTranslator.add()` 直接 raise，启动即崩**（§4）。
  所以标记层和译文层**必须由同一个写者输出**（`build_tl.py --marks`，共用 `picked[en]` 去重），
  并在生成时跳过"已被 say 层输出过"的串——本项目有 4 条 `Yes` / `No` / `Keep going` / `You should go` 同时是 say 和 menu。
  将来若用户改口径要译选项（`--kinds say,menu`），徽章和译文要在**同一条 `new`** 里合成，不能各写一条。

### 16.5 徽章字形必须先过 cmap 闸门

**本项目返工最多的一处**：用户选的 `🚩`(U+1F6A9) 和备选 `⚑`(U+2691) 在游戏自带的
`NotoSansSC-VariableFont_wght.ttf` 里**都没有**；而选项实际用的 UI 字体 `LEMONMILK` 连 `⚠` 和中文都没有。
Ren'Py 没有逐字回退（§6.1），所以直接写就是豆腐块——第一版截图实测就是这样翻车的。
可用的有 `★ ☆ ⚠ ▲ △ ● ○ ◆ → 【】 「」`，最终定 `★她主导` / `☆你主导` / `⚠掉好感`，
并且**整段徽章包 `{font=}`**（不包的话连"她主导"三个字都是豆腐）。

`tools/font_cmap.py` 是纯 stdlib 的 `cmap` 读取器，两个坑单独记：

- fmt4 中 `idRangeOffset == 0` 时**delta 的结果是 glyph id，不是码位**，而 glyph id 0 = `.notdef`。
  把 glyph id 当码位塞进集合，会把手旗符号报成"有"——我第一版就是这么误判、然后被截图打脸的。
- fmt12 的三元组是 `(startCode, endCode, startGlyphID)`，**只有前两个是码位**；
  拿 `startGlyphID` 去展开区间同样造成大面积假"有"。
- 变量字体要优先挑 `(3,10)` 的 fmt12 子表，其次 `(3,1)` fmt4；只读第一个子表就下结论不安全。

`qa.py --marks ... --badge-font <ttf>` 把它变成硬门禁：徽章前缀每个字符必须在字体里存在；
每条标记的 `new` 必须同时含徽章、含原 `old`、含 `{font=`（缺哪个分别报 `badge-lost` / `badge-ate-en` / `glyph`）。

### 16.6 标记的自检（不靠手点）

`renpy.display_menu([(caption, None), ...], interact=False)` 能渲染**真实的选择屏**且不等点击
（`renpy/exports/menuexports.py:202` 的 `interact` 参数），配 `renpy.pause(0.6)` + `renpy.screenshot()` 就是确定性截图。
选项串一律从 `route_marks.json` 程序化取（§9.0 的教训）。断言三件事：
`translate_string(en)` 含徽章、含原 `en`、含 `{font=`。临时 harness 用完连 `.rpyc` 一起删。

### 16.7 发布边界

`route_rules.json` 的**实例**含剧透（label 名、变量名、`why` 字段逐字引用游戏文本），算衍生内容：
公开仓只放 `localization/route_rules.template.json`（字段 + `$doc` + 空值），
实例与 `route_marks.json` / `route_review.txt` 一律 gitignore，和 `en-zh.json` 同级处理。

---

## 17. 路线书签：把玩家想看的那条线的**场景**直接列成可点入口

> 需求来源（用户 2026-10-06）："我喜欢男M女S情节，在游戏里单独开一个游玩项，把所有这类情节集中进去，
> 一口气玩完，不用浪费时间过其他剧情；而且**不是**只玩作者精选的 CG，而是真正进原游戏内部，
> 过对话、剧情、选项、动画 —— 相当于往游戏里插一堆书签。"

### 17.1 它和 §16 路线标记是两件事

| | §16 路线标记 | §17 路线书签 |
| --- | --- | --- |
| 解决的问题 | 玩家**正在玩**，需要知道下一步该选哪个 | 玩家**不想玩别的**，要直接跳到目标场景 |
| 单位 | 一个选项字符串（`strings:` 替换） | 一个 `label`（引擎的跳转目标） |
| 判定依据 | 选项 body 里改了哪个数值 | 场景**内容**（数值状态常常根本不存在） |
| 覆盖范围 | 只有 menu 站点 | 全部场景，包括作者没做进画廊的 |

两者共用一份判定纪律（**判不出来一律进 review，不许猜**），但不共用代码路径。

### 17.2 引擎已经把最难的部分做完了：`Replay(label, scope=…, locked=False)`

8.0.3 的链路（行号都实测过）：
`Replay.__call__`（`renpy/common/00action_other.rpy:426-443`）→ `renpy.game.call_replay`
（`renpy/game.py:362-419`）：

```python
old_log = renpy.game.log; renpy.game.log = renpy.python.RollbackLog()
sb = renpy.python.StoreBackup(); renpy.python.clean_stores()   # store 回到 init 后的干净值
context = renpy.execution.Context(True); contexts.append(context)
renpy.exports.execute_default_statement()                      # default 全部重放
for k, v in config.replay_scope.items(): setattr(store, k, v)
for k, v in scope.items(): setattr(store, k, v)                # ← 逐场景注入前置状态
store._in_replay = label
context.goto_label("_start_replay"); run_context(False)
finally: contexts.pop(); renpy.game.log = old_log; sb.restore()  # ← 退出时全量还原
```

`_start_replay`（`renpy/common/00start.rpy:158-167`）会 `call _start_store`（**跑
`config.start_callbacks`**，所以覆盖层的语言/解锁钩子在回放里同样生效）、`scene black`、
`_init_language()`、`block_rollback(purge=True)`，最后 `jump expression _in_replay`。
回放期间 autosave 被引擎主动抑制（`renpy/loadsave.py:540-542`）。

**结论**：用户要的"自动快照、退出不影响主线"不用自己实现，`Replay` 就是它。
`scope` 是官方给的状态播种口 —— 别自己造快照层。

### 17.3 停车闸：这一节是本功能真正的工程量

`Replay` 是 `jump` 进目标 label，不是 `call`，所以**目标 label 必须自己知道什么时候停**。
作者的写法是在场景末尾加：

```rpy
    if _in_replay:
        return
    jump e1scene01_continue      # 正常游玩才往下走
```

实测 Carnal Contract：392 个 label 里只有 **23 个**头尾守卫齐全，
**而符合本路线的 16 条候选里，一条都没有守卫** —— 作者做进画廊的场景和他自己的敏感内容不重合。
不加停车闸的话，`e8_hotel_with_diane_submissive_sex` 会在 `chapter08.rpy:7613`
`jump` 到后续剧情，漏出约 600 行无关内容。

8.0.3 能用的钩子只有一处，而且**它不能改流程**：`config.statement_callbacks`
（`renpy/config.py:526-528`）由 `statement_name()`（`renpy/ast.py:41-47`）在每条语句前调用，
**只传一个名字字符串、返回值被丢弃**。所以不能靠回调"返回一个新节点"来改道。

可用的取巧点：`renpy/execution.py:524` 在 `node.execute()`（:581）**之前**就把
`self.current = node.name` 设好了，而每个节点都以名字索引在 `renpy.game.script.namemap`
（`renpy/script.py:490`，查表用 `lookup` :908-929）。于是回调里能拿回**正在执行的那个节点**
及其 `(filename, linenumber)`，判断它是否还在本场景范围内，越界就
`renpy.end_replay()`（`renpy/exports.py:3556-3566` → `raise EndReplay`，
在 `CONTROL_EXCEPTIONS` 里，`call_replay` 的 `except EndReplay` 干净接住并 restore）。

```rpy
init 10000 python:
    def cc_bm_stop_guard(name):
        ranges = getattr(renpy.store, "cc_bm_ranges", None)     # 见下面的坑
        if not ranges: return
        node = renpy.game.script.lookup(renpy.game.context().current)
        fn, ln = getattr(node, "filename", None), getattr(node, "linenumber", None)
        if not renpy.store.cc_bm_armed:
            if _in(fn, ln): renpy.store.cc_bm_armed = True       # 落进本场景才开始盯
            return
        if not _in(fn, ln) or renpy.session["cc_bm_stmts"] > 40000:
            renpy.session["cc_bm_stop"] = "%s:%d" % (fn, ln)
            renpy.store.cc_bm_ranges = None
            renpy.end_replay()
    config.statement_callbacks.append(cc_bm_stop_guard)
```

四个必须记住的点：

1. **允许范围通过 `Replay(scope={...})` 注入 store**，这样引擎退出回放时 `sb.restore()`
   自动把它抹掉 —— 不需要自己解除武装，也不会漏进正常游玩。反过来，**跨测试/跨场景的
   "我现在在哪个书签里"这类状态要放 `renpy.session`**，因为 store 写入会在退出时被抹掉。
2. **`default cc_bm_ranges = None` 在 init 阶段还不存在**，而 `statement_callbacks` 在 init
   期间就会被调用（`init python:` 本身就是一条语句）。所以回调里**必须 `getattr` 兜底**，
   否则 `AttributeError: 'StoreModule' object has no attribute …`，游戏启动即崩。
   这是本项目最贵的一个坑：写的时候完全看不出来。
3. **要等"落进本场景"再武装**：`_start_replay` 在跳到目标之前会先跑引擎自己的语句，
   一上来就盯会在第一条就 end_replay。
4. **加一条语句计数熔断**（本项目 40000）：范围写错时最坏结果应该是"这场提前结束"，
   而不是"把整局游戏在书签里跑完"。

已知误杀形态：**合法的场景内绕行**会跳出区间。实证 `e8_hotel_with_diane` 在 7055 的 menu
分叉到 7062 / 7715，两个目标都在它自己的 `[6728,7062)` 之外。
对策：书签打在**分支 label** 上，或让规则文件支持 `extend` 白名单；
扫描器要把 `escapes`（区间外跳转）报出来，不许静默。

### 17.4 自动选那条：唯一切点是 store 里的 `menu` 名字

链路：`ast.Menu.execute`（`renpy/ast.py:1903`）→ `renpy.exports.menu`（`exports.py:916`）
→ `exports.py:1010` 处 **`rv = renpy.store.menu(new_items)`** —— 它在调用时才解析 store 名字，
store 绑定见 `renpy/defaultstore.py:357`。所以：

- ✅ patch `renpy.store.menu`：唯一有效切点。
- ❌ patch `renpy.exports.display_menu`：**无效**，名字已经绑定了。
- `init 10000` 的 patch 能活过 `clean_stores()`（干净基线在 init 全部跑完后才拍，
  `renpy/main.py:619`）。

选中之后不要自己伪造返回值，用引擎自己的自动选择通路
`renpy.ui.pausebehavior(0.4, value)`（先例 `exports.py:1150-1153`，
`PauseBehavior.event()` 返回 `self.result`，见 `renpy/display/behavior.py:505-543`），
它成为这次 `renpy.ui.interact` 的返回值 —— chosen 标记、`log("Player chose:")` 全部保留。

**`renpy.display_menu(..., interact=False)` 不能用来自动选**：它返回 `None`
（`exports.py:1248`），`Menu.execute` 拿到 `None` 会 `next_node(self.next)` **静默跳过选择**。
§16.6 用它只是"渲染真实选择屏截图"，那个用途仍然成立，别混用。

**判不出方向时不要猜**：直接落回 `_cc_bm_real_menu(items)` 把真菜单弹给玩家
（用户口径"停下来问我"）。这条要测：把开关关掉跑一遍，断言自动选**没有**发生。

picks（每个 menu 该选第几项）离线算，运行时按 `文件:行号` 查 ——
**不要去匹配选项字符串**，因为双语覆盖层已经把 caption 变成"中文\n英文"了。
推导方法：对规则文件里每一对 `she_leads` / `he_leads`，找一个它的两个选项分别跳到这两个
label 的 menu，取跳向 `she_leads` 的那个下标。找不到就进 review，不猜。

### 17.5 判定纪律：内容优先于名字，且文本边界要自己验

- **label 名会骗人。** 本项目的 BJJ 分岔里，`mc_on_top_triangle` 实际是女压男，
  名字中性的 `n_on_top_triangle` 反而是男压女。判反一次就会把整条书签排错，
  还会把自动选指到相反分支。规则文件里专门放一个 `content_over_name` 字段记这种反例。
- **不要用成就名/画廊 id 判定。** 它们是发行商的 sanitized 标签
  （`ach_e7_save_becky = "Save Becky from a kidnapper."`），一条 dom/sub 都没有，
  只能当旁证。
- **区分"剧情上的男性无力"和"D/s"**：绑架、被捕、越狱、被下药全部要排除，
  否则清单会被灌水。
- **纯选择节点**（整个 label 只到 menu 为止）算 `unsure` 进列表，不要直接丢。
- **切给判定 agent 的场景文本必须按"全部 label"划边界**。本项目第一版按"全部候选"划，
  于是一条场景的文本越界吃到后面好几个 label 并被腰斩，两个 agent 独立报
  "文本不完整/越界"，那一批判定全部作废重跑。判据：切完打一行每场景尾行，
  看是不是停在自己的边界上。
- 判定 agent 的契约照抄 §8.1（恰好三次调用、回复一行），但**规则文件里要留
  `note` 字段**，否则"换向点在哪一句"这种信息没地方放，agent 会挤进 `reason`。
  `reversed_midway` 要写 JSON 布尔，写成字符串 `"false"` 在下游是真值。

### 17.6 验证：三个对照测试，一个都不能省

合成鼠标点击送不进 SDL（§9.3），所以**在探针里直接调 `Replay` 那个 action 对象**，
或调书签自己的 `cc_bm_open(entry)`：

1. **极小范围**：给一个 `[line, line+2)` 的假范围 → 断言 `session["cc_bm_stop"]` 落在
   紧接着的那一行（证明闸会停），并且退出后 `ranges is None`、`armed is False`
   （证明引擎自动解除武装，不会漏进正常游玩）。
2. **真实范围**：挑一条**不含 menu** 的场景（含 menu 的会停下来等点击，探针就挂住）→
   断言 stop 正好落在 `range_end`（证明不早停也不晚停），并断言进/出前后 store 变量一致。
3. **自动选开关联动**：自动开 → 断言 `session["cc_bm_autopick"] == "<menu 位置> -> #N"`
   且随后停在跳入的下条场景起点；自动关 → 断言 `cc_bm_autopick` 为 `None`（菜单留给了玩家）。

UI 截图必须走**真实路径** `ShowMenu("…")()`。`renpy.show_screen(...)` 会让
`get_screen()` 返回真但画面根本没渲染出来（本项目实测截到全黑/主菜单），
是 §9.0 那类假通过的又一个变体。`ShowMenu` 会阻塞在交互里 —— 这正好：
阻塞期间 periodic 回调仍然跑，在回调里 `renpy.screenshot()` 就是真画面。

**探针会污染 persistent**：项目里 `persistent.cc_bm_auto = False` 这类写入会随
`renpy.quit(save=True)` 存下来，下一轮测试的初始状态就被改了（本项目因此把"自动开"的
测试跑成了"自动关"）。测试脚本要**显式设定**它依赖的每个开关，并在结尾复原。

### 17.7 这一轮踩到的其它坑

- **parse 错误看 `log.txt`，不是 `traceback.txt`**。screen 语言里写 `… \` 续行会报
  `expected a keyword argument, colon, or end of line`，只进 log.txt 并弹错误框；
  只查 traceback.txt 的自检会**假通过**（本项目就这么被骗过一次，"boots clean"是假的）。
- **`<exe> --lint` 能在不开窗口的情况下抓出 parse 错误**，比"启动 + 查文件"快且准，
  适合每轮改完 `.rpy` 就跑。
- **`[f()]` 插值在 8.0.3 不支持**：Ren'Py 把 `[...]` 当名字/下标查，
  报 `NameError: Name 'cc_bm_auto_label()' is not defined`。要么先算好字符串再
  `("%s" % value)` 拼，要么 `[dict['key']]` 这种简单取值。
- **`Menu.items` 的第二项是条件字符串，不是分支块**（实测 `('Dominant.', 'True')`），
  选项体靠 `next` 链平铺在语句表里。所以从 AST 往下找 jump 一定找不到，
  推 picks 要回去读 `.rpy` 文本。
- 改完 `.rpy` 后 lint 仍报同一行的话，先删掉它的 `.rpyc` 再看（陈旧字节码会骗人）。

### 17.8 发布边界

`bookmark_rules.json` 的**实例**含剧透（label 名、场景内容摘要、逐字证据），算衍生内容：
公开仓只放 `localization/bookmark_rules.template.json`；实例与 `scenes.json` /
`bookmark_groups/` / `verdicts_*.json` / `bookmark_titles.json` / `bookmark_review.txt`
一律 gitignore，和 `en-zh.json` 同级处理。`game/cc_bookmarks.rpy` 与
`game/cc_bookmark_data.rpy` 是**产物**，也不进公开仓。
