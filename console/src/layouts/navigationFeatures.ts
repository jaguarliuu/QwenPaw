export interface NavigationFeatures {
  channelsEnabled: boolean;
}

export function getNavigationFeatures(): NavigationFeatures {
  return {
    channelsEnabled: false,
  };
}
