# Backend Requirements for Science Talk

## Overview

Science Talk is a forum for sharing scientific results, methods, tools, and discussions. This document outlines the backend requirements to support the frontend application.

## Authentication

### AT Protocol / Bluesky Integration

- **Method**: Use AT Protocol (atproto) for authentication via Bluesky
- **User Identity**: Users authenticate with their Bluesky handles (e.g., `username.bsky.social`)
- **Session Management**:
  - Support JWT tokens or AT Protocol session tokens
  - Implement token refresh mechanism
  - Store minimal user data locally (handle, display name, avatar URL)
- **Permissions**: All authenticated users can post, comment, and vote

## Data Models

### User
```
- id: UUID (primary key)
- bluesky_did: string (unique, AT Protocol DID)
- handle: string (Bluesky handle)
- display_name: string (optional)
- avatar_url: string (optional)
- karma: integer (total points from all posts/comments)
- created_at: timestamp
- updated_at: timestamp
```

### Post
```
- id: UUID (primary key)
- title: string (required, max 300 chars)
- type: enum (result, method, review, discussion, ask, tool)
- url: string (optional, required for result/method/review/tool)
- text: text (optional, required for discussion/ask)
- author_id: UUID (foreign key to User)
- author_handle: string (denormalized for display)
- points: integer (default 1)
- comment_count: integer (default 0, denormalized)
- created_at: timestamp
- updated_at: timestamp
- deleted_at: timestamp (soft delete)
```

### Comment
```
- id: UUID (primary key)
- post_id: UUID (foreign key to Post)
- parent_id: UUID (foreign key to Comment, nullable for top-level)
- author_id: UUID (foreign key to User)
- author_handle: string (denormalized for display)
- text: text (required, max 10000 chars)
- points: integer (default 1)
- depth: integer (for efficient querying)
- created_at: timestamp
- updated_at: timestamp
- deleted_at: timestamp (soft delete)
```

### Vote
```
- id: UUID (primary key)
- user_id: UUID (foreign key to User)
- votable_type: enum (post, comment)
- votable_id: UUID (polymorphic reference)
- vote_type: enum (up) - only upvotes for now
- created_at: timestamp

- unique constraint on (user_id, votable_type, votable_id)
```

## API Endpoints

### Authentication
- `POST /auth/bluesky/login` - Initiate Bluesky OAuth flow
- `POST /auth/bluesky/callback` - Handle OAuth callback
- `POST /auth/refresh` - Refresh authentication token
- `POST /auth/logout` - Invalidate session
- `GET /auth/me` - Get current user info

### Posts
- `GET /posts` - List posts (paginated)
  - Query params: `sort` (recent, active), `type`, `page`, `limit`
- `GET /posts/:id` - Get single post with details
- `POST /posts` - Create new post (authenticated)
- `PUT /posts/:id` - Update post (author only)
- `DELETE /posts/:id` - Soft delete post (author only)
- `POST /posts/:id/vote` - Upvote a post (authenticated)
- `DELETE /posts/:id/vote` - Remove vote (authenticated)

### Comments
- `GET /posts/:postId/comments` - Get comments for a post (nested structure)
- `POST /posts/:postId/comments` - Create top-level comment (authenticated)
- `POST /comments/:id/replies` - Reply to a comment (authenticated)
- `PUT /comments/:id` - Update comment (author only)
- `DELETE /comments/:id` - Soft delete comment (author only)
- `POST /comments/:id/vote` - Upvote a comment (authenticated)
- `DELETE /comments/:id/vote` - Remove vote (authenticated)

### Users
- `GET /users/:handle` - Get user profile and their posts/comments
- `GET /users/:handle/karma` - Get user karma score

## Features

### Post Submission
- Support 6 post types: result, method, review, discussion, ask, tool
- **URL posts** (result, method, review, tool): Require URL, optional text description
- **Text posts** (discussion, ask): Require text content, no URL
- Title required for all posts (max 300 chars)
- Validate URLs when provided
- Extract domain from URLs for display

### Comments
- **Nested/threaded comments** with unlimited depth
- Efficient retrieval of comment trees
- Display comment depth for indentation on frontend
- Support markdown formatting in comment text

### Voting
- **Upvote only** system (no downvotes)
- Users can vote on posts and comments
- One vote per user per item
- Points update in real-time
- Track total karma per user

### Feed Sorting
- **Recent**: Sort by `created_at` descending
- **Active**: Sort by recent comment activity (last comment timestamp)
- Pagination with configurable page size (default 30)

### Validation
- Content validation (no empty posts, reasonable length limits)

## Technical Requirements

### Technology Stack Recommendations
- **Language**: Node.js/TypeScript or Python
- **Framework**: Express.js, Fastify, or FastAPI
- **Database**: PostgreSQL (required for nested comments, JSONB support)
- **AT Protocol SDK**: Use official `@atproto/api` (Node) or equivalent

### Database
- Use PostgreSQL with proper indexes
- Indexes on:
  - `posts.created_at`, `posts.type`, `posts.author_id`
  - `comments.post_id`, `comments.parent_id`, `comments.created_at`
  - `votes (user_id, votable_type, votable_id)`
- Use recursive CTEs or ltree for efficient comment tree queries

### API Design
- RESTful API design
- JSON request/response format
- Proper HTTP status codes
- Error responses with consistent structure
- CORS support for frontend origin

### Security
- AT Protocol token validation
- Input sanitization and validation
- SQL injection prevention (use parameterized queries)
- XSS prevention (sanitize user input)
- HTTPS only in production

### Logging
- Basic request/response logging
- Error logging

## Future Considerations (Out of Scope for MVP)

- Rate limiting and spam prevention
- Performance optimization and caching
- User notifications
- Post editing history
- Comment search
- Moderation tools (flagging, hiding posts)
- User blocking
- Email notifications
- RSS feeds
- Admin dashboard
- Analytics and insights

## Data Migration & Seeding

- Create database schema migrations
- Seed initial data for development:
  - Test users (mock Bluesky accounts)
  - Sample posts across all types
  - Sample comments with nested structure
  - Sample votes for realistic karma scores

## Testing Requirements

- Basic integration tests for API endpoints
- AT Protocol authentication flow testing (use test accounts)

## Deployment

- Environment-based configuration (development, production)
- Basic database backup strategy
