import json
from tabulate import tabulate
from soc.apiclient.itop import keys_to_dict, GetAction, CreateAction, UpdateAction


# Factories
# =========
get = GetAction(iclass="Organization", output=["name", "code", "id"])


# Sub-parser and commands
# =======================

def command_get(args):
    res = get()
    table = []
    for org in [org for _, org in res["objects"].items()]:
        table.append([org["fields"]["id"], org["fields"]["code"], org["fields"]["name"]])
    print(tabulate(table, headers=["ID", "Code", "Name"]))


def add_parser(sp):
    """Add parsers to base parsing structure.

    Arguments:
        sp (object): Sub-parsers container.
    """
    # 'get' command.
    p_get = sp.add_parser("orgs-get", help="List organization")
    p_get.set_defaults(func=command_get)
