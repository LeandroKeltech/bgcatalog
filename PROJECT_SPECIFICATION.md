# Board Game Catalog - Complete Project Specification

## Project Overview
A Django-based web application for managing and selling a board game collection with integrated pricing from BoardGameGeek (BGG) and BoardGamePrices APIs.

**Live Production URL:** https://bgcatalog.fly.dev  
**Repository:** LeandroKeltech/bgcatalog (GitHub)  
**Framework:** Django 5.2.7 + PostgreSQL  
**Hosting:** Fly.io with automatic CI/CD via GitHub Actions  

---

## Core Features

### 1. Board Game Catalog Management
- **Public Catalog** (`/catalog/`) - Browse available games with filtering and search
- **Admin Panel** (`/admin-panel/`) - Full CRUD operations for board games
- **Game Details** - Comprehensive game information display with images, ratings, and metadata

### 2. BoardGameGeek Integration
**Challenge:** BGG API blocks Fly.io datacenter IPs with 401 Unauthorized errors

**Current Solution - Multi-tier Fallback Strategy:**
1. **Primary:** BGG XML API2 (3 retry strategies with different headers/sessions)
2. **Fallback #1:** Board Game Atlas API (https://www.boardgameatlas.com)
3. **Fallback #2:** BGG web scraping with BeautifulSoup4
4. **Enhancement:** When BGA returns data, enrich with BGG web scraping if BGG ID is found

**Data Extracted:**
- Basic info: Name, Year, Designer, Description
- Gameplay: Min/Max Players, Playtime, Minimum Age
- Categories & Mechanics
- Ratings: Average rating, number of ratings, BGG rank
- Images: Thumbnails and full-size images
- Pricing from BoardGamePrices.co.uk

**Search Features:**
- Text search with fuzzy matching
- Barcode scanner integration (QuaggaJS) for UPC/EAN lookup
- Thumbnail previews in search results

### 3. Stock Reservation System
**Purpose:** Prevent overselling by temporarily holding stock when customers request quotes

**Implementation:**
- `StockReservation` model with states: active, confirmed, cancelled, expired
- 30-minute automatic reservation on checkout
- Atomic transactions to prevent race conditions
- Available quantity = `stock_quantity - reserved_quantity`

**Admin Features:**
- Reservation management interface
- Confirm sale (reduces stock permanently)
- Cancel reservation (releases stock)
- Extend reservation time
- Automatic expiry after timeout

### 4. Shopping Cart & Checkout
- Session-based cart (no login required)
- Add/remove games, update quantities
- Real-time stock validation
- Email quote system (currently console backend for development)
- Creates stock reservations on checkout

### 5. Pricing & Discounts
- MSRP pricing from BoardGamePrices API
- Manual discount percentage system
- Final price calculation: `final_price = msrp_price * (1 - discount/100)`
- GBP to EUR conversion (rate: 1.17)
- Price display includes shipping estimates

---

## Technical Architecture

### Database Schema

**BoardGame Model:**
```python
- name: CharField (required)
- bgg_id: CharField (unique, optional) - BoardGameGeek ID or BGA ID (prefixed with 'bga_')
- year_published: IntegerField
- designer: CharField
- description: TextField
- image_url: URLField
- thumbnail_url: URLField
- min_players, max_players: IntegerField
- min_playtime, max_playtime: IntegerField
- min_age: IntegerField
- categories, mechanics: CharField (comma-separated)
- rating_average, rating_bayes: FloatField
- rank_overall, num_ratings: IntegerField
- msrp_price: DecimalField
- discount_percentage: IntegerField (default: 0)
- stock_quantity: IntegerField (default: 1)
- condition: CharField (choices: new, like_new, very_good, good, acceptable)
- is_sold: BooleanField
- sold_date: DateTimeField
- notes: TextField (admin only)
- created_at, updated_at: DateTimeField
```

**StockReservation Model:**
```python
- game: ForeignKey(BoardGame)
- quantity: IntegerField
- status: CharField (choices: active, confirmed, cancelled, expired)
- customer_name, customer_email, customer_phone: CharField
- session_key: CharField
- reserved_at: DateTimeField
- expires_at: DateTimeField (reserved_at + 30 minutes)
- confirmed_at, cancelled_at: DateTimeField
- admin_notes: TextField
```

### API Integrations

**BoardGameGeek XML API2:**
- Search: `https://boardgamegeek.com/xmlapi2/search`
- Details: `https://boardgamegeek.com/xmlapi2/thing`
- **Issue:** Returns 401 from Fly.io IPs

**Board Game Atlas API:**
- Endpoint: `https://api.boardgameatlas.com/api/search`
- Client ID: `JMc8dOwiQE` (public test key)
- Free tier: 100 requests/month
- Returns: game details, images, ratings, but sometimes missing designer/year

**BoardGamePrices API:**
- Endpoint: `https://www.boardgameprices.co.uk/plugin/info`
- Fetches lowest EU/UK prices for games
- Currency: EUR (Ireland market)
- Fallback: GBP with conversion

**Web Scraping (BeautifulSoup4):**
- BGG search page: Extract game links, names, years from HTML tables
- BGG game page: Extract all metadata via regex and element selectors
- Handles different HTML structures (old vs new BGG layout)

### File Structure
```
bgcatalog/
├── catalog/
│   ├── models.py           # BoardGame, StockReservation
│   ├── views.py            # Public catalog views
│   ├── admin_views.py      # Admin panel views
│   ├── cart_views.py       # Shopping cart & checkout
│   ├── bgg_views.py        # BGG search & import
│   ├── bgg_price_service.py # BGG/BGA API integration
│   ├── urls.py             # URL routing
│   ├── templates/catalog/  # Django templates
│   │   ├── public_catalog.html
│   │   ├── game_detail.html
│   │   ├── cart.html
│   │   ├── bgg_search.html
│   │   ├── reservation_management.html
│   │   └── ...
│   └── static/catalog/
│       ├── styles.css
│       └── js/barcode_scanner.js
├── bgcatalog/
│   ├── settings.py         # Django settings
│   └── urls.py             # Root URL config
├── .github/workflows/
│   └── fly-deploy.yml      # CI/CD pipeline
├── fly.toml                # Fly.io configuration
├── requirements.txt        # Python dependencies
└── manage.py
```

### Key Dependencies
```
Django==5.2.7
psycopg2-binary==2.9.10    # PostgreSQL adapter
requests==2.32.3            # HTTP requests
beautifulsoup4==4.12.3      # Web scraping
lxml==5.3.0                 # XML parsing
urllib3==2.2.3              # HTTP library
gunicorn==23.0.0            # Production WSGI server
whitenoise==6.8.2           # Static file serving
```

### Frontend Technologies
- **Bootstrap 5** - UI framework
- **Bootstrap Icons** - Icon library
- **QuaggaJS** - Barcode scanning (UPC/EAN support)
- **Vanilla JavaScript** - No heavy frameworks
- **Responsive Design** - Mobile-first approach

---

## Deployment & Infrastructure

### Fly.io Configuration
- **App Name:** bgcatalog
- **Region:** lhr (London)
- **Database:** Fly Postgres
- **Environment Variables:**
  - `SECRET_KEY` - Django secret
  - `DATABASE_URL` - PostgreSQL connection string
  - `ALLOWED_HOSTS` - bgcatalog.fly.dev
  - `DEBUG` - False in production

### CI/CD Pipeline (GitHub Actions)
**Trigger:** Push to main branch

**Workflow:**
1. Checkout code
2. Setup Fly.io CLI
3. Deploy to Fly.io (`flyctl deploy`)
4. Run migrations automatically
5. Collect static files

**File:** `.github/workflows/fly-deploy.yml`

### Static Files
- Served via WhiteNoise in production
- Collected to `/static/` during deployment
- CDN-ready (can add Cloudflare in future)

---

## Current Issues & Solutions

### Issue 1: BGG API 401 Errors
**Problem:** BGG blocks requests from Fly.io datacenter IPs  
**Solution:** Multi-tier fallback (BGA API → Web Scraping)  
**Status:** Working with fallbacks

### Issue 2: Incomplete BGA Data
**Problem:** Board Game Atlas sometimes missing year, designer, detailed description  
**Solution:** Extract BGG ID from BGA data, enrich via BGG web scraping  
**Status:** Implemented, needs testing

### Issue 3: Web Scraping Extraction
**Problem:** BGG HTML structure varies, game names in search results sometimes empty  
**Solution:** Multiple extraction strategies, fallback text parsing  
**Status:** Improved with extensive logging

### Issue 4: Missing Metadata in Templates
**Problem:** Designer, year, player count not displaying in UI  
**Solution:** Ensure BGA data mapping + BGG scraping enrichment  
**Status:** In progress with debug logging

---

## User Workflows

### Admin Workflow
1. **Add New Game:**
   - Search BGG/BGA by name or barcode
   - Select game from results
   - Review auto-populated data (name, year, designer, images, etc.)
   - Set stock quantity, condition, discount
   - Save to catalog

2. **Manage Inventory:**
   - View all games in admin panel
   - Edit game details, pricing, stock
   - Mark games as sold
   - Delete games from catalog

3. **Handle Reservations:**
   - View pending reservations
   - Confirm sales (reduces stock)
   - Cancel reservations (releases stock)
   - Extend reservation time if needed

### Customer Workflow
1. **Browse Catalog:**
   - View all available games
   - Filter by condition, price range
   - Search by name
   - Scan barcode to find game

2. **Add to Cart:**
   - Select game, choose quantity
   - View cart with total price
   - Validate stock availability

3. **Request Quote:**
   - Fill contact information
   - Submit cart
   - Receive quote email
   - Stock reserved for 30 minutes

---

## Testing Scenarios

### BGG Integration Tests
- Search returns results from BGA when BGG fails
- Game details populate all fields (name, year, designer, etc.)
- Thumbnails display in search results
- Web scraping extracts player count, playtime, age

### Stock Reservation Tests
- Cart checkout creates active reservation
- Available quantity reflects reserved stock
- Expiry after 30 minutes releases stock
- Admin can confirm/cancel reservations
- No overselling (atomic transactions)

### Cart Tests
- Add multiple games
- Update quantities
- Remove items
- Stock validation prevents ordering out-of-stock items
- Email quote generation

---

## Future Enhancements

### High Priority
1. **Email Configuration:** Connect real SMTP server (currently console backend)
2. **BGG Proxy Solution:** Self-hosted proxy or third-party service to bypass IP blocks
3. **Data Validation:** Ensure all game metadata populated before saving
4. **Image Uploads:** Allow manual image uploads if API fails

### Medium Priority
5. **User Authentication:** Customer accounts, order history
6. **Payment Integration:** Stripe/PayPal for direct purchases
7. **Inventory Alerts:** Notify when stock low
8. **Advanced Search:** Filter by players, playtime, mechanics, categories
9. **Wishlist:** Customer can save favorite games

### Low Priority
10. **Multi-language Support:** Portuguese, Spanish
11. **Mobile App:** React Native or Flutter
12. **Analytics Dashboard:** Sales metrics, popular games
13. **Bulk Import:** CSV upload for multiple games
14. **API Endpoint:** RESTful API for external integrations

---

## Development Setup

### Local Environment
```bash
# Clone repository
git clone https://github.com/LeandroKeltech/bgcatalog.git
cd bgcatalog

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Access app at http://127.0.0.1:8000
```

### Environment Variables (.env)
```
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3  # or PostgreSQL URL
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## API Documentation

### BGG Price Service (`bgg_price_service.py`)

**Functions:**

1. **`search_bgg_games(query: str, exact: bool = False) -> List[Dict]`**
   - Searches for games via BGG API → BGA API → Web Scraping
   - Returns: List of games with bgg_id, name, year, thumbnail

2. **`get_bgg_game_details(bgg_id: str) -> Dict`**
   - Fetches complete game details
   - Handles both BGG IDs and BGA IDs (prefixed with 'bga_')
   - Returns: Full game metadata

3. **`get_bga_game_details(bga_id: str) -> Dict`**
   - Fetches from Board Game Atlas API
   - Enriches with BGG web scraping if BGG ID found
   - Returns: Mapped game data in our format

4. **`scrape_bgg_game_page(bgg_id: str) -> Dict`**
   - Comprehensive BGG page scraping
   - Extracts: year, designer, description, players, playtime, age
   - Returns: Partial game data for enrichment

5. **`fetch_boardgameprices(bgg_id: str) -> Dict`**
   - Fetches pricing from BoardGamePrices.co.uk
   - Converts GBP to EUR if needed
   - Returns: Price, store, URL, availability

---

## Security Considerations

### Current Implementation
- CSRF protection enabled
- Session-based authentication for admin
- SQL injection prevention (Django ORM)
- XSS protection (Django templates auto-escape)
- HTTPS enforced in production (Fly.io)

### Recommendations
- Rate limiting on search endpoints
- Input validation on all forms
- API key rotation for BGA
- Backup strategy for database
- Error monitoring (Sentry integration)

---

## Performance Optimization

### Current Optimizations
- Database indexing on bgg_id, name, created_at
- Static file compression (WhiteNoise)
- Session-based cart (no database writes per action)
- Connection pooling for PostgreSQL
- SSL verification disabled for BGG scraping (faster)

### Recommended Improvements
- Redis caching for BGG/BGA API responses (24-hour TTL)
- Database query optimization (select_related, prefetch_related)
- CDN for static assets (Cloudflare)
- Background tasks for API calls (Celery + Redis)
- Image optimization/compression

---

## Monitoring & Logging

### Current Logging
- Console logging in development
- Fly.io logs in production (`fly logs`)
- Extensive debug prints in bgg_price_service.py

### Recommended Setup
- Structured logging (JSON format)
- Log aggregation (Papertrail, Loggly)
- Error tracking (Sentry)
- Uptime monitoring (UptimeRobot)
- Performance monitoring (New Relic, DataDog)

---

## Support & Documentation

### For Developers
- **Code Style:** PEP 8 (Python), Standard JS
- **Git Workflow:** Feature branches → PR → Main (auto-deploy)
- **Testing:** Django TestCase, pytest (to be added)
- **Documentation:** Inline comments, docstrings

### For Users
- Admin guide: See `STOCK_RESERVATION_SYSTEM.md`
- User manual: To be created
- API documentation: This file

---

## Contact & Resources

- **Production:** https://bgcatalog.fly.dev
- **Repository:** https://github.com/LeandroKeltech/bgcatalog
- **Issue Tracker:** GitHub Issues
- **CI/CD:** GitHub Actions
- **Hosting:** Fly.io (lhr region)

---

## Changelog

### Recent Updates (November 2025)
- ✅ Integrated Board Game Atlas API as BGG fallback
- ✅ Implemented comprehensive BGG web scraping
- ✅ Added thumbnail images to search results
- ✅ Enhanced game details extraction (players, playtime, age, categories, mechanics)
- ✅ Added BGG ratings display in templates
- ✅ Implemented stock reservation system
- ✅ Created admin reservation management interface
- ✅ Added automatic reservation expiry
- ✅ Improved error handling and logging

### Pending
- ⏳ Fix designer/year population from BGA data
- ⏳ Test complete stock reservation flow
- ⏳ Deploy stock reservation system
- ⏳ Configure production email SMTP

---

## Technical Specifications Summary

**Language:** Python 3.11+  
**Framework:** Django 5.2.7  
**Database:** PostgreSQL 15  
**Web Server:** Gunicorn  
**Reverse Proxy:** Fly.io (nginx)  
**OS:** Linux (Fly.io containers)  
**Architecture:** Monolith (single Django app)  
**API Style:** Server-side rendered (Django templates) + AJAX  
**Authentication:** Django sessions  
**File Storage:** Local filesystem (can migrate to S3)  

---

*Last Updated: November 7, 2025*
