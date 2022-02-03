import os
import glob
import json
import soc.apiclient.itop
from soc.apiclient.itop import keys_to_dict, LOADED_FACTORIES


# def invalid_factory(name):
#     """Raise an Exception explaining that the requested factory is not available.
#     """
#     raise Exception("No such factory: '{0}'".format(name))


def command_list(args):

    def list_factories(args):
        # globexpr = os.path.join(os.path.dirname(os.path.abspath(__file__)), "factories", "*.py")
        # factories = [p.split('.')[0] for p in [os.path.basename(p) for p in glob.glob(globexpr)] if p not in ["__init__.py", ]]
        for name, _ in LOADED_FACTORIES.items():
            print(name)

    what_func = {
        "factories": list_factories
    }
    if args.what in what_func:
        what_func[args.what](args)
    else:
        print("usage: list {{{0}}}".format("|".join([k for k, _ in what_func.items()])))


def command_get(args):
    print(LOADED_FACTORIES)
    factory = LOADED_FACTORIES.get(args.iclass)
    if factory is None:
        raise Exception("Invalid factory: '{0}'".format(args.iclass))
    key = keys_to_dict(args.keys)
    if len(args.output) < 1:
        res = factory.get(key=key)
    else:
        res = factory.get(key=key, output=args.output)
    print(json.dumps(res, indent=2))


def command_create(args):
    factory = LOADED_FACTORIES.get(args.iclass)
    if factory is None:
        raise Exception("Invalid factory: '{0}'".format(args.iclass))
    fields = keys_to_dict(args.fields)
    res = factory.create(fields=fields)
    print(json.dumps(res, indent=2))


def command_update(args):
    factory = LOADED_FACTORIES.get(args.iclass)
    if factory is None:
        raise Exception("Invalid factory: '{0}'".format(args.iclass))
    fields = keys_to_dict(args.fields)
    res = factory.update(key=args.key, fields=fields)
    print(json.dumps(res, indent=2))


def add_parser(sp):
    """Add parsers to base parsing structure.

    Arguments:
        sp (object): Sub-parsers container.
    """
    # 'list' command.
    p_get = sp.add_parser("core-list", help="Get a given class")
    p_get.set_defaults(func=command_list)
    p_get.add_argument("what", default=None, nargs='?', help="Item category to list")
    # 'get' command.
    p_get = sp.add_parser("core-get", help="Get a given class")
    p_get.set_defaults(func=command_get)
    p_get.add_argument("iclass", help="Class name")
    p_get.add_argument("--output", default=[], nargs='+', help="Output fields")
    p_get.add_argument("--keys", default=[], nargs='+', help="Filtering keys")
    # 'create' command.
    p_create = sp.add_parser("core-create", help="Create a given class instance")
    p_create.set_defaults(func=command_create)
    p_create.add_argument("iclass", help="Class name")
    p_create.add_argument("--fields", default=[], nargs='+', help="New object fields")
    # 'update' command.
    p_update = sp.add_parser("core-update", help="Update a given class instance")
    p_update.set_defaults(func=command_update)
    p_update.add_argument("iclass", help="Class name")
    p_update.add_argument("key", type=int, help="Class instance key")
    p_update.add_argument("--fields", default=[], nargs='+', help="Updated fields")
