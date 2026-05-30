import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { fetchChatAvatarUrl } from "../../api/client";
import { Icon } from "../Icon";

interface ChatAvatarProps {
  accountId: number | null;
  chatId: string;
  title: string;
  hasAvatar?: boolean;
  fallbackIcon?: LucideIcon;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function ChatAvatar({
  accountId,
  chatId,
  title,
  hasAvatar,
  fallbackIcon,
  className,
  size = "md",
}: ChatAvatarProps) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const shouldTryPhoto = hasAvatar !== false;

  useEffect(() => {
    if (!accountId || !shouldTryPhoto) {
      setSrc(null);
      setFailed(false);
      return;
    }

    let cancelled = false;

    fetchChatAvatarUrl(accountId, chatId)
      .then((url) => {
        if (cancelled) return;
        setSrc(url);
        setFailed(!url);
      })
      .catch(() => {
        if (!cancelled) {
          setSrc(null);
          setFailed(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [accountId, chatId, shouldTryPhoto]);

  const letter = (title || "?").slice(0, 1).toUpperCase();
  const showImage = Boolean(src) && !failed;

  return (
    <div className={`chat-avatar chat-avatar-${size}${className ? ` ${className}` : ""}`}>
      {showImage ? (
        <img src={src!} alt="" loading="lazy" onError={() => setFailed(true)} />
      ) : fallbackIcon ? (
        <Icon icon={fallbackIcon} size={size === "lg" ? "lg" : "sm"} />
      ) : (
        <span>{letter}</span>
      )}
    </div>
  );
}
