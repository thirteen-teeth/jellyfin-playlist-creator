#!/usr/bin/env python3
"""
Jellyfin Playlist Creator - Create playlists from CLI arguments
"""

import argparse
import json
import sys
import requests
from urllib.parse import urljoin
from typing import List, Dict, Optional


class JellyfinPlaylistCreator:
    def __init__(self, server_url: str, api_key: str):
        """
        Initialize the Jellyfin playlist creator.
        
        Args:
            server_url: Base URL of your Jellyfin server (e.g., http://localhost:8096)
            api_key: Jellyfin API key for authentication
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'X-MediaBrowser-Token': self.api_key})
        
    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """Make a request to the Jellyfin API."""
        url = urljoin(self.server_url, f'/jellyfin/Items{endpoint}')
        
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}", file=sys.stderr)
            sys.exit(1)
    
    def search_items(self, search_terms: List[str], item_type: str = 'Audio', verbose: bool = False, limit: int = 1000) -> List[Dict]:
        """
        Search for items on the Jellyfin server by file path.
        
        Args:
            search_terms: List of search terms to match in file paths (AND logic)
            item_type: Type of items to search for (Audio, Video, etc.)
            verbose: Enable verbose output for debugging
            limit: Maximum number of items to retrieve (default: 1000)
        
        Returns:
            List of items matching the search criteria
        """
        try:
            # Get user ID first
            user_id = self.get_user_id()
            if not user_id:
                print("Error: Could not get user ID", file=sys.stderr)
                return []
            
            if verbose:
                print(f"[DEBUG] Using User ID: {user_id}", file=sys.stderr)
            
            # Recursively fetch all items from all libraries
            params = {
                'limit': limit,
                'recursive': 'true'
            }
            
            url = f"{self.server_url}/Users/{user_id}/Items"
            if verbose:
                print(f"[DEBUG] Fetching all items from: {url}", file=sys.stderr)
                print(f"[DEBUG] Params: {params}", file=sys.stderr)
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if verbose:
                print(f"[DEBUG] Full API Response:\n{json.dumps(data, indent=2)}", file=sys.stderr)
            
            items = data.get('Items', [])
            print(f"Found {len(items)} total items", file=sys.stderr)
            
            if verbose and items:
                print(f"[DEBUG] Sample items:", file=sys.stderr)
                for item in items[:3]:
                    print(f"  - Name: {item.get('Name')}, Type: {item.get('Type')}, Path: {item.get('Path')}", file=sys.stderr)
            
            # Filter items by file path - all search terms must be present
            filtered_items = []
            search_terms_lower = [term.lower() for term in search_terms]
            
            for item in items:
                path = item.get('Path', '').lower()
                name = item.get('Name', '').lower()
                item_type_actual = item.get('Type', '')
                
                # Skip folders and collections
                if item_type_actual in ['Folder', 'CollectionFolder']:
                    continue
                
                if verbose:
                    print(f"[DEBUG] Checking: {item.get('Name')} (Type: {item_type_actual}) | Path: {path}", file=sys.stderr)
                    for term in search_terms_lower:
                        path_match = term in path
                        name_match = term in name
                        print(f"  Term '{term}': in_path={path_match}, in_name={name_match}", file=sys.stderr)
                
                # Check if all search terms are in the file path or name
                if all(term in path or term in name for term in search_terms_lower):
                    filtered_items.append(item)
                    print(f"  ✓ {item.get('Name')} ({item_type_actual}): {path}", file=sys.stderr)
            
            print(f"Found {len(filtered_items)} items matching search terms", file=sys.stderr)
            return filtered_items
            
        except requests.exceptions.RequestException as e:
            print(f"Error searching items: {e}", file=sys.stderr)
            return []
    
    def get_playlists(self, name: str = None) -> List[Dict]:
        """
        Get playlists, optionally filtered by name.
        
        Args:
            name: Optional playlist name to filter by
        
        Returns:
            List of playlists
        """
        try:
            user_id = self.get_user_id()
            if not user_id:
                print("Error: Could not get user ID for fetching playlists", file=sys.stderr)
                return []

            # Correct endpoint to get playlists for a user
            url = f"{self.server_url}/Users/{user_id}/Items"
            params = {
                'includeItemTypes': 'Playlist',
                'recursive': 'true'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            playlists = data.get('Items', [])
            
            if name:
                playlists = [p for p in playlists if p.get('Name', '').lower() == name.lower()]
            
            return playlists
        except requests.exceptions.RequestException as e:
            print(f"Error getting playlists: {e}", file=sys.stderr)
            return []
    
    def delete_playlist(self, playlist_id: str) -> bool:
        """
        Delete a playlist by ID.
        
        Args:
            playlist_id: ID of the playlist to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Correct endpoint for deleting a playlist
            url = f"{self.server_url}/Items/{playlist_id}"
            response = self.session.delete(url)
            response.raise_for_status()
            print(f"Deleted existing playlist with ID: {playlist_id}", file=sys.stderr)
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error deleting playlist: {e}", file=sys.stderr)
            return False
    
    def create_playlist(self, name: str, item_ids: List[str], unique_id: str = None) -> Optional[str]:
        """
        Create a new playlist with the given items, overwriting any existing playlist with the same unique_id.
        
        Args:
            name: Name of the playlist
            item_ids: List of item IDs to add to the playlist
            unique_id: Unique identifier to prevent duplicate playlists
        
        Returns:
            Playlist ID if successful, None otherwise
        """
        try:
            # If unique_id provided, delete any existing playlists with the same id in description/name
            if unique_id:
                playlists = self.get_playlists()
                
                # Look for playlist with matching unique_id in name and delete all matches
                for playlist in playlists:
                    if f"[{unique_id}]" in playlist.get('Name', ''):
                        self.delete_playlist(playlist['Id'])
            
            url = f"{self.server_url}/Playlists"
            user_id = self.get_user_id()
            
            # Add unique_id to name if provided
            playlist_name = f"{name} [{unique_id}]" if unique_id else name
            
            # Step 1: Create the empty playlist first (without items)
            data = {
                'Name': playlist_name,
                'Ids': [],  # Start with empty list
                'UserId': user_id
            }
            
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            
            playlist_id = result.get('Id')
            if not playlist_id:
                print(f"Error: No playlist ID returned from API", file=sys.stderr)
                return None
            
            print(f"Playlist '{playlist_name}' created with ID: {playlist_id}", file=sys.stderr)
            
            # Step 2: Add items to the playlist if there are any
            if item_ids:
                add_url = f"{self.server_url}/Playlists/{playlist_id}/Items"
                # Pass IDs as query parameters, comma-delimited
                params = {
                    'ids': ','.join(item_ids),
                    'userId': user_id
                }
                
                response = self.session.post(add_url, params=params)
                response.raise_for_status()
                print(f"Added {len(item_ids)} items to playlist", file=sys.stderr)
            
            print(f"Playlist '{playlist_name}' created successfully", file=sys.stderr)
            return playlist_id
            
        except requests.exceptions.RequestException as e:
            print(f"Error creating playlist: {e}", file=sys.stderr)
            return None
    
    def add_items_to_playlist(self, playlist_id: str, item_ids: List[str]) -> bool:
        """
        Add items to an existing playlist.
        
        Args:
            playlist_id: ID of the playlist
            item_ids: List of item IDs to add
        
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.server_url}/Playlists/{playlist_id}/Items"
            user_id = self.get_user_id()
            
            # Pass IDs as query parameters, comma-delimited
            params = {
                'ids': ','.join(item_ids),
                'userId': user_id
            }
            
            response = self.session.post(url, params=params)
            response.raise_for_status()
            print(f"Added {len(item_ids)} items to playlist", file=sys.stderr)
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Error adding items to playlist: {e}", file=sys.stderr)
            return False
    
    def get_user_id(self) -> Optional[str]:
        """Get the current user ID."""
        try:
            url = f"{self.server_url}/Users"
            response = self.session.get(url)
            response.raise_for_status()
            users = response.json()
            
            if users:
                return users[0]['Id']
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error getting user ID: {e}", file=sys.stderr)
            return None


def main():
    parser = argparse.ArgumentParser(
        description='Create Jellyfin playlists from CLI arguments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create a video playlist with items in path containing "addams" (default type)
  python jellyfin_playlist_creator.py -s http://localhost:8096 -k YOUR_API_KEY \\
    -n "Addams Family" --search addams
  
  # Create a music playlist with items in path containing both "jazz" and "piano"
  python jellyfin_playlist_creator.py -s http://localhost:8096 -k YOUR_API_KEY \\
    -n "Jazz Piano" --search jazz piano --type Audio
        '''
    )
    
    parser.add_argument('-s', '--server', required=True, 
                       help='Jellyfin server URL (e.g., http://localhost:8096)')
    parser.add_argument('-k', '--api-key', required=True,
                       help='Jellyfin API key for authentication')
    parser.add_argument('-n', '--name', required=True,
                       help='Name of the playlist to create')
    parser.add_argument('--search', nargs='+', required=True,
                       help='Search terms to find in file paths (space-separated, all must match)')
    parser.add_argument('--type', default='Movie',
                       choices=['Audio', 'Video', 'Movie', 'Series', 'MusicVideo'],
                       help='Type of items to search for (default: Movie)')
    parser.add_argument('--output', action='store_true',
                       help='Output playlist contents as JSON')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output for debugging')
    parser.add_argument('--limit', type=int, default=10000,
                       help='Maximum number of items to retrieve (default: 10000)')
    
    args = parser.parse_args()
    
    # Initialize the creator
    creator = JellyfinPlaylistCreator(args.server, args.api_key)
    
    print(f"Searching for items matching: {', '.join(args.search)}", file=sys.stderr)
    
    # Search for items
    items = creator.search_items(args.search, args.type, verbose=args.verbose, limit=args.limit)
    
    if not items:
        print("No items found matching the search criteria", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(items)} items matching all search terms", file=sys.stderr)
    
    # Extract item IDs
    item_ids = [item['Id'] for item in items]
    
    # Create the playlist
    playlist_id = creator.create_playlist(args.name, item_ids, unique_id=args.name)
    
    if not playlist_id:
        print("Failed to create playlist", file=sys.stderr)
        sys.exit(1)
    
    # Output playlist contents if requested
    if args.output:
        output = {
            'playlist_id': playlist_id,
            'name': args.name,
            'item_count': len(items),
            'items': [
                {
                    'id': item['Id'],
                    'name': item.get('Name', 'Unknown'),
                    'type': item.get('Type', 'Unknown'),
                    'artist': item.get('AlbumArtist', item.get('SeriesName', 'N/A'))
                }
                for item in items
            ]
        }
        print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
