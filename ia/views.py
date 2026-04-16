from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q

from ia.forms import AgentConversationStartForm, AgentDefinitionConfigForm, LlmProviderConfigForm
from ia.models import AgentConversation, AgentDefinition, LlmProviderConfig
from ia.services.policy_gate import PolicyContext, PolicyGate


def _get_empresa(request):
    return getattr(request.user, "empresa_activa", None)


def _get_visible_agents(request):
    empresa = _get_empresa(request)
    agents = AgentDefinition.objects.filter(is_active=True)
    if empresa:
        agents = agents.filter(Q(empresa=empresa) | Q(empresa__isnull=True)).order_by("-empresa_id", "name")
    else:
        agents = agents.filter(empresa__isnull=True).order_by("name")

    deduped = {}
    for agent in agents:
        if agent.slug in deduped:
            continue
        if agent.required_permission and not PolicyGate.has_permission(request.user, agent.required_permission):
            continue
        deduped[agent.slug] = agent
    return list(deduped.values())


def _require_ia_admin(request):
    if not PolicyGate.has_permission(request.user, "ia.admin"):
        return HttpResponseForbidden("No tenés permisos para administrar IA.")
    return None


def _build_provider_forms(providers, *, override_key=None, override_form=None):
    forms = {str(provider.id): LlmProviderConfigForm(instance=provider) for provider in providers}
    forms["new"] = LlmProviderConfigForm()
    if override_form is not None and override_key is not None:
        forms[str(override_key)] = override_form
    return forms


def _build_agent_forms(agents, *, override_key=None, override_form=None):
    forms = {str(agent.id): AgentDefinitionConfigForm(instance=agent) for agent in agents}
    if override_form is not None and override_key is not None:
        forms[str(override_key)] = override_form
    return forms


def _conversation_belongs_to_request(conversation: AgentConversation, policy_context: PolicyContext) -> bool:
    if conversation.empresa_id and policy_context.empresa and conversation.empresa_id != policy_context.empresa.id:
        return False
    if conversation.owner_user_id and policy_context.owner_user:
        return conversation.owner_user_id == policy_context.owner_user.id
    if conversation.owner_legacy_user_id and policy_context.legacy_user_id:
        return conversation.owner_legacy_user_id == policy_context.legacy_user_id
    return conversation.owner_user_id is None and conversation.owner_legacy_user_id is None


@login_required
def ia_home(request):
    PolicyGate.ensure_authenticated(request)
    agents = _get_visible_agents(request)
    recent_conversations = AgentConversation.objects.none()
    context = PolicyGate.build_context(request)
    if context.owner_user:
        recent_conversations = AgentConversation.objects.filter(owner_user=context.owner_user).select_related("agent")[:10]
    elif context.legacy_user_id:
        recent_conversations = AgentConversation.objects.filter(owner_legacy_user_id=context.legacy_user_id).select_related("agent")[:10]

    return render(
        request,
        "ia/home.html",
        {
            "agents": agents,
            "recent_conversations": recent_conversations,
            "can_admin_ia": PolicyGate.has_permission(request.user, "ia.admin"),
        },
    )


@login_required
def ia_chat(request, slug):
    PolicyGate.ensure_authenticated(request)
    empresa = _get_empresa(request)
    queryset = AgentDefinition.objects.filter(slug=slug, is_active=True)
    if empresa:
        queryset = queryset.filter(Q(empresa=empresa) | Q(empresa__isnull=True)).order_by("-empresa_id")
    else:
        queryset = queryset.filter(empresa__isnull=True)
    agent = queryset.first()
    if not agent:
        raise Http404("Agente no encontrado.")
    context = PolicyGate.ensure_agent_access(request, agent)

    conversation = None
    conversation_uuid = request.GET.get("conversation")
    if conversation_uuid:
        conversation = get_object_or_404(
            AgentConversation.objects.select_related("agent").prefetch_related("messages"),
            conversation_uuid=conversation_uuid,
        )
        if not _conversation_belongs_to_request(conversation, context):
            raise Http404("Conversación no encontrada.")

    return render(
        request,
        "ia/chat.html",
        {
            "agent": agent,
            "conversation": conversation,
            "start_form": AgentConversationStartForm(),
        },
    )


@login_required
def ia_configuration(request):
    PolicyGate.ensure_authenticated(request)
    denial = _require_ia_admin(request)
    if denial:
        return denial

    providers = LlmProviderConfig.objects.order_by("name")
    agents = AgentDefinition.objects.order_by("name")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_provider":
            provider_id = request.POST.get("provider_id")
            provider = get_object_or_404(LlmProviderConfig, pk=provider_id) if provider_id else None
            form = LlmProviderConfigForm(request.POST, instance=provider)
            if form.is_valid():
                form.save()
                messages.success(request, "Proveedor IA guardado correctamente.")
                return redirect("ia:configuration")
            messages.error(request, "No se pudo guardar el proveedor IA.")
            provider_forms = _build_provider_forms(
                providers,
                override_key=(provider.id if provider else "new"),
                override_form=form,
            )
            agent_forms = _build_agent_forms(agents)
            return render(
                request,
                "ia/configuration.html",
                {"providers": providers, "agents": agents, "provider_forms": provider_forms, "agent_forms": agent_forms},
            )

        if action == "save_agent":
            agent = get_object_or_404(AgentDefinition, pk=request.POST.get("agent_id"))
            form = AgentDefinitionConfigForm(request.POST, instance=agent)
            if form.is_valid():
                form.save()
                messages.success(request, "Configuración del agente guardada correctamente.")
                return redirect("ia:configuration")
            messages.error(request, "No se pudo guardar la configuración del agente.")
            provider_forms = _build_provider_forms(providers)
            agent_forms = _build_agent_forms(agents, override_key=agent.id, override_form=form)
            return render(
                request,
                "ia/configuration.html",
                {"providers": providers, "agents": agents, "provider_forms": provider_forms, "agent_forms": agent_forms},
            )

    provider_forms = _build_provider_forms(providers)
    agent_forms = _build_agent_forms(agents)
    return render(
        request,
        "ia/configuration.html",
        {
            "providers": providers,
            "agents": agents,
            "provider_forms": provider_forms,
            "agent_forms": agent_forms,
        },
    )
