import unittest
import requests
import re
import base64
from time import sleep


class TestMandelbrotService(unittest.TestCase):
    """Black box tests for the Mandelbrot set generator service."""

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

    def test_get_homepage(self):
        """Test that GET request shows form but no image."""
        response = requests.get(f"{self.BASE_URL}/")
        self.assertEqual(response.status_code, 200)
        content = response.text

        # Check required elements are present
        self.assertIn('<title>Mandelbrot Generator</title>', content)
        self.assertIn('<h1>Mandelbrot Set Generator</h1>', content)
        self.assertIn('<form action="/" method="post">', content)
        self.assertIn('<button type="submit">Run</button>', content)

        # Verify no image is present
        self.assertNotIn('Generated Image:', content)
        self.assertNotIn('data:image/png;base64,', content)
        self.assertNotIn('Time taken:', content)

    def test_post_generates_image(self):
        """Test that POST request generates and returns a valid image."""
        response = requests.post(f"{self.BASE_URL}/")
        self.assertEqual(response.status_code, 200)
        content = response.text

        # Check that the image section is present
        self.assertIn('<h2>Generated Image:</h2>', content)
        self.assertIn('Time taken:', content)
        self.assertIn('Point of Interest:', content)

        # Extract and validate base64 image
        image_match = re.search(r'data:image/png;base64,([^"]+)', content)
        self.assertIsNotNone(image_match, "No base64 image found in response")

        # Verify the base64 string is valid and can be decoded
        try:
            image_data = base64.b64decode(image_match.group(1))
            # Check if it's a valid PNG (PNG magic number)
            self.assertTrue(image_data.startswith(b'\x89PNG\r\n\x1a\n'),
                            "Generated image is not a valid PNG")
        except Exception as e:
            self.fail(f"Failed to decode base64 image: {str(e)}")

        # Check timing information is present and reasonable
        time_match = re.search(r'Time taken: ([\d.]+) seconds', content)
        self.assertIsNotNone(time_match, "Time taken not found in response")
        time_taken = float(time_match.group(1))
        self.assertGreater(
            time_taken, 0, "Time taken should be greater than 0")


if __name__ == '__main__':
    unittest.main()
