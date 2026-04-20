import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getHeaderLinkItems } from "./headerLinks";

describe("getHeaderLinkItems", () => {
  it("returns no external links for the internal build", () => {
    assert.deepEqual(getHeaderLinkItems(), []);
  });
});
