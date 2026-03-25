"""ML Pipeline Microservice - Comment Analysis using FastEmbed + scikit-learn"""

import logging
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from comment_analyzer import analyze_comments_ml

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18798)