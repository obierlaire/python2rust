import unittest
import json
from main import app, calculate_primes_up_to, matrix_multiply
import requests
from multiprocessing import Process
import time
import re


def run_flask_server():
    """Function to run the Flask server for testing."""
    app.run(host='127.0.0.1', port=8080)


class TestComputationalFunctions(unittest.TestCase):
    """Unit tests for computational functions."""

    def test_calculate_primes_small(self):
        """Test prime calculation with small numbers."""
        primes = calculate_primes_up_to(10)
        self.assertEqual(primes, [2, 3, 5, 7])

    def test_calculate_primes_larger(self):
        """Test prime calculation with larger numbers."""
        primes = calculate_primes_up_to(20)
        self.assertEqual(primes, [2, 3, 5, 7, 11, 13, 17, 19])

    def test_matrix_multiply_2x2(self):
        """Test matrix multiplication with 2x2 matrices."""
        result = matrix_multiply(2)
        expected = [[0, 1],
                    [0, 2]]
        self.assertEqual(result, expected)

    def test_matrix_multiply_3x3(self):
        """Test matrix multiplication with 3x3 matrices."""
        result = matrix_multiply(3)
        expected = [[0, 5, 10],
                    [0, 8, 16],
                    [0, 11, 22]]
        self.assertEqual(result, expected)
        total_sum = sum(sum(row) for row in result)
        self.assertEqual(total_sum, 72)


class TestWebInterface(unittest.TestCase):
    """Integration tests for web interface."""

    @classmethod
    def setUpClass(cls):
        """Start Flask server in a separate process."""
        # Use the standalone function instead of lambda
        cls.server = Process(target=run_flask_server)
        cls.server.start()
        # Give the server a moment to start up
        time.sleep(2)

        # Check if server is actually running
        max_retries = 5
        for i in range(max_retries):
            try:
                requests.get('http://127.0.0.1:8080/')
                break
            except requests.ConnectionError:
                if i == max_retries - 1:
                    raise
                time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        """Shut down the Flask server."""
        if hasattr(cls, 'server'):
            cls.server.terminate()
            cls.server.join(timeout=1)
            if cls.server.is_alive():
                cls.server.kill()  # Force kill if still alive

    def setUp(self):
        """Ensure server is running before each test."""
        try:
            requests.get('http://127.0.0.1:8080/')
        except requests.ConnectionError:
            self.skipTest("Server is not running")

    def test_get_homepage(self):
        """Test GET request to homepage."""
        response = requests.get('http://127.0.0.1:8080/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Performance Demonstration', response.text)
        self.assertIn('Run Heavy Computation', response.text)

    def test_post_computation(self):
        """Test POST request for computation."""
        response = requests.post('http://127.0.0.1:8080/')
        self.assertEqual(response.status_code, 200)

        # Check if computation results are present
        self.assertIn('Results:', response.text)
        self.assertIn('Time taken:', response.text)
        self.assertIn('Number of primes found:', response.text)
        self.assertIn('Last few primes:', response.text)
        self.assertIn('Matrix multiplication sum:', response.text)

        # Extract and verify some values using regex
        prime_count = re.search(
            r'Number of primes found: (\d+)', response.text)
        self.assertIsNotNone(prime_count)
        self.assertGreater(int(prime_count.group(1)), 0)

        # Check for matrix sum
        matrix_sum = re.search(
            r'Matrix multiplication sum: (\d+)', response.text)
        self.assertIsNotNone(matrix_sum)
        self.assertGreater(int(matrix_sum.group(1)), 0)


if __name__ == '__main__':
    unittest.main()
