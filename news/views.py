# -*-coding: utf-8 -*-

from django.shortcuts import render
from django.shortcuts import render_to_response, render, RequestContext
from django.template.context_processors import csrf
from django.contrib.auth.decorators import login_required
from django.contrib import auth
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q


from django.utils.translation import ugettext as _


from django.contrib.admin.views.decorators import staff_member_required

from .models import News, NewsPortal, NewsCategory, Companies

from news.models import RssNews
from userprofile.models import UserRssPortals
import datetime


#@login_required(login_url='/auth/login/')
def main_page_load(request):
    args = {
        "current_year": datetime.datetime.now().year,
        "title": "| Home",
        "news_block": True,
        "breaking_news": render_news_by_sendec(request)[0],
        "total_middle_news": render_news_by_sendec(request)[1:4],
        "total_bottom_news": render_news_by_sendec(request)[4:13],
        "interest": get_interesting_news(request)[:3],
    }

    # LOCALIZATION
    args["latest"] = _("Latest")

    args.update(csrf(request))
    if auth.get_user(request).username:
        args["username"]=User.objects.get(username=auth.get_user(request).username)
    #if User.objects.get(username=auth.get_user(request).username).is_active:
    return render_to_response("index_new.html", args)
    #else:
    #    return HttpResponseRedirect("/auth/preferences=categories")


def render_news_by_sendec(request, **kwargs):
    if len(kwargs) > 0:
        return News.objects.all().filter(news_category_id=kwargs["category_id"]).exclude(id=kwargs["news_id"]).values()
    else:
        return News.objects.all().values()


def get_company_news(request, news_id, company_id):
    current_company_news = News.objects.filter(news_company_owner=company_id).exclude(id=news_id).order_by("-news_post_date")
    #latest_10_news = News.objects.all().order_by("-news_post_date")
    #return latest_10_news
    return current_company_news


def get_latest_news_total(request):
    latest_10_news = News.objects.all().order_by("-news_post_date")
    return latest_10_news


#@login_required(login_url='/auth/login/')
def render_current_news(request, category_id, news_id):
    import datetime
    from userprofile.models import UserLikesNews
    from .forms import NewsCommentsForm, NewsCommentsRepliesForm
    current_news = News.objects.get(id=news_id)
    args = {
        "title": "| %s" % current_news.news_title,
        "current_news_values": current_news,
        "other_materials": render_news_by_sendec(request, news_id=news_id, category_id=category_id).exclude(id=news_id)[:12],
        "latest_news": get_company_news(request, news_id, current_news.news_company_owner_id)[:5],
        "company_name": str(Companies.objects.get(id=current_news.news_company_owner_id)).capitalize(),
        "current_day": datetime.datetime.now().day,
        #"comments_form": NewsCommentsForm,
        #"replies_form": NewsCommentsRepliesForm,
        "comments_total": comments_load(request, news_id),
        "replies_total": replies_load(request, news_id),
        "liked": check_like(request, news_id),
        "disliked": check_dislike(request, news_id),
        "like_amount": UserLikesNews.objects.filter(news_id=news_id).filter(like=True).count(),
        "dislike_amount": UserLikesNews.objects.filter(news_id=news_id).filter(dislike=True).count(),
        "current_news_title": current_news.news_title,
        "external_link": shared_news_link(request, news_id),
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    addition_news_watches(request, news_id)
    args.update(csrf(request))
    return render_to_response("current_news.html", args)


@login_required(login_url="/auth/login/")
def render_user_news(request, page_number=1):

    user = User.objects.get(username=auth.get_user(request).username)

    args = {
        "title": "| My news",
        #"portals": get_user_chosen_portals(request),
        #"usernews": get_user_news_by_portals(request),
       # "deftest": test.html(request),
        #"rss_news": get_rss_news(request),
        "test": set_rss_for_user_test(request),
        "user_rss": get_user_rss_news(request, user_id=user.id)
    }
    args.update(csrf(request))
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    from news.models import RssNews
    all_rss_news = set_rss_for_user_test(request) #RssNews.objects.all().values()
    current_page = Paginator(object_list=all_rss_news, per_page=12)
    args["rss_news"] = current_page.page(page_number)
    return render_to_response("user_news.html", args)


def get_user_chosen_portals(request):
    from userprofile.models import UserSettings
    return UserSettings.objects.get(user_id=User.objects.get(username=auth.get_user(request).username).id).portals_to_show.split(",")

def get_rss_news_pagination(request, current_page, next_page):
    from news.models import RssNews
    import json

    data_rss_news = [current_new.get_json_rss() for current_new in RssNews.objects.all()[current_page:next_page]]

    response_data = {
        "rss": data_rss_news,
    }

    return HttpResponse(json.dumps(response_data), content_type="application/json")


def get_current_rss_news(request, news_id):
    from news.models import RssNews
    import json
    return HttpResponse(json.dumps({"rss_news": RssNews.objects.get(id=news_id).get_json_rss()}), content_type="application/json")



def get_rss_news(request):
    from news.models import RssNews
    return RssNews.objects.all().values()


#@login_required(login_url="/auth/login/")
def render_top_news_page(request):
    from .models import NewsWatches
    args = {
        "top_news": get_top_news(request),
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("top_news.html", args)


def get_user_news_by_portals(request):
    from news.models import News, NewsPortal
    from userprofile.models import UserSettings
    from itertools import chain
    from operator import attrgetter
    from django.db.models import Q

    inst = UserSettings.objects.get(user_id=User.objects.get(username=auth.get_user(request).username).id).portals_to_show.split(",")

    #total_news = sorted(
    #    chain(
    #        News.objects.filter(news_portal_name_id=inst[cur_id]).values() for cur_id in range(len(inst)-1)
    #    ),
    #    key=attrgetter("news_post_date"),
    #    reverse=True
    #)

    total_news_2 = list(News.objects.filter(Q(news_portal_name_id=inst[cur_id])).order_by("-news_post_date") for cur_id in range(len(inst)-1))

    return total_news_2


def test(request):
    from news.models import News, NewsPortal
    from userprofile.models import UserSettings
    from itertools import chain
    from operator import attrgetter
    from django.db.models import Q

    inst_portals = UserSettings.objects.get(user_id=User.objects.get(username=auth.get_user(request).username).id).portals_to_show.split(",")
    inst_categories = UserSettings.objects.get(user_id=User.objects.get(username=auth.get_user(request).username).id).categories_to_show.split(",")

    # return chain(
    #         [News.objects.filter(Q(news_portal_name_id=inst_portals[cur_id])) for cur_id in range(len(inst_portals)-1)],
    #         [News.objects.filter(Q(news_category_id=inst_categories[cur_id])) for cur_id in range(len(inst_categories)-1)],
    #     (News.objects.order_by("-news_post_date"))
    #     )

    check = False

    test_new = sorted(
        chain(
            News.objects.filter(news_category_id=1),
            News.objects.filter(news_category_id=6 if check == True else 0),
        ),
        key=attrgetter("news_post_date"),
        reverse=True
    )
    return test_new
    #return [News.objects.filter(Q(news_category_id=inst_categories[cur_cat_id])).filter(Q(news_portal_name_id=inst_portals[cur_id]))
     #       for cur_cat_id in range(len(inst_categories)-1) for cur_id in range(len(inst_portals)-1)]



def check_like(request, news_id):
    from userprofile.models import UserLikesNews
    if auth.get_user(request).is_authenticated():
        if UserLikesNews.objects.filter(user_id=User.objects.get(username=auth.get_user(request).username).id).filter(news_id=news_id).filter(like=True).exists():
            return True
        else:
            return False
    else:
        pass


def check_dislike(request, news_id):
    from userprofile.models import UserLikesNews
    if auth.get_user(request).is_authenticated():
        if UserLikesNews.objects.filter(user_id=User.objects.get(username=auth.get_user(request).username).id).filter(news_id=news_id).filter(dislike=True  ).exists():
            return True
        else:
            return False
    else:
        pass


def update_latest_news(request):
    from .models import News
    import json

    latest_new = News.objects.filter(news_latest_shown=False).order_by("-news_post_date")[0]
    string = """<span class='time' style='color: blue;'>%s</span>
<span class='title' onclick="location.href='/news/%s/%s/';">%s</span><br>""" \
             % (latest_new.news_post_date.time().strftime("%H:%M"), latest_new.news_category_id, latest_new.id, latest_new.news_title)

    response_data = {
        "latest_news": [cur_new.get_json_news() for cur_new in News.objects.all().all().order_by("-news_post_date")[:1]],
        "string": [string]
    }

    latest_10 = News.objects.filter(news_currently_showing=True).order_by("-news_post_date")[:10]
    latest_10[10].news_currently_showing = False
    latest_10[10].save()

    latest_new.news_currently_showing = True
    latest_new.news_latest_shown = True
    latest_new.save()
    return HttpResponse(json.dumps(response_data), content_type="application/json")


def set_shown(request, news_id):
    from .models import News
    instance = News.objects.get(id=int(news_id))
    instance.news_latest_shown = True
    instance.save()
    return HttpResponse()


@login_required(login_url="/auth/login/")
def addition_news_watches(request, news_id):
    from .models import NewsWatches
    if NewsWatches.objects.filter(news_id=news_id).exists():
        instance = NewsWatches.objects.get(news_id=news_id)
        instance.watches += 1
        instance.save()
    else:
        NewsWatches.objects.create(
            news_id=news_id,
            watches=1,
        )
    return HttpResponse()


def get_top_news(request):
    """
    Get top 10 by watches news.
    :param request:
    :return:
    """
    from .models import NewsWatches, News
    top_list_id = NewsWatches.objects.all()[:10].values()
    top_news = [News.objects.get(id=int(cur_news_id["news_id"])) for cur_news_id in top_list_id]
    return top_news


#@login_required(login_url="/auth/login/")
def render_current_news_comments(request, category_id, news_id):
    from .models import NewsComments, NewsCommentsReplies
    import json
    news_comments = NewsComments.objects.filter(news_attached=int(news_id))
    news_replies = NewsCommentsReplies.objects.filter(news_attached=int(news_id))
    response_data = {
        "content_comments": [data_comments.get_json_comments() for data_comments in news_comments.all()],
        "content_replies": [data_replies.get_json_replies() for data_replies in news_replies.all()]
    }
    return HttpResponse(json.dumps(response_data), content_type="application/json")


#@login_required(login_url="/auth/login/")
def render_current_category(request, category_name):
    args = {
        "title": "| Politics",
        "latest_news": get_latest_news_total(request),
        "category_title": category_name.capitalize(),
        #"cat_news": News.objects.filter(news_category_id=NewsCategory.objects.get(category_name=category_name.capitalize()).id),
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("current_category.html", args)

############################################################################
###################### CATEGORIES ##########################################
############################################################################
def render_technology_news(request):
    args = {
        "title": "| Technology",
        "top_technology": get_technology_news(request)[0],
        "technology_news": get_technology_news(request)[1:],
        "category_title": "TECHNOLOGY",
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("technology.html", args)


def get_technology_news(request):
    from news.models import News
    return News.objects.all().filter(news_category_id=2)
##########3#################### END TECHNOLOGY #######################################


def render_auto_news(request):
    args = {
        "title": "| Auto",
        "top_auto_news": get_auto_news(request)[0],
        "auto_news": get_auto_news(request)[1:],
        "category_title": "AUTO",
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("auto.html", args)


def get_auto_news(request):
    return News.objects.all().filter(news_category_id=4)
################################### END AUTO #########################################


def render_bit_news(request):
    args = {
        "title": "| BIT",
        "top_bit_news": get_bit_news(request)[0],
        "bit_news": get_bit_news(request)[1:],
        "category_title": "BIT",
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("bit.html", args)


def get_bit_news(request):
    return News.objects.all().filter(news_category_id=6)
################################### END BIT #########################################


def render_companies_news(request):
    from news.models import Companies
    args = {
        "title": "| Companies",
        "companies": get_companies(request),
        "category_title": "COMPANIES",
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("companies.html", args)


def get_companies(request):
    from news.models import Companies
    return Companies.objects.all().order_by("id")


def render_current_company(request, company_name):
    from news.models import Companies
    args = {
        "username": User.objects.get(username=auth.get_user(request).username),
        "company": Companies.objects.get(verbose_name=company_name),
        "news": get_companies_news(request, Companies.objects.get(verbose_name=company_name).id),
    }
    args.update(csrf(request))
    return render_to_response("current_company.html", args)


def get_companies_news(request, company_id):
    return News.objects.filter(news_company_owner_id=company_id).order_by("-news_post_date").values()

############################## END COMPANIES ###################################

def render_entertainment_news(request):
    args = {
        "title": "| Entertainment",
        "top_entertainment_news": get_entertainment_news(request)[0],
        "entertainment_news": get_entertainment_news(request)[1:],
        "category_title": "ENTERTAINMENT",
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("entertainment.html", args)


def get_entertainment_news(request):
    return News.objects.all().filter(news_category_id=3)

################### END ENTERTAINMENT ######################################3333

def render_latest_news(request):
    args = {
        "title": "| Latest",
        "top_latest_news": get_latest_news_total(request)[0],
        "latest_news": get_latest_news_total(request)[1:10],
        "category_title": "LATEST",
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("latest.html", args)


def render_reviews_news(request):
    args = {
        "title": "| Reviews",
        "latest_news": get_latest_news_total(request),
        "category_title": "REVIEWS",
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("reviews.html", args)


def render_space_news(request):
    args = {
        "title": "| Space",
        "top_space_news": get_space_news(request)[0],
        "space_news": get_space_news(request)[1:],
        "category_title": "SPACE",
    }
    if auth.get_user(request).username:
        args["username"] = User.objects.get(username=auth.get_user(request).username)
    args.update(csrf(request))
    return render_to_response("space.html", args)


def get_space_news(request):
    return News.objects.all().filter(news_category_id=NewsCategory.objects.get(category_name="Space").id)


#################################### END SPACE ##############################3


@login_required(login_url="/auth/login")
def comment_send(request, category_id, news_id):
    from .forms import NewsCommentsForm
    from userprofile.models import UserProfile
    args = {
        "username": User.objects.get(username=auth.get_user(request).username),
    }
    args.update(csrf(request))

    if request.POST:
        form = NewsCommentsForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.news_attached = News.objects.get(id=news_id)
            comment.comments_author = User.objects.get(username=auth.get_user(request).username)
            form.save()

    return HttpResponseRedirect("/news/%s/%s/" % (category_id, news_id), args)


def comments_load(request, news_id):
    from .models import NewsComments
    return NewsComments.objects.filter(news_attached=news_id).order_by("-comments_post_date").values()


@login_required(login_url="/auth/login/")
def reply_send(request, news_id, comment_id):
    from .forms import NewsCommentsRepliesForm
    from .models import NewsComments
    args = {
        "username": User.objects.get(username=auth.get_user(request).username),
    }
    args.update(csrf(request))

    if request.POST:
        form = NewsCommentsRepliesForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.comment_attached = NewsComments.objects.get(id=comment_id)
            reply.news_attached = News.objects.get(id=news_id)
            reply.reply_author = User.objects.get(username=auth.get_user(request).username)
            form.save()
    return HttpResponseRedirect("/news/%s/%s/" % (News.objects.get(id=news_id).news_category_id,news_id), args)


def replies_load(request, news_id):
    from .models import NewsCommentsReplies
    return NewsCommentsReplies.objects.filter(news_attached=news_id).order_by("reply_post_date").values()

@login_required(login_url="/auth/login/")
def add_like_news(request, news_id):
    from .models import News
    from userprofile.models import UserLikesNews
    import json
    if UserLikesNews.objects.filter(user_id=User.objects.get(username=auth.get_user(request).username).id).filter(news_id=news_id).exists():
        user_like_instance = UserLikesNews.objects.filter(user_id=User.objects.get(username=auth.get_user(request).username).id).get(news_id=news_id)
        # Add like to pair USER-news
        user_like_instance.dislike=False
        user_like_instance.like=True
        user_like_instance.save()
    else:
        instance = News.objects.get(id=news_id)
        instance.news_likes += 1
        instance.save()
        UserLikesNews.objects.create(
            like=True,
            dislike=False,
            news_id=news_id,
            user_id=User.objects.get(username=auth.get_user(request).username).id
        )
    return HttpResponse()


@login_required(login_url="/auth/login/")
def add_dislike_news(request, news_id):
    from .models import News
    from userprofile.models import UserLikesNews
    import json

    if UserLikesNews.objects.filter(user_id=User.objects.get(username=auth.get_user(request).username).id).filter(news_id=news_id).exists():
        user_dislike_instance = UserLikesNews.objects.filter(user_id=User.objects.get(username=auth.get_user(request).username).id).get(news_id=news_id)
        # Add like to pair USER-news
        user_dislike_instance.dislike=True
        user_dislike_instance.like=False
        user_dislike_instance.save()
    else:
        instance = News.objects.get(id=news_id)
        instance.news_likes += 1
        instance.save()
        UserLikesNews.objects.create(
            like=False,
            dislike=True,
            news_id=news_id,
            user_id=User.objects.get(username=auth.get_user(request).username).id
        )
    return HttpResponse()


#@login_required(login_url="/auth/login/")
def check_like_amount(request, news_id):
    from userprofile.models import UserLikesNews
    import json
    return HttpResponse(json.dumps({"likes": UserLikesNews.objects.filter(news_id=news_id).filter(like=True).count()}), content_type="application/json")


#@login_required(login_url="/auth/login/")
def check_dislike_amount(request, news_id):
    from userprofile.models import UserLikesNews
    import json
    return HttpResponse(json.dumps({"dislikes": UserLikesNews.objects.filter(news_id=news_id).filter(dislike=True).count()}), content_type="application/json")


def delete_comment(request, comment_id):
    from news.models import NewsComments
    args = {}
    args.update(csrf(request))
    news_instance = News.objects.get(id=NewsComments.objects.get(id=int(comment_id)).news_attached_id)
    if User.objects.get(username=auth.get_user(request).username).is_staff:
        instance = NewsComments.objects.get(id=int(comment_id))
        instance.delete()
    else:
        pass
    return HttpResponseRedirect("/news/%s/%s/" % (news_instance.news_category_id, news_instance.id), args)

def delete_reply(request, reply_id):
    from news.models import NewsCommentsReplies
    args = {}
    args.update(csrf(request))
    news_instance = News.objects.get(id=NewsCommentsReplies.objects.get(id=int(reply_id)).news_attached_id)
    if User.objects.get(username=auth.get_user(request).username).is_staff:
        instance = NewsCommentsReplies.objects.get(id=int(reply_id))
        instance.delete()
    else:
        pass
    return HttpResponseRedirect("/news/%s/%s/" % (news_instance.news_category_id, news_instance.id), args)


#@login_required(login_url="/auth/login/")
def shared_news_link(request, news_id):
    news = News.objects.get(id=news_id)
    shared_link = "http://127.0.0.1:8000/ext/trans/{0}/{1}/".format(news.news_category_id, news.id)
    return shared_link


def external_transition(request, cat_id, news_id):
    from news.models import NewsWatches
    news_instance = NewsWatches.objects.get(news_id=news_id)
    news_instance.external_transition += 1
    news_instance.save()
    return HttpResponseRedirect("/news/%s/%s/" % (cat_id, news_id))


def get_user_rss_news(request, user_id):
    return UserRssPortals.objects.filter(user_id=user_id).filter(check=True).values()


def get_updated_user_rss(request):
    import json

    user = User.objects.get(username=auth.get_user(request).username)

    portals = UserRssPortals.objects.filter(user_id=user.id).filter(check=True)
    data = [portal.get_json_portal() for portal in portals.all()]

    response_data = {
        "portals": data,
    }
    return HttpResponse(json.dumps(response_data), content_type="application/json")


def set_rss_for_user_test(request):
    user = User.objects.get(username=auth.get_user(request).username)
    portals_user_list = get_user_rss_news(request, user_id=user.id)
    test_new = RssNews.objects.filter(portal_name_id__in=(portals_user_list[i]["portal_id"] for i in range(len(portals_user_list)))).values()
    return test_new


def remove_rss_portal_from_feed(request, uuid, pid):
    from news.models import RssNews, RssPortals
    from userprofile.models import UserProfile
    args = {}
    args.update(csrf(request))
    user = User.objects.get(id=UserProfile.objects.get(uuid=uuid).user_id)
    user_rss_instance = UserRssPortals.objects.get(portal_id=pid, user_id=user.id)
    user_rss_instance.check = False
    user_rss_instance.save()
    return render_to_response("user_news.html", args, context_instance=RequestContext(request))


def save_rss_news(request, rss_id):
    from .models import RssSaveNews, RssNews
    user = User.objects.get(username=auth.get_user(request).username)
    if RssSaveNews.objects.filter(user_id=user.id).filter(news_id=rss_id).exists() == False:
        RssSaveNews.objects.create(
            user_id=user.id,
            news_id=rss_id
        )
    else:
        pass
    return HttpResponse()


def get_interesting_news(request):
    from news.models import NewsWatches
    interest_news = NewsWatches.objects.all().order_by("-watches").values("news_id")
    return News.objects.filter(id__in=interest_news).values()