# Python2Rust

A tool for automatically migrating Python code to Rust using AI. Leverages Claude to analyze Python code and generate equivalent Rust implementations.

## Features

- Automatic Python to Rust code conversion
- Preserves functionality while leveraging Rust's performance benefits
- Handles web servers, algorithms, and data processing code
- Includes comprehensive testing and verification
- Maintains exact input/output compatibility

## Installation

1. Clone the repository:
```bash
git clone https://github.com/obierlaire/python2rust.git
cd python2rust
```

2. Install dependencies with Poetry:
```bash
poetry install
```

3. Set up API tokens:
- Create a `.claude_token` file with your Anthropic API key
- (Optional) Create a `.hf_token` file for HuggingFace models

## Usage

Basic usage:
```bash
python -m python2rust --python-file path/to/your/file.py --output-dir generated
```

Check the `examples/` directory for more use cases:
- `simple_migration.py`: Basic code migration
- `server_migration.py`: Web server migration
- `batch_migration.py`: Multiple file migration

## Development

1. Set up development environment:
```bash
make dev
```

2. Run tests:
```bash
make test
```

3. Clean generated files:
```bash
make clean
```

## Requirements

- Python 3.9+
- Poetry for dependency management
- Rust toolchain for testing generated code
- Anthropic API key

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request