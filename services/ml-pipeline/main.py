"""ML Pipeline Microservice - Comment Analysis using FastEmbed + scikit-learn"""

import logging
import os
from typing import Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from comment_analyzer import analyze_comments_ml, get_embeddings
from taxonomy import load_taxonomy, save_taxonomy, batch_classify, drill_down_cluster, MasterTaxonomy
from taxonomy_builder import build_taxonomy_from_comments

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Pipeline Service",
    description="ML-powered comment analysis using FastEmbed embeddings and scikit-learn clustering",
    version="1.0.0"
)


class CommentInput(BaseModel):
    text: str
    username: Optional[str] = ""
    likes: Optional[int] = 0
    is_reply: Optional[bool] = False


class AnalyzeCommentsRequest(BaseModel):
    comments: List[CommentInput]
    post_caption: Optional[str] = ""
    creator_username: Optional[str] = ""


class BuildTaxonomyRequest(BaseModel):
    comments_by_post: Dict[int, List[Dict]]


class ClassifyTextsRequest(BaseModel):
    texts: List[str]


class DrillDownRequest(BaseModel):
    texts: List[str]
    parent_label: str


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ml-pipeline"}


@app.post("/analyze-comments")
async def analyze_comments(request: AnalyzeCommentsRequest) -> Dict:
    """Analyze comments using ML pipeline.
    
    Accepts:
    - comments: List of comment objects with text, username, likes, is_reply fields
    - post_caption: Optional post caption for context
    - creator_username: Optional creator username to detect unanswered questions
    
    Returns the full ML analysis result with themes, questions, pain_points, 
    content_gaps, video_topic_suggestions, etc.
    """
    try:
        # Convert pydantic models to dicts for the analyzer
        comments_dict = [
            {
                "text": comment.text,
                "username": comment.username,
                "likes": comment.likes,
                "is_reply": comment.is_reply
            }
            for comment in request.comments
        ]
        
        # Call the ML analyzer
        result = await analyze_comments_ml(
            comments=comments_dict,
            post_caption=request.post_caption,
            creator_username=request.creator_username
        )
        
        logger.info(f"Analyzed {len(comments_dict)} comments, found {len(result.get('themes', []))} themes")
        return result
        
    except Exception as e:
        logger.error(f"Comment analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/taxonomy/build")
async def build_taxonomy(request: BuildTaxonomyRequest) -> Dict:
    """Build Master Taxonomy from comment data.
    
    Accepts:
    - comments_by_post: Dict mapping post_id to list of comment dicts
    
    Returns the complete taxonomy JSON structure.
    """
    try:
        fastembed_url = os.getenv("FASTEMBED_URL", "http://10.0.0.11:11435/api/embed")
        
        # Build taxonomy from comments
        taxonomy = await build_taxonomy_from_comments(
            request.comments_by_post, 
            fastembed_url
        )
        
        logger.info(f"Built taxonomy with {len(taxonomy.categories)} categories")
        
        # Convert to dict for response
        from dataclasses import asdict
        return asdict(taxonomy)
        
    except Exception as e:
        logger.error(f"Taxonomy building failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build taxonomy: {str(e)}")


@app.get("/taxonomy")
async def get_taxonomy() -> Union[Dict, None]:
    """Get the current Master Taxonomy.
    
    Returns the taxonomy JSON or null if no taxonomy exists.
    """
    try:
        taxonomy = load_taxonomy()
        
        if taxonomy is None:
            return None
            
        from dataclasses import asdict
        return asdict(taxonomy)
        
    except Exception as e:
        logger.error(f"Failed to load taxonomy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load taxonomy: {str(e)}")


@app.post("/taxonomy/classify")
async def classify_texts(request: ClassifyTextsRequest) -> List[Dict]:
    """Classify texts against the current Master Taxonomy.
    
    Accepts:
    - texts: List of text strings to classify
    
    Returns list of classification results with label, safety_label, confidence.
    """
    try:
        # Load current taxonomy
        taxonomy = load_taxonomy()
        if taxonomy is None:
            raise HTTPException(status_code=404, detail="No taxonomy found. Build one first.")
        
        # Get embeddings for input texts
        embeddings = await get_embeddings(request.texts)
        if embeddings is None:
            raise HTTPException(status_code=503, detail="FastEmbed service unavailable")
        
        # Classify against taxonomy
        results = batch_classify(request.texts, embeddings, taxonomy)
        
        logger.info(f"Classified {len(request.texts)} texts")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@app.post("/taxonomy/drill-down")
async def drill_down(request: DrillDownRequest) -> List[Dict]:
    """Drill down into a general cluster to find sub-topics.
    
    Accepts:
    - texts: List of texts to re-cluster
    - parent_label: Label of the parent cluster
    
    Returns list of sub-topic objects.
    """
    try:
        # Get embeddings for input texts
        embeddings = await get_embeddings(request.texts)
        if embeddings is None:
            raise HTTPException(status_code=503, detail="FastEmbed service unavailable")
        
        # Import global stopwords
        from taxonomy_builder import GLOBAL_STOPWORDS
        
        # Perform drill-down clustering
        sub_topics = drill_down_cluster(
            request.texts, 
            embeddings, 
            request.parent_label,
            GLOBAL_STOPWORDS
        )
        
        # Convert to dict for response
        from dataclasses import asdict
        results = [asdict(sub_topic) for sub_topic in sub_topics]
        
        logger.info(f"Drilled down {len(request.texts)} texts into {len(results)} sub-topics")
        return results
        
    except Exception as e:
        logger.error(f"Drill-down failed: {e}")
        raise HTTPException(status_code=500, detail=f"Drill-down failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18798)