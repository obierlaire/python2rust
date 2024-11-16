from flask import Flask, render_template_string, request
from array import array
import io
import logging
import base64
import random
import time
import math

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Predefined interesting points in the Mandelbrot set
CENTER_POINTS = [
    {"name": "Classic Center", "coords": (-0.75, 0.1)},
    {"name": "Seahorse Valley", "coords": (
        0.001643721971153, 0.822467633298876)},
    {"name": "Elephant Valley", "coords": (-0.1015, 0.633)},
    {"name": "Dendrites", "coords": (-1.749, 0.0)},
    {"name": "Spiral Pattern", "coords": (-0.1592, -1.0316)},
    {"name": "Julia Set Boundary", "coords": (0.285, 0.01)},
    {"name": "Main Cardioid", "coords": (-1.25, 0.02)},
]


def countIterationsUntilDivergent(c, threshold):
    z = complex(0, 0)
    for iteration in range(threshold):
        z = (z * z) + c
        if abs(z) > 4:
            break
    return iteration


def linspace(start, stop, num):
    if num < 2:
        return [start]
    step = (stop - start) / (num - 1)
    return [start + step * i for i in range(num)]


def create_image(data, width, height):
    """Create a simple grayscale PNG image from data."""
    import png  # Only import when needed

    # Normalize data to 0-255 range
    max_val = max(max(row) for row in data)
    if max_val == 0:
        max_val = 1

    # Convert to grayscale bytes
    pixels = []
    for row in data:
        pixel_row = []
        for val in row:
            gray = int((val * 255) / max_val)
            pixel_row.extend([gray, gray, gray])  # RGB
        pixels.append(pixel_row)

    # Create PNG
    output = io.BytesIO()
    w = png.Writer(width=width, height=height, greyscale=False)
    w.write(output, pixels)
    return output.getvalue()


def generate_mandelbrot(threshold, density):
    selected_point = random.choice(CENTER_POINTS)
    point_name = selected_point["name"]
    real_center, imag_center = selected_point["coords"]
    zoom_factor = random.uniform(0.0001, 0.01)

    # Define bounds
    real_min = real_center - zoom_factor
    real_max = real_center + zoom_factor
    imag_min = imag_center - zoom_factor
    imag_max = imag_center + zoom_factor

    # Create grid and compute points
    start_time = time.time()

    real_axis = linspace(real_min, real_max, density)
    imag_axis = linspace(imag_min, imag_max, density)

    # Compute Mandelbrot set
    grid = []
    for ix in range(density):
        row = []
        for iy in range(density):
            c = complex(real_axis[ix], imag_axis[iy])
            row.append(countIterationsUntilDivergent(c, threshold))
        grid.append(row)

    # Create image
    image_data = create_image(grid, density, density)
    elapsed_time = time.time() - start_time

    logging.info(
        f"Mandelbrot set generated in {elapsed_time:.2f} seconds at {point_name}")

    # Encode to base64
    img_base64 = base64.b64encode(image_data).decode('utf-8')
    return img_base64, elapsed_time, point_name


# HTML template for the web page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mandelbrot Generator</title>
</head>
<body>
    <h1>Mandelbrot Set Generator</h1>
    <form action="/" method="post">
        <button type="submit">Run</button>
    </form>
    {% if image %}
    <h2>Generated Image:</h2>
    <p>Point of Interest: {{ point_name }}</p>
    <p>Time taken: {{ elapsed_time }} seconds</p>
    <img src="data:image/png;base64,{{ image }}" alt="Mandelbrot Set">
    {% endif %}
</body>
</html>
"""


@app.route('/', methods=['GET', 'POST'])
def index():
    image = None
    elapsed_time = 0.0
    point_name = ""
    if request.method == 'POST':
        logging.info("Received request to generate Mandelbrot set.")
        image, elapsed_time, point_name = generate_mandelbrot(
            threshold=1000, density=1000)
    return render_template_string(HTML_TEMPLATE, image=image, elapsed_time=f"{elapsed_time:.2f}", point_name=point_name)


def main():
    """Main function to start the Flask app."""
    logging.info("Starting the Flask application.")
    app.run(host='127.0.0.1', port=8080, debug=True)


if __name__ == '__main__':
    main()
