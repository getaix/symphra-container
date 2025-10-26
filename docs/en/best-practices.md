# Best Practices

## Keys
- Prefer type keys; use string keys for dynamic bindings only
- Use `GenericKey` to disambiguate generics

## Lifetimes
- Default to `TRANSIENT` unless stateful or expensive
- Use `SINGLETON` for stateless or heavy resources
- Use `SCOPED` for request/session-bound dependencies

## Factories
- Use factories for resources needing explicit creation/teardown (DB connections)

## Interceptors & Diagnostics
- Add interceptors for logging, metrics, and error traces
- Export dependency graphs to review architecture

## Testing
- Override registrations in tests via `override=True`
- Provide fakes/stubs per scope

## Web Frameworks
- Bind a scope per request (FastAPI/Flask/Django integrations)

## Generics
- Register concrete implementations with `register_generic`
