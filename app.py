from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    """Handle search requests"""
    data = request.get_json()
    query = data.get('query', '')
    
    # TODO: Implement search logic here
    results = {
        'query': query,
        'results': []
    }
    
    return jsonify(results)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
