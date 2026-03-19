cat > build.sh << 'EOF'
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
EOF