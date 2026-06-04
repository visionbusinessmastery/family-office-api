from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text

load_dotenv()
print('SECRET_KEY=' + str(os.getenv('SECRET_KEY')))
print('DATABASE_URL=' + str(os.getenv('DATABASE_URL')))
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.begin() as conn:
    rows = conn.execute(text('SELECT email, plan, id FROM users LIMIT 5')).fetchall()
    print('USERS_SAMPLE=' + str([(row.email, row.plan, row.id) for row in rows]))
