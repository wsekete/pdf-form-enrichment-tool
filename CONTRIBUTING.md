# Contributing to PDF Form Enrichment Tool

We welcome contributions! Please follow these guidelines.

## Development Setup

```bash
git clone https://github.com/yourusername/pdf-form-enrichment-tool.git
cd pdf-form-enrichment-tool
make setup
```

## Code Style

- Use Black for formatting: `make format`
- Follow PEP 8
- Add type hints
- Write comprehensive tests
- Document your code

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure all tests pass: `make test`
6. Run quality checks: `make quality`
7. Submit a pull request

## Testing

```bash
make test          # Run tests
make test-cov      # Run with coverage
make quality       # Run all quality checks
```

## Questions?

Open an issue or start a discussion!
