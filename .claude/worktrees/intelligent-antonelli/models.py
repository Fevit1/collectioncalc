"""
Slab Worthy — Model Configuration with Fallback

Centralizes all Anthropic model names. If a model returns 404,
the wrapper automatically tries the next fallback in the chain.
Update this file when Anthropic releases or deprecates models.

Last verified: 2026-03-14

Usage:
    from models import get_model, SONNET, HAIKU, OPUS

    # Simple — get current best model for a tier
    model = get_model('sonnet')

    # Or use constants directly
    model = SONNET  # returns current active model string
"""

MODEL_CHAINS = {
    'haiku': [
        'claude-3-5-haiku-latest',
        'claude-3-5-haiku-20241022',
    ],
    'sonnet': [
        'claude-sonnet-4-20250514',
        'claude-sonnet-4-latest',
        'claude-3-5-sonnet-latest',
    ],
    'sonnet-new': [
        'claude-sonnet-4-5-20250929',
        'claude-sonnet-4-20250514',
        'claude-sonnet-4-latest',
    ],
    'opus': [
        'claude-opus-4-6',
        'claude-opus-4-latest',
    ],
}

# Track which model in each chain is currently working
_active_index = {tier: 0 for tier in MODEL_CHAINS}


def get_model(tier):
    """Get the current active model name for a tier."""
    chain = MODEL_CHAINS.get(tier)
    if not chain:
        raise ValueError(f"Unknown model tier: {tier}")
    idx = _active_index.get(tier, 0)
    return chain[min(idx, len(chain) - 1)]


def advance_fallback(tier):
    """Advance to the next fallback model for a tier. Returns the new model name or None if exhausted."""
    chain = MODEL_CHAINS.get(tier)
    if not chain:
        return None
    current = _active_index.get(tier, 0)
    next_idx = current + 1
    if next_idx >= len(chain):
        return None
    _active_index[tier] = next_idx
    old_model = chain[current]
    new_model = chain[next_idx]
    print(f"[Models] {tier} tier falling back: {old_model} → {new_model}")
    return new_model


def call_with_fallback(client, tier, **kwargs):
    """
    Call Anthropic API with automatic model fallback on 404/not_found.

    Args:
        client: Anthropic client instance
        tier: Model tier ('haiku', 'sonnet', 'sonnet-new', 'opus')
        **kwargs: Arguments passed to client.messages.create() (excluding 'model')

    Returns:
        Anthropic API response

    Raises:
        Last error if all fallbacks exhausted
    """
    import anthropic

    chain = MODEL_CHAINS.get(tier, [])
    start_idx = _active_index.get(tier, 0)
    last_error = None

    for i in range(start_idx, len(chain)):
        model = chain[i]
        try:
            response = client.messages.create(model=model, **kwargs)
            if i != start_idx:
                print(f"[Models] {tier} tier now using: {model}")
            return response
        except anthropic.NotFoundError as e:
            if 'model' in str(e).lower():
                print(f"[Models] {model} returned 404 — trying next fallback")
                _active_index[tier] = i + 1
                last_error = e
                continue
            raise

    raise last_error or ValueError(f"All {tier} fallbacks exhausted: {chain}")


# Convenience constants — these are properties that resolve at call time
class _ModelProxy:
    def __init__(self, tier):
        self._tier = tier
    def __str__(self):
        return get_model(self._tier)
    def __repr__(self):
        return get_model(self._tier)
    def __eq__(self, other):
        return str(self) == str(other)


HAIKU = get_model('haiku')
SONNET = get_model('sonnet')
SONNET_NEW = get_model('sonnet-new')
OPUS = get_model('opus')
