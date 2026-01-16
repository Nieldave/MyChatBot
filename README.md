# System Architecture

This document describes the architecture, design decisions, and data flow of the Chatbot Platform.

The system is designed as a secure, scalable, and modular full-stack application that separates concerns between authentication, application logic, data persistence, and AI inference.

## High-Level Architecture

```
Client (React Frontend)
        |
        |  Firebase Authentication (Client SDK)
        |  ID Token (JWT)
        |
Backend API (FastAPI)
        |
        |  Firebase Admin SDK (Token Verification)
        |  Business Logic & Authorization
        |
Cloud Firestore (Database)
        |
        |
External LLM Provider (OpenRouter)
```

## Core Design Principles

### 1. Separation of Concerns

- Frontend handles only UI, user interaction, and authentication initiation
- Backend handles authorization, data access, validation, and LLM communication
- Database stores only application data, never authentication credentials
- LLM API keys and database credentials remain strictly backend-only

### 2. Stateless Backend

- The backend does not store sessions
- Every request is authenticated using Firebase-issued JWT tokens
- Enables horizontal scaling and easy deployment

### 3. Zero Trust Model

- The backend never trusts user-supplied identifiers
- User identity is always extracted from verified Firebase ID tokens
- Ownership checks are enforced at the database level

## Authentication Architecture

### Authentication Flow

1. User signs up or logs in using Firebase Authentication on the frontend
2. Firebase issues an ID token (JWT)
3. The frontend attaches the token to every API request
4. The backend verifies the token using Firebase Admin SDK
5. The decoded token provides the authenticated user ID
6. All database queries are scoped to this user ID

### Why Firebase Authentication

- Industry-grade security
- Handles password hashing, token rotation, and session management
- Reduces attack surface by removing custom authentication logic
- Seamless integration with both frontend and backend

## Backend Architecture

### Framework

**FastAPI (Python)**

#### Reasons for FastAPI

- Async-first design suitable for LLM API calls
- Automatic request validation using Pydantic
- Built-in OpenAPI documentation
- High performance and scalability

### Backend Responsibilities

- Verify Firebase ID tokens
- Enforce authorization and ownership checks
- Interact with Firestore
- Call external LLM APIs
- Handle file uploads and metadata
- Return structured API responses

## Database Architecture (Firestore)

### Collections Overview

#### users

Stores basic user metadata after registration:

- email
- displayName
- createdAt

#### projects

Represents user-created AI agents:

- userId
- name
- systemPrompt
- createdAt

#### messages (subcollection under projects)

Stores chat history:

- role (user / assistant)
- content
- timestamp

#### files

Stores uploaded file metadata:

- projectId
- userId
- filename
- contentType
- size
- uploadedAt

### Indexing Strategy

- Composite indexes are used for filtered and ordered queries
- Ensures efficient retrieval of user-specific projects and messages

## LLM Integration Architecture

### LLM Provider

**OpenRouter** (supports multiple open-source and commercial models)

### Integration Flow

1. Backend constructs chat context using:
   - Project system prompt
   - Recent chat history
   - Current user message
2. Backend sends request to OpenRouter API
3. LLM response is received asynchronously
4. Response is persisted in Firestore
5. Response is returned to the frontend

### Key Design Decisions

- LLM API keys are never exposed to the frontend
- Context length is limited to control latency and cost
- LLM logic is isolated to allow provider swapping

## Frontend Architecture

### Framework

**React with TypeScript (Vite)**

### Frontend Responsibilities

- Handle user authentication via Firebase SDK
- Maintain UI state and routing
- Attach ID tokens to backend requests
- Render projects, chat messages, and files
- Handle loading, error, and empty states gracefully

### State Management

- Firebase auth state listener for session persistence
- Backend is the source of truth for all application data

## Security Considerations

- Backend-only access to Firestore and LLM APIs
- Firebase Admin SDK used exclusively on backend
- JWT verification on every protected request
- Authorization enforced via ownership checks
- Environment variables used for secrets
- No credentials committed to version control

## Scalability and Extensibility

### Scalability

- Stateless backend allows horizontal scaling
- Firestore supports concurrent users and projects
- Async LLM calls reduce request blocking

### Extensibility

Modular API design supports:

- Analytics
- File embeddings
- Streaming responses
- Multiple LLM providers
- Role-based access control

## Summary

This architecture follows modern backend and AI platform best practices. It ensures security, scalability, and maintainability while remaining flexible enough to support future enhancements without major refactoring.
