"""3-state circuit breaker (CLOSED / OPEN / HALF_OPEN) per key."""
import logging
import time
from enum import Enum

from config import config
from agent import store

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def _fail_threshold() -> int:
    return getattr(config, "circuit_fail_threshold", 5)


def _cooldown_s() -> int:
    return getattr(config, "circuit_cooldown_s", 30)


_cache = {}


def _memory_cache():
    return _cache


def get_state(key: str) -> CircuitState:
    cache = _memory_cache()
    if key in cache:
        row = cache[key]
    else:
        row = store.get_circuit_state(key)
        if row:
            cache[key] = row

    if not row:
        return CircuitState.CLOSED

    state = row.get("state", "closed")
    if state == CircuitState.OPEN.value:
        opened = row.get("opened_at") or 0
        if time.time() - float(opened) >= _cooldown_s():
            _set_state(key, CircuitState.HALF_OPEN, row.get("fail_count", 0))
            return CircuitState.HALF_OPEN
    return CircuitState(state)


def _set_state(key: str, state: CircuitState, fail_count: int = 0):
    opened = time.time() if state == CircuitState.OPEN else None
    store.upsert_circuit_state(key, state.value, fail_count, opened)
    _memory_cache()[key] = {
        "key": key, "state": state.value, "fail_count": fail_count, "opened_at": opened,
    }


def is_open(key: str) -> bool:
    s = get_state(key)
    return s == CircuitState.OPEN


def record_success(key: str):
    _set_state(key, CircuitState.CLOSED, 0)


def record_failure(key: str):
    cache = _memory_cache()
    row = cache.get(key) or store.get_circuit_state(key) or {"fail_count": 0}
    fc = int(row.get("fail_count", 0)) + 1
    state = get_state(key)

    if state == CircuitState.HALF_OPEN:
        _set_state(key, CircuitState.OPEN, fc)
        logger.warning(f"[healing/circuit] {key} half-open probe failed -> OPEN")
        return

    if fc >= _fail_threshold():
        _set_state(key, CircuitState.OPEN, fc)
        logger.warning(f"[healing/circuit] {key} threshold reached -> OPEN ({fc} failures)")
    else:
        _set_state(key, CircuitState.CLOSED, fc)


def allow_call(key: str) -> bool:
    """Return False if circuit is OPEN (fast-fail). HALF_OPEN allows one probe."""
    state = get_state(key)
    if state == CircuitState.OPEN:
        return False
    return True


def all_circuits() -> list:
    return store.list_circuit_states()
