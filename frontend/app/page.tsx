export default function Home() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col gap-4 p-8">
      <h1 className="text-3xl font-semibold">BlendGuard</h1>
      <p className="text-base opacity-70">
        Build a diversified ETF portfolio from your goals, beliefs, and risk
        limits.
      </p>
      <p className="text-sm opacity-50">
        Skeleton only. Backend: <code>POST /api/optimize</code>.
      </p>
    </main>
  );
}
