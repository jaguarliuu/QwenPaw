/** Bundled channel logos shared by Channel settings cards and Chat session list. */
export const CHANNEL_ICON_URLS: Record<string, string> = {
  dingtalk: "/assets/channels/dingtalk.png",
  voice: "/assets/channels/voice.png",
  qq: "/assets/channels/qq.png",
  feishu: "/assets/channels/feishu.png",
  xiaoyi: "/assets/channels/xiaoyi.png",
  telegram: "/assets/channels/telegram.png",
  mqtt: "/assets/channels/mqtt.png",
  imessage: "/assets/channels/imessage.png",
  discord: "/assets/channels/discord.png",
  mattermost: "/assets/channels/mattermost.png",
  matrix: "/assets/channels/matrix.png",
  console: "/assets/channels/console.png",
  wecom: "/assets/channels/wecom.png",
  wechat: "/assets/channels/weixin.png",
  weixin: "/assets/channels/weixin.png",
};

export const CHANNEL_DEFAULT_ICON_URL = "/assets/channels/default.png";

export function getChannelIconUrl(channelKey: string): string {
  return CHANNEL_ICON_URLS[channelKey] ?? CHANNEL_DEFAULT_ICON_URL;
}
