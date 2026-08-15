from fastapi import HTTPException, Request


def delegated_tenant(request: Request) -> str:
    tenant_id = request.headers.get("x-viewsense-tenant", "").strip()
    if not tenant_id or len(tenant_id) > 128:
        raise HTTPException(status_code=400, detail="valid X-ViewSense-Tenant header required")
    request.state.tenant_id = tenant_id
    return tenant_id
