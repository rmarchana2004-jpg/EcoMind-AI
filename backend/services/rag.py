import json
import faiss
import numpy as np

from backend.services.embeddings import generate_embedding


INDEX_FILE = "backend/vectorstore/knowledge.index"
METADATA_FILE = "backend/vectorstore/metadata.json"


# Load FAISS index
index = faiss.read_index(INDEX_FILE)

# Load metadata
with open(METADATA_FILE, "r", encoding="utf-8") as file:
    metadata = json.load(file)


def search_knowledge(query: str, top_k: int = 5):

    # Create embedding for the query
    query_embedding = generate_embedding(query)

    query_embedding = np.array(
        [query_embedding],
        dtype="float32"
    )

    # Search FAISS
    distances, indices = index.search(
        query_embedding,
        top_k * 2
    )

    results = []

    for distance, index_number in zip(
        distances[0],
        indices[0]
    ):

        if index_number == -1:
            continue

        result = metadata[index_number]

        text = result.get("text", "").strip()

        # Ignore very short chunks
        if len(text) < 150:
            continue

        results.append({
            "text": text,
            "page": result.get("page"),
            "filename": result.get("filename"),
            "distance": round(float(distance), 4)
        })

        if len(results) >= top_k:
            break

    return results