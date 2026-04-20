import { getHeaderFeatures } from "./headerFeatures";

export interface HeaderLinkItem {
  key: "changelog" | "docs" | "faq" | "github";
}

export function getHeaderLinkItems(): HeaderLinkItem[] {
  if (!getHeaderFeatures().externalLinksEnabled) {
    return [];
  }

  return [];
}
