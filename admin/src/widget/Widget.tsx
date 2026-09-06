import { useState } from "react";
import ChatHeader from "./components/ChatHeader";
import ChatPanel from "./components/ChatPanal";

export interface WidgetProps {
  waveColor: string;
  innerSize: number;
  outerSize: number;
  iconUrl?: string;
  panelWidth: number;
  panelHeight: number;
  panelBg: string;
}

export default function Widget({
  waveColor,
  innerSize,
  outerSize,
  iconUrl,
  panelWidth,
  panelHeight,
  panelBg,
}: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false);


  if (isOpen) {
    return (
      <div
        className="flex flex-col overflow-hidden rounded-xl shadow-2xl"
        style={{ width: panelWidth, height: panelHeight, background: panelBg }}
      >
        <ChatHeader onClose={() => setIsOpen(false)} />
        <ChatPanel />
      </div>
    );
  }

  const ringStyle = {
    background: waveColor,
    width: innerSize,
    height: innerSize,
    top: (outerSize - innerSize) / 2,
    left: (outerSize - innerSize) / 2,
  };

  return (
    <button
      className="relative flex cursor-pointer items-center justify-center border-0 bg-transparent p-0"
      style={{ width: outerSize, height: outerSize }}
      aria-label="Open chat"
      onClick={() => setIsOpen(true)}
    >
      <span className="absolute rounded-full animate-wg-wave" style={ringStyle} />
      <span
        className="absolute rounded-full animate-wg-wave"
        style={{ ...ringStyle, animationDelay: "0.6s" }}
      />
      <span
        className="absolute rounded-full animate-wg-wave"
        style={{ ...ringStyle, animationDelay: "1.2s" }}
      />
      {iconUrl ? (
        <img
          className="relative z-10 rounded-full object-cover shadow-lg"
          src={iconUrl}
          alt=""
          width={innerSize}
          height={innerSize}
        />
      ) : (
        <span
          className="relative z-10 rounded-full shadow-lg"
          style={{ width: innerSize, height: innerSize, background: waveColor }}
        />
      )}
    </button>
  );
}
