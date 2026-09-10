import { useEffect, useState } from 'react';
import { C, H2, P, Snippet, Table } from './prose';

declare global {
  interface Window {
    widgets?: { createChat: (config?: Record<string, unknown>) => void };
  }
}

// widget.js is built next to the console, so it sits in the directory the
// console itself was served from (keeps the prefix on a sub-path deployment).
const appBase = `${window.location.origin}${window.location.pathname.replace(
  /[^/]*$/,
  '',
)}`.replace(/\/$/, '');
const widgetUrl = `${appBase}/widget.js`;

const SNIPPET = `<script type="module" src="${widgetUrl}"></script>
<script type="module">
  widgets.createChat({
    backendUrl: '${appBase}',
    agentName: 'Assistant',
    welcomeMessage: 'Hi! Ask me anything.',
    position: 'bottom-right',
    waveColor: '#6366f1',
  });
</script>`;

const OPTIONS: [string, string, string][] = [
  ['backendUrl', "widget.js's own directory", 'API origin the chat talks to.'],
  ['position', "'bottom-right'", 'Corner: bottom/top + left/right.'],
  ['offsetX / offsetY', '20 / 20', 'Distance from that corner, in px.'],
  ['waveColor', "'#6366f1'", 'Chat head colour and its pulsing rings.'],
  ['innerSize / outerSize', '56 / 80', 'Chat head size and its wave area, in px.'],
  ['iconUrl', '—', 'Image for the chat head; a plain circle when unset.'],
  ['panelWidth / panelHeight', '384 / 600', 'Open chat panel size, in px.'],
  ['panelBg', "'#ffffff'", 'Panel background.'],
  ['agentName', "'Assistant'", 'Name shown in the panel header.'],
  ['welcomeMessage', "'This is the widget panel.'", 'First message in the panel.'],
];

export default function Widget() {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');

  useEffect(() => {
    let host: Element | null = null;
    let left = false;

    function mount() {
      if (left) return;
      window.widgets?.createChat({
        backendUrl: appBase,
        agentName: 'Assistant',
        welcomeMessage: 'Hi! Ask me anything.',
      });
      // createChat appends its host to document.body, outside React's tree.
      host = document.body.lastElementChild;
      setStatus('ready');
    }

    if (window.widgets) {
      mount();
    } else {
      const script = document.createElement('script');
      script.type = 'module';
      script.src = widgetUrl;
      script.onload = mount;
      script.onerror = () => setStatus('error');
      document.head.appendChild(script);
    }

    // Without this the chat head outlives the page and follows the user around.
    return () => {
      left = true;
      host?.remove();
    };
  }, []);

  return (
    <>
      <div className="flex items-center gap-2">
        <span
          className={`h-2 w-2 rounded-full ${
            status === 'ready'
              ? 'bg-green-500'
              : status === 'error'
                ? 'bg-red-500'
                : 'bg-amber-400'
          }`}
        />
        <span className="text-sm font-semibold">
          {status === 'ready'
            ? 'Widget is live on this page'
            : status === 'error'
              ? 'widget.js failed to load'
              : 'Loading widget.js…'}
        </span>
      </div>
      <P>
        {status === 'error' ? (
          <>
            Could not load <C>{widgetUrl}</C>. Build the front-end so <code>widget.js</code> is in{' '}
            <code>admin/dist</code>.
          </>
        ) : (
          <>
            Open the chat head in the bottom-right corner. It is loaded from <C>{widgetUrl}</C> —
            the same script and call any site would use.
          </>
        )}
      </P>

      <H2 id="embed">Embed it on your site</H2>
      <P>
        Drop these two script tags before <C>&lt;/body&gt;</C>.
      </P>
      <Snippet code={SNIPPET} lang="html" />
      <P>
        <code>backendUrl</code> defaults to the directory <code>widget.js</code> was served from,
        so it can be dropped when both live on the same host. Chat calls send cookies, so add the
        embedding site's origin to <code>ALLOWED_ORIGINS</code> on the backend.
      </P>

      <H2 id="options">createChat options</H2>
      <Table
        head={['Option', 'Default', 'What it does']}
        rows={OPTIONS.map(([name, fallback, description]) => [
          <span className="whitespace-nowrap font-mono text-[13px] text-slate-800">{name}</span>,
          <span className="whitespace-nowrap font-mono text-[13px] text-slate-500">{fallback}</span>,
          description,
        ])}
      />
    </>
  );
}
