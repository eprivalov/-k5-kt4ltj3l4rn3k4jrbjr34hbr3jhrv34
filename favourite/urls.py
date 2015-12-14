from django.conf.urls import include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    url(r'^$', 'favourite.views.render_liked_news_page'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
