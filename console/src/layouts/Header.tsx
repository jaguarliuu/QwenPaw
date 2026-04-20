import { Layout, Space } from "antd";
import LanguageSwitcher from "../components/LanguageSwitcher/index";
import ThemeToggleButton from "../components/ThemeToggleButton";
import styles from "./index.module.less";
import api from "../api";
import { useTheme } from "../contexts/ThemeContext";
import { useState, useEffect } from "react";
import {
  APP_DISPLAY_NAME,
  LOGIN_LOGO_DARK_PATH,
  LOGIN_LOGO_LIGHT_PATH,
} from "@/assets/branding";
import { getHeaderLinkItems } from "./headerLinks";
import { getHeaderFeatures } from "./headerFeatures";

const { Header: AntHeader } = Layout;

export default function Header() {
  const { isDark } = useTheme();
  const { externalLinksEnabled } = getHeaderFeatures();
  const headerLinkItems = externalLinksEnabled ? getHeaderLinkItems() : [];
  const [version, setVersion] = useState<string>("");

  useEffect(() => {
    api
      .getVersion()
      .then((res) => setVersion(res?.version ?? ""))
      .catch(() => {});
  }, []);

  return (
    <AntHeader className={styles.header}>
      <div className={styles.logoWrapper}>
        <img
          src={isDark ? LOGIN_LOGO_DARK_PATH : LOGIN_LOGO_LIGHT_PATH}
          alt={APP_DISPLAY_NAME}
          className={styles.logoImg}
        />
        <div className={styles.logoDivider} />
        {version && (
          <span className={`${styles.versionBadge} ${styles.versionBadgeDefault}`}>
            v{version}
          </span>
        )}
      </div>
      <Space size="middle">
        {externalLinksEnabled && headerLinkItems.length > 0 && (
          <div className={styles.headerDivider} />
        )}
        <LanguageSwitcher />
        <ThemeToggleButton />
      </Space>
    </AntHeader>
  );
}
