/**
 * Animated, abstract neural-network background for the landing hero.
 * Pure SVG, lightweight, decorative.
 */
export function NeuralBackground() {
  const nodes = Array.from({ length: 28 }, (_, i) => ({
    id: i,
    x: (i % 7) * 16 + 4 + (i % 2 ? 2 : -2),
    y: Math.floor(i / 7) * 22 + 8,
    delay: (i % 5) * 0.6,
  }));
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Glow blobs */}
      <div className="absolute -top-40 -left-20 h-96 w-96 rounded-full bg-teal/30 blur-3xl animate-float-slow" />
      <div className="absolute top-20 -right-32 h-[28rem] w-[28rem] rounded-full bg-lavender/30 blur-3xl animate-float-slow" style={{ animationDelay: "2s" }} />
      <div className="absolute bottom-[-10rem] left-1/3 h-[26rem] w-[26rem] rounded-full bg-primary/30 blur-3xl animate-float-slow" style={{ animationDelay: "4s" }} />

      {/* Network grid */}
      <svg
        viewBox="0 0 120 80"
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 w-full h-full opacity-40"
      >
        <defs>
          <linearGradient id="line" x1="0" x2="1">
            <stop offset="0" stopColor="oklch(0.78 0.10 215)" stopOpacity="0.0" />
            <stop offset="0.5" stopColor="oklch(0.78 0.10 215)" stopOpacity="0.7" />
            <stop offset="1" stopColor="oklch(0.78 0.10 215)" stopOpacity="0.0" />
          </linearGradient>
        </defs>
        {nodes.map((a) =>
          nodes
            .filter((b) => b.id > a.id)
            .map((b) => {
              const dx = a.x - b.x;
              const dy = a.y - b.y;
              const d = Math.hypot(dx, dy);
              if (d > 22) return null;
              return (
                <line
                  key={`${a.id}-${b.id}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="url(#line)"
                  strokeWidth="0.18"
                  className="animate-brain-wave"
                  style={{ animationDelay: `${a.delay}s` }}
                />
              );
            }),
        )}
        {nodes.map((n) => (
          <circle
            key={n.id}
            cx={n.x}
            cy={n.y}
            r="0.6"
            fill="oklch(0.85 0.10 200)"
            className="animate-pulse-soft"
            style={{ animationDelay: `${n.delay}s` }}
          />
        ))}
      </svg>

      {/* EEG wave at the bottom */}
      <svg
        viewBox="0 0 600 100"
        preserveAspectRatio="none"
        className="absolute bottom-0 left-0 w-full h-24 opacity-50"
      >
        <path
          d="M0 50 Q 30 10 60 50 T 120 50 T 180 50 T 240 50 T 300 50 T 360 50 T 420 50 T 480 50 T 540 50 T 600 50"
          fill="none"
          stroke="oklch(0.78 0.10 215)"
          strokeWidth="1"
          className="animate-brain-wave"
        />
        <path
          d="M0 60 Q 30 30 60 60 T 120 60 T 180 60 T 240 60 T 300 60 T 360 60 T 420 60 T 480 60 T 540 60 T 600 60"
          fill="none"
          stroke="oklch(0.78 0.07 295)"
          strokeWidth="0.6"
          className="animate-brain-wave"
          style={{ animationDelay: "1.5s" }}
        />
      </svg>
    </div>
  );
}
