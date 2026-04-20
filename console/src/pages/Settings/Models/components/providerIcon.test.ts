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
