from flask import Flask
from flask_cors import CORS
from compare_invbal import register_routes
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# CORS(app)  # Allow all origins for now; you can restrict this later

# 🚨 Explicit CORS setup
CORS(app,
     supports_credentials=True,
     origins=[
         "https://vue-basic-flame.vercel.app",
         "https://vue-basic-mark-artims-projects.vercel.app",
         "http://localhost:3000"
     ])

# Set a maximum content length for file uploads (20 MB)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB

# Register route(s) from other modules
register_routes(app)

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()
    return {"error": "Internal server error", "message": str(e)}, 500



@app.route('/')
def health_check():
    return {'status': 'Python backend is running!'}

if __name__ == '__main__':
    # Run on Railway’s exposed port
    app.run(host='0.0.0.0', port=8000)
