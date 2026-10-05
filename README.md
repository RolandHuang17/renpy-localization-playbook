# Ren'Py 发行版汉化 / 本地化工具链

给 **Ren'Py 官方发行的 PC/zip 版游戏**（无源码）做"中英双语对白"的可复制流程与工具集。
所有产物都是**新增文件**，靠 Ren'Py 的加载优先级生效，因此卸载 = 删文件，原文件零修改、存档兼容不破。

**唯一入口是 [`RENPY_LOCALIZATION_PLAYBOOK.md`](RENPY_LOCALIZATION_PLAYBOOK.md)。**
§0.5 是默认需求口径，§14 是照抄即可的命令序列，§15 是用来估工时和判断异常的实测基线，其余章节是依据和踩过的坑。

## 三种模式

| | 判据 | 抽取 / 复用工具 |
| --- | --- | --- |
| **A 归档型** | `game/` 下只有 `*.rpa` + `tl/None/`，没有散落 `.rpy` | `tools/extract.py`（解 RPA3 索引 + RPC2 容器 + stub unpickler 反序列化 AST），自带官方译文在归档里时按 identifier 连接 |
| **B 散文本型** | `game/*.rpy` 能直接读到明文 | `tools/rpy_extract.py`（只收 `label` 块内的 say 语句） |
| **B+ 散文本 + 自带明文官方译文** | `game/tl/<lang>/*.rpy` 也是明文 | 上一步之后接 `tools/tl_reuse.py`（按**内容**配对，省掉 99% 翻译量） |

三种模式共用同一份 `localization/en-zh.json` 记录结构，所以生成、校验、回滚三段完全一致。

## 用法

把 `RENPY_LOCALIZATION_PLAYBOOK.md` 和 `tools/` 一起复制到游戏根目录，然后：

```bash
# 模式 B（散文本）示例
python tools/rpy_extract.py --game game --out localization/en-zh.json
python tools/tl_reuse.py --tl game/tl/chinese --apply   # 仅 B+：游戏自带明文官方中文时
# …翻译写进 localization/out_NN.json（{id: 中文}）…
python tools/apply_trans.py
python tools/align_check.py --only-names --names "<speakers.json 的显示名>"   # 必须 FAILURES: 0
python tools/build_tl.py --lang zh --kinds say --layout zh-first \
    --font-mode tag --font-ref fonts/NotoSansSC-VariableFont_wght.ttf     --flag <项目缩写>_bi_off --clean
#   游戏没自带 CJK 字体时把 --font-ref 换成 --cjk-font "C:/Windows/Fonts/NotoSansSC-VF.ttf"（会复制一份进 tl/<lang>/font/）
#   固定高度对白框才需要：--textbox-height <按 §5.1 公式算出的固定高度> --window-bg <底图>
#   若 screen say 写死了 style "window"（不是 say_window）：--window-style window,window1 --window-ypos <绝对值>
python tools/qa.py                   # 必须 FAILURES: 0
python tools/uninstall.py --dry-run  # 必须恰好列出你新增的每个文件
```

只依赖标准库 + 本机 Python 3，不需要装任何包。

## 工具清单

| 文件 | 职责 |
| --- | --- |
| `rpautil.py` | RPA3 索引 / RPC2 slot / stub unpickler / AST 遍历，模式 A 的公共底座 |
| `extract.py` | 模式 A 抽取，并按 identifier 连接归档里自带的官方译文 |
| `rpy_extract.py` | 模式 B 抽取（明文 `.rpy`） |
| `tl_reuse.py` | 模式 B+ 复用官方译文：解析明文 `translate <lang>` 块，按内容配对（含说话人前缀形态、未知转义保留反斜杠、折叠空白二次配对） |
| `denames.py` | 复用官方译文时，把音译人名还原成原文；`--seed` 可喂已知名字表出候选（**只出候选，别直接 `--apply`**，放宽闸门会抓出同句共现词） |
| `dump_groups.py` | 把未译条目按序切成大组，供批量派工 |
| `apply_trans.py` | 合并译文分片，做标签 / 插值 / 换行守恒预检，拒绝项进 `rejected/` |
| `align_check.py` | 对齐与漏译审计（标签守恒抓不到"错位一行"，这里补上）。`--only-names` 用角色显示名当唯一硬判据，`[...]` 插值不算漏译 |
| `build_tl.py` | 生成 `tl/<lang>/**.rpy` + 语言 / 字体 / 断行 / 对白框装配文件。`--font-ref` 引用游戏已自带的字体（零新增文件），`--window-style` / `--window-ypos` 处理固定高度对白框 |
| `qa.py` | BOM、`old` 唯一性、逐字节等于源串、双语对完整性、覆盖率 |
| `uninstall.py` | 一键回滚，扫 `tl/<lang>/` 下全部文件（含复制进去的字体） |

## 注意

`localization/` 只应包含**你自己的**术语表与翻译中间产物。仓库里只放了
[`localization/glossary.template.md`](localization/glossary.template.md) 模板——
换项目时复制成 `glossary.md` 重写内容。游戏原文、译文 JSON、报告都不要提交。

## 已验证项目

Sunset Rose 0.3（A，无官方译文，3,966 条）、Midnight Paradise 1.1（A，复用官方中文 53,762 / 59,201 条）、
The Tutor 1.0（B，323 条）、By Justice or Mercy v25（B+，18,164 条对白复用 18,544 条唯一串，真缺口 64 条）。
引擎 8.5.3 / 8.5.2 / 8.4.2 / 8.3.7。工时与异常红线见手册 §15。
