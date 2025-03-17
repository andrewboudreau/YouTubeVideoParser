from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import cv2
import threading

class OCRProcessor:
    def __init__(self, model_name="microsoft/trocr-base-printed"):
        self.model_name = model_name
        self.model_loaded = False
        self.processor = None
        self.model = None
        
        # Start loading in a separate thread
        self.load_thread = threading.Thread(target=self.load_model)
        self.load_thread.daemon = True
        self.load_thread.start()
    
    def load_model(self):
        """Load the TrOCR model in a background thread"""
        try:
            self.processor = TrOCRProcessor.from_pretrained(self.model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(self.model_name)
            self.model_loaded = True
            print("TrOCR model loaded successfully")
        except Exception as e:
            print(f"Error loading TrOCR model: {str(e)}")
    
    def extract_text(self, image):
        """Extract text from an image using TrOCR"""
        if not self.model_loaded:
            return None
            
        try:
            # If image is a numpy array (OpenCV format), convert to PIL
            if isinstance(image, cv2.UMat) or (hasattr(image, 'shape') and len(image.shape) == 3):
                # Convert OpenCV BGR to RGB for PIL
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_image)
            elif isinstance(image, Image.Image):
                pil_image = image
            else:
                raise ValueError("Unsupported image format")
                
            # Process the image with TrOCR
            pixel_values = self.processor(pil_image, return_tensors="pt").pixel_values
            generated_ids = self.model.generate(pixel_values, max_new_tokens=50)
            extracted_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            return extracted_text.strip()
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return None
    
    def clean_numeric_text(self, text):
        """Clean text to extract only numeric values (with decimal points)"""
        if not text:
            return ""
            
        # Remove '$' and spaces
        cleaned = text.replace('$', '').replace(' ', '')
        
        # Keep only digits and decimal points
        result = ''.join(char for char in cleaned if char.isdigit() or char == '.')
        
        # Try to convert to float to validate it's a number
        try:
            value = float(result)
            # Cap minimum value at 0
            if value < 0:
                value = ""
            # Ignore values over 50000
            if value > 50000:
                return ""
            return str(value)
        except ValueError:
            # If it's not a valid number, return empty string
            return ""
