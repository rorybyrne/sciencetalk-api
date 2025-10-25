"""Test container builder with selective unmocking."""

from dishka import AsyncContainer, make_async_container

from talk.util.di import PROVIDERS, Component, get_provider


def build_test_container(unmock: set[Component] | None = None) -> AsyncContainer:
    """Build test container with selective unmocking.

    Assumes docker-compose services already running via `just local-up`.
    Settings are loaded from environment variables (set TEST=1 or similar for test config).

    Args:
        unmock: Components to use production implementations for.
                All others use mocks if available.

    Returns:
        Configured test container

    Raises:
        ValueError: If unknown components or dependency violations

    Examples:
        # Unit tests - all mocks
        container = build_test_container()

        # Integration tests - real persistence
        container = build_test_container(unmock={"persistence"})

        # E2E tests - all real
        container = build_test_container(unmock={"persistence", "bluesky"})
    """
    unmock = unmock or set()
    _validate_unmock(unmock)

    # Get provider instances
    provider_instances = []
    for base in PROVIDERS:
        # Determine if mockable
        is_mockable = bool(base.__subclasses__())

        if not is_mockable:
            # Concrete provider - always use as-is
            provider_class = get_provider(base, use_mock=False)
        else:
            # Mockable component - check unmock list
            component_name = getattr(base, "__mock_component__", None)
            use_mock = component_name not in unmock if component_name else False
            provider_class = get_provider(base, use_mock=use_mock)

        # All providers instantiated without arguments (Settings comes from DI)
        provider_instances.append(provider_class())

    return make_async_container(*provider_instances)


def _validate_unmock(unmock: set[Component]) -> None:
    """Validate unmock configuration.

    Args:
        unmock: Set of components to unmock

    Raises:
        ValueError: If unknown components or dependency violations
    """
    # Get all mockable components
    mockable_providers = [p for p in PROVIDERS if p.__subclasses__()]
    all_components = {
        getattr(p, "__mock_component__")
        for p in mockable_providers
        if hasattr(p, "__mock_component__")
    }

    # Check for unknown components
    unknown = unmock - all_components
    if unknown:
        raise ValueError(f"Unknown components: {unknown}")

    # Check dependencies
    for base in mockable_providers:
        component_name = getattr(base, "__mock_component__", None)
        if component_name in unmock:
            depends_on = getattr(base, "__depends_on__", set())
            missing = depends_on - unmock
            if missing:
                raise ValueError(
                    f"Component '{component_name}' requires {missing} to be unmocked"
                )
