from accounts.models import CustomUser
from allauth.socialaccount.models import SocialAccount
from allauth.account.models import EmailAddress
from django.db import transaction
import requests
from django.core.files.temp import NamedTemporaryFile
from django.core.files import File

# create a function to generate ussername from email


def generate_username(email):
    username = email.split("@")[0]
    # check if user name exists
    if not CustomUser.objects.filter(username=username).exists():
        return username
    number = CustomUser.objects.filter(username=username).count() + 1
    username = f"{username}{number}"
    return username


@transaction.atomic
def register_google_user(data):
    """
    This is a function to register a user if the user doesn't exist

    It also create Profile and Allauth Social profile if the is doesn't exist.
    An already created account with the same email and using google oath2 will
    be authenticated.
    """
    user_id = data["sub"]
    email = data["email"]
    provider = "google"

    user_queryset = CustomUser.objects.filter(email=email)

    if user_queryset.exists():
        return user_queryset.first().email

    # lets create a new user
    username = generate_username(email)

    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        fullname=data["name"],
        first_name=data["given_name"],
        last_name=data["family_name"],
    )
    user.is_active = True
    user.save()

    # try and save profile picture
    try:
        image_url = data["picture"]
        response = requests.get(image_url)
        response.raise_for_status()
        image_temp = NamedTemporaryFile(delete=True)
        image_temp.write(response.content)
        image_temp.flush()
        image_field = getattr(user, "profile_picture")
        image_field.save(f'{image_url.split("/")[-1]}', File(image_temp))
        user.save()
    except Exception as e:
        pass
    # creat a profile for the user
    # create and email for the user
    EmailAddress.objects.create(
        user=user,
        email=user.email,
        verified=True,
        primary=True,
    )
    # create an allauth social account
    SocialAccount.objects.create(
        user=user,
        provider=provider,
        uid=user_id,
        extra_data=data,
    )

    return user.email
