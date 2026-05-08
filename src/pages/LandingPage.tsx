import { Link } from "@tanstack/react-router";
import { ArrowRight, Brain, ShieldCheck, Microscope, Sparkles, Activity, FileSearch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NeuralBackground } from "@/components/NeuralBackground";
import { AXES } from "@/lib/axes";
import { ThemeToggle } from "@/components/ThemeToggle";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Top nav */}
      <header className="sticky top-0 z-30 backdrop-blur bg-background/70 border-b">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-xl bg-gradient-hero shadow-glow grid place-items-center">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <div className="leading-tight">
              <div className="font-semibold tracking-tight">brAIn</div>
              <div className="text-[11px] text-muted-foreground">Decision support</div>
            </div>
          </Link>
          <nav className="ml-8 hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#how" className="hover:text-foreground transition">How it works</a>
            <a href="#axes" className="hover:text-foreground transition">7 Axes</a>
            <a href="#explain" className="hover:text-foreground transition">Explainability</a>
            <a href="#why" className="hover:text-foreground transition">Why it matters</a>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <Button asChild variant="ghost" size="sm">
              <Link to="/dashboard">Sign in</Link>
            </Button>
            <Button asChild size="sm" className="gap-1.5">
              <Link to="/dashboard">
                Open platform <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <NeuralBackground />
        <div className="relative max-w-7xl mx-auto px-6 pt-24 pb-32 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border bg-card/70 px-3 py-1 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-teal animate-pulse-soft" />
            AI-powered neurology decision support · v1.0 demo
          </div>
          <h1 className="mt-6 text-5xl md:text-7xl font-semibold tracking-tight text-balance">
            <span className="bg-gradient-to-br from-primary via-[oklch(0.45_0.10_230)] to-teal bg-clip-text text-transparent">
              brAIn
            </span>
          </h1>
          <p className="mt-4 text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto text-balance">
            Making hidden brain dynamics visible through AI.
          </p>
          <p className="mt-3 text-sm text-muted-foreground max-w-2xl mx-auto">
            A clinician-facing platform that surfaces interpretable patterns across 7 neurological axes —
            from MRI and fMRI to gait video and EEG.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg" className="gap-2">
              <Link to="/dashboard">
                Explore platform <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/axes">View 7 axes</Link>
            </Button>
            <Button asChild size="lg" variant="ghost">
              <Link to="/axes/alzheimer-dementia">Start an analysis</Link>
            </Button>
          </div>

          <div className="mt-14 inline-flex items-center gap-2 text-[11px] text-muted-foreground bg-lavender/15 border border-lavender/40 rounded-full px-3 py-1.5">
            <ShieldCheck className="h-3.5 w-3.5" />
            Decision-support tool — not a standalone diagnosis.
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="py-24 bg-gradient-soft">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto">
            <div className="text-xs uppercase tracking-wider text-bluegray">How it works</div>
            <h2 className="mt-2 text-3xl md:text-4xl font-semibold tracking-tight">
              From scan to interpretable insight in three steps.
            </h2>
          </div>
          <div className="mt-12 grid md:grid-cols-3 gap-6">
            {[
              { icon: Microscope, t: "1. Upload", d: "Drop in MRI, fMRI, video or EEG. Patient metadata stays optional and on your device." },
              { icon: Sparkles, t: "2. Analyze", d: "Axis-specific models run inference and generate prediction, confidence and explainability layers." },
              { icon: FileSearch, t: "3. Interpret", d: "Review heatmaps, region tables, signal markers — then export a decision-support report." },
            ].map((s, i) => (
              <div key={i} className="rounded-2xl border bg-gradient-card p-7 shadow-soft">
                <div className="h-11 w-11 rounded-xl bg-primary/10 grid place-items-center text-primary">
                  <s.icon className="h-5 w-5" />
                </div>
                <h3 className="mt-4 text-lg font-semibold">{s.t}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 7 Axes */}
      <section id="axes" className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto">
            <div className="text-xs uppercase tracking-wider text-bluegray">The 7 axes</div>
            <h2 className="mt-2 text-3xl md:text-4xl font-semibold tracking-tight">
              Coverage across the neurological spectrum.
            </h2>
            <p className="mt-3 text-muted-foreground">
              Each axis is a self-contained module — independent models, inputs and explainability outputs.
            </p>
          </div>
          <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {AXES.map((a) => (
              <Link
                key={a.id}
                to={`/axes/${a.slug}`}
                className="group rounded-2xl border bg-gradient-card p-6 shadow-soft hover:shadow-elegant hover:-translate-y-1 transition-all"
              >
                <div className="flex items-start justify-between">
                  <div className={`h-11 w-11 rounded-xl bg-gradient-to-br ${a.accent} text-white grid place-items-center`}>
                    <a.icon className="h-5 w-5" />
                  </div>
                  <span className="text-[11px] tabular-nums text-bluegray">A{String(a.number).padStart(2, "0")}</span>
                </div>
                <h3 className="mt-4 font-semibold tracking-tight">{a.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{a.purpose}</p>
                <div className="mt-4 text-xs text-primary inline-flex items-center gap-1">
                  Open axis <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Explainability */}
      <section id="explain" className="py-24 bg-gradient-soft">
        <div className="max-w-6xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="text-xs uppercase tracking-wider text-bluegray">Explainability-first AI</div>
            <h2 className="mt-2 text-3xl md:text-4xl font-semibold tracking-tight text-balance">
              Every prediction comes with a story.
            </h2>
            <p className="mt-4 text-muted-foreground leading-relaxed">
              We surface region heatmaps for MRI, network graphs for fMRI, timeline markers
              for video, and segment-level highlights for EEG. The clinician stays in the loop —
              the model never speaks alone.
            </p>
            <ul className="mt-6 space-y-2.5 text-sm">
              {[
                "AI-detected pattern, never a verdict",
                "Confidence distribution across alternatives",
                "Region- or signal-level contribution",
                "Exportable decision-support report",
              ].map((p) => (
                <li key={p} className="flex items-center gap-2.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-teal" /> {p}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border bg-card p-6 shadow-elegant">
            <div className="aspect-square rounded-xl bg-[oklch(0.12_0.02_255)] grid place-items-center overflow-hidden relative">
              <NeuralBackground />
              <Activity className="h-16 w-16 text-white relative z-10 opacity-90" />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-[11px]">
              <div className="rounded-md bg-accent/40 px-2 py-1.5 text-center">Heatmap</div>
              <div className="rounded-md bg-accent/40 px-2 py-1.5 text-center">Region table</div>
              <div className="rounded-md bg-accent/40 px-2 py-1.5 text-center">Disclaimer</div>
            </div>
          </div>
        </div>
      </section>

      {/* Why it matters */}
      <section id="why" className="py-24">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <div className="text-xs uppercase tracking-wider text-bluegray">Why it matters</div>
          <h2 className="mt-2 text-3xl md:text-4xl font-semibold tracking-tight text-balance">
            Subtle neurological patterns are hard to see — and easy to miss.
          </h2>
          <p className="mt-5 text-muted-foreground leading-relaxed">
            brAIn helps clinicians and researchers surface suggestive findings earlier,
            compare across modalities, and export reproducible decision-support reports.
            It complements clinical judgement — it does not replace it.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg">
              <Link to="/dashboard">Open the platform</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/axes">Browse the 7 axes</Link>
            </Button>
          </div>
        </div>
      </section>

      <footer className="border-t py-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-wrap items-center justify-between gap-4 text-xs text-muted-foreground">
          <div>© 2026 brAIn — Decision-support platform.</div>
          <div>Not a standalone diagnostic device. For research and clinical interpretation support only.</div>
        </div>
      </footer>
    </div>
  );
}
