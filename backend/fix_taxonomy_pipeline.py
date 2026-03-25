#!/usr/bin/env python3
"""Fix War Room taxonomy pipeline failures."""

import re

def fix_enhanced_audience_data_sql():
    """Fix the incomplete SQL query in _get_enhanced_audience_data function."""
    
    # Read the current file
    with open('app/api/content_intel.py', 'r') as f:
        content = f.read()
    
    # Find and fix the incomplete SQL query
    old_sql_pattern = r'''query = """
        WITH commenter_data AS \(
            SELECT 
                cp\.id,
                cp\.competitor_id,
                c\.handle as competitor_handle,
                cp\.comments_data,
                cp\.engagement_score,
                cp\.posted_at
            FROM crm\.competitor_posts cp
            JOIN crm\.competitors c ON cp\.competitor_id = c\.id
            WHERE c\.org_id = :org_id
              AND cp\.comments_data IS NOT NULL
              AND \(cp\.comments_data->>'analyzed'\)::int > 0
        """'''
    
    new_sql = '''query = """
        SELECT 
            cp.id,
            cp.competitor_id,
            c.handle as competitor_handle,
            cp.comments_data,
            cp.engagement_score,
            cp.posted_at
        FROM crm.competitor_posts cp
        JOIN crm.competitors c ON cp.competitor_id = c.id
        WHERE c.org_id = :org_id
          AND cp.comments_data IS NOT NULL
          AND (cp.comments_data->>'analyzed')::int > 0
        """'''
    
    # Replace the incomplete CTE with a simple SELECT
    content = re.sub(old_sql_pattern, new_sql, content, flags=re.MULTILINE | re.DOTALL)
    
    # Fix the attribute access error - change post.posted_at to post['posted_at'] or getattr access
    content = re.sub(
        r'posted_at = post\.posted_at or datetime\.now\(\)',
        'posted_at = getattr(post, "posted_at", None) or post.get("posted_at") or datetime.now()',
        content
    )
    
    content = re.sub(
        r'competitor_handle = post\.competitor_handle',
        'competitor_handle = getattr(post, "competitor_handle", None) or post.get("competitor_handle", "")',
        content
    )
    
    content = re.sub(
        r'comments_data = post\.comments_data',
        'comments_data = getattr(post, "comments_data", None) or post.get("comments_data")',
        content
    )
    
    # Write back the fixed content
    with open('app/api/content_intel.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed incomplete SQL query and attribute access errors")

if __name__ == "__main__":
    fix_enhanced_audience_data_sql()
    print("🔧 War Room taxonomy pipeline fixes applied successfully")