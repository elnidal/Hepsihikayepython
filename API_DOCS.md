# HepsiHikaye Mobile API Documentation

This document provides details about the RESTful API endpoints available for the HepsiHikaye iOS app integration.

## Base URL

All API requests should be made to: `https://hepsihikaye.net/api/v1/`

## Authentication

The API uses JWT token authentication. 

### Login

**Endpoint:** `/auth/login`
**Method:** `POST`
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "admin"
    },
    "expires_in": 604800
  }
}
```

### Authenticated Requests

For all authenticated endpoints, include the token in the Authorization header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Refresh

**Endpoint:** `/auth/refresh`
**Method:** `POST`
**Auth Required:** Yes

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 604800
  }
}
```

## Posts

### Get Posts List

**Endpoint:** `/posts`
**Method:** `GET`
**Auth Required:** Yes

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)
- `category_id` (optional): Filter by category ID
- `featured` (optional): Filter by featured status (true/false)

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "Post Title",
        "excerpt": "Post excerpt...",
        "category_id": 1,
        "category_name": "Category Name",
        "created_at": "2025-04-02T16:11:00",
        "views": 33,
        "likes": 2,
        "published": true,
        "featured": true,
        "image": "https://example.com/image.jpg"
      }
    ],
    "page": 1,
    "pages": 5,
    "total": 100
  }
}
```

### Get Single Post

**Endpoint:** `/posts/{post_id}`
**Method:** `GET`
**Auth Required:** Yes

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "id": 1,
    "title": "Post Title",
    "content": "<p>HTML content of the post...</p>",
    "excerpt": "Post excerpt",
    "category_id": 1,
    "category_name": "Category Name",
    "author": "Author Name",
    "created_at": "2025-04-02T16:11:00",
    "updated_at": "2025-04-03T10:15:00",
    "views": 33,
    "likes": 2,
    "dislikes": 0,
    "published": true,
    "featured": true,
    "image": "https://example.com/image.jpg",
    "comments": [
      {
        "id": 1,
        "content": "Comment text",
        "name": "Commenter Name",
        "created_at": "2025-04-03T12:30:00",
        "status": "approved"
      }
    ]
  }
}
```

### Create Post

**Endpoint:** `/posts`
**Method:** `POST`
**Auth Required:** Yes
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "title": "New Post Title",
  "content": "<p>HTML content of the post...</p>",
  "excerpt": "Post excerpt",
  "author": "Author Name",
  "category_id": 1,
  "published": true,
  "featured": false,
  "image": "https://example.com/image.jpg"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Post created successfully",
  "data": {
    "id": 5,
    "title": "New Post Title"
  }
}
```

### Update Post

**Endpoint:** `/posts/{post_id}`
**Method:** `PUT`
**Auth Required:** Yes
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "title": "Updated Post Title",
  "content": "<p>Updated HTML content...</p>",
  "excerpt": "Updated excerpt",
  "featured": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Post updated successfully",
  "data": {
    "id": 5,
    "title": "Updated Post Title"
  }
}
```

### Delete Post

**Endpoint:** `/posts/{post_id}`
**Method:** `DELETE`
**Auth Required:** Yes

**Response:**
```json
{
  "status": "success",
  "message": "Post deleted successfully",
  "data": null
}
```

## Categories

### Get Categories

**Endpoint:** `/categories`
**Method:** `GET`
**Auth Required:** Yes

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": [
    {
      "id": 1,
      "name": "Öykü",
      "slug": "oyku",
      "post_count": 25
    },
    {
      "id": 2,
      "name": "Roman",
      "slug": "roman",
      "post_count": 10
    }
  ]
}
```

## Comments

### Get Comments

**Endpoint:** `/comments`
**Method:** `GET`
**Auth Required:** Yes

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)
- `status` (optional): Filter by status (pending, approved, rejected)

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "items": [
      {
        "id": 1,
        "content": "Comment text",
        "name": "Commenter Name",
        "email": "commenter@example.com",
        "created_at": "2025-04-03T12:30:00",
        "status": "pending",
        "post_id": 1,
        "post_title": "Post Title",
        "video_id": null,
        "video_title": null
      }
    ],
    "page": 1,
    "pages": 3,
    "total": 45
  }
}
```

### Update Comment Status

**Endpoint:** `/comments/{comment_id}`
**Method:** `PUT`
**Auth Required:** Yes
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "status": "approved"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Comment status updated",
  "data": null
}
```

## Feed Management

### Get Admin Feed

**Endpoint:** `/feed`
**Method:** `GET`
**Auth Required:** Yes

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 10)
- `category_id` (optional): Filter by category ID

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "Post Title",
        "content": "<p>HTML content of the post...</p>",
        "excerpt": "Post excerpt...",
        "category_id": 1,
        "category_name": "Category Name",
        "author": "Author Name",
        "created_at": "2025-04-02T16:11:00",
        "views": 33,
        "likes": 2,
        "published": true,
        "featured": true,
        "image": "https://example.com/image.jpg",
        "enclosure": {
          "url": "https://example.com/image.jpg",
          "type": "image/jpeg",
          "length": 0
        },
        "comments_count": 5
      }
    ],
    "page": 1,
    "pages": 5,
    "total": 100
  }
}
```

### Get Public Feed

**Endpoint:** `/public/feed`
**Method:** `GET`
**Auth Required:** No

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 10)
- `category_id` (optional): Filter by category ID

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "Post Title",
        "excerpt": "Post excerpt...",
        "category_id": 1,
        "category_name": "Category Name",
        "author": "Author Name",
        "created_at": "2025-04-02T16:11:00",
        "views": 33,
        "likes": 2,
        "image": "https://example.com/image.jpg",
        "enclosure": {
          "url": "https://example.com/image.jpg",
          "type": "image/jpeg",
          "length": 0
        },
        "comments_count": 5
      }
    ],
    "page": 1,
    "pages": 5,
    "total": 100
  }
}
```

### Get Public Post Detail

**Endpoint:** `/public/post/{post_id}`
**Method:** `GET`
**Auth Required:** No

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "id": 1,
    "title": "Post Title",
    "content": "<p>HTML content of the post...</p>",
    "excerpt": "Post excerpt",
    "category_id": 1,
    "category_name": "Category Name",
    "author": "Author Name",
    "created_at": "2025-04-02T16:11:00",
    "views": 34,
    "likes": 2,
    "dislikes": 0,
    "image": "https://example.com/image.jpg",
    "enclosure": {
      "url": "https://example.com/image.jpg",
      "type": "image/jpeg",
      "length": 0
    },
    "comments": [
      {
        "id": 1,
        "content": "Comment text",
        "name": "Commenter Name",
        "created_at": "2025-04-03T12:30:00",
        "status": "approved"
      }
    ]
  }
}
```

## Statistics

### Get Overview Statistics

**Endpoint:** `/stats/overview`
**Method:** `GET`
**Auth Required:** Yes

**Response:**
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "counts": {
      "posts": 100,
      "views": 5240,
      "comments": 345,
      "likes": 720,
      "videos": 15,
      "categories": 5
    },
    "recent_posts": [
      {
        "id": 5,
        "title": "Recent Post Title",
        "created_at": "2025-04-10T16:20:00",
        "views": 15
      }
    ],
    "top_posts": [
      {
        "id": 1,
        "title": "Most Popular Post",
        "views": 500
      }
    ]
  }
}
```

## Media Upload

### Upload Media File

**Endpoint:** `/media/upload`
**Method:** `POST`
**Auth Required:** Yes
**Content-Type:** `multipart/form-data`

**Form Parameters:**
- `file`: The file to upload
- `folder` (optional): Subfolder to store in (default: "posts")

**Response:**
```json
{
  "status": "success",
  "message": "File uploaded successfully",
  "data": {
    "url": "https://example.com/uploads/posts/20250410162530_image.jpg"
  }
}
```

## Standard RSS Feed

In addition to the API endpoints, a standard RSS feed is available at:

**URL:** `https://hepsihikaye.net/feed`

This feed follows the RSS 2.0 specification and includes:
- Enclosure tags for images
- Full article content in content:encoded tags
- Proper category tags
- Consistent date formats

This is useful for RSS readers and other applications that can consume standard RSS feeds.

## Error Responses

All error responses follow this format:

```json
{
  "status": "error",
  "message": "Error message details",
  "data": null
}
```

Common HTTP status codes:
- `400`: Bad Request - Invalid parameters
- `401`: Unauthorized - Authentication required or token invalid
- `404`: Not Found - Resource not found
- `500`: Server Error - Internal server error

## Implementation Notes for iOS Developers

1. Store authentication tokens securely in the iOS keychain
2. Implement token refresh logic when tokens expire
3. Handle network errors gracefully with appropriate user messaging
4. Use proper error handling and loading states in the UI
5. Consider implementing offline capabilities for content editing
6. For the reader app, use the `/public/feed` and `/public/post/{post_id}` endpoints
7. For the admin app, use the authenticated endpoints 