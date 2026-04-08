from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(fix_site, sender=self)


def fix_site(sender, **kwargs):
    try:
        from django.contrib.sites.models import Site
        Site.objects.update_or_create(
            id=1,
            defaults={
                'domain': 'artisan-marketplace-ze6r.onrender.com',
                'name': 'Artisan Marketplace'
            }
        )
    except Exception:
        pass