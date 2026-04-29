import type { DataInsight } from "@/lib/wihyData";

interface DataInsightCardProps {
  insight: DataInsight;
}

export function DataInsightCard({ insight }: DataInsightCardProps) {
  return (
    <article className="rounded-xl border border-sky-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{insight.label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-900">{insight.value}</p>
      <p className="mt-2 text-sm text-slate-600">{insight.note}</p>
    </article>
  );
}
