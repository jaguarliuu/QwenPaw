import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getNavigationFeatures } from "./navigationFeatures";

describe("getNavigationFeatures", () => {
  it("hides the channels route for the internal desktop build", () => {
    assert.deepEqual(getNavigationFeatures(), {
      channelsEnabled: false,
    });
  });
});
