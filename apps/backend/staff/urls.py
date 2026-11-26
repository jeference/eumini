from django.urls import path

from staff import views

_order = "staff/orders/<uuid:order_id>"
_partner = "staff/partners/<uuid:partner_id>"

urlpatterns = [
    path("staff/orders/", views.StaffOrderListView.as_view()),
    path("staff/orders/summary/", views.StaffQueueSummaryView.as_view()),
    path(f"{_order}/", views.StaffOrderDetailView.as_view()),
    path(f"{_order}/events/", views.StaffOrderEventsView.as_view()),
    path(f"{_order}/items/<uuid:item_id>/download/", views.StaffItemDownloadView.as_view()),
    path(f"{_order}/items/<uuid:item_id>/files/", views.StaffItemFileView.as_view()),
    path(f"{_order}/assign/", views.StaffAssignView.as_view()),
    path(f"{_order}/unassign/", views.StaffUnassignView.as_view()),
    path(f"{_order}/label/", views.StaffLabelView.as_view()),
    path(f"{_order}/label/download/", views.StaffLabelDownloadView.as_view()),
    path(f"{_order}/deliver/", views.StaffDeliverView.as_view()),
    path("staff/issues/<uuid:issue_id>/resolve/", views.StaffIssueResolveView.as_view()),
    path("staff/partners/", views.StaffPartnerListView.as_view()),
    path(f"{_partner}/", views.StaffPartnerDetailView.as_view()),
    path(f"{_partner}/invite/", views.StaffPartnerInviteView.as_view()),
    path(f"{_partner}/deactivate/", views.StaffPartnerDeactivateView.as_view()),
    path(f"{_partner}/reactivate/", views.StaffPartnerReactivateView.as_view()),
    path(f"{_partner}/entries/", views.StaffPartnerEntryListView.as_view()),
    path(f"{_partner}/payouts/", views.StaffPartnerPayoutListView.as_view()),
    path(f"{_partner}/adjustments/", views.StaffPartnerAdjustmentView.as_view()),
    path("staff/rates/", views.StaffRatesView.as_view()),
]
