const BASE = "https://images.unsplash.com";

function u(id: string, w: number, h: number): string {
  return `${BASE}/${id}?w=${w}&h=${h}&q=80&auto=format&fit=crop`;
}

// Curated pools of Unsplash photo IDs per category
const CATEGORY_POOLS: Record<string, string[]> = {
  "nutrition-education": [
    "photo-1490645935967-10de6ba17061", // colorful healthy bowls
    "photo-1512621776951-a57141f2eefd", // salad bowl overhead
    "photo-1498837167922-ddd27525d352", // food flat lay
  ],
  "health-explained": [
    "photo-1490474418585-ba9bad8fd0ea", // meal prep containers
    "photo-1540420773420-3366772f4999", // vegetables assortment
    "photo-1543362906-acfc16c67564",    // healthy food spread
  ],
  "food-systems": [
    "photo-1542838132-92c53300491e",    // farmer's market produce
    "photo-1488459716781-31db52582fe9", // food market stall
    "photo-1557843643-a1a56f5e5b9f",    // grocery shopping
  ],
  "research-explained": [
    "photo-1576086213369-97a306d36557", // science lab
    "photo-1532187863486-abf9dbad1b69", // research clipboard
    "photo-1551288049-bebda4e38f71",    // data analytics
  ],
  "from-the-data": [
    "photo-1551288049-bebda4e38f71",    // data analytics
    "photo-1543286386-523158b5ea4b",    // charts on screen
    "photo-1460925895917-afdab827c52f", // data visualization
  ],
  perspective: [
    "photo-1498837167922-ddd27525d352", // food flat lay
    "photo-1490645935967-10de6ba17061", // colorful bowls
    "photo-1504674900247-0877df9cc836", // food photography
  ],
  sponsored: [
    "photo-1504674900247-0877df9cc836", // food photography
    "photo-1565299624946-b28f40a0ae38", // overhead food
    "photo-1567620905732-2d1ec7ab7445", // food spread
  ],
};

// Tag-specific overrides (checked before category pool)
const TAG_IMAGES: Record<string, string> = {
  protein:           "photo-1482049016688-2d3e1b311543", // eggs & protein foods
  hydration:         "photo-1548839140-29a749e1cf4d",    // water glass
  water:             "photo-1548839140-29a749e1cf4d",
  family:            "photo-1547592180-85f173990554",    // family meal
  kids:              "photo-1547592180-85f173990554",
  children:          "photo-1547592180-85f173990554",
  budget:            "photo-1559181567-c3190b325437",    // groceries
  grocery:           "photo-1559181567-c3190b325437",
  fiber:             "photo-1540420773420-3366772f4999", // vegetables
  vegetables:        "photo-1540420773420-3366772f4999",
  "meal prep":       "photo-1490474418585-ba9bad8fd0ea",
  calories:          "photo-1490323914169-4b1abb4a6d37", // fruit & scale
  breakfast:         "photo-1525351484163-7529414344d8", // breakfast spread
  sodium:            "photo-1565958011703-44f9829ba187", // salt shaker
  salt:              "photo-1565958011703-44f9829ba187",
  "weight management":"photo-1517836357463-d25dfeac3438",// tape measure
  "weight loss":     "photo-1517836357463-d25dfeac3438",
  snacks:            "photo-1601004890684-d8cbf643f5f2", // healthy snacks
  lunch:             "photo-1546069901-ba9599a7e63c",    // lunch box
  dinner:            "photo-1555939594-58d7cb561cf",    // dinner plate
  mediterranean:     "photo-1544025162-d76538a8a101",   // mediterranean spread
  sodium_blood:      "photo-1551029506-0807df851541",
};

const DEFAULT_POOL = CATEGORY_POOLS["nutrition-education"];

export interface ArticleHeroImage {
  src: string;
  thumb: string;
  credit: string;
}

export function getArticleHeroImage(article: {
  slug: string;
  category: string;
  tags: string[];
  image?: string;
}): ArticleHeroImage {
  if (article.image) {
    return { src: article.image, thumb: article.image, credit: "" };
  }

  // Check tags for specific overrides (case-insensitive)
  for (const tag of article.tags) {
    const id = TAG_IMAGES[tag.toLowerCase()];
    if (id) {
      return {
        src: u(id, 1200, 630),
        thumb: u(id, 600, 340),
        credit: "Unsplash",
      };
    }
  }

  // Fall back to category pool, deterministic selection by slug char sum
  const pool = CATEGORY_POOLS[article.category] ?? DEFAULT_POOL;
  const idx = [...article.slug].reduce((acc, c) => acc + c.charCodeAt(0), 0) % pool.length;
  const id = pool[idx];

  return {
    src: u(id, 1200, 630),
    thumb: u(id, 600, 340),
    credit: "Unsplash",
  };
}
