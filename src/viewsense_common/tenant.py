from fastapi import HTTPException, Request


def delegated_tenant(request: Request) -> str:
    if request.headers.get("x-viewsense-tenant") is not None:
        raise HTTPException(
            status_code=400,
            detail="unsigned tenant delegation header is prohibited",
        )
    envelope = getattr(request.state, "trust_envelope", None)
    tenant_id = getattr(envelope, "tenant_id", None)
    if not tenant_id or len(tenant_id) > 128:
        raise HTTPException(status_code=403, detail="signed tenant trust envelope required")
    return str(tenant_id)
