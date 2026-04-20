export interface HeaderFeatures {
  externalLinksEnabled: boolean;
  updateChecksEnabled: boolean;
}

export function getHeaderFeatures(): HeaderFeatures {
  return {
    externalLinksEnabled: false,
    updateChecksEnabled: false,
  };
}
