def __init__(self):
        """Initialize Gemini service"""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Hardcode the model name to the standard string to be safe
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info(f"✓ Gemini Service initialized: gemini-1.5-flash")