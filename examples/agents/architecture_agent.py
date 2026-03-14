"""
ArchitectureAgent — stage 1 of the example pipeline.

Input : {"feature": "<plain-text feature description>"}
Output: {
    "feature": str,
    "entities": list[str],
    "components": list[str],
    "models": list[{"name": str, "fields": list[str]}],
    "routes": list[{"method": str, "path": str, "handler": str, "level": int}],
    "security_concerns": list[str],
}

No LLM required — derives structure from keyword matching.
Replace _extract_entities() and route generation with LLM calls in v3.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.base import AgentTask, BaseAgent
from src.agents.registry import register

# ---------------------------------------------------------------------------
# Keyword maps
# ---------------------------------------------------------------------------

# Maps lowercase words/phrases → canonical entity names
_ENTITY_MAP: dict[str, str] = {
    "user": "User",       "users": "User",
    "auth": "Auth",       "authentication": "Auth",  "login": "Auth",
    "token": "Token",     "jwt": "Token",
    "session": "Session", "sessions": "Session",
    "role": "Role",       "roles": "Role",
    "permission": "Permission", "permissions": "Permission",
    "product": "Product", "products": "Product",     "item": "Product",
    "order": "Order",     "orders": "Order",
    "payment": "Payment", "payments": "Payment",
    "invoice": "Invoice", "invoices": "Invoice",
    "customer": "Customer", "customers": "Customer",
    "profile": "Profile", "profiles": "Profile",
    "post": "Post",       "posts": "Post",           "article": "Post",
    "comment": "Comment", "comments": "Comment",
    "category": "Category", "categories": "Category",
    "tag": "Tag",         "tags": "Tag",
    "file": "File",       "upload": "Upload",        "uploads": "Upload",
    "notification": "Notification",
    "message": "Message", "messages": "Message",
    "report": "Report",   "reports": "Report",
    "search": "Search",   "analytics": "Analytics",
}

# Maps keywords → human-readable security concern
_SECURITY_MAP: dict[str, str] = {
    "password":   "Password hashing required (bcrypt / argon2)",
    "auth":       "Authentication flow — validate credentials, issue tokens",
    "jwt":        "JWT signing key rotation and expiry policy",
    "token":      "Token revocation list and expiry enforcement",
    "role":       "RBAC — least-privilege enforcement per endpoint",
    "permission": "Permission boundary validation on every write",
    "payment":    "PCI compliance — never log raw card data",
    "api":        "Rate limiting and input validation on all endpoints",
    "file":       "File type and size validation before storage",
    "upload":     "Malware scanning on uploaded files",
    "email":      "Email address validation; prevent header injection",
    "admin":      "Admin endpoints require elevated-privilege check",
    "delete":     "Soft-delete preferred; hard-delete requires Level-3 approval",
}

# Default field sets per entity; used by BackendAgent code generator
_DEFAULT_FIELDS: dict[str, list[str]] = {
    "User":         ["id: str", "email: str", "password_hash: str",
                     "created_at: datetime", "updated_at: Optional[datetime]"],
    "Auth":         ["user_id: str", "access_token: str", "refresh_token: str",
                     "expires_at: datetime"],
    "Token":        ["value: str", "user_id: str", "expires_at: datetime",
                     "revoked: bool"],
    "Session":      ["id: str", "user_id: str", "ip_address: str",
                     "created_at: datetime", "expires_at: datetime"],
    "Role":         ["id: str", "name: str", "permissions: list[str]"],
    "Permission":   ["id: str", "name: str", "resource: str", "action: str"],
    "Product":      ["id: str", "name: str", "description: str",
                     "price: float", "stock: int"],
    "Order":        ["id: str", "user_id: str", "items: list[dict]",
                     "total: float", "status: str", "created_at: datetime"],
    "Payment":      ["id: str", "order_id: str", "amount: float",
                     "currency: str", "status: str",
                     "processed_at: Optional[datetime]"],
    "Invoice":      ["id: str", "order_id: str", "amount: float",
                     "issued_at: datetime", "due_at: datetime"],
    "Customer":     ["id: str", "name: str", "email: str", "phone: Optional[str]"],
    "Profile":      ["user_id: str", "display_name: str", "bio: str",
                     "avatar_url: Optional[str]"],
    "Post":         ["id: str", "author_id: str", "title: str", "body: str",
                     "published: bool", "created_at: datetime"],
    "Comment":      ["id: str", "post_id: str", "author_id: str",
                     "body: str", "created_at: datetime"],
    "Category":     ["id: str", "name: str", "slug: str",
                     "parent_id: Optional[str]"],
    "Tag":          ["id: str", "name: str", "slug: str"],
    "File":         ["id: str", "owner_id: str", "filename: str",
                     "size_bytes: int", "mime_type: str", "url: str",
                     "uploaded_at: datetime"],
    "Upload":       ["id: str", "owner_id: str", "filename: str",
                     "size_bytes: int", "status: str"],
    "Notification": ["id: str", "user_id: str", "kind: str",
                     "message: str", "read: bool", "created_at: datetime"],
    "Message":      ["id: str", "sender_id: str", "recipient_id: str",
                     "body: str", "sent_at: datetime", "read: bool"],
    "Report":       ["id: str", "author_id: str", "title: str",
                     "content: dict", "generated_at: datetime"],
    "Search":       ["query: str", "filters: dict", "results: list[dict]",
                     "total: int"],
    "Analytics":    ["event: str", "user_id: Optional[str]",
                     "metadata: dict", "occurred_at: datetime"],
}

_FALLBACK_FIELDS = ["id: str", "name: str", "created_at: datetime",
                    "updated_at: Optional[datetime]"]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@register
class ArchitectureAgent(BaseAgent):
    """
    Derives a structured architecture plan from a plain-text feature description.
    Stage 1 of 3 in the example pipeline.
    """

    name = "architecture-agent"
    allowed_tools = ["read_spec"]

    def execute(self, task: AgentTask) -> dict[str, Any]:
        feature: str = task.input.get("feature", "")
        if not feature.strip():
            raise ValueError("Input 'feature' must be a non-empty string.")

        entities = self._extract_entities(feature)
        if not entities:
            entities = ["Resource"]          # safe fallback

        models = [
            {"name": e, "fields": _DEFAULT_FIELDS.get(e, _FALLBACK_FIELDS)}
            for e in entities
        ]
        components = self._derive_components(entities)
        routes = self._derive_routes(entities)
        security_concerns = self._identify_security_concerns(feature)

        return {
            "feature": feature,
            "entities": entities,
            "components": components,
            "models": models,
            "routes": routes,
            "security_concerns": security_concerns,
        }

    # ------------------------------------------------------------------

    def _extract_entities(self, text: str) -> list[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        seen: dict[str, int] = {}   # entity → order of first appearance
        for word in words:
            entity = _ENTITY_MAP.get(word)
            if entity and entity not in seen:
                seen[entity] = len(seen)
        return sorted(seen, key=lambda e: seen[e])

    def _derive_components(self, entities: list[str]) -> list[str]:
        components: list[str] = []
        for entity in entities:
            components.append(f"{entity}Service")
            components.append(f"{entity}Repository")
        return components

    def _derive_routes(self, entities: list[str]) -> list[dict]:
        routes: list[dict] = []
        for entity in entities:
            resource = entity.lower() + "s"
            entity_l = entity.lower()
            routes.extend([
                {"method": "GET",    "path": f"/{resource}",
                 "handler": f"list_{entity_l}s",   "security_level": 1},
                {"method": "POST",   "path": f"/{resource}",
                 "handler": f"create_{entity_l}",  "security_level": 2},
                {"method": "GET",    "path": f"/{resource}/{{id}}",
                 "handler": f"get_{entity_l}",     "security_level": 1},
                {"method": "PUT",    "path": f"/{resource}/{{id}}",
                 "handler": f"update_{entity_l}",  "security_level": 2},
                {"method": "DELETE", "path": f"/{resource}/{{id}}",
                 "handler": f"delete_{entity_l}",  "security_level": 3},
            ])
        return routes

    def _identify_security_concerns(self, text: str) -> list[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        seen: set[str] = set()
        concerns: list[str] = []
        for word in words:
            concern = _SECURITY_MAP.get(word)
            if concern and concern not in seen:
                seen.add(concern)
                concerns.append(concern)
        return concerns
