# Board Game Catalog 🎲

A Django-based web application to catalog and sell board games. Integrates with BoardGameGeek API for game information and Google Sheets for data synchronization.

## Features

✅ **BoardGameGeek Integration**
- Search games by partial name
- Automatic import of game details (description, designer, players, playtime, images, etc.)

✅ **Inventory Management**
- Full CRUD operations (Create, Read, Update, Delete)
- Multiple condition types (New, Like New, Used, Damaged, Missing Pieces)
- Automatic discount calculation based on condition
- Stock quantity tracking
- Mark games as sold/unsold

✅ **Pricing System**
- MSRP price tracking
- Configurable discount percentages
- Automatic final price calculation
- Default discounts: New (30%), Like New (50%), Used (70%)

✅ **Image Management**
- Image carousel for multiple game photos
- Automatic thumbnail from BGG

✅ **Public Catalog**
- Customer-facing storefront
- Search and filter functionality
- Beautiful Bootstrap 5 UI

✅ **Google Sheets Sync**
- Automatic synchronization with Google Sheets
- Export entire catalog
- Real-time updates

## Tech Stack

- **Backend**: Django 5.2.7
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Frontend**: Bootstrap 5, Bootstrap Icons
- **APIs**: BoardGameGeek XML API v2, Google Sheets API
- **Deployment**: Render.com / Railway.app

## Installation

### Prerequisites

- Python 3.10+
- Git
- Google Cloud Platform account (for Google Sheets integration)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/LeandroKeltech/bgcatalog.git
   cd bgcatalog
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your settings:
   - `SECRET_KEY`: Generate a new Django secret key
   - `DEBUG`: Set to `False` in production
   - `ALLOWED_HOSTS`: Add your domain
   - `GOOGLE_SHEETS_CREDENTIALS_FILE`: Path to Google credentials JSON
   - `GOOGLE_SHEETS_NAME`: Name of your Google Sheet
   - `GOOGLE_SHEETS_SHARE_EMAIL`: Your email to share the sheet

5. **Google Sheets Setup**
   
   a. Go to [Google Cloud Console](https://console.cloud.google.com/)
   
   b. Create a new project
   
   c. Enable Google Sheets API and Google Drive API
   
   d. Create Service Account credentials
   
   e. Download the JSON key file and save as `google_credentials.json` in project root
   
   f. Share your Google Sheet with the service account email (found in the JSON file)

6. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Admin catalog: http://localhost:8000/
   - Django admin: http://localhost:8000/admin/
   - Public catalog: http://localhost:8000/public/

## Usage

### Adding Games

1. Click "Add Game (BGG)" in the navigation
2. Search for a game by name (partial matches work)
3. Select the game from search results
4. Review pre-filled information from BGG
5. Set condition, price, and stock quantity
6. Click "Add to Catalog"

### Managing Games

- **View**: Click on any game card to see details
- **Edit**: Click "Edit" button on game detail page
- **Delete**: Click "Delete" button and confirm
- **Mark Sold**: Click "Mark Sold" when a game is sold
- **Unmark Sold**: Restore a sold game to inventory

### Syncing to Google Sheets

- Click "Sync to Sheets" button in navigation
- Automatic sync happens on create/update/delete operations

### Public Catalog

- Share the `/public/` URL with customers
- They can browse available games
- View details, pricing, and conditions
- No ability to edit or delete

## Deployment

### Render.com (Recommended)

1. Push your code to GitHub

2. Create account on [Render.com](https://render.com)

3. Create new Web Service

4. Connect your GitHub repository

5. Configure:
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command**: `gunicorn bgcatalog_project.wsgi:application`
   - **Environment Variables**: Add all from `.env` file

6. Add PostgreSQL database (optional but recommended)

7. Deploy!

### Railway.app (Alternative)

1. Push your code to GitHub

2. Create account on [Railway.app](https://railway.app)

3. Create new project from GitHub repo

4. Add PostgreSQL database

5. Configure environment variables

6. Deploy automatically on push

## Project Structure

```
bgcatalog/
├── bgcatalog_project/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── catalog/                     # Main app
│   ├── models.py               # BoardGame model
│   ├── views.py                # All views
│   ├── urls.py                 # URL routing
│   ├── admin.py                # Django admin config
│   ├── bgg_service.py          # BGG API integration
│   ├── sheets_service.py       # Google Sheets integration
│   └── templates/              # HTML templates
│       └── catalog/
│           ├── base.html
│           ├── catalog_list.html
│           ├── game_detail.html
│           ├── game_form.html
│           ├── bgg_search.html
│           ├── public_base.html
│           ├── public_catalog.html
│           └── public_game_detail.html
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## API Documentation

### BoardGameGeek API

The app uses [BGG XML API2](https://boardgamegeek.com/wiki/page/BGG_XML_API2):

- **Search**: `/xmlapi2/search?query={name}&type=boardgame`
- **Details**: `/xmlapi2/thing?id={id}&stats=1`

### Google Sheets API

Uses `gspread` library with Service Account authentication.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is open source and available under the MIT License.

## Support

For issues or questions:
- Open an issue on GitHub
- Check BGG API documentation
- Review Django documentation

## Roadmap

- [ ] WhatsApp integration for customer inquiries
- [ ] Image upload functionality
- [ ] PDF catalog generation
- [ ] Multiple currency support
- [ ] Advanced analytics dashboard
- [ ] Email notifications

## Credits

- **BoardGameGeek** for the awesome API
- **Django** for the robust framework
- **Bootstrap** for beautiful UI components

---

Made with ❤️ for board game enthusiasts
