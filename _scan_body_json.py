import urllib.request, json

url = 'https://storage.googleapis.com/cg-web-assets/blog/posts/index.json'
with urllib.request.urlopen(url) as r:
    index = json.load(r)
posts = index if isinstance(index, list) else index.get('posts', [])
affected = []
for p in posts:
    slug = p.get('slug','')
    post_url = f'https://storage.googleapis.com/cg-web-assets/blog/posts/{slug}.json'
    try:
        with urllib.request.urlopen(post_url) as r2:
            data = json.load(r2)
        body = data.get('body','') or data.get('body_markdown','')
        if ('"slug"' in body or '"journal"' in body) and '{' in body:
            # show the offending snippet
            idx = body.find('"slug"')
            if idx == -1:
                idx = body.find('"journal"')
            snippet = body[max(0,idx-30):idx+80].replace('\n',' ')
            affected.append((slug, snippet))
    except Exception as e:
        pass

print(f'Affected: {len(affected)} posts')
for slug, snippet in affected:
    print(f'  {slug}')
    print(f'    ...{snippet}...')
