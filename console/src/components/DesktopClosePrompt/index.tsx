import { Button, Checkbox, Modal, Space, Typography } from "antd";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const DESKTOP_CLOSE_EVENT = "stategrid-desktop-close-request";

declare global {
  interface Window {
    pywebview?: {
      api?: {
        handle_close_choice?: (
          action: "minimize" | "exit" | "cancel",
          remember?: boolean,
        ) => Promise<void> | void;
      };
    };
  }
}

export default function DesktopClosePrompt() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [rememberChoice, setRememberChoice] = useState(false);

  useEffect(() => {
    const handleRequest = () => {
      setRememberChoice(false);
      setOpen(true);
    };

    window.addEventListener(DESKTOP_CLOSE_EVENT, handleRequest);
    return () => {
      window.removeEventListener(DESKTOP_CLOSE_EVENT, handleRequest);
    };
  }, []);

  const submitChoice = async (action: "minimize" | "exit" | "cancel") => {
    try {
      await window.pywebview?.api?.handle_close_choice?.(
        action,
        action === "cancel" ? false : rememberChoice,
      );
    } finally {
      setOpen(false);
      setRememberChoice(false);
    }
  };

  return (
    <Modal
      title={t("desktopClose.title")}
      open={open}
      closable={false}
      maskClosable={false}
      keyboard={false}
      footer={null}
      onCancel={() => submitChoice("cancel")}
    >
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Typography.Text>{t("desktopClose.description")}</Typography.Text>
        <Checkbox
          checked={rememberChoice}
          onChange={(event) => setRememberChoice(event.target.checked)}
        >
          {t("desktopClose.remember")}
        </Checkbox>
        <Space style={{ justifyContent: "flex-end", width: "100%" }}>
          <Button onClick={() => submitChoice("cancel")}>
            {t("desktopClose.cancel")}
          </Button>
          <Button onClick={() => submitChoice("minimize")}>
            {t("desktopClose.minimize")}
          </Button>
          <Button danger type="primary" onClick={() => submitChoice("exit")}>
            {t("desktopClose.exit")}
          </Button>
        </Space>
      </Space>
    </Modal>
  );
}
