import chromadb
import uuid

client = chromadb.PersistentClient(path="/app/chroma_data")

collection = client.get_or_create_collection(
    name="medical_ai_cache"
)


def search_cached_answer(user_question: str, threshold: float = 0.30):
    """
    Lower Chroma distance means more similar.
    If distance is below threshold, we reuse stored answer.
    """

    results = collection.query(
        query_texts=[user_question],
        n_results=1,
        include=["documents", "metadatas", "distances"]
    )

    if not results["ids"] or not results["ids"][0]:
        return None

    distance = results["distances"][0][0]
    metadata = results["metadatas"][0][0]

    if distance <= threshold:
        return {
            "answer": metadata["answer"],
            "matched_question": results["documents"][0][0],
            "distance": distance
        }

    return None


def save_answer_to_cache(user_question: str, ai_answer: str):
    item_id = str(uuid.uuid4())

    collection.add(
        ids=[item_id],
        documents=[user_question],
        metadatas=[{
            "answer": ai_answer
        }]
    )

    return item_idUnable to initialize device PRN
