import Link from "next/link";

import { AdSlot } from "@/components/AdSlot";
import { getArticleHeroImage } from "@/lib/article-images";
import { getAllArticles } from "@/lib/articles";
import { getExternalFeedArticles } from "@/lib/externalFeeds";

interface MixedFeedItem {
  id: string;
  title: string;
  summary: string;
  href: string;
  source: string;
  publishedAt?: string;
  imageUrl?: string;
  category?: string;
  author?: string;
  isInternal: boolean;
  readingTime?: number;
}

function dateLabel(value?: string): string {
  if (!value) return "Recent";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "Recent";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function prettyCategory(value?: string): string | undefined {
  if (!value) return undefined;
  const first = value.split(",")[0]?.trim() || value;
  const clean = first.replace(/-/g, " ");
  return clean.length > 36 ? `${clean.slice(0, 33)}...` : clean;
}

function isWithinLastWeek(value?: string): boolean {
  if (!value) return false;
  const publishedAt = new Date(value);
  if (Number.isNaN(publishedAt.getTime())) return false;

  const now = Date.now();
  const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
  return now - publishedAt.getTime() <= sevenDaysMs;
}

function diversifyBySource(items: MixedFeedItem[], maxRun = 3): MixedFeedItem[] {
  const remaining = [...items];
  const arranged: MixedFeedItem[] = [];
  let lastSource = "";
  let run = 0;

  while (remaining.length) {
    let pickIndex = 0;
    if (run >= maxRun) {
      const nextDifferent = remaining.findIndex((item) => item.source !== lastSource);
      if (nextDifferent >= 0) pickIndex = nextDifferent;
    }

    const [picked] = remaining.splice(pickIndex, 1);
    arranged.push(picked);

    if (picked.source === lastSource) {
      run += 1;
    } else {
      lastSource = picked.source;
      run = 1;
    }
  }

  return arranged;
}

export async function MixedContentFeed() {
  const internal = getAllArticles()
    .slice(0, 4)
    .map((article) => {
      const hero = getArticleHeroImage(article);
      return {
        id: `vowels-${article.slug}`,
        title: article.title,
        summary: article.description,
        href: `/article/${article.slug}`,
        source: "Vowels",
        publishedAt: article.publishedAt,
        imageUrl: hero.thumb,
        category: article.category,
        author: article.author,
        isInternal: true,
        readingTime: article.readingTime,
      } satisfies MixedFeedItem;
    })
    .filter((item) => isWithinLastWeek(item.publishedAt));

  const external = (await getExternalFeedArticles(180)).map((article) => ({
    id: `ext-${article.id}`,
    title: article.title,
    summary: article.summary || "",
    href: article.link,
    source: article.source,
    publishedAt: article.publishedAt,
    imageUrl: article.imageUrl,
    category: article.category,
    author: article.author,
    isInternal: false,
  }))
    .filter((item) => isWithinLastWeek(item.publishedAt)) satisfies MixedFeedItem[];

  const mixed = diversifyBySource(
    [...internal, ...external].sort((a, b) => +new Date(b.publishedAt || 0) - +new Date(a.publishedAt || 0)),
    6,
  ).slice(0, 120);

  const feedNodes = mixed.flatMap((item, idx) => {
    const nodes = [
      <li
        key={item.id}
        className=""
      >
        <article
          className="flex flex-col rounded-2xl border border-black/10 bg-white p-4 transition hover:border-brand/30"
        >
          {item.imageUrl ? (
            item.isInternal ? (
              <Link href={item.href} className="mb-3 block overflow-hidden rounded-xl">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  loading="lazy"
                  className="h-48 w-full object-cover sm:h-52"
                />
              </Link>
            ) : (
              <a href={item.href} target="_blank" rel="noopener noreferrer" className="mb-3 block overflow-hidden rounded-xl">
                <img src={item.imageUrl} alt={item.title} loading="lazy" className="h-48 w-full object-cover sm:h-52" />
              </a>
            )
          ) : null}

          <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
            <span>{item.source}</span>
            <span>•</span>
            <span>{dateLabel(item.publishedAt)}</span>
            {item.category ? (
              <>
                <span>•</span>
                <span>{prettyCategory(item.category)}</span>
              </>
            ) : null}
            {item.isInternal ? (
              <>
                <span>•</span>
                <span className="text-brand">original</span>
              </>
            ) : null}
          </div>

          <h3 className="mt-2 line-clamp-3 font-serif text-2xl leading-tight text-slate-950">
            {item.isInternal ? (
              <Link href={item.href} className="hover:text-brand">
                {item.title}
              </Link>
            ) : (
              <a href={item.href} target="_blank" rel="noopener noreferrer" className="hover:text-brand">
                {item.title}
              </a>
            )}
          </h3>

          {item.summary ? (
            <p className="mt-2 line-clamp-4 text-sm leading-6 text-slate-700">
              {item.summary}
            </p>
          ) : null}

          <div className="mt-auto pt-3 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            {item.author ? `By ${item.author}` : item.isInternal && item.readingTime ? `${item.readingTime} min read` : "Read"}
          </div>
        </article>
      </li>,
    ];

    if (idx === 1) {
      nodes.push(
        <li key="ad-top-billboard" className="md:col-span-2 xl:col-span-3">
          <AdSlot slotName="Homepage Leaderboard" size="leaderboard" className="w-full" />
        </li>,
      );
    }

    if ((idx + 1) % 4 === 0) {
      nodes.push(
        <li key={`ad-inline-${idx}`} className="md:col-span-2 xl:col-span-3">
          <AdSlot slotName="Research Results Inline Ad" size="infeed" className="w-full" />
        </li>,
      );
    }

    if ((idx + 1) % 10 === 0) {
      nodes.push(
        <li key={`ad-rect-${idx}`} className="md:col-span-2 xl:col-span-1">
          <AdSlot slotName="Content Partner Rectangle" size="rectangle" className="w-full" />
        </li>,
      );
    }

    return nodes;
  });

  return (
    mixed.length ? (
      <ul className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
        {feedNodes}
      </ul>
    ) : (
      <section className="rounded-2xl bg-white p-6 text-sm text-slate-700">
        No stories from the last 7 days are available right now.
      </section>
    )
  );
}
