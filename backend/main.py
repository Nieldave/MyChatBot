import base64
from fastapi import status, Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Depends, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth as firebase_auth, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime
import httpx
from typing import List, Optional
import config
from models import UserCreate, UserLogin, ProjectCreate, ChatMessage, ChatHistory

def get_timestamp():
    return datetime.utcnow()

def serialize_timestamp(timestamp):
    """Convert Firestore Timestamp to ISO string"""
    if timestamp is None:
        return None
    if hasattr(timestamp, 'isoformat'):
        return timestamp.isoformat()
    return str(timestamp)

app = FastAPI(title="Chatbot Platform API")

# CORS allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AUTHENTICATION 

def verify_token(authorization: str = Header(...)) -> str:
    """Verify Firebase ID token and return user ID"""
    try:
        print(f"\n🔍 Verifying token...")
        print(f"Header received: {authorization[:50] if len(authorization) > 50 else authorization}...")
        
        if not authorization.startswith("Bearer "):
            print("❌ Authorization header doesn't start with 'Bearer '")
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        token = authorization.split("Bearer ")[1]
        print(f"Token length: {len(token)}")
        print(f"Token preview: {token[:30]}...")
        
        decoded = firebase_auth.verify_id_token(token)
        print(f"✅ Token verified successfully for user: {decoded['uid']}")
        return decoded["uid"]
        
    except firebase_auth.InvalidIdTokenError as e:
        print(f"❌ Invalid Firebase token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    except firebase_auth.ExpiredIdTokenError as e:
        print(f"❌ Expired Firebase token: {str(e)}")
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        print(f"❌ Token verification error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    
@app.post("/api/auth/register")
async def register(user: UserCreate):
    """Register a new user using Firebase Authentication"""
    try:
        # Create user in Firebase Auth
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password,
            display_name=user.display_name
        )
        
        # Store user metadata in Firestore
        config.db.collection("users").document(user_record.uid).set({
            "email": user.email,
            "displayName": user.display_name,
            "createdAt": datetime.utcnow()
        })
        
        return {
            "success": True,
            "uid": user_record.uid,
            "message": "User registered successfully"
        }
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Email already exists")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/login")
async def login(user: UserLogin):
    """
    Login endpoint - Returns instructions for client-side authentication
    Actual login happens on frontend using Firebase SDK
    """
    try:
        # Verify user exists
        user_record = firebase_auth.get_user_by_email(user.email)
        return {
            "success": True,
            "message": "Use Firebase SDK on frontend to get ID token",
            "uid": user_record.uid
        }
    except firebase_auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/auth/me")
async def get_current_user(user_id: str = Depends(verify_token)):
    """Get current authenticated user details"""
    try:
        user_data = config.db.collection("users").document(user_id).get()
        if not user_data.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        data = user_data.to_dict()
        # Convert timestamp
        if "createdAt" in data:
            data["createdAt"] = serialize_timestamp(data["createdAt"])
        
        return {"uid": user_id, **data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# PROJECTS/AGENTS 

@app.post("/api/projects")
async def create_project(project: ProjectCreate, user_id: str = Depends(verify_token)):
    """Create a new project/agent for the authenticated user"""
    try:
        project_ref = config.db.collection("projects").document()
        project_data = {
            "userId": user_id,
            "name": project.name,
            "systemPrompt": project.system_prompt,
            "createdAt": datetime.utcnow()
        }
        project_ref.set(project_data)
        
        print(f"✅ Created project {project_ref.id} for user {user_id}")
        
        return {
            "success": True,
            "projectId": project_ref.id,
            "message": "Project created successfully"
        }
    except Exception as e:
        print(f"❌ Error creating project: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/projects")
async def list_projects(user_id: str = Depends(verify_token)):
    """List all projects for the authenticated user"""
    try:
        print(f"\n📋 Fetching projects for user: {user_id}")
        
        projects = config.db.collection("projects")\
            .where(filter=FieldFilter("userId", "==", user_id))\
            .stream()
        
        result = []
        for project in projects:
            data = project.to_dict()
            
            # Convert Firestore Timestamp to ISO string
            created_at = serialize_timestamp(data.get("createdAt"))
            
            project_dict = {
                "id": project.id,
                "name": data.get("name"),
                "systemPrompt": data.get("systemPrompt"),
                "createdAt": created_at,
                "userId": data.get("userId")
            }
            result.append(project_dict)
            print(f"  ✓ Project: {project_dict['name']} (ID: {project.id})")
        
        # Sort in Python (newest first)
        result.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        
        print(f"✅ Returning {len(result)} projects")
        return {"projects": result}
        
    except Exception as e:
        print(f"❌ Error in list_projects: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, user_id: str = Depends(verify_token)):
    """Get a specific project by ID"""
    try:
        project_ref = config.db.collection("projects").document(project_id).get()
        
        if not project_ref.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_data = project_ref.to_dict()
        
        # Verify ownership
        if project_data.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        # Convert Timestamp to string
        project_data["createdAt"] = serialize_timestamp(project_data.get("createdAt"))
        
        return {
            "id": project_id,
            **project_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, user_id: str = Depends(verify_token)):
    """Delete a project"""
    try:
        project_ref = config.db.collection("projects").document(project_id)
        project = project_ref.get()
        
        if not project.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.to_dict().get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        # Delete all messages in subcollection
        messages = config.db.collection("projects").document(project_id).collection("messages").stream()
        for msg in messages:
            msg.reference.delete()
        
        # Delete project
        project_ref.delete()
        
        print(f"✅ Deleted project {project_id}")
        return {"success": True, "message": "Project deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# CHAT

async def call_openrouter_llm(messages: List[dict]) -> str:
    """Call OpenRouter API for LLM completion"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct",  # Free tier model
                    "messages": messages
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"LLM API error: {response.text}"
                )
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="LLM request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

@app.post("/api/chat/{project_id}")
async def chat(project_id: str, chat_msg: ChatMessage, user_id: str = Depends(verify_token)):
    """Send a chat message and get LLM response"""
    try:
        # 1. Verify project ownership
        project_ref = config.db.collection("projects").document(project_id).get()
        
        if not project_ref.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_data = project_ref.to_dict()
        
        if project_data.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        # 2. Get chat history
        chat_history_ref = config.db.collection("projects").document(project_id)\
            .collection("messages").order_by("timestamp").limit(20)
        
        messages = [{"role": "system", "content": project_data.get("systemPrompt", "")}]
        
        for msg in chat_history_ref.stream():
            msg_data = msg.to_dict()
            messages.append({
                "role": msg_data.get("role"),
                "content": msg_data.get("content")
            })
        
        # 3. Add user message
        messages.append({"role": "user", "content": chat_msg.message})
        
        # 4. Call LLM
        print(f"💬 Calling LLM for project {project_id}")
        assistant_response = await call_openrouter_llm(messages)
        
        # 5. Save user message
        config.db.collection("projects").document(project_id)\
            .collection("messages").add({
                "role": "user",
                "content": chat_msg.message,
                "timestamp": datetime.utcnow()
            })
        
        # 6. Save assistant response
        config.db.collection("projects").document(project_id)\
            .collection("messages").add({
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.utcnow()
            })
        
        print(f"✅ Chat completed for project {project_id}")
        
        return {
            "success": True,
            "response": assistant_response
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/{project_id}/history")
async def get_chat_history(project_id: str, user_id: str = Depends(verify_token)):
    """Get chat history for a project"""
    try:
        # Verify ownership
        project_ref = config.db.collection("projects").document(project_id).get()
        
        if not project_ref.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project_ref.to_dict().get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        # Get messages
        messages = config.db.collection("projects").document(project_id)\
            .collection("messages").order_by("timestamp").stream()
        
        history = []
        for msg in messages:
            msg_data = msg.to_dict()
            
            # Convert timestamp to string
            timestamp = serialize_timestamp(msg_data.get("timestamp"))
            
            history.append({
                "role": msg_data.get("role"),
                "content": msg_data.get("content"),
                "timestamp": timestamp
            })
        
        print(f"✅ Returning {len(history)} messages for project {project_id}")
        return {"history": history}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# FILE UPLOAD (BONUS)

@app.post("/api/projects/{project_id}/files")
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(verify_token)
):
    try:
        # Verify project ownership
        project_ref = config.db.collection("projects").document(project_id)
        project_doc = project_ref.get()

        if not project_doc.exists:
            raise HTTPException(status_code=404, detail="Project not found")

        if project_doc.to_dict()["userId"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Read file
        content = await file.read()
        file_size = len(content)

        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # Convert to base64
        content_b64 = base64.b64encode(content).decode("utf-8")

        file_ref = config.db.collection("files").document()

        file_ref.set({
            "projectId": project_id,
            "userId": user_id,
            "filename": file.filename,
            "contentType": file.content_type,
            "size": file_size,
            "contentBase64": content_b64,
            "uploadedAt": get_timestamp()
        })

        print(f"✅ Uploaded file {file.filename} to project {project_id}")

        return {
            "success": True,
            "fileId": file_ref.id,
            "filename": file.filename,
            "size": file_size,
            "contentType": file.content_type
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@app.get("/api/projects/{project_id}/files")
async def list_files(
    project_id: str,
    user_id: str = Depends(verify_token)
):
    try:
        project_ref = config.db.collection("projects").document(project_id)
        project_doc = project_ref.get()

        if not project_doc.exists:
            raise HTTPException(status_code=404, detail="Project not found")

        if project_doc.to_dict()["userId"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        files_query = config.db.collection("files")\
            .where("projectId", "==", project_id)\
            .where("userId", "==", user_id)

        files = []
        for doc in files_query.stream():
            data = doc.to_dict()
            data.pop("contentBase64", None)  # Don't send base64 in list
            data["fileId"] = doc.id
            data["uploadedAt"] = serialize_timestamp(data.get("uploadedAt"))
            files.append(data)

        return {
            "projectId": project_id,
            "count": len(files),
            "files": files
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch files: {str(e)}")

@app.delete("/api/projects/{project_id}/files/{file_id}")
async def delete_file(
    project_id: str,
    file_id: str,
    user_id: str = Depends(verify_token)
):
    try:
        project_ref = config.db.collection("projects").document(project_id)
        project_doc = project_ref.get()

        if not project_doc.exists:
            raise HTTPException(status_code=404, detail="Project not found")

        if project_doc.to_dict()["userId"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        file_ref = config.db.collection("files").document(file_id)
        file_doc = file_ref.get()

        if not file_doc.exists:
            raise HTTPException(status_code=404, detail="File not found")

        if file_doc.to_dict()["projectId"] != project_id:
            raise HTTPException(status_code=400, detail="File does not belong to project")

        file_ref.delete()

        return {
            "success": True,
            "fileId": file_id,
            "message": "File deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# HEALTH CHECK

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Chatbot Platform API",
        "version": "1.0.0"
    }

@app.get("/api/health")
async def health_check():
    try:
        # Firestore check
        try:
            config.db.collection("_health").limit(1).get()
            firestore_status = "connected"
        except Exception as e:
            firestore_status = f"error: {str(e)}"

        llm_status = "configured" if config.OPENROUTER_API_KEY else "not_configured"

        return {
            "status": "healthy",
            "timestamp": get_timestamp().isoformat(),
            "services": {
                "api": "online",
                "firestore": firestore_status,
                "llm": llm_status,
                "auth": "firebase"
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": get_timestamp().isoformat()
        }

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "path": str(request.url)
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "timestamp": get_timestamp().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)