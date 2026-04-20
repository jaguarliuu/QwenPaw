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
