print("WARNING: I made it to the top line of main.py")

from flask import Flask, request
from flask_cors import CORS
from compare_invbal import register_routes
from csv_processor import register_csv_routes
import logging
import sys, os

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.info("Logging initialized")
logger = logging.getLogger(__name__)
logger.info("[main.py] Starting Flask server setup...")

app = Flask(__name__)

# Explicit CORS setup
CORS(app,
     supports_credentials=True,
     origins=[
         "https://vue-basic-flame.vercel.app",
         "https://vue-basic-mark-artims-projects.vercel.app",
         "http://localhost:3000"
     ])
logger.info("[main.py] CORS configured.")

# Max upload size for file processing
app.config['MAX_CONTENT_LENGTH'] = 40 * 1024 * 1024  # 40 MB
logger.info("[main.py] MAX_CONTENT_LENGTH set to 40MB.")

# Register API routes
register_routes(app)
register_csv_routes(app)
logger.info("[main.py] Routes registered (compare_invbal, csv_processor, etc.).")

# Request logging middleware
@app.before_request
def log_request():
    logger.info(f"[REQUEST] {request.method} {request.path} from {request.remote_addr}")
    if request.form:
        logger.info(f"[FORM DATA] {dict(request.form)}")

# Global error handler to log tracebacks
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()
    logger.error("[main.py] Unhandled Exception", exc_info=True)
    return {"error": "Internal server error", "message": str(e)}, 500

# Root health check at root path
@app.route('/')
def root_health_check():
    logger.info("[main.py] / health check was called.")
    return {'status': 'Python backend is running!'}

# Dedicated /health endpoint used by deployment platforms
@app.route('/health')
def health_check():
    logger.info("[main.py] /health endpoint was called.")
    return {'status': 'ok'}

if __name__ == '__main__':
    logger.info("[main.py] Flask server is starting...")
    port = int(os.environ.get("PORT", 5000))
    print("main.py booting up")
    app.run(host='0.0.0.0', port=port)

    

