import asyncio
import sys
import os
import json
from pathlib import Path

# Add the project root to sys.path
root_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(root_dir))

async def test_card_vision(image_path_str):
    """
    Test the AI vision appraisal with a local image file.
    """
    try:
        from app.services.appraisal import appraise_card_from_image
        from dotenv import load_dotenv
        
        # Load environment variables (for Gemini API Key)
        load_dotenv()
        
        image_path = Path(image_path_str)
        if not image_path.exists():
            print(f"Error: Image file not found at {image_path}")
            return

        print(f"\n[TEST] Appraising image: {image_path.name}")
        print("-" * 50)
        
        # Read image bytes
        with open(image_path, "rb") as f:
            image_data = f.read()
            
        # Call the appraisal service
        result = await appraise_card_from_image(image_data=image_data)
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
            
        print("\nAI APPRAISAL RESULTS:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("-" * 50)
        
        # Verify specific fields important for the Team Rocket card
        print("\nVERIFICATION CHECK:")
        print(f"Card Name (EN): {result.get('card_name_english')}")
        print(f"Set Code:       {result.get('set_name')} (Expected: 'Rocket' or 'R')")
        print(f"Full Set Name:  {result.get('full_set_name')} (Expected: 'Team Rocket')")
        print(f"Condition:      {result.get('card_condition')}")
        print(f"Card Number:    {result.get('card_number')} (Vintage cards often have no number)")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_vision_appraisal.py <image_path>")
        sys.exit(1)
        
    image_arg = sys.argv[1]
    asyncio.run(test_card_vision(image_arg))
