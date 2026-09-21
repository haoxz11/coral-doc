# AGENTS.md

本仓库是一个跨 agent 的 skill（`SKILL.md` + `references/` + `scripts/` + `VERSION`），无构建、无依赖（脚本只用 python3 标准库）。改这个仓库改的是 skill 的行为本身，产出物是文档和脚本内容，代码评审的对象是 Markdown 的规则表述是否准确、无歧义。

用户实际运行的副本装在 `~/.agents/skills/coral-doc/`；**本仓库是唯一源头**，只改工作副本对已安装的副本无效。发布走 提交 → 推送 → 使用方拉取；本地快速验证用 README「维护指南」里的 rsync 命令（只能用于非克隆安装的那份）。所有对 skill 内容的修改都发生在本仓库，装好的那份只在 `coral skill ensure` 或 rsync 时更新。

## 硬约束

- **只使用 `references/coral-markdown.md` 列出的渲染能力**。给 skill 增加任何 markdown 写法前，先确认它在该速查里存在；清单外的 shortcode / HTML 会被 coral 原样输出。
- skill **不绑定**特定团队清单、固定路径或某个具体 agent；文档库地址永远由使用者给出。新增功能时守住这条边界。
- `scripts/` 只用 python3 标准库，引入任何第三方依赖前先停下。
- 全部文档用简体中文，行文直接面向使用者，与现有 SKILL.md / README 的口吻保持一致。提交信息是中文一行式，概括这次行为变化（如「缓存分桶化：imports.json 拆为 ~/.coral-doc/ 分桶目录并脚本化」）。

## 改动联动

每个文件都有联动对象，动一个必须检查其余。完整联动表见 README「维护指南」，按你动的文件对号入座：

| 你改了 | 必须同步检查 |
|---|---|
| `SKILL.md` front matter（name / description / when_to_use） | 唤起行为直接由这三项决定（当前为仅手动唤起）；改后同步 README「调用方式：仅手动唤起」 |
| `references/coral-markdown.md` | README「coral markdown 能力速查」表 + SKILL.md 的美化清单 |
| `references/dingtalk-import.md` | SKILL.md「钉钉文档导入」对应步骤；缓存相关改动还要同步 README「幂等缓存」 |
| `scripts/imports_cache.py` | `references/dingtalk-import.md` 第 2 节（布局与子命令）+ README「幂等缓存」 |

`README.md` 是 SKILL.md 的说明与导读，三者对同一规则的表述只保留一处权威定义，其余位置引用。

## 版本

用户可感知的行为变化（流程、命令、缓存布局、唤起方式）递增 `VERSION`，并在提交信息中带上版本号。纯笔误、格式修正可不递增。

## 验证

没有自动化测试。改动 `scripts/imports_cache.py` 后，用隔离的 HOME 跑子命令做冒烟，**不要用真实环境**——脚本默认写 `~/.coral-doc/`，那是用户跨会话的持久缓存，被测试数据污染后线上判定会出错：

```bash
export TMPHOME=$(mktemp -d)
HOME=$TMPHOME python3 scripts/imports_cache.py hash <某个文件>
HOME=$TMPHOME python3 scripts/imports_cache.py record-import /tmp/lib node1 target=/tmp/a.md
HOME=$TMPHOME python3 scripts/imports_cache.py lookup /tmp/lib node1
```

`migrate` 子命令会迁移真实缓存，只在线上升级场景手动执行，测试时同样套上临时 HOME。

文档改动的验证方式是通读改后的流程是否自洽：步骤之间引用的文件、字段、子命令是否真实存在，front matter 字段表与 coral-markdown.md 是否一致。
