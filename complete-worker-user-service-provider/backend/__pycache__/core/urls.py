from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

# ======================================================
#                 AUTHENTICATION & USER ROUTES
# ======================================================
urlpatterns = [
   
    path('signup/', views.user_signup, name='user_signup'),
    path('login/', views.api_user_login, name='api_user_login'),
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('social-login/google/', views.google_social_login, name='google_social_login'),
    path('csrf/', views.csrf, name='csrf_token'),
    path('user-profile/', views.user_profile, name='user_profile'),

    # ======================================================
    #                 RECOMMENDATION & BOOKING ROUTES
    # ======================================================
    path('recommend/<int:user_id>/', views.recommend_view, name='recommend'),
    path('bookings/', views.BookingCreateView.as_view(), name='booking_create'),
    path('user/bookings/', views.user_booking_history, name='user_bookings'),
    path('user/bookings/<int:booking_id>/', views.user_booking_detail, name='user_booking_detail'),
    path('bookings/<int:booking_id>/cancel/', views.BookingCancelView.as_view(), name='booking_cancel'),

    # ======================================================
    #                     WORKER ROUTES
    # ======================================================
    path('workers/', views.WorkerListView.as_view(), name='worker_list'),
    path('worker/homepage/', views.worker_homepage, name='worker_homepage'),
    path('worker/job/<int:pk>/', views.job_detail, name='job_detail'),
    path('worker/job/accept/', views.accept_job, name='accept_job'),
    path('worker/job/complete/', views.complete_job, name='complete_job'),
    path('worker/job/tariff/', views.update_tariff, name='update_tariff'),
    path('worker/job/pay/', views.pay_job, name='pay_job'),
    path('worker/settings/', views.WorkerSettingsView.as_view(), name='worker_settings'),
    path('worker/availability/', views.update_availability, name='update_availability'),
    path('worker/bookings/send_receipt/', views.send_receipt, name='send_receipt'),
    path('worker/confirm_cod_payment/', views.confirm_cod_payment, name='confirm_cod_payment'),
    path('worker/earnings/', views.worker_earnings_list, name='worker_earnings_list'),

    # ======================================================
    #                 RATING & REVIEW ROUTES
    # ======================================================
    path('rating/submit/', views.submit_rating, name='submit_rating'),

    # ======================================================
    #                 PAYMENT ROUTES
    # ======================================================
    path('payment/create_order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
    path('payment/cod/', views.set_cod_payment, name='set_cod_payment'),
    path('payments/create-order1/', views.CreatePaymentOrderView.as_view(), name='create_payment_order'),
    path('payments/verify1/', views.VerifyPaymentView.as_view(), name='verify_payment_alt'),

    # ======================================================
    #                WORKER APPLICATION ROUTES
    # ======================================================
    path('worker-application/', views.WorkerApplicationView.as_view(), name='worker_application_create'),
    path('worker-application/<int:pk>/', views.WorkerApplicationView.as_view(), name='worker_application_update'),

    # ======================================================
    #                 CHATBOT & EVENTS ROUTES
    # ======================================================
    path('chatbot/', views.chatbot_response_view, name='chatbot_api'),
    path('events/', views.sse_stream, name='sse_stream'),

    # ======================================================
    #                 ADMIN ROUTES
    # ======================================================
    path('admin/', views.admin_dashboard_api, name='admin-dashboard'),
    path('admin/download_report/', views.admin_download_report, name='admin-download-report'),
    path('admin/users/', views.admin_list_users, name='admin-list-users'),
    path('admin/workers/', views.admin_list_workers, name='admin-list-workers'),
    path('admin/bookings/', views.admin_list_bookings, name='admin-list-bookings'),
   
    
    path('admin/dashboard/', views.admin_dashboard_api, name='admin_dashboard_api'),

    # ======================================================
    #                 VERIFIER 1 ROUTES
    # ======================================================
    path('verifier1/applications/', views.Verifier1ApplicationViewSet.as_view({'get': 'list'}), name='verifier1_application_list'),
    path('verifier1/applications/<int:pk>/', views.Verifier1ApplicationViewSet.as_view({'get': 'retrieve'}), name='verifier1_application_detail'),
    path('verifier1/applications/<int:pk>/documents/', views.Verifier1ApplicationViewSet.as_view({'get': 'documents'}), name='verifier1_application_documents'),
    path('verifier1/applications/<int:pk>/review_status/', views.Verifier1ApplicationViewSet.as_view({'get': 'review_status'}), name='verifier1_application_review_status'),
    path('verifier1/applications/<int:pk>/logs/', views.Verifier1ApplicationViewSet.as_view({'get': 'logs'}), name='verifier1_application_logs'),

    path('verifier1/reviews/', views.Verifier1ReviewViewSet.as_view({'get': 'list', 'post': 'create'}), name='verifier1_review_list'),
    path('verifier1/reviews/<int:pk>/', views.Verifier1ReviewViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    }), name='verifier1_review_detail'),
    path('verifier1/reviews/statistics/', views.Verifier1ReviewViewSet.as_view({'get': 'statistics'}), name='verifier1_review_statistics'),

    # ======================================================
    #                 VERIFIER 2 ROUTES
    # ======================================================
    path('verifier2/applications/', views.Verifier2ApplicationViewSet.as_view({'get': 'list'}), name='verifier2_applications_list'),
    path('verifier2/applications/<int:pk>/', views.Verifier2ApplicationViewSet.as_view({'get': 'retrieve'}), name='verifier2_applications_detail'),
    path('verifier2/applications/<int:pk>/documents/', views.Verifier2ApplicationViewSet.as_view({'get': 'documents'}), name='verifier2_application_documents'),
    path('verifier2/applications/<int:pk>/review_status/', views.Verifier2ApplicationViewSet.as_view({'get': 'review_status'}), name='verifier2_application_review_status'),

    path('verifier2/reviews/', views.Verifier2ReviewViewSet.as_view({'get': 'list', 'post': 'create'}), name='verifier2_reviews_list'),
    path('verifier2/reviews/<int:pk>/', views.Verifier2ReviewViewSet.as_view({
        'get': 'retrieve', 'patch': 'partial_update', 'put': 'update', 'delete': 'destroy'
    }), name='verifier2_review_detail'),
    path('verifier2/reviews/statistics/', views.Verifier2ReviewViewSet.as_view({'get': 'statistics'}), name='verifier2_reviews_statistics'),
    path('verifier2/reviews/<int:pk>/send_otp/', views.Verifier2ReviewViewSet.as_view({'post': 'send_otp'}), name='verifier2_send_otp'),
    path('verifier2/reviews/<int:pk>/verify_otp/', views.Verifier2ReviewViewSet.as_view({'post': 'verify_otp'}), name='verifier2_verify_otp'),
    
    # ======================================================
    #                 VERIFIER 3 ROUTES
    # ======================================================
    path('verifier3/applications/', views.Verifier3ApplicationViewSet.as_view({'get': 'list'}), name='verifier3_applications'),
    path('verifier3/applications/<int:pk>/', views.Verifier3ApplicationViewSet.as_view({'get': 'retrieve'}), name='verifier3_application_detail'),
    path('verifier3/reviews/', views.Verifier3ReviewViewSet.as_view({'get': 'list', 'post': 'create'}), name='verifier3_review_list'),
    path('verifier3/reviews/<int:pk>/', views.Verifier3ReviewViewSet.as_view({
        'get': 'retrieve', 'patch': 'partial_update', 'put': 'update', 'delete': 'destroy'
    }), name='verifier3_review_detail'),
    path('verifier3/reviews/dashboard/', views.Verifier3ReviewViewSet.as_view({'get': 'dashboard'}), name='verifier3_dashboard'),
    path('verifier3/reviews/pending_applications/', views.Verifier3ReviewViewSet.as_view({'get': 'pending_applications'}), name='verifier3_pending_applications'),
    path('verifier3/approved-workers/', views.Verifier3ApprovedListView.as_view(), name='verifier3_approved_workers'),
    path('verifier3/statistics/', views.Verifier3StatisticsView.as_view(), name='verifier3_statistics'),
    path('verifier3/applications/<int:pk>/documents/', views.Verifier3ApplicationViewSet.as_view({'get': 'documents'}), name='verifier3_application_documents'),
    path('verifier3/applications/<int:pk>/review_status/', views.Verifier3ApplicationViewSet.as_view({'get': 'review_status'}), name='verifier3_application_review_status'),
    # ======================================================
    #                 SHARED / MISC ROUTES
    # ======================================================
    path('applications/<int:pk>/', views.ApplicationSharedDetailView.as_view(), name='shared_application_detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
