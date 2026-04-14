import json
p = json.load(open('data/_inspect_post.json', encoding='utf-8-sig'))

print('=== SEO FIELDS ===')
print('title:', repr(p.get('title','MISSING')))
print('meta_description:', repr(p.get('meta_description','MISSING')))
print('seo_keywords:', p.get('seo_keywords',[]))
print('topic_slug:', p.get('topic_slug'))

print('\n=== FAQ ITEMS ===')
for f in p.get('faq_items',[])[:4]:
    print(' Q:', f.get('question','')[:90])

print('\n=== CITATIONS ===')
for c in p.get('citations',[]):
    yr = c.get('year', '?')
    title = c.get('title', '')[:70]
    print(f'  [{yr}] {title}')

print('\n=== KEY TAKEAWAYS ===')
for t in p.get('key_takeaways',[]):
    print(' -', t[:90])

print('\n=== BODY PREVIEW ===')
print(p.get('body','')[:600])

print('\n=== ALL KEYS ===', list(p.keys()))
print('word_count:', p.get('word_count'))
