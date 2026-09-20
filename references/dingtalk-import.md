# 钉钉文档导入流程

把钉钉文档转成 Markdown 存入 coral 文档库的详细步骤。读取工具优先 dws CLI，兼容钉钉 MCP；图片通过 coral-mcp 上传换长期链接。

## 1. 读取钉钉文档

**优先 dws CLI**（本地已安装的钉钉命令行，OAuth 已登录）：

```bash
dws doc info --node <ID或URL>    # 元信息：contentType/extension/nodeType，用于类型探测
dws doc read --node <ID或URL>    # 返回 Markdown 格式的文档内容（需文档有下载权限）
```

`--node` 接受文档 ID、`alidocs.dingtalk.com/i/nodes/{id}` URL、`document/edit|preview?dentryKey=` 完整 URL。分享短链（`alidocs.dingtalk.com/i/p/{key}`）无法被 dws 解析，需用户给出完整链接或文档 ID。

**类型探测路由**：仅普通文档（adoc）可 `doc read`。表格（axls）、画板（adraw）、白板（awbd）、多维表（able）等**不支持**——告知用户当前不支持该类型，建议先在钉钉中转为普通文档再导入。

**dws 不可用时**（命令不存在、认证过期且无法续期）：改用会话中已配置的钉钉 MCP，按其实际工具清单完成同等操作（读文档内容、拿元信息）。两者都不可用则告知用户并停止。

## 2. 图片处理（核心）

钉钉返回的图片是**临时签名 URL，几分钟内过期**——绝不能原样保留在 markdown 里。

### 2.1 发现 coral-mcp

按顺序尝试：

1. **已安装**：当前会话的 MCP 工具中已有 coral 的上传工具（工具描述带 `【coral-mcp】` 前缀，工具名 `upload_file` / `finalize_upload`）——直接使用。
2. **未安装**：读文档库**首页** front matter（根目录分支页回退链 `_index.md` > `index.md` > `readme.md`）中的 `remote_url` 字段——它指向该库对应的 coral 服务实例，MCP 端点为 `{remote_url}/mcp`（JSON-RPC 2.0，POST，`tools/call` 方法）。调用需要鉴权时若拿不到 token，向用户询问。
3. 首页没有 `remote_url` 字段、且 coral-mcp 未安装：向用户询问 coral 服务地址（或让用户安装 coral-mcp），不要猜测。

### 2.2 上传换链接

对每张图片：

1. `upload_file`：参数 `file_name`（含扩展名）、可选 `content_type`。返回 `post_url` 与一组表单字段（含 `object_key`，key 与 Content-Type 被 policy 钉死不可篡改）。
2. 以 `multipart/form-data POST` 把图片字节**直传对象存储**（文件不经过 coral）。**文件字段名必须是 `file` 且放在表单最后**；表单字段不要写到 query 或 header。
3. `finalize_upload`：参数 `object_key` + `file_name`。返回**长期可用的访问链接与现成 markdown 片段**（如 `![名称](链接)`）。

注意事项：

- 单文件大小上限在工具描述中注明（超出会被对象存储直接拒绝）——超限图片告知用户单独处理。
- 非法扩展名、特殊字符文件名可能被拒，重试时改用安全文件名（如 `image-01.png`）。

### 2.3 改写文档引用

用 `finalize_upload` 返回的 markdown 片段（或访问链接）**替换原文中的临时 URL 引用**，逐张对应，不要漏改、错位。

## 3. 导不出的内容

白板（以及任何导不出图片的内容）：**保留钉钉原文链接**，不做强行转换。可在该位置保留原有的文字说明；如果原文中没有任何说明，保持链接原样即可，并在转换摘要中列出。

## 4. front matter 与来源

```yaml
---
title: <钉钉文档标题>
date: <钉钉文档最后修改时间，YYYY-MM-DD HH:MM:SS；拿不到用当天>
---
```

文档**尾部**注明来源（正文最后追加，不是 front matter 字段）：

```markdown
---

> 来源：[钉钉原文 · <文档标题>](<钉钉文档URL>)
```

## 5. 转换摘要（落盘前确认用）

向用户展示的固定格式：

- 目标文件绝对路径
- 图片：共 N 张，已上传 M 张（失败/超限的列出原因）
- 导不出的内容：K 处保留钉钉链接（列出是什么，如"白板 ×2"）
- 不支持的元素：清单（如有）

**保真导入是默认行为，不询问是否增强**；可增强点最多在最终汇报中顺带一提，用户主动要求才改写。

确认后写入目标路径。

## 6. 落盘后收尾

- **不做落盘后验证**：本地文件写入成功即任务完成。不检查站点渲染、不回访图片链接等任何二次确认——本技能只负责生成并落盘文档。
- **清理临时文件**：导入过程中产生的本地临时文件——下载的图片、`doc read` 导出的内容、中间结果（URL 列表、上传结果等）——在落盘完成后**全部删除**，不留遗留。建议每次导入使用独立的临时目录（如 `/tmp/dingtalk-import-<时间戳或ID>`），收尾时整目录删除；目录内若发现非本次导入产生的文件（前次会话遗留），不要复用其结果，直接换新目录。
