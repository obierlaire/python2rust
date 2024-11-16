import unittest
import requests
import re
from time import sleep


class TestPerformanceService(unittest.TestCase):
    """Black box tests for the performance demonstration service."""

    BASE_URL = "http://127.0.0.1:8080"

    @classmethod
    def setUpClass(cls):
        """Verify service is accessible before running tests."""
        max_retries = 3

        for i in range(max_retries):
            try:
                response = requests.get(cls.BASE_URL)
                if response.status_code == 200:
                    return
            except requests.ConnectionError:
                if i == max_retries - 1:
                    raise unittest.SkipTest(
                        f"Service at {cls.BASE_URL} is not accessible. "
                        "Please ensure the service is running before running tests."
                    )
                sleep(1)

    def test_homepage_structure(self):
        """Test that homepage contains all required elements."""
        response = requests.get(f"{self.BASE_URL}/")
        self.assertEqual(response.status_code, 200)

        content = response.text
        required_elements = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<meta charset="UTF-8">',
            '<meta name="viewport"',
            '<title>Performance Demo</title>',
            '<h1>Performance Demonstration</h1>',
            '<form action="/" method="post">',
            '<button type="submit">Run Heavy Computation</button>'
        ]
        for element in required_elements:
            self.assertIn(element, content, f"Missing element: {element}")

        required_styles = [
            'font-family: Arial, sans-serif',
            'max-width: 800px',
            'margin: 0 auto',
            'padding: 20px'
        ]
        for style in required_styles:
            self.assertIn(style, content, f"Missing style: {style}")

    def test_computation_correctness(self):
        """Test that computation endpoint returns correct results."""
        response = requests.post(f"{self.BASE_URL}/")
        self.assertEqual(response.status_code, 200)
        content = response.text

        # Validate prime number calculations
        prime_count = re.search(r'Number of primes found: (\d+)', content)
        self.assertIsNotNone(prime_count, "Prime count not found in response")
        count = int(prime_count.group(1))
        self.assertEqual(count, 78498, "Incorrect number of primes found")

        # Validate matrix multiplication for 200x200 matrices
        matrix_sum = re.search(r'Matrix multiplication sum: (\d+)', content)
        self.assertIsNotNone(matrix_sum, "Matrix multiplication sum not found")
        sum_value = int(matrix_sum.group(1))
        expected_sum = 18414465000000
        self.assertEqual(sum_value, expected_sum,
                         f"Incorrect matrix multiplication sum. Expected {expected_sum}, got {sum_value}")

        # Validate timing information
        time_match = re.search(r'Time taken: ([\d.]+) seconds', content)
        self.assertIsNotNone(time_match, "Time taken not found in response")
        time_taken = float(time_match.group(1))
        self.assertGreater(
            time_taken, 0.01, "Computation time suspiciously short")

        # Validate last primes
        primes_match = re.search(r'Last few primes: \[([\d, ]+)\]', content)
        self.assertIsNotNone(primes_match, "Last primes not found in response")
        last_primes = eval(f"[{primes_match.group(1)}]")
        # Corrected order: the primes are returned in ascending order
        expected_last_primes = [999953, 999959, 999961, 999979, 999983]
        self.assertEqual(last_primes, expected_last_primes,
                         "Incorrect last prime numbers")

    def test_error_handling(self):
        """Test service handles invalid requests appropriately."""

        # Test non-existent endpoint
        response = requests.get(f"{self.BASE_URL}/nonexistent")
        self.assertEqual(response.status_code, 404,
                         "Should return 404 for non-existent paths")


if __name__ == '__main__':
    unittest.main()
