from collections import defaultdict

from django.db.models import Q

from fame.models import Fame, FameLevels
from socialnetwork.models import Posts, SocialNetworkUsers


# general methods independent of html and REST views
# should be used by REST and html views


def _get_social_network_user(user) -> SocialNetworkUsers:
    """Given a FameUser, gets the social network user from the request. Assumes that the user is authenticated."""
    try:
        user = SocialNetworkUsers.objects.get(id=user.id)
    except SocialNetworkUsers.DoesNotExist:
        raise PermissionError("User does not exist")
    return user


def timeline(user: SocialNetworkUsers, start: int = 0, end: int = None, published=True):
    """Get the timeline of the user. Assumes that the user is authenticated."""
    _follows = user.follows.all()
    posts = Posts.objects.filter(
        (Q(author__in=_follows) & Q(published=published)) | Q(author=user)
    ).order_by("-submitted")
    if end is None:
        return posts[start:]
    else:
        return posts[start: end + 1]


def search(keyword: str, start: int = 0, end: int = None, published=True):
    """Search for all posts in the system containing the keyword. Assumes that all posts are public"""
    posts = Posts.objects.filter(
        Q(content__icontains=keyword)
        | Q(author__email__icontains=keyword)
        | Q(author__first_name__icontains=keyword)
        | Q(author__last_name__icontains=keyword),
        published=published,
    ).order_by("-submitted")
    if end is None:
        return posts[start:]
    else:
        return posts[start: end + 1]


def follows(user: SocialNetworkUsers, start: int = 0, end: int = None):
    """Get the users followed by this user. Assumes that the user is authenticated."""
    _follows = user.follows.all()
    print(_follows)
    if end is None:
        return _follows[start:]
    else:
        return _follows[start: end + 1]


def followers(user: SocialNetworkUsers, start: int = 0, end: int = None):
    """Get the followers of this user. Assumes that the user is authenticated."""
    _followers = user.followed_by.all()
    if end is None:
        return _followers[start:]
    else:
        return _followers[start: end + 1]


def follow(user: SocialNetworkUsers, user_to_follow: SocialNetworkUsers):
    """Follow a user. Assumes that the user is authenticated. If user already follows the user, signal that."""
    if user_to_follow in user.follows.all():
        return {"followed": False}
    user.follows.add(user_to_follow)
    user.save()
    return {"followed": True}


def unfollow(user: SocialNetworkUsers, user_to_unfollow: SocialNetworkUsers):
    """Unfollow a user. Assumes that the user is authenticated. If user does not follow the user anyway, signal that."""
    if user_to_unfollow not in user.follows.all():
        return {"unfollowed": False}
    user.follows.remove(user_to_unfollow)
    user.save()
    return {"unfollowed": True}


def submit_post(
        user: SocialNetworkUsers,
        content: str,
        cites: Posts = None,
        replies_to: Posts = None,
):
    """Submit a post for publication. Assumes that the user is authenticated.
    returns a tuple of three elements:
    1. a dictionary with the keys "published" and "id" (the id of the post)
    2. a list of dictionaries containing the expertise areas and their truth ratings
    3. a boolean indicating whether the user was banned and logged out and should be redirected to the login page
    """

    # create post  instance:
    post = Posts.objects.create(
        content=content,
        author=user,
        cites=cites,
        replies_to=replies_to,
    )

    # classify the content into expertise areas:
    # only publish the post if none of the expertise areas contains bullshit:
    _at_least_one_expertise_area_contains_bullshit, _expertise_areas = (
        post.determine_expertise_areas_and_truth_ratings()
    )
    post.published = not _at_least_one_expertise_area_contains_bullshit

    redirect_to_logout = False

    #########################
    # T1
    #########################
    user_fame_profile = Fame.objects.filter(user=user)

    for area in _expertise_areas:
        expertise_area_name = area["expertise_area"]
        for p_fame in user_fame_profile:
            if p_fame.expertise_area == expertise_area_name and p_fame.fame_level.numeric_value < 0:
                post.published = False
                break

    #########################
    # T2
    #########################

    post.save()

    if _at_least_one_expertise_area_contains_bullshit:
        for area in _expertise_areas:
            expertise_area = area["expertise_area"]
            truth_rating = area["truth_rating"]
            if truth_rating.numeric_value < 0:
                try:
                    user_fame = Fame.objects.get(user=user, expertise_area=expertise_area)
                    try:
                        next_lower_fame_level = user_fame.fame_level.get_next_lower_fame_level()
                        user_fame.fame_level = next_lower_fame_level
                        user_fame.save()
                    except ValueError:
                        # Cannot lower fame level any further
                        user.is_active = False
                        user.save()
                        redirect_to_logout = True
                        Posts.objects.filter(author=user).update(published=False)
                        break
                except Fame.DoesNotExist:
                    confuser_fame_level = FameLevels.objects.get(name="Confuser", numeric_value=-10)
                    Fame.objects.create(user=user, expertise_area=expertise_area, fame_level=confuser_fame_level)
                    pass
                if not user.is_active:
                    break

    return (
        {"published": post.published, "id": post.id},
        _expertise_areas,
        redirect_to_logout,
    )


def rate_post(
        user: SocialNetworkUsers, post: Posts, rating_type: str, rating_score: int
):
    """Rate a post. Assumes that the user is authenticated. If user already rated the post with the given rating_type,
    update that rating score."""
    user_rating = None
    try:
        user_rating = user.userratings_set.get(post=post, rating_type=rating_type)
    except user.userratings_set.model.DoesNotExist:
        pass

    if user == post.author:
        raise PermissionError(
            "User is the author of the post. You cannot rate your own post."
        )

    if user_rating is not None:
        # update the existing rating:
        user_rating.rating_score = rating_score
        user_rating.save()
        return {"rated": True, "type": "update"}
    else:
        # create a new rating:
        user.userratings_set.add(
            post,
            through_defaults={"rating_type": rating_type, "rating_score": rating_score},
        )
        user.save()
        return {"rated": True, "type": "new"}


def fame(user: SocialNetworkUsers):
    """Get the fame of a user. Assumes that the user is authenticated."""
    try:
        user = SocialNetworkUsers.objects.get(id=user.id)
    except SocialNetworkUsers.DoesNotExist:
        raise ValueError("User does not exist")

    return user, Fame.objects.filter(user=user)


def experts():
    """Return for each existing expertise area in the fame profiles a list of the users having positive fame for that
    expertise area. The list should be a Python dictionary with keys ``user'' (for the user) and ``fame_level_numeric''
    (for the corresponding fame value), and should be ranked, i.e. users with the highest fame are shown first, in case
    there is a tie, within that tie sort by date_joined (most recent first). Note that expertise areas with no expert
    may be omitted.
    """
    #########################
    # T3
    #########################
    # Users with positive fame levels
    positive_fame_users = Fame.objects.filter(fame_level__numeric_value__gt=0).select_related('user', 'expertise_area',
                                                                                              'fame_level')
    experts_by_area = defaultdict(list)

    # Populate the dictionary
    for _fame in positive_fame_users:
        experts_by_area[_fame.expertise_area].append({
            'user': _fame.user,
            'fame_level_numeric': _fame.fame_level.numeric_value
        })


    # Sort users within each expertise area
    for area in experts_by_area:

        experts_by_area[area] = sorted(
            experts_by_area[area],
            key=lambda x: (-x['fame_level_numeric'], -x['user'].date_joined.timestamp())
        )


    return experts_by_area


def bullshitters():
    """Return for each existing expertise area in the fame profiles a list of the users having negative fame for that
    expertise area. The list should be a Python dictionary with keys ``user'' (for the user) and ``fame_level_numeric''
    (for the corresponding fame value), and should be ranked, i.e. users with the lowest fame are shown first, in case
    there is a tie, within that tie sort by date_joined (most recent first). Note that expertise areas with no expert
    may be omitted.
    """
    #########################
    # T4
    #########################
    # Users with negative fame levels
    negative_fame_users = Fame.objects.filter(fame_level__numeric_value__lt=0).select_related('user', 'expertise_area',
                                                                                              'fame_level')

    bullshitters_by_area = defaultdict(list)

    # Populate the dictionary
    for _fame in negative_fame_users:
        bullshitters_by_area[_fame.expertise_area].append({
            'user': _fame.user,
            'fame_level_numeric': _fame.fame_level.numeric_value
        })

    # Sort users within each expertise area
    for area in bullshitters_by_area:
        bullshitters_by_area[area] = sorted(
            bullshitters_by_area[area],
            key=lambda x: (x['fame_level_numeric'], -x['user'].date_joined.timestamp())
        )

    return bullshitters_by_area
