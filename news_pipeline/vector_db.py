"""Vector database management using ChromaDB."""

from typing import List

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


class VectorDBManager:
    """Manage vector database operations for document storage and retrieval."""

    def __init__(
        self,
        persist_directory: str = "chroma_db",
        collection_name: str = "summaries",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize vector database manager.

        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection
            embedding_model: HuggingFace embedding model name
        """
        # Initialize embeddings once
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model
        )

        # Initialize DB
        self.db = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name=collection_name
        )

    def add_document(self, doc: Document):
        """
        Add a single document to the database.

        Args:
            doc: Document to add
        """
        doc_id = doc.metadata.get("source_url")

        self.db.add_documents(
            [doc],
            ids=[doc_id]
        )

    def search(self, query: str, k: int = 3) -> List[Document]:
        """
        Search for similar documents.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of similar documents
        """
        return self.db.similarity_search(query, k=k)

    def search_with_threshold(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.1
    ) -> List[Document]:
        """
        Search with a similarity threshold.

        Args:
            query: Search query
            k: Number of results to return
            threshold: Maximum distance threshold (lower is more similar)

        Returns:
            List of documents within the threshold
        """
        results = self.db.similarity_search_with_score(query, k=k)
        docs = []
        for doc, score in results:
            if score <= threshold:
                docs.append(doc)
        return docs

    def delete_all(self):
        """Delete all documents from the collection."""
        self.db.delete_collection()