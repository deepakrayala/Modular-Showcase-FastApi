import os
import jwt
import httpx

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

SPRING_BOOT_URL = os.getenv(
    "SPRING_BOOT_URL",
    "https://modular-showcase-backend-springboot.onrender.com/"
)

NODE_BACKEND_URL = os.getenv(
    "NODE_BACKEND_URL",
    "https://modular-showcase-backend-node-js.onrender.com/"
)

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS384")

app = FastAPI(
    title="Modular Component Showcase - API Gateway",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

spring_client = httpx.AsyncClient(
    base_url=SPRING_BOOT_URL,
    timeout=30.0
)

node_client = httpx.AsyncClient(
    base_url=NODE_BACKEND_URL,
    timeout=30.0
)

def decode_token(authorization: str | None):
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]

    if not JWT_SECRET:
        return None

    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
    except Exception:
        return None

async def proxy_request(
    method: str,
    path: str,
    request: Request,
    auth_required: bool = False,
    client: httpx.AsyncClient | None = None,
) -> JSONResponse:

    authorization = request.headers.get("Authorization")

    if auth_required:
        payload = decode_token(authorization)

        if payload is None:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized"
            )

    headers = {}

    content_type = request.headers.get("Content-Type")

    if content_type:
        headers["Content-Type"] = content_type

    if authorization:
        headers["Authorization"] = authorization

    body = None

    if method in ["POST", "PUT", "PATCH"]:
        body = await request.body()

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
            try:
                return JSONResponse(
                    status_code=response.status_code,
                    content=response.json(),
                )
            except Exception:
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": response.text},
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

@app.get("/")
def root():
    return {
        "name": "Modular Component Showcase - API Gateway",
        "version": "1.0.0",
        "status": "running",
    }

@app.get("/health")
async def health():
    spring_ok = False
    node_ok = False

    try:
        response = await spring_client.get("/api/auth/health")
        spring_ok = response.status_code == 200
    except Exception:
        pass

    try:
        response = await node_client.get("/api/health")
        node_ok = response.status_code == 200
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

@app.get("/api/reviews")
async def get_reviews(request: Request):
    return await proxy_request(
        "GET",
        "/api/reviews",
        request,
        client=node_client,
    )

@app.get("/api/reviews/{review_id}")
async def get_review(
    review_id: str,
    request: Request,
):
    return await proxy_request(
        "GET",
        f"/api/reviews/{review_id}",
        request,
        client=node_client,
    )

@app.post("/api/reviews")
async def create_review(request: Request):
    return await proxy_request(
        "POST",
        "/api/reviews",
        request,
        auth_required=False,
        client=node_client,
    )

@app.put("/api/reviews/{review_id}")
async def update_review(
    review_id: str,
    request: Request,
):
    return await proxy_request(
        "PUT",
        f"/api/reviews/{review_id}",
        request,
        auth_required=True,
        client=node_client,
    )

@app.delete("/api/reviews/{review_id}")
async def delete_review(
    review_id: str,
    request: Request,
):
    return await proxy_request(
        "DELETE",
        f"/api/reviews/{review_id}",
        request,
        auth_required=True,
        client=node_client,
    )

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
    return {
        "message": "working"
    }

@app.get("/debug-token")
async def debug_token(request: Request):
    authorization = request.headers.get("Authorization")

    return {
        "authorization": "Present" if authorization else "Missing"
    }

@app.on_event("shutdown")
async def shutdown():
    await spring_client.aclose()
    await node_client.aclose()
