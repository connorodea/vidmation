# AIVidio — Complete Backend API Specification

> Feed this to v0.app to generate the frontend UI for aividio.com
>
> Tech stack: Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui
> Design: OpenAI-inspired dark mode (#0d0d0d background, #1a1a1a surfaces, #10a37f accent green)
> Font: Inter
> Domain: aividio.com

---

## Brand

- **Name**: AIVidio
- **Tagline**: Create Faceless YouTube Videos with AI
- **Logo**: "Ai" monogram in a rounded green (#10a37f) square
- **Theme**: Dark mode only. Background #0d0d0d, cards #1a1a1a, borders rgba(255,255,255,0.08), text #ececec/#999/#666, accent #10a37f

---

## Authentication

All protected endpoints require `Authorization: Bearer <access_token>` header.

### POST /auth/signup
Create a new account.
```json
Request: { "name": "string", "email": "string", "password": "string (min 8, upper+lower+digit)" }
Response 201: { "access_token": "jwt", "refresh_token": "jwt", "user": { "id": "uuid", "email": "string", "name": "string", "subscription_tier": "free", "is_verified": false } }
Error 400: { "detail": "Email already registered" }
Error 422: { "detail": "Password must contain uppercase, lowercase, and digit" }
```

### POST /auth/login
```json
Request: { "email": "string", "password": "string" }
Response 200: { "access_token": "jwt", "refresh_token": "jwt", "user": { ... } }
Error 401: { "detail": "Invalid email or password" }
Error 429: { "detail": "Too many attempts. Try again in 60 seconds." }
```

### POST /auth/refresh
```json
Request: { "refresh_token": "jwt" }
Response 200: { "access_token": "jwt", "refresh_token": "jwt" }
Error 401: { "detail": "Invalid or expired refresh token" }
```

### GET /auth/me (Protected)
```json
Response 200: {
  "id": "uuid",
  "email": "string",
  "name": "string",
  "subscription_tier": "free | pro | business",
  "subscription_expires_at": "datetime | null",
  "is_active": true,
  "is_admin": false,
  "is_verified": false,
  "created_at": "datetime",
  "last_login_at": "datetime"
}
```

### PUT /auth/me (Protected)
```json
Request: { "name": "string?", "email": "string?" }
Response 200: { "user": { ... } }
```

### POST /auth/change-password (Protected)
```json
Request: { "old_password": "string", "new_password": "string" }
Response 200: { "message": "Password updated" }
Error 400: { "detail": "Incorrect current password" }
```

### POST /auth/logout (Protected)
```json
Response 200: { "message": "Logged out" }
```

### POST /auth/forgot-password
```json
Request: { "email": "string" }
Response 200: { "message": "If that email exists, a reset link has been sent." }
```

### POST /auth/reset-password
```json
Request: { "token": "string", "new_password": "string" }
Response 200: { "message": "Password has been reset" }
Error 400: { "detail": "Invalid or expired reset token" }
```

---

## Videos

### POST /api/v1/videos (Protected)
Create a video and queue generation.
```json
Request: {
  "topic": "string (required)",
  "channel_id": "uuid (required)",
  "format": "landscape | portrait | short (default: landscape)",
  "style": "oil_painting | cinematic_realism | anime_illustration | watercolor | dark_noir | retro_vintage | corporate_clean | sci_fi_futuristic | nature_documentary | stock_footage",
  "voice": "onyx | echo | nova | alloy | shimmer | fable (default: onyx)",
  "music_style": "cinematic | ambient | upbeat | dark | none (default: cinematic)",
  "caption_style": "yellow_keyword | white_clean | bold_centered (default: yellow_keyword)",
  "duration": "short | medium | long (default: medium)",
  "niche": "finance | tech | self_improvement | business | crypto | health | education | entertainment | general"
}
Response 201: {
  "video": { "id": "uuid", "title": "", "status": "draft", "topic_prompt": "string", ... },
  "job": { "id": "uuid", "status": "queued", "job_type": "full_pipeline", ... }
}
```

### GET /api/v1/videos (Protected)
```
Query params: ?status=draft|generating|ready|uploaded|failed &limit=50 &offset=0 &channel_id=uuid
Response 200: {
  "videos": [ { "id", "title", "status", "format", "duration_seconds", "thumbnail_path", "youtube_url", "created_at", "channel": { "id", "name" } } ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

### GET /api/v1/videos/{id} (Protected)
```json
Response 200: {
  "id": "uuid",
  "channel_id": "uuid",
  "title": "string",
  "description": "string",
  "tags": ["string"],
  "topic_prompt": "string",
  "script_json": { "title", "hook", "sections": [{ "section_number", "heading", "narration", "visual_query" }], "outro" },
  "format": "landscape",
  "status": "ready",
  "youtube_video_id": "string | null",
  "youtube_url": "string | null",
  "duration_seconds": 480.5,
  "file_path": "string | null",
  "thumbnail_path": "string | null",
  "error_message": "string | null",
  "created_at": "datetime",
  "channel": { "id", "name" },
  "jobs": [{ "id", "status", "current_stage", "progress_pct", "created_at" }],
  "assets": [{ "id", "asset_type", "source", "file_path" }]
}
```

### DELETE /api/v1/videos/{id} (Protected)
```json
Response 200: { "message": "Video deleted" }
```

### POST /api/v1/videos/batch (Protected)
Generate multiple videos at once.
```json
Request: {
  "topics": ["string", "string", ...],
  "channel_id": "uuid",
  "format": "landscape",
  "style": "oil_painting"
}
Response 201: {
  "videos": [ { "id", "topic_prompt", "status": "draft" } ],
  "jobs": [ { "id", "video_id", "status": "queued" } ],
  "count": 5
}
```

### POST /api/v1/videos/{id}/export (Protected)
Export video for multiple platforms.
```json
Request: { "platforms": ["youtube", "tiktok", "instagram_reels"] }
Response 200: {
  "exports": {
    "youtube": { "file_path": "string", "format": "1920x1080" },
    "tiktok": { "file_path": "string", "format": "1080x1920" },
    "instagram_reels": { "file_path": "string", "format": "1080x1920" }
  }
}
```

### GET /api/v1/videos/{id}/status (Protected)
Poll for generation progress.
```json
Response 200: {
  "status": "generating",
  "current_stage": "images",
  "progress_pct": 45,
  "stages": [
    { "name": "script", "status": "completed" },
    { "name": "voiceover", "status": "completed" },
    { "name": "images", "status": "running", "progress": 12, "total": 40 },
    { "name": "assembly", "status": "pending" },
    { "name": "captions", "status": "pending" },
    { "name": "export", "status": "pending" }
  ],
  "estimated_seconds_remaining": 120
}
```

---

## Channels

### POST /api/v1/channels (Protected)
```json
Request: { "name": "string", "niche": "finance", "profile_path": "channel_profiles/default.yml" }
Response 201: { "id": "uuid", "name": "string", "is_active": true, "created_at": "datetime" }
```

### GET /api/v1/channels (Protected)
```json
Response 200: {
  "channels": [{ "id", "name", "youtube_channel_id", "profile_path", "is_active", "created_at" }]
}
```

### GET /api/v1/channels/{id} (Protected)
### PUT /api/v1/channels/{id} (Protected)
### DELETE /api/v1/channels/{id} (Protected)

---

## Jobs

### GET /api/v1/jobs (Protected)
```
Query: ?status=queued|running|completed|failed &limit=50
Response 200: {
  "jobs": [{
    "id": "uuid",
    "video_id": "uuid",
    "job_type": "full_pipeline | script_only | tts_only",
    "status": "running",
    "current_stage": "voiceover",
    "progress_pct": 25,
    "started_at": "datetime",
    "completed_at": "datetime | null",
    "error_detail": "string | null",
    "created_at": "datetime",
    "video": { "id", "title", "topic_prompt" }
  }]
}
```

### GET /api/v1/jobs/{id} (Protected)
### POST /api/v1/jobs/{id}/cancel (Protected)
### POST /api/v1/jobs/{id}/retry (Protected)

---

## Generate (Direct generation endpoints)

### POST /api/v1/generate/script (Protected)
Generate just a script without creating a video.
```json
Request: { "topic": "string", "style": "oil_painting", "niche": "finance", "duration": "long" }
Response 200: {
  "title": "string",
  "hook": "string",
  "sections": [{ "section_number": 1, "heading": "string", "narration": "string (~200 words)", "visual_query": "string" }],
  "outro": "string",
  "tags": ["string"],
  "total_words": 1500,
  "estimated_duration_seconds": 600
}
```

### POST /api/v1/generate/voiceover (Protected)
```json
Request: { "text": "string", "voice": "onyx", "provider": "openai" }
Response 200: { "audio_url": "string", "duration_seconds": 45.2 }
```

### POST /api/v1/generate/thumbnail (Protected)
```json
Request: { "title": "string", "style": "oil_painting", "niche": "finance" }
Response 200: { "image_url": "string", "size": "1792x1024" }
```

### POST /api/v1/generate/video (Protected, Async)
Full pipeline — returns immediately with job_id.
```json
Request: {
  "topic": "string",
  "channel_name": "string",
  "style": "oil_painting",
  "format": "landscape",
  "voice": "onyx",
  "music_style": "dark_cinematic",
  "caption_style": "yellow_keyword",
  "duration": "long"
}
Response 202: { "job_id": "uuid", "status": "queued", "message": "Video generation started" }
```

---

## AI Agent

### POST /api/v1/agent/create (Protected, Async)
Let AI orchestrate the entire video creation with intelligent decisions.
```json
Request: {
  "topic": "string",
  "channel": "string",
  "style": "oil_painting",
  "duration": "10-12 minutes",
  "budget_limit": 2.00,
  "upload": false
}
Response 202: { "job_id": "uuid", "message": "AI agent started" }
```

### GET /api/v1/agent/status/{job_id} (Protected)
```json
Response 200: {
  "status": "running",
  "current_action": "Generating oil paintings for section 3...",
  "stages_completed": ["script", "voiceover", "images_1", "images_2"],
  "cost_so_far": 0.45,
  "estimated_total_cost": 1.20
}
```

### POST /api/v1/agent/plan (Protected)
Get a production plan without executing.
```json
Request: { "topic": "string", "channel": "string", "style": "oil_painting" }
Response 200: {
  "plan": {
    "steps": [{ "name": "string", "service": "string", "estimated_cost": 0.05 }],
    "total_estimated_cost": 1.20,
    "total_estimated_time_seconds": 300
  }
}
```

---

## Analytics

### GET /api/v1/analytics/costs (Protected)
```
Query: ?period=daily|weekly|monthly
Response 200: {
  "total_cost": 45.20,
  "total_calls": 1250,
  "by_service": { "openai_tts": 12.50, "replicate_flux": 8.30, "openai_gpt4o": 15.40, "pexels": 0.00 },
  "daily_trend": [{ "date": "2026-04-01", "cost": 5.20 }]
}
```

### GET /api/v1/analytics/estimate (Protected)
```
Query: ?style=oil_painting&duration=long
Response 200: {
  "estimated_cost": 0.85,
  "breakdown": { "script": 0.05, "voiceover": 0.15, "images": 0.17, "whisper": 0.02, "music": 0.00 }
}
```

---

## Webhooks

### POST /api/v1/webhooks (Protected)
```json
Request: { "url": "https://example.com/webhook", "events": ["video.completed", "job.failed"], "secret": "string?" }
Response 201: { "id": "uuid", "url": "string", "events": ["string"], "is_active": true }
```

Events: video.created, video.completed, video.failed, video.uploaded, job.started, job.completed, job.failed, batch.completed

---

## Content Planning

### GET /api/v1/content/calendar (Protected)
```json
Response 200: {
  "weeks": [{ "date": "2026-04-07", "items": [{ "topic": "string", "status": "pending|completed|skipped", "video_id": "uuid?" }] }]
}
```

### POST /api/v1/content/generate (Protected)
```json
Request: { "channel_id": "uuid", "weeks": 4 }
Response 200: { "calendar": { ... }, "trending_topics": [{ "topic": "string", "relevance_score": 0.85 }] }
```

---

## Schedule

### POST /api/v1/schedule/video (Protected)
```json
Request: { "video_id": "uuid", "publish_at": "datetime", "platforms": ["youtube", "tiktok"] }
Response 201: { "schedule_id": "uuid", "status": "scheduled" }
```

### POST /api/v1/schedule/recurring (Protected)
```json
Request: { "channel_id": "uuid", "cron_expression": "0 9 * * 1,3,5", "topic_source": "ai|content_calendar" }
Response 201: { "schedule_id": "uuid", "next_run_at": "datetime" }
```

---

## Voices

### GET /api/v1/voices (Protected)
```json
Response 200: {
  "voices": [{
    "id": "uuid",
    "name": "string",
    "provider": "openai | elevenlabs | replicate",
    "is_cloned": false,
    "preview_url": "string?",
    "usage_count": 42
  }]
}
```

### POST /api/v1/voices/clone (Protected)
```
Content-Type: multipart/form-data
Fields: audio (file), name (string), provider (string)
Response 201: { "id": "uuid", "name": "string", "voice_id": "string" }
```

---

## Notifications

### GET /api/v1/notifications (Protected)
```json
Response 200: {
  "notifications": [{
    "id": "uuid",
    "event": "video.completed",
    "title": "Video Ready",
    "message": "Your video 'The Hidden System...' is ready to download.",
    "read_at": "datetime | null",
    "created_at": "datetime"
  }],
  "unread_count": 3
}
```

### POST /api/v1/notifications/{id}/read (Protected)
### GET /api/v1/notifications/unread-count (Protected)
```json
Response 200: { "count": 3 }
```

---

## Video Styles

10 visual styles available for any topic:

| ID | Name | Best For | Keyword Highlight |
|----|------|----------|------------------|
| `oil_painting` | Oil Painting | History, finance, storytelling | Gold #FFD700 |
| `cinematic_realism` | Cinematic Realism | Business, tech, lifestyle | Green #10a37f |
| `anime_illustration` | Anime / Illustration | Gaming, pop culture, storytelling | Red #FF6B6B |
| `watercolor` | Watercolor | Wellness, spirituality, nature | Blue #7C9FF5 |
| `dark_noir` | Dark Noir | Crime, mystery, true crime | Red #FF4444 |
| `retro_vintage` | Retro Vintage | Nostalgia, music, history | Orange #F5A623 |
| `corporate_clean` | Corporate Clean | Business, SaaS, B2B | Green #10a37f |
| `sci_fi_futuristic` | Sci-Fi Futuristic | AI, technology, space | Cyan #00F5FF |
| `nature_documentary` | Nature Documentary | Wildlife, science, geography | Green #4CAF50 |
| `stock_footage` | Stock Footage | Any topic (real video clips) | White #FFFFFF |

---

## Subscription Tiers

| Tier | Price | Videos/Month | Resolution | Features |
|------|-------|-------------|------------|----------|
| **Free** | $0 | 3 | 720p | Watermark, basic styles |
| **Pro** | $29/mo | 30 | 1080p | All styles, batch mode, no watermark |
| **Business** | $79/mo | Unlimited | 4K | API access, white-label, priority support |

---

## UI Pages Needed

1. **Landing page** (/) — Hero, features, pricing, FAQ, CTA (unauthenticated)
2. **Login** (/login) — Email + password
3. **Signup** (/signup) — Name, email, password with strength indicator
4. **Dashboard** (/) — Stats cards, active jobs, recent videos, cost widget
5. **Create Video** (/videos/new) — 5-step wizard: Topic → Script → Voice → Visuals → Generate
6. **Video List** (/videos) — Table with status filters
7. **Video Detail** (/videos/[id]) — Metadata, script, jobs, preview
8. **Channels** (/channels) — Channel management
9. **Jobs** (/jobs) — Job queue with live progress
10. **Analytics** (/analytics) — Cost charts, usage tracking
11. **Content Planner** (/content) — Weekly calendar, trending topics
12. **Voices** (/voices) — Voice library, clone flow
13. **Schedule** (/schedule) — Publishing schedule
14. **Settings** (/settings) — API keys, notifications, billing, webhooks
15. **Pricing** (/pricing) — Subscription tiers with Stripe checkout
