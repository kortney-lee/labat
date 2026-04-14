import psycopg2

conn = psycopg2.connect(
    host='127.0.0.1', port=5433, user='postgres',
    password='Godiswilling1!', dbname='wihy_chat'
)
cur = conn.cursor()

# Unique user questions by frequency
cur.execute("""
SELECT COUNT(*) as cnt,
       regexp_replace(LEFT(content, 120), '[^\x20-\x7E]', '', 'g') as question
FROM chat_messages 
WHERE role = 'user' 
    AND content IS NOT NULL 
    AND LENGTH(content) BETWEEN 15 AND 300
    AND content NOT LIKE '%%test%%'
    AND content NOT LIKE '%%Test%%'
    AND content NOT LIKE '%%@%%'
    AND content NOT LIKE '%%Complete your%%'
    AND content NOT LIKE '%%View meal%%'
    AND content NOT LIKE '%%Thanks%%'
    AND content NOT LIKE '%%Hello%%'
    AND content NOT LIKE '%%SEO%%'
    AND content NOT LIKE '%%seo%%'
    AND content NOT LIKE '%%ALEX%%'
    AND content NOT LIKE '%%alex%%'
    AND content NOT LIKE '%%Build%%'
    AND content NOT LIKE '%%build%%'
GROUP BY regexp_replace(LEFT(content, 120), '[^\x20-\x7E]', '', 'g')
ORDER BY cnt DESC
LIMIT 80
""")

print("="*90)
print("WHAT REAL USERS ASK WIHY (unique questions, ranked by frequency)")
print("="*90)
print(f"{'#':>4}  Question")
print("-"*90)
for cnt, q in cur.fetchall():
    print(f"{cnt:>4}x {q}")

# Intent distribution
print("\n" + "="*90)
print("INTENT DISTRIBUTION (what topics people ask about)")
print("="*90)
cur.execute("""
SELECT COALESCE(intent, 'unknown') as intent, 
       COUNT(*) as cnt,
       COALESCE(service_used, '?') as service
FROM chat_messages 
WHERE role = 'user' AND content IS NOT NULL AND LENGTH(content) > 10
GROUP BY intent, service_used
ORDER BY cnt DESC
LIMIT 30
""")
print(f"{'Count':>6}  {'Intent':<25} Service")
print("-"*70)
for intent, cnt, svc in cur.fetchall():
    print(f"{cnt:>6}  {intent:<25} {svc}")

# Total stats
cur.execute("SELECT COUNT(*) FROM chat_messages WHERE role='user' AND content IS NOT NULL")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT session_id) FROM chat_messages")
sessions = cur.fetchone()[0]
cur.execute("SELECT MIN(created_at)::date, MAX(created_at)::date FROM chat_messages")
first, last = cur.fetchone()
print(f"\nTotal user messages: {total}")
print(f"Total sessions: {sessions}")
print(f"Date range: {first} to {last}")

conn.close()
