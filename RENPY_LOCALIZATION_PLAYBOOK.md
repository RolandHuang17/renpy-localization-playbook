# Ren'Py 发行版汉化 / 本地化施工手册

> 面向执行者（人或编码 agent）的可复制流程。适用于 **Ren'Py 官方发行的 PC/zip 版游戏**（含打包脚本、无源码）。
> **默认需求全在 §0.5**——只丢这份 md 时那 7 条就是需求，不用等补充说明。**要开工请直接看 §14「新项目执行手册」**（A/B 两条分支的命令顺序 + 换项目要改的参数），§15 是可用来估工时和判断异常的真实基线，其余章节是依据和坑。
> 本文件由 Sunset Rose 0.3 汉化任务（2026-10-04，3966 条 / 21.4 万字符）实测沉淀，在 Midnight Paradise 1.1 任务（2026-10-04，**59,201 条对白 / 300 万字符**，其中 53,762 条直接复用官方译文）上复验与修正，又在 The Tutor 1.0 任务（2026-10-05，**323 条对白 / 3.9 万字符，散文本 `.rpy` 无归档**）上补齐了"小项目 + 固定高度对白框"这条分支，再在 By Justice or Mercy v25（2026-10-05，**散文本 + 自带明文官方中文：18,164 条对白，复用 99.65%**）上补齐了模式 B 的译文复用（`tl_reuse.py`）、`--font-ref`、`--window-style/--window-ypos` 与 §9.0 的探针方法学。
> 引擎结论在 Ren'Py **8.5.3 / 8.5.2 / 8.4.2 / 8.3.7** 上都验证过；标注版本相关的条目换版本需复验。
> 配套工具集（11 个纯标准库 Python 文件，可直接复制）见 §12；参考实现留在 Midnight Paradise（归档型）、The Tutor（散文本型）与 By Justice or Mercy（散文本 + 自带明文官方译文型）三个项目的 `tools/` 下。

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

## 0. 先判断适用性

按这个顺序看目录，决定走哪条路：

| 观察 | 结论 |
| --- | --- |
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

**但先读 `screen say` 再决定改哪个样式（By Justice or Mercy v25 踩到的修正）**：模板的 `window:` 走 `say_window`，
可很多发行版把窗口写死成 `style "window"` / `"window1"`（按 `persistent.color` 二选一）。这种情况下面这块
`translate <lang> style say_window` **完全无效**。更麻烦的是背景若写在 screen 里
（`background Image(im.Alpha("gui/textbox.png", l_alpha))`），样式层的 `background Frame(...)` 也压不过它——
screen 属性优先级高于样式，于是"增高 + 换 Frame"这条主路整个走不通。两个新开关：

- `--window-style window,window1`：把样式块发到游戏真正使用的那个样式名上（默认 `say_window`，别照抄）。
- `--window-ypos <绝对值>`：**上移而不是增高**，美术零变形、也不需要换背景。
  本项目实测：`style window` 是 `xpos 130 / ypos 835 / ysize 278`，屏幕 1080 高，正文从 `ypos + dialogue_ypos = 900` 起排，
  行距实测 58px → **只有 3 行可见**，双语长句必然掉出屏幕底边（原版单英文的长句本来就已经掉出去了）。
  `ypos` 提到 725 后正文起点 790 → 容 5 行，覆盖 99.97% 的条目（≥6 行仅 4 条），
  顺带把原本超出屏幕 33px 的对白框美术整个拉回画面内。
  选值方法不变：先按上面的公式算全表行数分布，再按"要容几行"反推 `ypos ≤ 屏高 - 行数*行距 - dialogue_ypos`。

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
- 环境变量 `RENPY_LANGUAGE` 优先级最高（`00start.rpy` 的 `_init_language`），可做零逻辑的启动脚本开关。
- 提前设 `default_language` 还有额外收益：游戏在 `init` 阶段用 `_()` 求值的 `define` 数据（目标标题、事件描述）也会跟着翻译。

---

## 8. 批量翻译的工程做法

- **批次要大**（本项目每组 ~420 条），小批次的固定开销会把 token 吃掉一个数量级：7 条的批次实测 30 万 token，420 条的批次 25–77 万。Midnight Paradise 缺口 5,439 条切成 13 组（每组 ≤430 条 / ≤27,000 字符），单组实测 23 万–155 万 token、3.5–7.5 分钟，**13 组后台并发一次跑完**。
- **并发用后台 agent**（`run_in_background`），主线程同时做去音译、QA、构建，不空等。
- **prompt 要精简并明确禁止自检**：写死"不要写校验脚本、不要读真源 JSON、一次读完一次写完"。允许 agent 自我校验会让 token 翻几倍（第 11 组自己跑了校验，用到 155 万 token，是均值 2 倍）。
- 每个 agent 只喂：术语表 + 该组 `{id, who, file, line, en}`；只回 `{id: 译文}`，不输出英文、不解释。
- 给 agent 的上下文顺序：同一 `file` 内按 `line` 升序＝剧情发生顺序，必须连读，否则代词/时态/称呼全乱。
- 术语表要显式列出：说话人变量→显示名、`[...]`/`{...}` 必须原样保留、换行处数保持、重复英文串必须同译、露骨内容按原文语气直译（不写清"这是用户自有游戏的虚构文本本地化"，模型会回避）。
- **人名/专有名词按需求写死**：本项目的规则是"人名一律保持英文原样、不音译"，术语表里要给出正反例（`我和 Kyle 约好了` ✅ / `我和凯尔约好了` ❌），并说明亲属称谓例外（Mom→妈妈）。
- 回收侧的校验器要能容忍"合法的非译文"：纯拟声、纯人名行（`Isabel?! Connor?!`）译完仍不含 CJK，`no-cjk` 判定要先看原文有没有可译的词，否则会误退一批（本项目首跑退了 2 条，都是这种）。
- 进度用"真源 JSON 里 zh 非空计数"记账，天然可断点续跑（生成器只输出已译条目，未译自动保持原文）。

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
         $ renpy.game.preferences.auto_forward = True
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
1. **`RENPY_AUTO_LOAD=<存档名>` 环境变量**：启动即载入存档，直接进真实游戏界面。最有用的一招（前提是 `game/saves/` 里有存档；全新发行包通常没有）。
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

## 11. 回滚与可逆性

- 全部产物是新增文件：`game/tl/<lang>/**`、一个挂载用 `.rpy`、一个字体。卸载 = 删这几样。
- 提供 `tools/uninstall.py`：删新增文件 + 从 `localization/backup/` 还原任何被替换过的原文件，并写一份操作日志。
- 永远不改：`*.rpa`、`renpy/`、`game/saves/`。

---

## 12. 文件契约（复制到新项目时的最小工具集）

| 文件 | 职责 | 输入 → 输出 |
| --- | --- | --- |
| `tools/rpautil.py` | RPA3 索引 / RPC2 slot / stub unpickler / AST 遍历，其余工具的公共底座 | — |
| `tools/extract.py` | 解析全部 rpa+rpyc，抽源文本待译串，**同时**按 identifier 连接归档里自带的各语言译文并多数表决 | `game/*.rpa` → `en-zh.json` + `speakers.json` + `extract_report.txt` |
| `tools/denames.py` | 复用官方译文时把音译人名还原成原文（判别式对齐 + 音译字闸门 + 人工补充表 + 所有格变体 + 最长优先） | JSON → 就地改写 + `names_proposed.tsv`（不过滤版供人工复核） |
| `tools/dump_groups.py` | 把未译条目按序切成大组 | JSON → `localization/groups/group_NN.json` |
| `tools/apply_trans.py` | 合并 agent 回传的译文分片，做标签/插值/换行守恒预检，拒绝项进 `rejected/` 保留原文便于复跑 | `out_NN.json` → 写回真源 JSON |
| `tools/build_tl.py` | 生成 `tl` 文件 + 语言/字体/断行装配文件；`--layout`（zh-first / en-first / zh-only）、`--kinds`、`--clean`、`--limit`（冒烟测试）；`--font-mode map\|tag` + `--cjk-font`（复制字体）或 `--font-ref`（**引用游戏已自带的路径，零新增文件**）；`--window-style`（窗口样式真名）+ `--window-ypos`（固定高度框上移）；自动扫描归档内已有 CJK 字体并按字重建映射 | JSON → `game/tl/<lang>/**.rpy` + `generated_files.txt` |
| `tools/qa.py` | 校验：BOM、**`old` 无重复（重复=启动即崩）**、每个 `old` 确实等于某条真实源串、双语对里英文未丢失、标签/插值守恒、覆盖率 | → `qa_report.txt`，非零退出码表示有问题 |
| `tools/rpy_extract.py` | **模式 B**：游戏直接给散文本 `.rpy` 时的抽取器。先收集 `Character(...)` 变量名，只认"裸字符串"或"已知角色变量 + 字符串"两种语句，并且**只收 `label` 块内的**——`screen`/`style` 块里的裸字符串（`"bottom_left"` 这类）会被误判成对白，缩进栈判上下文可以挡住它 | `game/**/*.rpy` → 与 `extract.py` 完全同构的 `en-zh.json` |
| `tools/tl_reuse.py` | **模式 B 复用官方译文**：解析明文 `game/tl/<lang>/*.rpy` 里的 id 块 / `strings` 块，按**内容**配对（§3.6）。说话人前缀形态、未知转义保留反斜杠、折叠空白二次配对是它的三条命门 | `tl/<lang>/*.rpy` + JSON → 就地填 `zh` + `reuse_report.txt` |
| `tools/align_check.py` | 对齐与漏译审计（见 §8.5）。`apply_trans.py` 的标签守恒**抓不到"整对错位一行"**，因为错位后标签仍然相等；这里用"英文里出现的专名必须也出现在中文里"+"中文里不许残留小写英文单词"两个判据补上。`--only-names` 让显示名表成为唯一硬判据，`[...]` 插值不算漏译 | JSON → `align_report.txt`，非零退出码表示有硬失败 |
| `tools/uninstall.py` | 一键回滚（按 manifest + 扫 `tl/<lang>/` 双保险）。**扫描要收目录下全部文件**，不能只挑 `.rpy`/`.rpyc`——`--cjk-font` 复制进去的字体也在 `tl/<lang>/font/` 里，漏了就不是"零残留" | — |
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
13. **对白框有没有固定 `ysize`** → 有就必须处理，否则第二语言被推到屏幕外（§5.1）：先读 `screen say` 用的哪个样式名，能换底图就 `--textbox-height`（固定值，绝不 `ysize None`），背景写在 screen 里换不掉就 `--window-style` + `--window-ypos` 上移。
14. **游戏有没有对某些文字显式 `{font=}`**（标题卡/打字机字体）→ 有就用 `--font-mode tag`，别用全局字体映射把它们一起换掉（§6.2）。
15. `zh` 字段连 `{标签}` 一起存，让标签守恒成为真闸门；生成器只负责拼中英两行。
16. 翻完跑 `align_check.py`：标签检查抓不到"错位一行"，专名与漏译检查能。
17. 交付前 `uninstall.py --dry-run` 列出的必须**恰好**是你新增的文件，包含复制进去的字体。
18. **模式 B 且 `game/tl/<lang>/*.rpy` 是明文** → 用 `tl_reuse.py` 按内容配对官方译文（§3.6）；收割正则要能吃 `# mc "old"` / `mc "new"` 的说话人前缀形态，未知转义要连反斜杠一起保留，配对失败先试折叠空白。
19. **布局自检必须走真 `renpy.say(who, tr, interact=False)`**（在真实游戏上下文里），`always_shown` + `use say(...)` 的自建 screen 是假故障制造机（§9.0）。
20. **`denames.py` 报 0 candidates ≠ 官方没音译人名**。再 `grep '·'` 一次，并用 `align_check --only-names` 的"英文有名字、中文没有"清单逐行确认（§3.5 第 6/7 条）。
21. **改对白框之前先读 `screen say` 用的是哪个样式名**：`style "window"` 的游戏对 `say_window` 的覆盖完全无感；背景写在 screen 里时样式层也改不到它（§5.1）。

---

## 14. 新项目执行手册（照抄顺序即可）

前提：把 `tools/`（9 个文件）和这份 md 一起复制到新游戏根目录，`cd` 到该目录。所有脚本只依赖标准库 + 本机 Python 3，不需要装包。

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

**换项目只需要动 5 个地方**（其余一律不用改）：

| 位置 | 改什么 |
| --- | --- |
| `--lang` | 语言代码。若游戏自带 `chinese`，**必须另起一个名**（`zh`），否则你的 `strings:` 会被官方 id 块压掉（§3.5） |
| `--kinds` | 只译对白用 `say`；要连选择支一起译用 `say,menu`；`uwrap`（HUD/图鉴/系统文案）默认**不要**开，见 §5 |
| `build_tl.py --picker-name/--flag` | 语言菜单里显示的名字、persistent 开关变量名 |
| `localization/glossary.md` | 每个游戏的术语、人名表、语域基线——这是唯一需要重写的文本 |
| `localization/names_manual.tsv` | 每个游戏的音译变体，第一次跑完候选表后人工填一次 |

**分支判断（决定工作量的唯一变量）**：
- 归档里有官方中文 → 翻译量 = `untranslated` 缺口（本项目 5,439 条，约 20 分钟 agent 时间）。
- 没有官方中文 → 翻译量 = 全部 `say` 条数（按 §15 的 token 基线估算，Sunset Rose 3,966 条约 40 分钟）。
- 字体：归档里已有 CJK 字体 → 零新增文件；没有 → 从系统复制一份 OFL 字体到 `game/tl/zh/fonts/` 再映射。

### 14.1 模式 B：散文本 `.rpy`（无归档）的完整命令序列

判据：`find game -name '*.rpa'` 为空、`game/*.rpy` 能直接读到明文。**仍然不要改源码**，产物照旧落在 `game/tl/<lang>/`。

```bash
# 1) 抽取（不需要解归档，所以不用 extract.py）
python tools/rpy_extract.py --game game --out localization/en-zh.json
#   extract_report.txt 里确认三件事：
#     character vars   : 只列出了真正的说话人变量
#     say statements   : unique N，duplicate-old 应为 0（不为 0 说明有整句重复，已自动去重）
#     然后跑一遍反向核对：源文件里的 say 行是否全部进了表（漏一行 = 少译一行）

# 1b) 如果 game/tl/<官方语言>/*.rpy 是明文（自带官方译文）——先复用再翻译（§3.6）
python tools/tl_reuse.py --tl game/tl/chinese            # 只看报告
python tools/tl_reuse.py --tl game/tl/chinese --apply     # 本项目：18,608 条里 18,544 条直接复用
#   然后 grep '·' localization/en-zh.json 查音译残留，按 §3.5 第 6/7 条手工补 names_manual.tsv

# 2) 翻译：<=500 条直接主线程写 localization/out_NN.json（{id: 中文}，标签照抄）
python tools/apply_trans.py          # 标签/插值/换行守恒预检
python tools/align_check.py --only-names --names "$(python -c "...")"   # 硬失败必须 0

# 3) 生成 + 校验
python tools/build_tl.py --lang zh --kinds say --layout zh-first \
    --font-mode tag --font-ref fonts/NotoSansSC-VariableFont_wght.ttf     --flag <项目缩写>_bi_off --clean
#   游戏没自带 CJK 字体时改用 --cjk-font "C:/Windows/Fonts/NotoSansSC-VF.ttf"（复制一份进 tl/<lang>/font/）
#   固定高度对白框二选一（§5.1）：
#     能换底图 -> --textbox-height <按公式算的固定高度> --window-bg <底图>
#     底图写在 screen 里换不掉 -> --window-style <screen say 真用的样式名> --window-ypos <绝对值>
python tools/qa.py                   # 必须 FAILURES: 0

# 4) 游戏内自检（§9）：临时 harness 截图 + translate_string 断言，用完连 .rpyc 一起删
# 5) python tools/uninstall.py --dry-run  # 必须恰好列出你新增的每个文件（含字体）
```

`--font-ref` 与 `--cjk-font` 二选一：游戏已经带了 CJK 字体就用前者（零新增文件），没带才用后者（复制一份进 `tl/zh/font/`）。
`--window-style/--window-ypos` 只在"固定高度对白框"需要上移时才写；先按 §5.1 读 `screen say` 确认窗口样式真名。

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

**对白框容量实测（用来判断要不要动 ypos）**：`gui.text_size 35`、`dialogue_width 1116`、`dialogue_ypos 65`、
`textbox_height 278`、`window ypos 835` → 行距实测 58px，正文起点 900，屏幕 1080 → **只有 3 行可见**；
双语行数分布 2 行 16,262 / 3 行 1,471 / 4 行 303 / ≥5 行 55。`ypos` 上移到 725 → 5 行，覆盖 99.97%。

**这条基线用来判断"小项目该花多久"**：散文本 + 几百条对白，正常应该在 1 小时内收工；如果超过，多半是（a）在对白框高度上返工（先读 `style window` 再动手）、或（b）反复重启游戏等过场（改用 §9 的临时 screen 验证布局，不必推进剧情）。

**用来判断"哪里不对"的红线**：
- `extract` 的 say 条数比 `.rpyc` 源文件数×合理对白量高出一个数量级 → 大概率没排除 `tl/**`（§3）。
- 单组 token 超过 100 万 → agent 在自我校验，prompt 里把"禁止自检"写得更硬（§8）。
- `qa.py` 报 `dup` → 生成器去重跨 kind 没做好，游戏会启动即崩（§4）。
- `qa.py` 报 `ghost` → `old` 和源串不逐字节相等，多半是转义顺序或 `\n` 处理错（§4），这类条目会静默不生效。
- 截图满屏豆腐块 → 字体三层挂载缺一层，尤其 `translate <lang> style`（§6.1）。
