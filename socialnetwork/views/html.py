from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from socialnetwork import api
from socialnetwork.api import _get_social_network_user
from socialnetwork.serializers import PostsSerializer
from socialnetwork.models import SocialNetworkUsers


@require_http_methods(["GET"])
@login_required
def timeline(request):
    # using the serializer to get the data, then use JSON in the template!
    # avoids having to do the same thing twice

    # get extra URL parameters:
    keyword = request.GET.get("search", "")
    published = request.GET.get("published", True)
    error = request.GET.get("error", None)

    # if keyword is not empty, use search method of API:
    if keyword and keyword != "":
        context = {
            "posts": PostsSerializer(
                api.search(keyword, published=published), many=True
            ).data,
            "searchkeyword": keyword,
            "error": error,
            "follows": api.follows(_get_social_network_user(request.user)).values_list('id', flat=True)
        }
    else:  # otherwise, use timeline method of API:
        context = {
            "posts": PostsSerializer(
                api.timeline(
                    _get_social_network_user(request.user), published=published
                ),
                many=True,
            ).data,
            "searchkeyword": "",
            "error": error,
        }

    return render(request, "timeline.html", context=context)


@require_http_methods(["POST"])
@login_required
def follow(request):
    user = _get_social_network_user(request.user)
    user_to_follow_id = request.POST.get("user_to_follow_id")
    user_to_follow = get_object_or_404(SocialNetworkUsers, id=user_to_follow_id)
    context = {
        "posts": PostsSerializer(
            api.timeline(
                _get_social_network_user(request.user), published=True
            ),
            many=True,

        ).data,
        "searchkeyword": "",
        "error": None,
        "follows": api.follows(_get_social_network_user(request.user)).values_list('id', flat=True)

    }
    if user_to_follow in user.follows.all():
        messages.error(request, 'Error')
        return render(request, 'timeline.html', context)

    user.follows.add(user_to_follow)
    user.save()
    messages.success(request, 'success')
    return render(request, 'timeline.html', context)


@require_http_methods(["POST"])
@login_required
def unfollow(request):
    user = _get_social_network_user(request.user)
    user_to_unfollow_id = request.POST.get("user_to_follow_id")
    user_to_unfollow = get_object_or_404(SocialNetworkUsers, id=user_to_unfollow_id)
    context = {
        "posts": PostsSerializer(
            api.timeline(
                _get_social_network_user(request.user), published=True
            ),
            many=True,

        ).data,
        "searchkeyword": "",
        "error": None,
        "follows": api.follows(_get_social_network_user(request.user)).values_list('id', flat=True)

    }

    api.unfollow(user, user_to_unfollow)
    user.save()
    messages.success(request, 'success')
    return render(request, 'timeline.html', context)
