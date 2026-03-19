/**
 * Content to Social - Extract content from URLs and generate social media posts
 * 
 * Features:
 * - URL content extraction (articles, YouTube, GitHub, etc.)
 * - Multi-platform post generation with optimization
 * - A/B testing variations
 * - Scheduling with approval workflow
 */

'use client'

import React, { useState, useCallback } from 'react'
import { authFetch } from '@/lib/api'

// Platform configurations matching backend
const PLATFORM_CONFIGS: Record<string, { name: string; emoji: string; maxChars: number; color: string }> = {
  instagram: { name: 'Instagram', emoji: '📷', maxChars: 2200, color: 'bg-pink-500' },
  tiktok: { name: 'TikTok', emoji: '🎵', maxChars: 2200, color: 'bg-black' },
  twitter: { name: 'Twitter/X', emoji: '🐦', maxChars: 280, color: 'bg-blue-400' },
  linkedin: { name: 'LinkedIn', emoji: '💼', maxChars: 3000, color: 'bg-warroom-accent' },
  facebook: { name: 'Facebook', emoji: '👥', maxChars: 63206, color: 'bg-warroom-accent/100' }
}

const TONE_OPTIONS = [
  { value: 'professional', label: 'Professional', description: 'Business-focused and informative' },
  { value: 'casual', label: 'Casual', description: 'Friendly and conversational' },
  { value: 'funny', label: 'Funny', description: 'Humorous and entertaining' },
  { value: 'inspiring', label: 'Inspiring', description: 'Motivational and uplifting' }
]

interface ExtractedContent {
  title: string
  body_text: string
  summary: string
  images: string[]
  author: string
  published_date: string
  word_count: number
  source_url: string
  content_type: string
  social_summary?: {
    hook: string
    main_points: string[]
    cta: string
    suggested_hashtags: string[]
  }
}

interface GeneratedPost {
  text: string
  hashtags: string[]
  suggested_media: string[]
  post_type: string
  character_count: number
  truncated: boolean
  key_message: string
  platform: string
}

export default function ContentToSocial() {
  // State management
  const [url, setUrl] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [scheduling, setScheduling] = useState(false)
  const [extractedContent, setExtractedContent] = useState<ExtractedContent | null>(null)
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['instagram', 'twitter'])
  const [selectedTone, setSelectedTone] = useState('professional')
  const [generatedPosts, setGeneratedPosts] = useState<Record<string, GeneratedPost>>({})
  const [editingPosts, setEditingPosts] = useState<Record<string, string>>({})
  const [scheduledFor, setScheduledFor] = useState('')
  const [requireApproval, setRequireApproval] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Clear messages
  const clearMessages = useCallback(() => {
    setError(null)
    setSuccess(null)
  }, [])

  // Extract content from URL
  const handleExtract = async () => {
    if (!url.trim()) {
      setError('Please enter a valid URL')
      return
    }

    setExtracting(true)
    clearMessages()

    try {
      const response = await authFetch('/api/content-social/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url.trim(),
          include_social_summary: true
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to extract content')
      }

      const data = await response.json()
      setExtractedContent(data.data.content)
      setSuccess(`Successfully extracted content: ${data.data.content.title}`)
      
      // Clear any previous posts when new content is extracted
      setGeneratedPosts({})
      setEditingPosts({})
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to extract content')
    } finally {
      setExtracting(false)
    }
  }

  // Generate posts for selected platforms
  const handleGeneratePosts = async () => {
    if (!extractedContent) {
      setError('Please extract content first')
      return
    }

    if (selectedPlatforms.length === 0) {
      setError('Please select at least one platform')
      return
    }

    setGenerating(true)
    clearMessages()

    try {
      const response = await authFetch('/api/content-social/generate-posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: extractedContent,
          platforms: selectedPlatforms,
          tone: selectedTone
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to generate posts')
      }

      const data = await response.json()
      setGeneratedPosts(data.data.posts)
      
      // Initialize editing state
      const editState: Record<string, string> = {}
      Object.entries(data.data.posts).forEach(([platform, post]: [string, any]) => {
        editState[platform] = post.text
      })
      setEditingPosts(editState)
      
      setSuccess(`Generated ${Object.keys(data.data.posts).length} posts successfully`)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate posts')
    } finally {
      setGenerating(false)
    }
  }

  // Schedule posts
  const handleSchedule = async () => {
    if (Object.keys(generatedPosts).length === 0) {
      setError('Please generate posts first')
      return
    }

    if (!scheduledFor) {
      setError('Please select a schedule time')
      return
    }

    const scheduleDateTime = new Date(scheduledFor)
    if (scheduleDateTime <= new Date()) {
      setError('Schedule time must be in the future')
      return
    }

    setScheduling(true)
    clearMessages()

    try {
      // Update posts with edited text
      const postsToSchedule = { ...generatedPosts }
      Object.keys(editingPosts).forEach(platform => {
        if (postsToSchedule[platform]) {
          postsToSchedule[platform].text = editingPosts[platform]
          postsToSchedule[platform].character_count = editingPosts[platform].length
        }
      })

      const response = await authFetch('/api/content-social/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          posts: postsToSchedule,
          selected_platforms: selectedPlatforms,
          scheduled_for: scheduleDateTime.toISOString(),
          require_approval: requireApproval,
          approval_note: 'Generated from content extraction pipeline'
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to schedule posts')
      }

      const data = await response.json()
      setSuccess(
        requireApproval 
          ? `Posts submitted for approval (ID: ${data.data.approval_id})`
          : `Posts scheduled successfully for ${scheduleDateTime.toLocaleString()}`
      )
      
      // Reset form
      setUrl('')
      setExtractedContent(null)
      setGeneratedPosts({})
      setEditingPosts({})
      setScheduledFor('')
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to schedule posts')
    } finally {
      setScheduling(false)
    }
  }

  // Platform toggle handler
  const togglePlatform = (platform: string) => {
    setSelectedPlatforms(prev => 
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    )
  }

  // Post text editing handler
  const updatePostText = (platform: string, text: string) => {
    setEditingPosts(prev => ({
      ...prev,
      [platform]: text
    }))
  }

  // Get minimum schedule time (30 minutes from now)
  const getMinScheduleTime = () => {
    const now = new Date()
    now.setMinutes(now.getMinutes() + 30)
    return now.toISOString().slice(0, 16) // Format for datetime-local input
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="bg-warroom-surface rounded-lg border border-warroom-border p-6">
        <h1 className="text-2xl font-bold text-warroom-text mb-2">
          📄➡️📱 Content to Social Media
        </h1>
        <p className="text-warroom-muted mb-6">
          Extract content from any URL and generate optimized social media posts for multiple platforms
        </p>

        {/* Error/Success Messages */}
        {error && (
          <div className="mb-4 p-4 bg-red-500/10 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}
        
        {success && (
          <div className="mb-4 p-4 bg-emerald-500/10 border border-green-200 rounded-lg">
            <p className="text-green-800">{success}</p>
          </div>
        )}

        {/* Step 1: URL Input */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-warroom-text">
            1. Extract Content from URL
          </h2>
          
          <div className="flex space-x-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/article or youtube.com/watch?v=..."
              className="flex-1 px-3 py-2 border border-warroom-border rounded-md focus:outline-none focus:ring-2 focus:ring-warroom-accent"
              disabled={extracting}
            />
            <button
              onClick={handleExtract}
              disabled={extracting || !url.trim()}
              className="px-4 py-2 bg-warroom-accent text-white rounded-md hover:bg-warroom-accent/80 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {extracting ? 'Extracting...' : 'Extract'}
            </button>
          </div>
          
          <p className="text-sm text-warroom-muted">
            Supports: Articles, blog posts, YouTube videos, GitHub repos, and more
          </p>
        </div>

        {/* Extracted Content Preview */}
        {extractedContent && (
          <div className="mt-6 p-4 bg-warroom-bg rounded-lg">
            <h3 className="font-semibold text-warroom-text mb-2">📄 Extracted Content</h3>
            <div className="space-y-2">
              <p><strong>Title:</strong> {extractedContent.title}</p>
              <p><strong>Type:</strong> {extractedContent.content_type}</p>
              <p><strong>Word Count:</strong> {extractedContent.word_count}</p>
              {extractedContent.author && <p><strong>Author:</strong> {extractedContent.author}</p>}
              {extractedContent.summary && (
                <div>
                  <strong>Summary:</strong>
                  <p className="mt-1 text-warroom-muted">{extractedContent.summary}</p>
                </div>
              )}
              {extractedContent.social_summary && (
                <div>
                  <strong>Hook:</strong>
                  <p className="mt-1 text-warroom-muted">{extractedContent.social_summary.hook}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 2: Platform Selection & Generation */}
        {extractedContent && (
          <div className="mt-8 space-y-4">
            <h2 className="text-lg font-semibold text-warroom-text">
              2. Select Platforms & Generate Posts
            </h2>
            
            {/* Platform Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Target Platforms
              </label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(PLATFORM_CONFIGS).map(([key, config]) => (
                  <button
                    key={key}
                    onClick={() => togglePlatform(key)}
                    className={`px-3 py-2 rounded-md text-sm font-medium border transition-colors ${
                      selectedPlatforms.includes(key)
                        ? 'bg-warroom-accent text-white border-blue-600'
                        : 'bg-warroom-surface text-slate-700 border-warroom-border hover:border-slate-400'
                    }`}
                  >
                    {config.emoji} {config.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Tone Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Tone & Style
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {TONE_OPTIONS.map(tone => (
                  <label key={tone.value} className="relative cursor-pointer">
                    <input
                      type="radio"
                      name="tone"
                      value={tone.value}
                      checked={selectedTone === tone.value}
                      onChange={(e) => setSelectedTone(e.target.value)}
                      className="sr-only"
                    />
                    <div className={`p-3 rounded-lg border text-center transition-colors ${
                      selectedTone === tone.value
                        ? 'bg-warroom-accent/10 border-blue-500 text-blue-900'
                        : 'bg-warroom-surface border-warroom-border hover:border-warroom-border'
                    }`}>
                      <div className="font-medium text-sm">{tone.label}</div>
                      <div className="text-xs text-warroom-muted mt-1">{tone.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGeneratePosts}
              disabled={generating || selectedPlatforms.length === 0}
              className="w-full py-3 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {generating ? 'Generating Posts...' : 'Generate Platform-Optimized Posts'}
            </button>
          </div>
        )}

        {/* Generated Posts Preview & Editing */}
        {Object.keys(generatedPosts).length > 0 && (
          <div className="mt-8 space-y-6">
            <h2 className="text-lg font-semibold text-warroom-text">
              3. Review & Edit Generated Posts
            </h2>
            
            <div className="grid gap-6">
              {selectedPlatforms.map(platform => {
                const post = generatedPosts[platform]
                const config = PLATFORM_CONFIGS[platform]
                const editedText = editingPosts[platform] || post?.text || ''
                const charCount = editedText.length
                const isOverLimit = charCount > config.maxChars
                
                if (!post) return null
                
                return (
                  <div key={platform} className="border border-warroom-border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <span className={`w-3 h-3 rounded-full ${config.color}`} />
                        <h3 className="font-semibold">{config.emoji} {config.name}</h3>
                        <span className="text-sm text-warroom-muted">
                          ({post.post_type})
                        </span>
                      </div>
                      <div className={`text-sm ${isOverLimit ? 'text-red-400' : 'text-warroom-muted'}`}>
                        {charCount}/{config.maxChars} chars
                      </div>
                    </div>
                    
                    <textarea
                      value={editedText}
                      onChange={(e) => updatePostText(platform, e.target.value)}
                      className={`w-full h-32 p-3 border rounded-md resize-none ${
                        isOverLimit ? 'border-red-300' : 'border-warroom-border'
                      }`}
                      placeholder="Post content..."
                    />
                    
                    {post.hashtags && post.hashtags.length > 0 && (
                      <div className="mt-2">
                        <span className="text-sm text-warroom-muted">Suggested hashtags: </span>
                        <span className="text-sm text-warroom-accent">
                          {post.hashtags.join(' ')}
                        </span>
                      </div>
                    )}
                    
                    {post.suggested_media && post.suggested_media.length > 0 && (
                      <div className="mt-2">
                        <span className="text-sm text-warroom-muted">
                          📷 {post.suggested_media.length} suggested image(s)
                        </span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Step 3: Scheduling */}
        {Object.keys(generatedPosts).length > 0 && (
          <div className="mt-8 space-y-4">
            <h2 className="text-lg font-semibold text-warroom-text">
              4. Schedule Posts
            </h2>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Schedule For
                </label>
                <input
                  type="datetime-local"
                  value={scheduledFor}
                  onChange={(e) => setScheduledFor(e.target.value)}
                  min={getMinScheduleTime()}
                  className="w-full px-3 py-2 border border-warroom-border rounded-md focus:outline-none focus:ring-2 focus:ring-warroom-accent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Approval Required
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={requireApproval}
                    onChange={(e) => setRequireApproval(e.target.checked)}
                    className="rounded border-warroom-border"
                  />
                  <span className="text-sm">Require manual approval before posting</span>
                </label>
              </div>
            </div>
            
            <button
              onClick={handleSchedule}
              disabled={scheduling || !scheduledFor}
              className="w-full py-3 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {scheduling ? 'Scheduling...' : 
               requireApproval ? 'Submit for Approval' : 'Schedule Now'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}