# StateGrid Upstream Merge Design

## Goal

在保留当前 StateGrid Desktop 内网定制的前提下，将 `example/QwenPaw` 中自 `d586bc11` 之后、对桌面内网版本有价值的上游通用更新合并进当前分支。

## Scope

本次仅合并以下类别的上游更新：

- OpenAI 兼容请求、流式、重试、消息归一化相关的 provider 与 agent 稳定性修复
- `send_file`、`view_media`、`shell`、`files` 路由等和工具执行、文件展示直接相关的通用能力
- 桌面启动、安装器、Windows 兼容、桌面测试等与 StateGrid Desktop 打包和运行直接相关的改进
- 控制台中对内网桌面版仍然有价值、且不破坏现有产品裁剪的通用交互改进
- 与上述改动配套的必要测试

明确排除以下内容：

- `deepseek` 相关模型、兼容性和展示逻辑
- 外部渠道能力和渠道增强，包括但不限于 Telegram、DingTalk、QQ、Weixin、WeCom、Mattermost、Matrix、SIP、iMessage
- 官网文档站、release note、GitHub 导流、FAQ/文档外链恢复
- 会重新打开自动更新、扫描更新或版本展示的逻辑

## Existing Customizations To Preserve

当前分支已经存在以下内网定制，合并时必须保持不变：

- 桌面产品名为 `StateGrid Desktop`
- 桌面与控制台使用本地图标和本地静态资源
- Header 右上角外链和版本展示已隐藏
- 自动更新逻辑和更新扫描已关闭
- 频道对外只暴露控制台；不恢复上游多频道入口
- 新增 SMTP `send_email` 工具与对应配置页
- 系统提示词和默认 agent 描述已改为内部版本
- 关闭窗口保持当前默认行为，不重新引入会卡死的关闭弹窗

## Current State

当前仓库已吸收至上游 `d586bc11` 附近的部分能力，并在此基础上做了较多产品化改动。`example/QwenPaw` 已前进至 `94896470`，其中包含大量功能、前端和资源更新。

这些上游更新不能直接整体 merge，因为它们会覆盖以下已定制区域：

- `console/src/layouts/*` 中的 Header、导航与品牌展示
- `src/qwenpaw/cli/desktop_cmd.py` 中的桌面行为和打包细节
- `src/qwenpaw/config/*`、`src/qwenpaw/app/routers/config.py` 中的渠道暴露范围
- provider 与 tool 相关模块中我们已经落地的内网兼容修复

## Design

### 1. Controlled Merge Strategy

不采用整段 rebase，也不按 commit 机械 cherry-pick，而是按功能主题手工移植：

- 后端稳定性
- 桌面与打包链路
- 控制台通用增强
- 测试补齐

这样可以对每个冲突点进行显式决策，优先保留当前内网产品边界。

### 2. Backend Merge Boundary

后端优先吸收以下通用更新：

- `openai_provider.py`
- `openai_chat_model_compat.py`
- `retry_chat_model.py`
- `model_factory.py`
- `session.py`
- `send_file.py`
- `view_media.py`
- `shell.py`
- `routers/files.py`

这些文件与内网部署下的流式调用、长任务、文件引用、媒体预览和工具稳定性直接相关，且不依赖外部渠道能力。

对 `deepseek`、外部渠道和大范围安全审批重构，仅在被上述通用修复间接依赖时做最小兼容，不主动引入完整特性。

### 3. Desktop Merge Boundary

桌面相关仅吸收会提升稳定性、安装体验、打包结果可用性的部分，包括：

- `desktop_cmd.py` 的 Windows 兼容与运行健壮性改动
- 安装器脚本与桌面测试中和安装/卸载/入口可见性直接相关的内容

但必须保留：

- `StateGrid Desktop` 品牌名
- 现有 logo / icon
- 默认关闭行为
- 关闭更新相关逻辑

### 4. Console Merge Boundary

前端仅选择性合并以下通用增强：

- Skills / Tools 页面中与通用可用性相关的重构
- Workspace/FileEditor 与文件预览相关的小范围增强
- Session 列表与聊天页中对交互稳定性有帮助的修复
- 模型提供商展示的小范围兼容修复

以下行为必须保持现状：

- Header 外链隐藏
- 版本号不展示
- 频道页不恢复多渠道运营能力
- 不恢复更新入口

### 5. Verification Strategy

验证分为三层：

1. Python 定向单测：provider、desktop、tools、config
2. 前端构建：确认受控合并后 `console` 仍可编译
3. 约束验证：确认只暴露 `console` 渠道，品牌与隐藏项未回退

## Risks And Mitigations

### 上游文件跨度过大，容易带回被裁剪能力

通过“按文件主题手工移植”代替整体 merge，并在每一组改动后检查 `get_available_channels`、Header 配置和桌面常量。

### Provider 兼容改动和我们现有调试修复发生冲突

优先保留已有内网诊断日志，再按上游逻辑补兼容层和测试，避免回退排障能力。

### 前端重构覆盖定制化 UI

仅移植通用逻辑，不直接整体替换 `Header.tsx`、`navigationFeatures.ts`、品牌资源映射等定制文件；必要时只摘取上游局部实现。
