from __future__ import annotations

import requests


class LlmGatewayError(Exception):
    pass


class LlmGatewayService:
    DEFAULT_TIMEOUT_SECONDS = 45

    @classmethod
    def generate_text(
        cls,
        *,
        provider_config,
        model_name: str,
        system_prompt: str,
        user_message: str,
        memories: list,
        max_output_tokens: int = 1000,
        temperature: float = 0.2,
    ) -> dict:
        if not provider_config or not provider_config.is_active:
            raise LlmGatewayError("Proveedor IA no configurado o inactivo.")
        api_key = provider_config.get_api_key()
        if not api_key:
            raise LlmGatewayError("El proveedor IA no tiene API key configurada.")
        if not model_name:
            raise LlmGatewayError("No hay modelo configurado para el agente.")

        if provider_config.provider_kind in ("openai", "openai_compatible"):
            return cls._call_openai_compatible(
                provider_config=provider_config,
                api_key=api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_message=user_message,
                memories=memories,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            )
        if provider_config.provider_kind == "anthropic":
            return cls._call_anthropic(
                provider_config=provider_config,
                api_key=api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_message=user_message,
                memories=memories,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            )
        raise LlmGatewayError(f"Tipo de proveedor no soportado: {provider_config.provider_kind}")

    @staticmethod
    def _openai_chat_completion_token_key(model_name: str) -> str:
        """
        Chat Completions: modelos recientes (p. ej. familia gpt-5) usan max_completion_tokens;
        el resto suele aceptar max_tokens.
        """
        n = (model_name or "").strip().lower()
        if n.startswith("gpt-5"):
            return "max_completion_tokens"
        if n.startswith(("o1", "o3", "o4")):
            return "max_completion_tokens"
        return "max_tokens"

    @classmethod
    def _call_openai_compatible(
        cls,
        *,
        provider_config,
        api_key: str,
        model_name: str,
        system_prompt: str,
        user_message: str,
        memories: list,
        max_output_tokens: int,
        temperature: float,
    ) -> dict:
        base_url = (provider_config.base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        memory_context = cls._build_memory_context(memories)
        system_content = system_prompt.strip()
        if memory_context:
            system_content = f"{system_content}\n\nContexto de memoria relevante:\n{memory_context}".strip()

        token_key = cls._openai_chat_completion_token_key(model_name)
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            token_key: max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider_config.organization_id:
            headers["OpenAI-Organization"] = provider_config.organization_id

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=cls.DEFAULT_TIMEOUT_SECONDS,
        )
        # Algunos modelos (p. ej. gpt-5.x) no aceptan max_tokens y exigen max_completion_tokens.
        if response.status_code == 400 and token_key == "max_tokens":
            err_snippet = (response.text or "")[:800].lower()
            if "max_completion_tokens" in err_snippet and "max_tokens" in err_snippet:
                payload = {k: v for k, v in payload.items() if k not in ("max_tokens", "max_completion_tokens")}
                payload["max_completion_tokens"] = max_output_tokens
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=cls.DEFAULT_TIMEOUT_SECONDS,
                )
        if response.status_code >= 400:
            raise LlmGatewayError(f"Error OpenAI/OpenAI-compatible: {response.status_code} {response.text[:400]}")

        data = response.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmGatewayError("Respuesta inválida del proveedor OpenAI-compatible.") from exc

        usage = data.get("usage") or {}
        return {
            "text": text or "",
            "raw": data,
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }

    @classmethod
    def _call_anthropic(
        cls,
        *,
        provider_config,
        api_key: str,
        model_name: str,
        system_prompt: str,
        user_message: str,
        memories: list,
        max_output_tokens: int,
        temperature: float,
    ) -> dict:
        base_url = (provider_config.base_url or "https://api.anthropic.com").rstrip("/")
        url = f"{base_url}/v1/messages"
        memory_context = cls._build_memory_context(memories)
        system_content = system_prompt.strip()
        if memory_context:
            system_content = f"{system_content}\n\nContexto de memoria relevante:\n{memory_context}".strip()

        payload = {
            "model": model_name,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "system": system_content,
            "messages": [
                {"role": "user", "content": user_message},
            ],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=cls.DEFAULT_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            raise LlmGatewayError(f"Error Anthropic: {response.status_code} {response.text[:400]}")
        data = response.json()
        try:
            text_blocks = [block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"]
            text = "\n".join([block for block in text_blocks if block]).strip()
        except Exception as exc:
            raise LlmGatewayError("Respuesta inválida del proveedor Anthropic.") from exc

        usage = data.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        return {
            "text": text,
            "raw": data,
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

    @staticmethod
    def _build_memory_context(memories: list) -> str:
        lines = []
        for memory in memories[:5]:
            prefix = f"[{memory.memory_type}]"
            key = f" {memory.key}:" if memory.key else ":"
            lines.append(f"{prefix}{key} {memory.content}")
        return "\n".join(lines)
