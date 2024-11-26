from django.urls import path

from fame.views.bullshitters import bullshitter_list
from fame.views.experts import expert_list
from fame.views.html import fame_list
from fame.views.rest import ExpertiseAreasApiView, FameUsersApiView, FameListApiView, BullshittersApiView, \
    ExpertsApiView

app_name = "fame"

urlpatterns = [
    path(
        "api/expertise_areas", ExpertiseAreasApiView.as_view(), name="expertise_areas"
    ),
    path("api/users", FameUsersApiView.as_view(), name="fame_users"),
    path("api/fame", FameListApiView.as_view(), name="fame_fulllist"),
    path("html/fame", fame_list, name="fame_list"),
    path("api/experts", ExpertsApiView.as_view(), name="experts"),
    path("api/bullshitters", BullshittersApiView.as_view(), name="bullshitters"),
    path("html/experts", expert_list, name="expert_list"),
    path("html/bullshitters", bullshitter_list, name="bullshitter_list")
]
