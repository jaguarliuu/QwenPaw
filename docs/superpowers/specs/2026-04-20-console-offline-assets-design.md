# Console Offline Assets Design

## Goal

将 `console` 运行时依赖的远程图片、图标和字体全部收拢为仓库内本地静态资源，确保桌面端在内网或离线环境下不再向外网请求这些资源。

## Scope

本次仅处理 `console` 运行时资源，不处理以下内容：

- `website` 目录中的文档站图片和截图
- `README.md`、`README_zh.md` 中的外链图片
- 第三方 npm 包内置图标资源

纳入本次范围的运行时资源包括：

- 登录页 logo
- Header logo
- favicon
- 更新弹窗 banner 背景图
- Chat 欢迎页 avatar
- 渠道图标
- 模型提供商图标
- `console/index.html` 中通过 Google Fonts 加载的字体

## Current State

当前 `console` 运行时仍存在多处远程资源引用：

- `console/index.html`
- `console/src/pages/Login/index.tsx`
- `console/src/layouts/Header.tsx`
- `console/src/layouts/index.module.less`
- `console/src/pages/Chat/OptionsPanel/defaultConfig.ts`
- `console/src/pages/Chat/index.tsx`
- `console/src/pages/Control/Channels/components/channelIcons.ts`
- `console/src/pages/Settings/Models/components/providerIcon.ts`

这些路径会在桌面端启动后直接请求公网 CDN 或 Google Fonts，不符合内网版本要求。

## Design

### Static Asset Layout

新增 `console/public/assets` 作为统一静态资源根目录，按用途分组：

- `console/public/assets/branding`
- `console/public/assets/channels`
- `console/public/assets/providers`
- `console/public/assets/chat`
- `console/public/assets/fonts`

Vite 会将 `public` 下资源原样复制到产物中，因此 HTML、TSX 和 LESS 都可以统一通过 `/assets/...` 绝对路径访问，避免为不同文件类型引入额外构建适配。

### Runtime Reference Strategy

运行时代码不再保留远程 URL，改为以下方式：

- favicon 与字体样式：直接在 `console/index.html` 使用本地路径
- logo、avatar、banner：抽成明确常量后在 TSX / 配置文件中引用
- 渠道图标、提供商图标：保留现有映射函数接口，但映射值改为 `/assets/...`
- LESS 中的背景图：直接改为本地 `/assets/...`

这样可以将 UI 行为保持不变，只替换资源来源。

### Font Localization

移除 `console/index.html` 中的 Google Fonts `preconnect` 与远程样式表引用，新增本地字体样式文件，例如 `console/public/assets/fonts/fonts.css`。

`fonts.css` 通过 `@font-face` 指向下载到仓库中的字体文件，并继续暴露当前页面已经使用的字体族：

- `Inter`
- `Lato`
- `Newsreader`

这样现有样式无需改名，只需要改字体来源。

### Code Organization

为减少散落字面量，新增一个 branding 资源常量模块，集中管理下列路径：

- 浅色 / 深色 logo
- favicon
- welcome avatar
- chat avatar
- update banner

渠道图标与 provider 图标则在现有文件上就地保留接口，避免引发调用方改动。

### Verification

完成后应满足以下条件：

1. `console` 运行时代码中不再包含远程图片或字体 URL。
2. `console` 构建结果中包含所需静态资源。
3. 登录页、Header、模型提供商列表、渠道列表、欢迎页和更新弹窗均正常显示资源。
4. 离线环境下启动桌面端时，不会因为上述资源缺失而白屏或出现破图。

## Risks And Mitigations

### 字体文件体积增加

本地化字体会增加打包体积。控制方式是仅下载当前实际使用的字重，避免把完整字体族全部打进仓库。

### 图标路径散落导致漏改

通过一次扫描 `console` 中远程资源引用，并为关键映射文件添加测试，防止后续回退到远程 URL。

### 视觉回归

通过保持原图资源和原字体家族名不变，将风险控制在资源来源切换，而不是 UI 重设计。
