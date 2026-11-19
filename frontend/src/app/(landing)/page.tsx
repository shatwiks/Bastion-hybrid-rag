import React from "react";
import { LandingScripts } from "@/components/LandingScripts";

const STACK_HUB_SPEC = JSON.stringify({
  layout: "hub",
  alt: "Bastion connects PostgreSQL, Redis, FastAPI, Ollama, OpenAI, and Anthropic behind one retrieval pipeline.",
  ground: "none",
  motion: { cycle: 3.4 },
  center: { label: "Bastion", icon: "ui:shield" },
  spokes: [
    { label: "Postgres", icon: "postgres" },
    { label: "Redis", icon: "redis" },
    { label: "FastAPI", icon: "fastapi" },
    { label: "Ollama", icon: "ollama" },
    { label: "OpenAI", icon: "openai" },
    { label: "Anthropic", icon: "anthropic" },
  ],
});

export default function BastionLandingPage() {
  return (
    <>
      {/* type: software
          deal: hero centred, palette stone-blueprint, type urbanist (second dealt pairing after epilogue failed hero-lines at 36 chars), radius sharp, nav nav-mega, close close-type, footer footer-dark, rhythm space, buttons tonal, mark ring, ground sand, effect gradient-mesh
          moments: pinned-chapters (#walkthrough, re-dealt excluding marquee-row) */}

      <header className="nav">
        <div className="wrap nav__bar">
          <a className="skip-link" href="#top">
            Skip to content
          </a>
          <a className="nav__logo" href="#top">
            <span className="mark" data-mark="ring" aria-hidden="true" />
            Bastion
          </a>

          <nav className="nav__links" aria-label="Main">
            <div className="nav__item">
              <a className="nav__link" href="#engine">
                Engine{" "}
                <svg className="chev" viewBox="0 0 12 12" aria-hidden="true">
                  <path
                    d="M3 4.5l3 3 3-3"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </a>
              <div className="nav__menu">
                <div className="wrap grid">
                  <div className="menu-col span-3">
                    <p className="t-label">Security</p>
                    <a href="#engine">
                      SQL RBAC<span>Pre-retrieval WHERE isolation</span>
                    </a>
                    <a href="#engine">
                      Refusal gate<span>Blocks answers below 0.65</span>
                    </a>
                    <a href="#engine">
                      Scoped cache<span>Tenant and entity cache keys</span>
                    </a>
                  </div>
                  <div className="menu-col span-3">
                    <p className="t-label">Retrieval</p>
                    <a href="#pipeline">
                      Hybrid RRF<span>pgvector cosine plus dual FTS</span>
                    </a>
                    <a href="#benchmarks">
                      Benchmarks<span>28 probes and 14 refusal traps</span>
                    </a>
                  </div>
                  <a className="menu-card span-3 start-10" href="/workspace">
                    <div className="panel">
                      <img
                        className="frame__img"
                        src="/assets/ui-preview.png"
                        alt="Bastion split-pane workspace with citation popovers and live 6-step telemetry"
                      />
                    </div>
                    <span className="t-card">Live inspector</span>
                    <span className="t-small muted">
                      Switch roles and watch all six stages
                    </span>
                  </a>
                </div>
              </div>
            </div>
            <div className="nav__item">
              <a className="nav__link" href="#pipeline">
                Pipeline
              </a>
            </div>
            <div className="nav__item">
              <a className="nav__link" href="#benchmarks">
                Benchmarks
              </a>
            </div>
            <div className="nav__item">
              <a className="nav__link" href="#questions">
                Questions
              </a>
            </div>
          </nav>

          <div className="nav__actions">
            <a className="nav__link" href="#benchmarks">
              Read benchmarks
            </a>
            <a className="btn btn--primary" href="/workspace">
              Open live workspace
            </a>
          </div>

          <button
            className="nav__toggle"
            type="button"
            aria-expanded="false"
            aria-label="Menu"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path
                d="M2 5h14M2 13h14"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </header>

      <main id="top">
        {/* Screen 1: Dealt hero--centred */}
        <section
          className="hero hero--centred"
          data-enter=""
          aria-labelledby="hero-h"
        >
          <div className="wrap">
            <div className="hero-text">
              <div className="hero__c">
                <a className="pill" href="#benchmarks">
                  <span>100% precision</span>
                  <span className="muted">28 benchmark probes</span>
                </a>
                <h1 id="hero-h" aria-label="Hybrid RAG for engineering teams">
                  <span className="ly-mark" aria-hidden="true" /> Hybrid RAG for
                  engineering teams
                </h1>
                <p className="hero__lead">
                  Bastion filters document roles inside PostgreSQL before
                  ranking, fuses pgvector with BM25, and refuses low-confidence
                  answers below 0.65.
                </p>
                <div className="btn-row">
                  <a className="btn btn--primary" href="/workspace">
                    Open live workspace
                    <svg className="m-arrow" viewBox="0 0 12 12" aria-hidden="true">
                      <path className="m-arrow__stem" d="M1 6h8" />
                      <path className="m-arrow__head" d="M4.5 2.5 8 6l-3.5 3.5" />
                    </svg>
                  </a>
                  <a className="btn btn--secondary" href="#benchmarks">
                    See benchmark results
                  </a>
                </div>
              </div>

              <div
                className="hero__window"
                data-fx="gradient-mesh"
                data-fx-seed="7"
                data-fx-palette='{"bg":"#d9ccb7","surface":"#e9e0d2","ink":"#2a2622","accent":"#a8794a"}'
                role="img"
                aria-label="Bastion answering an ERR_409_CONFLICT lock contention query with verified inline citations under support_tier_1"
              >
                <div className="ly-piece b-win" aria-hidden="true">
                  <div className="b-win__bar">
                    <span className="b-win__dots">
                      <i />
                      <i />
                      <i />
                    </span>
                    <span>
                      <b>hybrid-kb</b> · support_tier_1
                    </span>
                    <span className="sp" />
                    <span>pgvector · Redis · 0.65 Gate</span>
                  </div>
                  <div className="b-win__body">
                    <div className="b-inbox">
                      <div className="q">scope:f5125156</div>
                      <div className="t is-on">
                        <i style={{ background: "#c8d9f8" }}>T1</i>
                        <b>ERR_409_CONFLICT</b>
                        <time>0.996</time>
                        <span>storage-cli locks release</span>
                      </div>
                      <div className="t">
                        <i style={{ background: "#b9dfc8" }}>T1</i>
                        <b>SKU-9921-A limits</b>
                        <time>0.989</time>
                        <span>368.6 TB · 1,180 W dual PSU</span>
                      </div>
                      <div className="t">
                        <i style={{ background: "#f2c6c6" }}>PB</i>
                        <b>Q3 M&amp;A targets</b>
                        <time>0.000</time>
                        <span>Refused · 0 LLM tokens spent</span>
                      </div>
                    </div>
                    <div className="b-convo">
                      <div className="b-chat" data-ly-steps="900">
                        <div className="b-msg b-msg--me">
                          How do I resolve ERR_409_CONFLICT during storage sync?
                        </div>
                        <div className="b-tool" data-step="">
                          SQL RBAC + Hybrid RRF (25 chunks) · Cross-Encoder 0.9964
                        </div>
                        <div className="b-msg b-msg--bot" data-step="">
                          Inspect the lock owner with storage-cli locks inspect,
                          release stale leases older than 30 seconds, and resume
                          sync with backoff.
                          <small>4 verified sources</small>
                        </div>
                        <div className="b-acts" data-step="">
                          <span>Inspect citation</span>
                          <span>View 6-step trace</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Screen 2: app-frame (full-width real product window) */}
        <section
          className="section"
          id="pipeline"
          aria-labelledby="pipeline-h"
        >
          <div className="wrap">
            <div className="grid">
              <div className="span-5">
                <h2 id="pipeline-h">Bastion 6-step pipeline traces</h2>
              </div>
              <div className="span-6 start-7 stack-4">
                <p className="t-lead">
                  Bastion checks your signed role token, looks up scoped cache
                  entries, fuses vector and BM25 candidates, scores relevance,
                  and streams grounded citations in one inspectable view.
                </p>
                <p>
                  <a className="link" href="/workspace">
                    Inspect live trace
                  </a>
                </p>
              </div>
            </div>

            <div
              className="ui app fill"
              role="img"
              aria-label="Bastion multi-tenant request log beside the six-step hybrid retrieval and Cross-Encoder pipeline"
              data-ui-pause-host=""
            >
              <div className="app__pane app__pane--list">
                <div
                  className="ui ui-panel ui-win"
                  data-ui="window"
                  data-open="Checking"
                  data-work="Reranking"
                  data-done="Grounded"
                >
                  <div className="ui-win__bar">
                    <span className="ui-dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    <span className="ui-win__crumb">
                      Bastion <i>/</i> <b>Traces</b>
                    </span>
                    <span className="ui-spacer" />
                    <span className="ui-win__search" aria-hidden="true">
                      <span className="ui-win__ph">Filter</span>
                      <span className="ui-kbd">/</span>
                    </span>
                  </div>
                  <div className="ui-win__body">
                    <nav className="ui-win__side" aria-hidden="true">
                      <span className="ui-win__nav is-on">
                        Traces<em>9</em>
                      </span>
                      <span className="ui-win__nav">
                        Cached<em>3</em>
                      </span>
                      <span className="ui-win__nav">
                        Refused<em>2</em>
                      </span>
                      <span className="ui-win__nav">Ingest</span>
                      <span className="ui-win__label">Indexes</span>
                      <span className="ui-win__nav">
                        <span className="ui-win__hash">#</span>runbooks
                      </span>
                      <span className="ui-win__nav">
                        <span className="ui-win__hash">#</span>architecture
                      </span>
                    </nav>
                    <div className="ui-win__main">
                      <div className="ui-win__cols" aria-hidden="true">
                        <span>Scope</span>
                        <span>Query</span>
                        <span>Outcome</span>
                        <span>Score</span>
                      </div>
                      <ul className="ui-win__rows">
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="1">
                            T1
                          </span>
                          <span className="ui-win__who">role / tier_1</span>
                          <span className="ui-win__sub">
                            Resolve ERR_409_CONFLICT lock
                          </span>
                          <span className="ui-win__st is-done" data-st="">
                            Grounded
                          </span>
                          <span className="ui-win__age">0.996</span>
                        </li>
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="2">
                            PB
                          </span>
                          <span className="ui-win__who">role / public</span>
                          <span className="ui-win__sub">
                            Q3 M&amp;A expansion targets
                          </span>
                          <span className="ui-win__st is-you" data-st="">
                            Refused
                          </span>
                          <span className="ui-win__age">0.000</span>
                        </li>
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="3">
                            EX
                          </span>
                          <span className="ui-win__who">role / exec</span>
                          <span className="ui-win__sub">
                            Q3 M&amp;A expansion targets
                          </span>
                          <span className="ui-win__st is-done" data-st="">
                            Cache HIT
                          </span>
                          <span className="ui-win__age">61ms</span>
                        </li>
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="4">
                            T1
                          </span>
                          <span className="ui-win__who">role / tier_1</span>
                          <span className="ui-win__sub">
                            ERR_401_SEC_REVOKED mTLS fix
                          </span>
                          <span className="ui-win__st is-done" data-st="">
                            Grounded
                          </span>
                          <span className="ui-win__age">0.994</span>
                        </li>
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="5">
                            T1
                          </span>
                          <span className="ui-win__who">role / tier_1</span>
                          <span className="ui-win__sub">
                            SKU-9921-A dual PSU draw
                          </span>
                          <span className="ui-win__st is-done" data-st="">
                            Grounded
                          </span>
                          <span className="ui-win__age">0.991</span>
                        </li>
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="2">
                            EX
                          </span>
                          <span className="ui-win__who">role / exec</span>
                          <span className="ui-win__sub">
                            TARGET-AEGIS-7 board ceiling
                          </span>
                          <span className="ui-win__st is-done" data-st="">
                            Grounded
                          </span>
                          <span className="ui-win__age">0.988</span>
                        </li>
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="1">
                            PB
                          </span>
                          <span className="ui-win__who">role / public</span>
                          <span className="ui-win__sub">
                            Quantum wormhole flux capacitor
                          </span>
                          <span className="ui-win__st is-you" data-st="">
                            Refused
                          </span>
                          <span className="ui-win__age">0.001</span>
                        </li>
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="4">
                            T1
                          </span>
                          <span className="ui-win__who">role / tier_1</span>
                          <span className="ui-win__sub">
                            SKU-GLX-500 inspected TLS spec
                          </span>
                          <span className="ui-win__st is-done" data-st="">
                            Grounded
                          </span>
                          <span className="ui-win__age">0.993</span>
                        </li>
                        <li className="ui-win__row" data-row="">
                          <span className="ui-avatar" data-tone="3">
                            PB
                          </span>
                          <span className="ui-win__who">role / public</span>
                          <span className="ui-win__sub">
                            Mission-Critical uptime SLA
                          </span>
                          <span className="ui-win__st is-done" data-st="">
                            Cache HIT
                          </span>
                          <span className="ui-win__age">24ms</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="app__pane app__pane--open" data-ui-loop="">
                <div className="ui ui-panel ui-pipe" data-ui="pipeline-board">
                  <div className="ui-pipe__head">
                    <span className="ui-pipe__repo">bastion/rag</span>
                    <i className="ui-pipe__slash">/</i>
                    <code className="ui-pipe__ref">hybrid-kb</code>
                    <span className="ui-pipe__run">#f51251</span>
                    <span className="ui-spacer" />
                    <span className="ui-pipe__total">
                      <span data-pipe-total="">412ms</span>
                    </span>
                    <span
                      className="ui-chip ui-chip--ink ui-chip--live ui-pipe__chip"
                      data-pipe-chip=""
                      data-done="Grounded"
                    >
                      Streaming
                    </span>
                  </div>
                  <div className="ui-pipe__commit">
                    <span className="ui-avatar" data-tone="4">
                      T1
                    </span>
                    <span className="ui-pipe__msg">
                      How do I resolve ERR_409_CONFLICT?
                    </span>
                    <code className="ui-pipe__sha">0.9964</code>
                    <button
                      className="ui-btn ui-btn--ghost ui-btn--sm ui-pipe__btn"
                      type="button"
                      tabIndex={-1}
                      data-pipe-btn=""
                      data-done="Re-run"
                    >
                      Trace
                    </button>
                  </div>
                  <ol className="ui-pipe__steps">
                    <li className="ui-pipe__step is-done" data-step="auth">
                      <span className="ui-pipe__ico">
                        <svg viewBox="0 0 16 16" aria-hidden="true">
                          <path d="m4.5 8.2 2.3 2.3 4.7-5" />
                        </svg>
                      </span>
                      <span className="ui-pipe__name">
                        <span className="ui-pipe__tool" aria-hidden="true">
                          <img src="/assets/icons/fastapi.svg" alt="" />
                        </span>
                        <span className="ui-pipe__nm">Auth</span>
                      </span>
                      <code className="ui-pipe__cmd">PyJWT SecurityContext</code>
                      <span className="ui-pipe__time" data-time="">
                        0.4ms
                      </span>
                      <span className="ui-pipe__bar">
                        <i />
                      </span>
                    </li>
                    <li className="ui-pipe__step is-done" data-step="cache">
                      <span className="ui-pipe__ico">
                        <svg viewBox="0 0 16 16" aria-hidden="true">
                          <path d="m4.5 8.2 2.3 2.3 4.7-5" />
                        </svg>
                      </span>
                      <span className="ui-pipe__name">
                        <span className="ui-pipe__tool" aria-hidden="true">
                          <img src="/assets/icons/redis.svg" alt="" />
                        </span>
                        <span className="ui-pipe__nm">Cache</span>
                      </span>
                      <code className="ui-pipe__cmd">fp:err_409_conflict</code>
                      <span className="ui-pipe__time" data-time="">
                        18ms
                      </span>
                      <span className="ui-pipe__bar">
                        <i />
                      </span>
                    </li>
                    <li
                      className="ui-pipe__step is-run"
                      data-step="hybrid"
                      style={{ "--k": 0.7 } as React.CSSProperties}
                    >
                      <span className="ui-pipe__ico">
                        <svg viewBox="0 0 16 16" aria-hidden="true">
                          <path d="m4.5 8.2 2.3 2.3 4.7-5" />
                        </svg>
                      </span>
                      <span className="ui-pipe__name">
                        <span className="ui-pipe__tool" aria-hidden="true">
                          <img src="/assets/icons/postgres.svg" alt="" />
                        </span>
                        <span className="ui-pipe__nm">Hybrid</span>
                      </span>
                      <code className="ui-pipe__cmd">
                        WHERE tenant_id AND roles
                      </code>
                      <span className="ui-pipe__time" data-time="172ms">
                        124ms
                      </span>
                      <span className="ui-pipe__bar">
                        <i />
                      </span>
                    </li>
                    <li className="ui-pipe__step" data-step="gate">
                      <span className="ui-pipe__ico">
                        <svg viewBox="0 0 16 16" aria-hidden="true">
                          <path d="m4.5 8.2 2.3 2.3 4.7-5" />
                        </svg>
                      </span>
                      <span className="ui-pipe__name">
                        <span className="ui-pipe__tool" aria-hidden="true">
                          <img src="/assets/icons/python.svg" alt="" />
                        </span>
                        <span className="ui-pipe__nm">Gate</span>
                      </span>
                      <code className="ui-pipe__cmd">
                        ms-marco-MiniLM Sigmoid
                      </code>
                      <span className="ui-pipe__time" data-time="214ms">
                        Queued
                      </span>
                      <span className="ui-pipe__bar">
                        <i />
                      </span>
                    </li>
                    <li className="ui-pipe__step" data-step="stream">
                      <span className="ui-pipe__ico">
                        <svg viewBox="0 0 16 16" aria-hidden="true">
                          <path d="m4.5 8.2 2.3 2.3 4.7-5" />
                        </svg>
                      </span>
                      <span className="ui-pipe__name">
                        <span className="ui-pipe__tool" aria-hidden="true">
                          <img src="/assets/icons/ollama.svg" alt="" />
                        </span>
                        <span className="ui-pipe__nm">Stream</span>
                      </span>
                      <code className="ui-pipe__cmd">
                        SSE [chunk_id] stream
                      </code>
                      <span className="ui-pipe__time" data-time="34ms">
                        Queued
                      </span>
                      <span className="ui-pipe__bar">
                        <i />
                      </span>
                    </li>
                  </ol>
                  <div className="ui-pipe__log" aria-hidden="true">
                    <span className="ui-pipe__line" data-step="auth">
                      <b>$</b>verify HS256 JWT -&gt; scope_hash=f5125156de6f5c83
                    </span>
                    <span className="ui-pipe__line" data-step="cache">
                      <b>$</b>SCAN llm_cache:hybrid_kb:f5125156:err_409_conflict
                    </span>
                    <span className="ui-pipe__line is-on" data-step="hybrid">
                      <b>$</b>SET LOCAL hnsw.iterative_scan = &apos;relaxed_order&apos;
                    </span>
                    <span className="ui-pipe__line is-on" data-step="hybrid">
                      dense + dual-fts merged via RRF (k=60): 25 candidates
                    </span>
                    <span className="ui-pipe__line" data-step="gate">
                      <b>$</b>CrossEncoder top_score=0.9964 &gt;= 0.65 -&gt; PASS (4 chunks)
                    </span>
                    <span className="ui-pipe__line" data-step="stream">
                      <b>$</b>SSE emitted citations + async Langfuse trace committed
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Screens 3-4: features-2x2 (two screens via .g2) */}
        <section
          className="section g2"
          id="engine"
          aria-labelledby="engine-h"
        >
          <div className="wrap">
            <div className="group">
              <div className="section-head">
                <h2 id="engine-h">
                  Bastion 4 guardrails on every query.{" "}
                  <span className="muted">
                    SQL RBAC, hybrid search, 0.65 refusal and Redis cache.
                  </span>
                </h2>
              </div>

              <div className="grid">
                <article className="card card--row card--open span-6">
                  <h3>Bastion SQL RBAC filter</h3>
                  <p>
                    Tenant and role predicates execute inside PostgreSQL before
                    HNSW ranking.
                  </p>
                  <div
                    className="panel"
                    data-fx="grain-gradient"
                    data-fx-seed="21"
                    data-fx-palette='{"bg":"#d9ccb7","surface":"#e9e0d2","ink":"#2a2622","accent":"#a8794a"}'
                    data-fx-params='{"speed":0,"drift":0,"grainMotion":0}'
                    role="img"
                    aria-label="A public role request is blocked from reading confidential Q3 M&A documents"
                  >
                    <div className="stage stage--fade-b">
                      <div
                        className="at-rise fit"
                        style={
                          {
                            "--fit-max": "400px",
                            "--ax": "max(24px, 50% - 200px)",
                            "--ay": "32px",
                            "--ay-sm": "14px",
                          } as React.CSSProperties
                        }
                        data-ui-loop=""
                      >
                        <div className="ui ui-panel ui-chat" data-ui="chat">
                          <div className="ui-head">
                            <span className="ui-agent" aria-hidden="true" />
                            <div className="ui-title">
                              hybrid-kb · public
                            </div>
                            <span className="ui-chat__online">RBAC</span>
                            <span className="ui-spacer" />
                          </div>
                          <div className="ui-chat__body">
                            <div className="ui-chat__day">
                              scope:42062a7a · 0.65 gate
                            </div>
                            <div className="ui-msg ui-msg--me" data-chat-q="">
                              <span className="ui-msg__text">
                                What are the confidential Q3 M&amp;A targets?
                              </span>
                            </div>
                            <div className="ui-msg ui-msg--bot" data-chat-a="">
                              <span
                                className="ui-agent ui-msg__av"
                                aria-hidden="true"
                              />
                              <span className="ui-msg__col">
                                <span
                                  className="ui-chat__typing"
                                  aria-hidden="true"
                                >
                                  <i />
                                  <i />
                                  <i />
                                </span>
                                <span className="ui-chat__answer">
                                  Refused at <b>0.0000 &lt; 0.65</b>. Zero
                                  accessible chunks matched your public role.
                                </span>
                                <span className="ui-chat__srcs">
                                  <span className="ui-chat__src">
                                    LLM Called: FALSE (0 tokens)
                                  </span>
                                </span>
                              </span>
                            </div>
                          </div>
                          <div className="ui-chat__input">
                            <span className="ui-chat__ph">
                              Switch to Executive to re-run
                            </span>
                            <span className="ui-chat__send" aria-hidden="true">
                              <svg viewBox="0 0 16 16" width="14" height="14">
                                <path
                                  d="M8 13V3.5M3.8 7.5 8 3.3l4.2 4.2"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="1.7"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                />
                              </svg>
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </article>

                <article className="card card--row card--open span-6">
                  <h3>42-case CI benchmark gates</h3>
                  <p>
                    Every run benchmarks hybrid RRF across 28 retrieval probes
                    and 14 refusal traps.
                  </p>
                  <div
                    className="panel"
                    data-fx="grain-gradient"
                    data-fx-seed="34"
                    data-fx-palette='{"bg":"#c6d3df","surface":"#d6e0e9","ink":"#25303a","accent":"#3f6a92"}'
                    data-fx-params='{"speed":0,"drift":0,"grainMotion":0}'
                    role="img"
                    aria-label="Terminal benchmark run showing 100 percent retrieval precision, 32.59 percent MRR lift, and zero RBAC leakage"
                  >
                    <div className="stage">
                      <div
                        className="at-rise fit"
                        style={
                          {
                            "--fit-max": "430px",
                            "--ax": "max(24px, 50% - 215px)",
                            "--ay": "24px",
                            "--ay-sm": "14px",
                          } as React.CSSProperties
                        }
                      >
                        <div
                          className="ui ui-panel ui-term"
                          data-ui="terminal-run"
                        >
                          <div className="ui-term__head">
                            <span className="ui-dots" aria-hidden="true">
                              <i />
                              <i />
                              <i />
                            </span>
                            <span className="ui-term__title">
                              bastion/backend
                            </span>
                            <span className="ui-meta">uv</span>
                            <span className="ui-spacer" />
                            <span className="ui-chip ui-chip--plain ui-term__branch">
                              main
                            </span>
                          </div>
                          <div className="ui-term__screen" data-term-screen="">
                            <div className="ui-term__track" data-term-track="">
                              <div className="ui-term__ln ui-term__cmd">
                                <span className="ui-term__cwd">~/bastion</span>
                                <span className="ui-term__sig">$</span>
                                <span
                                  className="ui-term__typed"
                                  data-term-cmd=""
                                >
                                  uv run pytest tests -q
                                </span>
                              </div>
                              <div
                                className="ui-term__ln ui-term__meter"
                                data-term-out=""
                                data-term-meter=""
                              >
                                <span
                                  className="ui-term__bar"
                                  style={{ "--p": 1 } as React.CSSProperties}
                                >
                                  <i />
                                </span>
                                <span
                                  className="ui-term__count"
                                  data-term-count=""
                                >
                                  4 of 4 gates
                                </span>
                              </div>
                              <div
                                className="ui-term__ln ui-term__log"
                                data-term-out=""
                                data-term-step=""
                              >
                                <svg
                                  className="ui-term__tick"
                                  viewBox="0 0 16 16"
                                  aria-hidden="true"
                                >
                                  <path d="m3.5 8.4 2.8 2.8 6.2-6.4" />
                                </svg>
                                <span className="ui-term__path">
                                  precision_at_k
                                </span>
                                <span className="ui-term__n">100.0%</span>
                                <span className="ui-term__t">PASS</span>
                              </div>
                              <div
                                className="ui-term__ln ui-term__log"
                                data-term-out=""
                                data-term-step=""
                              >
                                <svg
                                  className="ui-term__tick"
                                  viewBox="0 0 16 16"
                                  aria-hidden="true"
                                >
                                  <path d="m3.5 8.4 2.8 2.8 6.2-6.4" />
                                </svg>
                                <span className="ui-term__path">
                                  mrr_lift_vs_dense
                                </span>
                                <span className="ui-term__n">+32.59%</span>
                                <span className="ui-term__t">PASS</span>
                              </div>
                              <div
                                className="ui-term__ln ui-term__log"
                                data-term-out=""
                                data-term-step=""
                              >
                                <svg
                                  className="ui-term__tick"
                                  viewBox="0 0 16 16"
                                  aria-hidden="true"
                                >
                                  <path d="m3.5 8.4 2.8 2.8 6.2-6.4" />
                                </svg>
                                <span className="ui-term__path">
                                  rbac_leakage_rate
                                </span>
                                <span className="ui-term__n">0.0000</span>
                                <span className="ui-term__t">PASS</span>
                              </div>
                              <div
                                className="ui-term__ln ui-term__done"
                                data-term-out=""
                                data-term-done=""
                              >
                                <span className="ui-term__ok">
                                  <svg viewBox="0 0 16 16" aria-hidden="true">
                                    <path d="m4.5 8.3 2.4 2.4 4.6-5" />
                                  </svg>
                                </span>
                                <b>All gates passed</b>
                                <span className="ui-term__dim">42 cases</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              </div>
            </div>

            <div className="grid">
              <article className="card card--row card--open span-6">
                <h3>Bastion hybrid pgvector and BM25 search</h3>
                <p>
                  Parallel pgvector HNSW and dual-dictionary BM25 lanes preserve
                  error codes and tables.
                </p>
                <div
                  className="panel"
                  data-fx="grain-gradient"
                  data-fx-seed="58"
                  data-fx-palette='{"bg":"#cdd6c6","surface":"#dce3d6","ink":"#262d24","accent":"#6c8e63"}'
                  data-fx-params='{"speed":0,"drift":0,"grainMotion":0}'
                  role="img"
                  aria-label="Bastion hybrid RRF search matching ERR_409_CONFLICT lock across dense vector and BM25 indexes"
                >
                  <div className="stage stage--fade-b">
                    <div
                      className="at-rise fit"
                      style={
                        {
                          "--fit-max": "380px",
                          "--ax": "max(24px, 50% - 190px)",
                          "--ay": "28px",
                          "--ay-sm": "14px",
                        } as React.CSSProperties
                      }
                    >
                      <div className="ui ui-panel ui-search" data-ui="search">
                        <div className="ui-search__field">
                          <svg
                            className="ui-icon"
                            viewBox="0 0 16 16"
                            aria-hidden="true"
                          >
                            <circle cx="7" cy="7" r="4.5" />
                            <path d="m10.5 10.5 3 3" />
                          </svg>
                          <span className="ui-search__q">
                            <span data-search-q="">ERR_409_CONFLICT lock</span>
                            <i className="ui-search__caret" />
                          </span>
                          <kbd className="ui-search__kbd">RRF</kbd>
                        </div>
                        <div className="ui-search__group">
                          Hybrid RRF top matches
                        </div>
                        <ul className="ui-search__list" data-search-list="">
                          <li className="ui-search__row is-sel">
                            <span className="ui-search__ico">
                              <svg className="ui-icon" viewBox="0 0 16 16">
                                <path d="M4 2.5h5l3 3v8H4z" />
                                <path d="M9 2.5v3h3" />
                              </svg>
                            </span>
                            <span className="ui-search__t">
                              <b>ERR_409_CONFLICT</b> storage <b>lock</b>
                            </span>
                            <span className="ui-search__m">0.996</span>
                          </li>
                          <li className="ui-search__row">
                            <span className="ui-search__ico">
                              <svg className="ui-icon" viewBox="0 0 16 16">
                                <path d="M4 2.5h5l3 3v8H4z" />
                                <path d="M9 2.5v3h3" />
                              </svg>
                            </span>
                            <span className="ui-search__t">
                              SKU-9921-A lease <b>lock</b> limit
                            </span>
                            <span className="ui-search__m">0.989</span>
                          </li>
                          <li className="ui-search__row">
                            <span className="ui-search__ico">
                              <svg className="ui-icon" viewBox="0 0 16 16">
                                <path d="M2.5 4.5h11v8h-11z" />
                                <path d="m2.5 5 5.5 4 5.5-4" />
                              </svg>
                            </span>
                            <span className="ui-search__t">
                              mTLS <b>ERR_401</b> token rotation
                            </span>
                            <span className="ui-search__m">0.941</span>
                          </li>
                        </ul>
                        <div className="ui-search__foot">
                          <span>Dense #1 + BM25 #4</span>
                          <span>k=60 RRF</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </article>

              <article className="card card--row card--open span-6">
                <h3>Bastion local Ollama and cloud LLMs</h3>
                <p>
                  Switch between offline mode, local Ollama, OpenAI, Gemini or
                  Anthropic from one file.
                </p>
                <div className="panel panel--dg">
                  <div
                    className="dg"
                    data-dg-still=""
                    data-icon-base="/assets/icons"
                    data-diagram={STACK_HUB_SPEC}
                  />
                </div>
              </article>
            </div>
          </div>
        </section>

        {/* Screens 5-6: Dealt moment pinned-chapters (2 screens live) */}
        <section
          className="section"
          id="walkthrough"
          data-moment="pinned-chapters"
          aria-labelledby="walkthrough-h"
        >
          <div className="wrap mo-pc__grid">
            <div className="mo-pc__text">
              <h2 id="walkthrough-h">Bastion live workspace walkthrough</h2>
              <ol className="mo-pc__steps">
                <li className="mo-pc__step">
                  <h3>1. Switch RBAC role JWT</h3>
                  <p>
                    Pick Public, Support Tier 1 or Executive in the top command
                    bar to mint a signed role scope_hash in real time.
                  </p>
                  <figure className="mo-pc__visual">
                    <img
                      src="/assets/chapter-scope.png"
                      alt="Bastion workspace empty state with tenant and role switchers in the top command bar"
                    />
                  </figure>
                </li>
                <li className="mo-pc__step">
                  <h3>2. Inspect inline chunk citations</h3>
                  <p>
                    Click any citation badge to read the chunk ACL, Cross-Encoder
                    score, Dense rank, BM25 rank and RRF score.
                  </p>
                  <figure className="mo-pc__visual">
                    <img
                      src="/assets/chapter-citation.png"
                      alt="Bastion citation popover showing Storage Troubleshooting Guide, allowed roles, 99.6 percent score, and RRF rank"
                    />
                  </figure>
                </li>
                <li className="mo-pc__step">
                  <h3>3. Block answers below 0.65</h3>
                  <p>
                    Out-of-domain or restricted queries stop at step four with
                    zero generation tokens spent and a refusal notice.
                  </p>
                  <figure className="mo-pc__visual">
                    <img
                      src="/assets/chapter-refusal.png"
                      alt="Bastion deterministic refusal banner showing 0.0008 below 0.65 threshold and LLM Called FALSE"
                    />
                  </figure>
                </li>
              </ol>
            </div>
            <div className="mo-pc__visuals frame" />
          </div>
        </section>

        {/* Screen 7: Benchmarks comparison */}
        <section
          className="section"
          id="benchmarks"
          aria-labelledby="benchmarks-h"
        >
          <div className="wrap grid">
            <div className="span-5 stack-4">
              <h2 id="benchmarks-h">Bastion benchmark results (28 probes)</h2>
              <p>
                Recorded in latest_benchmark.json across 28 retrieval probes and
                14 adversarial refusal traps against live PostgreSQL.
              </p>
              <ul className="rows rows--spec">
                <li>
                  <span className="rows__name">
                    Retrieval precision (28 probes)
                  </span>
                  <span className="rows__value">100.0%</span>
                </li>
                <li>
                  <span className="rows__name">Mean reciprocal rank (MRR)</span>
                  <span className="rows__value">1.0000</span>
                </li>
                <li>
                  <span className="rows__name">
                    MRR lift vs. dense baseline
                  </span>
                  <span className="rows__value">+32.59%</span>
                </li>
                <li>
                  <span className="rows__name">Ungrounded trap answers</span>
                  <span className="rows__value">0.0%</span>
                </li>
                <li>
                  <span className="rows__name">Role boundary RBAC leaks</span>
                  <span className="rows__value">0.0000</span>
                </li>
              </ul>
            </div>

            <div
              className="panel bench-panel span-6 start-7"
              data-fx="gradient-mesh"
              data-fx-seed="19"
              data-fx-palette='{"bg":"#c6d3df","surface":"#d6e0e9","ink":"#25303a","accent":"#3f6a92"}'
              data-fx-params='{"speed":0,"calm":0.2,"calmX":0.5,"calmY":0.9,"tint":0.6,"relief":0.35}'
              role="img"
              aria-label="Bastion retrieval precision bar chart showing 100 percent accuracy across 28 probes, up 18.6 points over the 81.4 percent dense baseline"
            >
              <div className="stage stage--fade-b">
                <div
                  className="at-corner to-edge fit"
                  style={
                    {
                      "--ax": "32px",
                      "--ay": "36px",
                      "--ay-sm": "16px",
                      "--fit-max": "480px",
                    } as React.CSSProperties
                  }
                >
                  <div
                    className="ui ui-panel ui-stat"
                    data-ui="stat"
                    data-from="81"
                    data-to="100"
                    data-suffix="%"
                  >
                    <div className="ui-stat__head">
                      <div className="ui-stat__top">
                        <span className="ui-stat__label">
                          Hybrid RRF precision@k
                        </span>
                        <span className="ui-stat__range">
                          28 probes
                          <svg
                            className="ui-icon"
                            viewBox="0 0 16 16"
                            aria-hidden="true"
                          >
                            <path d="m4.5 6.5 3.5 3.5 3.5-3.5" />
                          </svg>
                        </span>
                      </div>
                      <div className="ui-stat__line">
                        <span className="ui-stat__num" data-stat-num="">
                          100%
                        </span>
                        <span className="ui-chip ui-chip--plain ui-stat__delta">
                          <svg viewBox="0 0 12 12" aria-hidden="true">
                            <path
                              d="M6 9.5v-7M3 5.5l3-3 3 3"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                          18.6 pts
                        </span>
                        <span className="ui-stat__sub">
                          vs. 81.4% dense baseline
                        </span>
                      </div>
                    </div>
                    <div className="ui-stat__chart">
                      <svg
                        className="ui-stat__svg"
                        viewBox="0 0 400 120"
                        preserveAspectRatio="none"
                        aria-hidden="true"
                      >
                        <path
                          className="ui-stat__grid"
                          d="M0 30.5H400M0 60.5H400M0 90.5H400"
                        />
                        <path
                          className="ui-stat__cover"
                          fillRule="evenodd"
                          d=""
                        />
                        <g className="ui-stat__bars">
                          <rect
                            rx="3"
                            x="0.00"
                            y="49.04"
                            width="21.14"
                            height="70.96"
                          />
                          <rect
                            rx="3"
                            x="29.14"
                            y="40.86"
                            width="21.14"
                            height="79.14"
                          />
                          <rect
                            rx="3"
                            x="58.29"
                            y="44.95"
                            width="21.14"
                            height="75.05"
                          />
                          <rect
                            rx="3"
                            x="87.43"
                            y="36.76"
                            width="21.14"
                            height="83.24"
                          />
                          <rect
                            rx="3"
                            x="116.57"
                            y="42.22"
                            width="21.14"
                            height="77.78"
                          />
                          <rect
                            rx="3"
                            x="145.71"
                            y="34.04"
                            width="21.14"
                            height="85.96"
                          />
                          <rect
                            rx="3"
                            x="174.86"
                            y="38.13"
                            width="21.14"
                            height="81.87"
                          />
                          <rect
                            rx="3"
                            x="204.00"
                            y="29.94"
                            width="21.14"
                            height="90.06"
                          />
                          <rect
                            rx="3"
                            x="233.14"
                            y="35.40"
                            width="21.14"
                            height="84.60"
                          />
                          <rect
                            rx="3"
                            x="262.29"
                            y="25.85"
                            width="21.14"
                            height="94.15"
                          />
                          <rect
                            rx="3"
                            x="291.43"
                            y="31.31"
                            width="21.14"
                            height="88.69"
                          />
                          <rect
                            rx="3"
                            x="320.57"
                            y="23.12"
                            width="21.14"
                            height="96.88"
                          />
                          <rect
                            rx="3"
                            x="349.71"
                            y="27.21"
                            width="21.14"
                            height="92.79"
                          />
                          <rect
                            rx="3"
                            x="378.86"
                            y="16.30"
                            width="21.14"
                            height="103.70"
                          />
                        </g>
                      </svg>
                      <div className="ui-stat__axis" aria-hidden="true">
                        <span>Dense</span>
                        <span>BM25</span>
                        <span>Hybrid RRF</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Screen 8: FAQ with real stack visual */}
        <section
          className="section"
          id="questions"
          aria-labelledby="questions-h"
        >
          <div className="wrap grid">
            <div className="span-5 stack-4">
              <h2 id="questions-h">Bastion questions</h2>
              <p>
                Bastion indexes Markdown and plain-text runbooks today. Scanned
                PDFs and external SSO providers sit outside the core service.
              </p>
              <p>
                <a className="link" href="/workspace">
                  Try the workspace
                </a>
              </p>

              <div className="stack-icons" aria-label="Core stack">
                <div className="stack-icon-tile">
                  <img src="/assets/icons/postgres.svg" alt="" />
                  <span>Postgres</span>
                </div>
                <div className="stack-icon-tile">
                  <img src="/assets/icons/redis.svg" alt="" />
                  <span>Redis 8</span>
                </div>
                <div className="stack-icon-tile">
                  <img src="/assets/icons/fastapi.svg" alt="" />
                  <span>FastAPI</span>
                </div>
                <div className="stack-icon-tile">
                  <img src="/assets/icons/ollama.svg" alt="" />
                  <span>Ollama</span>
                </div>
              </div>
            </div>

            <div className="faq span-6 start-7">
              <div className="faq__item">
                <h3>Does Bastion require a cloud API key?</h3>
                <p>
                  No. Embeddings and reranking run locally on HuggingFace
                  models, and generation works offline or with local Ollama.
                </p>
              </div>
              <div className="faq__item">
                <h3>How does Bastion SQL RBAC prevent leaks?</h3>
                <p>
                  FastAPI verifies the JWT and passes tenant_id and
                  allowed_roles into PostgreSQL WHERE clauses before HNSW
                  ranking.
                </p>
              </div>
              <div className="faq__item">
                <h3>What happens when confidence drops below 0.65?</h3>
                <p>
                  The Cross-Encoder stops at step four, returns a structured
                  refusal notice, and spends zero generation tokens.
                </p>
              </div>
              <div className="faq__item">
                <h3>Can a Bastion cache hit leak across 3 roles?</h3>
                <p>
                  No. Redis partitions keys by tenant_id, canonical role
                  scope_hash, and entity tokens, clearing them on document
                  ingest.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Screen 9: footer.closing (close-type + footer-dark) */}
      <footer
        className="footer closing footer--dark ground-inverse"
        id="contact"
        aria-labelledby="close-h"
      >
        <div className="wrap">
          <div className="closing__cta close--type">
            <div className="section-head">
              <h2 id="close-h">Open the Bastion 6-step workspace</h2>
              <p className="t-small muted">
                Switch tenants, upload Markdown, and inspect every score in your
                browser.
              </p>
            </div>
            <a
              className="btn btn--primary btn--xl btn--wide"
              href="/workspace"
            >
              Open live workspace
              <svg className="m-arrow" viewBox="0 0 12 12" aria-hidden="true">
                <path className="m-arrow__stem" d="M1 6h8" />
                <path className="m-arrow__head" d="M4.5 2.5 8 6l-3.5 3.5" />
              </svg>
            </a>
          </div>

          <div className="closing__links">
            <div className="grid">
              <div className="span-4 stack-5">
                <a className="footer__mark" href="#top">
                  <span className="mark" data-mark="ring" aria-hidden="true" />
                  Bastion
                </a>
              </div>
              <div className="span-2 start-7 footer__col">
                <h3>Engine</h3>
                <ul>
                  <li>
                    <a href="#pipeline">Pipeline</a>
                  </li>
                  <li>
                    <a href="#engine">Guardrails</a>
                  </li>
                  <li>
                    <a href="#benchmarks">Benchmarks</a>
                  </li>
                </ul>
              </div>
              <div className="span-2 footer__col">
                <h3>Workspace</h3>
                <ul>
                  <li>
                    <a href="/workspace">Live chat</a>
                  </li>
                  <li>
                    <a href="#questions">Questions</a>
                  </li>
                </ul>
              </div>
              <div className="span-2 footer__col">
                <h3>Source</h3>
                <ul>
                  <li>
                    <a href="https://github.com/shatwiks/Bastion-hybrid-rag">
                      GitHub repo
                    </a>
                  </li>
                </ul>
              </div>
            </div>

            <div className="footer__legal">
              <span>&copy; 2026 Bastion Hybrid RAG</span>
              <span>
                Product names and logos are trademarks of their owners
              </span>
            </div>
          </div>
        </div>
      </footer>

      <LandingScripts />
    </>
  );
}
