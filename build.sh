<<<<<<< HEAD
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

## Step 3 — Update `Procfile`
Replace everything in `Procfile` with:
```
web: gunicorn marketplace.wsgi:application
=======
cat > build.sh << 'EOF'
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
EOF
>>>>>>> 17c4b19adfb3a7de101fac88df4c78870c832492