import { request } from "../request";

export interface ToolInfo {
  name: string;
  enabled: boolean;
  description: string;
  async_execution: boolean;
  icon: string;
}

export interface EmailToolConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  from_address: string;
  from_name: string;
  reply_to: string;
  use_ssl: boolean;
  use_starttls: boolean;
  timeout_sec: number;
  allow_untrusted_tls: boolean;
}

export const toolsApi = {
  /**
   * List all built-in tools
   */
  listTools: () => request<ToolInfo[]>("/tools"),

  /**
   * Toggle tool enabled status
   */
  toggleTool: (toolName: string) =>
    request<ToolInfo>(`/tools/${encodeURIComponent(toolName)}/toggle`, {
      method: "PATCH",
    }),

  /**
   * Update tool async_execution setting
   */
  updateAsyncExecution: (toolName: string, asyncExecution: boolean) =>
    request<ToolInfo>(
      `/tools/${encodeURIComponent(toolName)}/async-execution`,
      {
        method: "PATCH",
        body: JSON.stringify({ async_execution: asyncExecution }),
      },
    ),

  /**
   * Get SMTP configuration for the send_email tool
   */
  getSendEmailConfig: () => request<EmailToolConfig>("/tools/send_email/config"),

  /**
   * Update SMTP configuration for the send_email tool
   */
  updateSendEmailConfig: (config: EmailToolConfig) =>
    request<EmailToolConfig>("/tools/send_email/config", {
      method: "PUT",
      body: JSON.stringify(config),
    }),
};
