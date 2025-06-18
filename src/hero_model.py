# src/hero_model.py

import json
from datetime import datetime
from typing import Dict, List, Any, Optional

class Hero:
    """
    Represents the data structure for a 'Not The End' character sheet.
    This class holds all information about a hero and handles serialization
    to and from JSON format.
    """
    def __init__(self):
        # Basic Info
        self.name: str = "New Hero"
        self.concept: str = "" # "I would risk everything for..."
        self.last_updated: str = datetime.utcnow().isoformat()

        # The Hexagon Hive: 19 traits total.
        # Each trait can hold a success token 'O'.
        # We will represent this as a dict where the value is another dict
        # containing the text and the number of tokens.
        self.traits: Dict[str, Dict[str, Any]] = {
            # Archetype
            "archetype": {"text": "", "tokens": 0},
            # 6 Qualities (3 used at creation) 
            "q1": {"text": "", "tokens": 0}, "q2": {"text": "", "tokens": 0},
            "q3": {"text": "", "tokens": 0}, "q4": {"text": "", "tokens": 0},
            "q5": {"text": "", "tokens": 0}, "q6": {"text": "", "tokens": 0},
            # 12 Abilities (4 used at creation) 
            "a1": {"text": "", "tokens": 0}, "a2": {"text": "", "tokens": 0},
            "a3": {"text": "", "tokens": 0}, "a4": {"text": "", "tokens": 0},
            "a5": {"text": "", "tokens": 0}, "a6": {"text": "", "tokens": 0},
            "a7": {"text": "", "tokens": 0}, "a8": {"text": "", "tokens": 0},
            "a9": {"text": "", "tokens": 0}, "a10": {"text": "", "tokens": 0},
            "a11": {"text": "", "tokens": 0}, "a12": {"text": "", "tokens": 0},
        }

        # Resources: A list of 3 to 5 useful items or contacts.
        self.resources: List[str] = []

        # Scars: Can be added to the hive, but are mechanically different.
        # A scar adds a complication token '●' to the bag.
        # For simplicity in the data model, we'll track them similarly to traits.
        # The UI will render them differently (underlined).
        self.scars: Dict[str, Dict[str, Any]] = {}

        # Lessons: Special abilities learned by the hero.
        self.lessons: List[str] = []

        # Misfortunes: Negative conditions that add '●' to the bag.
        # A dict mapping the misfortune name to the number of '●' tokens.
        self.misfortunes: Dict[str, int] = {}

        # Mind State
        self.adrenaline: int = 0 # Number of '●' tokens on Adrenaline
        self.confusion: int = 0  # Number of '●' tokens on Confusion

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Hero instance into a dictionary for JSON serialization."""
        self.last_updated = datetime.utcnow().isoformat()
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Hero':
        """Creates a Hero instance from a dictionary."""
        hero = cls()
        for key, value in data.items():
            if hasattr(hero, key):
                setattr(hero, key, value)
        return hero

    def save_to_file(self, filepath: str):
        """Saves the hero's data to a JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4)

    @staticmethod
    def load_from_file(filepath: str) -> Optional['Hero']:
        """Loads a hero's data from a JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Hero.from_dict(data)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

# Example Usage & Test
if __name__ == "__main__":
    print("Testing Hero Model...")

    # Create a sample hero based on Lothar from the rulebook 
    lothar = Hero()
    lothar.name = "Lothar"
    lothar.concept = "A deep sense of justice, hardened by many battles."
    
    # Set traits 
    lothar.traits["archetype"]["text"] = "Bounty Hunter"
    lothar.traits["q1"]["text"] = "Veteran"
    lothar.traits["q2"]["text"] = "Cunning"
    lothar.traits["q3"]["text"] = "Frightening"
    lothar.traits["a1"]["text"] = "Archery"
    lothar.traits["a2"]["text"] = "Investigate"
    lothar.traits["a3"]["text"] = "Pass unnoticed"
    lothar.traits["a4"]["text"] = "Interrogate"

    # Set resources 
    lothar.resources = [
        "Metal handcuffs",
        "Bow and arrows",
        "Sturdy clothes",
        "Bounty hunter license",
        "50 coins"
    ]
    
    # Add a misfortune for testing 
    lothar.misfortunes["Hunted"] = 1

    # Save the hero to a file
    file_path = "lothar_hero_sheet.json"
    lothar.save_to_file(file_path)
    print(f"'{lothar.name}' saved to {file_path}")

    # Load the hero from the file
    loaded_lothar = Hero.load_from_file(file_path)
    if loaded_lothar:
        print(f"Successfully loaded '{loaded_lothar.name}'.")
        print(f"Archetype: {loaded_lothar.traits['archetype']['text']}")
        print(f"Resources: {loaded_lothar.resources}")
        print(f"Misfortunes: {loaded_lothar.misfortunes}")
        # Verify data integrity
        assert lothar.name == loaded_lothar.name
        assert lothar.resources == loaded_lothar.resources
        print("Data integrity check passed.")

    # Show the JSON structure
    print("\n--- Sample JSON Output ---")
    print(json.dumps(lothar.to_dict(), indent=4))