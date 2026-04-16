from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from ia.models import AgentMemoryItem, MemoryScope


class MemoryService:
    """Recuperación simple de memoria persistente hasta incorporar indexación semántica."""

    @staticmethod
    def get_relevant_memory(agent, policy_context, query: str, limit: int = 5):
        now = timezone.now()
        base_qs = AgentMemoryItem.objects.filter(
            agent=agent,
            is_active=True,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

        if policy_context.empresa:
            base_qs = base_qs.filter(Q(empresa__isnull=True) | Q(empresa=policy_context.empresa))
        else:
            base_qs = base_qs.filter(empresa__isnull=True)

        owner_filters = Q(scope=MemoryScope.AGENT) | Q(scope=MemoryScope.TENANT)
        if policy_context.owner_user:
            owner_filters |= Q(scope=MemoryScope.USER, owner_user=policy_context.owner_user)
        if policy_context.legacy_user_id:
            owner_filters |= Q(scope=MemoryScope.USER, owner_legacy_user_id=policy_context.legacy_user_id)

        filtered_qs = base_qs.filter(owner_filters)

        query = (query or "").strip()
        if query:
            terms = [term for term in query.split() if len(term) >= 3][:6]
            if terms:
                text_q = Q()
                for term in terms:
                    text_q |= Q(content__icontains=term) | Q(key__icontains=term) | Q(source_summary__icontains=term)
                filtered_qs = filtered_qs.filter(text_q)

        items = list(filtered_qs.order_by("-is_confirmed", "-confidence", "-updated_at")[:limit])
        if items:
            AgentMemoryItem.objects.filter(id__in=[item.id for item in items]).update(last_accessed_at=now)
        return items

    @staticmethod
    def propose_memory_write(
        *,
        agent,
        conversation,
        policy_context,
        content: str,
        memory_type: str = "episodic",
        scope: str = "user",
        key: str = "",
        source_summary: str = "",
        confidence=0.50,
        metadata: dict | None = None,
    ):
        return AgentMemoryItem.objects.create(
            agent=agent,
            empresa=policy_context.empresa,
            conversation=conversation,
            owner_user=policy_context.owner_user,
            owner_legacy_user_id=policy_context.legacy_user_id,
            owner_legacy_user_code=policy_context.legacy_user_code,
            scope=scope,
            memory_type=memory_type,
            key=key,
            content=content,
            source_summary=source_summary,
            confidence=confidence,
            is_confirmed=False,
            metadata=metadata or {},
        )
