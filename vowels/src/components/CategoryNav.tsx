import Link from "next/link";

const categories = [
  "nutrition-education",
  "health-explained",
  "food-systems",
  "research-explained",
  "from-the-data",
  "perspective",
  "sponsored",
] as const;

export function CategoryNav() {
  return (
    <nav className="flex flex-wrap items-center gap-2" aria-label="Category Navigation">
      {categories.map((slug) => (
        <Link
          key={slug}
          href={`/category/${slug}`}
          className="rounded-full border border-black/10 bg-white/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600 transition hover:border-brand/40 hover:text-brand"
        >
          {slug.replace(/-/g, " ")}
        </Link>
      ))}
    </nav>
  );
}
