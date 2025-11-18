#!/usr/bin/env python3
"""
Reset setup state for GenAI Sales Analyst
"""
from src.utils.setup_state import SetupState

def main():
    setup_state = SetupState()
    setup_state.reset_state()
    print("✅ Setup state reset successfully!")
    print("You can now start fresh with Option 1, 2, or 3")

if __name__ == "__main__":
    main()
