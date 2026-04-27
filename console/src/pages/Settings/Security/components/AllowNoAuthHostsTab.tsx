import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Input,
  Popconfirm,
  Table,
  Tag,
} from "@agentscope-ai/design";
import { Space } from "antd";
import { PlusCircleOutlined, DeleteOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import api from "../../../../api";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import styles from "../index.module.less";

interface AllowNoAuthHostsTabProps {
  onSave?: (handlers: {
    save: () => Promise<void>;
    reset: () => void;
    saving: boolean;
  }) => void;
}

const DEFAULT_HOSTS = new Set(["127.0.0.1", "::1"]);

export function AllowNoAuthHostsTab({
  onSave,
}: AllowNoAuthHostsTabProps = {}) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [hosts, setHosts] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newHost, setNewHost] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getAllowNoAuthHosts();
      setHosts(data?.hosts ?? ["127.0.0.1", "::1"]);
    } catch {
      message.error(t("security.allowNoAuthHosts.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [message, t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const isValidIP = useCallback((value: string) => {
    const ipv4 =
      /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/;
    const ipv6 =
      /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:))$/;
    return ipv4.test(value) || ipv6.test(value);
  }, []);

  const handleAdd = useCallback(() => {
    const trimmed = newHost.trim();
    if (!trimmed) {
      return;
    }
    if (!isValidIP(trimmed)) {
      message.error(t("security.allowNoAuthHosts.invalidIP"));
      return;
    }
    if (hosts.includes(trimmed)) {
      message.warning(t("security.allowNoAuthHosts.duplicate"));
      return;
    }
    setHosts((prev) => [...prev, trimmed]);
    setNewHost("");
  }, [hosts, isValidIP, message, newHost, t]);

  const handleRemove = useCallback((host: string) => {
    setHosts((prev) => prev.filter((item) => item !== host));
  }, []);

  const handleSave = useCallback(async () => {
    try {
      setSaving(true);
      await api.updateAllowNoAuthHosts({ hosts });
      message.success(t("security.allowNoAuthHosts.saveSuccess"));
    } catch {
      message.error(t("security.allowNoAuthHosts.saveFailed"));
    } finally {
      setSaving(false);
    }
  }, [hosts, message, t]);

  const handleReset = useCallback(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    onSave?.({ save: handleSave, reset: handleReset, saving });
  }, [handleReset, handleSave, onSave, saving]);

  const dataSource = hosts.map((host) => ({ key: host, host }));
  const columns = [
    {
      title: t("security.allowNoAuthHosts.ipAddress"),
      dataIndex: "host",
      key: "host",
      render: (host: string) => (
        <Space>
          <code>{host}</code>
          {DEFAULT_HOSTS.has(host) && (
            <Tag color="orange">{t("security.allowNoAuthHosts.default")}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t("security.allowNoAuthHosts.actions"),
      key: "actions",
      width: 80,
      render: (_: unknown, record: { host: string }) => (
        <Popconfirm
          title={t("security.allowNoAuthHosts.removeConfirm")}
          onConfirm={() => handleRemove(record.host)}
          okText={t("common.delete")}
          cancelText={t("common.cancel")}
        >
          <Button type="text" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      <Alert
        type="warning"
        showIcon
        message={t("security.allowNoAuthHosts.warningTitle")}
        description={t("security.allowNoAuthHosts.warningDescription")}
        style={{ marginBottom: 16 }}
      />

      <Card className={styles.formCard}>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            value={newHost}
            onChange={(e) => setNewHost(e.target.value)}
            placeholder={t("security.allowNoAuthHosts.inputPlaceholder")}
            onPressEnter={handleAdd}
            allowClear
          />
          <Button
            type="primary"
            icon={<PlusCircleOutlined />}
            onClick={handleAdd}
            disabled={!newHost.trim()}
          >
            {t("security.allowNoAuthHosts.add")}
          </Button>
        </Space.Compact>
      </Card>

      <Card className={styles.tableCard}>
        <Table
          columns={columns}
          dataSource={dataSource}
          loading={loading}
          pagination={false}
          size="middle"
          locale={{
            emptyText: t("security.allowNoAuthHosts.empty"),
          }}
        />
      </Card>
    </>
  );
}
