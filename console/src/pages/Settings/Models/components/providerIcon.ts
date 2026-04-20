const PROVIDER_ICON_URLS: Record<string, string> = {
  modelscope: "/assets/providers/modelscope.png",
  "aliyun-codingplan": "/assets/providers/aliyun-codingplan.png",
  deepseek: "/assets/providers/deepseek.png",
  gemini: "/assets/providers/gemini.png",
  "azure-openai": "/assets/providers/azure-openai.png",
  "kimi-cn": "/assets/providers/kimi.png",
  "kimi-intl": "/assets/providers/kimi.png",
  anthropic: "/assets/providers/anthropic.png",
  ollama: "/assets/providers/ollama.png",
  "minimax-cn": "/assets/providers/minimax.png",
  minimax: "/assets/providers/minimax.png",
  openai: "/assets/providers/openai.png",
  dashscope: "/assets/providers/dashscope.png",
  lmstudio: "/assets/providers/lmstudio.png",
  "siliconflow-cn": "/assets/providers/siliconflow.png",
  "siliconflow-intl": "/assets/providers/siliconflow.png",
  "qwenpaw-local": "/assets/providers/qwenpaw-local.png",
  "zhipu-cn": "/assets/providers/zhipu.png",
  "zhipu-intl": "/assets/providers/zhipu.png",
  "zhipu-cn-codingplan": "/assets/providers/zhipu.png",
  "zhipu-intl-codingplan": "/assets/providers/zhipu.png",
  openrouter: "/assets/providers/openrouter.png",
  opencode: "/assets/providers/opencode.png",
};

const DEFAULT_PROVIDER_ICON_URL = "/assets/providers/default.jpg";

export const providerIcon = (provider: string) =>
  PROVIDER_ICON_URLS[provider] ?? DEFAULT_PROVIDER_ICON_URL;
