import os
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI

# Connect to Neon + SSL
DB_URL = os.getenv("DATABASE_URL")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_db():
    """Create a secure SSL-enabled connection to Neon PostgreSQL."""
    conn = psycopg2.connect(
        DB_URL,
        sslmode="require",
        cursor_factory=RealDictCursor
    )
    return conn


def embed_query(text):
    """Generate an embedding for the changed filename or diff snippet."""
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=[text]
    )
    return response.data[0].embedding


def search_similar_chunks(query_text, limit=12):
    """
    Return the top-N most semantically similar code chunks to the provided text.
    - query_text: name of changed file or its contents
    - limit: how many chunks to return
    """
    embedding = embed_query(query_text)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            repo_name,
            file_path,
            content,
            embedding <-> %s AS distance
        FROM code_chunks
        ORDER BY embedding <-> %s
        LIMIT %s;
    """, (embedding, embedding, limit))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows
