"""One-time taxonomy construction from existing comment data.

Builds Master Taxonomy using clustering and keyword extraction.
"""

import logging
import math
import re
import uuid
from collections import Counter
from typing import Dict, List, Set

import httpx
import numpy as np
from sklearn.cluster import KMeans

from taxonomy import (
    MasterTaxonomy, TaxonomyCategory, SubTopic, save_taxonomy, 
    extract_keywords_from_cluster, drill_down_cluster
)

logger = logging.getLogger(__name__)

# Global stopwords for filtering generic terms
GLOBAL_STOPWORDS = {
    "the", "and", "for", "this", "that", "you", "your", "with", "from", "have", "are",
    "but", "not", "was", "were", "been", "being", "its", "just", "really", "very",
    "would", "could", "should", "will", "can", "more", "about", "like", "what",
    "how", "all", "they", "them", "their", "there", "here", "also", "than", "then",
    "too", "out", "get", "got", "has", "had", "did", "does", "don", "one", "who",
    "want", "know", "think", "make", "need", "some", "look", "going", "thing",
    "comment", "comments", "video", "post", "instagram", "follow", "following",
    "love", "great", "amazing", "awesome", "good", "nice", "thanks", "thank"
}

# Pattern sets for safety label classification
QUESTION_PATTERNS = [r'\?', r'\bhow\s+', r'\bwhat\s+', r'\bwhere\s+', r'\bwhen\s+', r'\bwhy\s+', r'\bwhich\s+']
PAIN_PATTERNS = [r'\bstruggle\b', r'\bcan\'?t\b', r'\bwish\s+', r'\bfrustr', r'\bconfused\b', r'\bstuck\b']
REQUEST_PATTERNS = [r'\bplease\b', r'\bcan\s+you\b', r'\bmake\s+a\b', r'\btutorial\s+on\b']
PRAISE_PATTERNS = [r'\blove\b', r'\bamazing\b', r'\bawesome\b', r'\bthank\b', r'\bappreciate\b']
PRODUCT_PATTERNS = [r'[A-Z][a-z]+(?:\s+[A-Z][a-z]*){0,2}', r'@\w+']


async def get_fastembed_embeddings(texts: List[str], fastembed_url: str) -> np.ndarray:
    """Get embeddings from FastEmbed server.
    
    Args:
        texts: List of text strings to embed
        fastembed_url: FastEmbed server endpoint URL
        
    Returns:
        numpy array of shape (n_texts, 768)
        
    Raises:
        Exception if FastEmbed request fails
    """
    if not texts:
        return np.array([])
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            fastembed_url,
            json={"input": texts},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        embeddings = data.get("embeddings", [])
        
        if len(embeddings) != len(texts):
            raise ValueError(f"Expected {len(texts)} embeddings, got {len(embeddings)}")
        
        return np.array(embeddings, dtype=np.float32)


def find_representative_texts(texts: List[str], embeddings: np.ndarray, centroid: np.ndarray, top_k: int = 3) -> List[str]:
    """Find the most representative texts closest to the cluster centroid.
    
    Args:
        texts: List of text strings in the cluster
        embeddings: Embeddings for the texts
        centroid: Cluster centroid vector
        top_k: Number of representative texts to return
    
    Returns:
        List of representative text strings
    """
    if len(texts) == 0:
        return []
    
    # Calculate distances from centroid
    distances = []
    for i, embedding in enumerate(embeddings):
        distance = np.linalg.norm(embedding - centroid)
        distances.append((distance, i))
    
    # Sort by distance (closest first) and return top_k
    distances.sort(key=lambda x: x[0])
    representative_indices = [idx for _, idx in distances[:top_k]]
    
    return [texts[i] for i in representative_indices]


def generate_cluster_label_from_keywords(keywords: List[str], max_words: int = 3) -> str:
    """Generate a readable cluster label from top keywords.
    
    Args:
        keywords: List of keywords sorted by importance
        max_words: Maximum number of words in the label
    
    Returns:
        Human-readable cluster label
    """
    if not keywords:
        return "General Discussion"
    
    # Take the top words and create a readable phrase
    top_keywords = keywords[:max_words]
    
    # Simple heuristics for better labels
    if len(top_keywords) == 1:
        return top_keywords[0].title()
    elif len(top_keywords) == 2:
        return f"{top_keywords[0].title()} {top_keywords[1].title()}"
    else:
        # For 3+ words, try to make it more natural
        return " ".join(word.title() for word in top_keywords)


def classify_safety_label(texts: List[str]) -> str:
    """Assign a business-level safety label based on content patterns.
    
    Args:
        texts: List of texts in the cluster
    
    Returns:
        Safety label: Question, Pain Point, Feature Request, Positive Feedback, 
        Product Discussion, or Discussion
    """
    combined_text = " ".join(texts).lower()
    
    # Count pattern matches
    question_score = sum(len(re.findall(pattern, combined_text)) for pattern in QUESTION_PATTERNS)
    pain_score = sum(len(re.findall(pattern, combined_text)) for pattern in PAIN_PATTERNS)
    request_score = sum(len(re.findall(pattern, combined_text)) for pattern in REQUEST_PATTERNS)
    praise_score = sum(len(re.findall(pattern, combined_text)) for pattern in PRAISE_PATTERNS)
    product_score = sum(len(re.findall(pattern, combined_text)) for pattern in PRODUCT_PATTERNS)
    
    # Determine the dominant pattern
    scores = {
        "Question": question_score,
        "Pain Point": pain_score,
        "Feature Request": request_score,
        "Positive Feedback": praise_score,
        "Product Discussion": product_score
    }
    
    # Return the highest scoring category, or default to Discussion
    max_score = max(scores.values())
    if max_score > 0:
        return max(scores, key=scores.get)
    else:
        return "Discussion"


def should_drill_down(cluster_size: int, total_comments: int, keywords: List[str]) -> bool:
    """Determine if a cluster needs drill-down (hierarchical sub-clustering).
    
    Args:
        cluster_size: Number of comments in this cluster
        total_comments: Total number of comments across all clusters
        keywords: List of keywords extracted from the cluster
    
    Returns:
        True if cluster should be drilled down into sub-topics
    """
    # Drill down if cluster is >30% of total data
    if cluster_size > (total_comments * 0.3):
        return True
    
    # Drill down if keywords are too generic (common words)
    generic_keywords = {"general", "discussion", "comment", "video", "post", "content"}
    if any(keyword.lower() in generic_keywords for keyword in keywords[:3]):
        return True
    
    return False


async def build_taxonomy_from_comments(comments_by_post: Dict[int, List[Dict]], 
                                     fastembed_url: str) -> MasterTaxonomy:
    """Build Master Taxonomy from clustered comment data.
    
    Args:
        comments_by_post: Dict mapping post_id to list of comment dicts
        fastembed_url: FastEmbed server endpoint URL
    
    Returns:
        Complete MasterTaxonomy ready for use
    """
    logger.info("Building taxonomy from comment data...")
    
    # Step 1: Collect all comment texts across all posts
    all_texts = []
    for post_id, comments in comments_by_post.items():
        for comment in comments:
            text = comment.get("text", "").strip()
            if text and len(text) >= 5:  # Filter very short comments
                all_texts.append(text)
    
    if len(all_texts) < 3:
        logger.warning("Not enough comments to build taxonomy")
        return MasterTaxonomy(categories=[])
    
    logger.info(f"Processing {len(all_texts)} comments from {len(comments_by_post)} posts")
    
    # Step 2: Embed all comments via FastEmbed
    embeddings = await get_fastembed_embeddings(all_texts, fastembed_url)
    logger.info(f"Generated {len(embeddings)} embeddings of dimension {embeddings.shape[1]}")
    
    # Step 3: Initial clustering with KMeans
    # k = sqrt(n_comments / 5), min 3, max 20
    n_comments = len(all_texts)
    k = max(3, min(20, int(math.sqrt(n_comments / 5))))
    logger.info(f"Clustering {n_comments} comments into {k} initial clusters")
    
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    centroids = kmeans.cluster_centers_
    
    # Step 4: Process each cluster
    categories = []
    
    for cluster_id in range(k):
        cluster_indices = np.where(cluster_labels == cluster_id)[0]
        cluster_texts = [all_texts[i] for i in cluster_indices]
        cluster_embeddings = embeddings[cluster_indices]
        cluster_centroid = centroids[cluster_id]
        
        if len(cluster_texts) == 0:
            continue
        
        logger.info(f"Processing cluster {cluster_id + 1}/{k} with {len(cluster_texts)} comments")
        
        # Step 4a: Find representative texts (closest to centroid)
        sample_texts = find_representative_texts(
            cluster_texts, cluster_embeddings, cluster_centroid, top_k=3
        )
        
        # Step 4b: Extract top keywords
        keywords = extract_keywords_from_cluster(
            cluster_texts, GLOBAL_STOPWORDS, top_k=12
        )
        
        # Step 4c: Generate label from keywords
        cluster_label = generate_cluster_label_from_keywords(keywords, max_words=3)
        
        # Step 4d: Assign safety label
        safety_label = classify_safety_label(cluster_texts)
        
        # Step 4e: Check if drill-down is required
        drill_down_required = should_drill_down(
            len(cluster_texts), n_comments, keywords
        )
        
        # Step 5: Handle drill-down clusters
        sub_topics = []
        if drill_down_required and len(cluster_texts) > 6:
            logger.info(f"Drilling down cluster '{cluster_label}' with {len(cluster_texts)} comments")
            sub_topics = drill_down_cluster(
                cluster_texts, cluster_embeddings, cluster_label, GLOBAL_STOPWORDS
            )
        
        # Create taxonomy category
        category = TaxonomyCategory(
            id=f"category_{cluster_id + 1}",
            label=cluster_label,
            safety_label=safety_label,
            description=f"Comments related to {cluster_label.lower()}. "
                       f"Contains {len(cluster_texts)} sample comments.",
            keywords=keywords[:8],  # Top 8 keywords
            centroid=cluster_centroid.tolist(),
            drill_down_required=drill_down_required,
            sub_topics=sub_topics,
            sample_texts=sample_texts
        )
        
        categories.append(category)
        logger.info(f"Created category '{cluster_label}' with {len(sub_topics)} sub-topics")
    
    # Create and save the master taxonomy
    taxonomy = MasterTaxonomy(
        version="1.0",
        categories=categories
    )
    
    # Save to file
    if save_taxonomy(taxonomy):
        logger.info(f"Successfully built and saved taxonomy with {len(categories)} categories")
    else:
        logger.error("Failed to save taxonomy to file")
    
    return taxonomy