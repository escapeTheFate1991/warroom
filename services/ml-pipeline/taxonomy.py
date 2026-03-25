"""Master Taxonomy system for comment classification.

Provides centroid-based classification using pre-trained taxonomy for fast,
zero-cost labeling of new comments.
"""

import json
import os
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from sklearn.cluster import KMeans
from collections import Counter
import re

logger = logging.getLogger(__name__)

TAXONOMY_PATH = os.getenv("TAXONOMY_PATH", "/app/taxonomy.json")

@dataclass
class SubTopic:
    id: str
    label: str
    keywords: List[str]
    centroid: Optional[List[float]] = None  # 768-dim embedding centroid

@dataclass  
class TaxonomyCategory:
    id: str
    label: str
    safety_label: str  # Business-level category (Bug Report, Feedback, Feature Request, etc.)
    description: str
    keywords: List[str]
    centroid: Optional[List[float]] = None  # 768-dim embedding centroid
    drill_down_required: bool = False
    sub_topics: List[SubTopic] = field(default_factory=list)
    sample_texts: List[str] = field(default_factory=list)  # Top 3 representative texts

@dataclass
class MasterTaxonomy:
    version: str = "1.0"
    last_updated: str = ""
    categories: List[TaxonomyCategory] = field(default_factory=list)


def load_taxonomy() -> Optional[MasterTaxonomy]:
    """Load Master Taxonomy from JSON file.
    
    Returns None if file doesn't exist or is invalid.
    """
    try:
        if not os.path.exists(TAXONOMY_PATH):
            logger.warning(f"Taxonomy file not found at {TAXONOMY_PATH}")
            return None
            
        with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert dict to dataclass
        categories = []
        for cat_data in data.get("categories", []):
            sub_topics = [
                SubTopic(
                    id=sub_data["id"],
                    label=sub_data["label"],
                    keywords=sub_data["keywords"],
                    centroid=sub_data.get("centroid")
                )
                for sub_data in cat_data.get("sub_topics", [])
            ]
            
            category = TaxonomyCategory(
                id=cat_data["id"],
                label=cat_data["label"],
                safety_label=cat_data["safety_label"],
                description=cat_data["description"],
                keywords=cat_data["keywords"],
                centroid=cat_data.get("centroid"),
                drill_down_required=cat_data.get("drill_down_required", False),
                sub_topics=sub_topics,
                sample_texts=cat_data.get("sample_texts", [])
            )
            categories.append(category)
        
        taxonomy = MasterTaxonomy(
            version=data.get("version", "1.0"),
            last_updated=data.get("last_updated", ""),
            categories=categories
        )
        
        logger.info(f"Loaded taxonomy with {len(categories)} categories")
        return taxonomy
        
    except Exception as e:
        logger.error(f"Failed to load taxonomy: {e}")
        return None


def save_taxonomy(taxonomy: MasterTaxonomy) -> bool:
    """Save Master Taxonomy to JSON file.
    
    Returns True if successful, False otherwise.
    """
    try:
        # Update timestamp
        taxonomy.last_updated = datetime.utcnow().isoformat() + "Z"
        
        # Convert to dict for JSON serialization
        data = asdict(taxonomy)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(TAXONOMY_PATH), exist_ok=True)
        
        # Write to file
        with open(TAXONOMY_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved taxonomy to {TAXONOMY_PATH}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save taxonomy: {e}")
        return False


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    # Normalize vectors
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return np.dot(vec1, vec2) / (norm1 * norm2)


def match_to_taxonomy(embedding: List[float], taxonomy: MasterTaxonomy) -> Tuple[str, float]:
    """Match an embedding against all category centroids using cosine similarity.
    
    Returns:
        Tuple of (label, similarity_score) for the best match.
        Returns ("unknown", 0.0) if no valid centroids exist.
    """
    if not taxonomy.categories:
        return ("unknown", 0.0)
    
    query_vec = np.array(embedding, dtype=np.float32)
    best_label = "unknown"
    best_score = 0.0
    
    for category in taxonomy.categories:
        if category.centroid is None:
            continue
            
        centroid_vec = np.array(category.centroid, dtype=np.float32)
        similarity = cosine_similarity(query_vec, centroid_vec)
        
        if similarity > best_score:
            best_score = similarity
            best_label = category.label
    
    return (best_label, best_score)


def classify_comment(text: str, embedding: List[float], taxonomy: MasterTaxonomy) -> Dict:
    """Classify a single comment against the taxonomy.
    
    Returns:
        {
            "text": original text,
            "label": predicted category label,
            "safety_label": business category,
            "confidence": similarity score,
            "confidence_level": "HIGH" | "MEDIUM" | "LOW",
            "is_new": True if below threshold
        }
    """
    label, confidence = match_to_taxonomy(embedding, taxonomy)
    
    # Find the matching category for safety label
    safety_label = "Discussion"  # Default
    for category in taxonomy.categories:
        if category.label == label:
            safety_label = category.safety_label
            break
    
    # Determine confidence level based on thresholds
    if confidence >= 0.85:
        confidence_level = "HIGH"
        is_new = False
    elif confidence >= 0.6:
        confidence_level = "MEDIUM"
        is_new = False
    else:
        confidence_level = "LOW"
        is_new = True
    
    return {
        "text": text,
        "label": label,
        "safety_label": safety_label,
        "confidence": round(confidence, 3),
        "confidence_level": confidence_level,
        "is_new": is_new
    }


def batch_classify(texts: List[str], embeddings: np.ndarray, taxonomy: MasterTaxonomy) -> List[Dict]:
    """Classify a batch of comments against the taxonomy.
    
    Args:
        texts: List of comment texts
        embeddings: numpy array of shape (n_comments, 768)
        taxonomy: Master taxonomy to classify against
    
    Returns:
        List of classification results, one per comment.
    """
    if len(texts) != len(embeddings):
        raise ValueError("Number of texts and embeddings must match")
    
    results = []
    for text, embedding in zip(texts, embeddings):
        result = classify_comment(text, embedding.tolist(), taxonomy)
        results.append(result)
    
    return results


def extract_keywords_from_cluster(texts: List[str], global_stopwords: set, top_k: int = 10) -> List[str]:
    """Extract distinctive keywords from a cluster of texts.
    
    Uses simple frequency analysis, filtering global stopwords.
    """
    # Combine all texts and extract words
    combined_text = " ".join(texts).lower()
    words = re.findall(r'\b[a-z]{3,}\b', combined_text)
    
    # Filter stopwords and count frequencies
    filtered_words = [w for w in words if w not in global_stopwords]
    word_counts = Counter(filtered_words)
    
    # Return top keywords
    return [word for word, _ in word_counts.most_common(top_k)]


def drill_down_cluster(texts: List[str], embeddings: np.ndarray, 
                      parent_label: str, global_stopwords: set) -> List[SubTopic]:
    """Re-cluster a "General" cluster with higher resolution.
    
    Args:
        texts: List of comment texts in the general cluster
        embeddings: Embeddings for the texts (shape: n_texts x 768)
        parent_label: Label of the parent cluster being drilled down
        global_stopwords: Set of common words to filter from keywords
    
    Returns:
        List of SubTopic objects with refined categorization.
    """
    if len(texts) < 2:
        # Too few texts to cluster
        keywords = extract_keywords_from_cluster(texts, global_stopwords, top_k=5)
        return [SubTopic(
            id=f"{parent_label.lower().replace(' ', '_')}_subtopic_1",
            label=f"{parent_label} - General",
            keywords=keywords,
            centroid=embeddings.mean(axis=0).tolist() if len(embeddings) > 0 else None
        )]
    
    # Determine number of sub-clusters (3-5 based on data size)
    n_clusters = min(max(len(texts) // 3, 2), 5)
    
    try:
        # Perform k-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        centroids = kmeans.cluster_centers_
        
        sub_topics = []
        
        # Process each sub-cluster
        for cluster_id in range(n_clusters):
            cluster_indices = np.where(cluster_labels == cluster_id)[0]
            cluster_texts = [texts[i] for i in cluster_indices]
            
            if not cluster_texts:
                continue
            
            # Extract keywords for this sub-cluster
            keywords = extract_keywords_from_cluster(cluster_texts, global_stopwords, top_k=8)
            
            # Generate sub-topic label from top keywords
            if len(keywords) >= 2:
                sub_label = f"{keywords[0]} {keywords[1]}".title()
            elif len(keywords) == 1:
                sub_label = keywords[0].title()
            else:
                sub_label = f"{parent_label} - Subtopic {cluster_id + 1}"
            
            sub_topic = SubTopic(
                id=f"{parent_label.lower().replace(' ', '_')}_subtopic_{cluster_id + 1}",
                label=sub_label,
                keywords=keywords,
                centroid=centroids[cluster_id].tolist()
            )
            
            sub_topics.append(sub_topic)
        
        logger.info(f"Drilled down '{parent_label}' into {len(sub_topics)} sub-topics")
        return sub_topics
        
    except Exception as e:
        logger.warning(f"Drill-down clustering failed: {e}")
        # Fallback: create a single sub-topic
        keywords = extract_keywords_from_cluster(texts, global_stopwords, top_k=5)
        return [SubTopic(
            id=f"{parent_label.lower().replace(' ', '_')}_subtopic_1",
            label=f"{parent_label} - General",
            keywords=keywords,
            centroid=embeddings.mean(axis=0).tolist() if len(embeddings) > 0 else None
        )]