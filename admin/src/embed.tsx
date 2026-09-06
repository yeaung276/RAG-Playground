import { createRoot } from 'react-dom/client';
import Widget from './widget/Widget';
import { WidgetProvider } from './widget/config';
import css from './widget/index.css?inline';

type Position = 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';

interface ChatConfig {
  backendUrl?: string;
  position?: Position;
  offsetX?: number;
  offsetY?: number;
  waveColor?: string;
  innerSize?: number;
  outerSize?: number;
  iconUrl?: string;
  panelWidth?: number;
  panelHeight?: number;
  panelBg?: string;
  agentName?: string;
  welcomeMessage?: string;
}

// The directory widget.js was served from: at <base>/widget.js this is <base>,
// so a sub-path deployment (…/chat/widget.js) keeps its prefix.
const defaultBackendUrl = new URL('.', import.meta.url).href.replace(/\/$/, '');

function positionStyles(
  position: Position,
  offsetX: number,
  offsetY: number,
): string {
  const x = position.endsWith('right')
    ? `right:${offsetX}px`
    : `left:${offsetX}px`;
  const y = position.startsWith('bottom')
    ? `bottom:${offsetY}px`
    : `top:${offsetY}px`;
  return `position:fixed;${y};${x};z-index:9999`;
}

function createChat(config: ChatConfig = {}) {
  const {
    backendUrl = defaultBackendUrl,
    position = 'bottom-right',
    offsetX = 20,
    offsetY = 20,
    waveColor = '#6366f1',
    innerSize = 56,
    outerSize = 80,
    iconUrl,
    panelWidth = 384,
    panelHeight = 600,
    panelBg = '#ffffff',
    agentName = 'Assistant',
    welcomeMessage = 'This is the widget panel.',
  } = config;

  const host = document.createElement('div');
  host.setAttribute('style', positionStyles(position, offsetX, offsetY));
  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: 'open' });

  const style = document.createElement('style');
  style.textContent = css;
  shadow.appendChild(style);

  const mount = document.createElement('div');
  shadow.appendChild(mount);

  createRoot(mount).render(
    <WidgetProvider
      value={{
        backendUrl,
        iconUrl,
        agentName,
        welcomeMessage,
      }}
    >
      <Widget
        waveColor={waveColor}
        innerSize={innerSize}
        outerSize={outerSize}
        iconUrl={iconUrl}
        panelWidth={panelWidth}
        panelHeight={panelHeight}
        panelBg={panelBg}
      />
    </WidgetProvider>,
  );
}

(window as any).widgets = { createChat };
