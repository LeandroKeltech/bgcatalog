# Catalog App (Kivy/KivyMD)

A simple Android app for cataloging boardgames, furniture, kitchen, and other items, with export to Google Sheets.

## Features
- Barcode scanning (boardgames)
- Photo capture (all categories)
- Local SQLite database
- Price rules and rounding
- Manual review before publishing
- Export to Google Sheets (Apps Script)
- Inventory management and logs

## Installation & Build
1. Install [Python 3.8+](https://www.python.org/)
2. Install [Buildozer](https://github.com/kivy/buildozer) on Linux (WSL recommended for Windows)
3. Clone this repo and run:
   ```
   pip install -r requirements.txt
   python db/models.py  # Create DB tables
   buildozer -v android debug  # Build APK
   ```
4. Transfer APK to your Android device and install (enable sideloading)

## First Use
- Grant camera and storage permissions
- Configure your Google Apps Script URL in Settings

## Export
- Select items and tap Export to send to Google Sheets
- See feedback for success or error

## Backup
- Export local JSON/CSV from the Export screen

## Known Limitations
- Barcode scanning requires a scanner app (ZXing/ML Kit). If not installed, manual EAN entry is available.
- No two-way sync with Sheets.
- LLM features are optional and not required for core flows.

## Test Checklist
See `tests/test_checklist.md` for acceptance criteria.
