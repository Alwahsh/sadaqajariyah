// Sadaqa Jariyah — Final direction
// Communal's civic structure + Garden's warm sand + sage palette.
// DM Sans throughout, with Fraunces serif used sparingly for display warmth.
// Domain: sadaqajariyah.online

const { useState, useMemo } = React;

const T = {
  // From Garden palette
  bg:       '#F5EFE3',  // warm sand background
  bgCard:   '#FBF7EE',  // creamy card
  bgSoft:   '#EFE8D8',  // section bg (slightly darker than bg for layering)
  ink:      '#1F2A24',  // deep forest ink
  inkSoft:  '#5C6660',
  inkMute:  '#8B928C',
  rule:     '#E2D9C5',
  ruleSoft: '#EBE3D1',

  sage:     '#6B8E73',  // primary sage
  sageDeep: '#3F5D4A',  // CTA background
  sageSoft: '#D9E4D6',  // tag/chip background

  clay:     '#C28E5C',  // warm accent
  amber:    '#B87333',

  // Typography (Communal-style)
  sans:     '"DM Sans", -apple-system, BlinkMacSystemFont, sans-serif',
  display:  '"DM Sans", -apple-system, sans-serif',
  serif:    '"Fraunces", "Iowan Old Style", Georgia, serif',
  mono:     '"DM Mono", ui-monospace, monospace',
  ar:       '"Noto Naskh Arabic", "Amiri", serif',
};

// ── Brand mark (Garden-style 8-pointed star, simplified) ────
function Mark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none">
      <circle cx="14" cy="14" r="13" fill={T.sageDeep} />
      <path d="M14 6 C 16 10, 18 12, 22 14 C 18 16, 16 18, 14 22 C 12 18, 10 16, 6 14 C 10 12, 12 10, 14 6 Z"
            fill={T.bgCard} fillOpacity="0.95" />
    </svg>
  );
}

function Wordmark({ size = 17 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <Mark size={size + 12} />
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.05 }}>
        <span style={{ fontFamily: T.sans, fontSize: size, fontWeight: 600, color: T.ink, letterSpacing: '-0.02em' }}>
          Sadaqa Jariyah
        </span>
        <span style={{ fontFamily: T.ar, fontSize: size - 4, color: T.sageDeep, marginTop: 2, direction: 'rtl' }}>
          صدقة جارية
        </span>
      </div>
    </div>
  );
}

// ── Buttons ─────────────────────────────────────────────────
function Btn({ children, variant = 'primary', size = 'md', style = {}, onClick }) {
  const sizes = {
    sm: { padding: '8px 14px', fontSize: 13 },
    md: { padding: '11px 20px', fontSize: 14 },
    lg: { padding: '14px 26px', fontSize: 15 },
  };
  const variants = {
    primary: { background: T.sageDeep, color: T.bgCard, border: '1px solid ' + T.sageDeep },
    ghost:   { background: 'transparent', color: T.ink, border: '1px solid ' + T.rule },
    soft:    { background: T.sageSoft, color: T.sageDeep, border: '1px solid ' + T.sageSoft },
    light:   { background: T.bgCard, color: T.ink, border: '1px solid ' + T.rule },
  };
  return (
    <button onClick={onClick} style={{
      ...sizes[size], ...variants[variant],
      fontFamily: T.sans, fontWeight: 500, cursor: 'pointer',
      borderRadius: 10, letterSpacing: '-0.005em', transition: 'all .15s', ...style,
    }}>{children}</button>
  );
}

// ── Avatar ──────────────────────────────────────────────────
function Avatar({ name, size = 44 }) {
  const initials = name.split(' ').map(p => p[0]).slice(0, 2).join('');
  const palettes = [
    { bg: T.sageSoft,  fg: T.sageDeep },
    { bg: '#EFD9C2',   fg: '#8B5A2C' },
    { bg: '#E8DCC0',   fg: '#6B5A36' },
    { bg: '#C9D7C2',   fg: '#3D5A3F' },
  ];
  const p = palettes[(name.charCodeAt(0) + name.length) % 4];
  return (
    <div style={{
      width: size, height: size, borderRadius: 12,
      background: p.bg, color: p.fg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: T.serif, fontSize: size * 0.38, fontWeight: 500,
      flexShrink: 0,
    }}>{initials}</div>
  );
}

// ── Frame, Nav, Footer ──────────────────────────────────────
function Frame({ children, scroll = false, width = 1100, height = 720 }) {
  return (
    <div style={{
      width, height, background: T.bg, color: T.ink,
      fontFamily: T.sans, overflow: scroll ? 'auto' : 'hidden',
      position: 'relative',
    }}>
      {children}
    </div>
  );
}

function Nav({ active, loggedIn = false }) {
  const links = [['home', 'Home'], ['directory', 'Directory'], ['about', 'About']];
  return (
    <nav style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '18px 36px', borderBottom: `1px solid ${T.rule}`,
      background: T.bg,
    }}>
      <Wordmark size={16} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 28, fontSize: 14 }}>
        {links.map(([k, l]) => (
          <span key={k} style={{
            color: active === k ? T.ink : T.inkSoft,
            fontWeight: active === k ? 600 : 500,
            cursor: 'pointer',
          }}>{l}</span>
        ))}
        {loggedIn ? (
          <>
            <span style={{ color: T.inkSoft, cursor: 'pointer', fontWeight: 500 }}>Settings</span>
            <Avatar name="Ibrahim Siddiqui" size={32} />
          </>
        ) : (
          <>
            <span style={{ color: T.inkSoft, cursor: 'pointer', fontWeight: 500 }}>Log in</span>
            <Btn size="sm">Offer your time</Btn>
          </>
        )}
      </div>
    </nav>
  );
}

function Footer() {
  return (
    <div style={{
      padding: '24px 36px', borderTop: `1px solid ${T.rule}`,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontSize: 12.5, color: T.inkMute, background: T.bg,
    }}>
      <span>© 2026 Sadaqa Jariyah · sadaqajariyah.online · Run by community volunteers</span>
      <span style={{ display: 'flex', gap: 20 }}>
        <span style={{ cursor: 'pointer' }}>Privacy</span>
        <span style={{ cursor: 'pointer' }}>Terms</span>
        <span style={{ cursor: 'pointer' }}>Contact</span>
      </span>
    </div>
  );
}

// ── Field component ─────────────────────────────────────────
function Field({ label, placeholder, value, multiline, help, suffix }) {
  return (
    <label style={{ display: 'block' }}>
      <div style={{ fontSize: 12.5, fontWeight: 600, color: T.ink, marginBottom: 6 }}>{label}</div>
      <div style={{ position: 'relative' }}>
        {multiline ? (
          <textarea defaultValue={value} placeholder={placeholder} rows={4} style={{
            width: '100%', padding: '12px 14px', borderRadius: 10,
            border: `1px solid ${T.rule}`, background: T.bgCard,
            fontFamily: T.sans, fontSize: 14, color: T.ink, outline: 'none',
            resize: 'vertical', lineHeight: 1.5,
          }} />
        ) : (
          <input defaultValue={value} placeholder={placeholder} style={{
            width: '100%', padding: '12px 14px', borderRadius: 10,
            border: `1px solid ${T.rule}`, background: T.bgCard,
            fontFamily: T.sans, fontSize: 14, color: T.ink, outline: 'none',
            paddingRight: suffix ? 70 : 14,
          }} />
        )}
        {suffix && (
          <span style={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            fontSize: 12, color: T.inkMute, fontFamily: T.mono,
          }}>{suffix}</span>
        )}
      </div>
      {help && <div style={{ fontSize: 12, color: T.inkMute, marginTop: 6 }}>{help}</div>}
    </label>
  );
}

// ── Screens ─────────────────────────────────────────────────

function Home() {
  return (
    <Frame>
      <Nav active="home" />
      <div style={{
        background: T.bgSoft, padding: '64px 36px 56px',
        borderBottom: `1px solid ${T.rule}`,
      }}>
        <div style={{ maxWidth: 980, margin: '0 auto' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '5px 12px', borderRadius: 999,
            background: T.bgCard, border: `1px solid ${T.rule}`,
            fontSize: 12.5, color: T.sageDeep, fontWeight: 500,
            marginBottom: 24,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: T.sage }} />
            <span>{window.SJ_DATA.members.length} members offering their time</span>
          </div>
          <h1 style={{
            fontFamily: T.display, fontSize: 60, lineHeight: 1.05,
            fontWeight: 600, letterSpacing: '-0.035em',
            color: T.ink, margin: '0 0 20px',
            maxWidth: 760, textWrap: 'balance',
          }}>
            Find someone in your community to&nbsp;help.
          </h1>
          <p style={{
            fontSize: 18.5, lineHeight: 1.5, color: T.inkSoft,
            maxWidth: 600, margin: '0 0 32px',
          }}>
            A directory of community members offering mentorship, counsel, and quiet hours of
            their time — in the spirit of <em style={{ color: T.sageDeep }}>sadaqa jariyah</em>, a charity that keeps flowing.
          </p>
          <div style={{ display: 'flex', gap: 10 }}>
            <Btn size="lg">Browse the directory →</Btn>
            <Btn size="lg" variant="ghost">Offer your time</Btn>
          </div>
        </div>
      </div>

      <div style={{
        padding: '50px 36px 30px', maxWidth: 980, margin: '0 auto',
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 22,
      }}>
        {[
          { n: '01', t: 'Browse', d: 'Search by name, language, or what you need help with. Filter by predefined categories.' },
          { n: '02', t: 'Read', d: 'Each member writes a short bio in their own words and lists what they’re glad to help with.' },
          { n: '03', t: 'Schedule', d: 'Booking goes through the member’s own scheduling tool. We never see your appointment.' },
        ].map(s => (
          <div key={s.n} style={{
            padding: 24, borderRadius: 14,
            background: T.bgCard, border: `1px solid ${T.rule}`,
          }}>
            <div style={{ fontFamily: T.mono, fontSize: 12, color: T.clay, marginBottom: 12, letterSpacing: '-0.02em' }}>{s.n}</div>
            <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 6, letterSpacing: '-0.02em' }}>{s.t}</div>
            <div style={{ fontSize: 13.5, lineHeight: 1.55, color: T.inkSoft }}>{s.d}</div>
          </div>
        ))}
      </div>

      <Footer />
    </Frame>
  );
}

function Directory() {
  const data = window.SJ_DATA;
  const [q, setQ] = useState('');
  const [cat, setCat] = useState('all');
  const filtered = useMemo(() => data.members.filter(m => {
    const okQ = !q || m.name.toLowerCase().includes(q.toLowerCase()) ||
                (m.otherText || '').toLowerCase().includes(q.toLowerCase()) ||
                m.bio.toLowerCase().includes(q.toLowerCase());
    const okC = cat === 'all' || m.services.some(s => s.toLowerCase().replace(/[^a-z]+/g, '-').includes(cat));
    return okQ && okC;
  }), [q, cat]);

  return (
    <Frame scroll>
      <Nav active="directory" />
      <div style={{ padding: '32px 36px 16px', maxWidth: 1080, margin: '0 auto' }}>
        <h1 style={{
          fontFamily: T.display, fontSize: 36, fontWeight: 600,
          margin: '0 0 6px', letterSpacing: '-0.03em',
        }}>Directory</h1>
        <p style={{ color: T.inkSoft, fontSize: 14.5, margin: '0 0 22px' }}>
          {data.members.length} members offering their time. Search and filter to find the right person.
        </p>

        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16,
        }}>
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', gap: 10,
            padding: '12px 16px', border: `1px solid ${T.rule}`,
            borderRadius: 10, background: T.bgCard,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={T.inkSoft} strokeWidth="2">
              <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Search by name, or what you need help with…"
              style={{
                flex: 1, border: 'none', background: 'transparent', outline: 'none',
                fontFamily: T.sans, fontSize: 14, color: T.ink,
              }}
            />
            {q && <button onClick={() => setQ('')} style={{ border: 'none', background: 'transparent', color: T.inkMute, cursor: 'pointer', fontSize: 12 }}>Clear</button>}
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 24 }}>
          {[{slug: 'all', name: 'All', count: data.members.length}, ...data.categories].map(c => (
            <button key={c.slug} onClick={() => setCat(c.slug)} style={{
              padding: '6px 12px', borderRadius: 8,
              border: `1px solid ${cat === c.slug ? T.sageDeep : T.rule}`,
              background: cat === c.slug ? T.sageSoft : T.bgCard,
              color: cat === c.slug ? T.sageDeep : T.inkSoft,
              fontFamily: T.sans, fontSize: 13, fontWeight: 500, cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}>
              {c.name}
              <span style={{ fontSize: 11, color: cat === c.slug ? T.sageDeep : T.inkMute, opacity: 0.7 }}>{c.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div style={{
        maxWidth: 1080, margin: '0 auto', padding: '0 36px 32px',
      }}>
        <div style={{
          background: T.bgCard, border: `1px solid ${T.rule}`,
          borderRadius: 12, overflow: 'hidden',
        }}>
          {filtered.map((m, i) => (
            <div key={m.username} style={{
              display: 'grid', gridTemplateColumns: '52px 1fr 220px auto', gap: 18,
              padding: '18px 20px',
              borderTop: i === 0 ? 'none' : `1px solid ${T.ruleSoft}`,
              alignItems: 'center',
            }}>
              <Avatar name={m.name} size={44} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 3, letterSpacing: '-0.015em' }}>{m.name}</div>
                <div style={{
                  fontSize: 13, color: T.inkSoft, lineHeight: 1.45,
                  display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                }}>{m.bio}</div>
                <div style={{ fontSize: 11.5, color: T.inkMute, marginTop: 6, fontFamily: T.mono }}>
                  {m.city} · {m.languages.join(', ')}
                </div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignContent: 'center' }}>
                {m.services.slice(0, 2).map(s => (
                  <span key={s} style={{
                    fontSize: 11.5, padding: '3px 9px', borderRadius: 6,
                    background: T.sageSoft, color: T.sageDeep, fontWeight: 500,
                  }}>{m.otherText && s === 'Other' ? m.otherText : s}</span>
                ))}
              </div>
              <Btn size="sm" variant="ghost">View →</Btn>
            </div>
          ))}
          {filtered.length === 0 && (
            <div style={{
              padding: 60, textAlign: 'center', color: T.inkSoft,
              fontFamily: T.serif, fontStyle: 'italic', fontSize: 17,
            }}>No one matches that search yet.</div>
          )}
        </div>

        <div style={{
          marginTop: 22, display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', fontSize: 13, color: T.inkSoft,
        }}>
          <span>Showing {filtered.length} of {data.members.length}</span>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <Btn size="sm" variant="ghost">←</Btn>
            <span style={{ padding: '8px 12px', fontWeight: 600 }}>1</span>
            <span style={{ padding: '8px 12px', color: T.inkMute, cursor: 'pointer' }}>2</span>
            <Btn size="sm" variant="ghost">→</Btn>
          </div>
        </div>
      </div>

      <Footer />
    </Frame>
  );
}

function Profile() {
  const m = window.SJ_DATA.members[0];
  return (
    <Frame scroll>
      <Nav active="directory" />
      <div style={{ padding: '24px 36px 12px', maxWidth: 980, margin: '0 auto' }}>
        <div style={{ fontSize: 13, color: T.inkSoft, marginBottom: 20, cursor: 'pointer' }}>
          ← Back to directory
        </div>
      </div>

      <div style={{
        padding: '0 36px 48px', maxWidth: 980, margin: '0 auto',
        display: 'grid', gridTemplateColumns: '1fr 320px', gap: 40, alignItems: 'start',
      }}>
        <div>
          <div style={{ display: 'flex', gap: 18, alignItems: 'center', marginBottom: 24 }}>
            <Avatar name={m.name} size={68} />
            <div>
              <h1 style={{
                fontFamily: T.display, fontSize: 34, fontWeight: 600,
                margin: '0 0 4px', letterSpacing: '-0.025em', lineHeight: 1.1,
              }}>{m.name}</h1>
              <div style={{ fontSize: 14, color: T.inkSoft, fontFamily: T.mono }}>
                {m.city} · {m.languages.join(' · ')}
              </div>
            </div>
          </div>

          <p style={{
            fontSize: 17, lineHeight: 1.6, color: T.ink,
            margin: '0 0 30px', maxWidth: 580,
          }}>
            {m.bio}
          </p>

          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 11.5, fontWeight: 600, color: T.inkMute, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>
              Glad to help with
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {m.services.map(s => (
                <span key={s} style={{
                  fontSize: 13, padding: '7px 14px', borderRadius: 8,
                  background: T.sageSoft, color: T.sageDeep, fontWeight: 500,
                }}>{s}</span>
              ))}
            </div>
          </div>

          <div style={{
            padding: '14px 18px', borderRadius: 10,
            background: T.bgCard, border: `1px solid ${T.rule}`,
            fontSize: 13, color: T.inkSoft, lineHeight: 1.55,
          }}>
            <strong style={{ color: T.ink }}>How scheduling works.</strong>{' '}
            Booking happens on {m.name.split(' ')[0]}’s {m.tool}. Sadaqa Jariyah doesn’t see your appointment,
            your name, or your reason for booking.
          </div>
        </div>

        <div style={{
          background: T.sageDeep, color: T.bgCard, padding: 24, borderRadius: 14,
          position: 'sticky', top: 20,
        }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: T.sageSoft, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 8 }}>
            Schedule a session
          </div>
          <div style={{
            fontFamily: T.display, fontSize: 22, fontWeight: 600,
            lineHeight: 1.25, marginBottom: 18, letterSpacing: '-0.02em',
          }}>
            Book directly with {m.name.split(' ')[0]}.
          </div>
          <button style={{
            width: '100%', padding: '14px', borderRadius: 10,
            background: T.bgCard, color: T.ink, border: 'none',
            fontFamily: T.sans, fontSize: 15, fontWeight: 600, cursor: 'pointer',
            letterSpacing: '-0.005em',
          }}>Schedule with me →</button>
          <div style={{
            fontSize: 11.5, color: 'rgba(251,247,238,0.7)',
            textAlign: 'center', marginTop: 10,
          }}>
            Opens {m.tool} in a new tab
          </div>

          <div style={{
            marginTop: 22, paddingTop: 18,
            borderTop: `1px solid rgba(251,247,238,0.18)`,
            fontSize: 12.5, lineHeight: 1.7,
          }}>
            <Row k="Member since" v="2023" />
            <Row k="Languages" v={m.languages.join(', ')} />
            <Row k="Tool" v={m.tool} />
          </div>
        </div>
      </div>

      <Footer />
    </Frame>
  );
}

function Row({ k, v }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
      <span style={{ color: 'rgba(251,247,238,0.6)' }}>{k}</span>
      <span style={{ color: T.bgCard, fontWeight: 500 }}>{v}</span>
    </div>
  );
}

function Signup() {
  return (
    <Frame scroll>
      <Nav active="home" />
      <div style={{
        background: T.bgSoft, padding: '40px 36px',
        borderBottom: `1px solid ${T.rule}`,
      }}>
        <div style={{ maxWidth: 480, margin: '0 auto', textAlign: 'center' }}>
          <h1 style={{
            fontFamily: T.display, fontSize: 38, fontWeight: 600,
            margin: '0 0 8px', letterSpacing: '-0.03em',
          }}>Offer your time</h1>
          <p style={{ fontSize: 15, color: T.inkSoft, margin: 0 }}>
            Three minutes to set up. Free for the community, always.
          </p>
        </div>
      </div>
      <div style={{ padding: '36px', maxWidth: 480, margin: '0 auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Field label="Full name" placeholder="Maryam Abdul-Rahman" />
          <Field label="Username" placeholder="maryam" help="Your profile lives at sadaqajariyah.online/p/[username]. Case-insensitive, 3–30 characters." />
          <Field label="Email" placeholder="maryam@example.com" />
          <Field label="Password" placeholder="••••••••••" help="Minimum 10 characters. We never see your password — it’s hashed before storage." />

          <label style={{ display: 'flex', gap: 10, fontSize: 13.5, color: T.inkSoft, marginTop: 6 }}>
            <input type="checkbox" defaultChecked style={{ accentColor: T.sageDeep, marginTop: 2 }} />
            <span>I agree to the <span style={{ color: T.sageDeep, fontWeight: 600, cursor: 'pointer' }}>Terms</span> and <span style={{ color: T.sageDeep, fontWeight: 600, cursor: 'pointer' }}>Privacy notice</span>.</span>
          </label>

          <Btn size="lg" style={{ marginTop: 8 }}>Create my account</Btn>
          <div style={{ textAlign: 'center', fontSize: 13.5, color: T.inkSoft, marginTop: 4 }}>
            Already a member? <span style={{ color: T.sageDeep, fontWeight: 600, cursor: 'pointer' }}>Log in →</span>
          </div>
        </div>
      </div>
      <Footer />
    </Frame>
  );
}

function Login() {
  return (
    <Frame>
      <Nav active="home" />
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 'calc(100% - 65px - 65px)', background: T.bgSoft,
      }}>
        <div style={{
          width: 380, background: T.bgCard, borderRadius: 14, padding: 32,
          border: `1px solid ${T.rule}`,
        }}>
          <Mark size={36} />
          <h1 style={{ fontFamily: T.display, fontSize: 26, fontWeight: 600, margin: '18px 0 4px', letterSpacing: '-0.02em' }}>
            Welcome back
          </h1>
          <p style={{ fontSize: 14, color: T.inkSoft, margin: '0 0 24px' }}>
            Log in to update your profile or scheduling link.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Field label="Email" placeholder="maryam@example.com" />
            <Field label="Password" placeholder="••••••••••" />
            <div style={{ textAlign: 'right', fontSize: 12.5, color: T.sageDeep, marginTop: -4, fontWeight: 600, cursor: 'pointer' }}>
              Forgot your password?
            </div>
            <Btn size="lg" style={{ marginTop: 6 }}>Log in</Btn>
          </div>

          <div style={{
            marginTop: 22, paddingTop: 18, borderTop: `1px solid ${T.rule}`,
            fontSize: 13, color: T.inkSoft, textAlign: 'center',
          }}>
            New here? <span style={{ color: T.sageDeep, fontWeight: 600, cursor: 'pointer' }}>Offer your time →</span>
          </div>
        </div>
      </div>
      <Footer />
    </Frame>
  );
}

function Edit() {
  const cats = window.SJ_DATA.categories;
  const [sel, setSel] = useState(['mentoring', 'career-advice']);
  const toggle = s => setSel(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s]);

  return (
    <Frame scroll>
      <Nav active="home" loggedIn />
      <div style={{ padding: '32px 36px 24px', maxWidth: 720, margin: '0 auto' }}>
        <div style={{ display: 'flex', gap: 6, fontSize: 13, color: T.inkSoft, marginBottom: 14 }}>
          <span style={{ cursor: 'pointer' }}>Settings</span>
          <span>·</span>
          <span style={{ color: T.ink, fontWeight: 500 }}>Profile</span>
        </div>
        <h1 style={{
          fontFamily: T.display, fontSize: 32, fontWeight: 600,
          margin: '0 0 6px', letterSpacing: '-0.025em',
        }}>Your profile</h1>
        <p style={{ fontSize: 14, color: T.inkSoft, margin: '0 0 24px' }}>
          What appears at <span style={{ fontFamily: T.mono, color: T.sageDeep }}>sadaqajariyah.online/p/ibrahim-s</span>
        </p>

        <div style={{
          background: '#FBF1D6', border: `1px solid #E8D58A`, borderRadius: 10,
          padding: '12px 16px', marginBottom: 24, fontSize: 13.5,
          color: '#6B5418', display: 'flex', gap: 10, alignItems: 'flex-start',
        }}>
          <span>⚠</span>
          <span>We don’t recognize this scheduling tool — make sure the link works for visitors.</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <Field label="Full name" value="Ibrahim Siddiqui" />
          <Field label="Bio" multiline value="Software engineer at a healthcare startup. Happy to talk through resumes, technical interviews, and the early years of a tech career with anyone in the community." help="World-readable. 20–1000 characters." />
          <Field label="Scheduling link" value="https://meetings.example-tool.io/ibrahim/30min" help="Calendly, Cal.com, SavvyCal, Google appointments — any tool. Must start with https://" />

          <div>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: T.ink, marginBottom: 10 }}>Services you offer</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {cats.map(c => (
                <button key={c.slug} onClick={() => toggle(c.slug)} style={{
                  padding: '6px 12px', borderRadius: 8,
                  border: `1px solid ${sel.includes(c.slug) ? T.sageDeep : T.rule}`,
                  background: sel.includes(c.slug) ? T.sageSoft : T.bgCard,
                  color: sel.includes(c.slug) ? T.sageDeep : T.inkSoft,
                  fontFamily: T.sans, fontSize: 13, fontWeight: 500, cursor: 'pointer',
                }}>{c.name}</button>
              ))}
            </div>
            {sel.includes('other') && (
              <input
                placeholder="Briefly describe what you offer (140 chars)"
                style={{
                  width: '100%', marginTop: 12,
                  padding: '12px 14px', borderRadius: 10,
                  border: `1px solid ${T.rule}`, background: T.bgCard,
                  fontFamily: T.sans, fontSize: 14, outline: 'none',
                }}
              />
            )}
          </div>

          <div style={{
            display: 'flex', gap: 10, marginTop: 12, paddingTop: 22,
            borderTop: `1px solid ${T.rule}`,
          }}>
            <Btn>Save changes</Btn>
            <Btn variant="ghost">View public profile</Btn>
          </div>
        </div>
      </div>
      <Footer />
    </Frame>
  );
}

function Owner() {
  return (
    <Frame>
      <Nav active="directory" loggedIn />
      <div style={{ padding: '24px 36px 12px', maxWidth: 720, margin: '0 auto' }}>
        <div style={{
          background: '#FBF1D6', border: `1px solid #E8D58A`, borderRadius: 10,
          padding: '14px 18px', marginBottom: 24, fontSize: 13.5,
          color: '#6B5418', display: 'flex', gap: 12, alignItems: 'flex-start',
        }}>
          <span style={{ fontSize: 18 }}>⚠</span>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 2, color: '#3F3208' }}>
              Your profile is hidden from the directory
            </div>
            Add a scheduling link in <span style={{ textDecoration: 'underline', cursor: 'pointer' }}>settings</span> to publish it.
            Only you can see this page right now.
          </div>
        </div>

        <div style={{ display: 'flex', gap: 18, alignItems: 'center', marginBottom: 22 }}>
          <Avatar name="Ibrahim Siddiqui" size={68} />
          <div>
            <h1 style={{
              fontFamily: T.display, fontSize: 30, fontWeight: 600,
              margin: '0 0 4px', letterSpacing: '-0.025em',
            }}>Ibrahim Siddiqui</h1>
            <div style={{ fontSize: 13.5, color: T.inkSoft, fontFamily: T.mono }}>
              Toronto, ON · English, Urdu
            </div>
          </div>
        </div>

        <p style={{
          fontSize: 16, lineHeight: 1.6, color: T.ink,
          margin: '0 0 28px', maxWidth: 540,
        }}>
          Software engineer at a healthcare startup. Happy to talk through resumes, technical
          interviews, and the early years of a tech career.
        </p>

        <div style={{
          padding: 24, borderRadius: 12,
          border: `1.5px dashed ${T.rule}`,
          textAlign: 'center', background: T.bgCard,
        }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>
            Add a scheduling link to publish
          </div>
          <div style={{
            fontSize: 13.5, color: T.inkSoft, marginBottom: 14,
            lineHeight: 1.5, maxWidth: 360, marginInline: 'auto',
          }}>
            Once you link Calendly, Cal.com, or any scheduling tool, your profile will appear in the directory.
          </div>
          <Btn>Add a scheduling link</Btn>
        </div>
      </div>
      <Footer />
    </Frame>
  );
}

function Privacy() {
  return (
    <Frame scroll>
      <Nav active="about" />
      <div style={{
        background: T.bgSoft, padding: '40px 36px', borderBottom: `1px solid ${T.rule}`,
      }}>
        <div style={{ maxWidth: 680, margin: '0 auto' }}>
          <div style={{
            fontSize: 12, fontWeight: 600, color: T.sageDeep,
            letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8,
          }}>
            Privacy notice
          </div>
          <h1 style={{
            fontFamily: T.display, fontSize: 40, fontWeight: 600,
            margin: '0 0 8px', letterSpacing: '-0.03em', lineHeight: 1.1,
          }}>What we hold, and what we don’t.</h1>
          <p style={{ fontSize: 13, color: T.inkMute, margin: 0, fontFamily: T.mono }}>
            Last updated 3 May 2026
          </p>
        </div>
      </div>
      <div style={{ padding: '40px 36px 50px', maxWidth: 680, margin: '0 auto' }}>
        {[
          ['What we collect at signup', 'Your email, a password (hashed, never stored in the clear), a chosen username, and the IP address of your signup request as recorded in our request logs.'],
          ['What is shown publicly', 'Your full name, your bio, the services you list, and your scheduling link. Anything in those fields is world-readable — write only what you’re comfortable with strangers reading.'],
          ['What we never see', 'Your appointments. When a visitor clicks your scheduling link, they’re sent to your scheduling tool with that tool’s own privacy policy. We do not see who books, when, or why.'],
          ['Auth-flow email only', 'We send password resets and signup confirmations. We do not send marketing or booking-related email.'],
          ['Account deactivation', 'Email the operator and we’ll deactivate your account. Self-serve deletion will arrive in a later version.'],
        ].map(([t, body]) => (
          <div key={t} style={{
            paddingBottom: 22, marginBottom: 22, borderBottom: `1px solid ${T.rule}`,
          }}>
            <h2 style={{
              fontFamily: T.display, fontSize: 19, fontWeight: 600,
              margin: '0 0 8px', letterSpacing: '-0.02em',
            }}>{t}</h2>
            <p style={{ fontSize: 14.5, lineHeight: 1.6, color: T.inkSoft, margin: 0 }}>{body}</p>
          </div>
        ))}
      </div>
      <Footer />
    </Frame>
  );
}

window.FinalScreens = {
  Home, Directory, Profile, Signup, Login, Edit, Owner, Privacy,
};
