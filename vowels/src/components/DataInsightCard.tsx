import type { DataInsight } from "@/lib/wihyData";

interface DataInsightCardProps {
  insight: DataInsight;
}

export function DataInsightCard({ insight }: DataInsightCardProps) {
  return (
    <article className="rounded-[1.25rem] border border-black/10 bg-gradient-to-b from-white to-mist p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{insight.label}</p>
      <p className="mt-3 font-serif text-4xl leading-none text-brand">{insight.value}</p>
      <p className="mt-3 text-sm text-slate-700">{insight.note}</p>
    </article>
  );
}
