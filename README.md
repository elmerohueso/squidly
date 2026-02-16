# Squidly

A modern web application framework built with Flask and TypeScript, featuring a clean, modern design inspired by Tidal.

## Features

- 🐍 **Flask Backend** - Lightweight and powerful Python web framework
- 📘 **TypeScript Frontend** - Type-safe JavaScript for better development
- 🎨 **Modern UI** - Clean, dark-themed design with smooth animations
- 🐳 **Docker Ready** - Containerized for easy deployment
- 🔍 **Search Functionality** - Built-in search interface

## Prerequisites

- Docker and Docker Compose (recommended)
- OR:
  - Python 3.11+
  - Node.js 20+

## Quick Start with Docker

1. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   Open your browser to `http://localhost:5000`

## Development Setup (Without Docker)

### Backend Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. **Install Node dependencies:**
   ```bash
   npm install
   ```

2. **Build TypeScript:**
   ```bash
   npm run build
   ```

   Or for development with watch mode:
   ```bash
   npm run dev
   ```

### Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
squidly/
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
├── package.json           # Node dependencies
├── tsconfig.json          # TypeScript configuration
├── webpack.config.js      # Webpack bundler config
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker orchestration
├── src/
│   └── app.ts            # TypeScript entry point
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── styles.css        # Central stylesheet
    └── dist/             # Built assets (generated)
```

## API Endpoints

- `GET /` - Main page
- `POST /api/search` - Search endpoint
- `GET /api/health` - Health check

## Styling

All styles are centralized in `static/styles.css` for consistent design throughout the application. The design features:

- Dark theme with modern color palette
- Smooth transitions and animations
- Responsive design for mobile and desktop
- Custom scrollbar styling

## Development

- **TypeScript:** Edit files in `src/` and run `npm run dev` for auto-compilation
- **Python:** Flask runs in debug mode by default during local development
- **Styles:** Edit `static/styles.css` for styling changes

## Production Deployment

The Docker setup uses a multi-stage build process:

1. Builds TypeScript assets
2. Creates optimized Python runtime
3. Runs with Gunicorn for production performance

To deploy:

```bash
docker-compose up -d
```

## License

MIT

## Contributing

Feel free to submit issues and enhancement requests!
