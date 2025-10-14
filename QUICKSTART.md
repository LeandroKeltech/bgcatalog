# Board Game Catalog - Quick Start Guide 🎲

## ✅ Project Status: COMPLETE!

Your Django Board Game Catalog is ready to use!

## 🚀 What's Included

### Features
- ✅ BoardGameGeek API integration (search games by name)
- ✅ Complete CRUD operations (Create, Read, Update, Delete)
- ✅ Automatic discount calculation based on condition
- ✅ Stock/inventory management
- ✅ Mark games as sold/unsold
- ✅ Image carousel for game photos
- ✅ Google Sheets synchronization
- ✅ Public storefront for customers
- ✅ Admin dashboard
- ✅ Beautiful Bootstrap 5 UI
- ✅ Responsive mobile-friendly design

### Default Discounts
- New: 30%
- Like New: 50%
- Used: 70%
- Damaged: 80%
- Missing Pieces: 85%

## 🎯 Your Application is Running!

**Server Address**: http://127.0.0.1:8000/

### Available URLs:

- **Admin Catalog**: http://127.0.0.1:8000/
- **BGG Search**: http://127.0.0.1:8000/bgg/search/
- **Django Admin**: http://127.0.0.1:8000/admin/
- **Public Catalog**: http://127.0.0.1:8000/public/

### Admin Credentials:
- Username: `admin`
- Password: `admin123`

## 📝 Quick Start Tutorial

### 1. Add Your First Game

1. Open http://127.0.0.1:8000/bgg/search/
2. Search for a game (e.g., "Catan")
3. Click on the game from search results
4. Review the pre-filled information from BGG
5. Set:
   - Condition (automatically sets discount)
   - MSRP Price (check Amazon or BGG marketplace)
   - Stock Quantity
   - Optional notes
6. Click "Add to Catalog"

### 2. View Your Catalog

- Go to http://127.0.0.1:8000/
- See all your games in a beautiful grid
- Use filters to search by condition, stock status
- Sort by name or price

### 3. Manage Games

- Click any game to see full details with image carousel
- Edit: Update any information
- Mark Sold: Track when games are sold
- Delete: Remove games from catalog

### 4. Share Public Catalog

- Share http://127.0.0.1:8000/public/ with customers
- Clean, customer-friendly interface
- Shows only available games (not sold)
- No ability to edit or delete

## 🔧 Project Structure

```
bgcatalog/
├── catalog/                    # Main app
│   ├── models.py              # BoardGame model
│   ├── views.py               # All views
│   ├── urls.py                # URL routing
│   ├── bgg_service.py         # BGG API integration
│   ├── sheets_service.py      # Google Sheets sync
│   └── templates/             # HTML templates
├── bgcatalog_project/         # Django settings
│   ├── settings.py            # Configuration
│   └── urls.py                # Main URL config
├── requirements.txt           # Python packages
├── .env.example              # Environment variables template
├── README.md                 # Full documentation
├── DEPLOYMENT.md             # Deployment guide
└── manage.py                 # Django management
```

## 🔗 Google Sheets Integration

### Setup Instructions:

1. **Create Google Cloud Project**
   - Go to https://console.cloud.google.com/
   - Create new project

2. **Enable APIs**
   - Enable "Google Sheets API"
   - Enable "Google Drive API"

3. **Create Service Account**
   - Go to "Credentials"
   - Create "Service Account"
   - Download JSON key file

4. **Save Credentials**
   - Save JSON file as `google_credentials.json` in project root
   - **IMPORTANT**: Never commit this file to GitHub!

5. **Create Google Sheet**
   - Create a new Google Sheet named "BoardGame Catalog"
   - Share it with the service account email (found in JSON file)
   - Give "Editor" permissions

6. **Test Sync**
   - Add a game to your catalog
   - Check if it appears in Google Sheets
   - Or click "Sync to Sheets" button in navigation

### Troubleshooting Sheets Sync:
- If sync fails, check:
  1. `google_credentials.json` exists in project root
  2. Service account email has access to the sheet
  3. Sheet name matches exactly (case-sensitive)
  4. APIs are enabled in Google Cloud Console

## 🌐 Deploy to Production

### Option 1: Render.com (Free)
1. Push code to GitHub
2. Create account on render.com
3. Follow DEPLOYMENT.md guide
4. Deploy in 5 minutes!

### Option 2: Railway.app (Free $5 credit)
1. Push code to GitHub
2. Create account on railway.app
3. Connect repository
4. Add PostgreSQL database
5. Deploy automatically!

See `DEPLOYMENT.md` for detailed instructions.

## 🛠️ Development Commands

```bash
# Start server
python manage.py runserver

# Create migrations (after model changes)
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run shell
python manage.py shell

# Collect static files (for production)
python manage.py collectstatic
```

## 📦 Dependencies

All dependencies are in `requirements.txt`:
- Django 5.2.7 - Web framework
- gspread - Google Sheets integration
- requests - HTTP library for BGG API
- python-decouple - Environment variables
- gunicorn - Production server
- whitenoise - Static files serving
- psycopg2-binary - PostgreSQL adapter
- And more...

## 🎨 Customization

### Change Colors
Edit `catalog/templates/catalog/base.html`:
```css
:root {
    --primary-color: #2c3e50;    /* Change this */
    --secondary-color: #3498db;   /* And this */
}
```

### Change Default Discounts
Edit `catalog/models.py` in the `BoardGame.save()` method:
```python
condition_defaults = {
    'new': 30.00,        # Change these values
    'like_new': 50.00,
    'used': 70.00,
}
```

### Add New Condition Types
Edit `catalog/models.py`:
```python
CONDITION_CHOICES = [
    ('new', 'New'),
    ('like_new', 'Like New'),
    ('used', 'Used'),
    ('your_new_condition', 'Your Label'),  # Add here
]
```

## 🐛 Common Issues

### Server won't start
```bash
# Check if port is in use
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <process_id> /F

# Try different port
python manage.py runserver 8001
```

### BGG API slow or failing
- BGG API can be slow (10-30 seconds)
- Try again if timeout occurs
- Check https://boardgamegeek.com is accessible

### Images not loading
- BGG sometimes blocks hotlinking
- Images are stored as URLs from BGG
- Some games may not have images

### Database locked error
- Close any DB browser tools
- Restart server
- Delete `db.sqlite3` and run migrations again (loses data)

## 📚 Additional Resources

- **Django Docs**: https://docs.djangoproject.com/
- **BGG API**: https://boardgamegeek.com/wiki/page/BGG_XML_API2
- **Bootstrap**: https://getbootstrap.com/docs/5.3/
- **Google Sheets API**: https://developers.google.com/sheets/api

## 🎯 Next Steps

1. ✅ Add your first game from BGG
2. ✅ Test all features (add, edit, delete, mark sold)
3. ✅ Setup Google Sheets integration
4. ✅ Customize colors and branding
5. ✅ Deploy to production
6. ✅ Share public catalog link with customers
7. ✅ Start selling board games! 💰

## 🤝 Need Help?

- Check `README.md` for full documentation
- Check `DEPLOYMENT.md` for deployment guide
- Review code comments
- Check Django error messages
- Search Django/Python documentation

## 📄 License

This project is open source and free to use for your board game business!

---

**Made with ❤️ for board game enthusiasts**

Enjoy your new Board Game Catalog! 🎲🎉
