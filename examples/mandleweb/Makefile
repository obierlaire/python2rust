# Define the main Python script
SCRIPT_NAME = mandleweb.py
COMPILED_DIR = __pycache__

# Default target: Run the Flask application using Poetry
.PHONY: run
run:
	@echo "Running Flask application with Poetry..."
	poetry run python $(SCRIPT_NAME)

# Compile the Python script to bytecode (.pyc)
.PHONY: compile
compile:
	@echo "Compiling the Python script to bytecode..."
	poetry run python -m py_compile $(SCRIPT_NAME)

# Run the compiled .pyc file with Poetry
.PHONY: run-compiled
run-compiled:
	@echo "Running the compiled .pyc file with Poetry..."
	# Find the compiled .pyc file dynamically, assuming only one is generated
	@COMPILED_FILE=$$(ls $(COMPILED_DIR) | grep $(SCRIPT_NAME:.py=).cpython) && \
	poetry run python $(COMPILED_DIR)/$$COMPILED_FILE


# Compile the Python script with Cython and run the compiled code
.PHONY: cython
cython:
	@echo "Compiling with Cython..."
	# Compile the Python script to C code and then to a shared object file (.so)
	poetry run cythonize -i -3 mandleweb.py
	@echo "Running the compiled Cython module..."
	# Import the compiled module and call the main() function explicitly
	poetry run python -c "import mandleweb; mandleweb.main()"

.PHONY: rustpython
rustpython:
	poetry run rustpython $(SCRIPT_NAME)

test:
	@echo "Running black box tests..."
	poetry run python -m unittest test_service.py -v

# Clean the compiled bytecode files
.PHONY: clean
clean:
	@echo "Cleaning compiled files..."
	rm -rf $(COMPILED_DIR)
	rm -rf build
	rm -rf *.c *.so *.log
	
