def format_error_for_fix(error_text: str) -> str:
    """Extract essential error information from build/test output."""
    if not error_text:
        return error_text

    # if error_text contains "AssertionError"
    if "AssertionError" in error_text:
        # TODO: format better in that case
        return error_text
    if "Test that" in error_text:
        # TODO: format better in that case
        return error_text

    # Extract compiler errors
    error_lines = []
    current_error = []
    in_error = False

    for line in error_text.split('\n'):
        if 'error[' in line or 'error:' in line:
            if in_error and current_error:
                error_lines.append('\n'.join(current_error))
            current_error = [line]
            in_error = True
        elif in_error and line.strip() and not line.startswith('   Compiling'):
            current_error.append(line)

    if current_error:
        error_lines.append('\n'.join(current_error))

    return '\n'.join(error_lines)

    error_lines = []
    in_error = False
    error_block = []

    for line in error_text.split('\n'):
        # Ignore compilation noise
        if any(x in line for x in [
            'Updating crates.io index',
            'Blocking waiting for',
            'Compiling',
            'Checking',
            'Adding',
            'Locking',
            'For more information'
        ]):
            continue

        # Start of error
        if line.startswith('error['):
            if error_block:
                error_lines.extend(error_block)
                error_block = []
            in_error = True
            error_block.append(line)
        # Error location
        elif in_error and ' --> ' in line:
            error_block.append(line)
        # Error detail
        elif in_error and line.strip() and not line.startswith('   |'):
            error_block.append(line)
        # End of error
        elif in_error and not line.strip():
            if error_block:
                error_lines.extend(error_block)
                error_block = []
            in_error = False

    if error_block:
        error_lines.extend(error_block)

    return '\n'.join(error_lines)
