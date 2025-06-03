"""
Utility functions for color palette extraction.
"""
import os
import requests
import tempfile
import random
from Pylette import extract_colors
from app.core.logging import logger
from typing import List, Union

def extract_color_palette(image_source: str, palette_size: int = 5) -> List[List[int]]:
    """
    Extract color palette from an image source (URL or file path).
    
    Args:
        image_source: URL or local path of the image to extract colors from
        palette_size: Number of colors to extract (between 3 and 10)
        
    Returns:
        List[List[int]]: List of RGB colors sorted by frequency
    """
    temp_image_path = None
    
    try:
        # Determine if image_source is a URL or local path
        if image_source.startswith(('http://', 'https://')):
            # It's a URL, download it
            try:
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                
                # Create a temporary file
                fd, temp_image_path = tempfile.mkstemp(suffix='.jpg')
                with os.fdopen(fd, 'wb') as f:
                    f.write(response.content)
                
                image_path = temp_image_path
            except Exception as e:
                logger.error(f"Error downloading image from {image_source}: {str(e)}")
                return get_fallback_colors(palette_size)
        else:
            # Assume it's a local file path
            if not os.path.exists(image_source):
                logger.error(f"Local image file does not exist: {image_source}")
                return get_fallback_colors(palette_size)
            image_path = image_source
        
        # Extract palette using Pylette
        logger.info(f"Extracting {palette_size} colors from image")
        palette = extract_colors(
            image=image_path, 
            palette_size=palette_size, 
            sort_mode='frequency'
        )
        
        # Convert palette to list of RGB values
        rgb_colors = []
        for color in palette:
            rgb_colors.append(list(color.rgb))
        
        # Clean up temporary file if created
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        return rgb_colors
    
    except Exception as e:
        logger.error(f"Error extracting color palette: {str(e)}")
        # Clean up temporary file
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        # Return fallback colors
        return get_fallback_colors(palette_size)

def get_fallback_colors(palette_size: int = 5) -> List[List[int]]:
    """
    Create fallback color palette when extraction fails.
    
    Args:
        palette_size: Number of colors to return
        
    Returns:
        List[List[int]]: List of RGB colors
    """
    # Predefined fallback palettes
    predefined_palettes = [
        # Google-like palette
        [
            [254, 254, 254],  # White
            [73, 137, 244],   # Blue
            [234, 73, 60],    # Red
            [251, 190, 14],   # Yellow
            [53, 168, 84]     # Green
        ],
        # Warm earthy palette
        [
            [251, 219, 147],  # Light peach
            [190, 91, 80],    # Coral
            [138, 45, 59],    # Dark coral
            [100, 27, 46],    # Burgundy
            [82, 40, 41]      # Dark brown
        ],
        # Soft pastel palette
        [
            [241, 231, 231],  # White
            [230, 157, 184],  # Pink
            [255, 208, 199],  # Salmon
            [255, 254, 206],  # Light yellow
            [189, 226, 218]   # Mint
        ],
        # Teal and neutral palette
        [
            [102, 210, 206],  # Teal
            [45, 170, 158],   # Dark teal
            [234, 234, 234],  # Light gray
            [227, 210, 195],  # Beige
            [93, 93, 93]      # Dark gray
        ]
    ]
    
    # Select a random palette
    fallback_palette = random.choice(predefined_palettes)
    
    # Ensure we return the requested number of colors
    if len(fallback_palette) > palette_size:
        return fallback_palette[:palette_size]
    
    # If we need more colors, duplicate some
    while len(fallback_palette) < palette_size:
        fallback_palette.append(random.choice(fallback_palette))
    
    return fallback_palette