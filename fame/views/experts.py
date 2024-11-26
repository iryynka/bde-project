from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from fame.serializers import FameSerializer
from fame.views.rest import ExpertsApiView
from socialnetwork import api
from socialnetwork.api import _get_social_network_user
from socialnetwork.models import SocialNetworkUsers


@require_http_methods(["GET"])
@login_required
def expert_list(request):
    expert_api_view = ExpertsApiView()
    experts = expert_api_view.get(request="").data
    context = {
        "experts": experts
    }
    print(experts)
    return render(request, "experts.html", context=context)
