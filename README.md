# Python2Rust

**DISCLAIMER: This tool is not intended to be used in production. This is only for demonstration purposes !**

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

or 

```
make clean
make migrate
```

The rust file is generated in `/generated/src` folder
Logs are in `/logs` folder
Calls to AI services, with prompts, number of tokens, carbon emissions are in `/generated/debug/`

Check the `examples/` directory for more use cases:
- `prime`: Basic python web server that calculate prime numbers and do matrix multiplication
- `mandleweb`: Mandlebrot set generation and webserver


## Requirements

- Python 3.9+
- Poetry for dependency management
- Rust toolchain for testing generated code
- Anthropic API key

## License

MIT License - see LICENSE file for details
