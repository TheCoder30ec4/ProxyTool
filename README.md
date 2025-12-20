# ProxyTool API Documentation

## Overview

ProxyTool API is a FastAPI-based backend service that provides authentication and chat functionality for managing users and processing resumes. The API supports user management, resume uploads, and AI-powered chat interactions.

**Version:** 0.1.0  
**Base URL:** `http://localhost:8000` (default)

## Table of Contents

- [General Endpoints](#general-endpoints)
- [Authentication Endpoints](#authentication-endpoints)
- [Chat Endpoints](#chat-endpoints)
- [Error Handling](#error-handling)
- [Request/Response Models](#requestresponse-models)

---

## General Endpoints

### Root Endpoint

#### `GET /`

Returns basic API information.

**Response:**
```json
{
  "message": "ProxyTool API is running",
  "version": "0.1.0"
}
```

**Status Code:** `200 OK`

---

### Health Check

#### `GET /health`

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Code:** `200 OK`

---

## Authentication Endpoints

All authentication endpoints are prefixed with `/auth`.

### Create User

#### `POST /auth/AddUser`

Creates a new user account.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Request Model:**
- `email` (string, required): Valid email address (EmailStr format)

**Response:**
```json
{
  "message": "User successfully created",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com"
  }
}
```

**Status Codes:**
- `201 Created`: User successfully created
- `400 Bad Request`: Invalid request or email already exists
- `500 Internal Server Error`: Unexpected server error

**Example Request:**
```bash
curl -X POST "http://localhost:8000/auth/AddUser" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

---

### Get User

#### `GET /auth/get-user`

Retrieves user information by email address.

**Query Parameters:**
- `email` (string, required): User email address

**Response:**
```json
{
  "message": "User retrieved successfully",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com"
  }
}
```

**Status Codes:**
- `200 OK`: User retrieved successfully
- `404 Not Found`: User not found
- `500 Internal Server Error`: Unexpected server error

**Example Request:**
```bash
curl -X GET "http://localhost:8000/auth/get-user?email=user@example.com"
```

---

### Delete User

#### `DELETE /auth/RemoveUser`

Deletes a user account by email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Request Model:**
- `email` (string, required): Valid email address (EmailStr format)

**Response:**
```json
{
  "message": "User successfully deleted",
  "deleted_email": "user@example.com"
}
```

**Status Codes:**
- `200 OK`: User successfully deleted
- `404 Not Found`: User not found
- `500 Internal Server Error`: Unexpected server error

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/auth/RemoveUser" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

---

## Chat Endpoints

All chat endpoints are prefixed with `/chat`.

### Upload Resume

#### `POST /chat/upload-resume`

Uploads and processes a resume file (PDF, DOCX, or TXT format).

**Request:**
- Content-Type: `multipart/form-data`

**Form Data:**
- `file` (file, required): Resume file (PDF, DOCX, or TXT)
- `email` (string, required): User email address

**Response:**
```json
{
  "message": "Resume successfully uploaded and processed",
  "data": {
    "filename": "resume.pdf",
    "content_type": "application/pdf",
    "file_size": 12345,
    "text_length": 5000,
    "chat_memory_id": "uuid-string",
    "user_id": "uuid-string"
  }
}
```

**Status Codes:**
- `201 Created`: Resume successfully uploaded and processed
- `400 Bad Request`: Invalid file format or missing parameters
- `404 Not Found`: User not found
- `500 Internal Server Error`: Unexpected server error

**Example Request:**
```bash
curl -X POST "http://localhost:8000/chat/upload-resume" \
  -F "file=@/path/to/resume.pdf" \
  -F "email=user@example.com"
```

---

### Get Resume Details

#### `GET /chat/get-resume-details`

Retrieves all resume details for a user.

**Query Parameters:**
- `email` (string, required): User email address

**Response:**
```json
{
  "message": "Resume details retrieved successfully",
  "user_id": "uuid-string",
  "user_email": "user@example.com",
  "resume_count": 2,
  "resume_details": [
    {
      "id": "uuid-string",
      "message": "message content",
      "resume_details": "extracted resume text",
      "created_at": "2024-01-01T00:00:00",
      "role": "user"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Resume details retrieved successfully
- `404 Not Found`: User not found
- `500 Internal Server Error`: Unexpected server error

**Example Request:**
```bash
curl -X GET "http://localhost:8000/chat/get-resume-details?email=user@example.com"
```

---

### Invoke Chat

#### `POST /chat/invoke`

Invokes a chat interaction with text or audio input (or both). Processes the input using AI models and returns explanations and code.

**Request:**
- Content-Type: `multipart/form-data`

**Form Data:**
- `email` (string, required): User email address
- `text` (string, optional): Text input for chat
- `audio` (file, optional): Audio file input (will be transcribed)
- `model` (string, optional): Model name to use (default: `"openai/gpt-oss-120b"`)
- `temperature` (float, optional): Sampling temperature (default: `0.6`)
- `top_p` (float, optional): Nucleus sampling parameter (default: `0.95`)

**Note:** At least one of `text` or `audio` must be provided.

**Response:**
```json
{
  "message": "Chat invocation completed successfully",
  "data": {
    "explanation": "AI-generated explanation",
    "code": "Generated code snippet",
    "user_id": "uuid-string"
  }
}
```

**Status Codes:**
- `200 OK`: Chat invocation completed successfully
- `400 Bad Request`: Missing required input (text or audio) or validation error
- `404 Not Found`: User not found
- `500 Internal Server Error`: Unexpected server error

**Example Requests:**

**Text-only:**
```bash
curl -X POST "http://localhost:8000/chat/invoke" \
  -F "email=user@example.com" \
  -F "text=What is Python?" \
  -F "model=openai/gpt-oss-120b" \
  -F "temperature=0.6" \
  -F "top_p=0.95"
```

**Audio-only:**
```bash
curl -X POST "http://localhost:8000/chat/invoke" \
  -F "email=user@example.com" \
  -F "audio=@/path/to/audio.wav"
```

**Text and Audio:**
```bash
curl -X POST "http://localhost:8000/chat/invoke" \
  -F "email=user@example.com" \
  -F "text=Additional context" \
  -F "audio=@/path/to/audio.wav"
```

---

## Error Handling

The API uses consistent error response formats:

### Error Response Format

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message"
}
```

### Common Error Types

- `ValidationError`: Invalid input parameters
- `NotFoundError`: Resource not found (e.g., user not found)
- `InternalServerError`: Unexpected server error

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource successfully created
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Request/Response Models

### UserRequestModel

```json
{
  "email": "string (EmailStr format)"
}
```

### UserResponseModel

```json
{
  "id": "string (UUID)",
  "email": "string"
}
```

### ResumeDetailResponseModel

```json
{
  "id": "string (UUID)",
  "message": "string",
  "resume_details": "string | null",
  "created_at": "string (ISO format) | null",
  "role": "string"
}
```

---

## CORS Configuration

The API is configured to accept requests from any origin (`*`). For production, configure the `allow_origins` in `main.py` to restrict access to specific domains.

---

## Running the API

### Development

```bash
cd Backend
python main.py
```

The API will be available at `http://localhost:8000`

### Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Notes

- All timestamps are in ISO 8601 format
- UUIDs are returned as strings
- File uploads support PDF, DOCX, and TXT formats
- Audio files are automatically transcribed before processing
- The chat endpoint requires at least one input (text or audio)

