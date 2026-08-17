export default function SystemHealthLoading() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-6 sm:px-6 lg:px-8">
      <div aria-label="Loading system health" className="mx-auto max-w-6xl" role="status">
        <div className="h-28 animate-pulse rounded-xl bg-slate-200 motion-reduce:animate-none" />
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {["release", "gold", "graph"].map((item) => (
            <div className="h-48 animate-pulse rounded-xl bg-slate-200 motion-reduce:animate-none" key={item} />
          ))}
        </div>
        <span className="sr-only">Loading verified release and provider health.</span>
      </div>
    </main>
  );
}
