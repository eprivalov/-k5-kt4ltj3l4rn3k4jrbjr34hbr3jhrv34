
from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^login/', 'loginsys.views.login'),
    url(r'^logout/', 'loginsys.views.logout'),
    url(r'^ps/', 'loginsys.views.pref_portals_save'),
    url(r'^cs/', 'loginsys.views.pref_cat_save'),
    url(r'^preferences=categories', "loginsys.views.render_user_preferences_categories_page"),
    url(r'^preferences=portals', "loginsys.views.render_user_preferences_portal_page"),
    url(r'^skip-preferences/', "loginsys.views.skip_preferences"),
    url(r'^register/', 'loginsys.views.register'),
]
