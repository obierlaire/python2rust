# Default values
PYTHON_FILE ?= ./examples/prime/python/main.py
# PYTHON_FILE ?= ./examples/mandleweb/mandleweb.py

OUTPUT_DIR ?= generated
CONFIG_DIR = $(HOME)/.config/python2rust
LOGS_DIR = logs

# Colors for pretty printing
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

# Ensure required directories exist
$(OUTPUT_DIR):
	@mkdir -p $(OUTPUT_DIR)/debug
	@mkdir -p $(OUTPUT_DIR)/latest
	@echo "$(GREEN)Created output directories$(RESET)"

$(LOGS_DIR):
	@mkdir -p $(LOGS_DIR)
	@echo "$(GREEN)Created logs directory$(RESET)"

$(CONFIG_DIR):
	@mkdir -p $(CONFIG_DIR)
	@echo "$(GREEN)Created config directory$(RESET)"

.PHONY: setup-dirs
setup-dirs: $(OUTPUT_DIR) $(LOGS_DIR) $(CONFIG_DIR)

.PHONY: setup-specs
setup-specs: $(CONFIG_DIR)
	@if [ ! -f migration_specs.json ]; then \
		cp src/python2rust/config/default_specs.json migration_specs.json && \
		echo "$(GREEN)Created migration_specs.json in current directory$(RESET)"; \
	fi
	@if [ ! -f $(CONFIG_DIR)/migration_specs.json ]; then \
		cp src/python2rust/config/default_specs.json $(CONFIG_DIR)/migration_specs.json && \
		echo "$(GREEN)Created migration_specs.json in $(CONFIG_DIR)$(RESET)"; \
	fi

.PHONY: setup
setup: setup-dirs setup-specs
	@echo "$(CYAN)Installing dependencies...$(RESET)"
	poetry install
	poetry run python setup.py
	@echo "$(GREEN)Setup complete!$(RESET)"

.PHONY: migrate
migrate: setup-dirs
	@echo "$(CYAN)Starting migration...$(RESET)"
	poetry run python -m python2rust.main --python-file $(PYTHON_FILE) --output-dir $(OUTPUT_DIR)

.PHONY: clean-cache
clean-cache:
	@echo "$(YELLOW)Cleaning Python cache...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

.PHONY: clean-generated
clean-generated:
	@echo "$(YELLOW)Cleaning generated files...$(RESET)"
	rm -rf $(OUTPUT_DIR)
	rm -rf $(LOGS_DIR)

.PHONY: clean
clean: clean-cache clean-generated
	@echo "$(GREEN)Clean complete!$(RESET)"

.PHONY: check-config
check-config:
	@echo "$(CYAN)Checking configuration...$(RESET)"
	@echo "Current directory specs: $$([ -f migration_specs.json ] && echo "$(GREEN)Found$(RESET)" || echo "$(YELLOW)Not found$(RESET)")"
	@echo "User config specs: $$([ -f $(CONFIG_DIR)/migration_specs.json ] && echo "$(GREEN)Found$(RESET)" || echo "$(YELLOW)Not found$(RESET)")"
	@echo "Package default specs: $$([ -f src/python2rust/config/default_specs.json ] && echo "$(GREEN)Found$(RESET)" || echo "$(YELLOW)Not found$(RESET)")"

.PHONY: show-debug
show-debug:
	@echo "$(CYAN)Debug directories:$(RESET)"
	@for d in $(OUTPUT_DIR)/debug/attempt_*; do \
		if [ -d "$$d" ]; then \
			echo "$$d"; \
			if [ -f "$$d/logs/verification.json" ]; then \
				echo "  - Verification results available"; \
			fi; \
			if [ -f "$$d/SUCCESS" ]; then \
				echo "  $(GREEN)✓ Success$(RESET)"; \
			else \
				echo "  $(YELLOW)✗ Failed$(RESET)"; \
			fi; \
		fi; \
	done

.PHONY: help
help:
	@echo "$(CYAN)Available commands:$(RESET)"
	@echo "  make setup         - Install dependencies and setup configuration"
	@echo "  make migrate      - Migrate Python file to Rust"
	@echo "  make clean        - Remove all generated files and cache"
	@echo "  make clean-cache  - Remove only Python cache files"
	@echo "  make check-config - Check configuration files status"
	@echo "  make show-debug   - Show debug attempts status"
	@echo ""
	@echo "$(CYAN)Configuration locations (in priority order):$(RESET)"
	@echo "  1. ./migration_specs.json (current directory)"
	@echo "  2. ~/.config/python2rust/migration_specs.json"
	@echo "  3. Package default specs"
	@echo ""
	@echo "$(CYAN)Configuration:$(RESET)"
	@echo "  PYTHON_FILE     - Python file to migrate (default: input.py)"
	@echo "  OUTPUT_DIR      - Output directory (default: generated)"
	@echo ""
	@echo "$(CYAN)Example usage:$(RESET)"
	@echo "  make migrate PYTHON_FILE=my_script.py"