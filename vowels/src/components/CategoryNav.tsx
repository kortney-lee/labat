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
    <nav className="mt-5 flex flex-wrap gap-2" aria-label="Category Navigation">
      {categories.map((slug) => (
        <Link
          key={slug}
          href={`/category/${slug}`}
          className="rounded-full border border-sky-200 bg-white px-3 py-1.5 text-xs font-medium uppercase tracking-wide text-slate-700 hover:border-newsroom hover:text-newsroom"
        >
          {slug.replace(/-/g, " ")}
        </Link>
      ))}
    </nav>
  );
}
