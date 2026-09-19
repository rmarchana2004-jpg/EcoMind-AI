import os
import json
import pymupdf
import faiss
import numpy as np

from backend.services.embeddings import generate_embedding

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KNOWLEDGE_FOLDER = os.path.join(BASE_DIR, "backend", "data", "knowledge")
VECTORSTORE_FOLDER = os.path.join(BASE_DIR, "backend", "vectorstore")

INDEX_FILE = os.path.join(VECTORSTORE_FOLDER, "knowledge.index")
METADATA_FILE = os.path.join(VECTORSTORE_FOLDER, "metadata.json")


def clean_text(text):
    text = " ".join(text.split())
    return text.strip()


def extract_pdf_chunks(pdf_path):
    chunks = []

    document = pymupdf.open(pdf_path)

    for page_number, page in enumerate(document, start=1):

        text = page.get_text("text")
        text = clean_text(text)

        if not text:
            continue

        # Skip very short pages / headings
        if len(text) < 200:
            continue

        words = text.split()

        chunk_size = 180
        overlap = 40

        start = 0

        while start < len(words):

            end = min(start + chunk_size, len(words))

            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            # Ignore very small chunks
            if len(chunk_text) >= 150:
                chunks.append({
                    "text": chunk_text,
                    "page": page_number,
                    "filename": os.path.basename(pdf_path)
                })

            if end == len(words):
                break

            start = end - overlap

    document.close()

    return chunks


def build_knowledge_base():

    all_chunks = []

    for filename in os.listdir(KNOWLEDGE_FOLDER):

        if filename.lower().endswith(".pdf"):

            pdf_path = os.path.join(
                KNOWLEDGE_FOLDER,
                filename
            )

            print(f"Processing: {filename}")

            chunks = extract_pdf_chunks(pdf_path)

            all_chunks.extend(chunks)

    if not all_chunks:
        print("No PDF files found.")
        return

    print(f"Total chunks: {len(all_chunks)}")

    texts = [
        chunk["text"]
        for chunk in all_chunks
    ]

    embeddings = []

    for i, text in enumerate(texts):

        if i % 50 == 0:
            print(f"Embedding chunk {i}/{len(texts)}")

        embedding = generate_embedding(text)

        embeddings.append(embedding)

    embeddings = np.array(
        embeddings,
        dtype="float32"
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(embeddings)

    os.makedirs(
        VECTORSTORE_FOLDER,
        exist_ok=True
    )

    faiss.write_index(
        index,
        INDEX_FILE
    )

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_chunks,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("Knowledge base created successfully!")
    print(f"Vectors stored: {len(all_chunks)}")


if __name__ == "__main__":
    build_knowledge_base()