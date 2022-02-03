import sys
import logging
import json
from tabulate import tabulate
from pkg_resources import resource_filename as pkgrs
import re
from soc.apiclient.itop import keys_to_dict, render_template, parse_vars, GetAction, CreateAction, UpdateAction


logger = logging.getLogger("soc.apiclient.itop.incident_siem")


get = GetAction(iclass="Incident",
                output=["title", "friendlyname", "org_id", "org_id_friendlyname", "operational_status"],
                key={"service_name": "CSOC - Security Monitoring"})


create = CreateAction(iclass="Incident", fields={
    "service_id": {"name": "CSOC - Security Monitoring"},
    "servicesubcategory_id": {"name": "Security Incident (Escalated)"},
    "team_id": {"name": "SOC_Analysts"},
    "agent_id": {"friendlyname": "Analyst SOC (Generic)"},
    "status": "pending",
    "pending_reason": "Waiting for feedback",
    "impact": 3,
    "urgency": 4
})


update = UpdateAction(iclass="Incident")

# update_stimulus = StimulateAction(iclass="Incident", stimulus=None)


def get_org_key(args):
    if getattr(args, "org_id", None) is not None:
        return args.org_id
    elif getattr(args, "org_code", None) is not None:
        return {"code": args.org_code}
    elif getattr(args, "org_name", None) is not None:
        return {"name": args.org_name}
    return None


def get_inc_key(args):
    if getattr(args, "inc", None) is not None:
        if args.inc.isdigit():
            return int(args.inc)
        elif re.match("I-([0-9]*)", args.inc):
            return {"friendlyname": args.inc}
        elif re.match("SOC-([a-zA-Z]*)-SIEM-([0-9]).*", args.inc):
            return {"title": args.inc}
    elif getattr(args, "inc_id", None) is not None:
        return int(args.inc_id)
    elif getattr(args, "inc_name", None) is not None:
        return {"friendlyname": args.inc_name}
    elif getattr(args, "inc_title", None) is not None:
        return {"title": args.inc_title}
    return None


def command_get(args):
    """Fetch the existing security incidents.
    """
    logger.info("invoking command_get")
    key     = {}
    inc_key = get_inc_key(args)
    org_key = get_org_key(args)
    # Setup incident's key selector
    if inc_key is not None:
        if isinstance(inc_key, dict):
            key.update(inc_key)
        else:
            key = inc_key
    # Setup organization's key selector
    if org_key is not None:
        key["org_id"] = org_key
    # Run query and assert results.
    res = get(key)
    incidents = res.get("objects", {})
    if incidents is None:
        incidents = {}
    # Display results.
    table = []
    for inc in [inc for _, inc in incidents.items()]:
        table.append([inc["key"],
                      inc["fields"]["friendlyname"],
                      inc["fields"]["title"],
                      inc["fields"]["org_id"],
                      inc["fields"]["org_id_friendlyname"],
                      inc["fields"]["operational_status"]])
    print(tabulate(table, headers=["Incident ID", "Incident Reference", "Incident Name", "Organization ID", "Organization Name", "Status"]))


def command_exists(args, interactive=True):
    """Check if a given case already exists.
    """
    logger.info("invoking command_exists")
    key     = {}
    inc_key = get_inc_key(args)
    # Setup incident's key selector
    if inc_key is not None:
        if isinstance(inc_key, dict):
            key.update(inc_key)
        else:
            key = inc_key
    # Run query
    res = get(key)
    if res["objects"] is not None and len(res["objects"]) > 0:
        logger.info("incident exists")
        if interactive is True:
            print("incident exists")
            sys.exit(0)
        return True
    else:
        logger.info("incident does not exists")
        if interactive is True:
            print("incident does not exists")
            sys.exit(1)
        return False


def command_publog(args, interactive=True):
    """Add a public log.
    """
    logger.info("invoking command_publog")
    key     = {}
    inc_key = get_inc_key(args)
    # Setup incident's key selector
    if inc_key is not None:
        if isinstance(inc_key, dict):
            key.update(inc_key)
        else:
            key = inc_key
    # Extract incident comments is needed.
    if args.diff is True:
        logger.info("extracting existing comments to performs the diff")
        res = get(key, output=["public_log"])
        if res["objects"] is not None and len(res["objects"]) == 1:
            for name, obj in res["objects"].items():
                for pl in obj["fields"]["public_log"]["entries"]:
                    logger.info("applying delta on text")
                    try:
                        args.text = re.sub(pl["message"], '', args.text, 1)
                    except Exception:
                        pass
                    logger.info("new text: ['{text}']".format(text=args.text))
    # Run.
    if len(args.text) > 0:
        fields = {"public_log": args.text, "status": "pending"}
        # res = update_stimulus(key, {"status": "new"}, stimulus="ev_new")
        res = update(key, {"public_log": args.text, "status": "pending"})
        # res = update_stimulus(key, {"public_log": args.text, "status": "pending"}, stimulus="ev_pending")
        # res = update()
        if interactive is True:
            print(json.dumps(res, indent=2))
        return res
    else:
        logger.info("no public log to append (probable delta strip result)")


def command_create(args, interactive=True):
    """Create or update a security incident.
    """
    logger.info("invoking command_create")
    exists = command_exists(args, interactive=False)
    if not exists:
        logger.info("creating new incident")
        variables = {}
        variables.update(parse_vars(args.vars))
        variables.update({"comment": args.text})
        fields = {
            "org_id": get_org_key(args),
            "title": args.inc_title,
            "description": render_template(args.template, variables),
            "urgency": args.inc_urgency,
            "public_log": args.text
        }
        res = create(fields=fields)
        if interactive is True:
            print(json.dumps(res, indent=2))
    else:
        logger.info("updating exisiting incident")
        res = command_publog(args, interactive=False)
    return res


def command_resolve(args, interactive=True):
    """switch a security incident state to 'Resolved'.
    """
    logger.info("invoking command_resolve")
    key     = {}
    inc_key = get_inc_key(args)
    # Setup incident's key selector
    if inc_key is not None:
        if isinstance(inc_key, dict):
            key.update(inc_key)
        else:
            key = inc_key
    # Run.
    fields = {"public_log": args.text, "status": "resolved"}
    res = update(key, fields)
    if interactive is True:
        print(json.dumps(res, indent=2))
    return res


def add_parser(sp):
    """Add parsers to base parsing structure.

    Arguments:
        sp (object): Sub-parsers container.
    """
    # =========================================================================
    # 'get' command.
    # =========================================================================
    p_get = sp.add_parser("incident-siem-get", help="Get existing SIEM incidents")
    p_get.set_defaults(func=command_get)
    # Organization and incident selector
    p_get_args = p_get.add_mutually_exclusive_group(required=False)
    p_get_args.add_argument("--org-id", type=int, dest="org_id", help="Customer ID", )
    p_get_args.add_argument("--org-code", type=str, dest="org_code", help="Customer Code")
    p_get_args.add_argument("--org-name", type=str, dest="org_name", help="Customer Name")
    p_get_args.add_argument("--inc", type=str, dest="inc", help="Incident (ID, name or title)")
    p_get_args.add_argument("--inc-id", type=int, dest="inc_id", help="Incident ID")
    p_get_args.add_argument("--inc-name", type=str, dest="inc_name", help="Incident name (looks like 'I-01234')")
    p_get_args.add_argument("--inc-title", type=str, dest="inc_title", help="Incident title (looks like 'SOC-CUST-SIEM-01234')")

    # =========================================================================
    # 'exists' command.
    # =========================================================================
    p_exists = sp.add_parser("incident-siem-exists", help="Check if a given case exists")
    p_exists.set_defaults(func=command_exists)
    # Incident selector
    p_exists_args = p_exists.add_mutually_exclusive_group(required=True)
    p_exists_args.add_argument("--inc", type=str, dest="inc", help="Incident (ID, name or title)")
    p_exists_args.add_argument("--inc-id", type=int, dest="inc_id", help="Incident ID")
    p_exists_args.add_argument("--inc-name", type=str, dest="inc_name", help="Incident name (looks like 'I-01234')")
    p_exists_args.add_argument("--inc-title", type=str, dest="inc_title", help="Incident title (looks like 'SOC-CUST-SIEM-01234')")

    # =========================================================================
    # 'publog' command.
    # =========================================================================
    p_publog = sp.add_parser("incident-siem-publog", help="Add a public log to an existing SIEM incident")
    p_publog.set_defaults(func=command_publog)
    # Incident selector
    p_publog_args = p_publog.add_mutually_exclusive_group(required=True)
    p_publog_args.add_argument("--inc", type=str, dest="inc", help="Incident (ID, name or title)")
    p_publog_args.add_argument("--inc-id", type=int, dest="inc_id", help="Incident ID")
    p_publog_args.add_argument("--inc-name", type=str, dest="inc_name", help="Incident name (looks like 'I-01234')")
    p_publog_args.add_argument("--inc-title", type=str, dest="inc_title", help="Incident title (looks like 'SOC-CUST-SIEM-01234')")
    # Comment
    p_publog.add_argument("--text", type=str, dest="text", required=True, help="Public log text (may contains basic HTML)")
    p_publog.add_argument("--diff", dest="diff", action="store_true", help="Keep only the difference between the existing comments and new text")

    # =========================================================================
    # 'create' command.
    # =========================================================================
    p_create = sp.add_parser("incident-siem-create", help="Create a new SIEM incident")
    p_create.set_defaults(func=command_create)
    # Organization selector
    p_create_args = p_create.add_mutually_exclusive_group(required=True)
    p_create_args.add_argument("--org-id", type=int, help="Customer ID", dest="org_id")
    p_create_args.add_argument("--org-code", type=str, help="Customer Code", dest="org_code")
    p_create_args.add_argument("--org-name", type=str, help="Customer Name", dest="org_name")
    # Case arguments
    p_create.add_argument("--inc-title", type=str, dest="inc_title", required=True, help="Incident title (looks like 'SOC-CUST-SIEM-01234')")
    p_create.add_argument("--inc-urgency", type=int, dest="inc_urgency", required=True, choices=[1, 2, 3, 4], help="Incident urgency (from 1 to 4)")
    # Template
    p_create.add_argument("--template", type=str, default=pkgrs(__name__, "static/incident_siem_template.html"), required=False, help="iTop mail template (supports Jinja2 HTML template)")
    p_create.add_argument("--vars", type=str, default=[], nargs='+', dest="vars", required=False, help="iTop mail template arguments as `key:value` list")
    # Public log
    p_create.add_argument("--text", type=str, dest="text", required=True, help="Comment and 1st public log text (may contains basic HTML)")
    p_create.add_argument("--diff", dest="diff", action="store_true", help="Keep only the difference between the existing comments and new text")

    # =========================================================================
    # 'resolve' command.
    # =========================================================================
    p_resolve = sp.add_parser("incident-siem-resolve", help="Resolved an exisiting SIEM incident")
    p_resolve.set_defaults(func=command_resolve)
    # Incident selector
    p_resolve_args = p_resolve.add_mutually_exclusive_group(required=True)
    p_resolve_args.add_argument("--inc", type=str, dest="inc", help="Incident (ID, name or title)")
    p_resolve_args.add_argument("--inc-id", type=int, dest="inc_id", help="Incident ID")
    p_resolve_args.add_argument("--inc-name", type=str, dest="inc_name", help="Incident name (looks like 'I-01234')")
    p_resolve_args.add_argument("--inc-title", type=str, dest="inc_title", help="Incident title (looks like 'SOC-CUST-SIEM-01234')")
    # Comment
    p_resolve.add_argument("--text", type=str, dest="text", help="Public log text (may contains basic HTML)")
