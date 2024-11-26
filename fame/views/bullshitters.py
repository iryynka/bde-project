from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from fame.views.rest import BullshittersApiView


@require_http_methods(["GET"])
@login_required
def bullshitter_list(request):
    expert_api_view = BullshittersApiView()
    bullshitters = expert_api_view.get(request="").data
    context = {
        "bullshitters": bullshitters
    }
    return render(request, "bullshitters.html", context=context)
