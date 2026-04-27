import React, { useCallback, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import styles from "./index.module.less";

export interface ContextMenuItem {
  key: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
  divider?: boolean;
  onClick?: () => void;
}

export interface ContextMenuProps {
  visible: boolean;
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export function ContextMenu({
  visible,
  x,
  y,
  items,
  onClose,
}: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  const adjustPosition = useCallback(() => {
    if (!menuRef.current || !visible) {
      return;
    }

    const rect = menuRef.current.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let adjustedX = x;
    let adjustedY = y;

    if (x + rect.width > viewportWidth) {
      adjustedX = viewportWidth - rect.width - 8;
    }
    if (y + rect.height > viewportHeight) {
      adjustedY = viewportHeight - rect.height - 8;
    }

    menuRef.current.style.left = `${Math.max(8, adjustedX)}px`;
    menuRef.current.style.top = `${Math.max(8, adjustedY)}px`;
  }, [visible, x, y]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    requestAnimationFrame(adjustPosition);

    const handleClickOutside = (event: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };
    const handleScroll = () => onClose();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("scroll", handleScroll, true);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", onClose);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("scroll", handleScroll, true);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", onClose);
    };
  }, [adjustPosition, onClose, visible]);

  if (!visible) {
    return null;
  }

  return createPortal(
    <div
      ref={menuRef}
      className={styles.contextMenu}
      style={{ left: x, top: y }}
    >
      {items.map((item) => {
        if (item.divider) {
          return <div key={item.key} className={styles.divider} />;
        }

        const className = [
          styles.menuItem,
          item.danger ? styles.danger : "",
          item.disabled ? styles.disabled : "",
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <div
            key={item.key}
            className={className}
            onClick={() => {
              if (item.disabled) {
                return;
              }
              item.onClick?.();
              onClose();
            }}
          >
            {item.icon ? (
              <span className={styles.menuIcon}>{item.icon}</span>
            ) : null}
            <span className={styles.menuLabel}>{item.label}</span>
          </div>
        );
      })}
    </div>,
    document.body,
  );
}

export function useContextMenu() {
  const [state, setState] = React.useState({
    visible: false,
    x: 0,
    y: 0,
  });

  const show = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setState({
      visible: true,
      x: event.clientX,
      y: event.clientY,
    });
  }, []);

  const hide = useCallback(() => {
    setState((prev) => ({ ...prev, visible: false }));
  }, []);

  return {
    ...state,
    show,
    hide,
  };
}
