# Prompt 07 — REST API Endpoints

**Context:** Read ENGRAM_BUILD_SPEC.md → "REST API" section.

**Task — api/v1/memories.py:**
Implement an APIRouter with these 5 endpoints:

1. `POST /memories`
   - Accepts MemoryCreateRequest
   - Routes to the correct layer based on req.layer
   - Returns MemoryResponse with HTTP 201

2. `GET /memories`
   - Query params: user_id (required), layer (optional, default=episodic), limit (default=50)
   - Returns MemoryListResponse

3. `GET /memories/{memory_id}`
   - Returns MemoryResponse or HTTP 404

4. `POST /memories/search`
   - Accepts MemorySearchRequest
   - Only works for semantic and hive layers (others return HTTP 400)
   - Returns MemorySearchResponse

5. `DELETE /memories/{memory_id}`
   - Deletes from correct layer
   - Returns HTTP 204

Use FastAPI Depends for DB connection injection (open/close per request).
Use proper HTTPException with meaningful detail messages.
Tag all routes with "memories" for OpenAPI grouping.
