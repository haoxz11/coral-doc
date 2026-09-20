# coral-doc

一个 Agent skill：按 coral 文档库的约定撰写 Markdown 并落盘到本地文档库。

它替使用者解决三件事：

- **位置选对**——从文档库现有结构里选一级菜单与目标目录，而不是随便丢一个路径。
- **类型判对**——命中发布意图时仿写库内同类发布文档的固定套路，其余情况按研发视角专业写作。
- **内容写对**——填对 front matter，并用 coral 的 markdown 能力（提示块、选项卡、mermaid 等）把文档写漂亮。

## 三种模式

本技能**只能手动唤起**（见下方「调用方式：仅手动唤起」一节）。被点名调用后，按下面的条件在内部选择模式：

| 模式 | 进入条件 | 做什么 |
|---|---|---|
| 手写模式（默认） | 提出要写文档，未给出其他线索 | 从零撰写一篇新文档 |
| 钉钉导入模式 | 给出钉钉文档链接/ID **且**表达存库意图 | 把钉钉文档转成 Markdown 存入库，图片换长期链接 |
| 本地优化模式 | 声明要优化某个本地 md 文件 | 按用户点明的项优化，并处理本地图片引用 |

只有钉钉链接、没有存库意图时（查询、讨论），不会进入导入模式。

## 前置条件

**必需**

- 一个 coral 文档库。

**按模式可选**

- 钉钉导入模式：优先使用本机已登录的 `dws` CLI；不可用时降级到会话中已配置的钉钉 MCP。两者都不可用会明确告知并停止，不会臆造内容。
- 涉及图片换链（钉钉导入、本地优化）：需要 `coral-mcp`（工具名 `upload_file` / `finalize_upload`）。未安装时，skill 会读文档库首页 front matter 的 `remote_url` 字段定位 coral 服务，走 `{remote_url}/mcp` 端点；两者都拿不到会向使用者询问服务地址。

**关于文档库地址**

文档库地址由使用者在指令中告知，skill **不猜测、不使用任何记忆中的路径**。整个过程中每次回复都会显式引用当前库地址（例如「文档库：`/path/to/content`」）；给出的路径不存在时会先确认正确地址。路径完全取决于使用者，不绑定任何特定团队或仓库。

## 安装

把本目录复制到 Agent 的 skills 目录。**本机当前生效位置是 `~/.zcode/skills/coral-doc/`**（会话实际加载的就是这一份）：

```bash
rsync -a --delete --delete-excluded \
  --exclude '.git' --exclude '.gitignore' --exclude '.zcode' \
  /Users/zhujy/coral-doc/ ~/.zcode/skills/coral-doc/
```

`~/.agents/skills/coral-doc/` 也是一个合法的 skill 发现根，可以作为安装目标：

```bash
rsync -a --delete --delete-excluded \
  --exclude '.git' --exclude '.gitignore' --exclude '.zcode' \
  /Users/zhujy/coral-doc/ ~/.agents/skills/coral-doc/
```

但**不要两处同时留**。发现顺序是 `~/.zcode/skills` 先于 `~/.agents/skills`，同名的两份只有先命中的那份会加载，另一份被遮蔽（改了也不生效）。若确定要迁到 `~/.agents/skills/`，先删掉 `~/.zcode/skills/coral-doc/` 再装。

安装后自查四项：

1. 对应目录下的 `SKILL.md` 存在，且首行是合法的 YAML front matter（`name` + `description` + `when_to_use`）。
2. `references/` 下的两个文件都在。
3. 目标文档库目录存在。
4. 若两处都装了，按上面的发现顺序确认最终生效的是哪一份。

## 使用示例

本技能不自动唤起，每次都要**点名它**，并把文档库地址一并给出：

```
用 coral-doc 把这次改动的设计文档写进文档库 ~/coral-book
```

```
用 /coral-doc 在文档库 ~/coral-book 写一篇这周的发版记录
```

```
用 coral-doc 把这个钉钉文档导入文档库 ~/coral-book：
https://alidocs.dingtalk.com/i/nodes/xxxxxxxx
```

```
用 coral-doc 优化 ~/coral-book/tools/deploy.md 文件
```

在支持 `/` 菜单的客户端里，直接输入 `/coral-doc` 唤起后，再补充任务与库地址也可以。

## 调用方式：仅手动唤起

本技能**不会因为你在写文档而被自动唤起**。它的 front matter 已明确声明「手动调用，禁止自动唤起」，并去掉了此前的触发词清单（写文档、写发版记录、write doc、release notes、提到 coral/文档库 等）。

- 唤起方式：在消息里显式点名 `coral-doc`（或 `/coral-doc`、`coral 技能`），然后再说明任务。
- 未点名时：即使你说的是「写一篇发版记录」「把这个钉钉文档存到文档库」这类原本会命中的场景，也不应自动调用。
- 已调用后：模式判定（手写 / 钉钉导入 / 本地优化）只是技能内部的流程分流，与唤不唤起无关。

## 手写模式工作流

### 1. 选一级菜单

扫描文档库根目录：每个一级子目录读其 `_index.md` 的 front matter，`title` 即菜单名（无 `_index.md` 或无 `title` 时用目录名），`weight` 小者在前、无 weight 沉底；根级 `.md` 文档也是一级菜单项。

使用者已指定菜单或目录时直接采用，但仍会展示最终目标路径供确认。**未指定存放位置时不会甩出全部菜单让使用者自己挑**——而是根据文档内容在库内找出最匹配的 2–3 个候选目录（可深到二级子目录），列出并附推荐理由供选择；确无合适候选才回退到完整菜单列表。

### 2. 意图判定（二选一）

**发布文档**——意图命中「发布 / 发版 / 上线 / release / 部署清单」时：

1. 在所选一级菜单的子目录树中搜索目录名含 `发布` / `release` / `发版` 的目录，找不到扩大到全库。
2. 优先选非归档目录（目录名含 `历史归档` / `历史发布` 的视为归档，仅作参考）；多候选时由使用者选。
3. 取该目录下**最新一篇**（按 front matter `date` 或文件名中的版本号/日期）作为**格式样板**。
4. 仿写样板的固定套路：章节结构、表格列、状态标记、front matter 字段全部照样板对齐，内容按本次实际情况填写。

**专业写作**（默认）——不仿写任何既有文档的格式。以研发工程师视角（架构、测试、运维等研发侧视角，视内容而定）自主组织章节结构（背景/目标/方案设计/影响面/上线计划等，视内容取舍）。

### 3. 填 front matter

| 文档类型 | 字段 |
|---|---|
| 普通文档 | `title`（从正文一级标题或用户意图提炼）+ `date`（当天，`YYYY-MM-DD HH:MM:SS`） |
| 发布文档 | 在普通文档基础上加 `permalink`：样板有惯例则照其模式生成，无则按目录路径生成 |
| 目录分支页 `_index.md` | `title` + `icon`（Iconify 名，带前缀如 `mdi:home`）+ `weight` |

front matter 用 YAML（首行 `---`）。完整字段语义见 [references/coral-markdown.md](references/coral-markdown.md)。

### 4. 动笔前确认

动笔前会展示并等待确认：目标文件绝对路径（库地址 + 菜单路径 + 文件名）、类型判定（仿写哪个样板文件 / 专业写作）、内容大纲（章节列表）。

### 5. 写作与美化

主动使用 coral 的 markdown 能力美化文档，语法速查见 [references/coral-markdown.md](references/coral-markdown.md)。写完后会再自检一遍：正文里是否还有该用这些能力的地方（散落的注意事项、多方案平铺、口头描述的流程），有则改写。

## 钉钉导入模式

详细命令与上传接口见 [references/dingtalk-import.md](references/dingtalk-import.md)。

1. **确定文档库地址、选一级菜单**：与手写模式相同。
2. **读取文档**：`dws doc info` 探测类型，`dws doc read` 取 Markdown 与元信息。仅**普通文档（adoc）**可读；表格（axls）、画板（adraw）、白板（awbd）、多维表（able）等不支持，会告知使用者并建议先在钉钉中转为普通文档。分享短链（`alidocs.dingtalk.com/i/p/{key}`）无法解析，需给出完整链接或文档 ID。
3. **图片处理（核心）**：钉钉返回的图片是**临时签名 URL，几分钟内过期**，绝不能原样保留。每张图片走 `upload_file` → multipart 直传对象存储（文件字段名必须是 `file` 且放在表单最后）→ `finalize_upload`，拿到长期链接后逐张改写引用，不漏改、不错位。
4. **导不出的内容**（白板等无导出 API 的图类）：保留钉钉原文链接，不强行转换。
5. **front matter**：`title` 用钉钉文档标题，`date` 用钉钉文档最后修改时间（拿不到则用当天）。
6. **文档尾部注明来源**：正文最后追加一行 `> 来源：[钉钉原文 · <标题>](<链接>)`。
7. **落盘前确认**：展示目标路径 + 转换摘要（图片 N 张已上传 / 导不出的内容 M 处保留链接 / 不支持的元素清单）。
8. **落盘后不做任何验证**：本地写入成功即完成，不检查站点渲染、不回访图片链接。
9. **清理临时文件**：过程中下载的图片、`doc read` 导出内容、中间结果全部删除。建议每次导入使用独立临时目录（如 `/tmp/dingtalk-import-<时间戳或ID>`），收尾整目录删除。

**保真导入是默认行为**，不会询问是否增强；发现的可增强点仅在最终汇报中顺带提及，使用者主动要求才改写。

## 本地优化模式

1. **读取文件**，识别**本地图片引用**（相对/绝对路径指向本地文件的 `![...](...)`；排除 http(s) 链接和已上传的 `/f/...` 远程链接）。
2. **有本地图片时询问**是否上传换取长期链接。删除规则：

   | 图片位置 | 上传成功后 |
   |---|---|
   | 文档库目录**内** | 改写引用，并**删除本地文件**（由 coral 服务统一提供） |
   | 文档库目录**外** | 只改写引用，**本地文件保留** |

3. **其他优化按使用者意图执行**：说了优化什么就做什么（格式修正、链接修复、coral 能力美化等），没提到的不会擅自做。目标落在文档库内时，遵循 front matter 与站内链接约定。
4. **落盘前确认**：展示改动摘要（图片 N 张中 M 张已上传换链、K 张库内文件已删除、失败原因；其他优化项清单），确认后写回原文件并汇报。上传失败的图片保留原引用并说明。

## coral markdown 能力速查

完整语法与语义见 [references/coral-markdown.md](references/coral-markdown.md)，此处只列速查。**只使用这份清单里的能力**——清单外的 shortcode 或 HTML 标签会被 coral 原样输出、不会渲染，除非仿写的样板本身就在用。

| 能力 | 写法要点 |
|---|---|
| front matter | 首行 `---` 为 YAML（`+++` 为 TOML），字段全部可选 |
| 提示块 | `{{% notice style="caution" title="风险提示" %}}...{{% /notice %}}`，`style` 白名单：`tip`/`info`/`note`/`caution`/`warning`/`important`/`danger`/`error` |
| 选项卡 | `{{< tabs >}}` + `{{% tab title="X" %}}...{{% /tab %}}`，首个 tab 默认 active |
| 子页目录 | `{{% children sort="weight" %}}`，适合章节目录页 |
| mermaid | 代码围栏，语言标注写 `mermaid`；仅围栏形式有效，没有对应 shortcode |
| 数学 | 块级 `$$...$$`（默认启用）、语言标注为 `math` 的围栏；行内 `$...$` 需服务端 `[render].inline_math = true` |
| 代码高亮 | 始终标注语言（`sql`、`json`、`yaml` 等），不写裸代码块 |
| GFM | 表格、任务列表、删除线、autolink；内嵌 HTML 原样透传 |
| 站内链接 | 写 `.md` 相对形式（`./detail.md`），coral 自动重写为站内 URL 并剥掉扩展名 |

**结构约定**

- 一级菜单 = 根目录下每个子目录（取其 `_index.md` title）+ 根级文档。
- 分支页回退链：`_index.md` > `index.md` > `readme.md`（不区分大小写）。
- 同级排序四级链：① `weight` 升序（无则沉底）→ ② 文件名数字前缀（`1.入门.md`）→ ③ `date` 倒序 → ④ 文件名序。
- 新建目录若需作为菜单节点展示，需创建 `_index.md`。

## 目录结构

工作流的完整规则细节见 [SKILL.md](SKILL.md)，本文档是它的说明与导读。

```
coral-doc/
├── SKILL.md                     # 主工作流：三种模式、菜单选择、front matter、确认与落盘规则
├── references/
│   ├── coral-markdown.md        # coral 渲染能力速查：front matter 字段、shortcode、图表、链接、排序
│   └── dingtalk-import.md       # 钉钉导入详细流程：dws 命令、类型路由、图片上传三步、收尾清理
└── README.md                    # 本文件
```

## 维护指南

**源码与安装是两份拷贝。** 源码在本目录，安装位置是 `~/.zcode/skills/coral-doc/`（复制而非软链）。改完源码需重新同步，否则 ZCode 加载的仍是旧版本：

```bash
rsync -a --delete --delete-excluded \
  --exclude '.git' --exclude '.gitignore' --exclude '.zcode' \
  /Users/zhujy/coral-doc/ ~/.zcode/skills/coral-doc/
```

仓库元数据（`.git` / `.gitignore` / `.zcode`）不要带进安装目录：安装目录只需要 `SKILL.md`、`references/` 和这份 README，混入 `.git` 会让它变成一个没有 remote 的游离工作副本。`--exclude` 负责不发送，`--delete-excluded` 负责把目标端已残留的同类文件删掉（只加 `--exclude` 时，目标端已存在的排除项不会被删除）。

**改动时的联动关系**

- `SKILL.md` front matter 的 `name` / `description` / `when_to_use` 共同决定**是否被自动唤起**。当前三者写的是「仅手动调用」，改动它们会直接改变唤起行为，改后需同步本文档的「调用方式：仅手动唤起」一节。

**改完必须重新同步**（源码改动不会自动生效到已安装副本），命令见「安装」一节。只改 `.agents` 或只改 `.zcode` 中的一份、而另一份仍在，会出现「改了没反应」——因为先命中的那份在生效。
- 新增或修改 coral 渲染能力，改 `references/coral-markdown.md`，并同步本文档的「coral markdown 能力速查」表与 `SKILL.md` 的美化清单。
- 导入流程的命令或上传接口有变化，改 `references/dingtalk-import.md`；摘要格式变化需同步 `SKILL.md` 的对应步骤。
- 保持约束：只使用 `references/coral-markdown.md` 列出的能力；不绑定特定团队清单或固定路径。

## 已知限制

- 钉钉仅支持普通文档（adoc）导入，表格/画板/白板/多维表需先在钉钉中转为文档。
- `<Badge>` 等 Hugo 主题 shortcode coral 不渲染（除非样板文档本身在用）。
- 行内数学公式默认关闭，需服务端开启 `[render].inline_math`。
- skill 只负责生成并落盘文档，不做落盘后的站点渲染或链接可用性校验。
- 钉钉返回的图片是短时效签名 URL，不走上传换链会很快失效。
