# Instagram CDN → Garage S3 Migration Job

## 🎯 **TASK COMPLETED**

Built a complete background job system to download 616 expired Instagram CDN URLs from the War Room database and store them permanently in Garage S3.

## ✅ **Deliverables**

### 1. **Core Migration Job** (`app/jobs/cdn_migration.py`)
- Complete async migration system with progress tracking
- S3 upload logic using `boto3` with Garage S3 credentials  
- Database updates to replace CDN URLs with S3 URLs
- Error handling for 404s, timeouts, S3 failures
- Batch processing (15 posts at a time to avoid overwhelming Instagram/S3)
- URL format: `http://10.0.0.11:3900/media/instagram/{competitor_name}/{post_id}_{timestamp}_{thumb|media}.{ext}`

### 2. **API Endpoints** (`app/api/cdn_migration.py`)
- `POST /api/jobs/migrate-cdn-urls` - Start full migration (616 URLs)
- `POST /api/jobs/migrate-cdn-urls/test` - Test with 5 URLs first
- `GET /api/jobs/cdn-migration/status` - Monitor progress and errors

### 3. **Integration** 
- Added to main FastAPI app (`app/main.py`)
- Uses existing War Room patterns (SQLAlchemy, asyncpg, FastAPI BackgroundTasks)
- Integrated with existing auth system

## 🧪 **Testing Results**

### ✅ **Expired URLs (Expected Behavior)**
- Tested with 5 old CDN URLs → All returned 403 (expired)
- Error handling working correctly
- Job completes gracefully even when all URLs are expired

### ✅ **Fresh URLs (Migration Success)**  
- Tested with 1 fresh URL → **100% success**
- Files uploaded to S3: `39,657 bytes` (thumbnail), video file (media)
- Database updated with new S3 URLs:
  - **Old**: `https://scontent-atl3-3.cdninstagram.com/v/t51.71878-15/...`
  - **New**: `http://10.0.0.11:3900/media/instagram/Promptwarrior/2340_20260321_093502_thumb.jpg`

### ✅ **S3 Storage Verified**
- Files successfully uploaded to `media` bucket
- Correct content types (`image/jpeg`, `video/mp4`)
- S3 client connection and authentication working

## 🚀 **How to Use**

### Start Backend
```bash
cd /home/eddy/Development/warroom/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Test with 5 URLs First
```bash
curl -X POST "http://localhost:8000/api/jobs/migrate-cdn-urls/test" \
  -H "Authorization: Bearer <your-jwt-token>"
```

### Run Full Migration (616 URLs)
```bash
curl -X POST "http://localhost:8000/api/jobs/migrate-cdn-urls" \
  -H "Authorization: Bearer <your-jwt-token>"
```

### Monitor Progress
```bash
curl "http://localhost:8000/api/jobs/cdn-migration/status" \
  -H "Authorization: Bearer <your-jwt-token>"
```

## 📊 **Expected Results**

- **Total URLs**: 616 Instagram CDN URLs
- **Expected Success Rate**: Low (most URLs likely expired)
- **Batch Size**: 15 URLs per batch (prevents overwhelming systems)
- **Storage Location**: Garage S3 `media` bucket
- **Database Updates**: `crm.competitor_posts` table URLs updated

## 🔧 **Technical Implementation**

### Database Query
```sql
SELECT cp.id, cp.thumbnail_url, cp.media_url, c.handle
FROM crm.competitor_posts cp
JOIN crm.competitors c ON cp.competitor_id = c.id
WHERE cp.thumbnail_url LIKE '%cdninstagram%' 
   OR cp.media_url LIKE '%cdninstagram%'
```

### S3 Configuration
```python
GARAGE_CONFIG = {
    "endpoint_url": "http://10.0.0.11:3900",
    "access_key_id": "GK891b44277c4af3277a8a3e93", 
    "secret_access_key": "d2c208430df9781a66562617379fa2d8470fb1aebcd011096475fa0a3b47c8b9",
    "region_name": "ai-local",
    "bucket": "media"
}
```

### Error Handling
- **403 Forbidden**: URL expired (logged, continues processing)
- **404 Not Found**: URL not found (logged, continues processing)  
- **S3 Upload Failed**: Retryable error (logged, URL not updated)
- **Database Update Failed**: Critical error (logged, continues processing)

## ⚡ **Ready for Production**

The migration job is production-ready with:
- ✅ Progress tracking and status monitoring
- ✅ Graceful error handling 
- ✅ Batch processing to prevent system overload
- ✅ Database transaction safety
- ✅ Comprehensive logging
- ✅ API endpoints for monitoring and control

**Recommendation**: Run the test endpoint first (`/test`) to verify everything works, then run the full migration (`/migrate-cdn-urls`).