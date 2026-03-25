#!/usr/bin/env python3
"""Quick test to verify taxonomy system functionality."""

import json
import numpy as np
from taxonomy import MasterTaxonomy, TaxonomyCategory, SubTopic, save_taxonomy, load_taxonomy, classify_comment

def test_taxonomy_basic():
    """Test basic taxonomy creation, save/load, and classification."""
    print("Testing taxonomy system...")
    
    # Create a simple test taxonomy
    categories = [
        TaxonomyCategory(
            id="cat_1",
            label="Video Editing Questions",
            safety_label="Question",
            description="Questions about video editing software and techniques",
            keywords=["editing", "software", "premiere", "davinci"],
            centroid=[0.1] * 768,  # Simple test centroid
            sample_texts=["How do I edit in Premiere?", "What's the best editing software?"]
        ),
        TaxonomyCategory(
            id="cat_2", 
            label="Product Recommendations",
            safety_label="Product Discussion",
            description="Discussions about recommended tools and products",
            keywords=["recommend", "best", "tool", "product"],
            centroid=[0.2] * 768,  # Different test centroid
            sample_texts=["I recommend DaVinci Resolve", "Best camera for beginners"]
        )
    ]
    
    taxonomy = MasterTaxonomy(
        version="test_1.0",
        categories=categories
    )
    
    # Test save
    print("Testing save...")
    success = save_taxonomy(taxonomy)
    if not success:
        print("❌ Save failed")
        return False
    print("✅ Save succeeded")
    
    # Test load
    print("Testing load...")
    loaded_taxonomy = load_taxonomy()
    if loaded_taxonomy is None:
        print("❌ Load failed")
        return False
    print("✅ Load succeeded")
    
    # Verify data integrity
    if len(loaded_taxonomy.categories) != 2:
        print("❌ Category count mismatch")
        return False
    
    if loaded_taxonomy.categories[0].label != "Video Editing Questions":
        print("❌ Category label mismatch")
        return False
    
    print("✅ Data integrity verified")
    
    # Test classification
    print("Testing classification...")
    test_text = "How do I use Premiere Pro for color grading?"
    test_embedding = [0.15] * 768  # Closer to cat_1 centroid
    
    result = classify_comment(test_text, test_embedding, loaded_taxonomy)
    
    expected_keys = {"text", "label", "safety_label", "confidence", "confidence_level", "is_new"}
    if not expected_keys.issubset(result.keys()):
        print(f"❌ Classification result missing keys: {expected_keys - result.keys()}")
        return False
    
    print(f"✅ Classification result: {result['label']} ({result['confidence']:.3f})")
    print("✅ All tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_taxonomy_basic()
        if success:
            print("\n🎉 Taxonomy system is working correctly!")
        else:
            print("\n💥 Tests failed!")
    except Exception as e:
        print(f"💥 Test error: {e}")
        import traceback
        traceback.print_exc()