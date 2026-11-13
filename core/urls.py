from django.urls import path

from . import api, views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('app/', views.customer_app, name='customer_app'),
    path('rider/', views.rider_app, name='rider_app'),
    path('vendor/', views.vendor_app, name='vendor_app'),

    path('api/tiles/<int:z>/<int:x>/<int:y>.png', api.map_tile, name='api_map_tile'),

    path('api/auth/login', api.login_account, name='api_login'),
    path('api/auth/register', api.register_customer, name='api_register'),
    path('api/me', api.me, name='api_me'),
    path('api/stock', api.stock_list, name='api_stock'),
    path('api/orders', api.orders_collection, name='api_orders'),
    path('api/orders/<int:order_id>', api.order_detail, name='api_order_detail'),
    path('api/orders/<int:order_id>/track', api.order_track, name='api_order_track'),
    path('api/orders/<int:order_id>/rate', api.order_rate, name='api_order_rate'),

    path('api/vendor/orders', api.vendor_orders, name='api_vendor_orders'),
    path('api/vendor/orders/<int:order_id>/accept', api.vendor_accept, name='api_vendor_accept'),
    path('api/vendor/orders/<int:order_id>/reject', api.vendor_reject, name='api_vendor_reject'),
    path('api/vendor/stats', api.vendor_stats, name='api_vendor_stats'),
    path('api/vendor/stock', api.vendor_stock, name='api_vendor_stock'),
    path('api/vendor/accepting', api.vendor_accepting, name='api_vendor_accepting'),
    path('api/vendor/settlement', api.vendor_settlement, name='api_vendor_settlement'),
    path('api/vendor/ratings', api.vendor_ratings, name='api_vendor_ratings'),

    path('api/rider/jobs/available', api.rider_jobs_available, name='api_rider_jobs'),
    path('api/rider/online', api.rider_online, name='api_rider_online'),
    path('api/rider/jobs/<int:order_id>/accept', api.rider_accept_job, name='api_rider_accept'),
    path('api/rider/jobs/<int:order_id>/decline', api.rider_decline_job, name='api_rider_decline'),
    path('api/rider/jobs/<int:order_id>/step', api.rider_step, name='api_rider_step'),
    path('api/rider/summary', api.rider_summary, name='api_rider_summary'),
]
