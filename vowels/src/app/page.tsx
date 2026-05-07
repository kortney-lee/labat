import { AdSlot } from "@/components/AdSlot";
import { AiModeResults } from "@/components/AiModeResults";
import { MixedContentFeed } from "@/components/MixedContentFeed";
import { ResearchResults } from "@/components/ResearchResults";
import { SearchHero } from "@/components/SearchHero";

export const dynamic = "force-static";

interface HomePageProps {
  searchParams?: {
    q?: string;
  };
}

export default function HomePage({ searchParams }: HomePageProps) {
  const query = searchParams?.q?.trim() || "";

  return (
    <div className="space-y-6 pb-24 md:pb-8">
      <SearchHero initialQuery={query} />

      <AdSlot slotName="Search Top Leaderboard" size="leaderboard" className="w-full" />

      <div id="results">
        <AiModeResults initialQuery={query || undefined} />
      </div>

      <div>
        <ResearchResults initialQuery={query || undefined} />
      </div>

      <AdSlot slotName="Research Results Inline Ad" size="infeed" className="w-full" />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start">
        <div className="space-y-6">
          <AdSlot slotName="Search Mid Rectangle" size="largerect" className="w-full" />

          <MixedContentFeed />

          <AdSlot slotName="Homepage Leaderboard" size="leaderboard" className="w-full" />
        </div>

        <aside className="hidden xl:block">
          <div className="sticky top-24 space-y-4">
            <AdSlot slotName="Sidebar Rectangle" size="rectangle" />
            <AdSlot slotName="Sidebar Half Page" size="halfpage" />
            <AdSlot slotName="Content Partner Rectangle" size="rectangle" />
          </div>
        </aside>
      </div>

      {/* Mobile anchor banner — fixed bottom, hides on md+ where sidebar handles monetization */}
      <div className="fixed bottom-0 left-0 right-0 z-30 md:hidden">
        <AdSlot slotName="Mobile Anchor Banner" size="mobilebanner" className="rounded-none border-t border-black/10" />
      </div>
    </div>
  );
}
