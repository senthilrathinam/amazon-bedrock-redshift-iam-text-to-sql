"""
Profile manager for storing and switching between connection profiles.
"""
import json
import os
from pathlib import Path


class ProfileManager:
    """Manages connection profiles for the application."""
    
    def __init__(self):
        """Initialize profile manager."""
        self.config_dir = Path.home() / '.genai_sales_analyst'
        self.profiles_file = self.config_dir / 'profiles.json'
        self.config_file = self.config_dir / 'config.json'
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(exist_ok=True)
    
    def get_profiles(self):
        """Get all saved profiles."""
        if not self.profiles_file.exists():
            return self._get_default_profiles()
        
        try:
            with open(self.profiles_file, 'r') as f:
                return json.load(f)
        except:
            return self._get_default_profiles()
    
    def _get_default_profiles(self):
        """Get default profiles."""
        return {
            "demo": {
                "name": "Demo (Northwind)",
                "type": "demo",
                "host": "localhost",
                "port": "5439",
                "database": "sales_analyst",
                "schema": "northwind",
                "user": "admin",
                "password": "Awsuser123$",
                "description": "Sample Northwind database"
            }
        }
    
    def save_profiles(self, profiles):
        """Save profiles to file."""
        with open(self.profiles_file, 'w') as f:
            json.dump(profiles, f, indent=2)
    
    def get_active_profile(self):
        """Get the currently active profile name."""
        if not self.config_file.exists():
            return "demo"
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('active_profile', 'demo')
        except:
            return "demo"
    
    def set_active_profile(self, profile_name):
        """Set the active profile."""
        config = {'active_profile': profile_name}
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def add_profile(self, profile_id, profile_data):
        """Add a new profile."""
        profiles = self.get_profiles()
        profiles[profile_id] = profile_data
        self.save_profiles(profiles)
    
    def delete_profile(self, profile_id):
        """Delete a profile."""
        profiles = self.get_profiles()
        if profile_id in profiles and profile_id != 'demo':
            del profiles[profile_id]
            self.save_profiles(profiles)
    
    def is_first_run(self):
        """Check if this is the first run."""
        return not self.config_file.exists()
    
    def mark_setup_complete(self):
        """Mark setup as complete."""
        config = {
            'active_profile': self.get_active_profile(),
            'setup_complete': True
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
