# Timetagger Analytics App

Streamlit application for visualizing Timetagger time tracking data.

## Features

- **Date Range Selection**: Filter records by start and end dates
- **Multi-level Sunburst Chart**: Visualize time distribution by tags with selectable hierarchy depth (1-5 levels)
- **Stacked Bar Chart**: View time distribution grouped by time periods (days/weeks/months) and level 1 tags
- **Record Splitting**: Automatically splits records that span multiple time periods across boundaries

## Prerequisites

1. **Timetagger must be running first** - The analytics app requires access to the Timetagger database
2. **Database path must be known** - You need to determine the path to the database file inside the container

## Setup Instructions

### 1. Start Timetagger

First, ensure Timetagger is running (see main [README.md](../README.md)):

```bash
docker-compose --env-file .env up -d timetagger
```

### 2. Find Database Path

Determine the path to the database file inside the Timetagger container:

```bash
# Get the container name
docker ps | grep timetagger

# Enter the container
docker exec -it <timetagger_container_name> sh

# Find the database file
find ${TIMETAGGER_DATADIR} -name "*.db" -type f

# Or check the structure
ls -la ${TIMETAGGER_DATADIR}/_timetagger/users/
```

The path will typically be: `${TIMETAGGER_DATADIR}/_timetagger/users/pe51k~cGU1MWs=.db`

### 3. Update .env File

Add the following variables to your `.env` file:

```bash
# Analytics App Configuration
ANALYTICS_PORT=8501
TIMETAGGER_DB_PATH=/data/timetagger/_timetagger/users/pe51k~cGU1MWs=.db
```

⚠️ **Important**: 
- `TIMETAGGER_DB_PATH` must match the path **inside the container** after volume mounting
- If `TIMETAGGER_DATADIR=/data/timetagger`, then use `/data/timetagger/_timetagger/users/pe51k~cGU1MWs=.db`
- The path should match where the volume is mounted in the analytics container

### 4. Start Analytics App

```bash
docker-compose --env-file .env up -d analytics
```

The app will be available at `http://localhost:${ANALYTICS_PORT}` (default: 8501).

## Environment Variables

Required variables in `.env`:

- `ANALYTICS_PORT`: Port for the Streamlit app (e.g., `8501`)
- `TIMETAGGER_DB_PATH`: Full path to the database file inside the container (must match the volume mount path)

## Local Development

For local development without Docker:

```bash
# Install dependencies
uv pip install streamlit pandas plotly

# Set database path
export TIMETAGGER_DB_PATH=/path/to/your/database.db

# Run the app
streamlit run app.py
```

## Project Structure

```
analytics_app/
├── app.py              # Main Streamlit application
├── db.py               # Database connection and query utilities
├── Dockerfile          # Docker configuration
├── pyproject.toml      # Python dependencies
└── README.md          # This file
```

## Troubleshooting

### Database file not found

- Verify `TIMETAGGER_DB_PATH` matches the actual path inside the container
- Check that the volume is mounted correctly in `docker-compose.yaml`
- Ensure Timetagger container is running and has created the database

### Port already in use

- Change `ANALYTICS_PORT` in `.env` to a different port
- Or stop the service using port 8501

### No data displayed

- Check that the date range includes records
- Verify the database contains time tracking records
- Check container logs: `docker-compose logs analytics`

