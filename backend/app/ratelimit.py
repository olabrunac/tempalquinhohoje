"""Rate limiting em memória por IP.

Objetivo: travar força bruta no admin e spam em POST /suggestions.

Limitações (consciente): o backend roda como função serverless na Vercel, então
este estado vive na memória de uma instância e morre no cold start / pode não ser
compartilhado entre instâncias. Isso é suficiente para ataques pequenos e bots
(que fazem request após request na mesma instância), mas não é um limitador
distribuído. Se um dia precisar de garantia real, o próximo passo é persistir as
tentativas no Postgres/Neon (tabela `login_attempt`) ou pôr um limitador na borda
(Vercel WAF / Cloudflare).
"""

import threading
import time
from collections import defaultdict, deque

# (chave, limite, janela em segundos)
Rule = tuple[str, int, float]


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        # teto de chaves guardadas, evita crescimento sem limite em memória
        self._max_keys = 10_000

    def _prune(self, now: float) -> None:
        """Remove entradas expiradas e descarta as mais antigas se passar do teto."""
        cutoff = now - 3600
        stale = [k for k, ts in self._hits.items() if not ts or ts[-1] < cutoff]
        for k in stale:
            self._hits.pop(k, None)
        if len(self._hits) > self._max_keys:
            # descarta as chaves com evento mais antigo
            oldest = sorted(self._hits.items(), key=lambda kv: kv[1][-1] if kv[1] else 0)
            for k, _ in oldest[: len(self._hits) - self._max_keys]:
                self._hits.pop(k, None)

    def check(self, key: str, limit: int, window: float) -> tuple[bool, int, float]:
        """Registra um hit e diz se passou.

        Returns (allowed, remaining, retry_after_seconds).
        """
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            bucket = self._hits[key]
            cutoff = now - window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(0.0, bucket[0] + window - now)
                return False, 0, retry_after
            bucket.append(now)
            return True, limit - len(bucket), 0.0

    def reset(self, key: str) -> None:
        """Limpa o contador (usado após login bem-sucedido)."""
        with self._lock:
            self._hits.pop(key, None)


# regras: chave lógica -> (limite, janela em segundos)
ADMIN_RULES: dict[str, Rule] = {
    # 10 tentativas de login erradas por IP a cada 5 min
    "admin_auth": ("admin_auth", 10, 300.0),
}
SUGGESTION_RULES: dict[str, Rule] = {
    # 5 sugestões por IP por hora
    "suggest": ("suggest", 5, 3600.0),
}

limiter = RateLimiter()


def client_ip(request) -> str:
    """IP do cliente, priorizando o header que a Vercel preenche."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # cadeia "a, b, c" -> o primeiro é o cliente original
        return forwarded.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real.strip()
    # fallback: melhor esforço (não é confiável atrás de proxy, mas evita 'shared')
    return request.client.host if request.client else "unknown"