# Momos Fanhao Diary

This is a static website project for Momos Fanhao Diary.

## Project Structure

- `generate/`: Python scripts for static page generation.
- `templates/`: Jinja2 templates (HTML pages).
- `output/`: All static HTML output (website root).
- `public/`: Static assets (images, CSS, JS).
- `scripts/`: Sitemap and automation tools.
- `build_all.py`: Script to generate the entire site.
- `vercel.json`: Vercel deployment configuration.
- `.env.example`: Example environment variables (rename to .env).
- `requirements.txt`: Python dependencies.
- `README.md`: Project description.

## Setup

1.  Rename `.env.example` to `.env` and fill in your actual configuration values.
2.  Install Python dependencies: `pip install -r requirements.txt`
3.  Run the build script: `python build_all.py`

## Deployment

This project is configured for Vercel deployment. 