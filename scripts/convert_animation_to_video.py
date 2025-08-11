#!/usr/bin/env python3
"""Convert Plotly HTML animation to MP4 video using existing Firefox."""

import asyncio
import os
from pathlib import Path

import cv2
import numpy as np
from playwright.async_api import async_playwright


async def capture_animation():
    """Capture frames from the Plotly animation."""
    async with async_playwright() as p:
        # Use playwright's Firefox
        browser = await p.firefox.launch(
            headless=True
        )
        
        # Start with a larger viewport to ensure plot fits
        page = await browser.new_page(viewport={"width": 2000, "height": 1200})
        
        # Load the HTML file
        file_path = Path("water_level_animation.html").absolute()
        await page.goto(f"file://{file_path}")
        
        # Wait for Plotly to load
        await page.wait_for_selector(".plotly", timeout=10000)
        await asyncio.sleep(2)  # Extra wait for animation to initialize
        
        # Get the actual plot element dimensions
        plot_element = await page.query_selector(".plotly")
        plot_box = await plot_element.bounding_box()
        
        print(f"Plot dimensions: {plot_box['width']}x{plot_box['height']}")
        print(f"Plot position: ({plot_box['x']}, {plot_box['y']})")
        
        # Find the play button and total frames
        # Get animation controls
        frames = []
        
        # Try to get the slider to determine frame count
        slider = await page.query_selector(".rangeslider-rangeplot")
        if not slider:
            # Alternative: look for frame controls
            slider = await page.query_selector("input[type='range']")
        
        # Get total number of frames from the slider
        if slider:
            max_frames = await slider.evaluate("el => el.max")
            max_frames = int(max_frames) if max_frames else 100
        else:
            max_frames = 100  # Default fallback
        
        print(f"Capturing {max_frames + 1} frames...")
        
        # Capture each frame
        for i in range(max_frames + 1):
            # Set the slider to specific frame
            await page.evaluate(f"""
                () => {{
                    const slider = document.querySelector('input[type="range"]');
                    if (slider) {{
                        slider.value = {i};
                        slider.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        slider.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    // Alternative method using Plotly directly
                    const plotDiv = document.querySelector('.plotly');
                    if (plotDiv && plotDiv._fullLayout && plotDiv._fullLayout.sliders) {{
                        Plotly.relayout(plotDiv, {{'sliders[0].active': {i}}});
                    }}
                }}
            """)
            
            # Wait for the frame to render
            await asyncio.sleep(0.1)
            
            # Take screenshot of just the plot element
            screenshot = await plot_element.screenshot()
            
            # Convert to numpy array for OpenCV
            nparr = np.frombuffer(screenshot, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            frames.append(img)
            
            if (i + 1) % 10 == 0:
                print(f"  Captured frame {i + 1}/{max_frames + 1}")
        
        await browser.close()
        
        return frames


def create_video(frames, output_path="water_level_animation.mp4", fps=10):
    """Create MP4 video from captured frames."""
    if not frames:
        print("No frames to process!")
        return
    
    print(f"Creating video with {len(frames)} frames at {fps} fps...")
    
    # Get frame dimensions
    height, width = frames[0].shape[:2]
    print(f"Video dimensions: {width}x{height}")
    
    # Define codec and create VideoWriter
    # Use H264 codec for better compatibility and quality
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Write frames to video
    for i, frame in enumerate(frames):
        out.write(frame)
        if (i + 1) % 10 == 0:
            print(f"  Written frame {i + 1}/{len(frames)}")
    
    # Release everything
    out.release()
    # cv2.destroyAllWindows()  # Not needed in headless mode
    
    print(f"Video saved as: {output_path}")
    print(f"Duration: {len(frames) / fps:.1f} seconds")


async def main():
    """Main function to convert HTML animation to video."""
    try:
        frames = await capture_animation()
        create_video(frames)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())