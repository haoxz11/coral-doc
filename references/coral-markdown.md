# coral markdown 能力速查

coral 是 Markdown 文档服务引擎。渲染管线：shortcode 占位 → 数学提取 → comrak 渲染（GFM 全开）→ shortcode 回填 → 数学回填 → TOC。写文档时只使用本文件列出的能力。

## Front matter

可选；首行 `---` 为 YAML，`+++` 为 TOML。全部字段可选：

| 字段 | 类型 | 语义 |
|---|---|---|
| `title` | string | 页面/目录树节点标题；缺失回退文件名去数字前缀 |
| `weight` | int | 排序权重，升序在前，无 weight 沉底 |
| `draft` | bool | `true` 且服务端 `content.draft=false` 时该页 404 |
| `permalink` | string | URL 覆盖（如 `/meta/`） |
| `icon` | string | 菜单图标：Iconify 名（带前缀，如 `mdi:home`）或图片 URL |
| `archetype` | string | `home` = 门户首页布局，其他值降级 |
| `url` | string | 仅 home 首页主按钮，markdown 链接语法 `[文案](地址)` |
| `disableToc` | bool | 关闭页内 TOC |
| `date` | string | 排序（规范化 `YYYY-MM-DD`）+ 页脚展示 |
| `remote_url` | string | 仅首页：远程附件地址，文档里的 `/f/...` 链接交给该实例解析；也是导入流程定位 coral 服务的依据 |

普通文档惯例：`title` + `date: YYYY-MM-DD HH:MM:SS`。目录分支页 `_index.md` 惯例：`title` + `icon` + `weight`（+ 可选 `permalink`）。

## Shortcodes

定界符：`{{% ... %}}` 内层按 markdown 渲染；`{{< ... >}}` 内层原样输出。支持嵌套同名深度配对。代码块/行内代码内的 shortcode 写法不生效（原样透传）。

### notice（提示块）

```markdown
{{% notice style="caution" title="风险提示" %}}
这里的内容会被渲染成带图标的警示块。
**markdown 语法**在内层有效。
{{% /notice %}}
```

`style` 白名单：`tip` / `info` / `note` / `caution` / `warning` / `important` / `danger` / `error`。`title` 可省略。

### tabs（选项卡）

```
{{< tabs >}}
{{% tab title="方案A" %}}
方案A 内容（markdown 有效）
{{% /tab %}}
{{% tab title="方案B" %}}
方案B 内容
{{% /tab %}}
{{< /tabs >}}
```

首个 tab 默认 active。

### children（子页目录）

```markdown
{{% children sort="weight" %}}
```

列出当前目录下的子页面链接，适合章节目录页。

### 未知 shortcode

原样输出并记 WARN 日志——**不要使用上表之外的 shortcode**，除非仿写的样板文档本身在用。

## 图表与公式

### Mermaid

````markdown
```mermaid
flowchart LR
    A[客户端] --> B{网关}
    B -->|成功| C[订单服务]
```
````

前端 CDN 渲染。只有围栏形式有效，没有 mermaid shortcode。

### 数学（KaTeX）

- 块级 `$$...$$`（默认启用）
- 行内 `$...$`（默认关闭，需服务端 `[render].inline_math = true`）
- ` ```math ` 围栏
- 代码块和行内代码内的 `$` 不触发；`\$` 转义

## 代码高亮

syntect 全量语法集，服务端输出 class 风格。**始终标注语言**：

````
```sql
SELECT * FROM t;
```
````

未知语言纯转义；无语言标注则无高亮。

## GFM

表格、任务列表 `- [ ]`、删除线 `~~x~~`、autolink、HTML 直通（`unsafe = true`：内嵌 HTML 会原样透传给浏览器，coral 不做渲染处理）。

## 链接

- 站内相对链接写 `.md` 形式：`./detail.md`、`../img.png`，coral 按源文件目录重写为站内绝对 URL（`.md` 剥扩展名）。
- 外链和站内静态文件自动加 `target="_blank" rel="noopener"`。

## 结构约定

- **一级菜单** = 根目录下每个子目录（取其 `_index.md` title）+ 根级文档。
- **分支页回退链**：`_index.md` > `index.md` > `readme.md`（不区分大小写）；`_index.md` 只有目录 URL，`index.md`/`readme.md` 充当分支页时双可达。
- **排序四级链**（同级）：① weight 升序（无沉底）→ ② 文件名数字前缀升序（`1.入门.md`）→ ③ date 倒序 → ④ 文件名序。
- 根 `_index.md` 的 title/icon 即站点标识；`archetype: home` + `url` 字段构成门户首页。
- 跳过垃圾文件：`.` 开头、`~` 结尾、`#...#` 包裹。
