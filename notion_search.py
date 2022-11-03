import argparse
import json
import os
import sys
from dataclasses import dataclass, field

import requests


@dataclass
class AlfredItem:
    title: str = ""
    subtitle: str = ""
    arg: str = ""
    icon: dict = field(default_factory=dict)
    mods: dict = field(default_factory=dict)
    text: dict = field(default_factory=dict)


class NotionClient:
    def __init__(self, pro_args) -> None:
        self.args = pro_args

    def search(self):
        headers = {
            "Notion-Version": "2022-06-28",
            "accept": "application/json",
            "authorization": f"Bearer {self.args.token}",
        }
        json_data = {
            "page_size": self.args.limit,
            "query": self.args.text_flat,
        }
        response = requests.post(
            "https://api.notion.com/v1/search", headers=headers, json=json_data
        )
        if response.status_code != 200:
            raise Exception(
                "Response {} ({})".format(response.status_code, response.text)
            )

        log(
            json.dumps(
                json.loads(response.text),
                sort_keys=True,
                indent=4,
                separators=(",", ": "),
            ),
            self.args,
        )

        return response.json()["results"]


def log(message, args):
    if args.output != "alfred":
        if args.verbose:
            print(message)


def convert_to_alfred(results: list):
    items = []
    for result in results:
        item = AlfredItem()
        item.title = parser_title(result)
        item.subtitle = result["last_edited_time"]
        item.arg = result["url"]
        # item.icon = {
        #     "path": "../icon.png"
        # }
        item.icon = result["icon"]
        item.mods = {
            "cmd": {"valid": True, "arg": result["url"], "subtitle": "Open in editor"}
        }
        item.text = {"copy": result["url"], "largetype": result["url"]}
        items.append(item.__dict__)
    return items


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("text", metavar="text", nargs="+")
    parser.add_argument(
        "--token",
        help="you can generate a token from https://developers.notion.com/, "
        "only suggest generate a read bot.",
    )
    parser.add_argument(
        "-o", "--output", default="cli", help="Specify output mode [alfred|cli]."
    )
    parser.add_argument(
        "-l", "--limit", default=10, help="Specify the max number of results"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Switch on logging"
    )
    # parser.add_argument("-c", "--content", action="store_true",
    # default=False, help="search content")

    args = parser.parse_args()

    args.token = get_token(args)
    args.text_flat = " ".join(args.text)

    return args


def get_token(args):
    token = os.getenv("CA_TOKEN", args.token)
    log(token, args)

    if token is None or len(token) <= 0:
        raise Exception("Token not specified.")

    return token


def convert_to_text(search_results, proj_args):
    text_result = ""

    if len(search_results) < 1:
        text_result += "No search results found\n"
        text_result += "    Search Notion for '" + proj_args.text_flat + "':\n"
        text_result += "    " + proj_args.url + proj_args.pathPrefix + "/search?text="

    for result in search_results:
        title = " ".join(
            foo["plain_text"] for foo in result["properties"]["title"]["title"]
        )
        url = result["url"]
        text_result += f"title: {title} \n url: {url} \n"

    return text_result


def parser_title(result) -> str:
    title = "unknown"
    for _, property_ in result["properties"].items():
        if property_["id"] == "title":
            title = " ".join(foo["plain_text"] for foo in property_["title"])
            break
    return title


def create_output(search_results, proj_args):
    if proj_args.output == "alfred":
        alfred_items = convert_to_alfred(search_results)
        sys.stdout.write(json.dumps({"items": alfred_items}))
    else:
        text_res = convert_to_text(search_results, proj_args)
        sys.stdout.write(text_res)


try:
    args = parse_args()
    notion_client = NotionClient(args)
    searchResults = notion_client.search()
    create_output(searchResults, args)

except Exception as e:
    sys.stdout.write(
        json.dumps(
            {
                "items": [
                    {
                        "title": "Error in Notion Search",
                        "subtitle": "Details: " + str(e),
                        "valid": False,
                        "text": {"copy": str(e), "largetype": str(e)},
                    }
                ]
            }
        )
    )

