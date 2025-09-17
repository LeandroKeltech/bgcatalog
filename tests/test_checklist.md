# Test Checklist — Catalog App

## Boardgames
- [ ] Create 5 boardgames (2 with EAN/barcode, 3 by BGG name search)
- [ ] Reference price entered manually (not from BGG)
- [ ] Suggested price = reference × 0.5, rounded to nearest 5 (ties down)
- [ ] Edit final price, confirm rounding
- [ ] Status = awaiting_review after save

## Other Categories
- [ ] Create 5 items (furniture/kitchen/others) with photo
- [ ] At least 2 use LLM suggestion for title/description (manual review required)
- [ ] Reference price and final price rules as above

## Inventory
- [ ] Mark item as sold: decrements stock, increments sold, logs action
- [ ] Prevent marking as sold if stock = 0 (confirmation required)

## Export
- [ ] Export to Google Sheets (Apps Script): upsert by ID
- [ ] Run two exports with edits in between, confirm upsert
- [ ] Export local JSON/CSV

## Scanner Fallback
- [ ] If no scanner app, manual EAN entry and install instructions shown

## Validation
- [ ] Required fields: title, condition/state, reference price > 0, final price > 0
- [ ] At least one photo required to publish
- [ ] Stock cannot go below 0

## UX & Quality
- [ ] App opens quickly, smooth scrolling
- [ ] Clear error messages for scanner, BGG, export
- [ ] Toasters/snackbars for feedback

## Settings
- [ ] Configure Apps Script URL
- [ ] Set image quality/compression
- [ ] Export column order matches contract

## Security & Privacy
- [ ] No PII collected
- [ ] Images stored in app private directory
- [ ] Apps Script key/URL stored locally

## About/Diagnostics (if implemented)
- [ ] Show app version, DB path, item count, image storage usage
