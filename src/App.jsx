import {
  ArrowLeft,
  ArrowUp,
  Bot,
  ChevronDown,
  CircleDot,
  Clock3,
  Download,
  FileCode2,
  FolderPlus,
  Grid2X2,
  MessageSquarePlus,
  Mic,
  MonitorCog,
  MoreHorizontal,
  Plus,
  Search,
  Settings,
  Sparkles,
  Zap,
} from "lucide-react";

const chats = [
  { title: "Add Flask SQLite backend", time: "20h" },
  { title: "Confirm coding tool", time: "3d" },
  { title: "Build inbox AI agent", time: "1mo" },
];

const quickActions = [
  { icon: <Bot size={16} />, label: "Research a buying decision" },
  { icon: <Grid2X2 size={16} />, label: "Connect Computer Use to Codex" },
];

function IconButton({ children, label, subtle = false }) {
  return (
    <button className={subtle ? "icon-button subtle" : "icon-button"} aria-label={label}>
      {children}
    </button>
  );
}

function SidebarItem({ icon, children }) {
  return (
    <button className="sidebar-item">
      {icon}
      <span>{children}</span>
    </button>
  );
}

function App() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="window-rail" aria-hidden="true">
            <CircleDot size={13} />
            <ArrowLeft size={18} />
            <ArrowLeft className="muted-forward" size={18} />
            <span className="download-dot">
              <Download size={16} />
            </span>
            <span className="menu-label">File</span>
            <span className="menu-label">Edit</span>
            <span className="menu-label">View</span>
            <span className="menu-label">Window</span>
            <span className="menu-label">Help</span>
          </div>

          <nav className="sidebar-nav" aria-label="Workspace navigation">
            <SidebarItem icon={<MessageSquarePlus size={17} />}>New chat</SidebarItem>
            <SidebarItem icon={<Search size={17} />}>Search</SidebarItem>
            <SidebarItem icon={<Grid2X2 size={17} />}>Plugins</SidebarItem>
            <SidebarItem icon={<Clock3 size={17} />}>Automations</SidebarItem>
            <SidebarItem icon={<FolderPlus size={17} />}>Project</SidebarItem>
          </nav>

          <section className="chat-list" aria-label="Recent chats">
            <h2>Chats</h2>
            {chats.map((chat) => (
              <button className="chat-row" key={chat.title}>
                <span>{chat.title}</span>
                <time>{chat.time}</time>
              </button>
            ))}
          </section>
        </div>

        <button className="settings-link">
          <span className="beta-badge">BETA</span>
          <Settings size={17} />
          <span>Settings</span>
        </button>
      </aside>

      <section className="workspace">
        <div className="workspace-frame">
          <div className="frame-controls" aria-hidden="true">
            <span />
            <span />
          </div>

          <div className="hero">
            <h1>What should we work on?</h1>

            <form className="composer" aria-label="Start a new task">
              <label className="visually-hidden" htmlFor="prompt">
                Prompt
              </label>
              <textarea id="prompt" placeholder="Do anything" rows="2" />

              <div className="composer-toolbar">
                <div className="toolbar-left">
                  <IconButton label="Add context" subtle>
                    <Plus size={20} />
                  </IconButton>
                </div>

                <div className="toolbar-right">
                  <button className="model-button" type="button">
                    <Zap size={15} />
                    <span>5.5</span>
                    <strong>Extra High</strong>
                    <ChevronDown size={15} />
                  </button>
                  <IconButton label="Voice input" subtle>
                    <Mic size={18} />
                  </IconButton>
                  <button className="send-button" aria-label="Send prompt">
                    <ArrowUp size={22} />
                  </button>
                </div>
              </div>
            </form>

            <div className="quick-actions">
              {quickActions.map((action) => (
                <button className="quick-action" key={action.label}>
                  {action.icon}
                  <span>{action.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="mobile-dock" aria-label="Mobile shortcuts">
            <IconButton label="Files">
              <FileCode2 size={18} />
            </IconButton>
            <IconButton label="Settings">
              <MonitorCog size={18} />
            </IconButton>
            <IconButton label="More">
              <MoreHorizontal size={18} />
            </IconButton>
            <IconButton label="New task">
              <Sparkles size={18} />
            </IconButton>
          </div>
        </div>
      </section>
    </main>
  );
}

export default App;
