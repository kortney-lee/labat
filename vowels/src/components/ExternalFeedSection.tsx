import { AdSlot } from "@/components/AdSlot";
import { getExternalFeedArticles } from "@/lib/externalFeeds";

interface ExternalArticle {
  id: string;
  title: string;
  link: string;
  source: string;
  publishedAt?: string;
  summary?: string;
  imageUrl?: string;
  author?: string;
  category?: string;
}

function dateLabel(value?: string): string {
  if (!value) return "Recent";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "Recent";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export async function ExternalFeedSection() {
  const articles = (await getExternalFeedArticles(180)) as ExternalArticle[];
  const featured = articles.slice(0, 12);
  const more = articles.slice(12, 84);

  return (
    <section className="news-card p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Around The Web</p>
          <h3 className="mt-2 font-serif text-3xl text-slate-950">External Health + Nutrition Feed</h3>
        </div>
        <span className="rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
          {`${articles.length} stories`}
        </span>
      </div>

      {articles.length ? (
        <div className="mt-5 space-y-5">
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {featured.map((article, idx) => (
              <li key={article.id} className="space-y-3">
                <article className="flex h-full flex-col rounded-2xl border border-black/10 bg-white p-4 transition hover:border-brand/30">
                  {article.imageUrl ? (
                    <a href={article.link} target="_blank" rel="noopener noreferrer" className="mb-3 block overflow-hidden rounded-xl">
                      <img src={article.imageUrl} alt={article.title} loading="lazy" className="h-52 w-full object-cover" />
                    </a>
                  ) : null}

                  <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                    <span>{article.source}</span>
                    <span>•</span>
                    <span>{dateLabel(article.publishedAt)}</span>
                    {article.category ? (
                      <>
                        <span>•</span>
                        <span>{article.category}</span>
                      </>
                    ) : null}
                  </div>

                  <h4 className="mt-2 line-clamp-3 font-serif text-2xl leading-tight text-slate-950">
                    <a href={article.link} target="_blank" rel="noopener noreferrer" className="hover:text-brand">
                      {article.title}
                    </a>
                  </h4>

                  {article.summary ? <p className="mt-2 line-clamp-4 text-sm leading-6 text-slate-700">{article.summary}</p> : null}
                  {article.author ? <p className="mt-auto pt-3 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">By {article.author}</p> : null}
                </article>

                {(idx + 1) % 6 === 0 ? <AdSlot slotName="Research Results Inline Ad" size="infeed" className="w-full" /> : null}
              </li>
            ))}
          </ul>

          {more.length ? (
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {more.map((article, idx) => (
                <li key={article.id} className="space-y-3">
                  <article className="flex h-full flex-col rounded-2xl border border-black/10 bg-white p-3 transition hover:border-brand/30">
                    <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
                      <span>{article.source}</span>
                      <span>•</span>
                      <span>{dateLabel(article.publishedAt)}</span>
                    </div>

                    <h4 className="mt-2 line-clamp-3 font-serif text-xl leading-tight text-slate-950">
                      <a href={article.link} target="_blank" rel="noopener noreferrer" className="hover:text-brand">
                        {article.title}
                      </a>
                    </h4>

                    {article.summary ? <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-700">{article.summary}</p> : null}
                  </article>

                  {(idx + 1) % 12 === 0 ? <AdSlot slotName="Research Results Inline Ad" size="infeed" className="w-full" /> : null}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-black/10 bg-white p-5 text-sm text-slate-600">
          No external feeds available right now. Try again shortly.
        </div>
      )}
    </section>
  );
}