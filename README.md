# Board Game Catalog

A Django-based web application for managing and selling a board game collection with integrated pricing from BoardGameGeek (BGG) and BoardGamePrices APIs.

## 🎯 Features

- **Public Catalog** - Browse available games with filtering and search
- **Admin Panel** - Full CRUD operations for board games
- **BGG Integration** - Multi-tier fallback strategy (BGG XML API → Board Game Atlas → Web Scraping)
- **Stock Reservation System** - 30-minute automatic reservations to prevent overselling
- **Shopping Cart** - Session-based cart with real-time stock validation
- **Email Quotes** - Automated quote generation for customers
- **Barcode Scanner** - QuaggaJS integration for UPC/EAN lookup
- **Responsive Design** - Bootstrap 5 with mobile-first approach

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL (for production) or SQLite (for development)
- Virtual environment tool (venv, virtualenv, or conda)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LeandroKeltech/bgcatalog.git
   cd bgcatalog
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   # Or use the provided script:
   python create_admin.py
   ```

7. **Collect static files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

8. **Run development server:**
   ```bash
   python manage.py runserver
   ```

9. **Access the application:**
   - Public Catalog: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin-panel/
   - Django Admin: http://127.0.0.1:8000/admin/

## 📦 Project Structure

```
bgcatalog/
├── catalog/
│   ├── models.py              # BoardGame, StockReservation models
│   ├── views.py               # Public catalog views
│   ├── admin_views.py         # Admin panel views
│   ├── cart_views.py          # Shopping cart & checkout
│   ├── bgg_views.py           # BGG search & import
│   ├── bgg_price_service.py   # API integration service
│   ├── urls.py                # URL routing
│   ├── templates/catalog/     # HTML templates
│   └── static/catalog/        # CSS, JS, images
├── bgcatalog_project/
│   ├── settings.py            # Django settings
│   └── urls.py                # Root URL config
├── .github/workflows/
│   └── fly-deploy.yml         # CI/CD pipeline
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── fly.toml                   # Fly.io configuration
└── manage.py                  # Django management script
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3  # or PostgreSQL URL
```

### Production Settings

For production deployment on Fly.io:

1. Set environment secrets:
   ```bash
   fly secrets set SECRET_KEY=your-secret-key
   fly secrets set DEBUG=False
   fly secrets set ALLOWED_HOSTS=bgcatalog.fly.dev
   ```

2. Deploy:
   ```bash
   fly deploy
   ```

## 📚 API Integration

### BoardGameGeek (BGG)

- **XML API2**: Primary source for game data
- **Fallback**: Board Game Atlas API
- **Last Resort**: Web scraping BGG pages

### Board Game Atlas

- **Client ID**: JMc8dOwiQE (public test key)
- **Free Tier**: 100 requests/month

### BoardGamePrices

- **Endpoint**: boardgameprices.co.uk
- **Currency**: EUR (Ireland market)

## 🛒 Stock Reservation System

### How It Works

1. Customer adds items to cart
2. On checkout, stock is reserved for 30 minutes
3. Admin can confirm sale (reduces stock) or cancel reservation
4. Expired reservations are automatically released

### Admin Management

- View all reservations at `/admin-panel/reservations/`
- Confirm, cancel, or extend reservation time
- Automatic expiry prevents overselling

## 🎨 Frontend

### Technologies

- **Bootstrap 5** - UI framework
- **Bootstrap Icons** - Icon library
- **QuaggaJS** - Barcode scanning
- **Vanilla JavaScript** - No heavy frameworks

### Responsive Design

- Mobile-first approach
- Optimized for desktop, tablet, and mobile
- Touch-friendly interface

## 📊 Database Schema

### BoardGame Model

- Basic info: name, year, designer, description
- Images: thumbnail_url, image_url
- Gameplay: players, playtime, age
- Ratings: average, rank, num_ratings
- Pricing: msrp_price, discount_percentage
- Inventory: stock_quantity, condition, is_sold

### StockReservation Model

- Reservation details: game, quantity, status
- Customer info: name, email, phone
- Timestamps: reserved_at, expires_at, confirmed_at
- Session tracking: session_key

## 🔐 Security

- CSRF protection enabled
- Session-based authentication
- SQL injection prevention (Django ORM)
- XSS protection (auto-escaped templates)
- HTTPS enforced in production

## 🚢 Deployment

### Fly.io

The app is deployed on Fly.io with automatic CI/CD:

- **Production URL**: https://bgcatalog.fly.dev
- **Region**: London (lhr)
- **Database**: Fly Postgres
- **Auto-deploy**: Push to main branch

### Manual Deployment

```bash
# Deploy to Fly.io
fly deploy

# Check deployment status
fly status

# View logs
fly logs

# SSH into container
fly ssh console
```

## 📝 Development

### Running Tests

```bash
python manage.py test catalog
```

### Code Style

- **Python**: PEP 8
- **JavaScript**: Standard JS
- **HTML/CSS**: BEM methodology

### Git Workflow

1. Create feature branch
2. Make changes
3. Create pull request
4. Merge to main (auto-deploys)

## 🐛 Troubleshooting

### BGG API 401 Errors

If BGG API returns 401 errors:
- Fallback to Board Game Atlas will activate automatically
- Web scraping serves as final fallback
- Check logs for detailed error information

### Stock Reservation Issues

If reservations aren't working:
- Ensure migrations are up to date
- Check that session middleware is enabled
- Verify database transactions are supported

### Static Files Not Loading

```bash
# Collect static files
python manage.py collectstatic --noinput

# In production, ensure WhiteNoise is configured
```

## 📖 Documentation

- **API Documentation**: See inline docstrings in `bgg_price_service.py`
- **Stock Reservations**: Check `STOCK_RESERVATION_SYSTEM.md`
- **Models**: Review `catalog/models.py` for field descriptions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 👥 Contact

- **Repository**: https://github.com/LeandroKeltech/bgcatalog
- **Issues**: https://github.com/LeandroKeltech/bgcatalog/issues
- **Production**: https://bgcatalog.fly.dev

## 🙏 Acknowledgments

- BoardGameGeek for game data
- Board Game Atlas for API fallback
- BoardGamePrices for pricing information
- Fly.io for hosting

---

**Built with ❤️ using Django 5.2.7**
