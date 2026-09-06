import { Plus, X } from 'lucide-react';
import { useWidgetConfig } from '../config';
import { useSession } from '../hooks/useSession';

interface IconButtonProps {
  title: string;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}

function IconButton({ title, onClick, disabled, children }: IconButtonProps) {
  return (
    <button
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
      className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-gray-100 text-gray-500 transition-colors hover:bg-gray-200 hover:text-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  );
}

export interface ChatHeaderProps {
  onClose: () => void;
}

export default function ChatHeader({ onClose }: ChatHeaderProps) {
  const { iconUrl, agentName } = useWidgetConfig();
  const { status, restart } = useSession();

  return (
    <div className="flex shrink-0 items-center justify-between border-b border-gray-200 px-4 py-3">
      <div className="flex items-center gap-2">
        {iconUrl ? (
          <img
            src={iconUrl}
            alt=""
            className="h-8 w-8 shrink-0 rounded-full object-cover"
          />
        ) : (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-500 text-sm font-medium text-white">
            {agentName.trim().charAt(0).toUpperCase()}
          </span>
        )}
        <span className="text-sm font-semibold text-gray-800">{agentName}</span>
      </div>
      <div className="flex items-center gap-1">
        <IconButton title="New chat" onClick={restart} disabled={status === 'connecting'}>
          <Plus size={16} />
        </IconButton>
        <IconButton title="Close" onClick={onClose}>
          <X size={14} />
        </IconButton>
      </div>
    </div>
  );
}
