"""Conexión compartida a Redis (cacheada para Streamlit)."""
import redis

from src.config import REDIS_HOST, REDIS_PORT

_cliente = None


def get_redis():
    """Cliente único con timeouts, para que la app no se cuelgue si Redis está caído."""
    global _cliente
    if _cliente is None:
        _cliente = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=10,
        )
    return _cliente
