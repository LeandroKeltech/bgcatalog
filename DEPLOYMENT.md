# Deployment Guide 🚀

This guide will help you deploy your Board Game Catalog to production.

## Option 1: Render.com (Recommended)

### Why Render?
- Free tier available
- Automatic deployments from GitHub
- Built-in PostgreSQL database
- Easy environment variable management
- HTTPS by default

### Steps:

1. **Prepare Your Repository**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub

3. **Create PostgreSQL Database**
   - Click "New +" → "PostgreSQL"
   - Name: `bgcatalog-db`
   - Region: Choose closest to you
   - Instance Type: Free
   - Click "Create Database"
   - Copy the "Internal Database URL"

4. **Create Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Name: `bgcatalog`
   - Region: Same as database
   - Branch: `main` or `creation`
   - Runtime: `Python 3`
   - Build Command: 
     ```
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - Start Command:
     ```
     gunicorn bgcatalog_project.wsgi:application
     ```

5. **Configure Environment Variables**
   
   Click "Environment" tab and add:
   
   ```
   SECRET_KEY=<generate-a-strong-random-key>
   DEBUG=False
   ALLOWED_HOSTS=your-app-name.onrender.com
   DATABASE_URL=<paste-internal-database-url>
   GOOGLE_SHEETS_CREDENTIALS_FILE=/etc/secrets/google_credentials.json
   GOOGLE_SHEETS_NAME=BoardGame Catalog
   GOOGLE_SHEETS_SHARE_EMAIL=your-email@example.com
   ```
   
   To generate SECRET_KEY:
   ```python
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

6. **Add Google Credentials as Secret File**
   - In Render dashboard, go to Environment
   - Click "Add Secret File"
   - Filename: `/etc/secrets/google_credentials.json`
   - Contents: Paste your Google service account JSON

7. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (3-5 minutes)
   - Your app will be at: `https://your-app-name.onrender.com`

8. **Create Superuser**
   - Go to your service dashboard
   - Click "Shell" tab
   - Run:
     ```bash
     python manage.py createsuperuser
     ```

9. **Test Your Site**
   - Visit `https://your-app-name.onrender.com`
   - Login to admin: `https://your-app-name.onrender.com/admin`
   - Add your first game!

### Automatic Deployments

Render automatically redeploys when you push to GitHub:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

---

## Option 2: Railway.app

### Why Railway?
- Very simple setup
- GitHub integration
- Free tier with $5 monthly credit
- PostgreSQL included

### Steps:

1. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign in with GitHub

2. **Create New Project**
   - Click "New Project"
   - Choose "Deploy from GitHub repo"
   - Select your `bgcatalog` repository

3. **Add PostgreSQL**
   - Click "New"
   - Select "Database" → "PostgreSQL"
   - Railway auto-generates `DATABASE_URL`

4. **Configure Variables**
   
   Click on your web service → "Variables":
   
   ```
   SECRET_KEY=<generate-a-strong-key>
   DEBUG=False
   ALLOWED_HOSTS=bgcatalog-production.up.railway.app
   GOOGLE_SHEETS_CREDENTIALS_FILE=google_credentials.json
   GOOGLE_SHEETS_NAME=BoardGame Catalog
   GOOGLE_SHEETS_SHARE_EMAIL=your-email@example.com
   ```

5. **Add Google Credentials**
   - Upload `google_credentials.json` to your repository (temporary)
   - After first deploy, remove it and add to `.gitignore`
   - Alternative: Use Railway's file storage

6. **Deploy**
   - Railway automatically deploys on push
   - Get your URL from "Settings" → "Domains"

7. **Create Superuser**
   - Click "..." menu → "Run a command"
   - Run: `python manage.py createsuperuser`

---

## Option 3: Heroku (Paid)

*Note: Heroku eliminated free tier in November 2022.*

### Steps:

1. **Install Heroku CLI**
   ```bash
   # Windows
   winget install Heroku.HerokuCLI
   
   # Mac
   brew tap heroku/brew && brew install heroku
   ```

2. **Login and Create App**
   ```bash
   heroku login
   heroku create bgcatalog-yourname
   ```

3. **Add PostgreSQL**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Set Environment Variables**
   ```bash
   heroku config:set SECRET_KEY="your-secret-key"
   heroku config:set DEBUG=False
   heroku config:set GOOGLE_SHEETS_NAME="BoardGame Catalog"
   ```

5. **Deploy**
   ```bash
   git push heroku main
   heroku run python manage.py migrate
   heroku run python manage.py createsuperuser
   heroku open
   ```

---

## Post-Deployment Checklist

- [ ] Test all pages load correctly
- [ ] Test BGG search functionality
- [ ] Test adding a game
- [ ] Test editing a game
- [ ] Test deleting a game
- [ ] Test marking sold/unsold
- [ ] Test Google Sheets sync
- [ ] Test public catalog view
- [ ] Create admin account
- [ ] Add contact information
- [ ] Share public URL with customers

---

## Troubleshooting

### Static Files Not Loading

1. Run collectstatic:
   ```bash
   python manage.py collectstatic --noinput
   ```

2. Check `STATIC_ROOT` and `STATICFILES_STORAGE` in settings.py

### Database Connection Error

1. Verify `DATABASE_URL` environment variable
2. Check database is running
3. Run migrations:
   ```bash
   python manage.py migrate
   ```

### Google Sheets Not Syncing

1. Verify `google_credentials.json` is uploaded
2. Check service account email has access to the sheet
3. Verify `GOOGLE_SHEETS_NAME` matches exactly

### BGG API Not Working

1. Check internet connectivity
2. BGG API may be slow - wait and retry
3. Check BGG API status: https://boardgamegeek.com/wiki/page/BGG_XML_API2

---

## Monitoring & Maintenance

### Check Logs (Render)
```bash
# View logs in real-time
In Render dashboard → Logs tab
```

### Check Logs (Railway)
```bash
# View deployment logs
In Railway dashboard → Deployments → Click on deployment
```

### Database Backups

**Render:**
- Automatic daily backups on paid plans
- Manual backup: Export from database dashboard

**Railway:**
- Use `pg_dump` command
- Store backups externally

### Update Dependencies

```bash
pip install --upgrade django
pip freeze > requirements.txt
git commit -am "Update dependencies"
git push
```

---

## Scaling

### If you need more performance:

1. **Upgrade database** (Render/Railway paid plans)
2. **Add caching** (Redis)
3. **Optimize queries** (select_related, prefetch_related)
4. **CDN for images** (Cloudinary, AWS S3)

---

## Security Best Practices

- ✅ Never commit `.env` or `google_credentials.json`
- ✅ Use strong `SECRET_KEY`
- ✅ Keep `DEBUG=False` in production
- ✅ Regularly update dependencies
- ✅ Use HTTPS (automatic on Render/Railway)
- ✅ Implement rate limiting for API calls
- ✅ Regular database backups

---

## Need Help?

- Render Docs: https://render.com/docs
- Railway Docs: https://docs.railway.app
- Django Deployment: https://docs.djangoproject.com/en/5.2/howto/deployment/
- BoardGameGeek API: https://boardgamegeek.com/wiki/page/BGG_XML_API2

---

Happy Deploying! 🎉
