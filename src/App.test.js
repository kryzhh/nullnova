import React, { useState, useEffect, useRef } from "react";

/* ---------------------------
  Small dependency-free SVG icons
---------------------------- */
const IconDownload = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
    <path
      fill="currentColor"
      d="M12 3v10.6L7.7 9.3 6.3 10.7 12 16.4l5.7-5.7-1.4-1.4L12 13.6V3z"
    />
    <path fill="currentColor" d="M5 19h14v2H5z" />
  </svg>
);
const IconCheck = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
    <path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z" />
  </svg>
);
const IconUsers = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
    <path
      fill="currentColor"
      d="M16 11a4 4 0 1 0-8 0 4 4 0 0 0 8 0zm4 7v2H4v-2c0-2.2 3.6-3.5 8-3.5s8 1.3 8 3.5z"
    />
  </svg>
);
const IconAward = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
    <path
      fill="currentColor"
      d="M12 2l2.2 4.5L19 8l-3.6 3 .9 5.1L12 14.8 7.7 16.1 8.6 11 5 8l4.8-1.5zM6 20l-1 2 4-1.5L12 22l3-1.5 4 1.5-1-2L12 18z"
    />
  </svg>
);
const IconLock = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
    <path
      fill="currentColor"
      d="M6 10V8a6 6 0 1 1 12 0v2h1a1 1 0 0 1 1 1v9H4v-9a1 1 0 0 1 1-1h1zm2 0h8V8a4 4 0 0 0-8 0v2z"
    />
  </svg>
);

/* ---------------------------
  Stat counter component (smooth)
---------------------------- */
function StatCounter({
  end,
  duration = 1500,
  format = (n) => n.toLocaleString(),
  suffix = "",
}) {
  const [value, setValue] = useState(0);
  const rafRef = useRef(null);
  useEffect(() => {
    const start = performance.now();
    const from = 0;
    const to = Number(end);
    if (to === 0) {
      setValue(0);
      return;
    }
    function step(now) {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1); // 0..1
      // easeOutCubic
      const eased = 1 - Math.pow(1 - t, 3);
      const current = from + (to - from) * eased;
      setValue(current);
      if (t < 1) rafRef.current = requestAnimationFrame(step);
    }
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [end, duration]);
  // Render integer if large; for small numbers allow decimals if needed
  const display =
    end >= 1000
      ? format(Math.floor(value))
      : end % 1 === 0
      ? Math.floor(value)
      : value.toFixed(2);
  return (
    <span>
      {display}
      {suffix}
    </span>
  );
}

/* ---------------------------
  Main component
---------------------------- */
const NullNovaWebsite = () => {
  // page title
  useEffect(() => {
    document.title = "NullNova";
  }, []);

  const [activeTab, setActiveTab] = useState("desktop");
  const [heroVerified, setHeroVerified] = useState(false);
  const [verifyingHero, setVerifyingHero] = useState(false);
  const [toolVerification, setToolVerification] = useState({}); // {toolName: true}

  const tools = {
    desktop: [
      {
        name: "Windows PC Wiper",
        description:
          "Complete system drive wiping for Windows computers. Ideal before disposal or resale.",
      },
      {
        name: "Mac Data Eraser",
        description:
          "Secure data wiping for macOS, including T2 chip-aware methods.",
      },
      {
        name: "Linux Drive Cleaner",
        description:
          "Professional wiping tools for Linux distributions with scripting support.",
      },
    ],
    mobile: [
      {
        name: "Android Wiper Pro",
        description:
          "Complete data erasure for Android devices — internal/external storage.",
      },
      {
        name: "iOS Data Destroyer",
        description:
          "Secure wiping for iPhones and iPads, compatible with modern iOS.",
      },
      {
        name: "Universal Mobile Wiper",
        description:
          "Cross-platform mobile wiping solution for mixed-device environments.",
      },
    ],
    enterprise: [
      {
        name: "Bulk Device Wiper",
        description:
          "Simultaneously wipe many devices with centralized control & logs.",
      },
      {
        name: "Network Drive Cleaner",
        description:
          "Remote wiping of NAS and network-attached storage with audit trails.",
      },
      {
        name: "Compliance Reporter",
        description:
          "Generate certified wiping reports for auditors and compliance teams.",
      },
    ],
  };

  const stats = [
    { id: "devices", end: 5000000, label: "Devices Wiped", suffix: "+" },
    {
      id: "success",
      end: 9999,
      label: "Verified Wipes (sample metric)",
      suffix: "+",
    },
    { id: "clients", end: 1200, label: "Corporate Clients", suffix: "+" },
    { id: "hours", end: 24, label: "Support Hours Daily", suffix: "/7" },
  ];

  // hero verify
  const handleHeroVerify = () => {
    if (heroVerified || verifyingHero) return;
    setVerifyingHero(true);
    // simulate verification delay
    setTimeout(() => {
      setHeroVerified(true);
      setVerifyingHero(false);
    }, 900);
  };

  // tool verify
  const handleToolVerify = (toolName) => {
    if (toolVerification[toolName]) return;
    // simulate verifying
    setToolVerification((s) => ({ ...s, [toolName]: "verifying" }));
    setTimeout(() => {
      setToolVerification((s) => ({ ...s, [toolName]: true }));
    }, 900);
  };

  return (
    <div className="nn-root">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        :root{
          --bg:#02040a;
          --text:#e6eef3;
          --muted:#9ca3af;
          --cyan:#06b6d4;
          --fuchsia:#d946ef;
          --glass: rgba(255,255,255,0.04);
          --glass-border: rgba(255,255,255,0.06);
        }
        *{box-sizing:border-box}
        html,body,#root{height:100%}
        body{margin:0;background:var(--bg);color:var(--text);font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;}
        .nn-root{min-height:100vh; position:relative; overflow-x:hidden;}

        /* background aurora + grain */
        .nn-bg{position:fixed; inset:0; z-index:0; pointer-events:none; overflow:hidden;}
        .nn-grain{position:absolute; inset:0; background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAABTElEQVRoQ+2YwQ3DIAxFW1pV9T2v6/2k2o3FQqK2fWAbG6S8W6a3t0mDsoXZ7/0pCFh2ABgBqQ6ABoAJ0oF6gK8gGFdVgQwAZkA6gD6SV5x2g7KqKkPeg8W4u0wB4ApwDOgD9gQv8l7p2ZMf4w6gB7wBdD0KrQ8gB4nE0wQy1/y12kHkE8HvJp3yQByA3k9M3wWgDsR6Bq3k1oA6b0o2k0R8m6qwv4C9c2Dpc1wq3c1xq5TyPxZYpXoVQ6C3cJQqggoq8w3w4Y3v3v9AV6g6k6jvKXqkgbQwQwAMyDpQxQ3H/2h8r6MOF9y8gEwAAAAASUVORK5CYII='); opacity:0.12; mix-blend-mode:overlay;}
        .aurora {
          position:absolute;
          width:70vmax;
          height:70vmax;
          border-radius:50%;
          filter: blur(140px);
          opacity:0.55;
          top:-10%;
          left:-10%;
          background: radial-gradient(circle at 30% 30%, rgba(6,182,212,0.18), transparent 30%),
                      radial-gradient(circle at 70% 70%, rgba(217,70,239,0.14), transparent 30%);
          animation: floatA 22s ease-in-out infinite alternate;
          mix-blend-mode: screen;
        }
        .aurora.alt {
          top:auto; bottom:-10%;
          left:50%;
          transform:translateX(-40%);
          animation-duration: 28s;
          background: radial-gradient(circle at 20% 80%, rgba(94,234,212,0.12), transparent 30%),
                      radial-gradient(circle at 80% 20%, rgba(217,70,239,0.12), transparent 30%);
        }
        @keyframes floatA {
          from { transform: translate(0,0) rotate(0deg) scale(1); }
          to { transform: translate(12%, -10%) rotate(25deg) scale(1.08); }
        }

        .container { position:relative; z-index:2; max-width:1100px; margin:0 auto; padding:22px; }

        /* navbar */
        .nav { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px; border-radius:12px; background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border:1px solid var(--glass-border); backdrop-filter: blur(8px); }
        .brand { font-weight:800; font-size:1.25rem; background: linear-gradient(90deg,var(--cyan),var(--fuchsia)); -webkit-background-clip:text; color:transparent; }
        .nav-links { display:flex; gap:14px; align-items:center; }
        .nav-link { color:var(--muted); text-decoration:none; font-weight:600; }
        .cta { padding:8px 14px; border-radius:10px; background: linear-gradient(90deg, rgba(6,182,212,0.12), rgba(217,70,239,0.12)); border:1px solid rgba(255,255,255,0.06); font-weight:700; color:var(--cyan); cursor:pointer; }

        /* hero */
        .hero { text-align:center; padding:64px 18px 40px; }
        .title { font-size:2.6rem; font-weight:800; line-height:1.02; margin-bottom:12px; text-shadow:0 8px 50px rgba(255,255,255,0.03); }
        .subtitle { color:var(--muted); max-width:760px; margin:0 auto 18px; font-size:1rem; line-height:1.6; }
        .hero-actions { display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-top:18px; }
        .btn { display:inline-flex; align-items:center; gap:10px; border-radius:12px; padding:10px 16px; font-weight:800; cursor:pointer; border:none; }
        .btn-primary { background:linear-gradient(90deg,var(--cyan),var(--fuchsia)); color:#021018; }
        .btn-ghost { background: rgba(255,255,255,0.04); color:var(--text); border:1px solid rgba(255,255,255,0.06); }

        /* stats (plain numbers) */
        .stats { display:flex; gap:20px; justify-content:center; align-items:center; flex-wrap:wrap; padding:28px 8px; }
        .stat { text-align:center; min-width:180px; }
        .stat .num { font-weight:900; font-size:1.6rem; background:linear-gradient(90deg,var(--cyan),var(--fuchsia)); -webkit-background-clip:text; color:transparent; }
        .stat .label { color:var(--muted); font-weight:700; margin-top:6px; }

        /* tools */
        .section { padding:48px 12px; }
        .section-title { text-align:center; font-size:1.6rem; font-weight:800; margin-bottom:8px; }
        .section-sub { text-align:center; color:var(--muted); margin-bottom:18px; }
        .tabs { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-bottom:16px; }
        .tab { padding:8px 14px; border-radius:12px; cursor:pointer; font-weight:700; border:1px solid var(--glass-border); background: rgba(255,255,255,0.02); color:var(--muted); }
        .tab.active { background:linear-gradient(90deg,var(--cyan),var(--fuchsia)); color:#021018; box-shadow:0 10px 30px rgba(6,182,212,0.06); }
        .tool-grid { display:grid; gap:12px; grid-template-columns: 1fr; }
        .tool { background:var(--glass); border:1px solid var(--glass-border); padding:14px; border-radius:12px; }
        .tool h4 { margin:0 0 8px 0; }
        .tool p { margin:0 0 12px 0; color:var(--muted); }

        .small-verified { display:inline-flex; align-items:center; gap:8px; color:#0b6f43; font-weight:800; background: rgba(11,111,67,0.08); padding:6px 8px; border-radius:10px; border:1px solid rgba(11,111,67,0.12); }

        /* about */
        .about { padding:40px 12px; max-width:900px; margin:0 auto; text-align:center; }
        .about h3 { font-size:1.5rem; margin-bottom:12px; }
        .about p { color:var(--muted); line-height:1.6; }

        /* footer */
        .footer { padding:28px 12px; text-align:center; color:var(--muted); }

        /* responsive */
        @media (min-width:720px) {
          .tool-grid { grid-template-columns: repeat(2, 1fr); }
          .title { font-size:3.6rem; }
          .stat .num { font-size:2rem; }
        }
        @media (min-width:1000px) {
          .tool-grid { grid-template-columns: repeat(3, 1fr); }
        }
      `}</style>

      <div className="nn-bg" aria-hidden>
        <div className="nn-grain" />
        <div className="aurora" />
        <div className="aurora alt" />
      </div>

      <div className="container">
        {/* NAV */}
        <header className="nav" role="banner" aria-label="Primary navigation">
          <div className="brand">NullNova</div>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <nav
              className="nav-links"
              aria-label="Site links"
              style={{ marginRight: 12 }}>
              <a className="nav-link" href="#features">
                Features
              </a>
              <a className="nav-link" href="#tools">
                Tools
              </a>
              <a className="nav-link" href="#about">
                About
              </a>
            </nav>
            <button className="cta" aria-label="Get Started">
              Get Started
            </button>
          </div>
        </header>

        {/* HERO */}
        <section className="hero" role="region" aria-labelledby="hero-heading">
          <h1 id="hero-heading" className="title">
            <span
              style={{
                background: "linear-gradient(90deg, white, #9ca3af)",
                WebkitBackgroundClip: "text",
                color: "transparent",
              }}>
              Complete Data
            </span>
            <br />
            <span
              style={{
                background: "linear-gradient(90deg,var(--cyan),var(--fuchsia))",
                WebkitBackgroundClip: "text",
                color: "transparent",
              }}>
              Destruction
            </span>
          </h1>

          {/* description before buttons */}
          <p className="subtitle">
            NullNova is a suite of secure data destruction tools built by
            privacy-first engineers. We combine multi-pass overwrite algorithms,
            device-specific erasure flows, and auditable reporting so your data
            is unrecoverable — forever.
          </p>

          <div
            className="hero-actions"
            role="group"
            aria-label="Primary actions">
            <button
              className="btn btn-primary"
              onClick={() => {
                /* you can wire actual download link here */
              }}
              title="Download NullNova">
              <IconDownload size={16} /> Download
            </button>

            <button
              className="btn btn-ghost"
              onClick={handleHeroVerify}
              title="Verify NullNova"
              aria-pressed={heroVerified}>
              {heroVerified ? (
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                  }}>
                  <IconCheck size={14} /> Verified
                </span>
              ) : verifyingHero ? (
                "Verifying..."
              ) : (
                "Verify"
              )}
            </button>
          </div>
        </section>

        {/* STATS (plain, animated, not boxed) */}
        <section aria-label="Statistics" className="stats" role="region">
          {stats.map((s) => (
            <div key={s.id} className="stat" role="group" aria-label={s.label}>
              <div className="num" aria-hidden>
                <StatCounter end={s.end} duration={1600} />
                {s.suffix}
              </div>
              <div className="label">{s.label}</div>
            </div>
          ))}
        </section>

        {/* TOOLS */}
        <section id="tools" className="section" aria-labelledby="tools-heading">
          <h2 id="tools-heading" className="section-title">
            Complete Wiping Solutions
          </h2>
          <p className="section-sub">
            Professional tools for every data destruction need.
          </p>

          <div className="tabs" role="tablist" aria-label="Tools categories">
            {Object.keys(tools).map((tab) => (
              <button
                key={tab}
                className={`tab ${activeTab === tab ? "active" : ""}`}
                role="tab"
                aria-selected={activeTab === tab}
                onClick={() => setActiveTab(tab)}>
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          <div className="tool-grid" role="list">
            {tools[activeTab].map((tool) => (
              <div
                key={tool.name}
                className="tool"
                role="listitem"
                aria-label={tool.name}>
                <h4>{tool.name}</h4>
                <p>{tool.description}</p>

                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      /* implement download behaviour */
                    }}
                    title={`Download ${tool.name}`}>
                    <IconDownload size={14} /> Download
                  </button>

                  <button
                    className="btn btn-ghost"
                    onClick={() => handleToolVerify(tool.name)}
                    title={`Verify ${tool.name}`}
                    aria-pressed={!!toolVerification[tool.name]}>
                    {toolVerification[tool.name] === true ? (
                      <span className="small-verified" aria-hidden>
                        <IconCheck size={14} /> Verified
                      </span>
                    ) : toolVerification[tool.name] === "verifying" ? (
                      "Verifying..."
                    ) : (
                      "Verify"
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ABOUT (after stats) */}
        <section id="about" className="about" aria-labelledby="about-heading">
          <h3 id="about-heading">Your Digital Fingerprint, Erased.</h3>
          <p>
            NullNova was created to solve a critical problem: incomplete data
            deletion. When you sell devices or dispose of storage, formatting
            isn't enough — residual data can be recovered. NullNova's
            standards-aligned multi-pass erasure, device-aware flows, and audit
            reporting ensure complete, irreversible destruction of sensitive
            data.
          </p>
          <div
            style={{
              marginTop: 18,
              display: "flex",
              gap: 28,
              justifyContent: "center",
              alignItems: "center",
              flexWrap: "wrap",
            }}>
            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  display: "inline-block",
                  padding: 10,
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.02)",
                }}>
                <IconUsers size={28} />
              </div>
              <div style={{ fontWeight: 800, marginTop: 8 }}>1M+</div>
              <div style={{ color: "var(--muted)" }}>Happy Users</div>
            </div>

            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  display: "inline-block",
                  padding: 10,
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.02)",
                }}>
                <IconAward size={28} />
              </div>
              <div style={{ fontWeight: 800, marginTop: 8 }}>5★</div>
              <div style={{ color: "var(--muted)" }}>User Rating</div>
            </div>

            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  display: "inline-block",
                  padding: 10,
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.02)",
                }}>
                <IconLock size={34} />
              </div>
              <div style={{ fontWeight: 800, marginTop: 8 }}>DoD & Intl.</div>
              <div style={{ color: "var(--muted)" }}>Standards Supported</div>
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="footer">
          © {new Date().getFullYear()} NullNova. All rights reserved.
        </footer>
      </div>
    </div>
  );
};

export default NullNovaWebsite;
