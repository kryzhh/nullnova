import React, { useState, useEffect } from "react";
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
/* ---------------------------
   Simple inline SVG icons
   (keeps this file dependency-free)
   --------------------------- */
const IconDownload = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path
      fill="currentColor"
      d="M12 3v10.586L7.707 9.293 6.293 10.707 12 16.414l5.707-5.707-1.414-1.414L12 13.586V3z"
    />
    <path fill="currentColor" d="M5 19h14v2H5z" />
  </svg>
);
const IconPlay = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path fill="currentColor" d="M8 5v14l11-7z" />
  </svg>
);
const IconShield = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path
      fill="currentColor"
      d="M12 2l7 3v5c0 5-3.5 9.6-7 11-3.5-1.4-7-6-7-11V5l7-3z"
    />
  </svg>
);
const IconDrive = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path fill="currentColor" d="M4 6h16v8H4zM2 18h20v2H2z" />
    <circle cx="8" cy="10" r="1" fill="currentColor" />
    <circle cx="12" cy="10" r="1" fill="currentColor" />
  </svg>
);
const IconPhone = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path
      fill="currentColor"
      d="M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm5 19a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"
    />
  </svg>
);
const IconCheck = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path fill="currentColor" d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z" />
  </svg>
);
const IconUsers = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path
      fill="currentColor"
      d="M16 11a4 4 0 1 0-8 0 4 4 0 0 0 8 0zm4 7v2H4v-2c0-2.2 3.6-3.5 8-3.5s8 1.3 8 3.5z"
    />
  </svg>
);
const IconAward = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path
      fill="currentColor"
      d="M12 2l2.2 4.5L19 8l-3.6 3 0.9 5.1L12 14.8 7.7 16.1 8.6 11 5 8l4.8-1.5zM6 20l-1 2 4-1.5L12 22l3-1.5 4 1.5-1-2L12 18z"
    />
  </svg>
);
const IconLock = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden>
    <path
      fill="currentColor"
      d="M6 10V8a6 6 0 1 1 12 0v2h1a1 1 0 0 1 1 1v9H4v-9a1 1 0 0 1 1-1h1zm2 0h8V8a4 4 0 0 0-8 0v2z"
    />
  </svg>
);

/* ---------------------------
   Main component
   --------------------------- */
const NullNovaWebsite = () => {
  const [activeTab, setActiveTab] = useState("desktop");

  useEffect(() => {
    document.title = "NullNova";
  }, []);

  const features = [
    {
      icon: <IconDrive className="icon" />,
      title: "Complete Hard Drive Wipe",
      description:
        "Permanently erase all data from HDDs and SSDs with tested multi-pass algorithms.",
    },
    {
      icon: <IconPhone className="icon" />,
      title: "Mobile Device Wiping",
      description:
        "Securely wipe smartphones and tablets before resale or disposal.",
    },
    {
      icon: <IconShield className="icon" />,
      title: "Multi-Pass Security",
      description:
        "Multiple overwrite passes and pattern obfuscation prevent recovery.",
    },
  ];

  const tools = [
    {
      id: "desktop",
      category: "Desktop Solutions",
      items: [
        {
          name: "Windows PC Wiper",
          description: "Complete system drive wiping for Windows computers.",
          verified: true,
        },
        {
          name: "Mac Data Eraser",
          description: "Secure data wiping for macOS systems (T2 aware).",
          verified: true,
        },
        {
          name: "Linux Drive Cleaner",
          description: "Professional wiping tools for Linux distributions.",
          verified: true,
        },
      ],
    },
    {
      id: "mobile",
      category: "Mobile Solutions",
      items: [
        {
          name: "Android Wiper Pro",
          description: "Complete data erasure for Android devices.",
          verified: true,
        },
        {
          name: "iOS Data Destroyer",
          description: "Secure wiping for iPhones and iPads.",
          verified: true,
        },
        {
          name: "Universal Mobile Wiper",
          description: "Cross-platform mobile wiping solution.",
          verified: true,
        },
      ],
    },
    {
      id: "enterprise",
      category: "Enterprise Tools",
      items: [
        {
          name: "Bulk Device Wiper",
          description: "Simultaneously wipe multiple devices at scale.",
          verified: true,
        },
        {
          name: "Network Drive Cleaner",
          description: "Remote wiping of network-attached storage systems.",
          verified: true,
        },
        {
          name: "Compliance Reporter",
          description: "Generate certified wiping reports for auditors.",
          verified: true,
        },
      ],
    },
  ];

  const stats = [
    { number: "5M+", label: "Devices Wiped" },
    { number: "99.99%", label: "Success Rate" },
    { number: "24/7", label: "Support" },
    { number: "100%", label: "Secure" },
  ];

  const gradientText = (text, gradient) => (
    <span
      style={{
        backgroundImage: gradient,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
      }}>
      {text}
    </span>
  );

  return (
    <div className="nn-main">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        :root{
          --bg: #02040a;
          --cyan: #06b6d4;
          --fuchsia: #d946ef;
          --glass: rgba(255,255,255,0.06);
          --glass-border: rgba(255,255,255,0.09);
          --muted: #9ca3af;
        }

        *{box-sizing:border-box}
        html,body,#root { height:100%; }
        body { margin:0; font-family: 'Inter', sans-serif; background: var(--bg); color: #e6eef3; -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale; }

        .nn-main { min-height:100vh; position:relative; overflow-x:hidden; }

        /* Background / aurora + grain */
        .nn-bg {
          position:fixed;
          inset:0;
          z-index:0;
          pointer-events:none;
          overflow:hidden;
        }
        .grain {
          position:absolute;
          inset:0;
          background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAABTElEQVRoQ+2YwQ3DIAxFW1pV9T2v6/2k2o3FQqK2fWAbG6S8W6a3t0mDsoXZ7/0pCFh2ABgBqQ6ABoAJ0oF6gK8gGFdVgQwAZkA6gD6SV5x2g7KqKkPeg8W4u0wB4ApwDOgD9gQv8l7p2ZMf4w6gB7wBdD0KrQ8gB4nE0wQy1/y12kHkE8HvJp3yQByA3k9M3wWgDsR6Bq3k1oA6b0o2k0R8m6qwv4C9c2Dpc1wq3c1xq5TyPxZYpXoVQ6C3cJQqggoq8w3w4Y3v3v9AV6g6k6jvKXqkgbQwQwAMyDpQxQ3H/2h8r6MOF9y8gEwAAAAASUVORK5CYII=');
          opacity:0.12;
          mix-blend-mode:overlay;
        }
        .aurora {
          position:absolute;
          width:60vmax;
          height:60vmax;
          filter: blur(140px);
          opacity:0.55;
          border-radius:50%;
          transform: translate(-10%, -30%);
          background: radial-gradient(circle at 30% 30%, rgba(6,182,212,0.18), transparent 30%),
                      radial-gradient(circle at 70% 70%, rgba(217,70,239,0.14), transparent 30%);
          animation: floatA 20s ease-in-out infinite alternate;
          mix-blend-mode: screen;
        }
        .aurora.alt {
          top:auto; bottom:-10%;
          left:50%;
          transform:translate(-40%, -10%);
          animation-duration: 26s;
          background: radial-gradient(circle at 20% 80%, rgba(94,234,212,0.12), transparent 30%),
                      radial-gradient(circle at 80% 20%, rgba(217,70,239,0.12), transparent 30%);
        }
        @keyframes floatA {
          from { transform: translate(-10%,-30%) rotate(0deg) scale(1); }
          to { transform: translate(10%,-10%) rotate(30deg) scale(1.08); }
        }

        /* layout */
        .nn-wrap { position:relative; z-index:2; padding:20px; max-width:1100px; margin:0 auto; }

        /* navbar */
        .nn-nav { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px; border-radius:12px; background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border: 1px solid var(--glass-border); backdrop-filter: blur(8px); margin-top:10px; }
        .nn-logo { font-weight:800; font-size:1.25rem; background: linear-gradient(90deg, var(--cyan), var(--fuchsia)); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .nn-links { display:flex; gap:16px; align-items:center; }
        .nn-link { color:var(--muted); text-decoration:none; font-weight:600; font-size:0.95rem; }
        .nn-link:hover { color:#fff; }

        .nn-cta { padding:8px 14px; border-radius:10px; background: linear-gradient(90deg, rgba(6,182,212,0.12), rgba(217,70,239,0.12)); border:1px solid rgba(255,255,255,0.06); font-weight:700; cursor:pointer; color:var(--cyan); }

        /* hero */
        .hero { text-align:center; padding:64px 16px 40px; }
        .hero-title { font-size:2.6rem; font-weight:800; line-height:1.02; margin-bottom:12px; text-shadow: 0 8px 50px rgba(255,255,255,0.03); }
        .hero-sub { color:var(--muted); max-width:720px; margin:0 auto 20px; font-size:1rem; line-height:1.6; }
        .hero-buttons { display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-bottom:28px; }
        .btn { padding:12px 20px; border-radius:12px; font-weight:700; cursor:pointer; border:none; display:inline-flex; align-items:center; gap:8px; }
        .btn-primary { background:linear-gradient(90deg,var(--cyan),var(--fuchsia)); color:#021018; box-shadow:0 8px 30px rgba(217,70,239,0.08); }
        .btn-secondary { background: rgba(255,255,255,0.03); color: #e6eef3; border:1px solid rgba(255,255,255,0.04); backdrop-filter: blur(6px); }

        .stats-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:16px; max-width:720px; margin:0 auto; }
        .stat { padding:12px; border-radius:12px; background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border:1px solid var(--glass-border); }
        .stat-number { font-size:1.4rem; font-weight:800; background:linear-gradient(90deg,var(--cyan),var(--fuchsia)); -webkit-background-clip:text; color:transparent; }
        .stat-label { color:var(--muted); font-weight:600; margin-top:6px; }

        /* sections */
        .section { padding:56px 12px; max-width:1100px; margin:0 auto; }
        .section-title { font-size:1.75rem; font-weight:700; margin-bottom:12px; text-align:center; }
        .section-sub { color:var(--muted); text-align:center; max-width:700px; margin:0 auto 24px; }

        /* glass card */
        .glass-card { background: var(--glass); border-radius:14px; padding:18px; border:1px solid var(--glass-border); backdrop-filter: blur(12px); transition: transform .25s ease, box-shadow .25s ease; }
        .glass-card:hover { transform: translateY(-6px); box-shadow: 0 20px 60px rgba(6,182,212,0.06); }

        .features-grid { display:grid; grid-template-columns:1fr; gap:16px; margin-top:18px; }
        .feature { display:flex; gap:12px; align-items:flex-start; }
        .feature .icon { width:42px; height:42px; color:var(--cyan); flex:0 0 42px; }
        .feature h3 { margin:0; font-size:1.05rem; font-weight:700; }
        .feature p { margin:6px 0 0; color:var(--muted); font-size:0.95rem; line-height:1.5; }

        /* tools tabs */
        .tabs { display:flex; gap:8px; justify-content:center; margin-bottom:18px; flex-wrap:wrap; }
        .tab-btn { padding:8px 14px; border-radius:12px; border:1px solid var(--glass-border); background: rgba(255,255,255,0.02); color:var(--muted); cursor:pointer; font-weight:700; }
        .tab-btn.active { background: linear-gradient(90deg,var(--cyan),var(--fuchsia)); color:#021018; box-shadow:0 10px 30px rgba(6,182,212,0.06); }

        .tools-grid { display:grid; grid-template-columns:1fr; gap:12px; margin-top:12px; }
        .tool-card { padding:14px; border-radius:12px; }

        /* about layout */
        .about-grid { display:grid; grid-template-columns:1fr; gap:16px; align-items:center; }
        .about-left h2 { margin:0 0 10px 0; }
        .about-right { display:flex; align-items:center; justify-content:center; }

        /* footer */
        .nn-footer { text-align:center; padding:28px 12px 80px; color:var(--muted); font-size:0.95rem; }

        /* responsive */
        @media(min-width:700px){
          .features-grid { grid-template-columns:repeat(3,1fr); }
          .tools-grid { grid-template-columns:repeat(3,1fr); }
          .about-grid { grid-template-columns: 1fr 420px; }
          .stats-grid { grid-template-columns:repeat(4,1fr); }
          .hero-title { font-size:3.6rem; }
        }
      `}</style>

      <div className="nn-bg" aria-hidden>
        <div className="grain" />
        <div className="aurora" />
        <div className="aurora alt" />
      </div>

      <div className="nn-wrap">
        {/* NAV */}
        <header className="nn-nav" role="banner">
                
                  
        
            
          <div className="nn-logo">NullNova</div>
          <nav
            className="nn-links"
            role="navigation"
            aria-label="Main navigation">
            <a className="nn-link" href="#features">
              Features
            </a>
            <a className="nn-link" href="#tools">
              Tools
            </a>
            <a className="nn-link" href="#about">
              About
            </a>
          </nav>
          <button className="nn-cta" aria-label="Get started">
            Get Started
          </button>
         <div>
                <SignedOut>
                  <SignInButton className="nn-cta" />
                </SignedOut>
                <SignedIn>
                  <UserButton appearance={{ elements: { userButtonBox: 'nn-cta' } }} />
                </SignedIn>
         </div> 
        </header>

        {/* HERO */}
        <main>
          <section
            className="hero"
            role="region"
            aria-labelledby="hero-heading">
            <h1 id="hero-heading" className="hero-title">
              {gradientText(
                "Complete Data",
                "linear-gradient(90deg, white, #9ca3af)"
              )}
              <br />
              {gradientText(
                "Destruction",
                "linear-gradient(90deg, var(--cyan), var(--fuchsia))"
              )}
            </h1>

            <p className="hero-sub">
              Don't just delete your data — destroy it. NullNova ensures
              sensitive information cannot be recovered when selling or
              disposing of devices.
            </p>

            <div
              className="hero-buttons"
              role="region"
              aria-label="Primary actions">
              <button className="btn btn-primary" title="Download NullNova">
                <IconDownload
                  className="icon-small"
                  style={{ width: 16, height: 16 }}
                />
                Free Download
              </button>
              <button className="btn btn-secondary" title="Watch demo">
                <IconPlay
                  className="icon-small"
                  style={{ width: 14, height: 14 }}
                />
                Watch Demo
              </button>
            </div>

            <div className="stats-grid" role="list">
              {stats.map((s) => (
                <div key={s.label} className="stat" role="listitem">
                  <div className="stat-number">
                    {gradientText(
                      s.number,
                      "linear-gradient(90deg,var(--cyan),var(--fuchsia))"
                    )}
                  </div>
                  <div className="stat-label">{s.label}</div>
                </div>
              ))}
            </div>
          </section>

          {/* FEATURES */}
          <section
            id="features"
            className="section"
            aria-labelledby="features-title">
            <h2 id="features-title" className="section-title">
              Why Choose NullNova?
            </h2>
            <p className="section-sub">
              Complete data destruction tools for individuals and enterprises,
              built on trust and impenetrable security.
            </p>

            <div className="features-grid" role="list">
              {features.map((f, idx) => (
                <div key={idx} className="glass-card feature" role="listitem">
                  <div style={{ minWidth: 42 }}>{f.icon}</div>
                  <div>
                    <h3>{f.title}</h3>
                    <p>{f.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* TOOLS */}
          <section id="tools" className="section" aria-labelledby="tools-title">
            <h2 id="tools-title" className="section-title">
              Complete Wiping Solutions
            </h2>
            <p className="section-sub">
              Professional tools for every data destruction need.
            </p>

            <div className="tabs" role="tablist" aria-label="Tool categories">
              {tools.map((t) => (
                <button
                  key={t.id}
                  className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
                  role="tab"
                  aria-selected={activeTab === t.id}
                  onClick={() => setActiveTab(t.id)}>
                  {t.category}
                </button>
              ))}
            </div>

            <div className="tools-grid" role="list">
              {tools
                .find((x) => x.id === activeTab)
                .items.map((item, i) => (
                  <div key={i} className="glass-card tool-card">
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}>
                      <h3 style={{ margin: 0 }}>{item.name}</h3>
                      {item.verified && (
                        <div title="Verified" style={{ color: "var(--cyan)" }}>
                          <IconCheck className="icon" />
                        </div>
                      )}
                    </div>
                    <p style={{ color: "var(--muted)", marginTop: 8 }}>
                      {item.description}
                    </p>
                    <div style={{ marginTop: 12 }}>
                      <button
                        style={{
                          padding: "8px 12px",
                          borderRadius: 10,
                          border: "1px solid rgba(255,255,255,0.06)",
                          background: "rgba(255,255,255,0.02)",
                          color: "#e6eef3",
                          fontWeight: 700,
                          cursor: "pointer",
                        }}>
                        Download Free
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </section>

          {/* ABOUT */}
          <section id="about" className="section" aria-labelledby="about-title">
            <h2 id="about-title" className="section-title">
              Your Digital Fingerprint, Erased.
            </h2>
            <p className="section-sub">
              NullNova was created to solve a critical problem: incomplete data
              deletion. Our military-grade wiping algorithms ensure your
              sensitive data is completely destroyed and cannot be recovered by
              any means.
            </p>

            <div className="about-grid" style={{ marginTop: 20 }}>
              <div className="about-left">
                <p style={{ color: "var(--muted)", lineHeight: 1.6 }}>
                  When you sell or dispose of storage, formatting is not enough
                  — data can still be recovered. NullNova's multi-pass,
                  standard-compliant methods ensure permanent erasure and
                  provide audit-ready reporting for compliance needs.
                </p>
                <div style={{ display: "flex", gap: 18, marginTop: 18 }}>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        margin: "0 auto 8px",
                        color: "var(--cyan)",
                      }}>
                      <IconUsers className="icon" />
                    </div>
                    <div style={{ fontWeight: 700 }}>1M+</div>
                    <div style={{ color: "var(--muted)" }}>Happy Users</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        margin: "0 auto 8px",
                        color: "var(--fuchsia)",
                      }}>
                      <IconAward className="icon" />
                    </div>
                    <div style={{ fontWeight: 700 }}>5★</div>
                    <div style={{ color: "var(--muted)" }}>User Rating</div>
                  </div>
                </div>
              </div>

              <div className="about-right">
                <div
                  className="glass-card"
                  style={{ width: 360, maxWidth: "100%" }}>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        width: 64,
                        height: 64,
                        margin: "0 auto 12px",
                        color: "var(--cyan)",
                      }}>
                      <IconLock className="icon" />
                    </div>
                    <h3 style={{ margin: 0 }}>Military-Grade Security</h3>
                    <p style={{ color: "var(--muted)", marginTop: 8 }}>
                      Implements DoD and international standards to guarantee
                      permanent data destruction.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </main>

        {/* FOOTER */}
        <footer className="nn-footer" role="contentinfo">
          <div>© {new Date().getFullYear()} NullNova. All rights reserved.</div>
        </footer>
      </div>
    </div>
  );
};

export default NullNovaWebsite;
