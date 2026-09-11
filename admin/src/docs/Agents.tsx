import { Link } from 'react-router-dom';
import { C, H2, H3, Note, P, Table } from './prose';

const GENERAL: [string, string][] = [
  ['Name', 'How the agent is identified everywhere, including as a handoff target. Set when you add the agent and fixed from then on.'],
  ['Description', 'What this agent handles. Other agents read it when deciding whether to hand work over, so write it as a scope, not a greeting.'],
];

const RUNTIME: [string, string][] = [
  ['Model', 'Which chat model answers. Only models registered with the decoder capability appear here.'],
  ['Temperature', '0–100. Low is repeatable and literal, high is varied. Tool-calling agents usually want it low.'],
  ['Max steps', 'How many tool-call rounds the agent may take before it has to answer. Stops a loop from running forever.'],
  ['Knowledge', 'Optional. Attach one knowledge to give the agent retrieval over those documents.'],
  ['System prompt', 'Prepended to every turn. Handoff descriptions are added automatically, so there is no need to restate them here.'],
];

const TOOL_FIELDS: [string, string][] = [
  ['Name', 'The function name the model calls. snake_case, unique within the agent, and fixed once the tool has been saved.'],
  ['Description', 'Tells the model when to call the tool. This is the main thing that decides whether it gets used correctly.'],
  ['Method and URL', 'The request to make. The URL may contain parameter placeholders.'],
  ['Headers and query', 'Sent with every call. Values may contain placeholders.'],
  ['Body', 'Raw request body for POST, PUT and PATCH. May contain placeholders.'],
  ['Auth', 'None, bearer token, API key header, or basic auth.'],
  ['Timeout', 'Milliseconds to wait before the call is abandoned.'],
  ['Parameters', 'What the model supplies at call time — name, type, whether it is required, and a description.'],
];

const MODES: [string, string][] = [
  ['No handoff', 'The agent answers everything it receives itself.'],
  ['Auto', 'Every other agent is reachable. Each one is offered using its own description, so keep those descriptions accurate.'],
  ['Manual', 'Only the targets you list, each with a routing rule you write yourself.'],
];

export default function Agents() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        An agent is one configured assistant: a model, a system prompt, optional knowledge, a set
        of HTTP tools it may call, and rules for handing work to other agents. Agents are managed
        on the{' '}
        <Link to="/agents" className="font-medium text-indigo-600 hover:text-indigo-700">
          Agents
        </Link>{' '}
        page — the roster on the left, the selected agent's settings on the right across four
        tabs: General, Runtime, Tools and Handoffs.
      </P>
      <P>
        Changes on the right are a draft until you press <C>Save changes</C>. Adding, deleting and
        promoting agents in the roster take effect immediately.
      </P>

      <H2 id="roster">Roster and entrypoint</H2>
      <P>
        Every conversation starts at the <b>entrypoint</b> — exactly one agent, marked with a crown
        in the roster. Hover any other agent and click its crown to move the entrypoint there; the
        previous one is demoted automatically. An agent with no entrypoint and no incoming handoff
        will never be reached.
      </P>
      <P>
        Each roster row also shows how many enabled tools the agent has and how many handoff
        targets it defines. Deleting an agent is immediate and cannot be undone.
      </P>
      <Note title="One entrypoint at a time">
        Deleting the entrypoint leaves the system without one. Promote another agent before or
        after, or the runtime has nowhere to start.
      </Note>

      <H2 id="general">General</H2>
      <Table
        head={['Field', 'What it means']}
        rows={GENERAL.map(([field, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{field}</span>,
          description,
        ])}
      />
      <Note title="Renaming">
        An agent's name cannot be changed after it is created, because handoffs and stored
        credentials are keyed against it. Delete the agent and add it again under the new name.
      </Note>

      <H2 id="runtime">Runtime</H2>
      <P>How the agent actually runs, and the prompt it runs with.</P>
      <Table
        head={['Field', 'What it means']}
        rows={RUNTIME.map(([field, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{field}</span>,
          description,
        ])}
      />

      <H2 id="tools">Tools</H2>
      <P>
        A tool is one HTTP request the agent may make. Each tool has a switch — a disabled tool
        stays configured but is not offered to the model.
      </P>
      <Table
        head={['Field', 'What it means']}
        rows={TOOL_FIELDS.map(([field, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{field}</span>,
          description,
        ])}
      />

      <H3>Parameters and placeholders</H3>
      <P>
        Declare a parameter, then reference it anywhere in the URL, query values, header values or
        body as <C>{'{{name}}'}</C>. At call time the model supplies the values and they are
        substituted in. A placeholder with no matching parameter is left in the request untouched,
        which makes a typo easy to spot.
      </P>

      <H3>Credentials</H3>
      <P>
        Bearer tokens and API keys are encrypted before they are stored and are never sent back to
        this console — the field shows <i>Stored — leave blank to keep</i> once one is saved. Type
        a new value to replace it, or set Auth to <C>None</C> to remove it. Basic auth credentials
        are stored as entered.
      </P>

      <H3>Testing</H3>
      <P>
        <C>Test tool</C> makes the request for real, from the server, using the tool exactly as it
        appears on screen — it does not have to be saved first. Fill in a value for each parameter
        under <i>Test values</i>, and the result shows the request that went out, the status code,
        the elapsed time and the response body. Credentials are masked in the echoed request.
      </P>
      <Note title="The request really is sent">
        Testing a tool that writes data will write it. Point the tool at a safe endpoint first if
        you are unsure what it does.
      </Note>

      <H2 id="handoffs">Handoffs</H2>
      <P>
        A handoff lets one agent transfer the conversation to another. Any agent can hand off, not
        only the entrypoint, and each handoff is offered to the model as a tool it may call.
      </P>
      <Table
        head={['Mode', 'Behaviour']}
        rows={MODES.map(([mode, behaviour]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{mode}</span>,
          behaviour,
        ])}
      />
      <P>
        In Manual mode you pick each target and write a description for it. Write that description
        as a routing rule — the condition under which the transfer should happen — because it is
        what the model reads when choosing. Each agent can be listed once.
      </P>

      <H2 id="saving">Saving</H2>
      <P>
        Save sends the whole agent at once. The tool list is replaced wholesale and matched by tool
        name: a tool you removed from the list is deleted along with its stored credential, and a
        tool whose token field you left blank keeps the token it already had.
      </P>
      <P>
        <C>Reset</C> discards the draft and reloads the saved agent. Switching to another agent
        also discards unsaved changes, so save before you move on.
      </P>
    </>
  );
}
