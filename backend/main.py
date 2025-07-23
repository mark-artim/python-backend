from flask import Flask
from flask_cors import CORS
from compare_invbal import register_routes
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("🚀 [main.py] Starting Flask server setup...")

app = Flask(__name__)

# 🚨 Explicit CORS setup
CORS(app,
     supports_credentials=True,
     origins=[
         "https://vue-basic-flame.vercel.app",
         "https://vue-basic-mark-artims-projects.vercel.app",
         "http://localhost:3000"
     ])
logger.info("✅ [main.py] CORS configured.")

# Max upload size for file processing
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB
logger.info("✅ [main.py] MAX_CONTENT_LENGTH set to 20MB.")

# Register API routes
register_routes(app)
logger.info("✅ [main.py] Routes registered (compare_invbal, etc.).")

# Global error handler to log tracebacks
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()
    logger.error("[main.py] ❌ Unhandled Exception", exc_info=True)
    return {"error": "Internal server error", "message": str(e)}, 500

# Root health check
@app.route('/')
def health_check():
    logger.info("✅ [main.py] / health check was called.")
    return {'status': 'Python backend is running!'}

if __name__ == '__main__':
    logger.info("🚀 [main.py] Flask server is starting on port 8000...")
    app.run(host='0.0.0.0', port=8000)
