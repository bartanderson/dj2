#!/usr/bin/env python
# scripts/visualize_embeddings.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from world.db import Database
from world.intent_manager import IntentManager

def load_embeddings_from_db():
    """Fetch all positive examples with intent name and embedding."""
    conn = Database.get_connection()
    try:
        with conn.cursor() as cur:
            # If using pgvector, embedding is vector type; cast to text to get array
            cur.execute("""
                SELECT i.name, ie.example_text, ie.embedding::text
                FROM intent_examples ie
                JOIN intents i ON ie.intent_id = i.id
                WHERE ie.is_positive = TRUE
            """)
            rows = cur.fetchall()
    finally:
        Database.return_connection(conn)

    intents = []
    texts = []
    vectors = []
    for intent, text, emb_str in rows:
        # Parse PostgreSQL vector string like '[0.1,0.2,...]'
        emb_str = emb_str.strip('[]')
        emb = np.array([float(x) for x in emb_str.split(',') if x])
        intents.append(intent)
        texts.append(text)
        vectors.append(emb)
    return intents, texts, np.array(vectors)

def load_embeddings_from_manager(im: IntentManager):
    """Alternative: compute embeddings on the fly (slower)."""
    examples = im.list_examples()
    intents = []
    texts = []
    vectors = []
    for ex in examples:
        if ex['is_positive']:
            intents.append(ex['intent'])
            texts.append(ex['text'])
            vectors.append(im._embed(ex['text']))
    return intents, texts, np.array(vectors)

def main():
    # Use the database approach (fastest)
    print("Loading embeddings from database...")
    intents, texts, vectors = load_embeddings_from_db()
    if len(vectors) == 0:
        print("No embeddings found. Run seed_intents.py first.")
        return

    # Reduce to 2D with PCA
    print(f"Reducing {len(vectors)} vectors to 2D with PCA...")
    pca = PCA(n_components=2)
    coords = pca.fit_transform(vectors)

    # Plot
    unique_intents = sorted(set(intents))
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_intents)))
    intent_to_color = {intent: colors[i] for i, intent in enumerate(unique_intents)}

    plt.figure(figsize=(12, 8))
    for intent in unique_intents:
        mask = [i for i, it in enumerate(intents) if it == intent]
        plt.scatter(coords[mask, 0], coords[mask, 1],
                    c=[intent_to_color[intent]], label=intent, alpha=0.7, edgecolors='k')

    # Optionally add text labels for a few points (optional)
    # for i, text in enumerate(texts):
    #     if len(text) < 30:  # avoid crowding
    #         plt.annotate(text, (coords[i,0], coords[i,1]), fontsize=6, alpha=0.5)

    plt.xlabel('Principal Component 1')
    plt.ylabel('Principal Component 2')
    plt.title('Intent Embedding Clusters (PCA)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('intent_clusters.png', dpi=150)
    plt.show()

    # Optional: t-SNE (better separation but slower)
    if len(vectors) > 1:
        print("Computing t-SNE (may take a few seconds)...")
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(vectors)-1))
        coords_tsne = tsne.fit_transform(vectors)
        plt.figure(figsize=(12, 8))
        for intent in unique_intents:
            mask = [i for i, it in enumerate(intents) if it == intent]
            plt.scatter(coords_tsne[mask, 0], coords_tsne[mask, 1],
                        c=[intent_to_color[intent]], label=intent, alpha=0.7, edgecolors='k')
        plt.xlabel('t-SNE Component 1')
        plt.ylabel('t-SNE Component 2')
        plt.title('Intent Embedding Clusters (t-SNE)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('intent_clusters_tsne.png', dpi=150)
        plt.show()

if __name__ == "__main__":
    main()