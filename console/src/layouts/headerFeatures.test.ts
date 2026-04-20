import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getHeaderFeatures } from "./headerFeatures";

describe("getHeaderFeatures", () => {
  it("disables external links and update checks for the internal build", () => {
    assert.deepEqual(getHeaderFeatures(), {
      externalLinksEnabled: false,
      updateChecksEnabled: false,
    });
  });
});
