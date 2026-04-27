# StateGrid Upstream Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge useful upstream QwenPaw updates into the StateGrid Desktop fork without restoring deepseek, external channels, update links, or other removed internet-facing features.

**Architecture:** Apply a controlled file-by-file merge in four slices: backend/provider stability, desktop packaging/runtime, selected console improvements, and regression coverage. For every conflicted area, preserve the fork's product boundary first and only import the smallest upstream logic needed for reliability or usability.

**Tech Stack:** Python, FastAPI, Click, webview desktop wrapper, React, TypeScript, Vite, pytest

---

### Task 1: Lock scope and baseline files

**Files:**
- Modify: `docs/superpowers/specs/2026-04-27-stategrid-upstream-merge-design.md`
- Modify: `docs/superpowers/plans/2026-04-27-stategrid-upstream-merge.md`

- [ ] **Step 1: Confirm the selected upstream range and exclusions**

Run: `rtk git -C example/QwenPaw log --oneline d586bc11..HEAD | head -n 80`
Expected: shows recent upstream commits including provider, desktop, console, token usage, channel, and deepseek changes

- [ ] **Step 2: Record the preserved fork constraints in the spec**

Ensure the spec explicitly preserves:

```text
StateGrid Desktop branding
single exposed channel: console
hidden header links and hidden version text
disabled update logic
existing SMTP send_email tool
default close-window behavior
```

- [ ] **Step 3: Keep the plan scoped to backend, desktop, and selected UI work**

Ensure the plan excludes:

```text
deepseek-related files
external channel feature work
website/docs/release assets
restoring updater or public links
```

### Task 2: Merge provider and tool stability updates

**Files:**
- Modify: `src/qwenpaw/providers/openai_chat_model_compat.py`
- Modify: `src/qwenpaw/providers/openai_provider.py`
- Modify: `src/qwenpaw/providers/retry_chat_model.py`
- Modify: `src/qwenpaw/agents/model_factory.py`
- Modify: `src/qwenpaw/app/runner/session.py`
- Modify: `src/qwenpaw/agents/tools/send_file.py`
- Modify: `src/qwenpaw/agents/tools/view_media.py`
- Modify: `src/qwenpaw/agents/tools/shell.py`
- Modify: `src/qwenpaw/app/routers/files.py`
- Test: `tests/unit/providers/test_openai_provider.py`
- Test: `tests/unit/providers/test_retry_chat_model.py`
- Test: `tests/unit/agents/test_model_factory_message_normalization.py`
- Test: `tests/unit/agents/test_session.py`
- Test: `tests/unit/agents/tools/test_send_file.py`
- Test: `tests/unit/agents/tools/test_view_media.py`
- Test: `tests/unit/agents/tools/test_shell.py`

- [ ] **Step 1: Diff current fork vs upstream for the selected backend files**

Run:

```bash
rtk git diff --no-index \
  src/qwenpaw/providers/openai_provider.py \
  example/QwenPaw/src/qwenpaw/providers/openai_provider.py
```

Expected: shows upstream compatibility logic that can be transplanted without deepseek-specific code

- [ ] **Step 2: Add or update focused tests before larger edits**

Target behaviors to cover:

```python
def test_provider_uses_compat_wrapper_for_openai_like_streams(): ...
def test_retry_chat_model_retries_remote_protocol_errors(): ...
def test_model_factory_normalizes_string_content_parts(): ...
async def test_send_file_to_user_resolves_relative_paths(): ...
def test_view_image_returns_local_file_message_for_supported_input(): ...
```

- [ ] **Step 3: Implement the minimal compatible merge**

Import only the upstream logic needed for:

```python
# provider stability
# stream compatibility
# protocol retry handling
# safer message normalization
# file URL encoding / media preview improvements
# configurable shell timeout support where already compatible
```

- [ ] **Step 4: Run the targeted backend test set**

Run:

```bash
rtk pytest \
  tests/unit/providers/test_openai_provider.py \
  tests/unit/providers/test_retry_chat_model.py \
  tests/unit/agents/test_model_factory_message_normalization.py \
  tests/unit/agents/test_session.py \
  tests/unit/agents/tools/test_send_file.py \
  tests/unit/agents/tools/test_view_media.py \
  tests/unit/agents/tools/test_shell.py -q
```

Expected: all selected tests pass

### Task 3: Merge desktop runtime and packaging improvements

**Files:**
- Modify: `src/qwenpaw/cli/desktop_cmd.py`
- Modify: `src/qwenpaw/cli/main.py`
- Modify: `src/qwenpaw/utils/startup_display.py`
- Modify: `.github/workflows/desktop-release.yml`
- Test: `tests/unit/cli/test_desktop_cmd.py`
- Test: `tests/unit/pack/test_desktop_nsi.py`

- [ ] **Step 1: Compare upstream desktop runtime changes against the forked desktop command**

Run:

```bash
rtk git diff --no-index \
  src/qwenpaw/cli/desktop_cmd.py \
  example/QwenPaw/src/qwenpaw/cli/desktop_cmd.py
```

Expected: a large diff showing upstream runtime fixes mixed with fork-specific branding and close behavior

- [ ] **Step 2: Preserve fork-specific desktop constants and disabled update behavior**

Keep these values intact:

```python
_DESKTOP_WINDOW_TITLE = "StateGrid Desktop"
# keep updater-related toggles disabled
# keep current close-window default behavior
```

- [ ] **Step 3: Import only the safe runtime improvements and matching tests**

Focus on:

```text
Windows ctypes fallbacks
desktop startup robustness
installer visibility/uninstall metadata
tests that assert the branded installer output
```

- [ ] **Step 4: Run desktop-focused tests**

Run:

```bash
rtk pytest tests/unit/cli/test_desktop_cmd.py tests/unit/pack/test_desktop_nsi.py -q
```

Expected: all desktop tests pass

### Task 4: Merge selected console improvements without breaking product trims

**Files:**
- Modify: `console/src/pages/Agent/Tools/index.tsx`
- Modify: `console/src/pages/Agent/Tools/useTools.ts`
- Modify: `console/src/pages/Agent/Skills/index.tsx`
- Modify: `console/src/pages/Agent/Skills/useSkillsPage.tsx`
- Modify: `console/src/pages/Agent/Workspace/components/FileEditor.tsx`
- Modify: `console/src/pages/Control/Sessions/index.tsx`
- Modify: `console/src/pages/Control/Sessions/components/columns.tsx`
- Modify: `console/src/pages/Settings/Models/components/providerIcon.ts`
- Modify: `console/src/locales/zh.json`
- Modify: `console/src/locales/en.json`
- Modify: `console/src/layouts/Header.tsx`
- Modify: `console/src/layouts/headerLinks.ts`
- Modify: `console/src/layouts/navigationFeatures.ts`
- Test: `console/src/layouts/headerLinks.test.ts`
- Test: `console/src/layouts/navigationFeatures.test.ts`
- Test: `console/src/pages/Chat/OptionsPanel/defaultConfig.test.ts`

- [ ] **Step 1: Diff only the selected UI files against upstream**

Run one file at a time, for example:

```bash
rtk git diff --no-index \
  console/src/pages/Agent/Tools/index.tsx \
  example/QwenPaw/console/src/pages/Agent/Tools/index.tsx
```

Expected: upstream UI improvements are visible without requiring full header/nav replacement

- [ ] **Step 2: Preserve the fork-specific header and navigation feature gates**

Keep tests and code that enforce:

```ts
getHeaderLinkItems() === []
getNavigationFeatures().showVersion === false
```

- [ ] **Step 3: Transplant only the logic that improves tools, skills, files, and sessions**

Do not restore:

```text
GitHub / docs / FAQ links
multi-channel control UX
version display
updater entry points
```

- [ ] **Step 4: Build and run targeted frontend checks**

Run:

```bash
rtk npm --prefix console test -- --run \
  src/layouts/headerLinks.test.ts \
  src/layouts/navigationFeatures.test.ts \
  src/pages/Chat/OptionsPanel/defaultConfig.test.ts
rtk npm --prefix console run build
```

Expected: tests pass and Vite build succeeds

### Task 5: Re-validate fork boundaries and summarize merged features

**Files:**
- Modify: `src/qwenpaw/config/utils.py`
- Modify: `tests/unit/config/test_available_channels.py`
- Modify: `docs/superpowers/specs/2026-04-27-stategrid-upstream-merge-design.md`

- [ ] **Step 1: Verify the available channel boundary remains intact**

Run:

```bash
rtk pytest tests/unit/config/test_available_channels.py -q
```

Expected: only `console` is exposed

- [ ] **Step 2: Run a final targeted regression sweep**

Run:

```bash
rtk pytest \
  tests/unit/config/test_available_channels.py \
  tests/unit/cli/test_desktop_cmd.py \
  tests/unit/pack/test_desktop_nsi.py \
  tests/unit/providers/test_openai_provider.py \
  tests/unit/providers/test_retry_chat_model.py \
  tests/unit/agents/tools/test_send_email.py \
  tests/unit/agents/tools/test_send_file.py \
  tests/unit/agents/tools/test_view_media.py -q
```

Expected: regression suite passes

- [ ] **Step 3: Produce a human-readable merge summary**

Summarize by category:

```text
backend/provider stability updates
desktop/runtime improvements
selected console enhancements
explicitly excluded upstream features
```
