from flask import Flask, render_template_string, request
import time

app = Flask(__name__)

## maybe have it as a CLI also

def calculate_primes_up_to(n):
    """Calculate primes using exactly the same algorithm as Rust."""
    primes = []
    num_range = range(2, n + 1)
    for num in num_range:
        sqrt = int(num ** 0.5)
        is_prime = True
        for i in range(2, sqrt + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes

def matrix_multiply(size):
    """Matrix multiplication using exactly the same algorithm as Rust."""
    matrix1 = [[i + j for j in range(size)] for i in range(size)]
    matrix2 = [[i * j for j in range(size)] for i in range(size)]
    
    result = []
    for i in range(size):
        row = []
        for j in range(size):
            sum_val = 0
            for k in range(size):
                sum_val += matrix1[i][k] * matrix2[k][j]
            row.append(sum_val)
        result.append(row)
    return result

# Fixed Jinja2 template syntax
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Demo</title>
    <style>
        body { 
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Performance Demonstration</h1>
    <form action="/" method="post">
        <button type="submit">Run Heavy Computation</button>
    </form>
    
    {% if results %}
    <h2>Results:</h2>
    <p>Time taken: {{ results.time_taken }} seconds</p>
    <h3>Statistics:</h3>
    <ul>
        <li>Number of primes found: {{ results.prime_count }}</li>
        <li>Last few primes: {{ results.last_primes }}</li>
        <li>Matrix multiplication sum: {{ results.matrix_sum }}</li>
    </ul>
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    if request.method == 'POST':
        start_time = time.time()
        
        # Calculate primes up to 100000
        primes = calculate_primes_up_to(1000000)
        
        # Perform 200x200 matrix multiplication
        matrix_result = matrix_multiply(200)
        matrix_sum = sum(sum(row) for row in matrix_result)
        
        results = {
            'time_taken': f"{time.time() - start_time:.2f}",
            'prime_count': len(primes),
            'last_primes': str(primes[-5:]),
            'matrix_sum': matrix_sum
        }
    
    return render_template_string(HTML_TEMPLATE, results=results)

def main():
    """Entry point for running the Flask app."""
    print("Server starting at http://127.0.0.1:8080")
    app.run(host='127.0.0.1', port=8080)

if __name__ == '__main__':
    main()
