const modules = [
  {
    label: "01",
    title: "Coastal Change Explorer",
    description: "Compare radar observations and surface change across time.",
  },
  {
    label: "02",
    title: "Tide-Aware Verification",
    description: "Put each signal beside its tide context and uncertainty.",
  },
  {
    label: "03",
    title: "Mission Planner",
    description: "Turn evidence into a ranked list of field actions.",
  },
];

export default function Home() {
  const apiConfigured = Boolean(process.env.NEXT_PUBLIC_API_URL);

  return (
    <main className="shell">
      <nav className="nav">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>TideAware</span>
        </div>
        <span className="nav-status">
          <span className="status-dot" />
          Initial platform shell
        </span>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">COASTAL INTELLIGENCE / 0.1</p>
          <h1>Find the changes worth checking.</h1>
          <p className="lede">
            TideAware connects NISAR radar signals, tide context and field
            evidence so conservation teams can prioritize real threats.
          </p>
          <div className="hero-actions">
            <a className="button button-primary" href="#modules">
              Explore the platform
            </a>
            <a className="button button-quiet" href="/api/health">
              Check web health ↗
            </a>
          </div>
        </div>

        <div className="signal-panel" aria-label="Platform status">
          <div className="panel-topline">
            <span>PLATFORM STATUS</span>
            <span className="mono">LIVE SHELL</span>
          </div>
          <div className="signal-grid">
            <div>
              <span className="signal-value">03</span>
              <span className="signal-label">core modules</span>
            </div>
            <div>
              <span className="signal-value">L-band</span>
              <span className="signal-label">radar context</span>
            </div>
            <div>
              <span className="signal-value">{apiConfigured ? "API" : "LOCAL"}</span>
              <span className="signal-label">runtime mode</span>
            </div>
          </div>
          <div className="waveform" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
          <p className="panel-note">
            Ready for Supabase data, MapLibre layers and a FastAPI connection.
          </p>
        </div>
      </section>

      <section className="module-section" id="modules">
        <div className="section-heading">
          <p className="eyebrow">THE FIRST BUILD</p>
          <h2>From observation to action.</h2>
        </div>
        <div className="module-list">
          {modules.map((module) => (
            <article className="module-row" key={module.label}>
              <span className="module-label">{module.label}</span>
              <h3>{module.title}</h3>
              <p>{module.description}</p>
              <span className="module-arrow" aria-hidden="true">
                ↗
              </span>
            </article>
          ))}
        </div>
      </section>

      <footer className="footer">
        <span>TIDEAWARE / NASA SPACE APPS CONCEPT</span>
        <span className="mono">NEXT + FASTAPI + SUPABASE</span>
      </footer>
    </main>
  );
}
