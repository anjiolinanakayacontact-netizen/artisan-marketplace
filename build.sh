pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

## Step 3 — Update `Procfile`
Replace everything in `Procfile` with:
```
web: gunicorn marketplace.wsgi:application