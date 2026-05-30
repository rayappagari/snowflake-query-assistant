from dotenv import load_dotenv
load_dotenv()
from db.connection import execute_query

rows = execute_query(
    "SELECT table_schema, COUNT(*) as table_count "
    "FROM information_schema.tables "
    "WHERE table_type = 'BASE TABLE' "
    "GROUP BY table_schema ORDER BY table_schema"
)
print("Available schemas:")
for r in rows:
    print(f"  {r['TABLE_SCHEMA']}  ({r['TABLE_COUNT']} tables)")
