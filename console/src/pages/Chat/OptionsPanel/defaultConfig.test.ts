import assert from "node:assert/strict";
import { describe, it } from "node:test";
import defaultConfig from "./defaultConfig";

describe("default chat config branding", () => {
  it("shows the internal desktop brand name", () => {
    assert.equal(defaultConfig.theme.leftHeader.title, "StateGrid Desktop");
  });
});
