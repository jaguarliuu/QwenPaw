import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  APP_DISPLAY_NAME,
  APP_FAVICON_PATH,
  CHAT_AVATAR_PATH,
  LOGIN_LOGO_DARK_PATH,
  LOGIN_LOGO_LIGHT_PATH,
  WELCOME_AVATAR_PATH,
  UPDATE_BANNER_PATH,
} from "./branding";

describe("branding asset paths", () => {
  it("uses bundled assets for all branding paths", () => {
    for (const path of [
      APP_FAVICON_PATH,
      CHAT_AVATAR_PATH,
      LOGIN_LOGO_DARK_PATH,
      LOGIN_LOGO_LIGHT_PATH,
      WELCOME_AVATAR_PATH,
      UPDATE_BANNER_PATH,
    ]) {
      assert.match(path, /^\/assets\//);
      assert.doesNotMatch(path, /^https?:\/\//);
    }
  });

  it("uses the localized StateGrid branding assets", () => {
    assert.equal(APP_DISPLAY_NAME, "StateGrid Desktop");
    assert.equal(APP_FAVICON_PATH, "/assets/logo/icon-local.ico");
    assert.equal(LOGIN_LOGO_LIGHT_PATH, "/assets/logo/icon-local.png");
    assert.equal(LOGIN_LOGO_DARK_PATH, "/assets/logo/icon-local.png");
  });
});
