import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from src.labat.services.blog_writer import publish_article, update_blog_index

TOPIC_FILE = Path('data/cg_topic_hubs_apr8_2026.json')


def slug_to_title(slug: str) -> str:
    return slug.replace('-', ' ').replace('/', ' ').strip().title()


def build_body(topic_name: str, topic_desc: str, article_title: str) -> str:
    return f"""# {article_title}

{topic_desc}

## Why This Matters

Families do better when nutrition guidance is practical, affordable, and easy to apply during busy weeks.
This guide focuses on simple choices that improve consistency over perfection.

## What To Do This Week

- Pick one small change you can repeat for 7 days.
- Build your grocery list around that change.
- Keep meals simple and balanced instead of chasing perfection.
- Track what felt easiest so you can keep it next week.

## Community Groceries Strategy

The goal is flexibility without subscription lock-in.
You can choose ingredients based on your budget, dietary goals, and your family routine.

## Cost and Practicality

Use low-friction meal structures: protein, produce, fiber-rich carbs, and healthy fats.
Batch-prep staples once, then mix and match through the week.

## Nutrition Notes

Use labels to reduce added sugar, improve protein quality, and avoid over-relying on ultra-processed options.
Small repeatable decisions compound over time.

## FAQ

### Do I need a perfect plan to make progress?
No. Consistency with simple habits beats complexity.

### How quickly should I change my routine?
One to two changes per week is usually the most sustainable approach.

### What should I prioritize first?
Prioritize meal structure, hydration, and realistic shopping habits.

## Takeaway

Build a system your household can actually maintain.
Community Groceries is designed to help you shop smarter and eat better with less friction.
"""


async def main() -> None:
    data = json.loads(TOPIC_FILE.read_text(encoding='utf-8'))
    topics = data.get('topics', [])

    published = []
    now = datetime.now(timezone.utc).isoformat()

    for topic in topics:
        topic_name = topic['name']
        topic_slug = topic['slug']
        topic_desc = topic['description']

        for path in topic.get('starter_articles', []):
            slug = path.split('/blog/', 1)[-1].strip()
            if not slug:
                continue

            title = slug_to_title(slug)
            body = build_body(topic_name, topic_desc, title)
            meta = (topic_desc[:148] + '...') if len(topic_desc) > 151 else topic_desc

            article = {
                'slug': slug,
                'brand': 'communitygroceries',
                'title': title,
                'topic': topic_name,
                'topic_slug': topic_slug,
                'body': body,
                'meta_description': meta,
                'seo_keywords': [
                    title.lower(),
                    topic_name.lower(),
                    'community groceries',
                    'healthy grocery delivery',
                ],
                'citations': [],
                'author': 'Kortney',
                'created_at': now,
                'word_count': len(body.split()),
            }

            urls = await publish_article(article, hero_bytes=None)
            published.append({'slug': slug, 'topic_slug': topic_slug, 'article_url': urls.get('article', '')})

    posts = update_blog_index('communitygroceries')

    out = {
        'generated_at': now,
        'published_count': len(published),
        'index_count': len(posts),
        'published': published,
    }
    Path('data/cg_topic_publish_result_apr8_2026.json').write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    print('Published:', len(published))
    print('Index count:', len(posts))
    print('Saved: data/cg_topic_publish_result_apr8_2026.json')


if __name__ == '__main__':
    asyncio.run(main())
