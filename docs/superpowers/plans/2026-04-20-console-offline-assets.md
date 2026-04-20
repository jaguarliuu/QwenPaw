# Console Offline Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `console` 运行时依赖的远程图片、图标和字体全部改为仓库内本地静态资源，确保桌面端在内网或离线环境中正常显示。

**Architecture:** 统一使用 `console/public/assets` 承载静态资源，通过 `/assets/...` 绝对路径在 `index.html`、TSX 和 LESS 中引用。为 branding 类资源新增集中常量模块；渠道图标和 provider 图标保留原有映射接口，仅替换映射值并用测试兜底，防止后续重新引入远程 URL。

**Tech Stack:** Vite, React, TypeScript, LESS, Node `node:test`

---

## File Structure

- Create: `console/public/assets/branding/*`
- Create: `console/public/assets/channels/*`
- Create: `console/public/assets/providers/*`
- Create: `console/public/assets/chat/*`
- Create: `console/public/assets/fonts/*`
- Create: `console/src/assets/branding.ts`
- Create: `console/src/assets/branding.test.ts`
- Create: `console/src/pages/Control/Channels/components/channelIcons.test.ts`
- Create: `console/src/pages/Settings/Models/components/providerIcon.test.ts`
- Modify: `console/index.html`
- Modify: `console/src/pages/Login/index.tsx`
- Modify: `console/src/layouts/Header.tsx`
- Modify: `console/src/layouts/index.module.less`
- Modify: `console/src/pages/Chat/OptionsPanel/defaultConfig.ts`
- Modify: `console/src/pages/Chat/index.tsx`
- Modify: `console/src/pages/Control/Channels/components/channelIcons.ts`
- Modify: `console/src/pages/Settings/Models/components/providerIcon.ts`

### Task 1: Add failing tests for local asset contracts

**Files:**
- Create: `console/src/assets/branding.test.ts`
- Create: `console/src/pages/Control/Channels/components/channelIcons.test.ts`
- Create: `console/src/pages/Settings/Models/components/providerIcon.test.ts`
- Modify: `console/src/pages/Control/Channels/components/channelIcons.ts`
- Modify: `console/src/pages/Settings/Models/components/providerIcon.ts`

- [ ] **Step 1: Write the failing test for branding constants**

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  APP_FAVICON_PATH,
  CHAT_AVATAR_PATH,
  LOGIN_LOGO_DARK_PATH,
  LOGIN_LOGO_LIGHT_PATH,
  UPDATE_BANNER_PATH,
} from "./branding";

describe("branding asset paths", () => {
  it("uses bundled assets for all branding paths", () => {
    for (const path of [
      APP_FAVICON_PATH,
      CHAT_AVATAR_PATH,
      LOGIN_LOGO_DARK_PATH,
      LOGIN_LOGO_LIGHT_PATH,
      UPDATE_BANNER_PATH,
    ]) {
      assert.match(path, /^\/assets\//);
      assert.doesNotMatch(path, /^https?:\/\//);
    }
  });
});
```

- [ ] **Step 2: Write the failing test for channel icon mappings**

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  CHANNEL_DEFAULT_ICON_URL,
  CHANNEL_ICON_URLS,
  getChannelIconUrl,
} from "./channelIcons";

describe("channel icon asset paths", () => {
  it("keeps every channel icon local", () => {
    for (const path of Object.values(CHANNEL_ICON_URLS)) {
      assert.match(path, /^\/assets\/channels\//);
      assert.doesNotMatch(path, /^https?:\/\//);
    }
    assert.match(CHANNEL_DEFAULT_ICON_URL, /^\/assets\/channels\//);
  });

  it("falls back to the bundled default icon", () => {
    assert.equal(getChannelIconUrl("missing"), CHANNEL_DEFAULT_ICON_URL);
  });
});
```

- [ ] **Step 3: Write the failing test for provider icon mappings**

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { providerIcon } from "./providerIcon";

describe("provider icon asset paths", () => {
  it("uses bundled assets for known providers", () => {
    for (const provider of [
      "openai",
      "deepseek",
      "anthropic",
      "dashscope",
      "qwenpaw-local",
    ]) {
      assert.match(providerIcon(provider), /^\/assets\/providers\//);
      assert.doesNotMatch(providerIcon(provider), /^https?:\/\//);
    }
  });

  it("uses a bundled default icon for unknown providers", () => {
    assert.match(providerIcon("unknown-provider"), /^\/assets\/providers\//);
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run:

```bash
rtk node --test console/src/assets/branding.test.ts console/src/pages/Control/Channels/components/channelIcons.test.ts console/src/pages/Settings/Models/components/providerIcon.test.ts
```

Expected:

```text
FAIL because branding.ts does not exist yet and the icon mappings still return remote URLs
```

- [ ] **Step 5: Commit**

```bash
git add console/src/assets/branding.test.ts console/src/pages/Control/Channels/components/channelIcons.test.ts console/src/pages/Settings/Models/components/providerIcon.test.ts
git commit -m "test(console): add local asset path coverage"
```

### Task 2: Add bundled assets and local font stylesheet

**Files:**
- Create: `console/public/assets/branding/*`
- Create: `console/public/assets/channels/*`
- Create: `console/public/assets/providers/*`
- Create: `console/public/assets/chat/*`
- Create: `console/public/assets/fonts/fonts.css`
- Create: `console/public/assets/fonts/*.woff2`

- [ ] **Step 1: Download and place branding, chat, channel, and provider assets under public**

```text
Place the downloaded files under:
- console/public/assets/branding/
- console/public/assets/channels/
- console/public/assets/providers/
- console/public/assets/chat/
Use stable filenames such as:
- logo-light.svg
- logo-dark.svg
- favicon.svg
- update-banner.png
- welcome-avatar.png
- channel-dingtalk.png
- provider-openai.png
```

- [ ] **Step 2: Add a local font stylesheet**

```css
@font-face {
  font-family: "Inter";
  src: url("/assets/fonts/inter-400.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Inter";
  src: url("/assets/fonts/inter-500.woff2") format("woff2");
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Inter";
  src: url("/assets/fonts/inter-600.woff2") format("woff2");
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}
```

- [ ] **Step 3: Add remaining font faces used by the page**

```css
@font-face {
  font-family: "Lato";
  src: url("/assets/fonts/lato-400.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Lato";
  src: url("/assets/fonts/lato-700.woff2") format("woff2");
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Newsreader";
  src: url("/assets/fonts/newsreader-400.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Newsreader";
  src: url("/assets/fonts/newsreader-500.woff2") format("woff2");
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Newsreader";
  src: url("/assets/fonts/newsreader-400-italic.woff2") format("woff2");
  font-weight: 400;
  font-style: italic;
  font-display: swap;
}
```

- [ ] **Step 4: Verify files exist locally**

Run:

```bash
rtk rg --files console/public/assets
```

Expected:

```text
Lists branding, channels, providers, chat, and fonts asset files with no missing directories
```

- [ ] **Step 5: Commit**

```bash
git add console/public/assets
git commit -m "feat(console): bundle offline runtime assets"
```

### Task 3: Rewire the console to local asset paths

**Files:**
- Create: `console/src/assets/branding.ts`
- Modify: `console/index.html`
- Modify: `console/src/pages/Login/index.tsx`
- Modify: `console/src/layouts/Header.tsx`
- Modify: `console/src/layouts/index.module.less`
- Modify: `console/src/pages/Chat/OptionsPanel/defaultConfig.ts`
- Modify: `console/src/pages/Chat/index.tsx`
- Modify: `console/src/pages/Control/Channels/components/channelIcons.ts`
- Modify: `console/src/pages/Settings/Models/components/providerIcon.ts`

- [ ] **Step 1: Implement centralized branding constants**

```ts
export const APP_FAVICON_PATH = "/assets/branding/favicon.svg";
export const LOGIN_LOGO_LIGHT_PATH = "/assets/branding/logo-light.svg";
export const LOGIN_LOGO_DARK_PATH = "/assets/branding/logo-dark.svg";
export const CHAT_AVATAR_PATH = "/assets/chat/welcome-avatar.png";
export const UPDATE_BANNER_PATH = "/assets/branding/update-banner.png";
```

- [ ] **Step 2: Update HTML to local favicon and local fonts**

```html
<link rel="icon" type="image/svg+xml" href="/assets/branding/favicon.svg" />
<link rel="stylesheet" href="/assets/fonts/fonts.css" />
```

Remove:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  rel="stylesheet"
  href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Lato:wght@400;700&family=Newsreader:ital,wght@0,400;0,500;1,400&display=swap"
/>
```

- [ ] **Step 3: Update branding consumers to import local constants**

```ts
import {
  CHAT_AVATAR_PATH,
  LOGIN_LOGO_DARK_PATH,
  LOGIN_LOGO_LIGHT_PATH,
} from "@/assets/branding";
```

And replace runtime URLs:

```ts
src={isDark ? LOGIN_LOGO_DARK_PATH : LOGIN_LOGO_LIGHT_PATH}
avatar: CHAT_AVATAR_PATH
```

- [ ] **Step 4: Replace channel icon mapping values with local paths**

```ts
export const CHANNEL_ICON_URLS: Record<string, string> = {
  dingtalk: "/assets/channels/dingtalk.png",
  voice: "/assets/channels/voice.png",
  qq: "/assets/channels/qq.png",
};

export const CHANNEL_DEFAULT_ICON_URL = "/assets/channels/default.png";
```

- [ ] **Step 5: Replace provider icon mapping values with local paths**

```ts
case "openai":
  return "/assets/providers/openai.png";
case "deepseek":
  return "/assets/providers/deepseek.png";
default:
  return "/assets/providers/default.jpg";
```

- [ ] **Step 6: Replace the update banner background with a local path**

```less
.updateModalBanner {
  background: url("/assets/branding/update-banner.png") no-repeat center top;
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run:

```bash
rtk node --test console/src/assets/branding.test.ts console/src/pages/Control/Channels/components/channelIcons.test.ts console/src/pages/Settings/Models/components/providerIcon.test.ts
```

Expected:

```text
PASS for all local asset path tests
```

- [ ] **Step 8: Commit**

```bash
git add console/index.html console/src/assets/branding.ts console/src/pages/Login/index.tsx console/src/layouts/Header.tsx console/src/layouts/index.module.less console/src/pages/Chat/OptionsPanel/defaultConfig.ts console/src/pages/Chat/index.tsx console/src/pages/Control/Channels/components/channelIcons.ts console/src/pages/Settings/Models/components/providerIcon.ts
git commit -m "feat(console): switch runtime assets to bundled files"
```

### Task 4: Verify the console no longer depends on remote runtime assets

**Files:**
- Verify: `console/index.html`
- Verify: `console/src/**/*`

- [ ] **Step 1: Run a targeted remote asset scan**

Run:

```bash
rtk rg -n "https?://.*(png|svg|jpg|jpeg|webp|woff2?)|fonts.googleapis.com|fonts.gstatic.com" console/index.html console/src
```

Expected:

```text
No matches
```

- [ ] **Step 2: Build the console**

Run:

```bash
cd console && rtk npm run build
```

Expected:

```text
TypeScript build succeeds and Vite build emits the production bundle
```

- [ ] **Step 3: Spot-check bundled asset references in the build output**

Run:

```bash
rtk rg -n "/assets/" console/dist
```

Expected:

```text
Matches for branding, channel, provider, chat, and font assets in the built output
```

- [ ] **Step 4: Commit**

```bash
git add console
git commit -m "chore(console): verify offline asset packaging"
```
