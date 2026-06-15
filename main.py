"""
FastAPI Gateway - Entry point for all frontend requests.
Proxies auth and CRUD operations to Spring Boot backend.
Provides its own lightweight endpoints for component metadata.
"""

import jwt
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SPRING_BOOT_URL = "http://localhost:9090"
NODE_BACKEND_URL = "http://localhost:5000"
JWT_SECRET = "MySuperSecretKeyForJWTTokenGeneration2026SpringBootApp!@#$"
JWT_ALGORITHM = "HS384"

app = FastAPI(title="Modular Component Showcase - API Gateway")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# HTTP Clients
# ---------------------------------------------------------------------------
spring_client = httpx.AsyncClient(
    base_url=SPRING_BOOT_URL,
    timeout=30.0
)

node_client = httpx.AsyncClient(
    base_url=NODE_BACKEND_URL,
    timeout=30.0
)

# ---------------------------------------------------------------------------
# JWT Helper
# ---------------------------------------------------------------------------
def decode_token(authorization: str | None):

    print("\n========== JWT DEBUG ==========")

    if not authorization:
        print("Authorization header missing")
        return None

    print("AUTH HEADER:", authorization)

    if not authorization.startswith("Bearer "):
        print("Bearer prefix missing")
        return None

    token = authorization[7:]

    print("TOKEN:", token)

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        print("JWT VALID")
        print("PAYLOAD:", payload)

        return payload

    except Exception as e:
        print("JWT ERROR:", str(e))
        return None


# ---------------------------------------------------------------------------
# Request Proxy
# ---------------------------------------------------------------------------
async def proxy_request(
    method: str,
    path: str,
    request: Request,
    auth_required: bool = False,
    client: httpx.AsyncClient | None = None,
) -> JSONResponse:
    print("\n===== REQUEST DEBUG =====")
    print("PATH:", path)
    print("AUTH REQUIRED:", auth_required)
    print("AUTH HEADER:", request.headers.get("Authorization"))
    # JWT validation if needed
    if auth_required:
        payload = decode_token(
            request.headers.get("Authorization")
        )

        if payload is None:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized"
            )

    # Forward important headers
    headers = {}

    content_type = request.headers.get("Content-Type")
    if content_type:
        headers["Content-Type"] = content_type

    authorization = request.headers.get("Authorization")
    if authorization:
        headers["Authorization"] = authorization

    # Read body
    body = None

    if method in ["POST", "PUT", "PATCH"]:
        body = await request.body()

    # Use provided client or default to Spring Boot client
    http_client = client or spring_client

    try:
        response = await http_client.request(
            method=method,
            url=path,
            headers=headers,
            content=body,
        )

        response_content_type = response.headers.get(
            "content-type",
            ""
        )

        if "application/json" in response_content_type:
            return JSONResponse(
                status_code=response.status_code,
                content=response.json(),
            )

        return JSONResponse(
            status_code=response.status_code,
            content={"text": response.text},
        )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Backend service unavailable: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "name": "Modular Component Showcase - API Gateway",
        "version": "1.0.0",
        "status": "running",
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():

    spring_ok = False
    node_ok = False

    try:
        r = await spring_client.get("/api/auth/health")
        spring_ok = r.status_code == 200
    except Exception:
        pass

    try:
        r = await node_client.get("/api/health")
        node_ok = r.status_code == 200
    except Exception:
        pass

    return {
        "gateway": "ok",
        "spring_boot": "ok" if spring_ok else "unreachable",
        "node_backend": "ok" if node_ok else "unreachable",
        "timestamp": __import__(
            "datetime"
        ).datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Auth APIs
# ---------------------------------------------------------------------------
@app.post("/api/auth/signup")
async def signup(request: Request):
    return await proxy_request(
        "POST",
        "/api/auth/signup",
        request
    )


@app.post("/api/auth/login")
async def login(request: Request):
    return await proxy_request(
        "POST",
        "/api/auth/login",
        request
    )


@app.get("/api/auth/users")
async def get_users(request: Request):
    return await proxy_request(
        "GET",
        "/api/auth/users",
        request,
        auth_required=True
    )


@app.delete("/api/auth/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request
):
    return await proxy_request(
        "DELETE",
        f"/api/auth/users/{user_id}",
        request,
        auth_required=True
    )


@app.get("/api/auth/health")
async def auth_health(request: Request):
    return await proxy_request(
        "GET",
        "/api/auth/health",
        request
    )


# ---------------------------------------------------------------------------
# Components APIs
# ---------------------------------------------------------------------------
@app.get("/api/components")
async def get_components(request: Request):
    return await proxy_request(
        "GET",
        "/api/components",
        request
    )


@app.get("/api/components/{component_id}")
async def get_component(
    component_id: int,
    request: Request
):
    return await proxy_request(
        "GET",
        f"/api/components/{component_id}",
        request
    )


@app.post("/api/components")
async def create_component(request: Request):
    return await proxy_request(
        "POST",
        "/api/components",
        request,
        auth_required=True
    )


@app.put("/api/components/{component_id}")
async def update_component(
    component_id: int,
    request: Request
):
    return await proxy_request(
        "PUT",
        f"/api/components/{component_id}",
        request,
        auth_required=True
    )


@app.delete("/api/components/{component_id}")
async def delete_component(
    component_id: int,
    request: Request
):
    return await proxy_request(
        "DELETE",
        f"/api/components/{component_id}",
        request,
        auth_required=True
    )


# ---------------------------------------------------------------------------
# MongoDB Component APIs (proxied to Node.js backend → MongoDB)
# ---------------------------------------------------------------------------
@app.get("/api/mongo/components")
async def get_mongo_components(request: Request):
    return await proxy_request(
        "GET",
        "/api/mongo/components",
        request,
        client=node_client,
    )


@app.get("/api/mongo/components/{component_id}")
async def get_mongo_component(
    component_id: str,
    request: Request,
):
    return await proxy_request(
        "GET",
        f"/api/mongo/components/{component_id}",
        request,
        client=node_client,
    )


@app.post("/api/mongo/components")
async def create_mongo_component(request: Request):
    return await proxy_request(
        "POST",
        "/api/mongo/components",
        request,
        auth_required=True,
        client=node_client,
    )


@app.put("/api/mongo/components/{component_id}")
async def update_mongo_component(
    component_id: str,
    request: Request,
):
    return await proxy_request(
        "PUT",
        f"/api/mongo/components/{component_id}",
        request,
        auth_required=True,
        client=node_client,
    )


@app.delete("/api/mongo/components/{component_id}")
async def delete_mongo_component(
    component_id: str,
    request: Request,
):
    return await proxy_request(
        "DELETE",
        f"/api/mongo/components/{component_id}",
        request,
        auth_required=True,
        client=node_client,
    )


# ---------------------------------------------------------------------------
# Legacy Endpoint
# ---------------------------------------------------------------------------
@app.get("/components")
def static_components():
    return {
        "components": [
            "Navbar",
            "Sidebar",
            "Button",
            "Card",
            "Modal",
            "DataTable",
            "Form",
            "Badge",
            "Alert",
            "Spinner",
        ]
    }

@app.get("/test")
def test():
    print("TEST ROUTE HIT")
    return {"message": "working"}
@app.get("/debug-token")
async def debug_token(request: Request):
    return {
        "authorization": request.headers.get("Authorization")
    }
# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------
@app.on_event("shutdown")
async def shutdown():
    await spring_client.aclose()
    await node_client.aclose()