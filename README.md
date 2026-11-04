# OpenCode V2 一键配置（Linux）

导入 Apricityx 的模型分组：**openai-272k、openai-1m、guomo、opencode**。
不安装 OpenCode 本体；请先安装 OpenCode V2。依赖 Bash、curl、Python 3（建议 3.9+），不需要 sudo。

## 一行安装

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Apricityx/opencode-config/main/install.sh)
```

确认安装后，**交互式输入自己的 New API API Key，输入不回显**。
统一网关：`https://newapi.server.apricityx.top:55555/v1`。
脚本不发送或验证 Key，不进行付费测试调用。

> 远程脚本会修改全局配置。建议先阅读仓库中的 `install.sh`，确认可信后再运行。
> 下载失败不会完成安装；受限网络请先下载文件，再执行 `bash install.sh`。

## 包含的模型

- **openai-272k**：5 个 GPT 模型，输入预算 272,000，输出预算 128,000。
- **openai-1m**：相同 5 个 GPT 模型，输入预算 922,000，输出预算 128,000。
- **guomo**：11 个模型，包括 DeepSeek V4、GLM、Kimi、MiniMax、Grok、Gemini。
- **opencode**：保留内置服务及其动态模型目录，不修改它的 endpoint 或认证。

默认：`openai-272k/gpt-6.1-sol`。完整模型、变体、兼容设置和 token 预算见 `providers.json`。
这些参数继承自原配置，**不是对网关当前支持情况的保证**；实际可用性取决于 Key 的分组、额度和上游。

## 安装行为

1. 定位 `${XDG_CONFIG_HOME:-$HOME/.config}/opencode`，读取全局 `opencode.json` 和 `opencode.jsonc`。
2. 隐藏输入 API Key，备份现有配置和旧 `newapi.key` 至 `backups/newapi-时间戳/`。
3. 将两个全局配置合并为 `opencode.json`，原有 JSONC 重写为仅含 schema 的空配置。
   支持 JSONC 注释、尾逗号；**注释与格式不会保留，但原文件会备份**。冲突字段以 JSONC 为准。
4. 替换 provider 定义，使用 V2 `provider.use` 策略仅允许上述四个 provider。
   删除旧的 provider 启用/禁用字段和已知 `opencode-claude` 插件加载项。
5. 保留 MCP、权限、技能、无关插件等其他设置。其他插件注入的 provider 由策略屏蔽，不擅自卸载插件。
6. Key 保存为本机独立的 `newapi.key`（权限 `600`），配置使用绝对路径 `{file:...}` 引用。
   不写入 shell profile、命令行参数或 GitHub；备份也包含旧 Key，应妥善保管。

内置 `opencode` 不共用 New API Key；付费模型需用户自行连接 OpenCode 账户。
已有第三方认证记录不删除，但 provider 策略会禁用它们。系统/组织策略可能优先于全局设置。
已有 agent、command 或 session 如指定被删除的 provider，需自行改选保留的模型。
环境变量 `OPENCODE_CONFIG`、系统配置或插件仍可能带来覆盖，请在 `/models` 检查最终结果。

配置自动重载，也可执行 `/reload`，不需要重启服务。

## 恢复

备份路径在安装完成后显示。将备份中的 `opencode.json`、`opencode.jsonc` 和 `newapi.key`
恢复到配置目录；安装前不存在的文件需相应移走。请先检查备份内容，不要把密钥上传或公开。

## 开发与验证

`installer.py` 是安装逻辑，`providers.json` 是公开模板，`install.sh` 是内嵌模板的独立安装器。
`build.py` 从维护者本机配置中选取三个 provider 的模型定义，重设公开 endpoint 和凭据引用，生成模板与脚本。

```bash
python3 build.py
python3 -m unittest -v
bash -n install.sh
```

仅发布白名单导出的模型配置，不包含维护者的 API Key、MCP、权限、技能或私人插件。
