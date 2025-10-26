# FAQ

## ServiceNotFoundError on resolve
- Ensure the type or generic key has been registered
- For `Optional[T]`, absence will not raise errors

## How to debug circular dependencies?
- Use diagnostics and dependency graph visualization (`visualization` module)

## Async services
- Unified interface supports async; simply `await` methods as needed

## How to mock in tests?
- Use `register(..., override=True)` to replace existing registrations
