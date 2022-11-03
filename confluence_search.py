import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field

import requests


def log(message, proj_args):
    if proj_args.output != 'alfred':
        if proj_args.verbose:
            print(message)


@dataclass
class AlfredItem:
    title: str = ""
    subtitle: str = ""
    arg: str = ""
    icon: dict = field(default_factory=dict)
    mods: dict = field(default_factory=dict)
    text: dict = field(default_factory=dict)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("text", metavar='text', nargs='+')
    parser.add_argument("--url",
                        help="Specify the url.")
    parser.add_argument("--user", help="Specify the user's email")
    parser.add_argument("--token",
                        help="Specify the authentication token")
    parser.add_argument("-o", "--output", default='cli', help="Specify output mode [alfred|cli].")
    parser.add_argument("-s", "--space", nargs="?", default=None, const=None, help="Specify the space key")
    parser.add_argument("-l", "--limit", default=10, help="Specify the max number of results")
    parser.add_argument("-t", "--type", default="page,blogpost",
                        help="Type of content to search for [page,blogpost,attachment] (default: page,blogpost)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Switch on logging")
    parser.add_argument("-c", "--content", action="store_true", default=False, help="search content")

    proj_args = parser.parse_args()

    proj_args.textAsString = " ".join(proj_args.text)

    proj_args.url = get_and_validate_url(proj_args)
    proj_args.user = get_and_validate_user(proj_args)
    proj_args.token = get_and_validate_token(proj_args)

    proj_args.pathPrefix = ""
    proj_args.isDatacenter = True
    if re.search("atlassian.net", proj_args.url) or re.search("jira.com", proj_args.url):
        proj_args.isDatacenter = False
        proj_args.pathPrefix = "/wiki"

    return proj_args


def get_and_validate_url(proj_args):
    url = os.getenv("CA_URL", proj_args.url)
    url = re.sub("/+$", "", url)
    log(url, proj_args)

    if url is None or len(url) <= 0:
        raise Exception("URL not specified.")

    return url


def get_and_validate_user(proj_args):
    user = os.getenv("CA_USER", proj_args.user)
    log(user, proj_args)

    if user is None or len(user) <= 0:
        raise Exception("User not specified.")

    return user


def get_and_validate_token(proj_args):
    token = os.getenv("CA_TOKEN", proj_args.token)
    log(token, proj_args)

    if token is None or len(token) <= 0:
        raise Exception("Token not specified.")

    return token


def search_confluence(proj_args):
    response = requests.request(
        "GET",
        proj_args.url + proj_args.pathPrefix + '/rest/api/search',
        headers={
            "Authorization": create_auth(proj_args)
        },
        params=create_search_query(proj_args, "title")
    )

    if response.status_code != 200:
        raise Exception('Response {} ({})'.format(response.status_code, response.text))

    log(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")), proj_args)

    return json.loads(response.text)["results"]


def search_confluence_content(proj_args):
    response = requests.request(
        "GET",
        proj_args.url + proj_args.pathPrefix + '/rest/api/search',
        headers={
            "Authorization": create_auth(proj_args)
        },
        params=create_search_query(proj_args, "text")
    )

    if response.status_code != 200:
        raise Exception('Response {} ({})'.format(response.status_code, response.text))

    log(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")), proj_args)

    return json.loads(response.text)["results"]


def create_auth(proj_args):
    auth_header = f"Bearer {proj_args.token}"
    log(auth_header, proj_args)
    return auth_header


def create_search_query(proj_args, granularity: str):
    log("space: {}".format(proj_args.space), proj_args)
    log("text: {}".format(proj_args.text), proj_args)

    cql = granularity + " ~ \"" + proj_args.textAsString + "\""

    if proj_args.space:
        cql += " AND space = \"" + proj_args.space + "\""

    cql += " AND type IN (" + proj_args.type + ")"

    log('cql: ' + cql, proj_args)

    return {
        'cql': cql,
        'limit': proj_args.limit,
        'expand': 'content.space,content.metadata.properties.emoji_title_published,content.history.lastUpdated'
    }


def create_output(search_results, proj_args):
    if proj_args.output == 'alfred':
        alfred_items = convert2alfred(search_results, proj_args)
        sys.stdout.write(json.dumps({
            "items": alfred_items
        }))
    else:
        text_result = convert2text(search_results, proj_args)
        sys.stdout.write(text_result)


def convert2alfred(search_results, proj_args):
    alfred_items = []

    if len(search_results) < 1:
        alfred_items.append({
            "title": "No search results",
            "subtitle": "Hit <enter> to do a full-text search for '" + proj_args.textAsString + "' in Confluence",
            "arg": proj_args.url + proj_args.pathPrefix + "/search?text=" + proj_args.textAsString,
            "icon": {
                "path": "./assets/search-for.png"
            },
        })

    for result in search_results:
        # docs: https://www.alfredapp.com/help/workflows/inputs/script-filter/json/
        item = AlfredItem()
        item.title = create_title(result)
        item.subtitle = create_subtitle(result)
        item.arg = create_url(result, proj_args)
        item.icon = {
            "path": get_icon_path(result)
        }
        item.mods = get_mods(result, proj_args)
        item.text = {
            "copy": create_url(result, proj_args),
            "largetype": create_url(result, proj_args)
        }

        alfred_items.append(item.__dict__)

    return alfred_items


def create_title(result):
    if "emoji-title-published" in result["content"]["metadata"]["properties"]:
        emoji = chr(ast.literal_eval(
            '0x' + result["content"]["metadata"]["properties"]["emoji-title-published"]["value"])) + ' '
    else:
        emoji = ''

    return "{1}{2}".format(
        result["content"]["space"]["key"],
        emoji,
        result["content"]["title"])


def create_subtitle(result):
    return "Last Update: {1} by {2} | Space: {0}".format(
        result["content"]["space"]["name"],
        result["friendlyLastModified"],
        result["content"]["history"]["lastUpdated"]["by"]["displayName"])


def create_url(result, proj_args):
    return proj_args.url + proj_args.pathPrefix + result["url"]


def get_icon_path(result):
    path = "./assets/content-type-page.png"

    if result["content"]["type"] == "blogpost":
        path = "./assets/content-type-blogpost.png"

    return path


def get_mods(result, proj_args):
    mod = {}

    if proj_args.isDatacenter:
        if result["content"]["type"] == "blogpost" or result["content"]["type"] == "page":
            mod["cmd"] = {
                "valid": True,
                "arg": proj_args.url + proj_args.pathPrefix + "/pages/editpage.action?pageId=" + result["content"][
                    "id"],
                "subtitle": "Open in editor"
            }
    else:
        if result["content"]["type"] == "blogpost" or result["content"]["type"] == "page":
            mod["cmd"] = {
                "valid": True,
                "arg": proj_args.url + proj_args.pathPrefix + result["content"]["_links"]["editui"],
                "subtitle": "Open in editor"
            }

    return mod


def convert2text(search_results, proj_args):
    text_result = ""

    if len(search_results) < 1:
        text_result += "No search results found\n"
        text_result += "    Search Confluence for '" + proj_args.textAsString + "':\n"
        text_result += "    " + proj_args.url + proj_args.pathPrefix + "/search?text=" + proj_args.textAsString

    for result in search_results:
        text_result += "· " + create_title(result) + "\n"
        text_result += "    " + create_subtitle(result) + "\n"
        text_result += "    " + create_url(result, proj_args)

    return text_result


try:
    args = parse_args()
    if args.content:
        results = search_confluence_content(args)
    else:
        results = search_confluence(args)
    create_output(results, args)

except Exception as e:
    sys.stdout.write(json.dumps({
        "items": [{
            "title": "Error in Confluence Quicksearch",
            "subtitle": "Details: " + str(e),
            "valid": False,
            "text": {
                "copy": str(e),
                "largetype": str(e)
            }
        }]
    }))

