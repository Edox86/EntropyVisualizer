#!/usr/bin/env python3
"""
Entropy Visualizer

This tool reads any file, splits it into blocks (default 16 bytes),
computes the Shannon entropy for each block (normalized),
and prints each block's hex bytes with a background color that
varies from blue (cold) for low entropy to red (hot) for high entropy.

Optionally, an image is created where each block is represented
by a colored square arranged sequentially.

Usage:
  python3 EntropyVisualizer.py myfile.bin --block-size 8 --image entropy.png
"""

import argparse
import math
import sys

# Try to import Pillow for image creation. If not available, set Image to None.
try:
    from PIL import Image
except ImportError:
    Image = None


def compute_entropy(block: bytes) -> float:
    """
    Compute the Shannon entropy of a given block of bytes.
    Returns 0.0 for an empty block.
    """
    if not block:
        return 0.0
    freq = {}
    # Count frequency of each byte in the block.
    for b in block:
        freq[b] = freq.get(b, 0) + 1
    ent = 0.0
    # Calculate entropy using Shannon's formula.
    for count in freq.values():
        p = count / len(block)
        ent -= p * math.log2(p)
    return ent


def max_entropy(n: int) -> float:
    """
    Return the maximum possible entropy for n bytes.
    For n < 256, maximum entropy is log2(n) (if all bytes are different).
    For n >= 256, maximum entropy is 8.
    """
    if n == 0:
        return 0.0
    return math.log2(n) if n < 256 else 8.0


def entropy_to_color(norm: float) -> tuple:
    """
    Map a normalized entropy value (0.0 to 1.0) to an RGB color.
    Color gradient:
      0.0   -> Blue (cold)
      0.25  -> Cyan
      0.5   -> Green
      0.75  -> Yellow
      1.0   -> Red (hot)
    """
    anchors = [
        (0.0, (0, 0, 255)),  # blue
        (0.25, (0, 255, 255)),  # cyan
        (0.5, (0, 255, 0)),  # green
        (0.75, (255, 255, 0)),  # yellow
        (1.0, (255, 0, 0))  # red
    ]
    # Clamp normalized value between 0.0 and 1.0.
    norm = max(0.0, min(1.0, norm))
    # Linearly interpolate between anchor colors.
    for i in range(len(anchors) - 1):
        (x0, col0), (x1, col1) = anchors[i], anchors[i + 1]
        if x0 <= norm <= x1:
            t = (norm - x0) / (x1 - x0)
            r = int(col0[0] + t * (col1[0] - col0[0]))
            g = int(col0[1] + t * (col1[1] - col0[1]))
            b = int(col0[2] + t * (col1[2] - col0[2]))
            return (r, g, b)
    return anchors[-1][1]


def create_image(colors, pixel_size, output_file):
    """
    Create an image where each block is drawn as a colored square in a grid.
    The output image is fixed to 400x800 pixels.

    If blocks can be arranged in a single vertical column with squares at least
    'pixel_size' pixels, use that layout. Otherwise, compute a grid layout that
    maximizes square size within the fixed canvas.

    Parameters:
      colors: List of RGB tuples for each block.
      pixel_size: Minimum acceptable square size for vertical layout.
      output_file: Filename to save the generated image.
    """
    if Image is None:
        print("Pillow is not installed. Please install it (pip install Pillow) to create images.")
        return

    # Define fixed canvas size.
    canvas_width, canvas_height = 400, 800
    n = len(colors)

    # Consider vertical layout (1 column).
    vertical_square_size = int(min(canvas_width, canvas_height / n))

    if vertical_square_size >= pixel_size:
        best_cols = 1
        best_rows = n
        max_square_size = vertical_square_size
    else:
        # Compute grid layout that maximizes square size.
        max_square_size = 0
        best_cols = 1
        best_rows = 1
        for cols in range(1, n + 1):
            rows = math.ceil(n / cols)
            square_size = int(min(canvas_width / cols, canvas_height / rows))
            if square_size > max_square_size:
                max_square_size = square_size
                best_cols = cols
                best_rows = rows

    # Calculate margins to center the grid on the canvas.
    left_margin = (canvas_width - best_cols * max_square_size) // 2
    top_margin = (canvas_height - best_rows * max_square_size) // 2

    # Create a new white image.
    img = Image.new("RGB", (canvas_width, canvas_height), "white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)

    # Draw colored squares for each block.
    for i, col in enumerate(colors):
        row = i // best_cols
        col_index = i % best_cols
        x = left_margin + col_index * max_square_size
        y = top_margin + row * max_square_size
        draw.rectangle([x, y, x + max_square_size - 1, y + max_square_size - 1], fill=col)

    try:
        img.save(output_file)
        print(f"Image saved to {output_file}")
    except Exception as e:
        print("Error saving image:", e)


def main():
    """
    Main function to parse arguments, process the file, print the colored hex output,
    and generate an image if requested.
    """
    parser = argparse.ArgumentParser(description="File entropy visualizer")
    parser.add_argument("filename", help="File to process")
    parser.add_argument("-b", "--block-size", type=int, default=16,
                        help="Number of bytes per block (default: 16)")
    parser.add_argument("-i", "--image", default=None,
                        help="If provided, save an image with the given filename")
    args = parser.parse_args()

    # Attempt to read the file in binary mode.
    try:
        with open(args.filename, "rb") as f:
            data = f.read()
    except Exception as e:
        print("Error opening file:", e)
        sys.exit(1)

    bs = args.block_size
    blocks = [data[i:i + bs] for i in range(0, len(data), bs)]

    # Print header for hex output.
    count = 0
    while count < bs:
        spacing = "  " if count < 0x10 else " " if count < 0x100 else ""
        print(f"{count:X}{spacing}", end="")
        count += 1
    print("")

    color_list = []
    offset_counter = 0
    # Process each block: calculate entropy, map to color, and print hex output.
    for block in blocks:
        ent = compute_entropy(block)
        max_ent = max_entropy(len(block))
        norm = ent / max_ent if max_ent > 0 else 0.0
        col = entropy_to_color(norm)
        color_list.append(col)
        hex_str = " ".join(f"{b:02x}" for b in block)
        # Print hex string with background color using ANSI escape codes.
        sys.stdout.write(f"\033[48;2;{col[0]};{col[1]};{col[2]}m{hex_str}\033[0m")
        sys.stdout.write(f"[0x{offset_counter:X}]\n")
        offset_counter += bs
    sys.stdout.write("\n")

    # If image output is requested, create the image.
    if args.image:
        create_image(color_list, 1, args.image)


if __name__ == "__main__":
    main()
