import { useEffect, useMemo } from "react";
import { Card, Switch, Empty, Button } from "@agentscope-ai/design";
import { Form, Input, InputNumber, Switch as AntSwitch } from "antd";
import {
  EyeOutlined,
  EyeInvisibleOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useTools } from "./useTools";
import { useTranslation } from "react-i18next";
import type { ToolInfo } from "../../../api/modules/tools";
import { PageHeader } from "@/components/PageHeader";
import styles from "./index.module.less";

const ICON_PALETTE = [
  "#f56a00",
  "#7265e6",
  "#ffbf00",
  "#00a2ae",
  "#87d068",
  "#1890ff",
  "#eb2f96",
  "#722ed1",
];

function hashStringToIndex(value: string, mod: number): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) % mod;
}

function ToolIcon({ icon, name }: { icon: string; name: string }) {
  if (icon) {
    return <span>{icon}</span>;
  }

  const letter = name.charAt(0).toUpperCase();
  const backgroundColor =
    ICON_PALETTE[hashStringToIndex(name, ICON_PALETTE.length)];

  return (
    <span className={styles.toolIconFallback} style={{ backgroundColor }}>
      {letter}
    </span>
  );
}

export default function ToolsPage() {
  const { t } = useTranslation();
  const {
    tools,
    emailConfig,
    loading,
    batchLoading,
    emailSaving,
    toggleEnabled,
    toggleAsyncExecution,
    enableAll,
    disableAll,
    saveEmailConfig,
  } = useTools();
  const [form] = Form.useForm();
  const handleToggle = (tool: ToolInfo) => {
    toggleEnabled(tool);
  };

  const hasDisabledTools = useMemo(
    () => tools.some((tool) => !tool.enabled),
    [tools],
  );
  const hasEnabledTools = useMemo(
    () => tools.some((tool) => tool.enabled),
    [tools],
  );

  useEffect(() => {
    form.setFieldsValue(emailConfig);
  }, [emailConfig, form]);

  return (
    <div className={styles.toolsPage}>
      <PageHeader
        items={[{ title: t("nav.agent") }, { title: t("tools.title") }]}
        extra={
          <div className={styles.headerAction}>
            <Switch
              checked={hasEnabledTools && !hasDisabledTools}
              onChange={() => (hasDisabledTools ? enableAll() : disableAll())}
              disabled={batchLoading || loading}
              checkedChildren={t("tools.enableAll")}
              unCheckedChildren={t("tools.disableAll")}
            />
          </div>
        }
      />
      <div className={styles.toolsContainer}>
        {loading ? (
          <div className={styles.loading}>
            <p>{t("common.loading")}</p>
          </div>
        ) : tools.length === 0 ? (
          <Empty description={t("tools.emptyState")} />
        ) : (
          <div className={styles.configSection}>
            <div className={styles.toolsGrid}>
              {tools.map((tool) => (
                <Card
                  key={tool.name}
                  className={`${styles.toolCard} ${
                    tool.enabled ? styles.enabledCard : ""
                  }`}
                >
                  <div className={styles.cardHeader}>
                    <h3 className={styles.toolName}>
                      <ToolIcon icon={tool.icon} name={tool.name} /> {tool.name}
                    </h3>
                    <div className={styles.statusContainer}>
                      <span className={styles.statusDot} />
                      <span className={styles.statusText}>
                        {tool.enabled
                          ? t("common.enabled")
                          : t("common.disabled")}
                      </span>
                    </div>
                  </div>

                  <p className={styles.toolDescription}>{tool.description}</p>

                  <div className={styles.cardFooter}>
                    {tool.name === "execute_shell_command" && (
                      <Button
                        className={styles.toggleButton}
                        onClick={() => toggleAsyncExecution(tool)}
                        disabled={!tool.enabled}
                        icon={
                          tool.async_execution ? (
                            <ThunderboltOutlined />
                          ) : (
                            <ClockCircleOutlined />
                          )
                        }
                      >
                        {tool.async_execution
                          ? t("tools.asyncExecutionEnabled")
                          : t("tools.asyncExecutionDisabled")}
                      </Button>
                    )}
                    <Button
                      className={styles.toggleButton}
                      onClick={() => handleToggle(tool)}
                      icon={
                        tool.enabled ? <EyeInvisibleOutlined /> : <EyeOutlined />
                      }
                    >
                      {tool.enabled ? t("common.disable") : t("common.enable")}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>

            <Card className={styles.configCard}>
              <div className={styles.configHeader}>
                <div>
                  <h3 className={styles.configTitle}>
                    {t("tools.emailConfigTitle")}
                  </h3>
                  <p className={styles.configDescription}>
                    {t("tools.emailConfigDescription")}
                  </p>
                </div>
              </div>
              <Form
                form={form}
                layout="vertical"
                className={styles.configForm}
                initialValues={emailConfig}
                onFinish={saveEmailConfig}
              >
                <div className={styles.configGrid}>
                  <Form.Item
                    name="host"
                    label={t("tools.email.host")}
                    rules={[{ required: true, message: t("tools.email.hostRequired") }]}
                  >
                    <Input />
                  </Form.Item>
                  <Form.Item
                    name="port"
                    label={t("tools.email.port")}
                    rules={[{ required: true, message: t("tools.email.portRequired") }]}
                  >
                    <InputNumber min={1} max={65535} style={{ width: "100%" }} />
                  </Form.Item>
                  <Form.Item name="username" label={t("tools.email.username")}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="password" label={t("tools.email.password")}>
                    <Input.Password />
                  </Form.Item>
                  <Form.Item
                    name="from_address"
                    label={t("tools.email.fromAddress")}
                    rules={[
                      {
                        required: true,
                        message: t("tools.email.fromAddressRequired"),
                      },
                    ]}
                  >
                    <Input />
                  </Form.Item>
                  <Form.Item name="from_name" label={t("tools.email.fromName")}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="reply_to" label={t("tools.email.replyTo")}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="timeout_sec" label={t("tools.email.timeout")}>
                    <InputNumber min={1} max={300} style={{ width: "100%" }} />
                  </Form.Item>
                </div>
                <div className={styles.toggleRow}>
                  <Form.Item
                    name="use_ssl"
                    label={t("tools.email.useSsl")}
                    valuePropName="checked"
                  >
                    <AntSwitch />
                  </Form.Item>
                  <Form.Item
                    name="use_starttls"
                    label={t("tools.email.useStarttls")}
                    valuePropName="checked"
                  >
                    <AntSwitch />
                  </Form.Item>
                  <Form.Item
                    name="allow_untrusted_tls"
                    label={t("tools.email.allowUntrustedTls")}
                    valuePropName="checked"
                  >
                    <AntSwitch />
                  </Form.Item>
                </div>
                <div className={styles.formActions}>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={emailSaving}
                  >
                    {t("common.save")}
                  </Button>
                </div>
              </Form>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
