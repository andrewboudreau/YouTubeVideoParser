import argparse
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image

def extract_text_from_image(image_path: str, model_name: str = "microsoft/trocr-base-printed") -> str:
    # Load the processor and model
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    
    # Open the image file and convert it to RGB
    image = Image.open(image_path).convert("RGB")
    
    # Process the image to get pixel values
    pixel_values = processor(image, return_tensors="pt").pixel_values
    
    # Generate predicted token ids
    generated_ids = model.generate(pixel_values)
    
    # Decode the token ids to text
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return generated_text

def main():
    parser = argparse.ArgumentParser(description="Extract text from an image using the TrOCR model.")
    parser.add_argument("image_path", type=str, help="Path to the image file to be processed.")
    parser.add_argument("--model", type=str, default="microsoft/trocr-base-printed", 
                        help="Model name to use (default: microsoft/trocr-base-printed).")
    
    args = parser.parse_args()
    
    extracted_text = extract_text_from_image(args.image_path, args.model)
    print("Extracted Text:")
    print(extracted_text)

if __name__ == "__main__":
    main()
