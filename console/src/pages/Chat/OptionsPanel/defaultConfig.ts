import type { TFunction } from "i18next";
import { APP_DISPLAY_NAME, WELCOME_AVATAR_PATH } from "@/assets/branding";

const defaultConfig = {
  theme: {
    colorPrimary: "#FF7F16",
    darkMode: false,
    prefix: "qwenpaw",
    leftHeader: {
      logo: "",
      title: APP_DISPLAY_NAME,
    },
  },
  sender: {
    attachments: true,
    maxLength: 10000,
    disclaimer: "Works for you, grows with you",
  },
  welcome: {
    greeting: "Hello, how can I help you today?",
    description:
      "I am a helpful assistant that can help you with your questions.",
    avatar: WELCOME_AVATAR_PATH,
    prompts: [
      {
        value: "Let's start a new journey!",
      },
      {
        value: "Can you tell me what skills you have?",
      },
    ],
  },
  api: {
    baseURL: "",
    token: "",
  },
} as const;

export function getDefaultConfig(t: TFunction) {
  return {
    ...defaultConfig,
    sender: {
      ...defaultConfig.sender,
      disclaimer: t("chat.disclaimer"),
    },
    welcome: {
      ...defaultConfig.welcome,
      greeting: t("chat.greeting"),
      description: t("chat.description"),
      prompts: [{ value: t("chat.prompt1") }, { value: t("chat.prompt2") }],
    },
  };
}

export default defaultConfig;

export type DefaultConfig = typeof defaultConfig;
