# Jellyfin Playlist Creator

A command-line tool to create Jellyfin playlists based on search criteria.

## Features

- Search for items on your Jellyfin server by multiple terms
- Create new playlists with matching items
- Support for different media types (Audio, Video, Movies, etc.)
- JSON output option for scripting

## Setup

### Prerequisites
- Python 3.7 or higher (for local setup) OR Docker/Docker Compose
- Access to a Jellyfin server with an API key

### Installation

#### Option 1: Local Python Installation

1. Clone or download this project
2. Install dependencies:
```bash
pip install -r requirements.txt
```

#### Option 2: Docker

1. Clone or download this project
2. Build the Docker image:
```bash
docker build -t jellyfin-playlist-creator .
```

Or use docker-compose for easier management:
```bash
docker-compose build
```

### Getting Your API Key

1. Log in to your Jellyfin server at `http://localhost.local:8096/`
2. Go to Dashboard → Settings → API Keys
3. Create a new API key
4. Copy the key for use with this script

### Environment Configuration

Create a `.env` file in the project root:
```
JELLYFIN_SERVER=http://host.docker.internal:8096
JELLYFIN_API_KEY=your_api_key_here
```

Or copy from the provided template:
```bash
cp .env.example .env
# Then edit .env with your actual credentials
```

## Usage

### Local Python

```bash
python jellyfin_playlist_creator.py -s <SERVER_URL> -k <API_KEY> -n <PLAYLIST_NAME> --search <TERMS> [--type <TYPE>] [--output]
```

### Docker

#### Using docker-compose (Recommended)

```bash
# Build the image
docker-compose build

# Run the script (automatically uses .env)
docker-compose run --rm jellyfin-playlist-creator python jellyfin_playlist_creator.py \
  -s $JELLYFIN_SERVER \
  -k $JELLYFIN_API_KEY \
  -n "My Playlist" \
  --search jazz piano
```

The `.env` file is automatically loaded by docker-compose.

On **Windows**, use `host.docker.internal` to reference your host machine. On **Linux**, use `172.17.0.1` or your actual machine IP.

#### Using docker directly

```bash
# Build the image
docker build -t jellyfin-playlist-creator .

# Load .env and run the script
docker run --rm --env-file .env jellyfin-playlist-creator \
  -s $JELLYFIN_SERVER \
  -k $JELLYFIN_API_KEY \
  -n "My Playlist" \
  --search jazz piano \
  --type Audio
```

### Basic Command Structure
```bash
python jellyfin_playlist_creator.py -s <SERVER_URL> -k <API_KEY> -n <PLAYLIST_NAME> --search <TERMS> [--type <TYPE>] [--output]
```

### Arguments

- `-s, --server` (required): Your Jellyfin server URL (e.g., `http://local.local:8096`)
- `-k, --api-key` (required): Your Jellyfin API key
- `-n, --name` (required): Name for the new playlist
- `--search` (required): Space-separated search terms (uses AND logic - items must match all terms)
- `--type` (optional): Type of items to search for
  - `Audio` (default) - Music tracks
  - `Video` - Videos/episodes
  - `Movie` - Movies
  - `Series` - TV series
  - `MusicVideo` - Music videos
- `--output` (optional): Output playlist contents as JSON

### Examples

#### Create a music playlist with "jazz" and "piano"
```bash
python jellyfin_playlist_creator.py \
  -s http://desktop-vsovj37.local:8096 \
  -k 604b8cdc81814f39ae2f0c86a1dab618 \
  -n "ava-addams" \
  --search addams
```

#### Create a video playlist with trailers
```bash
python jellyfin_playlist_creator.py \
  -s http://desktop-vsovj37.local:8096 \
  -k your_api_key_here \
  -n "Movie Trailers" \
  --search trailer \
  --type Video
```

#### Create a playlist and output the results
```bash
python jellyfin_playlist_creator.py \
  -s http://desktop-vsovj37.local:8096 \
  -k your_api_key_here \
  -n "My Playlist" \
  --search classic symphony \
  --output
```

## Output

When using `--output`, the script returns JSON with:
```json
{
  "playlist_id": "playlist-id-here",
  "name": "Playlist Name",
  "item_count": 42,
  "items": [
    {
      "id": "item-id",
      "name": "Item Name",
      "type": "Audio",
      "artist": "Artist Name"
    }
  ]
}
```

## Search Logic

- All search terms are combined with **AND** logic
- An item must match ALL search terms to be included in the playlist
- Search is performed on item names and metadata

## Troubleshooting

### Connection Error
- Verify your server URL is correct
- Check that the Jellyfin server is running
- Ensure your computer can reach the server

### Authentication Error
- Verify your API key is correct
- Check that the API key hasn't been revoked in the Jellyfin settings

### No Items Found
- Try using broader search terms
- Check the spelling of your search terms
- Use the correct `--type` for the content you're searching for

## Notes

- The script searches across your entire Jellyfin library
- Search terms are case-insensitive
- Playlists are created immediately and can be viewed in your Jellyfin client

---

## Tag Current Video (`tag-current-video.sh`)

A Bash script that lets you quickly apply custom tags to the video currently playing in Jellyfin, without leaving your terminal.

### What it does

1. Queries Jellyfin's `/Sessions` endpoint to find what you are currently playing.
2. Fetches the full metadata for that item via `/Items/{id}`.
3. Appends your supplied tags to the item's existing tags, skipping any duplicates.
4. Pushes the updated metadata back to Jellyfin via `POST /Items/{id}`.
5. Prints a confirmation summary.

### Prerequisites

- [`curl`](https://curl.se/) — for making HTTP requests to the Jellyfin API
- [`jq`](https://stedolan.github.io/jq/) — for parsing and transforming JSON

### Configuration

Set the following environment variables (or export them in your shell profile):

| Variable | Default | Description |
|---|---|---|
| `JELLYFIN_URL` | `http://localhost:8096` | Base URL of your Jellyfin server |
| `JELLYFIN_API_KEY` | *(required)* | API key from Dashboard → API Keys |
| `JELLYFIN_USER_ID` | *(required)* | User ID from Dashboard → Users → click user → ID in URL |

```bash
export JELLYFIN_URL="http://localhost:8096"
export JELLYFIN_API_KEY="your-api-key-here"
export JELLYFIN_USER_ID="your-user-id-here"
```

### Usage

```bash
./tag-current-video.sh <tag1> [tag2] [tag3] ...
```

Tags that contain spaces must be quoted:

```bash
./tag-current-video.sh "big cat" dog pickle
```

#### Examples

```bash
# Tag the currently playing video with three tags
./tag-current-video.sh cat dog pickle
# ✅ Tagged "Funny Clip 42" with: 'cat' 'dog' 'pickle'

# Tag with multi-word tags
./tag-current-video.sh "cute animals" funny outdoor
# ✅ Tagged "Garden Video" with: 'cute animals' 'funny' 'outdoor'
```
