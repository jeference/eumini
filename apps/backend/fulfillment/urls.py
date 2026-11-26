from django.urls import path

from fulfillment import views

urlpatterns = [
    path("partner/me/", views.PartnerMeView.as_view()),
    path("partner/invite/accept/", views.PartnerInviteAcceptView.as_view()),
    path("partner/orders/", views.PartnerOrderListView.as_view()),
    path("partner/orders/summary/", views.PartnerOrderSummaryView.as_view()),
    path("partner/orders/<uuid:order_id>/", views.PartnerOrderDetailView.as_view()),
    path(
        "partner/orders/<uuid:order_id>/items/<uuid:item_id>/download/",
        views.PartnerItemDownloadView.as_view(),
    ),
    path(
        "partner/orders/<uuid:order_id>/label/download/",
        views.PartnerLabelDownloadView.as_view(),
    ),
    path("partner/orders/<uuid:order_id>/refuse/", views.PartnerRefuseView.as_view()),
    path("partner/orders/<uuid:order_id>/start/", views.PartnerStartView.as_view()),
    path("partner/orders/<uuid:order_id>/ready/", views.PartnerReadyView.as_view()),
    path("partner/orders/<uuid:order_id>/post/", views.PartnerPostView.as_view()),
    path("partner/orders/<uuid:order_id>/issues/", views.PartnerIssueView.as_view()),
    path("partner/earnings/", views.PartnerBalanceView.as_view()),
    path("partner/earnings/entries/", views.PartnerEntryListView.as_view()),
    path("partner/payouts/", views.PartnerPayoutListView.as_view()),
]
