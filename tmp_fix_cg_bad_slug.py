import json
from pathlib import Path
from google.cloud import storage
from src.labat.services.blog_writer import update_blog_index

BAD_BLOB = 'blog/posts//blog-low-risk-drinking-guidelines-explained.json'
GOOD_SLUG = 'low-risk-drinking-guidelines-explained'

# Delete malformed post blob if present.
client = storage.Client()
bucket = client.bucket('cg-web-assets')
bad = bucket.blob(BAD_BLOB)
if bad.exists():
    bad.delete()
    print('Deleted malformed blob:', BAD_BLOB)
else:
    print('No malformed blob found')

# Ensure corrected post exists.
good_blob = bucket.blob(f'blog/posts/{GOOD_SLUG}.json')
if not good_blob.exists():
    article = {
        'slug': GOOD_SLUG,
        'brand': 'communitygroceries',
        'title': 'Low Risk Drinking Guidelines Explained',
        'topic': 'Alcohol and Health',
        'topic_slug': 'alcohol-and-health',
        'body': '# Low Risk Drinking Guidelines Explained\n\nPractical guidance on alcohol, sleep, recovery, and long-term health tradeoffs.\n',
        'meta_description': 'A practical guide to low-risk drinking limits, recovery impact, and long-term health tradeoffs.',
        'seo_keywords': ['low risk drinking guidelines', 'alcohol and health', 'community groceries'],
        'citations': [],
        'author': 'Kortney',
        'created_at': '2026-04-08T21:35:31.546666+00:00',
        'word_count': 16,
    }
    good_blob.upload_from_string(json.dumps(article, indent=2), content_type='application/json')
    print('Created corrected post:', GOOD_SLUG)
else:
    print('Corrected post already exists:', GOOD_SLUG)

posts = update_blog_index('communitygroceries')
print('Index rebuilt. Count:', len(posts))
