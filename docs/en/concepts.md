# Core Concepts

## Lifetimes
- `SINGLETON`: single instance across the app
- `TRANSIENT`: new instance per resolve
- `SCOPED`: single instance per scope (e.g., per request)
- `FACTORY`: created by a factory callable

## Service Keys
- Supports both type keys and string keys
- Prefer type keys for static safety; use strings for dynamic scenarios

## Constructor Injection
- Analyses `__init__` type hints and injects dependencies (`ConstructorInjector`)
- Supports `Optional[T]` and defaults
- Supports explicit `Injected` marker

## Scopes
- Use `container.create_scope()` to create a scope
- `SCOPED` services are unique within a scope
- Scope teardown releases resources

## Interceptors
- Hooks for before/after/error to log and collect metrics
- Can intercept resolution and lifecycle events

## Generics
- `GenericKey` distinguishes type parameters
- Bind concrete implementations with `register_generic(container, Repository[User], UserRepository)`

## Circular Dependency Detection
- Detects cycles during resolution (`CircularDependencyDetector`)
- Diagnostic and visualization utilities help debugging

## Async Support
- Unified sync/async resolution; uses `asyncio` internally when required

## Performance & Diagnostics
- Built-in metrics and timers; diagnostic report and dependency graph export
